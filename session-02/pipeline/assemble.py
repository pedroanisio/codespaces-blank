"""
assemble.py — FFmpeg assembly layer (v3 schema).

Executes the renderPlan operation sequence from the v3 instance:
  - ConcatOp     → concatenate shot clips in scene/shot order
  - AudioMixOp   → composite audio tracks with timeline timing + gain + pan
  - ColorGradeOp → FFmpeg eq filter from operation intent/strength or directorInstructions
  - EncodeOp     → FFmpeg final encode using compression settings from the operation
  - TransitionOp → FFmpeg xfade between clips (dissolve/fade/wipe/etc.)
  - FilterOp     → FFmpeg filtergraph passthrough

Pre-flight checks:
  - editVersions[].approvedForRender must be True (or --force)
  - spatialConsistency constraints are validated and warnings emitted

All intermediate files are written under output_dir/intermediate/.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _pick(obj: dict, path: str) -> Any:
    val: Any = obj
    for k in path.split("."):
        if not isinstance(val, dict):
            return None
        val = val.get(k)
    return val


def _shot_id(shot: dict) -> str:
    return shot.get("logicalId") or shot.get("id") or ""


# ── Pre-flight: approval gate (#4) ───────────────────────────────────────────

class ApprovalError(RuntimeError):
    """Raised when no editVersion is approved for render."""


def check_approval(instance: dict, *, force: bool = False) -> None:
    """Verify at least one editVersion has approvedForRender=True.

    Raises ApprovalError unless force=True.
    """
    edit_versions = (instance.get("assembly") or {}).get("editVersions") or []
    if not edit_versions:
        if force:
            log.warning("No editVersions found — proceeding (--force)")
            return
        raise ApprovalError(
            "No editVersions in assembly. "
            "Create an editVersion with approvedForRender: true, or use force=True."
        )

    approved = [ev for ev in edit_versions if ev.get("approvedForRender") is True]
    if not approved:
        names = [ev.get("name", ev.get("id", "?")) for ev in edit_versions]
        if force:
            log.warning(
                "No editVersion approved for render (found: %s) — proceeding (--force)",
                ", ".join(names),
            )
            return
        raise ApprovalError(
            f"No editVersion has approvedForRender=true. "
            f"Found: {', '.join(names)}. Set approvedForRender: true or use force=True."
        )

    log.info("✓ Approved editVersion: %s", approved[0].get("name", approved[0].get("id")))


# ── Pre-flight: spatial consistency validation (#10) ──────────────────────────

def validate_spatial_consistency(instance: dict) -> list[str]:
    """Validate spatial consistency constraints across scenes and shots.

    Returns a list of warning/error messages.
    """
    warnings: list[str] = []
    production = instance.get("production") or {}
    scenes = production.get("scenes") or []
    shots_by_id: dict[str, dict] = {}
    for s in production.get("shots") or []:
        shots_by_id[s.get("id", "")] = s
        shots_by_id[s.get("logicalId", "")] = s

    for scene in scenes:
        sc = scene.get("spatialConsistency") or {}
        if not sc.get("required"):
            continue

        scene_name = scene.get("name", scene.get("id", "?"))
        shot_refs = scene.get("shotRefs") or []

        # Check 180-degree rule
        if sc.get("enforce180DegreeRule"):
            camera_positions = []
            for ref in shot_refs:
                shot = shots_by_id.get(ref.get("id", ""))
                if not shot:
                    continue
                spec = shot.get("cinematicSpec") or {}
                extrinsics = spec.get("cameraExtrinsics") or {}
                transform = extrinsics.get("transform") or {}
                pos = transform.get("position")
                if pos:
                    camera_positions.append((shot.get("name", shot.get("id")), pos))

            if len(camera_positions) >= 2:
                action_line = _find_action_line(scene)
                _check_180_rule(scene_name, camera_positions, warnings,
                                action_line=action_line)

        # Check screen direction consistency
        if sc.get("enforceScreenDirection"):
            for ref in shot_refs:
                shot = shots_by_id.get(ref.get("id", ""))
                if not shot:
                    continue
                spec = shot.get("cinematicSpec") or {}
                if spec.get("cameraAngle") == "over_the_shoulder":
                    bridge = spec.get("spatialBridgeAnchorRef")
                    if not bridge:
                        warnings.append(
                            f"[{scene_name}] Shot {shot.get('name', '?')} uses OTS angle "
                            f"without spatialBridgeAnchorRef — screen direction may be inconsistent"
                        )

        # Check max position drift
        max_drift = sc.get("maxPositionDriftM")
        if max_drift is not None:
            warnings.append(
                f"[{scene_name}] maxPositionDriftM={max_drift} specified — "
                f"runtime drift validation requires generated frames (not enforceable pre-render)"
            )

        # Fix F: Evaluate SpatialRule[] custom rules
        for rule in sc.get("rules") or []:
            _evaluate_spatial_rule(rule, scene_name, shots_by_id, shot_refs, warnings)

    return warnings


def _evaluate_spatial_rule(
    rule: dict,
    scene_name: str,
    shots_by_id: dict[str, dict],
    shot_refs: list[dict],
    warnings: list[str],
) -> None:
    """Evaluate a single SpatialRule against the scene's shots.

    Supports ruleTypes: proximity, exclusion_zone, facing_constraint,
    camera_boundary, relative_position, sightline.
    """
    rule_type = rule.get("ruleType", "")
    severity = rule.get("severity", "warning")
    notes = rule.get("notes", "")
    subject_ref = (rule.get("subjectRef") or {}).get("id", "")
    target_ref = (rule.get("targetRef") or {}).get("id", "")

    subject = shots_by_id.get(subject_ref)
    target = shots_by_id.get(target_ref)

    def _pos(entity: dict | None) -> dict | None:
        if not entity:
            return None
        spec = entity.get("cinematicSpec") or {}
        ext = spec.get("cameraExtrinsics") or {}
        t = ext.get("transform") or {}
        return t.get("position")

    def _distance(a: dict, b: dict) -> float:
        dx = a.get("x", 0) - b.get("x", 0)
        dy = a.get("y", 0) - b.get("y", 0)
        dz = a.get("z", 0) - b.get("z", 0)
        return (dx**2 + dy**2 + dz**2) ** 0.5

    tag = f"[{scene_name}] [{severity}]"

    if rule_type == "proximity":
        sp = _pos(subject)
        tp = _pos(target)
        if sp and tp:
            dist = _distance(sp, tp)
            min_d = rule.get("distanceMinM")
            max_d = rule.get("distanceMaxM")
            if min_d is not None and dist < min_d:
                warnings.append(
                    f"{tag} proximity: {subject_ref} is {dist:.2f}m from {target_ref} "
                    f"(min {min_d}m). {notes}"
                )
            if max_d is not None and dist > max_d:
                warnings.append(
                    f"{tag} proximity: {subject_ref} is {dist:.2f}m from {target_ref} "
                    f"(max {max_d}m). {notes}"
                )

    elif rule_type == "exclusion_zone":
        tp = _pos(target)
        if tp:
            radius = rule.get("distanceMinM", 0)
            for ref in shot_refs:
                shot = shots_by_id.get(ref.get("id", ""))
                sp = _pos(shot)
                if sp and shot and _distance(sp, tp) < radius:
                    warnings.append(
                        f"{tag} exclusion_zone: {shot.get('name', '?')} camera at "
                        f"{_distance(sp, tp):.2f}m violates {radius}m exclusion around "
                        f"{target_ref}. {notes}"
                    )

    elif rule_type == "camera_boundary":
        max_d = rule.get("distanceMaxM")
        if max_d is not None:
            for ref in shot_refs:
                shot = shots_by_id.get(ref.get("id", ""))
                sp = _pos(shot)
                if sp:
                    dist_from_origin = (sp.get("x", 0)**2 + sp.get("z", 0)**2) ** 0.5
                    if dist_from_origin > max_d:
                        warnings.append(
                            f"{tag} camera_boundary: {shot.get('name', '?')} at "
                            f"{dist_from_origin:.2f}m exceeds boundary {max_d}m. {notes}"
                        )

    elif rule_type in ("facing_constraint", "sightline"):
        tol = rule.get("angleToleranceDeg")
        if tol is not None:
            warnings.append(
                f"{tag} {rule_type}: angleToleranceDeg={tol}° specified — "
                f"requires orientation data to validate. {notes}"
            )

    elif rule_type == "relative_position":
        sp = _pos(subject)
        tp = _pos(target)
        if sp and tp:
            dist = _distance(sp, tp)
            min_d = rule.get("distanceMinM")
            max_d = rule.get("distanceMaxM")
            if min_d is not None and dist < min_d:
                warnings.append(f"{tag} relative_position: distance {dist:.2f}m < min {min_d}m. {notes}")
            if max_d is not None and dist > max_d:
                warnings.append(f"{tag} relative_position: distance {dist:.2f}m > max {max_d}m. {notes}")


def _find_action_line(scene: dict) -> tuple[dict, dict] | None:
    """Extract the action_line anchor pair from a scene's sceneSpace.spatialAnchors."""
    space = scene.get("sceneSpace") or {}
    anchors = space.get("spatialAnchors") or []
    by_id: dict[str, dict] = {a.get("anchorId", ""): a for a in anchors}

    for anc in anchors:
        if anc.get("anchorType") == "action_line" and anc.get("linkedAnchorId"):
            linked = by_id.get(anc["linkedAnchorId"])
            if linked and linked.get("position") and anc.get("position"):
                return (anc["position"], linked["position"])
    return None


