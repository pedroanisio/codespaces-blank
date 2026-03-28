#!/usr/bin/env python3
"""
organize.py — Session-02 subfolder structure inspector and move proposer.

Inspects all files in session-02/, classifies each one against a set of
formally defined subfolder categories, and proposes moves. Does NOT execute
any moves unless --apply is passed.

Usage:
    python organize.py                   # inspect & propose (dry run)
    python organize.py --apply           # execute proposed moves
    python organize.py --json            # output proposals as JSON
    python organize.py -v                # verbose: show classification reasoning
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Callable


# ═══════════════════════════════════════════════════════════════════════════
# 1. FORMAL SUBFOLDER DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SubfolderDef:
    """Formal definition of a target subfolder."""

    name: str
    """Directory name relative to session-02/."""

    description: str
    """What this folder holds — its raison d'être."""

    criteria: list[str]
    """
    Human-readable classification criteria.
    A file belongs here if it satisfies ANY of these criteria.
    """

    match: Callable[[Path, FileInfo], bool]
    """
    Programmatic classifier: returns True if *file* belongs in this folder.
    Receives the file path and a FileInfo with pre-computed metadata.
    """

    priority: int = 0
    """
    When a file matches multiple folders, higher priority wins.
    Default 0 — first match in definition order breaks ties at equal priority.
    """


@dataclass
class FileInfo:
    """Pre-computed metadata about a file, used by classifiers."""

    path: Path
    name: str
    stem: str
    suffix: str
    size: int
    first_lines: str  # first ~512 bytes as text (empty if binary)

    # derived flags
    is_json: bool = False
    is_markdown: bool = False
    is_python: bool = False
    is_html: bool = False
    is_spreadsheet: bool = False

    # content-sniffed flags (set after loading first_lines)
    looks_like_json_schema: bool = False
    looks_like_instance: bool = False
    looks_like_prompt: bool = False
    looks_like_report: bool = False


# ── helpers for match functions ───────────────────────────────────────────

def _sniff(info: FileInfo) -> None:
    """Populate content-sniffed flags from first_lines."""
    fl = info.first_lines.lower()

    # JSON Schema detection
    if info.is_json:
        info.looks_like_json_schema = any(k in fl for k in (
            '"$schema"', '"$id"', '"type":', '"properties":', '"definitions":',
            '"$defs":', '"jsonschema"',
        ))
        info.looks_like_instance = not info.looks_like_json_schema and any(k in fl for k in (
            '"schemaversion"', '"schema_version"', '"format_id"',
            '"project"', '"package"', '"variant"',
        ))

    # Markdown prompt detection
    if info.is_markdown:
        info.looks_like_prompt = any(k in fl for k in (
            'propose a', 'design a', 'generate a', 'create a',
            'the schema must', 'you are', 'your task',
            'prompt', 'instruction',
        ))
        info.looks_like_report = any(k in fl for k in (
            'report', 'scorecard', 'answer:', 'review',
            'analysis', 'evaluation', 'findings',
        ))


# ── classifier functions ─────────────────────────────────────────────────

def _is_schema(p: Path, info: FileInfo) -> bool:
    """JSON Schema files: formal type definitions."""
    if info.suffix == '.json' and info.looks_like_json_schema:
        return True
    if info.suffix == '.json' and 'schema' in info.stem.lower():
        return True
    if info.suffix == '.json' and 'term-map' in info.stem.lower():
        return True
    return False


def _is_spec(p: Path, info: FileInfo) -> bool:
    """Schema specifications and documentation in markdown."""
    if not info.is_markdown:
        return False
    stem = info.stem.lower()
    if any(k in stem for k in ('schema', 'spec', 'extension', 'unified', 'orchestration')):
        return True
    if any(k in stem for k in ('guide',)) and 'schema' in info.first_lines.lower():
        return True
    return False


def _is_style(p: Path, info: FileInfo) -> bool:
    """Style guides, taxonomies, and creative references."""
    if not info.is_markdown:
        return False
    stem = info.stem.lower()
    return any(k in stem for k in ('style', 'taxonomy', '20-styles', 'camera', 'scene', 'video-v'))


