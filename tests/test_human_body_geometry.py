import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from human_body import geometry, shared, skeleton


def _registry_with_bones():
    reg = shared.Reg()
    skeleton.gen_skeleton(reg, 75, 175)
    return reg


def test_csg_builder_branches():
    assert geometry._csg_long_bone(40, 4, 4, "Femur (R)")["nodeType"] == "operation"
    assert geometry._csg_long_bone(35, 4, 4, "Humerus (R)")["nodeType"] == "operation"
    assert geometry._csg_long_bone(32, 4, 4, "Tibia (R)")["nodeType"] == "operation"
    assert geometry._csg_long_bone(30, 4, 4, "Ulna (R)")["nodeType"] == "operation"
    assert geometry._csg_long_bone(10, 2, 2, "Metacarpal I (R)")["nodeType"] == "operation"
    assert geometry._csg_long_bone(3, 1, 1, "Thumb distal phalanx (R)")["nodeType"] == "primitive"

    assert geometry._csg_flat_bone(10, 10, 1, "Frontal bone")["primitive"]["primitiveType"] == "ellipsoid"
    temporal_flat = geometry._csg_flat_bone(6, 5, 1, "Temporal bone (R)")
    assert temporal_flat["operation"] == "union"
    assert geometry._csg_flat_bone(10, 10, 1, "Scapula (R)")["operation"] == "union"
    assert geometry._csg_flat_bone(10, 5, 1, "Sternum")["operation"] == "union"
    assert geometry._csg_flat_bone(10, 2, 1, "Rib 1 (R)")["operation"] == "union"
    assert geometry._csg_flat_bone(2, 1, 0.1, "Nasal bone (R)")["primitive"]["primitiveType"] == "box"
    assert geometry._csg_flat_bone(5, 5, 2, "Flat bone")["primitive"]["primitiveType"] == "box"

    assert geometry._csg_irregular_bone(4, 4, 4, "T1 vertebra")["operation"] == "union"
    assert geometry._csg_irregular_bone(4, 4, 4, "C1 atlas")["operation"] == "union"
    assert geometry._csg_irregular_bone(10, 8, 6, "Hip bone (R)")["operation"] == "union"
    assert geometry._csg_irregular_bone(10, 8, 6, "Sacrum")["operation"] == "union"
    assert geometry._csg_irregular_bone(3, 2, 2, "Coccyx")["primitive"]["primitiveType"] == "cylinder"
    mandible = geometry._csg_irregular_bone(10, 8, 4, "Mandible")
    assert mandible["operation"] == "union"
    assert len(mandible["children"]) >= 5
    sphenoid = geometry._csg_irregular_bone(5, 5, 5, "Sphenoid bone")
    assert sphenoid["operation"] == "union"
    assert len(sphenoid["children"]) >= 3
    assert geometry._csg_irregular_bone(5, 5, 5, "Hyoid")["operation"] == "union"
    assert geometry._csg_irregular_bone(1, 1, 1, "Malleus (R)")["primitive"]["primitiveType"] == "ellipsoid"
    maxilla = geometry._csg_irregular_bone(3, 3, 3, "Maxilla (R)")
    assert maxilla["operation"] == "union"
    zygomatic = geometry._csg_irregular_bone(3, 3, 3, "Zygomatic bone (R)")
    assert zygomatic["operation"] == "union"
    assert geometry._csg_irregular_bone(3, 3, 3, "Random irregular")["primitive"]["primitiveType"] == "ellipsoid"

    assert geometry._csg_short_bone(8, 4, 4, "Calcaneus (R)")["operation"] == "union"
    assert geometry._csg_short_bone(6, 4, 3, "Talus (R)")["operation"] == "union"
    assert geometry._csg_short_bone(3, 3, 3, "Scaphoid (R)")["primitive"]["primitiveType"] == "ellipsoid"
    assert geometry._csg_sesamoid_bone(4, 4, 2, "Patella (R)")["operation"] == "union"


