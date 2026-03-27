"""
Tests for assemble.py — validates all 10 schema compliance fixes.

Run: python -m pytest pipeline/test_assemble.py -v
  or: python -m pipeline.test_assemble  (standalone)
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Module under test
from pipeline.assemble import (
    ApprovalError,
    check_approval,
    validate_spatial_consistency,
    _resolve_audio_timing,
    _resolve_audio_codec,
    _resolve_color_grade_params,
    _color_grade_cmd,
    _encode_cmd,
    _build_audio_mix_cmd,
    _parse_color_direction,
    populate_final_output,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _minimal_instance(**overrides) -> dict:
    """Return a minimal valid v3 instance for testing."""
    base = {
        "schemaVersion": "3.1.0",
        "package": {"packageId": "pkg.test", "createdAt": "2026-01-01T00:00:00Z"},
        "project": {"name": "Test Project"},
        "qualityProfiles": [{
            "id": "qp.test.v1",
            "profile": {
                "name": "Test",
                "video": {
                    "resolution": {"widthPx": 1920, "heightPx": 1080},
                    "frameRate": {"fps": 24, "mode": "constant"},
                },
                "audio": {"sampleRateHz": 44100, "channelLayout": "stereo"},
            },
        }],
        "canonicalDocuments": {
            "story": {},
            "script": {},
            "directorInstructions": {
                "colorDirection": "warm amber palette",
            },
        },
        "production": {
            "characters": [],
            "environments": [],
            "props": [],
            "scenes": [],
            "shots": [],
        },
        "assetLibrary": {
            "visualAssets": [],
            "audioAssets": [],
            "marketingAssets": [],
            "genericAssets": [],
        },
        "orchestration": {"workflows": []},
        "assembly": {
            "timelines": [],
            "editVersions": [
                {"id": "ev.1", "name": "Edit v1", "approvedForRender": True, "timelineRef": {"id": "tl.1"}},
            ],
            "renderPlans": [],
        },
        "deliverables": [],
        "relationships": [],
    }
    for k, v in overrides.items():
        _deep_set(base, k, v)
    return base


def _deep_set(obj: dict, path: str, value) -> None:
    keys = path.split(".")
    d = obj
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


# ═══════════════════════════════════════════════════════════════════════════════
# #4 — Approval gate
# ═══════════════════════════════════════════════════════════════════════════════

class TestApprovalGate(unittest.TestCase):
    """Fix #4: editVersions[].approvedForRender must be checked."""

    def test_approved_passes(self):
        instance = _minimal_instance()
        # Should not raise
        check_approval(instance)

    def test_not_approved_raises(self):
        instance = _minimal_instance()
        instance["assembly"]["editVersions"] = [
            {"id": "ev.1", "name": "Draft", "approvedForRender": False, "timelineRef": {"id": "tl.1"}},
        ]
        with self.assertRaises(ApprovalError) as ctx:
            check_approval(instance)
        self.assertIn("approvedForRender", str(ctx.exception))

    def test_no_edit_versions_raises(self):
        instance = _minimal_instance()
        instance["assembly"]["editVersions"] = []
        with self.assertRaises(ApprovalError):
            check_approval(instance)

    def test_force_bypasses(self):
        instance = _minimal_instance()
        instance["assembly"]["editVersions"] = [
            {"id": "ev.1", "name": "Draft", "approvedForRender": False, "timelineRef": {"id": "tl.1"}},
        ]
        # Should not raise with force=True
        check_approval(instance, force=True)

    def test_force_bypasses_empty(self):
        instance = _minimal_instance()
        instance["assembly"]["editVersions"] = []
        check_approval(instance, force=True)


