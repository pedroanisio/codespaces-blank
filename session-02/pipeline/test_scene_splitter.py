"""
Tests for scene_splitter.py — validates scene decomposition for parallel rendering.

Run: python -m pytest pipeline/test_scene_splitter.py -v
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from pipeline.scene_splitter import (
    AudioSlice,
    SceneRenderContext,
    TransitionHandle,
    decompose_color_grade,
    slice_audio_for_scene,
    split_instance_by_scene,
    _scene_time_ranges,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _load_spark() -> dict:
    path = EXAMPLES_DIR / "spark.gvpp.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _minimal_instance(
    *,
    n_scenes: int = 2,
    scene_dur: float = 5.0,
    audio_tracks: list[dict] | None = None,
    transitions: bool = False,
) -> dict:
    """Build a minimal v3 instance for testing."""
    shots = []
    scenes = []
    video_clips = []
    cursor = 0.0

    for si in range(1, n_scenes + 1):
        shot_id = f"shot-{si:02d}01"
        shots.append({
            "id": shot_id,
            "logicalId": shot_id,
            "entityType": "shot",
            "targetDurationSec": scene_dur,
            "sceneRef": {"id": f"scene-{si:02d}"},
        })
        scene = {
            "id": f"scene-{si:02d}",
            "logicalId": f"scene-{si:02d}",
            "entityType": "scene",
            "sceneNumber": si,
            "targetDurationSec": scene_dur,
            "shotRefs": [{"id": shot_id}],
        }
        if transitions:
            if si > 1:
                scene["transitionIn"] = {"type": "dissolve", "durationSec": 0.5}
            if si < n_scenes:
                scene["transitionOut"] = {"type": "dissolve", "durationSec": 0.5}
        scenes.append(scene)
        video_clips.append({
            "clipId": f"vc-{si:02d}",
            "sourceRef": {"id": shot_id},
            "timelineStartSec": cursor,
            "durationSec": scene_dur,
            "layerOrder": 0,
        })
        cursor += scene_dur

    total_dur = cursor

    if audio_tracks is None:
        audio_tracks = [
            {
                "clipId": "ac-score",
                "sourceRef": {"id": "aa-score"},
                "timelineStartSec": 0,
                "durationSec": total_dur,
                "layerOrder": 0,
            },
        ]

    return {
        "schemaVersion": "3.0.0",
        "package": {"packageId": "pkg-test"},
        "project": {"name": "Test", "targetRuntimeSec": total_dur},
        "qualityProfiles": [{
            "id": "qp-test",
            "profile": {
                "name": "Test",
                "video": {"resolution": {"widthPx": 1920, "heightPx": 1080},
                          "frameRate": {"fps": 24}},
                "audio": {"sampleRateHz": 44100, "channelLayout": "stereo"},
            },
        }],
        "canonicalDocuments": {
            "story": {},
            "script": {},
            "directorInstructions": {
                "colorDirection": "Desaturated blue-grey, golden warmth introduced at 8s"
            },
        },
        "production": {
            "characters": [],
            "environments": [],
            "props": [],
            "scenes": scenes,
            "shots": shots,
        },
        "assetLibrary": {
            "visualAssets": [],
            "audioAssets": [{"id": "aa-score", "logicalId": "aa-score",
                             "audioType": "music"}],
            "marketingAssets": [],
            "genericAssets": [],
        },
        "orchestration": {"workflows": []},
        "assembly": {
            "timelines": [{
                "id": "tl-master",
                "durationSec": total_dur,
                "videoClips": video_clips,
                "audioClips": audio_tracks,
            }],
            "editVersions": [],
            "renderPlans": [{
                "id": "rp-master",
                "operations": [
                    {
                        "opId": "op-mix",
                        "opType": "audioMix",
                        "tracks": [
                            {"audioRef": {"id": "aa-score"}, "gainDb": -3.0, "pan": 0},
                        ],
                    },
                    {
                        "opId": "op-grade",
                        "opType": "colorGrade",
                        "intent": "Desaturated blue-grey, golden warmth introduced at 8s",
                    },
                    {"opId": "op-encode", "opType": "encode"},
                ],
            }],
        },
        "deliverables": [],
        "relationships": [],
    }


# ── Test: split_instance_by_scene ─────────────────────────────────────────────

class TestSplitInstanceByScene(unittest.TestCase):

    def test_spark_returns_4_contexts(self):
        instance = _load_spark()
        contexts = split_instance_by_scene(instance)
        self.assertEqual(len(contexts), 4)

    def test_spark_scene_names(self):
        instance = _load_spark()
        contexts = split_instance_by_scene(instance)
        names = [c.scene["name"] for c in contexts]
        self.assertEqual(names, ["Desolation", "Discovery", "Sacrifice", "Light"])

    def test_spark_shot_counts(self):
        instance = _load_spark()
        contexts = split_instance_by_scene(instance)
        counts = [len(c.shots) for c in contexts]
        self.assertEqual(counts, [2, 2, 2, 2])

    def test_spark_total_shots_equals_instance(self):
        instance = _load_spark()
        contexts = split_instance_by_scene(instance)
        total = sum(len(c.shots) for c in contexts)
        self.assertEqual(total, len(instance["production"]["shots"]))

    def test_spark_time_ranges(self):
        instance = _load_spark()
        contexts = split_instance_by_scene(instance)
        ranges = [(c.scene_start_sec, c.scene_end_sec) for c in contexts]
        self.assertEqual(ranges, [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0), (12.0, 15.0)])

    def test_spark_scene_durations_sum_to_total(self):
        instance = _load_spark()
        contexts = split_instance_by_scene(instance)
        total = sum(c.scene_end_sec - c.scene_start_sec for c in contexts)
        self.assertAlmostEqual(total, 15.0)

    def test_spark_transitions(self):
        instance = _load_spark()
        contexts = split_instance_by_scene(instance)
        # Scene 1: no head, dissolve tail
        self.assertEqual(contexts[0].transition_head.type, "cut")
        self.assertEqual(contexts[0].transition_tail.type, "dissolve")
        self.assertAlmostEqual(contexts[0].transition_tail.duration_sec, 0.5)
        # Scene 2: dissolve head and tail
        self.assertEqual(contexts[1].transition_head.type, "dissolve")
        self.assertEqual(contexts[1].transition_tail.type, "dissolve")
        # Scene 4: dissolve head, no tail
        self.assertEqual(contexts[3].transition_head.type, "dissolve")
        self.assertEqual(contexts[3].transition_tail.type, "cut")

    def test_minimal_2_scenes(self):
        instance = _minimal_instance(n_scenes=2, scene_dur=5.0)
        contexts = split_instance_by_scene(instance)
        self.assertEqual(len(contexts), 2)
        self.assertAlmostEqual(contexts[0].scene_start_sec, 0.0)
        self.assertAlmostEqual(contexts[0].scene_end_sec, 5.0)
        self.assertAlmostEqual(contexts[1].scene_start_sec, 5.0)
        self.assertAlmostEqual(contexts[1].scene_end_sec, 10.0)

    def test_empty_instance(self):
        instance = {"production": {"scenes": [], "shots": []},
                     "assembly": {"timelines": [], "renderPlans": []},
                     "assetLibrary": {"audioAssets": []},
                     "qualityProfiles": [], "canonicalDocuments": {}}
        contexts = split_instance_by_scene(instance)
        self.assertEqual(contexts, [])

    def test_quality_profile_passed_through(self):
        instance = _minimal_instance()
        contexts = split_instance_by_scene(instance)
        self.assertEqual(contexts[0].quality_profile["name"], "Test")


# ── Test: slice_audio_for_scene ───────────────────────────────────────────────

class TestSliceAudioForScene(unittest.TestCase):

    def test_full_span_track_present_in_all_scenes(self):
        """A track spanning the full timeline should appear in every scene."""
        instance = _minimal_instance(n_scenes=3, scene_dur=5.0)
        for scene_start in [0.0, 5.0, 10.0]:
            slices = slice_audio_for_scene(scene_start, scene_start + 5.0, instance)
            score_slices = [s for s in slices if s.audio_asset_id == "aa-score"]
            self.assertEqual(len(score_slices), 1,
                             f"Score track missing at scene_start={scene_start}")

    def test_no_overlap_produces_empty(self):
        """A track outside the scene range should produce no slices."""
        audio_clips = [
            {"clipId": "ac-fx", "sourceRef": {"id": "aa-fx"},
             "timelineStartSec": 20, "durationSec": 5, "layerOrder": 1},
        ]
        instance = _minimal_instance(audio_tracks=audio_clips)
        slices = slice_audio_for_scene(0.0, 5.0, instance)
        fx_slices = [s for s in slices if s.audio_asset_id == "aa-fx"]
        self.assertEqual(len(fx_slices), 0)

    def test_partial_overlap_computes_intersection(self):
        """A track partially overlapping should be sliced to the intersection."""
        audio_clips = [
            {"clipId": "ac-fx", "sourceRef": {"id": "aa-fx"},
             "timelineStartSec": 3.0, "durationSec": 4.0, "layerOrder": 1},
        ]
        instance = _minimal_instance(n_scenes=2, scene_dur=5.0,
                                     audio_tracks=audio_clips)
        # Scene 1: 0-5s, track at 3-7s → intersection 3-5s → local 3-5s
        slices = slice_audio_for_scene(0.0, 5.0, instance)
        fx = [s for s in slices if s.audio_asset_id == "aa-fx"]
        self.assertEqual(len(fx), 1)
        self.assertAlmostEqual(fx[0].source_start_sec, 3.0)
        self.assertAlmostEqual(fx[0].source_end_sec, 5.0)
        self.assertAlmostEqual(fx[0].local_start_sec, 3.0)
        self.assertAlmostEqual(fx[0].local_end_sec, 5.0)

    def test_boundary_track_included(self):
        """A track starting exactly at scene boundary should be included."""
        audio_clips = [
            {"clipId": "ac-fx", "sourceRef": {"id": "aa-fx"},
             "timelineStartSec": 5.0, "durationSec": 3.0, "layerOrder": 1},
        ]
        instance = _minimal_instance(n_scenes=2, scene_dur=5.0,
                                     audio_tracks=audio_clips)
        # Scene 2: 5-10s, track at 5-8s → full overlap
        slices = slice_audio_for_scene(5.0, 10.0, instance)
        fx = [s for s in slices if s.audio_asset_id == "aa-fx"]
        self.assertEqual(len(fx), 1)
        self.assertAlmostEqual(fx[0].local_start_sec, 0.0)
        self.assertAlmostEqual(fx[0].local_end_sec, 3.0)

    def test_gain_and_pan_from_render_plan(self):
        """Gain and pan should be inherited from the render plan tracks."""
        instance = _load_spark()
        slices = slice_audio_for_scene(0.0, 4.0, instance)
        score = [s for s in slices if s.audio_asset_id == "aa-score"]
        self.assertEqual(len(score), 1)
        self.assertAlmostEqual(score[0].gain_db, -3.0)
        self.assertAlmostEqual(score[0].pan, 0.0)

    def test_spark_scene_03_has_9_audio_slices(self):
        """Scene 3 (Sacrifice) should have 9 audio tracks due to debris SFX."""
        instance = _load_spark()
        slices = slice_audio_for_scene(8.0, 12.0, instance)
        self.assertEqual(len(slices), 9)

    def test_spark_scene_04_has_ambient_warm(self):
        """Scene 4 should include the warm ambient that starts at 12s."""
        instance = _load_spark()
        slices = slice_audio_for_scene(12.0, 15.0, instance)
        warm = [s for s in slices if s.audio_asset_id == "aa-ambient-warm"]
        self.assertEqual(len(warm), 1)
        self.assertAlmostEqual(warm[0].local_start_sec, 0.0)
        self.assertAlmostEqual(warm[0].local_end_sec, 3.0)

    def test_fade_preserved_from_clip_transition(self):
        """Clip transitionIn/Out fades should propagate to the slice."""
        instance = _load_spark()
        slices = slice_audio_for_scene(12.0, 15.0, instance)
        warm = [s for s in slices if s.audio_asset_id == "aa-ambient-warm"]
        self.assertEqual(len(warm), 1)
        # aa-ambient-warm has transitionIn fade 0.8s starting at 12.0s
        self.assertAlmostEqual(warm[0].fade_in_sec, 0.8)


# ── Test: decompose_color_grade ───────────────────────────────────────────────

class TestDecomposeColorGrade(unittest.TestCase):

    def test_no_intent_returns_neutral(self):
        instance = {"assembly": {"renderPlans": []},
                     "canonicalDocuments": {"directorInstructions": {}}}
        result = decompose_color_grade(0, 5, 15, instance)
        self.assertAlmostEqual(result["brightness"], 0.0)
        self.assertAlmostEqual(result["contrast"], 1.0)
        self.assertAlmostEqual(result["saturation"], 1.0)

    def test_early_scene_is_cooler(self):
        """Scene at the start should have lower brightness/saturation."""
        instance = _load_spark()
        early = decompose_color_grade(0, 4, 15, instance)
        late = decompose_color_grade(12, 15, 15, instance)
        self.assertLess(early["brightness"], late["brightness"])
        self.assertLess(early["saturation"], late["saturation"])

    def test_late_scene_is_warmer(self):
        """Scene at the end should have higher brightness (warm shift)."""
        instance = _load_spark()
        late = decompose_color_grade(12, 15, 15, instance)
        self.assertGreater(late["brightness"], 0)

    def test_uniform_grade_when_no_temporal_arc(self):
        """Without temporal keywords, all scenes get the same grade."""
        instance = {
            "assembly": {"renderPlans": [{
                "operations": [{"opType": "colorGrade", "intent": "desaturated cool"}]
            }]},
            "canonicalDocuments": {"directorInstructions": {}},
        }
        g1 = decompose_color_grade(0, 5, 15, instance)
        g2 = decompose_color_grade(10, 15, 15, instance)
        self.assertAlmostEqual(g1["saturation"], g2["saturation"])
        self.assertAlmostEqual(g1["brightness"], g2["brightness"])

    def test_strength_scales_output(self):
        """Strength < 1 should reduce the effect."""
        instance = {
            "assembly": {"renderPlans": [{
                "operations": [{"opType": "colorGrade",
                                "intent": "desaturated cool", "strength": 0.5}]
            }]},
            "canonicalDocuments": {"directorInstructions": {}},
        }
        result = decompose_color_grade(0, 5, 15, instance)
        # Saturation should be closer to 1.0 than the full-strength version
        self.assertGreater(result["saturation"], 0.75)  # full strength would be 0.75


# ── Test: _scene_time_ranges ──────────────────────────────────────────────────

class TestSceneTimeRanges(unittest.TestCase):

    def test_spark_4_ranges(self):
        instance = _load_spark()
        ranges = _scene_time_ranges(instance)
        self.assertEqual(len(ranges), 4)

    def test_spark_contiguous(self):
        """Scene ranges should be contiguous (no gaps)."""
        instance = _load_spark()
        ranges = _scene_time_ranges(instance)
        for i in range(len(ranges) - 1):
            _, _, end = ranges[i]
            _, start, _ = ranges[i + 1]
            self.assertAlmostEqual(end, start,
                                   msg=f"Gap between scene {i+1} and {i+2}")

    def test_fallback_to_target_duration(self):
        """Without timeline, should derive from targetDurationSec."""
        instance = {
            "production": {
                "scenes": [
                    {"id": "s1", "sceneNumber": 1, "targetDurationSec": 5, "shotRefs": []},
                    {"id": "s2", "sceneNumber": 2, "targetDurationSec": 3, "shotRefs": []},
                ],
                "shots": [],
            },
            "assembly": {"timelines": []},
        }
        ranges = _scene_time_ranges(instance)
        self.assertEqual(len(ranges), 2)
        self.assertAlmostEqual(ranges[0][1], 0.0)
        self.assertAlmostEqual(ranges[0][2], 5.0)
        self.assertAlmostEqual(ranges[1][1], 5.0)
        self.assertAlmostEqual(ranges[1][2], 8.0)


# ── Test: integration with spark.gvpp.json ────────────────────────────────────

class TestSparkIntegration(unittest.TestCase):
    """End-to-end tests against the real Spark project instance."""

    def setUp(self):
        self.instance = _load_spark()
        self.contexts = split_instance_by_scene(self.instance)

    def test_all_shots_assigned(self):
        """Every shot in the instance must appear in exactly one context."""
        all_shots = self.instance["production"]["shots"]
        assigned_ids = set()
        for ctx in self.contexts:
            for shot in ctx.shots:
                shot_id = shot.get("id") or shot.get("logicalId")
                self.assertNotIn(shot_id, assigned_ids,
                                 f"Shot {shot_id} assigned to multiple scenes")
                assigned_ids.add(shot_id)
        instance_ids = {s.get("id") or s.get("logicalId") for s in all_shots}
        self.assertEqual(assigned_ids, instance_ids)

    def test_audio_coverage(self):
        """Every timeline audio clip should appear in at least one scene's slices."""
        tl = self.instance["assembly"]["timelines"][0]
        clip_ids = {(c.get("sourceRef") or {}).get("id", "") for c in tl["audioClips"]}
        sliced_ids: set[str] = set()
        for ctx in self.contexts:
            for s in ctx.audio_slices:
                sliced_ids.add(s.audio_asset_id)
        self.assertEqual(clip_ids, sliced_ids,
                         f"Missing: {clip_ids - sliced_ids}")

    def test_no_time_gaps_in_audio_score(self):
        """The score track should cover the full 0-15s across all scenes."""
        score_ranges: list[tuple[float, float]] = []
        for ctx in self.contexts:
            for s in ctx.audio_slices:
                if s.audio_asset_id == "aa-score":
                    score_ranges.append((s.source_start_sec, s.source_end_sec))
        score_ranges.sort()
        # Should be: (0,4), (4,8), (8,12), (12,15)
        self.assertEqual(len(score_ranges), 4)
        self.assertAlmostEqual(score_ranges[0][0], 0.0)
        self.assertAlmostEqual(score_ranges[-1][1], 15.0)
        for i in range(len(score_ranges) - 1):
            self.assertAlmostEqual(score_ranges[i][1], score_ranges[i + 1][0])

    def test_color_grade_monotonic_warmth(self):
        """Color grade brightness should increase from scene 1 to scene 4."""
        brightnesses = [c.color_grade_params["brightness"] for c in self.contexts]
        for i in range(len(brightnesses) - 1):
            self.assertLessEqual(brightnesses[i], brightnesses[i + 1],
                                 f"Brightness not monotonically increasing: {brightnesses}")

    def test_director_instructions_present(self):
        """Each context should carry the director instructions."""
        for ctx in self.contexts:
            self.assertIn("colorDirection", ctx.director_instructions)


if __name__ == "__main__":
    unittest.main()
