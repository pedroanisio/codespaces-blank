"""
Regression tests for pipeline fixes applied during the Spark GVPP build sessions.

Covers:
  1. syncPoints v3 array format in _stub_audio (generate.py)
  2. Video provider constraint-based routing (generate.py)
  3. Reference image chaining — BytesIO .name for MIME type (providers.py)
  4. Codec name mapping H.265→libx265 (assemble.py)
  5. Profile normalization "Main 10"→"main10" (assemble.py)
  6. Build ID UUID and log file naming (run.py)
  7. Enriched prompt passthrough to Runway (generate.py)

Run: python -m pytest pipeline/test_regressions.py -v
  or: python -m pipeline.test_regressions
"""

from __future__ import annotations

import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _minimal_instance(**overrides) -> dict:
    """Minimal valid v3 instance for testing."""
    base = {
        "schemaVersion": "3.0.0",
        "package": {
            "packageId": "pkg-test",
            "createdAt": "2026-01-01T00:00:00Z",
            "versioningPolicy": {"immutablePublishedVersions": True, "defaultReferenceMode": "exact"},
        },
        "project": {
            "id": "prj-test", "logicalId": "prj-test", "entityType": "project",
            "name": "Test", "version": {"number": "1.0.0", "state": "draft"},
            "targetRuntimeSec": 10,
            "defaultQualityProfileRef": {"id": "qp-1"},
        },
        "qualityProfiles": [{
            "id": "qp-1", "logicalId": "qp-1", "entityType": "qualityProfile",
            "name": "Test QP", "version": {"number": "1.0.0", "state": "draft"},
            "profile": {"name": "test"},
        }],
        "canonicalDocuments": {
            "story": {
                "id": "s-1", "logicalId": "s-1", "entityType": "story",
                "name": "Story", "version": {"number": "1.0.0", "state": "draft"},
                "logline": "test", "beats": [],
            },
            "script": {
                "id": "sc-1", "logicalId": "sc-1", "entityType": "script",
                "name": "Script", "version": {"number": "1.0.0", "state": "draft"},
                "segments": [],
            },
            "directorInstructions": {
                "id": "di-1", "logicalId": "di-1", "entityType": "directorInstructions",
                "name": "DI", "version": {"number": "1.0.0", "state": "draft"},
                "visionStatement": "test",
            },
        },
        "production": {
            "characters": [], "environments": [], "props": [],
            "scenes": [], "shots": [],
        },
        "assetLibrary": {
            "visualAssets": [], "audioAssets": [],
            "marketingAssets": [], "genericAssets": [],
        },
        "orchestration": {"workflows": []},
        "assembly": {
            "timelines": [], "editVersions": [], "renderPlans": [],
        },
        "deliverables": [],
        "relationships": [],
    }
    for k, v in overrides.items():
        keys = k.split(".")
        target = base
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = v
    return base


# ═════════════════════════════════════════════════════════════════════════════
# §1  syncPoints v3 array format (_stub_audio)
# ═════════════════════════════════════════════════════════════════════════════

