"""
generate.py — AI generation layer for the video production pipeline (v3 schema).

Two modes per asset type:
  STUB  (default)  — creates placeholder assets using FFmpeg.
                     No API keys required. Produces a fully runnable pipeline.
  REAL             — calls actual APIs when the matching env var is set:
                       RUNWAY_API_KEY     → Runway Gen4  (video shots)
                       GEMINI_API_KEY     → Google Veo 3.1 (video shots — fallback)
                       ELEVENLABS_API_KEY → ElevenLabs   (dialogue / voice-over)
                       SUNO_COOKIE        → Suno         (music)

Public API
----------
  generate_shots(instance, output_dir)  -> dict[shot_logical_id, Path]
  generate_audio(instance, output_dir)  -> dict[audio_logical_id, Path]

Schema (v3)
-----------
  Shots come from  instance["production"]["shots"]
  ordered via      instance["production"]["scenes"][*]["shotRefs"]

  Audio assets are instance["assetLibrary"]["audioAssets"]
  with sync timing in asset["syncPoints"]["timelineInSec/OutSec/..."]
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

log = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _shot_id(shot: dict) -> str:
    return shot.get("logicalId") or shot.get("id") or "unknown-shot"


def _shots_in_order(instance: dict) -> list[dict]:
    """
    Return all shots sorted by scene order then shot order within each scene.
    Reads v3 fields: production.scenes[*].shotRefs → production.shots.
    """
    production = instance.get("production", {})
    shots_by_lid: dict[str, dict] = {
        _shot_id(s): s for s in production.get("shots", [])
    }

    scenes = sorted(
        production.get("scenes", []),
        key=lambda s: s.get("sceneNumber", 0),
    )

    ordered: list[dict] = []
    seen: set[str] = set()
    for scene in scenes:
        for ref in scene.get("shotRefs", []):
            lid = ref.get("logicalId") or ref.get("id") or ""
            if lid and lid not in seen:
                shot = shots_by_lid.get(lid)
                if shot:
                    ordered.append(shot)
                    seen.add(lid)

    # Fallback: no scene→shot refs — use shots list sorted by order
    if not ordered:
        ordered = sorted(production.get("shots", []), key=lambda s: s.get("order", 0))

    return ordered


# ── stub generators ───────────────────────────────────────────────────────────

def _stub_shot_video(shot: dict, out_path: Path) -> None:
    """
    Solid-colour MP4 clip coloured from cinematicSpec.colorPalette,
    duration from targetDurationSec.  FFmpeg drawtext labels each clip.
    """
    duration = float(shot.get("targetDurationSec", 5.0))
    spec = shot.get("cinematicSpec") or {}
    palette = spec.get("colorPalette") or ["#1a1a2e"]
    r, g, b = _hex_to_rgb(palette[0])

    label = (shot.get("purpose") or _shot_id(shot))[:50].replace(":", r"\:").replace("'", "")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={r:02x}{g:02x}{b:02x}:s=1920x1080:r=24:d={duration}",
        "-vf", f"drawtext=text='{label}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-an",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    log.debug("stub video → %s (%.1fs, #%02x%02x%02x)", out_path.name, duration, r, g, b)


def _stub_audio(asset: dict, out_path: Path) -> None:
    """
    Silent (or soft-tone for music) MP3 matching the asset's sync window.
    Reads v3 syncPoints.timelineInSec / timelineOutSec.
    """
    sync = asset.get("syncPoints") or {}
    t_in  = float(sync.get("timelineInSec",  0))
    t_out = float(sync.get("timelineOutSec", t_in + 5))
    duration = max(t_out - t_in, 0.5)
    audio_type = asset.get("audioType") or "ambient"

    if audio_type == "music":
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=60:duration={duration}",
            "-af", "volume=0.06",
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_path),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(duration),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_path),
        ]

    subprocess.run(cmd, check=True, capture_output=True)
    log.debug("stub audio → %s (%.1fs, type=%s)", out_path.name, duration, audio_type)


# ── real generators ───────────────────────────────────────────────────────────

def _runway_generate_shot(shot: dict, api_key: str, out_path: Path) -> None:
    """Generate a video clip via Runway Gen4 REST API."""
    import requests  # noqa: PLC0415

    steps = shot.get("generation", {}).get("steps") or [{}]
    prompt = steps[0].get("prompt") or shot.get("purpose") or "cinematic shot"
    duration = int(shot.get("targetDurationSec", 5))

    payload = {
        "promptText": prompt,
        "model": "gen4_turbo",
        "duration": min(duration, 10),
        "ratio": "1280:768",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(
        "https://api.dev.runwayml.com/v1/image_to_video",
        json=payload, headers=headers, timeout=30,
    )
    resp.raise_for_status()
    task_id = resp.json()["id"]

    for _ in range(120):
        time.sleep(5)
        poll = requests.get(
            f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
            headers=headers, timeout=10,
        )
        poll.raise_for_status()
        data = poll.json()
        status = data.get("status")
        if status == "SUCCEEDED":
            video_url = data["output"][0]
            break
        if status == "FAILED":
            raise RuntimeError(f"Runway task {task_id} failed: {data.get('failure')}")
    else:
        raise TimeoutError(f"Runway task {task_id} timed out")

    video_resp = requests.get(video_url, timeout=120)
    video_resp.raise_for_status()
    out_path.write_bytes(video_resp.content)
    log.info("runway → %s", out_path.name)


def _veo_generate_shot(shot: dict, api_key: str, out_path: Path) -> None:
    """Generate a video clip via Google Veo 3.1 (Gemini API)."""
    from google import genai  # noqa: PLC0415
    from google.genai import types  # noqa: PLC0415

    steps = shot.get("generation", {}).get("steps") or [{}]
    prompt = steps[0].get("prompt") or shot.get("purpose") or "cinematic shot"

    client = genai.Client(api_key=api_key)

    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio="16:9",
        ),
    )

    # Poll until complete (max ~10 min)
    for _ in range(120):
        time.sleep(5)
        operation = client.operations.get(operation)
        if operation.done:
            break
    else:
        raise TimeoutError("Veo 3.1 video generation timed out")

    if not operation.response or not operation.response.generated_videos:
        raise RuntimeError("Veo 3.1 returned no video")

    video = operation.response.generated_videos[0].video
    out_path.write_bytes(video.video_bytes)
    log.info("veo 3.1 → %s", out_path.name)


def _elevenlabs_generate_audio(asset: dict, api_key: str, out_path: Path) -> None:
    """Generate speech via ElevenLabs TTS."""
    import requests  # noqa: PLC0415

    steps = asset.get("generation", {}).get("steps") or [{}]
    text = asset.get("transcript") or steps[0].get("prompt") or ""
    if not text:
        _stub_audio(asset, out_path)
        return

    gen = steps[0] if steps else {}
    voice_id = gen.get("voiceId") or "21m00Tcm4TlvDq8ikWAM"
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.75, "similarity_boost": 0.85},
    }
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        json=payload,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    out_path.write_bytes(resp.content)
    log.info("elevenlabs → %s", out_path.name)


def _suno_generate_music(asset: dict, cookie: str, out_path: Path) -> None:
    """Generate music via Suno unofficial API."""
    import requests  # noqa: PLC0415

    steps = asset.get("generation", {}).get("steps") or [{}]
    prompt = steps[0].get("prompt") or "cinematic ambient instrumental"
    sync = asset.get("syncPoints") or {}
    duration = float(sync.get("timelineOutSec", 60)) - float(sync.get("timelineInSec", 0))

    headers = {"Cookie": cookie, "Content-Type": "application/json"}
    payload = {"prompt": prompt, "make_instrumental": True, "wait_audio": True}

    resp = requests.post(
        "https://studio-api.suno.ai/api/generate/v2/",
        json=payload, headers=headers, timeout=120,
    )
    resp.raise_for_status()
    clips = resp.json().get("clips") or []
    if not clips:
        raise ValueError("Suno returned no clips")

    audio_url = clips[0].get("audio_url")
    audio_resp = requests.get(audio_url, timeout=60)
    audio_resp.raise_for_status()
    out_path.write_bytes(audio_resp.content)
    log.info("suno → %s", out_path.name)


# ── public API ────────────────────────────────────────────────────────────────

def generate_shots(instance: dict, output_dir: Path) -> dict[str, Path]:
    """
    Generate (or stub) one video clip per shot.

    Returns {shot_logical_id: path_to_clip}.
    """
    shots_dir = output_dir / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    runway_key = os.getenv("RUNWAY_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    all_shots = _shots_in_order(instance)

    if not all_shots:
        log.warning("generate_shots: no shots found in instance — nothing to generate")
        return {}

    results: dict[str, Path] = {}
    errors: list[str] = []

    def _process(shot: dict) -> tuple[str, Path]:
        sid = _shot_id(shot)
        out_path = shots_dir / f"{sid}.mp4"
        if out_path.exists():
            log.debug("cache hit: %s", out_path.name)
            return sid, out_path
        # Try Runway first
        if runway_key:
            try:
                _runway_generate_shot(shot, runway_key, out_path)
                return sid, out_path
            except Exception as exc:
                log.warning("Runway failed for %s (%s) — trying Veo fallback", sid, exc)
        # Try Veo 3.1 as fallback
        if gemini_key and "REPLACE_ME" not in gemini_key:
            try:
                _veo_generate_shot(shot, gemini_key, out_path)
                return sid, out_path
            except Exception as exc:
                log.warning("Veo 3.1 failed for %s (%s) — falling back to stub", sid, exc)
        _stub_shot_video(shot, out_path)
        return sid, out_path

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_process, s): _shot_id(s) for s in all_shots}
        for fut in as_completed(futures):
            try:
                sid, path = fut.result()
                results[sid] = path
                log.info("[shot] %-52s → %s", sid, path.name)
            except Exception as exc:
                errors.append(f"{futures[fut]}: {exc}")

    if errors:
        log.warning("%d shot generation error(s):\n  %s", len(errors), "\n  ".join(errors))

    return results


def generate_audio(instance: dict, output_dir: Path) -> dict[str, Path]:
    """
    Generate (or stub) one audio file per audioAsset.

    Returns {asset_logical_id: path_to_file}.
    Reads from instance["assetLibrary"]["audioAssets"] (v3).
    """
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    suno_cookie = os.getenv("SUNO_COOKIE")

    audio_assets: list[dict] = (
        instance.get("assetLibrary", {}).get("audioAssets") or []
    )
    results: dict[str, Path] = {}

    def _asset_id(asset: dict) -> str:
        return asset.get("logicalId") or asset.get("id") or "unknown-audio"

    def _process(asset: dict) -> tuple[str, Path]:
        key = _asset_id(asset)
        out_path = audio_dir / f"{key}.mp3"
        if out_path.exists():
            log.debug("cache hit: %s", out_path.name)
            return key, out_path

        steps = asset.get("generation", {}).get("steps") or [{}]
        tool = steps[0].get("tool") or "stub"
        atype = asset.get("audioType") or "ambient"

        if tool == "elevenlabs" and elevenlabs_key and asset.get("transcript"):
            try:
                _elevenlabs_generate_audio(asset, elevenlabs_key, out_path)
                return key, out_path
            except Exception as exc:
                log.warning("ElevenLabs failed for %s (%s) — stub", key, exc)

        if tool == "suno" and suno_cookie and atype == "music":
            try:
                _suno_generate_music(asset, suno_cookie, out_path)
                return key, out_path
            except Exception as exc:
                log.warning("Suno failed for %s (%s) — stub", key, exc)

        _stub_audio(asset, out_path)
        return key, out_path

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_process, a): _asset_id(a) for a in audio_assets}
        for fut in as_completed(futures):
            key, path = fut.result()
            results[key] = path
            log.info("[audio] %-52s → %s", key, path.name)

    return results
