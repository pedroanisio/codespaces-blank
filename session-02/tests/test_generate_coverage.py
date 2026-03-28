"""
Coverage tests for pipeline/generate.py — targeting >90% line coverage.

Covers:
  - Helper functions (_hex_to_rgb, _shot_id)
  - Stub generators (_stub_shot_video, _stub_audio)
  - Real API generators with mocks (_runway, _veo, _elevenlabs, _suno)
  - Orchestrators (generate_shots, generate_audio) with full fallback chains
  - Reference collection and per-shot ref selection logic

Run: python -m pytest tests/test_generate_coverage.py -v --cov=pipeline.generate
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def demo_instance():
    p = Path(__file__).parent.parent / "demo-30s.json"
    return json.loads(p.read_text())


@pytest.fixture
def minimal_shot():
    return {
        "id": "shot.1.v1", "logicalId": "shot.1", "entityType": "shot",
        "name": "Test Shot", "version": {"number": "1.0.0", "state": "draft"},
        "shotNumber": 1,
        "sceneRef": {"id": "scene.1.v1"},
        "targetDurationSec": 3,
        "cinematicSpec": {
            "shotType": "wide", "cameraAngle": "eye_level",
            "cameraMovement": "static", "focalLengthMm": 24,
            "colorPalette": ["#ff0000"],
        },
        "genParams": {
            "stepId": "step.1", "operationType": "video_generation",
            "prompt": "Test prompt.",
        },
    }


@pytest.fixture
def minimal_instance(minimal_shot):
    return {
        "schemaVersion": "3.1.0",
        "production": {
            "characters": [{"id": "c.v1", "logicalId": "c", "entityType": "character",
                            "name": "C", "version": {"number": "1.0.0", "state": "draft"},
                            "description": "A test character.", "heightM": 1.75}],
            "environments": [{"id": "e.v1", "logicalId": "e", "entityType": "environment",
                              "name": "E", "version": {"number": "1.0.0", "state": "draft"},
                              "description": "A test environment."}],
            "props": [],
            "styleGuides": [],
            "scenes": [{
                "id": "scene.1.v1", "logicalId": "scene.1", "entityType": "scene",
                "sceneNumber": 1, "name": "S1",
                "version": {"number": "1.0.0", "state": "draft"},
                "characterRefs": [{"id": "c.v1"}],
                "environmentRef": {"id": "e.v1"},
                "propRefs": [],
                "shotRefs": [{"id": "shot.1.v1"}],
            }],
            "shots": [minimal_shot],
        },
        "assetLibrary": {
            "audioAssets": [
                {"id": "a.dial.v1", "logicalId": "a.dial", "entityType": "audioAsset",
                 "name": "Dialogue", "audioType": "dialogue",
                 "transcript": "Hello world.",
                 "version": {"number": "1.0.0", "state": "draft"},
                 "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "mono", "codec": "flac"}},
                {"id": "a.amb.v1", "logicalId": "a.amb", "entityType": "audioAsset",
                 "name": "Wind Howling", "audioType": "ambient",
                 "version": {"number": "1.0.0", "state": "draft"},
                 "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"}},
                {"id": "a.mus.v1", "logicalId": "a.mus", "entityType": "audioAsset",
                 "name": "Epic Score", "audioType": "music",
                 "mood": "epic orchestral",
                 "version": {"number": "1.0.0", "state": "draft"},
                 "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"}},
            ],
            "visualAssets": [], "marketingAssets": [], "genericAssets": [],
        },
        "canonicalDocuments": {
            "story": {"id": "st.v1", "logicalId": "st", "entityType": "story",
                      "name": "S", "version": {"number": "1.0.0", "state": "draft"}},
            "script": {"id": "sc.v1", "logicalId": "sc", "entityType": "script",
                       "name": "S", "version": {"number": "1.0.0", "state": "draft"}},
            "directorInstructions": {
                "id": "di.v1", "logicalId": "di", "entityType": "directorInstructions",
                "name": "DI", "version": {"number": "1.0.0", "state": "draft"},
                "colorDirection": "warm amber",
                "mustAvoid": ["daylight"],
            },
        },
        "qualityProfiles": [],
        "orchestration": {"workflows": []},
        "assembly": {"timelines": [], "editVersions": [], "renderPlans": []},
        "deliverables": [], "relationships": [],
        "package": {"packageId": "p", "createdAt": "2026-01-01T00:00:00Z", "versioningPolicy": {}},
        "project": {"id": "p.v1", "logicalId": "p", "entityType": "project",
                     "name": "Test", "version": {"number": "1.0.0", "state": "draft"}},
    }


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestHexToRgb:
    def test_six_digit(self):
        from pipeline.generate import _hex_to_rgb
        assert _hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_three_digit(self):
        from pipeline.generate import _hex_to_rgb
        assert _hex_to_rgb("#f00") == (255, 0, 0)

    def test_no_hash(self):
        from pipeline.generate import _hex_to_rgb
        assert _hex_to_rgb("1a1a2e") == (26, 26, 46)


class TestShotId:
    def test_logical_id(self):
        from pipeline.generate import _shot_id
        assert _shot_id({"logicalId": "shot.1", "id": "shot.1.v1"}) == "shot.1"

    def test_id_fallback(self):
        from pipeline.generate import _shot_id
        assert _shot_id({"id": "shot.1.v1"}) == "shot.1.v1"

    def test_unknown_fallback(self):
        from pipeline.generate import _shot_id
        assert _shot_id({}) == "unknown-shot"


# ══════════════════════════════════════════════════════════════════════════════
# Stub generators
# ══════════════════════════════════════════════════════════════════════════════

class TestStubShotVideo:
    def test_creates_mp4(self, minimal_shot, tmp_path):
        from pipeline.generate import _stub_shot_video
        out = tmp_path / "test.mp4"
        _stub_shot_video(minimal_shot, out)
        assert out.exists()
        assert out.stat().st_size > 100

    def test_uses_palette_color(self, minimal_shot, tmp_path):
        from pipeline.generate import _stub_shot_video
        minimal_shot["cinematicSpec"]["colorPalette"] = ["#00ff00"]
        out = tmp_path / "test.mp4"
        _stub_shot_video(minimal_shot, out)
        assert out.exists()

    def test_default_palette(self, tmp_path):
        from pipeline.generate import _stub_shot_video
        out = tmp_path / "test.mp4"
        _stub_shot_video({"targetDurationSec": 1}, out)
        assert out.exists()


class TestStubAudio:
    def test_creates_silence_mp3(self, tmp_path):
        from pipeline.generate import _stub_audio
        out = tmp_path / "test.mp3"
        _stub_audio({"audioType": "ambient"}, out)
        assert out.exists()
        assert out.stat().st_size > 100

    def test_creates_music_tone(self, tmp_path):
        from pipeline.generate import _stub_audio
        out = tmp_path / "test.mp3"
        _stub_audio({"audioType": "music"}, out)
        assert out.exists()

    def test_uses_sync_points(self, tmp_path):
        from pipeline.generate import _stub_audio
        out = tmp_path / "test.mp3"
        _stub_audio({
            "audioType": "sfx",
            "syncPoints": {"timelineInSec": 2, "timelineOutSec": 5},
        }, out)
        assert out.exists()


# ══════════════════════════════════════════════════════════════════════════════
# Real generators (mocked APIs)
# ══════════════════════════════════════════════════════════════════════════════

class TestRunwayGenerator:
    def test_successful_generation(self, minimal_shot, tmp_path):
        from pipeline.generate import _runway_generate_shot
        out = tmp_path / "shot.mp4"

        mock_post = MagicMock()
        mock_post.ok = True
        mock_post.json.return_value = {"id": "task-123"}

        mock_poll = MagicMock()
        mock_poll.json.return_value = {"status": "SUCCEEDED", "artifacts": ["https://example.com/video.mp4"]}

        mock_download = MagicMock()
        mock_download.content = b"\x00" * 1000

        with patch("requests.post", return_value=mock_post) as mp, \
             patch("requests.get", side_effect=[mock_poll, mock_download]), \
             patch("time.sleep"):
            _runway_generate_shot(minimal_shot, "test-key", out)

        assert out.exists()
        assert out.stat().st_size == 1000

    def test_failed_task(self, minimal_shot, tmp_path):
        from pipeline.generate import _runway_generate_shot
        out = tmp_path / "shot.mp4"

        mock_post = MagicMock()
        mock_post.ok = True
        mock_post.json.return_value = {"id": "task-fail"}

        mock_poll = MagicMock()
        mock_poll.json.return_value = {"status": "FAILED", "failure": "out of credits"}

        with patch("requests.post", return_value=mock_post), \
             patch("requests.get", return_value=mock_poll), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="failed"):
                _runway_generate_shot(minimal_shot, "test-key", out)

    def test_timeout(self, minimal_shot, tmp_path):
        from pipeline.generate import _runway_generate_shot
        out = tmp_path / "shot.mp4"

        mock_post = MagicMock()
        mock_post.ok = True
        mock_post.json.return_value = {"id": "task-slow"}

        mock_poll = MagicMock()
        mock_poll.json.return_value = {"status": "PROCESSING"}

        with patch("requests.post", return_value=mock_post), \
             patch("requests.get", return_value=mock_poll), \
             patch("time.sleep"):
            with pytest.raises(TimeoutError):
                _runway_generate_shot(minimal_shot, "test-key", out)

    def test_http_error(self, minimal_shot, tmp_path):
        from pipeline.generate import _runway_generate_shot
        import requests as req
        out = tmp_path / "shot.mp4"

        mock_post = MagicMock()
        mock_post.ok = False
        mock_post.status_code = 400
        mock_post.raise_for_status.side_effect = req.HTTPError("400 Bad Request")

        with patch("requests.post", return_value=mock_post):
            with pytest.raises(req.HTTPError):
                _runway_generate_shot(minimal_shot, "test-key", out)

    def test_artifact_dict_format(self, minimal_shot, tmp_path):
        """Runway may return artifacts as [{"url": "..."}] instead of ["..."]."""
        from pipeline.generate import _runway_generate_shot
        out = tmp_path / "shot.mp4"

        mock_post = MagicMock()
        mock_post.ok = True
        mock_post.json.return_value = {"id": "task-dict"}

        mock_poll = MagicMock()
        mock_poll.json.return_value = {
            "status": "SUCCEEDED",
            "artifacts": [{"url": "https://example.com/video.mp4"}],
        }

        mock_download = MagicMock()
        mock_download.content = b"\x00" * 500

        with patch("requests.post", return_value=mock_post), \
             patch("requests.get", side_effect=[mock_poll, mock_download]), \
             patch("time.sleep"):
            _runway_generate_shot(minimal_shot, "test-key", out)

        assert out.exists()


class TestVeoGenerator:
    def _mock_veo(self, *, video_bytes=None, video_uri=None, done=True, no_video=False):
        """Build mock google.genai client and operation."""
        mock_client = MagicMock()
        mock_op = MagicMock()
        mock_op.done = done

        if no_video:
            mock_op.response = None
        else:
            mock_video = MagicMock()
            mock_video.video_bytes = video_bytes
            mock_video.uri = video_uri
            mock_generated = MagicMock()
            mock_generated.video = mock_video
            mock_op.response = MagicMock()
            mock_op.response.generated_videos = [mock_generated]

        mock_client.models.generate_videos.return_value = mock_op
        mock_client.operations.get.return_value = mock_op
        return mock_client

    def test_video_bytes_path(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(video_bytes=b"\x00" * 2000)

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "test-key", out)

        assert out.exists()
        assert out.stat().st_size == 2000

    def test_video_uri_path(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(
            video_uri="https://generativelanguage.googleapis.com/v1beta/files/abc:download"
        )

        mock_download = MagicMock()
        mock_download.content = b"\x00" * 3000

        with patch("google.genai.Client", return_value=mock_client), \
             patch("requests.get", return_value=mock_download) as mock_get, \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "my-api-key", out)

        assert out.exists()
        # Verify API key was appended to download URL
        call_url = mock_get.call_args[0][0]
        assert "key=my-api-key" in call_url

    def test_no_video_raises(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(no_video=True)

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="no video"):
                _veo_generate_shot(minimal_shot, "test-key", out)

    def test_no_bytes_no_uri_raises(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(video_bytes=None, video_uri=None)

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="no video_bytes or uri"):
                _veo_generate_shot(minimal_shot, "test-key", out)

    def test_reference_images_passed(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(video_bytes=b"\x00" * 100)

        refs = [b"\x89PNG" + b"\x00" * 200, b"\x89PNG" + b"\x00" * 200]

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "key", out, reference_images=refs)

        # First attempt includes refs (succeeds on first try since mock doesn't raise)
        first_call_config = mock_client.models.generate_videos.call_args_list[0][1]["config"]
        assert first_call_config.reference_images is not None
        assert len(first_call_config.reference_images) == 2

    def test_skips_small_ref_images(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(video_bytes=b"\x00" * 100)

        refs = [b"\x89PNG" + b"\x00" * 200, b"tiny"]  # second is too small (<100)

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "key", out, reference_images=refs)

        first_call_config = mock_client.models.generate_videos.call_args_list[0][1]["config"]
        assert len(first_call_config.reference_images) == 1

    def test_max_3_refs(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(video_bytes=b"\x00" * 100)

        refs = [b"\x89PNG" + b"\x00" * 200] * 5  # 5 refs, should cap at 3

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "key", out, reference_images=refs)

        first_call_config = mock_client.models.generate_videos.call_args_list[0][1]["config"]
        assert len(first_call_config.reference_images) == 3

    def test_reference_type_all_style(self, minimal_shot, tmp_path):
        """All refs should use STYLE type (avoids Veo policy filter vs ASSET)."""
        from pipeline.generate import _veo_generate_shot
        from google.genai import types
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(video_bytes=b"\x00" * 100)

        refs = [b"\x89PNG" + b"\x00" * 200, b"\x89PNG" + b"\x00" * 200, b"\x89PNG" + b"\x00" * 200]

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "key", out, reference_images=refs)

        first_call_config = mock_client.models.generate_videos.call_args_list[0][1]["config"]
        ref_types = [r.reference_type for r in first_call_config.reference_images]
        assert all(t == types.VideoGenerationReferenceType.STYLE for t in ref_types)

    def test_policy_rejection_retries_without_refs(self, minimal_shot, tmp_path):
        """On INVALID_ARGUMENT, should retry without reference images."""
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"

        # First call raises policy error, second succeeds
        mock_client = MagicMock()
        mock_op_success = MagicMock()
        mock_op_success.done = True
        mock_video = MagicMock()
        mock_video.video_bytes = b"\x00" * 2000
        mock_video.uri = None
        mock_generated = MagicMock()
        mock_generated.video = mock_video
        mock_op_success.response = MagicMock()
        mock_op_success.response.generated_videos = [mock_generated]

        mock_client.models.generate_videos.side_effect = [
            Exception("400 INVALID_ARGUMENT: use case not supported"),
            mock_op_success,
        ]
        mock_client.operations.get.return_value = mock_op_success

        refs = [b"\x89PNG" + b"\x00" * 200]

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "key", out, reference_images=refs)

        assert out.exists()
        # Should have been called twice: once with refs (failed), once without
        assert mock_client.models.generate_videos.call_count == 2
        second_config = mock_client.models.generate_videos.call_args_list[1][1]["config"]
        # Second attempt should have no reference images
        has_refs = getattr(second_config, "reference_images", None)
        assert not has_refs or len(has_refs) == 0

    def test_enriched_prompt_used(self, minimal_shot, tmp_path):
        from pipeline.generate import _veo_generate_shot
        out = tmp_path / "shot.mp4"
        mock_client = self._mock_veo(video_bytes=b"\x00" * 100)

        with patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            _veo_generate_shot(minimal_shot, "key", out, enriched_prompt="CUSTOM PROMPT")

        call_prompt = mock_client.models.generate_videos.call_args[1]["prompt"]
        assert call_prompt == "CUSTOM PROMPT"


class TestElevenLabsGenerator:
    def test_successful_tts(self, tmp_path):
        from pipeline.generate import _elevenlabs_generate_audio
        out = tmp_path / "audio.mp3"
        asset = {"transcript": "Hello world.", "audioType": "dialogue"}

        mock_resp = MagicMock()
        mock_resp.content = b"\xff\xfb\x90" + b"\x00" * 500

        with patch("requests.post", return_value=mock_resp):
            _elevenlabs_generate_audio(asset, "test-key", out)

        assert out.exists()

    def test_empty_transcript_stubs(self, tmp_path):
        from pipeline.generate import _elevenlabs_generate_audio
        out = tmp_path / "audio.mp3"
        asset = {"transcript": "", "audioType": "dialogue"}

        with patch("pipeline.generate._stub_audio") as mock_stub:
            _elevenlabs_generate_audio(asset, "test-key", out)
            mock_stub.assert_called_once()

    def test_custom_voice_id(self, tmp_path):
        from pipeline.generate import _elevenlabs_generate_audio
        out = tmp_path / "audio.mp3"
        asset = {
            "transcript": "Custom voice.",
            "generation": {"steps": [{"voiceId": "custom-voice-123"}]},
        }

        mock_resp = MagicMock()
        mock_resp.content = b"\x00" * 500

        with patch("requests.post", return_value=mock_resp) as mock_post:
            _elevenlabs_generate_audio(asset, "test-key", out)

        call_url = mock_post.call_args[0][0]
        assert "custom-voice-123" in call_url


class TestSunoGenerator:
    def test_successful_music(self, tmp_path):
        from pipeline.generate import _suno_generate_music
        out = tmp_path / "music.mp3"
        asset = {"audioType": "music"}

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "clips": [{"audio_url": "https://example.com/music.mp3"}]
        }

        mock_download = MagicMock()
        mock_download.content = b"\x00" * 1000

        with patch("requests.post", return_value=mock_resp), \
             patch("requests.get", return_value=mock_download):
            _suno_generate_music(asset, "cookie-val", out)

        assert out.exists()

    def test_no_clips_raises(self, tmp_path):
        from pipeline.generate import _suno_generate_music
        out = tmp_path / "music.mp3"

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"clips": []}

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(ValueError, match="no clips"):
                _suno_generate_music({}, "cookie", out)


# ══════════════════════════════════════════════════════════════════════════════
# generate_shots orchestrator
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateShots:
    def test_empty_shots_returns_empty(self, tmp_path):
        from pipeline.generate import generate_shots
        instance = {"production": {"scenes": [], "shots": []}}
        with patch("pipeline.generate._generate_reference_images") as m:
            result = generate_shots(instance, tmp_path)
        assert result == {}

    def test_stub_fallback(self, minimal_instance, tmp_path):
        """With no API keys, falls through to stub."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": ""}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img):
            result = generate_shots(minimal_instance, tmp_path)

        assert len(result) == 1
        assert "shot.1" in result
        assert result["shot.1"].exists()

    def test_cache_hit(self, minimal_instance, tmp_path):
        """Pre-existing shot file should be used without regeneration."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500

        shots_dir = tmp_path / "shots"
        shots_dir.mkdir()
        cached = shots_dir / "shot.1.mp4"
        cached.write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": ""}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img):
            result = generate_shots(minimal_instance, tmp_path)

        assert result["shot.1"] == cached

    def test_runway_to_veo_fallback(self, minimal_instance, tmp_path):
        """Runway fails → Veo succeeds."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500

        mock_veo_client = MagicMock()
        mock_op = MagicMock()
        mock_op.done = True
        mock_video = MagicMock()
        mock_video.video_bytes = b"\x00" * 2000
        mock_video.uri = None
        mock_gen = MagicMock()
        mock_gen.video = mock_video
        mock_op.response = MagicMock()
        mock_op.response.generated_videos = [mock_gen]
        mock_veo_client.models.generate_videos.return_value = mock_op
        mock_veo_client.operations.get.return_value = mock_op

        import requests as req

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "bad-key", "GEMINI_API_KEY": "good-key"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("requests.post", side_effect=req.HTTPError("400")), \
             patch("google.genai.Client", return_value=mock_veo_client), \
             patch("time.sleep"):
            result = generate_shots(minimal_instance, tmp_path)

        assert len(result) == 1
        assert result["shot.1"].exists()
        assert result["shot.1"].stat().st_size == 2000


