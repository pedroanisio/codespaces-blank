"""
v3: Scan-line silhouette extraction with adaptive + global thresholding.

Usage:
    python scripts/extract_scanline.py <image_path> [output.json]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import extract, strokes, geometry, io as fio


def run(image_path: str, output_path: str) -> dict:
    gray = extract.load_gray(image_path)
    h, w = gray.shape

    binary = extract.threshold_lines(gray, adaptive=True, global_val=210)
    bounds = extract.find_bounds(binary)

    print(f"Bounds: x=[{bounds.x_left},{bounds.x_right}], y=[{bounds.y_top},{bounds.y_bot}]")
    print(f"Midline: {bounds.midline_px:.1f}, Height: {bounds.fig_height_px}px, Scale: {bounds.scale:.6f}")

    right_outer, right_inner = extract.scanline_silhouette(binary, bounds)
    print(f"Scan-line profile: {len(right_outer)} outer, {len(right_inner)} inner pts")

    contour_raw = extract.build_contour(right_outer, right_inner)
    contour_final = geometry.smooth(geometry.resample(contour_raw, n=700))

    print(f"Contour: {len(contour_final)} pts")
    print(f"  dx: [{contour_final[:,0].min():.4f}, {contour_final[:,0].max():.4f}]")
    print(f"  dy: [{contour_final[:,1].min():.4f}, {contour_final[:,1].max():.4f}]")

    all_strokes = strokes.extract_all(gray, binary, bounds)
    print(f"Total strokes: {len(all_strokes)}, pts: {sum(len(s) for s in all_strokes)}")

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
        print("Usage: python extract_scanline.py <image_path> [output.json]")
        sys.exit(1)

    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else img_path.rsplit(".", 1)[0] + ".json"
    run(img_path, out_path)
