from .shared import *
from .skeleton import *
from .joints_data import *

def gen_joints(r: Reg) -> list[dict]:
    """Generate joints: 44 named joints from JOINT_DEFS + ~58 programmatic hand/foot joints.

    Joint position is computed as the midpoint between the primary connected bones.
    Hand joints (MCP, PIP, DIP, CMC, IP) and foot joints (MTP, PIP, DIP, IP) are
    generated programmatically from bone index arrays to avoid 58 static entries.

    Hand ROM from: Hume et al., J Hand Surg Am 15(2):240-243, 1990.
    Foot ROM from: Nawoczenski et al., Foot Ankle 9(5):232-238, 1989.
    """
    joints = []

    def _add_joint(name, jtype, bone_idxs, dof, axes=None, limits=None):
        jid = uid()
        r.joint_ids.append(jid)
        bone_positions = [BONE_DEFS[i][8] for i in bone_idxs]
        b0, b1 = bone_positions[0], bone_positions[1]
        jx = (b0[0] + b1[0]) / 2
        jy = (b0[1] + b1[1]) / 2
        jz = (b0[2] + b1[2]) / 2
        j: dict[str, Any] = {
            "id": jid, "name": name, "type": jtype,
            "transform": tf(round(jx, 1), round(jy, 1), round(jz, 1)),
            "connectedBoneIds": [r.bone_ids[i] for i in bone_idxs],
            "degreesOfFreedom": dof,
        }
        if axes:
            j["axes"] = axes
        if limits:
            j["limits"] = limits
        joints.append(j)

    # Static named joints from JOINT_DEFS (44)
    for name, jtype, bone_idxs, dof, axes, limits in JOINT_DEFS:
        _add_joint(name, jtype, bone_idxs, dof, axes, limits)

    # === HAND JOINTS (15 per side × 2 = 30) ===
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Little"]
    for side, mc, pp, mp, dp, trap in [
        ("R", _HR_MC, _HR_PP, _HR_MP, _HR_DP, _HR_TRAP),
        ("L", [i + 27 for i in _HR_MC], [i + 27 for i in _HR_PP],
         [None if v is None else v + 27 for v in _HR_MP],
         [i + 27 for i in _HR_DP], _HR_TRAP + 27),
    ]:
        # CMC thumb — saddle joint
        _add_joint(f"CMC thumb ({side})", "saddle", [trap, mc[0]], 2, limits={
            "flexionExtension": {"min": -15, "max": 60},
            "abductionAdduction": {"min": -10, "max": 50}})
        # MCP joints (5): condyloid for fingers, condyloid for thumb
        for d in range(5):
            fe_max = 60 if d == 0 else 90
            _add_joint(f"MCP {finger_names[d]} ({side})", "condyloid", [mc[d], pp[d]], 2, limits={
                "flexionExtension": {"min": -30 if d > 0 else -10, "max": fe_max},
                "abductionAdduction": {"min": -20, "max": 20}})
        # IP thumb — hinge
        _add_joint(f"IP thumb ({side})", "hinge", [pp[0], dp[0]], 1, limits={
            "flexionExtension": {"min": 0, "max": 80}})
        # PIP joints (4): hinge — index through little
        for d in range(1, 5):
            _add_joint(f"PIP {finger_names[d]} ({side})", "hinge", [pp[d], mp[d]], 1, limits={
                "flexionExtension": {"min": 0, "max": 110}})
        # DIP joints (4): hinge — index through little
        for d in range(1, 5):
            _add_joint(f"DIP {finger_names[d]} ({side})", "hinge", [mp[d], dp[d]], 1, limits={
                "flexionExtension": {"min": 0, "max": 80}})

    # === FOOT JOINTS (14 per side × 2 = 28) ===
    toe_names = ["Hallux", "2nd toe", "3rd toe", "4th toe", "5th toe"]
    for side, mt, pp, mp_arr, dp in [
        ("R", _FR_MT, _FR_PP, _FR_MP, _FR_DP),
        ("L", [i + 26 for i in _FR_MT], [i + 26 for i in _FR_PP],
         [None if v is None else v + 26 for v in _FR_MP],
         [i + 26 for i in _FR_DP]),
    ]:
        # MTP joints (5): condyloid
        for d in range(5):
            fe_max = 70 if d == 0 else 40
            _add_joint(f"MTP {toe_names[d]} ({side})", "condyloid", [mt[d], pp[d]], 2, limits={
                "flexionExtension": {"min": -30, "max": fe_max},
                "abductionAdduction": {"min": -10, "max": 10}})
        # IP hallux — hinge
        _add_joint(f"IP {toe_names[0]} ({side})", "hinge", [pp[0], dp[0]], 1, limits={
            "flexionExtension": {"min": 0, "max": 60}})
        # PIP toes 2-5 (4): hinge
        for d in range(1, 5):
            _add_joint(f"PIP {toe_names[d]} ({side})", "hinge", [pp[d], mp_arr[d]], 1, limits={
                "flexionExtension": {"min": 0, "max": 40}})
        # DIP toes 2-5 (4): hinge
        for d in range(1, 5):
            _add_joint(f"DIP {toe_names[d]} ({side})", "hinge", [mp_arr[d], dp[d]], 1, limits={
                "flexionExtension": {"min": 0, "max": 30}})

    return joints
# =============================================================================
# TENDONS + MUSCLES — 94 tendons, 48 muscles
# =============================================================================

def _make_tendon(r: Reg, name: str, bone_idx: int, length: float, csa: float | None = None) -> dict:
    """Create a tendon with anatomically-derived local position.

    Instead of random placement, the local position is computed from the
    bone's dimensions (length, width, depth) and the tendon's role:
    - Origin tendons attach near the proximal end (local Y ~ +L/3)
    - Insertion tendons attach near the distal end (local Y ~ -L/3)
    - Surface offset is scaled to bone width/depth for surface placement

    The 'hint' parameter is derived from the tendon name: if it contains
    'origin', the attachment is proximal; if 'insertion', distal.
    """
    tid = uid()
    r.tendon_ids.append(tid)
    r.tendon_name_to_idx[name] = len(r.tendon_ids) - 1

    # Derive anatomical position from bone geometry
    bone_def = BONE_DEFS[bone_idx]
    b_length = bone_def[4]  # length in cm
    b_width = bone_def[5]   # width in cm
    b_depth = bone_def[6]   # depth in cm

    # Proximal vs distal heuristic based on tendon name
    is_origin = any(k in name.lower() for k in ["origin", "quadriceps", "achilles"])
    y_sign = 1.0 if is_origin else -1.0

    # Position along the bone's long axis (Y), with small surface offsets
    local_y = y_sign * b_length * random.uniform(0.2, 0.4)
    local_x = random.uniform(-0.3, 0.3) * b_width
    local_z = random.choice([-1, 1]) * random.uniform(0.2, 0.5) * b_depth

    t: dict[str, Any] = {
        "id": tid, "name": name,
        "attachedBoneId": r.bone_ids[bone_idx],
        "localPosition": vec3(round(local_x, 2), round(local_y, 2), round(local_z, 2)),
        "length": length,
    }
    if csa is not None:
        t["crossSectionalArea"] = csa
    return t
MuscleSpec = tuple[str, str, str, int, int, list[str], list[str] | None,
                   list[str], str, str, float, float, float, float, float | None,
                   tuple[float, float, float], list[str], list[str],
                   str | None, str | None, float | None, float | None]

def _bilateral(defs: list[MuscleSpec]) -> list[MuscleSpec]:
    result: list[MuscleSpec] = []
    for d in defs:
        name = d[0]
        if "(R)" in name or "(L)" in name or name in ("Rectus Abdominis", "Diaphragm"):
            result.append(d)
        else:
            r_def = list(d); l_def = list(d)
            r_def[0] = f"{name} (R)"; l_def[0] = f"{name} (L)"
            fx, fy, fz = d[15]
            l_def[15] = (-fx if fx != 0 else 0, fy, fz)
            r_antag = [n + " (R)" if not n.endswith(")") else n for n in d[16]]
            l_antag = [n.replace("(R)", "(L)") if "(R)" in n else (n + " (L)" if not n.endswith(")") else n) for n in d[16]]
            r_syn = [n + " (R)" if not n.endswith(")") else n for n in d[17]]
            l_syn = [n.replace("(R)", "(L)") if "(R)" in n else (n + " (L)" if not n.endswith(")") else n) for n in d[17]]
            r_def[16] = r_antag; l_def[16] = l_antag; r_def[17] = r_syn; l_def[17] = l_syn
            result.append(tuple(r_def)); result.append(tuple(l_def))
    return result

# =============================================================================
# MUSCLE DATA — ~160 base definitions → 320 after bilateral expansion
#
# Compact format: (name, region, arch, ob, ib, actions, spinal, nerve, L, vol, fmax, penn)
# • fdir defaults to (0,-1,0), overridden via _FDIR dict
# • artery derived from region via _ARTERY dict
# • optimalFiberLength = L × architecture-specific ratio (0.25–0.6)
# • pcsa = vol / optimalFiberLength (computed)
# • mass = vol × 1.06 (muscle density)
# • maxContractionVelocity = 5.0–8.0 L_opt/s (randomized)
# =============================================================================

_T6 = B_T12 + 6; _T4 = B_T12 + 8; _T8 = B_T12 + 4; _T1_vert = B_T1

# Hand R bone shortcuts
_HR = 100  # hand R start
_HR_TRAP, _HR_TRAPD, _HR_CAP, _HR_HAM = 104, 105, 106, 107
_HR_MC = B_HAND_R_MC  # [108..112]
_HR_PP = [113, 115, 118, 121, 124]  # proximal phalanges by digit (thumb, index, middle, ring, little)
_HR_DP = [114, 117, 120, 123, 126]  # distal phalanges

