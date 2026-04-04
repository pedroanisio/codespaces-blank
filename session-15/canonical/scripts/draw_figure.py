"""Render a figure JSON to a mirrored PNG.

Usage:
    python scripts/draw_figure.py <contours.json> [output.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import io as fio, render

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python draw_figure.py <contours.json> [output.png]")
        sys.exit(1)

    json_path = sys.argv[1]
    out_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else json_path.rsplit(".", 1)[0] + ".png"
    )

    data = fio.load_figure(json_path)
    meta = data["meta"]
    print(f"Drawing: {meta['contour_points']} contour pts, "
          f"{meta['detail_strokes']} detail strokes")

    render.draw(data, out_path)
