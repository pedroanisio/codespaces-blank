"""Image → silhouette extraction: bounding box, midline, scan-line, guide removal.

Requires OpenCV (cv2) and numpy.
"""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class BoundingBox:
    """Figure bounding box in pixel coordinates."""
    x_left: int
    x_right: int
    y_top: int
    y_bot: int
    midline_px: float
    fig_height_px: int
    scale: float  # px → head-units (8.0 / fig_height_px)


def load_gray(image_path: str) -> np.ndarray:
    """Read image and convert to grayscale. Raises on failure."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def threshold_lines(
    gray: np.ndarray,
    *,
    adaptive: bool = True,
    global_val: int = 210,
) -> np.ndarray:
    """Produce a binary mask of ink lines.

    If *adaptive* is True, combines adaptive + global thresholds (v3 behaviour).
    If False, uses only global threshold (v4 behaviour).
    """
    _, line_global = cv2.threshold(gray, global_val, 255, cv2.THRESH_BINARY_INV)

    if not adaptive:
        return line_global

    line_bin = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 8,
    )
    return cv2.bitwise_or(line_bin, line_global)


def remove_guides(binary: np.ndarray) -> np.ndarray:
    """Remove horizontal and vertical guide lines via morphological opening."""
    h, w = binary.shape

    horiz_k = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 4, 1))
    vert_k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 4))

    h_guides = cv2.dilate(
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_k),
        np.ones((7, 1), np.uint8), iterations=2,
    )
    v_guides = cv2.dilate(
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_k),
        np.ones((1, 7), np.uint8), iterations=2,
    )

    clean = binary.copy()
    clean[h_guides > 0] = 0
    clean[v_guides > 0] = 0
    return clean


def find_bounds(
    binary: np.ndarray,
    thresh_ratio: float = 0.01,
) -> BoundingBox:
    """Find figure bounding box and midline from a binary ink mask."""
    col_sums = binary.sum(axis=0)
    row_sums = binary.sum(axis=1)

    fig_cols = np.where(col_sums > col_sums.max() * thresh_ratio)[0]
    fig_rows = np.where(row_sums > row_sums.max() * thresh_ratio)[0]

    x_left, x_right = int(fig_cols[0]), int(fig_cols[-1])
    y_top, y_bot = int(fig_rows[0]), int(fig_rows[-1])
    midline_px = (x_left + x_right) / 2.0
    fig_height_px = y_bot - y_top
    scale = 8.0 / fig_height_px

    return BoundingBox(
        x_left=x_left, x_right=x_right,
        y_top=y_top, y_bot=y_bot,
        midline_px=midline_px,
        fig_height_px=fig_height_px,
        scale=scale,
    )


def scanline_silhouette(
    binary: np.ndarray,
    bounds: BoundingBox,
    *,
    dilate_k: int = 3,
    gap_thresh: float = 0.05,
    max_dx_factor: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Scan-line right-half silhouette extraction.

    Returns (right_outer, right_inner) as Nx2 arrays in head-unit coords.
    *max_dx_factor*: if set, clamp outer dx to bounding-box width * factor.
    """
    thick = cv2.dilate(
        binary,
        np.ones((dilate_k, dilate_k), np.uint8),
        iterations=1,
    )

    max_plausible_dx = None
    if max_dx_factor is not None:
        max_plausible_dx = (bounds.x_right - bounds.midline_px) * bounds.scale * max_dx_factor

    right_outer, right_inner = [], []

    for row in range(bounds.y_top, bounds.y_bot + 1):
        ink = np.where(thick[row, :] > 0)[0]
        if len(ink) == 0:
            continue

        dy = (row - bounds.y_top) * bounds.scale
        right_px = ink[ink >= bounds.midline_px]
        if len(right_px) == 0:
            continue

        outer_dx = (right_px[-1] - bounds.midline_px) * bounds.scale
        inner_dx = (right_px[0] - bounds.midline_px) * bounds.scale

        if max_plausible_dx is not None:
            outer_dx = min(outer_dx, max_plausible_dx)

        right_outer.append([outer_dx, dy])
        if outer_dx - inner_dx > gap_thresh:
            right_inner.append([inner_dx, dy])

    return np.array(right_outer), np.array(right_inner)


def build_contour(
    right_outer: np.ndarray,
    right_inner: np.ndarray,
) -> np.ndarray:
    """Combine outer (going down) and inner (reversed, going up) into one contour."""
    raw = np.vstack([right_outer, right_inner[::-1]])
    raw[:, 0] = np.maximum(raw[:, 0], 0)
    return raw
