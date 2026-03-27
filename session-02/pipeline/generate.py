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
    # Index shots by both id and logicalId so refs using either will match
    shots_index: dict[str, dict] = {}
    for s in production.get("shots", []):
        shots_index[s.get("id", "")] = s
        shots_index[s.get("logicalId", "")] = s

    scenes = sorted(
        production.get("scenes", []),
        key=lambda s: s.get("sceneNumber", 0),
    )

    ordered: list[dict] = []
    seen: set[str] = set()
    for scene in scenes:
        for ref in scene.get("shotRefs", []):
            ref_id = ref.get("id") or ref.get("logicalId") or ""
            if ref_id and ref_id not in seen:
                shot = shots_index.get(ref_id)
                if shot:
                    ordered.append(shot)
                    seen.add(ref_id)
                    # Also mark the other key as seen
                    seen.add(shot.get("id", ""))
                    seen.add(shot.get("logicalId", ""))

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
    """Generate a video clip via Runway Gen4.5 text-to-video REST API."""
    import requests  # noqa: PLC0415

    gen_params = shot.get("genParams") or {}
    prompt = gen_params.get("prompt") or shot.get("purpose") or "cinematic shot"
    duration = min(int(shot.get("targetDurationSec", 5)), 10)

    payload = {
        "promptText": prompt,
        "model": "gen4.5",
        "duration": duration,
        "ratio": "1280:720",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06",
    }
    resp = requests.post(
        "https://api.dev.runwayml.com/v1/text_to_video",
        json=payload, headers=headers, timeout=30,
    )
    resp.raise_for_status()
    task_id = resp.json()["id"]
    log.info("runway task %s started for %s", task_id, _shot_id(shot))

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
            artifacts = data.get("artifacts") or data.get("output") or []
            if isinstance(artifacts, list) and artifacts:
                video_url = artifacts[0] if isinstance(artifacts[0], str) else artifacts[0].get("url", "")
            else:
                raise RuntimeError(f"Runway task {task_id}: no artifacts in response")
            break
        if status == "FAILED":
            raise RuntimeError(f"Runway task {task_id} failed: {data.get('failure', data.get('error', 'unknown'))}")
    else:
        raise TimeoutError(f"Runway task {task_id} timed out after 10 minutes")

    video_resp = requests.get(video_url, timeout=120)
    video_resp.raise_for_status()
    out_path.write_bytes(video_resp.content)
    log.info("runway → %s (%d bytes)", out_path.name, len(video_resp.content))


def _veo_generate_shot(
    shot: dict,
    api_key: str,
    out_path: Path,
    *,
    enriched_prompt: str | None = None,
    reference_images: list[bytes] | None = None,
) -> None:
    """Generate a video clip via Google Veo 3.1 (Gemini API) with reference images."""
    import requests as _req  # noqa: PLC0415
    from google import genai  # noqa: PLC0415
    from google.genai import types  # noqa: PLC0415

    gen_params = shot.get("genParams") or {}
    prompt = enriched_prompt or gen_params.get("prompt") or shot.get("purpose") or "cinematic shot"

    client = genai.Client(api_key=api_key)

    # Build reference images for character/style consistency
    veo_refs: list[types.VideoGenerationReferenceImage] = []
    for i, img_bytes in enumerate(reference_images or []):
        if not img_bytes or len(img_bytes) < 100:
            continue  # skip stubs
        ref_type = types.VideoGenerationReferenceType.ASSET
        veo_refs.append(types.VideoGenerationReferenceImage(
            image=types.Image(image_bytes=img_bytes, mime_type="image/png"),
            reference_type=ref_type,
        ))
    # Veo supports max 3 reference images
    veo_refs = veo_refs[:3]

    config = types.GenerateVideosConfig(aspect_ratio="16:9")
    if veo_refs:
        config.reference_images = veo_refs
        log.info("veo 3.1: %d reference image(s) for %s", len(veo_refs), _shot_id(shot))

    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=prompt,
        config=config,
    )
    log.info("veo 3.1 task started for %s", _shot_id(shot))

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

    # Video data may be in video_bytes or behind a download URI
    if video.video_bytes:
        out_path.write_bytes(video.video_bytes)
    elif video.uri:
        # Gemini file URIs require the API key for auth
        download_url = video.uri
        if "generativelanguage.googleapis.com" in download_url:
            sep = "&" if "?" in download_url else "?"
            download_url = f"{download_url}{sep}key={api_key}"
        resp = _req.get(download_url, timeout=120, allow_redirects=True)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
    else:
        raise RuntimeError("Veo 3.1: no video_bytes or uri in response")

    log.info("veo 3.1 → %s (%d bytes)", out_path.name, out_path.stat().st_size)


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


# ── consistency layer ─────────────────────────────────────────────────────────

