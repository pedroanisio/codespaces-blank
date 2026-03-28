#!/usr/bin/env python3
"""
organize.py — General-purpose directory organizer.

Reads a declarative YAML config that defines target folders and classification
rules, inspects a directory, proposes moves, and optionally applies them.

No domain knowledge is hardcoded. All classification logic lives in the config.

Usage:
    python organize.py                        # dry run with ./organize.yaml
    python organize.py -c my_rules.yaml       # use custom config
    python organize.py --apply                 # execute moves
    python organize.py --init                  # generate a starter config
    python organize.py --json                  # JSON output
    python organize.py -v                      # verbose reasoning
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ═══════════════════════════════════════════════════════════════════════════
# 1. RULE ENGINE — declarative matchers
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FileInfo:
    """Pre-computed metadata about a file, used by rule evaluation."""
    path: Path
    name: str
    stem: str
    suffix: str          # lowercase, includes dot
    size: int
    head: str            # first N bytes as text (empty if binary/unreadable)
    rel: str             # path relative to scan root


def load_file_info(path: Path, root: Path, *, head_bytes: int = 1024) -> FileInfo:
    """Build FileInfo for a single file."""
    suffix = path.suffix.lower()
    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    head = ""
    # Only read head for text-like extensions
    TEXT_SUFFIXES = {
        '.json', '.md', '.txt', '.html', '.htm', '.py', '.ts', '.tsx',
        '.js', '.jsx', '.css', '.yaml', '.yml', '.toml', '.csv', '.tsv',
        '.xml', '.svg', '.sh', '.bash', '.zsh', '.rs', '.go', '.rb',
        '.java', '.c', '.h', '.cpp', '.hpp', '.sql', '.graphql', '.proto',
        '.env', '.ini', '.cfg', '.conf', '.tex', '.rst', '.adoc',
    }
    if suffix in TEXT_SUFFIXES or path.name.startswith('.'):
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:head_bytes]
        except OSError:
            pass

    try:
        rel = str(path.relative_to(root))
    except ValueError:
        rel = path.name

    return FileInfo(
        path=path,
        name=path.name,
        stem=path.stem,
        suffix=suffix,
        size=size,
        head=head,
        rel=rel,
    )


# ── Individual rule evaluators ────────────────────────────────────────────
#
# Each rule type is a pure function:  (file_info, rule_params) → bool
# Rule params come directly from the YAML config.

def _eval_extension(info: FileInfo, params: Any) -> bool:
    """Match file extension(s). Params: str or list[str], with or without dot."""
    if isinstance(params, str):
        params = [params]
    normalized = [e if e.startswith('.') else f'.{e}' for e in params]
    return info.suffix in normalized


def _eval_name_glob(info: FileInfo, params: Any) -> bool:
    """Match filename against glob pattern(s). Uses fnmatch semantics."""
    import fnmatch
    if isinstance(params, str):
        params = [params]
    return any(fnmatch.fnmatch(info.name, pat) for pat in params)


def _eval_name_regex(info: FileInfo, params: Any) -> bool:
    """Match filename against regex pattern(s)."""
    if isinstance(params, str):
        params = [params]
    return any(re.search(pat, info.name, re.IGNORECASE) for pat in params)


def _eval_stem_contains(info: FileInfo, params: Any) -> bool:
    """Match if stem (name without extension) contains any of the given substrings."""
    if isinstance(params, str):
        params = [params]
    stem_lower = info.stem.lower()
    return any(kw.lower() in stem_lower for kw in params)


def _eval_stem_startswith(info: FileInfo, params: Any) -> bool:
    """Match if stem starts with any of the given prefixes."""
    if isinstance(params, str):
        params = [params]
    stem_lower = info.stem.lower()
    return any(stem_lower.startswith(px.lower()) for px in params)


def _eval_content_contains(info: FileInfo, params: Any) -> bool:
    """Match if file head contains any of the given substrings (case-insensitive)."""
    if not info.head:
        return False
    if isinstance(params, str):
        params = [params]
    head_lower = info.head.lower()
    return any(kw.lower() in head_lower for kw in params)


def _eval_content_regex(info: FileInfo, params: Any) -> bool:
    """Match if file head matches any of the given regex patterns."""
    if not info.head:
        return False
    if isinstance(params, str):
        params = [params]
    return any(re.search(pat, info.head, re.IGNORECASE | re.MULTILINE) for pat in params)


def _eval_size_gt(info: FileInfo, params: Any) -> bool:
    """Match if file size > N bytes."""
    return info.size > int(params)


def _eval_size_lt(info: FileInfo, params: Any) -> bool:
    """Match if file size < N bytes."""
    return info.size < int(params)


def _eval_path_contains(info: FileInfo, params: Any) -> bool:
    """Match if the relative path contains any substring."""
    if isinstance(params, str):
        params = [params]
    rel_lower = info.rel.lower()
    return any(kw.lower() in rel_lower for kw in params)


# ── Rule evaluator registry ──────────────────────────────────────────────

RULE_EVALUATORS: dict[str, Any] = {
    "extension":        _eval_extension,
    "name_glob":        _eval_name_glob,
    "name_regex":       _eval_name_regex,
    "stem_contains":    _eval_stem_contains,
    "stem_startswith":  _eval_stem_startswith,
    "content_contains": _eval_content_contains,
    "content_regex":    _eval_content_regex,
    "size_gt":          _eval_size_gt,
    "size_lt":          _eval_size_lt,
    "path_contains":    _eval_path_contains,
}


# ── Composite rule evaluation ────────────────────────────────────────────

@dataclass(frozen=True)
class Rule:
    """A single atomic rule parsed from config."""
    type: str
    params: Any
    negate: bool = False

    def evaluate(self, info: FileInfo) -> bool:
        evaluator = RULE_EVALUATORS.get(self.type)
        if evaluator is None:
            raise ValueError(f"Unknown rule type: '{self.type}'. "
                             f"Available: {sorted(RULE_EVALUATORS)}")
        result = evaluator(info, self.params)
        return (not result) if self.negate else result

    def explain(self) -> str:
        neg = "NOT " if self.negate else ""
        return f"{neg}{self.type}({self.params})"


@dataclass(frozen=True)
class RuleGroup:
    """
    A group of rules combined with a logical operator.

    mode="any"  → OR  (file matches if ANY rule matches)  — default
    mode="all"  → AND (file matches if ALL rules match)
    """
    rules: tuple[Rule, ...]
    mode: str = "any"  # "any" | "all"

    def evaluate(self, info: FileInfo) -> bool:
        if self.mode == "all":
            return all(r.evaluate(info) for r in self.rules)
        return any(r.evaluate(info) for r in self.rules)

    def explain_match(self, info: FileInfo) -> list[str]:
        """Return human-readable reasons for matched rules."""
        return [r.explain() for r in self.rules if r.evaluate(info)]


# ═══════════════════════════════════════════════════════════════════════════
# 2. FOLDER DEFINITIONS — parsed from config
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FolderDef:
    """A target folder with its classification rules."""
    name: str
    description: str
    rules: RuleGroup
    priority: int = 0


def parse_rule(raw: dict[str, Any]) -> Rule:
    """Parse a single rule dict from config."""
    negate = raw.pop("negate", False) if isinstance(raw, dict) else False

    # The dict should have exactly one key (the rule type) after removing 'negate'
    rule_keys = [k for k in raw if k != "negate"]
    if len(rule_keys) != 1:
        raise ValueError(
            f"Each rule must have exactly one type key, got: {rule_keys}. "
            f"Full rule: {raw}"
        )
    rule_type = rule_keys[0]
    return Rule(type=rule_type, params=raw[rule_type], negate=negate)


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
        """Load config from YAML or JSON file."""
        text = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()

        if suffix in ('.yaml', '.yml'):
            if yaml is None:
                print("ERROR: PyYAML is required for YAML configs. "
                      "Install with: pip install pyyaml", file=sys.stderr)
                sys.exit(1)
            data = yaml.safe_load(text)
        elif suffix == '.json':
            data = json.loads(text)
        else:
            # Try YAML first, fall back to JSON
            try:
                if yaml:
                    data = yaml.safe_load(text)
                else:
                    data = json.loads(text)
            except Exception:
                data = json.loads(text)

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
    """Look for a config file in the scan directory."""
    for name in DEFAULT_CONFIG_NAMES:
        candidate = scan_dir / name
        if candidate.is_file():
            return candidate
    return None


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