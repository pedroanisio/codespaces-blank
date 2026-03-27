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
                _check_180_rule(scene_name, camera_positions, warnings)

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

    return warnings


def _check_180_rule(
    scene_name: str,
    camera_positions: list[tuple[str, dict]],
    warnings: list[str],
) -> None:
    """Check if all cameras are on the same side of the X=0 plane (simplified).

    Real 180-degree validation would use the action line spatial anchors,
    but this provides a basic check using camera X positions.
    """
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


# ── Shot ordering ─────────────────────────────────────────────────────────────

def _shots_in_scene_order(instance: dict, shot_clips: dict[str, Path]) -> list[Path]:
    """Return clip paths ordered by scene number then shot order."""
    production = instance.get("production") or {}
    id_to_logical: dict[str, str] = {}
    for s in production.get("shots") or []:
        lid = s.get("logicalId", "")
        sid = s.get("id", "")
        if lid:
            id_to_logical[lid] = lid
        if sid:
            id_to_logical[sid] = lid

    scenes = sorted(
        production.get("scenes") or [],
        key=lambda s: s.get("sceneNumber", 0),
    )

    ordered: list[Path] = []
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
                seen.add(logical)
            else:
                log.warning("missing clip for shot %s — skipped", ref_id)

    if not ordered:
        for lid, path in shot_clips.items():
            if path.exists():
                ordered.append(path)

    return ordered


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


def _concat_clips_ffmpeg(
    clip_paths: list[Path],
    out_path: Path,
    *,
    scenes: list[dict] | None = None,
) -> None:
    """Concatenate clips with per-scene transitions.

    Supports: cut (default), fade, dissolve, wipe, push, zoom.
    Schema TransitionSpec types: cut, dissolve, fade, wipe, push, zoom, custom.
    """
    if not clip_paths:
        return

    has_transitions = False
    if scenes:
        for s in scenes:
            t_in = (s.get("transitionIn") or {}).get("type", "cut")
            t_out = (s.get("transitionOut") or {}).get("type", "cut")
            if t_in != "cut" or t_out != "cut":
                has_transitions = True
                break

    if not has_transitions or len(clip_paths) <= 1:
        list_file = out_path.parent / "_concat_list.txt"
        list_file.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in clip_paths),
            encoding="utf-8",
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        list_file.unlink(missing_ok=True)
        return

    # Build xfade filter chain
    durations = [_get_clip_duration(p) for p in clip_paths]

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

    inputs = []
    for p in clip_paths:
        inputs += ["-i", str(p)]

    filter_parts = []
    current_offset = 0.0
    prev_label = "[0:v]"

    for i in range(len(clip_paths) - 1):
        t_spec = transition_specs[i] if i < len(transition_specs) else {"type": "cut"}
        t_type = t_spec.get("type", "cut")
        t_dur = float(t_spec.get("durationSec", 0.5))

        if t_type == "cut" or t_type not in xfade_map:
            current_offset += durations[i]
            prev_label = f"[{i + 1}:v]"
            continue

        xfade_name = xfade_map[t_type]
        t_dur = min(t_dur, durations[i] * 0.5, durations[i + 1] * 0.5)
        offset = current_offset + durations[i] - t_dur

        out_label = f"[v{i}]" if i < len(clip_paths) - 2 else "[vout]"
        next_label = f"[{i + 1}:v]"

        filter_parts.append(
            f"{prev_label}{next_label}xfade=transition={xfade_name}:duration={t_dur:.2f}:offset={offset:.2f}{out_label}"
        )
        prev_label = out_label
        current_offset = offset

    if not filter_parts:
        list_file = out_path.parent / "_concat_list.txt"
        list_file.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in clip_paths),
            encoding="utf-8",
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        list_file.unlink(missing_ok=True)
        return

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-an",
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
        chain += f"apad=whole_dur=300"
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

    return [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", audio_codec, "-b:a", audio_bitrate,
        str(out_path),
    ]


# ── Color grade (#1, #2) ─────────────────────────────────────────────────────

def _parse_color_direction(direction: str) -> dict:
    """Heuristically derive eq filter params from a color-direction text."""
    d = direction.lower()
    brightness, contrast, saturation = 0.0, 1.0, 1.0
    if "desaturated" in d or "muted" in d:
        saturation = 0.75
    if "vibrant" in d or "saturated" in d:
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


