from .anatomy import *
from .body import *
from .geometry import *
from .joints_data import *
from .joints_muscles import *
from .nerves_data import *
from .shared import *
from .skeleton import *


# ---------------------------------------------------------------------------
# Component definitions for selective generation
# ---------------------------------------------------------------------------

# Each component maps to one or more output keys and declares which other
# components must be *generated* (for registry population) before it.
# "skeleton" is always generated — it populates bone_ids which everything needs.

COMPONENTS: dict[str, dict] = {
    "skeleton":      {"keys": ["skeleton"]},
    "joints":        {"keys": ["joints"]},
    "nerves":        {"keys": ["nerves"]},
    "muscles":       {"keys": ["tendons", "muscles"],       "deps": ["joints", "nerves"]},
    "organs":        {"keys": ["organs"]},
    "vascular":      {"keys": ["vascularSystem"]},
    "ligaments":     {"keys": ["ligaments"]},
    "cartilage":     {"keys": ["cartilage"]},
    "segments":      {"keys": ["segments"]},
    "poses":         {"keys": ["currentPose", "savedPoses"], "deps": ["joints"]},
    "loading":       {"keys": ["loadingConditions", "freeBodyDiagrams", "referenceFrames"],
                      "deps": ["joints"]},
    "motion":        {"keys": ["motionSequences"],           "deps": ["joints"]},
    "geometry":      {"keys": ["boneGeometries"]},
    "appearance":    {"keys": ["rendering", "clothing", "hair"], "deps": ["joints"]},
    "metadata":      {"keys": ["derivationGraph", "constitutiveLaws"]},
}

ALL_COMPONENTS = frozenset(COMPONENTS)


def _resolve_components(
    include: set[str] | None = None,
    exclude: set[str] | None = None,
) -> set[str]:
    """Resolve the set of components to include in the output.

    Returns the component names that should appear in the final dict.
    Dependencies are generated for registry purposes but only requested
    components appear in the output.
    """
    if include is not None:
        unknown = include - ALL_COMPONENTS
        if unknown:
            raise ValueError(f"Unknown components: {', '.join(sorted(unknown))}. "
                             f"Valid: {', '.join(sorted(ALL_COMPONENTS))}")
        selected = include
    elif exclude is not None:
        unknown = exclude - ALL_COMPONENTS
        if unknown:
            raise ValueError(f"Unknown components: {', '.join(sorted(unknown))}. "
                             f"Valid: {', '.join(sorted(ALL_COMPONENTS))}")
        selected = ALL_COMPONENTS - exclude
    else:
        selected = set(ALL_COMPONENTS)
    return selected


def _generation_order(selected: set[str]) -> list[str]:
    """Return components to generate, in dependency order.

    Includes transitive deps needed for registry population even if
    the dep itself isn't in the selected output set.
    """
    to_generate: set[str] = set()

    def _add(name: str) -> None:
        if name in to_generate:
            return
        to_generate.add(name)
        for dep in COMPONENTS[name].get("deps", []):
            _add(dep)

    for name in selected:
        _add(name)

    # Stable generation order: skeleton first, then alphabetical
    order = sorted(to_generate - {"skeleton"})
    return ["skeleton"] + order


