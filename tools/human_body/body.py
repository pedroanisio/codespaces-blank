from .shared import *
from .skeleton import *
from .joints_data import *
from .joints_muscles import *
from .anatomy import *
from .geometry import *

def gen_hair(height: float) -> dict:
    return {
        "style": random.choice(["Curly, short", "Straight, medium", "Wavy, long", "Buzz cut", "Afro"]),
        "color": color(random.randint(20, 80), random.randint(15, 60), random.randint(10, 50)),
        "length": random.randint(2, 25),
        "density": round(random.uniform(0.5, 0.95), 2),
        "transform": tf(0, height, 0),
    }


# =============================================================================
# SEGMENTS — 15 (bone lists updated for 206-bone layout)
# =============================================================================

# Trunk bones: all thoracic vertebrae + sternum + 24 ribs + scapulae + clavicles
_TRUNK_BONES = (list(range(B_L5, B_T1 + 1))            # L5–T1 (17 vertebrae)
                + [B_STERNUM]                             # sternum
                + B_RIB_R + B_RIB_L                       # 24 individual ribs
                + [B_SCAP_R, B_SCAP_L, B_CLAV_R, B_CLAV_L])

# Head-neck bones: cervical vertebrae + all cranial + facial + hyoid + ossicles
_HEAD_BONES = (list(range(B_C7, B_C1 + 1))              # C7–C1 (7 vertebrae)
               + list(range(B_FRONTAL, B_ETHMOID + 1))    # 8 cranial
               + list(range(B_MAXILLA_R, B_MANDIBLE + 1)) # 14 facial
               + [B_HYOID]                                  # hyoid
               + list(range(B_MALLEUS_R, B_STAPES_L + 1))) # 6 ossicles

# Hand R: all 27 bones (indices 100–126)
_HAND_R_BONES = list(range(100, 127))
_HAND_L_BONES = list(range(127, 154))

# Foot R: all 26 bones (indices 154–179)
_FOOT_R_BONES = list(range(154, 180))
_FOOT_L_BONES = list(range(180, 206))

# De Leva P (1996) Table 2-4: mass fraction, segment length (cm), CoM ratio (proximal)
# Trunk = upper + middle trunk only (pelvis is separate segment)
SEG_DEFS = [
    ("Pelvis", [B_HIP_R, B_HIP_L, B_SACRUM, B_COCCYX], None, [J_HIP_R, J_HIP_L], 0.1117, 18, 0.6115),
    ("Thigh (R)", [B_FEM_R], J_HIP_R, [J_KNEE_R], 0.1416, 45, 0.4095),
    ("Thigh (L)", [B_FEM_L], J_HIP_L, [J_KNEE_L], 0.1416, 45, 0.4095),
    ("Shank (R)", [B_TIB_R, B_FIB_R, B_PAT_R], J_KNEE_R, [J_ANKLE_R], 0.0433, 40, 0.4459),
    ("Shank (L)", [B_TIB_L, B_FIB_L, B_PAT_L], J_KNEE_L, [J_ANKLE_L], 0.0433, 40, 0.4459),
    ("Trunk", _TRUNK_BONES, 8, [J_SHOULDER_R, J_SHOULDER_L], 0.3229, 46, 0.4486),
    ("Head-neck", _HEAD_BONES, 18, [], 0.0694, 22, 0.5976),
    ("Upper arm (R)", [B_HUMER_R], J_SHOULDER_R, [J_ELBOW_R], 0.0271, 36, 0.5772),
    ("Upper arm (L)", [B_HUMER_L], J_SHOULDER_L, [J_ELBOW_L], 0.0271, 36, 0.5772),
    ("Forearm (R)", [B_RAD_R, B_ULNA_R], J_ELBOW_R, [J_WRIST_R], 0.0162, 26, 0.4574),
    ("Forearm (L)", [B_RAD_L, B_ULNA_L], J_ELBOW_L, [J_WRIST_L], 0.0162, 26, 0.4574),
    ("Hand (R)", _HAND_R_BONES, J_WRIST_R, [], 0.0061, 19, 0.7474),
    ("Hand (L)", _HAND_L_BONES, J_WRIST_L, [], 0.0061, 19, 0.7474),
    ("Foot (R)", _FOOT_R_BONES, J_ANKLE_R, [], 0.0137, 26, 0.4415),
    ("Foot (L)", _FOOT_L_BONES, J_ANKLE_L, [], 0.0137, 26, 0.4415),
]


def gen_segments(r: Reg, weight: float, sex: str = "male") -> list[dict]:
    """Generate body segments with sex-specific inertial properties.

    Segment mass fractions, CoM ratios, and radii of gyration are from:
      De Leva P, "Adjustments to Zatsiorsky-Seluyanov's segment inertia
      parameters", J Biomech 29(9):1223-1230, 1996, Tables 2-4.

    The SEG_DEFS table carries the male values as defaults. Female values
    are applied via sex-specific overrides when biologicalSex == 'female'.

    Inertia tensor is computed from radius of gyration ratios:
      I_xx = m × (ρ_sagittal × L)²
      I_yy = m × (ρ_longitudinal × L)²
      I_zz = m × (ρ_frontal × L)²
    where ρ is the ratio and L is the segment length.
    """
    # De Leva (1996) female overrides: (mass_frac, com_ratio)
    # Trunk = upper + middle trunk (excluding pelvis), same as male partitioning
    _FEMALE: dict[str, tuple[float, float]] = {
        "Pelvis":       (0.1247, 0.5920),
        "Thigh (R)":    (0.1478, 0.4283),
        "Thigh (L)":    (0.1478, 0.4283),
        "Shank (R)":    (0.0481, 0.4416),
        "Shank (L)":    (0.0481, 0.4416),
        "Trunk":        (0.3010, 0.4964),  # female upper+middle trunk = 0.4257 - 0.1247
        "Head-neck":    (0.0668, 0.4841),
        "Upper arm (R)": (0.0255, 0.4559),
        "Upper arm (L)": (0.0255, 0.4559),
        "Forearm (R)":  (0.0138, 0.4343),
        "Forearm (L)":  (0.0138, 0.4343),
        "Hand (R)":     (0.0056, 0.7474),
        "Hand (L)":     (0.0056, 0.7474),
        "Foot (R)":     (0.0129, 0.4014),
        "Foot (L)":     (0.0129, 0.4014),
    }

    # Radii of gyration ratios (ρ/L): (sagittal, longitudinal, frontal)
    # De Leva (1996) Table 4 — male values
    _GYRATION: dict[str, tuple[float, float, float]] = {
        "Pelvis":       (0.313, 0.157, 0.315),
        "Thigh (R)":    (0.329, 0.149, 0.329),
        "Thigh (L)":    (0.329, 0.149, 0.329),
        "Shank (R)":    (0.275, 0.103, 0.271),
        "Shank (L)":    (0.275, 0.103, 0.271),
        "Trunk":        (0.372, 0.191, 0.362),
        "Head-neck":    (0.362, 0.312, 0.376),
        "Upper arm (R)": (0.285, 0.158, 0.269),
        "Upper arm (L)": (0.285, 0.158, 0.269),
        "Forearm (R)":  (0.276, 0.121, 0.265),
        "Forearm (L)":  (0.276, 0.121, 0.265),
        "Hand (R)":     (0.288, 0.235, 0.184),
        "Hand (L)":     (0.288, 0.235, 0.184),
        "Foot (R)":     (0.257, 0.124, 0.245),
        "Foot (L)":     (0.257, 0.124, 0.245),
    }

    segs = []
    for name, bone_idxs, prox_j, distal_js, mass_frac, seg_len, com_ratio in SEG_DEFS:
        sid = uid(); r.segment_ids.append(sid)

        # Apply sex-specific overrides
        if sex == "female" and name in _FEMALE:
            mass_frac, com_ratio = _FEMALE[name]

        seg_mass = round(weight * mass_frac, 2)

        # Inertia from radii of gyration
        rho = _GYRATION.get(name, (0.3, 0.15, 0.3))
        ixx = round(seg_mass * (rho[0] * seg_len) ** 2, 1)   # sagittal
        iyy = round(seg_mass * (rho[1] * seg_len) ** 2, 1)   # longitudinal
        izz = round(seg_mass * (rho[2] * seg_len) ** 2, 1)   # frontal

        segs.append({
            "id": sid, "name": name,
            "boneIds": [r.bone_ids[i] for i in bone_idxs],
            "proximalJointId": r.joint_ids[prox_j] if prox_j is not None else None,
            "distalJointIds": [r.joint_ids[j] for j in distal_js],
            "mass": seg_mass,
            "centerOfMass": vec3(0, round(seg_len * com_ratio, 2), 0),
            "inertiaTensor": sym_tensor(ixx, iyy, izz),
            "segmentLength": seg_len,
        })
    return segs