def _build_style_preamble(instance: dict) -> str:
    """
    Extract a consistent visual preamble from the instance's characters,
    environments, style guides, and director instructions.
    Prepended to every shot prompt so the video model maintains coherence.
    """
    parts: list[str] = []

    # Director style mandate
    di = (instance.get("canonicalDocuments") or {}).get("directorInstructions") or {}
    if di.get("visionStatement"):
        parts.append(f"Director vision: {di['visionStatement']}")
    if di.get("colorDirection"):
        parts.append(f"Color palette: {di['colorDirection']}")

    # Style guide
    for sg in (instance.get("production") or {}).get("styleGuides", []):
        gl = sg.get("guidelines") or {}
        if gl.get("adjectives"):
            parts.append(f"Visual style: {', '.join(gl['adjectives'])}")
        if gl.get("palette"):
            parts.append(f"Color references: {', '.join(gl['palette'])}")
        neg = sg.get("negativeStylePrompt")
        if neg:
            parts.append(f"AVOID: {neg}")

    # Character descriptions (canonical)
    for char in (instance.get("production") or {}).get("characters", []):
        desc = char.get("description", "")
        if desc:
            parts.append(f"Character {char.get('name', '?')}: {desc}")
        # Use canonicalPromptFragments if available
        for frag in char.get("canonicalPromptFragments", []):
            if frag.get("locked"):
                parts.append(f"  [locked] {frag['fragment']}")

    # Environment descriptions
    for env in (instance.get("production") or {}).get("environments", []):
        desc = env.get("description", "")
        if desc:
            parts.append(f"Setting: {desc}")

    return "\n".join(parts)


def _generate_reference_images(
    instance: dict, output_dir: Path
) -> dict[str, bytes]:
    """
    Generate canonical reference images for each character.
    Returns {character_logicalId: png_bytes}.
    Uses providers.generate_image() (DALL-E → Imagen → stub).
    """
    from pipeline.providers import generate_image  # noqa: PLC0415

    refs_dir = output_dir / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    preamble = _build_style_preamble(instance)
    characters = (instance.get("production") or {}).get("characters", [])
    ref_images: dict[str, bytes] = {}

    for char in characters:
        char_lid = char.get("logicalId") or char.get("id") or "unknown"
        ref_path = refs_dir / f"{char_lid}.png"

        # Use cached reference if available
        if ref_path.exists():
            ref_images[char_lid] = ref_path.read_bytes()
            log.info("[ref] cache hit: %s", ref_path.name)
            continue

        desc = char.get("description", "")
        name = char.get("name", "character")

        # Build a detailed character reference prompt
        prompt = (
            f"Full portrait reference sheet of {name}: {desc}. "
            f"Front-facing, neutral lighting, full body visible, clean background. "
            f"Photorealistic, cinematic, consistent with: {preamble[:500]}"
        )

        log.info("[ref] generating reference image for %s", name)
        img_bytes = generate_image(prompt, size="1024x1024", quality="hd")
        ref_path.write_bytes(img_bytes)
        ref_images[char_lid] = img_bytes
        log.info("[ref] %s → %s (%d bytes)", name, ref_path.name, len(img_bytes))

    return ref_images


def _enrich_prompt(shot: dict, instance: dict, preamble: str) -> str:
    """
    Build a consistency-enriched prompt for a shot by combining:
    - The style preamble (character/environment/color context)
    - The shot's specific generation prompt
    - Scene mood and shot type context
    """
    gen_params = shot.get("genParams") or {}
    base_prompt = gen_params.get("prompt") or shot.get("purpose") or "cinematic shot"

    # Get scene context
    scene_ref_id = (shot.get("sceneRef") or {}).get("id", "")
    scene_mood = ""
    for scene in (instance.get("production") or {}).get("scenes", []):
        if scene.get("id") == scene_ref_id or scene.get("logicalId") == scene_ref_id:
            scene_mood = scene.get("mood", "")
            break

    # Cinematic spec context
    spec = shot.get("cinematicSpec") or {}
    shot_type = spec.get("shotType", "")
    movement = spec.get("cameraMovement", "")
    angle = spec.get("cameraAngle", "")
    style_adj = ", ".join((spec.get("style") or {}).get("adjectives", []))

    # Build enriched prompt
    enriched_parts = [
        f"[GLOBAL STYLE CONTEXT]\n{preamble}",
        f"\n[SHOT SPECIFICATION]",
        f"Shot type: {shot_type}, Camera: {angle} angle, {movement} movement",
    ]
    if style_adj:
        enriched_parts.append(f"Shot mood: {style_adj}")
    if scene_mood:
        enriched_parts.append(f"Scene mood: {scene_mood}")
    enriched_parts.append(f"\n[GENERATION PROMPT]\n{base_prompt}")

    # Director's must-avoid as negative guidance
    di = (instance.get("canonicalDocuments") or {}).get("directorInstructions") or {}
    avoid = di.get("mustAvoid", [])
    if avoid:
        enriched_parts.append(f"\nDO NOT include: {', '.join(avoid)}")

    return "\n".join(enriched_parts)


