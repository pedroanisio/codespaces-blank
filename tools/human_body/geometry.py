from .geometry_parts import generation as _generation
from .geometry_parts.csg import (
    _csg_flat_bone,
    _csg_irregular_bone,
    _csg_long_bone,
    _csg_sesamoid_bone,
    _csg_short_bone,
    _op,
    _prim,
)
from .geometry_parts.generation import gen_bone_geometries as _gen_bone_geometries
from .geometry_parts.mesh import (
    _deform_positions,
    _indexed_mesh_geometry,
    _is_skull_bone,
    _lathe_mesh,
    _lod_from_mesh,
    _mesh_for_bone,
    _mesh_vertex_normals,
    _name_perturb,
    _round_list,
    _select_vertices,
    _skull_mesh_for_bone,
    _skull_surface_regions,
    _uv_sphere_mesh,
)


_load_mesh_manifest = _generation._load_mesh_manifest
_load_bone_mesh_map = _generation._load_bone_mesh_map


def gen_bone_geometries(*args, **kwargs):
    original_manifest = _generation._load_mesh_manifest
    original_map = _generation._load_bone_mesh_map
    _generation._load_mesh_manifest = _load_mesh_manifest
    _generation._load_bone_mesh_map = _load_bone_mesh_map
    try:
        return _gen_bone_geometries(*args, **kwargs)
    finally:
        _generation._load_mesh_manifest = original_manifest
        _generation._load_bone_mesh_map = original_map


__all__ = [name for name in globals() if not name.startswith("_")]