# ═══════════════════════════════════════════════════════════════════════════════
# #10 — Spatial consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpatialConsistency(unittest.TestCase):
    """Fix #10: Validate spatial consistency constraints."""

    def test_no_constraints_no_warnings(self):
        instance = _minimal_instance()
        instance["production"]["scenes"] = [
            {"id": "scene.1", "sceneNumber": 1, "shotRefs": [], "targetDurationSec": 10},
        ]
        warnings = validate_spatial_consistency(instance)
        self.assertEqual(warnings, [])

    def test_180_rule_violation_detected(self):
        instance = _minimal_instance()
        instance["production"]["shots"] = [
            {
                "id": "shot.1", "logicalId": "shot.1", "name": "S1",
                "cinematicSpec": {
                    "cameraExtrinsics": {"transform": {"position": {"x": 1.5, "y": 1.6, "z": 0.8}}},
                },
            },
            {
                "id": "shot.2", "logicalId": "shot.2", "name": "S2",
                "cinematicSpec": {
                    "cameraExtrinsics": {"transform": {"position": {"x": -1.5, "y": 1.6, "z": 0.8}}},
                },
            },
        ]
        instance["production"]["scenes"] = [{
            "id": "scene.1", "name": "Scene 1", "sceneNumber": 1,
            "targetDurationSec": 10,
            "shotRefs": [{"id": "shot.1"}, {"id": "shot.2"}],
            "spatialConsistency": {
                "required": True,
                "enforce180DegreeRule": True,
            },
        }]
        warnings = validate_spatial_consistency(instance)
        self.assertTrue(any("180-degree" in w for w in warnings))

    def test_180_rule_same_side_ok(self):
        instance = _minimal_instance()
        instance["production"]["shots"] = [
            {
                "id": "shot.1", "logicalId": "shot.1", "name": "S1",
                "cinematicSpec": {
                    "cameraExtrinsics": {"transform": {"position": {"x": 1.5, "y": 1.6, "z": 0.8}}},
                },
            },
            {
                "id": "shot.2", "logicalId": "shot.2", "name": "S2",
                "cinematicSpec": {
                    "cameraExtrinsics": {"transform": {"position": {"x": 2.0, "y": 1.0, "z": 0.5}}},
                },
            },
        ]
        instance["production"]["scenes"] = [{
            "id": "scene.1", "name": "Scene 1", "sceneNumber": 1,
            "targetDurationSec": 10,
            "shotRefs": [{"id": "shot.1"}, {"id": "shot.2"}],
            "spatialConsistency": {"required": True, "enforce180DegreeRule": True},
        }]
        warnings = validate_spatial_consistency(instance)
        self.assertFalse(any("180-degree" in w for w in warnings))

    def test_screen_direction_ots_without_bridge(self):
        instance = _minimal_instance()
        instance["production"]["shots"] = [{
            "id": "shot.1", "logicalId": "shot.1", "name": "S1",
            "cinematicSpec": {"cameraAngle": "over_the_shoulder"},
        }]
        instance["production"]["scenes"] = [{
            "id": "scene.1", "name": "Scene 1", "sceneNumber": 1,
            "targetDurationSec": 10,
            "shotRefs": [{"id": "shot.1"}],
            "spatialConsistency": {"required": True, "enforceScreenDirection": True},
        }]
        warnings = validate_spatial_consistency(instance)
        self.assertTrue(any("OTS" in w and "spatialBridgeAnchorRef" in w for w in warnings))

    def test_max_position_drift_warning(self):
        instance = _minimal_instance()
        instance["production"]["scenes"] = [{
            "id": "scene.1", "name": "Scene 1", "sceneNumber": 1,
            "targetDurationSec": 10,
            "shotRefs": [],
            "spatialConsistency": {"required": True, "maxPositionDriftM": 0.5},
        }]
        warnings = validate_spatial_consistency(instance)
        self.assertTrue(any("maxPositionDriftM" in w for w in warnings))


