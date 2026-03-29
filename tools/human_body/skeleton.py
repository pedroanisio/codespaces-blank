from typing import NamedTuple

from .shared import *


# =============================================================================
# SKELETON — 206 bones
# =============================================================================

class BoneDef(NamedTuple):
    name: str
    classification: str
    region: str
    parent_idx: int | None
    length: float
    width: float
    depth: float
    mass: float
    pos: tuple[float, float, float]


def _build_bone_defs() -> list[BoneDef]:
    """Build the full 206-bone definition list.

    Parents can be specified as int (index), str (bone name for forward refs),
    or None (root). String parents are resolved to indices after all bones are added.
    """
    bones: list[BoneDef] = []

    def add(name: str, cls: str, region: str, parent: int | str | None,
            l: float, w: float, d: float, m: float, pos: tuple[float, float, float]) -> int:
        idx = len(bones)
        bones.append(BoneDef(name, cls, region, parent, l, w, d, m, pos))
        return idx

    # === PELVIC GIRDLE (2) + SACRUM/COCCYX (2) ===
    add("Hip bone (R)", "irregular", "appendicular_pelvic", None, 18, 14, 8, 290, (-5, 95, 0))
    add("Hip bone (L)", "irregular", "appendicular_pelvic", None, 18, 14, 8, 290, (5, 95, 0))
    add("Sacrum", "irregular", "axial_vertebral", "Hip bone (R)", 12, 10, 3, 180, (0, 90, -3))
    add("Coccyx", "irregular", "axial_vertebral", "Sacrum", 3, 2.5, 1.5, 8, (0, 87, -4))

    # === CRANIAL BONES (8) ===
    # Frontal bone → C1 atlas (forward reference resolved after build)
    add("Frontal bone", "flat", "axial_cranium", "C1 atlas", 12, 12, 0.7, 90, (0, 174, 4))
    add("Parietal bone (R)", "flat", "axial_cranium", "Frontal bone", 12, 11, 0.5, 55, (-5, 176, 0))
    add("Parietal bone (L)", "flat", "axial_cranium", "Frontal bone", 12, 11, 0.5, 55, (5, 176, 0))
    add("Temporal bone (R)", "irregular", "axial_cranium", "Parietal bone (R)", 5, 4, 0.4, 30, (-6, 170, 0))
    add("Temporal bone (L)", "irregular", "axial_cranium", "Parietal bone (L)", 5, 4, 0.4, 30, (6, 170, 0))
    add("Occipital bone", "flat", "axial_cranium", "Frontal bone", 10, 10, 0.8, 80, (0, 172, -5))
    add("Sphenoid bone", "irregular", "axial_cranium", "Frontal bone", 5, 7, 3, 30, (0, 168, 1))
    add("Ethmoid bone", "irregular", "axial_cranium", "Frontal bone", 3, 2.5, 3, 8, (0, 170, 4))

    # === FACIAL BONES (14) ===
    add("Maxilla (R)", "irregular", "axial_face", "Sphenoid bone", 4, 3, 2, 15, (-1.5, 165, 5))
    add("Maxilla (L)", "irregular", "axial_face", "Sphenoid bone", 4, 3, 2, 15, (1.5, 165, 5))
    add("Palatine bone (R)", "irregular", "axial_face", "Maxilla (R)", 2.5, 2, 0.3, 3, (-1, 164, 3))
    add("Palatine bone (L)", "irregular", "axial_face", "Maxilla (L)", 2.5, 2, 0.3, 3, (1, 164, 3))
    add("Zygomatic bone (R)", "irregular", "axial_face", "Maxilla (R)", 3, 3, 0.5, 8, (-5, 167, 5))
    add("Zygomatic bone (L)", "irregular", "axial_face", "Maxilla (L)", 3, 3, 0.5, 8, (5, 167, 5))
    add("Nasal bone (R)", "flat", "axial_face", "Frontal bone", 2.5, 0.8, 0.2, 2, (-0.4, 168, 6))
    add("Nasal bone (L)", "flat", "axial_face", "Frontal bone", 2.5, 0.8, 0.2, 2, (0.4, 168, 6))
    add("Lacrimal bone (R)", "flat", "axial_face", "Ethmoid bone", 1.5, 1, 0.1, 1, (-1.5, 169, 5))
    add("Lacrimal bone (L)", "flat", "axial_face", "Ethmoid bone", 1.5, 1, 0.1, 1, (1.5, 169, 5))
    add("Inferior nasal concha (R)", "irregular", "axial_face", "Maxilla (R)", 4, 1.5, 0.3, 2, (-1, 166, 5))
    add("Inferior nasal concha (L)", "irregular", "axial_face", "Maxilla (L)", 4, 1.5, 0.3, 2, (1, 166, 5))
    add("Vomer", "flat", "axial_face", "Sphenoid bone", 4, 3, 0.2, 3, (0, 166, 4))
    add("Mandible", "irregular", "axial_face", "Temporal bone (R)", 10, 12, 3, 80, (0, 162, 4))

    # === HYOID (1) ===
    add("Hyoid", "irregular", "axial_vertebral", "Mandible", 4, 3, 1, 3, (0, 157, 4))

    # === EAR OSSICLES (6) ===
    add("Malleus (R)", "irregular", "axial_cranium", "Temporal bone (R)", 0.8, 0.3, 0.3, 0.023, (-6, 170, 0.5))
    add("Incus (R)", "irregular", "axial_cranium", "Malleus (R)", 0.7, 0.5, 0.3, 0.030, (-6, 170, 0.3))
    add("Stapes (R)", "irregular", "axial_cranium", "Incus (R)", 0.3, 0.3, 0.2, 0.003, (-6, 170, 0.1))
    add("Malleus (L)", "irregular", "axial_cranium", "Temporal bone (L)", 0.8, 0.3, 0.3, 0.023, (6, 170, 0.5))
    add("Incus (L)", "irregular", "axial_cranium", "Malleus (L)", 0.7, 0.5, 0.3, 0.030, (6, 170, 0.3))
    add("Stapes (L)", "irregular", "axial_cranium", "Incus (L)", 0.3, 0.3, 0.2, 0.003, (6, 170, 0.1))

    # === STERNUM (1) ===
    add("Sternum", "flat", "axial_thorax", "T6 vertebra", 17, 5, 1.5, 40, (0, 130, 5))

    # === RIBS (24): R1–R12 then L1–L12 ===
    rib_lengths = [7, 10, 12, 14, 15, 16, 15, 14, 13, 12, 10, 8]
    rib_masses = [10, 12, 14, 16, 18, 20, 18, 16, 14, 12, 10, 8]
    for i in range(12):
        t_name = f"T{i+1} vertebra"
        y = 138 - i * 2.5
        add(f"Rib {i+1} (R)", "flat", "axial_thorax", t_name,
            rib_lengths[i], 1.2, 0.6, rib_masses[i], (-10, y, 0))
    for i in range(12):
        t_name = f"T{i+1} vertebra"
        y = 138 - i * 2.5
        add(f"Rib {i+1} (L)", "flat", "axial_thorax", t_name,
            rib_lengths[i], 1.2, 0.6, rib_masses[i], (10, y, 0))

    # === PECTORAL GIRDLE (4) ===
    add("Scapula (R)", "flat", "appendicular_pectoral", "T6 vertebra", 15, 10, 1, 60, (-18, 145, -5))
    add("Scapula (L)", "flat", "appendicular_pectoral", "T6 vertebra", 15, 10, 1, 60, (18, 145, -5))
    add("Clavicle (R)", "long", "appendicular_pectoral", "Sternum", 15, 1.3, 1.1, 25, (-8, 150, 3))
    add("Clavicle (L)", "long", "appendicular_pectoral", "Sternum", 15, 1.3, 1.1, 25, (8, 150, 3))

    # === UPPER LIMB LONG BONES (6) ===
    add("Humerus (R)", "long", "appendicular_upper", "Scapula (R)", 36, 2.2, 2, 200, (-23, 148, 0))
    add("Humerus (L)", "long", "appendicular_upper", "Scapula (L)", 36, 2.2, 2, 200, (23, 148, 0))
    add("Radius (R)", "long", "appendicular_upper", "Humerus (R)", 26, 1.6, 1.4, 60, (-25, 112, 2))
    add("Radius (L)", "long", "appendicular_upper", "Humerus (L)", 26, 1.6, 1.4, 60, (25, 112, 2))
    add("Ulna (R)", "long", "appendicular_upper", "Humerus (R)", 28, 1.5, 1.3, 65, (-24, 112, -1))
    add("Ulna (L)", "long", "appendicular_upper", "Humerus (L)", 28, 1.5, 1.3, 65, (24, 112, -1))

    # === LOWER LIMB LONG BONES (8) ===
    add("Femur (R)", "long", "appendicular_lower", "Hip bone (R)", 45, 3.2, 2.8, 450, (-9, 92, 0))
    add("Femur (L)", "long", "appendicular_lower", "Hip bone (L)", 45, 3.2, 2.8, 450, (9, 92, 0))
    add("Patella (R)", "sesamoid", "appendicular_lower", "Femur (R)", 4, 4.5, 2, 25, (-9, 50, 3))
    add("Patella (L)", "sesamoid", "appendicular_lower", "Femur (L)", 4, 4.5, 2, 25, (9, 50, 3))
    add("Tibia (R)", "long", "appendicular_lower", "Femur (R)", 40, 2.8, 2.4, 340, (-9, 47, 0))
    add("Tibia (L)", "long", "appendicular_lower", "Femur (L)", 40, 2.8, 2.4, 340, (9, 47, 0))
    add("Fibula (R)", "long", "appendicular_lower", "Tibia (R)", 38, 1.2, 1, 55, (-12, 47, 0))
    add("Fibula (L)", "long", "appendicular_lower", "Tibia (L)", 38, 1.2, 1, 55, (12, 47, 0))

    # === LUMBAR VERTEBRAE L5–L1 (5) ===
    for i, level in enumerate(range(5, 0, -1)):
        parent = "Sacrum" if i == 0 else f"L{level + 1} vertebra"
        y = 95 + i * 3.6
        add(f"L{level} vertebra", "irregular", "axial_vertebral", parent,
            3.2, 5, 3.5, 40, (0, y, -2))

    # === THORACIC VERTEBRAE T12–T1 (12) ===
    for i, level in enumerate(range(12, 0, -1)):
        parent = "L1 vertebra" if i == 0 else f"T{level + 1} vertebra"
        y = 113 + i * 2.3
        add(f"T{level} vertebra", "irregular", "axial_vertebral", parent,
            2.3, 4.5, 3, 23, (0, y, -2))

    # === CERVICAL VERTEBRAE C7–C1 (7) ===
    for i, level in enumerate(range(7, 0, -1)):
        name = f"C{level} vertebra" if level > 2 else ("C2 axis" if level == 2 else "C1 atlas")
        parent = "T1 vertebra" if i == 0 else (
            f"C{level + 1} vertebra" if level + 1 > 2 else ("C2 axis" if level + 1 == 2 else "C1 atlas")
        )
        y = 155 + i * 1.7
        add(name, "irregular", "axial_vertebral", parent,
            1.7, 3, 2.5, 11, (0, y, 0))

    # === HAND R (27 bones: 8 carpals + 5 metacarpals + 14 phalanges) ===
    _add_hand(bones, add, "R", "Radius (R)", -26, 86)

    # === HAND L (27 bones) ===
    _add_hand(bones, add, "L", "Radius (L)", 26, 86)

    # === FOOT R (26 bones: 7 tarsals + 5 metatarsals + 14 phalanges) ===
    _add_foot(bones, add, "R", "Tibia (R)", -9, 0)

    # === FOOT L (26 bones) ===
    _add_foot(bones, add, "L", "Tibia (L)", 9, 0)

    # --- Resolve name-based parents to indices ---
    name_to_idx: dict[str, int] = {b.name: i for i, b in enumerate(bones)}
    resolved: list[BoneDef] = []
    for b in bones:
        if isinstance(b.parent_idx, str):
            pidx = name_to_idx.get(b.parent_idx)
            if pidx is None:
                raise ValueError(f"Bone '{b.name}' references unknown parent '{b.parent_idx}'")
            resolved.append(b._replace(parent_idx=pidx))
        else:
            resolved.append(b)

    # --- Validate parent DAG: every parent index must be valid ---
    for i, b in enumerate(resolved):
        assert b.parent_idx is None or (0 <= b.parent_idx < len(resolved)), \
            f"Bone {i} ({b.name}): invalid parent index {b.parent_idx}"

    return resolved


