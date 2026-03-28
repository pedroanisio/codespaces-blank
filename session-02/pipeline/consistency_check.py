"""
consistency_check.py — Detect and optionally fix scene-level consistency gaps.

Scans a GVPP v3 instance for shots that lack the consistency anchors and
temporal bridges required for coherent multi-angle scene coverage.

Detections
----------
  1. Scenes with multiple shots but no ``generation.consistencyAnchors``
  2. Shots missing ``genParams.consistencyAnchors``
  3. Non-first shots in a scene missing ``cinematicSpec.temporalBridgeAnchorRef``
  4. Shots referencing entities (characters/environments/props) not covered
     by their anchors
  5. ``genParams`` present but missing required ``stepId``/``operationType``

Usage
-----
  # Check a single file:
  python -m pipeline.consistency_check examples/spark.gvpp.json

  # Check all examples:
  python -m pipeline.consistency_check examples/*.gvpp.json

  # Auto-fix and write back:
  python -m pipeline.consistency_check examples/spark.gvpp.json --fix

  # Validate fixed output against schema:
  python -m pipeline.consistency_check examples/spark.gvpp.json --fix --validate
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    severity: Severity
    entity_id: str
    message: str
    fixable: bool = False


@dataclass
class ConsistencyReport:
    path: str
    findings: list[Finding] = field(default_factory=list)
    fixed: int = 0

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.WARNING]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def check_consistency(instance: dict) -> list[Finding]:
    """Analyze a GVPP v3 instance for consistency gaps. Returns findings."""
    findings: list[Finding] = []
    production = instance.get("production") or {}
    scenes = production.get("scenes", [])
    shots = production.get("shots", [])

    # Index shots by id
    shot_index: dict[str, dict] = {}
    for sh in shots:
        shot_index[sh.get("id", "")] = sh
        if sh.get("logicalId"):
            shot_index[sh["logicalId"]] = sh

    # Index entities for anchor coverage checks
    entity_ids: dict[str, str] = {}  # id -> entityType
    for kind in ("characters", "environments", "props"):
        for e in production.get(kind, []):
            etype = e.get("entityType", kind.rstrip("s"))
            entity_ids[e.get("id", "")] = etype
            if e.get("logicalId"):
                entity_ids[e["logicalId"]] = etype

    for scene in scenes:
        scene_id = scene.get("id") or scene.get("logicalId") or "?"
        shot_refs = scene.get("shotRefs", [])

        # ── Check 1: Scene-level generation.consistencyAnchors ────────────
        scene_gen = scene.get("generation") or {}
        scene_anchors = scene_gen.get("consistencyAnchors", [])
        if len(shot_refs) > 1 and not scene_anchors:
            findings.append(Finding(
                severity=Severity.ERROR,
                entity_id=scene_id,
                message=(
                    f"Scene has {len(shot_refs)} shots but no "
                    f"generation.consistencyAnchors — shots will generate "
                    f"with inconsistent lighting, environment, and objects"
                ),
                fixable=True,
            ))

        # Collect all entity refs the scene declares
        scene_char_ids = {r.get("id", "") for r in scene.get("characterRefs", [])}
        scene_env_id = (scene.get("environmentRef") or {}).get("id", "")
        scene_prop_ids = {r.get("id", "") for r in scene.get("propRefs", [])}
        scene_entity_ids = scene_char_ids | scene_prop_ids
        if scene_env_id:
            scene_entity_ids.add(scene_env_id)

        # Check scene anchor coverage
        if scene_anchors:
            anchored_refs = {
                (a.get("ref") or {}).get("id", "") for a in scene_anchors
            }
            uncovered = scene_entity_ids - anchored_refs - {""}
            if uncovered:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    entity_id=scene_id,
                    message=(
                        f"Scene references entities not covered by "
                        f"consistency anchors: {', '.join(sorted(uncovered))}"
                    ),
                    fixable=True,
                ))

        # ── Per-shot checks ───────────────────────────────────────────────
        for i, sref in enumerate(shot_refs):
            ref_id = sref.get("id") or sref.get("logicalId") or ""
            shot = shot_index.get(ref_id)
            if not shot:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    entity_id=ref_id or f"{scene_id}/shotRef[{i}]",
                    message=f"Shot ref '{ref_id}' not found in production.shots",
                    fixable=False,
                ))
                continue

            shot_id = shot.get("id") or shot.get("logicalId") or ref_id
            gp = shot.get("genParams") or {}
            shot_anchors = gp.get("consistencyAnchors", [])
            spec = shot.get("cinematicSpec") or {}
            bridge = (spec.get("temporalBridgeAnchorRef") or {}).get("id", "")

            # ── Check 2: Shot-level consistency anchors ───────────────────
            if not shot_anchors:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    entity_id=shot_id,
                    message=(
                        "Shot has no genParams.consistencyAnchors — "
                        "will rely on pipeline auto-inference only"
                    ),
                    fixable=True,
                ))

            # ── Check 3: Temporal bridge for non-first shots ──────────────
            if i > 0 and not bridge:
                prev_id = shot_refs[i - 1].get("id") or shot_refs[i - 1].get("logicalId") or ""
                findings.append(Finding(
                    severity=Severity.ERROR,
                    entity_id=shot_id,
                    message=(
                        f"Non-first shot in scene missing "
                        f"temporalBridgeAnchorRef (should point to {prev_id})"
                    ),
                    fixable=True,
                ))

            # ── Check 4: Anchor coverage vs shot entity refs ──────────────
            shot_char_ids = {r.get("id", "") for r in shot.get("characterRefs", [])}
            shot_env_id = (shot.get("environmentRef") or {}).get("id", "")
            shot_prop_ids = {r.get("id", "") for r in shot.get("propRefs", [])}
            shot_entities = shot_char_ids | shot_prop_ids
            if shot_env_id:
                shot_entities.add(shot_env_id)

            if shot_anchors and shot_entities:
                anchored = {
                    (a.get("ref") or {}).get("id", "") for a in shot_anchors
                }
                uncovered = shot_entities - anchored - {""}
                if uncovered:
                    findings.append(Finding(
                        severity=Severity.WARNING,
                        entity_id=shot_id,
                        message=(
                            f"Shot references entities not covered by "
                            f"its anchors: {', '.join(sorted(uncovered))}"
                        ),
                        fixable=True,
                    ))

            # ── Check 5: genParams missing required fields ────────────────
            if gp and "consistencyAnchors" in gp and "stepId" not in gp:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    entity_id=shot_id,
                    message="genParams present but missing required 'stepId'",
                    fixable=True,
                ))

    return findings


def fix_consistency(instance: dict) -> int:
    """
    Apply automatic fixes for all fixable consistency gaps.
    Mutates instance in-place. Returns number of fixes applied.
    """
    fixes = 0
    production = instance.get("production") or {}
    scenes = production.get("scenes", [])

    for scene in scenes:
        scene_id = scene.get("id") or scene.get("logicalId") or ""
        shot_refs = scene.get("shotRefs", [])

        # Fix scene-level generation.consistencyAnchors
        scene_gen = scene.get("generation") or {}
        if not scene_gen.get("consistencyAnchors"):
            anchors = []
            for cref in scene.get("characterRefs", []):
                anchors.append({
                    "anchorType": "character",
                    "name": f"Character identity — {cref['id']}",
                    "ref": {"id": cref["id"]},
                    "lockLevel": "hard",
                    "attributes": [
                        "appearance", "costume", "proportions", "color",
                    ],
                })
            eref = scene.get("environmentRef")
            if eref:
                anchors.append({
                    "anchorType": "environment",
                    "name": f"Environment continuity — {eref['id']}",
                    "ref": {"id": eref["id"]},
                    "lockLevel": "hard",
                    "attributes": [
                        "layout", "lighting", "color_temperature",
                        "atmosphere", "set_dressing",
                    ],
                })
            for pref in scene.get("propRefs", []):
                anchors.append({
                    "anchorType": "prop",
                    "name": f"Prop continuity — {pref['id']}",
                    "ref": {"id": pref["id"]},
                    "lockLevel": "medium",
                    "attributes": ["appearance", "position", "scale"],
                })
            if anchors:
                scene["generation"] = {"consistencyAnchors": anchors}
                fixes += 1

        scene_anchors = scene.get("generation", {}).get("consistencyAnchors", [])

        # Fix per-shot data
        shot_index: dict[str, dict] = {}
        for sh in production.get("shots", []):
            shot_index[sh.get("id", "")] = sh
            if sh.get("logicalId"):
                shot_index[sh["logicalId"]] = sh

        for i, sref in enumerate(shot_refs):
            ref_id = sref.get("id") or sref.get("logicalId") or ""
            shot = shot_index.get(ref_id)
            if not shot:
                continue

            # Fix temporal bridge
            if i > 0:
                spec = shot.setdefault("cinematicSpec", {})
                if not spec.get("temporalBridgeAnchorRef"):
                    prev_id = (
                        shot_refs[i - 1].get("id")
                        or shot_refs[i - 1].get("logicalId")
                        or ""
                    )
                    spec["temporalBridgeAnchorRef"] = {
                        "id": prev_id,
                        "notes": (
                            "Auto-linked: previous shot in same scene "
                            "for visual continuity"
                        ),
                    }
                    fixes += 1

            # Fix genParams.consistencyAnchors
            gp = shot.setdefault("genParams", {})
            if not gp.get("consistencyAnchors") and scene_anchors:
                gp["consistencyAnchors"] = list(scene_anchors)
                fixes += 1

            # Fix missing stepId/operationType
            if gp and "stepId" not in gp:
                sid = shot.get("id") or shot.get("logicalId") or "unknown"
                gp["stepId"] = f"gen-{sid}"
                gp["operationType"] = "video_generation"
                fixes += 1

    return fixes


def format_report(report: ConsistencyReport) -> str:
    """Format a report for terminal output."""
    lines = [f"\n{'='*60}", f"  {report.path}", f"{'='*60}"]

    if not report.findings:
        lines.append("  ✓ No consistency issues found.")
        return "\n".join(lines)

    severity_icon = {
        Severity.ERROR: "✗",
        Severity.WARNING: "⚠",
        Severity.INFO: "·",
    }

    for f in report.findings:
        icon = severity_icon[f.severity]
        fix_tag = " [fixable]" if f.fixable else ""
        lines.append(f"  {icon} [{f.entity_id}] {f.message}{fix_tag}")

    errors = len(report.errors)
    warnings = len(report.warnings)
    lines.append(f"\n  Summary: {errors} error(s), {warnings} warning(s)")
    if report.fixed:
        lines.append(f"  Fixed: {report.fixed} issue(s)")
    lines.append(f"  Status: {'PASS' if report.ok else 'FAIL'}")
    return "\n".join(lines)


def process_file(
    path: Path, *, fix: bool = False, validate: bool = False,
) -> ConsistencyReport:
    """Check (and optionally fix) a single GVPP file."""
    report = ConsistencyReport(path=str(path))

    try:
        instance = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        report.findings.append(Finding(
            severity=Severity.ERROR,
            entity_id=str(path),
            message=f"Failed to read: {exc}",
        ))
        return report

    report.findings = check_consistency(instance)

    if fix and any(f.fixable for f in report.findings):
        report.fixed = fix_consistency(instance)
        path.write_text(json.dumps(instance, indent=2, ensure_ascii=False) + "\n")
        # Re-check after fix
        report.findings = check_consistency(instance)

    if validate:
        schema_path = Path(__file__).parent.parent / "schemas" / "active" / "gvpp-v3.schema.json"
        if schema_path.exists():
            try:
                import jsonschema
                schema = json.loads(schema_path.read_text())
                jsonschema.validate(instance, schema)
            except jsonschema.ValidationError as exc:
                report.findings.append(Finding(
                    severity=Severity.ERROR,
                    entity_id=str(path),
                    message=f"Schema validation failed: {exc.message}",
                ))
            except ImportError:
                report.findings.append(Finding(
                    severity=Severity.WARNING,
                    entity_id=str(path),
                    message="jsonschema not installed — skipping schema validation",
                ))

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect and fix scene-level consistency gaps in GVPP files.",
    )
    parser.add_argument(
        "files", nargs="+", type=Path,
        help="GVPP JSON file(s) to check",
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Auto-fix fixable issues and write back",
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate against JSON Schema after fix",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output findings as JSON",
    )
    args = parser.parse_args(argv)

    all_ok = True
    reports = []
    for fpath in args.files:
        report = process_file(fpath, fix=args.fix, validate=args.validate)
        reports.append(report)
        if not report.ok:
            all_ok = False

    if args.json_output:
        out = []
        for r in reports:
            out.append({
                "path": r.path,
                "ok": r.ok,
                "fixed": r.fixed,
                "findings": [
                    {
                        "severity": f.severity.value,
                        "entity_id": f.entity_id,
                        "message": f.message,
                        "fixable": f.fixable,
                    }
                    for f in r.findings
                ],
            })
        print(json.dumps(out, indent=2))
    else:
        for r in reports:
            print(format_report(r))

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
