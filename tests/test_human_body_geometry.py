import json
import math
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

    frontal_flat = geometry._csg_flat_bone(10, 10, 1, "Frontal bone")
    assert frontal_flat["operation"] == "union"
    assert len(frontal_flat["children"]) >= 5
    temporal_flat = geometry._csg_flat_bone(6, 5, 1, "Temporal bone (R)")
    assert temporal_flat["operation"] == "union"
    assert geometry._csg_flat_bone(10, 10, 1, "Scapula (R)")["operation"] == "union"
    assert geometry._csg_flat_bone(10, 5, 1, "Sternum")["operation"] == "union"
    rib_1 = geometry._csg_flat_bone(10, 2, 1, "Rib 1 (R)")
    rib_7 = geometry._csg_flat_bone(14, 2, 1, "Rib 7 (R)")
    rib_12 = geometry._csg_flat_bone(8, 2, 1, "Rib 12 (R)")
    assert rib_1["operation"] == "union"
    assert len(rib_1["children"]) == 2
    assert len(rib_7["children"]) == 3
    assert len(rib_12["children"]) == 2
    assert geometry._csg_flat_bone(2, 1, 0.1, "Nasal bone (R)")["primitive"]["primitiveType"] == "box"
    assert geometry._csg_flat_bone(5, 5, 2, "Flat bone")["primitive"]["primitiveType"] == "box"

    t1 = geometry._csg_irregular_bone(4, 4, 4, "T1 vertebra")
    c3 = geometry._csg_irregular_bone(4, 4, 4, "C3 vertebra")
    c7 = geometry._csg_irregular_bone(4, 4, 4, "C7 vertebra")
    l5 = geometry._csg_irregular_bone(4, 4, 4, "L5 vertebra")
    atlas = geometry._csg_irregular_bone(4, 4, 4, "C1 atlas")
    axis = geometry._csg_irregular_bone(4, 4, 4, "C2 axis")
    hip = geometry._csg_irregular_bone(10, 8, 6, "Hip bone (R)")
    assert t1["operation"] == "union"
    assert c3["operation"] == "union"
    assert c7["operation"] == "union"
    assert l5["operation"] == "union"
    assert atlas["operation"] == "union"
    assert axis["operation"] == "union"
    assert hip["operation"] == "union"
    assert atlas["children"][0]["primitive"]["primitiveType"] == "capsule"
    assert all(child["primitive"]["primitiveType"] != "sphere" for child in atlas["children"] if child["nodeType"] == "primitive")
    assert axis["children"][1]["primitive"]["primitiveType"] == "capsule"
    assert any(child["primitive"]["primitiveType"] == "sphere" for child in t1["children"] if child["nodeType"] == "primitive")
    assert c7["children"][-1]["primitive"]["primitiveType"] == "cylinder"
    assert l5["children"][0]["primitive"]["radiusTop"] > c3["children"][0]["primitive"]["radiusTop"]
    assert any(child["nodeType"] == "operation" and child["operation"] == "subtract" for child in hip["children"])
    assert len(hip["children"]) >= 6
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
    assert normals[:3] == [0.0, 1.0, 0.0]

    lathe = geometry._lathe_mesh([(0.5, -1.0), (1.0, 1.0)], 6)
    sphere = geometry._uv_sphere_mesh(1.0, 2.0, 3.0, 6, 4)
    assert len(lathe[0]) > 0 and len(sphere[0]) > 0
    assert geometry._name_perturb("Femur", 1) == geometry._name_perturb("Femur", 1)

    assert geometry._mesh_for_bone("Femur (R)", "long", 40, 4, 4, 8, 6)[0]
    assert geometry._mesh_for_bone("Frontal bone", "flat", 10, 8, 1, 8, 6)[0]
    assert geometry._mesh_for_bone("Scapula (R)", "flat", 10, 8, 1, 8, 6)[0]
    rib_1_mesh = geometry._mesh_for_bone("Rib 1 (R)", "flat", 10, 2, 1, 8, 6)
    rib_7_mesh = geometry._mesh_for_bone("Rib 7 (R)", "flat", 14, 2, 1, 8, 6)
    rib_12_mesh = geometry._mesh_for_bone("Rib 12 (R)", "flat", 8, 2, 1, 8, 6)
    assert geometry._mesh_for_bone("Scaphoid (R)", "short", 3, 3, 3, 8, 6)[0]
    assert geometry._mesh_for_bone("Patella (R)", "sesamoid", 3, 3, 3, 8, 6)[0]
    assert geometry._mesh_for_bone("Mandible", "irregular", 10, 8, 4, 8, 6)[0]
    atlas_mesh = geometry._mesh_for_bone("C1 atlas", "irregular", 4, 4, 4, 8, 6)
    axis_mesh = geometry._mesh_for_bone("C2 axis", "irregular", 4, 4, 4, 8, 6)
    c3_mesh = geometry._mesh_for_bone("C3 vertebra", "irregular", 4, 4, 4, 8, 6)
    c7_mesh = geometry._mesh_for_bone("C7 vertebra", "irregular", 4, 4, 4, 8, 6)
    t1_mesh = geometry._mesh_for_bone("T1 vertebra", "irregular", 4, 4, 4, 8, 6)
    l5_mesh = geometry._mesh_for_bone("L5 vertebra", "irregular", 4, 4, 4, 8, 6)
    hip_mesh = geometry._mesh_for_bone("Hip bone (R)", "irregular", 10, 8, 6, 8, 6)
    assert len(rib_1_mesh[0]) != len(rib_7_mesh[0]) or rib_1_mesh[0] != rib_7_mesh[0]
    assert len(rib_12_mesh[0]) == len(rib_1_mesh[0])
    assert len(atlas_mesh[0]) > len(axis_mesh[0])
    assert len(c7_mesh[0]) > len(c3_mesh[0])
    assert len(t1_mesh[0]) > len(c3_mesh[0])
    assert max(l5_mesh[0][1::3]) > max(c3_mesh[0][1::3])
    assert len(hip_mesh[0]) > len(axis_mesh[0])

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
    assert all(g["isManifold"] is False for g in indexed)
    indexed_by_bone = {g["boneId"]: g for g in indexed}
    skull_landmark_names = {
        lm["name"]
        for lm in indexed_by_bone[reg.bone_ids[shared.B_SPHENOID]].get("landmarks", [])
    }
    assert "sella_turcica" in skull_landmark_names
    menton = next(
        lm
        for lm in indexed_by_bone[reg.bone_ids[shared.B_MANDIBLE]].get("landmarks", [])
        if lm["name"] == "menton"
    )
    menton_normal = menton["surfaceNormal"]
    assert math.isclose(
        math.sqrt(
            menton_normal["x"] ** 2 + menton_normal["y"] ** 2 + menton_normal["z"] ** 2
        ),
        1.0,
        rel_tol=1e-6,
    )
    frontal_csg = parametric[shared.B_FRONTAL]["csgTree"]
    assert frontal_csg["operation"] == "union"
    assert len(frontal_csg["children"]) >= 5


def test_public_geometry_exports_hide_private_helpers():
    assert "_mesh_for_bone" not in geometry.__all__
    assert "gen_bone_geometries" in geometry.__all__


def test_skeleton_helpers_validate_cycles_and_names():
    assert skeleton._cervical_name(1) == "C1 atlas"
    assert skeleton._cervical_name(2) == "C2 axis"
    assert skeleton._cervical_name(7) == "C7 vertebra"

    acyclic = [
        skeleton.BoneDef("root", "flat", "axial", None, 1, 1, 1, 1, (0, 0, 0)),
        skeleton.BoneDef("child", "flat", "axial", 0, 1, 1, 1, 1, (0, 0, 0)),
    ]
    skeleton._validate_parent_graph(acyclic)

    cyclic = [
        skeleton.BoneDef("a", "flat", "axial", 1, 1, 1, 1, 1, (0, 0, 0)),
        skeleton.BoneDef("b", "flat", "axial", 0, 1, 1, 1, 1, (0, 0, 0)),
    ]
    try:
        skeleton._validate_parent_graph(cyclic)
        raise AssertionError("Expected cycle validation to fail")
    except ValueError as exc:
        assert "parent cycle" in str(exc)
