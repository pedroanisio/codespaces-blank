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
    "dubbedAudioRef", "adaptedMarketingRef", "storyRef",
    "assemblyPlanRef", "thumbnailSourceRef", "sourceEditRef",
    "renderPlanRef", "sceneRef", "shotRef",
    "startBeatRef", "endBeatRef",
}

# Fields that should be arrays of EntityRef objects
ARRAY_REF_FIELDS = {
    "targetOutputRefs", "clipRefs", "characterRefs", "propRefs",
    "shotRefs", "storyBeatRefs", "scriptSegmentRefs", "directorNoteRefs",
    "referenceAssetRefs", "sceneRefs", "sourceRefs", "dependencyRefs",
    "inputRefs", "outputRefs",
    "subtitleTrackRefs", "sourceSceneRefs", "sourceShotRefs", "sourceAssetRefs",
    "adapterRefs", "environmentRefs",
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

def fix_dependencies(deps: object) -> list:
    """Convert dependency list to schema-compliant array of relationship edges."""
    if isinstance(deps, dict) and "edges" in deps:
        edges = deps.get("edges", [])
    elif isinstance(deps, list):
        edges = deps
    else:
        return []

    valid_dep_types = {"requires", "blocks", "derives_from", "supersedes", "references", "syncs_with", "custom"}
    fixed_edges = []
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            continue

        from_ref = edge.get("fromRef", {})
        to_ref = edge.get("toRef", {})

        fixed_edge = {
            "edgeId": edge.get("edgeId") or f"dep-{i:03d}",
            "fromRef": to_entity_ref(from_ref) if from_ref else {"id": "unknown"},
            "toRef": to_entity_ref(to_ref) if to_ref else {"id": "unknown"},
            "dependencyType": edge.get("dependencyType", "requires"),
        }

        dep = fixed_edge["dependencyType"]
        if dep not in valid_dep_types:
            fixed_edge["dependencyType"] = "references"

        if edge.get("notes"):
            fixed_edge["notes"] = edge["notes"]

        fixed_edges.append(fixed_edge)

    return fixed_edges


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


# ── Fragment category fix ─────────────────────────────────────────────────────

CATEGORY_MAP = {
    "contextual": "custom",
    "end-state": "custom",
    "visual": "appearance",
    "character": "appearance",
    "setting": "environment",
    "tone": "mood",
    "lighting": "style",
    "camera": "style",
}
VALID_CATEGORIES = {"appearance", "style", "action", "environment", "mood", "constraint", "custom"}


def fix_fragment_categories(obj: object) -> object:
    """Fix non-enum category values in canonicalPromptFragments."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "canonicalPromptFragments" and isinstance(v, list):
                for frag in v:
                    if isinstance(frag, dict) and "category" in frag:
                        cat = frag["category"]
                        if cat not in VALID_CATEGORIES:
                            frag["category"] = CATEGORY_MAP.get(cat, "custom")
                result[k] = v
            else:
                result[k] = fix_fragment_categories(v)
        return result
    elif isinstance(obj, list):
        return [fix_fragment_categories(item) for item in obj]
    return obj


# ── QC Results fix ────────────────────────────────────────────────────────────

def fix_qc_result(qc: dict) -> dict:
    """Convert rule-template qcResult to schema-compliant check result."""
    result = {}
    # ruleId → metric
    result["metric"] = qc.get("ruleId") or qc.get("metric") or qc.get("name", "unknown")
    # status → pass
    status = qc.get("status", "")
    result["pass"] = status in ("pass", "passed", "success", "ok", True)
    # Keep allowed fields
    if "severity" in qc:
        sev = qc["severity"]
        result["severity"] = sev if sev in ("info", "warning", "error") else "info"
    if "notes" in qc:
        result["notes"] = qc["notes"]
    # measuredValue/targetValue → notes appendix
    extras = []
    if "measuredValue" in qc:
        extras.append(f"measured={qc['measuredValue']}")
    if "targetValue" in qc:
        extras.append(f"target={qc['targetValue']}")
    if extras:
        existing = result.get("notes", "")
        result["notes"] = f"{existing} ({', '.join(extras)})".strip()
    return result


def fix_qc_results_recursive(obj: object) -> object:
    """Fix qcResults arrays throughout."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "qcResults" and isinstance(v, list):
                result[k] = [fix_qc_result(qc) if isinstance(qc, dict) else qc for qc in v]
            else:
                result[k] = fix_qc_results_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_qc_results_recursive(item) for item in obj]
    return obj


# ── Platform deliveries fix ───────────────────────────────────────────────────

PLATFORM_DELIVERY_ALLOWED = {
    "platform", "format", "aspectRatio", "resolution", "frameRate",
    "maxDurationSec", "publishSchedule", "metadata",
}
VALID_PLATFORMS = {"youtube", "instagram", "tiktok", "vimeo", "broadcast", "theatrical", "streaming", "custom"}


