#!/usr/bin/env python3
"""CLI tool for generating valid Video Project JSON documents (v3 schema).

Usage:
    # Interactive mode — prompts for every section
    python create.py

    # Quick mode — minimal prompts, sensible defaults
    python create.py --quick --title "My Short" --logline "A story about..."

    # Non-interactive — all values via flags
    python create.py --title "My Short" --logline "A story about..." \
        --duration 60 --genre sci-fi --acts 3 --output my-project.json

    # AI-powered: generate from idea using the 24-skill pipeline
    python create.py --idea "A robot discovers music in an abandoned city"

    # Refine an existing document through AI skills
    python create.py --refine existing.json --output refined.json

    # Run specific skills on an existing document
    python create.py --refine existing.json --skills s04-character-designer,s05-environment-designer

    # Resume the pipeline from a specific skill
    python create.py --refine existing.json --start-from s07-director

    # Validate an existing document
    python create.py --validate existing.json
"""
from __future__ import annotations

import argparse
import json
import structlog
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = structlog.get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

SCHEMA_VERSION = "3.1.0"

SHOT_TYPES = [
    "wide", "medium", "medium_close_up", "close_up",
    "extreme_close_up", "insert", "over_the_shoulder",
]
CAMERA_ANGLES = ["eye_level", "low", "high", "dutch", "birds_eye", "worms_eye"]
CAMERA_MOVEMENTS = ["static", "pan", "tilt", "dolly", "zoom", "crane", "handheld"]
AUDIO_TYPES = ["ambient", "dialogue", "music", "sfx"]
TRANSITION_TYPES = ["cut", "fade", "dissolve", "wipe"]
GENRES = [
    "action", "adventure", "animation", "comedy", "crime", "documentary",
    "drama", "fantasy", "horror", "musical", "mystery", "romance",
    "science_fiction", "thriller", "war", "western",
]
SEGMENT_TYPES = ["scene_heading", "action", "dialogue", "transition", "parenthetical"]
VERSION_STATES = [
    "draft", "in_progress", "generating", "review",
    "changes_requested", "approved", "published", "archived", "deprecated",
]

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schemas" / "active" / "gvpp-v3.schema.json"


# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert text to a schema-safe identifier slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:80]


def make_id(prefix: str, slug: str, version: str = "v1") -> str:
    return f"{prefix}.{slug}.{version}"


def make_logical_id(prefix: str, slug: str) -> str:
    return f"{prefix}.{slug}"


def version_info(number: str = "1.0.0", state: str = "draft") -> dict:
    return {"number": number, "state": state}


def entity_ref(entity_id: str) -> dict:
    return {"id": entity_id}


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prompt_str(label: str, default: str = "") -> str:
    """Prompt user for a string value."""
    suffix = f" [{default}]" if default else ""
    value = input(f"  {label}{suffix}: ").strip()
    return value or default


def prompt_int(label: str, default: int = 0) -> int:
    suffix = f" [{default}]" if default else ""
    raw = input(f"  {label}{suffix}: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"    Invalid number, using default: {default}")
        return default


def prompt_float(label: str, default: float = 0.0) -> float:
    suffix = f" [{default}]" if default else ""
    raw = input(f"  {label}{suffix}: ").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"    Invalid number, using default: {default}")
        return default


def prompt_choice(label: str, choices: list[str], default: str = "") -> str:
    if not default:
        default = choices[0]
    print(f"  {label} (options: {', '.join(choices)})")
    value = input(f"    [{default}]: ").strip()
    if value and value in choices:
        return value
    if value and value not in choices:
        print(f"    Invalid choice, using default: {default}")
    return default


