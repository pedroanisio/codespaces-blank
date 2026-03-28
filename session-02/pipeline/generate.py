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

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)


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
    log.debug("stub_video_created", file=out_path.name, duration_s=round(duration, 1), color=f"#{r:02x}{g:02x}{b:02x}")


def _stub_audio(asset: dict, out_path: Path) -> None:
    """
    Silent (or soft-tone for music) MP3 matching the asset's sync window.
    Reads v3 syncPoints.timelineInSec / timelineOutSec.
    """
    raw_sync = asset.get("syncPoints")
    if isinstance(raw_sync, list) and raw_sync:
        # v3 format: array of SyncPoint objects with time.startSec / time.endSec
        first = raw_sync[0].get("time") or {} if isinstance(raw_sync[0], dict) else {}
        last = raw_sync[-1].get("time") or {} if isinstance(raw_sync[-1], dict) else {}
        t_in = float(first.get("startSec", 0))
        t_out = float(last.get("endSec", last.get("startSec", t_in + 5)))
    elif isinstance(raw_sync, dict):
        # v2 compat: single object with timelineInSec / timelineOutSec
        t_in = float(raw_sync.get("timelineInSec", 0))
        t_out = float(raw_sync.get("timelineOutSec", t_in + 5))
    else:
        t_in = 0
        t_out = 5
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
    log.debug("stub_audio_created", file=out_path.name, duration_s=round(duration, 1), audio_type=audio_type)


# ── real generators ───────────────────────────────────────────────────────────

# ── provider constraints ──────────────────────────────────────────────────────

# Each provider's hard constraints for video generation.
# Used by _pick_video_provider() to route shots without trial-and-error.
_VIDEO_PROVIDER_CONSTRAINTS = {
    "runway": {
        "min_duration_sec": 2,
        "max_duration_sec": 10,
        "max_prompt_chars": 1000,
        "supports_reference_images": False,
        "supported_ratios": ["1280:720", "720:1280", "1280:768"],
    },
    "veo": {
        "min_duration_sec": 4,     # API rejects < 4
        "max_duration_sec": 8,
        "max_prompt_chars": 8000,
        "supports_reference_images": True,
        "max_reference_images": 3,
        "supported_ratios": ["16:9", "9:16", "1:1"],
    },
}


def _pick_video_provider(
    shot: dict,
    *,
    runway_key: str | None,
    gemini_key: str | None,
    reference_images: list[bytes] | None = None,
) -> list[str]:
    """
    Return an ordered list of eligible providers for a given shot,
    based on provider constraints and shot requirements.

    Checks duration limits, reference image support, and API key availability.

    When the target duration is shorter than a provider's minimum, the provider
    is still eligible — it will generate at its minimum duration and the assembly
    stage will trim the clip to the target. A provider is only excluded if the
    target exceeds its maximum (can't generate enough content).

    Always includes "stub" as the final fallback.
    """
    duration = float(shot.get("targetDurationSec", 5))
    has_refs = bool(reference_images and any(len(b) > 100 for b in reference_images))
    candidates: list[str] = []

    # Runway — eligible if target ≤ max (will clamp up to min if needed)
    rc = _VIDEO_PROVIDER_CONSTRAINTS["runway"]
    if (runway_key and duration <= rc["max_duration_sec"]):
        candidates.append("runway")

    # Veo — eligible if target ≤ max (will clamp up to min if needed)
    vc = _VIDEO_PROVIDER_CONSTRAINTS["veo"]
    if (gemini_key and "REPLACE_ME" not in gemini_key
            and duration <= vc["max_duration_sec"]):
        # Prefer Veo when reference images are available and provider supports them
        if has_refs and vc["supports_reference_images"]:
            candidates.insert(0, "veo")
        else:
            candidates.append("veo")

    candidates.append("stub")

    log.debug(
        "video_provider_routing",
        shot_id=_shot_id(shot),
        duration=duration,
        has_refs=has_refs,
        providers=candidates,
    )
    return candidates


