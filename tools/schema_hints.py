#!/usr/bin/env python3
"""
schema_hints.py — Generate and maintain clustering hints for schema_tree.py.

Inspects a schema folder, analyzes definition names and structures, and
produces a .schema-hints.yaml file that schema_tree.py can consume to
improve its auto-clustering accuracy.

The hints file is designed to be:
  - Generated once, then refined (by human or LLM)
  - Auto-updated when new schema files appear
  - Machine-readable but human-editable

Usage:
    python schema_hints.py session-02/schemas/            # generate hints
    python schema_hints.py session-02/schemas/ --update    # update existing hints
    python schema_hints.py session-02/schemas/ --diff      # show what changed
    python schema_hints.py session-02/schemas/ --validate  # check hints consistency
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    HAS_YAML = False


# ═══════════════════════════════════════════════════════════════════════════
# 1. HINTS DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

HINTS_FILENAME = ".schema-hints.yaml"
HINTS_VERSION = "1.0.0"


@dataclass
class CategoryHint:
    """A category hint that tells the auto-clusterer where a definition belongs."""
    name: str                     # category name
    description: str              # what this category represents
    members: list[str]            # explicit definition names assigned here
    keywords: list[str]           # keywords that match defs to this category
    source: str = "auto"          # "auto" | "manual" | "llm"


@dataclass
class HintsFile:
    """The complete hints file structure."""
    version: str = HINTS_VERSION
    schema_dir: str = ""
    generated_at: str = ""
    updated_at: str = ""
    schema_files: list[str] = field(default_factory=list)
    definition_count: int = 0
    categories: list[CategoryHint] = field(default_factory=list)
    uncategorized: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "schema_dir": self.schema_dir,
            "generated_at": self.generated_at,
            "updated_at": self.updated_at,
            "schema_files": self.schema_files,
            "definition_count": self.definition_count,
            "categories": [
                {
                    "name": c.name,
                    "description": c.description,
                    "members": sorted(c.members),
                    "keywords": sorted(c.keywords),
                    "source": c.source,
                }
                for c in self.categories
            ],
            "uncategorized": sorted(self.uncategorized),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> HintsFile:
        cats = []
        for c in data.get("categories", []):
            cats.append(CategoryHint(
                name=c["name"],
                description=c.get("description", ""),
                members=c.get("members", []),
                keywords=c.get("keywords", []),
                source=c.get("source", "auto"),
            ))
        return HintsFile(
            version=data.get("version", HINTS_VERSION),
            schema_dir=data.get("schema_dir", ""),
            generated_at=data.get("generated_at", ""),
            updated_at=data.get("updated_at", ""),
            schema_files=data.get("schema_files", []),
            definition_count=data.get("definition_count", 0),
            categories=cats,
            uncategorized=data.get("uncategorized", []),
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2. SCHEMA ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _split_camel(name: str) -> list[str]:
    """Split CamelCase into lowercase tokens."""
    parts = re.sub(r'([A-Z])', r' \1', name).split()
    return [p.lower() for p in parts if p]


def _extract_defs(filepath: Path) -> list[tuple[str, dict]]:
    """Extract ($def_name, $def_body) pairs from a JSON schema file."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    defs = data.get("$defs", data.get("definitions", {}))
    if not isinstance(defs, dict):
        return []
    return [(name, body) for name, body in defs.items() if isinstance(body, dict)]


def _analyze_def(name: str, body: dict) -> dict[str, Any]:
    """Analyze a single definition for clustering signals."""
    tokens = _split_camel(name)
    props = body.get("properties", {})

    # Check allOf for additional properties
    if "allOf" in body and isinstance(body["allOf"], list):
        for item in body["allOf"]:
            if isinstance(item, dict) and "properties" in item:
                props = {**props, **item["properties"]}

    # Collect $refs
    refs: list[str] = []
    _collect_refs(body, refs)
    ref_names = [r.split("/")[-1] for r in refs if "/" in r]

    return {
        "name": name,
        "tokens": tokens,
        "suffix": tokens[-1] if tokens else "",
        "prefix": tokens[0] if tokens else "",
        "properties": list(props.keys()),
        "property_count": len(props),
        "ref_names": ref_names,
        "description": body.get("description", "")[:200],
        "has_allof": "allOf" in body,
        "has_anyof": "anyOf" in body,
        "has_oneof": "oneOf" in body,
    }


