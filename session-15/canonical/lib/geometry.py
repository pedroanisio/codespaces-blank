"""Contour geometry — resample, smooth, clamp, close gaps, palindrome dedup.

All functions are pure: np.ndarray in, np.ndarray out, no I/O.
"""

import numpy as np
from scipy.ndimage import uniform_filter1d


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
