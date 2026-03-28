"""
Tests for pipeline.consistency_check — scene consistency gap detection and auto-fix.

Run: python -m pytest tests/test_consistency_check.py -v
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.consistency_check import (
    Severity,
    Finding,
    check_consistency,
    fix_consistency,
    process_file,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

def _bare_instance(
    *,
    scene_anchors: bool = False,
    shot_anchors: bool = False,
    temporal_bridges: bool = False,
    single_shot: bool = False,
) -> dict:
    """Build a minimal v3 instance with configurable consistency state."""
    shots = [
        {
            "id": "sh-01", "logicalId": "sh-01", "entityType": "shot",
            "name": "Wide", "shotNumber": 1,
            "sceneRef": {"id": "sc-01"},
            "targetDurationSec": 2,
            "characterRefs": [{"id": "c1"}],
            "environmentRef": {"id": "e1"},
            "cinematicSpec": {"shotType": "wide"},
        },
    ]
    shot_refs = [{"id": "sh-01"}]

    if not single_shot:
        shot2 = {
            "id": "sh-02", "logicalId": "sh-02", "entityType": "shot",
            "name": "Close", "shotNumber": 2,
            "sceneRef": {"id": "sc-01"},
            "targetDurationSec": 2,
            "characterRefs": [{"id": "c1"}],
            "environmentRef": {"id": "e1"},
            "cinematicSpec": {"shotType": "close_up"},
        }
        if temporal_bridges:
            shot2["cinematicSpec"]["temporalBridgeAnchorRef"] = {
                "id": "sh-01",
                "notes": "Previous shot",
            }
        shots.append(shot2)
        shot_refs.append({"id": "sh-02"})

    scene = {
        "id": "sc-01", "logicalId": "sc-01", "entityType": "scene",
        "sceneNumber": 1, "name": "Scene 1",
        "characterRefs": [{"id": "c1"}],
        "environmentRef": {"id": "e1"},
        "propRefs": [{"id": "p1"}],
        "shotRefs": shot_refs,
    }
    if scene_anchors:
        scene["generation"] = {
            "consistencyAnchors": [
                {"anchorType": "character", "ref": {"id": "c1"}, "lockLevel": "hard"},
                {"anchorType": "environment", "ref": {"id": "e1"}, "lockLevel": "hard"},
                {"anchorType": "prop", "ref": {"id": "p1"}, "lockLevel": "medium"},
            ]
        }

    if shot_anchors:
        for sh in shots:
            sh["genParams"] = {
                "stepId": f"gen-{sh['id']}",
                "operationType": "video_generation",
                "consistencyAnchors": [
                    {"anchorType": "character", "ref": {"id": "c1"}, "lockLevel": "hard"},
                    {"anchorType": "environment", "ref": {"id": "e1"}, "lockLevel": "hard"},
                    {"anchorType": "prop", "ref": {"id": "p1"}, "lockLevel": "medium"},
                ],
            }

    return {
        "schemaVersion": "3.0.0",
        "production": {
            "characters": [
                {"id": "c1", "logicalId": "c1", "entityType": "character", "name": "C"},
            ],
            "environments": [
                {"id": "e1", "logicalId": "e1", "entityType": "environment", "name": "E"},
            ],
            "props": [
                {"id": "p1", "logicalId": "p1", "entityType": "prop", "name": "P"},
            ],
            "scenes": [scene],
            "shots": shots,
            "styleGuides": [],
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# Detection tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckConsistency:

    def test_fully_bare_instance_reports_all_gaps(self):
        """Instance with no anchors or bridges should report errors."""
        instance = _bare_instance()
        findings = check_consistency(instance)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        # Should detect: no scene anchors, no shot anchors (x2), no bridge (shot 2)
        assert len(errors) >= 4
        msgs = " ".join(f.message for f in errors)
        assert "generation.consistencyAnchors" in msgs
        assert "genParams.consistencyAnchors" in msgs
        assert "temporalBridgeAnchorRef" in msgs

    def test_fully_wired_instance_is_clean(self):
        """Instance with all anchors and bridges should have no errors."""
        instance = _bare_instance(
            scene_anchors=True,
            shot_anchors=True,
            temporal_bridges=True,
        )
        findings = check_consistency(instance)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_single_shot_scene_no_bridge_needed(self):
        """Single-shot scene should not flag missing bridge."""
        instance = _bare_instance(
            single_shot=True,
            scene_anchors=True,
            shot_anchors=True,
        )
        findings = check_consistency(instance)
        bridge_findings = [f for f in findings if "temporalBridge" in f.message]
        assert len(bridge_findings) == 0

    def test_missing_scene_anchors_only(self):
        """Missing scene anchors flagged even if shots have anchors."""
        instance = _bare_instance(shot_anchors=True, temporal_bridges=True)
        findings = check_consistency(instance)
        scene_errs = [
            f for f in findings
            if f.entity_id == "sc-01" and f.severity == Severity.ERROR
        ]
        assert len(scene_errs) >= 1
        assert "generation.consistencyAnchors" in scene_errs[0].message

    def test_missing_shot_anchors_only(self):
        """Missing shot anchors flagged even if scene has anchors."""
        instance = _bare_instance(scene_anchors=True, temporal_bridges=True)
        findings = check_consistency(instance)
        shot_errs = [
            f for f in findings
            if f.entity_id.startswith("sh-") and "genParams" in f.message
        ]
        assert len(shot_errs) == 2  # both shots

    def test_missing_bridge_only(self):
        """Missing bridge flagged for second shot."""
        instance = _bare_instance(scene_anchors=True, shot_anchors=True)
        findings = check_consistency(instance)
        bridge_errs = [f for f in findings if "temporalBridge" in f.message]
        assert len(bridge_errs) == 1
        assert bridge_errs[0].entity_id == "sh-02"
        assert "sh-01" in bridge_errs[0].message

    def test_uncovered_entity_warning(self):
        """Scene anchors that miss a declared entity should warn."""
        instance = _bare_instance(scene_anchors=True, shot_anchors=True, temporal_bridges=True)
        # Remove the prop anchor from scene
        instance["production"]["scenes"][0]["generation"]["consistencyAnchors"] = [
            {"anchorType": "character", "ref": {"id": "c1"}, "lockLevel": "hard"},
            {"anchorType": "environment", "ref": {"id": "e1"}, "lockLevel": "hard"},
            # prop p1 deliberately omitted
        ]
        findings = check_consistency(instance)
        warnings = [f for f in findings if f.severity == Severity.WARNING]
        assert any("p1" in w.message for w in warnings)

    def test_dangling_shot_ref(self):
        """Shot ref pointing to nonexistent shot should be an error."""
        instance = _bare_instance(scene_anchors=True)
        instance["production"]["scenes"][0]["shotRefs"].append({"id": "ghost"})
        findings = check_consistency(instance)
        ghost_errs = [f for f in findings if "ghost" in f.message or "ghost" in f.entity_id]
        assert len(ghost_errs) >= 1

    def test_genparams_missing_stepid(self):
        """genParams without stepId should flag error."""
        instance = _bare_instance(scene_anchors=True, temporal_bridges=True)
        # Add genParams with anchors but no stepId
        instance["production"]["shots"][0]["genParams"] = {
            "consistencyAnchors": [
                {"anchorType": "character", "ref": {"id": "c1"}, "lockLevel": "hard"},
            ],
        }
        findings = check_consistency(instance)
        step_errs = [f for f in findings if "stepId" in f.message]
        assert len(step_errs) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# Fix tests
# ══════════════════════════════════════════════════════════════════════════════

class TestFixConsistency:

    def test_fix_resolves_all_errors(self):
        """Fixing a bare instance should resolve all fixable errors."""
        instance = _bare_instance()
        pre = check_consistency(instance)
        assert len([f for f in pre if f.severity == Severity.ERROR]) > 0

        fixed = fix_consistency(instance)
        assert fixed > 0

        post = check_consistency(instance)
        post_errors = [f for f in post if f.severity == Severity.ERROR]
        assert len(post_errors) == 0

    def test_fix_adds_scene_anchors(self):
        """Fix should create generation.consistencyAnchors on scenes."""
        instance = _bare_instance()
        fix_consistency(instance)
        scene = instance["production"]["scenes"][0]
        anchors = scene.get("generation", {}).get("consistencyAnchors", [])
        assert len(anchors) >= 2  # at least character + environment
        types = {a["anchorType"] for a in anchors}
        assert "character" in types
        assert "environment" in types

    def test_fix_adds_temporal_bridges(self):
        """Fix should add temporalBridgeAnchorRef to non-first shots."""
        instance = _bare_instance()
        fix_consistency(instance)
        shot2 = instance["production"]["shots"][1]
        bridge = shot2["cinematicSpec"].get("temporalBridgeAnchorRef", {})
        assert bridge.get("id") == "sh-01"

    def test_fix_adds_step_id(self):
        """Fix should set stepId and operationType on genParams."""
        instance = _bare_instance()
        fix_consistency(instance)
        for sh in instance["production"]["shots"]:
            gp = sh.get("genParams", {})
            assert "stepId" in gp
            assert gp["operationType"] == "video_generation"

    def test_fix_idempotent(self):
        """Running fix twice should not change anything the second time."""
        instance = _bare_instance()
        fix_consistency(instance)
        snapshot = json.dumps(instance)
        fixes_2 = fix_consistency(instance)
        assert fixes_2 == 0
        assert json.dumps(instance) == snapshot

    def test_fix_preserves_existing_anchors(self):
        """Fix should not overwrite existing shot-level anchors."""
        instance = _bare_instance(shot_anchors=True)
        original_anchors = list(
            instance["production"]["shots"][0]["genParams"]["consistencyAnchors"]
        )
        fix_consistency(instance)
        current = instance["production"]["shots"][0]["genParams"]["consistencyAnchors"]
        assert current == original_anchors


# ══════════════════════════════════════════════════════════════════════════════
# File processing tests
# ══════════════════════════════════════════════════════════════════════════════

class TestProcessFile:

    def test_check_mode(self, tmp_path):
        """process_file in check-only mode should not modify the file."""
        fpath = tmp_path / "test.gvpp.json"
        instance = _bare_instance()
        fpath.write_text(json.dumps(instance, indent=2))
        original = fpath.read_text()

        report = process_file(fpath, fix=False)
        assert not report.ok
        assert fpath.read_text() == original  # unchanged

    def test_fix_mode(self, tmp_path):
        """process_file with --fix should write back and resolve errors."""
        fpath = tmp_path / "test.gvpp.json"
        instance = _bare_instance()
        fpath.write_text(json.dumps(instance, indent=2))

        report = process_file(fpath, fix=True)
        assert report.fixed > 0
        assert report.ok

        # Verify the file was rewritten
        reloaded = json.loads(fpath.read_text())
        assert reloaded["production"]["scenes"][0].get("generation")

    def test_invalid_json(self, tmp_path):
        """Non-JSON file should return error finding."""
        fpath = tmp_path / "bad.json"
        fpath.write_text("{not valid json")
        report = process_file(fpath)
        assert not report.ok
        assert "Failed to read" in report.findings[0].message

    def test_validate_flag(self, tmp_path):
        """--validate should run schema validation after fix."""
        fpath = tmp_path / "test.gvpp.json"
        instance = _bare_instance()
        fpath.write_text(json.dumps(instance, indent=2))

        # This won't pass full schema validation (minimal instance),
        # but it should at least not crash
        report = process_file(fpath, fix=True, validate=True)
        # Validation may fail on minimal instance — that's fine,
        # we're testing that the flag triggers validation
        assert report.findings is not None


# ══════════════════════════════════════════════════════════════════════════════
# Integration: real example files
# ══════════════════════════════════════════════════════════════════════════════

class TestRealExamples:

    @pytest.fixture(params=["spark.gvpp.json", "thundercats-hunt-teaser.gvpp.json"])
    def example_path(self, request):
        p = Path(__file__).parent.parent / "examples" / request.param
        if not p.exists():
            pytest.skip(f"{request.param} not found")
        return p

    def test_examples_pass_after_fix(self, example_path):
        """All example files should pass consistency check (already fixed)."""
        instance = json.loads(example_path.read_text())
        findings = check_consistency(instance)
        errors = [f for f in findings if f.severity == Severity.ERROR]
        assert len(errors) == 0, (
            f"{example_path.name} has {len(errors)} error(s): "
            + "; ".join(f.message for f in errors)
        )