def _collect_refs(obj: Any, refs: list[str]) -> None:
    """Recursively collect $ref strings."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            refs.append(obj["$ref"])
        for v in obj.values():
            _collect_refs(v, refs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_refs(item, refs)


# ═══════════════════════════════════════════════════════════════════════════
# 3. AUTO-CATEGORIZATION (for initial hint generation)
# ═══════════════════════════════════════════════════════════════════════════

def _auto_categorize(analyses: list[dict[str, Any]]) -> list[CategoryHint]:
    """Generate initial category hints from definition analyses."""
    categories: dict[str, CategoryHint] = {}
    assigned: set[str] = set()

    # ── Pass 1: Suffix clustering ────────────────────────────────────────
    suffix_groups: dict[str, list[dict]] = defaultdict(list)
    for a in analyses:
        if a["suffix"]:
            suffix_groups[a["suffix"]].append(a)

    MIN_GROUP = max(3, len(analyses) // 80)
    for suffix, members in sorted(suffix_groups.items(), key=lambda x: -len(x[1])):
        if len(members) < MIN_GROUP or len(suffix) <= 1:
            continue
        cat_name = _suffix_to_cat_name(suffix)
        cat = CategoryHint(
            name=cat_name,
            description=f"Definitions with suffix '{suffix}' — auto-detected structural pattern.",
            members=[m["name"] for m in members],
            keywords=[suffix],
            source="auto",
        )
        categories[cat_name] = cat
        assigned.update(m["name"] for m in members)

    # ── Pass 2: Shared-reference clustering ──────────────────────────────
    # Defs that reference the same types belong together
    unassigned = [a for a in analyses if a["name"] not in assigned]
    if len(unassigned) >= MIN_GROUP * 2:
        # Build co-reference groups
        ref_to_defs: dict[str, list[str]] = defaultdict(list)
        for a in unassigned:
            for ref in a["ref_names"]:
                ref_to_defs[ref].append(a["name"])

        # Find refs that are shared by many unassigned defs
        for ref, def_names in sorted(ref_to_defs.items(), key=lambda x: -len(x[1])):
            unassigned_names = [d for d in def_names if d not in assigned]
            if len(unassigned_names) < MIN_GROUP:
                continue
            cat_name = f"{ref}-consumers"
            if cat_name in categories:
                # Merge into existing
                categories[cat_name].members.extend(unassigned_names)
            else:
                categories[cat_name] = CategoryHint(
                    name=cat_name,
                    description=f"Definitions that reference '{ref}' — likely belong to the same domain.",
                    members=unassigned_names,
                    keywords=[ref.lower()],
                    source="auto",
                )
            assigned.update(unassigned_names)

    # ── Pass 3: Token-frequency clustering for remaining ─────────────────
    still_unassigned = [a for a in analyses if a["name"] not in assigned]
    token_groups: dict[str, list[str]] = defaultdict(list)
    for a in still_unassigned:
        for tok in a["tokens"]:
            if len(tok) > 3:
                token_groups[tok].append(a["name"])

    for tok, names in sorted(token_groups.items(), key=lambda x: -len(x[1])):
        unassigned_names = [n for n in names if n not in assigned]
        if len(unassigned_names) < MIN_GROUP:
            continue
        cat_name = f"{tok.capitalize()}-related"
        if cat_name in categories:
            categories[cat_name].members.extend(unassigned_names)
        else:
            categories[cat_name] = CategoryHint(
                name=cat_name,
                description=f"Definitions containing token '{tok}' — auto-grouped by naming pattern.",
                members=unassigned_names,
                keywords=[tok],
                source="auto",
            )
        assigned.update(unassigned_names)

    # Deduplicate members in each category
    for cat in categories.values():
        cat.members = sorted(set(cat.members))

    return list(categories.values())


def _suffix_to_cat_name(suffix: str) -> str:
    """Convert a suffix token to a category name."""
    mapping = {
        "entity": "Entity Types",
        "op": "Operations",
        "node": "Workflow Nodes",
        "spec": "Specifications",
        "config": "Configuration",
        "asset": "Assets",
        "ref": "References",
        "record": "Records",
        "rule": "Rules",
        "check": "Checks",
        "step": "Pipeline Steps",
        "result": "Results",
        "controls": "Controls",
        "profile": "Profiles",
    }
    return mapping.get(suffix, f"{suffix.capitalize()} types")


# ═══════════════════════════════════════════════════════════════════════════
# 4. HINT GENERATION & UPDATE
# ═══════════════════════════════════════════════════════════════════════════

def generate_hints(schema_dir: Path) -> HintsFile:
    """Generate a fresh hints file from a schema directory."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    json_files = sorted(schema_dir.glob("*.json"))

    all_analyses: list[dict[str, Any]] = []
    all_def_names: list[str] = []

    for jf in json_files:
        for def_name, def_body in _extract_defs(jf):
            analysis = _analyze_def(def_name, def_body)
            all_analyses.append(analysis)
            all_def_names.append(def_name)

    categories = _auto_categorize(all_analyses)

    # Find uncategorized
    categorized = set()
    for cat in categories:
        categorized.update(cat.members)
    uncategorized = sorted(set(all_def_names) - categorized)

    return HintsFile(
        version=HINTS_VERSION,
        schema_dir=str(schema_dir),
        generated_at=now,
        updated_at=now,
        schema_files=[f.name for f in json_files],
        definition_count=len(all_def_names),
        categories=categories,
        uncategorized=uncategorized,
    )


