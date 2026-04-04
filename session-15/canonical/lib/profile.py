"""Contour and stroke profiling — width-at-y, region classification, landmarks, transplant."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import uniform_filter1d
from scipy.signal import argrelextrema

from .model import Landmark


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


def _outer_portion(contour: np.ndarray) -> tuple[np.ndarray, int]:
    """Return the outer silhouette (top→bottom) and its end index in the full contour."""
    split = int(np.argmax(contour[:, 1]))
    return contour[: split + 1], split


def _find_extremum_in_band(
    dx_smooth: np.ndarray,
    dy: np.ndarray,
    dy_lo: float,
    dy_hi: float,
    kind: str,
    order: int = 8,
) -> int | None:
    """Find the most prominent local peak or valley within a dy band.

    Prefers actual local extrema (via argrelextrema) when available, falls back
    to global argmax/argmin within the band if no local extremum exists.

    Returns the index into the input arrays, or None if nothing found.
    """
    band_mask = (dy >= dy_lo) & (dy <= dy_hi)
    if not band_mask.any():
        return None

    band_indices = np.where(band_mask)[0]
    band_dx = dx_smooth[band_indices]

    # Try to find local extrema within the band
    comparator = np.greater if kind == "peak" else np.less
    local = argrelextrema(band_dx, comparator, order=min(order, max(1, len(band_dx) // 4)))[0]

    if len(local) > 0:
        # Pick the most prominent local extremum
        if kind == "peak":
            best = local[np.argmax(band_dx[local])]
        else:
            best = local[np.argmin(band_dx[local])]
        return int(band_indices[best])

    # Fallback: global extremum in band
    if kind == "peak":
        return int(band_indices[np.argmax(band_dx)])
    return int(band_indices[np.argmin(band_dx)])


def find_anatomical_landmarks(contour: np.ndarray) -> list[Landmark]:
    """Detect anatomical landmarks on the contour using 8HU dy-band constraints.

    Works on the outer silhouette portion (top→bottom). Returns Landmark
    objects with indices into the *full* contour.

    Detected landmarks (when present):
        head_peak      — widest point of cranium (dy 0.0–1.2)
        neck_valley    — narrowest neck point (dy 0.8–2.0)
        shoulder_peak  — shoulder width (dy 1.2–2.5)
        waist_valley   — narrowest torso point (dy 2.5–4.0)
        hip_peak       — widest hip point (dy 3.0–4.5)
        knee_valley    — narrowest point around knee (dy 5.0–6.5)
        ankle_valley   — narrowest point near ankle (dy 7.0–8.0)
    """
    outer, _ = _outer_portion(contour)
    n = len(outer)

    # Adaptive smoothing: kernel relative to outer length
    kernel = max(15, n // 40)
    if kernel % 2 == 0:
        kernel += 1
    dx_smooth = uniform_filter1d(outer[:, 0], kernel, mode="nearest")
    dy = outer[:, 1]

    # Detection bands: (name, dy_lo, dy_hi, kind)
    # Ordered top-to-bottom so earlier landmarks can constrain later ones.
    # Bands reflect the classical 8-head-unit proportional system:
    #   0.0 crown → 1.0 chin → 2.0 nipples → 3.0 navel → 4.0 crotch
    #   → 5.0 mid-thigh → 6.0 below-knee → 7.0 mid-calf → 8.0 sole
    BANDS = [
        ("head_peak",     0.0, 1.0, "peak"),
        ("neck_valley",   0.7, 1.5, "valley"),
        ("shoulder_peak", 1.2, 2.3, "peak"),
        ("waist_valley",  2.5, 3.5, "valley"),
        ("hip_peak",      3.2, 4.5, "peak"),
        ("knee_valley",   5.2, 6.5, "valley"),
        ("ankle_valley",  7.0, 8.0, "valley"),
    ]

    landmarks: list[Landmark] = []
    prev_dy = -1.0

    for name, dy_lo, dy_hi, kind in BANDS:
        # Constrain: each landmark must be below the previous one
        effective_lo = max(dy_lo, prev_dy + 0.1)
        if effective_lo >= dy_hi:
            continue

        idx = _find_extremum_in_band(dx_smooth, dy, effective_lo, dy_hi, kind)
        if idx is None:
            continue

        lm = Landmark(
            name=name,
            index=int(idx),
            dx=float(outer[idx, 0]),
            dy=float(outer[idx, 1]),
        )
        landmarks.append(lm)
        prev_dy = lm.dy

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