def _check_180_rule(
    scene_name: str,
    camera_positions: list[tuple[str, dict]],
    warnings: list[str],
    action_line: tuple[dict, dict] | None = None,
) -> None:
    """Check if all cameras are on the same side of the action line.

    When *action_line* is provided (two Position3D dicts from paired
    SpatialAnchors), uses a 2-D cross product on the XZ plane to determine
    the side.  Falls back to a simplified X=0 heuristic otherwise.
    """
    if action_line is not None:
        a, b = action_line
        dx = b.get("x", 0.0) - a.get("x", 0.0)
        dz = b.get("z", 0.0) - a.get("z", 0.0)
        if dx == 0.0 and dz == 0.0:
            return  # degenerate

        sides: list[tuple[str, bool]] = []
        for shot_name, pos in camera_positions:
            cx = pos.get("x", 0.0) - a.get("x", 0.0)
            cz = pos.get("z", 0.0) - a.get("z", 0.0)
            cross = dx * cz - dz * cx
            if abs(cross) < 1e-6:
                continue
            sides.append((shot_name, cross > 0))

        if len(sides) >= 2:
            first_side = sides[0][1]
            for shot_name, side in sides[1:]:
                if side != first_side:
                    warnings.append(
                        f"[{scene_name}] 180-degree rule violation: "
                        f"{shot_name} camera is on the {'positive' if side else 'negative'} "
                        f"side of the action line, first shot is on the "
                        f"{'positive' if first_side else 'negative'} side"
                    )
        return

    # Fallback: simplified X=0 heuristic
    x_signs = []
    for shot_name, pos in camera_positions:
        x = pos.get("x", 0.0)
        if x != 0.0:
            x_signs.append((shot_name, x > 0))

    if len(x_signs) >= 2:
        first_side = x_signs[0][1]
        for shot_name, side in x_signs[1:]:
            if side != first_side:
                warnings.append(
                    f"[{scene_name}] 180-degree rule violation: "
                    f"{shot_name} camera crosses action line "
                    f"(X={'+' if side else '-'} vs first shot X={'+' if first_side else '-'})"
                )


# ── Audio timing from schema-compliant sources (#3) ──────────────────────────

def _resolve_audio_timing(
    asset: dict,
    asset_id: str,
    clip_timing: dict[str, dict],
) -> tuple[float, float]:
    """Resolve audio start time and duration from schema-compliant sources.

    Priority:
      1. timeline.audioClips (authoritative)
      2. SyncPoint.time (TimeRange) — schema-compliant
      3. Legacy syncPoints.timelineInSec/Out (compat)
      4. Default: start=0, duration=30
    """
    # Source 1: timeline audioClips
    timing = clip_timing.get(asset_id)
    if timing:
        return timing["startSec"], timing["durationSec"]

    # Source 2: syncPoints — read the schema-compliant TimeRange
    sync_points = asset.get("syncPoints")
    if isinstance(sync_points, list) and sync_points:
        sp = sync_points[0]
        time_range = sp.get("time") or {}
        start = float(time_range.get("startSec", 0))
        end = float(time_range.get("endSec", 0))
        dur = float(time_range.get("durationSec", 0))
        if end > start:
            return start, end - start
        if dur > 0:
            return start, dur
    elif isinstance(sync_points, dict):
        time_range = sync_points.get("time") or {}
        start = float(time_range.get("startSec", 0))
        end = float(time_range.get("endSec", 0))
        dur = float(time_range.get("durationSec", 0))
        if end > start:
            return start, end - start
        if dur > 0:
            return start, dur
        # Source 3: legacy compat
        t_in = float(sync_points.get("timelineInSec", 0))
        t_out = float(sync_points.get("timelineOutSec", 0))
        if t_out > t_in:
            return t_in, t_out - t_in

    return 0.0, 30.0


