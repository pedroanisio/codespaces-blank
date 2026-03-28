#!/usr/bin/env python3
r"""
organize.py — General-purpose declarative directory organizer.
═══════════════════════════════════════════════════════════════

.. note:: This file follows the Embedded Self-Documentation (ESD) pattern.
   See concepts/embedded-self-documentation.md for the structural contract.

A single-file, zero-dependency* tool that classifies loose files in a
directory and moves them into subfolders based on declarative YAML/JSON rules.

(*) PyYAML is optional — JSON configs work without it.

────────────────────────────────────────────────────────────────────────
TABLE OF CONTENTS
────────────────────────────────────────────────────────────────────────

  1. Quick Start
  2. CLI Reference
  3. Config File Format
     3.1 settings
     3.2 folders (rules)
  4. Rule Types (complete reference)
  5. Rule Modes: "any" vs "all"
  6. Rule Negation
  7. Multiple Folder Entries & Priority
  8. Confidence Levels
  9. Config Discovery
 10. Starter Config (--init)
 11. JSON Output (--json)
 12. Running from Another Directory
 13. Examples
     13.1 Minimal config
     13.2 Real-world: session-02 video production
     13.3 Content-based classification
     13.4 Combining AND + OR groups
 14. Internals & Extension Points
 15. Limitations

────────────────────────────────────────────────────────────────────────
1. QUICK START
────────────────────────────────────────────────────────────────────────

  # Generate a starter config in the current directory:
  python tools/organize.py --init

  # Edit organize.yaml to define your folders and rules, then:
  python tools/organize.py                    # dry run — preview moves
  python tools/organize.py -v                 # dry run with rule reasoning
  python tools/organize.py --apply            # execute the moves

  # Use a config from a different location:
  python tools/organize.py -c path/to/rules.yaml --dir path/to/target/

────────────────────────────────────────────────────────────────────────
2. CLI REFERENCE
────────────────────────────────────────────────────────────────────────

  python organize.py [OPTIONS]

  Options:
    -c, --config PATH   Path to YAML or JSON config file.
                         Default: auto-discover organize.yaml / .yml / .json
                         in the scan directory.

    --dir PATH          Directory to organize.
                         Default: current working directory.

    --apply             Execute proposed moves (default is dry-run).
                         Moves are never destructive — if the target file
                         already exists, the move is skipped.

    --json              Output proposals as machine-readable JSON to stdout.
                         Suppresses all human-readable output.

    --init              Generate a commented starter organize.yaml in --dir.
                         Will not overwrite an existing file.

    --defs-only         Print parsed folder definitions and exit — useful to
                         verify a config without scanning files.

    -v, --verbose       Show which rules matched for each file and which
                         files were skipped (no rule matched).

────────────────────────────────────────────────────────────────────────
3. CONFIG FILE FORMAT
────────────────────────────────────────────────────────────────────────

  The config is YAML (preferred) or JSON with two top-level keys:

    settings:   global knobs (optional)
    folders:    list of target folder definitions (required)

  3.1 settings
  ─────────────

    settings:
      skip_dirs:
        - node_modules       # directory names to ignore entirely
        - __pycache__
        - .git

      root_keep:
        - README.md          # filenames that must stay at root — never moved
        - .env

      recursive: false       # false = scan top-level only (default)
                             # true  = scan all subdirectories (rglob)

      head_bytes: 512        # how many bytes of each file to read for
                             # content_contains / content_regex rules
                             # (default: 1024)

  All settings keys are optional. Defaults are sensible for most projects.

  3.2 folders (rules)
  ─────────────────────

    folders:
      - name: schemas              # target subfolder name (may contain /)
        description: JSON Schemas   # human-readable (shown in dry-run output)
        priority: 10               # higher wins when multiple folders match
        mode: all                  # "all" = AND, "any" = OR (default)
        rules:
          - extension: .json       # each rule is a dict with ONE type key
          - content_contains: '"$schema"'

  Fields:
    name          (required) Target subfolder path relative to scan root.
                  May include slashes: "docs/specs", "docs/styles".

    description   (optional) Shown in dry-run and --defs-only output.

    priority      (optional, default: 0) Integer. When a file matches
                  multiple folder definitions, the highest priority wins.
                  Among equal priorities, definition order wins.

    mode          (optional, default: "any")
                  "any" = file matches if ANY rule in the list matches (OR).
                  "all" = file matches only if ALL rules match (AND).

    rules         (required) List of rule dicts. See section 4.

────────────────────────────────────────────────────────────────────────
4. RULE TYPES (complete reference)
────────────────────────────────────────────────────────────────────────

  Every rule is a single-key dict. The key is the rule type, the value
  is the parameter(s). All string comparisons are case-insensitive.

  ┌─────────────────────┬────────────────────────────────────────────────┐
  │ Rule Type           │ Description                                    │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ extension           │ Match file extension (with or without dot).    │
  │                     │   extension: .json                             │
  │                     │   extension: [.json, .yaml, .yml]              │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ name_glob           │ Match filename with glob/fnmatch patterns.     │
  │                     │   name_glob: "*.test.*"                        │
  │                     │   name_glob: ["*.spec.*", "test_*"]            │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ name_regex          │ Match filename with regex (re.IGNORECASE).     │
  │                     │   name_regex: "^draft-.*\\.md$"               │
  │                     │   name_regex: ["report", "scorecard"]          │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ stem_contains       │ Match if stem (name minus extension) contains  │
  │                     │ any substring.                                 │
  │                     │   stem_contains: schema                        │
  │                     │   stem_contains: [schema, spec, term-map]      │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ stem_startswith     │ Match if stem starts with any prefix.          │
  │                     │   stem_startswith: prompt-                      │
  │                     │   stem_startswith: [perplexity-, grok-, manus-]│
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ content_contains    │ Match if first N bytes contain any substring.  │
  │                     │ N = settings.head_bytes (default 1024).        │
  │                     │ Only reads text-like files (by extension).     │
  │                     │   content_contains: '"$schema"'                │
  │                     │   content_contains: ['"$schema"', '"$id"']     │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ content_regex       │ Match if first N bytes match any regex.        │
  │                     │ Flags: IGNORECASE + MULTILINE.                 │
  │                     │   content_regex: "^#!.*python"                 │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ size_gt             │ Match if file size > N bytes.                  │
  │                     │   size_gt: 1048576   # > 1 MB                 │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ size_lt             │ Match if file size < N bytes.                  │
  │                     │   size_lt: 100       # < 100 bytes             │
  ├─────────────────────┼────────────────────────────────────────────────┤
  │ path_contains       │ Match if relative path contains any substring. │
  │                     │ Useful with recursive: true.                   │
  │                     │   path_contains: test                          │
  └─────────────────────┴────────────────────────────────────────────────┘

  Text-like extensions recognized for content_* rules:
    .json .md .txt .html .htm .py .ts .tsx .js .jsx .css .yaml .yml
    .toml .csv .tsv .xml .svg .sh .bash .zsh .rs .go .rb .java .c .h
    .cpp .hpp .sql .graphql .proto .env .ini .cfg .conf .tex .rst .adoc

  Binary files (.png, .mp4, .pdf, etc.) are never read for content rules —
  content_contains and content_regex silently return false for them.

────────────────────────────────────────────────────────────────────────
5. RULE MODES: "any" vs "all"
────────────────────────────────────────────────────────────────────────

  mode: any  (default, OR logic)
    The folder matches a file if ANY single rule in its list matches.
    Good for catch-all folders: "anything that is .html OR starts with
    perplexity- goes to research/".

  mode: all  (AND logic)
    The folder matches only if EVERY rule in its list matches.
    Good for narrow targeting: "must be .json AND must contain '$schema'
    in its content".

  You can define MULTIPLE entries for the same folder name with
  different modes — see section 7.

────────────────────────────────────────────────────────────────────────
6. RULE NEGATION
────────────────────────────────────────────────────────────────────────

  Any rule can be negated by adding `negate: true`:

    rules:
      - extension: .md
      - stem_contains: schema
        negate: true            # match .md files that do NOT contain "schema"

  This is useful in "all" mode to express: "must be X but NOT Y".

────────────────────────────────────────────────────────────────────────
7. MULTIPLE FOLDER ENTRIES & PRIORITY
────────────────────────────────────────────────────────────────────────

  The same folder name can appear multiple times in the folders list.
  Each entry is evaluated independently. This lets you combine different
  modes for the same target:

    # Entry 1: AND — files that are .json AND contain "$schema"
    - name: schemas
      priority: 10
      mode: all
      rules:
        - extension: .json
        - content_contains: ['"$schema"', '"$id"']

    # Entry 2: AND — files that are .json AND have "schema" in name
    - name: schemas
      priority: 10
      mode: all
      rules:
        - extension: .json
        - stem_contains: [schema, term-map]

  A file matching either entry lands in schemas/.

  When a file matches MULTIPLE different folders, the one with the
  highest priority wins. Equal priorities are broken by definition order
  (first defined wins).

────────────────────────────────────────────────────────────────────────
8. CONFIDENCE LEVELS
────────────────────────────────────────────────────────────────────────

  Each proposal is tagged with a confidence level:

    high    — only one folder matched, or the winner has strictly higher
              priority than all other matches.
    medium  — multiple folders matched with equal top priority.
    low     — (reserved for future heuristic scoring).

  Confidence is informational only — it does not affect --apply behavior.

────────────────────────────────────────────────────────────────────────
9. CONFIG DISCOVERY
────────────────────────────────────────────────────────────────────────

  If -c/--config is not specified, the tool searches the scan directory
  (--dir, default: cwd) for these filenames in order:

    1. organize.yaml
    2. organize.yml
    3. organize.json

  The first one found is used. If none exist, the tool exits with an
  error and suggests --init.

  This means you can drop a config next to the files you want to
  organize and just run:

    cd session-02 && python ../tools/organize.py

────────────────────────────────────────────────────────────────────────
10. STARTER CONFIG (--init)
────────────────────────────────────────────────────────────────────────

  python organize.py --init

  Generates a fully commented organize.yaml in the scan directory with
  example folder definitions for schemas, docs, tests, config, and
  scripts. Edit it to match your project's needs.

  Will NOT overwrite an existing organize.yaml.

────────────────────────────────────────────────────────────────────────
11. JSON OUTPUT (--json)
────────────────────────────────────────────────────────────────────────

  python organize.py --json

  Outputs a single JSON object to stdout with three keys:

    {
      "config":      "/abs/path/to/organize.yaml",
      "scan_dir":    "/abs/path/to/target",
      "definitions": [ ... parsed folder defs ... ],
      "proposals":   [
        {
          "source":      "my-file.json",
          "target":      "schemas/my-file.json",
          "folder_name": "schemas",
          "reasons":     ["extension(.json)", "content_contains(...)"],
          "confidence":  "high"
        }
      ]
    }

  Useful for piping into jq, CI validation, or integration with other tools.

────────────────────────────────────────────────────────────────────────
12. RUNNING FROM ANOTHER DIRECTORY
────────────────────────────────────────────────────────────────────────

  The tool separates "where the config is" from "where the files are":

  # Config in session-02/, scan session-02/ :
  python tools/organize.py -c session-02/session02_organize.yaml \
                           --dir session-02/

  # Config in tools/, scan a completely different directory:
  python tools/organize.py -c tools/my-rules.yaml --dir ~/Downloads/

  If --dir is omitted, the current working directory is scanned.

────────────────────────────────────────────────────────────────────────
13. EXAMPLES
────────────────────────────────────────────────────────────────────────

  13.1 Minimal config
  ─────────────────────

    folders:
      - name: images
        rules:
          - extension: [.png, .jpg, .jpeg, .gif, .svg, .webp]

  13.2 Real-world: session-02 video production
  ──────────────────────────────────────────────

    settings:
      skip_dirs: [skills, pipeline, tests, output, .pytest_cache]
      root_keep: [README.md, CHANGELOG.md, .env, validate.py]
      head_bytes: 512

    folders:
      - name: schemas
        priority: 10
        mode: all
        rules:
          - extension: .json
          - content_contains: ['"$schema"', '"$id"']

      - name: schemas
        priority: 10
        mode: all
        rules:
          - extension: .json
          - stem_contains: [schema, term-map]

      - name: research
        priority: 8
        mode: any
        rules:
          - stem_startswith: [perplexity-, grok-, manus-]
          - extension: [.html, .htm, .xlsx, .xls, .csv]

      - name: docs/reports
        priority: 5
        rules:
          - name_regex: "(?i)(report|scorecard).*\\.md$"

      - name: docs/specs
        priority: 4
        rules:
          - name_regex: "(?i)(schema|spec|extension|unified).*\\.md$"

      - name: docs/styles
        priority: 4
        rules:
          - name_regex: "(?i)(style|taxonomy|camera|scene).*\\.md$"

      - name: examples
        priority: 3
        rules:
          - name_regex: "(?i)(demo|example|instance).*\\.json$"

  13.3 Content-based classification
  ──────────────────────────────────

    folders:
      - name: shebang-scripts
        description: Files with a shebang line, regardless of extension.
        mode: any
        rules:
          - content_regex: "^#!"

  13.4 Combining AND + OR via multiple entries
  ──────────────────────────────────────────────

    # Must be .md AND contain "API" in name (AND group)
    - name: api-docs
      priority: 10
      mode: all
      rules:
        - extension: .md
        - stem_contains: api

    # OR: anything with "openapi" in content (OR group, same folder)
    - name: api-docs
      priority: 10
      mode: any
      rules:
        - content_contains: '"openapi"'

────────────────────────────────────────────────────────────────────────
14. INTERNALS & EXTENSION POINTS
────────────────────────────────────────────────────────────────────────

  The code has 7 numbered sections:

    1. RULE ENGINE      — FileInfo dataclass + 10 rule evaluators
    2. FOLDER DEFS      — FolderDef/RuleGroup parsing from config
    3. CONFIG LOADING   — YAML/JSON detection, Config.from_dict()
    4. INSPECTION        — Walk directory, match rules, build proposals
    5. DISPLAY & APPLY  — Pretty-print + shutil.move()
    6. STARTER CONFIG   — Embedded YAML template for --init
    7. CLI              — argparse + main()

  To add a new rule type:
    1. Write a function: def _eval_mytype(info: FileInfo, params: Any) -> bool
    2. Register it:      RULE_EVALUATORS["mytype"] = _eval_mytype
    3. Use it in YAML:   - mytype: <params>

  No other changes needed — the engine is fully data-driven.

────────────────────────────────────────────────────────────────────────
15. LIMITATIONS
────────────────────────────────────────────────────────────────────────

  - Flat moves only: files are moved into target folders, never renamed.
  - No destructive overwrites: if the target path already exists, the
    move is silently skipped (logged in --apply output).
  - Content rules only read text-like files (by extension allowlist).
    Binary files are never opened.
  - No undo: there is no built-in rollback. Use --json to save the plan
    before --apply, or rely on git to revert.
  - Non-recursive by default. Set recursive: true for deep scans, but
    note that files already inside a defined target folder are skipped
    to prevent re-moves.

────────────────────────────────────────────────────────────────────────

Dependencies:
  - Python 3.10+  (for X | Y type unions; 3.8+ works with __future__)
  - PyYAML        (optional — only needed for .yaml/.yml configs)

License: same as the parent repository.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

# ── Shared lib imports ────────────────────────────────────────────────────
# Ensure the project root is on sys.path so `lib` is importable
# whether invoked as `python tools/organize.py` or `python -m tools.organize`.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from lib.file_info import FileInfo, load_file_info  # noqa: E402
from lib.file_meta import FileMeta, FileRule, FileStatus, Severity  # noqa: E402
from lib.rules import Rule, RuleGroup, RULE_EVALUATORS, parse_rule  # noqa: E402

# ── File metadata (machine-readable, for AI agents) ──────────────────────
__file_meta__ = FileMeta(
    role="Declarative directory organizer CLI",
    domain="developer-tooling",
    status=FileStatus.STABLE,
    owner="tools",
    tags=["cli", "organizer", "rule-engine", "yaml", "json"],
    rules=[
        FileRule(
            rule="Test coverage must remain above 90%",
            severity=Severity.ERROR,
            rationale="This tool moves files on disk — under-tested rule logic "
                      "can silently misclassify and relocate user data.",
        ),
    ],
    schema_ref="",
    test_ref="tools/test_organize.py",
    forbidden_patterns=[r"shutil\.rmtree", r"os\.remove\("],
)
from lib.config import load_config, find_config as _lib_find_config  # noqa: E402



# ═══════════════════════════════════════════════════════════════════════════
# 1. FOLDER DEFINITIONS — parsed from config
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FolderDef:
    """A target folder with its classification rules."""
    name: str
    description: str
    rules: RuleGroup
    priority: int = 0


def parse_folder_def(raw: dict[str, Any]) -> FolderDef:
    """Parse a folder definition from config."""
    name = raw["name"]
    description = raw.get("description", "")
    priority = raw.get("priority", 0)
    mode = raw.get("mode", "any")

    raw_rules = raw.get("rules", [])
    rules = tuple(parse_rule(dict(r)) for r in raw_rules)  # copy dicts to allow pop

    return FolderDef(
        name=name,
        description=description,
        rules=RuleGroup(rules=rules, mode=mode),
        priority=priority,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. CONFIG LOADING
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    """Parsed organizer configuration."""
    folders: list[FolderDef]
    skip_dirs: set[str]
    root_keep: set[str]
    recursive: bool
    head_bytes: int

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Config:
        settings = data.get("settings", {})
        folders_raw = data.get("folders", [])

        return Config(
            folders=[parse_folder_def(f) for f in folders_raw],
            skip_dirs=set(settings.get("skip_dirs", [])),
            root_keep=set(settings.get("root_keep", [])),
            recursive=settings.get("recursive", False),
            head_bytes=settings.get("head_bytes", 1024),
        )

    @staticmethod
    def load(path: Path) -> Config:
        """Load config from YAML or JSON file (delegates to lib.config)."""
        data = load_config(path)
        return Config.from_dict(data)


# ═══════════════════════════════════════════════════════════════════════════
# 4. INSPECTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MoveProposal:
    """A proposed file move."""
    source: str           # relative to scan root
    target: str           # relative to scan root
    folder_name: str      # which FolderDef matched
    reasons: list[str]    # which rules matched
    confidence: str       # "high" | "medium" | "low"


def inspect(
    root: Path,
    config: Config,
    *,
    verbose: bool = False,
) -> list[MoveProposal]:
    """
    Walk root, classify each file against config.folders, return MoveProposals.
    """
    proposals: list[MoveProposal] = []

    if config.recursive:
        entries = sorted(root.rglob("*"))
    else:
        entries = sorted(root.iterdir())

    for entry in entries:
        # Skip directories when not recursing (recurse is handled by rglob)
        if not entry.is_file():
            continue

        # Compute relative path
        try:
            rel = entry.relative_to(root)
        except ValueError:
            continue

        # Skip files inside skip_dirs
        if any(part in config.skip_dirs for part in rel.parts[:-1]):
            continue

        # Skip files already inside a target folder
        if any(str(rel).startswith(f.name + "/") or str(rel).startswith(f.name + os.sep)
               for f in config.folders):
            continue

        # Skip hidden files (unless explicitly in root_keep)
        if entry.name.startswith('.') and entry.name not in config.root_keep:
            continue

        # Skip root_keep files
        if entry.name in config.root_keep:
            continue

        info = load_file_info(entry, root, head_bytes=config.head_bytes)

        # Evaluate all folder rules, collect matches
        matches: list[tuple[FolderDef, list[str]]] = []
        for folder_def in config.folders:
            if folder_def.rules.evaluate(info):
                reasons = folder_def.rules.explain_match(info)
                matches.append((folder_def, reasons))

        if not matches:
            if verbose:
                print(f"  [SKIP] {rel} — no rule matched")
            continue

        # Pick highest priority; definition order breaks ties
        matches.sort(key=lambda m: -m[0].priority)
        best, reasons = matches[0]

        # Confidence
        if len(matches) == 1:
            confidence = "high"
        elif matches[0][0].priority > matches[1][0].priority:
            confidence = "high"
        else:
            confidence = "medium"

        proposals.append(MoveProposal(
            source=str(rel),
            target=f"{best.name}/{entry.name}",
            folder_name=best.name,
            reasons=reasons,
            confidence=confidence,
        ))

    return proposals


# ═══════════════════════════════════════════════════════════════════════════
# 5. DISPLAY AND APPLY
# ═══════════════════════════════════════════════════════════════════════════

def print_definitions(config: Config) -> None:
    """Print the folder definitions from config."""
    print(f"\n{'═' * 70}")
    print("  FOLDER DEFINITIONS")
    print(f"{'═' * 70}")
    for fd in config.folders:
        print(f"\n  📁 {fd.name}/  (priority: {fd.priority}, mode: {fd.rules.mode})")
        if fd.description:
            # Word-wrap description
            desc = fd.description
            while desc:
                line = desc[:66]
                cut = line.rfind(' ') if len(desc) > 66 else len(line)
                if cut <= 0:
                    cut = len(line)
                print(f"     {desc[:cut].strip()}")
                desc = desc[cut:].strip()
        print(f"     Rules:")
        for rule in fd.rules.rules:
            neg = "NOT " if rule.negate else ""
            print(f"       • {neg}{rule.type}: {rule.params}")


def print_proposals(proposals: list[MoveProposal], *, verbose: bool = False) -> None:
    """Pretty-print proposed moves."""
    if not proposals:
        print("\n  No files need moving — everything is already organized.")
        return

    print(f"\n{'═' * 70}")
    print(f"  PROPOSED MOVES ({len(proposals)} files)")
    print(f"{'═' * 70}")

    by_folder: dict[str, list[MoveProposal]] = {}
    for p in proposals:
        by_folder.setdefault(p.folder_name, []).append(p)

    for folder_name, fps in sorted(by_folder.items()):
        print(f"\n  → {folder_name}/")
        for p in fps:
            tag = f"[{p.confidence.upper():6}]"
            print(f"    {tag}  {p.source}")
            if verbose:
                for r in p.reasons:
                    print(f"             ↳ {r}")

    print(f"\n{'─' * 70}")
    high = sum(1 for p in proposals if p.confidence == "high")
    med = sum(1 for p in proposals if p.confidence == "medium")
    low = sum(1 for p in proposals if p.confidence == "low")
    print(f"  Summary: {len(proposals)} file(s) to move")
    print(f"    high confidence : {high}")
    print(f"    medium          : {med}")
    print(f"    low             : {low}")
    print(f"\n  Run with --apply to execute these moves.")
    print(f"  Run with -v for rule reasoning.\n")


def apply_moves(root: Path, proposals: list[MoveProposal]) -> int:
    """Execute proposed moves. Returns count of files moved."""
    moved = 0
    for p in proposals:
        src = root / p.source
        dst = root / p.target

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
# 6. STARTER CONFIG GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

STARTER_CONFIG = """\
# organize.yaml — Declarative file organizer config
# Docs: each folder defines rules that classify files into it.
#
# Rule types:
#   extension:        ".json" or [".json", ".yaml"]
#   name_glob:        "*.test.*" or ["*.spec.*", "*.test.*"]
#   name_regex:       "^prefix-" or ["^draft-", "^wip-"]
#   stem_contains:    "schema" or ["schema", "spec"]
#   stem_startswith:  "prompt-" or ["prompt-", "template-"]
#   content_contains: '"$schema"' or ['"$schema"', '"$id"']
#   content_regex:    "^import\\\\s" or ["^#!.*python", "^#!.*bash"]
#   size_gt:          1048576   # bytes (1 MB)
#   size_lt:          100
#   path_contains:    "test" or ["test", "spec"]
#
# Any rule can be negated:  { extension: ".md", negate: true }
#
# mode: "any" (OR, default) — match if ANY rule hits
# mode: "all" (AND)         — match only if ALL rules hit