def _add_hand(bones: list, add, side: str, radius_parent: int | str, x: float, y: float) -> None:
    """Add 27 hand bones (8 carpals + 5 metacarpals + 14 phalanges)."""
    sign = -1 if side == "R" else 1
    start = len(bones)

    # Proximal carpal row (4) — attach to radius
    add(f"Scaphoid ({side})", "short", "appendicular_upper", radius_parent, 2.5, 1.5, 1.2, 5, (x, y, 2))
    add(f"Lunate ({side})", "short", "appendicular_upper", radius_parent, 2, 1.5, 1.2, 4, (x + sign, y, 1.5))
    add(f"Triquetrum ({side})", "short", "appendicular_upper", start + 1, 1.8, 1.5, 1.2, 3.5, (x + sign * 2, y, 1))
    add(f"Pisiform ({side})", "short", "appendicular_upper", start + 2, 1.2, 1, 0.8, 1.5, (x + sign * 2.5, y, 0.5))

    # Distal carpal row (4) — attach to proximal row
    add(f"Trapezium ({side})", "short", "appendicular_upper", start, 2, 1.5, 1.5, 4, (x - sign, y - 2, 2.5))
    add(f"Trapezoid ({side})", "short", "appendicular_upper", start, 1.5, 1.2, 1.2, 3, (x, y - 2, 2))
    add(f"Capitate ({side})", "short", "appendicular_upper", start + 1, 2.5, 1.5, 1.5, 5, (x + sign, y - 2, 1.5))
    add(f"Hamate ({side})", "short", "appendicular_upper", start + 2, 2, 1.5, 1.5, 4.5, (x + sign * 2, y - 2, 1))

    # Metacarpals I–V (5)
    mc_labels = ["I", "II", "III", "IV", "V"]
    mc_parents = [start + 4, start + 5, start + 6, start + 7, start + 7]  # trapezium, trapezoid, capitate, hamate, hamate
    mc_lengths = [4.5, 7, 6.5, 6, 5.5]
    for j in range(5):
        xoff = x + sign * (-1 + j * 1)
        add(f"Metacarpal {mc_labels[j]} ({side})", "long", "appendicular_upper", mc_parents[j],
            mc_lengths[j], 0.8, 0.6, 6, (xoff, y - 5 - j * 0.3, 2.5 - j * 0.3))

    mc_start = start + 8  # index of Metacarpal I

    # Phalanges (14): thumb has 2 (PP, DP), fingers have 3 (PP, MP, DP)
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Little"]
    for j in range(5):
        mc_idx = mc_start + j
        xoff = x + sign * (-1 + j * 1)
        ybase = y - 10 - j * 0.3
        # Proximal phalanx
        pp_idx = add(f"{finger_names[j]} proximal phalanx ({side})", "long", "appendicular_upper",
                      mc_idx, 4 if j == 0 else 4.5, 0.6, 0.5, 3, (xoff, ybase, 2.5 - j * 0.3))
        if j == 0:
            # Thumb: distal phalanx only (2 total)
            add(f"Thumb distal phalanx ({side})", "long", "appendicular_upper",
                pp_idx, 2.5, 0.5, 0.4, 1.5, (xoff, ybase - 4, 2.5))
        else:
            # Fingers: middle + distal (3 total)
            mp_idx = add(f"{finger_names[j]} middle phalanx ({side})", "long", "appendicular_upper",
                          pp_idx, 3, 0.5, 0.4, 2, (xoff, ybase - 4.5, 2.5 - j * 0.3))
            add(f"{finger_names[j]} distal phalanx ({side})", "long", "appendicular_upper",
                mp_idx, 2.2, 0.4, 0.3, 1, (xoff, ybase - 7.5, 2.5 - j * 0.3))


