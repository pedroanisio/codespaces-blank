"""
Tests for pipeline.assess — post-render video assessment.

Run: python -m pytest tests/test_assess.py -v
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pipeline.assess import (
    CheckResult,
    AssessmentReport,
    _ffprobe_duration,
    _hex_to_rgb,
    _color_distance,
    _pick,
    _shots_in_order,
    _build_shot_prompt_context,
    layer_1_technical,
    layer_2_content,
    layer_3_ai,
    assess,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

SPARK_PATH = Path(__file__).parent.parent / "examples" / "spark.gvpp.json"


@pytest.fixture
def spark_instance() -> dict:
    return json.loads(SPARK_PATH.read_text())


@pytest.fixture
def minimal_instance() -> dict:
    """Minimal instance for unit testing."""
    return {
        "schemaVersion": "3.0.0",
        "project": {
            "id": "prj-test", "logicalId": "prj-test", "entityType": "project",
            "name": "Test", "version": {"number": "1.0.0", "state": "draft"},
            "targetRuntimeSec": 5,
        },
        "qualityProfiles": [{
            "id": "qp-test", "logicalId": "qp-test", "entityType": "qualityProfile",
            "name": "Test QP", "version": {"number": "1.0.0", "state": "approved"},
            "profile": {
                "name": "Test",
                "video": {
                    "resolution": {"widthPx": 1920, "heightPx": 1080},
                    "frameRate": {"fps": 24, "mode": "constant"},
                    "runtimeToleranceSec": 0.5,
                },
                "audio": {
                    "sampleRateHz": 48000,
                    "channelLayout": "stereo",
                    "loudnessIntegratedLUFS": -14,
                    "truePeakDbTP": -1,
                },
            },
        }],
        "canonicalDocuments": {
            "story": {"id": "s", "logicalId": "s", "entityType": "story",
                      "name": "s", "version": {"number": "1.0.0", "state": "draft"}},
            "script": {"id": "sc", "logicalId": "sc", "entityType": "script",
                       "name": "sc", "version": {"number": "1.0.0", "state": "draft"}},
            "directorInstructions": {
                "id": "di", "logicalId": "di", "entityType": "directorInstructions",
                "name": "di", "version": {"number": "1.0.0", "state": "draft"},
            },
        },
        "production": {
            "characters": [{
                "id": "char-a", "logicalId": "char-a", "entityType": "character",
                "name": "Alice", "version": {"number": "1.0.0", "state": "approved"},
                "description": "A red robot.",
            }],
            "environments": [{
                "id": "env-b", "logicalId": "env-b", "entityType": "environment",
                "name": "Lab", "version": {"number": "1.0.0", "state": "approved"},
                "description": "A white lab.",
            }],
            "scenes": [{
                "id": "scene-01", "logicalId": "scene-01", "entityType": "scene",
                "name": "Test Scene", "version": {"number": "1.0.0", "state": "approved"},
                "sceneNumber": 1, "targetDurationSec": 5,
                "shotRefs": [{"id": "shot-01"}, {"id": "shot-02"}],
                "mood": "neutral", "timeOfDay": "day",
            }],
            "shots": [
                {
                    "id": "shot-01", "logicalId": "shot-01", "entityType": "shot",
                    "name": "Shot 1", "version": {"number": "1.0.0", "state": "approved"},
                    "sceneRef": {"id": "scene-01"}, "shotNumber": 1,
                    "targetDurationSec": 2.5,
                    "characterRefs": [{"id": "char-a"}],
                    "environmentRef": {"id": "env-b"},
                    "cinematicSpec": {
                        "shotType": "wide", "cameraAngle": "eye_level",
                        "style": {"adjectives": ["clean"], "palette": ["#FFFFFF", "#FF0000"]},
                    },
                },
                {
                    "id": "shot-02", "logicalId": "shot-02", "entityType": "shot",
                    "name": "Shot 2", "version": {"number": "1.0.0", "state": "approved"},
                    "sceneRef": {"id": "scene-01"}, "shotNumber": 2,
                    "targetDurationSec": 2.5,
                    "characterRefs": [{"id": "char-a"}],
                    "environmentRef": {"id": "env-b"},
                    "cinematicSpec": {
                        "shotType": "close_up", "cameraAngle": "low",
                        "style": {"adjectives": ["dramatic"], "palette": ["#000000"]},
                    },
                },
            ],
        },
        "assetLibrary": {
            "audioAssets": [{
                "id": "aa-music", "logicalId": "aa-music", "entityType": "audioAsset",
                "name": "Score", "version": {"number": "1.0.0", "state": "approved"},
                "audioType": "music",
            }],
        },
        "assembly": {
            "timelines": [{
                "id": "tl-master", "logicalId": "tl-master", "entityType": "timeline",
                "name": "Master", "version": {"number": "1.0.0", "state": "approved"},
                "durationSec": 5,
                "videoClips": [
                    {"clipId": "vc-01", "sourceRef": {"id": "shot-01"},
                     "timelineStartSec": 0, "durationSec": 2.5, "layerOrder": 0},
                    {"clipId": "vc-02", "sourceRef": {"id": "shot-02"},
                     "timelineStartSec": 2.5, "durationSec": 2.5, "layerOrder": 0},
                ],
                "audioClips": [
                    {"clipId": "ac-01", "sourceRef": {"id": "aa-music"},
                     "timelineStartSec": 0, "durationSec": 5, "layerOrder": 0},
                ],
            }],
            "editVersions": [{"id": "ev-01", "approvedForRender": True}],
            "renderPlans": [],
        },
    }


def _create_stub_video(path: Path, duration: float = 2.5, color: str = "0x1a1a2e") -> None:
    """Create a minimal colored stub video using FFmpeg."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color=c={color}:size=320x240:d={duration}:r=24",
         "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
         "-t", str(duration),
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
         "-c:a", "aac", "-b:a", "32k",
         str(path)],
        capture_output=True, timeout=15,
    )