settings:
  # Directories to skip entirely (already organized, build artifacts, etc.)
  skip_dirs:
    - node_modules
    - __pycache__
    - .git
    - .pytest_cache
    - dist
    - build

  # Files that should stay at root — never moved
  root_keep:
    - README.md
    - CHANGELOG.md
    - LICENSE
    - .gitignore
    - .env

  # Scan subdirectories? (default: false — top-level only)
  recursive: false

  # How many bytes of file content to read for content_* rules
  head_bytes: 1024

folders:
  # ── Example: JSON Schema files ──
  - name: schemas
    description: >
      Machine-readable schema files (JSON Schema, OpenAPI, etc.)
    priority: 10
    mode: any
    rules:
      - content_contains:
          - '"$schema"'
          - '"$id"'
          - '"openapi"'
      - stem_contains: schema

  # ── Example: Documentation ──
  - name: docs
    description: >
      Human-readable documentation, guides, and specifications.
    priority: 5
    mode: all
    rules:
      - extension: .md
      - stem_contains:
          - guide
          - spec
          - readme
          - docs
          - manual

  # ── Example: Test files ──
  - name: tests
    description: >
      Test files, fixtures, and test utilities.
    priority: 7
    mode: any
    rules:
      - name_glob:
          - "*.test.*"
          - "*.spec.*"
          - "test_*"
          - "*_test.*"
      - stem_contains: fixture

  # ── Example: Config files ──
  - name: config
    description: >
      Configuration files for tools, linters, bundlers, CI.
    priority: 3
    mode: any
    rules:
      - extension:
          - .yaml
          - .yml
          - .toml
          - .ini
          - .cfg
      - name_glob:
          - ".*rc"
          - ".*rc.json"
          - ".*.config.*"

  # ── Example: Scripts ──
  - name: scripts
    description: >
      Utility scripts, automation, and one-off tools.
    priority: 4
    mode: all
    rules:
      - extension:
          - .sh
          - .bash
          - .py
      - content_regex: "^#!"
