from ..shared import *
from ..skeleton import *
from .csg import *
from .mesh import *


def _load_mesh_manifest(assets_dir: str | None = None) -> dict[str, dict]:
    """Load the mesh manifest from the assets directory if it exists."""
    if assets_dir:
        manifest_path = Path(assets_dir) / "manifest.json"
    else:
        manifest_path = (Path(__file__).parent.parent.parent
                         / "session-3" / "human-controller" / "public" / "assets" / "bones" / "manifest.json")
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {}


def _load_bone_mesh_map() -> dict[str, str]:
    """Load bone name → filename mapping from bone_mesh_map.json."""
    map_path = (Path(__file__).parent.parent.parent
                / "session-3" / "human-controller" / "tools" / "bone_mesh_map.json")
    if not map_path.exists():
        return {}
    with open(map_path) as f:
        data = json.load(f)
    mapping: dict[str, str] = {}
    for section in ["bones", "vertebrae_pattern", "ribs_pattern"]:
        for name, info in data.get(section, {}).items():
            if isinstance(info, dict) and "file" in info:
                mapping[name] = info["file"]
    return mapping


def gen_bone_geometries(r: Reg, geometry_format: str = "indexed_mesh",
                        assets_dir: str | None = None,
                        asset_base_uri: str = "asset:///bones/") -> list[dict]:
    """Generate bone geometry for all 206 bones.

    Priority order:
      1. `external_asset` — if a GLB mesh file exists in the manifest
         (from BodyParts3D, Visible Human, or placeholder generation).
         This gives medical-grade bone shapes.
      2. `indexed_mesh` — procedurally generated inline triangle mesh.
         Watertight, UVs, normals, 2 LOD levels. Fallback.
      3. `parametric_csg` — compact CSG tree. Lightest weight.

    When `assets_dir` is provided (or manifest.json exists in the default
    location), bones with matching mesh files get `external_asset` geometry
    pointing to the GLB URI. Remaining bones get inline `indexed_mesh`.
    """
    _CSG_BUILDERS = {
        "long": _csg_long_bone,
        "flat": _csg_flat_bone,
        "irregular": _csg_irregular_bone,
        "short": _csg_short_bone,
        "sesamoid": _csg_sesamoid_bone,
    }

    # Load external mesh manifest and name→file mapping
    manifest = _load_mesh_manifest(assets_dir)
    mesh_map = _load_bone_mesh_map()

    geometries: list[dict] = []
    for i, (name, cls, _region, _parent, length, width, depth, _mass, _pos) in enumerate(BONE_DEFS):
        bone_id = r.bone_ids[i]

        # Try external_asset first
        mesh_filename = mesh_map.get(name)
        manifest_entry = manifest.get(name) if manifest else None

        if mesh_filename and manifest_entry:
            # External mesh available — use it
            geo: dict[str, Any] = {
                "geometryType": "external_asset",
                "id": uid(),
                "boneId": bone_id,
                "uri": f"{asset_base_uri}{mesh_filename}",
                "format": "glb",
                "contentHash": manifest_entry.get("hash", ""),
                "byteSize": manifest_entry.get("byteSize"),
                "coordinateSpace": {
                    "upAxis": "Y",
                    "units": "cm",
                    "handedness": "right",
                },
            }
            # LOD variants
            lod_entries = manifest_entry.get("lods", [])
            if len(lod_entries) > 1:
                lod_vars = []
                for le in lod_entries[1:]:
                    lod_level = le["level"]
                    lod_file = mesh_filename.replace(".glb", f"_lod{lod_level}.glb")
                    lod_vars.append({
                        "level": lod_level,
                        "uri": f"{asset_base_uri}{lod_file}",
                        "format": "glb",
                        "approximateTriangleCount": le.get("triangles"),
                    })
                geo["lodVariants"] = lod_vars
            geometries.append(geo)

        elif geometry_format == "parametric_csg":
            builder = _CSG_BUILDERS.get(cls, _csg_irregular_bone)
            csg_tree = builder(length, width, depth, name)
            geometries.append({
                "geometryType": "parametric_csg",
                "id": uid(),
                "boneId": bone_id,
                "csgTree": csg_tree,
                "collisionHull": "convex_hull" if cls in ("long", "irregular") else "aabb",
            })
        else:
            geometries.append(_indexed_mesh_geometry(name, cls, _region, bone_id, length, width, depth))

    # ── P0.4: Anatomical landmarks (ISB recommendations) ────────────────
    # Named points on bone surfaces required for reproducible joint
    # coordinate system definitions.
    #
    # Reference: Wu G et al., "ISB recommendation on definitions of joint
    # coordinate system", J Biomech 35(4):543-548, 2002 (lower extremity);
    # Wu G et al., J Biomech 38(5):981-992, 2005 (upper extremity).
    #
    # Positions are in bone-local frame (cm). Y = long axis.
    _LANDMARKS: dict[str, list[dict]] = {
        # Pelvis
        "Hip bone (R)": [
            {"name": "asis_r", "position": vec3(0, 5, 6), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "psis_r", "position": vec3(0, 3, -4), "surfaceNormal": vec3(0, 0, -1)},
            {"name": "iliac_crest_r", "position": vec3(0, 8, 0)},
        ],
        "Hip bone (L)": [
            {"name": "asis_l", "position": vec3(0, 5, 6), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "psis_l", "position": vec3(0, 3, -4), "surfaceNormal": vec3(0, 0, -1)},
            {"name": "iliac_crest_l", "position": vec3(0, 8, 0)},
        ],
        # Femur
        "Femur (R)": [
            {"name": "greater_trochanter_r", "position": vec3(-2, 20, 0), "surfaceNormal": vec3(-1, 0, 0)},
            {"name": "lateral_epicondyle_r", "position": vec3(-1.5, -20, 0), "surfaceNormal": vec3(-1, 0, 0)},
            {"name": "medial_epicondyle_r", "position": vec3(1.5, -20, 0), "surfaceNormal": vec3(1, 0, 0)},
        ],
        "Femur (L)": [
            {"name": "greater_trochanter_l", "position": vec3(2, 20, 0), "surfaceNormal": vec3(1, 0, 0)},
            {"name": "lateral_epicondyle_l", "position": vec3(1.5, -20, 0), "surfaceNormal": vec3(1, 0, 0)},
            {"name": "medial_epicondyle_l", "position": vec3(-1.5, -20, 0), "surfaceNormal": vec3(-1, 0, 0)},
        ],
        # Tibia
        "Tibia (R)": [
            {"name": "tibial_tuberosity_r", "position": vec3(0, 17, 1.5), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "medial_malleolus_r", "position": vec3(1, -18, 0), "surfaceNormal": vec3(1, 0, 0)},
        ],
        "Tibia (L)": [
            {"name": "tibial_tuberosity_l", "position": vec3(0, 17, 1.5), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "medial_malleolus_l", "position": vec3(-1, -18, 0), "surfaceNormal": vec3(-1, 0, 0)},
        ],
        # Fibula
        "Fibula (R)": [
            {"name": "lateral_malleolus_r", "position": vec3(0, -17, 0), "surfaceNormal": vec3(-1, 0, 0)},
        ],
        "Fibula (L)": [
            {"name": "lateral_malleolus_l", "position": vec3(0, -17, 0), "surfaceNormal": vec3(1, 0, 0)},
        ],
        # Calcaneus
        "Calcaneus (R)": [
            {"name": "calcaneal_tuberosity_r", "position": vec3(0, -3, -2), "surfaceNormal": vec3(0, -1, 0)},
        ],
        "Calcaneus (L)": [
            {"name": "calcaneal_tuberosity_l", "position": vec3(0, -3, -2), "surfaceNormal": vec3(0, -1, 0)},
        ],
        # Humerus
        "Humerus (R)": [
            {"name": "lateral_epicondyle_humerus_r", "position": vec3(-1, -16, 0), "surfaceNormal": vec3(-1, 0, 0)},
            {"name": "medial_epicondyle_humerus_r", "position": vec3(1, -16, 0), "surfaceNormal": vec3(1, 0, 0)},
        ],
        "Humerus (L)": [
            {"name": "lateral_epicondyle_humerus_l", "position": vec3(1, -16, 0), "surfaceNormal": vec3(1, 0, 0)},
            {"name": "medial_epicondyle_humerus_l", "position": vec3(-1, -16, 0), "surfaceNormal": vec3(-1, 0, 0)},
        ],
        # Radius
        "Radius (R)": [
            {"name": "radial_styloid_r", "position": vec3(0, -12, 0.5), "surfaceNormal": vec3(-1, 0, 0)},
        ],
        "Radius (L)": [
            {"name": "radial_styloid_l", "position": vec3(0, -12, 0.5), "surfaceNormal": vec3(1, 0, 0)},
        ],
        # Ulna
        "Ulna (R)": [
            {"name": "ulnar_styloid_r", "position": vec3(0, -13, -0.5), "surfaceNormal": vec3(1, 0, 0)},
            {"name": "olecranon_r", "position": vec3(0, 13, -1), "surfaceNormal": vec3(0, 0, -1)},
        ],
        "Ulna (L)": [
            {"name": "ulnar_styloid_l", "position": vec3(0, -13, -0.5), "surfaceNormal": vec3(-1, 0, 0)},
            {"name": "olecranon_l", "position": vec3(0, 13, -1), "surfaceNormal": vec3(0, 0, -1)},
        ],
        # Scapula
        "Scapula (R)": [
            {"name": "acromion_r", "position": vec3(5, 7, 0.5), "surfaceNormal": vec3(0, 1, 0)},
            {"name": "inferior_angle_scapula_r", "position": vec3(0, -7, 0)},
        ],
        "Scapula (L)": [
            {"name": "acromion_l", "position": vec3(-5, 7, 0.5), "surfaceNormal": vec3(0, 1, 0)},
            {"name": "inferior_angle_scapula_l", "position": vec3(0, -7, 0)},
        ],
        # Sternum / trunk
        "Sternum": [
            {"name": "suprasternal_notch", "position": vec3(0, 7.5, 0.5), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "xiphoid_process", "position": vec3(0, -7, 0.3), "surfaceNormal": vec3(0, 0, 1)},
        ],
        # Cervical
        "C7 vertebra": [
            {"name": "c7_spinous_process", "position": vec3(0, 0, -1.5), "surfaceNormal": vec3(0, 0, -1)},
        ],
        # Sacrum
        "Sacrum": [
            {"name": "sacral_promontory", "position": vec3(0, 5, 1), "surfaceNormal": vec3(0, 0, 1)},
        ],
        # Skull test set
        "Frontal bone": [
            {"name": "glabella", "position": vec3(0, -2.5, 4.8), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "supraorbital_margin_r", "position": vec3(-3.2, -4.5, 4.2), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "supraorbital_margin_l", "position": vec3(3.2, -4.5, 4.2), "surfaceNormal": vec3(0, 0, 1)},
        ],
        "Parietal bone (R)": [
            {"name": "parietal_eminence_r", "position": vec3(-4.8, 1.5, 0.0), "surfaceNormal": vec3(-1, 0, 0)},
        ],
        "Parietal bone (L)": [
            {"name": "parietal_eminence_l", "position": vec3(4.8, 1.5, 0.0), "surfaceNormal": vec3(1, 0, 0)},
        ],
        "Temporal bone (R)": [
            {"name": "mastoid_process_r", "position": vec3(-2.2, -1.8, -0.8), "surfaceNormal": vec3(-1, 0, -0.2)},
            {"name": "zygomatic_root_r", "position": vec3(-1.8, 0.3, 1.0), "surfaceNormal": vec3(-1, 0, 0.2)},
        ],
        "Temporal bone (L)": [
            {"name": "mastoid_process_l", "position": vec3(2.2, -1.8, -0.8), "surfaceNormal": vec3(1, 0, -0.2)},
            {"name": "zygomatic_root_l", "position": vec3(1.8, 0.3, 1.0), "surfaceNormal": vec3(1, 0, 0.2)},
        ],
        "Occipital bone": [
            {"name": "external_occipital_protuberance", "position": vec3(0, -1.2, -4.6), "surfaceNormal": vec3(0, 0, -1)},
        ],
        "Sphenoid bone": [
            {"name": "sella_turcica", "position": vec3(0, 0.4, 0.1), "surfaceNormal": vec3(0, 1, 0)},
            {"name": "greater_wing_r", "position": vec3(-2.0, -0.3, 0.0), "surfaceNormal": vec3(-1, 0, 0)},
            {"name": "greater_wing_l", "position": vec3(2.0, -0.3, 0.0), "surfaceNormal": vec3(1, 0, 0)},
            {"name": "pterygoid_process_r", "position": vec3(-0.9, 1.8, -0.4), "surfaceNormal": vec3(0, 1, -0.1)},
            {"name": "pterygoid_process_l", "position": vec3(0.9, 1.8, -0.4), "surfaceNormal": vec3(0, 1, -0.1)},
        ],
        "Zygomatic bone (R)": [
            {"name": "zygion_r", "position": vec3(-1.8, 0, 1.5), "surfaceNormal": vec3(-1, 0, 0.3)},
            {"name": "frontozygomatic_suture_r", "position": vec3(-1.2, 1.3, 0.9), "surfaceNormal": vec3(-0.5, 0.7, 0.2)},
        ],
        "Zygomatic bone (L)": [
            {"name": "zygion_l", "position": vec3(1.8, 0, 1.5), "surfaceNormal": vec3(1, 0, 0.3)},
            {"name": "frontozygomatic_suture_l", "position": vec3(1.2, 1.3, 0.9), "surfaceNormal": vec3(0.5, 0.7, 0.2)},
        ],
        "Maxilla (R)": [
            {"name": "infraorbital_foramen_r", "position": vec3(-0.9, 0.4, 1.1), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "alveolar_process_r", "position": vec3(-0.3, -1.1, 0.9), "surfaceNormal": vec3(0, -0.2, 1)},
        ],
        "Maxilla (L)": [
            {"name": "infraorbital_foramen_l", "position": vec3(0.9, 0.4, 1.1), "surfaceNormal": vec3(0, 0, 1)},
            {"name": "alveolar_process_l", "position": vec3(0.3, -1.1, 0.9), "surfaceNormal": vec3(0, -0.2, 1)},
        ],
        "Mandible": [
            {"name": "menton", "position": vec3(0, -4.5, 1.1), "surfaceNormal": vec3(0, -0.4, 1)},
            {"name": "gonion_r", "position": vec3(-4.8, 1.6, -0.5), "surfaceNormal": vec3(-1, 0, -0.1)},
            {"name": "gonion_l", "position": vec3(4.8, 1.6, -0.5), "surfaceNormal": vec3(1, 0, -0.1)},
            {"name": "condylion_r", "position": vec3(-4.6, 4.4, -0.5), "surfaceNormal": vec3(-0.6, 0.7, 0)},
            {"name": "condylion_l", "position": vec3(4.6, 4.4, -0.5), "surfaceNormal": vec3(0.6, 0.7, 0)},
        ],
    }

    # Inject landmarks into matching geometries
    bone_name_to_geo_idx: dict[str, int] = {}
    for gi, g in enumerate(geometries):
        # Find which bone this geometry belongs to
        for bi, bd in enumerate(BONE_DEFS):
            if r.bone_ids[bi] == g["boneId"]:
                bone_name_to_geo_idx[bd[0]] = gi
                break

    for bone_name, lms in _LANDMARKS.items():
        gi = bone_name_to_geo_idx.get(bone_name)
        if gi is not None:
            geometries[gi]["landmarks"] = lms

    return geometries

__all__ = [name for name in globals() if not name.startswith("__")]