def update_hints(schema_dir: Path, existing: HintsFile) -> tuple[HintsFile, dict[str, Any]]:
    """
    Update an existing hints file with new definitions.

    Returns (updated_hints, diff_info).
    Preserves manual/llm categorizations; only adds new defs.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    json_files = sorted(schema_dir.glob("*.json"))
    current_files = [f.name for f in json_files]

    # Gather all current definitions
    current_defs: dict[str, dict[str, Any]] = {}
    for jf in json_files:
        for def_name, def_body in _extract_defs(jf):
            current_defs[def_name] = _analyze_def(def_name, def_body)

    # What's already categorized
    existing_categorized: set[str] = set()
    for cat in existing.categories:
        existing_categorized.update(cat.members)
    existing_categorized.update(existing.uncategorized)

    # Find new and removed definitions
    current_names = set(current_defs.keys())
    previous_names = existing_categorized | set(existing.uncategorized)
    new_defs = current_names - previous_names
    removed_defs = previous_names - current_names
    new_files = set(current_files) - set(existing.schema_files)
    removed_files = set(existing.schema_files) - set(current_files)

    diff = {
        "new_definitions": sorted(new_defs),
        "removed_definitions": sorted(removed_defs),
        "new_files": sorted(new_files),
        "removed_files": sorted(removed_files),
        "previously_categorized": len(existing_categorized),
        "current_total": len(current_names),
    }

    # Categorize new definitions
    if new_defs:
        new_analyses = [current_defs[name] for name in new_defs]
        new_categories = _auto_categorize(new_analyses)

        # Try to merge new categories into existing ones by keyword/name overlap
        for new_cat in new_categories:
            merged = False
            for existing_cat in existing.categories:
                # Check keyword overlap
                shared_kw = set(new_cat.keywords) & set(existing_cat.keywords)
                # Check name similarity
                if shared_kw or _similar_names(new_cat.name, existing_cat.name):
                    existing_cat.members = sorted(set(existing_cat.members) | set(new_cat.members))
                    existing_cat.keywords = sorted(set(existing_cat.keywords) | set(new_cat.keywords))
                    merged = True
                    break
            if not merged:
                new_cat.source = "auto-update"
                existing.categories.append(new_cat)

        # New defs that didn't get categorized
        newly_categorized = set()
        for cat in existing.categories:
            newly_categorized.update(cat.members)
        still_uncategorized = sorted(new_defs - newly_categorized)
        existing.uncategorized = sorted(
            (set(existing.uncategorized) | set(still_uncategorized)) - removed_defs
        )
    else:
        # Just remove deleted defs
        existing.uncategorized = sorted(set(existing.uncategorized) - removed_defs)

    # Remove deleted defs from categories
    for cat in existing.categories:
        cat.members = sorted(set(cat.members) - removed_defs)

    # Remove empty categories
    existing.categories = [c for c in existing.categories if c.members]

    # Update metadata
    existing.updated_at = now
    existing.schema_files = current_files
    existing.definition_count = len(current_names)

    return existing, diff


def _similar_names(a: str, b: str) -> bool:
    """Check if two category names are semantically similar."""
    a_lower = a.lower().replace("-", " ").replace("_", " ")
    b_lower = b.lower().replace("-", " ").replace("_", " ")
    a_words = set(a_lower.split())
    b_words = set(b_lower.split())
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words)
    return overlap >= 1 and overlap / min(len(a_words), len(b_words)) >= 0.5


# ═══════════════════════════════════════════════════════════════════════════
# 5. FILE I/O
# ═══════════════════════════════════════════════════════════════════════════

def write_hints(hints: HintsFile, path: Path) -> None:
    """Write hints to YAML (preferred) or JSON."""
    data = hints.to_dict()

    if HAS_YAML:
        # Add a header comment
        header = (
            "# Schema clustering hints for schema_tree.py\n"
            "# Edit categories, rename them, move members between them.\n"
            "# Set source: 'manual' for hand-curated categories.\n"
            "# Run with --update to incorporate new schema definitions.\n"
            "#\n"
            f"# Generated: {hints.generated_at}\n"
            f"# Updated:   {hints.updated_at}\n"
            "#\n\n"
        )
        content = header + yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )
    else:
        content = json.dumps(data, indent=2, ensure_ascii=False)

    path.write_text(content, encoding="utf-8")


def read_hints(path: Path) -> HintsFile:
    """Read hints from YAML or JSON."""
    text = path.read_text(encoding="utf-8")
    if HAS_YAML and path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    return HintsFile.from_dict(data)


# ═══════════════════════════════════════════════════════════════════════════
# 6. VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_hints(hints: HintsFile, schema_dir: Path) -> list[str]:
    """Validate hints against current schema state. Returns list of issues."""
    issues: list[str] = []

    # Gather current definitions
    current_defs: set[str] = set()
    for jf in sorted(schema_dir.glob("*.json")):
        for def_name, _ in _extract_defs(jf):
            current_defs.add(def_name)

    # Check for defs in hints that no longer exist
    all_hinted: set[str] = set()
    for cat in hints.categories:
        for member in cat.members:
            all_hinted.add(member)
            if member not in current_defs:
                issues.append(f"[STALE] '{member}' in category '{cat.name}' no longer exists in schemas")

    for member in hints.uncategorized:
        all_hinted.add(member)
        if member not in current_defs:
            issues.append(f"[STALE] '{member}' in uncategorized list no longer exists")

    # Check for current defs not covered by hints
    missing = current_defs - all_hinted - set(hints.uncategorized)
    for name in sorted(missing):
        issues.append(f"[MISSING] '{name}' exists in schemas but not in hints — run --update")

    # Check for duplicate assignments
    seen: dict[str, str] = {}
    for cat in hints.categories:
        for member in cat.members:
            if member in seen:
                issues.append(f"[DUPLICATE] '{member}' assigned to both '{seen[member]}' and '{cat.name}'")
            seen[member] = cat.name

    # Check for empty categories
    for cat in hints.categories:
        if not cat.members:
            issues.append(f"[EMPTY] Category '{cat.name}' has no members")

    return issues


# ═══════════════════════════════════════════════════════════════════════════
# 7. LLM PROMPT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def generate_llm_prompt(hints: HintsFile, schema_dir: Path) -> str:
    """
    Generate a prompt that an LLM can use to improve the hints file.

    This is the bridge between automated clustering and human/LLM refinement.
    """
    # Gather some context about uncategorized defs
    uncategorized_analyses: list[dict[str, Any]] = []
    for jf in sorted(schema_dir.glob("*.json")):
        for def_name, def_body in _extract_defs(jf):
            if def_name in hints.uncategorized:
                uncategorized_analyses.append(_analyze_def(def_name, def_body))

    existing_cats = "\n".join(
        f"  - {c.name}: {', '.join(c.members[:8])}"
        f"{'...' if len(c.members) > 8 else ''}"
        for c in hints.categories
    )

    uncategorized_list = "\n".join(
        f"  - {a['name']} (suffix: {a['suffix']}, refs: {', '.join(a['ref_names'][:5])})"
        for a in uncategorized_analyses[:50]
    )

    return f"""\
