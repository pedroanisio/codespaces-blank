"""
skills.py — 24-skill video production pipeline executor.

Each skill maps to a SKILL.md specification in session-02/skills/.
Skills use the Claude API (primary) to generate structured JSON updates
that are deep-merged into a growing v3 schema instance.

Media-generating skills call provider APIs directly:
  S12 voice-producer      → providers.text_to_speech()
  S13 reference-asset-gen → providers.generate_image()
  S16 consistency-enforcer → providers.vision_score()

Usage
-----
  # Full pipeline from a creative idea
  from pipeline.skills import run_pipeline
  instance = run_pipeline("A lone robot discovers music in an abandoned city",
                          output_dir=Path("./output/my-project"))

  # Single skill
  from pipeline.skills import run_skill
  update = run_skill("s02-story-architect", instance)
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from pipeline import providers

log = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / "skills"

# ── skill execution order ──────────────────────────────────────────────────────
# Groups within each phase run in parallel; phases are sequential.

PIPELINE_PHASES: list[list[str]] = [
    # Phase 1 — Creative Foundation (sequential)
    ["s01-concept-seed"],
    ["s02-story-architect"],
    ["s03-scriptwriter"],
    # Phase 2 — World Building (parallel)
    ["s04-character-designer", "s05-environment-designer", "s06-prop-designer"],
    # Phase 3 — Direction (sequential)
    ["s07-director"],
    ["s08-cinematographer"],
    # Phase 4 — Scene + Audio (parallel)
    ["s09-scene-composer", "s10-music-composer", "s11-sound-designer", "s12-voice-producer"],
    # Phase 5 — Visual Generation
    ["s15-prompt-composer"],
    ["s13-reference-asset-gen"],
    ["s14-shot-video-gen"],
    ["s16-consistency-enforcer"],
    # Phase 6 — Assembly
    ["s17-timeline-assembler"],
    ["s18-post-production", "s19-audio-mixer"],
    ["s20-render-plan-builder"],
    # Phase 7 — QA + Delivery (parallel)
    ["s21-qa-validator"],
    ["s22-deliverable-packager", "s23-marketing-asset-gen"],
    # Meta
    ["s24-pipeline-orchestrator"],
]

# ── context key map ────────────────────────────────────────────────────────────
# Which top-level instance fields each skill needs to read.

_CONTEXT_MAP: dict[str, list[str]] = {
    "s01-concept-seed":       [],
    "s02-story-architect":    ["canonicalDocuments.story", "project", "qualityProfiles"],
    "s03-scriptwriter":       ["canonicalDocuments.story", "project", "qualityProfiles"],
    "s04-character-designer": ["canonicalDocuments.script", "canonicalDocuments.story", "project"],
    "s05-environment-designer": ["canonicalDocuments.script", "canonicalDocuments.story", "project"],
    "s06-prop-designer":      ["canonicalDocuments.script", "canonicalDocuments.story",
                               "production.environments"],
    "s07-director":           ["canonicalDocuments.story", "canonicalDocuments.script",
                               "production.characters", "production.environments",
                               "project", "qualityProfiles"],
    "s08-cinematographer":    ["canonicalDocuments.script", "canonicalDocuments.directorInstructions",
                               "canonicalDocuments.story", "production.characters",
                               "production.environments", "production.props", "qualityProfiles"],
    "s09-scene-composer":     ["production.shots", "canonicalDocuments.story",
                               "canonicalDocuments.script", "canonicalDocuments.directorInstructions",
                               "production.characters", "production.environments", "production.props"],
    "s10-music-composer":     ["canonicalDocuments.story", "canonicalDocuments.directorInstructions",
                               "production.scenes", "qualityProfiles"],
    "s11-sound-designer":     ["canonicalDocuments.script", "production.shots",
                               "production.scenes", "production.environments",
                               "canonicalDocuments.directorInstructions"],
    "s12-voice-producer":     ["canonicalDocuments.script", "production.characters",
                               "canonicalDocuments.directorInstructions", "qualityProfiles"],
    "s13-reference-asset-gen": ["production.characters", "production.environments",
                                "production.props", "canonicalDocuments.directorInstructions",
                                "qualityProfiles"],
    "s14-shot-video-gen":     ["production.shots", "assetLibrary.visualAssets",
                               "production.characters", "canonicalDocuments.directorInstructions",
                               "qualityProfiles"],
    "s15-prompt-composer":    ["production.characters", "production.environments",
                               "production.props", "canonicalDocuments.directorInstructions",
                               "production.shots", "qualityProfiles"],
    "s16-consistency-enforcer": ["assetLibrary.visualAssets", "production.characters",
                                 "qualityProfiles", "production.shots"],
    "s17-timeline-assembler": ["production.scenes", "production.shots",
                               "assetLibrary.visualAssets", "assetLibrary.audioAssets",
                               "canonicalDocuments.script", "qualityProfiles"],
    "s18-post-production":    ["assembly.timelines", "canonicalDocuments.directorInstructions",
                               "production.shots", "qualityProfiles"],
    "s19-audio-mixer":        ["assetLibrary.audioAssets", "assembly.timelines",
                               "qualityProfiles", "canonicalDocuments.directorInstructions"],
    "s20-render-plan-builder": ["assembly.timelines", "assembly.editVersions",
                                "qualityProfiles", "project"],
    "s21-qa-validator":       ["production.scenes", "production.shots",
                               "canonicalDocuments.directorInstructions", "qualityProfiles"],
    "s22-deliverable-packager": ["assembly.renderPlans", "project", "qualityProfiles",
                                 "canonicalDocuments.directorInstructions"],
    "s23-marketing-asset-gen": ["canonicalDocuments.story", "production.scenes",
                                "production.shots", "assetLibrary.visualAssets",
                                "assetLibrary.audioAssets", "project"],
    "s24-pipeline-orchestrator": ["project", "package", "orchestration", "relationships"],
}

_SYSTEM_PREAMBLE = """\
You are an autonomous AI skill in a video production pipeline.
Your complete specification is below. Follow it precisely.

