"""
scene_splitter.py — Decompose a v3 instance into per-scene render contexts.

Takes a fully-populated GVPP v3 instance and produces N independent
SceneRenderContext objects, one per scene, each containing:
  - The scene entity and its shots
  - Audio slices (tracks intersected with the scene's time range)
  - Per-scene color grade parameters
  - Transition handles for the stitch pass

Public API
----------
  split_instance_by_scene(instance)  -> list[SceneRenderContext]
  slice_audio_for_scene(...)         -> list[AudioSlice]
  decompose_color_grade(...)         -> dict

See: docs/specs/scene-parallel-render.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger(__name__)


# ── data classes ─────────────────────────────────────────────────────────────

@dataclass
class TransitionHandle:
    """Frames needed at a scene boundary for cross-scene transitions."""
    duration_sec: float = 0.0
    type: str = "cut"


@dataclass
class AudioSlice:
    """An audio track sliced to a scene's time range."""
    audio_asset_id: str
    audio_asset: dict
    source_start_sec: float        # absolute position in master timeline
    source_end_sec: float          # absolute position in master timeline
    local_start_sec: float         # remapped to scene-local 0-based time
    local_end_sec: float           # remapped to scene-local 0-based time
    gain_db: float = 0.0
    pan: float = 0.0
    fade_in_sec: float = 0.0      # applied if slice starts mid-track
    fade_out_sec: float = 0.0     # applied if slice ends mid-track


@dataclass
class SceneRenderContext:
    """Everything needed to render a single scene independently."""
    scene: dict
    scene_index: int
    scene_start_sec: float
    scene_end_sec: float
    shots: list[dict]
    audio_slices: list[AudioSlice]
    color_grade_params: dict
    quality_profile: dict
    transition_head: TransitionHandle = field(default_factory=TransitionHandle)
    transition_tail: TransitionHandle = field(default_factory=TransitionHandle)
    director_instructions: dict = field(default_factory=dict)


# ── helpers ──────────────────────────────────────────────────────────────────

def _pick(obj: dict, path: str) -> Any:
    """Get value at a dot-separated path."""
    val: Any = obj
    for k in path.split("."):
        if not isinstance(val, dict):
            return None
        val = val.get(k)
    return val


def _scene_time_ranges(instance: dict) -> list[tuple[dict, float, float]]:
    """Compute absolute (start, end) for each scene from timeline videoClips.

    Returns list of (scene_dict, start_sec, end_sec) sorted by sceneNumber.
    """
    production = instance.get("production") or {}
    scenes = sorted(
        production.get("scenes") or [],
        key=lambda s: s.get("sceneNumber", 0),
    )
    if not scenes:
        return []

    # Build shot→scene mapping
    shot_to_scene: dict[str, dict] = {}
    for scene in scenes:
        for ref in scene.get("shotRefs") or []:
            ref_id = ref.get("id") or ref.get("logicalId") or ""
            if ref_id:
                shot_to_scene[ref_id] = scene

    # Get timeline clip positions
    timelines = (instance.get("assembly") or {}).get("timelines") or []
    tl = timelines[0] if timelines else {}
    video_clips = tl.get("videoClips") or []

    # Map each scene to its earliest clip start and latest clip end
    scene_id_to_range: dict[str, tuple[float, float]] = {}
    for clip in video_clips:
        source_id = (clip.get("sourceRef") or {}).get("id", "")
        scene = shot_to_scene.get(source_id)
        if not scene:
            continue
        scene_id = scene.get("id") or scene.get("logicalId") or ""
        clip_start = float(clip.get("timelineStartSec", 0))
        clip_end = clip_start + float(clip.get("durationSec", 0))

        if scene_id in scene_id_to_range:
            prev_start, prev_end = scene_id_to_range[scene_id]
            scene_id_to_range[scene_id] = (
                min(prev_start, clip_start),
                max(prev_end, clip_end),
            )
        else:
            scene_id_to_range[scene_id] = (clip_start, clip_end)

    # Fallback: derive from targetDurationSec if no timeline
    if not scene_id_to_range:
        cursor = 0.0
        for scene in scenes:
            dur = float(scene.get("targetDurationSec", 0))
            scene_id = scene.get("id") or scene.get("logicalId") or ""
            scene_id_to_range[scene_id] = (cursor, cursor + dur)
            cursor += dur

    result = []
    for scene in scenes:
        scene_id = scene.get("id") or scene.get("logicalId") or ""
        start, end = scene_id_to_range.get(scene_id, (0.0, 0.0))
        result.append((scene, start, end))

    return result


