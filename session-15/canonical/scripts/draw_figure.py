"""
draw_figure.py — Stage 2: Matplotlib-only renderer

Reads a JSON file produced by extract_contours.py (Stage 1)
and draws the full symmetric figure: right half from data,
left half mirrored.

NO OpenCV, NO image files needed — just the JSON.

Usage:
    python draw_figure.py <contours.json> [output.png]
"""

import sys
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_data(json_path: str) -> dict:
    """Load the extracted contour data."""
    with open(json_path) as f:
        return json.load(f)


def draw(data: dict, output_path: str, **overrides):
    """
    Draw the full mirrored figure from extracted contour data.

    Parameters (overridable via **overrides):
        figsize:       (w, h) inches
        bg_color:      background colour
        contour_color: main silhouette colour
        contour_lw:    silhouette line width
        detail_color:  internal detail stroke colour
        detail_lw:     detail line width
        show_midline:  draw dashed midline
        show_guides:   draw horizontal head-unit guides
        title:         figure title (None = auto from metadata)
        xlim:          (xmin, xmax) or None for auto
    """

    # ── Defaults ──
    opts = {
        "figsize":       (7, 14),
        "bg_color":      "#ffffff",
        "contour_color": "#1a1a1a",
        "contour_lw":    1.5,
        "detail_color":  "#3a3a3a",
        "detail_lw":     0.7,
        "show_midline":  True,
        "show_guides":   False,
        "title":         None,
        "xlim":          None,
    }
    opts.update(overrides)

    # ── Unpack data ──
    contour = np.array(data["contour"])    # (N, 2): dx, dy
    strokes = [np.array(s) for s in data["strokes"]]
    meta = data["meta"]

    # ── Auto x-limits from max contour extent ──
    max_dx = contour[:, 0].max()
    margin = max_dx * 0.3
    if opts["xlim"] is None:
        opts["xlim"] = (-(max_dx + margin), max_dx + margin)

    # ── Create figure ──
    fig, ax = plt.subplots(
        figsize=opts["figsize"], facecolor=opts["bg_color"]
    )
    ax.set_facecolor(opts["bg_color"])

    # ── Draw both halves ──
    for sign in [1, -1]:
        # Silhouette
        ax.plot(
            sign * contour[:, 0], contour[:, 1],
            color=opts["contour_color"],
            lw=opts["contour_lw"],
            solid_capstyle="round",
            zorder=3,
        )
        # Close the contour loop
        ax.plot(
            [sign * contour[-1, 0], sign * contour[0, 0]],
            [contour[-1, 1], contour[0, 1]],
            color=opts["contour_color"],
            lw=opts["contour_lw"],
            solid_capstyle="round",
            zorder=3,
        )
        # Detail strokes
        for s in strokes:
            if len(s) >= 3:
                ax.plot(
                    sign * s[:, 0], s[:, 1],
                    color=opts["detail_color"],
                    lw=opts["detail_lw"],
                    solid_capstyle="round",
                    zorder=2,
                )

    # ── Guides ──
    if opts["show_midline"]:
        ax.axvline(0, color="#ddd", lw=0.3, ls="--", alpha=0.4, zorder=0)

    if opts["show_guides"]:
        for i in range(9):
            ax.axhline(i, color="#8eb4d8", lw=0.25, alpha=0.3, zorder=0)

    # ── Title ──
    title = opts["title"]
    if title is None:
        src = meta.get("source", "unknown")
        title = f"Extracted from {src.split('/')[-1]} — mirrored"
    ax.set_title(
        title, fontsize=12, fontweight="bold",
        color="#333", fontfamily="serif", pad=12,
    )

    # ── Axes ──
    ax.set_xlim(opts["xlim"])
    ax.set_ylim(8.2, -0.3)
    ax.set_aspect("equal")
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(
        output_path, dpi=180,
        facecolor=opts["bg_color"], bbox_inches="tight",
    )
    plt.close(fig)
    print(f"Saved → {output_path}")


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════
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

    data = load_data(json_path)
    meta = data["meta"]
    print(f"Drawing: {meta['contour_points']} contour pts, "
          f"{meta['detail_strokes']} detail strokes")

    draw(data, out_path)