def _is_report(p: Path, info: FileInfo) -> bool:
    """Analysis reports, scorecards, evaluations."""
    if not info.is_markdown:
        return False
    stem = info.stem.lower()
    if any(k in stem for k in ('report', 'scorecard')):
        return True
    if info.looks_like_report and not info.looks_like_prompt:
        return True
    return False


def _is_research(p: Path, info: FileInfo) -> bool:
    """External research, scraped content, third-party artifacts."""
    stem = info.stem.lower()
    # Files prefixed with external tool names (perplexity, chatgpt, grok, manus)
    external_prefixes = ('perplexity-', 'grok-', 'manus-')
    if any(stem.startswith(px) for px in external_prefixes):
        return True
    # HTML artifacts (sitemaps, term maps rendered as HTML)
    if info.is_html:
        return True
    # Spreadsheets
    if info.is_spreadsheet:
        return True
    return False


def _is_prompt(p: Path, info: FileInfo) -> bool:
    """Prompt templates used to drive LLM generation."""
    if not info.is_markdown:
        return False
    stem = info.stem.lower()
    if stem.startswith('prompt-'):
        return True
    if info.looks_like_prompt and not info.looks_like_report:
        # Only if filename also hints at prompt
        if 'prompt' in stem or 'instruction' in stem:
            return True
    return False


def _is_example(p: Path, info: FileInfo) -> bool:
    """Instance data, demos, example project files."""
    if not info.is_json:
        return False
    if info.looks_like_json_schema:
        return False
    stem = info.stem.lower()
    if any(k in stem for k in ('demo', 'example', 'instance', 'spec-instance')):
        return True
    if info.looks_like_instance and not info.looks_like_json_schema:
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# 2. SUBFOLDER REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

SUBFOLDERS: list[SubfolderDef] = [
    SubfolderDef(
        name="schemas",
        description=(
            "Machine-readable JSON Schema files that define the canonical data "
            "contracts for video projects, spatial extensions, and term maps. "
            "These are the single source of truth for validation."
        ),
        criteria=[
            "File is JSON and contains $schema, $id, or top-level 'properties'/'definitions'",
            "Filename contains 'schema' (e.g. *schema*.json)",
            "File is a JSON term map or vocabulary definition (e.g. term-map.json)",
        ],
        match=_is_schema,
        priority=10,
    ),
    SubfolderDef(
        name="docs/specs",
        description=(
            "Human-readable markdown documents that explain, narrate, or specify "
            "the schemas. Includes schema guides, extension specs, and unified "
            "schema narratives. These accompany — but do not replace — the "
            "machine-readable schemas."
        ),
        criteria=[
            "Markdown file whose stem contains 'schema', 'spec', 'extension', 'unified', or 'orchestration'",
            "Markdown file that discusses a schema (detected via content sniffing) and has 'guide' in the name",
        ],
        match=_is_spec,
        priority=5,
    ),
    SubfolderDef(
        name="docs/styles",
        description=(
            "Style guides, visual taxonomies, and creative reference catalogs. "
            "Defines the aesthetic vocabulary: animation styles, camera movements, "
            "scene compositions, and video styles."
        ),
        criteria=[
            "Markdown file whose stem contains 'style', 'taxonomy', '20-styles', 'camera', 'scene', or 'video-v'",
        ],
        match=_is_style,
        priority=5,
    ),
    SubfolderDef(
        name="docs/reports",
        description=(
            "Analysis outputs, evaluation scorecards, and skill reports. "
            "These are generated or authored assessments of schemas, pipelines, "
            "or skill definitions."
        ),
        criteria=[
            "Markdown file whose stem contains 'report' or 'scorecard'",
            "Markdown file whose content begins with report/analysis/evaluation language",
        ],
        match=_is_report,
        priority=4,
    ),
    SubfolderDef(
        name="research",
        description=(
            "Artifacts sourced from external tools or platforms: Perplexity "
            "research, Grok schema drafts, Manus orchestration docs, ChatGPT "
            "generated schemas, scraped HTML sitemaps, and spreadsheets. "
            "These are inputs to the project, not authored outputs."
        ),
        criteria=[
            "Filename starts with an external tool prefix (perplexity-, grok-, manus-)",
            "File is HTML (sitemaps, rendered term maps)",
            "File is a spreadsheet (.xlsx, .xls, .csv)",
        ],
        match=_is_research,
        priority=8,
    ),
    SubfolderDef(
        name="prompts",
        description=(
            "Prompt templates and instruction documents used to drive LLM "
            "generation passes. These are reusable inputs that define what "
            "an LLM should produce."
        ),
        criteria=[
            "Markdown file whose stem starts with 'prompt-'",
            "Markdown file with prompt/instruction content AND 'prompt' or 'instruction' in filename",
        ],
        match=_is_prompt,
        priority=6,
    ),
    SubfolderDef(
        name="examples",
        description=(
            "Concrete instance JSON files: demos, example projects, and "
            "Hollywood-spec instances. These are valid (or draft) instances "
            "of the schemas — test fixtures and reference data."
        ),
        criteria=[
            "JSON file that is NOT a schema (no $schema/$id/properties at top level)",
            "Filename contains 'demo', 'example', 'instance', or 'spec-instance'",
            "JSON file with schemaVersion/schema_version/format_id at top level (instance marker)",
        ],
        match=_is_example,
        priority=3,
    ),
]

