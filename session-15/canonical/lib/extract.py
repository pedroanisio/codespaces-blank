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
    """Remove long solid horizontal and vertical guide lines via morphological opening."""
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


def remove_text_components(
    binary: np.ndarray,
    *,
    min_area: int = 0,
    area_ratio: float = 0.002,
) -> np.ndarray:
    """Remove small connected components (text labels, stray marks) from binary mask.

    Keeps only components whose area >= max(min_area, total_image_area * area_ratio).
    The figure body is always the largest component and is preserved.
    """
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    h, w = binary.shape
    threshold = max(min_area, int(h * w * area_ratio))

    clean = np.zeros_like(binary)
    for i in range(1, n_labels):  # skip background (0)
        if stats[i, cv2.CC_STAT_AREA] >= threshold:
            clean[labels == i] = 255
    return clean


def find_bounds(
    binary: np.ndarray,
    thresh_ratio: float = 0.01,
    midline_px: float | None = None,
) -> BoundingBox:
    """Find figure bounding box and midline from a binary ink mask."""
    coords = np.argwhere(binary > 0)
    if len(coords) == 0:
        raise ValueError("Cannot find bounds in an empty binary mask")

    y_top = int(coords[:, 0].min())
    y_bot = int(coords[:, 0].max())
    x_left = int(coords[:, 1].min())
    x_right = int(coords[:, 1].max())
    if midline_px is None:
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