"""


def write_starter_config(path: Path) -> None:
    """Write the starter config to disk."""
    if path.exists():
        print(f"  Config already exists: {path}")
        print(f"  Rename or delete it first.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STARTER_CONFIG, encoding="utf-8")
    print(f"  Created starter config: {path}")
    print(f"  Edit it, then run:  python organize.py -c {path.name}")


# ═══════════════════════════════════════════════════════════════════════════
# 7. CLI
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG_NAMES = ["organize.yaml", "organize.yml", "organize.json"]


def find_config(scan_dir: Path) -> Path | None:
    """Look for a config file in the scan directory (delegates to lib.config)."""
    return _lib_find_config(scan_dir, DEFAULT_CONFIG_NAMES)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="General-purpose directory organizer with declarative rules.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python organize.py                         # dry run (auto-find config)
  python organize.py -c rules.yaml           # use specific config
  python organize.py -v                      # verbose: show rule reasoning
  python organize.py --json                  # output as JSON
  python organize.py --apply                 # execute the moves
  python organize.py --init                  # generate starter organize.yaml
  python organize.py --defs-only             # print folder definitions only
  python organize.py --dir ~/projects/foo    # scan a different directory

rule types:
  extension, name_glob, name_regex, stem_contains, stem_startswith,
  content_contains, content_regex, size_gt, size_lt, path_contains
  (any rule can be negated with 'negate: true')
""",
    )
    parser.add_argument("-c", "--config", type=Path, default=None,
                        help="Path to YAML/JSON config file.")
    parser.add_argument("--dir", type=Path, default=Path.cwd(),
                        help="Directory to organize (default: cwd).")
    parser.add_argument("--apply", action="store_true",
                        help="Execute proposed moves (default: dry run).")
    parser.add_argument("--json", action="store_true",
                        help="Output proposals as JSON.")
    parser.add_argument("--init", action="store_true",
                        help="Generate a starter organize.yaml in --dir.")
    parser.add_argument("--defs-only", action="store_true",
                        help="Print folder definitions, don't inspect files.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show rule reasoning for each file.")

    args = parser.parse_args()
    scan_dir = args.dir.resolve()

    # ── Init mode ─────────────────────────────────────────────────────────
    if args.init:
        write_starter_config(scan_dir / "organize.yaml")
        return 0

    # ── Locate config ─────────────────────────────────────────────────────
    if args.config:
        config_path = args.config.resolve()
    else:
        config_path = find_config(scan_dir)

    if config_path is None or not config_path.is_file():
        print("ERROR: No config file found.", file=sys.stderr)
        print("  Create one with:  python organize.py --init", file=sys.stderr)
        if args.config:
            print(f"  Specified config not found: {args.config}", file=sys.stderr)
        return 1

    if not scan_dir.is_dir():
        print(f"ERROR: Not a directory: {scan_dir}", file=sys.stderr)
        return 1

    # ── Load config ───────────────────────────────────────────────────────
    try:
        config = Config.load(config_path)
    except Exception as e:
        print(f"ERROR: Failed to parse config: {e}", file=sys.stderr)
        return 1

    if not args.json:
        print(f"\n  Config: {config_path}")
        print(f"  Target: {scan_dir}")

    # ── Definitions ───────────────────────────────────────────────────────
    if not args.json:
        print_definitions(config)

    if args.defs_only:
        return 0

    # ── Inspect ───────────────────────────────────────────────────────────
    proposals = inspect(scan_dir, config, verbose=args.verbose)

    # ── Output ────────────────────────────────────────────────────────────
    if args.json:
        out = {
            "config": str(config_path),
            "scan_dir": str(scan_dir),
            "definitions": [
                {
                    "name": fd.name,
                    "description": fd.description,
                    "priority": fd.priority,
                    "mode": fd.rules.mode,
                    "rules": [
                        {"type": r.type, "params": r.params, "negate": r.negate}
                        for r in fd.rules.rules
                    ],
                }
                for fd in config.folders
            ],
            "proposals": [asdict(p) for p in proposals],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print_proposals(proposals, verbose=args.verbose)

    # ── Apply ─────────────────────────────────────────────────────────────
    if args.apply:
        print(f"\n{'═' * 70}")
        print(f"  APPLYING MOVES")
        print(f"{'═' * 70}\n")
        moved = apply_moves(scan_dir, proposals)
        print(f"\n  Done: {moved}/{len(proposals)} file(s) moved.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())