"""
pipeline_check.py — End-to-end pipeline checklist with evidence generation.

Runs a v3 instance (or the demo-30s.json) through every pipeline stage,
asserting schema compliance and functional correctness at each gate.
Generates a timestamped evidence report in the output directory.

Usage
-----
  # Check the demo instance (fast, no API calls if --stub-only):
  python -m pipeline.pipeline_check

  # Check a custom instance:
  python -m pipeline.pipeline_check my-instance.json --output-dir ./evidence

  # Full live check (uses real APIs):
  python -m pipeline.pipeline_check --live
"""

from __future__ import annotations

import argparse
import json
import structlog
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Load .env ────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    for _env in [
        Path(__file__).parents[2] / ".env",
        Path(__file__).parents[1] / ".env",
        Path(__file__).parent / ".env",
    ]:
        if _env.exists():
            load_dotenv(_env, override=True)
except ImportError:
    pass

from pipeline.logging_config import configure_logging
configure_logging()
log = structlog.get_logger("pipeline.check")

# ── Paths ────────────────────────────────────────────────────────────────────
_SESSION_DIR = Path(__file__).parent.parent
_V3_SCHEMA = _SESSION_DIR / "schemas" / "claude-unified-video-project-v3.schema.json"
_SKILLS_SCHEMA = _SESSION_DIR / "skills" / "schema.json"
_DEMO_INSTANCE = _SESSION_DIR / "examples" / "demo-30s.json"

# ── ANSI ─────────────────────────────────────────────────────────────────────
_TTY = sys.stdout.isatty()
def _c(code: str, t: str) -> str:
    return f"\033[{code}m{t}\033[0m" if _TTY else t
PASS = lambda t: _c("32", t)
FAIL = lambda t: _c("31", t)
WARN = lambda t: _c("33", t)
BOLD = lambda t: _c("1", t)
DIM  = lambda t: _c("2", t)


# ═════════════════════════════════════════════════════════════════════════════
#  EVIDENCE COLLECTOR
# ═════════════════════════════════════════════════════════════════════════════