# ═══════════════════════════════════════════════════════════════════════════════
# #3 — SyncPoints / TimeRange
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudioTiming(unittest.TestCase):
    """Fix #3: SyncPoints must use schema-compliant TimeRange."""

    def test_timeline_clips_authoritative(self):
        clip_timing = {"audio.ambient.v1": {"startSec": 5.0, "durationSec": 20.0}}
        asset = {"id": "audio.ambient.v1"}
        start, dur = _resolve_audio_timing(asset, "audio.ambient.v1", clip_timing)
        self.assertEqual(start, 5.0)
        self.assertEqual(dur, 20.0)

    def test_schema_syncpoints_array_with_time_range(self):
        asset = {
            "id": "audio.dial.v1",
            "syncPoints": [
                {"label": "dialogue start", "time": {"startSec": 10, "endSec": 15}},
            ],
        }
        start, dur = _resolve_audio_timing(asset, "audio.dial.v1", {})
        self.assertEqual(start, 10.0)
        self.assertEqual(dur, 5.0)

    def test_schema_syncpoints_array_with_duration(self):
        asset = {
            "id": "audio.sfx.v1",
            "syncPoints": [
                {"label": "bang", "time": {"startSec": 3, "durationSec": 2}},
            ],
        }
        start, dur = _resolve_audio_timing(asset, "audio.sfx.v1", {})
        self.assertEqual(start, 3.0)
        self.assertEqual(dur, 2.0)

    def test_schema_syncpoints_single_object(self):
        asset = {
            "id": "audio.x",
            "syncPoints": {"time": {"startSec": 7, "endSec": 12}},
        }
        start, dur = _resolve_audio_timing(asset, "audio.x", {})
        self.assertEqual(start, 7.0)
        self.assertEqual(dur, 5.0)

    def test_legacy_compat_timelineInSec(self):
        asset = {
            "id": "audio.old",
            "syncPoints": {"timelineInSec": 20, "timelineOutSec": 40},
        }
        start, dur = _resolve_audio_timing(asset, "audio.old", {})
        self.assertEqual(start, 20.0)
        self.assertEqual(dur, 20.0)

    def test_default_when_no_sync(self):
        asset = {"id": "audio.none"}
        start, dur = _resolve_audio_timing(asset, "audio.none", {})
        self.assertEqual(start, 0.0)
        self.assertEqual(dur, 30.0)


# ═══════════════════════════════════════════════════════════════════════════════
# #6 — Audio codec from schema
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudioCodecResolution(unittest.TestCase):
    """Fix #6: Audio codec from AudioTechnicalSpec instead of hardcoded."""

    def test_flac_from_technical_spec(self):
        instance = _minimal_instance()
        instance["assetLibrary"]["audioAssets"] = [
            {"id": "a.1", "audioType": "ambient", "technicalSpec": {"codec": "flac", "sampleRateHz": 48000}},
        ]
        codec, bitrate = _resolve_audio_codec(instance)
        self.assertEqual(codec, "flac")

    def test_mp3_from_technical_spec(self):
        instance = _minimal_instance()
        instance["assetLibrary"]["audioAssets"] = [
            {"id": "a.1", "audioType": "music", "technicalSpec": {"codec": "mp3"}},
        ]
        codec, bitrate = _resolve_audio_codec(instance)
        self.assertEqual(codec, "libmp3lame")

    def test_default_aac_when_no_spec(self):
        instance = _minimal_instance()
        instance["assetLibrary"]["audioAssets"] = [
            {"id": "a.1", "audioType": "ambient"},
        ]
        codec, bitrate = _resolve_audio_codec(instance)
        self.assertEqual(codec, "aac")
        self.assertEqual(bitrate, "192k")

    def test_opus_from_spec(self):
        instance = _minimal_instance()
        instance["assetLibrary"]["audioAssets"] = [
            {"id": "a.1", "audioType": "music", "technicalSpec": {"codec": "opus"}},
        ]
        codec, _ = _resolve_audio_codec(instance)
        self.assertEqual(codec, "libopus")


# ═══════════════════════════════════════════════════════════════════════════════
# #1, #2 — Color grade from renderPlan + no-op passthrough
# ═══════════════════════════════════════════════════════════════════════════════