# =============================================================================
# POSES, LOADING CONDITIONS, DERIVATION GRAPH, CONSTITUTIVE LAWS
# (unchanged from 52-bone version — they reference joints/segments, not bones directly)
# =============================================================================

def gen_current_pose(r: Reg) -> dict:
    r.pose_id = uid()
    joint_states = []
    n_static = len(JOINT_DEFS)  # statically defined joints
    n_total = len(r.joint_ids)  # all joints including programmatic hand/foot
    for i in range(n_total):
        if i < n_static:
            dof = JOINT_DEFS[i][3]
        else:
            dof = 1  # programmatic joints default to 1-DOF hinge
        angles: dict = {"flexionExtension": round(random.uniform(-5, 15), 1),
                        "abductionAdduction": 0, "internalExternalRotation": 0}
        if dof >= 2:
            angles["abductionAdduction"] = round(random.uniform(-5, 5), 1)
        if dof >= 3:
            angles["internalExternalRotation"] = round(random.uniform(-5, 5), 1)
        joint_states.append({"jointId": r.joint_ids[i], "angles": angles})
    return {"id": r.pose_id, "name": "contrapposto", "rootSegmentId": r.segment_ids[0],
            "rootPose": rigid_pose(0, 95, 0, small_tilt_quat(2, 5, 1)), "jointStates": joint_states}
def gen_saved_poses(r: Reg) -> list[dict]:
    """Generate named poses: anatomical, T-pose, seated, mid-stance gait.

    Joint angles for gait from:
      Winter DA, "Biomechanics and Motor Control of Human Movement",
      4th ed., Ch.3, Table 3.1 (2009).
    """
    r.saved_pose_id = uid()
    major = [J_HIP_R, J_HIP_L, J_KNEE_R, J_KNEE_L, J_SHOULDER_R, J_SHOULDER_L, J_ELBOW_R, J_ELBOW_L]
    all_joints = list(range(len(r.joint_ids)))

    def _pose(pid, name, root_y, joint_angles):
        """Create a pose with specified joint angles (dict of joint_idx → angle_dict)."""
        states = []
        for ji in all_joints:
            angles = joint_angles.get(ji, {})
            states.append({"jointId": r.joint_ids[ji], "angles": {
                "flexionExtension": angles.get("fe", 0),
                "abductionAdduction": angles.get("aa", 0),
                "internalExternalRotation": angles.get("ie", 0),
            }})
        return {"id": pid, "name": name, "rootSegmentId": r.segment_ids[0],
                "rootPose": rigid_pose(0, root_y, 0), "jointStates": states}

    poses = []

    # 1. Anatomical position — all joints neutral
    poses.append(_pose(r.saved_pose_id, "anatomical_position", 95, {}))

    # 2. T-pose — shoulders abducted 90°, everything else neutral
    t_id = uid()
    poses.append(_pose(t_id, "t_pose", 95, {
        J_SHOULDER_R: {"aa": 90}, J_SHOULDER_L: {"aa": 90},
    }))

    # 3. Seated — hips and knees flexed ~90°
    seated_id = uid()
    poses.append(_pose(seated_id, "seated", 55, {
        J_HIP_R: {"fe": 90}, J_HIP_L: {"fe": 90},
        J_KNEE_R: {"fe": 90}, J_KNEE_L: {"fe": 90},
        J_ELBOW_R: {"fe": 90}, J_ELBOW_L: {"fe": 90},
    }))

    # 4. Mid-stance gait (R stance, L swing)
    # Winter (2009) Table 3.1: mid-stance angles
    midstance_id = uid()
    poses.append(_pose(midstance_id, "gait_midstance_r", 95, {
        J_HIP_R: {"fe": 8, "aa": -5},      # stance hip: slight flexion, adducted
        J_HIP_L: {"fe": 25, "aa": 3},       # swing hip: flexing forward
        J_KNEE_R: {"fe": 15},                # stance knee: slight flexion
        J_KNEE_L: {"fe": 60},                # swing knee: flexed for clearance
        J_ANKLE_R: {"fe": 5},                # stance ankle: slight dorsiflexion
        J_ANKLE_L: {"fe": -15},              # swing ankle: plantarflexed
        J_SHOULDER_R: {"fe": -15},            # arm swing back
        J_SHOULDER_L: {"fe": 20},             # arm swing forward
        J_ELBOW_R: {"fe": 15},
        J_ELBOW_L: {"fe": 25},
    }))

    # 5. Heel-strike (R heel contact)
    heelstrike_id = uid()
    poses.append(_pose(heelstrike_id, "gait_heelstrike_r", 95, {
        J_HIP_R: {"fe": 30, "aa": -3},       # stance hip: flexed at contact
        J_HIP_L: {"fe": -10},                 # trailing leg: extended
        J_KNEE_R: {"fe": 5},                  # stance knee: near full extension
        J_KNEE_L: {"fe": 40},                 # trailing knee: flexing
        J_ANKLE_R: {"fe": 0},                 # neutral at contact
        J_ANKLE_L: {"fe": -20},               # push-off plantarflexion
        J_SHOULDER_R: {"fe": -25},
        J_SHOULDER_L: {"fe": 30},
        J_ELBOW_R: {"fe": 20},
        J_ELBOW_L: {"fe": 30},
    }))

    # 6. Toe-off (R push-off)
    toeoff_id = uid()
    poses.append(_pose(toeoff_id, "gait_toeoff_r", 95, {
        J_HIP_R: {"fe": -10},                 # push-off hip: extended
        J_HIP_L: {"fe": 30},                  # swing hip: flexed
        J_KNEE_R: {"fe": 40},                 # push-off knee: flexing
        J_KNEE_L: {"fe": 5},                  # stance knee: extending
        J_ANKLE_R: {"fe": -20},               # push-off: plantarflexed
        J_ANKLE_L: {"fe": 5},                 # stance: dorsiflexed
        J_SHOULDER_R: {"fe": 25},
        J_SHOULDER_L: {"fe": -20},
        J_ELBOW_R: {"fe": 30},
        J_ELBOW_L: {"fe": 15},
    }))

    return poses
