from .shared import *
from .skeleton import *

def _prim(ptype: str, **kw) -> dict:
    """Create a CSG primitive leaf node."""
    return {"nodeType": "primitive", "primitive": {"primitiveType": ptype, **kw}}

def _op(operation: str, children: list[dict]) -> dict:
    """Create a CSG operation node."""
    return {"nodeType": "operation", "operation": operation, "children": children}

def _csg_long_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for long bones: shaft capsule + epiphyseal spheres.

    Major long bones (femur, humerus, tibia, ulna, radius, fibula) get
    proximal + distal epiphyses. Smaller ones (metacarpals, metatarsals,
    phalanges, clavicles) get a simpler capsule-only or capsule+sphere.
    """
    r_shaft = (w + d) / 4
    is_major = l > 20  # femur, humerus, tibia, ulna, radius, fibula
    is_medium = 5 < l <= 20  # clavicle, metacarpals, metatarsals
    # is_small: l <= 5 — phalanges

    if is_major:
        # Shaft spans full bone length minus epiphyseal radii at each end.
        # Epiphyses overlap the shaft ends for continuous geometry.
        r_prox = r_shaft * 1.4
        r_dist = r_shaft * 1.3
        shaft_h = max(1.0, l - r_prox - r_dist)
        # Epiphysis centers placed at shaft ends (overlap guaranteed)
        y_prox = round(shaft_h / 2, 1)
        y_dist = round(-shaft_h / 2, 1)

        if "Femur" in name:
            return _op("union", [
                _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                      position=vec3(0, 0, 0)),
                _prim("sphere", radius=round(r_prox * 1.2, 2),
                      position=vec3(0, y_prox, 0)),
                _prim("ellipsoid", radii=vec3(round(r_dist * 1.1, 2), round(r_dist * 0.8, 2), round(r_dist, 2)),
                      position=vec3(0, y_dist, 0)),
            ])
        if "Humerus" in name:
            return _op("union", [
                _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                      position=vec3(0, 0, 0)),
                _prim("sphere", radius=round(r_prox, 2),
                      position=vec3(0, y_prox, 0)),
                _prim("ellipsoid", radii=vec3(round(r_dist, 2), round(r_dist * 0.7, 2), round(r_dist * 1.2, 2)),
                      position=vec3(0, y_dist, 0)),
            ])
        if "Tibia" in name:
            return _op("union", [
                _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                      position=vec3(0, 0, 0)),
                _prim("ellipsoid", radii=vec3(round(r_prox * 1.3, 2), round(r_prox * 0.6, 2), round(r_prox, 2)),
                      position=vec3(0, y_prox, 0)),
                _prim("sphere", radius=round(r_dist * 0.8, 2),
                      position=vec3(0, y_dist, 0)),
            ])
        # Generic major: capsule + 2 spheres
        return _op("union", [
            _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(r_prox, 2),
                  position=vec3(0, y_prox, 0)),
            _prim("sphere", radius=round(r_dist, 2),
                  position=vec3(0, y_dist, 0)),
        ])

    if is_medium:
        shaft_h = l * 0.75
        r_end = r_shaft * 1.15
        return _op("union", [
            _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(r_end, 2),
                  position=vec3(0, round(-l / 2 + r_end * 0.8, 1), 0)),
        ])

    # Small (phalanges): simple capsule
    return _prim("capsule", radius=round(r_shaft, 2), height=round(max(0.3, l - 2 * r_shaft), 2),
                 position=vec3(0, 0, 0))


def _csg_flat_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for flat bones: thin box/ellipsoid, optionally with features."""
    # Cranial bones: curved ellipsoid shell
    if any(k in name for k in ["Frontal", "Parietal", "Occipital", "Temporal"]):
        return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                      position=vec3(0, 0, 0))

    # Scapula: flat plate + spine ridge
    if "Scapula" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("box", halfExtents=vec3(round(w * 0.05, 2), round(l * 0.35, 2), round(d * 0.3, 2)),
                  position=vec3(round(w * 0.3, 1), round(l * 0.1, 1), round(d * 0.3, 1))),
            _prim("sphere", radius=round(d * 0.7, 2),
                  position=vec3(round(w * 0.4, 1), round(l * 0.35, 1), round(d * 0.2, 1))),
        ])

    # Sternum: manubrium (top ~20%) + body (middle ~65%) + xiphoid (bottom ~15%)
    if "Sternum" in name:
        return _op("union", [
            # Sternal body — largest part
            _prim("box", halfExtents=vec3(round(w * 0.45, 2), round(l * 0.325, 2), round(d / 2, 2)),
                  position=vec3(0, round(-l * 0.05, 1), 0)),
            # Manubrium — wider, upper part
            _prim("box", halfExtents=vec3(round(w * 0.55, 2), round(l * 0.1, 2), round(d * 0.6, 2)),
                  position=vec3(0, round(l * 0.38, 1), 0)),
            # Xiphoid process — small tapered tip
            _prim("cylinder", radiusTop=round(d * 0.15, 2), radiusBottom=round(d * 0.35, 2),
                  height=round(l * 0.12, 2), position=vec3(0, round(-l * 0.44, 1), 0)),
        ])

    # Ribs: elongated capsule along the bone's long axis (Y in local frame).
    # The renderer orients this along the parent→child vector (vertebra→rib position).
    # Rib head (vertebral end) is slightly wider than the sternal end.
    if "Rib" in name:
        r_shaft = (w + d) / 4
        shaft_h = max(0.5, l * 0.85)
        return _op("union", [
            _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(r_shaft * 1.4, 2),
                  position=vec3(0, round(l * 0.42, 1), 0)),
        ])

    # Nasal, lacrimal, palatine, vomer — thin plates
    if d < 0.5 or (l < 3 and w < 2):
        return _prim("box", halfExtents=vec3(round(w / 2, 2), round(l / 2, 2), round(max(d, 0.1) / 2, 2)),
                      position=vec3(0, 0, 0))

    # Default flat: box
    return _prim("box", halfExtents=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0))


