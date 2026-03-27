"""
run.py — CLI orchestrator for the video production pipeline.

Usage
-----
  python -m pipeline.run <instance.json> [--output-dir ./output] [--stub-only]

Steps
-----
  1. Load and validate the schema instance (jsonschema Draft 2020-12)
  2. Generate shot clips  ┐ in parallel via ThreadPoolExecutor
     Generate audio files ┘
  3. Assemble: load → overlay_audio → color_grade → encode (FFmpeg)
  4. Print summary: elapsed time, output path, asset counts
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# Configure logging early so imported modules can use it
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline.run")

# ---------------------------------------------------------------------------
# Local imports (after sys.path adjustment when run as __main__)
# ---------------------------------------------------------------------------
try:
    from pipeline.generate import generate_audio, generate_shots
    from pipeline.assemble import assemble
except ModuleNotFoundError:
    # Allow running as `python pipeline/run.py` from session-02/
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.generate import generate_audio, generate_shots
    from pipeline.assemble import assemble


# ---------------------------------------------------------------------------
# Schema validation helper
# ---------------------------------------------------------------------------

_DEFAULT_SCHEMA = Path(__file__).parent.parent / "video-project-schema-v2.json"


def _validate(instance: dict, schema_path: Path) -> list[str]:
    """Return a list of validation error messages (empty = valid)."""
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:
        log.warning("jsonschema not installed — skipping validation")
        return []

    if not schema_path.exists():
        log.warning("Schema not found at %s — skipping validation", schema_path)
        return []

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(instance)]


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate and assemble a video from a schema instance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "instance",
        metavar="INSTANCE_JSON",
        help="Path to the video project instance JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        metavar="DIR",
        help="Directory for generated assets and final render (default: ./output).",
    )
    parser.add_argument(
        "--schema",
        default=str(_DEFAULT_SCHEMA),
        metavar="SCHEMA_JSON",
        help="Path to the JSON Schema file for validation.",
    )
    parser.add_argument(
        "--stub-only",
        action="store_true",
        help="Force stub generation even if API keys are set.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip JSON Schema validation of the instance.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG logging.",
    )

    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── 0. Load instance ────────────────────────────────────────────────────
    instance_path = Path(args.instance)
    if not instance_path.exists():
        log.error("Instance file not found: %s", instance_path)
        return 1

    log.info("Loading instance: %s", instance_path)
    instance = json.loads(instance_path.read_text(encoding="utf-8"))

    # ── 1. Validate ─────────────────────────────────────────────────────────
    if not args.skip_validation:
        schema_path = Path(args.schema)
        errors = _validate(instance, schema_path)
        if errors:
            log.error("Schema validation failed (%d error(s)):", len(errors))
            for e in errors[:10]:
                log.error("  • %s", e)
            if len(errors) > 10:
                log.error("  … and %d more", len(errors) - 10)
            return 1
        log.info("Schema validation passed ✓")

    # ── 2. Prepare output directory ─────────────────────────────────────────
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", output_dir.resolve())

    # ── 3. Stub-only mode: clear API keys from environment ───────────────────
    if args.stub_only:
        for key in ("RUNWAY_API_KEY", "ELEVENLABS_API_KEY", "SUNO_COOKIE"):
            os.environ.pop(key, None)
        log.info("stub-only mode: API keys cleared")

    # ── 4. Generate shots + audio in parallel ────────────────────────────────
    t_start = time.perf_counter()
    log.info("─── Generation phase ───────────────────────────────────────────")

    shot_clips: dict[str, Path] = {}
    audio_files: dict[str, Path] = {}
    gen_error: Exception | None = None

    def _gen_shots() -> dict[str, Path]:
        return generate_shots(instance, output_dir)

    def _gen_audio() -> dict[str, Path]:
        return generate_audio(instance, output_dir)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_shots = pool.submit(_gen_shots)
        fut_audio = pool.submit(_gen_audio)
        for fut in as_completed([fut_shots, fut_audio]):
            try:
                result = fut.result()
                if fut is fut_shots:
                    shot_clips = result
                else:
                    audio_files = result
            except Exception as exc:
                log.error("Generation error: %s", exc)
                gen_error = exc

    if gen_error:
        log.error("Aborting due to generation error.")
        return 1

    t_gen = time.perf_counter() - t_start
    log.info(
        "Generation complete: %d shot(s), %d audio track(s) in %.1fs",
        len(shot_clips), len(audio_files), t_gen,
    )

    # ── 5. Assemble ──────────────────────────────────────────────────────────
    log.info("─── Assembly phase ─────────────────────────────────────────────")
    t_asm = time.perf_counter()

    try:
        final_path = assemble(instance, output_dir, shot_clips, audio_files)
    except Exception as exc:
        log.error("Assembly failed: %s", exc, exc_info=args.verbose)
        return 1

    t_asm_elapsed = time.perf_counter() - t_asm
    t_total = time.perf_counter() - t_start

    # ── 6. Summary ───────────────────────────────────────────────────────────
    log.info("─── Summary ────────────────────────────────────────────────────")
    log.info("  Instance    : %s", instance_path.name)
    log.info("  Shots       : %d", len(shot_clips))
    log.info("  Audio tracks: %d", len(audio_files))
    log.info("  Gen time    : %.1fs", t_gen)
    log.info("  Asm time    : %.1fs", t_asm_elapsed)
    log.info("  Total time  : %.1fs", t_total)
    log.info("  Output      : %s", final_path.resolve())

    if final_path.exists():
        size_mb = final_path.stat().st_size / 1_048_576
        log.info("  File size   : %.2f MB", size_mb)
        print(f"\n✓ Render complete → {final_path.resolve()}  ({size_mb:.2f} MB)")
    else:
        log.warning("Output file not found at expected path: %s", final_path)
        print(f"\n⚠ Assembly returned {final_path} but file does not exist")

    return 0


if __name__ == "__main__":
    sys.exit(main())
