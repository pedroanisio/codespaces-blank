"""Contour and stroke profiling — width-at-y, region classification, landmarks, transplant."""

import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import uniform_filter1d
from scipy.signal import argrelextrema


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


# ═══════════════════════════════════════════════════════════════
#  Landmark detection
# ═══════════════════════════════════════════════════════════════


def find_landmarks(contour: np.ndarray) -> dict[str, int]:
    """Find structural landmarks (head peak, neck valley, etc.) via dx extrema."""
    dx_smooth = uniform_filter1d(contour[:, 0], 25, mode="nearest")

    peaks = argrelextrema(dx_smooth, np.greater, order=20)[0]
    valleys = argrelextrema(dx_smooth, np.less, order=20)[0]

    all_extrema = sorted(
        [(p, "peak", contour[p, 0], contour[p, 1]) for p in peaks]
        + [(v, "valley", contour[v, 0], contour[v, 1]) for v in valleys],
        key=lambda x: x[0],
    )

    landmarks: dict[str, int] = {}

    for idx, typ, dx, dy in all_extrema:
        if typ == "peak" and dy < 1.5 and dx > 0.2:
            landmarks["head_peak"] = idx
            break

    for idx, typ, dx, dy in all_extrema:
        if typ == "valley" and idx > landmarks.get("head_peak", 0) and dy < 2.0 and dx < 0.5:
            landmarks["neck_valley"] = idx
            break

    first_half = [(i, t, d, y) for i, t, d, y in all_extrema if i < 400 and t == "peak"]
    if first_half:
        landmarks["body_peak"] = max(first_half, key=lambda x: x[2])[0]

    mid_valleys = [(i, t, d, y) for i, t, d, y in all_extrema if t == "valley" and 2.5 < y < 5.0]
    if mid_valleys:
        landmarks["inner_valley"] = min(mid_valleys, key=lambda x: x[2])[0]

    return landmarks


# ═══════════════════════════════════════════════════════════════
#  Stroke transplanting
# ═══════════════════════════════════════════════════════════════


def transplant_strokes(
    source_contour: np.ndarray | list,
    source_strokes: list,
    target_contour: np.ndarray,
) -> list[np.ndarray]:
    """Transplant strokes by mapping relative dx position within the silhouette."""
    src_c = np.array(source_contour)
    src_w = width_interpolator(src_c)
    tgt_w = width_interpolator(target_contour)

    transplanted = []
    for stroke in source_strokes:
        s = np.array(stroke)
        new_s = np.zeros_like(s)
        for j in range(len(s)):
            dy, dx = s[j, 1], s[j, 0]
            sw = max(float(src_w(dy)), 0.01)
            tw = max(float(tgt_w(dy)), 0.01)
            new_s[j, 0] = (dx / sw) * tw
            new_s[j, 1] = dy
        transplanted.append(new_s)

    return transplanted


# ═══════════════════════════════════════════════════════════════
#  Full dataset profiling (for analyze.py)
# ═══════════════════════════════════════════════════════════════


def compute_profile(name: str, data: dict) -> dict:
    """Compute a comprehensive profile of a figure dataset."""
    from . import geometry  # lazy to avoid circular

    c = np.array(data["contour"])
    strokes = [np.array(s) for s in data["strokes"]]

    diffs = np.diff(c, axis=0)
    steps = np.sqrt(diffs[:, 0] ** 2 + diffs[:, 1] ** 2)
    gap = np.linalg.norm(c[0] - c[-1])

    lengths = [len(s) for s in strokes]
    pals = sum(1 for s in strokes if len(geometry.dedup_palindrome(s)) < len(s))
    dups = sum(len(s) - len(geometry.remove_consecutive_dups(s)) for s in strokes)
    widths = width_at_y(c)

    h = c[:, 1].max() - c[:, 1].min()
    w = c[:, 0].max()

    return {
        "name": name,
        "n_contour": len(c),
        "n_strokes": len(strokes),
        "total_stroke_pts": sum(lengths),
        "step_mean": steps.mean(),
        "step_cv": steps.std() / steps.mean() * 100,
        "gap": gap,
        "height": h,
        "max_dx": w,
        "ratio": h / (2 * w) if w > 0 else 0,
        "palindromes": pals,
        "dup_pts": dups,
        "widths": widths,
        "median_stroke_len": float(np.median(lengths)) if lengths else 0,
        "max_stroke_len": max(lengths) if lengths else 0,
    }