# Folders that are already organized — skip them entirely
SKIP_DIRS = {'skills', 'pipeline', 'tests', 'output', '.pytest_cache', '__pycache__'}

# Files that should stay at the root of session-02/
ROOT_KEEP = {'README.md', 'CHANGELOG.md', '.env', 'validate.py', 'check_env.py', 'organize.py'}


# ═══════════════════════════════════════════════════════════════════════════
# 3. INSPECTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MoveProposal:
    """A proposed file move."""
    source: str           # relative to session-02/
    target: str           # relative to session-02/
    folder_name: str      # which SubfolderDef matched
    reasons: list[str]    # which criteria matched
    confidence: str       # "high" | "medium" | "low"


def _load_file_info(path: Path) -> FileInfo:
    """Build a FileInfo for a single file."""
    suffix = path.suffix.lower()
    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    first_lines = ""
    if suffix in ('.json', '.md', '.html', '.py', '.txt', '.csv'):
        try:
            first_lines = path.read_text(encoding="utf-8", errors="replace")[:512]
        except OSError:
            pass

    info = FileInfo(
        path=path,
        name=path.name,
        stem=path.stem,
        suffix=suffix,
        size=size,
        first_lines=first_lines,
        is_json=(suffix == '.json'),
        is_markdown=(suffix == '.md'),
        is_python=(suffix == '.py'),
        is_html=(suffix in ('.html', '.htm')),
        is_spreadsheet=(suffix in ('.xlsx', '.xls', '.csv')),
    )
    _sniff(info)
    return info


def inspect(session_dir: Path, *, verbose: bool = False) -> list[MoveProposal]:
    """
    Walk session_dir, classify each file, return a list of MoveProposals.

    Files inside SKIP_DIRS and ROOT_KEEP are excluded.
    """
    proposals: list[MoveProposal] = []

    for entry in sorted(session_dir.iterdir()):
        # Skip directories that are already organized
        if entry.is_dir() and entry.name in SKIP_DIRS:
            continue
        # Skip hidden dirs/files (except .env which is in ROOT_KEEP)
        if entry.name.startswith('.') and entry.name not in ROOT_KEEP:
            continue
        # Only process files at the top level
        if not entry.is_file():
            continue
        # Skip files that belong at root
        if entry.name in ROOT_KEEP:
            continue

        info = _load_file_info(entry)

        # Run classifiers — collect all matches, pick highest priority
        matches: list[tuple[SubfolderDef, list[str]]] = []

        for folder_def in SUBFOLDERS:
            if folder_def.match(entry, info):
                # Determine which criteria matched (for reporting)
                matched_criteria = _explain_match(entry, info, folder_def)
                matches.append((folder_def, matched_criteria))

        if not matches:
            if verbose:
                print(f"  [SKIP] {entry.name} — no classifier matched")
            continue

        # Pick best match by priority (then definition order)
        matches.sort(key=lambda m: -m[0].priority)
        best_folder, reasons = matches[0]

        # Confidence heuristic
        if len(matches) == 1:
            confidence = "high"
        elif matches[0][0].priority > matches[1][0].priority:
            confidence = "high"
        else:
            confidence = "medium"

        rel_source = entry.name
        rel_target = f"{best_folder.name}/{entry.name}"

        proposals.append(MoveProposal(
            source=rel_source,
            target=rel_target,
            folder_name=best_folder.name,
            reasons=reasons,
            confidence=confidence,
        ))

    return proposals


