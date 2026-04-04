"""Stroke extraction — contour-based, skeleton-based, and path ordering.

Requires OpenCV (cv2), numpy, and scikit-image (skeletonize).
"""

import cv2
import numpy as np
from skimage.morphology import skeletonize

from .extract import BoundingBox
from .geometry import subsample


def _to_headunits(
    px_points: np.ndarray,
    bounds: BoundingBox,
) -> np.ndarray:
    """Convert pixel coords to right-half head-unit coords (dx, dy)."""
    dx = np.maximum((px_points[:, 0] - bounds.midline_px) * bounds.scale, 0)
    dy = (px_points[:, 1] - bounds.y_top) * bounds.scale
    return np.column_stack([dx, dy])


def from_contours(
    gray: np.ndarray,
    bounds: BoundingBox,
    *,
    thresh: int = 200,
    area_max: int = 50000,
    min_pts: int = 5,
    max_pts: int = 60,
    dx_limit: float | None = None,
) -> list[np.ndarray]:
    """Extract detail strokes from cv2 contours (right-half, head-unit coords).

    *dx_limit*: if set, reject strokes whose max dx exceeds this value.
    """
    _, clean = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
    all_contours, _ = cv2.findContours(clean, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    strokes = []
    for cnt in all_contours:
        pts = cnt.squeeze()
        if pts.ndim < 2 or len(pts) < min_pts:
            continue

        # Right-half only
        right_mask = pts[:, 0] >= (bounds.midline_px - 3)
        if right_mask.sum() < min_pts:
            continue

        # Skip outer silhouette
        if cv2.contourArea(cnt) > area_max:
            continue

        hu = _to_headunits(pts[right_mask].astype(float), bounds)

        # Skip out-of-bounds
        if hu[:, 1].min() > 8.2 or hu[:, 1].max() < -0.2:
            continue

        if dx_limit is not None and hu[:, 0].max() > dx_limit:
            continue

        strokes.append(subsample(hu, max_pts))

    return strokes


def order_path(
    points: list[tuple[float, float]],
    max_gap: float = 0.1,
    max_steps: int = 200,
) -> list[tuple[float, float]]:
    """Greedy nearest-neighbor path ordering, starting from topmost point."""
    if len(points) < 2:
        return points

    start = min(range(len(points)), key=lambda i: points[i][1])
    ordered = [points[start]]
    remaining = set(range(len(points))) - {start}
    gap_sq = max_gap ** 2

    for _ in range(min(len(points) - 1, max_steps)):
        if not remaining:
            break
        last = ordered[-1]
        best_d, best_i = float("inf"), None
        for i in remaining:
            d = (points[i][0] - last[0]) ** 2 + (points[i][1] - last[1]) ** 2
            if d < best_d:
                best_d, best_i = d, i
        if best_i is None or best_d > gap_sq:
            break
        ordered.append(points[best_i])
        remaining.discard(best_i)

    return ordered


def from_skeleton(
    binary: np.ndarray,
    bounds: BoundingBox,
    all_contours: list | None = None,
    *,
    min_pts: int = 8,
    min_ordered: int = 5,
    max_pts: int = 60,
    dx_limit: float | None = None,
) -> list[np.ndarray]:
    """Extract strokes from skeletonized inner lines with path ordering.

    *all_contours*: pre-computed contours (to find the outer mask).
    If None, contours are found from the binary image.
    """
    if all_contours is None:
        all_contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Skeletonize
    skel = skeletonize(binary > 0).astype(np.uint8) * 255

    # Mask out the outer silhouette
    outer_mask = np.zeros_like(binary)
    largest = max(all_contours, key=cv2.contourArea)
    cv2.drawContours(outer_mask, [largest], 0, 255, 5)
    inner_skel = skel.copy()
    inner_skel[outer_mask > 0] = 0

    # Connected components → individual strokes
    n_labels, labels = cv2.connectedComponents(inner_skel)

    strokes = []
    for lid in range(1, n_labels):
        ys, xs = np.where(labels == lid)

        # Right-half only
        right = xs >= (bounds.midline_px - 3)
        if right.sum() < min_pts:
            continue

        hu_dx = np.maximum((xs[right].astype(float) - bounds.midline_px) * bounds.scale, 0)
        hu_dy = (ys[right].astype(float) - bounds.y_top) * bounds.scale

        if hu_dy.min() > 8.2:
            continue
        if dx_limit is not None and hu_dx.max() > dx_limit:
            continue

        # Path-order the points
        pts = list(zip(hu_dx, hu_dy))
        ordered = order_path(pts)

        if len(ordered) < min_ordered:
            continue

        stroke = np.array(ordered)
        strokes.append(subsample(stroke, max_pts))

    return strokes


def extract_all(
    gray: np.ndarray,
    binary_for_strokes: np.ndarray,
    bounds: BoundingBox,
    *,
    contour_max_dx: float | None = None,
) -> list[np.ndarray]:
    """Full stroke extraction: contour-based + skeleton-based, merged.

    *contour_max_dx*: if set, reject strokes exceeding this dx (e.g. 1.15 * silhouette max).
    """
    contour_strokes = from_contours(gray, bounds, dx_limit=contour_max_dx)

    _, clean = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    all_contours, _ = cv2.findContours(clean, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    skeleton_strokes = from_skeleton(
        binary_for_strokes, bounds,
        all_contours=all_contours,
        dx_limit=contour_max_dx,
    )

    return contour_strokes + skeleton_strokes