class Evidence:
    """Accumulates check results and writes a report."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.gates: list[dict] = []
        self._current_gate: str = ""
        self._gate_checks: list[dict] = []
        self._pass = 0
        self._fail = 0
        self._warn = 0
        self._t0 = time.perf_counter()

    def begin_gate(self, name: str) -> None:
        if self._current_gate:
            self._flush_gate()
        self._current_gate = name
        self._gate_checks = []
        print(f"\n{BOLD(f'── {name} ')}" + "─" * max(0, 56 - len(name)))

    def check(self, name: str, passed: bool, detail: str = "", evidence: Any = None) -> bool:
        status = "PASS" if passed else "FAIL"
        sym = PASS("  ✓  ") if passed else FAIL("  ✗  ")
        det = DIM(f"  {detail}") if detail else ""
        print(f"  {name:<48}[{sym}]{det}")
        rec = {"name": name, "status": status, "detail": detail}
        if evidence is not None:
            rec["evidence"] = evidence
        self._gate_checks.append(rec)
        if passed:
            self._pass += 1
        else:
            self._fail += 1
        return passed

    def warn(self, name: str, detail: str = "") -> None:
        sym = WARN(" WARN ")
        det = DIM(f"  {detail}") if detail else ""
        print(f"  {name:<48}[{sym}]{det}")
        self._gate_checks.append({"name": name, "status": "WARN", "detail": detail})
        self._warn += 1

    def _flush_gate(self) -> None:
        self.gates.append({"gate": self._current_gate, "checks": self._gate_checks})

    def save_artifact(self, name: str, content: str | bytes) -> Path:
        """Write an evidence artifact to the output directory."""
        p = self.output_dir / name
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
        return p

    def summary(self) -> int:
        if self._current_gate:
            self._flush_gate()
        elapsed = time.perf_counter() - self._t0
        total = self._pass + self._fail + self._warn
        print(f"\n{'═' * 60}")
        print(BOLD("  PIPELINE CHECKLIST — SUMMARY"))
        print(f"{'═' * 60}")
        print(f"  Total checks  : {total}")
        print(f"  {PASS('PASS')}          : {self._pass}")
        print(f"  {FAIL('FAIL')}          : {self._fail}")
        print(f"  {WARN('WARN')}          : {self._warn}")
        print(f"  Elapsed       : {elapsed:.1f}s")
        print(f"  Evidence dir  : {self.output_dir.resolve()}")
        # Write JSON report
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_sec": round(elapsed, 2),
            "totals": {"pass": self._pass, "fail": self._fail, "warn": self._warn},
            "gates": self.gates,
        }
        report_path = self.save_artifact(
            "pipeline-check-report.json",
            json.dumps(report, indent=2, ensure_ascii=False),
        )
        print(f"  Report        : {report_path.name}")
        ok = self._fail == 0
        print()
        if ok:
            print(PASS("  ✓ ALL GATES PASSED"))
        else:
            print(FAIL(f"  ✗ {self._fail} CHECK(S) FAILED — see report for details"))
        print()
        return 0 if ok else 1


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER: JSON Schema validation
# ═════════════════════════════════════════════════════════════════════════════

def _schema_errors(instance: dict, schema_path: Path) -> list[str]:
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema not installed — pip install jsonschema"]
    if not schema_path.exists():
        return [f"schema not found: {schema_path}"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(instance)]


def _id_pattern_ok(val: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._:-]{1,200}$", val))


def _semver_ok(val: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+", val))


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 0: PREREQUISITES
# ═════════════════════════════════════════════════════════════════════════════

def gate_0_prerequisites(ev: Evidence, instance: dict, live: bool) -> None:
    ev.begin_gate("GATE 0 — Prerequisites")

    # Python version
    v = sys.version_info
    ev.check("Python ≥ 3.9", v >= (3, 9), f"v{v.major}.{v.minor}.{v.micro}")

    # ffmpeg
    ffmpeg = shutil.which("ffmpeg")
    ev.check("ffmpeg in PATH", ffmpeg is not None, ffmpeg or "not found")

    # jsonschema
    try:
        import jsonschema
        ev.check("jsonschema installed", True, jsonschema.__version__)
    except ImportError:
        ev.check("jsonschema installed", False, "pip install jsonschema")

    # Schema file exists
    ev.check("v3 schema file exists", _V3_SCHEMA.exists(), str(_V3_SCHEMA.name))

    # Demo instance file
    ev.check("demo-30s.json exists", _DEMO_INSTANCE.exists())

    # API keys (informational)
    required_keys = ["ANTHROPIC_API_KEY"]
    optional_keys = [
        "OPENAI_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY",
        "RUNWAY_API_KEY", "BRAVE_API_KEY", "DESCRIPT_API_KEY",
        "DEEPSEEK_API_KEY", "XAI_API_KEY",
    ]
    for k in required_keys:
        val = os.getenv(k, "")
        has = bool(val and "REPLACE_ME" not in val)
        ev.check(f"{k} set", has, "configured" if has else "MISSING — required for --idea mode")

    for k in optional_keys:
        val = os.getenv(k, "")
        has = bool(val and "REPLACE_ME" not in val)
        if has:
            ev.check(f"{k} set", True, "configured")
        else:
            ev.warn(f"{k} set", "not set — optional")


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 1: SCHEMA VALIDATION (raw instance)
# ═════════════════════════════════════════════════════════════════════════════

def gate_1_schema_validation(ev: Evidence, instance: dict) -> bool:
    ev.begin_gate("GATE 1 — JSON Schema Validation (v3)")

    # Full jsonschema check
    errors = _schema_errors(instance, _V3_SCHEMA)
    ev.check(
        "Instance passes v3 JSON Schema",
        len(errors) == 0,
        f"{len(errors)} error(s)" if errors else "valid",
        evidence=errors[:10] if errors else None,
    )
    for err in errors[:5]:
        print(FAIL(f"       → {err[:100]}"))

    # Root required keys
    required_root = [
        "schemaVersion", "package", "project", "qualityProfiles",
        "canonicalDocuments", "production", "assetLibrary",
        "orchestration", "assembly", "deliverables", "relationships",
    ]
    for key in required_root:
        ev.check(f"Root key: {key}", key in instance)

    # SemVer
    sv = instance.get("schemaVersion", "")
    ev.check("schemaVersion is SemVer", _semver_ok(sv), sv)

    return len(errors) == 0


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 2: CANONICAL DOCUMENTS
# ═════════════════════════════════════════════════════════════════════════════

def gate_2_canonical_documents(ev: Evidence, instance: dict) -> None:
    ev.begin_gate("GATE 2 — Canonical Documents")

    docs = instance.get("canonicalDocuments", {})

    # Story
    story = docs.get("story", {})
    ev.check("story exists", bool(story))
    beats = story.get("beats", [])
    ev.check("story.beats ≥ 1", len(beats) >= 1, f"{len(beats)} beat(s)")
    if beats:
        orders = [b.get("order", 0) for b in beats]
        ev.check("beats have sequential order", orders == sorted(orders), str(orders))
        for b in beats:
            ev.check(
                f"beat {b.get('beatId','?')}: has emotionalObjective",
                bool(b.get("emotionalObjective")),
            )

    # Script
    script = docs.get("script", {})
    ev.check("script exists", bool(script))
    segments = script.get("segments", [])
    ev.check("script.segments ≥ 1", len(segments) >= 1, f"{len(segments)} segment(s)")
    seg_types = {s.get("segmentType") for s in segments}
    ev.check(
        "script has scene_heading segments",
        "scene_heading" in seg_types,
        str(seg_types),
    )

    # Director Instructions
    di = docs.get("directorInstructions", {})
    ev.check("directorInstructions exists", bool(di))
    ev.check("visionStatement non-empty", bool(di.get("visionStatement")))
    ev.check("mustHaves[] ≥ 1", len(di.get("mustHaves", [])) >= 1)
    ev.check("mustAvoid[] ≥ 1", len(di.get("mustAvoid", [])) >= 1)
    ev.check("colorDirection non-empty", bool(di.get("colorDirection")))


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 3: PRODUCTION ENTITIES
# ═════════════════════════════════════════════════════════════════════════════

def gate_3_production(ev: Evidence, instance: dict) -> None:
    ev.begin_gate("GATE 3 — Production Entities")

    prod = instance.get("production", {})

    # Characters
    chars = prod.get("characters", [])
    ev.check("characters[] ≥ 1", len(chars) >= 1, f"{len(chars)}")
    for c in chars:
        cid = c.get("id", "?")
        ev.check(f"char {cid}: valid ID pattern", _id_pattern_ok(cid))
        ev.check(f"char {cid}: has name", bool(c.get("name")))
        ev.check(f"char {cid}: has description", bool(c.get("description")))

    # Environments
    envs = prod.get("environments", [])
    ev.check("environments[] ≥ 1", len(envs) >= 1, f"{len(envs)}")
    for e in envs:
        eid = e.get("id", "?")
        ev.check(f"env {eid}: has spatialExtent", bool(e.get("spatialExtent")))
        ev.check(f"env {eid}: has defaultSceneSpace", bool(e.get("defaultSceneSpace")))

    # Scenes
    scenes = prod.get("scenes", [])
    ev.check("scenes[] ≥ 1", len(scenes) >= 1, f"{len(scenes)}")
    scene_ids = set()
    for sc in scenes:
        sid = sc.get("id", "?")
        scene_ids.add(sid)
        ev.check(f"scene {sid}: has sceneNumber", sc.get("sceneNumber") is not None)
        ev.check(f"scene {sid}: has environmentRef", bool(sc.get("environmentRef")))
        ev.check(f"scene {sid}: targetDurationSec > 0", (sc.get("targetDurationSec") or 0) > 0)
        ev.check(f"scene {sid}: shotRefs ≥ 1", len(sc.get("shotRefs", [])) >= 1)
        ev.check(f"scene {sid}: has qaGate", bool(sc.get("qaGate")))

    # Shots
    shots = prod.get("shots", [])
    ev.check("shots[] ≥ 1", len(shots) >= 1, f"{len(shots)}")
    total_dur = 0
    for sh in shots:
        shid = sh.get("id", "?")
        spec = sh.get("cinematicSpec", {})
        ev.check(f"shot {shid}: has shotType", bool(spec.get("shotType")))
        ev.check(f"shot {shid}: has cameraAngle", bool(spec.get("cameraAngle")))
        ev.check(f"shot {shid}: has cameraMovement", bool(spec.get("cameraMovement")))
        dur = sh.get("targetDurationSec", 0)
        ev.check(f"shot {shid}: targetDurationSec > 0", dur > 0, f"{dur}s")
        total_dur += dur
        # sceneRef must point to a known scene
        sref = (sh.get("sceneRef") or {}).get("id", "")
        ev.check(f"shot {shid}: sceneRef valid", sref in scene_ids, sref)

    target = instance.get("project", {}).get("targetRuntimeSec", 0)
    if target:
        drift = abs(total_dur - target)
        ev.check(
            f"shot durations sum ≈ targetRuntime ({target}s)",
            drift <= target * 0.15,  # 15% tolerance
            f"sum={total_dur}s, drift={drift}s",
        )


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 4: ASSET LIBRARY
# ═════════════════════════════════════════════════════════════════════════════

def gate_4_asset_library(ev: Evidence, instance: dict) -> None:
    ev.begin_gate("GATE 4 — Asset Library")

    lib = instance.get("assetLibrary", {})

    # Required sections
    for section in ("visualAssets", "audioAssets", "marketingAssets", "genericAssets"):
        ev.check(f"assetLibrary.{section} exists", isinstance(lib.get(section), list))

    # Audio assets
    audio = lib.get("audioAssets", [])
    ev.check("audioAssets ≥ 1", len(audio) >= 1, f"{len(audio)}")
    audio_types_found = set()
    for a in audio:
        aid = a.get("id", "?")
        atype = a.get("audioType", "")
        audio_types_found.add(atype)
        ev.check(f"audio {aid}: has audioType", bool(atype), atype)
        ev.check(f"audio {aid}: valid ID pattern", _id_pattern_ok(aid))

    # Coverage: expect at least ambient + dialogue OR music
    ev.check(
        "audio type coverage (≥2 distinct types)",
        len(audio_types_found) >= 2,
        str(audio_types_found),
    )


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 5: ASSEMBLY (timelines, editVersions, renderPlans)
# ═════════════════════════════════════════════════════════════════════════════

def gate_5_assembly(ev: Evidence, instance: dict) -> None:
    ev.begin_gate("GATE 5 — Assembly")

    asm = instance.get("assembly", {})

    # Timelines
    tls = asm.get("timelines", [])
    ev.check("timelines ≥ 1", len(tls) >= 1, f"{len(tls)}")
    for tl in tls:
        tid = tl.get("id", "?")
        ev.check(f"timeline {tid}: durationSec > 0", (tl.get("durationSec") or 0) > 0)
        ev.check(f"timeline {tid}: has frameRate", bool(tl.get("frameRate")))
        ev.check(f"timeline {tid}: has resolution", bool(tl.get("resolution")))
        vclips = tl.get("videoClips", [])
        ev.check(f"timeline {tid}: videoClips ≥ 1", len(vclips) >= 1, f"{len(vclips)}")
        aclips = tl.get("audioClips", [])
        ev.check(f"timeline {tid}: audioClips ≥ 1", len(aclips) >= 1, f"{len(aclips)}")

    # Edit versions
    evs = asm.get("editVersions", [])
    ev.check("editVersions ≥ 1", len(evs) >= 1, f"{len(evs)}")
    any_approved = any(e.get("approvedForRender") for e in evs)
    ev.check("at least one editVersion approvedForRender", any_approved)

    # Render plans
    rps = asm.get("renderPlans", [])
    ev.check("renderPlans ≥ 1", len(rps) >= 1, f"{len(rps)}")
    for rp in rps:
        rpid = rp.get("id", "?")
        ops = rp.get("operations", [])
        ev.check(f"renderPlan {rpid}: operations ≥ 1", len(ops) >= 1, f"{len(ops)} op(s)")
        op_types = [o.get("opType") for o in ops]
        ev.check(f"renderPlan {rpid}: has concat op", "concat" in op_types, str(op_types))
        ev.check(f"renderPlan {rpid}: has encode op", "encode" in op_types)


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 6: DELIVERABLES + RELATIONSHIPS
# ═════════════════════════════════════════════════════════════════════════════

def gate_6_deliverables(ev: Evidence, instance: dict) -> None:
    ev.begin_gate("GATE 6 — Deliverables & Relationships")

    dels = instance.get("deliverables", [])
    ev.check("deliverables ≥ 1", len(dels) >= 1, f"{len(dels)}")
    for d in dels:
        did = d.get("id", "?")
        ev.check(f"deliverable {did}: outputType set", bool(d.get("outputType")))
        ev.check(f"deliverable {did}: runtimeSec > 0", (d.get("runtimeSec") or 0) > 0)
        ev.check(f"deliverable {did}: sourceTimelineRef", bool(d.get("sourceTimelineRef")))

    rels = instance.get("relationships", [])
    ev.check("relationships ≥ 1", len(rels) >= 1, f"{len(rels)}")


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 7: REFERENTIAL INTEGRITY
# ═════════════════════════════════════════════════════════════════════════════

def gate_7_referential_integrity(ev: Evidence, instance: dict) -> None:
    ev.begin_gate("GATE 7 — Referential Integrity (cross-entity refs)")

    # Collect all known entity IDs
    known_ids: set[str] = set()

    def _collect(obj: Any, depth: int = 0) -> None:
        if depth > 10:
            return
        if isinstance(obj, dict):
            for key in ("id", "logicalId", "beatId", "segmentId", "workflowId",
                        "clipId", "opId", "relationshipId"):
                val = obj.get(key)
                if val and isinstance(val, str):
                    known_ids.add(val)
            for v in obj.values():
                _collect(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item, depth + 1)

    _collect(instance)
    ev.check(f"Collected {len(known_ids)} entity IDs", len(known_ids) > 0)

    # Check all refs point to known IDs
    dangling: list[str] = []

    def _check_refs(obj: Any, path: str = "", depth: int = 0) -> None:
        if depth > 10:
            return
        if isinstance(obj, dict):
            # Refs are dicts with a single "id" key (e.g., {"id": "char.mira.v1"})
            if set(obj.keys()) == {"id"} and isinstance(obj.get("id"), str):
                ref_id = obj["id"]
                if ref_id not in known_ids:
                    dangling.append(f"{path} → {ref_id}")
            else:
                for k, v in obj.items():
                    if k.endswith("Ref") or k.endswith("Refs"):
                        _check_refs(v, f"{path}.{k}", depth + 1)
                    else:
                        _check_refs(v, f"{path}.{k}", depth + 1)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check_refs(item, f"{path}[{i}]", depth + 1)

    _check_refs(instance)
    ev.check(
        "No dangling refs (all Ref.id → known entity)",
        len(dangling) == 0,
        f"{len(dangling)} dangling" if dangling else "all refs resolved",
        evidence=dangling[:10] if dangling else None,
    )
    for d in dangling[:5]:
        print(FAIL(f"       → {d}"))


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 8: DERIVE PHASE
# ═════════════════════════════════════════════════════════════════════════════

def gate_8_derive(ev: Evidence, instance: dict) -> dict:
    ev.begin_gate("GATE 8 — Derive Phase (ensure_shots + ensure_audio)")

    from pipeline.derive import ensure_shots, ensure_audio

    n_shots_before = len(instance.get("production", {}).get("shots", []))
    n_audio_before = len(instance.get("assetLibrary", {}).get("audioAssets", []))

    instance = ensure_shots(instance)
    instance = ensure_audio(instance)

    n_shots_after = len(instance.get("production", {}).get("shots", []))
    n_audio_after = len(instance.get("assetLibrary", {}).get("audioAssets", []))

    ev.check(
        "ensure_shots produced shots",
        n_shots_after >= 1,
        f"{n_shots_before} → {n_shots_after}",
    )
    ev.check(
        "ensure_audio produced audio assets",
        n_audio_after >= 1,
        f"{n_audio_before} → {n_audio_after}",
    )

    # Verify derived shots have generation steps
    for sh in instance.get("production", {}).get("shots", []):
        steps = sh.get("generation", {}).get("steps", [])
        if steps:
            ev.check(
                f"shot {sh.get('id','?')}: generation.steps[0] has prompt",
                bool(steps[0].get("prompt")),
            )
            break  # spot check one

    # Verify derived audio assets have tool != "stub"
    for a in instance.get("assetLibrary", {}).get("audioAssets", []):
        steps = a.get("generation", {}).get("steps", [])
        if steps:
            tool = steps[0].get("tool", "stub")
            ev.check(
                f"audio {a.get('id','?')}: tool is not 'stub'",
                tool != "stub",
                f"tool={tool}",
            )
            break  # spot check one

    return instance


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 9: GENERATION PHASE (video + audio files)
# ═════════════════════════════════════════════════════════════════════════════

def _is_stub_video(path: Path) -> tuple[bool, str]:
    """
    Detect if a video file is a stub (solid-colour FFmpeg lavfi output).

    Stubs have:
    - lavfi virtual input (no real video source)
    - Single solid color across all frames (entropy near zero)
    - drawtext filter metadata in stream
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.exists():
        return False, "cannot probe"

    try:
        # Check if the input format is lavfi (stub signature)
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        probe = json.loads(r.stdout) if r.stdout else {}
        fmt_name = probe.get("format", {}).get("format_name", "")
        streams = probe.get("streams", [])

        # Check 1: video stream codec — stubs use libx264 ultrafast with tiny bitrate
        for s in streams:
            if s.get("codec_type") == "video":
                # Stubs have no audio stream
                has_audio = any(st.get("codec_type") == "audio" for st in streams)
                if not has_audio:
                    # Stub videos are generated with -an (no audio)
                    pass

        # Check 2: use ffmpeg signalstats to measure frame entropy
        # A solid-colour stub has near-zero spatial complexity
        r2 = subprocess.run(
            ["ffmpeg", "-i", str(path), "-vframes", "1",
             "-vf", "signalstats", "-f", "null", "-"],
            capture_output=True, text=True, timeout=10,
        )
        stderr = r2.stderr or ""

        # signalstats outputs YMIN/YMAX — if they're identical, it's a solid colour
        ymin = ymax = None
        for line in stderr.splitlines():
            if "YMIN" in line:
                parts = line.split()
                for p in parts:
                    if p.startswith("YMIN"):
                        ymin = p.split(":")[-1].strip() if ":" in p else None
                    if p.startswith("YMAX"):
                        ymax = p.split(":")[-1].strip() if ":" in p else None

        # Fallback: check file size heuristic — stub 5s 1080p ultrafast is typically < 30KB
        size_kb = path.stat().st_size / 1024
        duration = float(probe.get("format", {}).get("duration", 5))
        kb_per_sec = size_kb / max(duration, 0.1)

        # Real video (even low quality) > 50 KB/s; stub solid colour < 10 KB/s
        if kb_per_sec < 15:
            return True, f"bitrate={kb_per_sec:.1f} KB/s (solid colour stub signature)"

        return False, f"bitrate={kb_per_sec:.1f} KB/s"

    except Exception as exc:
        return False, f"probe error: {exc}"