def prompt_list(label: str, hint: str = "comma-separated") -> list[str]:
    raw = input(f"  {label} ({hint}): ").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def prompt_yes(label: str, default: bool = True) -> bool:
    yn = "Y/n" if default else "y/N"
    raw = input(f"  {label} [{yn}]: ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


# ── Section Builders ─────────────────────────────────────────────────────────

def build_package(slug: str) -> dict:
    return {
        "packageId": f"pkg.{slug}",
        "createdAt": iso_now(),
        "versioningPolicy": {},
    }


def build_project_interactive(slug: str) -> dict:
    print("\n── Project ─────────────────────────────────────────")
    title = prompt_str("Title", slug.replace("-", " ").title())
    desc = prompt_str("Description", f"A generative-AI video project: {title}")
    logline = prompt_str("Logline", desc)
    duration = prompt_int("Target runtime (seconds)", 60)
    genre = prompt_choice("Primary genre", GENRES, "drama")
    langs = prompt_list("Languages", "comma-separated, e.g. en-US,pt-BR") or ["en-US"]
    tags = prompt_list("Tags", "comma-separated") or [genre, "generative-ai"]

    return {
        "id": make_id("proj", slug),
        "logicalId": make_logical_id("proj", slug),
        "entityType": "project",
        "name": title,
        "version": version_info("1.0.0", "draft"),
        "description": desc,
        "tags": tags,
        "genres": [genre],
        "languages": langs,
        "targetRuntimeSec": duration,
        "defaultQualityProfileRef": entity_ref(make_id("qp", "broadcast-hd")),
    }, title, duration, logline


def build_project_from_args(args: argparse.Namespace, slug: str) -> tuple[dict, str, int, str]:
    title = args.title
    duration = args.duration or 60
    logline = args.logline or f"A generative-AI video project: {title}"
    genre = args.genre or "drama"
    langs = args.languages.split(",") if args.languages else ["en-US"]
    tags = args.tags.split(",") if args.tags else [genre, "generative-ai"]

    project = {
        "id": make_id("proj", slug),
        "logicalId": make_logical_id("proj", slug),
        "entityType": "project",
        "name": title,
        "version": version_info("1.0.0", "draft"),
        "description": args.description or logline,
        "tags": tags,
        "genres": [genre],
        "languages": langs,
        "targetRuntimeSec": duration,
        "defaultQualityProfileRef": entity_ref(make_id("qp", "broadcast-hd")),
    }
    return project, title, duration, logline


def build_quality_profile() -> list[dict]:
    return [{
        "id": make_id("qp", "broadcast-hd"),
        "logicalId": make_logical_id("qp", "broadcast-hd"),
        "entityType": "qualityProfile",
        "name": "Broadcast HD",
        "version": version_info("1.0.0", "approved"),
        "profile": {
            "name": "Broadcast HD",
            "video": {
                "resolution": {"widthPx": 1920, "heightPx": 1080},
                "frameRate": {"fps": 24, "mode": "constant"},
                "aspectRatio": {"expression": "16:9", "preset": "16:9"},
                "spatialConsistency": {
                    "required": True,
                    "enforce180DegreeRule": True,
                    "enforceScreenDirection": True,
                },
            },
            "audio": {"sampleRateHz": 44100, "channelLayout": "stereo"},
            "validationRules": [
                {"name": "Temporal consistency", "id": "qr.temporal", "severity": "error"},
                {"name": "180-degree rule", "id": "qr.180deg", "severity": "error"},
            ],
        },
    }]


def build_story_interactive(slug: str, logline: str, title: str) -> tuple[dict, list[dict]]:
    print("\n── Story ───────────────────────────────────────────")
    logline = prompt_str("Logline", logline)
    synopsis = prompt_str("Synopsis", f"Short film: {logline}")
    themes = prompt_list("Themes", "comma-separated") or ["drama"]
    tones = prompt_list("Tone", "comma-separated") or ["neutral"]

    num_beats = prompt_int("Number of story beats / acts", 3)
    beats: list[dict] = []
    for i in range(1, num_beats + 1):
        print(f"\n  ─ Beat {i} ─")
        name = prompt_str("Beat name", f"Act {i}")
        desc = prompt_str("Description", f"Beat {i} of the story")
        emotion = prompt_str("Emotional objective", "neutral")
        beats.append({
            "beatId": f"beat.act{i}",
            "name": name,
            "order": i,
            "description": desc,
            "emotionalObjective": emotion,
        })

    story = {
        "id": make_id("story", slug),
        "logicalId": make_logical_id("story", slug),
        "entityType": "story",
        "name": f"{title} — Story",
        "version": version_info("1.0.0", "draft"),
        "logline": logline,
        "synopsis": synopsis,
        "themes": themes,
        "tone": tones,
        "beats": beats,
    }
    return story, beats


def build_story_from_args(
    slug: str, logline: str, title: str, num_acts: int,
) -> tuple[dict, list[dict]]:
    beats = []
    act_names = ["Setup", "Confrontation", "Resolution"]
    emotions = ["tension", "conflict", "catharsis"]
    for i in range(1, num_acts + 1):
        name = act_names[i - 1] if i <= len(act_names) else f"Act {i}"
        emotion = emotions[i - 1] if i <= len(emotions) else "neutral"
        beats.append({
            "beatId": f"beat.act{i}",
            "name": name,
            "order": i,
            "description": f"{name} — act {i} of the story.",
            "emotionalObjective": emotion,
        })

    story = {
        "id": make_id("story", slug),
        "logicalId": make_logical_id("story", slug),
        "entityType": "story",
        "name": f"{title} — Story",
        "version": version_info("1.0.0", "draft"),
        "logline": logline,
        "synopsis": f"A {num_acts}-act short film. {logline}",
        "themes": ["drama"],
        "tone": ["neutral"],
        "beats": beats,
    }
    return story, beats


def build_script_interactive(
    slug: str, title: str, beats: list[dict],
) -> dict:
    print("\n── Script ──────────────────────────────────────────")
    use_auto = prompt_yes("Auto-generate script segments from beats?", True)
    segments: list[dict] = []
    order = 0

    if use_auto:
        for i, beat in enumerate(beats, 1):
            scene_id = f"scene.act{i}.v1"
            order += 1
            segments.append({
                "segmentId": f"seg.s{order}",
                "order": order,
                "segmentType": "scene_heading",
                "text": f"INT. LOCATION — {beat['name'].upper()}",
                "sceneRef": entity_ref(scene_id),
            })
            order += 1
            segments.append({
                "segmentId": f"seg.s{order}",
                "order": order,
                "segmentType": "action",
                "text": beat["description"],
                "sceneRef": entity_ref(scene_id),
            })
    else:
        print("  Enter script segments (empty line to stop):")
        while True:
            seg_type = prompt_choice(
                f"Segment {order + 1} type (blank to finish)",
                SEGMENT_TYPES, "action",
            )
            text = prompt_str("Text")
            if not text:
                break
            beat_idx = prompt_int("Beat/scene number (1-based)", 1)
            scene_id = f"scene.act{beat_idx}.v1"
            order += 1
            seg: dict[str, Any] = {
                "segmentId": f"seg.s{order}",
                "order": order,
                "segmentType": seg_type,
                "text": text,
                "sceneRef": entity_ref(scene_id),
            }
            segments.append(seg)

    return {
        "id": make_id("script", slug),
        "logicalId": make_logical_id("script", slug),
        "entityType": "script",
        "name": f"{title} — Script",
        "version": version_info("1.0.0", "draft"),
        "format": "fountain",
        "segments": segments,
    }


def build_script_from_beats(slug: str, title: str, beats: list[dict]) -> dict:
    segments: list[dict] = []
    order = 0
    for i, beat in enumerate(beats, 1):
        scene_id = f"scene.act{i}.v1"
        order += 1
        segments.append({
            "segmentId": f"seg.s{order}",
            "order": order,
            "segmentType": "scene_heading",
            "text": f"INT. LOCATION — {beat['name'].upper()}",
            "sceneRef": entity_ref(scene_id),
        })
        order += 1
        segments.append({
            "segmentId": f"seg.s{order}",
            "order": order,
            "segmentType": "action",
            "text": beat["description"],
            "sceneRef": entity_ref(scene_id),
        })
    return {
        "id": make_id("script", slug),
        "logicalId": make_logical_id("script", slug),
        "entityType": "script",
        "name": f"{title} — Script",
        "version": version_info("1.0.0", "draft"),
        "format": "fountain",
        "segments": segments,
    }


def build_director_instructions(slug: str, title: str) -> dict:
    return {
        "id": make_id("di", slug),
        "logicalId": make_logical_id("di", slug),
        "entityType": "directorInstructions",
        "name": f"{title} — Director Instructions",
        "version": version_info("1.0.0", "draft"),
        "visionStatement": f"Visual language for {title}.",
        "mustHaves": [],
        "mustAvoid": [],
        "editingLanguage": "Standard cuts. Dissolves for time transitions.",
        "colorDirection": "Neutral cinematic palette.",
        "qualityRules": [
            {"name": "Temporal consistency", "id": "qr.temporal", "severity": "error"},
            {"name": "180-degree rule", "id": "qr.180deg", "severity": "error"},
        ],
        "targetedNotes": [],
    }


def build_director_instructions_interactive(slug: str, title: str) -> dict:
    print("\n── Director Instructions ────────────────────────────")
    vision = prompt_str("Vision statement", f"Visual language for {title}.")
    must_haves = prompt_list("Must-haves", "comma-separated directives")
    must_avoid = prompt_list("Must-avoid", "comma-separated constraints")
    editing = prompt_str("Editing language", "Standard cuts. Dissolves for time transitions.")
    color = prompt_str("Color direction", "Neutral cinematic palette.")

    return {
        "id": make_id("di", slug),
        "logicalId": make_logical_id("di", slug),
        "entityType": "directorInstructions",
        "name": f"{title} — Director Instructions",
        "version": version_info("1.0.0", "draft"),
        "visionStatement": vision,
        "mustHaves": must_haves,
        "mustAvoid": must_avoid,
        "editingLanguage": editing,
        "colorDirection": color,
        "qualityRules": [
            {"name": "Temporal consistency", "id": "qr.temporal", "severity": "error"},
            {"name": "180-degree rule", "id": "qr.180deg", "severity": "error"},
        ],
        "targetedNotes": [],
    }


def build_characters_interactive() -> list[dict]:
    print("\n── Characters ──────────────────────────────────────")
    characters: list[dict] = []
    while True:
        name = prompt_str("Character name (blank to finish)")
        if not name:
            break
        char_slug = slugify(name)
        desc = prompt_str("Description", f"Character: {name}")
        height = prompt_float("Height (m)", 1.70)
        characters.append({
            "id": make_id("char", char_slug),
            "logicalId": make_logical_id("char", char_slug),
            "entityType": "character",
            "name": name,
            "version": version_info("1.0.0", "draft"),
            "description": desc,
            "heightM": height,
            "defaultBounds": {
                "volumeType": "sphere",
                "sphereCenter": {"x": 0.0, "y": round(height / 2, 2), "z": 0.0},
                "sphereRadiusM": round(height * 0.56, 2),
            },
        })
    if not characters:
        characters.append(_default_character())
    return characters


def _default_character() -> dict:
    return {
        "id": "char.protagonist.v1",
        "logicalId": "char.protagonist",
        "entityType": "character",
        "name": "Protagonist",
        "version": version_info("1.0.0", "draft"),
        "description": "The main character.",
        "heightM": 1.70,
        "defaultBounds": {
            "volumeType": "sphere",
            "sphereCenter": {"x": 0.0, "y": 0.85, "z": 0.0},
            "sphereRadiusM": 0.95,
        },
    }


def build_environments_interactive() -> list[dict]:
    print("\n── Environments ────────────────────────────────────")
    envs: list[dict] = []
    while True:
        name = prompt_str("Environment name (blank to finish)")
        if not name:
            break
        env_slug = slugify(name)
        desc = prompt_str("Description", name)
        envs.append({
            "id": make_id("env", env_slug),
            "logicalId": make_logical_id("env", env_slug),
            "entityType": "environment",
            "name": name,
            "version": version_info("1.0.0", "draft"),
            "description": desc,
            "defaultSceneSpace": {
                "coordinateSystem": {"handedness": "right", "upAxis": "+Y", "unitM": 1.0},
                "floorPlaneCoord": 0.0,
            },
            "spatialExtent": {
                "volumeType": "aabb",
                "aabbMin": {"x": -5.0, "y": 0.0, "z": -4.0},
                "aabbMax": {"x": 5.0, "y": 3.5, "z": 4.0},
            },
        })
    if not envs:
        envs.append(_default_environment())
    return envs


def _default_environment() -> dict:
    return {
        "id": "env.main-location.v1",
        "logicalId": "env.main-location",
        "entityType": "environment",
        "name": "Main Location",
        "version": version_info("1.0.0", "draft"),
        "description": "Primary shooting location.",
        "defaultSceneSpace": {
            "coordinateSystem": {"handedness": "right", "upAxis": "+Y", "unitM": 1.0},
            "floorPlaneCoord": 0.0,
        },
        "spatialExtent": {
            "volumeType": "aabb",
            "aabbMin": {"x": -5.0, "y": 0.0, "z": -4.0},
            "aabbMax": {"x": 5.0, "y": 3.5, "z": 4.0},
        },
    }


def build_scenes_and_shots(
    beats: list[dict],
    duration: int,
    characters: list[dict],
    environments: list[dict],
    shots_per_scene: int = 3,
    interactive: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Generate scenes and shots from beats."""
    num_beats = len(beats)
    if interactive:
        print("\n── Scenes & Shots ──────────────────────────────────")
        shots_per_scene = prompt_int("Shots per scene", 3)

    base_duration = duration / num_beats
    scenes: list[dict] = []
    shots: list[dict] = []
    shot_counter = 0
    cursor_sec = 0.0

    style_guide_id = "sg.project-style.v1"
    char_ref = entity_ref(characters[0]["id"])
    env_ref = entity_ref(environments[0]["id"])

    # Shot-type cycling pattern for visual variety
    shot_type_cycle = ["wide", "medium", "close_up", "medium_close_up", "insert", "extreme_close_up"]
    movement_cycle = ["static", "dolly", "static", "pan", "static", "zoom"]
    focal_lengths = {"wide": 24, "medium": 50, "close_up": 85, "medium_close_up": 85,
                     "extreme_close_up": 100, "insert": 100, "over_the_shoulder": 50}

    for scene_idx, beat in enumerate(beats, 1):
        scene_duration = round(base_duration)
        scene_start = round(cursor_sec)
        scene_end = round(cursor_sec + scene_duration)

        scene_shot_refs: list[dict] = []
        shot_duration_each = round(scene_duration / shots_per_scene, 1)

        for s in range(shots_per_scene):
            shot_counter += 1
            shot_id = f"shot.s{shot_counter}.v1"
            shot_logical = f"shot.s{shot_counter}"
            shot_start = round(cursor_sec + s * shot_duration_each)
            shot_end = round(shot_start + shot_duration_each)

            cycle_idx = (shot_counter - 1) % len(shot_type_cycle)
            stype = shot_type_cycle[cycle_idx]
            movement = movement_cycle[cycle_idx]
            focal = focal_lengths.get(stype, 50)

            cinematic: dict[str, Any] = {
                "shotType": stype,
                "cameraAngle": "eye_level",
                "cameraMovement": movement,
                "focalLengthMm": focal,
                "styleGuideRef": entity_ref(style_guide_id),
                "style": {"adjectives": [beat.get("emotionalObjective", "neutral")]},
            }
            # Temporal bridge from previous shot
            if shot_counter > 1:
                cinematic["temporalBridgeAnchorRef"] = entity_ref(
                    f"shot.s{shot_counter - 1}.v1"
                )

            gen_params: dict[str, Any] = {
                "stepId": f"step.s{shot_counter}.gen",
                "operationType": "video_generation",
                "prompt": (
                    f"{stype.replace('_', ' ').title()} shot — "
                    f"{beat['description']} "
                    f"({beat.get('emotionalObjective', 'neutral')} mood)"
                ),
            }
            # Character consistency anchors for close shots
            if stype in ("close_up", "medium_close_up", "extreme_close_up"):
                gen_params["consistencyAnchors"] = [{
                    "anchorType": "character",
                    "name": f"{characters[0]['name']} face consistency",
                    "ref": char_ref,
                    "lockLevel": "hard" if stype == "close_up" else "medium",
                }]

            shot = {
                "id": shot_id,
                "logicalId": shot_logical,
                "entityType": "shot",
                "name": f"S{shot_counter} — {stype.replace('_', ' ').title()}",
                "version": version_info("1.0.0", "draft"),
                "shotNumber": shot_counter,
                "sceneRef": entity_ref(f"scene.act{scene_idx}.v1"),
                "targetDurationSec": round(shot_duration_each),
                "plannedPosition": {"startSec": shot_start, "endSec": shot_end},
                "cinematicSpec": cinematic,
                "genParams": gen_params,
                "qaGate": {
                    "requiredChecks": [
                        "temporal_consistency", "character_coherence",
                        "duration_compliance", "resolution_compliance",
                    ],
                    "passThreshold": 0.8,
                },
            }
            shots.append(shot)
            scene_shot_refs.append(entity_ref(shot_id))

        seg_refs = [
            entity_ref(f"seg.s{scene_idx * 2 - 1}"),
            entity_ref(f"seg.s{scene_idx * 2}"),
        ]

        scene = {
            "id": f"scene.act{scene_idx}.v1",
            "logicalId": f"scene.act{scene_idx}",
            "entityType": "scene",
            "name": f"Act {scene_idx} — {beat['name']}",
            "version": version_info("1.0.0", "draft"),
            "sceneNumber": scene_idx,
            "synopsis": beat["description"],
            "storyBeatRefs": [entity_ref(beat["beatId"])],
            "scriptSegmentRefs": seg_refs,
            "characterRefs": [char_ref],
            "environmentRef": env_ref,
            "propRefs": [],
            "timeOfDay": "day",
            "weather": "interior",
            "mood": beat.get("emotionalObjective", "neutral"),
            "targetDurationSec": scene_duration,
            "plannedPosition": {"startSec": scene_start, "endSec": scene_end},
            "shotRefs": scene_shot_refs,
            "transitionIn": {"type": "fade" if scene_idx == 1 else "cut"},
            "transitionOut": {"type": "fade" if scene_idx == num_beats else "cut"},
            "sceneSpace": {
                "coordinateSystem": {"handedness": "right", "upAxis": "+Y", "unitM": 1.0},
                "floorPlaneCoord": 0.0,
                "spatialAnchors": [],
            },
            "spatialConsistency": {"required": True, "enforce180DegreeRule": True},
            "qaGate": {
                "requiredChecks": ["temporal_consistency", "character_coherence", "audio_sync"],
                "passThreshold": 0.8,
            },
        }
        scenes.append(scene)
        cursor_sec += scene_duration

    return scenes, shots


def build_audio_assets_interactive(characters: list[dict]) -> list[dict]:
    print("\n── Audio Assets ────────────────────────────────────")
    assets: list[dict] = []
    use_defaults = prompt_yes("Generate default audio assets (ambient + score)?", True)
    if use_defaults:
        assets.append({
            "id": "audio.ambient.v1",
            "logicalId": "audio.ambient",
            "entityType": "audioAsset",
            "name": "Ambient Sound",
            "version": version_info("1.0.0", "draft"),
            "audioType": "ambient",
            "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"},
        })
        assets.append({
            "id": "audio.score.v1",
            "logicalId": "audio.score",
            "entityType": "audioAsset",
            "name": "Score",
            "version": version_info("1.0.0", "draft"),
            "audioType": "music",
            "mood": "cinematic",
            "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"},
        })

    print("  Add dialogue or extra audio assets (blank to finish):")
    while True:
        name = prompt_str("Audio asset name (blank to finish)")
        if not name:
            break
        a_slug = slugify(name)
        a_type = prompt_choice("Type", AUDIO_TYPES, "dialogue")
        asset: dict[str, Any] = {
            "id": make_id("audio", a_slug),
            "logicalId": make_logical_id("audio", a_slug),
            "entityType": "audioAsset",
            "name": name,
            "version": version_info("1.0.0", "draft"),
            "audioType": a_type,
            "technicalSpec": {
                "sampleRateHz": 44100,
                "channelLayout": "mono" if a_type == "dialogue" else "stereo",
                "codec": "flac",
            },
        }
        if a_type == "dialogue" and characters:
            asset["characterRef"] = entity_ref(characters[0]["id"])
            transcript = prompt_str("Transcript")
            if transcript:
                asset["transcript"] = transcript
        assets.append(asset)

    if not assets:
        assets = _default_audio_assets()
    return assets


def _default_audio_assets() -> list[dict]:
    return [
        {
            "id": "audio.ambient.v1",
            "logicalId": "audio.ambient",
            "entityType": "audioAsset",
            "name": "Ambient Sound",
            "version": version_info("1.0.0", "draft"),
            "audioType": "ambient",
            "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"},
        },
        {
            "id": "audio.score.v1",
            "logicalId": "audio.score",
            "entityType": "audioAsset",
            "name": "Score",
            "version": version_info("1.0.0", "draft"),
            "audioType": "music",
            "mood": "cinematic",
            "technicalSpec": {"sampleRateHz": 44100, "channelLayout": "stereo", "codec": "flac"},
        },
    ]


def build_style_guide(title: str) -> list[dict]:
    return [{
        "id": "sg.project-style.v1",
        "logicalId": "sg.project-style",
        "entityType": "styleGuide",
        "name": f"{title} — Project Style Guide",
        "version": version_info("1.0.0", "draft"),
        "scope": "project",
        "guidelines": {
            "genres": [],
            "adjectives": ["cinematic"],
            "palette": [],
            "textureDescriptors": [],
            "cameraLanguage": "standard cinematic language",
        },
        "negativeStylePrompt": "",
        "appliesTo": [],
    }]


def build_timeline(shots: list[dict], audio_assets: list[dict], duration: int) -> dict:
    video_clips = []
    for shot in shots:
        pp = shot["plannedPosition"]
        video_clips.append({
            "clipId": f"vc.s{shot['shotNumber']}",
            "sourceRef": entity_ref(shot["id"]),
            "timelineStartSec": pp["startSec"],
            "durationSec": pp["endSec"] - pp["startSec"],
        })

    audio_clips = []
    for i, audio in enumerate(audio_assets):
        clip_id = f"ac.{slugify(audio['name'])}"
        is_full_length = audio["audioType"] in ("ambient", "music")
        audio_clips.append({
            "clipId": clip_id,
            "sourceRef": entity_ref(audio["id"]),
            "timelineStartSec": 0 if is_full_length else round(duration * (i / max(len(audio_assets), 1))),
            "durationSec": duration if is_full_length else 5,
        })

    return {
        "id": "tl.main.v1",
        "logicalId": "tl.main",
        "entityType": "timeline",
        "name": "Main Timeline",
        "version": version_info("1.0.0", "draft"),
        "durationSec": duration,
        "frameRate": {"fps": 24, "mode": "constant"},
        "resolution": {"widthPx": 1920, "heightPx": 1080},
        "videoClips": video_clips,
        "audioClips": audio_clips,
    }


def build_assembly(shots: list[dict], audio_assets: list[dict], duration: int) -> dict:
    timeline = build_timeline(shots, audio_assets, duration)

    render_clip_refs = [entity_ref(s["id"]) for s in shots]
    audio_tracks = []
    for audio in audio_assets:
        is_full = audio["audioType"] in ("ambient", "music")
        gain = -6 if audio["audioType"] == "ambient" else (-12 if audio["audioType"] == "music" else 0)
        audio_tracks.append({
            "audioRef": entity_ref(audio["id"]),
            "gainDb": gain,
            "timeRange": {"startSec": 0, "endSec": duration} if is_full else {"startSec": 0, "endSec": 5},
        })

    return {
        "timelines": [timeline],
        "editVersions": [{
            "id": "ev.initial.v1",
            "logicalId": "ev.initial",
            "entityType": "editVersion",
            "name": "Initial Edit",
            "version": version_info("1.0.0", "draft"),
            "timelineRef": entity_ref("tl.main.v1"),
            "changeList": ["Initial assembly — all shots placed on timeline."],
            "approvedForRender": False,
        }],
        "renderPlans": [{
            "id": "rp.main.v1",
            "logicalId": "rp.main",
            "entityType": "renderPlan",
            "name": "Main Render Plan",
            "version": version_info("1.0.0", "draft"),
            "sourceTimelineRef": entity_ref("tl.main.v1"),
            "compatibleRuntimes": ["moviepy", "ffmpeg"],
            "operations": [
                {
                    "opId": "op.concat",
                    "opType": "concat",
                    "clipRefs": render_clip_refs,
                    "method": "chain",
                },
                {
                    "opId": "op.audio-mix",
                    "opType": "audioMix",
                    "tracks": audio_tracks,
                },
                {
                    "opId": "op.color-grade",
                    "opType": "colorGrade",
                    "inputRef": entity_ref("op.concat"),
                    "intent": "neutral cinematic — balanced palette",
                    "strength": 0.7,
                },
                {
                    "opId": "op.encode",
                    "opType": "encode",
                    "inputRef": entity_ref("op.color-grade"),
                    "compression": {"codec": "libx264", "profile": "high", "bitrateMbps": 8},
                },
            ],
        }],
    }


def build_deliverables(duration: int) -> list[dict]:
    return [{
        "id": "del.output-1080p.v1",
        "logicalId": "del.output-1080p",
        "entityType": "finalOutput",
        "name": "Output — 1080p",
        "version": version_info("1.0.0", "draft"),
        "outputType": "video/mp4",
        "runtimeSec": duration,
        "sourceTimelineRef": entity_ref("tl.main.v1"),
        "renderPlanRef": entity_ref("rp.main.v1"),
        "platform": "youtube",
    }]


def build_relationships(scenes: list[dict], beats: list[dict]) -> list[dict]:
    rels: list[dict] = []
    for i, scene in enumerate(scenes):
        if i < len(beats):
            rels.append({
                "relationshipId": f"rel.scene{i+1}-beat{i+1}",
                "relationshipType": "references",
                "from": entity_ref(scene["id"]),
                "to": entity_ref(beats[i]["beatId"]),
            })
    return rels


def build_orchestration() -> dict:
    return {
        "workflows": [{
            "workflowId": "wf.main-pipeline",
            "name": "Main Generation Pipeline",
            "nodes": [],
            "edges": [],
        }],
    }


# ── Document Assembly ────────────────────────────────────────────────────────

def assemble_document(
    slug: str,
    title: str,
    duration: int,
    project: dict,
    story: dict,
    beats: list[dict],
    script: dict,
    director: dict,
    characters: list[dict],
    environments: list[dict],
    scenes: list[dict],
    shots: list[dict],
    audio_assets: list[dict],
) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "package": build_package(slug),
        "project": project,
        "qualityProfiles": build_quality_profile(),
        "canonicalDocuments": {
            "story": story,
            "script": script,
            "directorInstructions": director,
        },
        "production": {
            "characters": characters,
            "environments": environments,
            "props": [],
            "scenes": scenes,
            "shots": shots,
            "styleGuides": build_style_guide(title),
        },
        "assetLibrary": {
            "visualAssets": [],
            "audioAssets": audio_assets,
            "marketingAssets": [],
            "genericAssets": [],
        },
        "orchestration": build_orchestration(),
        "assembly": build_assembly(shots, audio_assets, duration),
        "deliverables": build_deliverables(duration),
        "relationships": build_relationships(scenes, beats),
    }


# ── Validation ───────────────────────────────────────────────────────────────

def validate_document(doc: dict, schema_path: Path | None = None) -> list[str]:
    """Validate a document against the v3 schema. Returns list of errors."""
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed — run: pip install jsonschema"]

    schema_path = schema_path or SCHEMA_FILE
    if not schema_path.exists():
        return [f"Schema file not found: {schema_path}"]

    with open(schema_path) as f:
        schema = json.load(f)

    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    return [
        f"  {'→'.join(str(p) for p in e.absolute_path)}: {e.message}"
        for e in errors
    ]


def validate_file(path: str) -> int:
    """Validate a JSON file and print results. Returns exit code."""
    try:
        with open(path) as f:
            doc = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"✗ Cannot read {path}: {exc}", file=sys.stderr)
        return 1

    errors = validate_document(doc)
    if errors:
        print(f"✗ {len(errors)} validation error(s) in {path}:")
        for e in errors[:30]:
            print(e)
        if len(errors) > 30:
            print(f"  ... and {len(errors) - 30} more")
        return 1

    print(f"✓ {path} is valid (schema v{SCHEMA_VERSION})")
    return 0


# ── Interactive Flow ─────────────────────────────────────────────────────────

def run_interactive(args: argparse.Namespace) -> dict:
    print("═══════════════════════════════════════════════════════")
    print("  Video Project JSON Generator (v3 schema)")
    print("═══════════════════════════════════════════════════════")
    print("  Press Enter to accept [defaults].\n")

    slug_input = prompt_str("Project slug (kebab-case)", "my-video-project")
    slug = slugify(slug_input)

    project, title, duration, logline = build_project_interactive(slug)
    story, beats = build_story_interactive(slug, logline, title)
    script = build_script_interactive(slug, title, beats)
    director = build_director_instructions_interactive(slug, title)
    characters = build_characters_interactive()
    environments = build_environments_interactive()
    audio_assets = build_audio_assets_interactive(characters)
    scenes, shots = build_scenes_and_shots(
        beats, duration, characters, environments, interactive=True,
    )

    return assemble_document(
        slug, title, duration, project, story, beats, script, director,
        characters, environments, scenes, shots, audio_assets,
    )


def run_quick(args: argparse.Namespace) -> dict:
    """Non-interactive generation from CLI flags."""
    title = args.title or "Untitled Project"
    slug = slugify(title)
    num_acts = args.acts or 3

    project, title, duration, logline = build_project_from_args(args, slug)
    story, beats = build_story_from_args(slug, logline, title, num_acts)
    script = build_script_from_beats(slug, title, beats)
    director = build_director_instructions(slug, title)
    characters = [_default_character()]
    environments = [_default_environment()]
    audio_assets = _default_audio_assets()
    scenes, shots = build_scenes_and_shots(
        beats, duration, characters, environments, shots_per_scene=args.shots_per_scene or 3,
    )

    return assemble_document(
        slug, title, duration, project, story, beats, script, director,
        characters, environments, scenes, shots, audio_assets,
    )


# ── Skills Integration ────────────────────────────────────────────────────────

# All valid skill directory names
ALL_SKILLS = [
    "s01-concept-seed", "s02-story-architect", "s03-scriptwriter",
    "s04-character-designer", "s05-environment-designer", "s06-prop-designer",
    "s07-director", "s08-cinematographer",
    "s09-scene-composer", "s10-music-composer", "s11-sound-designer", "s12-voice-producer",
    "s13-reference-asset-gen", "s14-shot-video-gen", "s15-prompt-composer", "s16-consistency-enforcer",
    "s17-timeline-assembler", "s18-post-production", "s19-audio-mixer", "s20-render-plan-builder",
    "s21-qa-validator", "s22-deliverable-packager", "s23-marketing-asset-gen",
    "s24-pipeline-orchestrator",
]


def _resolve_skill_names(raw: str) -> list[str]:
    """Parse a comma-separated skill spec into valid skill directory names.

    Accepts full names (s04-character-designer), short IDs (S04, s04),
    or numeric ranges (4-6).
    """
    resolved: list[str] = []
    for token in raw.split(","):
        token = token.strip().lower()
        if not token:
            continue
        # Full directory name
        if token in ALL_SKILLS:
            resolved.append(token)
            continue
        # Short ID: s04 or S04
        match = re.match(r"^s?(\d{1,2})$", token)
        if match:
            num = int(match.group(1))
            prefix = f"s{num:02d}-"
            for s in ALL_SKILLS:
                if s.startswith(prefix):
                    resolved.append(s)
            continue
        # Range: 4-6
        match = re.match(r"^(\d{1,2})-(\d{1,2})$", token)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            for num in range(start, end + 1):
                prefix = f"s{num:02d}-"
                for s in ALL_SKILLS:
                    if s.startswith(prefix):
                        resolved.append(s)
            continue
        print(f"  ⚠ Unknown skill: {token}", file=sys.stderr)
    return resolved


def run_idea_pipeline(
    idea: str,
    output_dir: Path,
    stub_media: bool = False,
    start_from: str | None = None,
) -> dict:
    """Run the full 24-skill AI pipeline from a creative idea."""
    from pipeline.skills import run_pipeline

    log.info("running_full_pipeline_from_idea")
    return run_pipeline(
        idea,
        output_dir=output_dir,
        stub_media=stub_media,
        start_from=start_from,
    )


def run_refine(
    instance: dict,
    skill_names: list[str] | None = None,
    output_dir: Path | None = None,
    stub_media: bool = False,
    start_from: str | None = None,
) -> dict:
    """Run specific skills (or the full pipeline) to refine an existing document.

    Parameters
    ----------
    instance    : Existing v3 document to refine.
    skill_names : Specific skills to run (None = full pipeline in order).
    output_dir  : Where to save generated assets.
    stub_media  : Skip real media generation.
    start_from  : Resume full pipeline from this skill.
    """
    from pipeline.skills import run_skill, PIPELINE_PHASES, _deep_merge

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # If specific skills requested, run them in pipeline order
    if skill_names:
        # Sort by pipeline order
        flat_order = [s for phase in PIPELINE_PHASES for s in phase]
        ordered = sorted(skill_names, key=lambda s: flat_order.index(s) if s in flat_order else 999)

        for skill_dir in ordered:
            log.info("refining_with_skill", skill=skill_dir)
            update = run_skill(
                skill_dir, instance,
                output_dir=output_dir,
                stub_media=stub_media,
            )
            if update:
                instance = _deep_merge(instance, update)
                log.info("merged_skill_update", top_level_keys=len(update))
            else:
                log.warning("skill_returned_empty_update", skill=skill_dir)
        return instance

    # No specific skills — run the full pipeline phases
    skipping = start_from is not None
    phase_num = 0

    for phase in PIPELINE_PHASES:
        phase_num += 1

        if skipping:
            if start_from in phase:
                skipping = False
            else:
                log.info("phase_skipped", phase=phase_num, resuming_from=start_from)
                continue

        phase_label = ", ".join(s.split("-", 1)[1] for s in phase)
        log.info("starting_phase", phase=phase_num, label=phase_label)

        for skill_dir in phase:
            update = run_skill(
                skill_dir, instance,
                output_dir=output_dir,
                stub_media=stub_media,
            )
            if update:
                instance = _deep_merge(instance, update)

    return instance


def _print_providers_status() -> None:
    """Print which AI providers are available."""
    try:
        from pipeline.providers import available_providers
        avail = available_providers()
        active = [k for k, v in avail.items() if v]
        inactive = [k for k, v in avail.items() if not v]
        if active:
            print(f"  Active providers: {', '.join(active)}", file=sys.stderr)
        if inactive:
            print(f"  Inactive providers: {', '.join(inactive)}", file=sys.stderr)
        if not active:
            print("  ⚠ No AI providers configured. Set API keys in .env", file=sys.stderr)
            print("    Skills will return empty updates.", file=sys.stderr)
    except ImportError:
        print("  ⚠ providers module not available", file=sys.stderr)


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="create",
        description="Generate valid Video Project JSON documents (v3 schema).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              python create.py                                        # interactive mode
              python create.py --quick --title "My Film"              # quick with defaults
              python create.py --title "X" --logline "..." -o x.json
              python create.py --validate existing.json               # validate only

            AI-powered skills:
              python create.py --idea "A robot discovers music"       # full 24-skill pipeline
              python create.py --refine doc.json                      # refine all sections via AI
              python create.py --refine doc.json --skills s04,s05,s07 # run specific skills
              python create.py --refine doc.json --start-from s07     # resume from skill
              python create.py --quick -t "X" --skills s02,s07 -o x.json  # scaffold + refine

            skill IDs:
              s01 concept-seed         s09 scene-composer       s17 timeline-assembler
              s02 story-architect      s10 music-composer       s18 post-production
              s03 scriptwriter         s11 sound-designer       s19 audio-mixer
              s04 character-designer   s12 voice-producer       s20 render-plan-builder
              s05 environment-designer s13 reference-asset-gen  s21 qa-validator
              s06 prop-designer        s14 shot-video-gen       s22 deliverable-packager
              s07 director             s15 prompt-composer      s23 marketing-asset-gen
              s08 cinematographer      s16 consistency-enforcer s24 pipeline-orchestrator
        """),
    )

    parser.add_argument("--validate", metavar="FILE",
                        help="Validate an existing JSON file against the v3 schema and exit")
    parser.add_argument("--quick", action="store_true",
                        help="Non-interactive mode — use flags and defaults")

    ai = parser.add_argument_group("AI skills")
    ai.add_argument("--idea", metavar="TEXT",
                    help="Generate a full project from a creative idea using the 24-skill AI pipeline")
    ai.add_argument("--refine", metavar="FILE",
                    help="Refine an existing JSON document by running AI skills on it")
    ai.add_argument("--skills", metavar="LIST",
                    help="Comma-separated skills to run (e.g. s02,s04-s06,s07-director). "
                         "Use with --refine or after scaffold generation")
    ai.add_argument("--start-from", metavar="SKILL",
                    help="Resume full pipeline from this skill (e.g. s07 or s07-director)")
    ai.add_argument("--stub-media", action="store_true",
                    help="Skip real image/TTS generation in media-producing skills")
    ai.add_argument("--output-dir", metavar="DIR", default="./output",
                    help="Directory for generated assets and progress snapshots (default: ./output)")

    proj = parser.add_argument_group("project")
    proj.add_argument("--title", "-t", help="Project title")
    proj.add_argument("--logline", "-l", help="One-line story logline")
    proj.add_argument("--description", help="Project description")
    proj.add_argument("--duration", "-d", type=int, help="Target runtime in seconds (default: 60)")
    proj.add_argument("--genre", "-g", choices=GENRES, help="Primary genre")
    proj.add_argument("--languages", help="Comma-separated language codes (default: en-US)")
    proj.add_argument("--tags", help="Comma-separated tags")

    struct = parser.add_argument_group("structure")
    struct.add_argument("--acts", type=int, help="Number of acts / story beats (default: 3)")
    struct.add_argument("--shots-per-scene", type=int, help="Shots per scene (default: 3)")

    out = parser.add_argument_group("output")
    out.add_argument("--output", "-o", metavar="FILE",
                     help="Output file path (default: stdout)")
    out.add_argument("--indent", type=int, default=2,
                     help="JSON indent level (default: 2)")
    out.add_argument("--no-validate", action="store_true",
                     help="Skip schema validation of generated document")
    out.add_argument("--schema", metavar="FILE",
                     help="Path to schema file (default: auto-detected)")
    out.add_argument("-v", "--verbose", action="store_true",
                     help="Enable DEBUG logging")

    return parser


