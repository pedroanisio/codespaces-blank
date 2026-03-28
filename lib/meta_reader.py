#!/usr/bin/env python3
"""
meta_reader — Extract and display FileMeta from any source file.

Reads __file_meta__ from Python files, frontmatter from Markdown,
or sidecar .meta.json files.

Usage:
    python -m lib.meta_reader <file>              # pretty print
    python -m lib.meta_reader <file> --json       # JSON output
    python -m lib.meta_reader <file> --rules      # rules only
    python -m lib.meta_reader <file> --check      # exit 1 if any ERROR rules are violated
    python -m lib.meta_reader <glob>              # multiple files
    python -m lib.meta_reader tools/ --recursive  # scan directory
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

from lib.file_meta import FileMeta


# ── Extraction strategies ────────────────────────────────────────────────────

def _extract_from_python(path: Path) -> dict[str, Any] | None:
    """Extract __file_meta__ dict from a Python file's AST."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__file_meta__":
                    # Try to evaluate the Call node (FileMeta(...))
                    try:
                        # Extract keyword arguments from the constructor call
                        if isinstance(node.value, ast.Call):
                            return _extract_call_kwargs(node.value, source)
                    except Exception:
                        pass
    return None


def _extract_call_kwargs(call: ast.Call, source: str) -> dict[str, Any]:
    """Extract keyword arguments from a FileMeta(...) constructor call."""
    result: dict[str, Any] = {}
    for kw in call.keywords:
        if kw.arg is None:
            continue
        try:
            result[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, TypeError):
            # For enum values like FileStatus.STABLE, extract the string
            if isinstance(kw.value, ast.Attribute):
                result[kw.arg] = kw.value.attr.lower()
            # For nested constructor calls like FileRule(...)
            elif isinstance(kw.value, ast.Call):
                if isinstance(kw.value, ast.Call):
                    result[kw.arg] = _extract_call_kwargs(kw.value, source)
            # For lists of constructor calls
            elif isinstance(kw.value, ast.List):
                items = []
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Call):
                        items.append(_extract_call_kwargs(elt, source))
                    else:
                        try:
                            items.append(ast.literal_eval(elt))
                        except (ValueError, TypeError):
                            if isinstance(elt, ast.Attribute):
                                items.append(elt.attr.lower())
                if items:
                    result[kw.arg] = items
    return result


def _extract_from_frontmatter(path: Path) -> dict[str, Any] | None:
    """Extract meta from YAML frontmatter (--- delimited) in Markdown files."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None

    try:
        import yaml
        data = yaml.safe_load(m.group(1))
        if isinstance(data, dict) and "role" in data:
            return data
    except ImportError:
        pass
    return None


def _extract_from_sidecar(path: Path) -> dict[str, Any] | None:
    """Read <filename>.meta.json sidecar file."""
    sidecar = path.parent / f"{path.name}.meta.json"
    if sidecar.exists():
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def extract_meta(path: Path) -> FileMeta | None:
    """Extract FileMeta from a file using all available strategies.

    Tries in order:
      1. Sidecar .meta.json
      2. Python __file_meta__
      3. Markdown frontmatter
    """
    raw = _extract_from_sidecar(path)
    if raw:
        return FileMeta.model_validate(raw)

    if path.suffix == ".py":
        raw = _extract_from_python(path)
        if raw:
            return FileMeta.model_validate(raw)

    if path.suffix in (".md", ".mdx"):
        raw = _extract_from_frontmatter(path)
        if raw:
            return FileMeta.model_validate(raw)

    return None


# ── Display ──────────────────────────────────────────────────────────────────

def print_meta(path: Path, meta: FileMeta) -> None:
    """Pretty-print a FileMeta to stdout."""
    print(f"\n{'═' * 70}")
    print(f"  {path}")
    print(f"{'═' * 70}")
    print(f"  Role:   {meta.role or '(not set)'}")
    print(f"  Domain: {meta.domain or '(not set)'}")
    print(f"  Status: {meta.status.value}")
    print(f"  Owner:  {meta.owner or '(not set)'}")

    if meta.tags:
        print(f"  Tags:   {', '.join(meta.tags)}")

    if meta.rules:
        print(f"\n  Rules ({len(meta.rules)}):")
        for r in meta.rules:
            icon = {"error": "!!!", "warning": " ! ", "info": " i "}[r.severity.value]
            print(f"    [{icon}] {r.rule}")
            if r.rationale:
                print(f"          Why: {r.rationale}")
            if r.applies_to:
                print(f"          Scope: {', '.join(r.applies_to)}")

    if meta.forbidden_patterns:
        print(f"\n  Forbidden patterns:")
        for p in meta.forbidden_patterns:
            print(f"    ✗ /{p}/")

    if meta.relations:
        print(f"\n  Relations ({len(meta.relations)}):")
        for rel in meta.relations:
            print(f"    {rel.relation.value:15} → {rel.target}")
            if rel.notes:
                print(f"                    {rel.notes}")

    if meta.schema_ref:
        print(f"\n  Schema: {meta.schema_ref}")
    if meta.test_ref:
        print(f"  Tests:  {meta.test_ref}")

    print()


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract and display FileMeta from source files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python -m lib.meta_reader tools/organize.py
  python -m lib.meta_reader tools/organize.py --json
  python -m lib.meta_reader tools/organize.py --rules
  python -m lib.meta_reader tools/ --recursive
  python -m lib.meta_reader tools/organize.py --check
""",
    )
    parser.add_argument("paths", nargs="+", help="File(s) or directory to scan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--rules", action="store_true", help="Show rules only")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if any file has ERROR-severity rules without test_ref")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="Scan directories recursively for Python/Markdown files")

    args = parser.parse_args()

    # Resolve paths
    files: list[Path] = []
    for p_str in args.paths:
        p = Path(p_str)
        if p.is_dir():
            pattern = "**/*" if args.recursive else "*"
            for f in sorted(p.glob(pattern)):
                if f.is_file() and f.suffix in (".py", ".md", ".mdx"):
                    files.append(f)
        elif p.is_file():
            files.append(p)
        else:
            print(f"  ⚠ Not found: {p}", file=sys.stderr)

    if not files:
        print("No files to scan.", file=sys.stderr)
        return 1

    results: list[dict] = []
    has_issues = False

    for f in files:
        meta = extract_meta(f)
        if meta is None:
            if not args.json and len(files) == 1:
                print(f"  No __file_meta__ found in {f}")
            continue

        if args.json:
            entry = {"file": str(f), **meta.model_dump()}
            results.append(entry)
        elif args.rules:
            if meta.rules:
                print(f"\n  {f}:")
                for r in meta.rules:
                    icon = {"error": "!!!", "warning": " ! ", "info": " i "}[r.severity.value]
                    print(f"    [{icon}] {r.rule}")
        else:
            print_meta(f, meta)

        if args.check:
            for r in meta.rules:
                if r.severity.value == "error":
                    has_issues = True

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    if args.check and has_issues:
        print("\n  ✗ Files with ERROR-severity rules found.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
