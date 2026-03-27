"""
assemble.py — MoviePy + FFmpeg assembly layer.

Executes the render_pipeline.steps defined in the schema instance:

  load          → concatenate shot clips in scene/shot order
  overlay_audio → composite audio tracks with timeline positioning
  color_grade   → FFmpeg eq filter (brightness / contrast / saturation)
                  with optional LUT (.cube) when the file exists
  encode        → FFmpeg libx265 / libx264 final encode

All intermediate files are written under output_dir/intermediate/.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


# ── internal helpers ──────────────────────────────────────────────────────────

def _shots_in_scene_order(instance: dict, shot_clips: dict[str, Path]) -> list[Path]:
    """
    Return clip paths ordered by scene order (from outputs[0].scene_order)
    then shot order within each scene.
    """
    scene_order_ids: list[str] = (
        instance["outputs"][0].get("scene_order")
        or [s["scene_id"] for s in instance["scenes"]]
    )
    scene_index = {sid: i for i, sid in enumerate(scene_order_ids)}

    ordered: list[Path] = []
    for scene in sorted(instance["scenes"], key=lambda s: scene_index.get(s["scene_id"], 999)):
        for shot in sorted(scene["shots"], key=lambda sh: sh.get("order", 0)):
            sid = shot["shot_id"]
            clip = shot_clips.get(sid)
            if clip and clip.exists():
                ordered.append(clip)
            else:
                log.warning("missing clip for shot %s — skipped", sid)
    return ordered


def _build_audio_mix_cmd(
    video_path: Path,
    audio_files: dict[str, Path],
    instance: dict,
    out_path: Path,
) -> list[str]:
    """
    Build an FFmpeg command that mixes all audio tracks onto the video
    according to each audio_asset's sync.timeline_in_sec / timeline_out_sec.

    Strategy:
      - Each audio is delayed with `adelay`, trimmed with `atrim`, and faded
        in/out via `afade`.
      - All tracks are mixed with `amix=normalize=0` (no level normalisation
        so relative volumes are preserved).
      - The video stream is copied unchanged.
    """
    audio_assets: dict[str, dict] = instance.get("audio_assets", {})

    inputs: list[str] = ["-i", str(video_path)]
    filter_parts: list[str] = []
    mix_inputs: list[str] = []

    valid_tracks = 0
    for idx, (key, asset) in enumerate(audio_assets.items()):
        audio_path = audio_files.get(key)
        if not audio_path or not audio_path.exists():
            log.warning("audio file missing for %s — skipped in mix", key)
            continue

        sync = asset.get("sync", {})
        t_in = float(sync.get("timeline_in_sec", 0))
        t_out = float(sync.get("timeline_out_sec", 90))
        fade_in = float(sync.get("fade_in_sec", 0))
        fade_out = float(sync.get("fade_out_sec", 0))
        duration = t_out - t_in

        inputs += ["-i", str(audio_path)]
        stream = idx + 1  # input 0 is video

        chain = f"[{stream}:a]"
        # trim the audio to the sync window length
        chain += f"atrim=duration={duration},"
        # delay by timeline_in_sec (ms)
        chain += f"adelay={int(t_in * 1000)}|{int(t_in * 1000)},"
        # pad to full video duration so amix doesn't cut short
        chain += f"apad=whole_dur=90"
        if fade_in > 0:
            chain += f",afade=t=in:st={t_in}:d={fade_in}"
        if fade_out > 0:
            chain += f",afade=t=out:st={t_out - fade_out}:d={fade_out}"
        tag = f"[a{idx}]"
        filter_parts.append(chain + tag)
        mix_inputs.append(tag)
        valid_tracks += 1

    if not mix_inputs:
        # no audio — copy video as-is
        return [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-c", "copy",
            str(out_path),
        ]

    mix_filter = "".join(mix_inputs) + f"amix=inputs={valid_tracks}:normalize=0[aout]"
    filter_parts.append(mix_filter)
    filter_complex = ";".join(filter_parts)

    return [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_path),
    ]


def _color_grade_cmd(
    input_path: Path,
    params: dict,
    lut_dir: Path,
    out_path: Path,
) -> list[str]:
    """
    Build FFmpeg color-grade command.

    Uses the `eq` filter for brightness/contrast/saturation.
    Prepends a LUT filter if the .cube file exists in lut_dir.
    """
    brightness = params.get("brightness", 0.0)
    contrast = params.get("contrast", 1.0)
    saturation = params.get("saturation", 1.0)
    lut_file = params.get("lut", "")

    # eq filter: brightness [-1,1], contrast [0,2], saturation [0,3]
    eq_filter = (
        f"eq=brightness={brightness:.3f}"
        f":contrast={contrast:.3f}"
        f":saturation={saturation:.3f}"
    )

    lut_path = lut_dir / lut_file if lut_file else None
    if lut_path and lut_path.exists():
        vf = f"lut3d='{lut_path}'," + eq_filter
        log.info("color grade: LUT %s + eq filter", lut_path.name)
    else:
        if lut_file:
            log.info("LUT '%s' not found — using eq filter only", lut_file)
        vf = eq_filter

    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "copy",
        str(out_path),
    ]


def _encode_cmd(input_path: Path, params: dict, output_path: Path) -> list[str]:
    """
    Build FFmpeg encode command from schema render_pipeline encode step params.
    Falls back to libx264 if libx265 is not available.
    """
    codec = params.get("codec", "libx264")
    crf = params.get("crf", 18)
    preset = params.get("preset", "slow")
    audio_codec = params.get("audio_codec", "aac")
    audio_bitrate = params.get("audio_bitrate", "192k")

    # Check if libx265 is available; fall back to libx264 if not
    probe = subprocess.run(
        ["ffmpeg", "-codecs"],
        capture_output=True, text=True
    )
    if codec == "libx265" and "libx265" not in probe.stdout:
        log.warning("libx265 not available, falling back to libx264")
        codec = "libx264"

    return [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c:v", codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", audio_codec,
        "-b:a", audio_bitrate,
        str(output_path),
    ]


def _concat_clips_ffmpeg(clip_paths: list[Path], out_path: Path) -> None:
    """Concatenate clips using FFmpeg concat demuxer (fast, lossless copy)."""
    list_file = out_path.parent / "_concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths),
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
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
    Execute render_pipeline.steps from the schema instance in dependency order.

    Returns the path to the final encoded output file.
    """
    inter = output_dir / "intermediate"
    inter.mkdir(parents=True, exist_ok=True)

    # Map step_id → result path so downstream steps can resolve inputs
    step_outputs: dict[str, Path] = {}
    final_path: Path | None = None

    steps = instance["render_pipeline"]["steps"]
    # Sort by dependency: steps with no depends_on first, then in listed order
    # (schema already guarantees correct order, but be explicit)
    ordered = []
    remaining = list(steps)
    satisfied: set[str] = set()
    max_iter = len(remaining) * len(remaining) + 1
    i = 0
    while remaining:
        if i > max_iter:
            log.error("Dependency cycle detected in render_pipeline — aborting")
            break
        step = remaining.pop(0)
        deps = step.get("depends_on", [])
        if all(d in satisfied for d in deps):
            ordered.append(step)
            satisfied.add(step["step_id"])
        else:
            remaining.append(step)
        i += 1

    for step in ordered:
        op = step["operation"]
        lib = step["library"]
        params = step.get("parameters", {})
        step_id = step["step_id"]

        log.info("▶ step [%s] op=%s lib=%s", step_id[:12], op, lib)

        # ── load ──────────────────────────────────────────────────────────────
        if op == "load":
            ordered_clips = _shots_in_scene_order(instance, shot_clips)
            if not ordered_clips:
                raise RuntimeError("No shot clips available to load")
            concat_path = inter / "01_concat.mp4"
            log.info("  concatenating %d clips → %s", len(ordered_clips), concat_path.name)
            _concat_clips_ffmpeg(ordered_clips, concat_path)
            step_outputs[step_id] = concat_path

        # ── overlay_audio ─────────────────────────────────────────────────────
        elif op == "overlay_audio":
            # Find the input video (most recent load output)
            input_ids = step.get("input_asset_ids", [])
            input_path = next(
                (step_outputs[i] for i in input_ids if i in step_outputs),
                step_outputs.get(list(step_outputs.keys())[-1]),
            )
            mixed_path = inter / "02_mixed.mp4"
            cmd = _build_audio_mix_cmd(input_path, audio_files, instance, mixed_path)
            log.info("  mixing %d audio tracks → %s", len(instance.get("audio_assets", {})), mixed_path.name)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("audio mix failed:\n%s", result.stderr.decode())
                # Fall back: keep video without audio
                shutil.copy(input_path, mixed_path)
            step_outputs[step_id] = mixed_path

        # ── color_grade ───────────────────────────────────────────────────────
        elif op == "color_grade":
            input_ids = step.get("input_asset_ids", [])
            input_path = next(
                (step_outputs[i] for i in input_ids if i in step_outputs),
                step_outputs.get(list(step_outputs.keys())[-1]),
            )
            graded_path = inter / "03_graded.mp4"
            cmd = _color_grade_cmd(input_path, params, output_dir, graded_path)
            log.info("  color grading → %s", graded_path.name)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("color grade failed:\n%s", result.stderr.decode())
                shutil.copy(input_path, graded_path)
            step_outputs[step_id] = graded_path

        # ── encode ────────────────────────────────────────────────────────────
        elif op == "encode":
            input_ids = step.get("input_asset_ids", [])
            input_path = next(
                (step_outputs[i] for i in input_ids if i in step_outputs),
                step_outputs.get(list(step_outputs.keys())[-1]),
            )
            filename = params.get("output_filename", "output.mp4")
            final_path = output_dir / filename
            cmd = _encode_cmd(input_path, params, final_path)
            log.info("  encoding → %s", final_path.name)
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                log.error("encode failed:\n%s", result.stderr.decode())
                shutil.copy(input_path, final_path)
            step_outputs[step_id] = final_path

        else:
            log.warning("  unknown operation '%s' — skipped", op)

    if final_path is None:
        # No encode step: return the last step output
        final_path = list(step_outputs.values())[-1] if step_outputs else output_dir / "output.mp4"

    return final_path