def _csg_irregular_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for irregular bones: vertebrae, hip, mandible, etc."""
    # Vertebrae: cylindrical body + posterior arch + spinous process
    if "vertebra" in name.lower() or "atlas" in name.lower() or "axis" in name.lower():
        body_r = w / 2 * 0.65
        body_h = l * 0.7
        arch_w = w * 0.45
        arch_d = d * 0.4
        sp_r = min(w, d) * 0.08
        sp_h = d * 0.3

        # Body is ANTERIOR (+Z), arch and processes are POSTERIOR (−Z)
        children = [
            _prim("cylinder", radiusTop=round(body_r, 2), radiusBottom=round(body_r, 2),
                  height=round(body_h, 2), position=vec3(0, 0, round(d * 0.2, 1))),
            _prim("box", halfExtents=vec3(round(arch_w, 2), round(l * 0.35, 2), round(arch_d, 2)),
                  position=vec3(0, 0, round(-d * 0.15, 1))),
        ]
        # Spinous process for thoracic/lumbar (not C1 atlas)
        if "atlas" not in name.lower():
            children.append(
                _prim("cylinder", radiusTop=round(sp_r, 2), radiusBottom=round(sp_r * 1.3, 2),
                      height=round(sp_h, 2), position=vec3(0, 0, round(-d * 0.4, 1))))
        # Transverse processes (lateral, along X axis)
        children.append(
            _prim("cylinder", radiusTop=round(sp_r * 0.8, 2), radiusBottom=round(sp_r * 0.8, 2),
                  height=round(w * 0.3, 2), position=vec3(round(w * 0.35, 1), 0, 0)))
        return _op("union", children)

    # Hip bone: ilium ellipsoid + ischium + acetabulum
    if "Hip bone" in name:
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w * 0.35, 2), round(l * 0.45, 2), round(d * 0.45, 2)),
                  position=vec3(0, round(l * 0.15, 1), 0)),
            _prim("box", halfExtents=vec3(round(w * 0.18, 2), round(l * 0.15, 2), round(d * 0.2, 2)),
                  position=vec3(0, round(-l * 0.3, 1), 0)),
            _op("subtract", [
                _prim("sphere", radius=round(d * 0.35, 2),
                      position=vec3(0, round(-l * 0.15, 1), round(-d * 0.3, 1))),
                _prim("sphere", radius=round(d * 0.28, 2),
                      position=vec3(0, round(-l * 0.15, 1), round(-d * 0.3, 1))),
            ]),
        ])

    # Sacrum: triangular wedge
    if "Sacrum" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("cylinder", radiusTop=round(w * 0.06, 2), radiusBottom=round(w * 0.06, 2),
                  height=round(l * 0.6, 2), position=vec3(0, round(l * 0.1, 1), round(-d * 0.25, 1))),
        ])

    # Coccyx: small tapered cone
    if "Coccyx" in name:
        return _prim("cylinder", radiusTop=round(w * 0.15, 2), radiusBottom=round(w * 0.35, 2),
                      height=round(l, 2), position=vec3(0, 0, 0))

    # Mandible: U-shaped jaw
    if "Mandible" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w * 0.45, 2), round(l * 0.18, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("box", halfExtents=vec3(round(w * 0.08, 2), round(l * 0.35, 2), round(d * 0.25, 2)),
                  position=vec3(round(w * 0.4, 1), round(l * 0.2, 1), round(d * 0.1, 1))),
            _prim("box", halfExtents=vec3(round(w * 0.08, 2), round(l * 0.35, 2), round(d * 0.25, 2)),
                  position=vec3(round(-w * 0.4, 1), round(l * 0.2, 1), round(d * 0.1, 1))),
        ])

    # Sphenoid: butterfly shape
    if "Sphenoid" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w * 0.2, 2), round(l * 0.3, 2), round(d * 0.25, 2)),
                  position=vec3(0, 0, 0)),
            _prim("box", halfExtents=vec3(round(w * 0.35, 2), round(l * 0.15, 2), round(d * 0.12, 2)),
                  position=vec3(0, round(-l * 0.1, 1), 0)),
        ])

    # Hyoid: U-shaped
    if "Hyoid" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w * 0.35, 2), round(l * 0.2, 2), round(d * 0.3, 2)),
                  position=vec3(0, 0, 0)),
            _prim("cylinder", radiusTop=round(d * 0.15, 2), radiusBottom=round(d * 0.15, 2),
                  height=round(l * 0.3, 2), position=vec3(round(w * 0.3, 1), round(l * 0.15, 1), 0)),
            _prim("cylinder", radiusTop=round(d * 0.15, 2), radiusBottom=round(d * 0.15, 2),
                  height=round(l * 0.3, 2), position=vec3(round(-w * 0.3, 1), round(l * 0.15, 1), 0)),
        ])

    # Ear ossicles: tiny spheres/ellipsoids
    if any(k in name for k in ["Malleus", "Incus", "Stapes"]):
        return _prim("ellipsoid", radii=vec3(round(w / 2, 3), round(l / 2, 3), round(d / 2, 3)),
                      position=vec3(0, 0, 0))

    # Maxilla, zygomatic, inferior concha, ethmoid — irregular facial
    if any(k in name for k in ["Maxilla", "Zygomatic", "Inferior nasal", "Ethmoid", "Palatine"]):
        return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                      position=vec3(0, 0, 0))

    # Default irregular: ellipsoid
    return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0))


def _csg_short_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for short bones: carpals, tarsals."""
    # Calcaneus: largest tarsal, box-like with tuberosity
    if "Calcaneus" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w / 2, 2), round(l * 0.4, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("ellipsoid", radii=vec3(round(w * 0.35, 2), round(l * 0.2, 2), round(d * 0.4, 2)),
                  position=vec3(0, round(-l * 0.3, 1), 0)),
        ])

    # Talus: dome-shaped for ankle joint
    if "Talus" in name:
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l * 0.35, 2), round(d * 0.4, 2)),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(min(w, d) * 0.25, 2),
                  position=vec3(0, round(l * 0.25, 1), 0)),
        ])

    # Default short: ellipsoid
    return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0))


