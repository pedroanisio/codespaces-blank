#!/usr/bin/env python3
"""Convert anatomical bone meshes into renderer-ready GLBs.

Supported sources:
  1. Local OBJ or STL files exported from BodyParts3D / Wikimedia Commons.
  2. Procedural placeholder generation for bones that do not yet have assets.

Pipeline:
  mesh → normalize → optional bilateral split → glTF 2.0 binary (.glb)
  - Recentered to bone centroid (local origin)
  - Scaled to cm
  - Y-up, right-handed
  - LOD 0 target: 5,000 triangles
  - LOD 1 target: 1,500 triangles

Usage:
  python3 tools/acquire_meshes.py --source-dir raw_meshes/ --output-dir public/assets/bones/
  python3 tools/acquire_meshes.py --placeholders
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import numpy as np
    import trimesh
except ImportError:
    print("ERROR: requires 'pip install trimesh pyglet numpy'", file=sys.stderr)
    sys.exit(1)


MESH_MAP = Path(__file__).parent / "bone_mesh_map.json"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "public" / "assets" / "bones"
LOD_TARGETS = {0: 5000, 1: 1500}
SUPPORTED_EXTENSIONS = (".obj", ".stl")

_BODY_PARTS3D_NAME_MAP: dict[str, str | tuple[str, str]] = {
    "frontal bone": "Frontal bone",
    "parietal bone": ("Parietal bone (R)", "Parietal bone (L)"),
    "temporal bone": ("Temporal bone (R)", "Temporal bone (L)"),
    "occipital bone": "Occipital bone",
    "sphenoid bone": "Sphenoid bone",
    "ethmoid bone": "Ethmoid bone",
    "maxilla": ("Maxilla (R)", "Maxilla (L)"),
    "palatine bone": ("Palatine bone (R)", "Palatine bone (L)"),
    "zygomatic bone": ("Zygomatic bone (R)", "Zygomatic bone (L)"),
    "nasal bone": ("Nasal bone (R)", "Nasal bone (L)"),
    "lacrimal bone": ("Lacrimal bone (R)", "Lacrimal bone (L)"),
    "inferior nasal concha": ("Inferior nasal concha (R)", "Inferior nasal concha (L)"),
    "vomer": "Vomer",
    "mandible": "Mandible",
    "hyoid": "Hyoid",
}


def load_mesh_map() -> dict[str, str]:
    """Return {bone_name: filename} from bone_mesh_map.json."""
    with open(MESH_MAP) as f:
        data = json.load(f)
    mapping: dict[str, str] = {}
    for section in ["bones", "vertebrae_pattern", "ribs_pattern"]:
        for name, info in data.get(section, {}).items():
            if isinstance(info, dict) and "file" in info:
                mapping[name] = info["file"]
    return mapping


def _normalize_source_key(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"bodyparts3d", " ", stem)
    stem = re.sub(r"\bfj\d+\b", " ", stem)
    stem = re.sub(r"\bbp\d+\b", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem


def _resolve_source_targets(source_name: str, mesh_map: dict[str, str]) -> list[tuple[str, str]]:
    normalized = _normalize_source_key(source_name)
    direct_matches = [
        (bone_name, filename)
        for bone_name, filename in mesh_map.items()
        if normalized == bone_name.lower()
    ]
    if direct_matches:
        return direct_matches

    for token, bones in _BODY_PARTS3D_NAME_MAP.items():
        if token not in normalized:
            continue
        if isinstance(bones, tuple):
            return [(bone_name, mesh_map[bone_name]) for bone_name in bones if bone_name in mesh_map]
        if bones in mesh_map:
            return [(bones, mesh_map[bones])]
    return []


def _load_triangle_mesh(path: Path) -> trimesh.Trimesh | None:
    try:
        loaded = trimesh.load(str(path), force="mesh")
    except Exception as exc:
        print(f"  SKIP {path.name}: {exc}")
        return None
    if isinstance(loaded, trimesh.Trimesh):
        return loaded
    print(f"  SKIP {path.name}: not a triangle mesh (got {type(loaded).__name__})")
    return None


def _normalize_mesh(mesh: trimesh.Trimesh) -> tuple[trimesh.Trimesh, dict]:
    normalized = mesh.copy()
    centroid = normalized.centroid.copy()
    normalized.vertices -= centroid

    unit_scale = 1.0
    extent = float(normalized.bounding_box.extents.max())
    if extent > 100:
        unit_scale = 0.1
        normalized.vertices *= unit_scale
    elif extent < 1:
        unit_scale = 100.0
        normalized.vertices *= unit_scale

    bounds = normalized.bounds
    y_range = bounds[1][1] - bounds[0][1]
    z_range = bounds[1][2] - bounds[0][2]
    rotated_x_deg = 0
    if z_range > y_range * 1.5:
        rot = trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0])
        normalized.apply_transform(rot)
        rotated_x_deg = -90

    centroid_cm = np.asarray(centroid, dtype=float) * unit_scale
    if rotated_x_deg:
        rot3 = trimesh.transformations.rotation_matrix(np.radians(rotated_x_deg), [1, 0, 0])[:3, :3]
        centroid_cm = rot3 @ centroid_cm

    normalization = {
        "centroidOffsetCm": centroid_cm.tolist(),
        "unitScale": unit_scale,
        "rotatedXDeg": rotated_x_deg,
    }
    return normalized, normalization


def _export_mesh_with_lods(mesh: trimesh.Trimesh, output_dir: Path, filename: str) -> dict:
    out_path = output_dir / filename
    lods_info = []

    for lod_level, target_faces in sorted(LOD_TARGETS.items()):
        if mesh.faces.shape[0] > target_faces:
            try:
                decimated = mesh.simplify_quadric_decimation(target_faces)
            except Exception:
                decimated = mesh.copy()
        else:
            decimated = mesh.copy()

        target_path = out_path if lod_level == 0 else output_dir / filename.replace(".glb", f"_lod{lod_level}.glb")
        decimated.export(str(target_path), file_type="glb")
        lods_info.append({
            "level": lod_level,
            "triangles": int(decimated.faces.shape[0]),
            "vertices": int(decimated.vertices.shape[0]),
        })

    with open(out_path, "rb") as f:
        content_hash = hashlib.sha256(f.read()).hexdigest()

    return {
        "file": filename,
        "hash": content_hash,
        "byteSize": out_path.stat().st_size,
        "lods": lods_info,
    }


def _split_components_fallback(mesh: trimesh.Trimesh) -> list[trimesh.Trimesh]:
    vertex_count = len(mesh.vertices)
    adjacency: list[set[int]] = [set() for _ in range(vertex_count)]
    for a, b, c in np.asarray(mesh.faces, dtype=int):
        adjacency[a].update((b, c))
        adjacency[b].update((a, c))
        adjacency[c].update((a, b))

    components: list[list[int]] = []
    seen: set[int] = set()
    for start in range(vertex_count):
        if start in seen:
            continue
        stack = [start]
        group: list[int] = []
        seen.add(start)
        while stack:
            current = stack.pop()
            group.append(current)
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        components.append(group)

    meshes: list[trimesh.Trimesh] = []
    for group in components:
        mask = np.isin(mesh.faces, np.asarray(group)).all(axis=1)
        if not mask.any():
            continue
        submesh = mesh.submesh([mask], append=True)
        if len(submesh.vertices) > 0:
            meshes.append(submesh)
    return meshes


def _split_bilateral_mesh(mesh: trimesh.Trimesh) -> dict[str, trimesh.Trimesh]:
    try:
        components = [c for c in mesh.split(only_watertight=False) if len(c.vertices) > 0]
    except ImportError:
        components = _split_components_fallback(mesh)
    if len(components) < 2:
        raise ValueError("bilateral split requires at least two disconnected components")

    components = sorted(components, key=lambda item: float(item.centroid[0]))
    right = trimesh.util.concatenate(components[: len(components) // 2])
    left = trimesh.util.concatenate(components[len(components) // 2 :])
    return {"R": right, "L": left}


def process_directory(source_dir: Path, output_dir: Path) -> None:
    """Process OBJ/STL files in source_dir into GLBs + manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    mesh_map = load_mesh_map()
    manifest: dict[str, dict] = {}
    mesh_files = sorted(
        path for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not mesh_files:
        print(f"No OBJ/STL files found in {source_dir}")
        return

    print(f"Found {len(mesh_files)} mesh files in {source_dir}")
    for mesh_path in mesh_files:
        targets = _resolve_source_targets(mesh_path.name, mesh_map)
        if not targets:
            print(f"  SKIP {mesh_path.name}: no bone mapping")
            continue

        mesh = _load_triangle_mesh(mesh_path)
        if mesh is None:
            continue

        print(f"  Processing: {mesh_path.name}")
        if len(targets) == 1:
            bone_name, filename = targets[0]
            normalized, normalization = _normalize_mesh(mesh)
            result = _export_mesh_with_lods(normalized, output_dir, filename)
            result["normalization"] = normalization
            manifest[bone_name] = result
            print(f"    ✓ {filename}: {result['lods'][0]['triangles']} tris")
            continue

        try:
            split_meshes = _split_bilateral_mesh(mesh)
        except ValueError as exc:
            print(f"    SKIP bilateral split: {exc}")
            continue

        for bone_name, filename in targets:
            side = "R" if "(R)" in bone_name else "L"
            normalized, normalization = _normalize_mesh(split_meshes[side])
            result = _export_mesh_with_lods(normalized, output_dir, filename)
            result["normalization"] = normalization
            manifest[bone_name] = result
            print(f"    ✓ {filename}: {result['lods'][0]['triangles']} tris")

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written: {manifest_path} ({len(manifest)} bones)")


def generate_placeholder_meshes(output_dir: Path) -> None:
    """Generate simple procedural meshes as placeholders until real data is available."""
    output_dir.mkdir(parents=True, exist_ok=True)
    mesh_map = load_mesh_map()
    manifest: dict[str, dict] = {}
    _BONE_DIMS: dict[str, tuple[float, float, float, str]] = {
        "femur_r": (45, 3.2, 2.8, "long_major"),
        "femur_l": (45, 3.2, 2.8, "long_major"),
        "humerus_r": (36, 2.2, 2.0, "long_major"),
        "humerus_l": (36, 2.2, 2.0, "long_major"),
        "tibia_r": (40, 2.8, 2.4, "long_major"),
        "tibia_l": (40, 2.8, 2.4, "long_major"),
        "fibula_r": (38, 1.2, 1.0, "long_thin"),
        "fibula_l": (38, 1.2, 1.0, "long_thin"),
        "radius_r": (26, 1.6, 1.4, "long_medium"),
        "radius_l": (26, 1.6, 1.4, "long_medium"),
        "ulna_r": (28, 1.5, 1.3, "long_medium"),
        "ulna_l": (28, 1.5, 1.3, "long_medium"),
        "hip_bone_r": (18, 14, 8, "pelvis"),
        "hip_bone_l": (18, 14, 8, "pelvis"),
        "sacrum": (12, 10, 3, "wedge"),
        "scapula_r": (15, 10, 1, "blade"),
        "scapula_l": (15, 10, 1, "blade"),
        "sternum": (17, 5, 1.5, "plate"),
        "frontal_bone": (12, 12, 0.7, "dome"),
        "parietal_bone_r": (12, 11, 0.5, "dome"),
        "parietal_bone_l": (12, 11, 0.5, "dome"),
        "occipital_bone": (10, 10, 0.8, "dome"),
        "mandible": (10, 12, 3, "jaw"),
        "patella_r": (4, 4.5, 2, "disc"),
        "patella_l": (4, 4.5, 2, "disc"),
        "calcaneus_r": (8, 4, 4.5, "block"),
        "calcaneus_l": (8, 4, 4.5, "block"),
        "talus_r": (6, 4, 3, "dome"),
        "talus_l": (6, 4, 3, "dome"),
        "clavicle_r": (15, 1.3, 1.1, "long_thin"),
        "clavicle_l": (15, 1.3, 1.1, "long_thin"),
    }

    for bone_name, filename in mesh_map.items():
        dims = _BONE_DIMS.get(filename.replace(".glb", ""))
        if not dims:
            continue
        l, w, d, hint = dims
        mesh = _make_placeholder_mesh(l, w, d, hint)
        if mesh is None:
            continue
        result = _export_mesh_with_lods(mesh, output_dir, filename)
        result["source"] = "procedural_placeholder"
        manifest[bone_name] = result
        print(f"  ✓ {filename}: {result['lods'][0]['triangles']} tris")

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nPlaceholder manifest: {manifest_path} ({len(manifest)} bones)")


def _make_placeholder_mesh(l: float, w: float, d: float, hint: str) -> trimesh.Trimesh | None:
    if hint == "long_major":
        return _lathe_bone(l, w, d, segments=32, profile_points=12)
    if hint == "long_medium":
        return _lathe_bone(l, w, d, segments=24, profile_points=10)
    if hint == "long_thin":
        return _lathe_bone(l, w * 1.2, d * 1.2, segments=16, profile_points=8)
    if hint == "pelvis":
        return _sculpted_pelvis(l, w, d)
    if hint == "dome":
        return _dome_mesh(l, w, d)
    if hint == "blade":
        return _blade_mesh(l, w, d)
    if hint == "plate":
        return _plate_mesh(l, w, d)
    if hint == "jaw":
        return _jaw_mesh(l, w, d)
    if hint == "wedge":
        return _wedge_mesh(l, w, d)
    if hint == "disc":
        return trimesh.creation.capsule(height=max(0.1, l - d), radius=max(w, d) / 2, count=[16, 8])
    if hint == "block":
        return trimesh.creation.box(extents=[w, l, d])
    return None


def _lathe_bone(l: float, w: float, d: float, segments: int = 24, profile_points: int = 10) -> trimesh.Trimesh:
    half = l / 2
    shaft_r = (w + d) / 4
    head_r = shaft_r * 1.5
    condyle_r = shaft_r * 1.35
    ts = np.linspace(0, 1, profile_points)
    radii = []
    ys = []
    for t in ts:
        y = -half + t * l
        end_prox = np.exp(-((t * 4) ** 2))
        end_dist = np.exp(-(((1 - t) * 4) ** 2))
        r = shaft_r + (head_r - shaft_r) * end_prox + (condyle_r - shaft_r) * end_dist
        radii.append(max(0.05, r))
        ys.append(y)
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    vertices = []
    for r, y in zip(radii, ys):
        for a in angles:
            x = r * np.cos(a) * (w / max(w, d))
            z = r * np.sin(a) * (d / max(w, d))
            vertices.append([x, y, z])
    vertices.append([0, -half, 0])
    vertices.append([0, half, 0])
    verts = np.array(vertices)
    faces = []
    rows = profile_points
    cols = segments
    for i in range(rows - 1):
        for j in range(cols):
            a = i * cols + j
            b = i * cols + (j + 1) % cols
            c = (i + 1) * cols + j
            dd = (i + 1) * cols + (j + 1) % cols
            faces.append([a, c, b])
            faces.append([b, c, dd])
    bottom_center = len(verts) - 2
    for j in range(cols):
        faces.append([bottom_center, j, (j + 1) % cols])
    top_center = len(verts) - 1
    top_row = (rows - 1) * cols
    for j in range(cols):
        faces.append([top_center, top_row + (j + 1) % cols, top_row + j])
    return trimesh.Trimesh(vertices=verts, faces=np.array(faces))


def _dome_mesh(l: float, w: float, d: float) -> trimesh.Trimesh:
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
    mask = sphere.vertices[:, 1] >= -0.1
    sphere.update_vertices(mask)
    sphere.vertices[:, 0] *= w / 2
    sphere.vertices[:, 1] *= l / 2
    sphere.vertices[:, 2] *= max(d, w * 0.25)
    return sphere


def _blade_mesh(l: float, w: float, d: float) -> trimesh.Trimesh:
    pts = np.array([
        [-w * 0.4, -l * 0.45, 0],
        [w * 0.4, -l * 0.45, 0],
        [w * 0.1, l * 0.45, 0],
        [-w * 0.4, -l * 0.45, d],
        [w * 0.4, -l * 0.45, d],
        [w * 0.1, l * 0.45, d],
    ])
    faces = np.array([
        [0, 1, 2], [3, 5, 4],
        [0, 3, 1], [1, 3, 4],
        [1, 4, 2], [2, 4, 5],
        [0, 2, 3], [3, 2, 5],
    ])
    return trimesh.Trimesh(vertices=pts, faces=faces)


def _plate_mesh(l: float, w: float, d: float) -> trimesh.Trimesh:
    return trimesh.creation.box(extents=[w, l, d])


def _jaw_mesh(l: float, w: float, d: float) -> trimesh.Trimesh:
    body_box = trimesh.creation.box(extents=[w * 0.8, l * 0.3, d * 0.6])
    ramus_r = trimesh.creation.box(extents=[d * 0.4, l * 0.6, d * 0.4])
    ramus_r.vertices[:, 0] += w * 0.35
    ramus_r.vertices[:, 1] += l * 0.2
    ramus_l = trimesh.creation.box(extents=[d * 0.4, l * 0.6, d * 0.4])
    ramus_l.vertices[:, 0] -= w * 0.35
    ramus_l.vertices[:, 1] += l * 0.2
    return trimesh.util.concatenate([body_box, ramus_r, ramus_l])


def _sculpted_pelvis(l: float, w: float, d: float) -> trimesh.Trimesh:
    ilium = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
    ilium.vertices[:, 0] *= w * 0.35
    ilium.vertices[:, 1] *= l * 0.45
    ilium.vertices[:, 2] *= d * 0.4
    ilium.vertices[:, 1] += l * 0.1
    ischium = trimesh.creation.box(extents=[w * 0.35, l * 0.3, d * 0.35])
    ischium.vertices[:, 1] -= l * 0.3
    return trimesh.util.concatenate([ilium, ischium])


def _wedge_mesh(l: float, w: float, d: float) -> trimesh.Trimesh:
    return trimesh.creation.box(extents=[w, l, d])


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire and convert anatomical bone meshes")
    parser.add_argument("--source-dir", type=str, help="Directory with OBJ/STL bone meshes")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--placeholders", action="store_true",
                        help="Generate procedural placeholder meshes (no external data needed)")
    args = parser.parse_args()

    output = Path(args.output_dir)
    if args.placeholders:
        generate_placeholder_meshes(output)
    elif args.source_dir:
        process_directory(Path(args.source_dir), output)
    else:
        print("Usage:")
        print("  --placeholders    Generate procedural placeholder GLBs")
        print("  --source-dir DIR  Convert OBJ/STL files from DIR to GLB")
        sys.exit(1)


if __name__ == "__main__":
    main()
