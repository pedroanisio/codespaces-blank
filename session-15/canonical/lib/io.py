"""Figure JSON I/O — load, validate, save, text conversion."""

import json
import re
from pathlib import Path
from typing import Any


REQUIRED_KEYS = {"contour", "strokes", "meta"}


def load_figure(path: str | Path) -> dict[str, Any]:
    """Load a figure JSON and validate required keys."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Figure JSON not found: {path}")

    with open(path) as f:
        data = json.load(f)

    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"{path.name}: missing required keys {missing}")

    return data


def save_figure(data: dict[str, Any], path: str | Path) -> None:
    """Save figure JSON, creating parent dirs if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(data, f)

    print(f"Saved → {path}")


def build_meta(
    *,
    contour_points: int,
    detail_strokes: int,
    source: str,
    **extra,
) -> dict[str, Any]:
    """Build a standardised meta block."""
    meta = {
        "contour_points": contour_points,
        "detail_strokes": detail_strokes,
        "source": source,
    }
    meta.update(extra)
    return meta


def convert_text(txt_path: str | Path, json_path: str | Path | None = None) -> dict:
    """Convert a full-data text dump to figure JSON.

    Handles both section-header formats:
      - "STROKES — ALL N DETAIL CURVES" (moto_rider style)
      - "── STROKES ──" (hero/biker style)
    """
    txt_path = Path(txt_path)
    if json_path is None:
        json_path = txt_path.with_suffix(".json")

    lines = txt_path.read_text().splitlines()
    contour: list[list[float]] = []
    strokes: list[list[list[float]]] = []
    in_contour = in_strokes = False

    for line in lines:
        line = line.rstrip()

        if re.match(r"── CONTOUR", line) or ("idx" in line and "dx" in line and "dy" in line):
            in_contour = True
            continue

        if re.match(r"── MEASURE", line) or (line.startswith("====") and in_contour and len(contour) > 10):
            in_contour = False
            continue

        if re.match(r"── STROKES", line) or ("STROKES" in line and "DETAIL" in line):
            in_contour = False
            in_strokes = True
            continue

        if in_contour:
            m = re.match(r"\s*(\d+)\s+([+-]?\d+\.\d+)\s+(\d+\.\d+)", line)
            if m:
                contour.append([float(m.group(2)), float(m.group(3))])

        if in_strokes:
            sm = re.match(r"\s*stroke\[\s*\d+\]\s*\(\s*\d+\s*pts\):\s*(.*)", line)
            if sm:
                points = re.findall(r"\(([^)]+)\)", sm.group(1))
                strokes.append([[float(x) for x in p.split(",")] for p in points])

    data = {
        "contour": contour,
        "strokes": strokes,
        "meta": build_meta(
            contour_points=len(contour),
            detail_strokes=len(strokes),
            source=txt_path.name,
        ),
    }

    save_figure(data, json_path)
    print(f"  Contour: {len(contour)} pts, Strokes: {len(strokes)}")
    return data
