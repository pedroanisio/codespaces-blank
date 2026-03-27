"""
providers.py — Unified multi-provider AI layer.

Loads .env automatically. All providers degrade gracefully when keys are absent.

Env vars
--------
  ANTHROPIC_API_KEY   Claude Sonnet 4.6 (primary skill executor — text + JSON)
  OPENAI_API_KEY      GPT-4.1 (JSON/vision) · GPT-Image-1.5 · TTS-HD (voice)
  DEEPSEEK_API_KEY    DeepSeek V3.2 — OpenAI-compatible alternative text provider
  XAI_API_KEY         Grok 4 — text/JSON + Aurora image generation
  GEMINI_API_KEY      Gemini 2.5 Flash (text/JSON) + Imagen 4 (images)
  BRAVE_API_KEY       Brave Search — web + LLM context research
  ELEVENLABS_API_KEY  ElevenLabs — Eleven v3 TTS · SFX · Music generation
  DESCRIPT_API_KEY    Descript — transcription + AI editing (beta API)

Public API
----------
  complete_json(system, user, *, prefer, max_tokens)   → dict   (JSON from best LLM)
  generate_image(prompt, *, size, quality)              → bytes  (PNG)
  text_to_speech(text, *, voice, speed)                 → bytes  (MP3)
  vision_score(b64_a, b64_b)                            → float  (0-1 similarity)
  search_web(query, *, count)                           → list[dict]
  search_web_context(query, *, max_tokens)              → str    (LLM-optimised text)
  generate_sound_effect(prompt, *, duration_seconds)    → bytes  (MP3)
  generate_music(prompt, *, duration_seconds, instrumental) → bytes (MP3)
  descript_import_media(url, *, project_name)            → dict   (project + job info)
  descript_agent_edit(project_id, prompt)                 → dict   (job info)
  descript_job_status(job_id)                             → dict   (job status)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Any, Literal

# Load .env — search from most-specific (session dir) to least-specific (repo root).
# Later calls with override=True take precedence over earlier ones.
try:
    from dotenv import load_dotenv
    for _env_candidate in [
        Path(__file__).parents[2] / ".env",   # repo root
        Path(__file__).parents[1] / ".env",   # session-02/
        Path(__file__).parent / ".env",        # pipeline/
    ]:
        if _env_candidate.exists():
            load_dotenv(_env_candidate, override=True)
except ImportError:
    pass  # python-dotenv not installed yet; env vars must be set manually

log = logging.getLogger(__name__)


# ── lazy client factories ──────────────────────────────────────────────────────

def _anthropic():
    """Return an Anthropic client, or None if key absent."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or "REPLACE_ME" in key:
        return None
    try:
        import anthropic  # noqa: PLC0415
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        log.warning("anthropic package not installed")
        return None


def _openai(*, base_url: str | None = None, key_env: str = "OPENAI_API_KEY"):
    """Return an OpenAI client (or xAI/Grok client), or None if key absent."""
    key = os.getenv(key_env, "")
    if not key or "REPLACE_ME" in key:
        return None
    try:
        from openai import OpenAI  # noqa: PLC0415
        kw: dict[str, Any] = {"api_key": key}
        if base_url:
            kw["base_url"] = base_url
        return OpenAI(**kw)
    except ImportError:
        log.warning("openai package not installed")
        return None


def _grok():
    return _openai(base_url="https://api.x.ai/v1", key_env="XAI_API_KEY")


def _deepseek():
    return _openai(base_url="https://api.deepseek.com", key_env="DEEPSEEK_API_KEY")


def _gemini(model: str = "gemini-2.5-flash"):
    """Return a Gemini GenerativeModel, or None if key absent."""
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or "REPLACE_ME" in key:
        return None
    try:
        import google.generativeai as genai  # noqa: PLC0415
        genai.configure(api_key=key)
        return genai.GenerativeModel(model)
    except ImportError:
        log.warning("google-generativeai package not installed")
        return None


# ── JSON extraction ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Extract the first JSON object from a model response text."""
    # ```json ... ``` block
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # ``` ... ``` block containing JSON
    m = re.search(r"```\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # First { ... } in text (balanced braces)
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start: i + 1])
    return json.loads(text)


_JSON_INSTRUCTION = (
    "\n\nIMPORTANT: Respond with ONLY a valid JSON object. "
    "No prose, no markdown outside the JSON. "
    "Wrap the JSON in ```json\\n...\\n``` if you need markup."
)


# ── complete_json ──────────────────────────────────────────────────────────────

