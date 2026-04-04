"""Figure JSON I/O — load, validate, save."""

import json
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
