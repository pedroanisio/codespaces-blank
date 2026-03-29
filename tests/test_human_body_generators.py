import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from human_body import anatomy, body, joints_data, joints_muscles, shared, skeleton


def _build_registry(seed: int = 123, sex: str = "male"):
    random.seed(seed)
    registry = shared.Reg()
    proportions = shared.gen_proportions(0)
    weight = proportions["weight"]
    height = proportions["totalHeight"]

    skel = skeleton.gen_skeleton(registry, weight, height)
    joints = joints_muscles.gen_joints(registry)
    nerves = anatomy.gen_nerves(registry)
    tendons, muscles = joints_muscles.gen_tendons_and_muscles(registry)
    organs = anatomy.gen_organs(registry, sex)
    vessels = anatomy.gen_vascular(registry)
    ligaments = anatomy.gen_ligaments(registry)
    cartilage = anatomy.gen_cartilage(registry)
    segments = body.gen_segments(registry, weight, sex)
    current_pose = body.gen_current_pose(registry)
    saved_poses = body.gen_saved_poses(registry)
    loading = body.gen_loading_conditions(registry, weight)

    return {
        "registry": registry,
        "proportions": proportions,
        "weight": weight,
        "height": height,
        "skeleton": skel,
        "joints": joints,
        "nerves": nerves,
        "tendons": tendons,
        "muscles": muscles,
        "organs": organs,
        "vessels": vessels,
        "ligaments": ligaments,
        "cartilage": cartilage,
        "segments": segments,
        "current_pose": current_pose,
        "saved_poses": saved_poses,
        "loading": loading,
    }


def test_shared_math_helpers_and_proportions_cycle():
    assert isinstance(shared.uid(), str)
    assert shared.vec3(1.2345678, 2, 3)["x"] == 1.234568
    assert shared.unit_vec3(0, 0, 0) == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert shared.unit_vec3(0, 2, 0) == {"x": 0.0, "y": 1.0, "z": 0.0}
    assert shared.identity_quat() == {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}
    quat = shared.small_tilt_quat(10, 20, 30)
    assert set(quat) == {"w", "x", "y", "z"}
    assert shared.rigid_pose(1, 2, 3)["position"]["z"] == 3
    assert shared.tf(1, 2, 3, 4, 5, 6)["rotation"]["y"] == 5
    assert shared.color(1, 2, 3, 0.5)["a"] == 0.5
    assert shared.sym_tensor(1, 2, 3)["zz"] == 3
    assert shared.material(foo="bar") == {"foo": "bar"}

    random.seed(7)
    sexes = [shared.gen_proportions(i)["biologicalSex"] for i in range(3)]
    assert sexes == shared.SEX_OPTIONS


