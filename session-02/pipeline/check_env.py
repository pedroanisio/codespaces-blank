"""
check_env.py — Environment readiness checker for the video production pipeline.

Verifies:
  - System tools  (ffmpeg, python version)
  - Python packages (required + optional)
  - API keys       (required + optional)

Prints a status table and a feature summary showing exactly what the pipeline
can and cannot do with the current configuration.

Usage
-----
  python -m pipeline.check_env
  python session-02/pipeline/check_env.py
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

# ── Load .env files (same search order as providers.py) ──────────────────────
try:
    from dotenv import load_dotenv
    for _env in [
        Path(__file__).parents[2] / ".env",   # repo root
        Path(__file__).parents[1] / ".env",   # session-02/
        Path(__file__).parent / ".env",        # pipeline/
    ]:
        if _env.exists():
            load_dotenv(_env, override=True)
except ImportError:
    pass  # python-dotenv checked below


# ── ANSI colours (disabled on non-TTY) ───────────────────────────────────────
_USE_COLOUR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

OK   = lambda t: _c("32", t)   # green
WARN = lambda t: _c("33", t)   # yellow
FAIL = lambda t: _c("31", t)   # red
DIM  = lambda t: _c("2",  t)   # dim/grey
BOLD = lambda t: _c("1",  t)   # bold


# ── Checkers ─────────────────────────────────────────────────────────────────

_IMPORT_NAME_MAP = {
    "python-dotenv": "dotenv",
    "google-genai": "google.genai",
    "google-generativeai": "google.generativeai",
}


def _check_package(name: str) -> tuple[bool, str]:
    """Return (installed, version_or_error_string)."""
    import_name = _IMPORT_NAME_MAP.get(name, name.replace("-", "_").split(".")[0])
    spec = importlib.util.find_spec(import_name)
    if spec is None:
        return False, "not installed"
    try:
        import importlib.metadata as meta
        ver = meta.version(name)
        return True, ver
    except Exception:
        return True, "installed"


def _check_cmd(cmd: str) -> tuple[bool, str]:
    """Return (found, version_or_path)."""
    path = shutil.which(cmd)
    if not path:
        return False, "not found in PATH"
    try:
        if cmd == "ffmpeg":
            r = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            first = r.stdout.splitlines()[0] if r.stdout else "unknown"
            return True, first.split("version ")[-1].split(" ")[0] if "version" in first else first
        return True, path
    except Exception as exc:
        return True, f"found ({exc})"


def _check_key(env_var: str) -> tuple[bool, str]:
    """Return (set, masked_value)."""
    val = os.getenv(env_var, "")
    if not val or "REPLACE_ME" in val or val == "your_key_here":
        return False, "not set"
    masked = val[:4] + "***" + val[-2:] if len(val) > 8 else "***"
    return True, masked


# ── Live API-key validators (cheap, read-only calls) ─────────────────────────

def _validate_anthropic() -> tuple[bool, str]:
    """Validate ANTHROPIC_API_KEY with a minimal Haiku call (~8 tokens)."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_openai() -> tuple[bool, str]:
    """Validate OPENAI_API_KEY with a free models.list() call."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        client.models.list()
        return True, ""
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_gemini() -> tuple[bool, str]:
    """Validate GEMINI_API_KEY with a minimal generate_content call (~4 tokens)."""
    # Try new google-genai SDK first, fall back to deprecated google-generativeai
    try:
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        client.models.generate_content(
            model="gemini-2.5-flash",
            contents="hi",
            config={"max_output_tokens": 4},
        )
        return True, ""
    except ImportError:
        pass
    # Fallback: deprecated SDK
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=os.environ["GEMINI_API_KEY"])
        genai_legacy.GenerativeModel("gemini-2.0-flash-lite").generate_content(
            "hi", generation_config={"max_output_tokens": 4},
        )
        return True, "⚠ using deprecated google-generativeai — run: pip install google-genai"
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_deepseek() -> tuple[bool, str]:
    """Validate DEEPSEEK_API_KEY via OpenAI-compatible models.list()."""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
        )
        client.models.list()
        return True, ""
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_xai() -> tuple[bool, str]:
    """Validate XAI_API_KEY with a lightweight GET /v1/api-key call."""
    try:
        import requests as _req
        resp = _req.get(
            "https://api.x.ai/v1/api-key",
            headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"},
            timeout=6,
        )
        if resp.status_code == 200:
            return True, ""
        if resp.status_code in (401, 403):
            return False, "invalid key"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_runway() -> tuple[bool, str]:
    """Validate RUNWAY_API_KEY with a free GET /v1/tasks."""
    try:
        import requests as _req
        resp = _req.get(
            "https://api.dev.runwayml.com/v1/tasks",
            headers={"Authorization": f"Bearer {os.environ['RUNWAY_API_KEY']}"},
            timeout=6,
        )
        if resp.status_code in (200, 400, 404):
            return True, ""
        if resp.status_code in (401, 403):
            return False, "invalid key"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_elevenlabs() -> tuple[bool, str]:
    """Validate ELEVENLABS_API_KEY with a free GET /v1/voices."""
    try:
        import requests as _req
        resp = _req.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
            timeout=6,
        )
        if resp.status_code == 200:
            return True, ""
        if resp.status_code == 401:
            return False, "invalid key"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_suno() -> tuple[bool, str]:
    """Validate SUNO_COOKIE with a lightweight billing/info check."""
    try:
        import requests as _req
        resp = _req.get(
            "https://studio-api.suno.ai/api/billing/info/",
            headers={"Cookie": os.environ["SUNO_COOKIE"]},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, ""
        if resp.status_code in (401, 403):
            return False, "expired or invalid cookie"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_descript() -> tuple[bool, str]:
    """Validate DESCRIPT_API_KEY with a lightweight API call."""
    try:
        import requests as _req
        resp = _req.get(
            "https://descriptapi.com/v1/jobs",
            headers={"Authorization": f"Bearer {os.environ['DESCRIPT_API_KEY']}"},
            timeout=10,
        )
        if resp.status_code in (200, 400, 404):
            return True, ""
        if resp.status_code in (401, 403):
            return False, "invalid key"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:80]


def _validate_brave() -> tuple[bool, str]:
    """Validate BRAVE_API_KEY with a minimal web search query."""
    try:
        import requests as _req
        resp = _req.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": os.environ["BRAVE_API_KEY"],
            },
            params={"q": "test", "count": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, ""
        if resp.status_code in (401, 403):
            return False, "invalid key"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)[:80]


# Map env-var name → validator function (only for keys that can be live-checked)
_KEY_VALIDATORS: dict[str, callable] = {
    "ANTHROPIC_API_KEY":  _validate_anthropic,
    "OPENAI_API_KEY":     _validate_openai,
    "GEMINI_API_KEY":     _validate_gemini,
    "DEEPSEEK_API_KEY":   _validate_deepseek,
    "XAI_API_KEY":        _validate_xai,
    "RUNWAY_API_KEY":     _validate_runway,
    "ELEVENLABS_API_KEY": _validate_elevenlabs,
    "SUNO_COOKIE":        _validate_suno,
    "BRAVE_API_KEY":      _validate_brave,
    "DESCRIPT_API_KEY":   _validate_descript,
}


def _check_ffmpeg_codecs() -> dict[str, bool]:
    """Check which codecs ffmpeg has compiled in."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-codecs"], capture_output=True, text=True, timeout=5
        )
        txt = r.stdout
        return {
            "libx264": "libx264" in txt,
            "libx265": "libx265" in txt,
            "libmp3lame": "libmp3lame" in txt,
            "aac": "aac" in txt,
        }
    except Exception:
        return {}


