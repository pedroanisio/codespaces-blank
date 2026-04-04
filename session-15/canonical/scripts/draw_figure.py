"""Render a figure JSON to a mirrored PNG.

Usage:
    python scripts/draw_figure.py <contours.json> [output.png] [--straight-fold]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import io as fio, render

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}

    if len(args) < 1:
        print("Usage: python draw_figure.py <contours.json> [output.png] [--straight-fold]")
        sys.exit(1)

    json_path = args[0]
    out_path = args[1] if len(args) > 1 else json_path.rsplit(".", 1)[0] + ".png"
    straight = "--straight-fold" in flags

    data = fio.load_figure(json_path)
    meta = data["meta"]
    mode = "straight-fold" if straight else "full-mirror"
    print(f"Drawing ({mode}): {meta['contour_points']} contour pts, "
          f"{meta['detail_strokes']} detail strokes")

    render.draw(data, out_path, straight_fold=straight)