def fix_platform_delivery(pd: dict) -> dict:
    """Fix a platformDelivery to match schema."""
    result = {}
    # Keep allowed fields
    platform = pd.get("platform", "custom")
    result["platform"] = platform if platform in VALID_PLATFORMS else "custom"

    if "format" in pd:
        result["format"] = pd["format"]

    # aspectRatio must be object {expression}
    ar = pd.get("aspectRatio")
    if isinstance(ar, str):
        result["aspectRatio"] = {"expression": ar}
    elif isinstance(ar, dict):
        result["aspectRatio"] = ar

    # resolution must be object {widthPx, heightPx}
    res = pd.get("resolution")
    if isinstance(res, dict):
        fixed_res = {}
        if "width" in res:
            fixed_res["widthPx"] = res["width"]
        if "height" in res:
            fixed_res["heightPx"] = res["height"]
        if "widthPx" in res:
            fixed_res["widthPx"] = res["widthPx"]
        if "heightPx" in res:
            fixed_res["heightPx"] = res["heightPx"]
        if fixed_res:
            result["resolution"] = fixed_res

    # frameRate must be object {fps}
    fr = pd.get("frameRate")
    if isinstance(fr, (int, float)):
        result["frameRate"] = {"fps": fr}
    elif isinstance(fr, dict):
        result["frameRate"] = fr

    if "maxDurationSec" in pd:
        result["maxDurationSec"] = pd["maxDurationSec"]

    # publishSchedule must have kind
    ps = pd.get("publishSchedule")
    if isinstance(ps, dict):
        if "kind" not in ps:
            ps["kind"] = "fixed"
        result["publishSchedule"] = ps

    # Move all technical spec fields into metadata
    tech_fields = {
        "codec", "profile", "bitrateMbps", "audioCodec", "audioSampleRateHz",
        "audioBitDepth", "audioChannelLayout", "loudnessIntegratedLUFS",
        "truePeakDbTP", "colorSpace", "dynamicRange", "containerNotes",
    }
    meta = {}
    for tk in tech_fields:
        if tk in pd:
            meta[tk] = str(pd[tk])
    # Also move non-schema schedule fields
    for sk in ("fuzzy", "month", "year", "notes"):
        if sk in pd and sk not in result:
            meta[f"schedule_{sk}"] = str(pd[sk])
    if meta:
        result["metadata"] = meta

    return result


def fix_platform_deliveries_recursive(obj: object) -> object:
    """Fix platformDeliveries arrays."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "platformDeliveries" and isinstance(v, list):
                result[k] = [fix_platform_delivery(pd) if isinstance(pd, dict) else pd for pd in v]
            else:
                result[k] = fix_platform_deliveries_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_platform_deliveries_recursive(item) for item in obj]
    return obj


# ── Localization targets fix ──────────────────────────────────────────────────

def fix_localization_targets_recursive(obj: object) -> object:
    """Ensure localizationTargets refs are objects, handle None values."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "localizationTargets" and isinstance(v, list):
                fixed = []
                for lt in v:
                    if isinstance(lt, dict):
                        # Fix null refs
                        if lt.get("dubbedAudioRef") is None:
                            lt.pop("dubbedAudioRef", None)
                        if lt.get("adaptedMarketingRef") is None:
                            lt.pop("adaptedMarketingRef", None)
                        fixed.append(lt)
                    else:
                        fixed.append(lt)
                result[k] = fixed
            else:
                result[k] = fix_localization_targets_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_localization_targets_recursive(item) for item in obj]
    return obj


# ── Visual asset generation fix ───────────────────────────────────────────────

GENERATION_STEP_ALLOWED = {
    "stepId", "operationType", "provider", "tool", "model",
    "executionEnvironment", "inputRefs", "outputRefs",
    "prompt", "negativePrompt", "systemPrompt", "structuredPrompt",
    "promptHistory", "seed", "guidanceScale", "inferenceSteps",
    "sampler", "scheduler", "strength", "cfg", "durationSec",
    "resolution", "aspectRatio", "frameRate", "referenceAssets",
    "consistencyAnchors", "adapterInputs", "voiceSettings",
    "cameraMotionHints", "parameters", "costEstimate",
}

# model allowed fields
MODEL_ALLOWED = {
    "provider", "tool", "modelId", "modelVersion", "checkpoint",
    "endpoint", "adapterRefs", "parameters",
}

PROMPT_HISTORY_ALLOWED = {
    "versionId", "prompt", "negativePrompt", "createdAt",
    "parentVersionId", "changeNote",
}

CONSISTENCY_ANCHOR_ALLOWED = {
    "anchorType", "name", "ref", "weight", "lockLevel", "attributes",
}

ANCHOR_TYPE_MAP = {
    "hard": "character",  # will be refined per-anchor
    "soft": "style",
}