def _check_python_version() -> tuple[bool, str]:
    v = sys.version_info
    ok = v >= (3, 9)
    return ok, f"{v.major}.{v.minor}.{v.micro}"


# ── Render helpers ────────────────────────────────────────────────────────────

_W_LABEL = 32
_W_STAT  = 12

def _row(label: str, status: str, note: str = "") -> str:
    stat_col = OK("  OK  ") if status == "ok" else (
        WARN(" WARN ") if status == "warn" else FAIL(" MISS ")
    )
    note_col = DIM(f"  {note}") if note else ""
    return f"  {label:<{_W_LABEL}}[{stat_col}]{note_col}"


def _section(title: str) -> str:
    return f"\n{BOLD(title)}\n" + "─" * 60


# ── Main check ────────────────────────────────────────────────────────────────

def run_checks() -> int:
    """Run all checks and print results. Returns exit code (0 = all required OK)."""

    print(BOLD("\n╔══════════════════════════════════════════════════════════╗"))
    print(BOLD(  "║   SAFE AI Production — Environment Readiness Check      ║"))
    print(BOLD(  "╚══════════════════════════════════════════════════════════╝"))

    all_required_ok = True
    feature_flags: dict[str, bool] = {}

    # ── 1. Python version ────────────────────────────────────────────────────
    print(_section("1. Python"))
    py_ok, py_ver = _check_python_version()
    print(_row("Python runtime", "ok" if py_ok else "miss", f"v{py_ver}"))
    if not py_ok:
        all_required_ok = False

    # ── 2. System tools ──────────────────────────────────────────────────────
    print(_section("2. System Tools"))

    ffmpeg_ok, ffmpeg_ver = _check_cmd("ffmpeg")
    print(_row("ffmpeg", "ok" if ffmpeg_ok else "miss", ffmpeg_ver))
    if not ffmpeg_ok:
        all_required_ok = False
        print(DIM("     → Install: https://ffmpeg.org/download.html"))

    if ffmpeg_ok:
        codecs = _check_ffmpeg_codecs()
        for codec, present in codecs.items():
            print(_row(f"  ffmpeg codec: {codec}", "ok" if present else "warn",
                       "" if present else "optional codec missing"))

    # ── 3. Required Python packages ──────────────────────────────────────────
    print(_section("3. Required Python Packages"))

    required_pkgs = [
        ("requests",           "HTTP calls to Runway / ElevenLabs / Suno"),
        ("python-dotenv",      "Load .env API keys"),
        ("anthropic",          "Claude AI — 24-skill pipeline"),
        ("jsonschema",         "Schema validation"),
    ]

    for pkg, desc in required_pkgs:
        ok, ver = _check_package(pkg)
        print(_row(pkg, "ok" if ok else "miss", ver if ok else f"pip install {pkg}"))
        if not ok:
            all_required_ok = False

    # ── 4. Optional Python packages ──────────────────────────────────────────
    print(_section("4. Optional Python Packages"))

    optional_pkgs = [
        ("openai",              "GPT-Image-1.5 · TTS-HD · GPT-4.1 vision"),
        ("google-genai",        "Gemini 2.5 Flash · Imagen 4 (recommended)"),
        ("google-generativeai", "Gemini (deprecated — upgrade to google-genai)"),
        ("moviepy",             "Legacy video utilities"),
        ("Pillow",              "Image processing"),
        ("tqdm",                "Progress bars"),
        ("audiocraft",          "MusicGen — local offline music generation"),
        ("torch",               "Required by audiocraft"),
        ("torchaudio",          "Required by audiocraft"),
    ]

    feature_flags["openai_pkg"]      = _check_package("openai")[0]
    feature_flags["gemini_pkg"]      = _check_package("google-generativeai")[0]
    feature_flags["audiocraft_pkg"]  = _check_package("audiocraft")[0]

    for pkg, desc in optional_pkgs:
        ok, ver = _check_package(pkg)
        status = "ok" if ok else "warn"
        note   = ver if ok else f"optional — enables: {desc}"
        print(_row(pkg, status, note))

    # ── 5. API Keys ──────────────────────────────────────────────────────────
    print(_section("5. API Keys"))

    keys: list[tuple[str, bool, str]] = [
        # (env_var, required, description)
        ("ANTHROPIC_API_KEY",   True,  "Claude — AI skills pipeline (--idea mode)"),
        ("OPENAI_API_KEY",      False, "GPT-Image-1.5 · TTS-HD · GPT-4.1 vision"),
        ("GEMINI_API_KEY",      False, "Gemini 2.5 Flash · Imagen 4 (image fallback)"),
        ("DEEPSEEK_API_KEY",    False, "DeepSeek V3.2 — text/JSON fallback provider"),
        ("XAI_API_KEY",         False, "Grok 4 — text/JSON + Aurora image gen"),
        ("RUNWAY_API_KEY",      False, "Runway Gen-4.5 — real video shot generation"),
        ("ELEVENLABS_API_KEY",  False, "Eleven v3 TTS · SFX · Music generation"),
        ("SUNO_COOKIE",         False, "Suno — music generation (unofficial API)"),
        ("BRAVE_API_KEY",       False, "Brave Search — web research for creative skills"),
        ("DESCRIPT_API_KEY",    False, "Descript — transcription + AI editing (beta)"),
        ("AUDIOCRAFT_MODEL_DIR",False, "Local MusicGen model cache path"),
    ]

    for env_var, required, desc in keys:
        ok, masked = _check_key(env_var)

        if env_var == "AUDIOCRAFT_MODEL_DIR" and ok:
            # Special: check directory actually exists
            dir_path = Path(os.environ[env_var])
            ok = dir_path.is_dir()
            masked = str(dir_path) if ok else f"{dir_path} (directory not found!)"

        status = "ok" if ok else ("miss" if required else "warn")
        req_tag = " [REQUIRED]" if required else " [optional]"
        note = masked if ok else f"not set — {desc}"
        print(_row(env_var + req_tag, status, note))

        # Live-validate keys that are present
        if ok and env_var in _KEY_VALIDATORS:
            valid, msg = _KEY_VALIDATORS[env_var]()
            if valid:
                print(DIM(f"    ↳ live validation              [") + OK(" PASS ") + DIM("]"))
                if msg:
                    print(WARN(f"       {msg}"))
            else:
                print(DIM(f"    ↳ live validation              [") + FAIL(" FAIL ") + DIM("]"))
                if msg:
                    print(FAIL(f"       {msg}"))
                ok = False  # key is set but invalid — treat as missing
                status = "miss" if required else "warn"

        if required and not ok:
            all_required_ok = False

        # Populate feature flags
        feature_flags[env_var] = ok

    # ── 6. .env file locations ───────────────────────────────────────────────
    print(_section("6. .env Files Found"))
    env_candidates = [
        Path(__file__).parents[2] / ".env",
        Path(__file__).parents[1] / ".env",
        Path(__file__).parent / ".env",
    ]
    found_any = False
    for p in env_candidates:
        if p.exists():
            label = "..." + str(p.resolve())[-28:] if len(str(p.resolve())) > 31 else str(p.resolve())
            print(_row(label, "ok", "loaded"))
            found_any = True
    if not found_any:
        print(_row("(no .env files found)", "warn",
                   "create session-02/.env with your keys"))

    # ── 7. Feature Summary ───────────────────────────────────────────────────
    print(_section("7. Feature Availability"))

    def feat(label: str, enabled: bool, note: str = "") -> None:
        sym = OK("  ✓  ") if enabled else WARN("  ✗  ")
        note_s = DIM(f"  {note}") if note else ""
        print(f"  {label:<44}[{sym}]{note_s}")

    feat("AI skills pipeline (--idea mode)",
         feature_flags.get("ANTHROPIC_API_KEY", False),
         "needs ANTHROPIC_API_KEY")

    feat("Reference image generation (S13)",
         feature_flags.get("OPENAI_API_KEY", False) or
         feature_flags.get("GEMINI_API_KEY", False),
         "needs OPENAI or GEMINI key")

    feat("Real dialogue / voice-over (TTS)",
         feature_flags.get("ELEVENLABS_API_KEY", False) or
         feature_flags.get("OPENAI_API_KEY", False),
         "needs ELEVENLABS or OPENAI key")

    feat("Real ambient + SFX audio",
         feature_flags.get("ELEVENLABS_API_KEY", False),
         "needs ELEVENLABS_API_KEY")

    feat("Real video shots (Runway Gen-4.5)",
         feature_flags.get("RUNWAY_API_KEY", False),
         "needs RUNWAY_API_KEY")

    feat("Real video shots (Google Veo 3.1)",
         feature_flags.get("GEMINI_API_KEY", False),
         "needs GEMINI_API_KEY (fallback when Runway unavailable)")

    feat("Image generation (Grok Aurora)",
         feature_flags.get("XAI_API_KEY", False),
         "needs XAI_API_KEY (fallback image provider)")

    feat("Image-guided video (Runway img2vid)",
         feature_flags.get("RUNWAY_API_KEY", False) and (
             feature_flags.get("OPENAI_API_KEY", False) or
             feature_flags.get("GEMINI_API_KEY", False)
         ),
         "needs RUNWAY + (OPENAI or GEMINI) for ref images")

    feat("Real music generation (Suno)",
         feature_flags.get("SUNO_COOKIE", False),
         "needs SUNO_COOKIE")

    feat("Real music generation (ElevenLabs)",
         feature_flags.get("ELEVENLABS_API_KEY", False),
         "needs ELEVENLABS_API_KEY")

    feat("Offline music generation (MusicGen)",
         feature_flags.get("audiocraft_pkg", False) and
         feature_flags.get("AUDIOCRAFT_MODEL_DIR", False),
         "needs audiocraft + AUDIOCRAFT_MODEL_DIR")

    feat("Transcription + AI editing (Descript)",
         feature_flags.get("DESCRIPT_API_KEY", False),
         "needs DESCRIPT_API_KEY (beta API)")

    feat("Sound effects generation (ElevenLabs SFX)",
         feature_flags.get("ELEVENLABS_API_KEY", False),
         "needs ELEVENLABS_API_KEY")

    feat("Web research for creative skills (S02/S04/S05)",
         feature_flags.get("BRAVE_API_KEY", False),
         "needs BRAVE_API_KEY")

    feat("LLM-optimised web context (Brave Context)",
         feature_flags.get("BRAVE_API_KEY", False),
         "needs BRAVE_API_KEY")

    feat("Video fallback: Ken Burns effect",
         ffmpeg_ok,
         "needs ffmpeg (always available when ffmpeg installed)")

    feat("Stub-only mode (no API keys needed)",
         ffmpeg_ok,
         "always available when ffmpeg installed")

    # ── 8. Final verdict ─────────────────────────────────────────────────────
    print()
    if all_required_ok:
        print(OK("  ✓ All required dependencies are satisfied."))
        print(DIM("    Run: python -m pipeline.run --idea \"your concept\" --output-dir ./output"))
    else:
        print(FAIL("  ✗ Some required dependencies are missing (see MISS items above)."))
        print(DIM("    Run:  pip install -r session-02/pipeline/requirements.txt"))
        print(DIM("    Then: set API keys in session-02/.env"))

    print()
    return 0 if all_required_ok else 1


if __name__ == "__main__":
    sys.exit(run_checks())