def test_skeleton_joint_and_biomechanics_generation():
    random.seed(11)
    data = _build_registry(seed=11, sex="male")
    registry = data["registry"]

    assert len(skeleton.BONE_DEFS) == 206
    assert len(data["skeleton"]) == 206
    assert data["skeleton"][shared.B_FRONTAL]["parentBoneId"] == registry.bone_ids[shared.B_C1]
    assert len(joints_data.JOINT_DEFS) == 72
    assert len(data["joints"]) > len(joints_data.JOINT_DEFS)
    assert any(j["name"] == "CMC thumb (R)" for j in data["joints"])
    assert any(j["name"] == "MTP Hallux (L)" for j in data["joints"])

    origin_tendon = joints_muscles._make_tendon(registry, "Achilles origin tendon", shared.B_TIB_R, 12.0, 1.2)
    insertion_tendon = joints_muscles._make_tendon(registry, "Test insertion tendon", shared.B_TIB_R, 10.0)
    assert origin_tendon["crossSectionalArea"] == 1.2
    assert origin_tendon["localPosition"]["y"] > 0
    assert insertion_tendon["localPosition"]["y"] < 0

    bilateral = joints_muscles._bilateral([
        ("Custom", "arm", "parallel", shared.B_HUMER_R, shared.B_RAD_R, ["flexion"], None, ["C5"], "Nerve", "Artery", 10, 1, 1, 1, None, (1, 0, 0), ["Other"], ["Friend"], None, None, None, None),
        ("Rectus Abdominis", "abdomen", "parallel", shared.B_STERNUM, shared.B_HIP_R, ["flexion"], None, ["T7"], "Nerve", "Artery", 10, 1, 1, 1, None, (0, 1, 0), [], [], None, None, None, None),
    ])
    assert any(item[0] == "Custom (R)" for item in bilateral)
    assert any(item[0] == "Custom (L)" for item in bilateral)
    assert any(item[0] == "Rectus Abdominis" for item in bilateral)

    assert joints_muscles._mirror_bone(shared.B_HIP_R) == shared.B_HIP_L
    assert joints_muscles._mirror_bone(shared.B_RIB_R[0]) == shared.B_RIB_L[0]
    assert joints_muscles._mirror_bone(shared.B_HAND_R_SCAPHOID) == shared.B_HAND_L_START
    assert joints_muscles._mirror_bone(shared.B_FOOT_R_CALCANEUS) == shared.B_FOOT_L_START
    assert joints_muscles._mirror_bone(shared.B_STERNUM) == shared.B_STERNUM

    assert len(data["tendons"]) == (2 * len(data["muscles"])) - len(joints_muscles.SHARED_ORIGIN_BASES)
    assert any("extensions" in m for m in data["muscles"])
    assert any("nerveId" in m["innervation"] for m in data["muscles"])


def test_anatomy_and_body_generators_cover_variants():
    male = _build_registry(seed=21, sex="male")
    female = _build_registry(seed=21, sex="female")
    other = _build_registry(seed=21, sex="intersex")

    assert any(o["name"] == "Prostate" for o in male["organs"])
    assert any(o["name"] == "Uterus" for o in female["organs"])
    assert not any(o["system"] == "reproductive" for o in other["organs"])

    nerves = male["nerves"]
    sciatic = next(n for n in nerves if n["name"] == "Sciatic nerve")
    tibial = next(n for n in nerves if n["name"] == "Tibial nerve")
    assert tibial["parentNerveId"] == sciatic["id"]

    assert any(v["vesselType"] == "artery" for v in male["vessels"])
    assert any(v["vesselType"] == "vein" for v in male["vessels"])

    female_pelvis = next(s for s in female["segments"] if s["name"] == "Pelvis")
    male_pelvis = next(s for s in male["segments"] if s["name"] == "Pelvis")
    assert female_pelvis["mass"] != male_pelvis["mass"]

    assert len(male["saved_poses"]) == 6
    assert len(male["current_pose"]["jointStates"]) == len(male["registry"].joint_ids)
    assert len(male["loading"]) == 7
    assert any(c["name"] == "carrying_external_load" for c in male["loading"])
    assert any(not c["equilibrium"]["isStatic"] or c["equilibrium"]["residualForceMagnitude"] >= 0 for c in male["loading"])

    refs = body._gen_reference_frames(male["registry"])
    fbds = body._gen_free_body_diagrams(male["registry"], male["loading"], male["weight"])
    motion = body._gen_motion_sequences(male["registry"])
    rendering = body._gen_rendering_layer(male["registry"])
    clothing = body._gen_clothing(male["height"])

    assert len(refs) == len(body.SEG_DEFS) + 1
    assert len(fbds) == len(body.SEG_DEFS)
    assert body._gen_free_body_diagrams(male["registry"], [], male["weight"]) == []
    assert motion[0]["name"] == "normal_gait_cycle"
    assert rendering["globalOpacity"] == 1.0
    assert len(clothing) == 3
    assert body.gen_derivation_graph()["version"] == "1.0.0"
    assert body.gen_constitutive_laws()["version"] == "1.0.0"