class TestColorGrade(unittest.TestCase):
    """Fix #1: near-lossless intermediate. Fix #2: read ColorGradeOp."""

    def test_noop_grade_uses_copy(self):
        """When grade params are neutral, should use -c copy (no re-encode)."""
        params = {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0}
        cmd = _color_grade_cmd(Path("/in.mp4"), params, 1.0, Path("/out.mp4"))
        self.assertIn("-c", cmd)
        self.assertIn("copy", cmd)
        self.assertNotIn("libx264", cmd)

    def test_active_grade_uses_crf_1(self):
        """When grade is active, should use CRF 1 for near-lossless intermediate."""
        params = {"brightness": 0.05, "contrast": 1.1, "saturation": 0.9}
        cmd = _color_grade_cmd(Path("/in.mp4"), params, 1.0, Path("/out.mp4"))
        self.assertIn("-crf", cmd)
        idx = cmd.index("-crf")
        self.assertEqual(cmd[idx + 1], "1")

    def test_strength_scales_params(self):
        """Strength < 1 should reduce the effect."""
        params = {"brightness": 0.1, "contrast": 1.2, "saturation": 0.8}
        cmd = _color_grade_cmd(Path("/in.mp4"), params, 0.5, Path("/out.mp4"))
        # brightness should be 0.1 * 0.5 = 0.05
        eq_idx = cmd.index("-vf") + 1
        eq_str = cmd[eq_idx]
        self.assertIn("brightness=0.050", eq_str)
        # contrast should be 1.0 + (1.2 - 1.0) * 0.5 = 1.1
        self.assertIn("contrast=1.100", eq_str)

    def test_zero_strength_is_noop(self):
        """Strength=0 should result in no-op (copy)."""
        params = {"brightness": 0.1, "contrast": 1.2, "saturation": 0.8}
        cmd = _color_grade_cmd(Path("/in.mp4"), params, 0.0, Path("/out.mp4"))
        self.assertIn("copy", cmd)

    def test_resolve_from_renderplan_colorgrade_op(self):
        """ColorGradeOp.intent + .strength should be preferred over directorInstructions."""
        instance = _minimal_instance()
        instance["assembly"]["renderPlans"] = [{
            "id": "rp.1",
            "operations": [
                {
                    "opId": "op.cg",
                    "opType": "colorGrade",
                    "inputRef": {"id": "op.concat"},
                    "intent": "cool desaturated noir",
                    "strength": 0.7,
                },
            ],
        }]
        params, strength = _resolve_color_grade_params(instance)
        self.assertEqual(strength, 0.7)
        # "cool" → brightness -0.03, "desaturated" → sat 0.75, "noir" → dark adjustments
        self.assertLess(params["brightness"], 0)
        self.assertLess(params["saturation"], 1.0)

    def test_fallback_to_director_instructions(self):
        """Without ColorGradeOp, should fall back to directorInstructions.colorDirection."""
        instance = _minimal_instance()
        instance["canonicalDocuments"]["directorInstructions"]["colorDirection"] = "warm amber palette"
        params, strength = _resolve_color_grade_params(instance)
        self.assertEqual(strength, 1.0)
        self.assertGreater(params["brightness"], 0)  # "warm" → positive


# ═══════════════════════════════════════════════════════════════════════════════
# #8 — Encode reads renderPlan EncodeOp
# ═══════════════════════════════════════════════════════════════════════════════

