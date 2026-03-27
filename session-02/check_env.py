#!/usr/bin/env python3
"""
check_env.py — Environment readiness check for the video production pipeline.

Verifies every tool, library, and API key required for full HD generation.
Prints a tiered capability report and exits 0 (all clear) or 1 (missing critical items).

Usage
-----
  python session-02/check_env.py            # from repo root
  python check_env.py                       # from session-02/
  python check_env.py --live               # also makes cheap live API calls
  python check_env.py --quiet              # only print failures
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# ── ANSI colours ──────────────────────────────────────────────────────────────

_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    codes = {"green": "32", "yellow": "33", "red": "31", "cyan": "36",
             "bold": "1", "dim": "2", "reset": "0"}
    return f"\033[{codes.get(code, '0')}m{text}\033[0m"


OK   = _c("green",  "✓")
WARN = _c("yellow", "⚠")
FAIL = _c("red",    "✗")
INFO = _c("cyan",   "·")

# ── load .env ─────────────────────────────────────────────────────────────────

def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # noqa: PLC0415
        for candidate in [
            Path(__file__).parents[1] / ".env",
            Path(__file__).parent    / ".env",
            Path(__file__).parent / "pipeline" / ".env",
        ]:
            if candidate.exists():
                load_dotenv(candidate, override=True)
                return
    except ImportError:
        pass  # python-dotenv will be caught below


# ── result accumulator ────────────────────────────────────────────────────────

class Report:
    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def ok(self, label: str, detail: str = "") -> None:
        if not self.quiet:
            suffix = f"  {_c('dim', detail)}" if detail else ""
            print(f"  {OK}  {label}{suffix}")

    def warn(self, label: str, detail: str = "") -> None:
        self.warnings.append(label)
        suffix = f"  {_c('dim', detail)}" if detail else ""
        print(f"  {WARN}  {label}{suffix}")

    def fail(self, label: str, detail: str = "") -> None:
        self.failures.append(label)
        suffix = f"  {_c('dim', detail)}" if detail else ""
        print(f"  {FAIL}  {label}{suffix}")

    def info(self, label: str, detail: str = "") -> None:
        if not self.quiet:
            suffix = f"  {_c('dim', detail)}" if detail else ""
            print(f"  {INFO}  {_c('dim', label)}{suffix}")

    def section(self, title: str) -> None:
        print(f"\n{_c('bold', title)}")


# ── checks ────────────────────────────────────────────────────────────────────

def check_python(r: Report) -> None:
    r.section("Python")
    major, minor = sys.version_info[:2]
    ver = f"{major}.{minor}.{sys.version_info[2]}"
    if (major, minor) >= (3, 10):
        r.ok(f"Python {ver}")
    elif (major, minor) >= (3, 8):
        r.warn(f"Python {ver}", "3.10+ recommended for full type-hint support")
    else:
        r.fail(f"Python {ver}", "3.10+ required")


def check_packages(r: Report) -> None:
    r.section("Python packages")

    required = [
        ("numpy",                "numpy",                "video frame operations"),
        ("requests",             "requests",             "API HTTP calls"),
        ("python-dotenv",        "dotenv",               ".env loading"),
        ("jsonschema",           "jsonschema",           "schema validation"),
    ]
    ai_packages = [
        ("anthropic",            "anthropic",            "Claude — primary skill executor (S01-S24)"),
        ("openai",               "openai",               "GPT-4o / DALL-E 3 / TTS fallback"),
        ("google-generativeai",  "google.generativeai",  "Gemini 2.0 Flash + Imagen 3"),
    ]
    optional = [
        ("tqdm",                 "tqdm",                 "progress bars"),
        ("moviepy",              "moviepy",              "legacy assembly fallback"),
        ("Pillow",               "PIL",                  "image utilities"),
    ]

    for pkg_name, import_name, purpose in required:
        spec = importlib.util.find_spec(import_name)
        if spec:
            r.ok(pkg_name, purpose)
        else:
            r.fail(pkg_name, f"pip install {pkg_name}  — {purpose}")

    for pkg_name, import_name, purpose in ai_packages:
        spec = importlib.util.find_spec(import_name)
        if spec:
            r.ok(pkg_name, purpose)
        else:
            r.warn(pkg_name, f"pip install {pkg_name}  — {purpose}")

    for pkg_name, import_name, purpose in optional:
        spec = importlib.util.find_spec(import_name)
        if spec:
            r.ok(pkg_name, purpose)
        else:
            r.info(f"{pkg_name} (optional)", f"pip install {pkg_name}  — {purpose}")


def check_ffmpeg(r: Report) -> None:
    r.section("FFmpeg")

    # Binary present
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if result.returncode != 0:
        r.fail("ffmpeg binary", "install: sudo apt install ffmpeg  OR  brew install ffmpeg")
        return

    first_line = result.stdout.splitlines()[0] if result.stdout else "?"
    r.ok("ffmpeg", first_line.split("Copyright")[0].strip())

    # Codec support
    codecs = subprocess.run(["ffmpeg", "-codecs"], capture_output=True, text=True).stdout

    codec_checks = [
        ("libx264",    "H.264 encoding (required for output)"),
        ("libx265",    "H.265/HEVC encoding (optional, better compression)"),
        ("libmp3lame", "MP3 audio encoding (stub audio)"),
        ("aac",        "AAC audio (final mix)"),
    ]
    for codec, desc in codec_checks:
        if codec in codecs:
            r.ok(codec, desc)
        elif codec == "libx264":
            r.fail(codec, f"{desc} — CRITICAL, pipeline cannot encode without this")
        elif codec == "libx265":
            r.info(f"{codec} (optional)", f"{desc} — pipeline falls back to libx264")
        else:
            r.warn(codec, desc)

    # Filter support
    filters = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True).stdout
    filter_checks = [
        ("drawtext", "text overlay on stub clips"),
        ("eq",       "colour grading"),
        ("lut3d",    "LUT-based colour grading (optional)"),
        ("adelay",   "audio timeline positioning"),
        ("amix",     "multi-track audio mixing"),
        ("afade",    "audio fade in/out"),
    ]
    for filt, desc in filter_checks:
        if filt in filters:
            r.ok(f"filter:{filt}", desc)
        elif filt in ("lut3d",):
            r.info(f"filter:{filt} (optional)", desc)
        else:
            r.warn(f"filter:{filt}", f"{desc} — may degrade assembly quality")

    # ffprobe
    probe = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True)
    if probe.returncode == 0:
        r.ok("ffprobe", "media inspection")
    else:
        r.warn("ffprobe", "not found — usually ships with ffmpeg")


def _key_status(env_var: str) -> tuple[str, str]:
    """Return (status, masked_value): 'ok' | 'placeholder' | 'missing'."""
    val = os.getenv(env_var, "")
    if not val:
        return "missing", ""
    if "REPLACE_ME" in val or "YOUR_" in val or val.startswith("sk-xxx"):
        return "placeholder", val[:8] + "…"
    # Mask all but first 6 and last 4 chars
    if len(val) > 12:
        masked = val[:6] + "…" + val[-4:]
    else:
        masked = val[:4] + "…"
    return "ok", masked


def check_api_keys(r: Report, live: bool = False) -> None:
    r.section("API keys")

    keys = [
        # (env_var,           service,            tier,       live_check_fn)
        ("ANTHROPIC_API_KEY",  "Anthropic Claude", "skills",   _live_check_anthropic),
        ("OPENAI_API_KEY",     "OpenAI GPT-4o",    "skills",   _live_check_openai),
        ("XAI_API_KEY",        "xAI Grok",         "skills",   None),
        ("GEMINI_API_KEY",     "Google Gemini",    "skills",   _live_check_gemini),
        ("RUNWAY_API_KEY",     "Runway Gen4",      "video",    _live_check_runway),
        ("ELEVENLABS_API_KEY", "ElevenLabs TTS",   "audio",    _live_check_elevenlabs),
        ("SUNO_COOKIE",        "Suno music",       "music",    None),
        ("MIDJOURNEY_TOKEN",   "Midjourney",       "images",   None),
    ]

    tier_labels = {
        "skills": "AI skills pipeline (S01-S24)",
        "video":  "HD shot video generation",
        "audio":  "dialogue / voice-over TTS",
        "music":  "generative music score",
        "images": "reference image generation",
    }

    for env_var, service, tier, check_fn in keys:
        status, masked = _key_status(env_var)
        tier_note = tier_labels.get(tier, tier)

        if status == "ok":
            if live and check_fn:
                live_ok, live_msg = check_fn()
                if live_ok:
                    r.ok(f"{env_var}  [{service}]", f"{masked}  {_c('green', '(live ✓)')}")
                else:
                    r.warn(
                        f"{env_var}  [{service}]",
                        f"{masked}  {_c('yellow', f'(live ✗: {live_msg})')}",
                    )
            else:
                r.ok(f"{env_var}  [{service}]", masked)
        elif status == "placeholder":
            r.warn(f"{env_var}  [{service}]", f"placeholder value — replace in .env  [{tier_note}]")
        else:
            if tier in ("skills",):
                # At least one AI provider is required for the skills pipeline
                r.warn(f"{env_var}  [{service}]", f"not set  [{tier_note}]")
            elif tier == "video":
                r.warn(f"{env_var}  [{service}]", "not set — pipeline falls back to STUB colour clips")
            elif tier == "audio":
                r.warn(f"{env_var}  [{service}]", "not set — dialogue/VO will be silent stubs")
            elif tier == "music":
                r.warn(f"{env_var}  [{service}]", "not set — score will be a soft-tone stub")
            else:
                r.info(f"{env_var}  [{service}] (optional)", f"not set  [{tier_note}]")

    # Summarise AI provider coverage
    print()
    ai_vars = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"]
    ai_present = [v for v in ai_vars if _key_status(v)[0] == "ok"]
    if ai_present:
        r.ok(
            f"AI provider coverage",
            f"{len(ai_present)}/{len(ai_vars)} providers active"
            f"  ({', '.join(v.split('_')[0].capitalize() for v in ai_present)})",
        )
    else:
        r.fail(
            "AI provider coverage",
            "NO AI provider configured — skills pipeline will produce empty stubs. "
            "Set at least ANTHROPIC_API_KEY.",
        )


def check_disk_space(r: Report) -> None:
    r.section("Disk space")
    try:
        import shutil  # noqa: PLC0415
        total, used, free = shutil.disk_usage(Path(__file__).parent)
        free_gb = free / 1_073_741_824
        used_pct = used / total * 100

        if free_gb >= 10:
            r.ok(f"{free_gb:.1f} GB free", f"{used_pct:.0f}% used  (10 GB+ recommended for full HD render)")
        elif free_gb >= 3:
            r.warn(f"{free_gb:.1f} GB free", "stub pipeline will work; HD Runway clips need ~10 GB")
        else:
            r.fail(f"{free_gb:.1f} GB free", "very low — HD generation likely to fail mid-run")
    except Exception as exc:
        r.warn("disk space check failed", str(exc))


def check_network(r: Report) -> None:
    r.section("Network connectivity")
    endpoints = [
        ("https://api.anthropic.com",          "Anthropic Claude API"),
        ("https://api.openai.com",             "OpenAI API"),
        ("https://api.dev.runwayml.com",       "Runway Gen4 API"),
        ("https://api.elevenlabs.io",          "ElevenLabs API"),
        ("https://generativelanguage.googleapis.com", "Google Gemini API"),
    ]
    try:
        import urllib.request  # noqa: PLC0415
        for url, label in endpoints:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "check_env/1.0"})
                urllib.request.urlopen(req, timeout=4)
                r.ok(label, url)
            except Exception:
                # Any response (even 4xx) means the host is reachable
                try:
                    urllib.request.urlopen(url, timeout=4)
                    r.ok(label, url)
                except Exception as exc:
                    msg = str(exc)
                    if "403" in msg or "401" in msg or "404" in msg:
                        r.ok(label, url)   # host reachable, auth rejected as expected
                    elif "SSL" in msg or "certificate" in msg.lower():
                        r.warn(label, f"SSL issue: {url}")
                    else:
                        r.warn(label, f"unreachable ({url})")
    except Exception as exc:
        r.warn("network check unavailable", str(exc))


# ── live API checks (cheap, read-only) ────────────────────────────────────────

def _live_check_anthropic() -> tuple[bool, str]:
    try:
        import anthropic  # noqa: PLC0415
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)[:60]


def _live_check_openai() -> tuple[bool, str]:
    try:
        from openai import OpenAI  # noqa: PLC0415
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        client.models.list()
        return True, ""
    except Exception as exc:
        return False, str(exc)[:60]


def _live_check_gemini() -> tuple[bool, str]:
    try:
        import google.generativeai as genai  # noqa: PLC0415
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        genai.GenerativeModel("gemini-2.0-flash").generate_content(
            "hi", generation_config={"max_output_tokens": 4}
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)[:60]


def _live_check_runway() -> tuple[bool, str]:
    try:
        import requests  # noqa: PLC0415
        resp = requests.get(
            "https://api.dev.runwayml.com/v1/tasks",
            headers={"Authorization": f"Bearer {os.environ['RUNWAY_API_KEY']}"},
            timeout=6,
        )
        if resp.status_code in (200, 400, 404):
            return True, ""
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:60]


def _live_check_elevenlabs() -> tuple[bool, str]:
    try:
        import requests  # noqa: PLC0415
        resp = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
            timeout=6,
        )
        if resp.status_code in (200, 401):
            return resp.status_code == 200, "invalid key" if resp.status_code == 401 else ""
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:60]


# ── capability summary ────────────────────────────────────────────────────────

def print_capability_summary(r: Report) -> None:
    print(f"\n{_c('bold', '─' * 60)}")
    print(_c("bold", "Capability tiers"))
    print(_c("bold", "─" * 60))

    def _tier(label: str, env_vars: list[str], fallback: str) -> None:
        present = any(_key_status(v)[0] == "ok" for v in env_vars)
        if present:
            keys_found = [v for v in env_vars if _key_status(v)[0] == "ok"]
            print(f"  {OK}  {label}")
            print(f"       {_c('dim', 'via ' + ', '.join(keys_found))}")
        else:
            print(f"  {WARN}  {label}")
            print(f"       {_c('dim', fallback)}")

    print()
    print(f"  {OK if not r.failures else WARN}  Stub mode (always available)")
    print(f"       {_c('dim', 'colour-block clips + silent audio — no API keys required')}")

    _tier(
        "AI skills pipeline  (story → script → shots → assembly instructions)",
        ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"],
        "Set ANTHROPIC_API_KEY for Claude (recommended) or OPENAI_API_KEY / GEMINI_API_KEY",
    )
    _tier(
        "HD video shot generation  (Runway Gen4 — real cinematic clips)",
        ["RUNWAY_API_KEY"],
        "Set RUNWAY_API_KEY — without it all shots are solid-colour stubs",
    )
    _tier(
        "Dialogue / voice-over  (ElevenLabs TTS)",
        ["ELEVENLABS_API_KEY"],
        "Set ELEVENLABS_API_KEY — without it all voice tracks are silent",
    )
    _tier(
        "Generative music score  (Suno)",
        ["SUNO_COOKIE"],
        "Set SUNO_COOKIE — without it score track is a soft 60Hz tone",
    )
    _tier(
        "Reference images  (DALL-E 3 / Imagen 3)",
        ["OPENAI_API_KEY", "GEMINI_API_KEY"],
        "Set OPENAI_API_KEY or GEMINI_API_KEY — S13 reference-asset-gen skill",
    )


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check environment readiness for the video production pipeline.",
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Make cheap live API calls to verify keys are valid (uses minimal credits).",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Only print failures and warnings.",
    )
    parser.add_argument(
        "--no-network", action="store_true",
        help="Skip network connectivity checks.",
    )
    args = parser.parse_args()

    _load_dotenv()

    print(_c("bold", "\n╔══════════════════════════════════════════════════════════╗"))
    print(_c("bold",   "║   Video Production Pipeline — Environment Check          ║"))
    print(_c("bold",   "╚══════════════════════════════════════════════════════════╝"))
    if args.live:
        print(f"  {_c('yellow', 'Live API validation enabled — this will consume minimal credits.')}")

    r = Report(quiet=args.quiet)

    check_python(r)
    check_packages(r)
    check_ffmpeg(r)
    check_api_keys(r, live=args.live)
    check_disk_space(r)
    if not args.no_network:
        check_network(r)

    print_capability_summary(r)

    # Final verdict
    print(f"\n{_c('bold', '─' * 60)}")
    if r.failures:
        print(f"\n  {FAIL}  {len(r.failures)} critical issue(s) found — pipeline cannot run in HD mode.")
        for f in r.failures:
            print(f"       {_c('red', f)}")
        print()
        return 1
    elif r.warnings:
        print(
            f"\n  {WARN}  {len(r.warnings)} warning(s) — "
            "stub mode works; set missing keys for full HD output."
        )
        print()
    else:
        print(f"\n  {OK}  All systems go — full HD pipeline ready.")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
