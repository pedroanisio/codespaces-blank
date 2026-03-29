from __future__ import annotations

import argparse
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from human_body.entry import generate_human_body


_SKULL_REGIONS = {"axial_cranium", "axial_face"}
_REGION_COLORS = {
    "axial_cranium": "#f3e5c8",
    "axial_face": "#ead6b0",
}
_VIEW_PLANES = (
    ("Coronal", 0, -90),
    ("Sagittal", 0, 0),
    ("Axial", 90, -90),
)
_FOUR_VIEW_PANELS = (
    ("Frontal", 8, -90),
    ("Coronal", 0, -90),
    ("Sagittal", 0, 0),
    ("Axial", 90, -90),
)


def _rotation_matrix_xyz(rotation_deg: dict) -> np.ndarray:
    rx, ry, rz = np.deg2rad([rotation_deg["x"], rotation_deg["y"], rotation_deg["z"]])
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)

    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx


def _skull_mesh_triangles(body: dict) -> tuple[list[np.ndarray], list[str]]:
    bones_by_id = {bone["id"]: bone for bone in body["skeleton"]}
    skull_ids = {
        bone["id"]
        for bone in body["skeleton"]
        if bone["region"] in _SKULL_REGIONS
    }

    triangles: list[np.ndarray] = []
    colors: list[str] = []

    for geo in body["boneGeometries"]:
        if geo["boneId"] not in skull_ids or geo["geometryType"] != "indexed_mesh":
            continue

        bone = bones_by_id[geo["boneId"]]
        lod0 = min(geo["lods"], key=lambda lod: lod["level"])
        positions = np.asarray(lod0["vertices"]["positions"], dtype=float).reshape(-1, 3)
        indices = np.asarray(lod0["indices"], dtype=int).reshape(-1, 3)
        rotation = _rotation_matrix_xyz(bone["transform"]["rotation"])
        translation = np.array(
            [
                bone["transform"]["position"]["x"],
                bone["transform"]["position"]["y"],
                bone["transform"]["position"]["z"],
            ],
            dtype=float,
        )
        scale = np.array(
            [
                bone["transform"]["scale"]["x"],
                bone["transform"]["scale"]["y"],
                bone["transform"]["scale"]["z"],
            ],
            dtype=float,
        )

        transformed = (positions * scale) @ rotation.T + translation
        triangles.extend(transformed[indices])
        colors.extend([_REGION_COLORS.get(bone["region"], "#e6d5b8")] * len(indices))

    return triangles, colors


def _configure_anatomical_axis(
    ax,
    *,
    label: str,
    elev: float,
    azim: float,
    center: np.ndarray,
    span: float,
    margin: float,
) -> None:
    ax.set_facecolor("#f6f1e7")
    ax.set_proj_type("ortho")
    ax.set_xlim(center[0] - span / 2 - margin, center[0] + span / 2 + margin)
    ax.set_ylim(center[1] - span / 2 - margin, center[1] + span / 2 + margin)
    ax.set_zlim(center[2] - span / 2 - margin, center[2] + span / 2 + margin)
    ax.set_box_aspect((1.0, 1.15, 0.9))
    ax.view_init(elev=elev, azim=azim, roll=0)
    ax.set_title(label, fontsize=13, color="#4a3a22", pad=10)
    ax.axis("off")


def render_skull_png(
    output_path: str | Path,
    *,
    seed: int = 0,
    variation: int = 0,
    dpi: int = 220,
    layout: str = "hero",
) -> Path:
    random.seed(seed)
    body = generate_human_body(
        variation=variation,
        bone_geometry_format="indexed_mesh",
        include={"skeleton", "geometry"},
    )
    triangles, colors = _skull_mesh_triangles(body)
    if not triangles:
        raise ValueError("No skull geometry triangles were generated")

    points = np.vstack(triangles)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = (mins + maxs) / 2
    span = max(maxs - mins)
    margin = span * 0.12

    if layout in {"three_planes", "four_views"}:
        panels = _VIEW_PLANES if layout == "three_planes" else _FOUR_VIEW_PANELS
        cols = len(panels)
        fig = plt.figure(figsize=(4.6 * cols, 5), dpi=dpi, facecolor="#f6f1e7")
        axes = [fig.add_subplot(1, cols, idx + 1, projection="3d") for idx in range(cols)]
        for ax, (label, elev, azim) in zip(axes, panels):
            collection = Poly3DCollection(
                triangles,
                facecolors=colors,
                edgecolors="#b4966d",
                linewidths=0.1,
                alpha=1.0,
            )
            collection.set_zsort("average")
            ax.add_collection3d(collection)
            _configure_anatomical_axis(
                ax,
                label=label,
                elev=elev,
                azim=azim,
                center=center,
                span=span,
                margin=margin,
            )
    else:
        fig = plt.figure(figsize=(8, 8), dpi=dpi, facecolor="#f6f1e7")
        ax = fig.add_subplot(111, projection="3d")
        ax.set_facecolor("#f6f1e7")

        collection = Poly3DCollection(
            triangles,
            facecolors=colors,
            edgecolors="#b4966d",
            linewidths=0.12,
            alpha=1.0,
        )
        collection.set_zsort("average")
        ax.add_collection3d(collection)

        ax.set_xlim(center[0] - span / 2 - margin, center[0] + span / 2 + margin)
        ax.set_ylim(center[1] - span / 2 - margin, center[1] + span / 2 + margin)
        ax.set_zlim(center[2] - span / 2 - margin, center[2] + span / 2 + margin)
        ax.set_box_aspect((1.0, 1.15, 0.9))
        ax.view_init(elev=18, azim=-58, roll=0)
        ax.axis("off")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", pad_inches=0, transparent=False)
    plt.close(fig)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and render the skull to a PNG")
    parser.add_argument("-o", "--output", default="results/skull/skull.png")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--variation", type=int, default=0)
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--layout", choices=["hero", "three_planes", "four_views"], default="hero")
    args = parser.parse_args()

    path = render_skull_png(
        args.output,
        seed=args.seed,
        variation=args.variation,
        dpi=args.dpi,
        layout=args.layout,
    )
    print(path)


if __name__ == "__main__":
    main()