class TestSyncPointsV3Format(unittest.TestCase):
    """Regression: _stub_audio must handle v3 syncPoints (array of SyncPoint)
    without crashing on 'list' object has no attribute 'get'."""

    def test_v3_array_syncpoints(self):
        """v3 format: array of {time: {startSec, endSec}} objects."""
        from pipeline.generate import _stub_audio

        asset = {
            "audioType": "sfx",
            "syncPoints": [
                {"label": "start", "time": {"startSec": 1.0, "endSec": 3.0}},
                {"label": "end", "time": {"startSec": 10.0, "endSec": 14.5}},
            ],
        }
        out = Path("/tmp/test_sync_v3.mp3")
        try:
            _stub_audio(asset, out)
            self.assertTrue(out.exists())
            # Duration should span from first startSec to last endSec: 14.5 - 1.0 = 13.5
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
                capture_output=True, text=True,
            )
            dur = float(result.stdout.strip())
            self.assertAlmostEqual(dur, 13.5, delta=0.5)
        finally:
            out.unlink(missing_ok=True)

    def test_v2_dict_syncpoints(self):
        """v2 compat: single dict with timelineInSec/timelineOutSec."""
        from pipeline.generate import _stub_audio

        asset = {
            "audioType": "ambient",
            "syncPoints": {"timelineInSec": 2.0, "timelineOutSec": 7.0},
        }
        out = Path("/tmp/test_sync_v2.mp3")
        try:
            _stub_audio(asset, out)
            self.assertTrue(out.exists())
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
                capture_output=True, text=True,
            )
            dur = float(result.stdout.strip())
            self.assertAlmostEqual(dur, 5.0, delta=0.5)
        finally:
            out.unlink(missing_ok=True)

    def test_no_syncpoints(self):
        """No syncPoints → default 5s duration."""
        from pipeline.generate import _stub_audio

        asset = {"audioType": "foley"}
        out = Path("/tmp/test_sync_none.mp3")
        try:
            _stub_audio(asset, out)
            self.assertTrue(out.exists())
        finally:
            out.unlink(missing_ok=True)

    def test_empty_array_syncpoints(self):
        """Empty array → default duration, no crash."""
        from pipeline.generate import _stub_audio

        asset = {"audioType": "foley", "syncPoints": []}
        out = Path("/tmp/test_sync_empty.mp3")
        try:
            _stub_audio(asset, out)
            self.assertTrue(out.exists())
        finally:
            out.unlink(missing_ok=True)


# ═════════════════════════════════════════════════════════════════════════════
# §2  Video provider constraint-based routing
# ═════════════════════════════════════════════════════════════════════════════

class TestVideoProviderRouting(unittest.TestCase):
    """Regression: _pick_video_provider must route based on duration and
    reference image support — never send <2s shots to Runway."""

    def setUp(self):
        from pipeline.generate import _pick_video_provider
        self._pick = _pick_video_provider

    def test_short_shot_skips_runway(self):
        """1.5s shot must NOT include Runway (min 2s)."""
        shot = {"id": "s1", "targetDurationSec": 1.5}
        providers = self._pick(shot, runway_key="rk", gemini_key="gk")
        self.assertNotIn("runway", providers)
        self.assertIn("veo", providers)
        self.assertIn("stub", providers)

    def test_2s_shot_includes_runway(self):
        """Exactly 2s fits Runway minimum."""
        shot = {"id": "s2", "targetDurationSec": 2.0}
        providers = self._pick(shot, runway_key="rk", gemini_key="gk")
        self.assertIn("runway", providers)

    def test_long_shot_skips_veo(self):
        """9s shot exceeds Veo max (8s) but fits Runway (10s max)."""
        shot = {"id": "s3", "targetDurationSec": 9.0}
        providers = self._pick(shot, runway_key="rk", gemini_key="gk")
        self.assertIn("runway", providers)
        self.assertNotIn("veo", providers)

    def test_refs_promote_veo(self):
        """When reference images available, Veo is preferred (supports refs)."""
        shot = {"id": "s4", "targetDurationSec": 3.0}
        refs = [b"x" * 200]
        providers = self._pick(shot, runway_key="rk", gemini_key="gk", reference_images=refs)
        self.assertEqual(providers[0], "veo")

    def test_no_refs_runway_first(self):
        """Without refs, Runway comes before Veo for eligible durations."""
        shot = {"id": "s5", "targetDurationSec": 3.0}
        providers = self._pick(shot, runway_key="rk", gemini_key="gk")
        runway_idx = providers.index("runway")
        veo_idx = providers.index("veo")
        self.assertLess(runway_idx, veo_idx)

    def test_no_keys_only_stub(self):
        """No API keys → only stub."""
        shot = {"id": "s6", "targetDurationSec": 3.0}
        providers = self._pick(shot, runway_key=None, gemini_key=None)
        self.assertEqual(providers, ["stub"])

    def test_stub_always_last(self):
        """Stub is always the final fallback."""
        shot = {"id": "s7", "targetDurationSec": 3.0}
        providers = self._pick(shot, runway_key="rk", gemini_key="gk")
        self.assertEqual(providers[-1], "stub")