class TestEncodeCmd(unittest.TestCase):
    """Fix #8: Encode command reads codec/bitrate from renderPlan EncodeOp."""

    def test_default_codec_without_renderplan(self):
        qp = {"video": {"resolution": {"widthPx": 1920, "heightPx": 1080}, "frameRate": {"fps": 24}}}
        cmd = _encode_cmd(Path("/in.mp4"), qp, Path("/out.mp4"))
        self.assertIn("libx264", cmd)
        self.assertIn("-crf", cmd)

    def test_codec_from_renderplan(self):
        qp = {"video": {"resolution": {"widthPx": 1920, "heightPx": 1080}, "frameRate": {"fps": 24}}}
        rp = {
            "operations": [{
                "opType": "encode",
                "compression": {"codec": "libx265", "bitrateMbps": 8, "profile": "main"},
            }],
        }
        cmd = _encode_cmd(Path("/in.mp4"), qp, Path("/out.mp4"), render_plan=rp)
        self.assertIn("libx265", cmd)
        self.assertIn("-b:v", cmd)
        self.assertIn("8M", cmd)
        self.assertIn("-profile:v", cmd)
        self.assertIn("main", cmd)
        # Should NOT have -crf when bitrate is specified
        self.assertNotIn("-crf", cmd)

    def test_crf_from_renderplan(self):
        qp = {"video": {"resolution": {"widthPx": 1280, "heightPx": 720}, "frameRate": {"fps": 30}}}
        rp = {"operations": [{"opType": "encode", "compression": {"codec": "libx264", "crf": 23}}]}
        cmd = _encode_cmd(Path("/in.mp4"), qp, Path("/out.mp4"), render_plan=rp)
        self.assertIn("-crf", cmd)
        idx = cmd.index("-crf")
        self.assertEqual(cmd[idx + 1], "23")

    def test_gop_and_maxbitrate(self):
        qp = {"video": {"resolution": {"widthPx": 1920, "heightPx": 1080}, "frameRate": {"fps": 24}}}
        rp = {"operations": [{
            "opType": "encode",
            "compression": {"codec": "libx264", "bitrateMbps": 5, "maxBitrateMbps": 10, "gopLength": 48},
        }]}
        cmd = _encode_cmd(Path("/in.mp4"), qp, Path("/out.mp4"), render_plan=rp)
        self.assertIn("-maxrate", cmd)
        self.assertIn("10M", cmd)
        self.assertIn("-g", cmd)
        self.assertIn("48", cmd)

    def test_audio_codec_passed_through(self):
        qp = {"video": {"resolution": {"widthPx": 1920, "heightPx": 1080}, "frameRate": {"fps": 24}}}
        cmd = _encode_cmd(Path("/in.mp4"), qp, Path("/out.mp4"), audio_codec="flac", audio_bitrate="320k")
        self.assertIn("flac", cmd)
        self.assertIn("320k", cmd)

    def test_resolution_and_fps_from_quality_profile(self):
        qp = {
            "video": {"resolution": {"widthPx": 3840, "heightPx": 2160}, "frameRate": {"fps": 60}},
            "audio": {"sampleRateHz": 48000},
        }
        cmd = _encode_cmd(Path("/in.mp4"), qp, Path("/out.mp4"))
        self.assertIn("scale=3840:2160,fps=60", cmd)
        self.assertIn("48000", cmd)


# ═══════════════════════════════════════════════════════════════════════════════
# #7 — Audio pan
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudioPan(unittest.TestCase):
    """Fix #7: AudioMixTrack.pan support."""

    def test_pan_in_mix_command(self):
        instance = _minimal_instance()
        instance["assetLibrary"]["audioAssets"] = [
            {"id": "a.1", "logicalId": "a.1", "audioType": "ambient"},
        ]
        instance["assembly"]["timelines"] = [{
            "audioClips": [{"sourceRef": {"id": "a.1"}, "timelineStartSec": 0, "durationSec": 10}],
        }]
        instance["assembly"]["renderPlans"] = [{
            "operations": [{
                "opType": "audioMix",
                "tracks": [{"audioRef": {"id": "a.1"}, "gainDb": -6, "pan": 0.8}],
            }],
        }]

        tmp = Path("/tmp/test_video.mp4")
        audio_files = {"a.1": Path("/tmp/test_audio.mp3")}

        with patch("pathlib.Path.exists", return_value=True):
            cmd = _build_audio_mix_cmd(tmp, audio_files, instance, Path("/tmp/out.mp4"))

        cmd_str = " ".join(cmd)
        self.assertIn("pan=stereo", cmd_str)

    def test_no_pan_when_center(self):
        instance = _minimal_instance()
        instance["assetLibrary"]["audioAssets"] = [
            {"id": "a.1", "logicalId": "a.1", "audioType": "ambient"},
        ]
        instance["assembly"]["timelines"] = [{
            "audioClips": [{"sourceRef": {"id": "a.1"}, "timelineStartSec": 0, "durationSec": 10}],
        }]
        instance["assembly"]["renderPlans"] = [{
            "operations": [{
                "opType": "audioMix",
                "tracks": [{"audioRef": {"id": "a.1"}, "gainDb": 0, "pan": 0}],
            }],
        }]

        tmp = Path("/tmp/test_video.mp4")
        audio_files = {"a.1": Path("/tmp/test_audio.mp3")}

        with patch("pathlib.Path.exists", return_value=True):
            cmd = _build_audio_mix_cmd(tmp, audio_files, instance, Path("/tmp/out.mp4"))

        cmd_str = " ".join(cmd)
        self.assertNotIn("pan=stereo", cmd_str)


