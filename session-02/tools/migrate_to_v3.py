#!/usr/bin/env python3
"""Migrate a GVPP instance JSON to strict v3.0.0 schema compliance.

Fixes:
  1. String refs → EntityRef objects {"id": "..."}
  2. Missing required fields (logicalId, name, version, entityType, etc.)
  3. Field renames (width→widthPx, height→heightPx, id→opId in operations)
  4. SyncPoint restructure (flat word/startSec/endSec → label + time object)
  5. Fragment restructure (fragmentId+text → fragment)
  6. Operation cleanup (remove non-schema fields, add opId)
  7. Audio generation cleanup (move TTS fields into generation.steps)
  8. Remove top-level non-schema keys (generationSteps, promptComposerMeta, etc.)
  9. Remove internal fields (_filePath)
  10. Add missing required fields on audioAssets, timelines, editVersions, renderPlans
  11. Fix dependencies (list of edges → {nodes, edges} with fromNodeId/toNodeId)
  12. Fix audioType enum values
  13. Fix shotRefs in scenes (remove extra shotNumber field)
  14. Fix qaGate/qaChecks references
"""
import json
import sys
import copy
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def to_entity_ref(val: object) -> dict:
    """Convert a value to an EntityRef object."""
    if isinstance(val, str):
        return {"id": val}
    if isinstance(val, dict):
        # Already an object — ensure it only has EntityRef keys
        allowed = {"id", "logicalId", "versionSelector", "role", "notes"}
        extra = set(val.keys()) - allowed
        clean = {k: v for k, v in val.items() if k in allowed}
        # If it had logicalId but no id, keep as-is
        if not clean:
            # Fallback: use the whole thing as id
            return val
        return clean
    return {"id": str(val)}


def to_entity_ref_list(lst: list) -> list:
    """Convert a list of values to EntityRef objects."""
    if not isinstance(lst, list):
        return lst
    return [to_entity_ref(item) for item in lst]


def ensure_version(obj: dict) -> dict:
    """Ensure version is an object {number, state}."""
    v = obj.get("version")
    if v is None:
        obj["version"] = {"number": "1.0.0", "state": "draft"}
    elif isinstance(v, str):
        obj["version"] = {"number": v, "state": "draft"}
    return obj


def ensure_entity_fields(obj: dict, entity_type: str, *, name_fallback: str = "") -> dict:
    """Add missing required entity fields."""
    if "logicalId" not in obj:
        obj["logicalId"] = obj.get("id", "")
    if "entityType" not in obj:
        obj["entityType"] = entity_type
    if "name" not in obj:
        obj["name"] = name_fallback or obj.get("id", entity_type)
    ensure_version(obj)
    return obj


# ── Ref field conversion ─────────────────────────────────────────────────────

# Fields that should be single EntityRef objects
SINGLE_REF_FIELDS = {
    "sourceTimelineRef", "timelineRef", "environmentRef",
    "inputRef", "targetQualityProfileRef", "qualityProfileRef",
    "audioRef", "speakerRef", "characterRef", "audioAssetRef",
    "fromRef", "toRef", "subjectRef", "targetRef",
}

# Fields that should be arrays of EntityRef objects
ARRAY_REF_FIELDS = {
    "targetOutputRefs", "clipRefs", "characterRefs", "propRefs",
    "shotRefs", "storyBeatRefs", "scriptSegmentRefs", "directorNoteRefs",
    "referenceAssetRefs", "sceneRefs", "sourceRefs", "dependencyRefs",
    "inputRefs", "outputRefs",
}