def _write_output(doc: dict, args: argparse.Namespace) -> int:
    """Validate and write the document. Returns exit code."""
    schema_path = Path(args.schema) if args.schema else None

    if not args.no_validate:
        errors = validate_document(doc, schema_path)
        if errors:
            print(f"\n⚠ {len(errors)} schema validation warning(s):", file=sys.stderr)
            for e in errors[:15]:
                print(e, file=sys.stderr)
            if len(errors) > 15:
                print(f"  ... and {len(errors) - 15} more", file=sys.stderr)
            print("\nDocument generated with warnings. Use --no-validate to suppress.\n",
                  file=sys.stderr)

    output = json.dumps(doc, indent=args.indent, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
        print(f"✓ Written to {out_path}", file=sys.stderr)
        if not args.no_validate and not validate_document(doc, schema_path):
            print(f"✓ Valid against schema v{SCHEMA_VERSION}", file=sys.stderr)
    else:
        print(output)

    # Print summary for AI-generated docs
    prod = doc.get("production", {})
    assets = doc.get("assetLibrary", {})
    counts = {
        "characters": len(prod.get("characters", [])),
        "environments": len(prod.get("environments", [])),
        "scenes": len(prod.get("scenes", [])),
        "shots": len(prod.get("shots", [])),
        "audio": len(assets.get("audioAssets", [])),
    }
    non_zero = {k: v for k, v in counts.items() if v}
    if non_zero:
        summary = ", ".join(f"{v} {k}" for k, v in non_zero.items())
        print(f"  Content: {summary}", file=sys.stderr)

    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # ── Logging setup ────────────────────────────────────────
    from pipeline.logging_config import configure_logging
    configure_logging(verbose=getattr(args, "verbose", False))

    # ── Validate mode ────────────────────────────────────────
    if args.validate:
        return validate_file(args.validate)

    # ── Idea mode: full 24-skill AI pipeline ─────────────────
    if args.idea:
        print("═══════════════════════════════════════════════════════", file=sys.stderr)
        print("  Video Project — AI Pipeline (24 skills)", file=sys.stderr)
        print("═══════════════════════════════════════════════════════", file=sys.stderr)
        _print_providers_status()
        output_dir = Path(args.output_dir)

        # Resolve --start-from short IDs
        start_from = None
        if args.start_from:
            resolved = _resolve_skill_names(args.start_from)
            start_from = resolved[0] if resolved else None

        doc = run_idea_pipeline(
            args.idea,
            output_dir=output_dir,
            stub_media=args.stub_media,
            start_from=start_from,
        )
        return _write_output(doc, args)

    # ── Refine mode: run skills on existing document ─────────
    if args.refine:
        print("═══════════════════════════════════════════════════════", file=sys.stderr)
        print("  Video Project — Refine with AI Skills", file=sys.stderr)
        print("═══════════════════════════════════════════════════════", file=sys.stderr)
        _print_providers_status()

        try:
            with open(args.refine) as f:
                doc = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as exc:
            print(f"✗ Cannot read {args.refine}: {exc}", file=sys.stderr)
            return 1

        print(f"  Loaded: {args.refine}", file=sys.stderr)

        skill_names = _resolve_skill_names(args.skills) if args.skills else None
        start_from = None
        if args.start_from:
            resolved = _resolve_skill_names(args.start_from)
            start_from = resolved[0] if resolved else None

        if skill_names:
            print(f"  Skills: {', '.join(skill_names)}", file=sys.stderr)
        elif start_from:
            print(f"  Resuming from: {start_from}", file=sys.stderr)
        else:
            print("  Running full pipeline refinement...", file=sys.stderr)

        output_dir = Path(args.output_dir)
        doc = run_refine(
            doc,
            skill_names=skill_names,
            output_dir=output_dir,
            stub_media=args.stub_media,
            start_from=start_from,
        )
        return _write_output(doc, args)

    # ── Scaffold + optional skills ───────────────────────────
    if args.quick or args.title:
        if not args.title:
            parser.error("--title is required in quick/non-interactive mode")
        doc = run_quick(args)
    else:
        doc = run_interactive(args)

    # If --skills specified alongside scaffold, refine the scaffold
    if args.skills:
        print("═══════════════════════════════════════════════════════", file=sys.stderr)
        print("  Refining scaffold with AI skills...", file=sys.stderr)
        print("═══════════════════════════════════════════════════════", file=sys.stderr)
        _print_providers_status()

        skill_names = _resolve_skill_names(args.skills)
        if skill_names:
            print(f"  Skills: {', '.join(skill_names)}", file=sys.stderr)
            output_dir = Path(args.output_dir)
            doc = run_refine(
                doc,
                skill_names=skill_names,
                output_dir=output_dir,
                stub_media=args.stub_media,
            )

    return _write_output(doc, args)


if __name__ == "__main__":
    raise SystemExit(main())