def test_mesh_and_skull_helpers_cover_branches():
    assert geometry._round_list([1.23456789]) == [1.234568]
    assert geometry._is_skull_bone("Frontal bone", "axial_cranium") is True
    assert geometry._is_skull_bone("Femur", "appendicular_lower") is False
    assert geometry._deform_positions([1.0, 2.0, 3.0], lambda x, y, z: (x + 1, y + 1, z + 1)) == [2.0, 3.0, 4.0]

    flat_cases = [
        "Frontal bone",
        "Parietal bone (R)",
        "Occipital bone",
        "Temporal bone (L)",
        "Zygomatic bone (R)",
        "Maxilla (L)",
        "Mandible",
        "Sphenoid bone",
        "Ethmoid bone",
        "Nasal bone (R)",
        "Vomer",
    ]
    for name in flat_cases:
        positions, indices, uvs = geometry._skull_mesh_for_bone(name, "flat", 10, 8, 1, 8, 6)
        assert positions and indices and uvs

    sample_positions = [
        -2.0, 2.0, 2.0,
        2.0, 2.0, 2.0,
        0.0, 1.0, 2.0,
        -2.0, -2.0, 2.0,
        2.0, -2.0, 2.0,
        0.0, -1.0, 2.0,
        -2.0, 0.0, -2.0,
        2.0, 0.0, -2.0,
        0.0, 2.0, -2.0,
    ]
    assert geometry._select_vertices(sample_positions, lambda x, y, z: z > 0) == [0, 1, 2, 3, 4, 5]
    assert geometry._skull_surface_regions("Frontal bone", sample_positions)
    assert geometry._skull_surface_regions("Parietal bone (R)", sample_positions)
    assert geometry._skull_surface_regions("Occipital bone", sample_positions)
    assert geometry._skull_surface_regions("Temporal bone (R)", sample_positions)
    assert geometry._skull_surface_regions("Zygomatic bone (R)", sample_positions)
    assert geometry._skull_surface_regions("Mandible", sample_positions)

    normals = geometry._mesh_vertex_normals([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0], [0, 1, 2])
    assert len(normals) == 9

    lathe = geometry._lathe_mesh([(0.5, -1.0), (1.0, 1.0)], 6)
    sphere = geometry._uv_sphere_mesh(1.0, 2.0, 3.0, 6, 4)
    assert len(lathe[0]) > 0 and len(sphere[0]) > 0
    assert geometry._name_perturb("Femur", 1) == geometry._name_perturb("Femur", 1)

    assert geometry._mesh_for_bone("Femur (R)", "long", 40, 4, 4, 8, 6)[0]
    assert geometry._mesh_for_bone("Frontal bone", "flat", 10, 8, 1, 8, 6)[0]
    assert geometry._mesh_for_bone("Scapula (R)", "flat", 10, 8, 1, 8, 6)[0]
    assert geometry._mesh_for_bone("Scaphoid (R)", "short", 3, 3, 3, 8, 6)[0]
    assert geometry._mesh_for_bone("Patella (R)", "sesamoid", 3, 3, 3, 8, 6)[0]
    assert geometry._mesh_for_bone("Mandible", "irregular", 10, 8, 4, 8, 6)[0]

    lod = geometry._lod_from_mesh(0, [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0], [0, 1, 2], [0.0, 0.0, 1.0, 0.0, 0.0, 1.0])
    assert lod["triangleCount"] == 1


def test_geometry_loading_and_generation_variants(tmp_path, monkeypatch):
    reg = _registry_with_bones()

    manifest_dir = tmp_path / "assets"
    manifest_dir.mkdir()
    (manifest_dir / "manifest.json").write_text(json.dumps({
        "Frontal bone": {
            "hash": "abc123",
            "byteSize": 42,
            "lods": [{"level": 0, "triangles": 100}, {"level": 1, "triangles": 50}],
        }
    }))

    assert geometry._load_mesh_manifest(str(manifest_dir))["Frontal bone"]["hash"] == "abc123"
    assert geometry._load_mesh_manifest(str(tmp_path / "missing")) == {}

    monkeypatch.setattr(geometry, "_load_bone_mesh_map", lambda: {"Frontal bone": "frontal.glb"})
    external = geometry.gen_bone_geometries(reg, assets_dir=str(manifest_dir))
    frontal = next(g for g in external if g["boneId"] == reg.bone_ids[shared.B_FRONTAL])
    assert frontal["geometryType"] == "external_asset"
    assert frontal["lodVariants"][0]["uri"].endswith("_lod1.glb")

    indexed = geometry.gen_bone_geometries(reg, geometry_format="indexed_mesh")
    parametric = geometry.gen_bone_geometries(reg, geometry_format="parametric_csg")
    assert len(indexed) == 206
    assert len(parametric) == 206
    assert any(g["geometryType"] == "indexed_mesh" for g in indexed)
    assert all(g["geometryType"] == "parametric_csg" for g in parametric)
    assert any("surfaceRegions" in g for g in indexed)
    assert any("landmarks" in g for g in indexed)
    indexed_by_bone = {g["boneId"]: g for g in indexed}
    skull_landmark_names = {
        lm["name"]
        for lm in indexed_by_bone[reg.bone_ids[shared.B_SPHENOID]].get("landmarks", [])
    }
    assert "sella_turcica" in skull_landmark_names
    frontal_csg = parametric[shared.B_FRONTAL]["csgTree"]
    assert frontal_csg["operation"] == "union"
    assert len(frontal_csg["children"]) >= 5
