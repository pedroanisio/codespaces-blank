"""
derive.py — Populate empty ``production.shots`` / ``production.scenes`` and
``assetLibrary.audioAssets`` from v3 story-beat data.

Called by run.py before generation when those sections are empty
(e.g. the pipeline ran to phase 16 but S14 had no video API key).

All output follows the v3 schema — no v2 field names.

Public API
----------
  ensure_shots(instance)   →  mutates instance in-place; returns it.
  ensure_audio(instance)   →  mutates instance in-place; returns it.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


# ── chromatic arc ─────────────────────────────────────────────────────────────
# Director spec: "grey-cold factory world → warm amber studio world"
# Keyed by beat order (1-indexed).

_BEAT_PALETTES: dict[int, list[str]] = {
    1: ["#2c2c34", "#1e2228", "#3a3530"],
    2: ["#28282e", "#1e2225", "#323230"],
    3: ["#3d2f1a", "#2c2218", "#4a3820"],
    4: ["#4a3820", "#3d2a15", "#5a4228"],
    5: ["#5c4025", "#4a3520", "#3d2818"],
    6: ["#6b4d2e", "#5c4025", "#7a5530"],
    7: ["#7a5530", "#6b4d2e", "#4a3820"],
    8: ["#1a1410", "#2a1e10", "#0a0808"],
}

# ── shot templates per beat ────────────────────────────────────────────────────
# (shot_type, camera_movement, duration_fraction)

_BEAT_SHOT_TEMPLATES: dict[int, list[tuple[str, str, float]]] = {
    1: [  # Reactivation in Emptiness — 30 s
        ("ECU", "static",     0.08),
        ("POV", "static",     0.27),
        ("MS",  "static",     0.33),
        ("WS",  "slow-drift", 0.32),
    ],
    2: [  # The Wandering Search — 30 s
        ("WS",  "slow-dolly", 0.40),
        ("MS",  "static",     0.27),
        ("CU",  "static",     0.20),
        ("WS",  "static",     0.13),
    ],
    3: [  # Discovery: The Artist's Studio — 40 s
        ("WS",  "static",     0.17),
        ("MS",  "static",     0.13),
        ("WS",  "slow-dolly", 0.35),
        ("CU",  "static",     0.17),
        ("MS",  "static",     0.18),
    ],
    4: [  # First Attempt: Pure Mimicry — 45 s
        ("CU",  "static",     0.18),
        ("ECU", "static",     0.18),
        ("MS",  "static",     0.27),
        ("CU",  "static",     0.18),
        ("MS",  "static",     0.19),
    ],
    5: [  # The Beautiful Mistake — 40 s
        ("CU",  "static",     0.15),
        ("ECU", "static",     0.30),
        ("MS",  "static",     0.30),
        ("CU",  "static",     0.25),
    ],
    6: [  # Obsessive Becoming — 60 s (montage)
        ("MS",       "static",     0.10),
        ("ECU",      "static",     0.10),
        ("CU",       "static",     0.10),
        ("overhead", "slow-drift", 0.12),
        ("ECU",      "static",     0.12),
        ("WS",       "static",     0.12),
        ("CU",       "static",     0.12),
        ("MS",       "static",     0.12),
        ("MS",       "static",     0.10),
    ],
    7: [  # The First True Painting — 35 s
        ("WS",  "static",     0.23),
        ("MS",  "slow-dolly", 0.32),
        ("CU",  "static",     0.25),
        ("MS",  "static",     0.20),
    ],
    8: [  # The Reaching Hand — 20 s
        ("CU",  "static",     0.30),
        ("WS",  "static",     0.70),   # 12 s+ uncut final hold
    ],
}

_BEAT_ENV_KEYS: dict[int, str] = {
    1: "env-factory-floor",
    2: "env-upper-corridors",
    3: "env-artists-studio",
    4: "env-artists-studio",
    5: "env-artists-studio",
    6: "env-artists-studio",
    7: "env-artists-studio",
    8: "env-artists-studio",
}

_ENV_FALLBACKS: dict[str, str] = {
    "env-factory-floor": (
        "vast shuttered industrial assembly floor, stripped conveyor belts, "
        "institutional concrete pillars, cold grey light from broken skylights, "
        "deep charcoal shadows, rust and steel, total human absence"
    ),
    "env-upper-corridors": (
        "abandoned factory upper-floor corridors, walls streaked rust and "
        "water damage, broken glass on concrete, faded warning signage, "
        "narrow cold atmospheric passages, industrial decay"
    ),
    "env-artists-studio": (
        "abandoned artist's studio in factory upper floor, warm amber "
        "north-skylight flooding the space, canvases leaning against walls, "
        "brushes in stiffened jars, painter's easel with half-finished work, "
        "paint-stained wooden floor, dust motes in warm light"
    ),
}

_AXIOM7_CORE = (
    "large industrial assembly robot, faded safety-yellow steel chassis heavily "
    "corroded with rust-red oxidation and bare metal patches, single cyclopean "
    "optical sensor cluster of concentric glass rings glowing dim cool blue-white "
    "light, heavy six-axis articulated arms with precision multi-finger claw "
    "end-effectors, worn stenciling 'AXIOM-7 // UNIT 07 // SECTOR C', "
    "intermittently strobing electric-blue LED indicator lights along upper torso"
)

_AXIOM7_STYLE = (
    "art-house science fiction, contemplative visually poetic tone, "
    "cinematic chiaroscuro lighting, painterly cinematography, "
    "shallow depth of field, 1920x1080 24fps, subtle film grain"
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _pick(obj: dict, path: str) -> Any:
    val: Any = obj
    for k in path.split("."):
        if not isinstance(val, dict):
            return None
        val = val.get(k)
    return val


def _env_prompt(env_key: str, envs: list[dict]) -> str:
    for env in envs:
        eid = env.get("logicalId") or env.get("id") or ""
        if env_key in eid:
            parts = [
                env.get("description") or env.get("name") or "",
                env.get("atmosphere") or "",
                env.get("lighting") or "",
            ]
            combined = ", ".join(p for p in parts if p)
            if combined.strip():
                return combined
    return _ENV_FALLBACKS.get(env_key, "cinematic film environment")


def _char_prompt(characters: list[dict]) -> str:
    for char in characters:
        if "AXIOM" in (char.get("name") or "").upper():
            frags = char.get("canonicalPromptFragments") or []
            locked = sorted(
                [f for f in frags if f.get("locked") and f.get("weight", 0) >= 0.75],
                key=lambda f: -f.get("weight", 0),
            )
            if locked:
                return ", ".join(f["fragment"] for f in locked[:4])
    return _AXIOM7_CORE


def _targeted_note(scene_lid: str, director_inst: dict) -> str:
    for note in (director_inst.get("targetedNotes") or []):
        ref = note.get("targetRef") or {}
        if scene_lid in (ref.get("logicalId") or ""):
            return note.get("note") or ""
    return ""


def _build_prompt(
    beat: dict,
    shot_type: str,
    camera_movement: str,
    env_desc: str,
    char_desc: str,
    note: str,
) -> str:
    shot_label = {
        "ECU": "extreme close-up",
        "CU":  "close-up",
        "MS":  "medium shot",
        "WS":  "wide shot",
        "POV": "robot point-of-view shot",
        "overhead": "overhead bird's-eye shot",
    }.get(shot_type, shot_type)

    cam_label = {
        "static":     "static locked-off camera",
        "slow-drift": "imperceptibly drifting camera",
        "slow-dolly": "slow motivated dolly-in",
    }.get(camera_movement, camera_movement)

    desc = beat.get("description", "")[:200]
    emotional = beat.get("emotionalObjective", "")
    note_snip = (note[:120] + "…") if len(note) > 120 else note

    parts = [
        f"{shot_label}, {cam_label}",
        char_desc,
        env_desc,
        f"scene: {beat.get('name','')} — {desc}" if desc else beat.get("name", ""),
        f"tone: {emotional}" if emotional else "",
        note_snip,
        _AXIOM7_STYLE,
    ]
    return ". ".join(p.strip().rstrip(".") for p in parts if p.strip())


# ── public API ────────────────────────────────────────────────────────────────

def ensure_shots(instance: dict) -> dict:
    """
    If ``production.scenes`` and ``production.shots`` are both empty,
    derive them from ``canonicalDocuments.story.beats`` and write them
    back into the instance in-place.

    Returns the (possibly mutated) instance.
    """
    production = instance.setdefault("production", {})
    if production.get("scenes") or production.get("shots"):
        return instance  # already populated — nothing to do

    beats: list[dict] = _pick(instance, "canonicalDocuments.story.beats") or []
    if not beats:
        log.warning("derive: no story beats found — production will remain empty")
        return instance

    director_inst: dict = _pick(instance, "canonicalDocuments.directorInstructions") or {}
    characters: list[dict] = production.get("characters") or []
    environments: list[dict] = production.get("environments") or []

    char_desc = _char_prompt(characters)
    all_shots: list[dict] = []
    all_scenes: list[dict] = []

    for beat in sorted(beats, key=lambda b: b.get("order", 0)):
        order = int(beat.get("order", 1))
        scene_refs = beat.get("sceneRefs") or []
        scene_lid = (
            scene_refs[0].get("logicalId")
            if scene_refs
            else f"scene-{order:03d}"
        )

        target = beat.get("targetRange") or {}
        beat_start = float(target.get("startSec", 0))
        beat_end = float(target.get("endSec", beat_start + 30))
        beat_duration = max(beat_end - beat_start, 1.0)

        env_key = _BEAT_ENV_KEYS.get(order, "env-factory-floor")
        env_desc = _env_prompt(env_key, environments)
        note = _targeted_note(scene_lid, director_inst)
        palette = _BEAT_PALETTES.get(order, ["#1a1a2e"])
        templates = _BEAT_SHOT_TEMPLATES.get(order, [("MS", "static", 1.0)])

        shot_refs: list[dict] = []
        for idx, (shot_type, cam_move, fraction) in enumerate(templates):
            raw_dur = beat_duration * fraction
            min_dur = 3.0 if order == 6 else 6.0
            if order == 8 and idx == len(templates) - 1:
                min_dur = 12.0
            duration = max(raw_dur, min_dur)

            shot_lid = f"shot-{order:03d}-{idx+1:03d}"
            prompt = _build_prompt(beat, shot_type, cam_move, env_desc, char_desc, note)

            shot: dict = {
                "id":        f"{shot_lid}-v1.0.0",
                "logicalId": shot_lid,
                "entityType": "shot",
                "order":     idx,
                "targetDurationSec": round(duration, 2),
                "purpose": f"{beat.get('name', f'Beat {order}')} — {shot_type} {idx+1}/{len(templates)}",
                "cinematicSpec": {
                    "colorPalette":    palette,
                    "shotType":        shot_type,
                    "cameraMovement":  cam_move,
                },
                "generation": {
                    "steps": [
                        {"tool": "runway-gen4", "prompt": prompt}
                    ]
                },
                "version": {"number": "1.0.0", "state": "draft"},
            }
            all_shots.append(shot)
            shot_refs.append({"entityType": "shot", "logicalId": shot_lid})

        scene: dict = {
            "id":        f"{scene_lid}-v1.0.0",
            "logicalId": scene_lid,
            "entityType": "scene",
            "sceneNumber": order,
            "beatRef": {"entityType": "beat", "logicalId": beat.get("beatId", f"beat-{order:03d}")},
            "shotRefs": shot_refs,
            "version": {"number": "1.0.0", "state": "draft"},
        }
        all_scenes.append(scene)

        log.info(
            "derive: beat %d (%s) → %d shots, %.0f–%.0f s",
            order, beat.get("name", ""), len(shot_refs), beat_start, beat_end,
        )

    production["shots"] = all_shots
    production["scenes"] = all_scenes
    log.info(
        "derive: populated %d scenes / %d shots from story beats",
        len(all_scenes), len(all_shots),
    )
    return instance


def ensure_audio(instance: dict) -> dict:
    """
    If ``assetLibrary.audioAssets`` is empty, derive four tracks from
    director instructions and write them back into the instance in-place.

    Returns the (possibly mutated) instance.
    """
    asset_lib = instance.setdefault("assetLibrary", {})
    if asset_lib.get("audioAssets"):
        return instance  # already populated

    director_inst: dict = _pick(instance, "canonicalDocuments.directorInstructions") or {}
    music_dir: str = director_inst.get("musicDirection") or ""
    target_runtime = float(
        _pick(instance, "project.targetRuntimeSec") or 300
    )

    score_ref = (
        "minimal solo piano unprocessed room sound, long-form ambient synthesis, "
        "slow-evolving pads, industrial harmonics, no percussion, "
        "tintinnabuli-influenced, single held piano note fading to silence at end"
    )
    for composer in ["Arvo Pärt", "Ólafur Arnalds", "Jóhann Jóhannsson"]:
        if composer in music_dir:
            score_ref = f"{composer} style, " + score_ref
            break

    audio_assets = [
        {
            "id": "audio-factory-ambience-v1.0.0",
            "logicalId": "audio-factory-ambience",
            "entityType": "audioAsset",
            "audioType": "ambient",
            "targetDurationSec": 62.0,
            "syncPoints": {
                "timelineInSec":  0.0,
                "timelineOutSec": 62.0,
                "fadeInSec":  0.0,
                "fadeOutSec": 4.0,
            },
            "generation": {"steps": [{"tool": "stub", "prompt": (
                "industrial factory ambience: creak of cooling steel, wind "
                "through unseen gaps, distant knock of settling metal, "
                "AXIOM-7 servo hum inside the acoustic — deeply still, 62 seconds"
            )}]},
            "version": {"number": "1.0.0", "state": "draft"},
        },
        {
            "id": "audio-studio-ambience-v1.0.0",
            "logicalId": "audio-studio-ambience",
            "entityType": "audioAsset",
            "audioType": "ambient",
            "targetDurationSec": target_runtime - 60,
            "syncPoints": {
                "timelineInSec":  60.0,
                "timelineOutSec": target_runtime,
                "fadeInSec":  4.0,
                "fadeOutSec": 0.0,
            },
            "generation": {"steps": [{"tool": "stub", "prompt": (
                "abandoned artist's studio ambience: faint wind against "
                "factory windows, occasional paint-jar clink, soft brushstroke "
                "texture, warm reverberant space, dust and silence"
            )}]},
            "version": {"number": "1.0.0", "state": "draft"},
        },
        {
            "id": "audio-axiom7-sfx-v1.0.0",
            "logicalId": "audio-axiom7-sfx",
            "entityType": "audioAsset",
            "audioType": "sfx",
            "targetDurationSec": target_runtime,
            "syncPoints": {
                "timelineInSec":  0.0,
                "timelineOutSec": target_runtime,
                "fadeInSec":  0.0,
                "fadeOutSec": 0.0,
            },
            "generation": {"steps": [{"tool": "stub", "prompt": (
                "AXIOM-7 mechanical SFX layer: servo whir, hydraulic arm movement, "
                "optical sensor focus click, chassis creak, power cell hum, "
                "brushstroke scrape of metal on canvas, decreasing intensity "
                "as power drains over 300 seconds"
            )}]},
            "version": {"number": "1.0.0", "state": "draft"},
        },
        {
            "id": "audio-minimal-score-v1.0.0",
            "logicalId": "audio-minimal-score",
            "entityType": "audioAsset",
            "audioType": "music",
            "targetDurationSec": target_runtime - 87,
            "syncPoints": {
                "timelineInSec":  80.0,
                "timelineOutSec": target_runtime - 7,
                "fadeInSec":  12.0,
                "fadeOutSec":  4.0,
            },
            "generation": {"steps": [{"tool": "suno", "prompt": score_ref}]},
            "version": {"number": "1.0.0", "state": "draft"},
        },
    ]

    asset_lib["audioAssets"] = audio_assets
    log.info("derive: populated %d audio assets from director instructions", len(audio_assets))
    return instance
