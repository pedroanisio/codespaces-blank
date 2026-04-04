"""
v4: Scan-line extraction with horizontal/vertical guide line removal.

Usage:
    python scripts/extract_with_guide_removal.py <image_path> [output.json]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import extract, strokes, geometry, io as fio


def run(image_path: str, output_path: str) -> dict:
    gray = extract.load_gray(image_path)
    h, w = gray.shape

    # v4 difference: global-only threshold + guide removal
    binary = extract.threshold_lines(gray, adaptive=False, global_val=215)
    binary = extract.remove_guides(binary)

    bounds = extract.find_bounds(binary, thresh_ratio=0.03)
    max_plausible_dx = (bounds.x_right - bounds.midline_px) * bounds.scale * 1.05

    print(f"{Path(image_path).name}: bbox=[{bounds.x_left},{bounds.x_right}]x"
          f"[{bounds.y_top},{bounds.y_bot}], midline={bounds.midline_px:.0f}, "
          f"max_dx_bound={max_plausible_dx:.3f}")

    right_outer, right_inner = extract.scanline_silhouette(
        binary, bounds, max_dx_factor=1.05,
    )
    contour_raw = extract.build_contour(right_outer, right_inner)
    contour_final = geometry.smooth(geometry.resample(contour_raw, n=700))

    print(f"  Contour: max_dx={contour_final[:,0].max():.3f}")

    contour_max = contour_final[:, 0].max()
    all_strokes = strokes.extract_all(
        gray, binary, bounds, contour_max_dx=contour_max * 1.15,
    )

    print(f"  Strokes: {len(all_strokes)}, pts: {sum(len(s) for s in all_strokes)}")

    source = Path(image_path).name
    data = {
        "contour": contour_final.tolist(),
        "strokes": [s.tolist() for s in all_strokes],
        "meta": fio.build_meta(
            contour_points=len(contour_final),
            detail_strokes=len(all_strokes),
            source=source,
            image_size=[w, h],
            midline_px=float(bounds.midline_px),
            y_top_px=bounds.y_top,
            y_bot_px=bounds.y_bot,
            fig_height_px=bounds.fig_height_px,
            scale_px_to_hu=bounds.scale,
        ),
    }

    fio.save_figure(data, output_path)
    return data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_with_guide_removal.py <image_path> [output.json]")
        sys.exit(1)

    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else img_path.rsplit(".", 1)[0] + ".json"
    run(img_path, out_path)
