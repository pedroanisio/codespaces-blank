from .shared import *
from .skeleton import *

# =============================================================================
# JOINTS — 24 (bone indices updated for 206-bone layout)
# =============================================================================

JOINT_DEFS: list[tuple[str, str, list[int], int, dict | None, dict | None]] = [
    ("Hip (R)", "ball_and_socket", [B_HIP_R, B_FEM_R], 3,
     {"primary": vec3(0, 0, 1), "secondary": vec3(1, 0, 0), "tertiary": vec3(0, 1, 0)},
     {"flexionExtension": {"min": -15, "max": 125}, "abductionAdduction": {"min": -30, "max": 45}, "internalExternalRotation": {"min": -45, "max": 45}}),
    ("Hip (L)", "ball_and_socket", [B_HIP_L, B_FEM_L], 3,
     {"primary": vec3(0, 0, 1), "secondary": vec3(1, 0, 0), "tertiary": vec3(0, 1, 0)},
     {"flexionExtension": {"min": -15, "max": 125}, "abductionAdduction": {"min": -30, "max": 45}, "internalExternalRotation": {"min": -45, "max": 45}}),
    ("Knee (R)", "hinge", [B_FEM_R, B_TIB_R, B_PAT_R], 1,
     {"primary": vec3(0, 0, 1)}, {"flexionExtension": {"min": 0, "max": 140}}),
    ("Knee (L)", "hinge", [B_FEM_L, B_TIB_L, B_PAT_L], 1,
     {"primary": vec3(0, 0, 1)}, {"flexionExtension": {"min": 0, "max": 140}}),
    ("Shoulder (R)", "ball_and_socket", [B_SCAP_R, B_HUMER_R], 3,
     {"primary": vec3(0, 0, 1), "secondary": vec3(1, 0, 0), "tertiary": vec3(0, 1, 0)},
     {"flexionExtension": {"min": -60, "max": 180}, "abductionAdduction": {"min": 0, "max": 180}, "internalExternalRotation": {"min": -90, "max": 90}}),
    ("Shoulder (L)", "ball_and_socket", [B_SCAP_L, B_HUMER_L], 3,
     {"primary": vec3(0, 0, 1), "secondary": vec3(1, 0, 0), "tertiary": vec3(0, 1, 0)},
     {"flexionExtension": {"min": -60, "max": 180}, "abductionAdduction": {"min": 0, "max": 180}, "internalExternalRotation": {"min": -90, "max": 90}}),
    ("Elbow (R)", "hinge", [B_HUMER_R, B_RAD_R, B_ULNA_R], 1,
     {"primary": vec3(0, 0, 1)}, {"flexionExtension": {"min": 0, "max": 150}}),
    ("Elbow (L)", "hinge", [B_HUMER_L, B_RAD_L, B_ULNA_L], 1,
     {"primary": vec3(0, 0, 1)}, {"flexionExtension": {"min": 0, "max": 150}}),
    ("L5-S1 lumbosacral", "cartilaginous", [B_SACRUM, B_L5], 3, None,
     {"flexionExtension": {"min": -5, "max": 15}, "abductionAdduction": {"min": -3, "max": 3}, "internalExternalRotation": {"min": -3, "max": 3}}),
    ("L5-L4 intervertebral", "cartilaginous", [B_L5, B_L5 + 1], 3, None,
     {"flexionExtension": {"min": -3, "max": 12}, "abductionAdduction": {"min": -3, "max": 3}}),
    ("L4-L3 intervertebral", "cartilaginous", [B_L5 + 1, B_L5 + 2], 3, None,
     {"flexionExtension": {"min": -3, "max": 12}, "abductionAdduction": {"min": -3, "max": 3}}),
    ("L3-L2 intervertebral", "cartilaginous", [B_L5 + 2, B_L5 + 3], 3, None,
     {"flexionExtension": {"min": -3, "max": 12}, "abductionAdduction": {"min": -3, "max": 3}}),
    ("L2-L1 intervertebral", "cartilaginous", [B_L5 + 3, B_L1], 3, None,
     {"flexionExtension": {"min": -3, "max": 12}, "abductionAdduction": {"min": -3, "max": 3}}),
    ("T12-L1 thoracolumbar", "cartilaginous", [B_L1, B_T12], 3, None,
     {"flexionExtension": {"min": -2, "max": 8}}),
    ("T12-T11 intervertebral", "cartilaginous", [B_T12, B_T12 + 1], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T9-T8 intervertebral", "cartilaginous", [B_T12 + 3, B_T12 + 4], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T5-T4 intervertebral", "cartilaginous", [B_T12 + 7, B_T12 + 8], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T2-T1 intervertebral", "cartilaginous", [B_T12 + 10, B_T1], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("C7-T1 cervicothoracic", "cartilaginous", [B_T1, B_C7], 3, None,
     {"flexionExtension": {"min": -5, "max": 10}}),
    ("C1-C2 atlantoaxial", "pivot", [B_C1, B_C1 - 1], 1, None,
     {"internalExternalRotation": {"min": -45, "max": 45}}),
    ("Wrist (R)", "condyloid", [B_RAD_R, B_ULNA_R, B_HAND_R_SCAPHOID], 2, None,
     {"flexionExtension": {"min": -80, "max": 80}, "abductionAdduction": {"min": -20, "max": 35}}),
    ("Wrist (L)", "condyloid", [B_RAD_L, B_ULNA_L, B_HAND_L_START], 2, None,
     {"flexionExtension": {"min": -80, "max": 80}, "abductionAdduction": {"min": -20, "max": 35}}),
    ("Ankle (R)", "hinge", [B_TIB_R, B_FIB_R, B_FOOT_R_TALUS], 1, None,
     {"flexionExtension": {"min": -20, "max": 50}}),
    ("Ankle (L)", "hinge", [B_TIB_L, B_FIB_L, B_FOOT_L_START + 1], 1, None,
     {"flexionExtension": {"min": -20, "max": 50}}),
    # === GIRDLE JOINTS (Round 3) ===
    ("Sternoclavicular (R)", "saddle", [B_STERNUM, B_CLAV_R], 3, None,
     {"flexionExtension": {"min": -15, "max": 15}, "abductionAdduction": {"min": -15, "max": 15}, "internalExternalRotation": {"min": -45, "max": 45}}),
    ("Sternoclavicular (L)", "saddle", [B_STERNUM, B_CLAV_L], 3, None,
     {"flexionExtension": {"min": -15, "max": 15}, "abductionAdduction": {"min": -15, "max": 15}, "internalExternalRotation": {"min": -45, "max": 45}}),
    ("Acromioclavicular (R)", "plane", [B_CLAV_R, B_SCAP_R], 3, None,
     {"flexionExtension": {"min": -10, "max": 10}, "abductionAdduction": {"min": -10, "max": 10}, "internalExternalRotation": {"min": -20, "max": 20}}),
    ("Acromioclavicular (L)", "plane", [B_CLAV_L, B_SCAP_L], 3, None,
     {"flexionExtension": {"min": -10, "max": 10}, "abductionAdduction": {"min": -10, "max": 10}, "internalExternalRotation": {"min": -20, "max": 20}}),
    ("Sacroiliac (R)", "plane", [B_SACRUM, B_HIP_R], 1, None,
     {"flexionExtension": {"min": -4, "max": 4}}),
    ("Sacroiliac (L)", "plane", [B_SACRUM, B_HIP_L], 1, None,
     {"flexionExtension": {"min": -4, "max": 4}}),
    ("Radioulnar proximal (R)", "pivot", [B_RAD_R, B_ULNA_R], 1, None,
     {"internalExternalRotation": {"min": -80, "max": 85}}),
    ("Radioulnar proximal (L)", "pivot", [B_RAD_L, B_ULNA_L], 1, None,
     {"internalExternalRotation": {"min": -80, "max": 85}}),
    # === CRANIAL JOINTS ===
    ("TMJ (R)", "condyloid", [B_TEMPORAL_R, B_MANDIBLE], 2, None,
     {"flexionExtension": {"min": 0, "max": 50}, "abductionAdduction": {"min": -10, "max": 10}}),
    ("TMJ (L)", "condyloid", [B_TEMPORAL_L, B_MANDIBLE], 2, None,
     {"flexionExtension": {"min": 0, "max": 50}, "abductionAdduction": {"min": -10, "max": 10}}),
    ("Atlanto-occipital", "condyloid", [B_C1, B_OCCIPITAL], 2,
     {"primary": vec3(0, 0, 1), "secondary": vec3(1, 0, 0)},
     {"flexionExtension": {"min": -10, "max": 25}, "abductionAdduction": {"min": -5, "max": 5}}),
    # === SUBTALAR ===
    ("Subtalar (R)", "plane", [B_FOOT_R_TALUS, B_FOOT_R_CALCANEUS], 1, None,
     {"flexionExtension": {"min": -15, "max": 30}}),
    ("Subtalar (L)", "plane", [B_FOOT_L_START + 1, B_FOOT_L_START], 1, None,
     {"flexionExtension": {"min": -15, "max": 30}}),
    # === MISSING INTERVERTEBRAL JOINTS (7) ===
    ("T11-T10 intervertebral", "cartilaginous", [B_T12 + 1, B_T12 + 2], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T10-T9 intervertebral", "cartilaginous", [B_T12 + 2, B_T12 + 3], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T8-T7 intervertebral", "cartilaginous", [B_T12 + 4, B_T12 + 5], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T7-T6 intervertebral", "cartilaginous", [B_T12 + 5, B_T12 + 6], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T6-T5 intervertebral", "cartilaginous", [B_T12 + 6, B_T12 + 7], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T4-T3 intervertebral", "cartilaginous", [B_T12 + 8, B_T12 + 9], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    ("T3-T2 intervertebral", "cartilaginous", [B_T12 + 9, B_T12 + 10], 3, None,
     {"flexionExtension": {"min": -2, "max": 5}}),
    # === COSTOVERTEBRAL JOINTS (24: R1-R12 + L1-L12) ===
    # Reference: Standring, Gray's Anatomy 42nd ed., Ch. 54
] + [
    (f"Costovertebral R{i+1}", "plane", [B_RIB_R[i], B_T1 - i], 1, None,
     {"flexionExtension": {"min": -3, "max": 3}})
    for i in range(12)
] + [
    (f"Costovertebral L{i+1}", "plane", [B_RIB_L[i], B_T1 - i], 1, None,
     {"flexionExtension": {"min": -3, "max": 3}})
    for i in range(12)
] + [
    # === CERVICAL IVDs (C6-C5 through C3-C2) ===
    ("C6-C5 intervertebral", "cartilaginous", [B_C7 + 1, B_C7 + 2], 3, None,
     {"flexionExtension": {"min": -5, "max": 15}, "abductionAdduction": {"min": -5, "max": 5}}),
    ("C5-C4 intervertebral", "cartilaginous", [B_C7 + 2, B_C7 + 3], 3, None,
     {"flexionExtension": {"min": -5, "max": 15}, "abductionAdduction": {"min": -5, "max": 5}}),
    ("C4-C3 intervertebral", "cartilaginous", [B_C7 + 3, B_C7 + 4], 3, None,
     {"flexionExtension": {"min": -5, "max": 15}, "abductionAdduction": {"min": -5, "max": 5}}),
    ("C3-C2 intervertebral", "cartilaginous", [B_C7 + 4, B_C7 + 5], 3, None,
     {"flexionExtension": {"min": -5, "max": 15}, "abductionAdduction": {"min": -5, "max": 5}}),
]
assert len(JOINT_DEFS) == 72


__all__ = [name for name in globals() if not name.startswith("__")]