def gen_loading_conditions(r: Reg, weight: float) -> list[dict]:
    """Generate multiple loading conditions covering common biomechanical scenarios.

    Force magnitudes from:
      - GRF: Winter (2009) Table 4.1 — normalized to body weight
      - Joint reactions: Bergmann et al., J Biomech 34(7):859-871, 2001 (hip)
      - Muscle forces: estimated from inverse dynamics solutions
    """
    conditions: list[dict] = []

    def _grf(name, mag, side, seg_idx):
        return {"id": uid(), "name": name, "forceType": "ground_reaction", "magnitude": mag, "direction": unit_vec3(0,1,0),
                "centerOfPressure": vec3(), "vertical": mag*0.98, "anteroposterior": mag*0.02, "mediolateral": mag*0.01,
                "contactSide": side, "contactSegmentId": r.segment_ids[seg_idx]}

    def _mf(name, mag, mname):
        mid = r.muscle_ids[r.muscle_name_to_idx[mname]] if mname in r.muscle_name_to_idx else uid()
        return {"id": uid(), "name": name, "forceType": "muscle", "magnitude": mag, "direction": unit_vec3(0,-1,0),
                "muscleId": mid, "applicationPoint": vec3(),
                "activeComponent": mag*0.9, "passiveComponent": mag*0.1}

    def _grav(si):
        m = round(weight * SEG_DEFS[si][4], 2)
        return {"id": uid(), "name": f"Weight {SEG_DEFS[si][0]}", "forceType": "gravitational",
                "magnitude": round(m * G / 100, 2), "direction": unit_vec3(0,-1,0),
                "targetSegmentId": r.segment_ids[si], "gravitationalAcceleration": G}

    def _jr(name, mag, ji):
        return {"id": uid(), "name": name, "forceType": "joint_reaction", "magnitude": mag, "direction": unit_vec3(0,1,0),
                "jointId": r.joint_ids[ji], "applicationPoint": vec3()}

    def _ext(name, mag, seg_idx, desc="external load"):
        return {"id": uid(), "name": name, "forceType": "external_applied", "magnitude": mag, "direction": unit_vec3(0,-1,0),
                "applicationPoint": vec3(), "targetSegmentId": r.segment_ids[seg_idx],
                "description": desc, "distributed": False}

    def _lig(name, mag, lig_name, ji):
        lid = None
        for i, l in enumerate(r.ligament_ids):
            if i < len(r.ligament_ids):
                lid = l
                break
        return {"id": uid(), "name": name, "forceType": "ligamentous", "magnitude": mag, "direction": unit_vec3(0,1,0),
                "ligamentName": lig_name, "jointId": r.joint_ids[ji], "applicationPoint": vec3(),
                "strain": round(random.uniform(0.01, 0.04), 3)}

    def _inertial(name, mag, seg_idx, ax=0, ay=0, az=0):
        return {"id": uid(), "name": name, "forceType": "inertial", "magnitude": mag, "direction": unit_vec3(0,-1,0),
                "targetSegmentId": r.segment_ids[seg_idx],
                "segmentAcceleration": vec3(ax, ay, az)}

    def _contact(name, mag, contact_id, seg_idx):
        return {"id": uid(), "name": name, "forceType": "contact", "magnitude": mag, "direction": unit_vec3(0,1,0),
                "contactId": contact_id, "applicationPoint": vec3(),
                "normalForce": mag, "targetSegmentId": r.segment_ids[seg_idx]}

    def _drag(name, mag, seg_idx, cd=1.1, area=1500):
        return {"id": uid(), "name": name, "forceType": "aerodynamic_drag", "magnitude": mag, "direction": unit_vec3(0,0,-1),
                "targetSegmentId": r.segment_ids[seg_idx], "dragCoefficient": cd,
                "frontalArea": area, "fluidDensity": 0.001225,
                "relativeVelocity": vec3(0, 0, round(random.uniform(100, 500), 1))}

    def _buoy(name, mag, seg_idx, disp_vol, density=1.0):
        return {"id": uid(), "name": name, "forceType": "buoyancy", "magnitude": mag, "direction": unit_vec3(0,1,0),
                "targetSegmentId": r.segment_ids[seg_idx], "displacedVolume": disp_vol,
                "fluidDensity": density, "centerOfBuoyancy": vec3(0, 50, 0)}

    def _equil(forces: list[dict]) -> dict:
        """Compute equilibrium from the actual force list.

        Sums all force vectors (magnitude × direction) to get the net force.
        isStatic is true only when the residual magnitude is below a threshold
        (1% of total body weight ≈ 7 N for a 75 kg person).

        This replaces the previous fabricated equilibrium that claimed isStatic=True
        with random nonzero residuals — a self-contradiction flagged in assessment_01.md §2.2.
        """
        fx, fy, fz = 0.0, 0.0, 0.0
        for f in forces:
            mag = f.get("magnitude", 0)
            d = f.get("direction", {"x": 0, "y": 0, "z": 0})
            fx += mag * d["x"]
            fy += mag * d["y"]
            fz += mag * d["z"]
        nf = vec3(round(fx, 2), round(fy, 2), round(fz, 2))
        res_force = round(math.sqrt(fx * fx + fy * fy + fz * fz), 2)
        # Static threshold: 1% of body weight (tw ≈ weight * 9.81)
        threshold = tw * 0.01
        return {
            "netForce": nf,
            "netMoment": vec3(0, 0, 0),  # moment computation requires application points — left as zero
            "isStatic": res_force < threshold,
            "residualForceMagnitude": res_force,
            "residualMomentMagnitude": 0.0,
        }

    def _contacts_bilateral():
        return [{"id": uid(), "name": "Right foot ground contact", "contactType": "foot_ground",
                  "segmentId": r.segment_ids[13], "surfaceNormal": unit_vec3(0,1,0), "contactPoint": vec3(-9,0,5), "isActive": True},
                {"id": uid(), "name": "Left foot ground contact", "contactType": "foot_ground",
                  "segmentId": r.segment_ids[14], "surfaceNormal": unit_vec3(0,1,0), "contactPoint": vec3(9,0,5), "isActive": True}]

    tw = weight * 9.81
    gravs = [_grav(si) for si in range(15)]

    # --- LC 1: Double-leg quiet standing ---
    f1 = [_grf("GRF (R foot)", round(tw*0.5), "right", 13),
          _grf("GRF (L foot)", round(tw*0.5), "left", 14)]
    f1 += [_mf("R erector spinae", 150, "Erector Spinae (R)"),
           _mf("L erector spinae", 150, "Erector Spinae (L)"),
           _mf("R soleus standing", 80, "Soleus (R)"),
           _mf("L soleus standing", 80, "Soleus (L)")]
    f1 += gravs
    f1 += [_jr("R hip joint reaction", round(tw*0.65), J_HIP_R),
           _jr("L hip joint reaction", round(tw*0.65), J_HIP_L),
           _jr("L5-S1 joint reaction", round(tw*0.55), J_L5S1)]
    # Ligamentous: passive restraint in standing
    f1 += [_lig("ACL passive (R)", 25, "Anterior cruciate ligament (R)", J_KNEE_R),
           _lig("ACL passive (L)", 25, "Anterior cruciate ligament (L)", J_KNEE_L)]
    conditions.append({"id": uid(), "name": "double_leg_standing", "poseId": r.saved_pose_id,
                        "forces": f1, "moments": [], "contacts": _contacts_bilateral(), "equilibrium": _equil(f1)})

    # --- LC 2: Contrapposto (asymmetric weight shift) ---
    rf = random.uniform(0.55, 0.75)
    f2 = [_grf("GRF (R foot)", round(tw*rf), "right", 13),
          _grf("GRF (L foot)", round(tw*(1-rf)), "left", 14)]
    f2 += [_mf("Rectus femoris force (R)", 285, "Rectus Femoris (R)"),
           _mf("Gastrocnemius force (R)", 180, "Gastrocnemius (R)"),
           _mf("L quad force", 120, "Rectus Femoris (L)"),
           _mf("L gastroc", 80, "Gastrocnemius (L)"),
           _mf("R erector spinae", 350, "Erector Spinae (R)"),
           _mf("L erector spinae", 340, "Erector Spinae (L)"),
           _mf("R gluteus max", 180, "Gluteus Maximus (R)"),
           _mf("R soleus", 220, "Soleus (R)")]
    f2 += gravs
    f2 += [_jr("R knee joint reaction", 1800, J_KNEE_R),
           _jr("R hip joint reaction", 2400, J_HIP_R),
           _jr("L5-S1 joint reaction", 900, J_L5S1)]
    km = {"id": uid(), "name": "Knee resultant moment (R)", "momentType": "joint_resultant",
          "aboutJointId": r.joint_ids[J_KNEE_R], "axis": unit_vec3(0,0,1), "magnitude": round(random.uniform(800,1500))}
    conditions.append({"id": uid(), "name": "contrapposto_standing", "poseId": r.pose_id,
                        "forces": f2, "moments": [km], "contacts": _contacts_bilateral(), "equilibrium": _equil(f2)})

    # --- LC 3: Mid-stance gait (R stance phase) ---
    # GRF ~ 1.0 BW at mid-stance (Winter 2009, Fig 4.4)
    f3 = [_grf("GRF (R foot midstance)", round(tw*1.0), "right", 13)]
    f3 += [_mf("R gluteus medius", 800, "Gluteus Medius (R)"),     # primary hip stabilizer
           _mf("R soleus midstance", 350, "Soleus (R)"),
           _mf("R gastroc midstance", 200, "Gastrocnemius (R)"),
           _mf("R tibialis ant", 50, "Tibialis Anterior (R)"),
           _mf("R vastus lat", 250, "Vastus Lateralis (R)"),
           _mf("R erector spinae gait", 200, "Erector Spinae (R)"),
           _mf("L erector spinae gait", 200, "Erector Spinae (L)")]
    f3 += gravs
    # Hip JRF ~ 2.5 BW at mid-stance (Bergmann 2001)
    f3 += [_jr("R hip JRF midstance", round(tw*2.5), J_HIP_R),
           _jr("R knee JRF midstance", round(tw*1.5), J_KNEE_R),
           _jr("R ankle JRF midstance", round(tw*3.0), J_ANKLE_R)]
    # Inertial: swing leg d'Alembert forces (~0.3g centripetal at swing thigh)
    # Reference: Winter (2009) Ch.5 — segment accelerations during gait
    f3 += [_inertial("L thigh inertial (swing)", round(weight*0.14*300), 2, 0, -300, 0),
           _inertial("L shank inertial (swing)", round(weight*0.046*500), 4, 0, -500, 0)]
    # Use the 4th saved pose (gait_midstance_r)
    ms_pose_id = r.saved_pose_id  # will be overridden at runtime
    conditions.append({"id": uid(), "name": "gait_midstance_r", "poseId": ms_pose_id,
                        "forces": f3, "moments": [], "contacts": _contacts_bilateral()[:1], "equilibrium": _equil(f3)})

    # --- LC 4: Heel-strike (R foot initial contact) ---
    # GRF ~ 1.2 BW at heel-strike impact (Winter 2009)
    f4 = [_grf("GRF (R foot heelstrike)", round(tw*1.2), "right", 13),
          _grf("GRF (L foot heelstrike)", round(tw*0.15), "left", 14)]  # trailing foot lifting
    f4 += [_mf("R tibialis ant heelstrike", 250, "Tibialis Anterior (R)"),  # eccentric braking
           _mf("R quad heelstrike", 400, "Rectus Femoris (R)"),
           _mf("R hamstring heelstrike", 200, "Biceps Femoris (R)"),
           _mf("R gluteus max heelstrike", 350, "Gluteus Maximus (R)")]
    f4 += gravs
    f4 += [_jr("R hip JRF heelstrike", round(tw*3.0), J_HIP_R),
           _jr("R knee JRF heelstrike", round(tw*2.0), J_KNEE_R)]
    conditions.append({"id": uid(), "name": "gait_heelstrike_r", "poseId": ms_pose_id,
                        "forces": f4, "moments": [], "contacts": _contacts_bilateral(), "equilibrium": _equil(f4)})

    # --- LC 5: Toe-off (R push-off) ---
    # GRF ~ 1.1 BW at toe-off (Winter 2009)
    f5 = [_grf("GRF (R foot toeoff)", round(tw*1.1), "right", 13)]
    f5 += [_mf("R gastroc toeoff", 1200, "Gastrocnemius (R)"),     # peak ankle plantarflexor
           _mf("R soleus toeoff", 2500, "Soleus (R)"),              # dominant push-off muscle
           _mf("R hip flexor toeoff", 300, "Iliopsoas (R)")]
    f5 += gravs
    f5 += [_jr("R ankle JRF toeoff", round(tw*5.0), J_ANKLE_R),    # peak ankle force
           _jr("R hip JRF toeoff", round(tw*2.0), J_HIP_R)]
    conditions.append({"id": uid(), "name": "gait_toeoff_r", "poseId": ms_pose_id,
                        "forces": f5, "moments": [], "contacts": _contacts_bilateral()[:1], "equilibrium": _equil(f5)})

    # --- LC 6: External load — carrying object + wind + contact ---
    # Scenario: carrying 10 kg box, walking into 3 m/s headwind
    # Reference: Kinoshita, Ergonomics 39(9):1163-1178, 1996 (manual handling)
    box_weight = 10 * G / 100  # 10 kg in N (G in cm/s²)
    contacts6 = _contacts_bilateral()
    # Contact of box against trunk
    box_contact_id = contacts6[0]["id"]  # reuse contact ID for ref
    contacts6.append({"id": uid(), "name": "Box-trunk contact", "contactType": "body_surface",
                       "segmentId": r.segment_ids[5], "surfaceNormal": unit_vec3(0,0,1),
                       "contactPoint": vec3(0, 120, 8), "isActive": True})
    box_cid = contacts6[-1]["id"]
    f6 = [_grf("GRF (R foot carry)", round(tw*0.55 + box_weight*0.5), "right", 13),
          _grf("GRF (L foot carry)", round(tw*0.55 + box_weight*0.5), "left", 14)]
    f6 += [_ext("Carried box weight", round(box_weight), 5, "10 kg box held at trunk level"),
           _mf("R erector spinae carry", 450, "Erector Spinae (R)"),
           _mf("L erector spinae carry", 450, "Erector Spinae (L)"),
           _mf("R biceps carry", 120, "Biceps Brachii (R)"),
           _mf("L biceps carry", 120, "Biceps Brachii (L)")]
    f6 += gravs
    f6 += [_jr("L5-S1 JRF carry", round(tw*1.2), J_L5S1)]
    # Contact force: box pressing against trunk
    f6.append(_contact("Box-trunk normal force", round(box_weight*0.3), box_cid, 5))
    # Aerodynamic drag: 3 m/s headwind (300 cm/s), trunk frontal area ~1500 cm²
    # F_drag = 0.5 × ρ × Cd × A × v² = 0.5 × 0.001225 × 1.1 × 1500 × 300² ≈ 9.1 N
    f6.append(_drag("Headwind drag (trunk)", 9, 5, cd=1.1, area=1500))
    # Ligamentous passive restraint at L5-S1 under load
    f6.append(_lig("PLL L5-S1 carry", 80, "Posterior longitudinal ligament (lumbar)", J_L5S1))
    conditions.append({"id": uid(), "name": "carrying_external_load", "poseId": r.saved_pose_id,
                        "forces": f6, "moments": [], "contacts": contacts6, "equilibrium": _equil(f6)})

    # --- LC 7: Aquatic — partial submersion with buoyancy ---
    # Scenario: standing in waist-deep water (pelvis + legs submerged)
    # Reference: Harrison & Teixeira, J Sports Sci 19(7):497-504, 2001
    f7 = [_grf("GRF (R foot underwater)", round(tw*0.3), "right", 13),
          _grf("GRF (L foot underwater)", round(tw*0.3), "left", 14)]
    f7 += gravs
    # Buoyancy on submerged segments: pelvis, thighs, shanks, feet
    # displaced volume ≈ segment mass / body density (~1.05 g/cm³) for each segment
    for si, seg_name in [(0, "pelvis"), (1, "thigh R"), (2, "thigh L"),
                          (3, "shank R"), (4, "shank L"), (13, "foot R"), (14, "foot L")]:
        seg_mass_kg = weight * SEG_DEFS[si][4]
        disp_vol = round(seg_mass_kg * 1000 / 1.05, 1)  # g / (g/cm³) = cm³
        buoy_force = round(disp_vol * 1.0 * G / 100, 1)  # ρ_water × V × g
        f7.append(_buoy(f"Buoyancy {seg_name}", buoy_force, si, disp_vol, density=1.0))
    f7 += [_jr("R hip JRF aquatic", round(tw*0.4), J_HIP_R),
           _jr("L hip JRF aquatic", round(tw*0.4), J_HIP_L)]
    # Water drag on legs during walking (~0.5 m/s, Cd=1.2 for cylinders)
    f7.append(_drag("Water drag (R shank)", 15, 3, cd=1.2, area=800))
    f7.append(_drag("Water drag (L shank)", 15, 4, cd=1.2, area=800))
    conditions.append({"id": uid(), "name": "aquatic_standing", "poseId": r.saved_pose_id,
                        "forces": f7, "moments": [], "contacts": _contacts_bilateral(), "equilibrium": _equil(f7)})

    return conditions
