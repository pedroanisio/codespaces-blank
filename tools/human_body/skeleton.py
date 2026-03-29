from .shared import *

# =============================================================================
# SKELETON — 206 bones
# =============================================================================

# BoneDef: (name, classification, region, parent_idx, length, width, depth, mass, (x,y,z))
BoneDef = tuple[str, str, str, int | None, float, float, float, float, tuple[float, float, float]]

def _build_bone_defs() -> list[BoneDef]:
    """Build the full 206-bone definition list."""
    bones: list[BoneDef] = []

    def add(name: str, cls: str, region: str, parent: int | None,
            l: float, w: float, d: float, m: float, pos: tuple[float, float, float]) -> int:
        idx = len(bones)
        bones.append((name, cls, region, parent, l, w, d, m, pos))
        return idx

    # === PELVIC GIRDLE (2) + SACRUM/COCCYX (2) ===
    add("Hip bone (R)", "irregular", "appendicular_pelvic", None, 18, 14, 8, 290, (-5, 95, 0))       # 0
    add("Hip bone (L)", "irregular", "appendicular_pelvic", None, 18, 14, 8, 290, (5, 95, 0))        # 1
    add("Sacrum", "irregular", "axial_vertebral", 0, 12, 10, 3, 180, (0, 90, -3))                     # 2
    add("Coccyx", "irregular", "axial_vertebral", 2, 3, 2.5, 1.5, 8, (0, 87, -4))                    # 3

    # === CRANIAL BONES (8) ===
    add("Frontal bone", "flat", "axial_cranium", None, 12, 12, 0.7, 90, (0, 174, 4))                  # 4  parent set later→C1
    add("Parietal bone (R)", "flat", "axial_cranium", 4, 12, 11, 0.5, 55, (-5, 176, 0))               # 5
    add("Parietal bone (L)", "flat", "axial_cranium", 4, 12, 11, 0.5, 55, (5, 176, 0))                # 6
    add("Temporal bone (R)", "irregular", "axial_cranium", 5, 5, 4, 0.4, 30, (-6, 170, 0))             # 7
    add("Temporal bone (L)", "irregular", "axial_cranium", 6, 5, 4, 0.4, 30, (6, 170, 0))              # 8
    add("Occipital bone", "flat", "axial_cranium", 4, 10, 10, 0.8, 80, (0, 172, -5))                  # 9
    add("Sphenoid bone", "irregular", "axial_cranium", 4, 5, 7, 3, 30, (0, 168, 1))                   # 10
    add("Ethmoid bone", "irregular", "axial_cranium", 4, 3, 2.5, 3, 8, (0, 170, 4))                   # 11

    # === FACIAL BONES (14) ===
    add("Maxilla (R)", "irregular", "axial_face", 10, 4, 3, 2, 15, (-1.5, 165, 5))                    # 12
    add("Maxilla (L)", "irregular", "axial_face", 10, 4, 3, 2, 15, (1.5, 165, 5))                     # 13
    add("Palatine bone (R)", "irregular", "axial_face", 12, 2.5, 2, 0.3, 3, (-1, 164, 3))             # 14
    add("Palatine bone (L)", "irregular", "axial_face", 13, 2.5, 2, 0.3, 3, (1, 164, 3))              # 15
    add("Zygomatic bone (R)", "irregular", "axial_face", 12, 3, 3, 0.5, 8, (-5, 167, 5))              # 16
    add("Zygomatic bone (L)", "irregular", "axial_face", 13, 3, 3, 0.5, 8, (5, 167, 5))               # 17
    add("Nasal bone (R)", "flat", "axial_face", 4, 2.5, 0.8, 0.2, 2, (-0.4, 168, 6))                 # 18
    add("Nasal bone (L)", "flat", "axial_face", 4, 2.5, 0.8, 0.2, 2, (0.4, 168, 6))                  # 19
    add("Lacrimal bone (R)", "flat", "axial_face", 11, 1.5, 1, 0.1, 1, (-1.5, 169, 5))                # 20
    add("Lacrimal bone (L)", "flat", "axial_face", 11, 1.5, 1, 0.1, 1, (1.5, 169, 5))                 # 21
    add("Inferior nasal concha (R)", "irregular", "axial_face", 12, 4, 1.5, 0.3, 2, (-1, 166, 5))     # 22
    add("Inferior nasal concha (L)", "irregular", "axial_face", 13, 4, 1.5, 0.3, 2, (1, 166, 5))      # 23
    add("Vomer", "flat", "axial_face", 10, 4, 3, 0.2, 3, (0, 166, 4))                                 # 24
    add("Mandible", "irregular", "axial_face", 7, 10, 12, 3, 80, (0, 162, 4))                          # 25

    # === HYOID (1) ===
    add("Hyoid", "irregular", "axial_vertebral", 25, 4, 3, 1, 3, (0, 157, 4))                          # 26

    # === EAR OSSICLES (6) ===
    add("Malleus (R)", "irregular", "axial_cranium", 7, 0.8, 0.3, 0.3, 0.023, (-6, 170, 0.5))         # 27
    add("Incus (R)", "irregular", "axial_cranium", 27, 0.7, 0.5, 0.3, 0.030, (-6, 170, 0.3))          # 28
    add("Stapes (R)", "irregular", "axial_cranium", 28, 0.3, 0.3, 0.2, 0.003, (-6, 170, 0.1))         # 29
    add("Malleus (L)", "irregular", "axial_cranium", 8, 0.8, 0.3, 0.3, 0.023, (6, 170, 0.5))          # 30
    add("Incus (L)", "irregular", "axial_cranium", 30, 0.7, 0.5, 0.3, 0.030, (6, 170, 0.3))           # 31
    add("Stapes (L)", "irregular", "axial_cranium", 31, 0.3, 0.3, 0.2, 0.003, (6, 170, 0.1))          # 32

    # === STERNUM (1) ===
    _t6 = 81 + 6  # T6 vertebra index (will be built below)
    add("Sternum", "flat", "axial_thorax", _t6, 17, 5, 1.5, 40, (0, 130, 5))                          # 33

    # === RIBS (24): R1–R12 then L1–L12 ===
    rib_lengths = [7, 10, 12, 14, 15, 16, 15, 14, 13, 12, 10, 8]
    rib_masses = [10, 12, 14, 16, 18, 20, 18, 16, 14, 12, 10, 8]
    for i in range(12):
        t_vert = 81 + (11 - i)  # T1→92, T2→91, ... T12→81 — rib attaches to its numbered thoracic
        y = 138 - i * 2.5
        add(f"Rib {i+1} (R)", "flat", "axial_thorax", t_vert,
            rib_lengths[i], 1.2, 0.6, rib_masses[i], (-10, y, 0))                                      # 34–45
    for i in range(12):
        t_vert = 81 + (11 - i)
        y = 138 - i * 2.5
        add(f"Rib {i+1} (L)", "flat", "axial_thorax", t_vert,
            rib_lengths[i], 1.2, 0.6, rib_masses[i], (10, y, 0))                                       # 46–57

    # === PECTORAL GIRDLE (4) ===
    add("Scapula (R)", "flat", "appendicular_pectoral", _t6, 15, 10, 1, 60, (-18, 145, -5))            # 58
    add("Scapula (L)", "flat", "appendicular_pectoral", _t6, 15, 10, 1, 60, (18, 145, -5))             # 59
    add("Clavicle (R)", "long", "appendicular_pectoral", 33, 15, 1.3, 1.1, 25, (-8, 150, 3))          # 60
    add("Clavicle (L)", "long", "appendicular_pectoral", 33, 15, 1.3, 1.1, 25, (8, 150, 3))           # 61

    # === UPPER LIMB LONG BONES (6) ===
    add("Humerus (R)", "long", "appendicular_upper", 58, 36, 2.2, 2, 200, (-23, 148, 0))              # 62
    add("Humerus (L)", "long", "appendicular_upper", 59, 36, 2.2, 2, 200, (23, 148, 0))               # 63
    add("Radius (R)", "long", "appendicular_upper", 62, 26, 1.6, 1.4, 60, (-25, 112, 2))              # 64
    add("Radius (L)", "long", "appendicular_upper", 63, 26, 1.6, 1.4, 60, (25, 112, 2))               # 65
    add("Ulna (R)", "long", "appendicular_upper", 62, 28, 1.5, 1.3, 65, (-24, 112, -1))               # 66
    add("Ulna (L)", "long", "appendicular_upper", 63, 28, 1.5, 1.3, 65, (24, 112, -1))                # 67

    # === LOWER LIMB LONG BONES (8) ===
    add("Femur (R)", "long", "appendicular_lower", 0, 45, 3.2, 2.8, 450, (-9, 92, 0))                 # 68
    add("Femur (L)", "long", "appendicular_lower", 1, 45, 3.2, 2.8, 450, (9, 92, 0))                  # 69
    add("Patella (R)", "sesamoid", "appendicular_lower", 68, 4, 4.5, 2, 25, (-9, 50, 3))              # 70
    add("Patella (L)", "sesamoid", "appendicular_lower", 69, 4, 4.5, 2, 25, (9, 50, 3))               # 71
    add("Tibia (R)", "long", "appendicular_lower", 68, 40, 2.8, 2.4, 340, (-9, 47, 0))                # 72
    add("Tibia (L)", "long", "appendicular_lower", 69, 40, 2.8, 2.4, 340, (9, 47, 0))                 # 73
    add("Fibula (R)", "long", "appendicular_lower", 72, 38, 1.2, 1, 55, (-12, 47, 0))                 # 74
    add("Fibula (L)", "long", "appendicular_lower", 73, 38, 1.2, 1, 55, (12, 47, 0))                  # 75

    # === LUMBAR VERTEBRAE L5–L1 (5) ===
    for i, level in enumerate(range(5, 0, -1)):
        parent = 2 if i == 0 else (76 + i - 1)  # Sacrum or previous lumbar
        y = 95 + i * 3.6
        add(f"L{level} vertebra", "irregular", "axial_vertebral", parent,
            3.2, 5, 3.5, 40, (0, y, -2))                                                               # 76–80

    # === THORACIC VERTEBRAE T12–T1 (12) ===
    for i, level in enumerate(range(12, 0, -1)):
        parent = 80 if i == 0 else (81 + i - 1)  # L1 or previous thoracic
        y = 113 + i * 2.3
        add(f"T{level} vertebra", "irregular", "axial_vertebral", parent,
            2.3, 4.5, 3, 23, (0, y, -2))                                                               # 81–92

    # === CERVICAL VERTEBRAE C7–C1 (7) ===
    for i, level in enumerate(range(7, 0, -1)):
        name = f"C{level} vertebra" if level > 2 else ("C2 axis" if level == 2 else "C1 atlas")
        parent = 92 if i == 0 else (93 + i - 1)  # T1 or previous cervical
        y = 155 + i * 1.7
        add(name, "irregular", "axial_vertebral", parent,
            1.7, 3, 2.5, 11, (0, y, 0))                                                                # 93–99

    # === HAND R (27 bones: 8 carpals + 5 metacarpals + 14 phalanges) ===
    _add_hand(bones, add, "R", 64, -26, 86)  # parent=Radius R, x=-26, y=86                            # 100–126

    # === HAND L (27 bones) ===
    _add_hand(bones, add, "L", 65, 26, 86)                                                              # 127–153

    # === FOOT R (26 bones: 7 tarsals + 5 metatarsals + 14 phalanges) ===
    _add_foot(bones, add, "R", 72, -9, 0)  # parent=Tibia R                                             # 154–179

    # === FOOT L (26 bones) ===
    _add_foot(bones, add, "L", 73, 9, 0)                                                                # 180–205

    # Fix frontal bone parent → C1 atlas (idx 99)
    bones[4] = (bones[4][0], bones[4][1], bones[4][2], 99, *bones[4][4:])

    return bones