# ── Audio codec from schema (#6) ─────────────────────────────────────────────

def _resolve_audio_codec(instance: dict) -> tuple[str, str]:
    """Resolve audio codec and bitrate from AudioTechnicalSpec.

    Returns (ffmpeg_codec, bitrate_flag), e.g. ("aac", "192k").
    """
    codec_map = {
        "aac": "aac",
        "mp3": "libmp3lame",
        "flac": "flac",
        "opus": "libopus",
        "vorbis": "libvorbis",
        "pcm": "pcm_s16le",
    }

    audio_assets = (instance.get("assetLibrary") or {}).get("audioAssets") or []
    for asset in audio_assets:
        spec = asset.get("technicalSpec") or {}
        schema_codec = spec.get("codec", "")
        if schema_codec and schema_codec in codec_map:
            return codec_map[schema_codec], "192k"

    return "aac", "192k"


# ── Fix B: channelLayout enforcement ─────────────────────────────────────────

def _resolve_channel_layout(instance: dict) -> str | None:
    """Resolve audio channel layout from qualityProfile or first audioAsset.

    Returns FFmpeg -ac value string or None (let FFmpeg decide).
    """
    layout_map = {
        "mono": "1", "stereo": "2", "5.1": "6", "7.1": "8",
        "quad": "4", "surround": "3",
    }
    # Check qualityProfile first
    qps = instance.get("qualityProfiles") or []
    qp = (qps[0] if qps else {}).get("profile") or {}
    layout = (qp.get("audio") or {}).get("channelLayout", "")
    if layout and layout in layout_map:
        return layout_map[layout]

    # Check first audioAsset technicalSpec
    for asset in (instance.get("assetLibrary") or {}).get("audioAssets") or []:
        spec = asset.get("technicalSpec") or {}
        cl = spec.get("channelLayout", "")
        if cl and cl in layout_map:
            return layout_map[cl]

    return None


# ── Fix C: compatibleRuntimes validation ─────────────────────────────────────

class RuntimeWarning(UserWarning):
    """Raised when the renderPlan's compatibleRuntimes exclude ffmpeg."""


def check_compatible_runtimes(instance: dict) -> list[str]:
    """Validate that 'ffmpeg' is in the renderPlan's compatibleRuntimes.

    Returns a list of warnings.
    """
    warnings: list[str] = []
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    for rp in render_plans:
        runtimes = rp.get("compatibleRuntimes") or []
        if runtimes and "ffmpeg" not in runtimes:
            name = rp.get("name", rp.get("id", "?"))
            warnings.append(
                f"renderPlan '{name}' declares compatibleRuntimes={runtimes} "
                f"which does not include 'ffmpeg'. This pipeline uses FFmpeg — "
                f"results may not match the intended runtime."
            )
    return warnings


# ── Clip reference resolution ─────────────────────────────────────────────────

def _resolve_clip_refs(
    clip_refs: list[dict],
    shot_clips: dict[str, Path],
) -> list[Path]:
    """Resolve ConcatOp.clipRefs (array of EntityRef) to ordered file paths.

    Returns the paths in the order declared by clipRefs.
    Returns empty list if none of the refs resolve to existing files.
    """
    ordered: list[Path] = []
    for ref in clip_refs:
        ref_id = ref.get("id") or ref.get("logicalId") or ""
        if not ref_id:
            continue
        clip = shot_clips.get(ref_id)
        if clip and clip.exists():
            ordered.append(clip)
        else:
            # Try matching by logicalId derivation (strip version suffix)
            for key, path in shot_clips.items():
                if ref_id.startswith(key) or key.startswith(ref_id):
                    if path.exists():
                        ordered.append(path)
                        break
            else:
                log.warning("clipRef %s could not be resolved to a clip file", ref_id)
    return ordered


# ── Shot ordering ─────────────────────────────────────────────────────────────

def _shots_in_scene_order(
    instance: dict, shot_clips: dict[str, Path],
) -> tuple[list[Path], list[float]]:
    """Return (clip_paths, target_durations) ordered by scene then shot."""
    production = instance.get("production") or {}
    id_to_logical: dict[str, str] = {}
    shot_by_id: dict[str, dict] = {}
    for s in production.get("shots") or []:
        lid = s.get("logicalId", "")
        sid = s.get("id", "")
        if lid:
            id_to_logical[lid] = lid
            shot_by_id[lid] = s
        if sid:
            id_to_logical[sid] = lid
            shot_by_id[sid] = s

    scenes = sorted(
        production.get("scenes") or [],
        key=lambda s: s.get("sceneNumber", 0),
    )

    ordered: list[Path] = []
    durations: list[float] = []
    seen: set[str] = set()
    for scene in scenes:
        for ref in scene.get("shotRefs") or []:
            ref_id = ref.get("id") or ref.get("logicalId") or ""
            logical = id_to_logical.get(ref_id, ref_id)
            if not logical or logical in seen:
                continue
            clip = shot_clips.get(logical)
            if clip and clip.exists():
                ordered.append(clip)
                shot = shot_by_id.get(ref_id) or shot_by_id.get(logical) or {}
                durations.append(float(shot.get("targetDurationSec", 0)))
                seen.add(logical)
            else:
                log.warning("missing clip for shot %s — skipped", ref_id)

    if not ordered:
        for lid, path in shot_clips.items():
            if path.exists():
                ordered.append(path)
                shot = shot_by_id.get(lid) or {}
                durations.append(float(shot.get("targetDurationSec", 0)))

    return ordered, durations


# ── Transition support (#5) ───────────────────────────────────────────────────

def _get_clip_duration(path: Path) -> float:
    """Probe clip duration via ffprobe."""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=5,
        )
        return float(probe.stdout.strip() or "5")
    except Exception:
        return 5.0


def _normalize_filter(
    idx: int,
    target_dur: float,
    actual_dur: float,
) -> str:
    """Build per-clip normalize filter: trim → scale → fps."""
    trim = f"trim=duration={target_dur}," if 0 < target_dur < actual_dur else ""
    return (
        f"[{idx}:v]{trim}setpts=PTS-STARTPTS,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[n{idx}]"
    )