You are analyzing a JSON Schema ecosystem to improve clustering of definitions
into meaningful categories. Below are the current auto-generated categories and
a list of uncategorized definitions.

TASK: For each uncategorized definition, either:
  1. Assign it to an existing category
  2. Propose a new category (with name, description, and keywords)
  3. Mark it as intentionally uncategorized (if it truly doesn't fit)

Also review existing categories — merge, rename, or split them if needed.

CURRENT CATEGORIES:
{existing_cats}

UNCATEGORIZED DEFINITIONS ({len(hints.uncategorized)} total):
{uncategorized_list}

OUTPUT FORMAT (YAML):
```yaml
actions:
  # Assign to existing category
  - action: assign
    definition: "DefinitionName"
    category: "Existing Category Name"

  # Create new category
  - action: create_category
    name: "New Category Name"
    description: "What this category represents"
    keywords: ["keyword1", "keyword2"]
    members: ["Def1", "Def2"]

  # Merge categories
  - action: merge
    from: "Source Category"
    into: "Target Category"

  # Rename category
  - action: rename
    from: "Old Name"
    to: "New Name"

  # Intentionally uncategorized
  - action: skip
    definition: "DefinitionName"
    reason: "Why it doesn't fit any category"
```

Be precise with definition names — they are case-sensitive.
Aim for 8-15 well-balanced categories.
"""


# ═══════════════════════════════════════════════════════════════════════════
# 8. CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and maintain clustering hints for schema_tree.py.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python schema_hints.py session-02/schemas/              # generate .schema-hints.yaml
  python schema_hints.py session-02/schemas/ --update      # update with new defs
  python schema_hints.py session-02/schemas/ --diff        # show what changed
  python schema_hints.py session-02/schemas/ --validate    # check consistency
  python schema_hints.py session-02/schemas/ --llm-prompt  # generate LLM improvement prompt
""",
    )
    parser.add_argument("schema_dir", type=Path,
                        help="Directory containing JSON Schema files.")
    parser.add_argument("--update", action="store_true",
                        help="Update existing hints with new definitions.")
    parser.add_argument("--diff", action="store_true",
                        help="Show what would change (dry run of --update).")
    parser.add_argument("--validate", action="store_true",
                        help="Validate hints against current schemas.")
    parser.add_argument("--llm-prompt", action="store_true",
                        help="Generate LLM prompt for improving categorization.")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Output path (default: <schema_dir>/.schema-hints.yaml).")

    args = parser.parse_args()
    schema_dir = args.schema_dir.resolve()

    if not schema_dir.is_dir():
        print(f"ERROR: Not a directory: {schema_dir}", file=sys.stderr)
        return 1

    hints_path = args.output or (schema_dir / HINTS_FILENAME)

    # ── Validate ─────────────────────────────────────────────────────────
    if args.validate:
        if not hints_path.is_file():
            print(f"ERROR: No hints file found: {hints_path}", file=sys.stderr)
            return 1
        hints = read_hints(hints_path)
        issues = validate_hints(hints, schema_dir)
        if issues:
            print(f"\n  Found {len(issues)} issue(s):\n")
            for issue in issues:
                print(f"    {issue}")
            print()
        else:
            print("\n  Hints file is valid and up to date.\n")
        return 1 if issues else 0

    # ── LLM Prompt ───────────────────────────────────────────────────────
    if args.llm_prompt:
        if not hints_path.is_file():
            print("  No existing hints — generating fresh hints first...\n")
            hints = generate_hints(schema_dir)
            write_hints(hints, hints_path)
            print(f"  Written: {hints_path}\n")
        else:
            hints = read_hints(hints_path)
        prompt = generate_llm_prompt(hints, schema_dir)
        print(prompt)
        return 0

    # ── Update ───────────────────────────────────────────────────────────
    if args.update or args.diff:
        if not hints_path.is_file():
            print(f"  No existing hints file. Generating fresh: {hints_path}")
            hints = generate_hints(schema_dir)
            write_hints(hints, hints_path)
            print(f"  Written: {hints_path}")
            print(f"  {hints.definition_count} definitions, {len(hints.categories)} categories")
            return 0

        existing = read_hints(hints_path)
        updated, diff = update_hints(schema_dir, existing)

        print(f"\n  Schema Hints Update Diff:")
        print(f"  {'─' * 50}")
        print(f"  New definitions:     {len(diff['new_definitions'])}")
        print(f"  Removed definitions: {len(diff['removed_definitions'])}")
        print(f"  New files:           {len(diff['new_files'])}")
        print(f"  Removed files:       {len(diff['removed_files'])}")
        print(f"  Total definitions:   {diff['current_total']}")

        if diff["new_definitions"]:
            print(f"\n  New definitions:")
            for name in diff["new_definitions"][:30]:
                print(f"    + {name}")
            if len(diff["new_definitions"]) > 30:
                print(f"    ... and {len(diff['new_definitions']) - 30} more")

        if diff["removed_definitions"]:
            print(f"\n  Removed definitions:")
            for name in diff["removed_definitions"][:30]:
                print(f"    - {name}")

        if args.diff:
            print(f"\n  (Dry run — no changes written. Use --update to apply.)\n")
        else:
            write_hints(updated, hints_path)
            print(f"\n  Updated: {hints_path}\n")

        return 0

    # ── Generate (fresh) ─────────────────────────────────────────────────
    if hints_path.is_file():
        print(f"  Hints file already exists: {hints_path}")
        print(f"  Use --update to incorporate new schemas, or delete to regenerate.")
        return 1

    hints = generate_hints(schema_dir)
    write_hints(hints, hints_path)

    categorized = sum(len(c.members) for c in hints.categories)
    print(f"\n  Generated: {hints_path}")
    print(f"  Schema files:    {len(hints.schema_files)}")
    print(f"  Definitions:     {hints.definition_count}")
    print(f"  Categories:      {len(hints.categories)}")
    print(f"  Categorized:     {categorized} ({categorized/hints.definition_count*100:.0f}%)")
    print(f"  Uncategorized:   {len(hints.uncategorized)}")
    print()
    print(f"  Categories:")
    for cat in sorted(hints.categories, key=lambda c: -len(c.members)):
        print(f"    {cat.name:30s}  {len(cat.members):3d} members  [{cat.source}]")
    print()
    print(f"  Next steps:")
    print(f"    1. Review and edit {hints_path}")
    print(f"    2. Run: python schema_hints.py {schema_dir} --validate")
    print(f"    3. Run: python schema_hints.py {schema_dir} --llm-prompt  (for LLM refinement)")
    print(f"    4. schema_tree.py will auto-detect and use the hints file.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
