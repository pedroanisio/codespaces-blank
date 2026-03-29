from ..shared import *
from ..skeleton import *
def _prim(ptype: str, **kw) -> dict:
    """Create a CSG primitive leaf node."""
    return {"nodeType": "primitive", "primitive": {"primitiveType": ptype, **kw}}

def _op(operation: str, children: list[dict]) -> dict:
    """Create a CSG operation node."""
    return {"nodeType": "operation", "operation": operation, "children": children}
def _rib_number(name: str) -> int | None:
    parts = name.split()
    if len(parts) < 2 or parts[0] != "Rib":
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None
def _csg_long_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for long bones."""
    r_shaft = (w + d) / 4
    is_major = l > 20
    is_medium = 5 < l <= 20

    if is_major:
        r_prox = r_shaft * 1.4
        r_dist = r_shaft * 1.3
        shaft_h = max(1.0, l - r_prox - r_dist)
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
        return _op("union", [
            _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(r_prox, 2),
                  position=vec3(0, y_prox, 0)),
            _prim("sphere", radius=round(r_dist, 2),
                  position=vec3(0, y_dist, 0)),
        ])

    if is_medium:
        if "Metacarpal" in name or "Metatarsal" in name:
            head_bias = -1 if "Metacarpal" in name else 1
            shaft_h = l * (0.7 if "Metacarpal" in name else 0.78)
            return _op("union", [
                _prim("capsule", radius=round(r_shaft * 0.92, 2), height=round(shaft_h, 2), position=vec3(0, 0, 0)),
                _prim("ellipsoid", radii=vec3(round(r_shaft * 1.2, 2), round(r_shaft * 0.9, 2), round(r_shaft, 2)),
                      position=vec3(0, round(head_bias * l * 0.32, 1), 0)),
            ])
        shaft_h = l * 0.75
        r_end = r_shaft * 1.15
        return _op("union", [
            _prim("capsule", radius=round(r_shaft, 2), height=round(shaft_h, 2),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(r_end, 2),
                  position=vec3(0, round(-l / 2 + r_end * 0.8, 1), 0)),
        ])

    return _prim("capsule", radius=round(r_shaft, 2), height=round(max(0.3, l - 2 * r_shaft), 2),
                 position=vec3(0, 0, 0))


def _csg_flat_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for flat bones: thin box/ellipsoid, optionally with features."""
    if "Frontal bone" in name:
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("capsule", radius=round(max(d * 0.45, 0.12), 2), height=round(w * 0.28, 2),
                  position=vec3(round(-w * 0.22, 2), round(-l * 0.22, 2), round(d * 1.8, 2))),
            _prim("capsule", radius=round(max(d * 0.45, 0.12), 2), height=round(w * 0.28, 2),
                  position=vec3(round(w * 0.22, 2), round(-l * 0.22, 2), round(d * 1.8, 2))),
            _prim("ellipsoid", radii=vec3(round(w * 0.12, 2), round(l * 0.08, 2), round(max(d * 0.8, 0.12), 2)),
                  position=vec3(0, round(-l * 0.18, 2), round(d * 1.9, 2))),
            _prim("box", halfExtents=vec3(round(w * 0.16, 2), round(l * 0.09, 2), round(max(d * 0.18, 0.08), 2)),
                  position=vec3(round(-w * 0.18, 2), round(-l * 0.34, 2), round(d * 0.65, 2))),
            _prim("box", halfExtents=vec3(round(w * 0.16, 2), round(l * 0.09, 2), round(max(d * 0.18, 0.08), 2)),
                  position=vec3(round(w * 0.18, 2), round(-l * 0.34, 2), round(d * 0.65, 2))),
        ])

    if "Temporal bone" in name:
        side = -1 if "(R)" in name else 1
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("capsule", radius=round(max(d * 0.42, 0.08), 2), height=round(w * 0.42, 2),
                  position=vec3(round(side * w * 0.28, 2), round(-l * 0.02, 2), round(d * 0.9, 2))),
            _prim("sphere", radius=round(max(min(w, l) * 0.18, 0.15), 2),
                  position=vec3(round(side * w * 0.18, 2), round(-l * 0.28, 2), round(-d * 0.85, 2))),
        ])

    if any(k in name for k in ["Parietal", "Occipital"]):
        return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                      position=vec3(0, 0, 0))

    if "Scapula" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("box", halfExtents=vec3(round(w * 0.05, 2), round(l * 0.35, 2), round(d * 0.3, 2)),
                  position=vec3(round(w * 0.3, 1), round(l * 0.1, 1), round(d * 0.3, 1))),
            _prim("sphere", radius=round(d * 0.7, 2),
                  position=vec3(round(w * 0.4, 1), round(l * 0.35, 1), round(d * 0.2, 1))),
        ])

    if "Sternum" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w * 0.45, 2), round(l * 0.325, 2), round(d / 2, 2)),
                  position=vec3(0, round(-l * 0.05, 1), 0)),
            _prim("box", halfExtents=vec3(round(w * 0.55, 2), round(l * 0.1, 2), round(d * 0.6, 2)),
                  position=vec3(0, round(l * 0.38, 1), 0)),
            _prim("cylinder", radiusTop=round(d * 0.15, 2), radiusBottom=round(d * 0.35, 2),
                  height=round(l * 0.12, 2), position=vec3(0, round(-l * 0.44, 1), 0)),
        ])

    if "Rib" in name:
        r_shaft = (w + d) / 4
        rib_num = _rib_number(name)
        if rib_num == 1:
            return _op("union", [
                _prim("capsule", radius=round(r_shaft * 1.08, 2), height=round(max(0.5, l * 0.68), 2),
                      position=vec3(0, 0, 0)),
                _prim("ellipsoid", radii=vec3(round(r_shaft * 1.5, 2), round(l * 0.14, 2), round(d * 0.9, 2)),
                      position=vec3(0, round(l * 0.28, 1), 0)),
            ])
        if rib_num in (11, 12):
            return _op("union", [
                _prim("capsule", radius=round(r_shaft * 0.92, 2), height=round(max(0.5, l * 0.74), 2),
                      position=vec3(0, round(-l * 0.04, 2), 0)),
                _prim("sphere", radius=round(r_shaft * 1.2, 2),
                      position=vec3(0, round(l * 0.3, 1), 0)),
            ])
        return _op("union", [
            _prim("capsule", radius=round(r_shaft, 2), height=round(max(0.5, l * 0.88), 2),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(r_shaft * 1.35, 2),
                  position=vec3(0, round(l * 0.42, 1), 0)),
            _prim("ellipsoid", radii=vec3(round(r_shaft * 0.7, 2), round(l * 0.12, 2), round(r_shaft * 0.85, 2)),
                  position=vec3(0, round(-l * 0.34, 2), round(d * 0.1, 2))),
        ])
    if any(k in name for k in ["Nasal bone", "Lacrimal bone", "Vomer"]):
        return _op("union", [_prim("box", halfExtents=vec3(round(w * 0.42, 2), round(l * 0.46, 2), round(max(d, 0.1) * 0.5, 2)), position=vec3(0, 0, 0)), _prim("capsule", radius=round(max(d * 0.12, 0.03), 2), height=round(l * 0.28, 2), position=vec3(0, round(-l * 0.08, 2), round(d * 0.22, 2)))])

    if d < 0.5 or (l < 3 and w < 2):
        return _prim("box", halfExtents=vec3(round(w / 2, 2), round(l / 2, 2), round(max(d, 0.1) / 2, 2)),
                      position=vec3(0, 0, 0))

    return _prim("box", halfExtents=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0))