# ═════════════════════════════════════════════════════════════════════════════
# §3  Reference image chaining — BytesIO .name for MIME type
# ═════════════════════════════════════════════════════════════════════════════

class TestReferenceImageChaining(unittest.TestCase):
    """Regression: generate_image with reference_image must send a BytesIO
    with .name='reference.png' so OpenAI detects the correct MIME type.
    Without this, the API returns 'unsupported mimetype application/octet-stream'."""

    @patch("pipeline.providers._openai")
    def test_bytesio_has_png_name(self, mock_openai_factory):
        """The BytesIO passed to images.edit must have .name = 'reference.png'."""
        from pipeline.providers import generate_image

        mock_client = MagicMock()
        mock_openai_factory.return_value = mock_client

        # Make images.edit return valid base64 PNG
        import base64
        fake_png = base64.b64encode(b"fake-png-bytes").decode()
        mock_resp = MagicMock()
        mock_resp.data = [MagicMock(b64_json=fake_png)]
        mock_client.images.edit.return_value = mock_resp

        ref_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # fake PNG header
        generate_image("test prompt", reference_image=ref_bytes)

        # Verify images.edit was called (not images.generate)
        mock_client.images.edit.assert_called_once()

        # Extract the BytesIO from the call
        call_kwargs = mock_client.images.edit.call_args
        image_arg = call_kwargs.kwargs.get("image") or call_kwargs[1].get("image")
        self.assertIsInstance(image_arg, list)
        buf = image_arg[0]
        self.assertIsInstance(buf, io.BytesIO)
        self.assertEqual(buf.name, "reference.png")

    @patch("pipeline.providers._openai")
    def test_no_reference_uses_generate(self, mock_openai_factory):
        """Without reference_image, images.generate is used (not edit)."""
        from pipeline.providers import generate_image

        mock_client = MagicMock()
        mock_openai_factory.return_value = mock_client

        import base64
        fake_png = base64.b64encode(b"fake-png-bytes").decode()
        mock_resp = MagicMock()
        mock_resp.data = [MagicMock(b64_json=fake_png)]
        mock_client.images.generate.return_value = mock_resp

        generate_image("test prompt")

        mock_client.images.generate.assert_called()
        mock_client.images.edit.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# §4  Codec name mapping (H.265 → libx265)
# ═════════════════════════════════════════════════════════════════════════════

class TestCodecMapping(unittest.TestCase):
    """Regression: _encode_cmd must map standard codec names to ffmpeg
    encoder names. 'H.265' sent directly causes 'Unknown encoder' error."""

    def _build_cmd(self, codec_name: str, profile: str | None = None) -> list[str]:
        from pipeline.assemble import _encode_cmd

        rp = {
            "operations": [{
                "opType": "encode",
                "compression": {"codec": codec_name},
            }]
        }
        if profile:
            rp["operations"][0]["compression"]["profile"] = profile

        return _encode_cmd(
            Path("/tmp/input.mp4"),
            {"video": {"resolution": {"widthPx": 1920, "heightPx": 1080},
                       "frameRate": {"fps": 24}},
             "audio": {"sampleRateHz": 48000}},
            Path("/tmp/output.mp4"),
            render_plan=rp,
        )

    def test_h265_maps_to_libx265(self):
        cmd = self._build_cmd("H.265")
        self.assertIn("libx265", cmd)
        self.assertNotIn("H.265", cmd)

    def test_h264_maps_to_libx264(self):
        cmd = self._build_cmd("H.264")
        self.assertIn("libx264", cmd)

    def test_hevc_maps_to_libx265(self):
        cmd = self._build_cmd("HEVC")
        self.assertIn("libx265", cmd)

    def test_vp9_maps_to_libvpx(self):
        cmd = self._build_cmd("VP9")
        self.assertIn("libvpx-vp9", cmd)

    def test_av1_maps_to_svtav1(self):
        cmd = self._build_cmd("AV1")
        self.assertIn("libsvtav1", cmd)

    def test_already_ffmpeg_name_passthrough(self):
        cmd = self._build_cmd("libx264")
        self.assertIn("libx264", cmd)

    def test_unknown_codec_passthrough(self):
        """Unknown codec names pass through unchanged (ffmpeg will error)."""
        cmd = self._build_cmd("prores_ks")
        self.assertIn("prores_ks", cmd)


