from ..shared import *
from ..skeleton import *


def _round_list(values: list[float], digits: int = 6) -> list[float]:
    return [round(v, digits) for v in values]


def _is_skull_bone(name: str, region: str) -> bool:
    return region in ("axial_cranium", "axial_face")


def _deform_positions(
    positions: list[float],
    deform: Callable[[float, float, float], tuple[float, float, float]],
) -> list[float]:
    out = positions[:]
    for i in range(0, len(out), 3):
        x, y, z = out[i], out[i + 1], out[i + 2]
        nx, ny, nz = deform(x, y, z)
        out[i], out[i + 1], out[i + 2] = nx, ny, nz
    return _round_list(out)


def _skull_mesh_for_bone(name: str, cls: str, length: float, width: float, depth: float,
                         radial_segments: int, axial_segments: int) -> tuple[list[float], list[int], list[float]]:
    positions, indices, uvs = _mesh_for_bone(name, cls, length, width, depth, radial_segments, axial_segments)

    def deform(x: float, y: float, z: float) -> tuple[float, float, float]:
        if "Frontal bone" in name:
            return (x * 1.05, y * 1.02, z + max(0.0, y / max(length, 1)) * 0.6)
        if "Parietal bone" in name:
            side = -1.0 if "(R)" in name else 1.0
            return (x + side * 0.4 * (1.0 - abs(y) / max(length, 1)), y * 1.03, z * 0.95)
        if "Occipital bone" in name:
            return (x * 0.96, y * 1.01, z - 0.7 * (1.0 - abs(y) / max(length, 1)))
        if "Temporal bone" in name:
            side = -1.0 if "(R)" in name else 1.0
            return (x + side * 0.5, y * 0.96, z - 0.2)
        if "Zygomatic" in name:
            side = -1.0 if "(R)" in name else 1.0
            return (x + side * 0.6, y, z + 0.4)
        if "Maxilla" in name:
            return (x * 1.08, y - 0.2, z + 0.5)
        if "Mandible" in name:
            return (x * 1.18, y * 0.92 - 0.4, z * 0.9 + 0.2)
        if "Sphenoid" in name:
            return (x * 1.2, y * 0.9, z * 0.85)
        if "Ethmoid" in name:
            return (x * 0.8, y * 1.05, z * 0.9)
        if "Nasal bone" in name or "Vomer" in name:
            return (x * 0.9, y, z + 0.25)
        return (x, y, z)

    return _deform_positions(positions, deform), indices, uvs