def _concat_clips_ffmpeg(
    clip_paths: list[Path],
    out_path: Path,
    *,
    scenes: list[dict] | None = None,
    target_durations: list[float] | None = None,
) -> None:
    """Concatenate clips with per-scene transitions.

    Supports: cut (default), fade, dissolve, wipe, push, zoom.
    Schema TransitionSpec types: cut, dissolve, fade, wipe, push, zoom, custom.
    """
    if not clip_paths:
        return

    actual_durs = [_get_clip_duration(p) for p in clip_paths]
    targets = target_durations or [0.0] * len(clip_paths)

    has_transitions = False
    if scenes:
        for s in scenes:
            t_in = (s.get("transitionIn") or {}).get("type", "cut")
            t_out = (s.get("transitionOut") or {}).get("type", "cut")
            if t_in != "cut" or t_out != "cut":
                has_transitions = True
                break

    inputs = []
    for p in clip_paths:
        inputs += ["-i", str(p)]

    norm_filters = [
        _normalize_filter(i, targets[i], actual_durs[i])
        for i in range(len(clip_paths))
    ]

    # Effective durations after trimming (used for xfade offsets)
    durations = [
        min(targets[i], actual_durs[i]) if targets[i] > 0 else actual_durs[i]
        for i in range(len(clip_paths))
    ]

    if not has_transitions or len(clip_paths) <= 1:
        concat_filter = "".join(f"[n{i}]" for i in range(len(clip_paths)))
        concat_filter += f"concat=n={len(clip_paths)}:v=1:a=0[vout]"
        all_filters = norm_filters + [concat_filter]

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", ";".join(all_filters),
            "-map", "[vout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return

    # Build xfade filter chain
    xfade_map = {
        "dissolve": "fade",
        "fade": "fade",
        "wipe": "wipeleft",
        "push": "slideleft",
        "zoom": "zoomin",
        "custom": "fade",
    }

    # Build transition list from scenes
    transition_specs: list[dict] = []
    if scenes:
        for s in scenes:
            transition_specs.append(s.get("transitionOut") or {"type": "cut"})

    # Every clip pair gets an xfade so the chain stays continuous.
    # "cut" transitions use a near-zero duration (1 frame ≈ 0.04s).
    _CUT_DUR = 0.04

    filter_parts = list(norm_filters)
    current_offset = 0.0
    prev_label = "[n0]"

    for i in range(len(clip_paths) - 1):
        t_spec = transition_specs[i] if i < len(transition_specs) else {"type": "cut"}
        t_type = t_spec.get("type", "cut")
        t_dur = float(t_spec.get("durationSec", 0.5))

        if t_type == "cut" or t_type not in xfade_map:
            xfade_name = "fade"
            t_dur = _CUT_DUR
        else:
            xfade_name = xfade_map[t_type]
            t_dur = min(t_dur, durations[i] * 0.5, durations[i + 1] * 0.5)

        offset = current_offset + durations[i] - t_dur
        out_label = "[vout]" if i == len(clip_paths) - 2 else f"[v{i}]"
        next_label = f"[n{i + 1}]"

        filter_parts.append(
            f"{prev_label}{next_label}xfade=transition={xfade_name}:duration={t_dur:.2f}:offset={offset:.2f}{out_label}"
        )
        prev_label = out_label
        current_offset = offset

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


# ── Fix A: ConcatOp.method=compose (vertical stack) ──────────────────────────

def _compose_clips_ffmpeg(clip_paths: list[Path], out_path: Path) -> None:
    """Stack clips vertically (compose method) using FFmpeg overlay.

    Schema ConcatOp.method='compose' means clips are composited/stacked,
    not sequentially chained.  The longest clip determines the duration.
    """
    if not clip_paths:
        return
    if len(clip_paths) == 1:
        shutil.copy(clip_paths[0], out_path)
        return

    inputs = []
    for p in clip_paths:
        inputs += ["-i", str(p)]

    # Build overlay chain: stack each clip on top of the previous
    filter_parts = []
    # Normalize all inputs
    for i in range(len(clip_paths)):
        filter_parts.append(
            f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,format=yuva420p,"
            f"colorchannelmixer=aa=0.5[l{i}]"
        )

    # Overlay layers: l0 is base, overlay l1..lN
    prev = f"[l0]"
    for i in range(1, len(clip_paths)):
        out_label = "[vout]" if i == len(clip_paths) - 1 else f"[ov{i}]"
        filter_parts.append(f"{prev}[l{i}]overlay=0:0:shortest=0{out_label}")
        prev = out_label

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "1",
        "-pix_fmt", "yuv420p", "-an",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


# ── Audio mix (#3, #6, #7) ───────────────────────────────────────────────────