def generate_human_body(
    variation: int = 0,
    bone_geometry_format: str = "indexed_mesh",
    include: set[str] | None = None,
    exclude: set[str] | None = None,
) -> dict:
    selected = _resolve_components(include, exclude)
    gen_set = set(_generation_order(selected))

    r = Reg()
    proportions = gen_proportions(variation)
    weight = proportions["weight"]
    height = proportions["totalHeight"]
    sex = proportions.get("biologicalSex", "male")

    # --- Always generate skeleton (populates bone_ids) ---
    skel = gen_skeleton(r, weight, height)

    # --- Registry-populating generators (cheap, run if needed by deps) ---
    joint_list = gen_joints(r) if "joints" in gen_set else []
    nerve_list = gen_nerves(r) if "nerves" in gen_set else []

    if "muscles" in gen_set:
        tendon_list, muscle_list = gen_tendons_and_muscles(r)
    else:
        tendon_list, muscle_list = [], []

    organ_list = gen_organs(r, sex) if "organs" in gen_set else []
    vascular_list = gen_vascular(r) if "vascular" in gen_set else []

    # Wire muscle → vascular IDs when both are present
    if "muscles" in selected and "vascular" in selected and muscle_list and vascular_list:
        vessel_name_to_id: dict[str, str] = {}
        for vessel in vascular_list:
            vessel_name_to_id[vessel["name"]] = vessel["id"]

        vessel_base_to_id: dict[str, str] = {}
        for vessel in vascular_list:
            base = vessel["name"].replace(" (R)", "").replace(" (L)", "")
            if base not in vessel_base_to_id:
                vessel_base_to_id[base] = vessel["id"]

        for muscle in muscle_list:
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

    ligament_list = gen_ligaments(r) if "ligaments" in gen_set else []
    cartilage_list = gen_cartilage(r) if "cartilage" in gen_set else []
    segment_list = gen_segments(r, weight, sex) if "segments" in gen_set else []

    if "poses" in gen_set:
        current_pose = gen_current_pose(r)
        saved_poses = gen_saved_poses(r)
    else:
        current_pose, saved_poses = {}, []

    loading = gen_loading_conditions(r, weight) if "loading" in gen_set else []
    ref_frames = _gen_reference_frames(r) if "loading" in gen_set else []
    fbds = _gen_free_body_diagrams(r, loading, weight) if "loading" in gen_set else []
    motion_seqs = _gen_motion_sequences(r) if "motion" in gen_set else []

    if "appearance" in gen_set:
        rendering = _gen_rendering_layer(r)
        clothing = _gen_clothing(height)
        hair = gen_hair(height)
    else:
        rendering, clothing, hair = {}, [], {}

    bone_geometries = (gen_bone_geometries(r, geometry_format=bone_geometry_format)
                       if "geometry" in gen_set else [])

    # --- Build output dict with only selected components ---
    output_keys = set()
    for name in selected:
        output_keys.update(COMPONENTS[name]["keys"])

    full = {
        "schemaVersion": SCHEMA_VERSION,
        "id": uid(),
        "name": f"generated_body_{variation:03d}",
        "proportions": proportions,
        "skeleton": skel,
        "joints": joint_list,
        "tendons": tendon_list,
        "muscles": muscle_list,
        "organs": organ_list,
        "vascularSystem": vascular_list,
        "ligaments": ligament_list,
        "cartilage": cartilage_list,
        "nerves": nerve_list,
        "hair": hair,
        "clothing": clothing,
        "segments": segment_list,
        "currentPose": current_pose,
        "savedPoses": saved_poses,
        "loadingConditions": loading,
        "derivationGraph": gen_derivation_graph() if "metadata" in selected else {},
        "constitutiveLaws": gen_constitutive_laws() if "metadata" in selected else {},
        "referenceFrames": ref_frames,
        "freeBodyDiagrams": fbds,
        "motionSequences": motion_seqs,
        "rendering": rendering,
        "boneGeometries": bone_geometries,
    }

    # Always include envelope keys; filter component data
    result = {"schemaVersion": full["schemaVersion"], "id": full["id"],
              "name": full["name"], "proportions": full["proportions"]}
    for key, value in full.items():
        if key in result:
            continue
        if key in output_keys:
            result[key] = value

    return result


def main() -> None:
    component_names = sorted(ALL_COMPONENTS)
    parser = argparse.ArgumentParser(
        description="Generate valid HumanBody v3.0.0 JSON (206 bones)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"available components:\n  {', '.join(component_names)}",
    )
    parser.add_argument("-n", "--count", type=int, default=1)
    parser.add_argument("-o", "--output-dir", type=str, default=None)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--bone-geometry-format", choices=["indexed_mesh", "parametric_csg"], default="indexed_mesh")
    parser.add_argument("--include", nargs="+", metavar="COMPONENT",
                        help=f"only generate these components (choices: {', '.join(component_names)})")
    parser.add_argument("--exclude", nargs="+", metavar="COMPONENT",
                        help=f"generate everything except these (choices: {', '.join(component_names)})")
    args = parser.parse_args()

    if args.include and args.exclude:
        parser.error("--include and --exclude are mutually exclusive")

    if args.seed is not None:
        random.seed(args.seed)

    inc = set(args.include) if args.include else None
    exc = set(args.exclude) if args.exclude else None

    indent = 2 if args.pretty else None
    bodies = [generate_human_body(i, bone_geometry_format=args.bone_geometry_format,
                                  include=inc, exclude=exc)
              for i in range(args.count)]
    if args.output_dir:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for i, body in enumerate(bodies):
            (out / f"body_{i:03d}.json").write_text(json.dumps(body, indent=indent, ensure_ascii=False) + "\n")
        print(f"Wrote {len(bodies)} file(s) to {out}/", file=sys.stderr)
        return

    print(json.dumps(bodies[0] if len(bodies) == 1 else bodies, indent=indent, ensure_ascii=False))
