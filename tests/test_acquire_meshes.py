import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "session-3" / "human-controller" / "tools" / "acquire_meshes.py"

spec = importlib.util.spec_from_file_location("acquire_meshes", MODULE_PATH)
acquire_meshes = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(acquire_meshes)


@pytest.mark.skipif(acquire_meshes.trimesh is None, reason="trimesh unavailable")
def test_resolve_source_targets_supports_bodyparts3d_skull_names():
    mesh_map = acquire_meshes.load_mesh_map()

    targets = acquire_meshes._resolve_source_targets(
        "BodyParts3D FJ6385 FJ6472 Parietal bone.stl",
        mesh_map,
    )

    assert [bone_name for bone_name, _ in targets] == [
        "Parietal bone (R)",
        "Parietal bone (L)",
    ]


@pytest.mark.skipif(acquire_meshes.trimesh is None, reason="trimesh unavailable")
def test_split_bilateral_mesh_assigns_right_and_left_by_x_centroid():
    right = acquire_meshes.trimesh.creation.box(extents=[1, 1, 1])
    right.vertices[:, 0] -= 5.0
    left = acquire_meshes.trimesh.creation.box(extents=[1, 1, 1])
    left.vertices[:, 0] += 5.0
    mesh = acquire_meshes.trimesh.util.concatenate([right, left])

    split = acquire_meshes._split_bilateral_mesh(mesh)

    assert split["R"].centroid[0] < 0
    assert split["L"].centroid[0] > 0


@pytest.mark.skipif(acquire_meshes.trimesh is None, reason="trimesh unavailable")
def test_process_directory_handles_stl_and_bilateral_skull_file(tmp_path):
    source_dir = tmp_path / "src"
    output_dir = tmp_path / "out"
    source_dir.mkdir()

    right = acquire_meshes.trimesh.creation.box(extents=[1, 1, 1])
    right.vertices[:, 0] -= 4.0
    left = acquire_meshes.trimesh.creation.box(extents=[1, 1, 1])
    left.vertices[:, 0] += 4.0
    bilateral = acquire_meshes.trimesh.util.concatenate([right, left])
    bilateral.export(source_dir / "BodyParts3D FJ6385 FJ6472 Parietal bone.stl")

    acquire_meshes.process_directory(source_dir, output_dir)

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert "Parietal bone (R)" in manifest
    assert "Parietal bone (L)" in manifest
    assert (output_dir / "parietal_bone_r.glb").exists()
    assert (output_dir / "parietal_bone_l.glb").exists()
    assert manifest["Parietal bone (R)"]["lods"][0]["triangles"] > 0
    assert "normalization" in manifest["Parietal bone (R)"]
    assert "centroidOffsetCm" in manifest["Parietal bone (R)"]["normalization"]


@pytest.mark.skipif(acquire_meshes.trimesh is None, reason="trimesh unavailable")
def test_dome_mesh_cuts_along_y_axis():
    dome = acquire_meshes._dome_mesh(12, 12, 1)
    assert dome.vertices[:, 1].min() >= -0.7