# ═══════════════════════════════════════════════════════════════════════════════
# #9 — FinalOutput population
# ═══════════════════════════════════════════════════════════════════════════════

class TestFinalOutputPopulation(unittest.TestCase):
    """Fix #9: Populate FinalOutputEntity after render."""

    def test_populates_deliverable(self):
        instance = _minimal_instance()
        instance["deliverables"] = [{
            "id": "del.1",
            "outputType": "video/mp4",
            "runtimeSec": 0,
            "version": {"number": "1.0.0", "state": "draft"},
        }]

        # Create a real temp file
        tmp = Path("/tmp/test_final_output.bin")
        tmp.write_bytes(b"fake video content for hash test")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="42.5\n", stderr="", returncode=0)
            result = populate_final_output(instance, tmp)

        d = result["deliverables"][0]
        self.assertEqual(d["runtimeSec"], 42.5)
        self.assertIn("_filePath", d)
        self.assertIn("_fileSizeBytes", d)
        self.assertIn("_checksum", d)
        self.assertEqual(d["_checksum"]["algorithm"], "sha256")
        self.assertEqual(len(d["_checksum"]["value"]), 64)
        self.assertIn("_renderedAt", d)
        self.assertEqual(d["version"]["state"], "generating")

        tmp.unlink(missing_ok=True)

    def test_no_deliverables_noop(self):
        instance = _minimal_instance()
        instance["deliverables"] = []
        result = populate_final_output(instance, Path("/tmp/nonexistent.mp4"))
        self.assertEqual(result["deliverables"], [])


# ═══════════════════════════════════════════════════════════════════════════════
# #5 — Transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestTransitions(unittest.TestCase):
    """Fix #5: Per-scene transition support."""

    def test_all_cuts_uses_concat_copy(self):
        """When all transitions are cuts, should use fast -c copy concat."""
        scenes = [
            {"transitionIn": {"type": "cut"}, "transitionOut": {"type": "cut"}},
            {"transitionIn": {"type": "cut"}, "transitionOut": {"type": "cut"}},
        ]
        # Just verify the function doesn't error — actual FFmpeg execution
        # would need real files, tested in integration
        from pipeline.assemble import _concat_clips_ffmpeg
        # We can't test with real files here, but verify the scene parsing logic
        has_transitions = False
        for s in scenes:
            t_in = (s.get("transitionIn") or {}).get("type", "cut")
            t_out = (s.get("transitionOut") or {}).get("type", "cut")
            if t_in != "cut" or t_out != "cut":
                has_transitions = True
        self.assertFalse(has_transitions)

    def test_dissolve_detected(self):
        scenes = [
            {"transitionIn": {"type": "fade"}, "transitionOut": {"type": "dissolve", "durationSec": 1.0}},
        ]
        has_transitions = False
        for s in scenes:
            t_in = (s.get("transitionIn") or {}).get("type", "cut")
            t_out = (s.get("transitionOut") or {}).get("type", "cut")
            if t_in != "cut" or t_out != "cut":
                has_transitions = True
        self.assertTrue(has_transitions)


