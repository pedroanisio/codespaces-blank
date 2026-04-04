"""Image → silhouette extraction: bounding box, midline, scan-line, flood-fill, guide removal.

Requires OpenCV (cv2) and numpy.
"""

from dataclasses import dataclass

import cv2
import numpy as np
from scipy.signal import savgol_filter
from skimage.morphology import skeletonize


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


# ═══════════════════════════════════════════════════════════════
#  Flood-fill extraction (v1 approach)
# ═══════════════════════════════════════════════════════════════


def flood_fill_body_mask(
    gray: np.ndarray,
    bg_thresh: int = 0,
) -> np.ndarray:
    """Create a binary body mask using threshold + flood-fill.

    *bg_thresh*: 0 = auto-detect from image mean.
    """
    H, W = gray.shape
    if bg_thresh == 0:
        bg_thresh = int(min(gray.mean() + 10, 220))

    _, bw = cv2.threshold(gray, bg_thresh, 255, cv2.THRESH_BINARY_INV)
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kern, iterations=5)

    flood = closed.copy()
    ff_mask = np.zeros((H + 2, W + 2), np.uint8)
    cv2.floodFill(flood, ff_mask, (0, 0), 255)

    body = cv2.bitwise_or(cv2.bitwise_not(flood), bw)
    body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, kern, iterations=3)
    body = cv2.morphologyEx(
        body, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        iterations=1,
    )
    return body


def find_bounds_from_mask(body: np.ndarray) -> BoundingBox:
    """Figure bounding box from a binary body mask, midline from head centroid."""
    coords = np.argwhere(body > 127)
    y_top = int(coords[:, 0].min())
    y_bot = int(coords[:, 0].max())
    fig_h = y_bot - y_top
    scale = 8.0 / fig_h

    # Midline from head centroid (top 10%)
    head_cx = []
    for y in range(y_top, y_top + max(1, int(fig_h * 0.10))):
        cols = np.where(body[y] > 127)[0]
        if len(cols) > 3:
            head_cx.append((cols.min() + cols.max()) / 2.0)
    mid = float(np.median(head_cx))

    x_left = int(coords[:, 1].min())
    x_right = int(coords[:, 1].max())

    return BoundingBox(
        x_left=x_left, x_right=x_right,
        y_top=y_top, y_bot=y_bot,
        midline_px=mid,
        fig_height_px=fig_h,
        scale=scale,
    )


def symmetry_check(
    body: np.ndarray,
    bounds: BoundingBox,
) -> dict:
    """Measure left/right symmetry at each head-unit level."""
    H = body.shape[0]
    symmetry = {}
    for hu in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
        y_px = int(bounds.y_top + hu / bounds.scale)
        if 0 <= y_px < H:
            cols = np.where(body[y_px] > 127)[0]
            if len(cols) > 3:
                r = (bounds.midline_px - cols.min()) * bounds.scale
                l = (cols.max() - bounds.midline_px) * bounds.scale
                symmetry[str(hu)] = {
                    "right_dx": round(r, 4),
                    "left_dx": round(l, 4),
                    "delta": round(abs(r - l), 4),
                }
    return symmetry