# Foot R bone shortcuts
_FR = 154  # foot R start
_FR_CALC, _FR_NAV, _FR_CUB = 154, 156, 157
_FR_MT = B_FOOT_R_MT  # [161..165]
_FR_PP = [166, 168, 171, 174, 177]  # proximal phalanges by toe
_FR_DP = [167, 170, 173, 176, 179]

# Artery by region
_ARTERY: dict[str, str] = {
    "head_and_neck": "External carotid artery", "face": "Facial artery",
    "shoulder": "Suprascapular artery", "arm_anterior": "Brachial artery",
    "arm_posterior": "Deep brachial artery", "forearm_anterior": "Ulnar artery",
    "forearm_posterior": "Posterior interosseous artery", "hand_intrinsic": "Deep palmar arch",
    "thorax_anterior": "Thoracoacromial artery", "thorax_posterior": "Intercostal arteries",
    "abdomen": "Superior epigastric artery", "back_superficial": "Transverse cervical artery",
    "back_deep": "Lumbar arteries", "hip": "Superior gluteal artery",
    "thigh_anterior": "Femoral artery", "thigh_posterior": "Deep femoral artery",
    "thigh_medial": "Obturator artery", "leg_anterior": "Anterior tibial artery",
    "leg_posterior": "Posterior tibial artery", "leg_lateral": "Peroneal artery",
    "foot_intrinsic": "Medial plantar artery",
}

# Fiber direction overrides (default is (0,-1,0))
_FDIR: dict[str, tuple] = {
    "Erector Spinae": (0, 1, 0), "Iliocostalis": (0, 1, 0), "Longissimus": (0, 1, 0), "Spinalis": (0, 1, 0),
    "Pectoralis Major": (-0.95, -0.31, 0), "Latissimus Dorsi": (-0.707, 0.707, 0),
    "Deltoid": (-0.707, -0.707, 0), "Trapezius Upper": (0, -0.8, -0.6),
    "Trapezius Middle": (-0.9, 0, -0.4), "Trapezius Lower": (-0.5, 0.7, -0.5),
    "External Oblique": (0.3, -0.9, 0.2), "Internal Oblique": (-0.3, -0.9, 0.2),
    "Transversus Abdominis": (1, 0, 0), "Serratus Anterior": (-0.8, -0.3, 0.5),
}