def _add_hand(bones: list, add, side: str, radius_idx: int, x: float, y: float) -> None:
    """Add 27 hand bones (8 carpals + 5 metacarpals + 14 phalanges)."""
    sign = -1 if side == "R" else 1
    start = len(bones)

    # Proximal carpal row (4) — attach to radius
    add(f"Scaphoid ({side})", "short", "appendicular_upper", radius_idx, 2.5, 1.5, 1.2, 5, (x, y, 2))
    add(f"Lunate ({side})", "short", "appendicular_upper", radius_idx, 2, 1.5, 1.2, 4, (x + sign, y, 1.5))
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


def _add_foot(bones: list, add, side: str, tibia_idx: int, x: float, y: float) -> None:
    """Add 26 foot bones (7 tarsals + 5 metatarsals + 14 phalanges)."""
    sign = -1 if side == "R" else 1
    start = len(bones)

    # Tarsals (7)
    add(f"Calcaneus ({side})", "short", "appendicular_lower", tibia_idx, 8, 4, 4.5, 60, (x, y + 1, -2))
    add(f"Talus ({side})", "short", "appendicular_lower", tibia_idx, 6, 4, 3, 35, (x, y + 3, 2))
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

    Inertia tensor: uniform-density ellipsoid approximation.
      I_xx = m/5 * (b^2 + c^2) where a=w/2, b=l/2, c=d/2
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


__all__ = [name for name in globals() if not name.startswith("__")]