def right_half_contour(
    body: np.ndarray,
    bounds: BoundingBox,
) -> np.ndarray:
    """Extract right-half silhouette contour via cv2.findContours on body mask.

    Returns Nx2 array (dx, dy) in head-unit coords, savgol-smoothed.
    """
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    right_mask = body.copy()
    right_mask[:, int(bounds.midline_px) + 3:] = 0
    right_mask = cv2.morphologyEx(right_mask, cv2.MORPH_CLOSE, kern, iterations=2)

    contours, _ = cv2.findContours(right_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    raw_pts = contours[0].reshape(-1, 2).astype(float)

    norm = np.column_stack([
        (bounds.midline_px - raw_pts[:, 0]) * bounds.scale,
        (raw_pts[:, 1] - bounds.y_top) * bounds.scale,
    ])

    # Two-pass savgol smoothing
    from .geometry import savgol_smooth
    norm = savgol_smooth(norm, window=35, poly=3)

    step = max(1, len(norm) // 600)
    contour_sub = norm[::step]

    contour_sub = savgol_smooth(contour_sub, window=15, poly=3)
    return contour_sub


def row_measurements(
    body: np.ndarray,
    bounds: BoundingBox,
) -> dict:
    """Row-by-row width measurements with span detection."""
    H = body.shape[0]
    measurements = {}
    for hu in np.arange(0.0, 8.05, 0.1):
        y_px = int(bounds.y_top + hu / bounds.scale)
        if y_px < 0 or y_px >= H:
            continue
        cols = np.where(body[y_px] > 127)[0]
        if len(cols) < 3:
            continue

        spans = []
        start = int(cols[0])
        for i in range(1, len(cols)):
            if cols[i] - cols[i - 1] > 8:
                spans.append((start, int(cols[i - 1])))
                start = int(cols[i])
        spans.append((start, int(cols[-1])))

        span_data = [
            {
                "outer_dx": round((bounds.midline_px - xl) * bounds.scale, 4),
                "inner_dx": round((bounds.midline_px - xr) * bounds.scale, 4),
            }
            for xl, xr in spans
        ]
        measurements[f"{hu:.1f}"] = span_data

    return measurements


def flood_fill_strokes(
    gray: np.ndarray,
    body_contours: list,
    bounds: BoundingBox,
    *,
    ink_thresh: int = 0,
) -> list[list]:
    """Extract internal detail strokes using skeletonize on flood-fill body interior.

    Returns list of stroke point-lists (already in head-unit coords).
    """
    H, W = gray.shape
    if ink_thresh == 0:
        ink_thresh = int(max(gray.mean() * 0.55, 130))

    ink_mask = cv2.inRange(gray, 0, ink_thresh)

    outer_thick = np.zeros_like(ink_mask)
    cv2.drawContours(outer_thick, body_contours[:1], -1, 255, 10)
    inner_ink = cv2.bitwise_and(ink_mask, cv2.bitwise_not(outer_thick))
    inner_ink[:, int(bounds.midline_px) + 5:] = 0

    skel = skeletonize(inner_ink > 0).astype(np.uint8) * 255

    int_contours, _ = cv2.findContours(skel, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    from .geometry import savgol_smooth

    strokes = []
    for c in int_contours:
        if len(c) < 10:
            continue
        pts = c.reshape(-1, 2).astype(float)
        npts = np.column_stack([
            (bounds.midline_px - pts[:, 0]) * bounds.scale,
            (pts[:, 1] - bounds.y_top) * bounds.scale,
        ])
        if npts[:, 1].min() < -0.2 or npts[:, 1].max() > 8.2:
            continue

        sw = min(7, len(npts) - (1 - len(npts) % 2))
        if sw >= 5:
            npts[:, 0] = savgol_filter(npts[:, 0], sw, 2)
            npts[:, 1] = savgol_filter(npts[:, 1], sw, 2)

        strokes.append(npts[::2].tolist())

    return strokes


def extract_flood_fill(image_path: str) -> dict:
    """Full flood-fill extraction pipeline (v1).

    Returns a complete figure dict with contour, strokes, symmetry, measurements.
    """
    gray = load_gray(image_path)
    H, W = gray.shape

    body = flood_fill_body_mask(gray)
    bounds = find_bounds_from_mask(body)
    sym = symmetry_check(body, bounds)
    contour = right_half_contour(body, bounds)
    meas = row_measurements(body, bounds)

    # Get body contours for stroke masking
    right_mask = body.copy()
    right_mask[:, int(bounds.midline_px) + 3:] = 0
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    right_mask = cv2.morphologyEx(right_mask, cv2.MORPH_CLOSE, kern, iterations=2)
    body_contours, _ = cv2.findContours(right_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    body_contours = sorted(body_contours, key=cv2.contourArea, reverse=True)

    strokes = flood_fill_strokes(gray, body_contours, bounds)

    return {
        "meta": {
            "source": image_path,
            "image_size": [W, H],
            "midline_px": round(bounds.midline_px, 1),
            "y_top_px": bounds.y_top,
            "y_bot_px": bounds.y_bot,
            "fig_height_px": bounds.fig_height_px,
            "scale_px_to_hu": round(bounds.scale, 6),
            "contour_points": len(contour),
            "detail_strokes": len(strokes),
        },
        "symmetry": sym,
        "contour": contour.round(4).tolist(),
        "measurements": meas,
        "strokes": strokes,
    }