def fix_consistency_anchor(anchor: dict) -> dict:
    """Fix a consistencyAnchor to be schema-compliant."""
    result = {}
    # Determine anchorType from context
    anchor_type = anchor.get("anchorType") or anchor.get("type", "custom")
    if anchor_type not in {"character", "style", "environment", "prop", "camera", "spatial", "custom"}:
        # Infer from sourceRef
        source = anchor.get("sourceRef", "")
        source_str = source if isinstance(source, str) else (source.get("id", "") if isinstance(source, dict) else "")
        if "char-" in source_str:
            anchor_type = "character"
        elif "env-" in source_str:
            anchor_type = "environment"
        elif "prop-" in source_str:
            anchor_type = "prop"
        else:
            anchor_type = "custom"
    result["anchorType"] = anchor_type

    if "name" in anchor:
        result["name"] = anchor["name"]

    # sourceRef → ref
    source_ref = anchor.get("sourceRef") or anchor.get("ref")
    if source_ref is not None:
        result["ref"] = to_entity_ref(source_ref)

    if "weight" in anchor:
        result["weight"] = anchor["weight"]

    lock = anchor.get("lockLevel") or anchor.get("type")
    if lock in ("soft", "medium", "hard"):
        result["lockLevel"] = lock

    if "attributes" in anchor:
        result["attributes"] = anchor["attributes"]

    return result


def fix_generation_step(step: dict) -> dict:
    """Fix a generation step to only have schema-allowed fields."""
    result = {}
    for k, v in step.items():
        if k in GENERATION_STEP_ALLOWED:
            if k == "model" and isinstance(v, dict):
                # Fix model to only have allowed fields
                fixed_model = {}
                if "name" in v:
                    fixed_model["modelId"] = v["name"]
                for mk in MODEL_ALLOWED:
                    if mk in v:
                        fixed_model[mk] = v[mk]
                result[k] = fixed_model
            elif k == "promptHistory" and isinstance(v, list):
                fixed_ph = []
                for ph in v:
                    if isinstance(ph, dict):
                        fixed = {}
                        if "version" in ph and "versionId" not in ph:
                            fixed["versionId"] = str(ph["version"])
                        for phk in PROMPT_HISTORY_ALLOWED:
                            if phk in ph:
                                fixed[phk] = ph[phk]
                        if "timestamp" in ph and "createdAt" not in fixed:
                            fixed["createdAt"] = ph["timestamp"]
                        fixed_ph.append(fixed)
                    else:
                        fixed_ph.append(ph)
                result[k] = fixed_ph
            elif k == "consistencyAnchors" and isinstance(v, list):
                result[k] = [fix_consistency_anchor(a) if isinstance(a, dict) else a for a in v]
            elif k == "aspectRatio" and isinstance(v, str):
                result[k] = {"expression": v}
            elif k == "frameRate" and isinstance(v, (int, float)):
                result[k] = {"fps": v}
            elif k == "cameraMotionHints" and isinstance(v, str):
                result[k] = {"description": v}
            else:
                result[k] = v
    # Ensure stepId
    if "stepId" not in result:
        result["stepId"] = "step-auto"
    return result