def _distill_prompt(prompt: str, max_chars: int, shot_id: str = "") -> str:
    """
    Distill a long enriched prompt into a concise version that fits within
    max_chars, using an LLM to preserve narrative intent rather than truncating.

    Falls back to smart truncation if no LLM is available.
    """
    if len(prompt) <= max_chars:
        return prompt

    # Try LLM distillation
    try:
        from pipeline.providers import _openai  # noqa: PLC0415
        client = _openai()
        if client:
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a video generation prompt distiller. "
                            f"Condense the following shot description into EXACTLY {max_chars - 50} characters or fewer. "
                            f"Keep: the specific ACTION (what happens), character appearance, camera angle/movement, lighting, mood. "
                            f"Drop: general style context, color hex codes, technical metadata, redundant descriptions. "
                            f"Output ONLY the condensed prompt, no explanation."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_chars // 3,
                temperature=0.3,
            )
            distilled = resp.choices[0].message.content.strip()
            if distilled and len(distilled) <= max_chars:
                log.info("prompt_distilled", shot_id=shot_id,
                         original_len=len(prompt), distilled_len=len(distilled))
                return distilled
            log.debug("prompt_distill_too_long", shot_id=shot_id, len=len(distilled))
    except Exception as exc:
        log.debug("prompt_distill_llm_failed", shot_id=shot_id, error=str(exc))

    # Fallback: structured truncation — keep the most important sections
    sections = prompt.split("\n\n")
    # Priority: [WHAT HAPPENS] > [CAMERA] > [CHARACTERS] > [FRAMING] > rest
    priority_keys = ["WHAT HAPPENS", "CAMERA", "CHARACTERS IN SHOT", "FRAMING", "CONTINUITY"]
    prioritized: list[str] = []
    remainder: list[str] = []
    for section in sections:
        if any(k in section for k in priority_keys):
            prioritized.append(section)
        else:
            remainder.append(section)

    result = "\n\n".join(prioritized)
    for section in remainder:
        if len(result) + len(section) + 2 <= max_chars:
            result = result + "\n\n" + section
        else:
            break

    log.info("prompt_truncated_smart", shot_id=shot_id,
             original_len=len(prompt), truncated_len=len(result[:max_chars]))
    return result[:max_chars]


def _runway_generate_shot(
    shot: dict,
    api_key: str,
    out_path: Path,
    *,
    enriched_prompt: str | None = None,
) -> None:
    """Generate a video clip via Runway Gen4.5 text-to-video REST API."""
    import requests  # noqa: PLC0415

    gen_params = shot.get("genParams") or {}
    rc = _VIDEO_PROVIDER_CONSTRAINTS["runway"]
    raw_prompt = enriched_prompt or gen_params.get("prompt") or shot.get("purpose") or "cinematic shot"
    # Distill prompt to fit Runway's limit (preserves narrative intent)
    prompt = _distill_prompt(raw_prompt, rc["max_prompt_chars"], shot_id=_shot_id(shot))
    duration = max(
        rc["min_duration_sec"],
        min(round(float(shot.get("targetDurationSec", 5))),
            rc["max_duration_sec"]),
    )

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
    log.debug("runway_payload", shot_id=_shot_id(shot), payload=payload)
    resp = requests.post(
        "https://api.dev.runwayml.com/v1/text_to_video",
        json=payload, headers=headers, timeout=30,
    )
    if not resp.ok:
        log.error("runway_request_failed", status_code=resp.status_code, shot_id=_shot_id(shot), response=resp.text)
        resp.raise_for_status()
    task_id = resp.json()["id"]
    log.info("runway_task_started", task_id=task_id, shot_id=_shot_id(shot))

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
    log.info("runway_video_downloaded", file=out_path.name, size_bytes=len(video_resp.content))


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
    vc = _VIDEO_PROVIDER_CONSTRAINTS["veo"]
    raw_prompt = enriched_prompt or gen_params.get("prompt") or shot.get("purpose") or "cinematic shot"
    prompt = _distill_prompt(raw_prompt, vc["max_prompt_chars"], shot_id=_shot_id(shot))

    # Clamp duration to Veo's supported range
    target_duration = float(shot.get("targetDurationSec", 5))
    duration = max(vc["min_duration_sec"], min(int(target_duration), vc["max_duration_sec"]))

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

    config = types.GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=1,
        duration_seconds=duration,
    )
    if veo_refs:
        config.reference_images = veo_refs
        log.info("veo_reference_images_attached", count=len(veo_refs), shot_id=_shot_id(shot))

    log.info("veo_request", shot_id=_shot_id(shot), duration=duration, prompt_len=len(prompt))
    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=prompt,
        config=config,
    )
    log.info("veo_task_started", shot_id=_shot_id(shot))

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

    log.info("veo_video_downloaded", file=out_path.name, size_bytes=out_path.stat().st_size)


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
    log.info("elevenlabs_audio_generated", file=out_path.name)


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
    log.info("suno_music_generated", file=out_path.name)


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
        "Character is ALONE — NO other objects, NO flowers, NO plants, NO props near or on the character. "
        "NO text, NO words, NO labels, NO writing on the character's body. "
        "Only render what is described in the character spec — do NOT add extra features. "
        "This is the PRIMARY identity anchor — body shape and features must be pixel-clear.",
    ),
    (
        "three_quarter",
        "SPRITE REFERENCE: Three-quarter (3/4) view of THE EXACT SAME character. "
        "Plain solid dark gray background (#222222). Character cleanly isolated like a game sprite. "
        "Slightly turned to show depth and profile. "
        "Character is ALONE — NO other objects, NO flowers, NO plants, NO props. "
        "NO text, NO words, NO labels, NO writing on the character's body. "
        "NO environment behind. Design IDENTICAL to the front-facing sprite.",
    ),
    (
        "full_body",
        "SPRITE REFERENCE: Full body standing pose, head-to-toe framing of THE EXACT SAME character. "
        "Plain solid dark gray background (#222222). Character cleanly isolated like a game sprite. "
        "Neutral relaxed stand. Full proportions visible from head to feet. "
        "Character is ALONE — NO other objects, NO flowers, NO plants, NO props. "
        "NO text, NO words, NO labels, NO writing on the character's body. "
        "NO environment behind. Design IDENTICAL to the front-facing sprite.",
    ),
]