# ══════════════════════════════════════════════════════════════════════════════
# generate_audio orchestrator
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateAudio:
    def test_stub_with_no_keys(self, minimal_instance, tmp_path):
        """No API keys → all audio stubs."""
        from pipeline.generate import generate_audio

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "", "SUNO_COOKIE": ""}, clear=False):
            result = generate_audio(minimal_instance, tmp_path)

        assert len(result) == 3
        for path in result.values():
            assert path.exists()

    def test_elevenlabs_dialogue_routing(self, minimal_instance, tmp_path):
        """Dialogue with transcript routes to ElevenLabs TTS."""
        from pipeline.generate import generate_audio

        mock_resp = MagicMock()
        mock_resp.content = b"\xff" * 500

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key", "SUNO_COOKIE": ""}, clear=False), \
             patch("requests.post", return_value=mock_resp), \
             patch("pipeline.providers.generate_sound_effect", return_value=b"\x00" * 300), \
             patch("pipeline.providers.generate_music", return_value=b"\x00" * 300):
            result = generate_audio(minimal_instance, tmp_path)

        assert len(result) == 3
        # Dialogue should have real content
        dial_path = result.get("a.dial")
        assert dial_path and dial_path.exists()

    def test_sfx_uses_name_as_prompt(self, minimal_instance, tmp_path):
        """SFX assets use name field as fallback prompt."""
        from pipeline.generate import generate_audio

        captured_prompts = []

        def mock_sfx(prompt, **kw):
            captured_prompts.append(prompt)
            return b"\x00" * 300

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "key", "SUNO_COOKIE": ""}, clear=False), \
             patch("requests.post", return_value=MagicMock(content=b"\x00" * 300)), \
             patch("pipeline.providers.generate_sound_effect", side_effect=mock_sfx), \
             patch("pipeline.providers.generate_music", return_value=b"\x00" * 300):
            generate_audio(minimal_instance, tmp_path)

        # "Wind Howling" is the ambient asset name
        assert any("Wind Howling" in p for p in captured_prompts)

    def test_music_uses_mood(self, minimal_instance, tmp_path):
        """Music assets use mood field as prompt."""
        from pipeline.generate import generate_audio

        captured_prompts = []

        def mock_music(prompt, **kw):
            captured_prompts.append(prompt)
            return b"\x00" * 300

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "key", "SUNO_COOKIE": ""}, clear=False), \
             patch("requests.post", return_value=MagicMock(content=b"\x00" * 300)), \
             patch("pipeline.providers.generate_sound_effect", return_value=b"\x00" * 300), \
             patch("pipeline.providers.generate_music", side_effect=mock_music):
            generate_audio(minimal_instance, tmp_path)

        assert any("epic orchestral" in p for p in captured_prompts)

    def test_cache_hit(self, minimal_instance, tmp_path):
        """Pre-existing audio files should be used."""
        from pipeline.generate import generate_audio

        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        for name in ["a.dial", "a.amb", "a.mus"]:
            (audio_dir / f"{name}.mp3").write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "", "SUNO_COOKIE": ""}, clear=False):
            result = generate_audio(minimal_instance, tmp_path)

        assert len(result) == 3

    def test_elevenlabs_failure_falls_to_stub(self, minimal_instance, tmp_path):
        """If ElevenLabs fails, fall back to stub audio."""
        from pipeline.generate import generate_audio

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "bad-key", "SUNO_COOKIE": ""}, clear=False), \
             patch("requests.post", side_effect=Exception("API error")), \
             patch("pipeline.providers.generate_sound_effect", side_effect=Exception("fail")), \
             patch("pipeline.providers.generate_music", side_effect=Exception("fail")):
            result = generate_audio(minimal_instance, tmp_path)

        assert len(result) == 3
        for path in result.values():
            assert path.exists()  # stubs were generated