def _csg_irregular_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for irregular bones: vertebrae, hip, mandible, etc."""
    if "vertebra" in name.lower() or "atlas" in name.lower() or "axis" in name.lower():
        if "atlas" in name.lower():
            ring_r = round(max(min(w, d) * 0.16, 0.12), 2)
            return _op("union", [
                _prim("capsule", radius=ring_r, height=round(w * 0.72, 2),
                      position=vec3(round(-w * 0.18, 2), 0, round(-d * 0.04, 2))),
                _prim("capsule", radius=ring_r, height=round(w * 0.72, 2),
                      position=vec3(round(w * 0.18, 2), 0, round(-d * 0.04, 2))),
                _prim("box", halfExtents=vec3(round(w * 0.18, 2), round(l * 0.1, 2), round(d * 0.16, 2)),
                      position=vec3(0, round(l * 0.22, 2), round(d * 0.08, 2))),
                _prim("box", halfExtents=vec3(round(w * 0.22, 2), round(l * 0.1, 2), round(d * 0.14, 2)),
                      position=vec3(0, round(-l * 0.22, 2), round(-d * 0.1, 2))),
                _prim("capsule", radius=round(max(ring_r * 0.5, 0.06), 2), height=round(w * 0.42, 2),
                      position=vec3(0, 0, round(-d * 0.24, 2))),
            ])
        if "axis" in name.lower():
            body_r = round(w / 2 * 0.58, 2)
            return _op("union", [
                _prim("cylinder", radiusTop=body_r, radiusBottom=body_r,
                      height=round(l * 0.62, 2), position=vec3(0, 0, round(d * 0.12, 2))),
                _prim("capsule", radius=round(max(body_r * 0.24, 0.08), 2), height=round(l * 0.42, 2),
                      position=vec3(0, round(l * 0.3, 2), round(d * 0.18, 2))),
                _prim("box", halfExtents=vec3(round(w * 0.42, 2), round(l * 0.22, 2), round(d * 0.18, 2)),
                      position=vec3(0, 0, round(-d * 0.08, 2))),
                _prim("cylinder", radiusTop=round(min(w, d) * 0.09, 2), radiusBottom=round(min(w, d) * 0.12, 2),
                      height=round(d * 0.42, 2), position=vec3(0, 0, round(-d * 0.34, 2))),
            ])
        is_cervical = name.startswith("C")
        is_thoracic = name.startswith("T")
        is_lumbar = name.startswith("L")
        body_r = w / 2 * (0.52 if is_cervical else 0.58 if is_thoracic else 0.72 if is_lumbar else 0.65)
        body_h = l * (0.58 if is_cervical else 0.64 if is_thoracic else 0.76 if is_lumbar else 0.7)
        arch_w = w * (0.52 if is_cervical else 0.42 if is_thoracic else 0.5 if is_lumbar else 0.45)
        arch_d = d * (0.32 if is_cervical else 0.44 if is_thoracic else 0.38 if is_lumbar else 0.4)
        sp_r = min(w, d) * (0.06 if is_cervical else 0.08 if is_thoracic else 0.1 if is_lumbar else 0.08)
        sp_h = d * (0.18 if is_cervical else 0.42 if is_thoracic else 0.22 if is_lumbar else 0.3)

        children = [
            _prim("cylinder", radiusTop=round(body_r, 2), radiusBottom=round(body_r, 2),
                  height=round(body_h, 2), position=vec3(0, 0, round(d * 0.2, 1))),
            _prim("box", halfExtents=vec3(round(arch_w, 2), round(l * 0.35, 2), round(arch_d, 2)),
                  position=vec3(0, 0, round(-d * 0.15, 1))),
        ]
        children.append(
            _prim("cylinder", radiusTop=round(sp_r, 2), radiusBottom=round(sp_r * (0.9 if is_cervical else 1.5 if is_thoracic else 1.2), 2),
                  height=round(sp_h, 2), position=vec3(0, 0, round(-d * (0.28 if is_cervical else 0.44 if is_thoracic else 0.32), 1))))
        children.append(
            _prim("cylinder", radiusTop=round(sp_r * 0.8, 2), radiusBottom=round(sp_r * 0.8, 2),
                  height=round(w * (0.42 if is_cervical else 0.24 if is_thoracic else 0.28), 2), position=vec3(round(w * 0.35, 1), 0, 0)))
        if is_thoracic:
            children.extend([
                _prim("sphere", radius=round(sp_r * 1.2, 2), position=vec3(round(w * 0.24, 1), 0, round(d * 0.18, 1))),
                _prim("sphere", radius=round(sp_r * 1.2, 2), position=vec3(round(-w * 0.24, 1), 0, round(d * 0.18, 1))),
            ])
        if name.startswith("C7"):
            children.append(
                _prim("cylinder", radiusTop=round(sp_r * 0.9, 2), radiusBottom=round(sp_r * 1.7, 2),
                      height=round(d * 0.36, 2), position=vec3(0, 0, round(-d * 0.48, 1))))
        return _op("union", children)

    if "Hip bone" in name:
        side = -1 if "(R)" in name else 1
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w * 0.3, 2), round(l * 0.34, 2), round(d * 0.18, 2)),
                  position=vec3(round(side * w * 0.06, 2), round(l * 0.18, 2), round(d * 0.04, 2))),
            _prim("box", halfExtents=vec3(round(w * 0.12, 2), round(l * 0.24, 2), round(d * 0.16, 2)),
                  position=vec3(round(side * w * 0.05, 2), round(-l * 0.04, 2), 0)),
            _prim("capsule", radius=round(max(d * 0.1, 0.12), 2), height=round(l * 0.46, 2),
                  position=vec3(round(side * w * 0.18, 2), round(-l * 0.16, 2), round(d * 0.08, 2))),
            _prim("capsule", radius=round(max(d * 0.08, 0.1), 2), height=round(l * 0.42, 2),
                  position=vec3(round(-side * w * 0.1, 2), round(-l * 0.22, 2), round(d * 0.22, 2))),
            _op("subtract", [
                _prim("ellipsoid", radii=vec3(round(w * 0.22, 2), round(l * 0.18, 2), round(d * 0.2, 2)),
                      position=vec3(0, round(-l * 0.12, 2), 0)),
                _prim("ellipsoid", radii=vec3(round(w * 0.14, 2), round(l * 0.1, 2), round(d * 0.11, 2)),
                      position=vec3(0, round(-l * 0.12, 2), 0)),
            ]),
            _op("subtract", [
                _prim("box", halfExtents=vec3(round(w * 0.18, 2), round(l * 0.16, 2), round(d * 0.12, 2)),
                      position=vec3(round(side * w * 0.02, 2), round(-l * 0.22, 2), round(d * 0.02, 2))),
                _prim("box", halfExtents=vec3(round(w * 0.09, 2), round(l * 0.08, 2), round(d * 0.06, 2)),
                      position=vec3(round(side * w * 0.02, 2), round(-l * 0.22, 2), round(d * 0.02, 2))),
            ]),
            _prim("capsule", radius=round(max(d * 0.08, 0.08), 2), height=round(l * 0.24, 2),
                  position=vec3(round(-side * w * 0.14, 2), round(l * 0.28, 2), round(-d * 0.04, 2))),
            _prim("box", halfExtents=vec3(round(w * 0.06, 2), round(l * 0.08, 2), round(d * 0.1, 2)),
                  position=vec3(round(side * w * 0.18, 2), round(-l * 0.04, 2), round(-d * 0.12, 2))),
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

    # Mandible: U-shaped jaw with ramus, condyle, coronoid, and chin.
    if "Mandible" in name:
        return _op("union", [
            _prim("capsule", radius=round(max(d * 0.22, 0.18), 2), height=round(w * 0.72, 2),
                  position=vec3(0, round(-l * 0.02, 2), round(d * 0.35, 2))),
            _prim("box", halfExtents=vec3(round(w * 0.08, 2), round(l * 0.35, 2), round(d * 0.25, 2)),
                  position=vec3(round(w * 0.4, 1), round(l * 0.2, 1), round(d * 0.1, 1))),
            _prim("box", halfExtents=vec3(round(w * 0.08, 2), round(l * 0.35, 2), round(d * 0.25, 2)),
                  position=vec3(round(-w * 0.4, 1), round(l * 0.2, 1), round(d * 0.1, 1))),
            _prim("ellipsoid", radii=vec3(round(w * 0.08, 2), round(l * 0.07, 2), round(d * 0.15, 2)),
                  position=vec3(round(w * 0.42, 1), round(l * 0.42, 1), round(-d * 0.12, 1))),
            _prim("ellipsoid", radii=vec3(round(w * 0.08, 2), round(l * 0.07, 2), round(d * 0.15, 2)),
                  position=vec3(round(-w * 0.42, 1), round(l * 0.42, 1), round(-d * 0.12, 1))),
            _prim("capsule", radius=round(max(d * 0.12, 0.08), 2), height=round(l * 0.22, 2),
                  position=vec3(round(w * 0.28, 1), round(l * 0.36, 1), round(d * 0.18, 1))),
            _prim("capsule", radius=round(max(d * 0.12, 0.08), 2), height=round(l * 0.22, 2),
                  position=vec3(round(-w * 0.28, 1), round(l * 0.36, 1), round(d * 0.18, 1))),
            _prim("ellipsoid", radii=vec3(round(w * 0.12, 2), round(l * 0.08, 2), round(d * 0.18, 2)),
                  position=vec3(0, round(-l * 0.1, 1), round(d * 0.62, 1))),
        ])

    if "Sphenoid" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w * 0.2, 2), round(l * 0.3, 2), round(d * 0.25, 2)),
                  position=vec3(0, 0, 0)),
            _prim("box", halfExtents=vec3(round(w * 0.35, 2), round(l * 0.15, 2), round(d * 0.12, 2)),
                  position=vec3(0, round(-l * 0.1, 1), 0)),
            _prim("capsule", radius=round(max(d * 0.1, 0.08), 2), height=round(l * 0.38, 2),
                  position=vec3(round(-w * 0.18, 2), round(l * 0.18, 2), round(-d * 0.08, 2))),
            _prim("capsule", radius=round(max(d * 0.1, 0.08), 2), height=round(l * 0.38, 2),
                  position=vec3(round(w * 0.18, 2), round(l * 0.18, 2), round(-d * 0.08, 2))),
        ])

    if "Hyoid" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w * 0.35, 2), round(l * 0.2, 2), round(d * 0.3, 2)),
                  position=vec3(0, 0, 0)),
            _prim("cylinder", radiusTop=round(d * 0.15, 2), radiusBottom=round(d * 0.15, 2),
                  height=round(l * 0.3, 2), position=vec3(round(w * 0.3, 1), round(l * 0.15, 1), 0)),
            _prim("cylinder", radiusTop=round(d * 0.15, 2), radiusBottom=round(d * 0.15, 2),
                  height=round(l * 0.3, 2), position=vec3(round(-w * 0.3, 1), round(l * 0.15, 1), 0)),
        ])

    if any(k in name for k in ["Malleus", "Incus", "Stapes"]):
        return _op("union", [_prim("ellipsoid", radii=vec3(round(w / 2, 3), round(l / 2, 3), round(d / 2, 3)), position=vec3(0, 0, 0)), _prim("capsule", radius=round(max(d * 0.08, 0.02), 3), height=round(l * (0.3 if "Stapes" in name else 0.45), 3), position=vec3(round(w * (0.12 if "Incus" in name else 0.18), 3), round(-l * 0.12, 3), 0))])
    if "Maxilla" in name:
        side = -1 if "(R)" in name else 1
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("box", halfExtents=vec3(round(w * 0.16, 2), round(l * 0.3, 2), round(d * 0.16, 2)),
                  position=vec3(round(side * w * 0.18, 2), round(l * 0.16, 2), round(d * 0.1, 2))),
            _prim("capsule", radius=round(max(d * 0.12, 0.08), 2), height=round(w * 0.48, 2),
                  position=vec3(0, round(-l * 0.22, 2), round(d * 0.45, 2))),
        ])

    if "Zygomatic" in name:
        side = -1 if "(R)" in name else 1
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("capsule", radius=round(max(d * 0.14, 0.08), 2), height=round(w * 0.55, 2),
                  position=vec3(round(side * w * 0.22, 2), round(l * 0.04, 2), round(d * 0.18, 2))),
        ])

    if any(k in name for k in ["Inferior nasal", "Ethmoid", "Palatine"]):
        return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                      position=vec3(0, 0, 0))
    return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0))
def _csg_short_bone(l: float, w: float, d: float, name: str) -> dict:
    """CSG tree for short bones: carpals, tarsals."""
    if "Calcaneus" in name:
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w / 2, 2), round(l * 0.4, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("ellipsoid", radii=vec3(round(w * 0.35, 2), round(l * 0.2, 2), round(d * 0.4, 2)),
                  position=vec3(0, round(-l * 0.3, 1), 0)),
        ])
    if "Talus" in name:
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l * 0.35, 2), round(d * 0.4, 2)),
                  position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(min(w, d) * 0.25, 2),
                  position=vec3(0, round(l * 0.25, 1), 0)),
        ])
    if any(k in name for k in ["Scaphoid", "Navicular", "Cuneiform"]):
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w * 0.44, 2), round(l * 0.42, 2), round(d * 0.36, 2)), position=vec3(0, 0, 0)),
            _prim("sphere", radius=round(min(w, d) * 0.16, 2), position=vec3(round(w * 0.18, 2), round(l * 0.12, 2), 0)),
        ])
    if any(k in name for k in ["Lunate", "Capitate", "Cuboid"]):
        return _op("union", [
            _prim("box", halfExtents=vec3(round(w * 0.36, 2), round(l * 0.34, 2), round(d * 0.34, 2)), position=vec3(0, 0, 0)),
            _prim("ellipsoid", radii=vec3(round(w * 0.22, 2), round(l * 0.16, 2), round(d * 0.2, 2)), position=vec3(0, round(l * 0.18, 2), 0)),
        ])
    if any(k in name for k in ["Hamate", "Pisiform"]):
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w * 0.42, 2), round(l * 0.38, 2), round(d * 0.34, 2)), position=vec3(0, 0, 0)),
            _prim("capsule", radius=round(max(d * 0.12, 0.06), 2), height=round(l * 0.28, 2), position=vec3(round(w * 0.2, 2), round(-l * 0.12, 2), 0)),
        ])
    return _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0))


def _csg_sesamoid_bone(l: float, w: float, d: float, _name: str) -> dict:
    """CSG tree for sesamoid bones."""
    return _op("union", [
        _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
              position=vec3(0, 0, 0)),
        _prim("sphere", radius=round(min(w, d) * 0.15, 2),
              position=vec3(0, round(-l * 0.25, 1), round(-d * 0.2, 1))),
    ])


__all__ = [name for name in globals() if not name.startswith("_")]