RULES:
1. Return ONLY a valid JSON object — no prose, no markdown outside the JSON block.
2. Follow the exact schema structure described in your specification.
3. Populate every required field in your "Writes" section.
4. Use realistic, creative, professional content appropriate for the project.
5. Valid entity IDs: alphanumeric + dots, dashes, colons, underscores (max 200 chars).
6. Version states should be "draft" unless you are s24-pipeline-orchestrator.
7. Wrap JSON in ```json\\n...\\n``` markers.

YOUR SKILL SPECIFICATION:
"""


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_skill_md(skill_dir: str) -> str:
    """Load SKILL.md for a given skill directory name."""
    path = SKILLS_DIR / skill_dir / "SKILL.md"
    if not path.exists():
        log.warning("SKILL.md not found: %s", path)
        return f"# {skill_dir}\nNo specification found."
    return path.read_text(encoding="utf-8")


def _pick(obj: dict, path: str) -> Any:
    """Get value at a dot-separated path."""
    keys = path.split(".")
    val: Any = obj
    for k in keys:
        if not isinstance(val, dict):
            return None
        val = val.get(k)
    return val


def _set_path(obj: dict, path: str, value: Any) -> None:
    """Set value at a dot-separated path, creating intermediate dicts."""
    keys = path.split(".")
    d = obj
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _get_context(skill_dir: str, instance: dict) -> dict:
    """Extract only the relevant portion of the instance for a skill."""
    paths = _CONTEXT_MAP.get(skill_dir, [])
    context: dict = {}
    for path in paths:
        val = _pick(instance, path)
        if val is not None:
            _set_path(context, path, val)
    return context


def _deep_merge(base: dict, update: dict) -> dict:
    """
    Deep-merge `update` into `base`.
    - Dicts are merged recursively.
    - Lists replace (the skill owns its arrays entirely).
    - Primitives replace.
    """
    result = dict(base)
    for key, val in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _empty_instance() -> dict:
    """Return a minimal skeleton v3 schema instance."""
    return {
        "schemaVersion": "3.0.0",
        "package": {},
        "project": {},
        "qualityProfiles": [],
        "canonicalDocuments": {
            "story": {},
            "script": {},
            "directorInstructions": {},
        },
        "production": {
            "characters": [],
            "environments": [],
            "props": [],
            "scenes": [],
            "shots": [],
        },
        "assetLibrary": {
            "visualAssets": [],
            "audioAssets": [],
            "marketingAssets": [],
            "genericAssets": [],
        },
        "orchestration": {"workflows": []},
        "assembly": {
            "timelines": [],
            "editVersions": [],
            "renderPlans": [],
        },
        "deliverables": [],
        "relationships": [],
    }


# ── core skill runner ──────────────────────────────────────────────────────────

def run_skill(
    skill_dir: str,
    instance: dict,
    *,
    idea: str = "",
    output_dir: Path | None = None,
    stub_media: bool = False,
) -> dict:
    """
    Execute one skill and return a dict update to merge into the instance.

    For media-generating skills (S12, S13, S16), also writes asset files to
    output_dir/references/ and output_dir/audio/.
    """
    skill_md = _load_skill_md(skill_dir)
    system = _SYSTEM_PREAMBLE + skill_md
    context = _get_context(skill_dir, instance)

    user_parts = []
    if idea:
        user_parts.append(f'Creative idea: "{idea}"')
    if context:
        user_parts.append(
            "Current schema instance (your relevant context):\n"
            + json.dumps(context, indent=2, ensure_ascii=False)
        )
    user_parts.append(
        f"Execute the {skill_dir} skill now. "
        "Return a JSON object containing ONLY the fields you write."
    )
    user = "\n\n".join(user_parts)

    log.info("  ▶ %s — calling AI...", skill_dir)
    t0 = time.perf_counter()
    update = providers.complete_json(system, user, max_tokens=8192)
    elapsed = time.perf_counter() - t0
    log.info("  ✓ %s — %.1fs, %d top-level keys", skill_dir, elapsed, len(update))

    # Post-process media-generating skills
    if not stub_media and output_dir:
        update = _post_process(skill_dir, instance, update, output_dir)

    return update


def _post_process(
    skill_dir: str,
    instance: dict,
    update: dict,
    output_dir: Path,
) -> dict:
    """
    For skills that generate real media assets, call provider APIs and
    save files to disk; patch the update dict with file paths.
    """

    # ── S12: voice-producer — TTS for every dialogue/VO asset ─────────────────
    if skill_dir == "s12-voice-producer":
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        assets = update.get("assetLibrary", {}).get("audioAssets", [])
        for asset in assets:
            atype = asset.get("audioType", "")
            if atype not in ("dialogue", "voice_over"):
                continue
            transcript = asset.get("transcript", "")
            if not transcript:
                continue
            asset_id = asset.get("id", asset.get("logicalId", f"audio-{id(asset)}"))
            out_path = audio_dir / f"{asset_id}.mp3"
            if out_path.exists():
                continue
            # Pick voice from character voiceProfile if available
            char_id = (asset.get("characterRef") or {}).get("logicalId", "")
            voice = _resolve_voice(char_id, instance)
            log.info("    TTS: %s → %s", asset_id, out_path.name)
            mp3 = providers.text_to_speech(transcript, voice=voice)
            if mp3:
                out_path.write_bytes(mp3)
            asset["_filePath"] = str(out_path)

    # ── S13: reference-asset-gen — generate reference images ──────────────────
    elif skill_dir == "s13-reference-asset-gen":
        refs_dir = output_dir / "references"
        refs_dir.mkdir(parents=True, exist_ok=True)
        assets = update.get("assetLibrary", {}).get("visualAssets", [])
        for asset in assets:
            if not asset.get("isCanonicalReference"):
                continue
            asset_id = asset.get("id", asset.get("logicalId", f"ref-{id(asset)}"))
            out_path = refs_dir / f"{asset_id}.png"
            if out_path.exists():
                asset["_filePath"] = str(out_path)
                continue
            # Build prompt from generation steps
            steps = asset.get("generation", {}).get("steps", [])
            prompt = steps[0].get("prompt", "") if steps else ""
            if not prompt:
                prompt = f"Reference image: {asset.get('purpose', 'cinematic reference')}"
            log.info("    IMG: %s → %s", asset_id, out_path.name)
            png = providers.generate_image(prompt)
            out_path.write_bytes(png)
            asset["_filePath"] = str(out_path)

    # ── S16: consistency-enforcer — score pairs of reference images ────────────
    elif skill_dir == "s16-consistency-enforcer":
        visual_assets = instance.get("assetLibrary", {}).get("visualAssets", [])
        refs = [a for a in visual_assets if a.get("isCanonicalReference")]
        if len(refs) >= 2:
            b64_a = _load_b64(refs[0].get("_filePath", ""))
            b64_b = _load_b64(refs[1].get("_filePath", ""))
            score = providers.vision_score(b64_a, b64_b)
            log.info("    consistency score: %.3f", score)
            # Inject score into update if it has a consistency section
            update.setdefault("_consistencyScore", score)

    return update


def _resolve_voice(char_logical_id: str, instance: dict) -> str:
    """Map a character's pitch range to an OpenAI TTS voice name."""
    pitch_map = {"low": "onyx", "mid": "nova", "high": "shimmer"}
    for char in instance.get("production", {}).get("characters", []):
        if char.get("logicalId") == char_logical_id:
            pitch = char.get("voiceProfile", {}).get("pitchRange", "mid")
            return pitch_map.get(pitch, "nova")
    return "nova"


