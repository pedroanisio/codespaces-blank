from ..shared import *
from ..skeleton import *

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
    # Frontal bone: vault plate with supraorbital ridges and glabella.
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

    # Temporal bone: thin cranial plate with zygomatic projection and mastoid bulge.
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

    # Cranial bones: curved ellipsoid shell
    if any(k in name for k in ["Parietal", "Occipital"]):
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

    # Sphenoid: body + broad greater wings + pterygoid processes.
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

    # Maxilla: body with frontal and alveolar processes.
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

    # Zygomatic: cheek prominence with an arch-like lateral process.
    if "Zygomatic" in name:
        side = -1 if "(R)" in name else 1
        return _op("union", [
            _prim("ellipsoid", radii=vec3(round(w / 2, 2), round(l / 2, 2), round(d / 2, 2)),
                  position=vec3(0, 0, 0)),
            _prim("capsule", radius=round(max(d * 0.14, 0.08), 2), height=round(w * 0.55, 2),
                  position=vec3(round(side * w * 0.22, 2), round(l * 0.04, 2), round(d * 0.18, 2))),
        ])

    # Inferior concha, ethmoid, palatine — simple irregular facial elements.
    if any(k in name for k in ["Inferior nasal", "Ethmoid", "Palatine"]):
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


__all__ = [name for name in globals() if not name.startswith("__")]