HILL_EQ = "F_muscle ≤ F_max × [a × f_L(L̃) × f_V(Ṽ) + f_PE(L̃)]"
LIG_EQ = "F_lig = piecewise(ε ≤ 0: 0, ε ≤ ε_toe: k_toe×ε^n, ε ≤ ε_fail: k×(ε-ε₀), ε > ε_fail: FAILURE)"
BONE_YIELD_EQ = "σ_bone = F / A ≤ σ_yield (rigid body assumption valid when σ_bone << σ_yield)"
HILL_V = [{"assumption": "Quasi-static muscle contraction", "validWhen": "Contraction velocity < V_max",
           "violatedWhen": "Ballistic motion", "consequence": "Force-velocity underestimates eccentric forces"}]
LIG_V = [{"assumption": "Ligament intact and within elastic range", "validWhen": "Strain < ultimate strain",
          "violatedWhen": "Ligament rupture", "consequence": "Force-strain model invalid"}]
BONE_V = [{"assumption": "Bones are rigid bodies", "validWhen": "Bone stress << yield stress",
           "violatedWhen": "Impact loading, stress near 130 MPa", "consequence": "Rigid body dynamics underestimates deformation"}]


def gen_derivation_graph() -> dict:
    ids = [uid() for _ in range(10)]
    rules = [
        {"id": ids[0], "name": "muscle_pcsa", "law": {"name": "PCSA definition", "equation": "PCSA = V / L_opt", "domain": "definition"},
         "inputFields": ["muscles[*].volume", "muscles[*].optimalFiberLength"], "outputField": "muscles[*].pcsa"},
        {"id": ids[1], "name": "forward_kinematics", "law": {"name": "Forward kinematics", "equation": "T_global = T_root × Π T_joint(θ)", "domain": "kinematics"},
         "inputFields": ["currentPose.rootPose", "currentPose.jointStates[*].angles", "segments[*].proximalJointId", "joints[*].axes"], "outputField": "currentPose.segmentStates[*].globalPose"},
        {"id": ids[2], "name": "segment_global_com", "law": {"name": "Coordinate transformation", "equation": "r_global = T_global × r_local", "domain": "kinematics"},
         "inputFields": ["currentPose.segmentStates[*].globalPose", "segments[*].centerOfMass"], "outputField": "currentPose.segmentStates[*].globalCenterOfMass", "dependsOn": [ids[1]]},
        {"id": ids[3], "name": "whole_body_com", "law": {"name": "Center of mass definition", "equation": "r_com = Σ(mᵢrᵢ) / Σ(mᵢ)", "domain": "definition"},
         "inputFields": ["currentPose.segmentStates[*].globalCenterOfMass", "segments[*].mass"], "outputField": "currentPose.wholeBodyCenterOfMass", "dependsOn": [ids[2]]},
        {"id": ids[4], "name": "gravitational_force_magnitude", "law": {"name": "Newton's law of gravitation (uniform field)", "equation": "F = m × g", "domain": "rigid_body_dynamics"},
         "inputFields": ["segments[*].mass", "loadingConditions[*].forces[type=gravitational].gravitationalAcceleration"], "outputField": "loadingConditions[*].forces[type=gravitational].magnitude"},
        {"id": ids[5], "name": "equilibrium_net_force", "law": {"name": "Force equilibrium", "equation": "F_net = Σ Fᵢ", "domain": "rigid_body_dynamics"},
         "inputFields": ["loadingConditions[*].forces[*].magnitude", "loadingConditions[*].forces[*].direction"], "outputField": "loadingConditions[*].equilibrium.netForce"},
        {"id": ids[6], "name": "equilibrium_residual_magnitude", "law": {"name": "Vector magnitude", "equation": "|F| = √(Fx² + Fy² + Fz²)", "domain": "definition"},
         "inputFields": ["loadingConditions[*].equilibrium.netForce"], "outputField": "loadingConditions[*].equilibrium.residualForceMagnitude", "dependsOn": [ids[5]]},
        {"id": ids[7], "name": "equilibrium_static_check", "law": {"name": "Static equilibrium criterion", "equation": "|F_net| < ε AND |M_net| < ε", "domain": "rigid_body_dynamics"},
         "inputFields": ["loadingConditions[*].equilibrium.residualForceMagnitude", "loadingConditions[*].equilibrium.residualMomentMagnitude"], "outputField": "loadingConditions[*].equilibrium.isStatic", "dependsOn": [ids[6]]},
        {"id": ids[8], "name": "fbd_translational_residual", "law": {"name": "Newton's second law", "equation": "ΣF = ma", "domain": "rigid_body_dynamics"},
         "inputFields": ["freeBodyDiagrams[*].forces[*].magnitude", "freeBodyDiagrams[*].forces[*].direction", "segments[matched].mass", "currentPose.segmentStates[matched].linearAcceleration"], "outputField": "freeBodyDiagrams[*].translationalResidual"},
        {"id": ids[9], "name": "fbd_rotational_residual", "law": {"name": "Euler's equation of rotation", "equation": "ΣM = Iα", "domain": "rigid_body_dynamics"},
         "inputFields": ["freeBodyDiagrams[*].moments[*]", "segments[matched].inertiaTensor", "currentPose.segmentStates[matched].angularAcceleration"], "outputField": "freeBodyDiagrams[*].rotationalResidual"},
    ]
    return {"version": "1.0.0", "rules": rules}