def _add_foot(bones: list, add, side: str, tibia_parent: int | str, x: float, y: float) -> None:
    """Add 26 foot bones (7 tarsals + 5 metatarsals + 14 phalanges)."""
    sign = -1 if side == "R" else 1
    start = len(bones)

    # Tarsals (7)
    add(f"Calcaneus ({side})", "short", "appendicular_lower", tibia_parent, 8, 4, 4.5, 60, (x, y + 1, -2))
    add(f"Talus ({side})", "short", "appendicular_lower", tibia_parent, 6, 4, 3, 35, (x, y + 3, 2))
    add(f"Navicular ({side})", "short", "appendicular_lower", start + 1, 3.5, 2.5, 1.5, 12, (x - sign, y + 2, 5))
    add(f"Cuboid ({side})", "short", "appendicular_lower", start, 3, 2.5, 2, 10, (x + sign * 2, y + 1, 5))
    add(f"Medial cuneiform ({side})", "short", "appendicular_lower", start + 2, 3, 2, 1.5, 6, (x - sign, y + 1, 7))
    add(f"Intermediate cuneiform ({side})", "short", "appendicular_lower", start + 2, 2.5, 1.5, 1.5, 4, (x, y + 1, 7))
    add(f"Lateral cuneiform ({side})", "short", "appendicular_lower", start + 2, 2.5, 2, 1.5, 5, (x + sign, y + 1, 7))

    # Metatarsals I–V (5)
    mt_parents = [start + 4, start + 5, start + 6, start + 3, start + 3]
    mt_lengths = [6.5, 7.5, 7, 6.5, 6]
    mt_labels = ["I", "II", "III", "IV", "V"]
    for j in range(5):
        xoff = x + sign * (-1.5 + j * 0.8)
        add(f"Metatarsal {mt_labels[j]} ({side})", "long", "appendicular_lower", mt_parents[j],
            mt_lengths[j], 1, 0.8, 8, (xoff, y, 10 + j * 0.3))

    mt_start = start + 7  # index of Metatarsal I

    # Phalanges (14): big toe has 2 (PP, DP), toes 2–5 have 3 (PP, MP, DP)
    toe_names = ["Hallux", "Second toe", "Third toe", "Fourth toe", "Fifth toe"]
    for j in range(5):
        mt_idx = mt_start + j
        xoff = x + sign * (-1.5 + j * 0.8)
        zbase = 15 + j * 0.3
        pp_idx = add(f"{toe_names[j]} proximal phalanx ({side})", "long", "appendicular_lower",
                      mt_idx, 3 if j == 0 else 2.5, 0.7, 0.5, 2, (xoff, y, zbase))
        if j == 0:
            add(f"Hallux distal phalanx ({side})", "long", "appendicular_lower",
                pp_idx, 2.5, 0.6, 0.5, 1.5, (xoff, y, zbase + 3))
        else:
            mp_idx = add(f"{toe_names[j]} middle phalanx ({side})", "long", "appendicular_lower",
                          pp_idx, 1.5, 0.5, 0.4, 0.8, (xoff, y, zbase + 2.5))
            add(f"{toe_names[j]} distal phalanx ({side})", "long", "appendicular_lower",
                mp_idx, 1.2, 0.4, 0.3, 0.5, (xoff, y, zbase + 4))