def _load_b64(file_path: str) -> str:
    """Load a file and return its base64 encoding."""
    if not file_path:
        return ""
    p = Path(file_path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode()


# ── pipeline orchestrator ─────────────────────────────────────────────────────

def run_pipeline(
    idea: str,
    *,
    output_dir: Path | None = None,
    stub_media: bool = False,
    save_progress: bool = True,
    start_from: str | None = None,
) -> dict:
    """
    Execute the full 24-skill pipeline from a creative idea.

    Parameters
    ----------
    idea        : The creative concept (free-form text).
    output_dir  : Where to save asset files and progress snapshots.
    stub_media  : Skip real image/TTS generation (faster, no API cost).
    save_progress : Save instance JSON after each phase.
    start_from  : Skill dir name to resume from (skips earlier skills).

    Returns
    -------
    dict : Fully populated v3 schema instance.
    """
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Check providers
    avail = providers.available_providers()
    configured = [k for k, v in avail.items() if v]
    if not configured:
        log.warning(
            "No AI providers configured. Set at least one API key in .env. "
            "Skills will return empty updates (stub instance only)."
        )
    else:
        log.info("Active providers: %s", ", ".join(configured))

    instance = _empty_instance()
    skipping = start_from is not None
    phase_num = 0

    for phase in PIPELINE_PHASES:
        phase_num += 1
        phase_label = ", ".join(s.split("-", 1)[1] for s in phase)

        # Resume support: skip phases until start_from skill is found
        if skipping:
            if start_from in phase:
                skipping = False
            else:
                log.info("Phase %d [%s] — skipped (resuming)", phase_num, phase_label)
                continue

        log.info("── Phase %d: %s", phase_num, phase_label)

        # Determine whether this skill is S01 (needs the idea)
        is_seed = phase == ["s01-concept-seed"]

        if len(phase) == 1:
            # Sequential — single skill
            skill = phase[0]
            update = run_skill(
                skill, instance,
                idea=idea if is_seed else "",
                output_dir=output_dir,
                stub_media=stub_media,
            )
            instance = _deep_merge(instance, update)
        else:
            # Parallel — multiple independent skills
            updates: dict[str, dict] = {}
            with ThreadPoolExecutor(max_workers=min(len(phase), 4)) as pool:
                futures = {
                    pool.submit(
                        run_skill, skill, instance,
                        idea="", output_dir=output_dir, stub_media=stub_media,
                    ): skill
                    for skill in phase
                }
                for fut in as_completed(futures):
                    skill = futures[fut]
                    try:
                        updates[skill] = fut.result()
                    except Exception as exc:
                        log.error("Skill %s failed: %s", skill, exc)
                        updates[skill] = {}

            # Merge in a deterministic order
            for skill in phase:
                instance = _deep_merge(instance, updates.get(skill, {}))

        # Save progress snapshot
        if save_progress and output_dir:
            snap = output_dir / f"instance-phase{phase_num:02d}.json"
            snap.write_text(
                json.dumps(instance, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log.debug("progress saved → %s", snap.name)

    # Final save
    if output_dir:
        final = output_dir / "instance.json"
        final.write_text(
            json.dumps(instance, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("✓ Pipeline complete → %s", final.resolve())

    return instance


# ── v3 → v2 bridge for existing assembly layer ────────────────────────────────

def bridge_v3_to_v2(instance: dict) -> dict:
    """
    Convert a v3 schema instance into a hybrid that the existing
    generate.py / assemble.py can consume (v2 field names).

    Returns the original instance unchanged if it is already v2.
    """
    if "production" not in instance:
        return instance  # already v2

    production = instance["production"]
    shots_by_id = {
        s.get("id", s.get("logicalId", "")): s
        for s in production.get("shots", [])
    }

    # Build v2-style scenes
    v2_scenes: list[dict] = []
    for scene in sorted(
        production.get("scenes", []),
        key=lambda s: s.get("sceneNumber", 0),
    ):
        scene_id = scene.get("id") or scene.get("logicalId", f"scene-{scene.get('sceneNumber', 0)}")
        v2_shots: list[dict] = []
        for i, ref in enumerate(scene.get("shotRefs", [])):
            sid = ref.get("logicalId") or ref.get("id", "")
            shot = shots_by_id.get(sid, {})
            if not shot:
                continue
            spec = shot.get("cinematicSpec") or {}
            steps = shot.get("generation", {}).get("steps", [{}])
            prompt = steps[0].get("prompt", "") if steps else ""
            v2_shots.append({
                "shot_id": shot.get("id") or shot.get("logicalId") or sid,
                "order": i,
                "label": shot.get("purpose", shot.get("description", sid)),
                "duration_sec": shot.get("targetDurationSec", 5.0),
                "cinematic_spec": {
                    "color_palette": spec.get("colorPalette", ["#1a1a2e"]),
                    "shot_type": spec.get("shotType", "MS"),
                    "camera_movement": spec.get("cameraMovement", "static"),
                },
                "gen_params": {
                    "prompt": prompt or shot.get("description", "cinematic shot"),
                    "model_id": "gen4_turbo",
                    "seed": None,
                },
            })
        v2_scenes.append({"scene_id": scene_id, "shots": v2_shots})

    # Fall back: if no scenes were built, flatten all shots into one scene
    if not v2_scenes and production.get("shots"):
        v2_shots = []
        for i, shot in enumerate(production["shots"]):
            spec = shot.get("cinematicSpec") or {}
            steps = shot.get("generation", {}).get("steps", [{}])
            prompt = steps[0].get("prompt", "") if steps else ""
            v2_shots.append({
                "shot_id": shot.get("id") or shot.get("logicalId") or f"shot-{i:03d}",
                "order": i,
                "label": shot.get("purpose", f"Shot {i+1}"),
                "duration_sec": shot.get("targetDurationSec", 5.0),
                "cinematic_spec": {
                    "color_palette": spec.get("colorPalette", ["#1a1a2e"]),
                },
                "gen_params": {
                    "prompt": prompt or shot.get("description", "cinematic shot"),
                    "model_id": "gen4_turbo",
                    "seed": None,
                },
            })
        v2_scenes = [{"scene_id": "scene-001", "shots": v2_shots}]

    # Build v2-style audio_assets dict
    v2_audio: dict[str, dict] = {}
    for asset in instance.get("assetLibrary", {}).get("audioAssets", []):
        key = asset.get("id") or asset.get("logicalId") or ""
        if not key:
            continue
        steps = asset.get("generation", {}).get("steps", [{}])
        prompt = steps[0].get("prompt", "") if steps else ""
        atype = asset.get("audioType", "ambient")
        tool = _audio_tool_from_type(atype)
        # Duration from syncPoints or targetDurationSec
        t_out = asset.get("targetDurationSec", 10.0)
        v2_audio[key] = {
            "type": atype,
            "transcript": asset.get("transcript", ""),
            "sync": {
                "timeline_in_sec": 0,
                "timeline_out_sec": t_out,
                "fade_in_sec": 0.5,
                "fade_out_sec": 1.0,
            },
            "gen_params": {
                "tool": tool,
                "prompt": prompt,
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
            "_filePath": asset.get("_filePath", ""),
        }

    # Derive color grade params from directorInstructions.colorDirection
    color_dir = instance.get("canonicalDocuments", {}).get("directorInstructions", {}).get(
        "colorDirection", ""
    )
    grade_params = _parse_color_direction(color_dir)

    # Build minimal v2 render pipeline
    project_name = (
        instance.get("project", {}).get("name", "output")
        .lower().replace(" ", "-")[:40]
    )
    render_pipeline = {
        "steps": [
            {"step_id": "load", "operation": "load", "library": "ffmpeg",
             "depends_on": []},
            {"step_id": "overlay_audio", "operation": "overlay_audio", "library": "ffmpeg",
             "depends_on": ["load"], "input_asset_ids": ["load"]},
            {"step_id": "color_grade", "operation": "color_grade", "library": "ffmpeg",
             "depends_on": ["overlay_audio"], "input_asset_ids": ["overlay_audio"],
             "parameters": grade_params},
            {"step_id": "encode", "operation": "encode", "library": "ffmpeg",
             "depends_on": ["color_grade"], "input_asset_ids": ["color_grade"],
             "parameters": {
                 "codec": "libx264", "crf": 18, "preset": "slow",
                 "audio_codec": "aac", "audio_bitrate": "192k",
                 "output_filename": f"{project_name}.mp4",
             }},
        ]
    }

    scene_order = [s["scene_id"] for s in v2_scenes]

    return {
        **instance,          # preserve all v3 fields
        "scenes": v2_scenes,
        "audio_assets": v2_audio,
        "render_pipeline": render_pipeline,
        "outputs": [{"scene_order": scene_order}],
    }


def _audio_tool_from_type(atype: str) -> str:
    return {
        "dialogue":   "elevenlabs",
        "voice_over": "elevenlabs",
        "music":      "suno",
        "sfx":        "stub",
        "ambient":    "stub",
        "foley":      "stub",
        "stem":       "suno",
    }.get(atype, "stub")


def _parse_color_direction(direction: str) -> dict:
    """Heuristically derive eq filter params from a text color direction string."""
    d = direction.lower()
    brightness = 0.0
    contrast = 1.0
    saturation = 1.0
    if "desaturated" in d or "muted" in d:
        saturation = 0.75
    if "vibrant" in d or "saturated" in d:
        saturation = 1.3
    if "warm" in d:
        brightness = 0.05
        contrast = 1.05
    if "cool" in d or "cold" in d:
        brightness = -0.03
    if "high contrast" in d:
        contrast = 1.2
    if "lifted blacks" in d or "film look" in d:
        brightness = 0.04
        contrast = 0.95
    return {
        "brightness": round(brightness, 3),
        "contrast": round(contrast, 3),
        "saturation": round(saturation, 3),
    }


# ── CLI entry-point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Run the full 24-skill pipeline.")
    parser.add_argument("idea", help="Creative idea / concept for the video.")
    parser.add_argument("--output-dir", default="./output/pipeline", metavar="DIR")
    parser.add_argument("--stub-media", action="store_true",
                        help="Skip real image/TTS generation.")
    parser.add_argument("--start-from", metavar="SKILL_DIR",
                        help="Resume pipeline from this skill (e.g. s07-director).")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    instance = run_pipeline(
        args.idea,
        output_dir=Path(args.output_dir),
        stub_media=args.stub_media,
        start_from=args.start_from,
    )

    print(f"\n✓ Pipeline complete. Instance saved to {args.output_dir}/instance.json")
    print(f"  Characters : {len(instance.get('production', {}).get('characters', []))}")
    print(f"  Shots      : {len(instance.get('production', {}).get('shots', []))}")
    print(f"  Audio      : {len(instance.get('assetLibrary', {}).get('audioAssets', []))}")
    sys.exit(0)