def complete_json(
    system: str,
    user: str,
    *,
    prefer: Literal["claude", "openai", "gemini", "grok", "deepseek"] = "claude",
    max_tokens: int = 8192,
) -> dict:
    """
    Call the best available AI provider and return the response parsed as JSON.

    Tries `prefer` first, then falls through claude → openai → gemini → deepseek → grok.
    Returns {} if all providers fail or are unconfigured.
    """
    order = [prefer, "claude", "openai", "gemini", "deepseek", "grok"]
    seen: set[str] = set()

    for p in order:
        if p in seen:
            continue
        seen.add(p)
        try:
            result = _dispatch(p, system, user + _JSON_INSTRUCTION, max_tokens)
            if result is not None:
                log.debug("complete_json via %s (%d chars)", p, len(json.dumps(result)))
                return result
        except Exception as exc:
            log.debug("provider %s error: %s", p, exc)

    log.warning("complete_json: all providers failed — returning {}")
    return {}


def _dispatch(provider: str, system: str, user: str, max_tokens: int) -> dict | None:
    if provider == "claude":
        return _claude_json(system, user, max_tokens)
    if provider == "openai":
        return _openai_json(system, user, max_tokens)
    if provider == "gemini":
        return _gemini_json(system, user, max_tokens)
    if provider == "grok":
        return _grok_json(system, user, max_tokens)
    if provider == "deepseek":
        return _deepseek_json(system, user, max_tokens)
    return None


def _claude_json(system: str, user: str, max_tokens: int) -> dict | None:
    client = _anthropic()
    if not client:
        return None
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _extract_json(resp.content[0].text)