def _csg_sesamoid_bone(l: float, w: float, d: float, _name: str) -> dict:
    """CSG tree for sesamoid bones: patella."""
    # Flattened ellipsoid with articular facet
    return _op("union", [
        _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
              position=vec3(0, 0, 0)),
        _prim("sphere", radius=round(min(w, d) * 0.15, 2),
              position=vec3(0, round(-l * 0.25, 1), round(-d * 0.2, 1))),
    ])


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


def _load_mesh_manifest(assets_dir: str | None = None) -> dict[str, dict]:
    """Load the mesh manifest from the assets directory if it exists."""
    if assets_dir:
        manifest_path = Path(assets_dir) / "manifest.json"
    else:
        manifest_path = (Path(__file__).parent.parent
                         / "session-3" / "human-controller" / "public" / "assets" / "bones" / "manifest.json")
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {}


def _load_bone_mesh_map() -> dict[str, str]:
    """Load bone name → filename mapping from bone_mesh_map.json."""
    map_path = (Path(__file__).parent.parent
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
        "Zygomatic bone (R)": [
            {"name": "zygion_r", "position": vec3(-1.8, 0, 1.5), "surfaceNormal": vec3(-1, 0, 0.3)},
        ],
        "Zygomatic bone (L)": [
            {"name": "zygion_l", "position": vec3(1.8, 0, 1.5), "surfaceNormal": vec3(1, 0, 0.3)},
        ],
        "Maxilla (R)": [
            {"name": "infraorbital_foramen_r", "position": vec3(-0.9, 0.4, 1.1), "surfaceNormal": vec3(0, 0, 1)},
        ],
        "Maxilla (L)": [
            {"name": "infraorbital_foramen_l", "position": vec3(0.9, 0.4, 1.1), "surfaceNormal": vec3(0, 0, 1)},
        ],
        "Mandible": [
            {"name": "menton", "position": vec3(0, -4.5, 1.1), "surfaceNormal": vec3(0, -0.4, 1)},
            {"name": "gonion_r", "position": vec3(-4.8, 1.6, -0.5), "surfaceNormal": vec3(-1, 0, -0.1)},
            {"name": "gonion_l", "position": vec3(4.8, 1.6, -0.5), "surfaceNormal": vec3(1, 0, -0.1)},
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


# =============================================================================
# HAIR
# =============================================================================


__all__ = [name for name in globals() if not name.startswith("__")]
