"""
generate.py — AI generation layer for the video production pipeline.

Two modes per asset type:
  STUB  (default)  — creates placeholder assets using MoviePy / Pillow / numpy.
                     No API keys required. Produces a fully runnable pipeline.
  REAL             — calls actual APIs when the matching env var is set:
                       RUNWAY_API_KEY     → Runway Gen4  (video shots)
                       ELEVENLABS_API_KEY → ElevenLabs   (dialogue / voice-over)
                       SUNO_COOKIE        → Suno         (music)
                       MIDJOURNEY_TOKEN   → Midjourney   (reference images, stub-only fallback)

Public API
----------
  generate_shots(instance, output_dir)  -> dict[shot_id, Path]
  generate_audio(instance, output_dir)  -> dict[audio_key, Path]
"""

from __future__ import annotations

import json
import logging
import math
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _shots_in_order(instance: dict) -> list[dict]:
    """Return all shots sorted by scene order then shot order."""
    scene_order = {
        sid: i
        for i, sid in enumerate(
            instance["outputs"][0].get(
                "scene_order",
                [s["scene_id"] for s in instance["scenes"]],
            )
        )
    }
    shots = []
    for scene in sorted(instance["scenes"], key=lambda s: scene_order.get(s["scene_id"], 0)):
        for shot in sorted(scene["shots"], key=lambda sh: sh.get("order", 0)):
            shots.append(shot)
    return shots


# ── stub generators ───────────────────────────────────────────────────────────

def _stub_shot_video(shot: dict, out_path: Path) -> None:
    """
    Produce a solid-colour MP4 clip whose colour comes from the shot's
    cinematic_spec.color_palette (first entry) and whose duration matches
    the schema. A white label is burned in via ffmpeg drawtext so every clip
    is visually distinct without requiring a font file.
    """
    duration = float(shot["duration_sec"])
    spec = shot.get("cinematic_spec", {})
    palette = spec.get("color_palette", ["#1a1a2e"])
    r, g, b = _hex_to_rgb(palette[0])

    label = shot.get("label", shot["shot_id"])[:50].replace(":", r"\:").replace("'", "")

    # 1. generate a raw solid-colour video with ffmpeg (fast, no Python deps)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={r:02x}{g:02x}{b:02x}:s=1920x1080:r=24:d={duration}",
        "-vf", f"drawtext=text='{label}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",
        "-an",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    log.debug("stub video → %s (%.1fs, #%02x%02x%02x)", out_path.name, duration, r, g, b)


def _stub_audio(audio_asset: dict, out_path: Path) -> None:
    """
    Produce a short silent MP3 whose length matches the asset's sync window.
    If audio_type is 'music', a soft 60 Hz tone is used instead of silence
    so the audio mixer has something to duck/fade.
    """
    sync = audio_asset.get("sync", {})
    duration = float(sync.get("timeline_out_sec", 5)) - float(sync.get("timeline_in_sec", 0))
    duration = max(0.5, duration)
    audio_type = audio_asset.get("type", "ambient")

    if audio_type == "music":
        freq = 60  # bass tone — distinct, not distracting
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency={freq}:duration={duration}",
            "-af", "volume=0.08",  # very quiet
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_path),
        ]
    else:
        # silence
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(duration),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_path),
        ]

    subprocess.run(cmd, check=True, capture_output=True)
    log.debug("stub audio → %s (%.1fs, type=%s)", out_path.name, duration, audio_type)


# ── real generators (Runway) ─────────────────────────────────────────────────