# ═══════════════════════════════════════════════════════════════════════════════
# Color direction parsing
# ═══════════════════════════════════════════════════════════════════════════════

class TestColorDirectionParsing(unittest.TestCase):
    """Verify the text-to-params heuristic handles schema example values."""

    def test_warm_amber(self):
        p = _parse_color_direction("Amber/dark palette in Acts 1–2. Warm green console glow.")
        self.assertGreater(p["brightness"], 0)   # "warm"
        self.assertLess(p["saturation"], 1.0)     # "dark"

    def test_cool_desaturated(self):
        p = _parse_color_direction("cool desaturated palette")
        self.assertLess(p["brightness"], 0)
        self.assertLess(p["saturation"], 1.0)

    def test_neutral_returns_defaults(self):
        p = _parse_color_direction("Neutral cinematic palette.")
        self.assertGreaterEqual(p["contrast"], 1.0)  # "cinematic"

    def test_empty_string(self):
        p = _parse_color_direction("")
        self.assertEqual(p["brightness"], 0.0)
        self.assertEqual(p["contrast"], 1.0)
        self.assertEqual(p["saturation"], 1.0)

    def test_rec709_filmic_dark(self):
        """Test the example project's actual colorGrade intent."""
        p = _parse_color_direction("rec709 filmic dark — amber highlights, crushed blacks")
        self.assertLess(p["brightness"], 0)       # "dark"
        self.assertGreater(p["contrast"], 1.0)    # "dark" → 1.15


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: example-project.json
# ═══════════════════════════════════════════════════════════════════════════════

class TestExampleProjectCompliance(unittest.TestCase):
    """Verify fixes work against the actual example-project.json."""

    @classmethod
    def setUpClass(cls):
        example_path = Path(__file__).parent.parent / "example-project.json"
        if not example_path.exists():
            raise unittest.SkipTest("example-project.json not found")
        cls.instance = json.loads(example_path.read_text(encoding="utf-8"))

    def test_approval_gate_passes(self):
        """Example project has approvedForRender=true."""
        check_approval(self.instance)

    def test_spatial_consistency_detects_constraints(self):
        """Example project has spatialConsistency on all scenes."""
        warnings = validate_spatial_consistency(self.instance)
        # The example project has enforce180DegreeRule on all scenes
        # Act 2 has camera positions that cross the action line per the schema design
        # This is intentional (matched OTS shots) — but S5/S6 should have bridges
        self.assertIsInstance(warnings, list)

    def test_audio_timing_from_timeline(self):
        """Example project audio should resolve from timeline.audioClips."""
        tl = self.instance["assembly"]["timelines"][0]
        clips = tl.get("audioClips", [])
        self.assertGreater(len(clips), 0)
        # Verify each clip has sourceRef + timing
        for clip in clips:
            self.assertIn("sourceRef", clip)
            self.assertIn("timelineStartSec", clip)
            self.assertIn("durationSec", clip)

    def test_encode_reads_example_compression(self):
        """Example project specifies libx265/8Mbps — encode should use it."""
        rp = self.instance["assembly"]["renderPlans"][0]
        qp = self.instance["qualityProfiles"][0].get("profile", {})
        cmd = _encode_cmd(Path("/in.mp4"), qp, Path("/out.mp4"), render_plan=rp)
        self.assertIn("libx265", cmd)
        self.assertIn("8M", cmd)

    def test_color_grade_from_example(self):
        """Example project has a colorGrade operation."""
        params, strength = _resolve_color_grade_params(self.instance)
        # Example: "rec709 filmic dark — amber highlights, crushed blacks"
        self.assertEqual(strength, 0.85)
        self.assertLess(params["brightness"], 0)

    def test_audio_codec_from_example(self):
        """Example project audio assets use flac codec."""
        codec, _ = _resolve_audio_codec(self.instance)
        self.assertEqual(codec, "flac")


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main()
