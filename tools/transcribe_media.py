#!/usr/bin/env python3
"""
Transcript extractor for audio/video media files using OpenAI Whisper.

Usage:
    python transcribe_media.py                          # scan current dir
    python transcribe_media.py path/to/dir              # scan a directory
    python transcribe_media.py file.mp4 file.m4a        # explicit files
    python transcribe_media.py --model large-v3 ...     # choose Whisper model
    python transcribe_media.py --output-dir transcripts # output directory
    python transcribe_media.py --format txt,json,srt    # output formats
"""

import argparse
import json
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".mp3", ".mp4", ".m4a", ".wav", ".webm",
    ".ogg", ".flac", ".mkv", ".avi", ".mov",
    ".wma", ".aac", ".opus",
}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]


def find_media_files(paths: list[Path]) -> list[Path]:
    found = []
    for p in paths:
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            found.append(p)
        elif p.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                found.extend(sorted(p.rglob(f"*{ext}")))
    return list(dict.fromkeys(found))  # deduplicate preserving order


def write_srt(segments: list[dict], path: Path) -> None:
    def fmt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with path.open("w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{fmt_time(seg['start'])} --> {fmt_time(seg['end'])}\n")
            f.write(f"{seg['text'].strip()}\n\n")


def already_processed(stem: str, output_dir: Path, formats: set[str]) -> bool:
    return all((output_dir / f"{stem}.{fmt}").exists() for fmt in formats)


def transcribe_file(
    media_path: Path,
    model,
    output_dir: Path,
    formats: set[str],
    language: str | None,
    force: bool = False,
) -> None:
    stem = media_path.stem

    if not force and already_processed(stem, output_dir, formats):
        print(f"  Skipping (already processed): {media_path.name}")
        return

    print(f"  Transcribing: {media_path.name}")

    options = {}
    if language:
        options["language"] = language

    result = model.transcribe(str(media_path), **options)

    output_dir.mkdir(parents=True, exist_ok=True)

    if "txt" in formats:
        txt_path = output_dir / f"{stem}.txt"
        txt_path.write_text(result["text"].strip(), encoding="utf-8")
        print(f"    -> {txt_path}")

    if "json" in formats:
        json_path = output_dir / f"{stem}.json"
        payload = {
            "source": str(media_path),
            "language": result.get("language"),
            "text": result["text"].strip(),
            "segments": [
                {
                    "id": s["id"],
                    "start": round(s["start"], 3),
                    "end": round(s["end"], 3),
                    "text": s["text"].strip(),
                }
                for s in result.get("segments", [])
            ],
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    -> {json_path}")

    if "srt" in formats:
        srt_path = output_dir / f"{stem}.srt"
        write_srt(result.get("segments", []), srt_path)
        print(f"    -> {srt_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract transcripts from audio/video files using Whisper."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="Files or directories to scan (default: current directory).",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=WHISPER_MODELS,
        help="Whisper model size (default: base). Larger = more accurate but slower.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("transcripts"),
        help="Directory to write transcript files (default: ./transcripts).",
    )
    parser.add_argument(
        "--format",
        default="txt",
        help="Comma-separated output formats: txt, json, srt (default: txt).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-transcribe files even if output already exists.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Force a language code, e.g. 'en', 'pt', 'de'. Auto-detected if omitted.",
    )
    args = parser.parse_args()

    formats = {f.strip().lower() for f in args.format.split(",")}
    invalid = formats - {"txt", "json", "srt"}
    if invalid:
        parser.error(f"Unknown format(s): {', '.join(invalid)}. Choose from txt, json, srt.")

    # Lazy-import so missing package gives a clear error
    try:
        import whisper
    except ImportError:
        print(
            "ERROR: 'openai-whisper' is not installed.\n"
            "Install it with:\n"
            "    pip install openai-whisper\n"
            "You also need ffmpeg:\n"
            "    sudo apt install ffmpeg   # Debian/Ubuntu\n"
            "    brew install ffmpeg       # macOS",
            file=sys.stderr,
        )
        sys.exit(1)

    media_files = find_media_files(args.paths)
    if not media_files:
        print("No supported media files found.")
        sys.exit(0)

    print(f"Found {len(media_files)} media file(s).")
    print(f"Loading Whisper model '{args.model}'...")
    model = whisper.load_model(args.model)

    for media_path in media_files:
        try:
            transcribe_file(media_path, model, args.output_dir, formats, args.language, args.force)
        except Exception as exc:
            print(f"  ERROR processing {media_path.name}: {exc}", file=sys.stderr)

    print("\nDone.")


if __name__ == "__main__":
    main()