def find_centered_square_crop(
    binary: np.ndarray,
    *,
    close_kernel: int = 9,
    margin_px: int = 8,
) -> tuple[tuple[int, int, int, int], np.ndarray]:
    """Find a square crop anchored to the image top-middle that keeps the main figure.

    The crop is selected from a morphologically closed mask so open line art behaves
    more like a filled figure. Candidate components are ranked by whether they cross
    the image vertical midpoint, then by how early they appear from the top-middle
    search axis, then by area. The final square contains the chosen component while
    excluding edge notes when possible.

    Returns ``((x_left, y_top, side, centerline_in_crop), crop_mask)``.
    """
    height, width = binary.shape
    center_x = width // 2

    kernel_size = max(3, close_kernel | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed)
    candidates: list[tuple[tuple[int, int, int, int], tuple[int, int, int, int]]] = []
    for label in range(1, n_labels):
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        area = int(stats[label, cv2.CC_STAT_AREA])
        touches_center = x <= center_x <= (x + w - 1)
        center_distance = min(abs(center_x - x), abs(center_x - (x + w - 1)), abs(center_x - (x + w // 2)))
        score = (1 if touches_center else 0, -y, area, -center_distance)
        candidates.append((score, (x, y, w, h)))

    if not candidates:
        raise ValueError("Cannot find a closed figure candidate in the binary mask")

    _, (comp_x, comp_y, comp_w, comp_h) = max(candidates, key=lambda item: item[0])

    left_span = max(0, center_x - comp_x)
    right_span = max(0, comp_x + comp_w - center_x)
    side = max(comp_h, left_span + right_span, comp_w) + (margin_px * 2)
    side = min(side, width, height)

    x_left = center_x - side // 2
    x_left = max(0, min(x_left, width - side))
    if comp_x < x_left:
        x_left = comp_x
    if comp_x + comp_w > x_left + side:
        x_left = comp_x + comp_w - side
    x_left = max(0, min(x_left, width - side))

    centerline_in_crop = center_x - x_left

    y_top = comp_y - margin_px
    y_top = max(0, min(y_top, height - side))
    if comp_y + comp_h > y_top + side:
        y_top = comp_y + comp_h - side
    y_top = max(0, min(y_top, height - side))

    crop = binary[y_top : y_top + side, x_left : x_left + side].copy()
    return (x_left, y_top, side, centerline_in_crop), crop


def scanline_silhouette(
    binary: np.ndarray,
    bounds: BoundingBox,
    *,
    dilate_k: int = 3,
    gap_thresh: float = 0.05,
    max_dx_factor: float | None = None,
    max_dx_hu: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Scan-line right-half silhouette extraction.

    Returns (right_outer, right_inner) as Nx2 arrays in head-unit coords.
    *max_dx_factor*: clamp outer dx to bounding-box half-width * factor.
    *max_dx_hu*: absolute max dx in head-units (overrides max_dx_factor).
    """
    thick = cv2.dilate(
        binary,
        np.ones((dilate_k, dilate_k), np.uint8),
        iterations=1,
    )

    max_plausible_dx = None
    if max_dx_hu is not None:
        max_plausible_dx = max_dx_hu
    elif max_dx_factor is not None:
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

    Guide lines are removed before closing to prevent them from bridging
    the crotch gap or widening the silhouette.

    *bg_thresh*: 0 = auto-detect from image mean.
    """
    H, W = gray.shape
    if bg_thresh == 0:
        bg_thresh = int(min(gray.mean() + 10, 220))

    _, bw = cv2.threshold(gray, bg_thresh, 255, cv2.THRESH_BINARY_INV)
    bw = remove_guides(bw)

    # Isolate the main figure ink BEFORE morphological closing.
    # Closing is aggressive (bridges ~15px gaps) and would merge the
    # figure with nearby rulers, construction marks, or text labels.
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bw)
    if n_labels > 2:
        areas = stats[1:, cv2.CC_STAT_AREA]
        largest = int(np.argmax(areas)) + 1
        bw = ((labels == largest).astype(np.uint8)) * 255

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

    # Width clamp: no human figure exceeds ~2.0 HU from midline.
    # Mask out pixels beyond that to exclude rulers, construction marks, etc.
    coords = np.argwhere(body > 127)
    if len(coords) > 0:
        y_top = int(coords[:, 0].min())
        y_bot = int(coords[:, 0].max())
        fig_h = y_bot - y_top
        # Find midline from head centroid (top 10%)
        head_cx = []
        for y in range(y_top, y_top + max(1, int(fig_h * 0.10))):
            cols = np.where(body[y] > 127)[0]
            if len(cols) > 3:
                head_cx.append((cols.min() + cols.max()) / 2.0)
        if head_cx:
            mid = float(np.median(head_cx))
            max_half_px = int(fig_h * (2.0 / 8.0))
            body[:, : max(0, int(mid) - max_half_px)] = 0
            body[:, min(W, int(mid) + max_half_px) :] = 0

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
    *,
    target_pts: int = 1200,
    smooth_w1: int = 15,
    smooth_w2: int = 7,
    max_dx_hu: float = 2.0,
) -> np.ndarray:
    """Extract right-half silhouette contour via cv2.findContours on body mask.

    Returns Nx2 array (dx, dy) in head-unit coords, savgol-smoothed.

    *target_pts*: output point count (higher = more detail).
    *smooth_w1/w2*: savgol window for coarse/fine passes (lower = sharper corners).
    *max_dx_hu*: maximum silhouette half-width in head-units. Pixels beyond
        this distance from the midline are masked out before contour extraction,
        excluding outstretched arms and other lateral extensions.
    """
    kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    right_mask = body.copy()
    right_mask[:, int(bounds.midline_px) + 3:] = 0

    # Clip to max width — excludes arms extending beyond torso width
    if max_dx_hu is not None:
        max_dx_px = int(max_dx_hu / bounds.scale)
        left_limit = int(bounds.midline_px) - max_dx_px
        if left_limit > 0:
            right_mask[:, :left_limit] = 0

    right_mask = cv2.morphologyEx(right_mask, cv2.MORPH_CLOSE, kern, iterations=2)

    contours, _ = cv2.findContours(right_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    raw_pts = contours[0].reshape(-1, 2).astype(float)

    norm = np.column_stack([
        (bounds.midline_px - raw_pts[:, 0]) * bounds.scale,
        (raw_pts[:, 1] - bounds.y_top) * bounds.scale,
    ])

    from .geometry import savgol_smooth
    norm = savgol_smooth(norm, window=smooth_w1, poly=3)

    step = max(1, len(norm) // target_pts)
    contour_sub = norm[::step]

    contour_sub = savgol_smooth(contour_sub, window=smooth_w2, poly=3)
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
    min_pts: int = 5,
    outer_mask_width: int = 5,
) -> list[list]:
    """Extract internal detail strokes using skeletonize on flood-fill body interior.

    Returns list of stroke point-lists (already in head-unit coords).

    *ink_thresh*: 0 = auto-detect. Higher values capture finer lines.
    *min_pts*: minimum points per stroke (lower = more small details).
    *outer_mask_width*: px width to erase around outer contour (lower = less detail lost).
    """
    H, W = gray.shape
    if ink_thresh == 0:
        ink_thresh = int(max(gray.mean() * 0.70, 140))

    ink_mask = cv2.inRange(gray, 0, ink_thresh)
    ink_mask = remove_guides(ink_mask)

    outer_thick = np.zeros_like(ink_mask)
    cv2.drawContours(outer_thick, body_contours[:1], -1, 255, outer_mask_width)
    inner_ink = cv2.bitwise_and(ink_mask, cv2.bitwise_not(outer_thick))
    inner_ink[:, int(bounds.midline_px) + 5:] = 0

    skel = skeletonize(inner_ink > 0).astype(np.uint8) * 255

    int_contours, _ = cv2.findContours(skel, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

    strokes = []
    for c in int_contours:
        if len(c) < min_pts:
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

        # Keep full resolution (no subsampling)
        strokes.append(npts.tolist())

    return strokes


def extract_flood_fill(image_path: str) -> "FigureData":
    """Full flood-fill extraction pipeline (v1).

    Isolates the main figure via centered square crop (handles images with
    multiple figures, text, or reference annotations), then extracts contour,
    strokes, landmarks, and parametric fit.
    """
    from .model import FigureData, ParametricFit
    from .profile import find_anatomical_landmarks
    from .geometry import fit_bspline_segments

    gray = load_gray(image_path)
    H, W = gray.shape

    # Isolate the main figure via a rectangular crop centered on the
    # largest ink component.  Unlike the older square crop this preserves
    # the full figure height for portrait images.
    pre_binary = threshold_lines(gray, adaptive=False, global_val=210)
    pre_binary = remove_text_components(pre_binary)
    n_lab, labels_pre, stats_pre, _ = cv2.connectedComponentsWithStats(pre_binary)
    if n_lab > 1:
        areas = stats_pre[1:, cv2.CC_STAT_AREA]
        big = int(np.argmax(areas)) + 1
        cx = int(stats_pre[big, cv2.CC_STAT_LEFT])
        cy = int(stats_pre[big, cv2.CC_STAT_TOP])
        cw = int(stats_pre[big, cv2.CC_STAT_WIDTH])
        ch = int(stats_pre[big, cv2.CC_STAT_HEIGHT])
        # Pad 5% around the component
        pad = max(int(max(cw, ch) * 0.05), 8)
        crop_x = max(0, cx - pad)
        crop_y = max(0, cy - pad)
        crop_w = min(W - crop_x, cw + 2 * pad)
        crop_h = min(H - crop_y, ch + 2 * pad)
    else:
        crop_x, crop_y, crop_w, crop_h = 0, 0, W, H
    gray = gray[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]

    from . import strokes as strokes_mod
    from .geometry import resample, smooth

    ch_px, cw_px = gray.shape

    # Two-pass guide removal: standard (w//4) catches rulers,
    # aggressive (w//8) catches shorter construction crosshairs.
    binary = threshold_lines(gray, adaptive=False, global_val=215)
    binary = remove_guides(binary)
    horiz_k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (cw_px // 8, 1))
    vert_k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (1, ch_px // 8))
    h2 = cv2.dilate(cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_k2),
                     np.ones((5, 1), np.uint8), iterations=1)
    v2 = cv2.dilate(cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_k2),
                     np.ones((1, 5), np.uint8), iterations=1)
    binary[h2 > 0] = 0
    binary[v2 > 0] = 0
    binary = remove_text_components(binary, area_ratio=0.001)

    # Scan-line silhouette (robust to construction rectangles)
    bounds = find_bounds(binary, thresh_ratio=0.03,
                         midline_px=float(cw_px // 2))
    outer, inner = scanline_silhouette(binary, bounds, max_dx_hu=1.8)
    contour_raw = build_contour(outer, inner)
    contour = smooth(resample(contour_raw, n=1200))

    # Strokes
    detail_strokes = strokes_mod.extract_all(
        gray, binary, bounds, contour_max_dx=contour[:, 0].max() * 1.15,
    )

    sym = {}
    meas = {}

    # Anatomical landmarks + parametric fit
    landmarks = find_anatomical_landmarks(contour)
    parametric = None
    if len(landmarks) >= 2:
        segments, max_err, mean_err = fit_bspline_segments(contour, landmarks)
        parametric = ParametricFit(
            segments=segments,
            max_error=max_err,
            mean_error=mean_err,
            n_original_points=len(contour),
            n_parameters=sum(s.n_parameters for s in segments),
        )

    meta = {
        "source": image_path,
        "image_size": [W, H],
        "crop_rect_px": [crop_x, crop_y, crop_w, crop_h],
        "midline_px": round(bounds.midline_px, 1),
        "y_top_px": bounds.y_top,
        "y_bot_px": bounds.y_bot,
        "fig_height_px": bounds.fig_height_px,
        "scale_px_to_hu": round(bounds.scale, 6),
        "contour_points": len(contour),
        "detail_strokes": len(detail_strokes),
    }

    return FigureData(
        contour=contour,
        strokes=[np.array(s) if not isinstance(s, np.ndarray) else s for s in detail_strokes],
        meta=meta,
        landmarks=landmarks,
        parametric=parametric,
        symmetry=sym,
        measurements=meas,
    )