def gen_constitutive_laws() -> dict:
    # P0.3: Tendon slack length ratios (L_T_slack / L_opt) per muscle.
    # Source: Delp et al., IEEE Trans Biomed Eng 37(8):757-767, 1990, Table I;
    #         Thelen, J Biomech Eng 125(1):70-77, 2003, Table 2.
    _TENDON_SLACK: dict[str, float] = {
        "Rectus Femoris": 3.46, "Biceps Femoris": 3.26, "Biceps Brachii": 2.43,
        "Triceps Brachii": 1.43, "Pectoralis Major": 0.85, "Deltoid": 1.15,
    }

    def _hill(name, mn):
        base = mn.replace(" (R)", "").replace(" (L)", "")
        slack = _TENDON_SLACK.get(base, 1.5)
        return {"lawType": "hill_muscle_model", "id": uid(), "name": name,
                "constrainedFields": {k: f"muscles[name={mn}].{k}" for k in ["muscleForce", "activation", "currentLength", "contractionVelocity", "maxIsometricForce", "optimalFiberLength", "maxContractionVelocity"]},
                "forceLength": {"widthParameter": 0.56, "minActiveForceLengthRatio": 0.5, "maxActiveForceLengthRatio": 1.5},
                "forceVelocity": {"concentricCurveShape": 0.25, "eccentricForceMax": 1.4, "eccentricCurveShape": 0.15},
                "passiveElement": {"strainAtMaxForce": 0.6, "exponentialShape": 4.0},
                "tendonCompliance": {
                    "normalizedSlackLength": round(slack, 2),
                    "strainAtMaxIsometricForce": 0.033,
                },
                "constraint": {"equation": HILL_EQ, "violationSeverity": "error", "toleranceFraction": 0.1}, "validityBoundaries": HILL_V}
    def _lig(name, ln):
        return {"lawType": "ligament_force_strain", "id": uid(), "name": name,
                "constrainedFields": {k: f"ligaments[name={ln}].{k}" for k in ["ligamentForce", "strain", "stiffness", "restingLength", "referenceStrain"]},
                "toeRegion": {"maxStrain": 0.04, "curveExponent": 2.0}, "linearRegion": {"stiffness": 200, "interceptStrain": 0.03},
                "failure": {"ultimateStrain": 0.12, "ultimateLoad": 2160}, "constraint": {"equation": LIG_EQ, "violationSeverity": "error", "strainTolerance": 0.005}, "validityBoundaries": LIG_V}
    laws = [_hill(f"hill_model_{n}", n) for n in ["Rectus Femoris (R)", "Biceps Femoris (R)", "Biceps Brachii (R)", "Triceps Brachii (R)", "Pectoralis Major (R)", "Deltoid (R)"]]
    laws += [_lig(f"force_strain_{n}", n) for n in ["Anterior cruciate ligament (R)", "Posterior cruciate ligament (R)", "Medial collateral ligament (R)", "Lateral collateral ligament (R)"]]
    laws.append({"lawType": "bone_yield_criterion", "id": uid(), "name": "rigid_body_yield_check",
                 "constrainedFields": {"jointReactionForce": "loadingConditions[*].forces[type=joint_reaction].magnitude"},
                 "parameters": {"corticalTensileYield": 130, "corticalCompressiveYield": 190, "trabecularCompressiveYield": 5, "fatigueReductionFactor": 0.6},
                 "constraint": {"equation": BONE_YIELD_EQ, "violationSeverity": "error"}, "validityBoundaries": BONE_V})
    return {"version": "1.0.0", "laws": laws}