# ═════════════════════════════════════════════════════════════════════════════
# §5  Profile normalization ("Main 10" → "main10")
# ═════════════════════════════════════════════════════════════════════════════

class TestProfileNormalization(unittest.TestCase):
    """Regression: x265 profile 'Main 10' must be normalized to 'main10'
    (lowercase, no space). Without this, ffmpeg errors with
    'Invalid or incompatible profile set: Main 10'."""

    def _build_cmd(self, profile: str) -> list[str]:
        from pipeline.assemble import _encode_cmd

        rp = {
            "operations": [{
                "opType": "encode",
                "compression": {"codec": "H.265", "profile": profile},
            }]
        }
        return _encode_cmd(
            Path("/tmp/input.mp4"),
            {"video": {"resolution": {"widthPx": 1920, "heightPx": 1080},
                       "frameRate": {"fps": 24}},
             "audio": {"sampleRateHz": 48000}},
            Path("/tmp/output.mp4"),
            render_plan=rp,
        )

    def test_main_10_normalized(self):
        cmd = self._build_cmd("Main 10")
        idx = cmd.index("-profile:v")
        self.assertEqual(cmd[idx + 1], "main10")

    def test_high_profile_normalized(self):
        cmd = self._build_cmd("High")
        idx = cmd.index("-profile:v")
        self.assertEqual(cmd[idx + 1], "high")

    def test_already_lowercase_unchanged(self):
        cmd = self._build_cmd("main10")
        idx = cmd.index("-profile:v")
        self.assertEqual(cmd[idx + 1], "main10")


# ═════════════════════════════════════════════════════════════════════════════
# §6  Build ID and log file naming
# ═════════════════════════════════════════════════════════════════════════════

class TestBuildIdAndLogs(unittest.TestCase):
    """Regression: each build must produce a UUID-named log and manifest."""

    def test_stub_build_creates_uuid_log(self):
        """A stub render must create build-{uuid}.log and build-{uuid}.json."""
        import shutil
        out = Path("/tmp/test-build-uuid")
        if out.exists():
            shutil.rmtree(out)

        spark_path = Path(__file__).parent.parent / "examples" / "spark.gvpp.json"
        if not spark_path.exists():
            self.skipTest("spark.gvpp.json not found")

        from pipeline.run import main
        result = main([
            "render", str(spark_path),
            "--output-dir", str(out),
            "--stub-only", "--skip-validation",
        ])

        self.assertEqual(result, 0)

        # Find build log and manifest
        logs = list(out.glob("build-*.log"))
        manifests = list(out.glob("build-*.json"))
        self.assertEqual(len(logs), 1, f"Expected 1 log, found {len(logs)}: {logs}")
        self.assertEqual(len(manifests), 1, f"Expected 1 manifest, found {len(manifests)}: {manifests}")

        # Build ID matches between log and manifest
        log_id = logs[0].stem.replace("build-", "")
        manifest_id = manifests[0].stem.replace("build-", "")
        self.assertEqual(log_id, manifest_id)

        # Manifest is valid JSON with expected fields
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        self.assertEqual(manifest["buildId"], log_id)
        self.assertIn("timestamp", manifest)
        self.assertIn("durationSec", manifest)
        self.assertTrue(manifest["stubOnly"])

        # Log is non-empty
        log_size = logs[0].stat().st_size
        self.assertGreater(log_size, 100)

        shutil.rmtree(out)

    def test_two_builds_different_ids(self):
        """Two consecutive builds to the same dir produce different UUIDs."""
        import shutil
        out = Path("/tmp/test-build-multi")
        if out.exists():
            shutil.rmtree(out)

        spark_path = Path(__file__).parent.parent / "examples" / "spark.gvpp.json"
        if not spark_path.exists():
            self.skipTest("spark.gvpp.json not found")

        from pipeline.run import main
        main(["render", str(spark_path), "--output-dir", str(out),
              "--stub-only", "--skip-validation"])
        main(["render", str(spark_path), "--output-dir", str(out),
              "--stub-only", "--skip-validation"])

        logs = sorted(out.glob("build-*.log"))
        self.assertEqual(len(logs), 2)
        id1 = logs[0].stem.replace("build-", "")
        id2 = logs[1].stem.replace("build-", "")
        self.assertNotEqual(id1, id2)

        shutil.rmtree(out)


