#!/usr/bin/env python3
"""
Prepare an audio file for sharing via WhatsApp.

Converts any supported audio file to OGG/Opus (the native WhatsApp voice note
format) and computes the 64-element waveform array expected by the WhatsApp
protocol when sending via the Business API.

Output
------
- <stem>.ogg          — converted audio, ready to upload
- <stem>.waveform.json — waveform + duration metadata for API payloads

Usage
-----
    python prepare_whatsapp_audio.py file.m4a
    python prepare_whatsapp_audio.py file.mp3 --output-dir out/
    python prepare_whatsapp_audio.py *.wav --bitrate 64k
"""

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".mp3", ".mp4", ".m4a", ".wav", ".webm",
    ".ogg", ".flac", ".aac", ".opus", ".wma",
}

# WhatsApp waveform: 64 amplitude samples, each 0–100
WAVEFORM_SAMPLES = 64
WAVEFORM_MAX = 100


# ---------------------------------------------------------------------------
# Audio loading
# ---------------------------------------------------------------------------

def load_audio_samples(path: Path, num_samples: int) -> tuple[list[float], float]:
    """
    Extract `num_samples` evenly-spaced RMS amplitude values and total duration
    from an audio file using ffmpeg.

    Returns (amplitudes, duration_seconds).
    Each amplitude is a float in [0.0, 1.0].
    """
    # Get duration first
    duration = _probe_duration(path)

    # Resample to mono 8kHz, split into equal chunks via astats filter
    # We generate num_samples chunks and read the RMS from each
    chunk_duration = duration / num_samples

    cmd = [
        "ffmpeg", "-v", "error",
        "-i", str(path),
        "-af", f"asetnsamples=n={int(8000 * chunk_duration)},astats=metadata=1:reset=1",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    amplitudes = _parse_rms_from_stderr(result.stderr, num_samples)
    return amplitudes, duration


def _probe_duration(path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _parse_rms_from_stderr(stderr: str, expected: int) -> list[float]:
    """
    Parse RMS_level values from ffmpeg astats filter output.
    Falls back to zeros if parsing fails.
    """
    import re
    # astats outputs lines like: lavfi.astats.Overall.RMS_level=-20.5
    matches = re.findall(r"RMS_level=(-?\d+\.?\d*)", stderr)

    if not matches:
        return [0.0] * expected

    # Convert dBFS to linear [0, 1]; silence is around -91 dBFS
    DB_FLOOR = -60.0
    amplitudes = []
    for db_str in matches:
        db = float(db_str)
        if db <= DB_FLOOR or db == float("-inf"):
            amplitudes.append(0.0)
        else:
            linear = 10 ** ((db - 0) / 20)  # 0 dBFS = 1.0
            amplitudes.append(min(1.0, max(0.0, linear)))

    # Pad or trim to expected count
    if len(amplitudes) < expected:
        amplitudes += [0.0] * (expected - len(amplitudes))
    return amplitudes[:expected]


# ---------------------------------------------------------------------------
# Waveform computation
# ---------------------------------------------------------------------------

def compute_waveform(amplitudes: list[float]) -> bytes:
    """
    Scale amplitudes to 0–100 integers and return as a bytes object.
    This is the format expected in the WhatsApp protobuf `waveform` field.
    """
    scaled = [int(round(a * WAVEFORM_MAX)) for a in amplitudes]
    return bytes(scaled)


def waveform_to_base64(waveform: bytes) -> str:
    """Encode waveform bytes as base64 string for use in the Business API."""
    return base64.b64encode(waveform).decode("ascii")


# ---------------------------------------------------------------------------
# Audio conversion
# ---------------------------------------------------------------------------

def convert_to_ogg_opus(src: Path, dst: Path, bitrate: str) -> None:
    """
    Convert `src` to OGG/Opus at the given bitrate, writing to `dst`.
    Raises subprocess.CalledProcessError on ffmpeg failure.
    """
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(src),
        "-c:a", "libopus",
        "-b:a", bitrate,
        "-vbr", "on",
        "-compression_level", "10",
        "-ar", "48000",
        "-ac", "1",        # mono — WhatsApp voice notes are always mono
        str(dst),
    ]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# Output manifest
# ---------------------------------------------------------------------------

def build_manifest(
    src: Path,
    ogg_path: Path,
    waveform: bytes,
    duration: float,
) -> dict:
    """
    Build a JSON-serialisable dict with all fields needed to send a WhatsApp
    voice note via the Business API.
    """
    return {
        "source_file": str(src),
        "ogg_file": str(ogg_path),
        "mimetype": "audio/ogg; codecs=opus",
        "ptt": True,
        "seconds": int(round(duration)),
        "waveform": waveform_to_base64(waveform),
        "waveform_raw": list(waveform),   # human-readable for debugging
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def process_file(src: Path, output_dir: Path, bitrate: str) -> None:
    """Convert one audio file and write its OGG + manifest."""
    print(f"  Processing: {src.name}")

    ogg_path = output_dir / f"{src.stem}.ogg"
    manifest_path = output_dir / f"{src.stem}.waveform.json"

    print(f"    Converting to OGG/Opus ({bitrate})…")
    convert_to_ogg_opus(src, ogg_path, bitrate)

    print(f"    Computing waveform…")
    amplitudes, duration = load_audio_samples(ogg_path, WAVEFORM_SAMPLES)
    waveform = compute_waveform(amplitudes)

    manifest = build_manifest(src, ogg_path, waveform, duration)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    print(f"    -> {ogg_path}")
    print(f"    -> {manifest_path}  (duration: {manifest['seconds']}s, ptt: true)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare audio files for WhatsApp sharing (OGG/Opus + waveform)."
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="Audio files to convert.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for output files (default: same directory as each input file).",
    )
    parser.add_argument(
        "--bitrate",
        default="64k",
        help="Opus bitrate (default: 64k). Use 32k for speech, 96k+ for music.",
    )
    args = parser.parse_args()

    # Validate inputs
    files = [f for f in args.files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    unsupported = [f for f in args.files if f.suffix.lower() not in SUPPORTED_EXTENSIONS]
    for f in unsupported:
        print(f"  SKIP (unsupported format): {f}", file=sys.stderr)

    if not files:
        print("No supported audio files provided.", file=sys.stderr)
        sys.exit(1)

    _check_ffmpeg()

    for src in files:
        output_dir = args.output_dir or src.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            process_file(src, output_dir, args.bitrate)
        except Exception as exc:
            print(f"  ERROR: {src.name}: {exc}", file=sys.stderr)

    print("\nDone.")


def _check_ffmpeg() -> None:
    """Exit early with a helpful message if ffmpeg/ffprobe are missing."""
    for tool in ("ffmpeg", "ffprobe"):
        result = subprocess.run(["which", tool], capture_output=True)
        if result.returncode != 0:
            print(
                f"ERROR: '{tool}' not found.\n"
                "Install it with:\n"
                "    sudo apt install ffmpeg   # Debian/Ubuntu\n"
                "    brew install ffmpeg       # macOS",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