def _openai_json(system: str, user: str, max_tokens: int) -> dict | None:
    client = _openai()
    if not client:
        return None
    resp = client.chat.completions.create(
        model="gpt-4.1",
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def _gemini_json(system: str, user: str, max_tokens: int) -> dict | None:
    model = _gemini()
    if not model:
        return None
    resp = model.generate_content(
        f"{system}\n\n{user}",
        generation_config={
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
        },
    )
    return _extract_json(resp.text)


def _grok_json(system: str, user: str, max_tokens: int) -> dict | None:
    client = _grok()
    if not client:
        return None
    resp = client.chat.completions.create(
        model="grok-4",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return _extract_json(resp.choices[0].message.content)


def _deepseek_json(system: str, user: str, max_tokens: int) -> dict | None:
    client = _deepseek()
    if not client:
        return None
    resp = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(resp.choices[0].message.content)


# ── generate_image ─────────────────────────────────────────────────────────────

def generate_image(
    prompt: str,
    *,
    size: str = "1024x1024",
    quality: str = "standard",
) -> bytes:
    """
    Generate an image from a text prompt. Returns PNG bytes.

    Tries GPT-Image-1.5 → DALL-E 3 → Gemini Imagen 4 → Grok Aurora → stub PNG.
    """
    # GPT Image 1.5 (OpenAI) — falls back to DALL-E 3 if unavailable
    client = _openai()
    if client:
        # Try gpt-image-1.5 first (higher quality, better text rendering)
        for img_model in ("gpt-image-1.5", "dall-e-3"):
            try:
                kw: dict[str, Any] = {
                    "model": img_model,
                    "prompt": prompt[:4000],
                    "n": 1,
                    "size": size,
                }
                if img_model.startswith("gpt-image"):
                    kw["quality"] = "high"
                    kw["output_format"] = "png"
                else:
                    kw["quality"] = quality
                    kw["response_format"] = "b64_json"
                resp = client.images.generate(**kw)
                img_bytes = (
                    base64.b64decode(resp.data[0].b64_json)
                    if hasattr(resp.data[0], "b64_json") and resp.data[0].b64_json
                    else base64.b64decode(resp.data[0].b64_json or "")
                )
                if img_bytes:
                    log.debug("generate_image: %s ✓ (%d bytes)", img_model, len(img_bytes))
                    return img_bytes
            except Exception as exc:
                log.debug("%s failed: %s — trying next", img_model, exc)
                continue

    # Gemini Imagen 3 (new google-genai SDK)
    key = os.getenv("GEMINI_API_KEY", "")
    if key and "REPLACE_ME" not in key:
        try:
            from google import genai as _genai  # noqa: PLC0415
            from google.genai import types as _gtypes  # noqa: PLC0415
            _img_client = _genai.Client(api_key=key)
            result = _img_client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt[:1024],
                config=_gtypes.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                ),
            )
            if result.generated_images:
                log.debug("generate_image: Gemini Imagen 4 ✓")
                return result.generated_images[0].image.image_bytes
        except ImportError:
            # Fallback to deprecated SDK
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", FutureWarning)
                    import google.generativeai as genai_legacy  # noqa: PLC0415
                genai_legacy.configure(api_key=key)
                imagen = genai_legacy.ImageGenerationModel("imagen-4.0-generate-001")
                result = imagen.generate_images(prompt=prompt[:1024], number_of_images=1)
                if result.images:
                    log.debug("generate_image: Gemini Imagen (legacy SDK) ✓")
                    return result.images[0]._image_bytes
            except Exception as exc:
                log.warning("Gemini Imagen (legacy) failed: %s", exc)
        except Exception as exc:
            log.warning("Gemini Imagen failed: %s", exc)

    # Grok Aurora (xAI) — OpenAI-compatible image generation
    grok_client = _grok()
    if grok_client:
        try:
            resp = grok_client.images.generate(
                model="grok-2-image-1212",
                prompt=prompt[:4000],
                n=1,
                response_format="b64_json",
            )
            data = resp.data[0].b64_json
            if data:
                log.debug("generate_image: Grok Aurora ✓ (%d bytes)", len(data) * 3 // 4)
                return base64.b64decode(data)
        except Exception as exc:
            log.warning("Grok Aurora failed: %s", exc)

    log.info("generate_image: using stub PNG")
    return _stub_png(prompt)


def _stub_png(seed: str = "") -> bytes:
    """Return a minimal 64×64 solid-colour PNG derived from the prompt string."""
    # Pick a hue from the seed string
    h = abs(hash(seed)) % 256
    r, g, b = h, (h * 97) % 256, (h * 197) % 256
    w, h_ = 64, 64
    raw = b""
    for y in range(h_):
        raw += b"\x00"  # filter: None
        for x in range(w):
            # gradient so rows/cols are visually distinct
            raw += bytes([
                min(255, r + x),
                min(255, g + y),
                min(255, b + (x + y) // 2),
                255,
            ])

    def _chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h_, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", idat)
        + _chunk(b"IEND", b"")
    )


# ── text_to_speech ─────────────────────────────────────────────────────────────

def text_to_speech(
    text: str,
    *,
    voice: str = "nova",
    speed: float = 1.0,
) -> bytes:
    """
    Convert text to speech. Returns MP3 bytes.

    Tries OpenAI TTS → ElevenLabs → FFmpeg silent stub.
    """
    if not text.strip():
        return _stub_silence_mp3(1.0)

    # OpenAI TTS — tts-1-hd for maximum audio quality
    client = _openai()
    if client:
        try:
            resp = client.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=text[:4096],
                speed=speed,
            )
            log.debug("text_to_speech: OpenAI TTS-HD ✓")
            return resp.content
        except Exception as exc:
            log.warning("OpenAI TTS-HD failed: %s", exc)

    # ElevenLabs fallback — eleven_v3 for maximum expressiveness
    el_key = os.getenv("ELEVENLABS_API_KEY", "")
    if el_key and "REPLACE_ME" not in el_key:
        try:
            import requests  # noqa: PLC0415
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                json={"text": text[:5000], "model_id": "eleven_v3"},
                headers={"xi-api-key": el_key, "Content-Type": "application/json"},
                timeout=60,
            )
            resp.raise_for_status()
            log.debug("text_to_speech: ElevenLabs v3 ✓")
            return resp.content
        except Exception as exc:
            log.warning("ElevenLabs TTS failed: %s", exc)

    # Estimate duration from word count (~150 wpm)
    words = len(text.split())
    duration = max(1.0, words / 150 * 60)
    log.info("text_to_speech: stub silence %.1fs", duration)
    return _stub_silence_mp3(duration)