def _build_audio_mix_cmd(
    video_path: Path,
    audio_files: dict[str, Path],
    instance: dict,
    out_path: Path,
) -> list[str]:
    """Build FFmpeg command to mix all audio tracks onto the video.

    Reads timing from timeline.audioClips → renderPlan.timeRange → syncPoints.time.
    Reads gain from renderPlan.audioMix.tracks[].gainDb.
    Reads pan from renderPlan.audioMix.tracks[].pan (#7).
    Reads audio codec from AudioTechnicalSpec (#6).
    """
    timelines = (instance.get("assembly") or {}).get("timelines") or []
    tl = timelines[0] if timelines else {}
    tl_audio_clips = tl.get("audioClips") or []

    clip_timing: dict[str, dict] = {}
    for ac in tl_audio_clips:
        ref_id = (ac.get("sourceRef") or {}).get("id", "")
        clip_timing[ref_id] = {
            "startSec": float(ac.get("timelineStartSec", 0)),
            "durationSec": float(ac.get("durationSec", 30)),
        }

    # Build gain + pan + timeRange from renderPlan AudioMixOp
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    rp = render_plans[0] if render_plans else {}
    track_info: dict[str, dict] = {}
    for op in rp.get("operations") or []:
        if op.get("opType") == "audioMix":
            for track in op.get("tracks") or []:
                ref_id = (track.get("audioRef") or {}).get("id", "")
                if ref_id:
                    info: dict[str, Any] = {}
                    if "gainDb" in track:
                        info["gainDb"] = float(track["gainDb"])
                    if "pan" in track:
                        info["pan"] = float(track["pan"])
                    tr = track.get("timeRange") or {}
                    if tr.get("startSec") is not None:
                        info["startSec"] = float(tr["startSec"])
                        end = float(tr.get("endSec", 0))
                        dur = float(tr.get("durationSec", 0))
                        info["durationSec"] = (end - info["startSec"]) if end > info["startSec"] else dur
                    track_info[ref_id] = info

    audio_assets: list[dict] = (instance.get("assetLibrary", {}).get("audioAssets") or [])
    asset_by_key: dict[str, dict] = {}
    for a in audio_assets:
        asset_by_key[a.get("logicalId", "")] = a
        asset_by_key[a.get("id", "")] = a

    audio_codec, audio_bitrate = _resolve_audio_codec(instance)

    # Resolve total timeline duration for audio padding
    tl_duration = float(tl.get("durationSec", 0))
    if not tl_duration:
        tl_duration = float((instance.get("project") or {}).get("targetRuntimeSec", 30))

    inputs: list[str] = ["-i", str(video_path)]
    filter_parts: list[str] = []
    mix_inputs: list[str] = []

    valid_tracks = 0
    for idx, (key, audio_path) in enumerate(audio_files.items()):
        if not audio_path or not audio_path.exists():
            log.warning("audio file missing for %s — skipped", key)
            continue

        asset = asset_by_key.get(key) or {}
        asset_id = asset.get("id", key)

        # Resolve timing (#3)
        t_info = track_info.get(asset_id) or {}
        if "startSec" in t_info and "durationSec" in t_info:
            t_in = t_info["startSec"]
            duration = t_info["durationSec"]
        else:
            t_in, duration = _resolve_audio_timing(asset, asset_id, clip_timing)

        gain_db = t_info.get("gainDb", track_info.get(key, {}).get("gainDb", 0))
        pan_value = t_info.get("pan", track_info.get(key, {}).get("pan", None))

        inputs += ["-i", str(audio_path)]
        stream = idx + 1

        chain = f"[{stream}:a]"
        chain += f"atrim=duration={duration},"
        chain += f"adelay={int(t_in * 1000)}|{int(t_in * 1000)},"
        chain += f"apad=whole_dur={tl_duration}"
        if gain_db != 0:
            chain += f",volume={gain_db}dB"
        if pan_value is not None and pan_value != 0:
            left_gain = max(0, 1.0 - pan_value)
            right_gain = max(0, 1.0 + pan_value)
            chain += f",pan=stereo|c0={left_gain:.2f}*c0|c1={right_gain:.2f}*c0"

        tag = f"[a{idx}]"
        filter_parts.append(chain + tag)
        mix_inputs.append(tag)
        valid_tracks += 1

    if not mix_inputs:
        return ["ffmpeg", "-y", "-i", str(video_path), "-c", "copy", str(out_path)]

    mix_filter = "".join(mix_inputs) + f"amix=inputs={valid_tracks}:normalize=0[aout]"
    filter_parts.append(mix_filter)

    # Fix B: enforce channelLayout from schema
    channel_count = _resolve_channel_layout(instance)
    ac_flag = ["-ac", channel_count] if channel_count else []

    return [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", audio_codec, "-b:a", audio_bitrate,
        *ac_flag,
        str(out_path),
    ]


# ── Color grade (#1, #2) ─────────────────────────────────────────────────────

def _parse_color_direction(direction: str) -> dict:
    """Heuristically derive eq filter params from a color-direction text."""
    d = direction.lower()
    brightness, contrast, saturation = 0.0, 1.0, 1.0
    if "desaturated" in d or "muted" in d:
        saturation = 0.75
    elif "vibrant" in d or ("saturated" in d and "desaturated" not in d):
        saturation = 1.3
    if "warm" in d or "amber" in d:
        brightness, contrast = 0.05, 1.05
    if "cool" in d or "cold" in d or "blue" in d:
        brightness = -0.03
    if "high contrast" in d:
        contrast = 1.2
    if "dark" in d or "crushed" in d or "noir" in d:
        brightness, contrast = -0.05, 1.15
        saturation = min(saturation, 0.85)
    if "lifted blacks" in d or "film look" in d or "filmic" in d:
        brightness, contrast = 0.04, 0.95
    if "cinematic" in d:
        contrast = max(contrast, 1.08)
        saturation = min(saturation, 0.9)
    return {
        "brightness": round(brightness, 3),
        "contrast":   round(contrast,   3),
        "saturation": round(saturation, 3),
    }


def _resolve_lut_path(lut_ref: dict | None, instance: dict) -> Path | None:
    """Resolve a lutRef EntityRef to a .cube file path on disk.

    Searches visualAssets and genericAssets for the referenced entity and
    returns its _filePath if it exists as a readable .cube / .3dl file.
    """
    if not lut_ref:
        return None
    ref_id = lut_ref.get("id") or lut_ref.get("logicalId") or ""
    if not ref_id:
        return None

    for pool_key in ("visualAssets", "genericAssets"):
        for asset in (instance.get("assetLibrary") or {}).get(pool_key) or []:
            if asset.get("id") == ref_id or asset.get("logicalId") == ref_id:
                fp = asset.get("_filePath", "")
                if fp:
                    p = Path(fp)
                    if p.exists() and p.suffix.lower() in (".cube", ".3dl"):
                        return p
    return None


def _resolve_color_grade_params(instance: dict) -> tuple[dict, float, Path | None]:
    """Resolve color grade parameters from renderPlan ColorGradeOp, then directorInstructions.

    Returns (eq_params dict, strength 0-1, lut_path or None).
    """
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    rp = render_plans[0] if render_plans else {}
    strength = 1.0
    lut_path: Path | None = None

    for op in rp.get("operations") or []:
        if op.get("opType") == "colorGrade":
            intent = op.get("intent", "")
            strength = float(op.get("strength", 1.0))
            lut_path = _resolve_lut_path(op.get("lutRef"), instance)
            if intent:
                return _parse_color_direction(intent), strength, lut_path

    color_direction = _pick(instance, "canonicalDocuments.directorInstructions.colorDirection") or ""
    return _parse_color_direction(color_direction), strength, lut_path