def fix_visual_asset_generation(obj: object) -> object:
    """Fix generation blocks on visual assets."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "generation" and isinstance(v, dict):
                gen = {}
                # Keep allowed top-level generation fields
                for gk, gv in v.items():
                    if gk in ("mode", "consistencyAnchors", "reproducibility", "extensions"):
                        if gk == "consistencyAnchors" and isinstance(gv, list):
                            gen[gk] = [fix_consistency_anchor(a) if isinstance(a, dict) else a for a in gv]
                        else:
                            gen[gk] = gv
                    elif gk == "steps" and isinstance(gv, list):
                        gen[gk] = [fix_generation_step(s) if isinstance(s, dict) else s for s in gv]
                if "mode" not in gen:
                    gen["mode"] = "ai_generated"
                result[k] = gen
            else:
                result[k] = fix_visual_asset_generation(v)
        return result
    elif isinstance(obj, list):
        return [fix_visual_asset_generation(item) for item in obj]
    return obj


# ── Visual asset entity fixes ─────────────────────────────────────────────────

VISUAL_ASSET_ALLOWED_EXTRA = {"sourceRef", "type"}  # Will be removed


def fix_visual_assets(assets: list) -> list:
    """Fix visualAsset items."""
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        ensure_entity_fields(asset, "visualAsset", name_fallback=asset.get("id", "visual"))
        # Remove non-schema fields
        asset.pop("type", None)
        asset.pop("sourceRef", None)
    return assets


# ── Marketing asset fixes ─────────────────────────────────────────────────────

def fix_marketing_assets(assets: list) -> list:
    """Fix marketingAsset items."""
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        ensure_entity_fields(asset, "marketingAsset", name_fallback=asset.get("id", "marketing"))
        # Fix null durationSec
        if asset.get("durationSec") is None:
            asset.pop("durationSec", None)
    return assets


# ── Script segments fix ───────────────────────────────────────────────────────

SEGMENT_TYPES = {
    "scene_heading", "action", "dialogue", "parenthetical",
    "transition", "title_card", "voice_over", "on_screen_text", "custom",
}


def fix_script_segments(segments: list) -> list:
    """Add missing required fields to script segments."""
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        if "order" not in seg:
            seg["order"] = i + 1
        if "segmentType" not in seg:
            # Infer from context
            if seg.get("audioAssetRef"):
                seg["segmentType"] = "dialogue"
            else:
                seg["segmentType"] = "custom"
    return segments


# ── Story arcs fix ────────────────────────────────────────────────────────────

def fix_story_arcs(arcs: list) -> list:
    """Remove non-schema fields from story arcs, add required fields."""
    for arc in arcs:
        if not isinstance(arc, dict):
            continue
        arc.pop("entityType", None)
        if "arcId" not in arc:
            arc["arcId"] = arc.get("id", "arc-unknown")
        if "name" not in arc:
            arc["name"] = arc.get("arcId", "Unknown Arc")
    return arcs


# ── Workflow status fix ───────────────────────────────────────────────────────

VALID_WORKFLOW_STATUS = {"pending", "running", "paused", "succeeded", "failed", "cancelled"}


def fix_workflows(workflows: list) -> list:
    """Fix workflow status values and edge structures."""
    for wf in workflows:
        if not isinstance(wf, dict):
            continue
        status = wf.get("status", "")
        if status == "success":
            wf["status"] = "succeeded"
        elif status not in VALID_WORKFLOW_STATUS:
            wf["status"] = "pending"
    return workflows


# ── Relationships fix ─────────────────────────────────────────────────────────

def fix_relationships(rels: object) -> list:
    """Convert relationships to schema-compliant array of edges with edgeId/dependencyType."""
    if isinstance(rels, dict) and "edges" in rels:
        edges = rels.get("edges", [])
    elif isinstance(rels, list):
        edges = rels
    else:
        return []

    fixed = []
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            continue
        result = {}
        result["edgeId"] = edge.get("edgeId") or edge.get("id") or f"rel-{i:03d}"

        if "fromRef" in edge:
            result["fromRef"] = to_entity_ref(edge["fromRef"])
        if "toRef" in edge:
            result["toRef"] = to_entity_ref(edge["toRef"])

        dep_type = edge.get("dependencyType", "references")
        valid_dep_types = {"requires", "blocks", "derives_from", "supersedes", "references", "syncs_with", "custom"}
        result["dependencyType"] = dep_type if dep_type in valid_dep_types else "references"

        if "required" in edge:
            result["required"] = edge["required"]
        if "notes" in edge:
            result["notes"] = edge["notes"]

        fixed.append(result)

    return fixed


# ── Audio technicalSpec fix ───────────────────────────────────────────────────

def fix_audio_tech_spec_recursive(obj: object) -> object:
    """Remove non-schema fields from audio technicalSpec."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "technicalSpec" and isinstance(v, dict):
                # Remove durationSec if it's in technicalSpec (not allowed there)
                cleaned = {tk: tv for tk, tv in v.items() if tk != "durationSec"}
                result[k] = cleaned
            else:
                result[k] = fix_audio_tech_spec_recursive(v)
        return result
    elif isinstance(obj, list):
        return [fix_audio_tech_spec_recursive(item) for item in obj]
    return obj


# ── Package fix ───────────────────────────────────────────────────────────────

GOVERNANCE_ALLOWED = {"requireApprovalForPublish"}
BUDGET_ALLOWED = {"currency"}
COMPLIANCE_ALLOWED = {"notes"}


def fix_package(pkg: dict) -> dict:
    """Remove non-schema package sub-objects (governance, budget, compliance extras)."""
    for section_name, allowed in [("governance", GOVERNANCE_ALLOWED),
                                   ("budget", BUDGET_ALLOWED),
                                   ("compliance", COMPLIANCE_ALLOWED)]:
        section = pkg.get(section_name)
        if not isinstance(section, dict):
            continue
        to_remove = [k for k in section if k not in allowed]
        for k in to_remove:
            del section[k]
    return pkg


# ── Project fix ───────────────────────────────────────────────────────────────

def fix_project(project: dict) -> dict:
    """Fix project-level schema issues."""
    # audiences items must be strings
    audiences = project.get("audiences") or []
    fixed_audiences = []
    for a in audiences:
        if isinstance(a, str):
            fixed_audiences.append(a)
        elif isinstance(a, dict):
            fixed_audiences.append(a.get("descriptor", str(a)))
        else:
            fixed_audiences.append(str(a))
    if audiences:
        project["audiences"] = fixed_audiences

    # defaultQualityProfileRef must be EntityRef
    dqpr = project.get("defaultQualityProfileRef")
    if isinstance(dqpr, str):
        project["defaultQualityProfileRef"] = {"id": dqpr}

    # globalCharacterRefs/globalEnvironmentRefs — clean entityType from refs
    for ref_field in ("globalCharacterRefs", "globalEnvironmentRefs", "globalPropRefs"):
        refs = project.get(ref_field)
        if isinstance(refs, list):
            project[ref_field] = [to_entity_ref(r) for r in refs]

    # globalPropRefs isn't in schema — move to extensions
    if "globalPropRefs" in project:
        ext = project.get("extensions") or {}
        ext["globalPropRefs"] = project.pop("globalPropRefs")
        project["extensions"] = ext

    return project


