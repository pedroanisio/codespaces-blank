"""Matplotlib renderer — JSON figure data to mirrored PNG.

No OpenCV needed — just matplotlib + numpy.
"""

import os
import tempfile
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon


def _split_outer(contour: np.ndarray) -> np.ndarray:
    """Extract only the outer silhouette portion of the contour.

    The contour traces: outer edge (top→bottom, large dx) then inner
    return (bottom→top, small dx near midline). The split point is
    where dy reaches its maximum (bottom of figure).
    """
    split = int(np.argmax(contour[:, 1]))
    return contour[: split + 1]


def draw(data: dict, output_path: str, **overrides) -> None:
    """Draw the full mirrored figure from extracted contour data.

    Parameters (overridable via **overrides):
        figsize:        (w, h) inches
        bg_color:       background colour
        contour_color:  main silhouette colour
        contour_lw:     silhouette line width
        detail_color:   internal detail stroke colour
        detail_lw:      detail line width
        show_midline:   draw dashed midline
        show_guides:    draw horizontal head-unit guides
        straight_fold:  True = close halves with a straight line at x=0
                        False = mirror the full contour (including inner path)
        title:          figure title (None = auto from metadata)
        xlim:           (xmin, xmax) or None for auto
    """
    opts = {
        "figsize":       (7, 14),
        "bg_color":      "#ffffff",
        "contour_color": "#1a1a1a",
        "contour_lw":    1.5,
        "detail_color":  "#3a3a3a",
        "detail_lw":     0.7,
        "show_midline":  True,
        "show_guides":   False,
        "straight_fold": False,
        "title":         None,
        "xlim":          None,
    }
    opts.update(overrides)

    contour = np.array(data["contour"])
    strokes = [np.array(s) for s in data["strokes"]]
    meta = data["meta"]

    max_dx = contour[:, 0].max()
    margin = max_dx * 0.3
    if opts["xlim"] is None:
        opts["xlim"] = (-(max_dx + margin), max_dx + margin)

    fig, ax = plt.subplots(
        figsize=opts["figsize"], facecolor=opts["bg_color"],
    )
    ax.set_facecolor(opts["bg_color"])

    if opts["straight_fold"]:
        # Clean the contour: clamp tiny dx to 0 (center noise) but
        # keep meaningful dx (inner leg separation, crotch detail)
        fold_thresh = max_dx * 0.03
        clean = contour.copy()
        clean[clean[:, 0] < fold_thresh, 0] = 0.0

        # Single unified outline: right full contour + left mirrored (reversed)
        outline_x = np.concatenate([clean[:, 0], -clean[::-1, 0]])
        outline_y = np.concatenate([clean[:, 1], clean[::-1, 1]])

        # This is both the visible outline AND the clip boundary
        clip_verts = np.column_stack([outline_x, outline_y])
        clip_poly = MplPolygon(
            clip_verts, closed=True, transform=ax.transData,
            visible=False,
        )
        ax.add_patch(clip_poly)

        # Draw the single unified outline
        ax.plot(
            outline_x, outline_y,
            color=opts["contour_color"], lw=opts["contour_lw"],
            solid_capstyle="round", zorder=3,
        )

        # Detail strokes — clipped to silhouette
        fold_thresh = max_dx * 0.06
        for s in strokes:
            if len(s) < 3:
                continue
            if s[:, 0].max() < fold_thresh:
                # Midline stroke — draw once, clipped
                line, = ax.plot(
                    s[:, 0], s[:, 1],
                    color=opts["detail_color"], lw=opts["detail_lw"],
                    solid_capstyle="round", zorder=2,
                )
                line.set_clip_path(clip_poly)
            else:
                for sign in [1, -1]:
                    line, = ax.plot(
                        sign * s[:, 0], s[:, 1],
                        color=opts["detail_color"], lw=opts["detail_lw"],
                        solid_capstyle="round", zorder=2,
                    )
                    line.set_clip_path(clip_poly)
    else:
        for sign in [1, -1]:
            ax.plot(
                sign * contour[:, 0], contour[:, 1],
                color=opts["contour_color"], lw=opts["contour_lw"],
                solid_capstyle="round", zorder=3,
            )
            ax.plot(
                [sign * contour[-1, 0], sign * contour[0, 0]],
                [contour[-1, 1], contour[0, 1]],
                color=opts["contour_color"], lw=opts["contour_lw"],
                solid_capstyle="round", zorder=3,
            )
            for s in strokes:
                if len(s) >= 3:
                    ax.plot(
                        sign * s[:, 0], s[:, 1],
                        color=opts["detail_color"], lw=opts["detail_lw"],
                        solid_capstyle="round", zorder=2,
                    )

    if opts["show_midline"]:
        ax.axvline(0, color="#ddd", lw=0.3, ls="--", alpha=0.4, zorder=0)

    if opts["show_guides"]:
        for i in range(9):
            ax.axhline(i, color="#8eb4d8", lw=0.25, alpha=0.3, zorder=0)

    title = opts["title"]
    if title is None:
        src = meta.get("source", "unknown")
        title = f"Extracted from {src.split('/')[-1]} — mirrored"
    ax.set_title(
        title, fontsize=12, fontweight="bold",
        color="#333", fontfamily="serif", pad=12,
    )

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
