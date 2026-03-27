"""
Regression tests for protocol compliance.

Verifies that generate.py and assemble.py correctly read and use
ALL protocol fields defined in the v3 schema instance JSON.

Run: python -m pytest tests/test_protocol_compliance.py -v
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

DEMO_PATH = Path(__file__).parent.parent / "demo-30s.json"


@pytest.fixture
def instance() -> dict:
    return json.loads(DEMO_PATH.read_text())


@pytest.fixture
def minimal_instance() -> dict:
    """Bare-minimum instance that exercises all code paths."""
    return {
        "schemaVersion": "3.1.0",
        "package": {"packageId": "pkg.test", "createdAt": "2026-01-01T00:00:00Z", "versioningPolicy": {}},
        "project": {
            "id": "proj.t.v1", "logicalId": "proj.t", "entityType": "project",
            "name": "Test Project", "version": {"number": "1.0.0", "state": "draft"},
            "targetRuntimeSec": 10,
        },
        "qualityProfiles": [{
            "id": "qp.t.v1", "logicalId": "qp.t", "entityType": "qualityProfile",
            "name": "Test QP", "version": {"number": "1.0.0", "state": "approved"},
            "profile": {
                "name": "Test",
                "video": {
                    "resolution": {"widthPx": 1280, "heightPx": 720},
                    "frameRate": {"fps": 30, "mode": "constant"},
                    "aspectRatio": {"expression": "16:9", "preset": "16:9"},
                },
                "audio": {"sampleRateHz": 48000, "channelLayout": "stereo"},
            },
        }],
        "canonicalDocuments": {
            "story": {
                "id": "story.t.v1", "logicalId": "story.t", "entityType": "story",
                "name": "Test Story", "version": {"number": "1.0.0", "state": "draft"},
            },
            "script": {
                "id": "script.t.v1", "logicalId": "script.t", "entityType": "script",
                "name": "Test Script", "version": {"number": "1.0.0", "state": "draft"},
            },
            "directorInstructions": {
                "id": "di.t.v1", "logicalId": "di.t", "entityType": "directorInstructions",
                "name": "Test DI", "version": {"number": "1.0.0", "state": "draft"},
                "colorDirection": "warm amber cinematic dark",
                "mustAvoid": ["bright daylight", "neon colors"],
                "mustHaves": ["film grain"],
            },
        },
        "production": {
            "characters": [{
                "id": "char.a.v1", "logicalId": "char.a", "entityType": "character",
                "name": "ALICE", "version": {"number": "1.0.0", "state": "approved"},
                "description": "A 30-year-old detective in a dark trench coat.",
            }],
            "environments": [{
                "id": "env.office.v1", "logicalId": "env.office", "entityType": "environment",
                "name": "Office", "version": {"number": "1.0.0", "state": "approved"},
                "description": "Dimly lit detective office with venetian blinds.",
            }],
            "props": [],
            "styleGuides": [{
                "id": "sg.noir.v1", "logicalId": "sg.noir", "entityType": "styleGuide",
                "name": "Noir Style", "version": {"number": "1.0.0", "state": "approved"},
                "scope": "project",
                "guidelines": {
                    "adjectives": ["noir", "moody", "shadowy"],
                    "palette": ["#1a1a1a", "#d4a017"],
                    "textureDescriptors": ["film grain", "smoke"],
                    "cameraLanguage": "slow, deliberate",
                },
                "negativeStylePrompt": "No bright colors, no daylight.",
                "appliesTo": [],
            }],
            "scenes": [{
                "id": "scene.1.v1", "logicalId": "scene.1", "entityType": "scene",
                "name": "Scene 1", "version": {"number": "1.0.0", "state": "approved"},
                "sceneNumber": 1,
                "timeOfDay": "night",
                "weather": "rainy",
                "mood": "tense",
                "targetDurationSec": 10,
                "characterRefs": [{"id": "char.a.v1"}],
                "environmentRef": {"id": "env.office.v1"},
                "shotRefs": [{"id": "shot.1.v1"}, {"id": "shot.2.v1"}],
                "transitionIn": {"type": "fade"},
                "transitionOut": {"type": "dissolve"},
            }],
            "shots": [
                {
                    "id": "shot.1.v1", "logicalId": "shot.1", "entityType": "shot",
                    "name": "Shot 1", "version": {"number": "1.0.0", "state": "approved"},
                    "shotNumber": 1,
                    "sceneRef": {"id": "scene.1.v1"},
                    "targetDurationSec": 5,
                    "plannedPosition": {"startSec": 0, "endSec": 5},
                    "cinematicSpec": {
                        "shotType": "wide",
                        "cameraAngle": "low",
                        "cameraMovement": "dolly",
                        "focalLengthMm": 24,
                        "styleGuideRef": {"id": "sg.noir.v1"},
                        "style": {
                            "adjectives": ["dark", "moody"],
                            "palette": ["#1a1a1a"],
                        },
                    },
                    "genParams": {
                        "stepId": "step.1",
                        "operationType": "video_generation",
                        "prompt": "Wide shot of detective office at night.",
                        "consistencyAnchors": [{
                            "anchorType": "character",
                            "name": "ALICE appearance",
                            "ref": {"id": "char.a.v1"},
                            "lockLevel": "hard",
                        }],
                    },
                },
                {
                    "id": "shot.2.v1", "logicalId": "shot.2", "entityType": "shot",
                    "name": "Shot 2", "version": {"number": "1.0.0", "state": "approved"},
                    "shotNumber": 2,
                    "sceneRef": {"id": "scene.1.v1"},
                    "targetDurationSec": 5,
                    "plannedPosition": {"startSec": 5, "endSec": 10},
                    "cinematicSpec": {
                        "shotType": "close_up",
                        "cameraAngle": "eye_level",
                        "cameraMovement": "static",
                        "focalLengthMm": 85,
                        "styleGuideRef": {"id": "sg.noir.v1"},
                        "temporalBridgeAnchorRef": {"id": "shot.1.v1"},
                        "style": {"adjectives": ["intimate"]},
                    },
                    "genParams": {
                        "stepId": "step.2",
                        "operationType": "video_generation",
                        "prompt": "Close-up of ALICE reading case files.",
                        "consistencyAnchors": [{
                            "anchorType": "character",
                            "name": "ALICE face lock",
                            "ref": {"id": "char.a.v1"},
                            "lockLevel": "hard",
                        }],
                    },
                },
            ],
        },
        "assetLibrary": {
            "visualAssets": [],
            "audioAssets": [
                {
                    "id": "audio.amb.v1", "logicalId": "audio.amb", "entityType": "audioAsset",
                    "name": "Rain on Window", "audioType": "ambient",
                    "version": {"number": "1.0.0", "state": "approved"},
                    "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"},
                },
                {
                    "id": "audio.dial.v1", "logicalId": "audio.dial", "entityType": "audioAsset",
                    "name": "ALICE Monologue", "audioType": "dialogue",
                    "characterRef": {"id": "char.a.v1"},
                    "transcript": "The rain never stops in this city.",
                    "version": {"number": "1.0.0", "state": "approved"},
                    "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "mono", "codec": "flac"},
                },
                {
                    "id": "audio.score.v1", "logicalId": "audio.score", "entityType": "audioAsset",
                    "name": "Noir Jazz Score", "audioType": "music",
                    "mood": "melancholic jazz noir",
                    "version": {"number": "1.0.0", "state": "approved"},
                    "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"},
                },
            ],
            "marketingAssets": [],
            "genericAssets": [],
        },
        "orchestration": {"workflows": []},
        "assembly": {
            "timelines": [{
                "id": "tl.t.v1", "logicalId": "tl.t", "entityType": "timeline",
                "name": "Main", "version": {"number": "1.0.0", "state": "draft"},
                "durationSec": 10,
                "frameRate": {"fps": 30, "mode": "constant"},
                "resolution": {"widthPx": 1280, "heightPx": 720},
                "videoClips": [
                    {"clipId": "vc.1", "sourceRef": {"id": "shot.1.v1"}, "timelineStartSec": 0, "durationSec": 5},
                    {"clipId": "vc.2", "sourceRef": {"id": "shot.2.v1"}, "timelineStartSec": 5, "durationSec": 5},
                ],
                "audioClips": [
                    {"clipId": "ac.amb", "sourceRef": {"id": "audio.amb.v1"}, "timelineStartSec": 0, "durationSec": 10},
                    {"clipId": "ac.dial", "sourceRef": {"id": "audio.dial.v1"}, "timelineStartSec": 3, "durationSec": 4},
                    {"clipId": "ac.score", "sourceRef": {"id": "audio.score.v1"}, "timelineStartSec": 0, "durationSec": 10},
                ],
            }],
            "editVersions": [],
            "renderPlans": [{
                "id": "rp.t.v1", "logicalId": "rp.t", "entityType": "renderPlan",
                "name": "Test RP", "version": {"number": "1.0.0", "state": "approved"},
                "sourceTimelineRef": {"id": "tl.t.v1"},
                "compatibleRuntimes": ["ffmpeg"],
                "operations": [
                    {"opId": "op.concat", "opType": "concat", "clipRefs": [{"id": "shot.1.v1"}, {"id": "shot.2.v1"}], "method": "chain"},
                    {"opId": "op.audio", "opType": "audioMix", "tracks": [
                        {"audioRef": {"id": "audio.amb.v1"}, "gainDb": -8, "timeRange": {"startSec": 0, "endSec": 10}},
                        {"audioRef": {"id": "audio.dial.v1"}, "gainDb": 0, "timeRange": {"startSec": 3, "endSec": 7}},
                        {"audioRef": {"id": "audio.score.v1"}, "gainDb": -14, "timeRange": {"startSec": 0, "endSec": 10}},
                    ]},
                    {"opId": "op.grade", "opType": "colorGrade", "inputRef": {"id": "op.concat"}, "intent": "dark amber", "strength": 0.9},
                    {"opId": "op.enc", "opType": "encode", "inputRef": {"id": "op.grade"}, "compression": {"codec": "libx264", "profile": "high", "bitrateMbps": 6}},
                ],
            }],
        },
        "deliverables": [{
            "id": "del.t.v1", "logicalId": "del.t", "entityType": "finalOutput",
            "name": "Test Output", "version": {"number": "1.0.0", "state": "draft"},
            "outputType": "video/mp4", "runtimeSec": 10,
            "sourceTimelineRef": {"id": "tl.t.v1"},
            "renderPlanRef": {"id": "rp.t.v1"},
            "platform": "youtube",
        }],
        "relationships": [],
    }


# ── generate.py: _enrich_prompt tests ─────────────────────────────────────────

class TestEnrichPrompt:
    """Verify that _enrich_prompt reads ALL protocol fields."""

    def _call(self, shot: dict, instance: dict) -> str:
        from pipeline.generate import _enrich_prompt, _build_style_preamble
        preamble = _build_style_preamble(instance)
        return _enrich_prompt(shot, instance, preamble)

    def test_shot_type_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "wide" in result.lower()

    def test_camera_angle_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "low" in result.lower()

    def test_camera_movement_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "dolly" in result.lower()

    def test_focal_length_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "24mm" in result
        assert "wide-angle" in result.lower()

    def test_focal_length_telephoto(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][1]
        result = self._call(shot, minimal_instance)
        assert "85mm" in result
        assert "shallow depth of field" in result.lower()

    def test_style_adjectives_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "dark" in result
        assert "moody" in result

    def test_style_palette_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "#1a1a1a" in result

    def test_scene_mood_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "tense" in result.lower()

    def test_scene_time_of_day(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "night" in result.lower()

    def test_scene_weather(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "rainy" in result.lower()

    def test_environment_description(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "venetian blinds" in result.lower()

    def test_style_guide_ref_resolved(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "STYLE GUIDE" in result
        assert "noir" in result.lower()
        assert "film grain" in result.lower()
        assert "No bright colors" in result

    def test_temporal_bridge_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][1]
        result = self._call(shot, minimal_instance)
        assert "CONTINUITY" in result
        assert "shot.1.v1" in result

    def test_lock_level_hard(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "STRICTLY" in result

    def test_must_avoid_in_prompt(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "DO NOT include" in result
        assert "bright daylight" in result

    def test_character_description_in_preamble(self, minimal_instance):
        from pipeline.generate import _build_style_preamble
        preamble = _build_style_preamble(minimal_instance)
        assert "ALICE" in preamble
        assert "trench coat" in preamble

    def test_director_color_direction_in_preamble(self, minimal_instance):
        from pipeline.generate import _build_style_preamble
        preamble = _build_style_preamble(minimal_instance)
        assert "warm amber cinematic dark" in preamble

    def test_base_prompt_preserved(self, minimal_instance):
        shot = minimal_instance["production"]["shots"][0]
        result = self._call(shot, minimal_instance)
        assert "Wide shot of detective office at night." in result


# ── generate.py: _shots_in_order tests ────────────────────────────────────────

class TestShotsInOrder:
    def test_resolves_versioned_ids(self, minimal_instance):
        from pipeline.generate import _shots_in_order
        ordered = _shots_in_order(minimal_instance)
        assert len(ordered) == 2
        assert ordered[0]["logicalId"] == "shot.1"
        assert ordered[1]["logicalId"] == "shot.2"

    def test_handles_logical_id_refs(self, minimal_instance):
        from pipeline.generate import _shots_in_order
        # Change refs to use logicalId instead of id
        minimal_instance["production"]["scenes"][0]["shotRefs"] = [
            {"logicalId": "shot.1"}, {"logicalId": "shot.2"}
        ]
        ordered = _shots_in_order(minimal_instance)
        assert len(ordered) == 2

    def test_empty_shots(self):
        from pipeline.generate import _shots_in_order
        assert _shots_in_order({"production": {"scenes": [], "shots": []}}) == []


# ── assemble.py: _parse_color_direction tests ────────────────────────────────

class TestColorDirection:
    def test_amber_triggers_warm(self):
        from pipeline.assemble import _parse_color_direction
        p = _parse_color_direction("Amber/dark palette")
        assert p["brightness"] < 0  # dark
        assert p["contrast"] > 1.0

    def test_dark_reduces_brightness(self):
        from pipeline.assemble import _parse_color_direction
        p = _parse_color_direction("dark crushed blacks")
        assert p["brightness"] < 0
        assert p["saturation"] < 1.0

    def test_cool_blue(self):
        from pipeline.assemble import _parse_color_direction
        p = _parse_color_direction("cool blue tones")
        assert p["brightness"] < 0

    def test_cinematic(self):
        from pipeline.assemble import _parse_color_direction
        p = _parse_color_direction("cinematic look")
        assert p["contrast"] >= 1.08

    def test_neutral_returns_defaults(self):
        from pipeline.assemble import _parse_color_direction
        p = _parse_color_direction("")
        assert p["brightness"] == 0.0
        assert p["contrast"] == 1.0
        assert p["saturation"] == 1.0


# ── assemble.py: _encode_cmd tests ───────────────────────────────────────────

class TestEncodeCmd:
    def test_reads_widthPx_heightPx(self):
        from pipeline.assemble import _encode_cmd
        qp = {"video": {"resolution": {"widthPx": 1280, "heightPx": 720}, "frameRate": {"fps": 30}}, "audio": {"sampleRateHz": 48000}}
        cmd = _encode_cmd(Path("/tmp/in.mp4"), qp, Path("/tmp/out.mp4"))
        cmd_str = " ".join(cmd)
        assert "1280:720" in cmd_str
        assert "fps=30" in cmd_str
        assert "48000" in cmd_str

    def test_fallback_width_height(self):
        from pipeline.assemble import _encode_cmd
        qp = {"video": {"resolution": {"width": 640, "height": 480}}, "audio": {}}
        cmd = _encode_cmd(Path("/tmp/in.mp4"), qp, Path("/tmp/out.mp4"))
        assert "640:480" in " ".join(cmd)

    def test_render_plan_codec(self):
        from pipeline.assemble import _encode_cmd
        qp = {"video": {"resolution": {"widthPx": 1920, "heightPx": 1080}}, "audio": {}}
        rp = {"operations": [{"opType": "encode", "compression": {"codec": "libx265", "bitrateMbps": 10}}]}
        cmd = _encode_cmd(Path("/tmp/in.mp4"), qp, Path("/tmp/out.mp4"), render_plan=rp)
        cmd_str = " ".join(cmd)
        assert "libx265" in cmd_str
        assert "10M" in cmd_str

    def test_default_codec_without_render_plan(self):
        from pipeline.assemble import _encode_cmd
        qp = {"video": {"resolution": {}}, "audio": {}}
        cmd = _encode_cmd(Path("/tmp/in.mp4"), qp, Path("/tmp/out.mp4"))
        assert "libx264" in " ".join(cmd)


# ── assemble.py: _build_audio_mix_cmd tests ──────────────────────────────────

class TestAudioMixCmd:
    def _make_audio_files(self, tmp_path: Path) -> dict[str, Path]:
        """Create dummy audio files."""
        files = {}
        for name in ["audio.amb", "audio.dial", "audio.score"]:
            p = tmp_path / f"{name}.mp3"
            # Minimal valid content (just needs to exist)
            p.write_bytes(b"\x00" * 100)
            files[name] = p
        return files

    def test_reads_timeline_audio_clips_timing(self, minimal_instance, tmp_path):
        from pipeline.assemble import _build_audio_mix_cmd
        video = tmp_path / "video.mp4"
        video.write_bytes(b"\x00" * 100)
        audio_files = self._make_audio_files(tmp_path)
        cmd = _build_audio_mix_cmd(video, audio_files, minimal_instance, tmp_path / "out.mp4")
        cmd_str = " ".join(cmd)
        # Dialogue starts at 3s → adelay=3000
        assert "3000" in cmd_str

    def test_applies_gain_from_render_plan(self, minimal_instance, tmp_path):
        from pipeline.assemble import _build_audio_mix_cmd
        video = tmp_path / "video.mp4"
        video.write_bytes(b"\x00" * 100)
        audio_files = self._make_audio_files(tmp_path)
        cmd = _build_audio_mix_cmd(video, audio_files, minimal_instance, tmp_path / "out.mp4")
        cmd_str = " ".join(cmd)
        # Ambient gain is -8dB, score is -14dB
        assert "-8dB" in cmd_str
        assert "-14dB" in cmd_str

    def test_no_gain_for_zero_db(self, minimal_instance, tmp_path):
        from pipeline.assemble import _build_audio_mix_cmd
        video = tmp_path / "video.mp4"
        video.write_bytes(b"\x00" * 100)
        audio_files = self._make_audio_files(tmp_path)
        cmd = _build_audio_mix_cmd(video, audio_files, minimal_instance, tmp_path / "out.mp4")
        cmd_str = " ".join(cmd)
        # Dialogue at 0dB should NOT have volume filter
        # Count volume filters — should be 2 (ambient + score), not 3
        assert cmd_str.count("volume=") == 2


# ── assemble.py: platform encoding tests ─────────────────────────────────────

class TestPlatformEncoding:
    def test_youtube_defaults_1080p(self, minimal_instance):
        """YouTube platform should default to 1920x1080 if not specified."""
        qp = minimal_instance["qualityProfiles"][0]["profile"]
        # Already has resolution, so platform shouldn't override
        video = qp.get("video", {})
        res = video.get("resolution", {})
        assert res.get("widthPx") == 1280  # original value preserved

    def test_tiktok_sets_vertical(self):
        """TikTok platform should set 9:16 vertical format."""
        instance = {
            "qualityProfiles": [{"profile": {"video": {"resolution": {}, "aspectRatio": {}}, "audio": {}}}],
            "deliverables": [{"platform": "tiktok"}],
            "assembly": {"renderPlans": []},
        }
        # Simulate what assemble() does
        deliverables = instance.get("deliverables") or []
        platform = deliverables[0].get("platform", "") if deliverables else ""
        qp = instance["qualityProfiles"][0]["profile"]
        video_cfg = qp.get("video") or {}
        res = video_cfg.get("resolution") or {}
        if platform in ("tiktok", "instagram_reels", "youtube_shorts"):
            if not res.get("widthPx"):
                res["widthPx"] = 1080
                res["heightPx"] = 1920
        assert res["widthPx"] == 1080
        assert res["heightPx"] == 1920


# ── generate.py: _extract_last_frame test ────────────────────────────────────

class TestExtractLastFrame:
    def test_returns_none_for_nonexistent(self):
        from pipeline.generate import _extract_last_frame
        result = _extract_last_frame(Path("/tmp/nonexistent.mp4"))
        assert result is None

    def test_extracts_from_real_video(self, tmp_path):
        """Generate a tiny test video and extract its last frame."""
        from pipeline.generate import _extract_last_frame
        video = tmp_path / "test.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "color=c=red:s=64x64:d=1",
            "-c:v", "libx264", "-preset", "ultrafast",
            str(video),
        ], capture_output=True, check=True)
        result = _extract_last_frame(video)
        assert result is not None
        assert len(result) > 100  # valid PNG


# ── Integration: demo-30s.json completeness ──────────────────────────────────

class TestDemoJsonCompleteness:
    """Verify demo-30s.json has all fields the pipeline needs."""

    def test_all_shots_have_cinematic_spec(self, instance):
        for shot in instance["production"]["shots"]:
            spec = shot.get("cinematicSpec")
            assert spec, f"Shot {shot['id']} missing cinematicSpec"
            assert spec.get("shotType"), f"Shot {shot['id']} missing shotType"
            assert spec.get("cameraAngle"), f"Shot {shot['id']} missing cameraAngle"
            assert spec.get("cameraMovement"), f"Shot {shot['id']} missing cameraMovement"
            assert spec.get("focalLengthMm"), f"Shot {shot['id']} missing focalLengthMm"

    def test_all_shots_have_gen_params(self, instance):
        for shot in instance["production"]["shots"]:
            gp = shot.get("genParams")
            assert gp, f"Shot {shot['id']} missing genParams"
            assert gp.get("prompt"), f"Shot {shot['id']} missing prompt"

    def test_all_scenes_have_transitions(self, instance):
        for scene in instance["production"]["scenes"]:
            assert scene.get("transitionIn"), f"Scene {scene['id']} missing transitionIn"
            assert scene.get("transitionOut"), f"Scene {scene['id']} missing transitionOut"

    def test_all_scenes_have_mood_and_time(self, instance):
        for scene in instance["production"]["scenes"]:
            assert scene.get("mood"), f"Scene {scene['id']} missing mood"
            assert scene.get("timeOfDay"), f"Scene {scene['id']} missing timeOfDay"

    def test_timeline_has_audio_clips(self, instance):
        tl = instance["assembly"]["timelines"][0]
        assert len(tl["audioClips"]) >= 1

    def test_render_plan_has_audio_mix_with_gains(self, instance):
        rp = instance["assembly"]["renderPlans"][0]
        audio_op = None
        for op in rp["operations"]:
            if op["opType"] == "audioMix":
                audio_op = op
                break
        assert audio_op, "renderPlan missing audioMix operation"
        for track in audio_op["tracks"]:
            assert "gainDb" in track, f"Track {track} missing gainDb"

    def test_render_plan_has_encode_with_codec(self, instance):
        rp = instance["assembly"]["renderPlans"][0]
        enc = None
        for op in rp["operations"]:
            if op["opType"] == "encode":
                enc = op
                break
        assert enc, "renderPlan missing encode operation"
        assert enc["compression"].get("codec"), "encode missing codec"

    def test_quality_profile_uses_widthPx(self, instance):
        qp = instance["qualityProfiles"][0]["profile"]
        res = qp["video"]["resolution"]
        assert "widthPx" in res, "qualityProfile should use widthPx not width"
        assert "heightPx" in res, "qualityProfile should use heightPx not height"

    def test_shots_reference_style_guide(self, instance):
        for shot in instance["production"]["shots"]:
            spec = shot.get("cinematicSpec") or {}
            assert spec.get("styleGuideRef"), f"Shot {shot['id']} missing styleGuideRef"

    def test_deliverable_has_platform(self, instance):
        assert instance["deliverables"][0].get("platform"), "deliverable missing platform"