# ── Quality profile fix ───────────────────────────────────────────────────────

def fix_quality_profiles(profiles: list) -> list:
    """Fix qualityProfile structure: video/audio → profile.video/audio."""
    for qp in profiles:
        if not isinstance(qp, dict):
            continue
        # Schema expects a nested "profile" object containing video/audio
        if "profile" not in qp and ("video" in qp or "audio" in qp):
            profile = {}
            if "video" in qp:
                video = qp.pop("video")
                # Fix video sub-fields
                if isinstance(video, dict):
                    # resolution.label not allowed
                    res = video.get("resolution")
                    if isinstance(res, dict):
                        res.pop("label", None)
                    # aspectRatio must be object
                    ar = video.get("aspectRatio")
                    if isinstance(ar, str):
                        video["aspectRatio"] = {"expression": ar}
                    # frameRate.mode: progressive → constant
                    fr = video.get("frameRate")
                    if isinstance(fr, dict) and fr.get("mode") == "progressive":
                        fr["mode"] = "constant"
                profile["video"] = video
            if "audio" in qp:
                audio = qp.pop("audio")
                if isinstance(audio, dict):
                    audio.pop("dialogueNormalization", None)
                profile["audio"] = audio
            profile["name"] = qp.get("name") or qp.get("id", "default")
            qp["profile"] = profile
        ensure_entity_fields(qp, "qualityProfile", name_fallback=qp.get("id", "qp"))
    return profiles


# ── Scene fix ─────────────────────────────────────────────────────────────────

TRANSITION_TYPE_MAP = {
    "fade_from_black": "fade",
    "fade_to_black": "fade",
    "smash_cut": "cut",
    "match_cut": "cut",
    "j_cut": "cut",
    "l_cut": "cut",
    "jump_cut": "cut",
    "cross_dissolve": "dissolve",
    "iris": "custom",
}


def fix_scenes(scenes: list) -> list:
    """Add name and fix transition types on scenes."""
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        if "name" not in scene:
            scene["name"] = scene.get("id") or scene.get("logicalId") or "Unnamed Scene"

        for t_field in ("transitionIn", "transitionOut"):
            t = scene.get(t_field)
            if isinstance(t, dict) and "type" in t:
                t_type = t["type"]
                if t_type not in {"cut", "dissolve", "fade", "wipe", "push", "zoom", "custom"}:
                    t["type"] = TRANSITION_TYPE_MAP.get(t_type, "custom")
    return scenes


# ── Canonical documents fix ───────────────────────────────────────────────────

def fix_canonical_documents(docs: dict) -> dict:
    """Add missing name fields to canonical documents."""
    for key in ("story", "script", "directorInstructions"):
        doc = docs.get(key)
        if isinstance(doc, dict) and "name" not in doc:
            doc["name"] = doc.get("id") or doc.get("logicalId") or key.replace("_", " ").title()
    return docs


# ── Shots required fields fix ─────────────────────────────────────────────────

def fix_shots_required(shots: list) -> list:
    """Add required fields to shots: sceneRef, targetDurationSec, cinematicSpec."""
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        if "sceneRef" not in shot:
            shot["sceneRef"] = {"id": "scene-unknown"}
        if "targetDurationSec" not in shot:
            shot["targetDurationSec"] = 5.0
        if "cinematicSpec" not in shot:
            shot["cinematicSpec"] = {}
    return shots


# ── Visual asset spec fix ─────────────────────────────────────────────────────

def fix_visual_asset_specs(assets: list) -> list:
    """Fix spec sub-fields on visual assets."""
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        spec = asset.get("spec")
        if not isinstance(spec, dict):
            continue

        # resolution.label not allowed
        res = spec.get("resolution")
        if isinstance(res, dict):
            res.pop("label", None)

        # aspectRatio must be object {expression}
        ar = spec.get("aspectRatio")
        if isinstance(ar, str):
            spec["aspectRatio"] = {"expression": ar}

        # frameRate must be object {fps}
        fr = spec.get("frameRate")
        if isinstance(fr, (int, float)):
            spec["frameRate"] = {"fps": fr}

        # Remove non-schema fields from spec
        for extra in ("colorSpace", "durationSec", "dynamicRange", "stylePreset"):
            spec.pop(extra, None)
    return assets


# ── Visual asset generation step deep fixes ───────────────────────────────────

ADAPTER_INPUT_ALLOWED = {"adapterType", "weight", "ref", "parameters"}
REFERENCE_ASSET_ALLOWED = {"ref", "role", "weight", "notes"}
COST_ESTIMATE_ALLOWED = {"amount", "currency", "notes"}
REPRODUCIBILITY_ALLOWED = {"deterministic", "extensions"}