# ── audio slicing ────────────────────────────────────────────────────────────

def slice_audio_for_scene(
    scene_start: float,
    scene_end: float,
    instance: dict,
) -> list[AudioSlice]:
    """Slice all audio tracks to a scene's time range.

    For each audio clip that overlaps [scene_start, scene_end]:
      1. Compute intersection
      2. Remap to scene-local time (subtract scene_start)
      3. Apply fade if the slice starts/ends mid-track
      4. Preserve gainDb and pan from the render plan
    """
    timelines = (instance.get("assembly") or {}).get("timelines") or []
    tl = timelines[0] if timelines else {}
    audio_clips = tl.get("audioClips") or []

    # Build gain/pan lookup from render plan
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    rp = render_plans[0] if render_plans else {}
    track_info: dict[str, dict] = {}
    for op in rp.get("operations") or []:
        if op.get("opType") == "audioMix":
            for track in op.get("tracks") or []:
                ref_id = (track.get("audioRef") or {}).get("id", "")
                if ref_id:
                    track_info[ref_id] = {
                        "gainDb": float(track.get("gainDb", 0)),
                        "pan": float(track.get("pan", 0)),
                    }

    # Build asset lookup
    audio_assets = (instance.get("assetLibrary") or {}).get("audioAssets") or []
    asset_by_id: dict[str, dict] = {}
    for a in audio_assets:
        for key in (a.get("id", ""), a.get("logicalId", "")):
            if key:
                asset_by_id[key] = a

    slices: list[AudioSlice] = []
    for clip in audio_clips:
        source_id = (clip.get("sourceRef") or {}).get("id", "")
        clip_start = float(clip.get("timelineStartSec", 0))
        clip_dur = float(clip.get("durationSec", 0))
        clip_end = clip_start + clip_dur

        # Check overlap with scene range
        inter_start = max(clip_start, scene_start)
        inter_end = min(clip_end, scene_end)
        if inter_end <= inter_start:
            continue  # no overlap

        # Remap to scene-local time
        local_start = inter_start - scene_start
        local_end = inter_end - scene_start

        # Detect mid-track slicing for fades
        fade_in = 0.0
        fade_out = 0.0

        # If clip has a transitionIn and we're starting at the clip start, use it
        t_in = clip.get("transitionIn") or {}
        if t_in.get("type") == "fade" and abs(inter_start - clip_start) < 0.01:
            fade_in = float(t_in.get("durationSec", 0))

        # If clip has a transitionOut and we're ending at the clip end, use it
        t_out = clip.get("transitionOut") or {}
        if t_out.get("type") == "fade" and abs(inter_end - clip_end) < 0.01:
            fade_out = float(t_out.get("durationSec", 0))

        # If we're slicing mid-track (not at natural boundary), add a short crossfade
        if inter_start > clip_start + 0.01 and fade_in == 0.0:
            fade_in = min(0.3, (inter_end - inter_start) * 0.1)
        if inter_end < clip_end - 0.01 and fade_out == 0.0:
            fade_out = min(0.3, (inter_end - inter_start) * 0.1)

        info = track_info.get(source_id, {})
        asset = asset_by_id.get(source_id, {})

        slices.append(AudioSlice(
            audio_asset_id=source_id,
            audio_asset=asset,
            source_start_sec=inter_start,
            source_end_sec=inter_end,
            local_start_sec=local_start,
            local_end_sec=local_end,
            gain_db=info.get("gainDb", 0.0),
            pan=info.get("pan", 0.0),
            fade_in_sec=fade_in,
            fade_out_sec=fade_out,
        ))

    return slices