def _explain_match(path: Path, info: FileInfo, folder_def: SubfolderDef) -> list[str]:
    """Return human-readable reasons why this file matched this folder."""
    reasons = []
    stem = info.stem.lower()
    name = info.name.lower()

    if folder_def.name == "schemas":
        if info.looks_like_json_schema:
            reasons.append("JSON content contains $schema / $id / properties (JSON Schema)")
        if 'schema' in stem:
            reasons.append(f"Filename contains 'schema': {info.name}")
        if 'term-map' in stem:
            reasons.append(f"Filename is a term map: {info.name}")

    elif folder_def.name == "docs/specs":
        for kw in ('schema', 'spec', 'extension', 'unified', 'orchestration'):
            if kw in stem:
                reasons.append(f"Stem contains '{kw}'")
        if 'guide' in stem:
            reasons.append("Stem contains 'guide' + schema content detected")

    elif folder_def.name == "docs/styles":
        for kw in ('style', 'taxonomy', '20-styles', 'camera', 'scene', 'video-v'):
            if kw in stem:
                reasons.append(f"Stem contains '{kw}'")

    elif folder_def.name == "docs/reports":
        for kw in ('report', 'scorecard'):
            if kw in stem:
                reasons.append(f"Stem contains '{kw}'")
        if info.looks_like_report:
            reasons.append("Content detected as report/analysis")

    elif folder_def.name == "research":
        for px in ('perplexity-', 'grok-', 'manus-'):
            if stem.startswith(px.rstrip('-')):
                reasons.append(f"External tool prefix: '{px}'")
        if info.is_html:
            reasons.append("HTML file (scraped / rendered artifact)")
        if info.is_spreadsheet:
            reasons.append(f"Spreadsheet: {info.suffix}")

    elif folder_def.name == "prompts":
        if stem.startswith('prompt-'):
            reasons.append("Filename starts with 'prompt-'")
        if info.looks_like_prompt:
            reasons.append("Content detected as prompt/instruction template")

    elif folder_def.name == "examples":
        if info.looks_like_instance:
            reasons.append("JSON contains instance markers (schemaVersion / format_id)")
        for kw in ('demo', 'example', 'instance', 'spec-instance'):
            if kw in stem:
                reasons.append(f"Filename contains '{kw}'")

    return reasons or ["Matched classifier (no specific reason extracted)"]


# ═══════════════════════════════════════════════════════════════════════════
# 4. DISPLAY AND APPLY
# ═══════════════════════════════════════════════════════════════════════════

def print_definitions() -> None:
    """Print the formal subfolder definitions."""
    print("\n" + "=" * 70)
    print("  SUBFOLDER DEFINITIONS")
    print("=" * 70)
    for sd in SUBFOLDERS:
        print(f"\n  {sd.name}/")
        print(f"  {'─' * len(sd.name)}──")
        # Wrap description at ~66 chars
        desc = sd.description
        while desc:
            line = desc[:66]
            cut = line.rfind(' ') if len(desc) > 66 else len(line)
            if cut <= 0:
                cut = len(line)
            print(f"    {desc[:cut].strip()}")
            desc = desc[cut:].strip()
        print(f"    Priority: {sd.priority}")
        print(f"    Criteria:")
        for c in sd.criteria:
            print(f"      • {c}")


