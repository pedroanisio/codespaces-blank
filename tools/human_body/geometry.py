from .geometry_parts import generation as _generation
from .geometry_parts.csg import *
from .geometry_parts.generation import *
from .geometry_parts.mesh import *


_load_mesh_manifest = _generation._load_mesh_manifest
_load_bone_mesh_map = _generation._load_bone_mesh_map


def gen_bone_geometries(*args, **kwargs):
    original_manifest = _generation._load_mesh_manifest
    original_map = _generation._load_bone_mesh_map
    _generation._load_mesh_manifest = _load_mesh_manifest
    _generation._load_bone_mesh_map = _load_bone_mesh_map
    try:
        return _generation.gen_bone_geometries(*args, **kwargs)
    finally:
        _generation._load_mesh_manifest = original_manifest
        _generation._load_bone_mesh_map = original_map


__all__ = [name for name in globals() if not name.startswith("__")]