# ── public API ────────────────────────────────────────────────────────────────

def generate_shots(instance: dict, output_dir: Path) -> dict[str, Path]:
    """
    Generate (or stub) one video clip per shot.

    Consistency pipeline:
      1. Generate canonical reference images for each character
      2. Build style preamble from instance context
      3. Enrich each shot prompt with character/environment/style context
      4. Pass reference images to video model for visual anchoring

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

    # ── Step 1: Generate reference images for consistency ─────────────────
    log.info("─── Reference image generation ─────────────────────────────")
    ref_images = _generate_reference_images(instance, output_dir)

    # ── Step 2: Build style preamble ──────────────────────────────────────
    preamble = _build_style_preamble(instance)
    log.info("Style preamble: %d chars", len(preamble))

    results: dict[str, Path] = {}
    errors: list[str] = []

    def _process(shot: dict) -> tuple[str, Path]:
        sid = _shot_id(shot)
        out_path = shots_dir / f"{sid}.mp4"
        if out_path.exists():
            log.debug("cache hit: %s", out_path.name)
            return sid, out_path

        # Enrich the prompt with full context
        enriched_prompt = _enrich_prompt(shot, instance, preamble)

        # Collect reference images for this shot's consistency anchors
        shot_refs: list[bytes] = []
        anchors = (shot.get("genParams") or {}).get("consistencyAnchors", [])
        for anchor in anchors:
            ref_id = (anchor.get("ref") or {}).get("id", "")
            # Map character ref IDs to their reference images
            for char in (instance.get("production") or {}).get("characters", []):
                if char.get("id") == ref_id or char.get("logicalId") == ref_id:
                    char_lid = char.get("logicalId") or char.get("id")
                    if char_lid in ref_images:
                        shot_refs.append(ref_images[char_lid])
        # If no explicit anchors but refs exist, use all refs
        if not shot_refs and ref_images:
            shot_refs = list(ref_images.values())

        # Try Runway first
        if runway_key:
            try:
                _runway_generate_shot(shot, runway_key, out_path)
                return sid, out_path
            except Exception as exc:
                log.warning("Runway failed for %s (%s) — trying Veo fallback", sid, exc)
        # Try Veo 3.1 with reference images
        if gemini_key and "REPLACE_ME" not in gemini_key:
            try:
                _veo_generate_shot(
                    shot, gemini_key, out_path,
                    enriched_prompt=enriched_prompt,
                    reference_images=shot_refs,
                )
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
        tool = steps[0].get("tool") or "auto"
        atype = asset.get("audioType") or "ambient"

        # ElevenLabs: use for dialogue/voice_over with transcript, or when explicitly requested
        use_elevenlabs = (
            elevenlabs_key and asset.get("transcript")
            and (tool in ("elevenlabs", "auto") and atype in ("dialogue", "voice_over"))
        )
        if use_elevenlabs:
            try:
                _elevenlabs_generate_audio(asset, elevenlabs_key, out_path)
                return key, out_path
            except Exception as exc:
                log.warning("ElevenLabs failed for %s (%s) — stub", key, exc)

        if (tool in ("suno", "auto")) and suno_cookie and atype == "music":
            try:
                _suno_generate_music(asset, suno_cookie, out_path)
                return key, out_path
            except Exception as exc:
                log.warning("Suno failed for %s (%s) — trying ElevenLabs", key, exc)

        # ElevenLabs: SFX / ambient
        if elevenlabs_key and tool in ("elevenlabs", "auto") and atype in ("sfx", "ambient"):
            prompt = steps[0].get("prompt") or asset.get("description") or atype
            duration = asset.get("durationSec")
            try:
                from . import providers
                data = providers.generate_sound_effect(prompt, duration_seconds=duration)
                if data:
                    out_path.write_bytes(data)
                    log.info("[audio] ElevenLabs SFX ✓  %s", key)
                    return key, out_path
            except Exception as exc:
                log.warning("ElevenLabs SFX failed for %s (%s) — stub", key, exc)

        # ElevenLabs: music (fallback when Suno unavailable)
        if elevenlabs_key and tool in ("elevenlabs", "suno", "auto") and atype == "music":
            prompt = steps[0].get("prompt") or asset.get("description") or "cinematic score"
            duration = asset.get("durationSec") or 30
            try:
                from . import providers
                data = providers.generate_music(prompt, duration_seconds=int(duration))
                if data:
                    out_path.write_bytes(data)
                    log.info("[audio] ElevenLabs Music ✓  %s", key)
                    return key, out_path
            except Exception as exc:
                log.warning("ElevenLabs Music failed for %s (%s) — stub", key, exc)

        _stub_audio(asset, out_path)
        return key, out_path

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_process, a): _asset_id(a) for a in audio_assets}
        for fut in as_completed(futures):
            key, path = fut.result()
            results[key] = path
            log.info("[audio] %-52s → %s", key, path.name)

    return results
