"""Contour and stroke profiling — width-at-y, region classification, comparison."""

import numpy as np
from scipy.interpolate import interp1d


# Standard body regions: (name, y_lo, y_hi) in head-units
BODY_REGIONS = [
    ("head", 0, 1),
    ("neck_shoulder", 1, 2),
    ("torso", 2, 3),
    ("hip", 3, 4),
    ("upper_leg", 4, 5),
    ("lower_leg", 5, 6),
    ("ankle_foot", 6, 8),
]


def width_at_y(
    contour: np.ndarray,
    y_levels: np.ndarray | None = None,
    *,
    tolerance: float = 0.15,
) -> dict[float, float]:
    """Max dx at each y level. Returns {y: max_dx}."""
    if y_levels is None:
        y_levels = np.arange(0, 9)

    widths = {}
    for y in y_levels:
        mask = np.abs(contour[:, 1] - y) < tolerance
        if mask.any():
            widths[float(y)] = float(contour[mask, 0].max())
    return widths


def width_interpolator(
    contour: np.ndarray,
    y_step: float = 0.05,
    y_range: tuple[float, float] = (0, 8.5),
) -> interp1d:
    """Build a continuous width-at-y interpolator from a contour."""
    y_grid = np.arange(y_range[0], y_range[1], y_step)
    widths = np.zeros(len(y_grid))

    for i, y in enumerate(y_grid):
        mask = np.abs(contour[:, 1] - y) < 0.1
        if mask.any():
            widths[i] = contour[mask, 0].max()
        else:
            dists = np.abs(contour[:, 1] - y)
            widths[i] = contour[np.argmin(dists), 0]

    return interp1d(y_grid, widths, bounds_error=False, fill_value="extrapolate")


def classify_by_region(
    strokes: list[np.ndarray],
    regions: list[tuple[str, float, float]] | None = None,
) -> dict[str, list[np.ndarray]]:
    """Group strokes into body regions by centroid y."""
    if regions is None:
        regions = BODY_REGIONS

    result = {name: [] for name, _, _ in regions}

    for s in strokes:
        cy = np.mean(s[:, 1])
        for name, y_lo, y_hi in regions:
            if y_lo <= cy < y_hi:
                result[name].append(s)
                break

    return result