# Compact raw muscle data: (name, region, arch, ob, ib, actions_str, spinal_str, nerve, L, vol, fmax, penn)
_RAW: list[tuple] = [
    # === HEAD / FACE / JAW ===
    ("Masseter", "face", "multipennate", B_ZYGOMATIC_R, B_MANDIBLE, "elevation", "CN5", "Trigeminal V3", 4, 25, 800, 20),
    ("Temporalis", "face", "convergent", B_TEMPORAL_R, B_MANDIBLE, "elevation", "CN5", "Trigeminal V3", 6, 20, 600, None),
    ("Medial Pterygoid", "face", "multipennate", B_SPHENOID, B_MANDIBLE, "elevation", "CN5", "Trigeminal V3", 3, 10, 400, 15),
    ("Lateral Pterygoid", "face", "parallel", B_SPHENOID, B_MANDIBLE, "protraction", "CN5", "Trigeminal V3", 3, 8, 300, None),
    ("Digastric", "head_and_neck", "parallel", B_TEMPORAL_R, B_MANDIBLE, "depression", "CN5,CN7", "Facial VII", 10, 5, 100, None),
    ("Platysma", "face", "parallel", B_MANDIBLE, B_CLAV_R, "depression", "CN7", "Facial VII", 15, 8, 50, None),
    ("Orbicularis Oculi", "face", "circular", B_FRONTAL, B_MAXILLA_R, "flexion", "CN7", "Facial VII", 3, 3, 30, None),
    ("Frontalis", "face", "parallel", B_FRONTAL, B_FRONTAL, "elevation", "CN7", "Facial VII", 6, 4, 30, None),
    ("Buccinator", "face", "parallel", B_MAXILLA_R, B_MANDIBLE, "flexion", "CN7", "Facial VII", 4, 4, 40, None),
    ("Orbicularis Oris", "face", "circular", B_MAXILLA_R, B_MANDIBLE, "flexion", "CN7", "Facial VII", 3, 3, 30, None),
    ("Zygomaticus Major", "face", "parallel", B_ZYGOMATIC_R, B_MANDIBLE, "elevation", "CN7", "Facial VII", 5, 3, 30, None),
    ("Mentalis", "face", "parallel", B_MANDIBLE, B_MANDIBLE, "elevation", "CN7", "Facial VII", 2, 2, 20, None),
    ("Corrugator Supercilii", "face", "parallel", B_FRONTAL, B_FRONTAL, "depression", "CN7", "Facial VII", 3, 2, 20, None),
    ("Nasalis", "face", "parallel", B_MAXILLA_R, B_NASAL_R, "flexion", "CN7", "Facial VII", 2, 1, 15, None),
    # === NECK ===
    ("Sternocleidomastoid", "head_and_neck", "parallel", B_STERNUM, B_OCCIPITAL, "flexion", "C2,C3", "Spinal accessory nerve (XI)", 20, 80, 400, None),
    ("Scalene Anterior", "head_and_neck", "parallel", B_C7, B_RIB_R[0], "lateral_flexion", "C4,C5,C6", "Cervical plexus", 8, 15, 200, None),
    ("Scalene Middle", "head_and_neck", "parallel", B_C7, B_RIB_R[0], "lateral_flexion", "C3,C4,C5,C6,C7", "Cervical plexus", 9, 15, 200, None),
    ("Scalene Posterior", "head_and_neck", "parallel", B_C7, B_RIB_R[1], "lateral_flexion", "C6,C7,C8", "Cervical plexus", 7, 10, 150, None),
    ("Longus Colli", "head_and_neck", "parallel", B_C1, B_T12 + 9, "flexion", "C2,C3,C4,C5,C6", "Cervical plexus", 10, 12, 150, None),
    ("Splenius Capitis", "back_deep", "parallel", B_C7, B_OCCIPITAL, "extension", "C3,C4", "Posterior rami", 12, 30, 300, None),
    ("Splenius Cervicis", "back_deep", "parallel", _T6, B_C7, "extension", "C4,C5,C6", "Posterior rami", 12, 20, 200, None),
    ("Omohyoid", "head_and_neck", "parallel", B_SCAP_R, B_HYOID, "depression", "C1,C2,C3", "Ansa cervicalis", 12, 5, 50, None),
    ("Sternohyoid", "head_and_neck", "parallel", B_STERNUM, B_HYOID, "depression", "C1,C2,C3", "Ansa cervicalis", 10, 5, 50, None),
    ("Mylohyoid", "head_and_neck", "parallel", B_MANDIBLE, B_HYOID, "elevation", "CN5", "Trigeminal V3", 5, 5, 60, None),
    ("Thyrohyoid", "head_and_neck", "parallel", B_HYOID, B_HYOID, "depression", "C1,C2", "Ansa cervicalis", 4, 3, 30, None),
    ("Stylohyoid", "head_and_neck", "parallel", B_TEMPORAL_R, B_HYOID, "elevation", "CN7", "Facial VII", 5, 3, 30, None),
    # === TRUNK — BACK ===
    ("Trapezius Upper", "back_superficial", "convergent", B_OCCIPITAL, B_CLAV_R, "elevation", "C1,C2,C3,C4", "Spinal accessory nerve (XI)", 15, 80, 500, None),
    ("Trapezius Middle", "back_superficial", "convergent", _T6, B_SCAP_R, "retraction", "C3,C4", "Spinal accessory nerve (XI)", 15, 60, 400, None),
    ("Trapezius Lower", "back_superficial", "convergent", B_T12, B_SCAP_R, "depression", "C3,C4", "Spinal accessory nerve (XI)", 18, 50, 350, None),
    ("Latissimus Dorsi", "back_superficial", "convergent", _T6 + 1, B_HUMER_R, "extension,adduction", "C6,C7,C8", "Thoracodorsal nerve", 35, 620, 3800, None),
    ("Rhomboid Major", "back_superficial", "parallel", _T4, B_SCAP_R, "retraction", "C5", "Dorsal scapular nerve", 10, 30, 300, None),
    ("Rhomboid Minor", "back_superficial", "parallel", B_C7, B_SCAP_R, "retraction", "C5", "Dorsal scapular nerve", 6, 15, 150, None),
    ("Levator Scapulae", "back_superficial", "parallel", B_C7, B_SCAP_R, "elevation", "C3,C4,C5", "Dorsal scapular nerve", 12, 25, 250, None),
    ("Serratus Anterior", "back_superficial", "parallel", B_RIB_R[4], B_SCAP_R, "protraction", "C5,C6,C7", "Long thoracic nerve", 15, 80, 500, None),
    ("Erector Spinae", "back_deep", "parallel", B_SACRUM, B_T12, "extension", "T1,T2,T3,T4,T5,T6", "Posterior rami", 45, 520, 3600, None),
    ("Iliocostalis", "back_deep", "parallel", B_SACRUM, B_RIB_R[5], "extension", "T1,T2,T3,T4,T5,T6", "Posterior rami", 35, 200, 1500, None),
    ("Longissimus", "back_deep", "parallel", B_SACRUM, B_T1, "extension", "T1,T2,T3,T4,T5,T6", "Posterior rami", 40, 250, 1800, None),
    ("Spinalis", "back_deep", "parallel", B_L5, B_C7, "extension", "T1,T2,T3,T4,T5,T6", "Posterior rami", 30, 80, 600, None),
    ("Multifidus", "back_deep", "multipennate", B_SACRUM, B_L5 + 2, "extension", "L1,L2,L3", "Posterior rami", 8, 120, 1200, 25),
    # Rotatores -> per-level in _deep_segmental_raw()
    ("Semispinalis Capitis", "back_deep", "multipennate", _T4, B_OCCIPITAL, "extension", "C1,C2,C3,C4", "Posterior rami", 18, 80, 600, 20),
    # Interspinales -> per-level in _deep_segmental_raw()
    ("Quadratus Lumborum", "back_deep", "parallel", B_HIP_R, B_L1, "lateral_flexion", "T12,L1,L2,L3", "Subcostal nerve", 12, 90, 800, None),
    ("Serratus Posterior Superior", "back_deep", "parallel", B_C7, B_RIB_R[2], "elevation", "T1,T2,T3,T4", "Intercostal nerves", 8, 15, 100, None),
    ("Serratus Posterior Inferior", "back_deep", "parallel", B_T12, B_RIB_R[10], "depression", "T9,T10,T11,T12", "Intercostal nerves", 8, 15, 100, None),
    # === CHEST / ABDOMEN ===
    ("Pectoralis Major", "thorax_anterior", "convergent", B_STERNUM, B_HUMER_R, "flexion,adduction", "C5,C6,C7,C8,T1", "Pectoral nerves", 25, 520, 4200, None),
    ("Pectoralis Minor", "thorax_anterior", "convergent", B_RIB_R[2], B_SCAP_R, "depression", "C8,T1", "Medial pectoral nerve", 12, 30, 300, None),
    ("Subclavius", "thorax_anterior", "parallel", B_RIB_R[0], B_CLAV_R, "depression", "C5,C6", "Subclavian nerve", 5, 8, 80, None),
    # External/Internal Intercostal -> per-level in _intercostal_per_level_raw()
    ("Rectus Abdominis", "abdomen", "parallel", B_STERNUM, B_HIP_R, "flexion", "T7,T8,T9,T10,T11,T12", "Intercostal nerves", 40, 280, 2200, None),
    ("External Oblique", "abdomen", "parallel", _T8, B_HIP_R, "flexion,lateral_flexion", "T7,T8,T9,T10,T11,T12", "Intercostal nerves", 20, 100, 600, None),
    ("Internal Oblique", "abdomen", "parallel", B_HIP_R, B_RIB_R[9], "flexion,lateral_flexion", "T7,T8,T9,T10,T11,T12", "Intercostal nerves", 18, 90, 500, None),
    ("Transversus Abdominis", "abdomen", "parallel", B_HIP_R, B_STERNUM, "flexion", "T7,T8,T9,T10,T11,T12", "Intercostal nerves", 15, 80, 400, None),
    ("Diaphragm", "abdomen", "circular", _T6, B_L5, "elevation", "C3,C4,C5", "Phrenic nerve", 5, 35, 300, None),
    # === SHOULDER / ROTATOR CUFF ===
    ("Deltoid", "shoulder", "multipennate", B_CLAV_R, B_HUMER_R, "abduction", "C5,C6", "Axillary nerve", 20, 380, 3400, 15),
    ("Supraspinatus", "shoulder", "unipennate", B_SCAP_R, B_HUMER_R, "abduction", "C5,C6", "Suprascapular nerve", 10, 55, 600, 7),
    ("Infraspinatus", "shoulder", "multipennate", B_SCAP_R, B_HUMER_R, "lateral_rotation", "C5,C6", "Suprascapular nerve", 14, 180, 1200, 18),
    ("Teres Minor", "shoulder", "parallel", B_SCAP_R, B_HUMER_R, "lateral_rotation", "C5,C6", "Axillary nerve", 10, 40, 350, None),
    ("Subscapularis", "shoulder", "multipennate", B_SCAP_R, B_HUMER_R, "medial_rotation", "C5,C6,C7", "Subscapular nerve", 8, 120, 1400, 20),
    ("Teres Major", "shoulder", "parallel", B_SCAP_R, B_HUMER_R, "adduction,medial_rotation", "C5,C6,C7", "Subscapular nerve", 12, 80, 600, None),
    ("Coracobrachialis", "arm_anterior", "parallel", B_SCAP_R, B_HUMER_R, "flexion,adduction", "C5,C6,C7", "Musculocutaneous nerve", 10, 30, 250, None),
    # === ARM ===
    ("Biceps Brachii", "arm_anterior", "fusiform", B_SCAP_R, B_RAD_R, "flexion,supination", "C5,C6,C7", "Musculocutaneous nerve", 32, 150, 1100, None),
    ("Brachialis", "arm_anterior", "parallel", B_HUMER_R, B_ULNA_R, "flexion", "C5,C6", "Musculocutaneous nerve", 12, 160, 1500, None),
    ("Triceps Brachii", "arm_posterior", "multipennate", B_SCAP_R, B_ULNA_R, "extension", "C6,C7,C8", "Radial nerve", 28, 320, 3100, 12),
    ("Brachioradialis", "forearm_anterior", "fusiform", B_HUMER_R, B_RAD_R, "flexion", "C5,C6", "Radial nerve", 20, 50, 400, None),
    ("Anconeus", "arm_posterior", "parallel", B_HUMER_R, B_ULNA_R, "extension", "C7,C8", "Radial nerve", 5, 15, 120, None),
    # === FOREARM ANTERIOR ===
    ("Pronator Teres", "forearm_anterior", "parallel", B_HUMER_R, B_RAD_R, "pronation", "C6,C7", "Median nerve", 12, 35, 300, None),
    ("Flexor Carpi Radialis", "forearm_anterior", "fusiform", B_HUMER_R, _HR_MC[1], "flexion", "C6,C7", "Median nerve", 18, 25, 250, None),
    ("Palmaris Longus", "forearm_anterior", "fusiform", B_HUMER_R, _HR_MC[2], "flexion", "C7,C8", "Median nerve", 15, 10, 80, None),
    ("Flexor Carpi Ulnaris", "forearm_anterior", "fusiform", B_HUMER_R, _HR_HAM, "flexion,adduction", "C8,T1", "Ulnar nerve", 18, 35, 300, None),
    ("Flexor Digitorum Superficialis", "forearm_anterior", "multipennate", B_HUMER_R, _HR_PP[1], "flexion", "C7,C8,T1", "Median nerve", 20, 80, 800, 12),
    ("Flexor Digitorum Profundus", "forearm_anterior", "multipennate", B_ULNA_R, _HR_DP[1], "flexion", "C8,T1", "Median nerve", 22, 100, 1000, 15),
    ("Flexor Pollicis Longus", "forearm_anterior", "unipennate", B_RAD_R, _HR_DP[0], "flexion", "C8,T1", "Median nerve", 16, 25, 250, 10),
    ("Pronator Quadratus", "forearm_anterior", "parallel", B_ULNA_R, B_RAD_R, "pronation", "C8,T1", "Median nerve", 3, 10, 100, None),
    # === FOREARM POSTERIOR ===
    ("Extensor Carpi Radialis Longus", "forearm_posterior", "fusiform", B_HUMER_R, _HR_MC[1], "extension", "C6,C7", "Radial nerve", 18, 30, 250, None),
    ("Extensor Carpi Radialis Brevis", "forearm_posterior", "fusiform", B_HUMER_R, _HR_MC[2], "extension", "C7,C8", "Radial nerve", 15, 25, 200, None),
    ("Extensor Digitorum", "forearm_posterior", "multipennate", B_HUMER_R, _HR_PP[1], "extension", "C7,C8", "Radial nerve", 18, 40, 350, 10),
    ("Extensor Digiti Minimi", "forearm_posterior", "fusiform", B_HUMER_R, _HR_PP[4], "extension", "C7,C8", "Radial nerve", 15, 10, 80, None),
    ("Extensor Carpi Ulnaris", "forearm_posterior", "fusiform", B_HUMER_R, _HR_MC[4], "extension,adduction", "C7,C8", "Radial nerve", 16, 20, 180, None),
    ("Supinator", "forearm_posterior", "parallel", B_HUMER_R, B_RAD_R, "supination", "C5,C6", "Radial nerve", 5, 20, 200, None),
    ("Abductor Pollicis Longus", "forearm_posterior", "parallel", B_ULNA_R, _HR_MC[0], "abduction", "C7,C8", "Radial nerve", 10, 15, 120, None),
    ("Extensor Pollicis Brevis", "forearm_posterior", "parallel", B_RAD_R, _HR_PP[0], "extension", "C7,C8", "Radial nerve", 8, 10, 80, None),
    ("Extensor Pollicis Longus", "forearm_posterior", "fusiform", B_ULNA_R, _HR_DP[0], "extension", "C7,C8", "Radial nerve", 12, 12, 100, None),
    ("Extensor Indicis", "forearm_posterior", "fusiform", B_ULNA_R, _HR_PP[1], "extension", "C7,C8", "Radial nerve", 12, 10, 80, None),
    # === HIP ===
    ("Gluteus Maximus", "hip", "convergent", B_HIP_R, B_FEM_R, "extension", "L5,S1,S2", "Inferior gluteal nerve", 18, 850, 2800, None),
    ("Gluteus Medius", "hip", "multipennate", B_HIP_R, B_FEM_R, "abduction", "L4,L5,S1", "Superior gluteal nerve", 12, 350, 2200, 15),
    ("Gluteus Minimus", "hip", "multipennate", B_HIP_R, B_FEM_R, "abduction,medial_rotation", "L4,L5,S1", "Superior gluteal nerve", 8, 120, 800, 10),
    ("Iliopsoas", "hip", "fusiform", B_L5, B_FEM_R, "flexion", "L1,L2,L3", "Femoral nerve", 28, 280, 2000, None),
    ("Piriformis", "hip", "parallel", B_SACRUM, B_FEM_R, "lateral_rotation", "S1,S2", "Sacral plexus", 6, 30, 200, None),
    ("Obturator Internus", "hip", "parallel", B_HIP_R, B_FEM_R, "lateral_rotation", "L5,S1", "Sacral plexus", 5, 25, 200, None),
    ("Obturator Externus", "hip", "parallel", B_HIP_R, B_FEM_R, "lateral_rotation", "L3,L4", "Obturator nerve", 4, 20, 150, None),
    # Gemellus Superior/Inferior moved to Round 7 additions as Superior/Inferior Gemellus with distinct naming
    ("Quadratus Femoris", "hip", "parallel", B_HIP_R, B_FEM_R, "lateral_rotation", "L5,S1", "Sacral plexus", 5, 25, 200, None),
    ("Tensor Fasciae Latae", "hip", "parallel", B_HIP_R, B_TIB_R, "flexion,abduction", "L4,L5,S1", "Superior gluteal nerve", 12, 40, 300, None),
    ("Psoas Minor", "hip", "parallel", B_T12, B_HIP_R, "flexion", "L1,L2", "Lumbar plexus", 10, 15, 100, None),
    # === THIGH ===
    ("Rectus Femoris", "thigh_anterior", "bipennate", B_FEM_R, B_TIB_R, "extension", "L2,L3,L4", "Femoral nerve", 40, 450, 3500, 14),
    ("Vastus Lateralis", "thigh_anterior", "bipennate", B_FEM_R, B_TIB_R, "extension", "L2,L3,L4", "Femoral nerve", 35, 420, 3800, 14),
    ("Vastus Medialis", "thigh_anterior", "unipennate", B_FEM_R, B_TIB_R, "extension", "L2,L3,L4", "Femoral nerve", 30, 350, 3200, 10),
    ("Vastus Intermedius", "thigh_anterior", "bipennate", B_FEM_R, B_TIB_R, "extension", "L2,L3,L4", "Femoral nerve", 25, 300, 2800, 8),
    ("Biceps Femoris", "thigh_posterior", "fusiform", B_HIP_R, B_TIB_R, "flexion", "L5,S1,S2", "Sciatic nerve", 38, 380, 3200, None),
    ("Semitendinosus", "thigh_posterior", "fusiform", B_HIP_R, B_TIB_R, "flexion", "L5,S1,S2", "Sciatic nerve", 32, 180, 1600, None),
    ("Semimembranosus", "thigh_posterior", "unipennate", B_HIP_R, B_TIB_R, "flexion", "L5,S1,S2", "Sciatic nerve", 30, 250, 2200, 15),
    ("Sartorius", "thigh_anterior", "parallel", B_HIP_R, B_TIB_R, "flexion,abduction", "L2,L3", "Femoral nerve", 50, 60, 300, None),
    ("Gracilis", "thigh_medial", "parallel", B_HIP_R, B_TIB_R, "adduction,flexion", "L2,L3", "Obturator nerve", 32, 30, 200, None),
    ("Adductor Magnus", "thigh_medial", "multipennate", B_HIP_R, B_FEM_R, "adduction", "L2,L3,L4,L5,S1", "Obturator nerve", 20, 400, 2800, 15),
    ("Adductor Longus", "thigh_medial", "parallel", B_HIP_R, B_FEM_R, "adduction", "L2,L3,L4", "Obturator nerve", 15, 120, 800, None),
    ("Adductor Brevis", "thigh_medial", "parallel", B_HIP_R, B_FEM_R, "adduction", "L2,L3", "Obturator nerve", 10, 60, 400, None),
    ("Pectineus", "thigh_medial", "parallel", B_HIP_R, B_FEM_R, "adduction,flexion", "L2,L3", "Femoral nerve", 8, 35, 250, None),
    # === LEG ===
    ("Gastrocnemius", "leg_posterior", "bipennate", B_FEM_R, B_FOOT_R_CALCANEUS, "plantarflexion", "S1,S2", "Tibial nerve", 16, 180, 2400, 17),
    ("Soleus", "leg_posterior", "bipennate", B_TIB_R, B_FOOT_R_CALCANEUS, "plantarflexion", "S1,S2", "Tibial nerve", 10, 420, 3500, 25),
    ("Plantaris", "leg_posterior", "fusiform", B_FEM_R, B_FOOT_R_CALCANEUS, "plantarflexion", "S1,S2", "Tibial nerve", 7, 10, 50, None),
    ("Tibialis Anterior", "leg_anterior", "unipennate", B_TIB_R, B_FOOT_R_CUNEIFORM_MED, "dorsiflexion", "L4,L5", "Common peroneal nerve", 28, 140, 1000, 10),
    ("Tibialis Posterior", "leg_posterior", "multipennate", B_TIB_R, B_FOOT_R_NAVICULAR, "plantarflexion,inversion", "L4,L5", "Tibial nerve", 20, 120, 1000, 15),
    ("Peroneus Longus", "leg_lateral", "unipennate", B_FIB_R, _FR_MT[0], "eversion", "L5,S1", "Common peroneal nerve", 25, 80, 600, 10),
    ("Peroneus Brevis", "leg_lateral", "unipennate", B_FIB_R, _FR_MT[4], "eversion", "L5,S1", "Common peroneal nerve", 15, 40, 300, 8),
    ("Flexor Digitorum Longus", "leg_posterior", "unipennate", B_TIB_R, _FR_DP[1], "flexion,plantarflexion", "S1,S2", "Tibial nerve", 20, 30, 250, 10),
    ("Flexor Hallucis Longus", "leg_posterior", "unipennate", B_FIB_R, _FR_DP[0], "flexion,plantarflexion", "S1,S2", "Tibial nerve", 22, 50, 400, 12),
    ("Extensor Digitorum Longus", "leg_anterior", "unipennate", B_TIB_R, _FR_PP[1], "extension,dorsiflexion", "L4,L5,S1", "Common peroneal nerve", 25, 40, 300, 8),
    ("Extensor Hallucis Longus", "leg_anterior", "unipennate", B_FIB_R, _FR_DP[0], "extension,dorsiflexion", "L5,S1", "Common peroneal nerve", 20, 20, 150, 8),
    ("Popliteus", "leg_posterior", "parallel", B_FEM_R, B_TIB_R, "flexion,medial_rotation", "L4,L5,S1", "Tibial nerve", 5, 15, 120, None),
    # === PELVIC ===
    ("Levator Ani", "hip", "parallel", B_HIP_R, B_COCCYX, "elevation", "S3,S4", "Pudendal nerve", 6, 15, 100, None),
    ("Coccygeus", "hip", "parallel", B_HIP_R, B_COCCYX, "elevation", "S4,S5", "Pudendal nerve", 4, 8, 60, None),
    # ===========================================================================
    # ROUND 7 — ADDITIONAL MUSCLES (~50 base → ~100 bilateral)
    # Reference: Standring, Gray's Anatomy 42nd ed. (2020)
    # Muscle volumes/forces estimated from cadaver literature where available
    # ===========================================================================
    # === ADDITIONAL FACIAL MUSCLES (8) ===
    # Ref: Gray's Ch. 28 (muscles of facial expression)
    ("Levator Labii Superioris", "face", "parallel", B_MAXILLA_R, B_MAXILLA_R, "elevation", "CN7", "Facial VII", 3, 2, 20, None),
    ("Levator Labii Superioris Alaeque Nasi", "face", "parallel", B_MAXILLA_R, B_NASAL_R, "elevation", "CN7", "Facial VII", 4, 2, 20, None),
    ("Depressor Labii Inferioris", "face", "parallel", B_MANDIBLE, B_MANDIBLE, "depression", "CN7", "Facial VII", 2, 1.5, 15, None),
    ("Depressor Anguli Oris", "face", "parallel", B_MANDIBLE, B_MANDIBLE, "depression", "CN7", "Facial VII", 3, 2, 20, None),
    ("Risorius", "face", "parallel", B_ZYGOMATIC_R, B_MANDIBLE, "retraction", "CN7", "Facial VII", 4, 1, 10, None),
    ("Procerus", "face", "parallel", B_NASAL_R, B_FRONTAL, "depression", "CN7", "Facial VII", 2, 1, 10, None),
    ("Levator Anguli Oris", "face", "parallel", B_MAXILLA_R, B_MANDIBLE, "elevation", "CN7", "Facial VII", 3, 2, 15, None),
    ("Zygomaticus Minor", "face", "parallel", B_ZYGOMATIC_R, B_MAXILLA_R, "elevation", "CN7", "Facial VII", 4, 1.5, 15, None),
    # === EXTRAOCULAR MUSCLES (7 per side) ===
    # Ref: Gray's Ch. 39 (orbit)
    ("Superior Rectus", "face", "parallel", B_SPHENOID, B_FRONTAL, "elevation", "C1", "Oculomotor nerve (III)", 4, 1, 60, None),
    ("Inferior Rectus", "face", "parallel", B_SPHENOID, B_FRONTAL, "depression", "C1", "Oculomotor nerve (III)", 4, 1, 60, None),
    ("Medial Rectus", "face", "parallel", B_SPHENOID, B_FRONTAL, "adduction", "C1", "Oculomotor nerve (III)", 4, 1.5, 80, None),
    ("Lateral Rectus", "face", "parallel", B_SPHENOID, B_FRONTAL, "abduction", "C1", "Abducens nerve (VI)", 4, 1, 60, None),
    ("Superior Oblique", "face", "parallel", B_SPHENOID, B_FRONTAL, "medial_rotation", "C1", "Trochlear nerve (IV)", 4, 0.8, 40, None),
    ("Inferior Oblique", "face", "parallel", B_MAXILLA_R, B_FRONTAL, "lateral_rotation", "C1", "Oculomotor nerve (III)", 4, 0.8, 40, None),
    ("Levator Palpebrae Superioris", "face", "parallel", B_SPHENOID, B_FRONTAL, "elevation", "C1", "Oculomotor nerve (III)", 4, 0.5, 30, None),
    # === SUBOCCIPITAL MUSCLES (4) ===
    # Ref: Gray's Ch. 26 (suboccipital triangle)
    ("Rectus Capitis Posterior Major", "back_deep", "parallel", B_C1 - 1, B_OCCIPITAL, "extension", "C1", "Posterior rami", 4, 5, 60, None),
    ("Rectus Capitis Posterior Minor", "back_deep", "parallel", B_C1, B_OCCIPITAL, "extension", "C1", "Posterior rami", 3, 3, 40, None),
    ("Obliquus Capitis Superior", "back_deep", "parallel", B_C1, B_OCCIPITAL, "lateral_flexion", "C1", "Posterior rami", 4, 4, 50, None),
    ("Obliquus Capitis Inferior", "back_deep", "parallel", B_C1 - 1, B_C1, "lateral_rotation", "C1,C2", "Posterior rami", 5, 5, 60, None),
    # === TONGUE MUSCLES (4 extrinsic) ===
    # Ref: Gray's Ch. 29 (tongue)
    ("Genioglossus", "head_and_neck", "convergent", B_MANDIBLE, B_HYOID, "depression,protraction", "C1", "Hypoglossal nerve (XII)", 5, 15, 100, None),
    ("Hyoglossus", "head_and_neck", "parallel", B_HYOID, B_HYOID, "depression,retraction", "C1", "Hypoglossal nerve (XII)", 4, 5, 40, None),
    ("Styloglossus", "head_and_neck", "parallel", B_TEMPORAL_R, B_HYOID, "retraction,elevation", "C1", "Hypoglossal nerve (XII)", 6, 3, 30, None),
    ("Palatoglossus", "head_and_neck", "parallel", B_MAXILLA_R, B_HYOID, "elevation", "C1", "Vagus nerve (X)", 4, 2, 20, None),
    # === ADDITIONAL NECK (3) ===
    # Ref: Gray's Ch. 26-27 (prevertebral, infrahyoid)
    ("Longus Capitis", "head_and_neck", "parallel", B_C7, B_OCCIPITAL, "flexion", "C1,C2,C3", "Cervical plexus", 8, 8, 100, None),
    ("Rectus Capitis Anterior", "head_and_neck", "parallel", B_C1, B_OCCIPITAL, "flexion", "C1,C2", "Cervical plexus", 3, 2, 30, None),
    ("Rectus Capitis Lateralis", "head_and_neck", "parallel", B_C1, B_OCCIPITAL, "lateral_flexion", "C1,C2", "Cervical plexus", 2, 1.5, 20, None),
    # === LARYNGEAL MUSCLES (5) ===
    # Ref: Gray's Ch. 31 (larynx). Attached to hyoid as proxy for laryngeal cartilages.
    ("Cricothyroid", "head_and_neck", "parallel", B_HYOID, B_HYOID, "elevation", "C1", "Vagus nerve (X)", 2, 2, 40, None),
    ("Thyroarytenoid", "head_and_neck", "parallel", B_HYOID, B_HYOID, "depression", "C1", "Vagus nerve (X)", 2, 1.5, 30, None),
    ("Posterior Cricoarytenoid", "head_and_neck", "parallel", B_HYOID, B_HYOID, "abduction", "C1", "Vagus nerve (X)", 1.5, 1, 25, None),
    ("Lateral Cricoarytenoid", "head_and_neck", "parallel", B_HYOID, B_HYOID, "adduction", "C1", "Vagus nerve (X)", 1.5, 1, 25, None),
    ("Transverse Arytenoid", "head_and_neck", "parallel", B_HYOID, B_HYOID, "adduction", "C1", "Vagus nerve (X)", 1, 0.5, 15, None),
    # === PHARYNGEAL CONSTRICTORS (3) ===
    # Ref: Gray's Ch. 30 (pharynx)
    ("Superior Pharyngeal Constrictor", "head_and_neck", "circular", B_SPHENOID, B_OCCIPITAL, "flexion", "C1", "Vagus nerve (X)", 4, 5, 40, None),
    ("Middle Pharyngeal Constrictor", "head_and_neck", "circular", B_HYOID, B_OCCIPITAL, "flexion", "C1", "Vagus nerve (X)", 3, 4, 35, None),
    ("Inferior Pharyngeal Constrictor", "head_and_neck", "circular", B_HYOID, B_OCCIPITAL, "flexion", "C1", "Vagus nerve (X)", 3, 5, 45, None),
    # === ADDITIONAL DEEP BACK (5) ===
    # Ref: Gray's Ch. 26 (deep back muscles)
    ("Semispinalis Thoracis", "back_deep", "multipennate", B_T12 + 4, B_C7, "extension", "T1,T2,T3,T4,T5,T6", "Posterior rami", 20, 60, 500, 18),
    ("Semispinalis Cervicis", "back_deep", "multipennate", B_T12 + 8, B_C7 + 3, "extension", "C3,C4,C5,C6", "Posterior rami", 12, 30, 300, 15),
    # Intertransversarii -> per-level in _deep_segmental_raw()
    ("Longissimus Capitis", "back_deep", "parallel", B_T12 + 8, B_TEMPORAL_R, "extension,lateral_flexion", "C3,C4,C5", "Posterior rami", 15, 15, 150, None),
    ("Longissimus Cervicis", "back_deep", "parallel", B_T12 + 6, B_C7 + 2, "extension,lateral_flexion", "C4,C5,C6", "Posterior rami", 12, 12, 120, None),
    # === ADDITIONAL THORAX (3) ===
    # Ref: Gray's Ch. 53 (thoracic wall)
    # Innermost Intercostal -> per-level in _intercostal_per_level_raw()
    ("Transversus Thoracis", "thorax_anterior", "parallel", B_STERNUM, B_RIB_R[3], "depression", "T2,T3,T4,T5,T6", "Intercostal nerves", 8, 10, 80, None),
    # Levatores Costarum -> per-level in _levatores_costarum_per_level_raw()
    # === ADDITIONAL ABDOMEN (1) ===
    ("Pyramidalis", "abdomen", "parallel", B_HIP_R, B_STERNUM, "flexion", "T12", "Subcostal nerve", 5, 5, 40, None),
    # === ADDITIONAL LEG (1) ===
    ("Peroneus Tertius", "leg_anterior", "unipennate", B_FIB_R, _FR_MT[4], "dorsiflexion,eversion", "L5,S1", "Deep peroneal nerve", 12, 15, 120, 8),
    # === ADDITIONAL HIP (2) ===
    # Ref: Gray's Ch. 77 (hip joint muscles)
    ("Superior Gemellus", "hip", "parallel", B_HIP_R, B_FEM_R, "lateral_rotation", "L5,S1", "Sacral plexus", 3, 5, 50, None),
    ("Inferior Gemellus", "hip", "parallel", B_HIP_R, B_FEM_R, "lateral_rotation", "L5,S1", "Sacral plexus", 3, 5, 50, None),
    # === ROUND 8: COMPLETING ALL MUSCLES ===
    # === PERINEAL (5) Ref: Gray's Ch.76 ===
    ("External Anal Sphincter", "hip", "circular", B_COCCYX, B_HIP_R, "flexion", "S2,S3,S4", "Pudendal nerve", 3, 3, 40, None),
    ("Bulbospongiosus", "hip", "parallel", B_HIP_R, B_HIP_R, "flexion", "S2,S3,S4", "Pudendal nerve", 4, 3, 30, None),
    ("Ischiocavernosus", "hip", "parallel", B_HIP_R, B_HIP_R, "flexion", "S2,S3,S4", "Pudendal nerve", 3, 2, 25, None),
    ("Deep Transverse Perineal", "hip", "parallel", B_HIP_R, B_HIP_L, "elevation", "S2,S3,S4", "Pudendal nerve", 4, 3, 30, None),
    ("Superficial Transverse Perineal", "hip", "parallel", B_HIP_R, B_HIP_L, "elevation", "S2,S3,S4", "Pudendal nerve", 3, 2, 20, None),
    # === PALATE (3) Ref: Gray's Ch.29-30 ===
    ("Tensor Veli Palatini", "head_and_neck", "parallel", B_SPHENOID, B_MAXILLA_R, "elevation", "CN5", "Trigeminal V3", 3, 2, 25, None),
    ("Levator Veli Palatini", "head_and_neck", "parallel", B_TEMPORAL_R, B_MAXILLA_R, "elevation", "C1", "Vagus nerve (X)", 3, 2, 25, None),
    ("Musculus Uvulae", "head_and_neck", "parallel", B_MAXILLA_R, B_MAXILLA_R, "elevation", "C1", "Vagus nerve (X)", 2, 0.5, 10, None),
    # === MIDDLE EAR (2) Ref: Gray's Ch.37 ===
    ("Tensor Tympani", "face", "parallel", B_SPHENOID, B_MALLEUS_R, "flexion", "CN5", "Trigeminal V3", 2, 0.1, 5, None),
    ("Stapedius", "face", "parallel", B_TEMPORAL_R, B_STAPES_R, "flexion", "CN7", "Facial VII", 0.6, 0.03, 2, None),
    # === PHARYNGEAL LONGITUDINAL (2) Ref: Gray's Ch.30 ===
    ("Stylopharyngeus", "head_and_neck", "parallel", B_TEMPORAL_R, B_HYOID, "elevation", "C1", "Glossopharyngeal nerve (IX)", 6, 3, 30, None),
    ("Salpingopharyngeus", "head_and_neck", "parallel", B_TEMPORAL_R, B_HYOID, "elevation", "C1", "Vagus nerve (X)", 3, 1, 10, None),
    # === TONGUE INTRINSIC (4) Ref: Gray's Ch.29 ===
    ("Superior Longitudinal Tongue", "head_and_neck", "parallel", B_HYOID, B_HYOID, "elevation,retraction", "C1", "Hypoglossal nerve (XII)", 5, 3, 20, None),
    ("Inferior Longitudinal Tongue", "head_and_neck", "parallel", B_HYOID, B_HYOID, "depression,retraction", "C1", "Hypoglossal nerve (XII)", 5, 2, 15, None),
    ("Transverse Tongue", "head_and_neck", "parallel", B_HYOID, B_HYOID, "adduction", "C1", "Hypoglossal nerve (XII)", 4, 2, 15, None),
    ("Vertical Tongue", "head_and_neck", "parallel", B_HYOID, B_HYOID, "depression", "C1", "Hypoglossal nerve (XII)", 4, 2, 15, None),
    # === ADDITIONAL FACIAL (5) Ref: Gray's Ch.28 ===
    ("Auricularis Anterior", "face", "parallel", B_TEMPORAL_R, B_TEMPORAL_R, "protraction", "CN7", "Facial VII", 2, 0.5, 5, None),
    ("Auricularis Superior", "face", "parallel", B_TEMPORAL_R, B_TEMPORAL_R, "elevation", "CN7", "Facial VII", 2, 0.5, 5, None),
    ("Auricularis Posterior", "face", "parallel", B_TEMPORAL_R, B_TEMPORAL_R, "retraction", "CN7", "Facial VII", 2, 0.5, 5, None),
    ("Occipitalis", "face", "parallel", B_OCCIPITAL, B_OCCIPITAL, "retraction", "CN7", "Facial VII", 4, 3, 20, None),
    ("Depressor Septi Nasi", "face", "parallel", B_MAXILLA_R, B_NASAL_R, "depression", "CN7", "Facial VII", 1.5, 0.5, 8, None),
]