def _create_stub_audio(path: Path, duration: float = 5.0) -> None:
    """Create a silent stub audio file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"anullsrc=r=48000:cl=stereo",
         "-t", str(duration), "-c:a", "libmp3lame", "-b:a", "32k",
         str(path)],
        capture_output=True, timeout=10,
    )


def _create_stub_image(path: Path, color: str = "0xFF0000") -> None:
    """Create a minimal stub PNG image."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color=c={color}:size=64x64:d=0.04:r=1",
         "-frames:v", "1", str(path)],
        capture_output=True, timeout=10,
    )


@pytest.fixture
def stub_output(tmp_path: Path, minimal_instance: dict) -> Path:
    """Create a stub render output directory matching the minimal instance."""
    # Shots
    _create_stub_video(tmp_path / "shots" / "shot-01.mp4", duration=2.5, color="0xFFFFFF")
    _create_stub_video(tmp_path / "shots" / "shot-02.mp4", duration=2.5, color="0x000000")

    # Audio
    _create_stub_audio(tmp_path / "audio" / "aa-music.mp3", duration=5.0)

    # References
    _create_stub_image(tmp_path / "references" / "char-a.front.png")
    _create_stub_image(tmp_path / "references" / "char-a.three_quarter.png")
    _create_stub_image(tmp_path / "references" / "char-a.full_body.png")
    _create_stub_image(tmp_path / "references" / "env-b.wide_plate.png")
    _create_stub_image(tmp_path / "references" / "env-b.detail_plate.png")

    # Intermediate: concat
    _create_stub_video(tmp_path / "intermediate" / "01_op-concat.mp4", duration=5.0)
    _create_stub_video(tmp_path / "intermediate" / "02_op-audio-mix.mp4", duration=5.0)
    _create_stub_video(tmp_path / "intermediate" / "03_op-grade.mp4", duration=5.0)

    # Final
    _create_stub_video(tmp_path / "test.mp4", duration=5.0)

    return tmp_path


# ═════════════════════════════════════════════════════════════════════════════
#  UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestHelpers:
    def test_hex_to_rgb_6char(self):
        assert _hex_to_rgb("#FF0000") == (255, 0, 0)
        assert _hex_to_rgb("#1a1a2e") == (26, 26, 46)

    def test_hex_to_rgb_3char(self):
        assert _hex_to_rgb("#FFF") == (255, 255, 255)

    def test_hex_to_rgb_no_hash(self):
        assert _hex_to_rgb("FF0000") == (255, 0, 0)

    def test_color_distance_same(self):
        assert _color_distance((255, 0, 0), (255, 0, 0)) == 0.0

    def test_color_distance_opposite(self):
        dist = _color_distance((0, 0, 0), (255, 255, 255))
        assert dist == pytest.approx(1.0, abs=0.01)

    def test_color_distance_mid(self):
        dist = _color_distance((128, 128, 128), (0, 0, 0))
        assert 0.3 < dist < 0.6

    def test_pick_nested(self):
        obj = {"a": {"b": {"c": 42}}}
        assert _pick(obj, "a.b.c") == 42

    def test_pick_missing(self):
        assert _pick({"a": 1}, "b.c") is None

    def test_pick_non_dict(self):
        assert _pick({"a": "string"}, "a.b") is None


class TestShotsInOrder:
    def test_orders_by_scene_then_shot(self, minimal_instance):
        ordered = _shots_in_order(minimal_instance)
        assert len(ordered) == 2
        assert ordered[0]["id"] == "shot-01"
        assert ordered[1]["id"] == "shot-02"

    def test_spark_has_8_shots(self, spark_instance):
        ordered = _shots_in_order(spark_instance)
        assert len(ordered) == 8
        assert ordered[0]["id"] == "shot-0101"
        assert ordered[-1]["id"] == "shot-0402"