def fix_adapter_input(ai: dict) -> dict:
    """Fix adapterInput to match schema."""
    result = {}
    if "adapterType" in ai:
        result["adapterType"] = ai["adapterType"]

    # source → ref
    source = ai.get("source") or ai.get("ref")
    if source is not None:
        result["ref"] = to_entity_ref(source)

    # characterRef → ref
    char_ref = ai.get("characterRef")
    if char_ref is not None and "ref" not in result:
        result["ref"] = to_entity_ref(char_ref)

    # targetRef → ref (for ControlNet)
    target_ref = ai.get("targetRef")
    if target_ref is not None and "ref" not in result:
        result["ref"] = to_entity_ref(target_ref)

    if "weight" in ai:
        result["weight"] = ai["weight"]

    # controlType → parameters
    if "controlType" in ai:
        result["parameters"] = {"controlType": ai["controlType"]}

    return result


def fix_reference_asset(ra: dict) -> dict:
    """Fix referenceAsset to match schema."""
    result = {}
    # sourceRef → ref
    ref = ra.get("ref") or ra.get("sourceRef")
    if ref is not None:
        result["ref"] = to_entity_ref(ref)

    # type → role
    role = ra.get("role") or ra.get("type")
    if role:
        result["role"] = role

    for field in ("weight", "notes"):
        if field in ra:
            result[field] = ra[field]

    return result


def fix_cost_estimate(ce: dict) -> dict:
    """Fix costEstimate to match schema."""
    result = {}
    amount = ce.get("amount") or ce.get("valueEstimate") or ce.get("tokenEstimate", 0)
    result["amount"] = amount
    result["currency"] = ce.get("currency", "USD")
    return result


def fix_reproducibility(repro: dict) -> dict:
    """Fix reproducibility to match schema."""
    result = {}
    if "deterministic" in repro:
        result["deterministic"] = repro["deterministic"]
    return result


def fix_generation_steps_deep(obj: object) -> object:
    """Deep-fix generation step internals (adapterInputs, costEstimate, etc.)."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "generation" and isinstance(v, dict):
                gen = {}
                for gk, gv in v.items():
                    if gk == "steps" and isinstance(gv, list):
                        fixed_steps = []
                        for step in gv:
                            if not isinstance(step, dict):
                                fixed_steps.append(step)
                                continue
                            # Ensure operationType
                            if "operationType" not in step:
                                step["operationType"] = "generation"
                            # Fix adapterInputs
                            if "adapterInputs" in step:
                                step["adapterInputs"] = [
                                    fix_adapter_input(ai) if isinstance(ai, dict) else ai
                                    for ai in step["adapterInputs"]
                                ]
                            # Fix referenceAssets
                            if "referenceAssets" in step:
                                step["referenceAssets"] = [
                                    fix_reference_asset(ra) if isinstance(ra, dict) else ra
                                    for ra in step["referenceAssets"]
                                ]
                            # Fix costEstimate
                            if "costEstimate" in step and isinstance(step["costEstimate"], dict):
                                step["costEstimate"] = fix_cost_estimate(step["costEstimate"])
                            # Remove non-schema fields from step
                            # (costActual, retryConfig, asyncConfig, status, metrics, logs)
                            for extra in ("costActual", "retryConfig", "asyncConfig",
                                          "status", "metrics", "logs"):
                                step.pop(extra, None)
                            fixed_steps.append(step)
                        gen[gk] = fixed_steps
                    elif gk == "reproducibility" and isinstance(gv, dict):
                        gen[gk] = fix_reproducibility(gv)
                    else:
                        gen[gk] = gv
                result[k] = gen
            else:
                result[k] = fix_generation_steps_deep(v)
        return result
    elif isinstance(obj, list):
        return [fix_generation_steps_deep(item) for item in obj]
    return obj


# ── Generic assets fix ────────────────────────────────────────────────────────

GENERIC_ASSET_EXTRAS = {
    "colorSpace", "filePath", "format", "label",
    "lutDimension", "lutSize", "technicalNotes",
    "maskParameters", "maskType", "overlayParameters",
    "resolution", "frameRate",
}


def fix_generic_assets(assets: list) -> list:
    """Fix genericAsset items."""
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        ensure_entity_fields(asset, "genericAsset", name_fallback=asset.get("label") or asset.get("id", "asset"))
        # Remove non-schema fields → extensions
        ext = asset.get("extensions") or {}
        for extra in GENERIC_ASSET_EXTRAS:
            if extra in asset:
                ext[extra] = asset.pop(extra)
        if ext:
            asset["extensions"] = ext
    return assets


# ── Null ref cleanup ──────────────────────────────────────────────────────────

def remove_null_refs_recursive(obj: object) -> object:
    """Remove ref fields that are None (schema expects object, not null)."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if v is None and k in SINGLE_REF_FIELDS:
                continue  # Skip null refs
            result[k] = remove_null_refs_recursive(v)
        return result
    elif isinstance(obj, list):
        return [remove_null_refs_recursive(item) for item in obj]
    return obj


# ── Workflow edges fix ────────────────────────────────────────────────────────

