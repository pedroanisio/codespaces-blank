"""
assemble.py — FFmpeg assembly layer (v3 schema).

Pipeline steps constructed from the v3 instance:
  load          → concatenate shot clips in scene/shot order
  overlay_audio → composite audio tracks with syncPoints timing
  color_grade   → FFmpeg eq filter derived from directorInstructions.colorDirection
  encode        → FFmpeg libx264 final encode at qualityProfile settings

All intermediate files are written under output_dir/intermediate/.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
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


def _shots_in_scene_order(instance: dict, shot_clips: dict[str, Path]) -> list[Path]:
    """
    Return clip paths ordered by production.scenes[*].sceneNumber
    then shot order within each scene.
    """
    production = instance.get("production", {})
    # Build a mapping from any ID form (id or logicalId) to the shot's logicalId
    # which is the key used by generate.py for shot_clips
    id_to_logical: dict[str, str] = {}
    for s in production.get("shots", []):
        lid = s.get("logicalId", "")
        sid = s.get("id", "")
        if lid:
            id_to_logical[lid] = lid
        if sid:
            id_to_logical[sid] = lid

    scenes = sorted(
        production.get("scenes", []),
        key=lambda s: s.get("sceneNumber", 0),
    )

    ordered: list[Path] = []
    seen: set[str] = set()
    for scene in scenes:
        for ref in scene.get("shotRefs", []):
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

    # Fallback: no scene refs worked — use dict order
    if not ordered:
        for lid, path in shot_clips.items():
            if path.exists():
                ordered.append(path)

    return ordered


def _build_audio_mix_cmd(
    video_path: Path,
    audio_files: dict[str, Path],
    instance: dict,
    out_path: Path,
) -> list[str]:
    """
    Build FFmpeg command to mix all audio tracks onto the video.

    Reads timing from timeline.audioClips (authoritative source) and
    gainDb from renderPlan.operations[opType=audioMix].tracks[].
    Falls back to audioAsset.syncPoints if timeline clips are absent.
    """
    # ── Build timing index from timeline audioClips ───────────────────────
    timelines = (instance.get("assembly") or {}).get("timelines") or []
    tl = timelines[0] if timelines else {}
    tl_audio_clips = tl.get("audioClips") or []

    # Map audio asset ref ID → {timelineStartSec, durationSec}
    clip_timing: dict[str, dict] = {}
    for ac in tl_audio_clips:
        ref_id = (ac.get("sourceRef") or {}).get("id", "")
        clip_timing[ref_id] = {
            "startSec": float(ac.get("timelineStartSec", 0)),
            "durationSec": float(ac.get("durationSec", 30)),
        }

    # ── Build gain index from renderPlan audioMix operation ───────────────
    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    rp = render_plans[0] if render_plans else {}
    gain_by_ref: dict[str, float] = {}
    for op in rp.get("operations", []):
        if op.get("opType") == "audioMix":
            for track in op.get("tracks", []):
                ref_id = (track.get("audioRef") or {}).get("id", "")
                if ref_id:
                    gain_by_ref[ref_id] = float(track.get("gainDb", 0))

    # ── Audio assets lookup ───────────────────────────────────────────────
    audio_assets: list[dict] = (
        instance.get("assetLibrary", {}).get("audioAssets") or []
    )
    asset_by_lid: dict[str, dict] = {}
    for a in audio_assets:
        asset_by_lid[a.get("logicalId", "")] = a
        asset_by_lid[a.get("id", "")] = a

    inputs: list[str] = ["-i", str(video_path)]
    filter_parts: list[str] = []
    mix_inputs: list[str] = []

    valid_tracks = 0
    for idx, (key, audio_path) in enumerate(audio_files.items()):
        if not audio_path or not audio_path.exists():
            log.warning("audio file missing for %s — skipped", key)
            continue

        asset = asset_by_lid.get(key) or {}
        asset_id = asset.get("id", "")

        # Get timing: prefer timeline audioClips, fallback to syncPoints
        timing = clip_timing.get(asset_id) or clip_timing.get(key)
        if timing:
            t_in = timing["startSec"]
            duration = timing["durationSec"]
        else:
            # Legacy: read from syncPoints
            sync = asset.get("syncPoints") or {}
            t_in = float(sync.get("timelineInSec", 0))
            t_out = float(sync.get("timelineOutSec", 30))
            duration = max(t_out - t_in, 0.1)

        # Get gain from renderPlan
        gain_db = gain_by_ref.get(asset_id, gain_by_ref.get(key, 0))

        inputs += ["-i", str(audio_path)]
        stream = idx + 1  # input 0 is video

        # Build per-track filter chain
        chain = f"[{stream}:a]"
        chain += f"atrim=duration={duration},"
        chain += f"adelay={int(t_in * 1000)}|{int(t_in * 1000)},"
        chain += f"apad=whole_dur=300"
        if gain_db != 0:
            chain += f",volume={gain_db}dB"
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
        "-c:a", "aac", "-b:a", "192k",
        str(out_path),
    ]


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


def _color_grade_cmd(input_path: Path, params: dict, out_path: Path) -> list[str]:
    brightness = params.get("brightness", 0.0)
    contrast   = params.get("contrast",   1.0)
    saturation = params.get("saturation", 1.0)
    eq_filter = (
        f"eq=brightness={brightness:.3f}"
        f":contrast={contrast:.3f}"
        f":saturation={saturation:.3f}"
    )
    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", eq_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-movflags", "+faststart",
        "-c:a", "copy",
        str(out_path),
    ]


def _encode_cmd(
    input_path: Path,
    qp: dict,
    output_path: Path,
    *,
    render_plan: dict | None = None,
) -> list[str]:
    """Build final encode command from qualityProfile + renderPlan settings."""
    video = qp.get("video") or {}
    resolution = video.get("resolution") or {}
    width  = resolution.get("widthPx") or resolution.get("width", 1920)
    height = resolution.get("heightPx") or resolution.get("height", 1080)
    fps    = (video.get("frameRate") or {}).get("fps", 24)
    audio_cfg = qp.get("audio") or {}
    sample_rate = audio_cfg.get("sampleRateHz", 44100)

    # Read codec/bitrate from renderPlan encode operation if available
    codec = "libx264"
    bitrate_flag: list[str] = ["-crf", "18"]
    if render_plan:
        for op in render_plan.get("operations", []):
            if op.get("opType") == "encode":
                comp = op.get("compression") or {}
                if comp.get("codec"):
                    codec = comp["codec"]
                if comp.get("bitrateMbps"):
                    bitrate_flag = ["-b:v", f"{comp['bitrateMbps']}M"]
                elif comp.get("crf"):
                    bitrate_flag = ["-crf", str(comp["crf"])]

    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"scale={width}:{height},fps={fps}",
        "-c:v", codec, *bitrate_flag, "-preset", "fast",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k",
        "-ar", str(sample_rate),
        str(output_path),
    ]


def _concat_clips_ffmpeg(
    clip_paths: list[Path],
    out_path: Path,
    *,
    transitions: list[dict] | None = None,
) -> None:
    """Concatenate clips with optional scene transitions (fade/dissolve)."""
    list_file = out_path.parent / "_concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths),
        encoding="utf-8",
    )

    # Build transition filter if transitions are provided
    vf_filters: list[str] = []
    if transitions:
        # Calculate cumulative time offsets for each clip
        offsets: list[float] = [0.0]
        for p in clip_paths[:-1]:
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "csv=p=0", str(p)],
                    capture_output=True, text=True, timeout=5,
                )
                dur = float(probe.stdout.strip() or "5")
            except Exception:
                dur = 5.0
            offsets.append(offsets[-1] + dur)

        total_dur = offsets[-1] + 5.0  # approx last clip

        # Apply fade-in at start if first transition is "fade"
        first_t = transitions[0] if transitions else {}
        if first_t.get("transitionIn", {}).get("type") == "fade":
            vf_filters.append("fade=t=in:st=0:d=1")

        # Apply fade-out at end if last transition is "fade"
        last_t = transitions[-1] if transitions else {}
        if last_t.get("transitionOut", {}).get("type") == "fade":
            vf_filters.append(f"fade=t=out:st={total_dur - 1.5}:d=1.5")

    if vf_filters:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-vf", ",".join(vf_filters),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            str(out_path),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(out_path),
        ]
    subprocess.run(cmd, check=True, capture_output=True)
    list_file.unlink(missing_ok=True)


# ── public API ────────────────────────────────────────────────────────────────

def assemble(
    instance: dict,
    output_dir: Path,
    shot_clips: dict[str, Path],
    audio_files: dict[str, Path],
) -> Path:
    """
    Assemble a final video from shot clips and audio tracks.

    Pipeline is constructed from the v3 instance:
      - Color grade params  ← canonicalDocuments.directorInstructions.colorDirection
      - Encode settings     ← qualityProfiles[0]
      - Output filename     ← project.name (kebab-cased)

    Returns the path to the final encoded file.
    """
    inter = output_dir / "intermediate"
    inter.mkdir(parents=True, exist_ok=True)

    # ── derive pipeline params from v3 instance ───────────────────────────────

    color_direction = _pick(instance, "canonicalDocuments.directorInstructions.colorDirection") or ""
    grade_params = _parse_color_direction(color_direction)

    quality_profiles = instance.get("qualityProfiles") or []
    qp = (quality_profiles[0] if quality_profiles else {}).get("profile") or {}

    render_plans = (instance.get("assembly") or {}).get("renderPlans") or []
    render_plan = render_plans[0] if render_plans else {}

    project_name = (
        (instance.get("project") or {}).get("name", "output")
        .lower().replace(" ", "-")[:40]
    )
    output_filename = f"{project_name}.mp4"

    # ── Extract scene transitions ─────────────────────────────────────────────
    scenes = sorted(
        (instance.get("production") or {}).get("scenes", []),
        key=lambda s: s.get("sceneNumber", 0),
    )
    scene_transitions = [
        {
            "transitionIn": s.get("transitionIn") or {},
            "transitionOut": s.get("transitionOut") or {},
        }
        for s in scenes
    ]

    # ── step 1: concatenate shot clips with transitions ───────────────────────
    ordered_clips = _shots_in_scene_order(instance, shot_clips)
    if not ordered_clips:
        raise RuntimeError("No shot clips available to assemble")

    concat_path = inter / "01_concat.mp4"
    log.info("▶ load — concatenating %d clips → %s", len(ordered_clips), concat_path.name)
    _concat_clips_ffmpeg(ordered_clips, concat_path, transitions=scene_transitions)

    # ── step 2: overlay audio with timing + gain from protocol ────────────────
    mixed_path = inter / "02_mixed.mp4"
    log.info("▶ overlay_audio — mixing %d track(s) → %s", len(audio_files), mixed_path.name)
    cmd = _build_audio_mix_cmd(concat_path, audio_files, instance, mixed_path)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("audio mix failed:\n%s", result.stderr.decode())
        shutil.copy(concat_path, mixed_path)

    # ── step 3: color grade ───────────────────────────────────────────────────
    graded_path = inter / "03_graded.mp4"
    log.info(
        "▶ color_grade — brightness=%.2f contrast=%.2f saturation=%.2f → %s",
        grade_params["brightness"], grade_params["contrast"], grade_params["saturation"],
        graded_path.name,
    )
    cmd = _color_grade_cmd(mixed_path, grade_params, graded_path)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("color grade failed:\n%s", result.stderr.decode())
        shutil.copy(mixed_path, graded_path)

    # ── step 4: final encode (reads codec/bitrate from renderPlan) ────────────
    final_path = output_dir / output_filename
    log.info("▶ encode → %s", final_path.name)
    cmd = _encode_cmd(graded_path, qp, final_path, render_plan=render_plan)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("encode failed:\n%s", result.stderr.decode())
        shutil.copy(graded_path, final_path)

    return final_path