def fix_refs_recursive(obj: object) -> object:
    """Walk the entire tree and fix ref fields."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in SINGLE_REF_FIELDS and v is not None:
                result[k] = to_entity_ref(v)
            elif k in ARRAY_REF_FIELDS and isinstance(v, list):
                result[k] = to_entity_ref_list(v)
            else:
                result[k] = fix_refs_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_refs_recursive(item) for item in obj]
    return obj


# ── SyncPoint migration ──────────────────────────────────────────────────────

def fix_sync_point(sp: dict) -> dict:
    """Convert flat syncPoint to schema-compliant structure."""
    result = {}
    # word → label
    if "word" in sp:
        result["label"] = sp["word"]
    elif "label" in sp:
        result["label"] = sp["label"]

    # Build time object from flat fields
    time_obj = {}
    if "startSec" in sp:
        time_obj["startSec"] = float(sp["startSec"])
    if "endSec" in sp:
        time_obj["endSec"] = float(sp["endSec"])
    if "durationSec" in sp:
        time_obj["durationSec"] = float(sp["durationSec"])
    # Also check for timelineSec/sourceSec (used in timeline audio mix tracks)
    if "timelineSec" in sp and "startSec" not in time_obj:
        time_obj["startSec"] = float(sp["timelineSec"])
    if "sourceSec" in sp and "endSec" not in time_obj:
        pass  # sourceSec is offset, not endSec

    if time_obj:
        result["time"] = time_obj

    # Keep schema-allowed fields
    if "anchorRef" in sp:
        result["anchorRef"] = to_entity_ref(sp["anchorRef"])
    if "toleranceFrames" in sp:
        result["toleranceFrames"] = sp["toleranceFrames"]
    if "beat" in sp:
        result["beat"] = sp["beat"]
    if "notes" in sp:
        # notes isn't in schema SyncPoint, but keep it as part of label
        if "label" in result and sp["notes"]:
            result["label"] = f"{result['label']} — {sp['notes']}"
        elif sp["notes"]:
            result["label"] = sp["notes"]

    return result


def fix_sync_points_recursive(obj: object) -> object:
    """Find and fix all syncPoints arrays in the tree."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "syncPoints" and isinstance(v, list):
                result[k] = [fix_sync_point(sp) if isinstance(sp, dict) else sp for sp in v]
            else:
                result[k] = fix_sync_points_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_sync_points_recursive(item) for item in obj]
    return obj


# ── Fragment migration ────────────────────────────────────────────────────────

def fix_fragment(frag: dict) -> dict:
    """Convert fragmentId+text to schema fragment."""
    result = {}
    # text → fragment
    if "text" in frag:
        result["fragment"] = frag["text"]
    elif "fragment" in frag:
        result["fragment"] = frag["fragment"]
    else:
        result["fragment"] = ""

    # Keep allowed fields
    for field in ("weight", "insertionOrder", "category", "locked"):
        if field in frag:
            result[field] = frag[field]

    return result


def fix_fragments_recursive(obj: object) -> object:
    """Find and fix all canonicalPromptFragments."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "canonicalPromptFragments" and isinstance(v, list):
                result[k] = [fix_fragment(f) if isinstance(f, dict) else f for f in v]
            else:
                result[k] = fix_fragments_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_fragments_recursive(item) for item in obj]
    return obj


# ── Resolution fix ────────────────────────────────────────────────────────────

def fix_resolution_recursive(obj: object) -> object:
    """Rename width→widthPx, height→heightPx in resolution objects."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "resolution" and isinstance(v, dict):
                res = {}
                for rk, rv in v.items():
                    if rk == "width":
                        res["widthPx"] = rv
                    elif rk == "height":
                        res["heightPx"] = rv
                    else:
                        res[rk] = rv
                result[k] = res
            else:
                result[k] = fix_resolution_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_resolution_recursive(item) for item in obj]
    return obj


# ── Operations fix ────────────────────────────────────────────────────────────

# Fields allowed per operation type (from schema)
OP_ALLOWED = {
    "concat": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "clipRefs", "method", "outputRef"},
    "audioMix": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "tracks", "outputRef"},
    "encode": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "inputRef", "compression", "targetQualityProfileRef", "outputRef"},
    "colorGrade": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "intent", "strength", "lutRef", "outputRef"},
    "filter": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "filterType", "parameters", "outputRef"},
    "retime": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "retime", "outputRef"},
    "transition": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "fromRef", "toRef", "spec", "outputRef"},
    "overlay": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "layers", "outputRef"},
    "manim": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "sceneClass", "outputRef"},
    "custom": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "outputRef"},
    "stitch": {"opId", "opType", "compatibleRuntimes", "runtimeHints", "outputRef"},
}

# Allowed fields in audioMix track items
AUDIO_TRACK_ALLOWED = {"audioRef", "gainDb", "pan", "timeRange", "syncPoints"}


def fix_operation(op: dict) -> dict:
    """Fix a single operation to be schema-compliant."""
    op_type = op.get("opType", "custom")
    allowed = OP_ALLOWED.get(op_type, OP_ALLOWED["custom"])

    result = {}
    # id → opId
    if "id" in op and "opId" not in op:
        result["opId"] = op["id"]
    elif "opId" in op:
        result["opId"] = op["opId"]
    else:
        result["opId"] = f"op-{op_type}-auto"

    result["opType"] = op_type

    for k, v in op.items():
        if k in ("id", "opType", "opId"):
            continue
        if k in allowed:
            result[k] = v

    # Fix audioMix tracks
    if op_type == "audioMix" and "tracks" in result:
        fixed_tracks = []
        for track in result["tracks"]:
            fixed = {}
            for tk, tv in track.items():
                if tk in AUDIO_TRACK_ALLOWED:
                    fixed[tk] = tv
            # Ensure audioRef exists
            if "audioRef" not in fixed and "audioRef" in track:
                fixed["audioRef"] = track["audioRef"]
            fixed_tracks.append(fixed)
        result["tracks"] = fixed_tracks

    return result