# ── color grade decomposition ────────────────────────────────────────────────

def decompose_color_grade(
    scene_start: float,
    scene_end: float,
    total_duration: float,
    instance: dict,
) -> dict:
    """Derive per-scene color grade parameters from the global intent.

    Uses the scene's midpoint time to interpolate along the color arc
    defined by the director's colorDirection or renderPlan colorGrade intent.

    Returns dict with brightness, contrast, saturation keys.
    """
    # Try renderPlan colorGrade intent first
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    rp = render_plans[0] if render_plans else {}
    intent = ""
    strength = 1.0
    for op in rp.get("operations") or []:
        if op.get("opType") == "colorGrade":
            intent = op.get("intent", "")
            strength = float(op.get("strength", 1.0))
            break

    # Fallback to directorInstructions
    if not intent:
        intent = _pick(instance, "canonicalDocuments.directorInstructions.colorDirection") or ""

    if not intent:
        return {"brightness": 0.0, "contrast": 1.0, "saturation": 1.0}

    d = intent.lower()

    # Parse the base grade (same as assemble.py _parse_color_direction)
    base_brightness = 0.0
    base_contrast = 1.0
    base_saturation = 1.0

    if "desaturated" in d or "muted" in d:
        base_saturation = 0.75
    elif "vibrant" in d or ("saturated" in d and "desaturated" not in d):
        base_saturation = 1.3
    if "warm" in d or "amber" in d:
        base_brightness, base_contrast = 0.05, 1.05
    if "cool" in d or "cold" in d or "blue" in d:
        base_brightness = -0.03
    if "high contrast" in d:
        base_contrast = 1.2
    if "dark" in d or "crushed" in d or "noir" in d:
        base_brightness, base_contrast = -0.05, 1.15
        base_saturation = min(base_saturation, 0.85)
    if "lifted blacks" in d or "film look" in d or "filmic" in d:
        base_brightness, base_contrast = 0.04, 0.95
    if "cinematic" in d:
        base_contrast = max(base_contrast, 1.08)
        base_saturation = min(base_saturation, 0.9)

    # Detect temporal arc keywords for interpolation
    # e.g., "desaturated ... golden warmth introduced at 12s"
    warm_brightness = 0.05
    warm_contrast = 1.05
    warm_saturation = 1.0

    has_temporal_arc = ("introduced" in d or "transition" in d or "arc" in d
                        or "warmth" in d or "golden" in d)

    if not has_temporal_arc or total_duration <= 0:
        # No temporal arc — use uniform base grade scaled by strength
        return {
            "brightness": round(base_brightness * strength, 3),
            "contrast": round(1.0 + (base_contrast - 1.0) * strength, 3),
            "saturation": round(1.0 + (base_saturation - 1.0) * strength, 3),
        }

    # Interpolate: scene midpoint as fraction of total duration
    midpoint = (scene_start + scene_end) / 2.0
    t = midpoint / total_duration  # 0..1

    # Parse warm transition point from intent (e.g., "at 12s")
    import re
    time_match = re.search(r"at\s+(\d+(?:\.\d+)?)\s*s", d)
    if time_match:
        warm_start = float(time_match.group(1)) / total_duration
    else:
        warm_start = 0.75  # default: warm starts at 75% of duration

    # Smooth interpolation: before warm_start use base, after use warm target
    if t < warm_start:
        # Interpolate slightly toward warm as we approach the transition
        blend = (t / warm_start) * 0.15  # max 15% blend before transition
    else:
        # Ramp up to full warm
        blend = 0.15 + 0.85 * min(1.0, (t - warm_start) / (1.0 - warm_start))

    brightness = base_brightness + (warm_brightness - base_brightness) * blend
    contrast = base_contrast + (warm_contrast - base_contrast) * blend
    saturation = base_saturation + (warm_saturation - base_saturation) * blend

    return {
        "brightness": round(brightness * strength, 3),
        "contrast": round(1.0 + (contrast - 1.0) * strength, 3),
        "saturation": round(1.0 + (saturation - 1.0) * strength, 3),
    }


