"""
providers.py — Unified multi-provider AI layer.

Loads .env automatically. All providers degrade gracefully when keys are absent.

Env vars
--------
  ANTHROPIC_API_KEY   Claude (primary skill executor — text + JSON)
  OPENAI_API_KEY      GPT-4o (JSON/vision) · DALL-E 3 (images) · TTS (voice)
  XAI_API_KEY         Grok-2 — OpenAI-compatible alternative text provider
  GEMINI_API_KEY      Gemini 2.0 Flash (text/JSON) + Imagen 3 (images)

Public API
----------
  complete_json(system, user, *, prefer, max_tokens) → dict
  generate_image(prompt, *, size, quality)            → bytes  (PNG)
  text_to_speech(text, *, voice, speed)               → bytes  (MP3)
  vision_score(b64_a, b64_b)                          → float  (0-1 similarity)
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


def _gemini(model: str = "gemini-2.0-flash"):
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
    prefer: Literal["claude", "openai", "gemini", "grok"] = "claude",
    max_tokens: int = 8192,
) -> dict:
    """
    Call the best available AI provider and return the response parsed as JSON.

    Tries `prefer` first, then falls through claude → openai → gemini → grok.
    Returns {} if all providers fail or are unconfigured.
    """
    order = [prefer, "claude", "openai", "gemini", "grok"]
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
        model="gpt-4o",
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
        model="grok-2-1212",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return _extract_json(resp.choices[0].message.content)


# ── generate_image ─────────────────────────────────────────────────────────────

def generate_image(
    prompt: str,
    *,
    size: str = "1024x1024",
    quality: str = "standard",
) -> bytes:
    """
    Generate an image from a text prompt. Returns PNG bytes.

    Tries DALL-E 3 → Gemini Imagen 3 → stub gradient PNG.
    """
    # DALL-E 3 (OpenAI)
    client = _openai()
    if client:
        try:
            resp = client.images.generate(
                model="dall-e-3",
                prompt=prompt[:4000],
                n=1,
                size=size,
                quality=quality,
                response_format="b64_json",
            )
            data = resp.data[0].b64_json
            log.debug("generate_image: DALL-E 3 ✓ (%d bytes)", len(data) * 3 // 4)
            return base64.b64decode(data)
        except Exception as exc:
            log.warning("DALL-E 3 failed: %s", exc)

    # Gemini Imagen 3
    key = os.getenv("GEMINI_API_KEY", "")
    if key and "REPLACE_ME" not in key:
        try:
            import google.generativeai as genai  # noqa: PLC0415
            genai.configure(api_key=key)
            imagen = genai.ImageGenerationModel("imagen-3.0-generate-002")
            result = imagen.generate_images(prompt=prompt[:1024], number_of_images=1)
            if result.images:
                log.debug("generate_image: Gemini Imagen ✓")
                return result.images[0]._image_bytes
        except Exception as exc:
            log.warning("Gemini Imagen failed: %s", exc)

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

    # OpenAI TTS
    client = _openai()
    if client:
        try:
            resp = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text[:4096],
                speed=speed,
            )
            log.debug("text_to_speech: OpenAI TTS ✓")
            return resp.content
        except Exception as exc:
            log.warning("OpenAI TTS failed: %s", exc)

    # ElevenLabs fallback
    el_key = os.getenv("ELEVENLABS_API_KEY", "")
    if el_key and "REPLACE_ME" not in el_key:
        try:
            import requests  # noqa: PLC0415
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                json={"text": text[:5000], "model_id": "eleven_multilingual_v2"},
                headers={"xi-api-key": el_key, "Content-Type": "application/json"},
                timeout=60,
            )
            resp.raise_for_status()
            log.debug("text_to_speech: ElevenLabs ✓")
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

    # GPT-4o Vision
    client = _openai()
    if client:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
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
            log.debug("vision_score GPT-4o: %s", exc)

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


# ── provider availability check ───────────────────────────────────────────────

def available_providers() -> dict[str, bool]:
    """Return which providers are configured (have real API keys)."""
    return {
        "claude":  _anthropic() is not None,
        "openai":  _openai() is not None,
        "grok":    _grok() is not None,
        "gemini":  _gemini() is not None,
    }