def _color_grade_cmd(
    input_path: Path,
    params: dict,
    strength: float,
    out_path: Path,
    *,
    lut_path: Path | None = None,
) -> list[str]:
    """Build color grade FFmpeg command.

    Supports:
      - LUT application via lut3d filter when lutRef resolves to a .cube file
      - eq filter from intent text heuristic, scaled by strength
      - -c copy passthrough when grade is a no-op
      - Near-lossless CRF 1 intermediate when re-encoding is needed
    """
    brightness = params.get("brightness", 0.0) * strength
    contrast = 1.0 + (params.get("contrast", 1.0) - 1.0) * strength
    saturation = 1.0 + (params.get("saturation", 1.0) - 1.0) * strength

    is_noop = (
        abs(brightness) < 0.001
        and abs(contrast - 1.0) < 0.001
        and abs(saturation - 1.0) < 0.001
        and lut_path is None
    )
    if is_noop:
        return ["ffmpeg", "-y", "-i", str(input_path), "-c", "copy", str(out_path)]

    # Build filter chain
    filters: list[str] = []
    if lut_path is not None:
        lut_str = str(lut_path).replace("\\", "/").replace(":", "\\:")
        filters.append(f"lut3d='{lut_str}'")
    if not (abs(brightness) < 0.001 and abs(contrast - 1.0) < 0.001 and abs(saturation - 1.0) < 0.001):
        filters.append(
            f"eq=brightness={brightness:.3f}"
            f":contrast={contrast:.3f}"
            f":saturation={saturation:.3f}"
        )

    vf = ",".join(filters)
    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "1",
        "-movflags", "+faststart",
        "-c:a", "copy",
        str(out_path),
    ]


# ── Final encode ──────────────────────────────────────────────────────────────

def _encode_cmd(
    input_path: Path,
    qp: dict,
    output_path: Path,
    *,
    render_plan: dict | None = None,
    audio_codec: str = "aac",
    audio_bitrate: str = "192k",
) -> list[str]:
    """Build final encode command from qualityProfile + renderPlan EncodeOp."""
    video = qp.get("video") or {}
    resolution = video.get("resolution") or {}
    width = resolution.get("widthPx") or resolution.get("width", 1920)
    height = resolution.get("heightPx") or resolution.get("height", 1080)
    fps = (video.get("frameRate") or {}).get("fps", 24)
    audio_cfg = qp.get("audio") or {}
    sample_rate = audio_cfg.get("sampleRateHz", 44100)

    codec = "libx264"
    bitrate_flag: list[str] = ["-crf", "18"]
    profile_flag: list[str] = []
    if render_plan:
        for op in render_plan.get("operations") or []:
            if op.get("opType") == "encode":
                comp = op.get("compression") or {}
                if comp.get("codec"):
                    codec = comp["codec"]
                if comp.get("bitrateMbps"):
                    bitrate_flag = ["-b:v", f"{comp['bitrateMbps']}M"]
                elif comp.get("crf"):
                    bitrate_flag = ["-crf", str(comp["crf"])]
                if comp.get("profile"):
                    profile_flag = ["-profile:v", comp["profile"]]
                if comp.get("maxBitrateMbps"):
                    bitrate_flag += ["-maxrate", f"{comp['maxBitrateMbps']}M",
                                     "-bufsize", f"{comp['maxBitrateMbps'] * 2}M"]
                if comp.get("gopLength"):
                    bitrate_flag += ["-g", str(comp["gopLength"])]

    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"scale={width}:{height},fps={fps}",
        "-pix_fmt", "yuv420p",
        "-c:v", codec, *bitrate_flag, *profile_flag, "-preset", "fast",
        "-movflags", "+faststart",
        "-c:a", audio_codec, "-b:a", audio_bitrate,
        "-ar", str(sample_rate),
        str(output_path),
    ]


# ── FinalOutput population (#9) ──────────────────────────────────────────────

def populate_final_output(instance: dict, final_path: Path) -> dict:
    """Populate deliverables[0] with post-render metadata."""
    deliverables = instance.get("deliverables") or []
    if not deliverables:
        return instance

    stat = final_path.stat()
    file_hash = hashlib.sha256(final_path.read_bytes()).hexdigest()

    runtime = 0.0
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "csv=p=0", str(final_path)],
            capture_output=True, text=True, timeout=10,
        )
        runtime = float(probe.stdout.strip() or "0")
    except Exception:
        pass

    deliverables[0]["runtimeSec"] = round(runtime, 2)
    deliverables[0]["_filePath"] = str(final_path)
    deliverables[0]["_fileSizeBytes"] = stat.st_size
    deliverables[0]["_checksum"] = {"algorithm": "sha256", "value": file_hash}
    deliverables[0]["_renderedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    version = deliverables[0].get("version") or {}
    version["state"] = "generating"
    deliverables[0]["version"] = version

    instance["deliverables"] = deliverables
    return instance


# ── Operation DAG executor ────────────────────────────────────────────────────

# Supported opTypes and the executor functions they dispatch to.
# Each executor receives (op, ctx) and returns the output Path.
# ctx holds instance, paths, intermediate dir, etc.

def _exec_retime(op: dict, input_path: Path, out_path: Path) -> list[str]:
    """Build FFmpeg command for RetimeOp (speed change / reverse / freeze frames)."""
    retime = op.get("retime") or {}
    speed_pct = float(retime.get("speedPercent", 100))
    reverse = retime.get("reverse", False)
    interpolation = retime.get("frameInterpolation", "none")
    freeze_frames = retime.get("freezeFrames") or []

    pts_factor = 100.0 / speed_pct if speed_pct > 0 else 1.0
    atempo = speed_pct / 100.0

    vf_parts = []
    if reverse:
        vf_parts.append("reverse")
    if abs(speed_pct - 100) > 0.1:
        vf_parts.append(f"setpts={pts_factor:.4f}*PTS")
    if interpolation == "blend" and abs(speed_pct - 100) > 0.1:
        vf_parts.append("minterpolate='mi_mode=blend'")
    elif interpolation == "optical_flow" and abs(speed_pct - 100) > 0.1:
        vf_parts.append("minterpolate='mi_mode=mci:mc_mode=aobmc:vsbmc=1'")

    # Fix D: freezeFrames — freeze at specified timestamps for 1 second each
    # Uses FFmpeg tpad filter to duplicate frames at the given timestamps
    if freeze_frames:
        # Build a select expression that pauses at each timestamp
        # Each freeze holds for ~1 second (24 frames at 24fps)
        hold_frames = 24
        for ts in sorted(freeze_frames):
            # freeze: duplicate the frame at timestamp ts for hold_frames extra frames
            vf_parts.append(
                f"tpad=stop_mode=clone:stop_duration=0,"
                f"setpts=PTS+if(gte(T\\,{ts:.3f})*lt(T\\,{ts:.3f}+1/{hold_frames})\\,1\\,0)/TB"
            )
        # Simpler approach: use the freeze filter (available in newer FFmpeg)
        # freeze=n=FRAME:d=DURATION for each freeze point
        vf_parts_clean = [p for p in vf_parts if not p.startswith("tpad=")]
        for ts in sorted(freeze_frames):
            vf_parts_clean.append(f"freeze=t={ts:.3f}:d=1")
        vf_parts = vf_parts_clean

    af_parts = []
    if reverse:
        af_parts.append("areverse")
    if abs(speed_pct - 100) > 0.1:
        t = atempo
        while t > 2.0:
            af_parts.append("atempo=2.0")
            t /= 2.0
        while t < 0.5:
            af_parts.append("atempo=0.5")
            t *= 2.0
        af_parts.append(f"atempo={t:.4f}")

    cmd = ["ffmpeg", "-y", "-i", str(input_path)]
    if vf_parts:
        cmd += ["-vf", ",".join(vf_parts)]
    if af_parts:
        cmd += ["-af", ",".join(af_parts)]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "1", "-c:a", "aac", str(out_path)]
    return cmd