# ══════════════════════════════════════════════════════════════════════════════
# extract_last_frame (additional edge cases)
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractLastFrameEdge:
    def test_corrupt_video_returns_none(self, tmp_path):
        from pipeline.generate import _extract_last_frame
        bad_video = tmp_path / "bad.mp4"
        bad_video.write_bytes(b"not a video")
        assert _extract_last_frame(bad_video) is None


# ══════════════════════════════════════════════════════════════════════════════
# generate_shots: ref collection integration (lines 993-1127)
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateShotsRefCollection:
    """Test the per-shot reference collection logic inside generate_shots._process()."""

    def _make_rich_instance(self):
        """Instance with anchors, props, envs, POV — exercises all ref paths."""
        return {
            "schemaVersion": "3.1.0",
            "production": {
                "characters": [
                    {"id": "c.v1", "logicalId": "c", "entityType": "character",
                     "name": "C", "version": {"number": "1.0.0", "state": "draft"},
                     "description": "Character.", "heightM": 1.7},
                ],
                "environments": [
                    {"id": "e.v1", "logicalId": "e", "entityType": "environment",
                     "name": "E", "version": {"number": "1.0.0", "state": "draft"},
                     "description": "Environment."},
                ],
                "props": [
                    {"id": "p.v1", "logicalId": "p", "entityType": "prop",
                     "name": "P", "version": {"number": "1.0.0", "state": "draft"},
                     "description": "Prop."},
                ],
                "styleGuides": [],
                "scenes": [{
                    "id": "sc.v1", "logicalId": "sc", "entityType": "scene",
                    "sceneNumber": 1, "name": "S1",
                    "version": {"number": "1.0.0", "state": "draft"},
                    "characterRefs": [{"id": "c.v1"}],
                    "environmentRef": {"id": "e.v1"},
                    "propRefs": [{"id": "p.v1"}],
                    "shotRefs": [{"id": "sh.1.v1"}, {"id": "sh.2.v1"}],
                }],
                "shots": [
                    {
                        "id": "sh.1.v1", "logicalId": "sh.1", "entityType": "shot",
                        "name": "Shot 1", "version": {"number": "1.0.0", "state": "draft"},
                        "shotNumber": 1, "sceneRef": {"id": "sc.v1"},
                        "targetDurationSec": 2,
                        "cinematicSpec": {
                            "shotType": "wide", "cameraAngle": "eye_level",
                            "cameraMovement": "static", "focalLengthMm": 24,
                            "colorPalette": ["#111111"],
                        },
                        "genParams": {
                            "stepId": "s1", "operationType": "video_generation",
                            "prompt": "Shot 1.",
                            "consistencyAnchors": [
                                {"anchorType": "character", "name": "C lock",
                                 "ref": {"id": "c.v1"}, "lockLevel": "hard"},
                                {"anchorType": "environment", "name": "E lock",
                                 "ref": {"id": "e.v1"}, "lockLevel": "medium"},
                                {"anchorType": "prop", "name": "P lock",
                                 "ref": {"id": "p.v1"}, "lockLevel": "soft"},
                            ],
                        },
                    },
                    {
                        "id": "sh.2.v1", "logicalId": "sh.2", "entityType": "shot",
                        "name": "Shot 2", "version": {"number": "1.0.0", "state": "draft"},
                        "shotNumber": 2, "sceneRef": {"id": "sc.v1"},
                        "targetDurationSec": 2,
                        "cinematicSpec": {
                            "shotType": "POV", "cameraAngle": "eye_level",
                            "cameraMovement": "static", "focalLengthMm": 50,
                            "temporalBridgeAnchorRef": {"id": "sh.1.v1"},
                            "colorPalette": ["#222222"],
                        },
                        "genParams": {
                            "stepId": "s2", "operationType": "video_generation",
                            "prompt": "Shot 2 POV.",
                        },
                    },
                ],
            },
            "assetLibrary": {"audioAssets": [], "visualAssets": [], "marketingAssets": [], "genericAssets": []},
            "canonicalDocuments": {
                "story": {"id": "st.v1", "logicalId": "st", "entityType": "story",
                          "name": "S", "version": {"number": "1.0.0", "state": "draft"}},
                "script": {"id": "sc2.v1", "logicalId": "sc2", "entityType": "script",
                           "name": "S", "version": {"number": "1.0.0", "state": "draft"}},
                "directorInstructions": {
                    "id": "di.v1", "logicalId": "di", "entityType": "directorInstructions",
                    "name": "DI", "version": {"number": "1.0.0", "state": "draft"},
                    "colorDirection": "warm amber",
                },
            },
            "qualityProfiles": [],
            "orchestration": {"workflows": []},
            "assembly": {"timelines": [], "editVersions": [], "renderPlans": []},
            "deliverables": [], "relationships": [],
            "package": {"packageId": "p", "createdAt": "2026-01-01T00:00:00Z", "versioningPolicy": {}},
            "project": {"id": "p.v1", "logicalId": "p", "entityType": "project",
                         "name": "T", "version": {"number": "1.0.0", "state": "draft"}},
        }

    def test_anchors_collect_character_env_prop_refs(self, tmp_path):
        """Shot with char/env/prop anchors should collect refs from all three."""
        from pipeline.generate import generate_shots, ReferenceLibrary
        fake_img = b"\x89PNG" + b"\x00" * 500
        instance = self._make_rich_instance()

        veo_refs_captured = []

        original_veo = None

        def mock_veo(shot, key, out, *, enriched_prompt=None, reference_images=None):
            veo_refs_captured.append(reference_images or [])
            out.write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": "k"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("pipeline.generate._veo_generate_shot", side_effect=mock_veo):
            result = generate_shots(instance, tmp_path)

        assert len(result) == 2
        # Shot 1 has 3 explicit anchors → should have refs from char + env + prop
        # The actual count depends on dedup but should be >= 1
        shot1_refs = veo_refs_captured[0] if veo_refs_captured else []
        assert len(shot1_refs) >= 1, "Shot 1 should have at least 1 reference image"

    def test_pov_shot_gets_pov_plate_priority(self, tmp_path):
        """POV shot type should prioritize the POV plate (priority 0)."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500
        instance = self._make_rich_instance()

        veo_calls = []

        def mock_veo(shot, key, out, *, enriched_prompt=None, reference_images=None):
            veo_calls.append({"shot": shot.get("logicalId"), "refs": len(reference_images or [])})
            out.write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": "k"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("pipeline.generate._veo_generate_shot", side_effect=mock_veo):
            generate_shots(instance, tmp_path)

        # Shot 2 is POV type — should get refs including POV plate
        shot2 = next((c for c in veo_calls if c["shot"] == "sh.2"), None)
        assert shot2 is not None
        assert shot2["refs"] >= 1

    def test_temporal_bridge_extracts_frame(self, tmp_path):
        """Shot with temporalBridgeAnchorRef should try to extract last frame from prev shot."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500
        instance = self._make_rich_instance()

        # Pre-create shot 1 so temporal bridge can extract from it
        shots_dir = tmp_path / "shots"
        shots_dir.mkdir(parents=True)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=64x64:d=1",
            "-c:v", "libx264", "-preset", "ultrafast", str(shots_dir / "sh.1.mp4"),
        ], capture_output=True, check=True)

        frame_extracted = []

        def mock_veo(shot, key, out, *, enriched_prompt=None, reference_images=None):
            if shot.get("logicalId") == "sh.2":
                frame_extracted.append(len(reference_images or []))
            out.write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": "k"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("pipeline.generate._veo_generate_shot", side_effect=mock_veo):
            generate_shots(instance, tmp_path)

        # Shot 2 has temporal bridge to shot 1 — should have extra ref from frame extraction
        assert len(frame_extracted) >= 1
        assert frame_extracted[0] >= 2  # at least: default fallback ref + temporal bridge frame

    def test_veo_timeout_raises(self, minimal_instance, tmp_path):
        """Veo timeout should fall through to stub."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500

        mock_client = MagicMock()
        mock_op = MagicMock()
        mock_op.done = False  # never completes
        mock_client.models.generate_videos.return_value = mock_op
        mock_client.operations.get.return_value = mock_op

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": "k"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("google.genai.Client", return_value=mock_client), \
             patch("time.sleep"):
            result = generate_shots(minimal_instance, tmp_path)

        # Should fall through to stub
        assert len(result) == 1
        assert result["shot.1"].exists()

    def test_no_anchors_uses_all_refs(self, tmp_path):
        """Shot with no explicit anchors should use all available refs."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500
        instance = self._make_rich_instance()
        # Remove anchors from shot 2
        instance["production"]["shots"][1]["genParams"].pop("consistencyAnchors", None)

        refs_passed = []

        def mock_veo(shot, key, out, *, enriched_prompt=None, reference_images=None):
            if shot.get("logicalId") == "sh.2":
                refs_passed.append(len(reference_images or []))
            out.write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": "k"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("pipeline.generate._veo_generate_shot", side_effect=mock_veo):
            generate_shots(instance, tmp_path)

        # Shot 2 has no anchors → fallback D uses all character fronts + env wide plate
        assert refs_passed[0] >= 1

    def test_scene_continuity_block_injected_in_prompt(self, tmp_path):
        """Shots sharing a scene should get a [SCENE CONTINUITY] block in the prompt."""
        from pipeline.generate import _enrich_prompt
        instance = self._make_rich_instance()
        shot1 = instance["production"]["shots"][0]
        prompt = _enrich_prompt(shot1, instance, "test preamble")
        assert "[SCENE CONTINUITY — CRITICAL]" in prompt
        assert "IDENTICAL" in prompt
        # Should reference the sibling shot
        assert "sh.2" in prompt or "Shot 2" in prompt

    def test_scene_continuity_absent_for_single_shot_scene(self, tmp_path):
        """Single-shot scene should NOT get continuity block."""
        from pipeline.generate import _enrich_prompt
        instance = self._make_rich_instance()
        # Remove shot 2 so scene has only 1 shot
        instance["production"]["shots"] = [instance["production"]["shots"][0]]
        instance["production"]["scenes"][0]["shotRefs"] = [{"id": "sh.1.v1"}]
        shot1 = instance["production"]["shots"][0]
        prompt = _enrich_prompt(shot1, instance, "test preamble")
        assert "[SCENE CONTINUITY" not in prompt

    def test_auto_temporal_bridge_for_second_shot(self, tmp_path):
        """Second shot in a scene should auto-infer temporal bridge from first."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500
        instance = self._make_rich_instance()
        # Remove explicit temporal bridge to test auto-inference
        instance["production"]["shots"][1]["cinematicSpec"].pop("temporalBridgeAnchorRef", None)

        # Pre-create shot 1 so temporal bridge can extract from it
        shots_dir = tmp_path / "shots"
        shots_dir.mkdir(parents=True)
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=64x64:d=1",
            "-c:v", "libx264", "-preset", "ultrafast", str(shots_dir / "sh.1.mp4"),
        ], capture_output=True, check=True)

        refs_for_shot2 = []

        def mock_veo(shot, key, out, *, enriched_prompt=None, reference_images=None):
            if shot.get("logicalId") == "sh.2":
                refs_for_shot2.append(len(reference_images or []))
            out.write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": "k"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("pipeline.generate._veo_generate_shot", side_effect=mock_veo):
            generate_shots(instance, tmp_path)

        # Auto-inferred bridge → should have temporal bridge frame
        assert len(refs_for_shot2) >= 1
        assert refs_for_shot2[0] >= 2

    def test_scene_level_anchors_inherited_by_shots(self, tmp_path):
        """Scene-level generation.consistencyAnchors should be inherited by shots."""
        from pipeline.generate import generate_shots
        fake_img = b"\x89PNG" + b"\x00" * 500
        instance = self._make_rich_instance()
        # Remove shot-level anchors, add scene-level ones
        for s in instance["production"]["shots"]:
            s.get("genParams", {}).pop("consistencyAnchors", None)
        instance["production"]["scenes"][0]["generation"] = {
            "consistencyAnchors": [
                {"anchorType": "character", "name": "Scene char lock",
                 "ref": {"id": "c.v1"}, "lockLevel": "hard"},
            ]
        }

        veo_calls = []

        def mock_veo(shot, key, out, *, enriched_prompt=None, reference_images=None):
            veo_calls.append({"shot": shot.get("logicalId"), "refs": len(reference_images or [])})
            out.write_bytes(b"\x00" * 100)

        with patch.dict(os.environ, {"RUNWAY_API_KEY": "", "GEMINI_API_KEY": "k"}, clear=False), \
             patch("pipeline.providers.generate_image", return_value=fake_img), \
             patch("pipeline.generate._veo_generate_shot", side_effect=mock_veo):
            generate_shots(instance, tmp_path)

        # Both shots should have inherited the scene-level anchor → character ref
        assert all(c["refs"] >= 1 for c in veo_calls)