# ── Workflow nodes fix ─────────────────────────────────────────────────────────

NODE_TYPE_MAP = {
    "GenerationNode": "generation",
    "TransformNode": "transform",
    "ValidationNode": "validation",
    "RenderNode": "render",
    "NotificationNode": "notification",
}
VALID_NODE_TYPES = {"generation", "transform", "validation", "render", "notification", "approval", "custom"}
VALID_NODE_STATUS = {"pending", "running", "succeeded", "failed", "cancelled"}


def _make_stub_generation_step(node: dict) -> dict:
    """Create a minimal generationStep from node metadata."""
    return {
        "stepId": node.get("nodeId", "step-auto"),
        "operationType": "generation",
    }


def fix_workflow_node(node: dict) -> dict:
    """Fix a single workflow node to match schema oneOf discriminated union."""
    raw_type = node.get("type") or node.get("nodeType", "custom")
    node_type = NODE_TYPE_MAP.get(raw_type, raw_type if raw_type in VALID_NODE_TYPES else "custom")

    # Collect extra fields for extensions
    base_fields = {"nodeId", "name", "nodeType", "type", "inputs", "outputs",
                    "retryPolicy", "cacheKey", "extensions", "status"}
    ext = node.get("extensions") or {}
    for nk, nv in node.items():
        if nk not in base_fields:
            ext[nk] = nv

    fixed = {
        "nodeId": node.get("nodeId", "node-auto"),
        "name": node.get("name", ""),
        "nodeType": node_type,
    }

    # Add type-specific required fields
    if node_type == "generation":
        fixed["generationStep"] = node.get("generationStep") or _make_stub_generation_step(node)
    elif node_type == "transform":
        fixed["operation"] = node.get("operation") or {
            "opId": f"op-{node.get('nodeId', 'auto')}",
            "opType": "custom",
            "executor": "pipeline",
        }
    elif node_type == "validation":
        fixed["validationRules"] = node.get("validationRules") or [
            {"name": node.get("name", "validation")}
        ]
    elif node_type == "render":
        fixed["renderPlanRef"] = node.get("renderPlanRef") or {"id": "renderplan-auto"}
    elif node_type == "notification":
        fixed["channel"] = node.get("channel") or "log"
    elif node_type == "approval":
        fixed["role"] = node.get("role") or "reviewer"
        fixed["approvalStatus"] = node.get("approvalStatus") or "pending"
    elif node_type == "custom":
        fixed["executor"] = node.get("executor") or {}

    if ext:
        fixed["extensions"] = ext

    return fixed