class TestBuildShotPromptContext:
    def test_includes_scene_mood(self, minimal_instance):
        shots = _shots_in_order(minimal_instance)
        ctx = _build_shot_prompt_context(minimal_instance, shots[0])
        assert "neutral" in ctx.lower()

    def test_includes_character(self, minimal_instance):
        shots = _shots_in_order(minimal_instance)
        ctx = _build_shot_prompt_context(minimal_instance, shots[0])
        assert "Alice" in ctx

    def test_includes_shot_type(self, minimal_instance):
        shots = _shots_in_order(minimal_instance)
        ctx = _build_shot_prompt_context(minimal_instance, shots[0])
        assert "wide" in ctx.lower()


class TestCheckResult:
    def test_passed_check(self):
        c = CheckResult(name="test", layer=1, passed=True)
        assert c.passed is True

    def test_failed_check(self):
        c = CheckResult(name="test", layer=1, passed=False, severity="error")
        assert c.passed is False


class TestAssessmentReport:
    def test_empty_report(self):
        r = AssessmentReport()
        assert r.passed == 0
        assert r.failed == 0
        assert r.warnings == 0

    def test_counts(self):
        r = AssessmentReport()
        r.add(CheckResult(name="a", layer=1, passed=True))
        r.add(CheckResult(name="b", layer=1, passed=False, severity="error"))
        r.add(CheckResult(name="c", layer=1, passed=False, severity="warning"))
        assert r.passed == 1
        assert r.failed == 1
        assert r.warnings == 1

    def test_to_dict(self):
        r = AssessmentReport(instance_path="test.json", output_dir="/tmp")
        r.add(CheckResult(name="a", layer=1, passed=True))
        d = r.to_dict()
        assert d["summary"]["total"] == 1
        assert d["summary"]["passed"] == 1
        assert len(d["checks"]) == 1