# ── Environment plate views (S13 Step 3) ─────────────────────────────────────

_ENVIRONMENT_VIEWS = [
    (
        "wide_plate",
        "BACKGROUND PLATE: Wide establishing shot of the EMPTY environment. "
        "Absolutely NO people, NO characters, NO robots, NO human figures. "
        "NO vegetation, NO plants, NO flowers, NO organic matter — only the built/industrial environment. "
        "Show the full spatial extent of the location — structure, ground, sky, lighting. "
        "This is a compositing background plate for later character compositing.",
    ),
    (
        "detail_plate",
        "BACKGROUND PLATE: Detail/atmosphere shot of THE SAME environment as the wide plate. "
        "NO people, NO characters, NO robots. "
        "NO vegetation, NO plants, NO flowers, NO organic matter. "
        "Focus on textures, lighting quality, material details, and mood. "
        "Close-up of the most distinctive STRUCTURAL element (metal, stone, concrete — not organic).",
    ),
]

# ── Prop reference views (S13 Step 4) ────────────────────────────────────────

_PROP_VIEWS = [
    (
        "front",
        "SPRITE REFERENCE: Front view of the object, cleanly isolated. "
        "Plain solid dark gray background (#222222). Object centered, fully visible. "
        "Object is ALONE — NO hands, NO people, NO characters, NO other objects nearby. "
        "NO glowing lights, NO LEDs unless explicitly described in the prop spec. "
        "NO text, NO labels on the object. "
        "Sharp focus on every detail. Render ONLY what is described.",
    ),
    (
        "three_quarter",
        "SPRITE REFERENCE: Three-quarter (3/4) angled view of THE EXACT SAME object. "
        "Plain solid dark gray background (#222222). Object cleanly isolated. "
        "Shows depth and dimensional detail. "
        "Object is ALONE — NO hands, NO people, NO characters, NO environment behind. "
        "NO glowing lights, NO LEDs unless explicitly described. "
        "Object design, shape, color, and materials IDENTICAL to front view.",
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
      - Props: 2 views per significant prop — S13 Step 4
      - POV plates: 1 per character × environment pair

    Generation is parallelized in waves:
      Wave 1: All anchor views (first view per entity) — fully parallel
      Wave 2: All secondary views (using wave 1 anchors) — fully parallel
      Wave 3: Third views + POV plates — fully parallel

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

    # ── Pre-compute prop-to-environment mapping ──────────────────────────
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

    # ── Pre-compute character × environment pairs for POV plates ─────────
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

    # ── Initialize lib containers ────────────────────────────────────────
    for char in production.get("characters", []):
        lib.characters[char.get("logicalId") or char.get("id") or "unknown"] = {}
    for env in production.get("environments", []):
        lib.environments[env.get("logicalId") or env.get("id") or "unknown"] = {}
    for prop in production.get("props", []):
        lib.props[prop.get("logicalId") or prop.get("id") or "unknown"] = {}

    # ── Anchors: dict from entity_lid → bytes (set by wave 1) ────────────
    anchors: dict[str, bytes] = {}

    # ── Helper: generate or load a single reference image ────────────────
    def _gen_one(
        entity_type: str,
        entity_lid: str,
        entity_name: str,
        view_name: str,
        prompt: str,
        anchor_key: str | None = None,
    ) -> tuple[str, str, str, bytes]:
        """Returns (entity_type, entity_lid, view_name, img_bytes)."""
        ref_path = refs_dir / f"{entity_lid}.{view_name}.png"

        if ref_path.exists():
            cached = ref_path.read_bytes()
            log.info("ref_cache_hit", file=ref_path.name)
            return entity_type, entity_lid, view_name, cached

        anchor = anchors.get(anchor_key) if anchor_key else None
        if anchor:
            prompt += " Maintain exact same design, proportions, colors, and materials as the reference image."

        log_fn = log.info
        log_fn("ref_generating", entity=entity_name, view=view_name)
        img_bytes = generate_image(prompt, size="1024x1024", quality="hd", reference_image=anchor)
        ref_path.write_bytes(img_bytes)
        log_fn("ref_generated", entity=entity_name, view=view_name, file=ref_path.name, size_bytes=len(img_bytes))
        return entity_type, entity_lid, view_name, img_bytes

    def _run_wave(tasks: list, max_workers: int = 4) -> None:
        """Execute a list of (callable, args) in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(fn, *args): label for fn, args, label in tasks}
            for fut in as_completed(futures):
                try:
                    etype, elid, vname, img_bytes = fut.result()
                    if etype == "character":
                        lib.characters[elid][vname] = img_bytes
                    elif etype == "environment":
                        lib.environments[elid][vname] = img_bytes
                    elif etype == "prop":
                        lib.props[elid][vname] = img_bytes
                    elif etype == "pov":
                        lib.pov_plates[elid] = img_bytes
                    # Store as anchor for subsequent waves
                    if vname in ("front", "wide_plate") and elid not in anchors:
                        anchors[elid] = img_bytes
                except Exception as exc:
                    log.warning("ref_generation_failed", label=futures[fut], error=str(exc))

    # ── WAVE 1: All first/anchor views (fully parallel) ──────────────────
    wave1: list = []

    def _char_prompt(char: dict, view_instr: str) -> str:
        """Build a character reference prompt with identity, banned traits, and negative guidance."""
        name = char.get("name", "character")
        locked_frags = [f.get("fragment", "") for f in char.get("canonicalPromptFragments", []) if f.get("locked")]
        identity = "; ".join(locked_frags) if locked_frags else char.get("description", "")
        banned = char.get("bannedTraits", [])
        neg = f" DO NOT add: {', '.join(banned)}." if banned else ""
        return (
            f"Character reference of {name}: {identity}. "
            f"{view_instr} {lighting_hint} "
            f"Photorealistic, cinematic.{neg}"
        )

    for char in production.get("characters", []):
        lid = char.get("logicalId") or char.get("id") or "unknown"
        name = char.get("name", "character")
        view_name, view_instr = _CHARACTER_VIEWS[0]
        prompt = _char_prompt(char, view_instr)
        wave1.append((_gen_one, ("character", lid, name, view_name, prompt, None), f"char:{lid}:{view_name}"))

    for env in production.get("environments", []):
        lid = env.get("logicalId") or env.get("id") or "unknown"
        name = env.get("name", "environment")
        desc = env.get("description", "")
        view_name, view_instr = _ENVIRONMENT_VIEWS[0]
        prompt = f"Environment reference of {name}: {desc}. {view_instr} Photorealistic, cinematic. Style: {preamble[:400]}"
        wave1.append((_gen_one, ("environment", lid, name, view_name, prompt, None), f"env:{lid}:{view_name}"))

    for prop in production.get("props", []):
        lid = prop.get("logicalId") or prop.get("id") or "unknown"
        name = prop.get("name", "prop")
        desc = prop.get("description", "")
        env = prop_to_env.get(lid)
        if env:
            env_light = f"Lit with the lighting of {env.get('name', 'environment')}: {env.get('description', '')[:150]}. "
        elif color_dir:
            env_light = f"Lit with {color_dir} color cast. "
        else:
            env_light = ""
        view_name, view_instr = _PROP_VIEWS[0]
        prompt = f"Prop reference of {name}: {desc}. {view_instr} {env_light}Photorealistic, cinematic."
        wave1.append((_gen_one, ("prop", lid, name, view_name, prompt, None), f"prop:{lid}:{view_name}"))

    log.info("ref_wave_1_start", tasks=len(wave1))
    _run_wave(wave1)
    log.info("ref_wave_1_complete", anchors=len(anchors))

    # ── WAVE 2: All secondary views (use wave 1 anchors) ────────────────
    wave2: list = []

    for char in production.get("characters", []):
        lid = char.get("logicalId") or char.get("id") or "unknown"
        name = char.get("name", "character")
        if len(_CHARACTER_VIEWS) > 1:
            view_name, view_instr = _CHARACTER_VIEWS[1]
            prompt = _char_prompt(char, view_instr)
            wave2.append((_gen_one, ("character", lid, name, view_name, prompt, lid), f"char:{lid}:{view_name}"))

    for env in production.get("environments", []):
        lid = env.get("logicalId") or env.get("id") or "unknown"
        name = env.get("name", "environment")
        desc = env.get("description", "")
        if len(_ENVIRONMENT_VIEWS) > 1:
            view_name, view_instr = _ENVIRONMENT_VIEWS[1]
            prompt = f"Environment reference of {name}: {desc}. {view_instr} Photorealistic, cinematic. Style: {preamble[:400]}"
            wave2.append((_gen_one, ("environment", lid, name, view_name, prompt, lid), f"env:{lid}:{view_name}"))

    for prop in production.get("props", []):
        lid = prop.get("logicalId") or prop.get("id") or "unknown"
        name = prop.get("name", "prop")
        desc = prop.get("description", "")
        env = prop_to_env.get(lid)
        if env:
            env_light = f"Lit with the lighting of {env.get('name', 'environment')}: {env.get('description', '')[:150]}. "
        elif color_dir:
            env_light = f"Lit with {color_dir} color cast. "
        else:
            env_light = ""
        if len(_PROP_VIEWS) > 1:
            view_name, view_instr = _PROP_VIEWS[1]
            prompt = f"Prop reference of {name}: {desc}. {view_instr} {env_light}Photorealistic, cinematic."
            wave2.append((_gen_one, ("prop", lid, name, view_name, prompt, lid), f"prop:{lid}:{view_name}"))

    log.info("ref_wave_2_start", tasks=len(wave2))
    _run_wave(wave2)
    log.info("ref_wave_2_complete")

    # ── WAVE 3: Third views (characters only) + POV plates ───────────────
    wave3: list = []

    for char in production.get("characters", []):
        lid = char.get("logicalId") or char.get("id") or "unknown"
        name = char.get("name", "character")
        if len(_CHARACTER_VIEWS) > 2:
            view_name, view_instr = _CHARACTER_VIEWS[2]
            prompt = _char_prompt(char, view_instr)
            wave3.append((_gen_one, ("character", lid, name, view_name, prompt, lid), f"char:{lid}:{view_name}"))

    for char, env in char_env_pairs:
        char_lid = char.get("logicalId") or char.get("id") or "unknown"
        env_lid = env.get("logicalId") or env.get("id") or "unknown"
        char_name = char.get("name", "character")
        env_name = env.get("name", "environment")
        env_desc = env.get("description", "")
        height_m = char.get("heightM", 1.7)
        eye_height = round(height_m * 0.94, 2)
        pov_key = f"{char_lid}:{env_lid}"
        prompt = (
            f"FIRST-PERSON CAMERA inside {env_name}: {env_desc}. "
            f"The camera IS at {eye_height}m height (the eye level of {char_name}). "
            f"This is a SUBJECTIVE shot — the camera is the character's eye. "
            f"Show ONLY what the character sees: the environment stretching out ahead. "
            f"The character is NOT visible — no robot, no body, no hands, no eyes in frame. "
            f"NO robot parts, NO mechanical elements in the foreground. "
            f"NO people, NO characters, NO figures of any kind. "
            f"Pure environment from a low vantage point. "
            f"Photorealistic, cinematic. Style: {preamble[:400]}"
        )

        # POV _gen_one wrapper — uses pov_key as entity_lid
        def _gen_pov(pov_key=pov_key, prompt=prompt, char_name=char_name, env_name=env_name, eye_height=eye_height):
            ref_path = refs_dir / f"pov.{pov_key.replace(':', '.')}.png"
            if ref_path.exists():
                cached = ref_path.read_bytes()
                log.info("ref_cache_hit", file=ref_path.name)
                return "pov", pov_key, "pov", cached
            log.info("ref_generating_pov_plate", character=char_name, environment=env_name, eye_height_m=eye_height)
            img_bytes = generate_image(prompt, size="1024x1024", quality="hd")
            ref_path.write_bytes(img_bytes)
            log.info("ref_pov_plate_generated", character=char_name, environment=env_name, file=ref_path.name, size_bytes=len(img_bytes))
            return "pov", pov_key, "pov", img_bytes

        wave3.append((_gen_pov, (), f"pov:{pov_key}"))

    if wave3:
        log.info("ref_wave_3_start", tasks=len(wave3))
        _run_wave(wave3)
        log.info("ref_wave_3_complete")

    # ── Summary ───────────────────────────────────────────────────────────
    total_chars = sum(len(v) for v in lib.characters.values())
    total_envs = sum(len(v) for v in lib.environments.values())
    total_povs = len(lib.pov_plates)
    total_props = sum(len(v) for v in lib.props.values())
    log.info(
        "ref_s13_complete",
        character_views=total_chars,
        environment_plates=total_envs,
        pov_plates=total_povs,
        prop_renders=total_props,
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
    shot_id = shot.get("id") or shot.get("logicalId") or ""

    # ── Resolve the shot's narrative action from script segments ──────────
    # This is the most important text for visual storytelling — it describes
    # what HAPPENS in the shot, not just its technical framing.
    action_description = ""
    script = (instance.get("canonicalDocuments") or {}).get("script") or {}
    for seg in script.get("segments", []):
        seg_shot_ref = (seg.get("shotRef") or {}).get("id", "")
        seg_scene_ref = (seg.get("sceneRef") or {}).get("id", "")
        # Match by shotRef first, then by sceneRef for action segments
        if seg_shot_ref == shot_id:
            action_description = seg.get("actionDescription") or seg.get("text") or ""
            break
    if not action_description:
        # Fall back: find script segments matching the shot's scene
        scene_ref_id_for_script = (shot.get("sceneRef") or {}).get("id", "")
        for seg in script.get("segments", []):
            seg_scene_ref = (seg.get("sceneRef") or {}).get("id", "")
            if (seg_scene_ref == scene_ref_id_for_script
                    and seg.get("segmentType") == "action"
                    and seg.get("actionDescription")):
                action_description = seg["actionDescription"]
                break

    # Build the narrative prompt from best available source.
    # When the script action covers the whole scene, prepend the shot's own
    # description to focus the model on this specific moment within the scene.
    shot_desc = shot.get("description") or ""
    if gen_params.get("prompt"):
        base_prompt = gen_params["prompt"]
    elif action_description and shot_desc:
        base_prompt = f"{shot_desc}\n\nFull scene action: {action_description}"
    elif action_description:
        base_prompt = action_description
    elif shot_desc:
        base_prompt = shot_desc
    else:
        base_prompt = shot.get("purpose") or "cinematic shot"

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

    # ── Scene continuity enforcement ─────────────────────────────────────
    # When multiple shots share the same scene, inject a hard constraint block
    # so the video model preserves identical lighting, environment, and objects.
    if scene_ref_id:
        sibling_shots: list[dict] = []
        for prod_shot in (instance.get("production") or {}).get("shots", []):
            sib_scene = (prod_shot.get("sceneRef") or {}).get("id", "")
            if sib_scene == scene_ref_id:
                sibling_shots.append(prod_shot)
        if len(sibling_shots) > 1:
            sib_descs = []
            for sib in sibling_shots:
                sib_id = sib.get("id") or sib.get("logicalId") or ""
                if sib_id == shot_id:
                    continue
                sib_desc = sib.get("description") or sib.get("name") or sib_id
                sib_type = (sib.get("cinematicSpec") or {}).get("shotType", "")
                sib_descs.append(f"  - {sib_id}: {sib_type} — {sib_desc}")
            continuity_block = (
                f"\n[SCENE CONTINUITY — CRITICAL]\n"
                f"This shot is one of {len(sibling_shots)} angles covering the SAME scene ({scene_ref_id}).\n"
                f"ALL shots in this scene MUST share IDENTICAL:\n"
                f"  - Lighting direction, intensity, and color temperature\n"
                f"  - Environment layout, set dressing, and background elements\n"
                f"  - Character costumes, positioning, and props present\n"
                f"  - Weather conditions and atmospheric effects\n"
                f"  - Color grading and overall tonal quality\n"
                f"Other shots in this scene:\n" + "\n".join(sib_descs) + "\n"
                f"Only the CAMERA ANGLE and FRAMING should differ between shots."
            )
            enriched_parts.append(continuity_block)

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

    # ── Character descriptions for characters in this shot ──────────────
    char_descs: list[str] = []
    for char_ref in shot.get("characterRefs", []):
        char_id = (char_ref.get("id") or "")
        for ch in (instance.get("production") or {}).get("characters", []):
            if ch.get("id") == char_id or ch.get("logicalId") == char_id:
                name = ch.get("name", "")
                appearance = ch.get("appearance", "")
                if name and appearance:
                    char_descs.append(f"{name}: {appearance}")
                elif name:
                    char_descs.append(f"{name}: {ch.get('description', '')}")
                break
    if char_descs:
        enriched_parts.append(f"\n[CHARACTERS IN SHOT]\n" + "\n".join(char_descs))

    # ── Framing and composition notes from cinematicSpec ──────────────────
    framing = spec.get("framing", "")
    composition = spec.get("compositionNotes", "")
    if framing:
        enriched_parts.append(f"\n[FRAMING]\n{framing}")
    if composition:
        enriched_parts.append(f"\n[COMPOSITION]\n{composition}")

    # ── Continuity notes ─────────────────────────────────────────────────
    continuity = shot.get("continuityNotes", "")
    if continuity:
        enriched_parts.append(f"\n[CONTINUITY NOTES]\n{continuity}")

    # ── The core narrative action — what happens in this shot ─────────────
    enriched_parts.append(f"\n[WHAT HAPPENS — GENERATE THIS]\n{base_prompt}")

    # Director's must-avoid as negative guidance
    di = (instance.get("canonicalDocuments") or {}).get("directorInstructions") or {}
    avoid = di.get("mustAvoid", [])
    if avoid:
        enriched_parts.append(f"\nDO NOT include: {', '.join(avoid)}")

    return "\n".join(enriched_parts)


# ── public API ────────────────────────────────────────────────────────────────

def generate_shots(
    instance: dict,
    output_dir: Path,
    *,
    scene_filter: str | None = None,
) -> dict[str, Path]:
    """
    Generate (or stub) one video clip per shot.

    Consistency pipeline:
      1. Generate canonical reference images for each character
      2. Build style preamble from instance context
      3. Enrich each shot prompt with character/environment/style context
      4. Pass reference images to video model for visual anchoring

    Parameters
    ----------
    scene_filter : If set, only generate shots belonging to this scene ID.

    Returns {shot_logical_id: path_to_clip}.
    """
    shots_dir = output_dir / "shots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    runway_key = os.getenv("RUNWAY_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    all_shots = _shots_in_order(instance)

    # Apply scene filter if specified
    if scene_filter:
        scene_shot_ids: set[str] = set()
        for scene in (instance.get("production") or {}).get("scenes") or []:
            scene_id = scene.get("id") or scene.get("logicalId") or ""
            if scene_id == scene_filter:
                for ref in scene.get("shotRefs") or []:
                    ref_id = ref.get("id") or ref.get("logicalId") or ""
                    if ref_id:
                        scene_shot_ids.add(ref_id)
                break
        all_shots = [s for s in all_shots
                     if (s.get("id") or "") in scene_shot_ids
                     or (s.get("logicalId") or "") in scene_shot_ids]
        log.info("scene_filter_applied", scene=scene_filter, shots=len(all_shots))

    if not all_shots:
        log.warning("generate_shots_empty", msg="no shots found in instance")
        return {}

    # ── Step 1: Full S13 reference generation ────────────────────────────
    log.info("s13_reference_generation_start")
    ref_lib = _generate_reference_images(instance, output_dir)

    # ── Step 2: Build style preamble ──────────────────────────────────────
    preamble = _build_style_preamble(instance)
    log.info("style_preamble_built", length_chars=len(preamble))

    # Build entity index for quick lookups
    production = instance.get("production") or {}
    entity_index: dict[str, dict] = {}
    for entity_list in ("characters", "environments", "props"):
        for e in production.get(entity_list, []):
            entity_index[e.get("id", "")] = e
            entity_index[e.get("logicalId", "")] = e

    # ── Scene-level consistency: build previous-shot map for auto bridges ─
    # Maps each shot ID to the previous shot ID in the same scene (by shotRefs order).
    # Also collects scene-level generation.consistencyAnchors for inheritance.
    _prev_shot_in_scene: dict[str, str] = {}  # shot_id → prev_shot_id
    _scene_anchors: dict[str, list] = {}       # scene_id → anchors list
    for scene in production.get("scenes", []):
        scene_id = scene.get("id") or scene.get("logicalId") or ""
        refs = scene.get("shotRefs", [])
        for i, ref in enumerate(refs):
            ref_id = ref.get("id") or ref.get("logicalId") or ""
            if i > 0:
                prev_id = refs[i - 1].get("id") or refs[i - 1].get("logicalId") or ""
                if ref_id and prev_id:
                    _prev_shot_in_scene[ref_id] = prev_id
        # Collect scene-level generation.consistencyAnchors
        scene_gen = scene.get("generation") or {}
        scene_cas = scene_gen.get("consistencyAnchors", [])
        if scene_cas and scene_id:
            _scene_anchors[scene_id] = scene_cas

    results: dict[str, Path] = {}
    errors: list[str] = []

    def _process(shot: dict) -> tuple[str, Path]:
        sid = _shot_id(shot)
        out_path = shots_dir / f"{sid}.mp4"
        if out_path.exists():
            log.debug("cache_hit", file=out_path.name)
            return sid, out_path

        # Enrich the prompt with full context
        enriched_prompt = _enrich_prompt(shot, instance, preamble)

        # ── Collect reference images per S13 protocol ─────────────────────
        # Priority: hard anchors first, then medium, then soft
        # Veo accepts max 3 refs, so we pick the most important
        ref_candidates: list[tuple[int, bytes]] = []  # (priority, bytes)
        lock_priority = {"hard": 0, "medium": 1, "soft": 2}

        # A) From explicit consistency anchors on the shot,
        #    merged with scene-level anchors (shot-level takes precedence).
        anchors = list((shot.get("genParams") or {}).get("consistencyAnchors", []))
        shot_scene_ref = (shot.get("sceneRef") or {}).get("id", "")
        if shot_scene_ref and shot_scene_ref in _scene_anchors:
            # Inherit scene-level anchors unless the shot already anchors that entity
            shot_anchor_refs = {
                (a.get("ref") or {}).get("id", "") for a in anchors
            }
            for sa in _scene_anchors[shot_scene_ref]:
                sa_ref = (sa.get("ref") or {}).get("id", "")
                if sa_ref not in shot_anchor_refs:
                    anchors.append(sa)
                    log.debug("scene_anchor_inherited", shot=sid, ref=sa_ref)
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

        # E) Temporal bridge: extract last frame from previous shot.
        #    Auto-infer bridge from scene order when not explicitly declared.
        bridge_ref = ((shot.get("cinematicSpec") or {})
                      .get("temporalBridgeAnchorRef") or {}).get("id", "")
        if not bridge_ref:
            shot_id_str = shot.get("id") or shot.get("logicalId") or ""
            bridge_ref = _prev_shot_in_scene.get(shot_id_str, "")
            if bridge_ref:
                log.debug("temporal_bridge_auto_inferred", shot=sid, from_shot=bridge_ref)
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
                                log.info("temporal_bridge_attached", from_shot=bridge_ref, to_shot=sid)
                        except Exception as exc:
                            log.debug("temporal_bridge_extraction_failed", error=str(exc))
                    break

        # Route to the best provider based on shot constraints
        providers = _pick_video_provider(
            shot,
            runway_key=runway_key,
            gemini_key=gemini_key,
            reference_images=ref_bytes,
        )
        for provider in providers:
            try:
                if provider == "runway":
                    _runway_generate_shot(shot, runway_key, out_path, enriched_prompt=enriched_prompt)
                    return sid, out_path
                elif provider == "veo":
                    _veo_generate_shot(
                        shot, gemini_key, out_path,
                        enriched_prompt=enriched_prompt,
                        reference_images=ref_bytes,
                    )
                    return sid, out_path
                elif provider == "stub":
                    _stub_shot_video(shot, out_path)
                    return sid, out_path
            except Exception as exc:
                remaining = providers[providers.index(provider) + 1:]
                log.warning(
                    "video_provider_failed",
                    shot_id=sid,
                    provider=provider,
                    error=str(exc),
                    fallback=remaining[0] if remaining else "none",
                )
                continue
        _stub_shot_video(shot, out_path)
        return sid, out_path

    # ── Generate shots SEQUENTIALLY in scene order ─────────────────────────
    # Each shot must complete before the next starts so that:
    #   1. The temporal bridge can extract the previous shot's last frame
    #   2. Visual continuity chains across cuts (same character, same lighting)
    # This is slower than parallel but produces coherent video.
    for shot in all_shots:
        try:
            sid, path = _process(shot)
            results[sid] = path
            log.info("shot_generated", shot_id=sid, file=path.name)
        except Exception as exc:
            errors.append(f"{_shot_id(shot)}: {exc}")
            log.warning("shot_generation_failed", shot_id=_shot_id(shot), error=str(exc))

    if errors:
        log.warning("shot_generation_errors", count=len(errors), details=errors)

    return results


def generate_audio(
    instance: dict,
    output_dir: Path,
    *,
    scene_filter: str | None = None,
) -> dict[str, Path]:
    """
    Generate (or stub) one audio file per audioAsset.

    Parameters
    ----------
    scene_filter : If set, only generate audio assets that overlap this scene's
                   time range on the master timeline.

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

    # Filter to only assets overlapping the target scene
    if scene_filter:
        from pipeline.scene_splitter import slice_audio_for_scene, _scene_time_ranges
        scene_ranges = _scene_time_ranges(instance)
        scene_start = scene_end = 0.0
        for scene, start, end in scene_ranges:
            scene_id = scene.get("id") or scene.get("logicalId") or ""
            if scene_id == scene_filter:
                scene_start, scene_end = start, end
                break
        slices = slice_audio_for_scene(scene_start, scene_end, instance)
        needed_ids = {s.audio_asset_id for s in slices}
        audio_assets = [a for a in audio_assets
                        if (a.get("id") or "") in needed_ids
                        or (a.get("logicalId") or "") in needed_ids]
        log.info("scene_filter_audio", scene=scene_filter, assets=len(audio_assets))
    results: dict[str, Path] = {}

    def _asset_id(asset: dict) -> str:
        return asset.get("logicalId") or asset.get("id") or "unknown-audio"

    def _process(asset: dict) -> tuple[str, Path]:
        key = _asset_id(asset)
        out_path = audio_dir / f"{key}.mp3"
        if out_path.exists():
            log.debug("cache_hit", file=out_path.name)
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
                log.warning("elevenlabs_failed_stub_fallback", asset_id=key, error=str(exc))

        if (tool in ("suno", "auto")) and suno_cookie and atype == "music":
            try:
                _suno_generate_music(asset, suno_cookie, out_path)
                return key, out_path
            except Exception as exc:
                log.warning("suno_failed_elevenlabs_fallback", asset_id=key, error=str(exc))

        # ElevenLabs: SFX / ambient
        if elevenlabs_key and tool in ("elevenlabs", "auto") and atype in ("sfx", "ambient"):
            prompt = steps[0].get("prompt") or asset.get("description") or asset.get("name") or atype
            duration = asset.get("durationSec")
            try:
                from . import providers
                data = providers.generate_sound_effect(prompt, duration_seconds=duration)
                if data:
                    out_path.write_bytes(data)
                    log.info("elevenlabs_sfx_generated", asset_id=key)
                    return key, out_path
            except Exception as exc:
                log.warning("elevenlabs_sfx_failed_stub_fallback", asset_id=key, error=str(exc))

        # ElevenLabs: music (fallback when Suno unavailable)
        if elevenlabs_key and tool in ("elevenlabs", "suno", "auto") and atype == "music":
            prompt = steps[0].get("prompt") or asset.get("description") or asset.get("mood") or asset.get("name") or "cinematic score"
            duration = asset.get("durationSec") or 30
            try:
                from . import providers
                data = providers.generate_music(prompt, duration_seconds=int(duration))
                if data:
                    out_path.write_bytes(data)
                    log.info("elevenlabs_music_generated", asset_id=key)
                    return key, out_path
            except Exception as exc:
                log.warning("elevenlabs_music_failed_stub_fallback", asset_id=key, error=str(exc))

        _stub_audio(asset, out_path)
        return key, out_path

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_process, a): _asset_id(a) for a in audio_assets}
        for fut in as_completed(futures):
            key, path = fut.result()
            results[key] = path
            log.info("audio_generated", asset_id=key, file=path.name)

    return results