def print_proposals(proposals: list[MoveProposal], *, verbose: bool = False) -> None:
    """Pretty-print the proposed moves."""
    if not proposals:
        print("\n  No files need moving — everything is already organized.")
        return

    print(f"\n{'=' * 70}")
    print(f"  PROPOSED MOVES ({len(proposals)} files)")
    print(f"{'=' * 70}")

    # Group by target folder
    by_folder: dict[str, list[MoveProposal]] = {}
    for p in proposals:
        by_folder.setdefault(p.folder_name, []).append(p)

    for folder_name, folder_proposals in sorted(by_folder.items()):
        print(f"\n  → {folder_name}/")
        for p in folder_proposals:
            tag = f"[{p.confidence.upper():6}]"
            print(f"    {tag}  {p.source}")
            if verbose:
                for r in p.reasons:
                    print(f"             ↳ {r}")

    # Summary
    print(f"\n{'─' * 70}")
    high = sum(1 for p in proposals if p.confidence == "high")
    med = sum(1 for p in proposals if p.confidence == "medium")
    low = sum(1 for p in proposals if p.confidence == "low")
    print(f"  Summary: {len(proposals)} file(s) to move")
    print(f"    high confidence : {high}")
    print(f"    medium          : {med}")
    print(f"    low             : {low}")
    print(f"\n  Run with --apply to execute these moves.")
    print(f"  Run with -v for classification reasoning.\n")


def apply_moves(session_dir: Path, proposals: list[MoveProposal]) -> int:
    """Execute the proposed moves. Returns count of files moved."""
    moved = 0
    for p in proposals:
        src = session_dir / p.source
        dst = session_dir / p.target

        if not src.exists():
            print(f"  [SKIP] {p.source} — source not found")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            print(f"  [SKIP] {p.source} — target already exists: {p.target}")
            continue

        shutil.move(str(src), str(dst))
        print(f"  [MOVED] {p.source} → {p.target}")
        moved += 1

    return moved


# ═══════════════════════════════════════════════════════════════════════════
# 5. CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect session-02/ files and propose subfolder organization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python organize.py              # show definitions + proposals (dry run)
  python organize.py -v           # verbose: include classification reasons
  python organize.py --json       # output proposals as JSON
  python organize.py --apply      # execute the moves
  python organize.py --defs-only  # just print subfolder definitions
""",
    )
    parser.add_argument("--apply", action="store_true",
                        help="Execute the proposed moves (default: dry run).")
    parser.add_argument("--json", action="store_true",
                        help="Output proposals as JSON instead of human-readable text.")
    parser.add_argument("--defs-only", action="store_true",
                        help="Only print subfolder definitions, do not inspect files.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show classification reasoning for each file.")
    parser.add_argument("--dir", type=Path, default=Path(__file__).parent,
                        help="Session directory to inspect (default: script's parent).")

    args = parser.parse_args()
    session_dir = args.dir.resolve()

    if not session_dir.is_dir():
        print(f"ERROR: Not a directory: {session_dir}", file=sys.stderr)
        return 1

    # ── Definitions ───────────────────────────────────────────────────────
    if not args.json:
        print_definitions()

    if args.defs_only:
        return 0

    # ── Inspect ───────────────────────────────────────────────────────────
    proposals = inspect(session_dir, verbose=args.verbose)

    # ── Output ────────────────────────────────────────────────────────────
    if args.json:
        out = {
            "session_dir": str(session_dir),
            "definitions": [
                {
                    "name": sd.name,
                    "description": sd.description,
                    "criteria": sd.criteria,
                    "priority": sd.priority,
                }
                for sd in SUBFOLDERS
            ],
            "proposals": [asdict(p) for p in proposals],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print_proposals(proposals, verbose=args.verbose)

    # ── Apply ─────────────────────────────────────────────────────────────
    if args.apply:
        print(f"\n{'=' * 70}")
        print(f"  APPLYING MOVES")
        print(f"{'=' * 70}\n")
        moved = apply_moves(session_dir, proposals)
        print(f"\n  Done: {moved}/{len(proposals)} file(s) moved.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