# =============================================================================
# ROOT ENTITY


def _gen_motion_sequences(r: Reg) -> list[dict]:
    """Generate a full gait cycle motion sequence (8 keyframes at ~140ms intervals).

    Joint angles interpolated through the gait cycle phases:
      0%   = heel-strike (R)     →  initial contact
      12%  = loading response    →  weight acceptance
      31%  = mid-stance          →  single-limb support
      50%  = terminal stance     →  heel rise
      62%  = pre-swing (toe-off) →  push-off
      75%  = mid-swing           →  limb advancement
      87%  = terminal swing      →  deceleration
      100% = heel-strike (next)  →  cycle repeats

    Data from: Winter DA, 'Biomechanics and Motor Control of Human Movement',
    4th ed., Ch. 3, Table 3.1, Fig. 3.2 (2009).

    Gait cycle duration: ~1.1s at normal walking speed (1.3 m/s).
    """
    all_joints = list(range(len(r.joint_ids)))

    def _pose_at(name, pct, angles_dict):
        states = []
        for ji in all_joints:
            a = angles_dict.get(ji, {})
            states.append({"jointId": r.joint_ids[ji], "angles": {
                "flexionExtension": a.get("fe", 0),
                "abductionAdduction": a.get("aa", 0),
                "internalExternalRotation": a.get("ie", 0),
            }})
        return {
            "id": uid(), "name": name,
            "rootSegmentId": r.segment_ids[0],
            "rootPose": rigid_pose(0, 95, 0),
            "jointStates": states,
            "timestamp": round(pct / 100 * 1.1, 3),  # seconds into cycle
        }

    # Winter (2009) Table 3.1 — sagittal plane joint angles at % gait cycle
    # Format: {joint_idx: {"fe": degrees, "aa": degrees}}
    gait_keyframes = [
        ("heel_strike", 0, {
            J_HIP_R: {"fe": 30, "aa": -3}, J_HIP_L: {"fe": -10},
            J_KNEE_R: {"fe": 5}, J_KNEE_L: {"fe": 40},
            J_ANKLE_R: {"fe": 0}, J_ANKLE_L: {"fe": -20},
            J_SHOULDER_R: {"fe": -25}, J_SHOULDER_L: {"fe": 30},
            J_ELBOW_R: {"fe": 20}, J_ELBOW_L: {"fe": 30},
        }),
        ("loading_response", 12, {
            J_HIP_R: {"fe": 25, "aa": -5}, J_HIP_L: {"fe": -5},
            J_KNEE_R: {"fe": 18}, J_KNEE_L: {"fe": 35},
            J_ANKLE_R: {"fe": -5}, J_ANKLE_L: {"fe": -15},
            J_SHOULDER_R: {"fe": -20}, J_SHOULDER_L: {"fe": 25},
            J_ELBOW_R: {"fe": 18}, J_ELBOW_L: {"fe": 28},
        }),
        ("mid_stance", 31, {
            J_HIP_R: {"fe": 8, "aa": -5}, J_HIP_L: {"fe": 25, "aa": 3},
            J_KNEE_R: {"fe": 15}, J_KNEE_L: {"fe": 60},
            J_ANKLE_R: {"fe": 5}, J_ANKLE_L: {"fe": -15},
            J_SHOULDER_R: {"fe": -10}, J_SHOULDER_L: {"fe": 15},
            J_ELBOW_R: {"fe": 12}, J_ELBOW_L: {"fe": 22},
        }),
        ("terminal_stance", 50, {
            J_HIP_R: {"fe": -5, "aa": -4}, J_HIP_L: {"fe": 30, "aa": 2},
            J_KNEE_R: {"fe": 8}, J_KNEE_L: {"fe": 25},
            J_ANKLE_R: {"fe": -10}, J_ANKLE_L: {"fe": 5},
            J_SHOULDER_R: {"fe": 5}, J_SHOULDER_L: {"fe": -5},
            J_ELBOW_R: {"fe": 10}, J_ELBOW_L: {"fe": 15},
        }),
        ("pre_swing", 62, {
            J_HIP_R: {"fe": -10}, J_HIP_L: {"fe": 30},
            J_KNEE_R: {"fe": 40}, J_KNEE_L: {"fe": 5},
            J_ANKLE_R: {"fe": -20}, J_ANKLE_L: {"fe": 5},
            J_SHOULDER_R: {"fe": 20}, J_SHOULDER_L: {"fe": -15},
            J_ELBOW_R: {"fe": 25}, J_ELBOW_L: {"fe": 12},
        }),
        ("initial_swing", 72, {
            J_HIP_R: {"fe": 10, "aa": 2}, J_HIP_L: {"fe": 15},
            J_KNEE_R: {"fe": 65}, J_KNEE_L: {"fe": 8},
            J_ANKLE_R: {"fe": -10}, J_ANKLE_L: {"fe": 3},
            J_SHOULDER_R: {"fe": 25}, J_SHOULDER_L: {"fe": -20},
            J_ELBOW_R: {"fe": 28}, J_ELBOW_L: {"fe": 10},
        }),
        ("mid_swing", 81, {
            J_HIP_R: {"fe": 25, "aa": 3}, J_HIP_L: {"fe": 8, "aa": -5},
            J_KNEE_R: {"fe": 60}, J_KNEE_L: {"fe": 15},
            J_ANKLE_R: {"fe": -5}, J_ANKLE_L: {"fe": 5},
            J_SHOULDER_R: {"fe": 28}, J_SHOULDER_L: {"fe": -22},
            J_ELBOW_R: {"fe": 30}, J_ELBOW_L: {"fe": 8},
        }),
        ("terminal_swing", 93, {
            J_HIP_R: {"fe": 30, "aa": -2}, J_HIP_L: {"fe": -5},
            J_KNEE_R: {"fe": 8}, J_KNEE_L: {"fe": 25},
            J_ANKLE_R: {"fe": 0}, J_ANKLE_L: {"fe": -8},
            J_SHOULDER_R: {"fe": -22}, J_SHOULDER_L: {"fe": 28},
            J_ELBOW_R: {"fe": 18}, J_ELBOW_L: {"fe": 28},
        }),
    ]

    poses = [_pose_at(name, pct, angles) for name, pct, angles in gait_keyframes]

    return [{
        "id": uid(),
        "name": "normal_gait_cycle",
        "description": "Full gait cycle at self-selected speed (~1.3 m/s). R leg stance → swing → stance.",
        "sampleRate": round(len(poses) / 1.1, 1),  # ~7.3 Hz
        "duration": 1.1,
        "poses": poses,
    }]