# ═════════════════════════════════════════════════════════════════════════════
# §7  Enriched prompt passthrough to Runway
# ═════════════════════════════════════════════════════════════════════════════

class TestRunwayEnrichedPrompt(unittest.TestCase):
    """Regression: _runway_generate_shot must accept and use enriched_prompt
    instead of falling back to bare 'cinematic shot'."""

    @patch("requests.post")
    def test_enriched_prompt_used(self, mock_post):
        """enriched_prompt kwarg should be the actual promptText sent to Runway."""
        from pipeline.generate import _runway_generate_shot

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "task-123"}
        mock_post.return_value = mock_resp

        shot = {"id": "test-shot", "targetDurationSec": 3, "purpose": "fallback purpose"}
        out = Path("/tmp/test_runway_prompt.mp4")

        try:
            _runway_generate_shot(
                shot, "fake-key", out,
                enriched_prompt="A detailed cinematic description of the scene with Spark robot"
            )
        except Exception:
            pass  # We only care about the POST payload

        # Check the payload sent to Runway
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertIn("Spark robot", payload["promptText"])
        self.assertNotEqual(payload["promptText"], "cinematic shot")
        self.assertNotEqual(payload["promptText"], "fallback purpose")

    @patch("requests.post")
    def test_fallback_without_enriched(self, mock_post):
        """Without enriched_prompt, falls back to shot.purpose."""
        from pipeline.generate import _runway_generate_shot

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"id": "task-456"}
        mock_post.return_value = mock_resp

        shot = {"id": "test", "targetDurationSec": 3, "purpose": "Establish desolation"}
        try:
            _runway_generate_shot(shot, "fake-key", Path("/tmp/test.mp4"))
        except Exception:
            pass

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertEqual(payload["promptText"], "Establish desolation")


# ═════════════════════════════════════════════════════════════════════════════
# §8  Schema path resolution
# ═════════════════════════════════════════════════════════════════════════════

class TestSchemaPathResolution(unittest.TestCase):
    """Regression: all pipeline modules must point to schemas/active/gvpp-v3.schema.json."""

    def test_run_schema_path(self):
        from pipeline.run import _V3_SCHEMA
        self.assertIn("active", str(_V3_SCHEMA))
        self.assertTrue(_V3_SCHEMA.name == "gvpp-v3.schema.json")

    def test_create_schema_path(self):
        from pipeline.create import SCHEMA_FILE
        self.assertIn("active", str(SCHEMA_FILE))
        self.assertTrue(SCHEMA_FILE.name == "gvpp-v3.schema.json")

    def test_pipeline_check_schema_path(self):
        from pipeline.pipeline_check import _V3_SCHEMA
        self.assertIn("active", str(_V3_SCHEMA))

    def test_schema_file_exists(self):
        from pipeline.run import _V3_SCHEMA
        self.assertTrue(_V3_SCHEMA.exists(), f"Schema not found: {_V3_SCHEMA}")


if __name__ == "__main__":
    unittest.main()
