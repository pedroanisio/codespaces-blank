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
    log.debug("runway payload for %s: %s", _shot_id(shot), payload)
    resp = requests.post(
        "https://api.dev.runwayml.com/v1/text_to_video",
        json=payload, headers=headers, timeout=30,
    )
    if not resp.ok:
        log.error("runway %d for %s: %s", resp.status_code, _shot_id(shot), resp.text)
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


# ── temporal bridge helper ────────────────────────────────────────────────────

def _extract_last_frame(video_path: Path) -> bytes | None:
    """Extract the last frame of a video as PNG bytes for temporal bridging."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp = Path(f.name)
    try:
        # Get duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", str(video_path)],
            capture_output=True, text=True, timeout=5,
        )
        dur = float(probe.stdout.strip() or "5")
        # Seek to 0.5s before end and grab last frame
        seek = max(0, dur - 0.5)
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(seek), "-i", str(video_path),
             "-frames:v", "1", "-q:v", "2", str(tmp)],
            capture_output=True, check=True, timeout=10,
        )
        data = tmp.read_bytes()
        return data if len(data) > 100 else None
    except Exception:
        return None
    finally:
        tmp.unlink(missing_ok=True)


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


class ReferenceLibrary:
    """
    Holds all canonical reference images generated by the S13 protocol.

    Organized by entity type and ID so shots can pick the right refs:
      - character refs: front, three_quarter, full_body
      - environment plates: wide_plate, detail_plate (NO characters)
      - pov plates: per (character, environment) pair — character's eye-level view
      - prop refs: isolated render
    """

    def __init__(self) -> None:
        self.characters: dict[str, dict[str, bytes]] = {}   # {char_lid: {view: bytes}}
        self.environments: dict[str, dict[str, bytes]] = {}  # {env_lid: {view: bytes}}
        self.pov_plates: dict[str, bytes] = {}               # {"char_lid:env_lid": bytes}
        self.props: dict[str, dict[str, bytes]] = {}         # {prop_lid: {view: bytes}}

    def all_character_refs(self, char_lid: str) -> list[bytes]:
        return list(self.characters.get(char_lid, {}).values())

    def primary_character_ref(self, char_lid: str) -> bytes | None:
        views = self.characters.get(char_lid, {})
        return views.get("front") or next(iter(views.values()), None)

    def all_environment_refs(self, env_lid: str) -> list[bytes]:
        return list(self.environments.get(env_lid, {}).values())

    def pov_plate(self, char_lid: str, env_lid: str) -> bytes | None:
        return self.pov_plates.get(f"{char_lid}:{env_lid}")

    def primary_prop_ref(self, prop_lid: str) -> bytes | None:
        views = self.props.get(prop_lid, {})
        return views.get("front") or next(iter(views.values()), None)

    def all_prop_refs(self, prop_lid: str) -> list[bytes]:
        return list(self.props.get(prop_lid, {}).values())

    def all_refs_flat(self) -> list[bytes]:
        """All reference images as a flat list (characters first, then envs, then POVs, then props)."""
        out: list[bytes] = []
        for views in self.characters.values():
            out.extend(views.values())
        for views in self.environments.values():
            out.extend(views.values())
        out.extend(self.pov_plates.values())
        for views in self.props.values():
            out.extend(views.values())
        return out


# ── Character reference views (S13 Step 2) ───────────────────────────────────

_CHARACTER_VIEWS = [
    (
        "front",
        "SPRITE REFERENCE: Front-facing view of the character, neutral expression. "
        "Plain solid dark gray background (#222222). Character cleanly isolated like a game sprite. "
        "Head-to-waist framing. NO environment, NO scene elements behind the character. "
        "This is the PRIMARY identity anchor — face and features must be pixel-clear.",
    ),
    (
        "three_quarter",
        "SPRITE REFERENCE: Three-quarter (3/4) view of the character, characteristic expression. "
        "Plain solid dark gray background (#222222). Character cleanly isolated like a game sprite. "
        "Slightly turned to show facial depth and jaw/cheekbone profile. "
        "NO environment behind. Face must be IDENTICAL to the front-facing sprite.",
    ),
    (
        "full_body",
        "SPRITE REFERENCE: Full body standing pose, head-to-toe framing. "
        "Plain solid dark gray background (#222222). Character cleanly isolated like a game sprite. "
        "Neutral T-pose or relaxed stand. Full wardrobe and proportions visible. "
        "NO environment behind. Face and clothing IDENTICAL to the front-facing sprite.",
    ),
]

# ── Environment plate views (S13 Step 3) ─────────────────────────────────────

_ENVIRONMENT_VIEWS = [
    (
        "wide_plate",
        "BACKGROUND PLATE: Wide establishing shot of the EMPTY environment. "
        "Absolutely NO people, NO characters, NO human figures. "
        "Show the full spatial extent of the location — walls, ceiling, floor, lighting. "
        "This is a compositing background plate.",
    ),
    (
        "detail_plate",
        "BACKGROUND PLATE: Detail/atmosphere shot of the environment. "
        "NO people, NO characters. Focus on textures, lighting quality, "
        "architectural details, and mood. Close-up of the most distinctive element.",
    ),
]

# ── Prop reference views (S13 Step 4) ────────────────────────────────────────

_PROP_VIEWS = [
    (
        "front",
        "SPRITE REFERENCE: Front view of the object, cleanly isolated. "
        "Plain solid dark gray background (#222222). Object centered, fully visible. "
        "NO hands, NO people. Sharp focus on every detail.",
    ),
    (
        "three_quarter",
        "SPRITE REFERENCE: Three-quarter (3/4) angled view of the object. "
        "Plain solid dark gray background (#222222). Object cleanly isolated. "
        "Shows depth and dimensional detail. NO hands, NO people. "
        "Object appearance IDENTICAL to front view.",
    ),
]


def _generate_reference_images(
    instance: dict, output_dir: Path
) -> ReferenceLibrary:
    """
    Full S13 reference asset generation protocol.

    Generates canonical reference images for ALL production entities:
      - Characters: 3 views (front, 3/4, full body) — S13 Step 2
      - Environments: 2 plates (wide, detail) — NO characters — S13 Step 3
      - Props: 1 isolated render per significant prop — S13 Step 4

    All images are cached on disk. Returns a ReferenceLibrary.
    """
    from pipeline.providers import generate_image  # noqa: PLC0415

    refs_dir = output_dir / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    preamble = _build_style_preamble(instance)
    production = instance.get("production") or {}
    lib = ReferenceLibrary()

    # ── Derive lighting context from director instructions ───────────────
    di = (instance.get("canonicalDocuments") or {}).get("directorInstructions") or {}
    color_dir = di.get("colorDirection", "")
    lighting_hint = f"Lit with {color_dir} color cast." if color_dir else ""

    # ── S13 Step 2: Character sprite references (3 views each) ────────────
    for char in production.get("characters", []):
        char_lid = char.get("logicalId") or char.get("id") or "unknown"
        char_name = char.get("name", "character")
        char_desc = char.get("description", "")

        # Collect locked prompt fragments if available
        locked_frags = [
            f.get("fragment", "")
            for f in char.get("canonicalPromptFragments", [])
            if f.get("locked")
        ]
        identity_block = "; ".join(locked_frags) if locked_frags else char_desc

        lib.characters[char_lid] = {}
        for view_name, view_instruction in _CHARACTER_VIEWS:
            ref_path = refs_dir / f"{char_lid}.{view_name}.png"

            if ref_path.exists():
                lib.characters[char_lid][view_name] = ref_path.read_bytes()
                log.info("[ref] cache hit: %s", ref_path.name)
                continue

            prompt = (
                f"Character reference of {char_name}: {identity_block}. "
                f"{view_instruction} "
                f"{lighting_hint} "
                f"Photorealistic, cinematic."
            )

            log.info("[ref] generating %s/%s", char_name, view_name)
            img_bytes = generate_image(prompt, size="1024x1024", quality="hd")
            ref_path.write_bytes(img_bytes)
            lib.characters[char_lid][view_name] = img_bytes
            log.info("[ref] %s/%s → %s (%d bytes)", char_name, view_name, ref_path.name, len(img_bytes))

    # ── S13 Step 3: Environment plates (2 views, NO characters) ───────────
    for env in production.get("environments", []):
        env_lid = env.get("logicalId") or env.get("id") or "unknown"
        env_name = env.get("name", "environment")
        env_desc = env.get("description", "")

        lib.environments[env_lid] = {}
        for view_name, view_instruction in _ENVIRONMENT_VIEWS:
            ref_path = refs_dir / f"{env_lid}.{view_name}.png"

            if ref_path.exists():
                lib.environments[env_lid][view_name] = ref_path.read_bytes()
                log.info("[ref] cache hit: %s", ref_path.name)
                continue

            prompt = (
                f"Environment reference of {env_name}: {env_desc}. "
                f"{view_instruction} "
                f"Photorealistic, cinematic. Style: {preamble[:400]}"
            )

            log.info("[ref] generating %s/%s", env_name, view_name)
            img_bytes = generate_image(prompt, size="1024x1024", quality="hd")
            ref_path.write_bytes(img_bytes)
            lib.environments[env_lid][view_name] = img_bytes
            log.info("[ref] %s/%s → %s (%d bytes)", env_name, view_name, ref_path.name, len(img_bytes))

    # ── S13 Step 4: Prop sprite references (multi-angle, env lighting) ────
    # Find which environment each prop appears in via scenes
    prop_to_env: dict[str, dict] = {}
    for scene in production.get("scenes", []):
        env_ref_id = (scene.get("environmentRef") or {}).get("id", "")
        env = None
        for e in production.get("environments", []):
            if e.get("id") == env_ref_id or e.get("logicalId") == env_ref_id:
                env = e
                break
        if not env:
            continue
        for prop_ref in scene.get("propRefs", []):
            prop_id = prop_ref.get("id", "")
            for p in production.get("props", []):
                if p.get("id") == prop_id or p.get("logicalId") == prop_id:
                    p_lid = p.get("logicalId") or p.get("id")
                    if p_lid not in prop_to_env:
                        prop_to_env[p_lid] = env
                    break

    for prop in production.get("props", []):
        prop_lid = prop.get("logicalId") or prop.get("id") or "unknown"
        prop_name = prop.get("name", "prop")
        prop_desc = prop.get("description", "")

        # Build environment lighting context for the sprite
        env = prop_to_env.get(prop_lid)
        if env:
            env_light = f"Lit with the lighting of {env.get('name', 'environment')}: {env.get('description', '')[:150]}. "
        elif color_dir:
            env_light = f"Lit with {color_dir} color cast. "
        else:
            env_light = ""

        lib.props[prop_lid] = {}
        for view_name, view_instruction in _PROP_VIEWS:
            ref_path = refs_dir / f"{prop_lid}.{view_name}.png"

            if ref_path.exists():
                lib.props[prop_lid][view_name] = ref_path.read_bytes()
                log.info("[ref] cache hit: %s", ref_path.name)
                continue

            prompt = (
                f"Prop reference of {prop_name}: {prop_desc}. "
                f"{view_instruction} "
                f"{env_light}"
                f"Photorealistic, cinematic."
            )

            log.info("[ref] generating prop %s/%s", prop_name, view_name)
            img_bytes = generate_image(prompt, size="1024x1024", quality="hd")
            ref_path.write_bytes(img_bytes)
            lib.props[prop_lid][view_name] = img_bytes
            log.info("[ref] %s/%s → %s (%d bytes)", prop_name, view_name, ref_path.name, len(img_bytes))

    # ── S13 Step 3b: POV environment plates (per character × environment) ──
    # Find which characters appear in which environments via scenes
    char_env_pairs: list[tuple[dict, dict]] = []
    seen_pairs: set[str] = set()
    for scene in production.get("scenes", []):
        env_ref_id = (scene.get("environmentRef") or {}).get("id", "")
        env = None
        for e in production.get("environments", []):
            if e.get("id") == env_ref_id or e.get("logicalId") == env_ref_id:
                env = e
                break
        if not env:
            continue
        for char_ref in scene.get("characterRefs", []):
            char_id = char_ref.get("id", "")
            for c in production.get("characters", []):
                if c.get("id") == char_id or c.get("logicalId") == char_id:
                    pair_key = f"{c.get('logicalId', c.get('id'))}:{env.get('logicalId', env.get('id'))}"
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        char_env_pairs.append((c, env))
                    break

    for char, env in char_env_pairs:
        char_lid = char.get("logicalId") or char.get("id") or "unknown"
        env_lid = env.get("logicalId") or env.get("id") or "unknown"
        char_name = char.get("name", "character")
        env_name = env.get("name", "environment")
        env_desc = env.get("description", "")
        height_m = char.get("heightM", 1.7)
        eye_height = round(height_m * 0.94, 2)

        pov_key = f"{char_lid}:{env_lid}"
        ref_path = refs_dir / f"pov.{char_lid}.{env_lid}.png"

        if ref_path.exists():
            lib.pov_plates[pov_key] = ref_path.read_bytes()
            log.info("[ref] cache hit: %s", ref_path.name)
            continue

        prompt = (
            f"First-person POV shot from {char_name}'s perspective inside {env_name}: {env_desc}. "
            f"Camera at eye-level height ({eye_height}m from floor). "
            f"Subjective viewpoint — what {char_name} sees when looking around the space. "
            f"NO people visible, NO characters, NO human figures — this is a pure first-person view. "
            f"Show the environment's depth, lighting, and spatial relationships. "
            f"Photorealistic, cinematic. Style: {preamble[:400]}"
        )

        log.info("[ref] generating POV plate: %s in %s (eye height %.2fm)", char_name, env_name, eye_height)
        img_bytes = generate_image(prompt, size="1024x1024", quality="hd")
        ref_path.write_bytes(img_bytes)
        lib.pov_plates[pov_key] = img_bytes
        log.info("[ref] POV %s:%s → %s (%d bytes)", char_name, env_name, ref_path.name, len(img_bytes))

    # ── Summary ───────────────────────────────────────────────────────────
    total_chars = sum(len(v) for v in lib.characters.values())
    total_envs = sum(len(v) for v in lib.environments.values())
    total_povs = len(lib.pov_plates)
    total_props = sum(len(v) for v in lib.props.values())
    log.info(
        "[ref] S13 complete: %d character views, %d environment plates, %d POV plates, %d prop renders",
        total_chars, total_envs, total_povs, total_props,
    )

    return lib


def _enrich_prompt(shot: dict, instance: dict, preamble: str) -> str:
    """
    Build a consistency-enriched prompt for a shot by combining ALL protocol fields:
    - Style preamble (character/environment/color/director context)
    - Cinematic spec (shot type, angle, movement, focal length, palette)
    - Scene context (mood, timeOfDay, weather, environment description)
    - The shot's specific generation prompt
    - Director must-avoid as negative guidance
    """
    gen_params = shot.get("genParams") or {}
    base_prompt = gen_params.get("prompt") or shot.get("purpose") or "cinematic shot"

    # ── Scene context ─────────────────────────────────────────────────────
    scene_ref_id = (shot.get("sceneRef") or {}).get("id", "")
    scene_mood = ""
    scene_time_of_day = ""
    scene_weather = ""
    scene_env_desc = ""
    for scene in (instance.get("production") or {}).get("scenes", []):
        if scene.get("id") == scene_ref_id or scene.get("logicalId") == scene_ref_id:
            scene_mood = scene.get("mood", "")
            scene_time_of_day = scene.get("timeOfDay", "")
            scene_weather = scene.get("weather", "")
            # Resolve environment description
            env_ref = (scene.get("environmentRef") or {}).get("id", "")
            if env_ref:
                for env in (instance.get("production") or {}).get("environments", []):
                    if env.get("id") == env_ref or env.get("logicalId") == env_ref:
                        scene_env_desc = env.get("description", "")
                        break
            break

    # ── Cinematic spec ────────────────────────────────────────────────────
    spec = shot.get("cinematicSpec") or {}
    shot_type = spec.get("shotType", "")
    movement = spec.get("cameraMovement", "")
    angle = spec.get("cameraAngle", "")
    focal_mm = spec.get("focalLengthMm")
    style_adj = ", ".join((spec.get("style") or {}).get("adjectives", []))
    style_palette = ", ".join((spec.get("style") or {}).get("palette", []))

    # ── Resolve styleGuideRef ─────────────────────────────────────────────
    sg_ref_id = (spec.get("styleGuideRef") or {}).get("id", "")
    sg_extra = ""
    if sg_ref_id:
        for sg in (instance.get("production") or {}).get("styleGuides", []):
            if sg.get("id") == sg_ref_id or sg.get("logicalId") == sg_ref_id:
                gl = sg.get("guidelines") or {}
                sg_adj = gl.get("adjectives", [])
                sg_palette = gl.get("palette", [])
                sg_tex = gl.get("textureDescriptors", [])
                sg_cam = gl.get("cameraLanguage", "")
                parts = []
                if sg_adj:
                    parts.append(f"Style: {', '.join(sg_adj)}")
                if sg_palette:
                    parts.append(f"Palette: {', '.join(sg_palette)}")
                if sg_tex:
                    parts.append(f"Textures: {', '.join(sg_tex)}")
                if sg_cam:
                    parts.append(f"Camera language: {sg_cam}")
                neg = sg.get("negativeStylePrompt", "")
                if neg:
                    parts.append(f"AVOID: {neg}")
                sg_extra = "\n".join(parts)
                break

    # Map focal length to depth-of-field guidance
    dof_hint = ""
    if focal_mm:
        if focal_mm <= 28:
            dof_hint = "wide-angle lens, deep depth of field, expansive perspective"
        elif focal_mm <= 50:
            dof_hint = "standard lens, natural perspective"
        elif focal_mm <= 85:
            dof_hint = "portrait lens, shallow depth of field, subject isolation"
        else:
            dof_hint = "telephoto lens, very shallow depth of field, compressed perspective"

    # ── Build enriched prompt ─────────────────────────────────────────────
    enriched_parts = [
        f"[GLOBAL STYLE CONTEXT]\n{preamble}",
    ]

    # Scene environment
    if scene_env_desc:
        enriched_parts.append(f"\n[ENVIRONMENT]\n{scene_env_desc}")
    scene_ctx = []
    if scene_time_of_day:
        scene_ctx.append(f"Time: {scene_time_of_day}")
    if scene_weather:
        scene_ctx.append(f"Setting: {scene_weather}")
    if scene_mood:
        scene_ctx.append(f"Mood: {scene_mood}")
    if scene_ctx:
        enriched_parts.append(f"\n[SCENE CONTEXT]\n{', '.join(scene_ctx)}")

    # Camera specification
    cam_parts = [f"Shot type: {shot_type}"]
    if angle:
        cam_parts.append(f"{angle} angle")
    if movement:
        cam_parts.append(f"{movement} movement")
    if focal_mm:
        cam_parts.append(f"{focal_mm}mm lens")
    if dof_hint:
        cam_parts.append(dof_hint)
    enriched_parts.append(f"\n[CAMERA]\n{', '.join(cam_parts)}")

    if style_adj:
        enriched_parts.append(f"Visual feel: {style_adj}")
    if style_palette:
        enriched_parts.append(f"Color palette: {style_palette}")

    # Style guide overrides (per-shot via styleGuideRef)
    if sg_extra:
        enriched_parts.append(f"\n[STYLE GUIDE]\n{sg_extra}")

    # Temporal bridge — continuity from previous shot
    bridge_ref = (spec.get("temporalBridgeAnchorRef") or {}).get("id", "")
    if bridge_ref:
        enriched_parts.append(
            f"\n[CONTINUITY] This shot must visually continue from shot {bridge_ref}. "
            f"Maintain the same lighting, color temperature, and spatial orientation."
        )

    # Consistency anchors with lock level context
    anchors = (shot.get("genParams") or {}).get("consistencyAnchors", [])
    if anchors:
        anchor_descs = []
        for anc in anchors:
            level = anc.get("lockLevel", "medium")
            name = anc.get("name", "")
            atype = anc.get("anchorType", "")
            strength = {"hard": "STRICTLY", "medium": "closely", "soft": "loosely"}.get(level, "closely")
            anchor_descs.append(f"  - {strength} match {atype}: {name}")
        enriched_parts.append(f"\n[CONSISTENCY REQUIREMENTS]\n" + "\n".join(anchor_descs))

    # ── Dialogue cues — tell the video model when a character is speaking ──
    shot_start = float((shot.get("plannedPosition") or {}).get("startSec", 0))
    shot_end = float((shot.get("plannedPosition") or {}).get("endSec", shot_start + float(shot.get("targetDurationSec", 5))))
    dialogue_cues: list[str] = []
    timelines = (instance.get("assembly") or {}).get("timelines") or []
    tl = timelines[0] if timelines else {}
    for ac in tl.get("audioClips") or []:
        ac_start = float(ac.get("timelineStartSec", 0))
        ac_dur = float(ac.get("durationSec", 0))
        ac_end = ac_start + ac_dur
        # Check if this audio clip overlaps with this shot's time window
        if ac_end <= shot_start or ac_start >= shot_end:
            continue
        src_id = (ac.get("sourceRef") or {}).get("id", "")
        # Find the audio asset to check if it's dialogue
        for aa in (instance.get("assetLibrary") or {}).get("audioAssets") or []:
            if aa.get("id") == src_id or aa.get("logicalId") == src_id:
                if aa.get("audioType") in ("dialogue", "voice_over"):
                    speaker_ref = (aa.get("characterRef") or {}).get("id", "")
                    speaker_name = ""
                    for ch in (instance.get("production") or {}).get("characters") or []:
                        if ch.get("id") == speaker_ref or ch.get("logicalId") == speaker_ref:
                            speaker_name = ch.get("name", "")
                            break
                    transcript = aa.get("transcript", "")
                    offset = max(0, ac_start - shot_start)
                    cue = f'{speaker_name or "Character"} speaks'
                    if transcript:
                        cue += f': "{transcript}"'
                    cue += f" (at {offset:.1f}s into this shot)"
                    dialogue_cues.append(cue)
                break
    if dialogue_cues:
        enriched_parts.append(
            f"\n[DIALOGUE — character must be visibly speaking]\n" + "\n".join(dialogue_cues)
        )

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

    # ── Step 1: Full S13 reference generation ────────────────────────────
    log.info("─── S13: Reference image generation ─────────────────────────")
    ref_lib = _generate_reference_images(instance, output_dir)

    # ── Step 2: Build style preamble ──────────────────────────────────────
    preamble = _build_style_preamble(instance)
    log.info("Style preamble: %d chars", len(preamble))

    # Build entity index for quick lookups
    production = instance.get("production") or {}
    entity_index: dict[str, dict] = {}
    for entity_list in ("characters", "environments", "props"):
        for e in production.get(entity_list, []):
            entity_index[e.get("id", "")] = e
            entity_index[e.get("logicalId", "")] = e

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

        # ── Collect reference images per S13 protocol ─────────────────────
        # Priority: hard anchors first, then medium, then soft
        # Veo accepts max 3 refs, so we pick the most important
        ref_candidates: list[tuple[int, bytes]] = []  # (priority, bytes)
        lock_priority = {"hard": 0, "medium": 1, "soft": 2}

        # A) From explicit consistency anchors on the shot
        anchors = (shot.get("genParams") or {}).get("consistencyAnchors", [])
        for anchor in anchors:
            ref_id = (anchor.get("ref") or {}).get("id", "")
            level = anchor.get("lockLevel", "medium")
            prio = lock_priority.get(level, 1)
            entity = entity_index.get(ref_id, {})
            entity_type = entity.get("entityType", "")
            entity_lid = entity.get("logicalId") or entity.get("id", "")

            if entity_type == "character":
                # Use primary (front) character ref — highest consistency value
                primary = ref_lib.primary_character_ref(entity_lid)
                if primary:
                    ref_candidates.append((prio, primary))
            elif entity_type == "environment":
                plate = next(iter(ref_lib.all_environment_refs(entity_lid)), None)
                if plate:
                    ref_candidates.append((prio + 1, plate))
            elif entity_type == "prop":
                prop_ref = ref_lib.primary_prop_ref(entity_lid)
                if prop_ref:
                    ref_candidates.append((prio + 1, prop_ref))

        # B) From the shot's scene → environment + POV plates
        scene_ref_id = (shot.get("sceneRef") or {}).get("id", "")
        scene = entity_index.get(scene_ref_id) or {}
        if scene.get("entityType") == "scene":
            env_ref_id = (scene.get("environmentRef") or {}).get("id", "")
            env = entity_index.get(env_ref_id, {})
            env_lid = env.get("logicalId") or env.get("id", "")

            # Add environment wide plate
            if env_lid and env_lid in ref_lib.environments:
                wide = ref_lib.environments[env_lid].get("wide_plate")
                if wide:
                    ref_candidates.append((2, wide))

            # Add POV plate for character-in-environment (if shot has character)
            shot_type = (shot.get("cinematicSpec") or {}).get("shotType", "")
            for char_ref in scene.get("characterRefs", []):
                char_id = char_ref.get("id", "")
                char = entity_index.get(char_id, {})
                char_lid = char.get("logicalId") or char.get("id", "")
                if char_lid and env_lid:
                    pov = ref_lib.pov_plate(char_lid, env_lid)
                    if pov:
                        # POV plates are higher priority for POV shots
                        pov_prio = 0 if shot_type.upper() == "POV" else 2
                        ref_candidates.append((pov_prio, pov))

            # C) Props referenced by the scene
            for prop_ref in scene.get("propRefs", []):
                prop_id = prop_ref.get("id", "")
                prop = entity_index.get(prop_id, {})
                prop_lid = prop.get("logicalId") or prop.get("id", "")
                if prop_lid in ref_lib.props:
                    p_front = ref_lib.primary_prop_ref(prop_lid)
                    if p_front:
                        ref_candidates.append((2, p_front))

        # D) If no explicit refs, use all character fronts + environment wide plate
        if not ref_candidates:
            for char_lid, views in ref_lib.characters.items():
                if "front" in views:
                    ref_candidates.append((0, views["front"]))
            for env_lid, views in ref_lib.environments.items():
                if "wide_plate" in views:
                    ref_candidates.append((2, views["wide_plate"]))

        # Sort by priority (hard=0 first), deduplicate, take max 3
        ref_candidates.sort(key=lambda x: x[0])
        seen_ids: set[int] = set()
        ref_bytes: list[bytes] = []
        for _, data in ref_candidates:
            data_id = id(data)
            if data_id not in seen_ids:
                seen_ids.add(data_id)
                ref_bytes.append(data)
            if len(ref_bytes) >= 3:
                break

        # E) Temporal bridge: extract last frame from previous shot
        bridge_ref = ((shot.get("cinematicSpec") or {})
                      .get("temporalBridgeAnchorRef") or {}).get("id", "")
        if bridge_ref and len(ref_bytes) < 3:
            for prev_shot in all_shots:
                if prev_shot.get("id") == bridge_ref or prev_shot.get("logicalId") == bridge_ref:
                    prev_lid = _shot_id(prev_shot)
                    prev_clip = shots_dir / f"{prev_lid}.mp4"
                    if prev_clip.exists():
                        try:
                            frame_bytes = _extract_last_frame(prev_clip)
                            if frame_bytes:
                                ref_bytes.append(frame_bytes)
                                log.info("temporal bridge: %s → %s", bridge_ref, sid)
                        except Exception as exc:
                            log.debug("temporal bridge extraction failed: %s", exc)
                    break

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
                    reference_images=ref_bytes,
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
            prompt = steps[0].get("prompt") or asset.get("description") or asset.get("name") or atype
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
            prompt = steps[0].get("prompt") or asset.get("description") or asset.get("mood") or asset.get("name") or "cinematic score"
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