def _gen_rendering_layer(r: Reg) -> dict:
    """Generate a rendering layer with per-subsystem color and opacity defaults.

    Rendering is separated from anatomy per Rule 30 (access patterns should
    not dictate structure). This layer overlays visual properties on entities
    referenced by ID.
    """
    bone_overrides = []
    for i, bone_id in enumerate(r.bone_ids):
        bone_overrides.append({
            "entityId": bone_id,
            "color": color(240, 230, 210, 1.0),  # ivory
            "opacity": 1.0,
            "visible": True,
            "material": material(
                baseColor=color(240, 230, 210, 1.0),
                roughness=0.45,
                metalness=0.02,
                clearcoat=0.2,
                clearcoatRoughness=0.35,
                sheen=0.15,
                sheenRoughness=0.5,
                sheenColor=color(255, 255, 240, 1.0),
            ),
        })

    muscle_overrides = []
    for i, muscle_id in enumerate(r.muscle_ids):
        muscle_overrides.append({
            "entityId": muscle_id,
            "color": color(180, 60, 50, 1.0),  # deep red
            "opacity": 0.7,
            "visible": True,
            "material": material(
                baseColor=color(180, 60, 50, 1.0),
                roughness=0.55,
                metalness=0.0,
                clearcoat=0.15,
                clearcoatRoughness=0.4,
                transmission=0.03,
                thickness=0.8,
                sheen=0.25,
                sheenRoughness=0.4,
                sheenColor=color(255, 136, 136, 1.0),
            ),
        })

    organ_overrides = []
    for i, organ_id in enumerate(r.organ_ids):
        organ_overrides.append({
            "entityId": organ_id,
            "color": color(200, 140, 120, 1.0),  # fleshy pink
            "opacity": 0.6,
            "visible": True,
            "material": material(
                baseColor=color(200, 140, 120, 1.0),
                roughness=0.5,
                metalness=0.0,
                clearcoat=0.3,
                clearcoatRoughness=0.25,
                transmission=0.1,
                thickness=1.5,
                sheen=0.15,
                sheenRoughness=0.5,
                sheenColor=color(255, 204, 204, 1.0),
            ),
        })

    vessel_overrides = []
    for i, vessel_id in enumerate(r.vessel_ids):
        vessel_overrides.append({
            "entityId": vessel_id,
            "color": color(180, 50, 50, 1.0),  # default to arterial red
            "opacity": 0.8,
            "visible": True,
            "material": material(
                baseColor=color(180, 50, 50, 1.0),
                roughness=0.4,
                metalness=0.0,
                clearcoat=0.35,
                clearcoatRoughness=0.15,
                transmission=0.12,
                thickness=0.4,
            ),
        })

    return {
        "boneOverrides": bone_overrides,
        "muscleOverrides": muscle_overrides,
        "organOverrides": organ_overrides,
        "vesselOverrides": vessel_overrides,
        "globalOpacity": 1.0,
    }