def _runway_generate_shot(shot: dict, api_key: str, out_path: Path) -> None:
    """
    Generate a video clip via Runway Gen4 REST API.

    Docs: https://docs.runwayml.com/reference/generate-video
    """
    import requests  # noqa: PLC0415

    gen = shot.get("gen_params", {})
    prompt = gen.get("prompt", shot.get("label", "cinematic shot"))
    duration = int(shot["duration_sec"])
    seed = gen.get("seed")

    payload = {
        "promptText": prompt,
        "model": gen.get("model_id", "gen4_turbo"),
        "duration": min(duration, 10),  # Gen4 max 10s per call
        "ratio": "1280:768",
    }
    if seed is not None:
        payload["seed"] = seed

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(
        "https://api.dev.runwayml.com/v1/image_to_video",
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    task_id = resp.json()["id"]

    # Poll until complete
    for _ in range(120):
        time.sleep(5)
        poll = requests.get(
            f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
            headers=headers,
            timeout=10,
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


# ── real generators (ElevenLabs) ─────────────────────────────────────────────

def _elevenlabs_generate_audio(audio_asset: dict, api_key: str, out_path: Path) -> None:
    """
    Generate speech / voice-over via ElevenLabs Text-to-Speech API.

    Docs: https://elevenlabs.io/docs/api-reference/text-to-speech
    """
    import requests  # noqa: PLC0415

    gen = audio_asset.get("gen_params", {})
    sg = gen.get("sound_generation", {})
    voice_id = sg.get("voice_id", "21m00Tcm4TlvDq8ikWAM")  # "Rachel" default
    text = audio_asset.get("transcript") or gen.get("prompt", "")
    if not text:
        _stub_audio(audio_asset, out_path)
        return

    payload = {
        "text": text,
        "model_id": gen.get("model_id", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": sg.get("voice_stability", 0.75),
            "similarity_boost": sg.get("voice_similarity", 0.85),
            "style": sg.get("voice_style", 0.0),
            "use_speaker_boost": sg.get("voice_use_speaker_boost", True),
        },
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


# ── real generators (Suno) ────────────────────────────────────────────────────

def _suno_generate_music(audio_asset: dict, cookie: str, out_path: Path) -> None:
    """
    Generate music via Suno unofficial API.

    Requires SUNO_COOKIE env var (your browser session cookie).
    Falls back to stub if cookie is empty.
    """
    import requests  # noqa: PLC0415

    gen = audio_asset.get("gen_params", {})
    prompt = gen.get("prompt", "cinematic ambient music, 60 seconds, instrumental")
    sync = audio_asset.get("sync", {})
    duration = float(sync.get("timeline_out_sec", 60)) - float(sync.get("timeline_in_sec", 0))

    headers = {"Cookie": cookie, "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "make_instrumental": True,
        "wait_audio": True,
    }

    resp = requests.post(
        "https://studio-api.suno.ai/api/generate/v2/",
        json=payload,
        headers=headers,
        timeout=120,
    )
    resp.raise_for_status()
    clips = resp.json().get("clips", [])
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

    Returns a mapping {shot_id: path_to_clip}.
    """
    shots_dir = output_dir / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    runway_key = os.getenv("RUNWAY_API_KEY")
    all_shots = _shots_in_order(instance)

    results: dict[str, Path] = {}
    errors: list[str] = []

    def _process(shot: dict) -> tuple[str, Path]:
        sid = shot["shot_id"]
        out_path = shots_dir / f"{sid}.mp4"
        if out_path.exists():
            log.debug("cache hit: %s", out_path.name)
            return sid, out_path
        if runway_key:
            try:
                _runway_generate_shot(shot, runway_key, out_path)
                return sid, out_path
            except Exception as exc:
                log.warning("Runway failed for %s (%s), falling back to stub", sid, exc)
        _stub_shot_video(shot, out_path)
        return sid, out_path

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_process, s): s["shot_id"] for s in all_shots}
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
    Generate (or stub) one audio file per audio_asset.

    Returns a mapping {audio_key: path_to_file}.
    """
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    suno_cookie = os.getenv("SUNO_COOKIE")

    audio_assets: dict[str, dict] = instance.get("audio_assets", {})
    results: dict[str, Path] = {}

    def _process(key: str, asset: dict) -> tuple[str, Path]:
        ext = "mp3"
        out_path = audio_dir / f"{key}.{ext}"
        if out_path.exists():
            log.debug("cache hit: %s", out_path.name)
            return key, out_path

        tool = asset.get("gen_params", {}).get("tool", "")
        atype = asset.get("type", "ambient")

        if tool == "elevenlabs" and elevenlabs_key and asset.get("transcript"):
            try:
                _elevenlabs_generate_audio(asset, elevenlabs_key, out_path)
                return key, out_path
            except Exception as exc:
                log.warning("ElevenLabs failed for %s (%s), falling back to stub", key, exc)

        if tool == "suno" and suno_cookie and atype == "music":
            try:
                _suno_generate_music(asset, suno_cookie, out_path)
                return key, out_path
            except Exception as exc:
                log.warning("Suno failed for %s (%s), falling back to stub", key, exc)

        _stub_audio(asset, out_path)
        return key, out_path

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_process, k, v): k for k, v in audio_assets.items()}
        for fut in as_completed(futures):
            key, path = fut.result()
            results[key] = path
            log.info("[audio] %-52s → %s", key, path.name)

    return results