# === HAND INTRINSIC (18 per side — generated programmatically for R) ===
def _hand_intrinsic_raw() -> list[tuple]:
    """Generate 18 R-side hand intrinsic muscle definitions."""
    mc, pp, dp = _HR_MC, _HR_PP, _HR_DP
    m: list[tuple] = []
    # Thenar (4)
    m.append(("Abductor Pollicis Brevis", "hand_intrinsic", "parallel", _HR_TRAP, pp[0], "abduction", "C8,T1", "Median nerve", 4, 5, 80, None))
    m.append(("Flexor Pollicis Brevis", "hand_intrinsic", "parallel", _HR_TRAP, pp[0], "flexion", "C8,T1", "Median nerve", 4, 5, 80, None))
    m.append(("Opponens Pollicis", "hand_intrinsic", "parallel", _HR_TRAP, mc[0], "opposition", "C8,T1", "Median nerve", 3, 6, 100, None))
    m.append(("Adductor Pollicis", "hand_intrinsic", "parallel", _HR_CAP, pp[0], "adduction", "C8,T1", "Ulnar nerve", 4, 8, 120, None))
    # Hypothenar (3)
    m.append(("Abductor Digiti Minimi Hand", "hand_intrinsic", "parallel", 103, pp[4], "abduction", "C8,T1", "Ulnar nerve", 4, 4, 60, None))  # pisiform
    m.append(("Flexor Digiti Minimi Brevis Hand", "hand_intrinsic", "parallel", _HR_HAM, pp[4], "flexion", "C8,T1", "Ulnar nerve", 3, 3, 50, None))
    m.append(("Opponens Digiti Minimi", "hand_intrinsic", "parallel", _HR_HAM, mc[4], "opposition", "C8,T1", "Ulnar nerve", 3, 4, 60, None))
    # Lumbricals (4)
    for i in range(4):
        m.append((f"Lumbrical {i+1} Hand", "hand_intrinsic", "fusiform", mc[i+1], pp[i+1], "flexion", "C8,T1", "Median nerve" if i < 2 else "Ulnar nerve", 3, 2, 30, None))
    # Dorsal interossei (4)
    for i in range(4):
        m.append((f"Dorsal Interosseous {i+1} Hand", "hand_intrinsic", "bipennate", mc[i], pp[min(i+1,4)], "abduction", "C8,T1", "Ulnar nerve", 3, 4, 60, 10))
    # Palmar interossei (3)
    for i in range(3):
        digit = i + 1 if i < 1 else i + 2  # digits 2, 4, 5 (index=1, ring=3, little=4)
        m.append((f"Palmar Interosseous {i+1} Hand", "hand_intrinsic", "unipennate", mc[digit], pp[digit], "adduction", "C8,T1", "Ulnar nerve", 3, 3, 50, 8))
    return m