def _resolve_color_grade_params(instance: dict) -> tuple[dict, float]:
    """Resolve color grade parameters from renderPlan ColorGradeOp, then directorInstructions.

    Returns (eq_params dict, strength 0-1).
    """
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    rp = render_plans[0] if render_plans else {}
    strength = 1.0

    for op in rp.get("operations") or []:
        if op.get("opType") == "colorGrade":
            intent = op.get("intent", "")
            strength = float(op.get("strength", 1.0))
            if intent:
                return _parse_color_direction(intent), strength

    color_direction = _pick(instance, "canonicalDocuments.directorInstructions.colorDirection") or ""
    return _parse_color_direction(color_direction), strength


def _color_grade_cmd(input_path: Path, params: dict, strength: float, out_path: Path) -> list[str]:
    """Build color grade FFmpeg command.

    Fix #1: Uses -c copy when no grading is needed. Uses near-lossless CRF 1
    for the intermediate to minimize quality loss before the final encode.
    """
    brightness = params.get("brightness", 0.0) * strength
    contrast = 1.0 + (params.get("contrast", 1.0) - 1.0) * strength
    saturation = 1.0 + (params.get("saturation", 1.0) - 1.0) * strength

    is_noop = (
        abs(brightness) < 0.001
        and abs(contrast - 1.0) < 0.001
        and abs(saturation - 1.0) < 0.001
    )
    if is_noop:
        return ["ffmpeg", "-y", "-i", str(input_path), "-c", "copy", str(out_path)]

    eq_filter = (
        f"eq=brightness={brightness:.3f}"
        f":contrast={contrast:.3f}"
        f":saturation={saturation:.3f}"
    )
    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", eq_filter,
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

    Pre-flight:
      - Checks editVersion approval (#4)
      - Validates spatial consistency (#10)

    Pipeline reads from v3 instance:
      - Color grade from ColorGradeOp or directorInstructions (#1, #2)
      - Audio timing from timeline/syncPoints/TimeRange (#3)
      - Audio codec from AudioTechnicalSpec (#6)
      - Audio pan from AudioMixTrack.pan (#7)
      - Encode settings from EncodeOp compression (#8)
      - Scene transitions from TransitionSpec (#5)

    Post-render:
      - Populates FinalOutputEntity (#9)

    Returns the path to the final encoded file.
    """
    inter = output_dir / "intermediate"
    inter.mkdir(parents=True, exist_ok=True)

    # ── Pre-flight: approval gate (#4) ────────────────────────────────────────
    check_approval(instance, force=force)

    # ── Pre-flight: spatial consistency (#10) ─────────────────────────────────
    spatial_warnings = validate_spatial_consistency(instance)
    for w in spatial_warnings:
        log.warning("spatial: %s", w)

    # ── Derive pipeline params ────────────────────────────────────────────────
    grade_params, grade_strength = _resolve_color_grade_params(instance)

    quality_profiles = instance.get("qualityProfiles") or []
    qp = (quality_profiles[0] if quality_profiles else {}).get("profile") or {}

    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    render_plan = render_plans[0] if render_plans else {}

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

    # ── Step 1: concat (#5) ───────────────────────────────────────────────────
    ordered_clips = _shots_in_scene_order(instance, shot_clips)
    if not ordered_clips:
        raise RuntimeError("No shot clips available to assemble")

    concat_path = inter / "01_concat.mp4"
    log.info("▶ concat — %d clips → %s", len(ordered_clips), concat_path.name)
    _concat_clips_ffmpeg(ordered_clips, concat_path, scenes=scenes)

    # ── Step 2: audio mix (#3, #6, #7) ────────────────────────────────────────
    mixed_path = inter / "02_mixed.mp4"
    log.info("▶ audio_mix — %d track(s) → %s", len(audio_files), mixed_path.name)
    cmd = _build_audio_mix_cmd(concat_path, audio_files, instance, mixed_path)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("audio mix failed:\n%s", result.stderr.decode())
        shutil.copy(concat_path, mixed_path)

    # ── Step 3: color grade (#1, #2) ──────────────────────────────────────────
    graded_path = inter / "03_graded.mp4"
    log.info(
        "▶ color_grade — b=%.2f c=%.2f s=%.2f strength=%.2f → %s",
        grade_params["brightness"], grade_params["contrast"],
        grade_params["saturation"], grade_strength, graded_path.name,
    )
    cmd = _color_grade_cmd(mixed_path, grade_params, grade_strength, graded_path)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("color grade failed:\n%s", result.stderr.decode())
        shutil.copy(mixed_path, graded_path)

    # ── Step 4: final encode (#8) ─────────────────────────────────────────────
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

    # ── Post-render: populate FinalOutputEntity (#9) ──────────────────────────
    if final_path.exists():
        populate_final_output(instance, final_path)

    return final_path
