"""Flood-fill contour extraction (v1).

Usage:
    python scripts/extract_contours.py <image_path> [output.json]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import extract, io as fio

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_contours.py <image_path> [output.json]")
        sys.exit(1)

    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else img_path.rsplit(".", 1)[0] + ".json"

    print(f"Extracting: {img_path}")
    data = extract.extract_flood_fill(img_path)
    meta = data["meta"]
    print(f"  Image:    {meta['image_size'][0]}x{meta['image_size'][1]}")
    print(f"  Midline:  {meta['midline_px']} px")
    print(f"  Height:   {meta['fig_height_px']} px -> 8.0 head-units")
    print(f"  Contour:  {meta['contour_points']} points")
    print(f"  Strokes:  {meta['detail_strokes']}")

    fio.save_figure(data, out_path)