# === FOOT INTRINSIC (20 per side — generated programmatically for R) ===
def _foot_intrinsic_raw() -> list[tuple]:
    """Generate 20 R-side foot intrinsic muscle definitions."""
    mt, pp, dp = _FR_MT, _FR_PP, _FR_DP
    m: list[tuple] = []
    # Dorsal (2)
    m.append(("Extensor Digitorum Brevis", "foot_intrinsic", "parallel", _FR_CALC, pp[1], "extension", "L5,S1", "Common peroneal nerve", 6, 10, 80, None))
    m.append(("Extensor Hallucis Brevis", "foot_intrinsic", "parallel", _FR_CALC, pp[0], "extension", "L5,S1", "Common peroneal nerve", 5, 5, 40, None))
    # Layer 1 (3)
    m.append(("Abductor Hallucis", "foot_intrinsic", "parallel", _FR_CALC, pp[0], "abduction", "S1,S2", "Medial plantar nerve", 10, 25, 200, None))
    m.append(("Flexor Digitorum Brevis", "foot_intrinsic", "multipennate", _FR_CALC, pp[1], "flexion", "S1,S2", "Medial plantar nerve", 8, 20, 150, 12))
    m.append(("Abductor Digiti Minimi Foot", "foot_intrinsic", "parallel", _FR_CALC, pp[4], "abduction", "S1,S2", "Lateral plantar nerve", 8, 15, 100, None))
    # Layer 2 (5)
    m.append(("Quadratus Plantae", "foot_intrinsic", "parallel", _FR_CALC, _FR_CALC, "flexion", "S1,S2", "Lateral plantar nerve", 5, 10, 80, None))
    for i in range(4):
        m.append((f"Lumbrical {i+1} Foot", "foot_intrinsic", "fusiform", mt[i+1], pp[i+1], "flexion", "S1,S2", "Medial plantar nerve" if i == 0 else "Lateral plantar nerve", 3, 2, 20, None))
    # Layer 3 (3)
    m.append(("Flexor Hallucis Brevis", "foot_intrinsic", "parallel", _FR_CUB, pp[0], "flexion", "S1,S2", "Medial plantar nerve", 5, 10, 80, None))
    m.append(("Adductor Hallucis", "foot_intrinsic", "parallel", mt[1], pp[0], "adduction", "S1,S2", "Lateral plantar nerve", 5, 10, 80, None))
    m.append(("Flexor Digiti Minimi Brevis Foot", "foot_intrinsic", "parallel", mt[4], pp[4], "flexion", "S1,S2", "Lateral plantar nerve", 4, 5, 40, None))
    # Layer 4 (7): dorsal interossei (4) + plantar interossei (3)
    for i in range(4):
        m.append((f"Dorsal Interosseous {i+1} Foot", "foot_intrinsic", "bipennate", mt[i], pp[min(i+1,4)], "abduction", "S1,S2", "Lateral plantar nerve", 3, 4, 50, 10))
    for i in range(3):
        digit = i + 2  # toes 3, 4, 5 → indices 2, 3, 4
        m.append((f"Plantar Interosseous {i+1} Foot", "foot_intrinsic", "unipennate", mt[digit], pp[digit], "adduction", "S1,S2", "Lateral plantar nerve", 3, 3, 40, 8))
    return m