def _stub_silence_mp3(duration: float) -> bytes:
    """Generate a silent MP3 of the given duration via FFmpeg."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = Path(f.name)
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(duration),
                "-c:a", "libmp3lame", "-b:a", "128k",
                str(tmp),
            ],
            capture_output=True, check=True,
        )
        data = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        return data
    except Exception as exc:
        log.debug("stub silence MP3 failed: %s", exc)
        return b""


# ── vision_score ───────────────────────────────────────────────────────────────

def vision_score(b64_a: str, b64_b: str) -> float:
    """
    Estimate visual similarity between two base64-encoded PNG images.
    Returns 0.0 (completely different) to 1.0 (identical).
    Returns 0.9 stub when vision providers are unavailable.
    """
    if not b64_a or not b64_b:
        return 0.9

    prompt = (
        "Compare the two images for visual consistency: same character appearance, "
        "colour palette, lighting style, and art direction. "
        "Return ONLY JSON: {\"similarity\": <float 0.0-1.0>}"
    )

    # GPT-4.1 Vision
    client = _openai()
    if client:
        try:
            resp = client.chat.completions.create(
                model="gpt-4.1",
                max_tokens=64,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{b64_a}"}},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{b64_b}"}},
                    ],
                }],
            )
            data = _extract_json(resp.choices[0].message.content)
            return float(data.get("similarity", 0.9))
        except Exception as exc:
            log.debug("vision_score GPT-4.1: %s", exc)

    # Gemini Vision fallback
    model = _gemini()
    if model:
        try:
            import google.generativeai as genai  # noqa: PLC0415
            parts = [
                prompt,
                {"mime_type": "image/png", "data": base64.b64decode(b64_a)},
                {"mime_type": "image/png", "data": base64.b64decode(b64_b)},
            ]
            resp = model.generate_content(parts)
            data = _extract_json(resp.text)
            return float(data.get("similarity", 0.9))
        except Exception as exc:
            log.debug("vision_score Gemini: %s", exc)

    return 0.9  # optimistic stub


# ── search_web (Brave Search API) ────────────────────────────────────────────

def search_web(
    query: str,
    *,
    count: int = 5,
) -> list[dict]:
    """
    Search the web using Brave Search API. Returns a list of results.

    Each result dict contains:
      - title:   str
      - url:     str
      - snippet: str

    Returns [] when BRAVE_API_KEY is absent or the request fails.
    """
    key = os.getenv("BRAVE_API_KEY", "")
    if not key or "REPLACE_ME" in key:
        log.debug("search_web: BRAVE_API_KEY not set — skipping")
        return []

    try:
        import requests as _req  # noqa: PLC0415

        resp = _req.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": key,
            },
            params={
                "q": query,
                "count": min(count, 20),
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:count]:
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("url", ""),
                "snippet": item.get("description", ""),
            })

        log.debug("search_web: Brave returned %d results for %r", len(results), query)
        return results

    except Exception as exc:
        log.warning("search_web failed: %s", exc)
        return []


def search_web_context(
    query: str,
    *,
    max_tokens: int = 4096,
) -> str:
    """
    Search the web and return LLM-optimised clean text via Brave LLM Context API.

    Returns pre-extracted, markdown-converted content chunks ideal for feeding
    into an LLM prompt. Returns "" when BRAVE_API_KEY is absent or request fails.
    """
    key = os.getenv("BRAVE_API_KEY", "")
    if not key or "REPLACE_ME" in key:
        log.debug("search_web_context: BRAVE_API_KEY not set — skipping")
        return ""

    try:
        import requests as _req  # noqa: PLC0415

        resp = _req.get(
            "https://api.search.brave.com/res/v1/llm/context",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": key,
            },
            params={
                "q": query,
                "maximum_number_of_tokens": min(max_tokens, 16384),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # Collect text from all context chunks
        chunks = []
        for item in data.get("results", []):
            text = item.get("text", "")
            if text:
                title = item.get("title", "")
                url = item.get("url", "")
                header = f"## {title}\n> Source: {url}\n" if title else ""
                chunks.append(f"{header}{text}")

        result = "\n\n---\n\n".join(chunks)
        log.debug("search_web_context: Brave returned %d chunks for %r", len(chunks), query)
        return result

    except Exception as exc:
        log.warning("search_web_context failed: %s", exc)
        return ""


# ── generate_sound_effect (ElevenLabs) ─────────────────────────────────────────

def generate_sound_effect(
    prompt: str,
    *,
    duration_seconds: float | None = None,
) -> bytes:
    """
    Generate a sound effect from a text description. Returns MP3 bytes.

    Uses ElevenLabs Sound Effects API. Returns b"" when unavailable.
    """
    el_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not el_key or "REPLACE_ME" in el_key:
        log.debug("generate_sound_effect: ELEVENLABS_API_KEY not set — skipping")
        return b""

    try:
        import requests as _req  # noqa: PLC0415

        payload: dict[str, Any] = {
            "text": prompt[:1000],
        }
        if duration_seconds is not None:
            payload["duration_seconds"] = min(duration_seconds, 22.0)

        resp = _req.post(
            "https://api.elevenlabs.io/v1/sound-generation",
            json=payload,
            headers={"xi-api-key": el_key, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        log.debug("generate_sound_effect: ElevenLabs ✓ (%d bytes)", len(resp.content))
        return resp.content
    except Exception as exc:
        log.warning("generate_sound_effect failed: %s", exc)
        return b""


# ── generate_music (ElevenLabs) ───────────────────────────────────────────────

def generate_music(
    prompt: str,
    *,
    duration_seconds: int = 30,
    instrumental: bool = False,
) -> bytes:
    """
    Generate music from a text description. Returns MP3 bytes.

    Uses ElevenLabs Music Generation API. Returns b"" when unavailable.
    """
    el_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not el_key or "REPLACE_ME" in el_key:
        log.debug("generate_music: ELEVENLABS_API_KEY not set — skipping")
        return b""

    try:
        import requests as _req  # noqa: PLC0415

        resp = _req.post(
            "https://api.elevenlabs.io/v1/music/stream",
            json={
                "prompt": prompt[:1000],
                "duration_seconds": min(duration_seconds, 300),
                "instrumental": instrumental,
            },
            headers={"xi-api-key": el_key, "Content-Type": "application/json"},
            timeout=120,
        )
        resp.raise_for_status()
        log.debug("generate_music: ElevenLabs ✓ (%d bytes)", len(resp.content))
        return resp.content
    except Exception as exc:
        log.warning("generate_music failed: %s", exc)
        return b""


# ── Descript (beta API) ────────────────────────────────────────────────────────

_DESCRIPT_BASE = "https://descriptapi.com/v1"


def _descript_headers() -> dict[str, str] | None:
    """Return Descript auth headers, or None if key absent."""
    key = os.getenv("DESCRIPT_API_KEY", "")
    if not key or "REPLACE_ME" in key:
        return None
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def descript_import_media(
    url: str,
    *,
    project_name: str = "pipeline-import",
) -> dict:
    """
    Import media into Descript from a public/pre-signed URL.

    Descript automatically transcribes imported media.
    Returns the API response dict with project and job info,
    or {} if the provider is unavailable.
    """
    headers = _descript_headers()
    if not headers:
        log.debug("descript_import_media: DESCRIPT_API_KEY not set — skipping")
        return {}

    try:
        import requests as _req  # noqa: PLC0415

        resp = _req.post(
            f"{_DESCRIPT_BASE}/projects/import",
            headers=headers,
            json={
                "name": project_name,
                "media_url": url,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        log.debug("descript_import_media: success — project %s", data.get("project_id", "?"))
        return data
    except Exception as exc:
        log.warning("descript_import_media failed: %s", exc)
        return {}


def descript_agent_edit(
    project_id: str,
    prompt: str,
) -> dict:
    """
    Use Descript's Agent Underlord to edit a project via natural language.

    Examples of prompts:
      - "Remove all filler words"
      - "Add captions"
      - "Apply Studio Sound"
      - "Create a 60-second highlight clip"

    Returns the API response dict with job info, or {} on failure.
    """
    headers = _descript_headers()
    if not headers:
        log.debug("descript_agent_edit: DESCRIPT_API_KEY not set — skipping")
        return {}

    try:
        import requests as _req  # noqa: PLC0415

        resp = _req.post(
            f"{_DESCRIPT_BASE}/projects/{project_id}/agent",
            headers=headers,
            json={"prompt": prompt},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        log.debug("descript_agent_edit: job %s", data.get("job_id", "?"))
        return data
    except Exception as exc:
        log.warning("descript_agent_edit failed: %s", exc)
        return {}


def descript_job_status(job_id: str) -> dict:
    """
    Poll the status of a Descript async job.

    Returns dict with at least {"status": "..."} or {} on failure.
    """
    headers = _descript_headers()
    if not headers:
        return {}

    try:
        import requests as _req  # noqa: PLC0415

        resp = _req.get(
            f"{_DESCRIPT_BASE}/jobs/{job_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        log.warning("descript_job_status failed: %s", exc)
        return {}


# ── provider availability check ───────────────────────────────────────────────

def available_providers() -> dict[str, bool]:
    """Return which providers are configured (have real API keys)."""
    brave_key = os.getenv("BRAVE_API_KEY", "")
    descript_key = os.getenv("DESCRIPT_API_KEY", "")
    return {
        "claude":    _anthropic() is not None,
        "openai":    _openai() is not None,
        "deepseek":  _deepseek() is not None,
        "grok":      _grok() is not None,
        "gemini":    _gemini() is not None,
        "brave":     bool(brave_key and "REPLACE_ME" not in brave_key),
        "descript":  bool(descript_key and "REPLACE_ME" not in descript_key),
    }