def _gen_clothing(height: float) -> list[dict]:
    """Generate basic clothing items."""
    return [
        {"id": uid(), "name": "T-shirt", "type": "top",
         "color": color(60, 80, 120, 1.0), "transform": tf(0, height * 0.75, 0),
         "fabric": "cotton jersey", "fit": "regular"},
        {"id": uid(), "name": "Jeans", "type": "bottom",
         "color": color(50, 60, 90, 1.0), "transform": tf(0, height * 0.48, 0),
         "fabric": "denim", "fit": "regular"},
        {"id": uid(), "name": "Sneakers", "type": "footwear",
         "color": color(220, 220, 220, 1.0), "transform": tf(0, 0, 5),
         "fabric": "synthetic mesh", "fit": "regular"},
    ]
# =============================================================================

def _gen_reference_frames(r: Reg) -> list[dict]:
    """Generate ISB reference frames: global lab frame + per-segment ACS.

    Global frame: +X anterior, +Y superior, +Z right lateral.
    Reference: Wu & Cavanagh, J Biomech 28(10):1257-1261, 1995.
    """
    frames = []
    gid = uid()
    frames.append({"id": gid, "name": "Global (lab)", "type": "global",
                    "parentFrameId": None, "poseInParent": rigid_pose(0, 0, 0),
                    "axisLabels": {"x": "anterior", "y": "superior", "z": "right_lateral"}})
    for si, (name, bone_idxs, prox_j, distal_js, _, seg_len, _) in enumerate(SEG_DEFS):
        fid = uid()
        if prox_j is not None and prox_j < len(JOINT_DEFS):
            jdef = JOINT_DEFS[prox_j]
            bp = [BONE_DEFS[bi][8] for bi in jdef[2][:2]]
            fx = round((bp[0][0] + bp[1][0]) / 2, 1)
            fy = round((bp[0][1] + bp[1][1]) / 2, 1)
            fz = round((bp[0][2] + bp[1][2]) / 2, 1)
        else:
            fx, fy, fz = 0, 95, 0
        frames.append({"id": fid, "name": f"{name} ACS", "type": "segment_anatomical",
                        "parentFrameId": gid, "poseInParent": rigid_pose(fx, fy, fz),
                        "axisLabels": {"x": "anterior", "y": "proximal_to_distal", "z": "right_lateral"}})
    return frames


def _gen_free_body_diagrams(r: Reg, loading: list[dict], weight: float) -> list[dict]:
    """Generate per-segment FBDs from the first loading condition.

    Each FBD isolates a segment with its gravitational, proximal, and
    distal joint reaction forces plus translational/rotational residuals.
    Reference: Winter, Biomechanics and Motor Control, 4th ed., Ch. 5.
    """
    if not loading:
        return []
    lc = loading[0]
    fbds = []
    for si, (name, bone_idxs, prox_j, distal_js, mass_frac, seg_len, _) in enumerate(SEG_DEFS):
        seg_mass = round(weight * mass_frac, 2)
        seg_w = round(seg_mass * G / 100, 2)
        forces = [{"id": uid(), "name": f"Weight {name}", "forceType": "gravitational",
                    "magnitude": seg_w, "direction": unit_vec3(0, -1, 0),
                    "targetSegmentId": r.segment_ids[si], "gravitationalAcceleration": G}]
        if prox_j is not None:
            forces.append({"id": uid(), "name": f"{name} proximal JRF",
                            "forceType": "joint_reaction", "magnitude": round(seg_w * 1.5, 2),
                            "direction": unit_vec3(0, 1, 0), "jointId": r.joint_ids[prox_j],
                            "applicationPoint": vec3()})
        for dj in distal_js:
            forces.append({"id": uid(), "name": f"{name} distal JRF",
                            "forceType": "joint_reaction", "magnitude": round(seg_w * 0.8, 2),
                            "direction": unit_vec3(0, -1, 0), "jointId": r.joint_ids[dj],
                            "applicationPoint": vec3()})
        fbds.append({"id": uid(), "name": f"FBD {name}", "segmentId": r.segment_ids[si],
                      "loadingConditionId": lc["id"], "forces": forces, "moments": [],
                      "translationalResidual": vec3(round(random.uniform(-0.5, 0.5), 2),
                                                      round(random.uniform(-0.5, 0.5), 2),
                                                      round(random.uniform(-0.2, 0.2), 2)),
                      "rotationalResidual": vec3(round(random.uniform(-1, 1), 2),
                                                   round(random.uniform(-0.5, 0.5), 2),
                                                   round(random.uniform(-0.5, 0.5), 2))})
    return fbds


# =============================================================================
# ROOT ENTITY
# =============================================================================


__all__ = [name for name in globals() if not name.startswith("__")]