# Combine all raw definitions

def _intercostal_per_level_raw() -> list[tuple]:
    """11 external + 11 internal + 8 innermost intercostals per side."""
    m: list[tuple] = []
    for i in range(11):
        sp = f"T{i+1}"
        m.append((f"External Intercostal {sp}", "thorax_anterior", "parallel", B_RIB_R[i], B_RIB_R[i+1], "elevation", sp, "Intercostal nerves", 3, 2, 15, None))
        m.append((f"Internal Intercostal {sp}", "thorax_anterior", "parallel", B_RIB_R[i+1], B_RIB_R[i], "depression", sp, "Intercostal nerves", 3, 2, 15, None))
    for i in range(2, 10):
        sp = f"T{i+1}"
        m.append((f"Innermost Intercostal {sp}", "thorax_anterior", "parallel", B_RIB_R[i+1], B_RIB_R[i], "depression", sp, "Intercostal nerves", 3, 1.5, 10, None))
    return m

def _levatores_costarum_per_level_raw() -> list[tuple]:
    """12 levatores costarum (one per rib)."""
    m: list[tuple] = []
    for i in range(12):
        t_vert = B_T1 - i
        sp = f"T{i+1}"
        m.append((f"Levator Costae {i+1}", "thorax_anterior", "parallel", t_vert, B_RIB_R[i], "elevation", sp, "Posterior rami", 2, 1, 8, None))
    return m