def fix_workflow_nodes(obj: object) -> object:
    """Fix orchestration workflow nodes to match schema."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "workflows" and isinstance(v, list):
                for wf in v:
                    if not isinstance(wf, dict):
                        continue
                    nodes = wf.get("nodes") or []
                    wf["nodes"] = [
                        fix_workflow_node(n) if isinstance(n, dict) else n
                        for n in nodes
                    ]
                result[k] = v
            else:
                result[k] = fix_workflow_nodes(v)
        return result
    elif isinstance(obj, list):
        return [fix_workflow_nodes(item) for item in obj]
    return obj


# ── Deliverables fix ──────────────────────────────────────────────────────────

PUBLISH_SCHEDULE_KIND_MAP = {
    "fixed": "exact",
    "tbd": "unknown",
    "approximate": "approximate",
    "exact": "exact",
    "range": "range",
    "unknown": "unknown",
}
PUBLISH_SCHEDULE_ALLOWED = {"kind", "date", "extensions"}


def fix_deliverables(deliverables: list) -> list:
    """Fix deliverable items."""
    for d in deliverables:
        if not isinstance(d, dict):
            continue
        ensure_entity_fields(d, "finalOutput", name_fallback=d.get("id", "output"))

        # Fix accessibilityConfig refs
        ac = d.get("accessibilityConfig")
        if isinstance(ac, dict):
            for ref_field in ("audioDescriptionRef", "signLanguageRef"):
                val = ac.get(ref_field)
                if val is None:
                    ac.pop(ref_field, None)
                elif isinstance(val, str):
                    ac[ref_field] = {"id": val}

        # Fix platformDeliveries publishSchedule
        pds = d.get("platformDeliveries") or []
        for pd in pds:
            if not isinstance(pd, dict):
                continue
            ps = pd.get("publishSchedule")
            if isinstance(ps, dict):
                kind = ps.get("kind", "unknown")
                ps["kind"] = PUBLISH_SCHEDULE_KIND_MAP.get(kind, kind if kind in {"exact", "approximate", "range", "unknown"} else "unknown")
                # Move non-schema fields out
                to_remove = [k for k in ps if k not in PUBLISH_SCHEDULE_ALLOWED]
                for k in to_remove:
                    del ps[k]

    return deliverables


def fix_workflow_edges(obj: object) -> object:
    """Fix orchestration workflow edges: remove dependencyType, use condition."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "workflows" and isinstance(v, list):
                for wf in v:
                    if isinstance(wf, dict):
                        edges = wf.get("edges") or []
                        fixed_edges = []
                        for edge in edges:
                            if not isinstance(edge, dict):
                                fixed_edges.append(edge)
                                continue
                            fixed = {}
                            fixed["fromNodeId"] = edge.get("fromNodeId") or edge.get("from", "")
                            fixed["toNodeId"] = edge.get("toNodeId") or edge.get("to", "")
                            dep = edge.get("dependencyType")
                            if dep:
                                fixed["condition"] = dep
                            if "notes" in edge:
                                fixed["notes"] = edge["notes"]
                            fixed_edges.append(fixed)
                        wf["edges"] = fixed_edges
                result[k] = v
            else:
                result[k] = fix_workflow_edges(v)
        return result
    elif isinstance(obj, list):
        return [fix_workflow_edges(item) for item in obj]
    return obj


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

    # 4. Fix fragment categories
    doc = fix_fragment_categories(doc)

    # 5. Fix syncPoints throughout
    doc = fix_sync_points_recursive(doc)

    # 6. Fix operations throughout (before ref fixing, since we rename id→opId)
    doc = fix_operations_in_tree(doc)

    # 7. Fix visual asset generation blocks (before ref fixing)
    doc = fix_visual_asset_generation(doc)

    # 8. Fix all refs throughout
    doc = fix_refs_recursive(doc)

    # 9. Remove null refs
    doc = remove_null_refs_recursive(doc)

    # 10. Fix localization targets (null refs)
    doc = fix_localization_targets_recursive(doc)

    # 11. Fix qcResults
    doc = fix_qc_results_recursive(doc)

    # 12. Fix platformDeliveries
    doc = fix_platform_deliveries_recursive(doc)

    # 13. Fix audio technicalSpec
    doc = fix_audio_tech_spec_recursive(doc)

    # 14. Fix generation step internals (adapterInputs, costEstimate, etc.)
    doc = fix_generation_steps_deep(doc)

    # 15. Fix workflow edges (dependencyType → condition)
    doc = fix_workflow_edges(doc)

    # 15b. Fix workflow nodes
    doc = fix_workflow_nodes(doc)

    # 16. Fix audio assets
    audio_assets = (doc.get("assetLibrary") or {}).get("audioAssets") or []
    for i, aa in enumerate(audio_assets):
        audio_assets[i] = fix_audio_asset(aa)

    # 17. Fix visual assets
    visual_assets = (doc.get("assetLibrary") or {}).get("visualAssets") or []
    if visual_assets:
        fix_visual_assets(visual_assets)
        fix_visual_asset_specs(visual_assets)

    # 18. Fix marketing assets
    marketing_assets = (doc.get("assetLibrary") or {}).get("marketingAssets") or []
    if marketing_assets:
        fix_marketing_assets(marketing_assets)

    # 19. Fix generic assets
    generic_assets = (doc.get("assetLibrary") or {}).get("genericAssets") or []
    if generic_assets:
        fix_generic_assets(generic_assets)

    # 20. Fix assembly entities
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

    # 21. Fix dependencies (list → {edges} with fromNodeId/toNodeId)
    if "dependencies" in doc:
        doc["dependencies"] = fix_dependencies(doc["dependencies"])

    # 22. Fix relationships (list → {edges} with edgeId/dependencyType)
    if "relationships" in doc:
        doc["relationships"] = fix_relationships(doc["relationships"])

    # 23. Fix package
    if "package" in doc:
        fix_package(doc["package"])

    # 24. Fix project
    if "project" in doc:
        fix_project(doc["project"])

    # 25. Fix quality profiles
    qps = doc.get("qualityProfiles") or []
    if qps:
        fix_quality_profiles(qps)

    # 26. Fix scenes
    scenes = (doc.get("production") or {}).get("scenes") or []
    if scenes:
        fix_scenes(scenes)
    for scene in scenes:
        fix_scene_shot_refs(scene)

    # 27. Fix shots
    shots = (doc.get("production") or {}).get("shots") or []
    if shots:
        doc["production"]["shots"] = fix_shots(shots)
        fix_shots_required(shots)

    # 28. Fix canonical documents
    if "canonicalDocuments" in doc:
        fix_canonical_documents(doc["canonicalDocuments"])

    # 29. Fix script segments
    script = (doc.get("canonicalDocuments") or {}).get("script") or {}
    segments = script.get("segments") or []
    if segments:
        fix_script_segments(segments)

    # 30. Fix story arcs
    story = (doc.get("canonicalDocuments") or {}).get("story") or {}
    arcs = story.get("arcs") or []
    if arcs:
        fix_story_arcs(arcs)

    # 31. Fix orchestration workflows
    workflows = (doc.get("orchestration") or {}).get("workflows") or []
    if workflows:
        fix_workflows(workflows)

    # 32. Fix deliverables
    deliverables = doc.get("deliverables") or []
    if deliverables:
        fix_deliverables(deliverables)

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
