"""
run.py — CLI orchestrator for the video production pipeline.

Modes
-----
  creative       Run 24-skill AI pipeline from an idea → output instance JSON only.
  creative+render  Run skills → generate → assemble → final video (default for --idea).
  render         Generate + assemble from a pre-built instance JSON → final video.
  refine         Re-run specific skills on an existing instance, then re-render.
  check          Validate an instance JSON against the schema (no generation).

Flags
-----
  --dry-run      Simulate everything: print what WOULD happen without calling APIs
                 or writing media files. Shows prompts, reference plan, and assembly
                 steps. Useful for cost estimation and prompt review.
  --stub-only    Generate real pipeline but use FFmpeg stubs instead of AI APIs.

Usage
-----
  # Creative only — AI writes the script, stops before rendering:
  python -m pipeline.run --idea "A robot learning to paint" --creative-only

  # Full pipeline — idea → AI script → generate → assemble:
  python -m pipeline.run --idea "A robot learning to paint"

  # Render only — from existing instance JSON:
  python -m pipeline.run render instance.json

  # Refine — re-run specific skills then re-render:
  python -m pipeline.run refine instance.json --start-from s07-director

  # Dry run — see what would happen without spending API credits:
  python -m pipeline.run --idea "A robot" --dry-run
  python -m pipeline.run render instance.json --dry-run

  # Check — validate instance only:
  python -m pipeline.run check instance.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env before anything else
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    for _env_candidate in [
        Path(__file__).parents[2] / ".env",
        Path(__file__).parents[1] / ".env",
        Path(__file__).parent / ".env",
    ]:
        if _env_candidate.exists():
            load_dotenv(_env_candidate, override=True)
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Configure logging
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
    from pipeline import skills as skills_module
    from pipeline.derive import ensure_shots, ensure_audio
except ModuleNotFoundError:
    # Allow running as `python pipeline/run.py` from session-02/
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from pipeline.generate import generate_audio, generate_shots
    from pipeline.assemble import assemble
    from pipeline import skills as skills_module
    from pipeline.derive import ensure_shots, ensure_audio


# ---------------------------------------------------------------------------
# Schema validation helper
# ---------------------------------------------------------------------------

_V3_SCHEMA = Path(__file__).parent.parent / "schemas" / "active" / "gvpp-v3.schema.json"


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

def _run_creative(idea: str, output_dir: Path, *, stub_only: bool, start_from: str | None, verbose: bool) -> dict:
    """Run the 24-skill AI pipeline from an idea. Returns the v3 instance."""
    log.info("─── %s ───", "skills_pipeline")
    log.info("Idea: %s", idea)

    try:
        v3_instance = skills_module.run_pipeline(
            idea,
            output_dir=output_dir,
            stub_media=stub_only,
            save_progress=True,
            start_from=start_from,
        )
    except Exception as exc:
        log.error("Skills pipeline failed: %s", exc, exc_info=verbose)
        raise

    instance_path = output_dir / "instance.json"
    instance_path.write_text(
        json.dumps(v3_instance, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("v3 instance saved → %s", instance_path)
    return v3_instance


def _run_derive(instance: dict) -> dict:
    """Derive shots/audio from story beats if production is empty."""
    log.info("─── %s ───", "derive")
    n_shots_before = len((instance.get("production") or {}).get("shots") or [])
    n_audio_before = len((instance.get("assetLibrary") or {}).get("audioAssets") or [])

    instance = ensure_shots(instance)
    instance = ensure_audio(instance)

    n_shots_after = len((instance.get("production") or {}).get("shots") or [])
    n_audio_after = len((instance.get("assetLibrary") or {}).get("audioAssets") or [])

    if n_shots_after > n_shots_before:
        log.info("Derived %d shots across %d scenes", n_shots_after,
                 len((instance.get("production") or {}).get("scenes") or []))
    else:
        log.info("production.shots already populated (%d shots)", n_shots_after)

    if n_audio_after > n_audio_before:
        log.info("Derived %d audio assets", n_audio_after)
    else:
        log.info("assetLibrary.audioAssets already populated (%d assets)", n_audio_after)

    return instance


def _run_render(instance: dict, output_dir: Path, *, verbose: bool) -> Path:
    """Generate assets + assemble final video. Returns path to final mp4."""
    # ── Generate shots + audio in parallel ────────────────────────────────
    t_gen_start = time.perf_counter()
    log.info("─── %s ───", "generation")

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
        raise RuntimeError(f"Generation failed: {gen_error}")

    t_gen = time.perf_counter() - t_gen_start
    log.info("Generation complete: %d shot(s), %d audio track(s) in %.1fs", len(shot_clips),
        len(audio_files), time.perf_counter() - t_gen_start)

    # ── Assemble ──────────────────────────────────────────────────────────
    log.info("─── %s ───", "assembly")
    t_asm = time.perf_counter()

    final_path = assemble(instance, output_dir, shot_clips, audio_files)

    t_asm_elapsed = time.perf_counter() - t_asm
    log.info("Assembly complete in %.1fs", t_asm_elapsed)

    return final_path


def _run_dry(instance: dict, output_dir: Path) -> None:
    """Dry run: print what WOULD happen without calling APIs."""
    production = instance.get("production") or {}
    asset_lib = instance.get("assetLibrary") or {}
    assembly = instance.get("assembly") or {}

    chars = production.get("characters", [])
    envs = production.get("environments", [])
    props = production.get("props", [])
    shots = production.get("shots", [])
    scenes = production.get("scenes", [])
    audio = asset_lib.get("audioAssets", [])
    timelines = assembly.get("timelines", [])
    render_plans = assembly.get("renderPlans", [])

    print("\n" + "=" * 60)
    print("  DRY RUN — No APIs will be called, no files written")
    print("=" * 60)

    print(f"\n  Project: {(instance.get('project') or {}).get('name', '?')}")
    print(f"  Schema:  {instance.get('schemaVersion', '?')}")

    # ── S13 References ────────────────────────────────────────────────────
    print(f"\n  --- S13 Reference Images ---")
    for c in chars:
        print(f"  [CHAR]  {c.get('name','?')} → 3 sprite views (front, 3/4, full body)")
    for e in envs:
        print(f"  [ENV]   {e.get('name','?')} → 2 plates (wide, detail)")
    for p in props:
        print(f"  [PROP]  {p.get('name','?')} → 2 sprite views (front, 3/4)")

    # Count POV pairs
    pov_pairs: set[str] = set()
    for scene in scenes:
        env_id = (scene.get("environmentRef") or {}).get("id", "")
        for cr in scene.get("characterRefs", []):
            pov_pairs.add(f"{cr.get('id','')}:{env_id}")
    print(f"  [POV]   {len(pov_pairs)} POV plate(s)")

    total_refs = len(chars) * 3 + len(envs) * 2 + len(props) * 2 + len(pov_pairs)
    print(f"  TOTAL:  {total_refs} reference images (est. ${total_refs * 0.04:.2f} DALL-E / ${total_refs * 0.03:.2f} Imagen)")

    # ── Shots ─────────────────────────────────────────────────────────────
    print(f"\n  --- Video Shots ---")
    total_dur = 0
    for shot in shots:
        dur = shot.get("targetDurationSec", 5)
        total_dur += dur
        spec = shot.get("cinematicSpec") or {}
        print(f"  [{shot.get('logicalId','?'):16}] {dur}s  {spec.get('shotType','?'):12} {spec.get('cameraMovement','?'):8} {spec.get('focalLengthMm','')}mm")
    print(f"  TOTAL:  {len(shots)} shots, {total_dur}s (est. ${total_dur * 0.75:.2f} Veo / ${total_dur * 0.50:.2f} Runway)")

    # ── Audio ─────────────────────────────────────────────────────────────
    print(f"\n  --- Audio Assets ---")
    for a in audio:
        atype = a.get("audioType", "?")
        name = a.get("name", "?")
        transcript = a.get("transcript", "")
        provider = "ElevenLabs TTS" if atype in ("dialogue", "voice_over") and transcript else \
                   "ElevenLabs SFX" if atype in ("sfx", "ambient") else \
                   "ElevenLabs Music" if atype == "music" else "stub"
        print(f"  [{atype:10}] {name:40} → {provider}")
    print(f"  TOTAL:  {len(audio)} audio tracks")

    # ── Assembly ──────────────────────────────────────────────────────────
    print(f"\n  --- Assembly ---")
    if timelines:
        tl = timelines[0]
        print(f"  Timeline: {tl.get('durationSec','?')}s, {len(tl.get('videoClips',[]))} video clips, {len(tl.get('audioClips',[]))} audio clips")
    if render_plans:
        rp = render_plans[0]
        ops = [op.get("opType","?") for op in rp.get("operations", [])]
        print(f"  Render plan: {' → '.join(ops)}")
        for op in rp.get("operations", []):
            if op.get("opType") == "audioMix":
                for t in op.get("tracks", []):
                    ref_id = (t.get("audioRef") or {}).get("id", "?")
                    print(f"    audio: {ref_id:30} gainDb={t.get('gainDb',0)}")
            if op.get("opType") == "encode":
                comp = op.get("compression", {})
                print(f"    encode: {comp.get('codec','?')} @ {comp.get('bitrateMbps','?')}Mbps")

    di = (instance.get("canonicalDocuments") or {}).get("directorInstructions") or {}
    print(f"  Color direction: {di.get('colorDirection', 'none')}")
    print(f"  Output dir: {output_dir.resolve()}")
    print(f"\n  No APIs called. No files written.\n")


def _run_render_scene(instance: dict, output_dir: Path, scene_id: str, *, verbose: bool) -> Path:
    """Render a single scene independently. Returns path to scene MP4."""
    from pipeline.scene_splitter import split_instance_by_scene
    from pipeline.assemble import assemble_scene

    log.info("─── %s ───", "scene_render")
    log.info("Scene: %s", scene_id)

    contexts = split_instance_by_scene(instance)
    target = None
    for ctx in contexts:
        ctx_id = ctx.scene.get("id") or ctx.scene.get("logicalId") or ""
        if ctx_id == scene_id:
            target = ctx
            break

    if target is None:
        available = [c.scene.get("id", "?") for c in contexts]
        raise ValueError(f"Scene '{scene_id}' not found. Available: {available}")

    # Generate only this scene's shots + audio
    t_gen = time.perf_counter()
    log.info("─── %s ───", "generation (scene-scoped)")

    shot_clips: dict[str, Path] = {}
    audio_files: dict[str, Path] = {}

    def _gen_shots():
        return generate_shots(instance, output_dir, scene_filter=scene_id)

    def _gen_audio():
        return generate_audio(instance, output_dir, scene_filter=scene_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_shots = pool.submit(_gen_shots)
        fut_audio = pool.submit(_gen_audio)
        for fut in as_completed([fut_shots, fut_audio]):
            result = fut.result()
            if fut is fut_shots:
                shot_clips = result
            else:
                audio_files = result

    log.info("Scene generation: %d shots, %d audio in %.1fs",
             len(shot_clips), len(audio_files), time.perf_counter() - t_gen)

    # Assemble single scene
    log.info("─── %s ───", "assembly (scene)")
    return assemble_scene(target, shot_clips, audio_files, output_dir)


def _run_render_parallel(instance: dict, output_dir: Path, *, verbose: bool) -> Path:
    """Render all scenes in parallel, then stitch. Returns path to final MP4."""
    from pipeline.scene_splitter import split_instance_by_scene
    from pipeline.assemble import assemble_scene, stitch_scenes

    log.info("─── %s ───", "parallel_scene_render")

    contexts = split_instance_by_scene(instance)
    if not contexts:
        raise RuntimeError("No scenes found in instance")

    log.info("Splitting into %d independent scene renders", len(contexts))

    # ── Step 1: Generate ALL shots + audio (shared across scenes) ─────────
    t_gen = time.perf_counter()
    log.info("─── %s ───", "generation (all)")

    shot_clips: dict[str, Path] = {}
    audio_files: dict[str, Path] = {}

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_shots = pool.submit(generate_shots, instance, output_dir)
        fut_audio = pool.submit(generate_audio, instance, output_dir)
        for fut in as_completed([fut_shots, fut_audio]):
            result = fut.result()
            if fut is fut_shots:
                shot_clips = result
            else:
                audio_files = result

    log.info("Generation complete: %d shots, %d audio in %.1fs",
             len(shot_clips), len(audio_files), time.perf_counter() - t_gen)

    # ── Step 2: Assemble each scene independently ─────────────────────────
    log.info("─── %s ───", "assembly (per-scene)")
    t_asm = time.perf_counter()

    scene_segments: list[Path] = [None] * len(contexts)  # type: ignore[list-item]
    errors: list[str] = []

    def _assemble_one(idx: int, ctx) -> tuple[int, Path]:
        return idx, assemble_scene(ctx, shot_clips, audio_files, output_dir)

    with ThreadPoolExecutor(max_workers=min(len(contexts), 4)) as pool:
        futures = {
            pool.submit(_assemble_one, i, ctx): i
            for i, ctx in enumerate(contexts)
        }
        for fut in as_completed(futures):
            try:
                idx, path = fut.result()
                scene_segments[idx] = path
            except Exception as exc:
                i = futures[fut]
                errors.append(f"scene-{i}: {exc}")
                log.error("scene_assembly_failed", scene_index=i, error=str(exc))

    if errors:
        raise RuntimeError(f"Scene assembly failed: {'; '.join(errors)}")

    log.info("All %d scenes assembled in %.1fs", len(contexts), time.perf_counter() - t_asm)

    # ── Step 3: Stitch scenes together ────────────────────────────────────
    log.info("─── %s ───", "stitch")
    transitions: list[dict] = []
    for i in range(len(contexts) - 1):
        tail = contexts[i].transition_tail
        transitions.append({"type": tail.type, "durationSec": tail.duration_sec})

    return stitch_scenes(scene_segments, transitions, output_dir, instance)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SAFE AI Production — Video Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Modes:
  --idea "text"                  creative + render (default: full pipeline)
  --idea "text" --creative-only  creative only (output instance JSON, no render)
  render instance.json           render only (generate + assemble from JSON)
  refine instance.json           re-run skills from --start-from, then render
  check instance.json            validate instance against schema only

Options:
  --dry-run            show what WOULD happen, no API calls, no files written
  --stub-only          real pipeline but FFmpeg stubs instead of AI APIs
  --start-from X       resume skills from skill X (e.g. s07-director)
  --scene SCENE_ID     render only this scene (e.g. scene-01)
  --parallel-scenes    render all scenes independently, then stitch

Examples:
  python -m pipeline.run --idea "A robot learning to paint"
  python -m pipeline.run --idea "A robot learning to paint" --creative-only
  python -m pipeline.run --idea "A robot learning to paint" --dry-run
  python -m pipeline.run render demo-30s.json
  python -m pipeline.run render demo-30s.json --dry-run
  python -m pipeline.run render demo-30s.json --stub-only
  python -m pipeline.run render demo-30s.json --scene scene-02
  python -m pipeline.run render demo-30s.json --parallel-scenes
  python -m pipeline.run refine output/instance.json --start-from s07-director
  python -m pipeline.run check demo-30s.json
""",
    )

    sub = parser.add_subparsers(dest="command")

    # ── render subcommand ─────────────────────────────────────────────────
    p_render = sub.add_parser("render", help="Generate + assemble from an instance JSON.")
    p_render.add_argument("instance", metavar="INSTANCE_JSON")

    # ── refine subcommand ─────────────────────────────────────────────────
    p_refine = sub.add_parser("refine", help="Re-run skills on an existing instance, then render.")
    p_refine.add_argument("instance", metavar="INSTANCE_JSON")

    # ── check subcommand ──────────────────────────────────────────────────
    p_check = sub.add_parser("check", help="Validate instance JSON against schema.")
    p_check.add_argument("instance", metavar="INSTANCE_JSON")

    # ── --idea (creative mode, top-level) ─────────────────────────────────
    parser.add_argument("--idea", metavar="TEXT",
                        help="Run 24-skill AI pipeline from a one-sentence idea.")
    parser.add_argument("--creative-only", action="store_true",
                        help="Stop after creative phase — output instance JSON, no render.")

    # ── Common options ────────────────────────────────────────────────────
    for p in (parser, p_render, p_refine, p_check):
        p.add_argument("--output-dir", default="./output", metavar="DIR",
                        help="Output directory (default: ./output).")
        p.add_argument("--dry-run", action="store_true",
                        help="Show what would happen — no API calls, no files.")
        p.add_argument("--stub-only", action="store_true",
                        help="FFmpeg stubs instead of real AI APIs.")
        p.add_argument("--skip-validation", action="store_true",
                        help="Skip JSON Schema validation.")
        p.add_argument("--start-from", metavar="SKILL_ID", default=None,
                        help="Resume pipeline from a specific skill.")
        p.add_argument("--scene", metavar="SCENE_ID", default=None,
                        help="Render only this scene (e.g. scene-01).")
        p.add_argument("--parallel-scenes", action="store_true",
                        help="Render all scenes independently, then stitch.")
        p.add_argument("--schema", default=str(_V3_SCHEMA), metavar="SCHEMA_JSON",
                        help="Path to v3 JSON Schema file.")
        p.add_argument("-v", "--verbose", action="store_true",
                        help="Enable DEBUG logging.")

    args = parser.parse_args(argv)

    # ── Require at least one mode ─────────────────────────────────────────
    if not args.command and not args.idea:
        parser.print_help()
        return 1

    # ── Validate mutually exclusive flags ─────────────────────────────────
    if getattr(args, "scene", None) and getattr(args, "parallel_scenes", False):
        log.error("--scene and --parallel-scenes are mutually exclusive")
        return 1

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Build ID (UUID) ──────────────────────────────────────────────────
    build_id = uuid.uuid4().hex[:12]

    # ── Persist all log output to {output_dir}/build-{id}.log ────────────
    _build_log_path = output_dir / f"build-{build_id}.log"
    _build_log_file = open(_build_log_path, "w", encoding="utf-8")  # noqa: SIM115

    # stdlib logging → file (in addition to console)
    _file_handler = logging.FileHandler(_build_log_path, mode="a", encoding="utf-8")
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger().addHandler(_file_handler)

    # structlog → tee to both stderr (console) and build log file
    try:
        import structlog  # noqa: PLC0415

        class _TeeLoggerFactory:
            """Write structlog output to both stderr and the build log file."""
            def __init__(self, log_file):
                self._file = log_file
            def __call__(self, *args, **kwargs):
                return self._TeeLogger(self._file)
            class _TeeLogger:
                def __init__(self, log_file):
                    self._file = log_file
                def msg(self, message: str) -> None:
                    sys.stderr.write(message + "\n")
                    sys.stderr.flush()
                    self._file.write(message + "\n")
                    self._file.flush()
                def __getattr__(self, name):
                    return self.msg

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            logger_factory=_TeeLoggerFactory(_build_log_file),
        )
    except (ImportError, Exception):
        pass  # structlog not available or already configured

    log.info("Build ID: %s", build_id)
    log.info("Output directory: %s", output_dir.resolve())
    log.info("Build log: %s", _build_log_path.name)

    # ── Stub-only: clear API keys ─────────────────────────────────────────
    if args.stub_only:
        for key in (
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY",
            "GEMINI_API_KEY", "RUNWAY_API_KEY", "ELEVENLABS_API_KEY", "SUNO_COOKIE",
        ):
            os.environ.pop(key, None)
        log.info("stub-only mode: all API keys cleared")

    t_start = time.perf_counter()

    # ══════════════════════════════════════════════════════════════════════
    # MODE: check — validate only
    # ══════════════════════════════════════════════════════════════════════
    if args.command == "check":
        instance_path = Path(args.instance)
        if not instance_path.exists():
            log.error("File not found: %s", instance_path)
            return 1
        instance = json.loads(instance_path.read_text(encoding="utf-8"))
        schema_path = Path(args.schema)
        errors = _validate(instance, schema_path)
        if errors:
            print(f"\n  ✗ {len(errors)} validation error(s):")
            for e in errors[:20]:
                print(f"    • {e}")
            return 1
        prod = instance.get("production") or {}
        print(f"\n  ✓ Valid v3 instance")
        print(f"    Scenes: {len(prod.get('scenes',[]))}  Shots: {len(prod.get('shots',[]))}  "
              f"Audio: {len((instance.get('assetLibrary') or {}).get('audioAssets',[]))}")
        return 0

    # ══════════════════════════════════════════════════════════════════════
    # LOAD INSTANCE (for render / refine / dry-run modes)
    # ══════════════════════════════════════════════════════════════════════
    instance = None

    if args.command in ("render", "refine"):
        instance_path = Path(args.instance)
        if not instance_path.exists():
            log.error("File not found: %s", instance_path)
            return 1
        log.info("Loading instance: %s", instance_path)
        instance = json.loads(instance_path.read_text(encoding="utf-8"))

        if not args.skip_validation:
            errors = _validate(instance, Path(args.schema))
            if errors:
                log.warning("Schema validation: %d issue(s) (continuing)", len(errors))
                for e in errors[:5]:
                    log.warning("  • %s", e)

    # ══════════════════════════════════════════════════════════════════════
    # CREATIVE PHASE (--idea or refine)
    # ══════════════════════════════════════════════════════════════════════
    if args.idea:
        if args.dry_run:
            # Dry run for --idea: show what the pipeline WOULD generate
            print("\n" + "=" * 60)
            print("  DRY RUN — Creative phase")
            print("=" * 60)
            print(f"\n  Idea: {args.idea}")
            print(f"  Mode: {'creative only' if args.creative_only else 'creative + render'}")
            print(f"  Output: {output_dir.resolve()}")
            print(f"  Skills: S01-S24 (24 skills, ~15-40 min)")
            print(f"  Provider: Claude → OpenAI → Gemini → DeepSeek → Grok")
            if args.creative_only:
                print(f"\n  Would output: {output_dir / 'instance.json'}")
            else:
                print(f"\n  After creative: would generate refs, shots, audio, and assemble")
            print(f"\n  No APIs called. No files written.\n")
            return 0

        try:
            instance = _run_creative(
                args.idea, output_dir,
                stub_only=args.stub_only,
                start_from=args.start_from,
                verbose=args.verbose,
            )
        except Exception:
            return 1

        t_skills = time.perf_counter() - t_start
        log.info("Skills pipeline complete in %.1fs", t_skills)

        if args.creative_only:
            print(f"\n✓ Creative phase complete → {output_dir / 'instance.json'}")
            return 0

    elif args.command == "refine":
        # Re-run skills on existing instance
        if not args.start_from:
            log.error("refine mode requires --start-from (e.g. --start-from s07-director)")
            return 1
        try:
            instance = _run_creative(
                "",  # no idea — uses existing instance context
                output_dir,
                stub_only=args.stub_only,
                start_from=args.start_from,
                verbose=args.verbose,
            )
        except Exception:
            return 1

    # ══════════════════════════════════════════════════════════════════════
    # DRY RUN — show plan and exit
    # ══════════════════════════════════════════════════════════════════════
    if args.dry_run:
        if instance is None:
            log.error("No instance available for dry run")
            return 1
        instance = _run_derive(instance)
        _run_dry(instance, output_dir)
        return 0

    # ══════════════════════════════════════════════════════════════════════
    # DERIVE + RENDER + ASSEMBLE
    # ══════════════════════════════════════════════════════════════════════
    if instance is None:
        log.error("No instance — use --idea or provide an instance JSON")
        return 1

    instance = _run_derive(instance)

    scene_id = getattr(args, "scene", None)
    parallel = getattr(args, "parallel_scenes", False)

    # ── Single-scene render ──────────────────────────────────────────────
    if scene_id:
        try:
            final_path = _run_render_scene(instance, output_dir, scene_id, verbose=args.verbose)
        except Exception as exc:
            log.error("Scene render failed: %s", exc)
            return 1
    # ── Parallel-scene render ────────────────────────────────────────────
    elif parallel:
        try:
            final_path = _run_render_parallel(instance, output_dir, verbose=args.verbose)
        except Exception as exc:
            log.error("Parallel render failed: %s", exc)
            return 1
    # ── Monolithic render (default) ──────────────────────────────────────
    else:
        try:
            final_path = _run_render(instance, output_dir, verbose=args.verbose)
        except Exception as exc:
            log.error("Render failed: %s", exc)
            return 1

    t_total = time.perf_counter() - t_start

    if final_path.exists():
        size_mb = final_path.stat().st_size / 1_048_576
        log.info("  Build ID    : %s", build_id)
        log.info("  Total time  : %.1fs", t_total)
        log.info("  Output      : %s", final_path.resolve())
        log.info("  File size   : %.2f MB", size_mb)
        print(f"\n✓ Render complete → {final_path.resolve()}  ({size_mb:.2f} MB)")
        print(f"  Build ID: {build_id}")
        print(f"  Log: {_build_log_path.name}")
    else:
        log.warning("Output file missing: %s", final_path)
        print(f"\n⚠ Assembly returned {final_path} but file does not exist")

    # ── Write build manifest ─────────────────────────────────────────────
    from datetime import datetime, timezone
    build_manifest = {
        "buildId": build_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": " ".join(sys.argv),
        "instance": str(Path(args.instance).resolve()) if hasattr(args, "instance") and args.instance else None,
        "outputDir": str(output_dir.resolve()),
        "log": _build_log_path.name,
        "output": final_path.name if final_path.exists() else None,
        "sizeMB": round(size_mb, 2) if final_path.exists() else None,
        "durationSec": round(t_total, 1),
        "stubOnly": args.stub_only,
    }
    (output_dir / f"build-{build_id}.json").write_text(
        json.dumps(build_manifest, indent=2), encoding="utf-8"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