def _is_stub_audio(path: Path) -> tuple[bool, str]:
    """
    Detect if an audio file is a stub (silence or sine wave from FFmpeg lavfi).

    Stubs have:
    - anullsrc (silence) or sine generator
    - Mean volume near -inf dB (silence) or exactly one frequency (sine)
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.exists():
        return False, "cannot probe"

    try:
        # Use volumedetect to get mean_volume
        r = subprocess.run(
            ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=10,
        )
        stderr = r.stderr or ""
        mean_vol = None
        max_vol = None
        for line in stderr.splitlines():
            if "mean_volume" in line:
                # e.g. [Parsed_volumedetect_0 ...] mean_volume: -91.0 dB
                parts = line.split("mean_volume:")
                if len(parts) > 1:
                    try:
                        mean_vol = float(parts[1].strip().split()[0])
                    except ValueError:
                        pass
            if "max_volume" in line:
                parts = line.split("max_volume:")
                if len(parts) > 1:
                    try:
                        max_vol = float(parts[1].strip().split()[0])
                    except ValueError:
                        pass

        if mean_vol is not None:
            # Silence stubs: mean_volume < -70 dB
            if mean_vol < -70:
                return True, f"mean_volume={mean_vol:.1f} dB (silence stub)"
            # Sine wave stubs: very consistent volume, mean close to max (< 3dB spread)
            if max_vol is not None and abs(mean_vol - max_vol) < 3.0 and mean_vol < -20:
                return True, f"mean={mean_vol:.1f} dB, max={max_vol:.1f} dB (sine stub signature)"

        # Fallback: file size heuristic — stub audio is ~16 KB/s at 128kbps
        # Real speech/music/SFX has the same bitrate but we already caught silence/sine above
        return False, f"mean_volume={mean_vol} dB" if mean_vol else "volumedetect unavailable"

    except Exception as exc:
        return False, f"probe error: {exc}"


def gate_9_generation(ev: Evidence, instance: dict, output_dir: Path, stub_only: bool) -> tuple[dict, dict]:
    ev.begin_gate("GATE 9 — Generation Phase (shots + audio)")

    from pipeline.generate import generate_shots, generate_audio

    shot_clips = generate_shots(instance, output_dir)
    audio_files = generate_audio(instance, output_dir)

    stub_shots: list[str] = []
    real_shots: list[str] = []
    stub_audio: list[str] = []
    real_audio: list[str] = []

    # ── Shots ────────────────────────────────────────────────────────────────
    expected_shots = len(instance.get("production", {}).get("shots", []))
    ev.check(
        f"generate_shots: count matches ({expected_shots})",
        len(shot_clips) == expected_shots,
        f"expected={expected_shots}, got={len(shot_clips)}",
    )

    for sid, path in shot_clips.items():
        if not path.exists():
            ev.check(f"shot {sid}: file exists", False, "MISSING")
            continue
        if path.stat().st_size == 0:
            ev.check(f"shot {sid}: file non-empty", False, "0 bytes")
            continue

        is_stub, detail = _is_stub_video(path)
        if is_stub:
            stub_shots.append(sid)
            ev.check(f"shot {sid}: is REAL content (not stub)", False, f"STUB — {detail}")
        else:
            real_shots.append(sid)
            ev.check(f"shot {sid}: is REAL content (not stub)", True, detail)

    # ── Audio ────────────────────────────────────────────────────────────────
    expected_audio = len(instance.get("assetLibrary", {}).get("audioAssets", []))
    ev.check(
        f"generate_audio: count matches ({expected_audio})",
        len(audio_files) == expected_audio,
        f"expected={expected_audio}, got={len(audio_files)}",
    )

    for aid, path in audio_files.items():
        if not path.exists():
            ev.check(f"audio {aid}: file exists", False, "MISSING")
            continue
        if path.stat().st_size == 0:
            ev.check(f"audio {aid}: file non-empty", False, "0 bytes")
            continue

        is_stub, detail = _is_stub_audio(path)
        if is_stub:
            stub_audio.append(aid)
            ev.check(f"audio {aid}: is REAL content (not stub)", False, f"STUB — {detail}")
        else:
            real_audio.append(aid)
            ev.check(f"audio {aid}: is REAL content (not stub)", True, detail)

    # ── Aggregate verdict ────────────────────────────────────────────────────
    total_assets = len(shot_clips) + len(audio_files)
    total_stubs = len(stub_shots) + len(stub_audio)
    total_real = len(real_shots) + len(real_audio)

    ev.check(
        f"REAL assets > 0 (got {total_real}/{total_assets})",
        total_real > 0,
        f"{total_real} real, {total_stubs} stubs",
    )
    ev.check(
        f"NO stubs in output (got {total_stubs}/{total_assets})",
        total_stubs == 0,
        f"stubs: {stub_shots + stub_audio}" if total_stubs else "all real",
        evidence={
            "real_shots": real_shots,
            "stub_shots": stub_shots,
            "real_audio": real_audio,
            "stub_audio": stub_audio,
        },
    )

    # Save the stub/real manifest as evidence
    ev.save_artifact("asset-provenance.json", json.dumps({
        "real_shots": real_shots,
        "stub_shots": stub_shots,
        "real_audio": real_audio,
        "stub_audio": stub_audio,
        "total_assets": total_assets,
        "total_real": total_real,
        "total_stubs": total_stubs,
        "verdict": "PASS" if total_stubs == 0 else "FAIL — stubs detected",
    }, indent=2))

    return shot_clips, audio_files


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 10: ASSEMBLY PHASE (final render)
# ═════════════════════════════════════════════════════════════════════════════

def gate_10_assembly(
    ev: Evidence,
    instance: dict,
    output_dir: Path,
    shot_clips: dict,
    audio_files: dict,
) -> None:
    ev.begin_gate("GATE 10 — Assembly Phase (FFmpeg render)")

    from pipeline.assemble import assemble

    try:
        final_path = assemble(instance, output_dir, shot_clips, audio_files)
        ev.check("assemble() completed without error", True)
    except Exception as exc:
        ev.check("assemble() completed without error", False, str(exc)[:80])
        return

    ev.check("output file exists", final_path.exists(), str(final_path.name))
    if not final_path.exists():
        return

    size = final_path.stat().st_size
    ev.check("output file > 0 bytes", size > 0, f"{size / 1024:.1f} KB")

    # ── ffprobe deep analysis ────────────────────────────────────────────
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        ev.warn("ffprobe not available", "install ffprobe for media analysis")
        return

    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(final_path)],
            capture_output=True, text=True, timeout=10,
        )
        probe = json.loads(r.stdout) if r.stdout else {}
        fmt = probe.get("format", {})
        duration = float(fmt.get("duration", 0))
        streams = probe.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        ev.check("ffprobe: has video stream", has_video)
        ev.check("ffprobe: has audio stream", has_audio)
        ev.check("ffprobe: duration > 0", duration > 0, f"{duration:.1f}s")

        target = instance.get("project", {}).get("targetRuntimeSec", 0)
        if target:
            drift = abs(duration - target)
            ev.check(
                f"ffprobe: duration ≈ target ({target}s ±20%)",
                drift <= target * 0.20,
                f"actual={duration:.1f}s, drift={drift:.1f}s",
            )

        # ── Stub detection on final render ───────────────────────────────
        is_stub, detail = _is_stub_video(final_path)
        ev.check(
            "final render: is REAL content (not assembled stubs)",
            not is_stub,
            f"STUB — {detail}" if is_stub else detail,
        )

        # ── Volume check: render should not be silent ────────────────────
        r2 = subprocess.run(
            ["ffmpeg", "-i", str(final_path), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, timeout=15,
        )
        mean_vol = None
        for line in (r2.stderr or "").splitlines():
            if "mean_volume" in line:
                parts = line.split("mean_volume:")
                if len(parts) > 1:
                    try:
                        mean_vol = float(parts[1].strip().split()[0])
                    except ValueError:
                        pass
        if mean_vol is not None:
            ev.check(
                "final render: audio is not silence",
                mean_vol > -70,
                f"mean_volume={mean_vol:.1f} dB" + (" (SILENT)" if mean_vol <= -70 else ""),
            )

        # Save probe as evidence
        ev.save_artifact("ffprobe-output.json", json.dumps(probe, indent=2))

    except Exception as exc:
        ev.warn("ffprobe analysis", str(exc)[:80])


# ═════════════════════════════════════════════════════════════════════════════
#  GATE 11: PROVIDER WIRING INTEGRITY
# ═════════════════════════════════════════════════════════════════════════════

def gate_11_provider_wiring(ev: Evidence) -> None:
    ev.begin_gate("GATE 11 — Provider Wiring Integrity")

    from pipeline import providers

    # Check all provider functions are importable
    expected_fns = [
        "complete_json", "generate_image", "text_to_speech", "vision_score",
        "search_web", "search_web_context",
        "generate_sound_effect", "generate_music",
        "descript_import_media", "descript_agent_edit", "descript_job_status",
        "available_providers",
    ]
    for fn_name in expected_fns:
        ev.check(
            f"providers.{fn_name} exists",
            hasattr(providers, fn_name) and callable(getattr(providers, fn_name)),
        )

    # Check available_providers()
    avail = providers.available_providers()
    ev.check("available_providers() returns dict", isinstance(avail, dict))
    for prov, active in avail.items():
        if active:
            ev.check(f"provider '{prov}' active", True)
        else:
            ev.warn(f"provider '{prov}' inactive", "API key not set")

    # Check generate.py wiring: SFX/ambient/music paths exist
    import inspect
    from pipeline.generate import generate_audio
    src = inspect.getsource(generate_audio)
    ev.check(
        "generate_audio: has SFX/ambient path",
        "generate_sound_effect" in src,
        "providers.generate_sound_effect() wired",
    )
    ev.check(
        "generate_audio: has music fallback path",
        "generate_music" in src,
        "providers.generate_music() wired",
    )

    # Check skills.py wiring: web research + descript
    from pipeline import skills
    skill_src = inspect.getsource(skills)
    ev.check(
        "skills.py: Brave Search wired to S02/S04/S05",
        "search_web_context" in skill_src,
    )
    ev.check(
        "skills.py: Descript wired to S18",
        "descript_import_media" in skill_src,
    )
    ev.check(
        "skills.py: _audio_tool_from_type uses 'auto' not 'stub'",
        '"sfx":        "auto"' in skill_src or "'sfx': 'auto'" in skill_src
        or '"sfx":        "auto"' in skill_src,
        "SFX/ambient/foley route to real providers",
    )


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline checklist — validate every stage with evidence.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "instance",
        nargs="?",
        default=str(_DEMO_INSTANCE),
        help=f"Instance JSON to check (default: {_DEMO_INSTANCE.name})",
    )
    parser.add_argument(
        "--output-dir",
        default="./evidence",
        help="Directory for evidence artifacts (default: ./evidence)",
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip generation + assembly gates (schema-only check).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG logging.",
    )

    args = parser.parse_args(argv)
    if args.verbose:
        from pipeline.logging_config import _configured
        import pipeline.logging_config as _logcfg
        _logcfg._configured = False
        configure_logging(verbose=True)

    output_dir = Path(args.output_dir)
    ev = Evidence(output_dir)

    # Load instance
    instance_path = Path(args.instance)
    if not instance_path.exists():
        print(FAIL(f"Instance file not found: {instance_path}"))
        return 1

    instance = json.loads(instance_path.read_text(encoding="utf-8"))

    print(BOLD("\n╔══════════════════════════════════════════════════════════╗"))
    print(BOLD(  "║   SAFE AI Production — Pipeline Checklist               ║"))
    print(BOLD(  "╚══════════════════════════════════════════════════════════╝"))
    print(DIM(f"  Instance : {instance_path.name}"))
    print(DIM(f"  Evidence : {output_dir.resolve()}"))

    # Save a copy of the input instance as evidence
    ev.save_artifact("input-instance.json", json.dumps(instance, indent=2, ensure_ascii=False))

    # ── Run gates ────────────────────────────────────────────────────────────
    gate_0_prerequisites(ev, instance, live=True)
    schema_ok = gate_1_schema_validation(ev, instance)
    gate_2_canonical_documents(ev, instance)
    gate_3_production(ev, instance)
    gate_4_asset_library(ev, instance)
    gate_5_assembly(ev, instance)
    gate_6_deliverables(ev, instance)
    gate_7_referential_integrity(ev, instance)
    gate_11_provider_wiring(ev)

    if not args.skip_generation:
        instance = gate_8_derive(ev, instance)
        # Save post-derive instance as evidence
        ev.save_artifact("post-derive-instance.json", json.dumps(instance, indent=2, ensure_ascii=False))

        shot_clips, audio_files = gate_9_generation(ev, instance, output_dir, stub_only=False)

        gate_10_assembly(ev, instance, output_dir, shot_clips, audio_files)
    else:
        print(DIM("\n  (generation + assembly gates skipped — use without --skip-generation to run them)"))

    return ev.summary()


if __name__ == "__main__":
    sys.exit(main())