def _exec_filter(op: dict, input_path: Path, out_path: Path) -> list[str]:
    """Build FFmpeg command for FilterOp (generic filter pass-through)."""
    filter_type = op.get("filterType", "")
    parameters = op.get("parameters") or {}

    # Map common filter types to FFmpeg filtergraphs
    if filter_type == "denoise":
        strength = parameters.get("strength", 5)
        vf = f"nlmeans={strength}"
    elif filter_type == "sharpen":
        amount = parameters.get("amount", 1.0)
        vf = f"unsharp=5:5:{amount}:5:5:0"
    elif filter_type == "stabilize":
        crop = parameters.get("maxCropPercent", 10)
        vf = f"vidstabdetect,vidstabtransform=crop=black:zoom={crop}"
    elif filter_type == "ffmpeg":
        # Direct FFmpeg filter string pass-through
        vf = parameters.get("vf", "null")
    else:
        # Unknown filter type: pass through as-is if it looks like an FFmpeg filter
        vf = filter_type if filter_type else "null"

    return [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "1",
        "-c:a", "copy",
        str(out_path),
    ]


def execute_operation_dag(
    operations: list[dict],
    instance: dict,
    output_dir: Path,
    shot_clips: dict[str, Path],
    audio_files: dict[str, Path],
) -> Path:
    """Execute renderPlan operations in declared order.

    Supported opTypes: concat, audioMix, colorGrade, encode, filter, retime.
    Unsupported opTypes (overlay, transition, manim, custom) are logged and skipped.

    Returns the path to the final output file.
    """
    inter = output_dir / "intermediate"
    inter.mkdir(parents=True, exist_ok=True)

    quality_profiles = instance.get("qualityProfiles") or []
    qp = (quality_profiles[0] if quality_profiles else {}).get("profile") or {}
    audio_codec, audio_bitrate = _resolve_audio_codec(instance)
    scenes = sorted(
        (instance.get("production") or {}).get("scenes") or [],
        key=lambda s: s.get("sceneNumber", 0),
    )

    # The render plan operations reference each other via inputRef/outputRef.
    # We track the "current" video path, updated after each step.
    current_path: Path | None = None
    step_num = 0

    for op in operations:
        op_type = op.get("opType", "")
        op_id = op.get("opId", f"step-{step_num}")
        step_num += 1

        if op_type == "concat":
            # Use clipRefs from the operation as authoritative ordering
            # when provided (schema: ConcatOp.clipRefs is required).
            # Fall back to scene-derived order only if clipRefs can't resolve.
            clip_refs = op.get("clipRefs") or []
            ordered_clips = _resolve_clip_refs(clip_refs, shot_clips)
            if not ordered_clips:
                ordered_clips, clip_targets = _shots_in_scene_order(instance, shot_clips)
            else:
                clip_targets = [0.0] * len(ordered_clips)
            if not ordered_clips:
                raise RuntimeError("No shot clips available to assemble")
            out = inter / f"{step_num:02d}_{op_id}.mp4"
            method = op.get("method", "chain")
            log.info("▶ [%s] concat — %d clips (method=%s)", op_id, len(ordered_clips), method)
            if method == "compose":
                _compose_clips_ffmpeg(ordered_clips, out)
            else:
                _concat_clips_ffmpeg(ordered_clips, out, scenes=scenes, target_durations=clip_targets)
            current_path = out

        elif op_type == "audioMix":
            if current_path is None:
                log.warning("[%s] audioMix with no prior video — skipping", op_id)
                continue
            out = inter / f"{step_num:02d}_{op_id}.mp4"
            log.info("▶ [%s] audioMix — %d tracks", op_id, len(audio_files))
            cmd = _build_audio_mix_cmd(current_path, audio_files, instance, out)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("[%s] audioMix failed:\n%s", op_id, result.stderr.decode())
                shutil.copy(current_path, out)
            current_path = out

        elif op_type == "colorGrade":
            if current_path is None:
                continue
            intent = op.get("intent", "")
            strength = float(op.get("strength", 1.0))
            lut_path = _resolve_lut_path(op.get("lutRef"), instance)
            params = _parse_color_direction(intent) if intent else _parse_color_direction(
                _pick(instance, "canonicalDocuments.directorInstructions.colorDirection") or ""
            )
            out = inter / f"{step_num:02d}_{op_id}.mp4"
            log.info("▶ [%s] colorGrade — strength=%.2f lut=%s", op_id, strength, lut_path)
            cmd = _color_grade_cmd(current_path, params, strength, out, lut_path=lut_path)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("[%s] colorGrade failed:\n%s", op_id, result.stderr.decode())
                shutil.copy(current_path, out)
            current_path = out

        elif op_type == "encode":
            if current_path is None:
                continue
            project_name = (
                (instance.get("project") or {}).get("name", "output")
                .lower().replace(" ", "-")[:40]
            )
            out = output_dir / f"{project_name}.mp4"
            rp = {"operations": [op]}  # wrap single op for _encode_cmd
            log.info("▶ [%s] encode → %s", op_id, out.name)
            cmd = _encode_cmd(current_path, qp, out, render_plan=rp,
                              audio_codec=audio_codec, audio_bitrate=audio_bitrate)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("[%s] encode failed:\n%s", op_id, result.stderr.decode())
                shutil.copy(current_path, out)
            current_path = out

        elif op_type == "filter":
            if current_path is None:
                continue
            out = inter / f"{step_num:02d}_{op_id}.mp4"
            log.info("▶ [%s] filter — type=%s", op_id, op.get("filterType", "?"))
            cmd = _exec_filter(op, current_path, out)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("[%s] filter failed:\n%s", op_id, result.stderr.decode())
                shutil.copy(current_path, out)
            current_path = out

        elif op_type == "retime":
            if current_path is None:
                continue
            out = inter / f"{step_num:02d}_{op_id}.mp4"
            log.info("▶ [%s] retime — speed=%s%% reverse=%s", op_id,
                     (op.get("retime") or {}).get("speedPercent", 100),
                     (op.get("retime") or {}).get("reverse", False))
            cmd = _exec_retime(op, current_path, out)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("[%s] retime failed:\n%s", op_id, result.stderr.decode())
                shutil.copy(current_path, out)
            current_path = out

        elif op_type == "transition":
            # Fix E: TransitionOp — apply xfade between fromRef and toRef clips
            if current_path is None:
                continue
            spec = op.get("spec") or {}
            t_type = spec.get("type", "dissolve")
            t_dur = float(spec.get("durationSec", 0.5))
            from_ref = (op.get("fromRef") or {}).get("id", "")
            to_ref = (op.get("toRef") or {}).get("id", "")

            xfade_map = {
                "dissolve": "fade", "fade": "fade", "wipe": "wipeleft",
                "push": "slideleft", "zoom": "zoomin", "custom": "fade",
            }
            xfade_name = xfade_map.get(t_type, "fade")

            # Resolve the two clips from shot_clips
            from_clip = shot_clips.get(from_ref)
            to_clip = shot_clips.get(to_ref)
            if from_clip and to_clip and from_clip.exists() and to_clip.exists():
                out = inter / f"{step_num:02d}_{op_id}.mp4"
                from_dur = _get_clip_duration(from_clip)
                t_dur = min(t_dur, from_dur * 0.5)
                offset = from_dur - t_dur
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(from_clip), "-i", str(to_clip),
                    "-filter_complex",
                    f"[0:v][1:v]xfade=transition={xfade_name}:duration={t_dur:.2f}:offset={offset:.2f}[vout]",
                    "-map", "[vout]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "1",
                    "-pix_fmt", "yuv420p", "-an",
                    str(out),
                ]
                log.info("▶ [%s] transition — %s (%s, %.1fs)", op_id, t_type, xfade_name, t_dur)
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode != 0:
                    log.error("[%s] transition failed:\n%s", op_id, result.stderr.decode())
                else:
                    current_path = out
            else:
                log.warning("[%s] transition: cannot resolve fromRef=%s or toRef=%s", op_id, from_ref, to_ref)

        else:
            log.warning("▶ [%s] unsupported opType '%s' — skipped", op_id, op_type)

    if current_path is None:
        raise RuntimeError("Operation DAG produced no output")
    return current_path


