"""
extract_contours.py — Stage 1: OpenCV contour extraction

Reads a frontal line-art image, extracts:
  - Main silhouette contour (right half)
  - Internal detail strokes (right half)
  - Key anatomical measurements

Saves everything as a self-contained JSON file that can be
drawn by Stage 2 (matplotlib only, no OpenCV needed).

Usage:
    python extract_contours.py <image_path> [output.json]
"""

import sys
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import savgol_filter
from skimage.morphology import skeletonize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import io as fio


def extract(image_path: str, ink_thresh: int = 0, bg_thresh: int = 0) -> dict:
    """
    Full extraction pipeline.

    Returns a dict with all data needed to reconstruct the figure:
      - contour:  [[dx, dy], ...] main silhouette (right half, normalised)
      - strokes:  [[[dx, dy], ...], ...] internal detail lines (right half)
      - measurements: dict of widths at key Y positions
      - meta: image size, midline, scale, etc.
    """

    # ── 1. Load ──────────────────────────────────────────────────
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape

    # Auto-detect thresholds if not provided
    mean_val = gray.mean()
    if bg_thresh == 0:
        bg_thresh = int(min(mean_val + 10, 220))
    if ink_thresh == 0:
        ink_thresh = int(max(mean_val * 0.55, 130))

    # ── 2. Body mask (threshold + flood-fill) ────────────────────
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

    # ── 3. Figure bounds + midline ───────────────────────────────
    coords = np.argwhere(body > 127)
    Y_TOP = int(coords[:, 0].min())
    Y_BOT = int(coords[:, 0].max())
    FIG_H = Y_BOT - Y_TOP
    SCALE = 8.0 / FIG_H  # normalise to 8 "head-units"

    # Midline from head centroid (top 10%)
    head_cx = []
    for y in range(Y_TOP, Y_TOP + max(1, int(FIG_H * 0.10))):
        cols = np.where(body[y] > 127)[0]
        if len(cols) > 3:
            head_cx.append((cols.min() + cols.max()) / 2.0)
    MID = float(np.median(head_cx))

    # ── 4. Symmetry check ────────────────────────────────────────
    symmetry = {}
    for hu in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
        y_px = int(Y_TOP + hu / SCALE)
        if 0 <= y_px < H:
            cols = np.where(body[y_px] > 127)[0]
            if len(cols) > 3:
                r = (MID - cols.min()) * SCALE
                l = (cols.max() - MID) * SCALE
                symmetry[str(hu)] = {
                    "right_dx": round(r, 4),
                    "left_dx": round(l, 4),
                    "delta": round(abs(r - l), 4),
                }

    # ── 5. Right-half silhouette contour ─────────────────────────
    right_mask = body.copy()
    right_mask[:, int(MID) + 3:] = 0
    right_mask = cv2.morphologyEx(right_mask, cv2.MORPH_CLOSE, kern, iterations=2)

    contours, _ = cv2.findContours(
        right_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    raw_pts = contours[0].reshape(-1, 2).astype(float)

    # Normalise: dx = (MID - x) * SCALE, dy = (y - Y_TOP) * SCALE
    norm = np.column_stack([
        (MID - raw_pts[:, 0]) * SCALE,
        (raw_pts[:, 1] - Y_TOP) * SCALE,
    ])

    # Smooth (two passes: coarse then fine)
    w1 = min(35, len(norm) - (1 if len(norm) % 2 == 0 else 0))
    if w1 >= 5:
        norm[:, 0] = savgol_filter(norm[:, 0], w1, 3, mode="wrap")
        norm[:, 1] = savgol_filter(norm[:, 1], w1, 3, mode="wrap")

    # Subsample
    step = max(1, len(norm) // 600)
    contour_sub = norm[::step]

    w2 = min(15, len(contour_sub) - (1 if len(contour_sub) % 2 == 0 else 0))
    if w2 >= 5:
        contour_sub[:, 0] = savgol_filter(contour_sub[:, 0], w2, 3, mode="wrap")
        contour_sub[:, 1] = savgol_filter(contour_sub[:, 1], w2, 3, mode="wrap")

    # ── 6. Row-by-row width measurements ─────────────────────────
    measurements = {}
    sample_ys = np.arange(0.0, 8.05, 0.1)
    for hu in sample_ys:
        y_px = int(Y_TOP + hu / SCALE)
        if y_px < 0 or y_px >= H:
            continue
        cols = np.where(body[y_px] > 127)[0]
        if len(cols) < 3:
            continue

        # Detect spans (gap > 8px = separate body part)
        spans = []
        start = int(cols[0])
        for i in range(1, len(cols)):
            if cols[i] - cols[i - 1] > 8:
                spans.append((start, int(cols[i - 1])))
                start = int(cols[i])
        spans.append((start, int(cols[-1])))

        # Convert to dx from midline
        span_data = []
        for xl, xr in spans:
            span_data.append({
                "outer_dx": round((MID - xl) * SCALE, 4),
                "inner_dx": round((MID - xr) * SCALE, 4),
            })

        measurements[f"{hu:.1f}"] = span_data

    # ── 7. Internal detail strokes ───────────────────────────────
    ink_mask = cv2.inRange(gray, 0, ink_thresh)

    # Remove outer contour so only internal lines remain
    outer_thick = np.zeros_like(ink_mask)
    cv2.drawContours(outer_thick, contours[:1], -1, 255, 10)
    inner_ink = cv2.bitwise_and(ink_mask, cv2.bitwise_not(outer_thick))
    inner_ink[:, int(MID) + 5:] = 0  # right half only

    # Skeletonize → thin lines
    skel = skeletonize(inner_ink > 0).astype(np.uint8) * 255

    int_contours, _ = cv2.findContours(
        skel, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE
    )

    strokes = []
    for c in int_contours:
        if len(c) < 10:
            continue
        pts = c.reshape(-1, 2).astype(float)
        npts = np.column_stack([
            (MID - pts[:, 0]) * SCALE,
            (pts[:, 1] - Y_TOP) * SCALE,
        ])
        # Skip out-of-bounds
        if npts[:, 1].min() < -0.2 or npts[:, 1].max() > 8.2:
            continue

        # Smooth
        sw = min(7, len(npts) - (1 - len(npts) % 2))
        if sw >= 5:
            npts[:, 0] = savgol_filter(npts[:, 0], sw, 2)
            npts[:, 1] = savgol_filter(npts[:, 1], sw, 2)

        strokes.append(npts[::2].tolist())

    # ── 8. Assemble output ───────────────────────────────────────
    result = {
        "meta": {
            "source": image_path,
            "image_size": [W, H],
            "midline_px": round(MID, 1),
            "y_top_px": Y_TOP,
            "y_bot_px": Y_BOT,
            "fig_height_px": FIG_H,
            "scale_px_to_hu": round(SCALE, 6),
            "contour_points": len(contour_sub),
            "detail_strokes": len(strokes),
        },
        "symmetry": symmetry,
        "contour": contour_sub.round(4).tolist(),
        "measurements": measurements,
        "strokes": strokes,
    }

    return result


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_contours.py <image_path> [output.json]")
        sys.exit(1)

    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else img_path.rsplit(".", 1)[0] + ".json"

    print(f"Extracting: {img_path}")
    data = extract(img_path)
    meta = data["meta"]
    print(f"  Image:    {meta['image_size'][0]}×{meta['image_size'][1]}")
    print(f"  Midline:  {meta['midline_px']} px")
    print(f"  Height:   {meta['fig_height_px']} px → 8.0 head-units")
    print(f"  Contour:  {meta['contour_points']} points")
    print(f"  Strokes:  {meta['detail_strokes']}")

    with open(out_path, "w") as f:
        json.dump(data, f)

    print(f"  Saved:    {out_path}")
    print(f"  Size:     {len(json.dumps(data)) / 1024:.0f} KB")