BONE_DEFS = _build_bone_defs()
assert len(BONE_DEFS) == 206, f"Expected 206 bones, got {len(BONE_DEFS)}"


def gen_skeleton(r: Reg, weight: float, height: float) -> list[dict]:
    """Generate skeleton with proportions-driven mass scaling and inertial properties.

    Bone masses in BONE_DEFS are for a 75 kg, 175 cm reference male (ICRP 89, 2002).
    All masses scale linearly by (weight / 75), dimensions by (height / 175).

    Known simplifications:
      - Mass scaling is linear (weight ratio), not volumetric (ds³). This is valid
        for body compositions near the 75 kg reference but diverges at extremes
        because bone volume scales cubically with height while mass is scaled linearly.
        ICRP 89 does not provide per-bone density data to support volumetric scaling.
      - Inertia tensors are expressed in the bone's local frame (pre-rotation).
        Downstream consumers that need world-frame inertia must apply R·I·Rᵀ using
        the bone's rotation from the transform.
      - centerOfMass is (0,0,0) for all bones — geometric center of the ellipsoid
        approximation. For irregular bones (hip, scapula, mandible) the true CoM is
        offset, but per-bone CoM data is not available in the reference dataset.

    Inertia tensor: uniform-density ellipsoid approximation.
      I_xx = m/5 * (b² + c²) where a=w/2, b=l/2, c=d/2
      Reference: Goldstein, Classical Mechanics, 3rd ed., Ch. 5.
    """
    REF_W = 75.0
    REF_H = 175.0
    ms = weight / REF_W
    ds = height / REF_H

    # Anatomical rotations (Euler XYZ degrees) for non-long bones.
    # CSG shapes are authored with Y-up as the bone's long axis.
    # These rotations orient them correctly in world space.
    # Convention: (rx, ry, rz) in degrees, applied as Euler XYZ intrinsic.
    _ROT: dict[str, tuple[float, float, float]] = {}

    # Ribs: rotate ~90° around Z so capsule Y-axis points laterally.
    # In Euler XYZ: +90° Z rotates local Y toward −X (leftward in world).
    # R ribs at negative X need local Y pointing toward −X: Z = +90°.
    # L ribs at positive X need local Y pointing toward +X: Z = −90°.
    # Forward tilt via X rotation: lower ribs tilt more anteriorly.
    for ri in range(12):
        tilt_fwd = 10 + ri * 3
        _ROT[f"Rib {ri+1} (R)"] = (tilt_fwd, 0, -90)  # local Y → +X → toward body (rib goes lateral-right)
        _ROT[f"Rib {ri+1} (L)"] = (tilt_fwd, 0, 90)   # local Y → −X → toward body (rib goes lateral-left)

    # Scapulae: thin plates lying flat on the back (long axis vertical, thin axis posterior)
    # Default CSG has Y=long axis which is correct, just needs slight forward tilt
    _ROT["Scapula (R)"] = (15, -10, 0)
    _ROT["Scapula (L)"] = (15, 10, 0)

    # Cranial bones: thin curved plates. CSG ellipsoid Y=long axis.
    # These are already roughly correct since they're at skull positions,
    # but parietal bones should tilt outward slightly
    _ROT["Parietal bone (R)"] = (0, 0, 15)
    _ROT["Parietal bone (L)"] = (0, 0, -15)

    # Sternum: vertical plate, thin in Z — already correct orientation

    for _ in BONE_DEFS:
        r.bone_ids.append(uid())
    bones = []
    for i, (name, cls, region, parent_idx, length, width, depth, mass, pos) in enumerate(BONE_DEFS):
        sl = round(length * ds, 2)
        sw = round(width * ds, 2)
        sd = round(depth * ds, 2)
        sm = max(0.01, round(mass * ms, 2))
        sp = (round(pos[0] * ds, 1), round(pos[1] * ds, 1), round(pos[2] * ds, 1))
        a, b, c = sw / 2, sl / 2, sd / 2
        ixx = round(sm / 5 * (b * b + c * c), 2)
        iyy = round(sm / 5 * (a * a + c * c), 2)
        izz = round(sm / 5 * (a * a + b * b), 2)
        rot = _ROT.get(name, (0, 0, 0))
        bone: dict[str, Any] = {
            "id": r.bone_ids[i], "name": name, "classification": cls, "region": region,
            "transform": tf(*sp, *rot),
            "length": sl, "width": sw, "depth": sd, "mass": sm,
            "centerOfMass": vec3(0, 0, 0),
            "inertiaTensor": sym_tensor(ixx, iyy, izz),
            "parentBoneId": r.bone_ids[parent_idx] if parent_idx is not None else None,
        }
        bones.append(bone)
    return bones


__all__ = [name for name in globals() if not name.startswith("_")]