# ── public API ────────────────────────────────────────────────────────────────

def assemble(
    instance: dict,
    output_dir: Path,
    shot_clips: dict[str, Path],
    audio_files: dict[str, Path],
    *,
    force: bool = False,
) -> Path:
    """
    Assemble a final video from shot clips and audio tracks.

    When the renderPlan contains operations, executes them as a DAG.
    Otherwise falls back to the default 4-step pipeline.

    Returns the path to the final encoded file.
    """
    inter = output_dir / "intermediate"
    inter.mkdir(parents=True, exist_ok=True)

    # ── Pre-flight ────────────────────────────────────────────────────────────
    check_approval(instance, force=force)
    spatial_warnings = validate_spatial_consistency(instance)
    for w in spatial_warnings:
        log.warning("spatial: %s", w)
    # Fix C: warn if FFmpeg not in compatibleRuntimes
    for w in check_compatible_runtimes(instance):
        log.warning("runtime: %s", w)

    # ── Check for renderPlan operations ───────────────────────────────────────
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    render_plan = render_plans[0] if render_plans else {}
    operations = render_plan.get("operations") or []

    if operations:
        log.info("Executing renderPlan DAG (%d operations)", len(operations))
        final_path = execute_operation_dag(
            operations, instance, output_dir, shot_clips, audio_files,
        )
        if final_path.exists():
            populate_final_output(instance, final_path)
        return final_path

    # ── Fallback: default 4-step pipeline ─────────────────────────────────────
    log.info("No renderPlan operations — using default pipeline")

    grade_params, grade_strength, lut_path = _resolve_color_grade_params(instance)
    quality_profiles = instance.get("qualityProfiles") or []
    qp = (quality_profiles[0] if quality_profiles else {}).get("profile") or {}
    audio_codec, audio_bitrate = _resolve_audio_codec(instance)

    project_name = (
        (instance.get("project") or {}).get("name", "output")
        .lower().replace(" ", "-")[:40]
    )
    output_filename = f"{project_name}.mp4"

    scenes = sorted(
        (instance.get("production") or {}).get("scenes") or [],
        key=lambda s: s.get("sceneNumber", 0),
    )

    ordered_clips, clip_targets = _shots_in_scene_order(instance, shot_clips)
    if not ordered_clips:
        raise RuntimeError("No shot clips available to assemble")

    concat_path = inter / "01_concat.mp4"
    log.info("▶ concat — %d clips → %s", len(ordered_clips), concat_path.name)
    _concat_clips_ffmpeg(ordered_clips, concat_path, scenes=scenes, target_durations=clip_targets)

    mixed_path = inter / "02_mixed.mp4"
    log.info("▶ audio_mix — %d track(s) → %s", len(audio_files), mixed_path.name)
    cmd = _build_audio_mix_cmd(concat_path, audio_files, instance, mixed_path)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("audio mix failed:\n%s", result.stderr.decode())
        shutil.copy(concat_path, mixed_path)

    graded_path = inter / "03_graded.mp4"
    log.info(
        "▶ color_grade — b=%.2f c=%.2f s=%.2f strength=%.2f lut=%s → %s",
        grade_params["brightness"], grade_params["contrast"],
        grade_params["saturation"], grade_strength, lut_path, graded_path.name,
    )
    cmd = _color_grade_cmd(mixed_path, grade_params, grade_strength, graded_path, lut_path=lut_path)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("color grade failed:\n%s", result.stderr.decode())
        shutil.copy(mixed_path, graded_path)

    final_path = output_dir / output_filename
    log.info("▶ encode → %s", final_path.name)
    cmd = _encode_cmd(
        graded_path, qp, final_path,
        render_plan=render_plan,
        audio_codec=audio_codec,
        audio_bitrate=audio_bitrate,
    )
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("encode failed:\n%s", result.stderr.decode())
        shutil.copy(graded_path, final_path)

    if final_path.exists():
        populate_final_output(instance, final_path)

    return final_path