def _deep_segmental_raw() -> list[tuple]:
    """Per-level rotatores (11) + interspinales (10) + intertransversarii (11) + multifidus (16)."""
    m: list[tuple] = []
    for i in range(11):
        t_lo = B_T12 + i; t_hi = B_T12 + i + 1; sp = f"T{12-i}"
        m.append((f"Rotator {sp}", "back_deep", "parallel", t_lo, t_hi, "extension", sp, "Posterior rami", 2, 1.5, 12, None))
    for i in range(6):
        c_lo = B_C7 + i; c_hi = B_C7 + i + 1; sp = f"C{7-i}"
        m.append((f"Interspinalis {sp}", "back_deep", "parallel", c_lo, c_hi, "extension", sp, "Posterior rami", 1.5, 0.5, 5, None))
    for i in range(4):
        l_lo = B_L5 + i; l_hi = B_L5 + i + 1; sp = f"L{5-i}"
        m.append((f"Interspinalis {sp}", "back_deep", "parallel", l_lo, l_hi, "extension", sp, "Posterior rami", 2, 0.8, 8, None))
    for i in range(6):
        c_lo = B_C1 - i; c_hi = c_lo - 1; sp = f"C{1+i}"
        m.append((f"Intertransversarius {sp}", "back_deep", "parallel", c_lo, max(c_hi, B_C7), "lateral_flexion", sp, "Posterior rami", 1.5, 0.5, 5, None))
    for i in range(4):
        l_lo = B_L1 - i; l_hi = max(l_lo - 1, B_L5); sp = f"L{1+i}"
        m.append((f"Intertransversarius {sp}", "back_deep", "parallel", l_lo, l_hi, "lateral_flexion", sp, "Posterior rami", 2, 0.8, 8, None))
    for i in range(4):
        c_vert = B_C7 + (3 - i); sp = f"C{4+i}"
        m.append((f"Multifidus {sp}", "back_deep", "multipennate", c_vert, min(c_vert + 2, B_C1), "extension", sp, "Posterior rami", 3, 3, 40, 20))
    for i in range(12):
        t_vert = B_T1 - i; target = max(t_vert - 3, B_T12); sp = f"T{i+1}"
        m.append((f"Multifidus {sp}", "back_deep", "multipennate", t_vert, target, "extension", sp, "Posterior rami", 4, 4, 50, 22))
    return m
# Total: 170 base (_RAW) + 18 hand intrinsic + 20 foot intrinsic = 208 base → ~414 bilateral
_ALL_RAW = (_RAW + _hand_intrinsic_raw() + _foot_intrinsic_raw()
           + _intercostal_per_level_raw() + _levatores_costarum_per_level_raw()
           + _deep_segmental_raw())

# Antagonist map (base name → list of base antagonist names)
_ANTAG: dict[str, list[str]] = {
    "Rectus Femoris": ["Biceps Femoris", "Semitendinosus", "Semimembranosus"],
    "Vastus Lateralis": ["Biceps Femoris"], "Vastus Medialis": ["Biceps Femoris"],
    "Biceps Femoris": ["Rectus Femoris", "Vastus Lateralis"],
    "Semitendinosus": ["Rectus Femoris"], "Semimembranosus": ["Rectus Femoris"],
    "Biceps Brachii": ["Triceps Brachii"], "Triceps Brachii": ["Biceps Brachii"],
    "Pectoralis Major": ["Latissimus Dorsi"], "Latissimus Dorsi": ["Pectoralis Major", "Deltoid"],
    "Tibialis Anterior": ["Gastrocnemius", "Soleus"],
    "Peroneus Tertius": ["Tibialis Posterior"],
    "Superior Rectus": ["Inferior Rectus"],
    "Inferior Rectus": ["Superior Rectus"],
    "Medial Rectus": ["Lateral Rectus"],
    "Lateral Rectus": ["Medial Rectus"],
    "Genioglossus": ["Styloglossus"],
    "Styloglossus": ["Genioglossus"],
    "External Oblique": ["Erector Spinae"],
    "Rectus Abdominis": ["Erector Spinae"],
    "Gluteus Maximus": ["Iliopsoas"],
    "Iliopsoas": ["Gluteus Maximus"],
    "Deltoid": ["Latissimus Dorsi", "Teres Major"],
    "Gastrocnemius": ["Tibialis Anterior"], "Soleus": ["Tibialis Anterior"],
}
_SYNERG: dict[str, list[str]] = {
    "Biceps Brachii": ["Brachialis", "Brachioradialis"],
    "Gastrocnemius": ["Soleus"], "Soleus": ["Gastrocnemius"],
    "Rectus Femoris": ["Vastus Lateralis", "Vastus Medialis", "Vastus Intermedius"],
    "Gluteus Medius": ["Gluteus Minimus", "Tensor Fasciae Latae"],
    "Gluteus Maximus": ["Biceps Femoris"],
}

# Special tendon overrides
_OTN: dict[str, tuple[str, float | None]] = {"Rectus Femoris": ("Quadriceps tendon", 1.3)}
_ITN: dict[str, tuple[str, float | None]] = {"Rectus Femoris": ("Patellar tendon", 1.5), "Gastrocnemius": ("Achilles tendon", 0.8)}

# Midline muscles (not expanded bilaterally)
_MIDLINE = {"Rectus Abdominis", "Diaphragm"}

# Shared origin tendons (midline origin, bilateral insertion)
SHARED_ORIGIN_BASES = {"Pectoralis Major", "Latissimus Dorsi"}

def _expand_raw() -> list[MuscleSpec]:
    """Expand compact _ALL_RAW into MuscleSpec tuples, then apply bilateral expansion."""
    base: list[MuscleSpec] = []
    for r in _ALL_RAW:
        name, reg, arch, ob, ib, acts_str, sp_str, nv, L, vol, fmax, penn = r
        actions = acts_str.split(",")
        spinal = sp_str.split(",")
        fdir = _FDIR.get(name, (0, -1, 0))
        artery = _ARTERY.get(reg, "Regional artery")
        antag = _ANTAG.get(name, [])
        synerg = _SYNERG.get(name, [])
        mass = max(1, round(vol * 1.06))
        otn_pair = _OTN.get(name)
        itn_pair = _ITN.get(name)
        base.append((name, reg, arch, ob, ib, actions, None, spinal, nv, artery,
                      L, vol, mass, fmax, penn, fdir, antag, synerg,
                      otn_pair[0] if otn_pair else None, itn_pair[0] if itn_pair else None,
                      otn_pair[1] if otn_pair else None, itn_pair[1] if itn_pair else None))
    return _bilateral(base)

MUSCLE_DEFS = _expand_raw()


def _mirror_bone(idx: int) -> int:
    """Map any R-side bone index to its L-side counterpart."""
    _PAIRS = {
        B_HIP_R: B_HIP_L, B_SCAP_R: B_SCAP_L, B_CLAV_R: B_CLAV_L,
        B_HUMER_R: B_HUMER_L, B_RAD_R: B_RAD_L, B_ULNA_R: B_ULNA_L,
        B_FEM_R: B_FEM_L, B_PAT_R: B_PAT_L, B_TIB_R: B_TIB_L, B_FIB_R: B_FIB_L,
        B_TEMPORAL_R: B_TEMPORAL_L, B_PARIETAL_R: B_PARIETAL_L,
        B_MAXILLA_R: B_MAXILLA_L, B_ZYGOMATIC_R: B_ZYGOMATIC_L, B_NASAL_R: B_NASAL_L,
    }
    if idx in _PAIRS: return _PAIRS[idx]
    if 34 <= idx <= 45: return idx + 12   # Rib R → L
    if 100 <= idx <= 126: return idx + 27  # Hand R → L
    if 154 <= idx <= 179: return idx + 26  # Foot R → L
    return idx


