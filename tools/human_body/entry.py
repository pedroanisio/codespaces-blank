from .anatomy import *
from .body import *
from .geometry import *
from .joints_data import *
from .joints_muscles import *
from .nerves_data import *
from .shared import *
from .skeleton import *


def generate_human_body(variation: int = 0, bone_geometry_format: str = "indexed_mesh") -> dict:
    r = Reg()
    proportions = gen_proportions(variation)
    weight = proportions["weight"]
    height = proportions["totalHeight"]
    sex = proportions.get("biologicalSex", "male")

    skeleton = gen_skeleton(r, weight, height)
    joints = gen_joints(r)
    nerves = gen_nerves(r)
    tendons, muscles = gen_tendons_and_muscles(r)
    organs = gen_organs(r, sex)
    vascular = gen_vascular(r)

    vessel_name_to_id: dict[str, str] = {}
    for vessel in vascular:
        vessel_name_to_id[vessel["name"]] = vessel["id"]

    vessel_base_to_id: dict[str, str] = {}
    for vessel in vascular:
        base = vessel["name"].replace(" (R)", "").replace(" (L)", "")
        if base not in vessel_base_to_id:
            vessel_base_to_id[base] = vessel["id"]

    for muscle in muscles:
        artery_name = muscle["bloodSupply"]["primaryArteryName"]
        vessel_id = vessel_name_to_id.get(artery_name)
        if not vessel_id:
            side = "(R)" if "(R)" in muscle["name"] else ("(L)" if "(L)" in muscle["name"] else "")
            if side:
                vessel_id = vessel_name_to_id.get(f"{artery_name} {side}")
        if not vessel_id:
            vessel_id = vessel_base_to_id.get(artery_name)
        if vessel_id:
            muscle["bloodSupply"]["primaryArteryId"] = vessel_id

    ligaments = gen_ligaments(r)
    cartilage = gen_cartilage(r)
    segments = gen_segments(r, weight, sex)
    current_pose = gen_current_pose(r)
    saved_poses = gen_saved_poses(r)
    loading = gen_loading_conditions(r, weight)
    ref_frames = _gen_reference_frames(r)
    fbds = _gen_free_body_diagrams(r, loading, weight)
    motion_seqs = _gen_motion_sequences(r)
    rendering = _gen_rendering_layer(r)
    clothing = _gen_clothing(height)
    bone_geometries = gen_bone_geometries(r, geometry_format=bone_geometry_format)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "id": uid(),
        "name": f"generated_body_{variation:03d}",
        "proportions": proportions,
        "skeleton": skeleton,
        "joints": joints,
        "tendons": tendons,
        "muscles": muscles,
        "organs": organs,
        "vascularSystem": vascular,
        "ligaments": ligaments,
        "cartilage": cartilage,
        "nerves": nerves,
        "hair": gen_hair(height),
        "clothing": clothing,
        "segments": segments,
        "currentPose": current_pose,
        "savedPoses": saved_poses,
        "loadingConditions": loading,
        "derivationGraph": gen_derivation_graph(),
        "constitutiveLaws": gen_constitutive_laws(),
        "referenceFrames": ref_frames,
        "freeBodyDiagrams": fbds,
        "motionSequences": motion_seqs,
        "rendering": rendering,
        "boneGeometries": bone_geometries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate valid HumanBody v3.0.0 JSON (206 bones)")
    parser.add_argument("-n", "--count", type=int, default=1)
    parser.add_argument("-o", "--output-dir", type=str, default=None)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--bone-geometry-format", choices=["indexed_mesh", "parametric_csg"], default="indexed_mesh")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    indent = 2 if args.pretty else None
    bodies = [generate_human_body(i, bone_geometry_format=args.bone_geometry_format) for i in range(args.count)]
    if args.output_dir:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for i, body in enumerate(bodies):
            (out / f"body_{i:03d}.json").write_text(json.dumps(body, indent=indent, ensure_ascii=False) + "\n")
        print(f"Wrote {len(bodies)} file(s) to {out}/", file=sys.stderr)
        return

    print(json.dumps(bodies[0] if len(bodies) == 1 else bodies, indent=indent, ensure_ascii=False))
