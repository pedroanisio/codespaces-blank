"""Contour geometry — resample, smooth, clamp, close gaps, palindrome dedup, B-spline fit.

All functions are pure: np.ndarray in, np.ndarray out, no I/O.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import splev, splprep
from scipy.ndimage import uniform_filter1d
from scipy.signal import savgol_filter


def arc_lengths(contour: np.ndarray) -> tuple[np.ndarray, float]:
    """Cumulative arc-length along a contour.

    Returns (cumulative_lengths, total_length).
    cumulative_lengths[0] == 0, cumulative_lengths[-1] == total_length.
    """
    diffs = np.diff(contour, axis=0)
    seg_len = np.sqrt(diffs[:, 0] ** 2 + diffs[:, 1] ** 2)
    cum = np.concatenate([[0], np.cumsum(seg_len)])
    return cum, cum[-1]


def resample(contour: np.ndarray, n: int = 700) -> np.ndarray:
    """Resample contour to *n* points at uniform arc-length spacing."""
    cum, total = arc_lengths(contour)
    t_uniform = np.linspace(0, total, n)
    return np.column_stack([
        np.interp(t_uniform, cum, contour[:, 0]),
        np.interp(t_uniform, cum, contour[:, 1]),
    ])


def smooth(
    contour: np.ndarray,
    kernel: int = 5,
    mode: str = "nearest",
) -> np.ndarray:
    """Uniform-filter smoothing on both axes, then clamp dx >= 0."""
    out = np.column_stack([
        uniform_filter1d(contour[:, 0], kernel, mode=mode),
        uniform_filter1d(contour[:, 1], kernel, mode=mode),
    ])
    out[:, 0] = np.maximum(out[:, 0], 0)
    return out


def clamp_dx(contour: np.ndarray, minimum: float = 0.0) -> np.ndarray:
    """Clamp dx values to a minimum (default 0)."""
    out = contour.copy()
    out[:, 0] = np.maximum(out[:, 0], minimum)
    return out


def close_gap(contour: np.ndarray, step: float = 0.03) -> np.ndarray:
    """Bridge-interpolate between last and first point to close a contour loop."""
    gap = np.linalg.norm(contour[0] - contour[-1])
    if gap < 1e-6:
        return contour

    n_bridge = max(2, int(gap / step))
    bridge = np.array([
        contour[-1] * (1 - t) + contour[0] * t
        for t in np.linspace(0, 1, n_bridge + 1)[1:-1]
    ])
    return np.vstack([contour, bridge, contour[0:1]])


def dedup_palindrome(stroke: np.ndarray, tol: float = 0.025) -> np.ndarray:
    """If a stroke traces out-and-back (palindrome), keep outward path only."""
    n = len(stroke)
    if n < 6:
        return stroke

    mid = n // 2
    first_half = stroke[:mid]
    second_half = stroke[n - mid:][::-1]

    if len(first_half) != len(second_half):
        return stroke

    if np.abs(first_half - second_half).max() < tol:
        if n % 2 == 1:
            return np.vstack([stroke[:mid], stroke[mid : mid + 1]])
        return stroke[:mid]

    return stroke


def remove_consecutive_dups(stroke: np.ndarray, atol: float = 1e-5) -> np.ndarray:
    """Remove consecutive duplicate points from a stroke."""
    if len(stroke) < 2:
        return stroke
    mask = np.ones(len(stroke), dtype=bool)
    for j in range(1, len(stroke)):
        if np.allclose(stroke[j], stroke[j - 1], atol=atol):
            mask[j] = False
    return stroke[mask]


def subsample(points: np.ndarray, max_pts: int = 60) -> np.ndarray:
    """Evenly subsample to at most *max_pts* points."""
    if len(points) <= max_pts:
        return points
    idx = np.linspace(0, len(points) - 1, max_pts, dtype=int)
    return points[idx]


def smooth_stroke(
    stroke: np.ndarray,
    kernel: int = 3,
    mode: str = "nearest",
) -> np.ndarray:
    """Uniform-filter smoothing for a single stroke (no clamping)."""
    return np.column_stack([
        uniform_filter1d(stroke[:, 0], kernel, mode=mode),
        uniform_filter1d(stroke[:, 1], kernel, mode=mode),
    ])


def savgol_smooth(
    contour: np.ndarray,
    window: int = 35,
    poly: int = 3,
    mode: str = "wrap",
) -> np.ndarray:
    """Savitzky-Golay smoothing on both axes.

    *window* is clamped to an odd value <= len(contour).
    """
    n = len(contour)
    w = min(window, n - (1 if n % 2 == 0 else 0))
    if w < 5:
        return contour.copy()
    out = contour.copy()
    out[:, 0] = savgol_filter(out[:, 0], w, poly, mode=mode)
    out[:, 1] = savgol_filter(out[:, 1], w, poly, mode=mode)
    return out


def resample_normalized(contour: np.ndarray, n: int = 800) -> np.ndarray:
    """Resample to *n* points at normalized arc-length [0, 1]."""
    cum, total = arc_lengths(contour)
    t_norm = cum / total
    t_uniform = np.linspace(0, 1, n)
    return np.column_stack([
        np.interp(t_uniform, t_norm, contour[:, 0]),
        np.interp(t_uniform, t_norm, contour[:, 1]),
    ])


def weighted_average(
    contours: dict[str, np.ndarray],
    weights: dict[str, float],
) -> np.ndarray:
    """Weighted average of same-length contours, then smooth + clamp."""
    result = sum(weights[name] * contours[name] for name in weights)
    return smooth(result)


# ═══════════════════════════════════════════════════════════════
#  Parametric B-spline fitting
# ═══════════════════════════════════════════════════════════════


def _fit_segment(
    points: np.ndarray,
    smoothing: float | None = None,
    degree: int = 3,
) -> tuple[list[float], list[float], list[float], int] | None:
    """Fit a single parametric cubic B-spline to an Nx2 point array.

    Returns (knots, coeffs_dx, coeffs_dy, degree), or None if the segment
    is too short to fit.
    *smoothing*: scipy splprep `s` parameter. None = auto.
    """
    n = len(points)
    k = min(degree, n - 1)
    if n < 4 or k < 1:
        return None

    s = smoothing if smoothing is not None else float(n) * 0.1

    try:
        tck, _ = splprep([points[:, 0], points[:, 1]], s=s, k=k)
    except (ValueError, TypeError):
        return None

    return tck[0].tolist(), tck[1][0].tolist(), tck[1][1].tolist(), k


def _evaluate_segment(
    knots: list[float],
    coeffs_dx: list[float],
    coeffs_dy: list[float],
    degree: int,
    n_points: int = 100,
) -> np.ndarray:
    """Evaluate a B-spline segment to n_points."""
    tck = (np.array(knots), [np.array(coeffs_dx), np.array(coeffs_dy)], degree)
    u = np.linspace(0, 1, n_points)
    try:
        dx, dy = splev(u, tck)
    except Exception:
        return np.empty((0, 2))
    return np.column_stack([dx, dy])


def fit_bspline_segments(
    contour: np.ndarray,
    landmarks: list,
    *,
    smoothing_factor: float = 0.1,
    degree: int = 3,
) -> tuple[list[dict], float, float]:
    """Fit piecewise cubic B-splines to contour segments between landmarks.

    Parameters
    ----------
    contour : Nx2 array in head-unit coords.
    landmarks : list of Landmark objects (must have .index, .name attributes),
        sorted by index. Only landmarks whose index falls within the outer
        contour portion (top→bottom) are used.
    smoothing_factor : multiplied by segment length to get the splprep `s` param.
    degree : B-spline degree (default 3 = cubic).

    Returns
    -------
    (segments, max_error, mean_error) where segments is a list of dicts
    with keys: label, landmark_start, landmark_end, knots, coeffs_dx,
    coeffs_dy, degree.
    """
    from .model import SplineSegment

    if len(landmarks) < 2:
        return [], 0.0, 0.0

    # Sort landmarks by contour index (path order, not anatomical dy order)
    sorted_lms = sorted(landmarks, key=lambda lm: lm.index)
    indices = [lm.index for lm in sorted_lms]
    names = [lm.name for lm in sorted_lms]

    segments: list[SplineSegment] = []

    for i in range(len(indices) - 1):
        start_idx = indices[i]
        end_idx = indices[i + 1]
        if end_idx <= start_idx:
            continue

        seg_points = contour[start_idx : end_idx + 1]
        if len(seg_points) < 2:
            continue

        s = float(len(seg_points)) * smoothing_factor
        result = _fit_segment(seg_points, smoothing=s, degree=degree)
        if result is None:
            continue
        knots, c_dx, c_dy, k = result

        label = f"{names[i]}_to_{names[i + 1]}"
        segments.append(SplineSegment(
            label=label,
            landmark_start=names[i],
            landmark_end=names[i + 1],
            knots=knots,
            coeffs_dx=c_dx,
            coeffs_dy=c_dy,
            degree=k,
        ))

    # Compute reconstruction error
    all_errors: list[float] = []
    for seg in segments:
        si = indices[names.index(seg.landmark_start)]
        ei = indices[names.index(seg.landmark_end)]
        original = contour[si : ei + 1]

        reconstructed = _evaluate_segment(
            seg.knots, seg.coeffs_dx, seg.coeffs_dy, seg.degree,
            n_points=len(original),
        )

        if len(reconstructed) == len(original):
            errors = np.sqrt(np.sum((original - reconstructed) ** 2, axis=1))
            all_errors.extend(errors.tolist())

    max_err = float(max(all_errors)) if all_errors else 0.0
    mean_err = float(np.mean(all_errors)) if all_errors else 0.0

    return segments, max_err, mean_err


def reconstruct_from_segments(
    segments: list,
    points_per_segment: int = 100,
) -> np.ndarray:
    """Reconstruct a contour from a list of SplineSegment objects.

    Adjacent segments share their boundary point (the landmark), so the
    last point of segment N is dropped to avoid duplication.
    """
    parts = []
    for i, seg in enumerate(segments):
        pts = _evaluate_segment(
            seg.knots, seg.coeffs_dx, seg.coeffs_dy, seg.degree,
            n_points=points_per_segment,
        )
        # Drop last point except for the final segment (shared with next segment's start)
        if i < len(segments) - 1:
            pts = pts[:-1]
        parts.append(pts)

    if not parts:
        return np.empty((0, 2))

    return np.vstack(parts)