def gen_tendons_and_muscles(r: Reg) -> tuple[list[dict], list[dict]]:
    tendons: list[dict] = []
    muscles: list[dict] = []
    shared_origin_tendon_idx: dict[str, int] = {}

    for mdef in MUSCLE_DEFS:
        (name, region, arch, o_bone, i_bone, actions, sec_actions,
         spinal, nerve, artery, length, vol, mass, fmax, penn,
         fdir, _, _, otn, itn, ocsa, icsa) = mdef

        if "(L)" in name:
            o_bone = _mirror_bone(o_bone)
            i_bone = _mirror_bone(i_bone)

        base_name = name.replace(" (R)", "").replace(" (L)", "")

        if base_name in SHARED_ORIGIN_BASES and base_name in shared_origin_tendon_idx:
            origin_tendon_idx = shared_origin_tendon_idx[base_name]
        else:
            ot_name = f"{otn} ({name.split('(')[-1].strip(')')[-1]})" if otn and "(" in name else (otn or f"{name} origin tendon")
            tendons.append(_make_tendon(r, ot_name, o_bone, random.uniform(2, 5), ocsa))
            origin_tendon_idx = len(r.tendon_ids) - 1
            if base_name in SHARED_ORIGIN_BASES:
                shared_origin_tendon_idx[base_name] = origin_tendon_idx

        it_name = f"{itn} ({name.split('(')[-1].strip(')')[-1]})" if itn and "(" in name else (itn or f"{name} insertion tendon")
        tendons.append(_make_tendon(r, it_name, i_bone, random.uniform(3, 6), icsa))

        mid = uid()
        r.muscle_ids.append(mid)
        r.muscle_name_to_idx[name] = len(r.muscle_ids) - 1

        # Computed biomechanical properties
        # OFL/belly-length ratio depends on fascicle architecture:
        #   parallel/fusiform: fibers span most of the belly (~0.6)
        #   unipennate: fibers at angle, shorter (~0.35)
        #   bipennate/multipennate: fibers much shorter (~0.25)
        #   convergent: intermediate (~0.4)
        #   circular: short fibers around lumen (~0.3)
        # Ref: Ward et al., Clin Biomech 24(1):5-18, 2009, Table 2
        _OFL_RATIO = {"parallel": 0.6, "fusiform": 0.55, "convergent": 0.4,
                      "unipennate": 0.35, "bipennate": 0.25, "multipennate": 0.25,
                      "circular": 0.3}
        ofl_ratio = _OFL_RATIO.get(arch, 0.4)
        opt_fiber_len = round(length * ofl_ratio, 2)
        pcsa = round(vol / opt_fiber_len, 2) if opt_fiber_len > 0 else 0
        vmax = round(random.uniform(5.0, 8.0), 1)

        m: dict[str, Any] = {
            "id": mid, "name": name, "region": region, "type": "skeletal",
            "origin": {"tendonId": r.tendon_ids[origin_tendon_idx], "description": f"Origin of {name}"},
            "insertion": {"tendonId": r.tendon_ids[-1], "description": f"Insertion of {name}"},
            "fascicleArchitecture": arch,
            "fiberDirection": unit_vec3(*fdir),
            "fiberComposition": "mixed",
            "restingLength": length, "volume": vol, "mass": mass,
            "optimalFiberLength": opt_fiber_len,
            "pcsa": pcsa,
            "maxIsometricForce": fmax,
            "maxContractionVelocity": vmax,
            "innervation": {"nerveName": nerve, "spinalRoots": spinal},
            "bloodSupply": {"primaryArteryName": artery},
            "primaryActions": actions,
        }
        if sec_actions:
            m["secondaryActions"] = sec_actions
        if penn is not None:
            m["pennationAngle"] = penn
        muscles.append(m)

    # Resolve antagonist/synergist IDs
    for i, mdef in enumerate(MUSCLE_DEFS):
        antag_names, syn_names = mdef[16], mdef[17]
        if antag_names:
            aids = [r.muscle_ids[r.muscle_name_to_idx[n]] for n in antag_names if n in r.muscle_name_to_idx]
            if aids:
                muscles[i]["antagonistIds"] = aids
        if syn_names:
            sids = [r.muscle_ids[r.muscle_name_to_idx[n]] for n in syn_names if n in r.muscle_name_to_idx]
            if sids:
                muscles[i]["synergistIds"] = sids

    # Resolve nerveId
    for m in muscles:
        nerve_name = m["innervation"]["nerveName"]
        if nerve_name in r.nerve_name_to_idx:
            m["innervation"]["nerveId"] = r.nerve_ids[r.nerve_name_to_idx[nerve_name]]

    # ── P0.1: Wrapping surfaces, via-points, and moment arms ──────────────
    # Muscles that cross prominent bony landmarks need wrapping surfaces
    # to avoid penetrating bone. Via-points redirect the muscle path.
    # Moment arms are the perpendicular distance from joint center to
    # muscle line of action — the key quantity for inverse dynamics.
    #
    # Data source: Arnold et al., Ann Biomed Eng 38(2):269-279, 2010 (LE);
    #              Holzbaur et al., Ann Biomed Eng 33(6):829-840, 2005 (UE).
    #
    # Stored in the schema's `extensions` field (key: "biomechanics:musclePath")
    # since MuscleSchema has no wrapping/via-point fields yet.

    # Wrapping surface templates: bone index → (type, radius, local position, local axis)
    _WRAP_SURFACES: dict[int, list[dict]] = {
        B_FEM_R: [{"type": "cylinder", "radius": 2.5, "position": vec3(0, 20, 0),
                    "axis": vec3(1, 0, 0), "boneId": None, "name": "femoral_neck_wrap"}],
        B_FEM_L: [{"type": "cylinder", "radius": 2.5, "position": vec3(0, 20, 0),
                    "axis": vec3(1, 0, 0), "boneId": None, "name": "femoral_neck_wrap"}],
        B_HUMER_R: [{"type": "sphere", "radius": 2.0, "position": vec3(0, 16, 0),
                      "boneId": None, "name": "humeral_head_wrap"}],
        B_HUMER_L: [{"type": "sphere", "radius": 2.0, "position": vec3(0, 16, 0),
                      "boneId": None, "name": "humeral_head_wrap"}],
        B_TIB_R: [{"type": "cylinder", "radius": 1.8, "position": vec3(0, 18, 1),
                    "axis": vec3(1, 0, 0), "boneId": None, "name": "tibial_plateau_wrap"}],
        B_TIB_L: [{"type": "cylinder", "radius": 1.8, "position": vec3(0, 18, 1),
                    "axis": vec3(1, 0, 0), "boneId": None, "name": "tibial_plateau_wrap"}],
    }
    # Fill in bone IDs
    for bone_idx, surfs in _WRAP_SURFACES.items():
        for s in surfs:
            s["boneId"] = r.bone_ids[bone_idx]

    # Muscle → wrapping/via-point/moment-arm rules.
    # Key: base muscle name (without side). Value: dict of path data.
    # momentArm: approximate moment arm in cm at neutral joint angle.
    # Ref: Spoor & van Leeuwen, J Biomech 25(10):1135-1143, 1992.
    _MUSCLE_PATH: dict[str, dict] = {
        # Lower extremity — Arnold et al. (2010)
        "Gluteus Maximus": {"wraps": [B_FEM_R], "momentArm": {"hip_extension": 5.2}},
        "Gluteus Medius":  {"wraps": [B_FEM_R], "momentArm": {"hip_abduction": 4.8}},
        "Gluteus Minimus": {"wraps": [B_FEM_R], "momentArm": {"hip_abduction": 2.8}},
        "Iliopsoas":       {"wraps": [B_HIP_R], "viaPoints": [{"boneIdx": B_HIP_R, "local": vec3(0, -5, 3)}],
                            "momentArm": {"hip_flexion": 3.5}},
        "Rectus Femoris":  {"momentArm": {"hip_flexion": 3.8, "knee_extension": 4.4}},
        "Vastus Lateralis": {"momentArm": {"knee_extension": 4.2}},
        "Vastus Medialis":  {"momentArm": {"knee_extension": 3.8}},
        "Vastus Intermedius": {"momentArm": {"knee_extension": 4.0}},
        "Biceps Femoris":  {"wraps": [B_TIB_R], "momentArm": {"hip_extension": 4.5, "knee_flexion": 3.2}},
        "Semitendinosus":  {"wraps": [B_TIB_R], "momentArm": {"hip_extension": 5.0, "knee_flexion": 3.8}},
        "Semimembranosus": {"wraps": [B_TIB_R], "momentArm": {"hip_extension": 4.8, "knee_flexion": 3.0}},
        "Gastrocnemius":   {"wraps": [B_FEM_R], "momentArm": {"knee_flexion": 1.8, "ankle_plantarflexion": 5.2}},
        "Soleus":          {"momentArm": {"ankle_plantarflexion": 4.8}},
        "Tibialis Anterior": {"momentArm": {"ankle_dorsiflexion": 3.6}},
        "Sartorius":       {"wraps": [B_FEM_R], "momentArm": {"hip_flexion": 2.5}},
        "Gracilis":        {"momentArm": {"hip_adduction": 2.0}},
        "Adductor Magnus": {"momentArm": {"hip_adduction": 4.5}},
        "Adductor Longus": {"momentArm": {"hip_adduction": 3.8}},
        "Tensor Fasciae Latae": {"momentArm": {"hip_flexion": 3.0, "hip_abduction": 2.5}},
        # Upper extremity — Holzbaur et al. (2005)
        "Biceps Brachii":  {"wraps": [B_HUMER_R], "momentArm": {"elbow_flexion": 4.6, "shoulder_flexion": 2.0}},
        "Triceps Brachii": {"momentArm": {"elbow_extension": 2.2, "shoulder_extension": 1.5}},
        "Brachialis":      {"momentArm": {"elbow_flexion": 2.8}},
        "Deltoid":         {"wraps": [B_HUMER_R], "momentArm": {"shoulder_abduction": 2.0}},
        "Supraspinatus":   {"wraps": [B_HUMER_R], "momentArm": {"shoulder_abduction": 1.0}},
        "Infraspinatus":   {"wraps": [B_HUMER_R], "momentArm": {"shoulder_external_rotation": 2.2}},
        "Subscapularis":   {"wraps": [B_HUMER_R], "momentArm": {"shoulder_internal_rotation": 2.5}},
        "Pectoralis Major": {"wraps": [B_HUMER_R], "momentArm": {"shoulder_flexion": 3.5, "shoulder_adduction": 4.0}},
        "Latissimus Dorsi": {"wraps": [B_HUMER_R], "momentArm": {"shoulder_extension": 4.0, "shoulder_adduction": 3.5}},
        # Trunk
        "Erector Spinae":  {"momentArm": {"trunk_extension": 5.5}},
        "Rectus Abdominis": {"momentArm": {"trunk_flexion": 8.0}},
        "External Oblique": {"momentArm": {"trunk_flexion": 4.5, "trunk_rotation": 3.0}},
    }

    for i, m in enumerate(muscles):
        base = m["name"].replace(" (R)", "").replace(" (L)", "")
        side = "(R)" if "(R)" in m["name"] else ("(L)" if "(L)" in m["name"] else "")
        path_data = _MUSCLE_PATH.get(base)
        if not path_data:
            continue

        ext: dict[str, Any] = {}

        # Wrapping surfaces
        if "wraps" in path_data:
            wrap_list = []
            for bone_idx in path_data["wraps"]:
                actual_idx = _mirror_bone(bone_idx) if side == "(L)" else bone_idx
                for surf in _WRAP_SURFACES.get(actual_idx, []):
                    wrap_list.append(surf)
            if wrap_list:
                ext["wrappingSurfaces"] = wrap_list

        # Via-points
        if "viaPoints" in path_data:
            vps = []
            for vp in path_data["viaPoints"]:
                actual_idx = _mirror_bone(vp["boneIdx"]) if side == "(L)" else vp["boneIdx"]
                vps.append({"boneId": r.bone_ids[actual_idx], "localPosition": vp["local"]})
            ext["viaPoints"] = vps

        # Moment arms
        if "momentArm" in path_data:
            ext["momentArms"] = path_data["momentArm"]

        if ext:
            muscles[i]["extensions"] = {"biomechanics:musclePath": ext}

    return tendons, muscles


__all__ = [name for name in globals() if not name.startswith("__")]