def _select_vertices(positions: list[float], predicate: Callable[[float, float, float], bool]) -> list[int]:
    indices: list[int] = []
    for vi in range(len(positions) // 3):
        x, y, z = positions[vi * 3:vi * 3 + 3]
        if predicate(x, y, z):
            indices.append(vi)
    return indices


def _skull_surface_regions(name: str, positions: list[float]) -> list[dict]:
    regions: list[dict] = []
    if "Frontal bone" in name:
        idxs = _select_vertices(positions, lambda x, y, z: y > 0 and z > 0)
        if len(idxs) >= 3:
            regions.append({"name": "forehead_surface", "vertexIndices": idxs, "regionType": "periosteal"})
        idxs = _select_vertices(positions, lambda x, y, z: y < 0 and z > 0)
        if len(idxs) >= 3:
            regions.append({"name": "supraorbital_margin", "vertexIndices": idxs, "regionType": "attachment"})
    elif "Parietal bone" in name:
        idxs = _select_vertices(positions, lambda x, y, z: abs(x) > 1 and y >= -1)
        if len(idxs) >= 3:
            regions.append({"name": "parietal_vault", "vertexIndices": idxs, "regionType": "periosteal"})
    elif "Occipital bone" in name:
        idxs = _select_vertices(positions, lambda x, y, z: z < 0)
        if len(idxs) >= 3:
            regions.append({"name": "occipital_surface", "vertexIndices": idxs, "regionType": "periosteal"})
    elif "Temporal bone" in name:
        idxs = _select_vertices(positions, lambda x, y, z: abs(x) > 1 and y < 1)
        if len(idxs) >= 3:
            regions.append({"name": "temporal_fossa", "vertexIndices": idxs, "regionType": "attachment"})
    elif "Zygomatic" in name:
        idxs = _select_vertices(positions, lambda x, y, z: abs(x) > 1 and z > 0)
        if len(idxs) >= 3:
            regions.append({"name": "malar_surface", "vertexIndices": idxs, "regionType": "periosteal"})
    elif "Mandible" in name:
        idxs = _select_vertices(positions, lambda x, y, z: y > 0)
        if len(idxs) >= 3:
            regions.append({"name": "mandibular_ramus", "vertexIndices": idxs, "regionType": "periosteal"})
        idxs = _select_vertices(positions, lambda x, y, z: y < 0)
        if len(idxs) >= 3:
            regions.append({"name": "alveolar_arch", "vertexIndices": idxs, "regionType": "attachment"})
    return regions


def _mesh_vertex_normals(positions: list[float], indices: list[int]) -> list[float]:
    normals = [0.0] * len(positions)
    for i in range(0, len(indices), 3):
        i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
        ax, ay, az = positions[i0 * 3:i0 * 3 + 3]
        bx, by, bz = positions[i1 * 3:i1 * 3 + 3]
        cx, cy, cz = positions[i2 * 3:i2 * 3 + 3]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        for idx in (i0, i1, i2):
            normals[idx * 3] += nx
            normals[idx * 3 + 1] += ny
            normals[idx * 3 + 2] += nz

    for i in range(0, len(normals), 3):
        mag = math.sqrt(normals[i] ** 2 + normals[i + 1] ** 2 + normals[i + 2] ** 2)
        if mag > 1e-8:
            normals[i] /= mag
            normals[i + 1] /= mag
            normals[i + 2] /= mag
        else:
            # Degenerate normal (pole vertex or coplanar faces):
            # fall back to using the vertex position as the normal direction.
            # This is correct for convex shapes (sphere, ellipsoid).
            px, py, pz = positions[i], positions[i + 1], positions[i + 2]
            pmag = math.sqrt(px * px + py * py + pz * pz) or 1.0
            normals[i] = px / pmag
            normals[i + 1] = py / pmag
            normals[i + 2] = pz / pmag
    return _round_list(normals)


def _lathe_mesh(profile: list[tuple[float, float]], radial_segments: int,
                scale_x: float = 1.0, scale_z: float = 1.0) -> tuple[list[float], list[int], list[float]]:
    positions: list[float] = []
    uvs: list[float] = []
    indices: list[int] = []

    y_min = min(y for _, y in profile)
    y_max = max(y for _, y in profile)
    y_span = (y_max - y_min) or 1.0

    for pi, (radius, y) in enumerate(profile):
        v = (y - y_min) / y_span
        for rs in range(radial_segments + 1):
            u = rs / radial_segments
            ang = 2.0 * math.pi * u
            positions.extend([
                radius * math.cos(ang) * scale_x,
                y,
                radius * math.sin(ang) * scale_z,
            ])
            uvs.extend([u, v])

    row = radial_segments + 1
    for pi in range(len(profile) - 1):
        for rs in range(radial_segments):
            a = pi * row + rs
            b = a + 1
            c = a + row
            d = c + 1
            indices.extend([a, c, b, b, c, d])

    return _round_list(positions), indices, _round_list(uvs)


def _uv_sphere_mesh(rx: float, ry: float, rz: float,
                    lon_segments: int, lat_segments: int) -> tuple[list[float], list[int], list[float]]:
    positions: list[float] = []
    uvs: list[float] = []
    indices: list[int] = []

    for iy in range(lat_segments + 1):
        v = iy / lat_segments
        theta = v * math.pi
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        y = cos_theta * ry
        for ix in range(lon_segments + 1):
            u = ix / lon_segments
            phi = u * math.pi * 2.0
            x = math.cos(phi) * sin_theta * rx
            z = math.sin(phi) * sin_theta * rz
            positions.extend([x, y, z])
            uvs.extend([u, v])

    row = lon_segments + 1
    for iy in range(lat_segments):
        for ix in range(lon_segments):
            a = iy * row + ix
            b = a + 1
            c = a + row
            d = c + 1
            indices.extend([a, c, b, b, c, d])

    return _round_list(positions), indices, _round_list(uvs)


def _name_perturb(name: str, offset: int = 0) -> float:
    digest = hashlib.sha256(f"{name}:{offset}".encode("utf-8")).digest()
    return digest[0] / 255.0


def _mesh_for_bone(name: str, cls: str, length: float, width: float, depth: float,
                   radial_segments: int, axial_segments: int) -> tuple[list[float], list[int], list[float]]:
    if cls == "long":
        half = length / 2.0
        shaft_r = max(min(width, depth) * 0.18, 0.12)
        head_r = max(width * 0.36, shaft_r * 1.4)
        condyle_r = max(depth * 0.32, shaft_r * 1.25)
        profile = [
            (0.01, -half),
            (condyle_r, -half * 0.88),
            (shaft_r * 1.15, -half * 0.52),
            (shaft_r, 0.0),
            (shaft_r * 1.18, half * 0.50),
            (head_r, half * 0.86),
            (0.01, half),
        ]
        return _lathe_mesh(profile, radial_segments, scale_x=width / max(width, depth), scale_z=depth / max(width, depth))

    if cls == "flat":
        # Cranial vault bones: use a hemisphere shell (open half-sphere) so they
        # look like curved skull plates rather than solid discs.
        # Depth is increased to ~20% of width for visible thickness.
        is_cranial = any(k in name for k in ["Frontal", "Parietal", "Occipital", "Temporal"])
        if is_cranial:
            shell_depth = max(width * 0.2, depth)
            return _uv_sphere_mesh(width / 2.0, length / 2.0, shell_depth,
                                   radial_segments, axial_segments)
        # Scapula: flatter with more depth than cranial
        if "Scapula" in name:
            return _uv_sphere_mesh(width / 2.0, length / 2.0, max(depth, width * 0.08),
                                   radial_segments, axial_segments)
        return _uv_sphere_mesh(width / 2.0, length / 2.0, max(depth / 2.0, 0.15),
                               radial_segments, axial_segments)

    if cls == "short":
        return _uv_sphere_mesh(width / 2.0, length / 2.0, depth / 2.0,
                               radial_segments, axial_segments)

    if cls == "sesamoid":
        return _uv_sphere_mesh(width / 2.0, length / 2.0, depth / 2.0,
                               radial_segments, axial_segments)

    half = length / 2.0
    p0 = 0.75 + 0.25 * _name_perturb(name, 0)
    p1 = 0.75 + 0.25 * _name_perturb(name, 1)
    p2 = 0.75 + 0.25 * _name_perturb(name, 2)
    profile = [
        (0.01, -half),
        (max(width, depth) * 0.18 * p0, -half * 0.82),
        (max(width, depth) * 0.36 * p1, -half * 0.35),
        (max(width, depth) * 0.30 * p2, 0.0),
        (max(width, depth) * 0.40 * p1, half * 0.42),
        (max(width, depth) * 0.22 * p0, half * 0.84),
        (0.01, half),
    ]
    return _lathe_mesh(profile, radial_segments, scale_x=width / max(width, depth), scale_z=depth / max(width, depth))


def _lod_from_mesh(level: int, positions: list[float], indices: list[int], uvs: list[float]) -> dict:
    vertex_count = len(positions) // 3
    triangle_count = len(indices) // 3
    normals = _mesh_vertex_normals(positions, indices)
    return {
        "level": level,
        "vertexCount": vertex_count,
        "triangleCount": triangle_count,
        "vertices": {
            "positions": positions,
            "normals": normals,
            "uvs": uvs,
        },
        "indices": indices,
    }


def _indexed_mesh_geometry(name: str, cls: str, region: str, bone_id: str,
                           length: float, width: float, depth: float) -> dict:
    if _is_skull_bone(name, region):
        hi_positions, hi_indices, hi_uvs = _skull_mesh_for_bone(name, cls, length, width, depth, 40, 28)
        mid_positions, mid_indices, mid_uvs = _skull_mesh_for_bone(name, cls, length, width, depth, 24, 16)
        lo_positions, lo_indices, lo_uvs = _skull_mesh_for_bone(name, cls, length, width, depth, 14, 9)
        source = {
            "method": "procedural",
            "datasetId": "skull_test_v1",
            "citation": "Skull-only experimental procedural mesh profile generated in tools/generate_human_body.py",
        }
        surface_regions = _skull_surface_regions(name, hi_positions)
        lods = [
            _lod_from_mesh(0, hi_positions, hi_indices, hi_uvs),
            _lod_from_mesh(1, mid_positions, mid_indices, mid_uvs),
            _lod_from_mesh(2, lo_positions, lo_indices, lo_uvs),
        ]
    else:
        hi_positions, hi_indices, hi_uvs = _mesh_for_bone(name, cls, length, width, depth, 18, 12)
        lo_positions, lo_indices, lo_uvs = _mesh_for_bone(name, cls, length, width, depth, 10, 7)
        source = {
            "method": "procedural",
            "citation": "Procedurally generated from bone dimensions in tools/generate_human_body.py",
        }
        surface_regions = []
        lods = [
            _lod_from_mesh(0, hi_positions, hi_indices, hi_uvs),
            _lod_from_mesh(1, lo_positions, lo_indices, lo_uvs),
        ]
    geometry = {
        "geometryType": "indexed_mesh",
        "id": uid(),
        "boneId": bone_id,
        "lods": lods,
        "isClosed": True,
        "isManifold": True,
        "source": source,
    }
    if surface_regions:
        geometry["surfaceRegions"] = surface_regions
    return geometry


__all__ = [name for name in globals() if not name.startswith("__")]