# ── main splitter ────────────────────────────────────────────────────────────

def split_instance_by_scene(instance: dict) -> list[SceneRenderContext]:
    """Decompose a v3 instance into per-scene render contexts.

    Each context is self-contained: it has the scene's shots, sliced audio,
    per-scene color grade, and transition handles.

    Parameters
    ----------
    instance : Full v3 GVPP instance dict.

    Returns
    -------
    list[SceneRenderContext] sorted by sceneNumber.
    """
    scene_ranges = _scene_time_ranges(instance)
    if not scene_ranges:
        log.warning("no_scenes_found")
        return []

    # Quality profile
    qps = instance.get("qualityProfiles") or []
    qp = (qps[0] if qps else {}).get("profile") or {}

    # Director instructions
    di = _pick(instance, "canonicalDocuments.directorInstructions") or {}

    # Total duration from timeline or project
    timelines = (instance.get("assembly") or {}).get("timelines") or []
    tl = timelines[0] if timelines else {}
    total_dur = float(tl.get("durationSec", 0))
    if total_dur <= 0:
        total_dur = float((instance.get("project") or {}).get("targetRuntimeSec", 0))
    if total_dur <= 0 and scene_ranges:
        total_dur = scene_ranges[-1][2]  # end of last scene

    # Shot index
    production = instance.get("production") or {}
    shots_by_id: dict[str, dict] = {}
    for s in production.get("shots") or []:
        for key in (s.get("id", ""), s.get("logicalId", "")):
            if key:
                shots_by_id[key] = s

    contexts: list[SceneRenderContext] = []

    for idx, (scene, start, end) in enumerate(scene_ranges):
        # Gather shots for this scene
        scene_shots: list[dict] = []
        for ref in scene.get("shotRefs") or []:
            ref_id = ref.get("id") or ref.get("logicalId") or ""
            shot = shots_by_id.get(ref_id)
            if shot:
                scene_shots.append(shot)

        # Slice audio
        audio_slices = slice_audio_for_scene(start, end, instance)

        # Decompose color grade
        grade_params = decompose_color_grade(start, end, total_dur, instance)

        # Transition handles
        t_head = TransitionHandle()
        t_tail = TransitionHandle()

        if idx > 0:
            t_in = scene.get("transitionIn") or {}
            t_type = t_in.get("type", "cut")
            if t_type != "cut":
                t_head = TransitionHandle(
                    duration_sec=float(t_in.get("durationSec", 0.5)),
                    type=t_type,
                )

        if idx < len(scene_ranges) - 1:
            t_out = scene.get("transitionOut") or {}
            t_type = t_out.get("type", "cut")
            if t_type != "cut":
                t_tail = TransitionHandle(
                    duration_sec=float(t_out.get("durationSec", 0.5)),
                    type=t_type,
                )

        contexts.append(SceneRenderContext(
            scene=scene,
            scene_index=idx,
            scene_start_sec=start,
            scene_end_sec=end,
            shots=scene_shots,
            audio_slices=audio_slices,
            color_grade_params=grade_params,
            quality_profile=qp,
            transition_head=t_head,
            transition_tail=t_tail,
            director_instructions=di,
        ))

    log.info(
        "split_complete",
        scenes=len(contexts),
        total_shots=sum(len(c.shots) for c in contexts),
        total_audio_slices=sum(len(c.audio_slices) for c in contexts),
    )

    return contexts