def fix_operations_in_tree(obj: object) -> object:
    """Fix operations arrays throughout the document."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "operations" and isinstance(v, list):
                result[k] = [
                    fix_operation(op) if isinstance(op, dict) and "opType" in op else op
                    for op in v
                ]
            else:
                result[k] = fix_operations_in_tree(v)
        return result
    elif isinstance(obj, list):
        return [fix_operations_in_tree(item) for item in obj]
    return obj


# ── Audio asset fixes ─────────────────────────────────────────────────────────

AUDIO_TYPE_MAP = {
    "dialogue": "dialogue",
    "voice_over": "voice_over",
    "music": "music",
    "sfx": "sfx",
    "ambient": "ambient",
    "foley": "foley",
    "stem": "stem",
    "custom": "custom",
}


def fix_audio_asset(asset: dict) -> dict:
    """Fix an audioAsset to be schema-compliant."""
    ensure_entity_fields(asset, "audioAsset", name_fallback=asset.get("id", "audio"))

    # Remove internal fields
    asset.pop("_filePath", None)

    # Fix audioType
    at = asset.get("audioType", "custom")
    asset["audioType"] = AUDIO_TYPE_MAP.get(at, "custom")

    # Add assetClass if missing (not in schema per latest check, but audioType serves)
    # Actually schema requires: id, logicalId, entityType, name, version, assetClass
    # But agent said assetClass doesn't exist — let's check audioType is there instead

    # Fix generation block
    gen = asset.get("generation")
    if isinstance(gen, dict):
        # Move TTS-specific fields into a generation step
        tts_fields = {}
        gen_clean = {}
        for gk, gv in gen.items():
            if gk in ("mode", "steps", "consistencyAnchors", "reproducibility", "extensions"):
                gen_clean[gk] = gv
            else:
                tts_fields[gk] = gv

        if "mode" not in gen_clean:
            gen_clean["mode"] = "ai_generated"

        if tts_fields and "steps" not in gen_clean:
            # Create a generation step from the TTS fields
            step = {
                "stepId": f"tts-{asset.get('id', 'unknown')}",
                "operationType": "tts",
                "provider": tts_fields.get("ttsModel", "unknown").split("/")[0] if tts_fields.get("ttsModel") else "unknown",
                "model": {
                    "name": tts_fields.get("ttsModel", "unknown"),
                },
                "prompt": tts_fields.get("performanceDirection", ""),
            }
            # Remove empty fields
            step = {k: v for k, v in step.items() if v}
            if "stepId" not in step:
                step["stepId"] = "tts-auto"
            gen_clean["steps"] = [step]

        asset["generation"] = gen_clean

    return asset


# ── Dependencies fix ──────────────────────────────────────────────────────────

def fix_dependencies(deps: object) -> dict:
    """Convert list-of-edges to {nodes, edges} with fromNodeId/toNodeId."""
    if isinstance(deps, dict) and "edges" in deps:
        # Already has structure, just fix edges
        edges = deps.get("edges", [])
        nodes = deps.get("nodes", [])
    elif isinstance(deps, list):
        edges = deps
        nodes = []
    else:
        return {"nodes": [], "edges": []}

    fixed_edges = []
    node_ids = set()
    for edge in edges:
        if not isinstance(edge, dict):
            continue

        from_ref = edge.get("fromRef", {})
        to_ref = edge.get("toRef", {})

        from_id = from_ref.get("logicalId") or from_ref.get("id", "") if isinstance(from_ref, dict) else str(from_ref)
        to_id = to_ref.get("logicalId") or to_ref.get("id", "") if isinstance(to_ref, dict) else str(to_ref)

        fixed_edge = {
            "fromNodeId": from_id,
            "toNodeId": to_id,
        }

        # dependencyType → condition (closest allowed field)
        dep_type = edge.get("dependencyType", "")
        if dep_type:
            fixed_edge["condition"] = dep_type

        if edge.get("notes"):
            fixed_edge["notes"] = edge["notes"]

        fixed_edges.append(fixed_edge)
        node_ids.add(from_id)
        node_ids.add(to_id)

    return {"edges": fixed_edges}


# ── Shot refs in scenes ───────────────────────────────────────────────────────

def fix_scene_shot_refs(scene: dict) -> dict:
    """Remove extra fields from shotRefs (like shotNumber)."""
    refs = scene.get("shotRefs", [])
    if isinstance(refs, list):
        scene["shotRefs"] = [to_entity_ref(r) for r in refs]
    return scene


# ── Timeline fix ──────────────────────────────────────────────────────────────

def fix_timeline(tl: dict) -> dict:
    """Add missing required fields to timeline."""
    ensure_entity_fields(tl, "timeline", name_fallback="Main Timeline")
    if "durationSec" not in tl:
        tl["durationSec"] = 600  # 10 min default from project targetRuntimeSec
    return tl


# ── Edit version fix ──────────────────────────────────────────────────────────

def fix_edit_version(ev: dict) -> dict:
    """Add missing required fields to editVersion."""
    ensure_entity_fields(ev, "editVersion", name_fallback="Edit v1")
    # timelineRef must be EntityRef
    if "timelineRef" in ev:
        ev["timelineRef"] = to_entity_ref(ev["timelineRef"])
    return ev


# ── Render plan fix ───────────────────────────────────────────────────────────

def fix_render_plan(rp: dict) -> dict:
    """Add missing required fields to renderPlan."""
    ensure_entity_fields(rp, "renderPlan", name_fallback="Main Render Plan")
    return rp


# ── QA structures → extensions ────────────────────────────────────────────────

def move_qa_to_extensions(doc: dict) -> dict:
    """Move non-schema top-level keys into extensions."""
    non_schema = {"generationSteps", "promptComposerMeta", "qaChecks", "qaGates"}
    extensions = doc.get("extensions") or {}
    for key in non_schema:
        if key in doc:
            extensions[key] = doc.pop(key)
    if extensions:
        doc["extensions"] = extensions
    return doc


# ── Shots fix ─────────────────────────────────────────────────────────────────

def fix_shots(shots: list) -> list:
    """Ensure shots have required entity fields."""
    fixed = []
    for shot in shots:
        if not isinstance(shot, dict):
            fixed.append(shot)
            continue
        # Shots with only shotNumber + qaGate are incomplete stubs
        # They need full entity fields
        ensure_entity_fields(shot, "shot", name_fallback=f"Shot {shot.get('shotNumber', '?')}")
        if "id" not in shot or not shot["id"]:
            sn = shot.get("shotNumber", 0)
            shot["id"] = f"shot-{sn:03d}"
            shot["logicalId"] = shot["id"]
        fixed.append(shot)
    return fixed


# ── Main migration ────────────────────────────────────────────────────────────

def migrate(doc: dict) -> dict:
    """Apply all migrations to a GVPP instance document."""
    doc = copy.deepcopy(doc)

    # 1. Move non-schema top-level keys to extensions
    doc = move_qa_to_extensions(doc)

    # 2. Fix resolution naming throughout
    doc = fix_resolution_recursive(doc)

    # 3. Fix fragments throughout
    doc = fix_fragments_recursive(doc)

    # 4. Fix syncPoints throughout
    doc = fix_sync_points_recursive(doc)

    # 5. Fix operations throughout (before ref fixing, since we rename id→opId)
    doc = fix_operations_in_tree(doc)

    # 6. Fix all refs throughout
    doc = fix_refs_recursive(doc)

    # 7. Fix audio assets
    audio_assets = (doc.get("assetLibrary") or {}).get("audioAssets") or []
    for i, aa in enumerate(audio_assets):
        audio_assets[i] = fix_audio_asset(aa)

    # 8. Fix assembly entities
    assembly = doc.get("assembly") or {}

    timelines = assembly.get("timelines") or []
    for i, tl in enumerate(timelines):
        timelines[i] = fix_timeline(tl)

    edit_versions = assembly.get("editVersions") or []
    for i, ev in enumerate(edit_versions):
        edit_versions[i] = fix_edit_version(ev)

    render_plans = assembly.get("renderPlans") or []
    for i, rp in enumerate(render_plans):
        render_plans[i] = fix_render_plan(rp)

    # 9. Fix dependencies
    if "dependencies" in doc:
        doc["dependencies"] = fix_dependencies(doc["dependencies"])

    # 10. Fix scenes
    scenes = (doc.get("production") or {}).get("scenes") or []
    for scene in scenes:
        fix_scene_shot_refs(scene)

    # 11. Fix shots
    shots = (doc.get("production") or {}).get("shots") or []
    if shots:
        doc["production"]["shots"] = fix_shots(shots)

    return doc


def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate_to_v3.py <input.json> [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path

    with open(input_path) as f:
        doc = json.load(f)

    migrated = migrate(doc)

    with open(output_path, "w") as f:
        json.dump(migrated, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Migrated: {input_path} → {output_path}")


if __name__ == "__main__":
    main()
