"""
Tests for scene-parallel rendering pipeline.

Validates:
  - assemble_scene() produces valid per-scene MP4s
  - stitch_scenes() joins segments with transitions
  - CLI --scene and --parallel-scenes flags
  - Equivalence: parallel render vs. monolithic render (duration check)

Run: python -m pytest pipeline/test_scene_parallel.py -v
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.assemble import assemble_scene, stitch_scenes
from pipeline.scene_splitter import split_instance_by_scene
from pipeline.run import main as run_main


# ── Helpers ──────────────────────────────────────────────────────────────────

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _load_spark() -> dict:
    return json.loads((EXAMPLES_DIR / "spark.gvpp.json").read_text(encoding="utf-8"))


def _ffprobe_duration(path: Path) -> float:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=5,
    )
    return float(probe.stdout.strip() or "0")


def _generate_stubs(instance: dict, output_dir: Path) -> tuple[dict, dict]:
    """Generate stub shots and audio. Returns (shot_clips, audio_files)."""
    from pipeline.generate import generate_shots, generate_audio
    import os
    # Clear API keys to force stub mode
    for key in ("RUNWAY_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "SUNO_COOKIE"):
        os.environ.pop(key, None)
    shot_clips = generate_shots(instance, output_dir)
    audio_files = generate_audio(instance, output_dir)
    return shot_clips, audio_files


# ── Test: assemble_scene ─────────────────────────────────────────────────────

class TestAssembleScene(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.instance = _load_spark()
        cls.contexts = split_instance_by_scene(cls.instance)
        cls.output_dir = Path("/tmp/test-assemble-scene")
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        cls.shot_clips, cls.audio_files = _generate_stubs(cls.instance, cls.output_dir)

    def test_scene_01_produces_mp4(self):
        path = assemble_scene(self.contexts[0], self.shot_clips, self.audio_files, self.output_dir)
        self.assertTrue(path.exists())
        self.assertTrue(path.suffix == ".mp4")

    def test_scene_01_duration(self):
        path = assemble_scene(self.contexts[0], self.shot_clips, self.audio_files, self.output_dir)
        dur = _ffprobe_duration(path)
        # Scene 01 target: 4.0s (shots: 2.5 + 1.5)
        self.assertAlmostEqual(dur, 4.0, delta=0.5)

    def test_scene_04_duration(self):
        path = assemble_scene(self.contexts[3], self.shot_clips, self.audio_files, self.output_dir)
        dur = _ffprobe_duration(path)
        # Scene 04 target: 3.0s (shots: 1.5 + 1.5)
        self.assertAlmostEqual(dur, 3.0, delta=0.5)

    def test_all_scenes_produce_output(self):
        for ctx in self.contexts:
            path = assemble_scene(ctx, self.shot_clips, self.audio_files, self.output_dir)
            self.assertTrue(path.exists(),
                            f"Scene {ctx.scene.get('name')} failed to produce output")

    def test_scene_segments_have_audio(self):
        """Scene segments should have audio tracks."""
        path = assemble_scene(self.contexts[0], self.shot_clips, self.audio_files, self.output_dir)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=5,
        )
        streams = probe.stdout.strip().split("\n")
        self.assertIn("audio", streams,
                       "Scene segment should contain an audio stream")


# ── Test: stitch_scenes ──────────────────────────────────────────────────────

class TestStitchScenes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.instance = _load_spark()
        cls.contexts = split_instance_by_scene(cls.instance)
        cls.output_dir = Path("/tmp/test-stitch-scenes")
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        shot_clips, audio_files = _generate_stubs(cls.instance, cls.output_dir)

        # Assemble all scene segments
        cls.segments = []
        for ctx in cls.contexts:
            path = assemble_scene(ctx, shot_clips, audio_files, cls.output_dir)
            cls.segments.append(path)

    def test_stitch_with_dissolves(self):
        transitions = [
            {"type": "dissolve", "durationSec": 0.5},
            {"type": "dissolve", "durationSec": 0.3},
            {"type": "dissolve", "durationSec": 0.5},
        ]
        path = stitch_scenes(self.segments, transitions, self.output_dir, self.instance)
        self.assertTrue(path.exists())
        dur = _ffprobe_duration(path)
        # Total: 4+4+4+3 = 15s minus transitions (0.5+0.3+0.5) ≈ 13.7s
        self.assertGreater(dur, 12.0)
        self.assertLess(dur, 16.0)

    def test_stitch_with_cuts(self):
        transitions = [
            {"type": "cut"},
            {"type": "cut"},
            {"type": "cut"},
        ]
        path = stitch_scenes(self.segments, transitions,
                             Path("/tmp/test-stitch-cuts"), self.instance)
        self.assertTrue(path.exists())
        dur = _ffprobe_duration(path)
        # With cuts: should be close to sum of segments
        segment_sum = sum(_ffprobe_duration(s) for s in self.segments)
        self.assertAlmostEqual(dur, segment_sum, delta=1.0)

    def test_stitch_output_name_from_project(self):
        transitions = [{"type": "cut"}] * (len(self.segments) - 1)
        path = stitch_scenes(self.segments, transitions, self.output_dir, self.instance)
        self.assertEqual(path.name, "spark.mp4")


# ── Test: CLI flags ──────────────────────────────────────────────────────────

class TestCLIFlags(unittest.TestCase):

    def test_scene_and_parallel_mutually_exclusive(self):
        ret = run_main(["render", "examples/spark.gvpp.json",
                        "--scene", "scene-01", "--parallel-scenes",
                        "--stub-only", "--output-dir", "/tmp/test-mutex"])
        self.assertEqual(ret, 1)

    def test_scene_flag_single_scene(self):
        ret = run_main(["render", "examples/spark.gvpp.json",
                        "--scene", "scene-02", "--stub-only",
                        "--output-dir", "/tmp/test-cli-scene02"])
        self.assertEqual(ret, 0)
        path = Path("/tmp/test-cli-scene02/scene-02.mp4")
        self.assertTrue(path.exists())

    def test_parallel_scenes_flag(self):
        ret = run_main(["render", "examples/spark.gvpp.json",
                        "--parallel-scenes", "--stub-only",
                        "--output-dir", "/tmp/test-cli-parallel"])
        self.assertEqual(ret, 0)
        path = Path("/tmp/test-cli-parallel/spark.mp4")
        self.assertTrue(path.exists())

    def test_invalid_scene_id(self):
        ret = run_main(["render", "examples/spark.gvpp.json",
                        "--scene", "scene-99", "--stub-only",
                        "--output-dir", "/tmp/test-cli-invalid"])
        self.assertEqual(ret, 1)

    def test_monolithic_still_works(self):
        ret = run_main(["render", "examples/spark.gvpp.json",
                        "--stub-only",
                        "--output-dir", "/tmp/test-cli-mono"])
        self.assertEqual(ret, 0)
        path = Path("/tmp/test-cli-mono/spark.mp4")
        self.assertTrue(path.exists())


# ── Test: equivalence ────────────────────────────────────────────────────────

class TestEquivalence(unittest.TestCase):
    """Verify parallel render produces output comparable to monolithic."""

    @classmethod
    def setUpClass(cls):
        # Monolithic
        run_main(["render", "examples/spark.gvpp.json",
                  "--stub-only", "--output-dir", "/tmp/test-equiv-mono"])
        cls.mono_path = Path("/tmp/test-equiv-mono/spark.mp4")

        # Parallel
        run_main(["render", "examples/spark.gvpp.json",
                  "--parallel-scenes", "--stub-only",
                  "--output-dir", "/tmp/test-equiv-para"])
        cls.para_path = Path("/tmp/test-equiv-para/spark.mp4")

    def test_both_exist(self):
        self.assertTrue(self.mono_path.exists())
        self.assertTrue(self.para_path.exists())

    def test_duration_within_tolerance(self):
        mono_dur = _ffprobe_duration(self.mono_path)
        para_dur = _ffprobe_duration(self.para_path)
        # Allow 2s tolerance (transitions + encoding differences)
        self.assertAlmostEqual(mono_dur, para_dur, delta=2.0)

    def test_both_have_audio(self):
        for path in (self.mono_path, self.para_path):
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "stream=codec_type", "-of", "csv=p=0", str(path)],
                capture_output=True, text=True, timeout=5,
            )
            streams = probe.stdout.strip().split("\n")
            self.assertIn("audio", streams, f"{path.name} should have audio")


if __name__ == "__main__":
    unittest.main()