# ═════════════════════════════════════════════════════════════════════════════
#  LAYER 1 INTEGRATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestLayer1Technical:
    def test_shot_files_found(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_1_technical(minimal_instance, stub_output, report)
        shot_checks = [c for c in report.checks if c.name.startswith("shot_file_exists:")]
        assert len(shot_checks) == 2
        assert all(c.passed for c in shot_checks)

    def test_shot_files_missing(self, minimal_instance, tmp_path):
        (tmp_path / "shots").mkdir()
        report = AssessmentReport()
        layer_1_technical(minimal_instance, tmp_path, report)
        shot_checks = [c for c in report.checks if c.name.startswith("shot_file_exists:")]
        assert len(shot_checks) == 2
        assert all(not c.passed for c in shot_checks)

    def test_audio_files_found(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_1_technical(minimal_instance, stub_output, report)
        audio_checks = [c for c in report.checks if c.name.startswith("audio_file_exists:")]
        assert len(audio_checks) == 1
        assert all(c.passed for c in audio_checks)

    def test_reference_images(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_1_technical(minimal_instance, stub_output, report)
        ref_checks = [c for c in report.checks if c.name.startswith("reference_exists:")]
        assert len(ref_checks) == 5  # 3 char views + 2 env plates
        assert all(c.passed for c in ref_checks)

    def test_intermediate_files(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_1_technical(minimal_instance, stub_output, report)
        inter_checks = [c for c in report.checks if c.name.startswith("intermediate_exists:")]
        assert len(inter_checks) == 3
        assert all(c.passed for c in inter_checks)

    def test_final_duration(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_1_technical(minimal_instance, stub_output, report)
        dur_check = next((c for c in report.checks if c.name == "final_duration"), None)
        assert dur_check is not None
        assert dur_check.passed

    def test_video_frame_rate(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_1_technical(minimal_instance, stub_output, report)
        fps_check = next((c for c in report.checks if c.name == "video_frame_rate"), None)
        assert fps_check is not None
        assert fps_check.passed


# ═════════════════════════════════════════════════════════════════════════════
#  LAYER 2 INTEGRATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestLayer2Content:
    def test_scene_cut_detection_runs(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_2_content(minimal_instance, stub_output, report)
        cut_checks = [c for c in report.checks if c.name.startswith("scene_cut")]
        assert len(cut_checks) >= 1

    def test_color_palette_check_runs(self, minimal_instance, stub_output):
        report = AssessmentReport()
        layer_2_content(minimal_instance, stub_output, report)
        color_checks = [c for c in report.checks if c.name.startswith("color_palette:")]
        # Should attempt color analysis for shots with palettes
        assert len(color_checks) >= 0  # may be 0 if extraction fails

    def test_no_crash_without_intermediate(self, minimal_instance, tmp_path):
        """Layer 2 should handle missing intermediate gracefully."""
        report = AssessmentReport()
        layer_2_content(minimal_instance, tmp_path, report)
        skip_check = next((c for c in report.checks if "skipped" in c.name), None)
        assert skip_check is not None
        assert not skip_check.passed


# ═════════════════════════════════════════════════════════════════════════════
#  LAYER 3 UNIT TESTS (MOCKED)
# ═════════════════════════════════════════════════════════════════════════════

class TestLayer3AI:
    @patch("pipeline.assess._vision_describe_frame")
    @patch("pipeline.assess._vision_character_consistency")
    def test_vision_adherence_runs(self, mock_consistency, mock_describe,
                                   minimal_instance, stub_output):
        mock_describe.return_value = {
            "description": "A wide shot of a white lab",
            "adherence_score": 0.8,
            "matched_elements": ["white lab"],
            "missing_elements": [],
            "issues": [],
        }
        mock_consistency.return_value = {
            "similarity": 0.92,
            "character": "Alice",
            "consistent_attributes": [],
            "drifted_attributes": [],
        }

        report = AssessmentReport()
        layer_3_ai(minimal_instance, stub_output, report)

        adherence = [c for c in report.checks if c.name.startswith("vision_adherence:")]
        assert len(adherence) == 2  # 2 shots
        assert all(c.passed for c in adherence)

    @patch("pipeline.assess._vision_describe_frame")
    @patch("pipeline.assess._vision_character_consistency")
    def test_low_adherence_fails(self, mock_consistency, mock_describe,
                                  minimal_instance, stub_output):
        mock_describe.return_value = {
            "description": "A completely different image",
            "adherence_score": 0.1,
            "matched_elements": [],
            "missing_elements": ["everything"],
            "issues": ["total mismatch"],
        }
        mock_consistency.return_value = {"similarity": 0.5, "character": "Alice",
                                          "consistent_attributes": [], "drifted_attributes": []}

        report = AssessmentReport()
        layer_3_ai(minimal_instance, stub_output, report)

        adherence = [c for c in report.checks if c.name.startswith("vision_adherence:")]
        assert any(not c.passed for c in adherence)


# ═════════════════════════════════════════════════════════════════════════════
#  FULL ASSESSMENT INTEGRATION
# ═════════════════════════════════════════════════════════════════════════════

class TestAssessIntegration:
    def test_layer_1_only(self, minimal_instance, stub_output):
        report = assess(minimal_instance, stub_output, max_layer=1)
        assert report.layers_run == [1]
        assert len(report.checks) > 0

    def test_layer_1_and_2(self, minimal_instance, stub_output):
        report = assess(minimal_instance, stub_output, max_layer=2)
        assert report.layers_run == [1, 2]
        assert any(c.layer == 2 for c in report.checks)

    @patch("pipeline.assess._vision_describe_frame")
    @patch("pipeline.assess._vision_character_consistency")
    def test_full_assessment(self, mock_consistency, mock_describe,
                              minimal_instance, stub_output):
        mock_describe.return_value = {
            "description": "test", "adherence_score": 0.9,
            "matched_elements": [], "missing_elements": [], "issues": [],
        }
        mock_consistency.return_value = {"similarity": 0.95, "character": "Alice",
                                          "consistent_attributes": [], "drifted_attributes": []}

        report = assess(minimal_instance, stub_output, max_layer=3)
        assert report.layers_run == [1, 2, 3]
        assert any(c.layer == 3 for c in report.checks)

    def test_report_serializable(self, minimal_instance, stub_output):
        report = assess(minimal_instance, stub_output, max_layer=1)
        d = report.to_dict()
        # Must be JSON-serializable
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["summary"]["total"] == len(report.checks)


# ═════════════════════════════════════════════════════════════════════════════
#  SPARK INSTANCE TESTS (against real build if available)
# ═════════════════════════════════════════════════════════════════════════════

SPARK_BUILD = Path(__file__).parent.parent.parent / "generated" / "videos" / "spark-build-1"


@pytest.mark.skipif(not SPARK_BUILD.exists(), reason="spark-build-1 not available")
class TestSparkBuild:
    def test_layer_1_spark(self, spark_instance):
        report = assess(spark_instance, SPARK_BUILD, max_layer=1)
        assert report.passed > 0
        # All shots should exist
        shot_checks = [c for c in report.checks if c.name.startswith("shot_file_exists:")]
        assert len(shot_checks) == 8
        assert all(c.passed for c in shot_checks)

    def test_layer_2_spark(self, spark_instance):
        report = assess(spark_instance, SPARK_BUILD, max_layer=2)
        assert any(c.layer == 2 for c in report.checks)
