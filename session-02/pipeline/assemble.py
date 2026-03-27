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

    Reads v3 syncPoints.timelineInSec/timelineOutSec/fadeInSec/fadeOutSec
    from each assetLibrary.audioAsset.
    """
    audio_assets: list[dict] = (
        instance.get("assetLibrary", {}).get("audioAssets") or []
    )
    asset_by_id: dict[str, dict] = {
        (a.get("logicalId") or a.get("id") or ""): a
        for a in audio_assets
    }

    inputs: list[str] = ["-i", str(video_path)]
    filter_parts: list[str] = []
    mix_inputs: list[str] = []

    valid_tracks = 0
    for idx, (key, audio_path) in enumerate(audio_files.items()):
        if not audio_path or not audio_path.exists():
            log.warning("audio file missing for %s — skipped", key)
            continue

        asset = asset_by_id.get(key) or {}
        sync = asset.get("syncPoints") or {}
        t_in    = float(sync.get("timelineInSec",  0))
        t_out   = float(sync.get("timelineOutSec", 90))
        fade_in = float(sync.get("fadeInSec",  0))
        fade_out = float(sync.get("fadeOutSec", 0))
        duration = max(t_out - t_in, 0.1)

        inputs += ["-i", str(audio_path)]
        stream = idx + 1  # input 0 is video

        chain = f"[{stream}:a]"
        chain += f"atrim=duration={duration},"
        chain += f"adelay={int(t_in * 1000)}|{int(t_in * 1000)},"
        chain += f"apad=whole_dur=300"
        if fade_in > 0:
            chain += f",afade=t=in:st={t_in}:d={fade_in}"
        if fade_out > 0:
            chain += f",afade=t=out:st={t_out - fade_out}:d={fade_out}"
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
    if "warm" in d:
        brightness, contrast = 0.05, 1.05
    if "cool" in d or "cold" in d:
        brightness = -0.03
    if "high contrast" in d:
        contrast = 1.2
    if "lifted blacks" in d or "film look" in d:
        brightness, contrast = 0.04, 0.95
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


def _encode_cmd(input_path: Path, qp: dict, output_path: Path) -> list[str]:
    """Build final encode command from qualityProfile video settings."""
    video = qp.get("video") or {}
    resolution = video.get("resolution") or {}
    width  = resolution.get("width",  1920)
    height = resolution.get("height", 1080)
    fps    = (video.get("frameRate") or {}).get("fps", 24)
    audio_cfg = qp.get("audio") or {}
    sample_rate = audio_cfg.get("sampleRateHz", 44100)

    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", f"scale={width}:{height},fps={fps}",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k",
        "-ar", str(sample_rate),
        str(output_path),
    ]


def _concat_clips_ffmpeg(clip_paths: list[Path], out_path: Path) -> None:
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
    qp = quality_profiles[0] if quality_profiles else {}

    project_name = (
        (instance.get("project") or {}).get("name", "output")
        .lower().replace(" ", "-")[:40]
    )
    output_filename = f"{project_name}.mp4"

    # ── step 1: concatenate shot clips ────────────────────────────────────────
    ordered_clips = _shots_in_scene_order(instance, shot_clips)
    if not ordered_clips:
        raise RuntimeError("No shot clips available to assemble")

    concat_path = inter / "01_concat.mp4"
    log.info("▶ load — concatenating %d clips → %s", len(ordered_clips), concat_path.name)
    _concat_clips_ffmpeg(ordered_clips, concat_path)

    # ── step 2: overlay audio ─────────────────────────────────────────────────
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

    # ── step 4: final encode ──────────────────────────────────────────────────
    final_path = output_dir / output_filename
    log.info("▶ encode → %s", final_path.name)
    cmd = _encode_cmd(graded_path, qp, final_path)
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error("encode failed:\n%s", result.stderr.decode())
        shutil.copy(graded_path, final_path)

    return final_path
