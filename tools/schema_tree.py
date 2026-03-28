#!/usr/bin/env python3
"""
schema_tree.py — Schema genealogy / "tree of life" builder.

Inspects a folder of JSON Schema files, extracts lineage relationships
($ref, allOf, anyOf, oneOf, $defs inheritance, cross-file references),
and renders the result as an ASCII tree, Mermaid diagram, or JSON graph.

Usage:
    python schema_tree.py <schema_dir>                  # ASCII tree
    python schema_tree.py <schema_dir> --mermaid        # Mermaid flowchart
    python schema_tree.py <schema_dir> --json           # JSON graph
    python schema_tree.py <schema_dir> --dot            # Graphviz DOT
    python schema_tree.py <schema_dir> --html           # D3 force-directed graph
    python schema_tree.py <schema_dir> --tree           # Phylogenetic lineage tree
    python schema_tree.py <schema_dir> --report         # Markdown analysis report
    python schema_tree.py <schema_dir> --report --usage # Report with code usage stats
    python schema_tree.py <schema_dir> -v               # Verbose: show edge reasons
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# 1. DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SchemaNode:
    """A node in the schema genealogy tree."""
    id: str                       # unique key: "file:defName" or "file" for root
    label: str                    # display name
    file: str                     # source filename
    schema_id: str = ""           # $id if present
    title: str = ""               # title if present
    version: str = ""             # schemaVersion / schema_version
    description: str = ""         # truncated description
    kind: str = "schema"          # "schema" | "definition" | "patch" | "vocabulary"
    def_count: int = 0            # number of $defs
    property_count: int = 0       # number of top-level properties
    properties: list[str] = field(default_factory=list)


@dataclass
class SchemaEdge:
    """A directed edge between two nodes."""
    source: str                   # node id
    target: str                   # node id
    relation: str                 # edge type
    detail: str = ""              # human-readable detail

    # Edge relation types:
    #   "inherits"       — allOf $ref (type inheritance)
    #   "composes"       — anyOf / oneOf $ref (union/variant)
    #   "references"     — $ref in properties (field-level reference)
    #   "defines"        — parent schema → $defs child
    #   "patches"        — patch/extension document → base schema
    #   "evolves"        — version lineage (v1 → v2)
    #   "duplicates"     — same $id found in multiple files


@dataclass
class SchemaGraph:
    """The full genealogy graph."""
    nodes: dict[str, SchemaNode] = field(default_factory=dict)
    edges: list[SchemaEdge] = field(default_factory=list)
    _schema_dir: str = ""  # set by caller for description-based lineage

    def add_node(self, node: SchemaNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: SchemaEdge) -> None:
        self.edges.append(edge)

    def roots(self) -> list[str]:
        """Nodes with no incoming edges (tree roots)."""
        has_incoming = {e.target for e in self.edges}
        return [nid for nid in self.nodes if nid not in has_incoming]

    def children(self, node_id: str) -> list[tuple[str, str]]:
        """Return (child_id, relation) for direct children."""
        return [(e.target, e.relation) for e in self.edges if e.source == node_id]


# ═══════════════════════════════════════════════════════════════════════════
# 2. SCHEMA PARSER
# ═══════════════════════════════════════════════════════════════════════════

def _extract_version(data: dict) -> str:
    """Try to extract a schema/document version."""
    for key in ("schemaVersion", "schema_version", "version"):
        if key in data:
            v = data[key]
            if isinstance(v, dict) and "const" in v:
                return str(v["const"])
            if isinstance(v, str):
                return v
    # Check properties for version with const
    props = data.get("properties", {})
    for key in ("schemaVersion", "schema_version", "version"):
        if key in props:
            p = props[key]
            if isinstance(p, dict) and "const" in p:
                return str(p["const"])
            if isinstance(p, dict) and "default" in p:
                return str(p["default"])
    # Fallback: extract version from description or title
    for text_field in ("description", "title"):
        text = data.get(text_field, "")
        if text:
            # Match patterns like "v3.0.0", "version 3.1.0", "Version: 1.0.0"
            m = re.search(r'(?:version[:\s]+|v)(\d+\.\d+\.\d+)', text, re.IGNORECASE)
            if m:
                return m.group(1)
    return ""


def _is_patch(data: dict, filename: str) -> bool:
    """Detect if a file is a patch/extension document."""
    fname = filename.lower()
    if any(k in fname for k in ("patch", "extension")):
        return True
    if "_integrationPoints" in data or "integrationPoints" in data:
        return True
    return False


def _is_vocabulary(data: dict) -> bool:
    """Detect non-schema vocabulary/term-map files."""
    if "$schema" not in data and "terms" in data:
        return True
    if "axes" in data and "terms" in data:
        return True
    return False


def _collect_refs(obj: Any, refs: list[str], context: str = "") -> None:
    """Recursively collect all $ref strings from a JSON structure."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            refs.append(obj["$ref"])
        for k, v in obj.items():
            _collect_refs(v, refs, context=k)
    elif isinstance(obj, list):
        for item in obj:
            _collect_refs(item, refs, context=context)


def _collect_composition_refs(obj: Any) -> dict[str, list[str]]:
    """Collect $refs organized by composition keyword (allOf, anyOf, oneOf)."""
    result: dict[str, list[str]] = {"allOf": [], "anyOf": [], "oneOf": [], "ref": []}

    if isinstance(obj, dict):
        if "$ref" in obj:
            result["ref"].append(obj["$ref"])

        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in obj:
                items = obj[keyword]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "$ref" in item:
                            result[keyword].append(item["$ref"])

        for k, v in obj.items():
            if k not in ("allOf", "anyOf", "oneOf", "$ref"):
                sub = _collect_composition_refs(v)
                for key in result:
                    result[key].extend(sub[key])
    elif isinstance(obj, list):
        for item in obj:
            sub = _collect_composition_refs(item)
            for key in result:
                result[key].extend(sub[key])

    return result


def parse_schema_file(filepath: Path, graph: SchemaGraph) -> str | None:
    """Parse a single schema file and add nodes/edges to the graph. Returns root node id."""
    try:
        text = filepath.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as e:
        print(f"  [WARN] Skipping {filepath.name}: {e}", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        return None

    fname = filepath.name
    file_key = filepath.stem

    # Determine kind
    if _is_vocabulary(data):
        kind = "vocabulary"
    elif _is_patch(data, fname):
        kind = "patch"
    else:
        kind = "schema"

    # Extract metadata
    schema_id = data.get("$id", "")
    title = data.get("title", "")
    version = _extract_version(data)
    description = data.get("description", "")[:120]
    defs = data.get("$defs", data.get("definitions", {}))
    props = data.get("properties", {})

    # Create root node for this file
    root_id = file_key
    root_node = SchemaNode(
        id=root_id,
        label=title or file_key,
        file=fname,
        schema_id=schema_id,
        title=title,
        version=version,
        description=description,
        kind=kind,
        def_count=len(defs) if isinstance(defs, dict) else 0,
        property_count=len(props) if isinstance(props, dict) else 0,
        properties=list(props.keys())[:20] if isinstance(props, dict) else [],
    )
    graph.add_node(root_node)

    # Create nodes for each $def
    if isinstance(defs, dict):
        for def_name, def_body in defs.items():
            if not isinstance(def_body, dict):
                continue
            def_id = f"{file_key}:{def_name}"
            def_desc = def_body.get("description", "")[:80]
            def_props = def_body.get("properties", {})

            # Check if def uses allOf (inheritance pattern)
            def_prop_keys = []
            if isinstance(def_props, dict):
                def_prop_keys = list(def_props.keys())
            # allOf often wraps properties — collect ALL for accurate counts
            if "allOf" in def_body and isinstance(def_body["allOf"], list):
                for item in def_body["allOf"]:
                    if isinstance(item, dict) and "properties" in item:
                        def_prop_keys.extend(list(item["properties"].keys()))

            def_node = SchemaNode(
                id=def_id,
                label=def_name,
                file=fname,
                kind="definition",
                description=def_desc,
                property_count=len(def_prop_keys),
                properties=def_prop_keys,
            )
            graph.add_node(def_node)

            # Edge: schema → defines → definition
            graph.add_edge(SchemaEdge(
                source=root_id,
                target=def_id,
                relation="defines",
                detail=f"$defs/{def_name}",
            ))

            # Analyze composition within this definition
            comp_refs = _collect_composition_refs(def_body)

            for ref_str in comp_refs["allOf"]:
                target_id = _resolve_ref(ref_str, file_key)
                if target_id:
                    graph.add_edge(SchemaEdge(
                        source=def_id,
                        target=target_id,
                        relation="inherits",
                        detail=f"allOf → {ref_str}",
                    ))

            for ref_str in comp_refs["anyOf"]:
                target_id = _resolve_ref(ref_str, file_key)
                if target_id:
                    graph.add_edge(SchemaEdge(
                        source=def_id,
                        target=target_id,
                        relation="composes",
                        detail=f"anyOf → {ref_str}",
                    ))

            for ref_str in comp_refs["oneOf"]:
                target_id = _resolve_ref(ref_str, file_key)
                if target_id:
                    graph.add_edge(SchemaEdge(
                        source=def_id,
                        target=target_id,
                        relation="composes",
                        detail=f"oneOf → {ref_str}",
                    ))

            # Property-level $refs (not from allOf/anyOf/oneOf)
            prop_refs: list[str] = []
            _collect_refs(def_props, prop_refs)
            # Also check allOf items for properties
            if "allOf" in def_body:
                for item in def_body["allOf"]:
                    if isinstance(item, dict) and "properties" in item:
                        _collect_refs(item["properties"], prop_refs)
            for ref_str in set(prop_refs):
                target_id = _resolve_ref(ref_str, file_key)
                if target_id and target_id != def_id:
                    graph.add_edge(SchemaEdge(
                        source=def_id,
                        target=target_id,
                        relation="references",
                        detail=f"property → {ref_str}",
                    ))

    # ── Root-level property $refs → $defs edges ──────────────────────────
    # Bug fix: root properties often $ref into $defs (e.g. "story": {"$ref": "#/$defs/Story"})
    # These edges are needed for orphan detection accuracy.
    if isinstance(props, dict):
        root_prop_refs: list[str] = []
        _collect_refs(props, root_prop_refs)
        for ref_str in set(root_prop_refs):
            target_id = _resolve_ref(ref_str, file_key)
            if target_id and target_id != root_id:
                graph.add_edge(SchemaEdge(
                    source=root_id,
                    target=target_id,
                    relation="references",
                    detail=f"root property → {ref_str}",
                ))

    return root_id


def _resolve_ref(ref: str, current_file_key: str) -> str | None:
    """Resolve a $ref string to a node id."""
    if ref.startswith("#/$defs/") or ref.startswith("#/definitions/"):
        # Internal reference
        def_name = ref.split("/")[-1]
        return f"{current_file_key}:{def_name}"
    if ref.startswith("#/"):
        # Internal path reference — skip for now
        return None
    if ref.startswith("http://") or ref.startswith("https://"):
        # External URI — could map to another file's $id
        return None
    # Relative file reference
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 3. CROSS-FILE LINEAGE DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def detect_lineage(graph: SchemaGraph) -> None:
    """Detect cross-file relationships: evolution, patches, duplicates."""
    file_nodes = [n for n in graph.nodes.values() if n.kind in ("schema", "patch", "vocabulary")]

    # Group by $id to find duplicates / shared lineage
    by_id: dict[str, list[SchemaNode]] = defaultdict(list)
    for n in file_nodes:
        if n.schema_id:
            by_id[n.schema_id].append(n)

    for schema_id, nodes in by_id.items():
        if len(nodes) > 1:
            for i in range(1, len(nodes)):
                graph.add_edge(SchemaEdge(
                    source=nodes[0].id,
                    target=nodes[i].id,
                    relation="duplicates",
                    detail=f"Shared $id: {schema_id}",
                ))

    # Detect version evolution by grouping schemas with similar names
    versioned: dict[str, list[SchemaNode]] = defaultdict(list)
    for n in file_nodes:
        if n.kind == "patch":
            continue
        # Normalize name: remove version markers
        base = re.sub(r'[-_]v?\d+(\.\d+)*$', '', n.id.lower())
        base = re.sub(r'[-_]schema$', '', base)
        versioned[base].append(n)

    for base_name, nodes in versioned.items():
        if len(nodes) < 2:
            continue
        # Sort by version string
        nodes.sort(key=lambda n: n.version or "0")
        for i in range(1, len(nodes)):
            graph.add_edge(SchemaEdge(
                source=nodes[i - 1].id,
                target=nodes[i].id,
                relation="evolves",
                detail=f"{nodes[i-1].version or '?'} → {nodes[i].version or '?'}",
            ))

    # Detect patches → base schema
    patches = [n for n in file_nodes if n.kind == "patch"]
    schemas = [n for n in file_nodes if n.kind == "schema"]
    for patch in patches:
        # Find the schema it patches (by shared $id prefix or name similarity)
        for schema in schemas:
            if schema.schema_id and patch.schema_id and schema.schema_id == patch.schema_id:
                graph.add_edge(SchemaEdge(
                    source=patch.id,
                    target=schema.id,
                    relation="patches",
                    detail=f"Extension patch → {schema.label}",
                ))
                break
        else:
            # Heuristic: patch filename contains part of a schema filename
            patch_stem = patch.id.lower()
            for schema in schemas:
                schema_stem = schema.id.lower()
                # Check overlap
                if any(word in schema_stem for word in patch_stem.split('-') if len(word) > 3):
                    graph.add_edge(SchemaEdge(
                        source=patch.id,
                        target=schema.id,
                        relation="patches",
                        detail=f"Patch → {schema.label} (name similarity)",
                    ))
                    break

    # ── Description-based lineage: parse description/title for file references ──
    # Schemas often declare lineage in their description field, e.g.:
    #   "Merges video-project-schema-v2.json and generative_video_project_package_schema.json"
    #   "See video-project-schema-v2.json for the full enhanced schema"
    file_stems = {n.id: n for n in file_nodes}
    file_names = {n.file: n for n in file_nodes}

    for node in file_nodes:
        # Search in description, title, and full raw description
        search_text = f"{node.title} {node.description}"
        # Also check the raw data for longer description
        for fpath in [Path(graph._schema_dir) / node.file] if hasattr(graph, '_schema_dir') else []:
            if fpath.exists():
                try:
                    raw = json.loads(fpath.read_text())
                    search_text += " " + raw.get("description", "")
                except Exception:
                    pass

        # Find references to other schema files by name
        for other in file_nodes:
            if other.id == node.id:
                continue
            # Check for filename mention (exact or partial stem match)
            other_stem = Path(other.file).stem
            # Normalize to a canonical form for fuzzy matching
            def _norm(s: str) -> str:
                return s.lower().replace("-", "_").replace(".", "_")
            other_norm = _norm(other_stem)
            text_norm = _norm(search_text)
            # Match full filename OR a substantial substring of the normalized stem (>15 chars)
            # Also try dropping common prefixes (chatgpt-, claude-, grok-, manus-, perplexity-)
            other_variants = [other_norm]
            for prefix in ("chatgpt_", "claude_", "grok_", "manus_", "perplexity_"):
                if other_norm.startswith(prefix):
                    other_variants.append(other_norm[len(prefix):])
            name_match = (
                other.file in search_text
                or any(len(v) > 15 and v in text_norm for v in other_variants)
            )
            if name_match:
                # Determine relation type from context
                text_lower = search_text.lower()
                if "merge" in text_lower or "combines" in text_lower:
                    rel = "evolves"
                    detail = f"description: merges {other.file}"
                elif "see " in text_lower or "successor" in text_lower or "enhanced" in text_lower:
                    rel = "evolves"
                    detail = f"description: references successor {other.file}"
                else:
                    rel = "evolves"
                    detail = f"description: references {other.file}"

                # Avoid duplicate edges
                exists = any(
                    e.source in (node.id, other.id) and e.target in (node.id, other.id)
                    and e.relation in ("evolves", "patches")
                    for e in graph.edges
                )
                if not exists:
                    graph.add_edge(SchemaEdge(
                        source=other.id,  # referenced file is the source/ancestor
                        target=node.id,   # file containing the reference is the successor
                        relation=rel,
                        detail=detail,
                    ))

    # Detect shared $defs names across files (convergent definitions)
    defs_by_name: dict[str, list[SchemaNode]] = defaultdict(list)
    for n in graph.nodes.values():
        if n.kind == "definition":
            defs_by_name[n.label].append(n)

    # We don't create edges for shared names — just note them for reporting


# ═══════════════════════════════════════════════════════════════════════════
# 4. GRAPH STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def compute_stats(graph: SchemaGraph) -> dict[str, Any]:
    """Compute summary statistics about the schema graph."""
    file_nodes = [n for n in graph.nodes.values() if n.kind != "definition"]
    def_nodes = [n for n in graph.nodes.values() if n.kind == "definition"]

    edge_types = defaultdict(int)
    for e in graph.edges:
        edge_types[e.relation] += 1

    # Find most-referenced definitions
    ref_count: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        if e.relation in ("inherits", "references", "composes"):
            ref_count[e.target] += 1
    most_referenced = sorted(ref_count.items(), key=lambda x: -x[1])[:15]

    # Shared definition names across files
    defs_by_name: dict[str, list[str]] = defaultdict(list)
    for n in def_nodes:
        defs_by_name[n.label].append(n.file)
    shared_defs = {name: files for name, files in defs_by_name.items() if len(set(files)) > 1}

    # Inheritance chains: find deepest
    def _chain_depth(node_id: str, visited: set | None = None) -> int:
        if visited is None:
            visited = set()
        if node_id in visited:
            return 0
        visited.add(node_id)
        parent_edges = [e for e in graph.edges
                        if e.source == node_id and e.relation == "inherits"]
        if not parent_edges:
            return 0
        return 1 + max(_chain_depth(e.target, visited) for e in parent_edges)

    inheritance_depths = {}
    for n in def_nodes:
        depth = _chain_depth(n.id)
        if depth > 0:
            inheritance_depths[n.id] = depth

    return {
        "files": len(file_nodes),
        "definitions_total": len(def_nodes),
        "edges_total": len(graph.edges),
        "edge_types": dict(edge_types),
        "most_referenced": [(nid, graph.nodes[nid].label if nid in graph.nodes else nid, cnt)
                            for nid, cnt in most_referenced],
        "shared_definitions": {name: sorted(set(files)) for name, files in
                               sorted(shared_defs.items())[:20]},
        "deepest_inheritance": sorted(inheritance_depths.items(), key=lambda x: -x[1])[:10],
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. RENDERERS
# ═══════════════════════════════════════════════════════════════════════════

# ── Symbols ──────────────────────────────────────────────────────────────

RELATION_SYMBOLS = {
    "defines":    "◆",
    "inherits":   "◀",
    "composes":   "◇",
    "references": "→",
    "patches":    "⚡",
    "evolves":    "↑",
    "duplicates": "≡",
}

KIND_SYMBOLS = {
    "schema":     "📄",
    "definition": "🔷",
    "patch":      "🩹",
    "vocabulary": "📖",
}


# ── ASCII Tree ───────────────────────────────────────────────────────────

def render_ascii(graph: SchemaGraph, *, verbose: bool = False, hints_path: Path | None = None) -> str:
    """Render the schema graph as an ASCII tree."""
    lines: list[str] = []
    lines.append("")
    lines.append("╔══════════════════════════════════════════════════════════════╗")
    lines.append("║          SCHEMA GENEALOGY — TREE OF LIFE                   ║")
    lines.append("╚══════════════════════════════════════════════════════════════╝")
    lines.append("")

    # Part 1: File-level lineage
    lines.append("─── FILE LINEAGE ─────────────────────────────────────────────")
    lines.append("")

    file_nodes = sorted(
        [n for n in graph.nodes.values() if n.kind != "definition"],
        key=lambda n: (n.kind, n.version or "0", n.label),
    )

    for node in file_nodes:
        sym = KIND_SYMBOLS.get(node.kind, "?")
        ver = f" v{node.version}" if node.version else ""
        defs = f" ({node.def_count} defs)" if node.def_count else ""
        lines.append(f"  {sym} {node.label}{ver}{defs}")
        lines.append(f"     {node.file}")
        if node.schema_id:
            lines.append(f"     $id: {node.schema_id}")

        # Show cross-file edges
        for edge in graph.edges:
            if edge.source == node.id and edge.relation in ("evolves", "patches", "duplicates"):
                sym2 = RELATION_SYMBOLS[edge.relation]
                target = graph.nodes.get(edge.target)
                tlabel = target.label if target else edge.target
                lines.append(f"     {sym2} {edge.relation} → {tlabel} ({edge.detail})")

        lines.append("")

    # Part 2: Definition inheritance trees (per file)
    lines.append("─── DEFINITION TREES ─────────────────────────────────────────")

    for file_node in file_nodes:
        if file_node.def_count == 0:
            continue

        lines.append("")
        lines.append(f"  {KIND_SYMBOLS.get(file_node.kind, '?')} {file_node.label}")

        # Get all definitions for this file
        file_defs = {nid: n for nid, n in graph.nodes.items()
                     if n.file == file_node.file and n.kind == "definition"}

        if not file_defs:
            continue

        # Find "root" definitions: those that inherit from nothing
        inherits_from = set()
        for e in graph.edges:
            if e.relation == "inherits" and e.source in file_defs:
                inherits_from.add(e.source)

        # Also find which defs are inherited BY others (parent defs)
        is_parent = set()
        for e in graph.edges:
            if e.relation == "inherits" and e.target in file_defs:
                is_parent.add(e.target)

        # Root defs = parent defs that don't inherit, or defs with no inheritance edges
        base_defs = sorted(is_parent - inherits_from)
        # Add standalone defs (neither parent nor child in inheritance)
        standalone = sorted(set(file_defs.keys()) - is_parent - inherits_from)

        # Render base types with their inheritance subtrees
        if base_defs:
            lines.append("  │")
            lines.append("  ├── Base Types (inherited by others)")
            rendered = set()
            for i, base_id in enumerate(base_defs):
                base_node = file_defs[base_id]
                is_last = (i == len(base_defs) - 1) and not standalone
                prefix = "  │   └── " if is_last else "  │   ├── "
                ref_count = sum(1 for e in graph.edges
                                if e.target == base_id and e.relation in ("inherits", "references"))
                refs_tag = f" (referenced {ref_count}x)" if ref_count > 1 else ""
                lines.append(f"{prefix}◀ {base_node.label}{refs_tag}")
                rendered.add(base_id)

                # Show children that inherit from this base
                children = [(e.source, e.detail) for e in graph.edges
                            if e.target == base_id and e.relation == "inherits"
                            and e.source in file_defs]
                child_prefix = "  │   │   " if not is_last else "  │       "
                for j, (child_id, detail) in enumerate(sorted(children)):
                    child_node = file_defs[child_id]
                    is_last_child = j == len(children) - 1
                    cpfx = "└── " if is_last_child else "├── "
                    lines.append(f"{child_prefix}{cpfx}{child_node.label}")
                    rendered.add(child_id)

        # Render categories of standalone definitions
        if standalone:
            # Group by common prefix/suffix patterns
            categories = _categorize_defs(standalone, file_defs, graph=graph, hints_path=hints_path)

            for cat_name, cat_ids in sorted(categories.items()):
                lines.append("  │")
                lines.append(f"  ├── {cat_name}")
                for k, def_id in enumerate(sorted(cat_ids)):
                    node = file_defs[def_id]
                    is_last_in_cat = k == len(cat_ids) - 1
                    prefix = "  │   └── " if is_last_in_cat else "  │   ├── "
                    props_tag = ""
                    if verbose and node.properties:
                        props_tag = f"  [{', '.join(node.properties[:5])}]"
                    lines.append(f"{prefix}{node.label}{props_tag}")

    # Part 3: Statistics
    stats = compute_stats(graph)
    lines.append("")
    lines.append("─── STATISTICS ───────────────────────────────────────────────")
    lines.append("")
    lines.append(f"  Schema files:   {stats['files']}")
    lines.append(f"  Definitions:    {stats['definitions_total']}")
    lines.append(f"  Relationships:  {stats['edges_total']}")
    lines.append(f"  Edge breakdown: {json.dumps(stats['edge_types'])}")
    lines.append("")

    if stats["most_referenced"]:
        lines.append("  Most referenced definitions:")
        for nid, label, cnt in stats["most_referenced"][:10]:
            lines.append(f"    {cnt:3d}x  {label}")
        lines.append("")

    if stats["shared_definitions"]:
        lines.append("  Shared definitions (same name, multiple files):")
        for name, files in list(stats["shared_definitions"].items())[:15]:
            lines.append(f"    {name} — {', '.join(f for f in files)}")
        lines.append("")

    if stats["deepest_inheritance"]:
        lines.append("  Deepest inheritance chains:")
        for nid, depth in stats["deepest_inheritance"][:5]:
            label = graph.nodes[nid].label if nid in graph.nodes else nid
            lines.append(f"    depth {depth}: {label}")
        lines.append("")

    return "\n".join(lines)


def _categorize_defs(
    def_ids: list[str],
    nodes: dict[str, SchemaNode],
    graph: SchemaGraph | None = None,
    hints_path: Path | None = None,
) -> dict[str, list[str]]:
    """Group definitions into categories.

    If a .schema-hints.yaml exists, uses it as the primary source for
    categorization and falls back to auto-clustering for uncovered defs.
    """
    hints_cats = _load_hints_categories(hints_path) if hints_path else None

    if hints_cats:
        return _apply_hints(def_ids, nodes, hints_cats, graph=graph)
    return _auto_categorize_defs(def_ids, nodes, graph=graph)


def _load_hints_categories(hints_path: Path | None) -> dict[str, list[str]] | None:
    """Try to load category hints from a .schema-hints.yaml file."""
    if hints_path is None or not hints_path.is_file():
        return None
    try:
        text = hints_path.read_text(encoding="utf-8")
        if hints_path.suffix in (".yaml", ".yml"):
            try:
                import yaml as _yaml
                data = _yaml.safe_load(text)
            except ImportError:
                return None
        else:
            data = json.loads(text)
        if not isinstance(data, dict) or "categories" not in data:
            return None
        result: dict[str, list[str]] = {}
        for cat in data["categories"]:
            name = cat.get("name", "")
            members = cat.get("members", [])
            keywords = cat.get("keywords", [])
            if name and (members or keywords):
                result[name] = {"members": members, "keywords": keywords}
        return result
    except Exception:
        return None


def _apply_hints(
    def_ids: list[str],
    nodes: dict[str, SchemaNode],
    hints: dict[str, Any],
    graph: SchemaGraph | None = None,
) -> dict[str, list[str]]:
    """Apply hint-based categorization, falling back to auto for uncovered defs."""
    categories: dict[str, list[str]] = defaultdict(list)
    assigned: set[str] = set()
    def_id_set = set(def_ids)

    # Map definition label → def_id for matching
    label_to_ids: dict[str, list[str]] = defaultdict(list)
    for did in def_ids:
        label_to_ids[nodes[did].label].append(did)

    for cat_name, cat_data in hints.items():
        members = cat_data.get("members", []) if isinstance(cat_data, dict) else cat_data
        keywords = cat_data.get("keywords", []) if isinstance(cat_data, dict) else []

        # Direct member assignment
        if isinstance(members, list):
            for member_name in members:
                for did in label_to_ids.get(member_name, []):
                    if did not in assigned:
                        categories[cat_name].append(did)
                        assigned.add(did)

        # Keyword matching for unassigned defs
        if isinstance(keywords, list):
            for did in def_ids:
                if did in assigned:
                    continue
                label_lower = nodes[did].label.lower()
                if any(kw.lower() in label_lower for kw in keywords):
                    categories[cat_name].append(did)
                    assigned.add(did)

    # Auto-cluster anything the hints didn't cover
    uncovered = [did for did in def_ids if did not in assigned]
    if uncovered:
        auto_cats = _auto_categorize_defs(uncovered, nodes, graph=graph)
        for cat_name, cat_ids in auto_cats.items():
            if cat_name in categories:
                categories[cat_name].extend(cat_ids)
            else:
                categories[cat_name] = cat_ids

    return {k: v for k, v in categories.items() if v}


# ── Hardcoded categorizer (baseline for scoring) ────────────────────────

_HARDCODED_PATTERNS: list[tuple[str, list[str], str]] = [
    # (category_name, keywords/suffixes, match_mode: "suffix" | "contains")
    ("Entity Types",     ["entity"],                                                    "suffix"),
    ("Asset Types",      ["asset"],                                                     "contains"),
    ("Spatial / 3D",     ["spatial", "position", "quaternion", "euler", "orientation",
                          "transform", "coordinate", "bounding", "scale3"],             "contains"),
    ("Composition Ops",  ["op"],                                                        "suffix"),
    ("Workflow",         ["workflow", "generation", "operation", "orchestration",
                          "pipeline"],                                                  "contains"),
    ("Quality / QA",     ["qa", "qc", "validation", "approval", "compliance",
                          "governance"],                                                "contains"),
    ("Time / Media",     ["timecode", "timerange", "framerate", "resolution",
                          "aspectratio", "timeline", "duration"],                       "contains"),
    ("Primitives",       ["semver", "ulid", "iso", "ref", "identifier", "uri"],         "contains"),
    ("Documentation",    ["comment", "note", "log", "tag", "annotation"],               "contains"),
    ("Rights / Legal",   ["rights", "license", "copy", "compliance"],                   "contains"),
    ("Localization",     ["localization", "accessibility", "i18n"],                      "contains"),
]


def _hardcoded_categorize_defs(
    def_ids: list[str], nodes: dict[str, SchemaNode],
) -> dict[str, list[str]]:
    """Baseline categorizer with domain-specific hardcoded patterns."""
    categories: dict[str, list[str]] = defaultdict(list)
    assigned: set[str] = set()

    for cat_name, keywords, mode in _HARDCODED_PATTERNS:
        for def_id in def_ids:
            if def_id in assigned:
                continue
            label = nodes[def_id].label.lower()
            if mode == "suffix":
                matched = any(label.endswith(kw) for kw in keywords)
            else:
                matched = any(kw in label for kw in keywords)
            if matched:
                categories[cat_name].append(def_id)
                assigned.add(def_id)

    for def_id in def_ids:
        if def_id not in assigned:
            categories["Other"].append(def_id)

    return {k: v for k, v in categories.items() if v}


# ── Auto-clustering categorizer ─────────────────────────────────────────

def _split_camel(name: str) -> list[str]:
    """Split CamelCase into lowercase tokens.  'AudioMixOp' → ['audio','mix','op']"""
    parts = re.sub(r'([A-Z])', r' \1', name).split()
    return [p.lower() for p in parts if p]


def _auto_categorize_defs(
    def_ids: list[str],
    nodes: dict[str, SchemaNode],
    graph: SchemaGraph | None = None,
) -> dict[str, list[str]]:
    """
    Auto-cluster definitions by detecting common suffixes, shared tokens,
    and (optionally) graph co-reference patterns.

    Strategy:
      1. Split each definition name into CamelCase tokens.
      2. Extract LAST token as suffix cluster (Entity, Op, Node, Spec, ...).
      3. For remaining defs, cluster by shared FIRST token (prefix).
      4. For still-remaining defs, cluster by shared interior token.
      5. If graph provided: cluster remaining defs by co-reference —
         defs that reference (or are referenced by) the same hub type
         are likely in the same domain.
      6. MERGE pass: consolidate small clusters into nearest larger cluster
         by token overlap, or into "Other".
      7. Everything leftover → "Other".

    Thresholds scale with total def count to stay useful at any size.
    """
    if not def_ids:
        return {}

    n = len(def_ids)
    log_n = math.log2(max(n, 2))
    # Adaptive thresholds using log-scaling:
    #   n=50  → 3/3/4/3/7     n=346 → 4/4/6/5/10     n=1000 → 5/5/7/6/12
    MIN_SUFFIX = max(2, round(log_n / 2))
    MIN_PREFIX = max(3, round(log_n / 2))
    MIN_INTERIOR = max(3, round(log_n / 1.5))
    MIN_COREF = max(3, round(log_n / 2))
    MERGE_BELOW = max(3, round(log_n / 1.8))
    TARGET_CLUSTERS = max(6, min(18, round(log_n * 1.2)))

    labels: dict[str, str] = {did: nodes[did].label for did in def_ids}
    tokens: dict[str, list[str]] = {did: _split_camel(labels[did]) for did in def_ids}
    token_sets: dict[str, set[str]] = {did: set(tokens[did]) for did in def_ids}

    categories: dict[str, list[str]] = defaultdict(list)
    assigned: set[str] = set()

    # ── Pass 1: Suffix clustering ────────────────────────────────────────
    suffix_groups: dict[str, list[str]] = defaultdict(list)
    for did in def_ids:
        toks = tokens[did]
        if toks:
            suffix_groups[toks[-1]].append(did)

    for suffix, members in sorted(suffix_groups.items(), key=lambda x: -len(x[1])):
        if len(members) < MIN_SUFFIX:
            continue
        if len(suffix) <= 1:
            continue
        cat_name = _suffix_to_label(suffix)
        for did in members:
            if did not in assigned:
                categories[cat_name].append(did)
                assigned.add(did)

    # ── Pass 2: Prefix clustering (first token) ─────────────────────────
    prefix_groups: dict[str, list[str]] = defaultdict(list)
    for did in def_ids:
        if did in assigned:
            continue
        toks = tokens[did]
        if toks:
            prefix_groups[toks[0]].append(did)

    for prefix, members in sorted(prefix_groups.items(), key=lambda x: -len(x[1])):
        if len(members) < MIN_PREFIX:
            continue
        if len(prefix) <= 2:
            continue
        cat_name = prefix.capitalize() + "-related"
        for did in members:
            if did not in assigned:
                categories[cat_name].append(did)
                assigned.add(did)

    # ── Pass 3: Shared interior token clustering ─────────────────────────
    interior_groups: dict[str, list[str]] = defaultdict(list)
    for did in def_ids:
        if did in assigned:
            continue
        toks = tokens[did]
        for tok in toks:
            if len(tok) > 3:
                interior_groups[tok].append(did)

    for tok, members in sorted(interior_groups.items(), key=lambda x: -len(x[1])):
        unassigned_members = [m for m in members if m not in assigned]
        if len(unassigned_members) < MIN_INTERIOR:
            continue
        cat_name = tok.capitalize() + "-related"
        if cat_name in categories:
            cat_name = tok.capitalize() + " types"
        for did in unassigned_members:
            if did not in assigned:
                categories[cat_name].append(did)
                assigned.add(did)

    # ── Pass 4: Co-reference clustering (graph-aware) ──────────────────
    # Defs that share many graph neighbors likely belong together.
    # For each unassigned def, build a "neighbor fingerprint" (set of defs
    # it references or is referenced by). Group defs with high overlap.
    if graph is not None:
        unassigned_ids = [did for did in def_ids if did not in assigned]
        if len(unassigned_ids) >= MIN_COREF * 2:
            # Build neighbor fingerprints
            neighbors: dict[str, set[str]] = defaultdict(set)
            for e in graph.edges:
                if e.relation in ("inherits", "references", "composes"):
                    neighbors[e.source].add(e.target)
                    neighbors[e.target].add(e.source)

            # Greedy clustering: pick the unassigned def with most unassigned
            # neighbors, form a cluster, repeat.
            remaining = set(unassigned_ids)
            while len(remaining) >= MIN_COREF:
                # Find the def with the most connections to other remaining defs
                best_seed = None
                best_connected: set[str] = set()
                for did in remaining:
                    connected = neighbors.get(did, set()) & remaining - {did}
                    if len(connected) > len(best_connected):
                        best_seed = did
                        best_connected = connected

                if best_seed is None or len(best_connected) < MIN_COREF - 1:
                    break

                # Form cluster: seed + its connected neighbors within remaining
                cluster = {best_seed} | best_connected

                # Expand: add any remaining def that connects to >= 50% of cluster
                for did in list(remaining - cluster):
                    overlap = len(neighbors.get(did, set()) & cluster)
                    if overlap >= len(cluster) * 0.4:
                        cluster.add(did)

                if len(cluster) < MIN_COREF:
                    # Not enough — skip this seed
                    remaining.discard(best_seed)
                    continue

                # Name the cluster from the most common tokens in its members
                cluster_toks: dict[str, int] = defaultdict(int)
                for did in cluster:
                    for tok in tokens.get(did, []):
                        if len(tok) > 2:
                            cluster_toks[tok] += 1
                top_tok = max(cluster_toks, key=cluster_toks.get) if cluster_toks else "misc"
                cat_name = top_tok.capitalize() + " group"
                # Avoid duplicates
                while cat_name in categories:
                    cat_name = cat_name + "+"

                for did in cluster:
                    if did not in assigned:
                        categories[cat_name].append(did)
                        assigned.add(did)
                remaining -= cluster

    # ── Pass 5: Merge small clusters ─────────────────────────────────────
    # Find the best larger cluster to absorb each small cluster, using
    # token overlap between cluster members as the similarity signal.

    def _cluster_tokens(cat_ids: list[str]) -> set[str]:
        """Collect all tokens across a cluster's members."""
        result: set[str] = set()
        for did in cat_ids:
            result.update(token_sets.get(did, set()))
        return result

    merged = True
    while merged:
        merged = False
        small_cats = [k for k, v in categories.items()
                      if k != "Other" and len(v) < MERGE_BELOW]
        if not small_cats:
            break

        large_cats = {k: _cluster_tokens(v) for k, v in categories.items()
                      if k != "Other" and len(v) >= MERGE_BELOW}

        for small_name in small_cats:
            if small_name not in categories:
                continue
            small_toks = _cluster_tokens(categories[small_name])
            small_members = categories[small_name]

            # Find best large cluster by Jaccard similarity of token sets
            best_target = None
            best_sim = 0.0
            for large_name, large_toks in large_cats.items():
                if large_name == small_name:
                    continue
                intersection = len(small_toks & large_toks)
                union = len(small_toks | large_toks)
                sim = intersection / union if union else 0
                if sim > best_sim:
                    best_sim = sim
                    best_target = large_name

            if best_target and best_sim >= 0.15:
                # Merge into the best target
                categories[best_target].extend(small_members)
                # Update large_cats token set
                large_cats[best_target] = large_cats[best_target] | small_toks
                del categories[small_name]
                merged = True
            else:
                # No good match — dump to Other
                categories["Other"].extend(small_members)
                del categories[small_name]
                merged = True

    # ── Pass 5: If too many clusters remain, merge smallest into nearest ──
    while len([k for k in categories if k != "Other"]) > TARGET_CLUSTERS:
        non_other = {k: v for k, v in categories.items() if k != "Other"}
        if len(non_other) <= TARGET_CLUSTERS:
            break
        # Find smallest non-Other cluster
        smallest_name = min(non_other, key=lambda k: len(non_other[k]))
        smallest_toks = _cluster_tokens(categories[smallest_name])
        smallest_members = categories[smallest_name]

        # Find best merge target
        best_target = None
        best_sim = -1.0
        for other_name, other_ids in non_other.items():
            if other_name == smallest_name:
                continue
            other_toks = _cluster_tokens(other_ids)
            intersection = len(smallest_toks & other_toks)
            union = len(smallest_toks | other_toks)
            sim = intersection / union if union else 0
            if sim > best_sim:
                best_sim = sim
                best_target = other_name

        if best_target and best_sim >= 0.05:
            categories[best_target].extend(smallest_members)
            del categories[smallest_name]
        else:
            categories["Other"].extend(smallest_members)
            del categories[smallest_name]

    # ── Remainder → Other ────────────────────────────────────────────────
    for did in def_ids:
        if did not in assigned and did not in categories.get("Other", []):
            categories["Other"].append(did)

    return {k: v for k, v in categories.items() if v}


def _suffix_to_label(suffix: str) -> str:
    """Convert a raw suffix token to a human-readable cluster label."""
    # Pluralize and title-case common suffixes
    known = {
        "entity": "Entity Types",
        "op": "Operations",
        "node": "Nodes",
        "spec": "Specifications",
        "config": "Configuration",
        "asset": "Assets",
        "ref": "References",
        "record": "Records",
        "rule": "Rules",
        "check": "Checks",
        "step": "Steps",
        "field": "Fields",
        "map": "Maps",
        "info": "Info Types",
        "result": "Results",
        "controls": "Controls",
        "profile": "Profiles",
    }
    if suffix in known:
        return known[suffix]
    # Generic: capitalize + "Types"
    return suffix.capitalize() + " types"


# ── Clustering quality scoring ───────────────────────────────────────────

@dataclass
class ClusterScore:
    """Quality metrics for a clustering result."""
    name: str                     # "auto" | "hardcoded"
    num_clusters: int             # excluding "Other"
    coverage: float               # % of defs NOT in "Other"
    mean_cluster_size: float      # avg size of non-Other clusters
    size_stddev: float            # stddev of cluster sizes (lower = more balanced)
    singleton_clusters: int       # clusters with only 1 member
    largest_cluster_pct: float    # % of defs in the largest non-Other cluster
    other_pct: float              # % of defs in "Other"
    composite: float = 0.0       # weighted composite score (0–100)


def score_clustering(
    categories: dict[str, list[str]],
    total: int,
    name: str = "",
) -> ClusterScore:
    """Score a clustering result on multiple quality dimensions."""
    non_other = {k: v for k, v in categories.items() if k != "Other"}
    other_count = len(categories.get("Other", []))

    num_clusters = len(non_other)
    if total == 0:
        return ClusterScore(name=name, num_clusters=0, coverage=0, mean_cluster_size=0,
                            size_stddev=0, singleton_clusters=0, largest_cluster_pct=0,
                            other_pct=100, composite=0)

    covered = total - other_count
    coverage = covered / total

    sizes = [len(v) for v in non_other.values()]
    mean_size = sum(sizes) / len(sizes) if sizes else 0
    variance = sum((s - mean_size) ** 2 for s in sizes) / len(sizes) if sizes else 0
    stddev = math.sqrt(variance)
    singletons = sum(1 for s in sizes if s == 1)
    largest_pct = max(sizes) / total if sizes else 0
    other_pct = other_count / total

    # Composite score (0–100):
    #   coverage (0–1) × 35   — reward classifying more defs
    #   cluster_count_score    — reward having meaningful number of clusters (sweet spot 5–15)
    #   balance_score          — penalize very uneven clusters
    #   singleton_penalty      — penalize too many singletons
    #   other_penalty          — penalize large "Other" bucket

    # Cluster count score: peak at ~8 clusters, falls off on both sides
    if num_clusters == 0:
        count_score = 0
    else:
        ideal = 8
        count_score = max(0, 1.0 - abs(num_clusters - ideal) / ideal)

    # Balance: normalized stddev (lower = better)
    balance = 1.0 - min(1.0, stddev / mean_size) if mean_size > 0 else 0

    # Singleton ratio
    singleton_ratio = singletons / num_clusters if num_clusters else 0
    singleton_penalty = 1.0 - singleton_ratio

    # Other ratio (smaller = better)
    other_score = 1.0 - other_pct

    composite = (
        coverage * 35 +
        count_score * 20 +
        balance * 20 +
        singleton_penalty * 10 +
        other_score * 15
    )

    return ClusterScore(
        name=name,
        num_clusters=num_clusters,
        coverage=coverage,
        mean_cluster_size=round(mean_size, 1),
        size_stddev=round(stddev, 1),
        singleton_clusters=singletons,
        largest_cluster_pct=round(largest_pct, 3),
        other_pct=round(other_pct, 3),
        composite=round(composite, 1),
    )


def compare_clusterings(
    def_ids: list[str],
    nodes: dict[str, SchemaNode],
    graph: SchemaGraph | None = None,
) -> dict[str, Any]:
    """Run both clustering strategies and return a comparison dict."""
    auto = _auto_categorize_defs(def_ids, nodes, graph=graph)
    hardcoded = _hardcoded_categorize_defs(def_ids, nodes)
    total = len(def_ids)

    auto_score = score_clustering(auto, total, name="auto")
    hard_score = score_clustering(hardcoded, total, name="hardcoded")

    # Agreement: for each def, check if both strategies assigned it to the
    # same cluster (by membership, not name).  Compute pairwise agreement ratio.
    # Use Rand Index: fraction of pairs that are (both same-cluster) or (both diff-cluster)
    # in both clusterings.
    auto_map = {}
    for cat, ids in auto.items():
        for did in ids:
            auto_map[did] = cat
    hard_map = {}
    for cat, ids in hardcoded.items():
        for did in ids:
            hard_map[did] = cat

    agree_same = 0
    agree_diff = 0
    disagree = 0
    n = len(def_ids)
    for i in range(n):
        for j in range(i + 1, n):
            a_same = auto_map.get(def_ids[i]) == auto_map.get(def_ids[j])
            h_same = hard_map.get(def_ids[i]) == hard_map.get(def_ids[j])
            if a_same == h_same:
                if a_same:
                    agree_same += 1
                else:
                    agree_diff += 1
            else:
                disagree += 1

    total_pairs = agree_same + agree_diff + disagree
    rand_index = (agree_same + agree_diff) / total_pairs if total_pairs else 1.0

    return {
        "auto": {"categories": auto, "score": auto_score},
        "hardcoded": {"categories": hardcoded, "score": hard_score},
        "rand_index": round(rand_index, 4),
        "agreement_pairs": agree_same + agree_diff,
        "disagreement_pairs": disagree,
        "total_pairs": total_pairs,
    }


# ── Mermaid ──────────────────────────────────────────────────────────────

def render_mermaid(graph: SchemaGraph, *, detail: str = "files") -> str:
    """Render as a Mermaid flowchart.

    detail: "files" — only file-level nodes
            "defs"  — include top definitions (capped)
            "full"  — everything (can be huge)
    """
    lines: list[str] = []
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("")

    # Sanitize ID for Mermaid
    def mid(s: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_]', '_', s)

    # Determine which nodes to include
    if detail == "files":
        include = {n.id for n in graph.nodes.values() if n.kind != "definition"}
    elif detail == "defs":
        # Files + base types + most-referenced defs (top 30)
        include = {n.id for n in graph.nodes.values() if n.kind != "definition"}
        ref_count: dict[str, int] = defaultdict(int)
        for e in graph.edges:
            if e.relation in ("inherits", "references", "composes"):
                ref_count[e.target] += 1
        top_defs = sorted(ref_count.items(), key=lambda x: -x[1])[:30]
        include.update(nid for nid, _ in top_defs)
    else:
        include = set(graph.nodes.keys())

    # Nodes
    for nid, node in graph.nodes.items():
        if nid not in include:
            continue
        m = mid(nid)
        ver = f" v{node.version}" if node.version else ""
        defs = f"\\n{node.def_count} defs" if node.def_count else ""
        if node.kind == "schema":
            lines.append(f'    {m}["{node.label}{ver}{defs}"]')
        elif node.kind == "patch":
            lines.append(f'    {m}{{"🩹 {node.label}{ver}"}}')
        elif node.kind == "vocabulary":
            lines.append(f'    {m}[/"📖 {node.label}"/]')
        else:
            lines.append(f'    {m}(["{node.label}"])')

    lines.append("")

    # Edges
    edge_styles = {
        "evolves":    "-->|evolves|",
        "patches":    "-.->|patches|",
        "inherits":   "-->|inherits|",
        "composes":   "-..->|composes|",
        "references": "-->|refs|",
        "defines":    "-->|defines|",
        "duplicates": "<-.->|dup|",
    }

    seen_edges = set()
    for e in graph.edges:
        if e.source not in include or e.target not in include:
            continue
        key = (e.source, e.target, e.relation)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        style = edge_styles.get(e.relation, "-->")
        lines.append(f"    {mid(e.source)} {style} {mid(e.target)}")

    # Styling
    lines.append("")
    lines.append("    classDef schema fill:#4a90d9,stroke:#2c5f8a,color:#fff")
    lines.append("    classDef patch fill:#f5a623,stroke:#c47d10,color:#fff")
    lines.append("    classDef vocab fill:#7ed321,stroke:#5a9e18,color:#fff")
    lines.append("    classDef defn fill:#9b59b6,stroke:#7d3c98,color:#fff")

    for nid, node in graph.nodes.items():
        if nid not in include:
            continue
        cls = {"schema": "schema", "patch": "patch", "vocabulary": "vocab",
               "definition": "defn"}.get(node.kind, "")
        if cls:
            lines.append(f"    class {mid(nid)} {cls}")

    lines.append("```")
    return "\n".join(lines)


# ── Graphviz DOT ─────────────────────────────────────────────────────────

def render_dot(graph: SchemaGraph, *, detail: str = "defs") -> str:
    """Render as Graphviz DOT."""
    lines: list[str] = []
    lines.append("digraph SchemaGenealogy {")
    lines.append('    rankdir=TB;')
    lines.append('    fontname="Helvetica";')
    lines.append('    node [fontname="Helvetica", fontsize=10];')
    lines.append('    edge [fontname="Helvetica", fontsize=8];')
    lines.append("")

    def did(s: str) -> str:
        return '"' + s.replace('"', '\\"') + '"'

    # Determine included nodes
    if detail == "files":
        include = {n.id for n in graph.nodes.values() if n.kind != "definition"}
    elif detail == "defs":
        include = {n.id for n in graph.nodes.values() if n.kind != "definition"}
        ref_count: dict[str, int] = defaultdict(int)
        for e in graph.edges:
            if e.relation in ("inherits", "references", "composes"):
                ref_count[e.target] += 1
        top_defs = sorted(ref_count.items(), key=lambda x: -x[1])[:40]
        include.update(nid for nid, _ in top_defs)
    else:
        include = set(graph.nodes.keys())

    # Group by file (subgraph clusters)
    by_file: dict[str, list[str]] = defaultdict(list)
    for nid, node in graph.nodes.items():
        if nid in include:
            by_file[node.file].append(nid)

    colors = {
        "schema": "#4a90d9", "patch": "#f5a623",
        "vocabulary": "#7ed321", "definition": "#d4a5e8",
    }
    shapes = {
        "schema": "box", "patch": "hexagon",
        "vocabulary": "parallelogram", "definition": "ellipse",
    }

    for fname, nids in by_file.items():
        lines.append(f'    subgraph "cluster_{fname}" {{')
        lines.append(f'        label="{fname}";')
        lines.append('        style=dashed; color="#999999";')
        for nid in nids:
            node = graph.nodes[nid]
            ver = f"\\nv{node.version}" if node.version else ""
            shape = shapes.get(node.kind, "box")
            color = colors.get(node.kind, "#cccccc")
            lines.append(f'        {did(nid)} [label="{node.label}{ver}", '
                         f'shape={shape}, style=filled, fillcolor="{color}"];')
        lines.append("    }")

    lines.append("")

    # Edges
    edge_styles = {
        "evolves":    'color="#2ecc71", penwidth=2, style=bold',
        "patches":    'color="#f39c12", style=dashed',
        "inherits":   'color="#3498db"',
        "composes":   'color="#9b59b6", style=dashed',
        "references": 'color="#95a5a6", style=dotted',
        "defines":    'color="#bdc3c7", style=dotted, arrowsize=0.5',
        "duplicates": 'color="#e74c3c", style=dashed, dir=both',
    }

    for e in graph.edges:
        if e.source not in include or e.target not in include:
            continue
        style = edge_styles.get(e.relation, "")
        label = e.relation
        lines.append(f'    {did(e.source)} -> {did(e.target)} [{style}, label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


# ── JSON ─────────────────────────────────────────────────────────────────

def render_json(graph: SchemaGraph) -> str:
    """Render as JSON graph."""
    data = {
        "nodes": [asdict(n) for n in graph.nodes.values()],
        "edges": [asdict(e) for e in graph.edges],
        "stats": compute_stats(graph),
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── Usage scanning ───────────────────────────────────────────────────────

def scan_usage(graph: SchemaGraph, schema_dir: Path) -> dict[str, dict]:
    """
    Grep the parent directory tree for code references to each schema file.

    Returns {filename: {"code_refs": int, "files": [str], "lifecycle": str}}.
    Lifecycle: "active" (>0 code refs), "superseded" (only in docs/changelogs),
               "orphaned" (0 refs anywhere).
    """
    search_root = schema_dir.parent
    file_nodes = [n for n in graph.nodes.values() if n.kind in ("schema", "patch", "vocabulary")]
    results: dict[str, dict] = {}

    for node in file_nodes:
        fname = node.file
        code_refs = 0
        ref_files: list[str] = []

        # Search for filename mentions in code files
        for ext in ("*.py", "*.ts", "*.js", "*.json", "*.md", "*.yaml", "*.yml"):
            for match_file in search_root.rglob(ext):
                if match_file.name == fname:
                    continue  # skip the schema file itself
                if "__pycache__" in str(match_file) or "node_modules" in str(match_file):
                    continue
                try:
                    content = match_file.read_text(errors="ignore")
                    if fname in content:
                        rel = str(match_file.relative_to(search_root))
                        ref_files.append(rel)
                        # Code vs docs distinction
                        if match_file.suffix in (".py", ".ts", ".js"):
                            code_refs += 1
                except Exception:
                    continue

        # Classify lifecycle
        if code_refs > 0:
            lifecycle = "active"
        elif ref_files:
            lifecycle = "superseded"
        else:
            lifecycle = "orphaned"

        results[fname] = {
            "code_refs": code_refs,
            "total_refs": len(ref_files),
            "files": ref_files[:10],
            "lifecycle": lifecycle,
        }

    return results


# ── Markdown Report ──────────────────────────────────────────────────────

def render_report(graph: SchemaGraph, schema_dir: Path, *, hints_path: Path | None = None, usage: dict | None = None) -> str:
    """Render a comprehensive Markdown analysis report."""
    stats = compute_stats(graph)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    file_nodes = sorted(
        [n for n in graph.nodes.values() if n.kind != "definition"],
        key=lambda n: (-n.def_count, n.label),
    )
    def_nodes = [n for n in graph.nodes.values() if n.kind == "definition"]

    # ── Pre-compute analysis data ────────────────────────────────────────

    # Coupling: how many cross-def references each definition has
    outgoing_refs: dict[str, int] = defaultdict(int)
    incoming_refs: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        if e.relation in ("inherits", "references", "composes"):
            outgoing_refs[e.source] += 1
            incoming_refs[e.target] += 1

    # Hub definitions: high incoming refs = heavily depended upon
    hubs = sorted(
        [(nid, cnt) for nid, cnt in incoming_refs.items() if nid in graph.nodes],
        key=lambda x: -x[1],
    )[:20]

    # Connector definitions: high outgoing refs = tightly coupled
    connectors = sorted(
        [(nid, cnt) for nid, cnt in outgoing_refs.items()
         if nid in graph.nodes and graph.nodes[nid].kind == "definition"],
        key=lambda x: -x[1],
    )[:15]

    # Orphan definitions: no incoming or outgoing refs (excluding "defines")
    ref_edges = [e for e in graph.edges if e.relation != "defines"]
    has_refs = {e.source for e in ref_edges} | {e.target for e in ref_edges}
    orphans = [n for n in def_nodes if n.id not in has_refs]

    # Shared definitions across files
    defs_by_name: dict[str, list[SchemaNode]] = defaultdict(list)
    for n in def_nodes:
        defs_by_name[n.label].append(n)
    shared_defs = {
        name: nodes for name, nodes in defs_by_name.items()
        if len(set(n.file for n in nodes)) > 1
    }

    # Convergent vs divergent: shared defs with same vs different property counts
    convergent = []
    divergent = []
    for name, nodes in sorted(shared_defs.items()):
        files = sorted(set(n.file for n in nodes))
        prop_counts = [n.property_count for n in nodes]
        prop_sets = [set(n.properties) for n in nodes]
        if len(set(prop_counts)) == 1 and len(prop_sets) > 0 and len(set(map(frozenset, prop_sets))) == 1:
            convergent.append((name, files))
        else:
            divergent.append((name, files, prop_counts, [n.properties[:8] for n in nodes]))

    # Inheritance trees
    base_types: dict[str, list[str]] = defaultdict(list)  # parent → [children]
    for e in graph.edges:
        if e.relation == "inherits":
            base_types[e.target].append(e.source)

    # Composition unions
    union_types: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        if e.relation == "composes":
            union_types[e.target].append(e.source)

    # File size distribution (by def count)
    total_defs = sum(n.def_count for n in file_nodes)

    # Category distribution — run both clusterings globally for comparison
    all_def_ids = [n.id for n in def_nodes]
    all_def_nodes = {n.id: n for n in def_nodes}
    clustering_comparison = compare_clusterings(all_def_ids, all_def_nodes, graph=graph)

    all_categories: dict[str, int] = defaultdict(int)
    for cat, ids in clustering_comparison["auto"]["categories"].items():
        all_categories[cat] += len(ids)

    # ── Build report ─────────────────────────────────────────────────────

    L: list[str] = []

    def h1(t: str) -> None: L.append(f"\n# {t}\n")
    def h2(t: str) -> None: L.append(f"\n## {t}\n")
    def h3(t: str) -> None: L.append(f"\n### {t}\n")
    def p(t: str) -> None: L.append(f"{t}\n")
    def bullet(t: str) -> None: L.append(f"- {t}")
    def row(*cols: str) -> None: L.append("| " + " | ".join(cols) + " |")
    def sep(n: int) -> None: L.append("| " + " | ".join(["---"] * n) + " |")

    h1("Schema Genealogy Report")
    p(f"> Auto-generated analysis of `{schema_dir}`")
    p(f"> Generated: {now}")

    # ── 1. Executive Summary ─────────────────────────────────────────────

    h2("1. Executive Summary")
    p("This report analyzes the structural composition, inheritance patterns, "
      "cross-file relationships, and health indicators of a JSON Schema ecosystem.")

    row("Metric", "Value")
    sep(2)
    row("Schema files", str(stats["files"]))
    row("Total definitions ($defs)", str(stats["definitions_total"]))
    row("Total relationships", str(stats["edges_total"]))
    row("Inheritance edges (allOf)", str(stats["edge_types"].get("inherits", 0)))
    row("Composition edges (anyOf/oneOf)", str(stats["edge_types"].get("composes", 0)))
    row("Reference edges (property $ref)", str(stats["edge_types"].get("references", 0)))
    row("Cross-file shared definitions", str(len(shared_defs)))
    row("Orphan definitions (unreferenced)", str(len(orphans)))

    # ── 2. Schema File Census ────────────────────────────────────────────

    h2("2. Schema File Census")

    if usage:
        row("File", "Kind", "Version", "$defs", "Props", "% defs", "Code refs", "Lifecycle")
        sep(8)
        for n in file_nodes:
            pct = f"{n.def_count / total_defs * 100:.1f}%" if total_defs else "0%"
            props = str(n.property_count) if n.property_count else "-"
            u = usage.get(n.file, {})
            code = str(u.get("code_refs", 0))
            lc = u.get("lifecycle", "?")
            lc_badge = {"active": "**active**", "superseded": "superseded", "orphaned": "~~orphaned~~"}.get(lc, lc)
            row(f"`{n.file}`", n.kind, n.version or "-", str(n.def_count), props, pct, code, lc_badge)
    else:
        row("File", "Kind", "Version", "$defs", "Properties", "% of total defs")
        sep(6)
        for n in file_nodes:
            pct = f"{n.def_count / total_defs * 100:.1f}%" if total_defs else "0%"
            props = str(n.property_count) if n.property_count else "-"
            row(f"`{n.file}`", n.kind, n.version or "-", str(n.def_count), props, pct)

    p("")
    p("**Observation:** " + _census_observation(file_nodes, total_defs))

    # ── 3. Inheritance Analysis ──────────────────────────────────────────

    h2("3. Inheritance Analysis (allOf)")

    if base_types:
        p("Definitions using `allOf` to extend a base type — the classical "
          "object-oriented inheritance pattern in JSON Schema.")
        L.append("")

        for parent_id, child_ids in sorted(base_types.items(),
                                           key=lambda x: -len(x[1])):
            parent = graph.nodes.get(parent_id)
            if not parent:
                continue
            parent_label = parent.label
            children_labels = []
            for cid in sorted(child_ids):
                cn = graph.nodes.get(cid)
                if cn:
                    children_labels.append(cn.label)

            h3(f"`{parent_label}` ({len(children_labels)} subtypes)")
            p(f"Defined in `{parent.file}`")
            if parent.properties:
                p(f"Inherited properties: `{'`, `'.join(parent.properties[:10])}`")
            p("")
            p("Subtypes:")
            for cl in children_labels:
                bullet(f"`{cl}`")
            L.append("")

        # Depth analysis
        if stats["deepest_inheritance"]:
            h3("Inheritance Depth")
            p("Maximum depth of inheritance chains (deeper = more layered abstraction).")
            L.append("")
            row("Definition", "Depth")
            sep(2)
            for nid, depth in stats["deepest_inheritance"]:
                label = graph.nodes[nid].label if nid in graph.nodes else nid
                row(f"`{label}`", str(depth))
    else:
        p("No `allOf`-based inheritance detected.")

    # ── 4. Composition Analysis ──────────────────────────────────────────

    h2("4. Composition Analysis (anyOf / oneOf)")

    if union_types:
        p("Definitions used as variants in discriminated unions or flexible type alternatives.")
        L.append("")
        row("Union target", "Used by (count)", "Consumers")
        sep(3)
        for target_id, source_ids in sorted(union_types.items(),
                                            key=lambda x: -len(x[1])):
            tn = graph.nodes.get(target_id)
            if not tn:
                continue
            consumers = ", ".join(f"`{graph.nodes[s].label}`"
                                  for s in sorted(set(source_ids))[:6]
                                  if s in graph.nodes)
            if len(source_ids) > 6:
                consumers += f" +{len(source_ids)-6} more"
            row(f"`{tn.label}`", str(len(source_ids)), consumers)
    else:
        p("No `anyOf`/`oneOf` composition detected.")

    # ── 5. Hub & Coupling Analysis ───────────────────────────────────────

    h2("5. Hub & Coupling Analysis")

    h3("5.1 Hub Definitions (most depended upon)")
    p("These are the foundational types that many other definitions reference. "
      "Changes to hubs have the widest blast radius.")
    L.append("")
    row("Definition", "Incoming refs", "File", "Risk")
    sep(4)
    for nid, cnt in hubs[:15]:
        node = graph.nodes.get(nid)
        if not node:
            continue
        risk = "CRITICAL" if cnt >= 20 else "HIGH" if cnt >= 10 else "MODERATE" if cnt >= 5 else "LOW"
        row(f"`{node.label}`", str(cnt), f"`{node.file}`", f"**{risk}**")

    h3("5.2 Most-Coupled Definitions (highest outgoing refs)")
    p("Definitions that reference many other types. High coupling can indicate "
      "a \"god object\" or a legitimate aggregation root.")
    L.append("")
    row("Definition", "Outgoing refs", "File")
    sep(3)
    for nid, cnt in connectors[:10]:
        node = graph.nodes.get(nid)
        if not node:
            continue
        row(f"`{node.label}`", str(cnt), f"`{node.file}`")

    # Coupling density metric
    if def_nodes:
        ref_edge_count = sum(1 for e in graph.edges if e.relation in ("inherits", "references", "composes"))
        max_possible = len(def_nodes) * (len(def_nodes) - 1)
        density = ref_edge_count / max_possible if max_possible else 0
        h3("5.3 Coupling Density")
        p(f"**{density:.4f}** ({ref_edge_count} reference edges / {max_possible} possible)")
        if density < 0.005:
            p("Interpretation: Loosely coupled — definitions are relatively independent.")
        elif density < 0.02:
            p("Interpretation: Moderately coupled — healthy level of interconnection.")
        else:
            p("Interpretation: Tightly coupled — consider breaking into smaller schemas.")

    # ── 6. Cross-File Convergence ────────────────────────────────────────

    h2("6. Cross-File Convergence & Divergence")
    p(f"**{len(shared_defs)}** definition names appear in multiple schema files. "
      "This reveals where schemas converge on shared concepts vs. where they diverge.")

    if convergent:
        h3("6.1 Convergent Definitions (identical structure)")
        p("These definitions share the same name AND the same property structure "
          "across files — strong candidates for extraction into a shared schema.")
        L.append("")
        row("Definition", "Files")
        sep(2)
        for name, files in convergent[:20]:
            row(f"`{name}`", ", ".join(f"`{f}`" for f in files))

    if divergent:
        h3("6.2 Divergent Definitions (same name, different structure)")
        p("These share a name but differ in property count or shape — potential "
          "incompatibilities or intentional evolution.")
        L.append("")
        row("Definition", "Files", "Property counts")
        sep(3)
        for name, files, pcounts, _ in divergent[:20]:
            pct_str = " / ".join(str(c) for c in pcounts)
            row(f"`{name}`", ", ".join(f"`{f}`" for f in files), pct_str)

    # ── 7. Category Distribution ─────────────────────────────────────────

    h2("7. Definition Category Distribution")
    p("Definitions auto-clustered by CamelCase token analysis (suffix, prefix, interior tokens).")
    L.append("")

    sorted_cats = sorted(all_categories.items(), key=lambda x: -x[1])
    total_categorized = sum(c for _, c in sorted_cats)

    row("Category", "Count", "% of total")
    sep(3)
    for cat, cnt in sorted_cats:
        pct = f"{cnt / total_categorized * 100:.1f}%" if total_categorized else "0%"
        bar = _bar(cnt, max(c for _, c in sorted_cats) if sorted_cats else 1)
        row(f"**{cat}**", f"{cnt} {bar}", pct)

    # ── 7.1 Clustering Quality Scorecard ─────────────────────────────────

    h3("7.1 Clustering Quality Scorecard")
    p("Compares the auto-clustering (suffix/prefix/token analysis) against a "
      "hardcoded domain-specific baseline. Higher composite = better.")
    L.append("")

    auto_s = clustering_comparison["auto"]["score"]
    hard_s = clustering_comparison["hardcoded"]["score"]

    row("Metric", "Auto-cluster", "Hardcoded baseline", "Explanation")
    sep(4)
    row("Composite score",
        f"**{auto_s.composite}**/100",
        f"**{hard_s.composite}**/100",
        "Weighted combination of all metrics below")
    row("Clusters (excl. Other)",
        str(auto_s.num_clusters),
        str(hard_s.num_clusters),
        "Ideal ~8; too few = too coarse, too many = too fragmented")
    row("Coverage",
        f"{auto_s.coverage:.1%}",
        f"{hard_s.coverage:.1%}",
        "% of defs assigned to a real cluster (not Other)")
    row("Other bucket",
        f"{auto_s.other_pct:.1%}",
        f"{hard_s.other_pct:.1%}",
        "% of defs that fell through all rules — lower = better")
    row("Mean cluster size",
        str(auto_s.mean_cluster_size),
        str(hard_s.mean_cluster_size),
        "Average members per cluster")
    row("Size std deviation",
        str(auto_s.size_stddev),
        str(hard_s.size_stddev),
        "Lower = more balanced cluster sizes")
    row("Singleton clusters",
        str(auto_s.singleton_clusters),
        str(hard_s.singleton_clusters),
        "Clusters with only 1 member — ideally 0")
    row("Largest cluster %",
        f"{auto_s.largest_cluster_pct:.1%}",
        f"{hard_s.largest_cluster_pct:.1%}",
        "Concentration in the biggest cluster")

    L.append("")
    ri = clustering_comparison["rand_index"]
    agree = clustering_comparison["agreement_pairs"]
    disagree = clustering_comparison["disagreement_pairs"]
    total_p = clustering_comparison["total_pairs"]

    p(f"**Rand Index: {ri:.4f}** — pairwise agreement between auto and hardcoded "
      f"({agree:,} agree / {disagree:,} disagree out of {total_p:,} pairs). "
      f"1.0 = identical clustering, 0.5 = random.")

    # Interpretation
    if ri >= 0.95:
        p("The auto-clustering is essentially equivalent to the hardcoded baseline.")
    elif ri >= 0.85:
        p("The auto-clustering closely matches the hardcoded baseline with minor differences.")
    elif ri >= 0.70:
        p("The auto-clustering moderately agrees with the hardcoded baseline — "
          "meaningful structural differences exist.")
    else:
        p("The auto-clustering significantly diverges from the hardcoded baseline — "
          "the two strategies organize definitions very differently.")

    # Show what's different: hardcoded categories not captured by auto
    h3("7.2 Hardcoded Baseline Categories (for reference)")
    p("Categories that the domain-specific hardcoded classifier produces:")
    L.append("")
    hard_cats = clustering_comparison["hardcoded"]["categories"]
    hard_sorted = sorted(hard_cats.items(), key=lambda x: -len(x[1]))
    row("Category", "Count")
    sep(2)
    for cat, ids in hard_sorted:
        row(f"`{cat}`", str(len(ids)))

    # ── 8. Orphan Analysis ───────────────────────────────────────────────

    h2("8. Orphan Definitions")
    p(f"**{len(orphans)}** definitions have no incoming or outgoing reference edges "
      "(excluding the parent `defines` edge). These may be unused, or only "
      "referenced from outside this schema directory.")

    if orphans:
        # Group orphans by file
        orphans_by_file: dict[str, list[str]] = defaultdict(list)
        for n in orphans:
            orphans_by_file[n.file].append(n.label)

        for fname, labels in sorted(orphans_by_file.items()):
            h3(f"`{fname}` ({len(labels)} orphans)")
            for lbl in sorted(labels):
                bullet(f"`{lbl}`")
            L.append("")

    # ── 9. Cross-File Lineage ────────────────────────────────────────────

    h2("9. Cross-File Lineage")

    lineage_edges = [e for e in graph.edges if e.relation in ("evolves", "patches", "duplicates")]
    if lineage_edges:
        row("Relation", "From", "To", "Detail")
        sep(4)
        for e in lineage_edges:
            src = graph.nodes.get(e.source)
            tgt = graph.nodes.get(e.target)
            row(
                f"**{e.relation}**",
                f"`{src.label}`" if src else e.source,
                f"`{tgt.label}`" if tgt else e.target,
                e.detail,
            )
    else:
        p("No cross-file evolution, patches, or duplicates detected.")

    # ── 10. Health Indicators ────────────────────────────────────────────

    h2("10. Health Indicators & Recommendations")

    findings: list[tuple[str, str, str]] = []  # (severity, finding, recommendation)

    # Large schemas
    for n in file_nodes:
        if n.def_count > 100:
            findings.append((
                "WARNING",
                f"`{n.file}` has {n.def_count} definitions",
                "Consider splitting into domain-specific sub-schemas "
                "(entity, workflow, qa, spatial) with $ref across files.",
            ))

    # Heavily referenced hubs
    for nid, cnt in hubs[:5]:
        if cnt >= 20:
            node = graph.nodes.get(nid)
            if node:
                findings.append((
                    "INFO",
                    f"`{node.label}` is referenced {cnt} times",
                    "This is a critical dependency. Ensure it has strong backward "
                    "compatibility guarantees and is tested independently.",
                ))

    # High orphan count
    if len(orphans) > 20:
        findings.append((
            "WARNING",
            f"{len(orphans)} orphan definitions detected",
            "Audit orphans — remove unused ones to reduce schema surface area, "
            "or add explicit references if they are used externally.",
        ))

    # Divergent shared defs
    if len(divergent) > 5:
        findings.append((
            "WARNING",
            f"{len(divergent)} definitions share names but differ across files",
            "Align divergent definitions or use distinct names to avoid "
            "confusion when combining schemas.",
        ))

    # No cross-file lineage
    if not lineage_edges:
        findings.append((
            "INFO",
            "No version evolution edges detected between files",
            "Consider adding $id and version metadata to enable automatic "
            "lineage tracking.",
        ))

    # Patch without base
    patch_nodes = [n for n in file_nodes if n.kind == "patch"]
    for pn in patch_nodes:
        patch_edges = [e for e in graph.edges if e.source == pn.id and e.relation == "patches"]
        if not patch_edges:
            findings.append((
                "WARNING",
                f"Patch `{pn.file}` has no detected base schema",
                "Ensure the patch references a base schema via $id or naming convention.",
            ))

    if findings:
        row("Severity", "Finding", "Recommendation")
        sep(3)
        for sev, finding, rec in findings:
            icon = {"WARNING": "!!", "INFO": "i", "ERROR": "!!!"}
            row(f"**{sev}**", finding, rec)
    else:
        p("No health issues detected.")

    # ── Footer ───────────────────────────────────────────────────────────

    L.append("")
    L.append("---")
    L.append(f"*Report generated by `schema_tree.py --report` on {now}*")
    L.append("")

    return "\n".join(L)


def _census_observation(file_nodes: list[SchemaNode], total_defs: int) -> str:
    """Generate a one-sentence observation about the schema census."""
    if not file_nodes:
        return "No schema files found."

    biggest = max(file_nodes, key=lambda n: n.def_count)
    if biggest.def_count > total_defs * 0.5:
        return (f"The schema ecosystem is dominated by `{biggest.file}` which contains "
                f"{biggest.def_count}/{total_defs} definitions "
                f"({biggest.def_count/total_defs*100:.0f}%). "
                f"This concentration suggests it serves as the unified/canonical schema.")

    kinds = defaultdict(int)
    for n in file_nodes:
        kinds[n.kind] += 1
    parts = [f"{cnt} {kind}(s)" for kind, cnt in sorted(kinds.items())]
    return f"The collection contains {', '.join(parts)} with {total_defs} total definitions."


def _bar(value: int, max_value: int, width: int = 12) -> str:
    """Render a tiny inline bar chart."""
    if max_value == 0:
        return ""
    filled = round(value / max_value * width)
    return "`" + "#" * filled + "." * (width - filled) + "`"


# ── HTML (self-contained with D3) ────────────────────────────────────────

def render_html(graph: SchemaGraph) -> str:
    """Render as a self-contained HTML file with a force-directed graph."""
    nodes_json = json.dumps([
        {
            "id": n.id,
            "label": n.label,
            "kind": n.kind,
            "file": n.file,
            "version": n.version,
            "def_count": n.def_count,
            "group": n.file,
        }
        for n in graph.nodes.values()
        if n.kind != "definition"  # file-level only for HTML (perf)
    ], indent=2)

    # Include top-referenced defs
    ref_count: dict[str, int] = defaultdict(int)
    for e in graph.edges:
        if e.relation in ("inherits", "references", "composes"):
            ref_count[e.target] += 1
    top_def_ids = {nid for nid, cnt in sorted(ref_count.items(), key=lambda x: -x[1])[:50]}

    def_nodes_json = json.dumps([
        {
            "id": n.id,
            "label": n.label,
            "kind": n.kind,
            "file": n.file,
            "version": "",
            "def_count": 0,
            "group": n.file,
        }
        for n in graph.nodes.values()
        if n.kind == "definition" and n.id in top_def_ids
    ], indent=2)

    included = {n.id for n in graph.nodes.values() if n.kind != "definition"} | top_def_ids

    edges_json = json.dumps([
        {
            "source": e.source,
            "target": e.target,
            "relation": e.relation,
            "detail": e.detail,
        }
        for e in graph.edges
        if e.source in included and e.target in included
    ], indent=2)

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Schema Genealogy — Tree of Life</title>
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; background: #1a1a2e; color: #eee; }}
  h1 {{ text-align: center; padding: 16px; margin: 0; font-size: 1.4em; color: #e0e0ff; }}
  svg {{ width: 100%; height: calc(100vh - 60px); }}
  .link {{ stroke-opacity: 0.4; }}
  .link.evolves {{ stroke: #2ecc71; stroke-width: 3; }}
  .link.patches {{ stroke: #f39c12; stroke-dasharray: 6 3; stroke-width: 2; }}
  .link.inherits {{ stroke: #3498db; stroke-width: 1.5; }}
  .link.composes {{ stroke: #9b59b6; stroke-dasharray: 4 2; }}
  .link.references {{ stroke: #555; stroke-dasharray: 2 2; stroke-width: 0.8; }}
  .link.defines {{ stroke: #444; stroke-width: 0.5; }}
  .link.duplicates {{ stroke: #e74c3c; stroke-dasharray: 5 3; }}
  .node-label {{ font-size: 11px; fill: #ddd; pointer-events: none; }}
  .tooltip {{
    position: absolute; background: #16213e; border: 1px solid #444;
    padding: 8px 12px; border-radius: 6px; font-size: 12px;
    pointer-events: none; display: none; max-width: 300px;
  }}
  .legend {{ position: fixed; bottom: 12px; left: 12px; background: #16213e;
    padding: 10px 14px; border-radius: 8px; font-size: 11px; border: 1px solid #333; }}
  .legend div {{ margin: 3px 0; }}
  .legend .swatch {{ display: inline-block; width: 14px; height: 14px;
    border-radius: 50%; vertical-align: middle; margin-right: 6px; }}
</style>
</head>
<body>
<h1>Schema Genealogy &mdash; Tree of Life</h1>
<div class="tooltip" id="tooltip"></div>
<div class="legend">
  <div><span class="swatch" style="background:#4a90d9"></span>Schema</div>
  <div><span class="swatch" style="background:#f5a623"></span>Patch</div>
  <div><span class="swatch" style="background:#7ed321"></span>Vocabulary</div>
  <div><span class="swatch" style="background:#d4a5e8"></span>Definition</div>
</div>
<svg id="graph"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const fileNodes = {nodes_json};
const defNodes = {def_nodes_json};
const nodes = [...fileNodes, ...defNodes];
const links = {edges_json};

const kindColor = {{
  schema: "#4a90d9", patch: "#f5a623",
  vocabulary: "#7ed321", definition: "#d4a5e8"
}};
const kindRadius = {{ schema: 18, patch: 14, vocabulary: 12, definition: 8 }};

const svg = d3.select("#graph");
const width = window.innerWidth;
const height = window.innerHeight - 60;

const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(d =>
    d.relation === "defines" ? 40 : d.relation === "evolves" ? 120 : 80
  ))
  .force("charge", d3.forceManyBody().strength(-200))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collision", d3.forceCollide().radius(d => (kindRadius[d.kind] || 10) + 4));

const g = svg.append("g");

// Zoom
svg.call(d3.zoom().scaleExtent([0.1, 5]).on("zoom", (e) => g.attr("transform", e.transform)));

const link = g.selectAll(".link")
  .data(links).join("line")
  .attr("class", d => "link " + d.relation);

const node = g.selectAll(".node")
  .data(nodes).join("circle")
  .attr("r", d => kindRadius[d.kind] || 10)
  .attr("fill", d => kindColor[d.kind] || "#888")
  .attr("stroke", "#fff")
  .attr("stroke-width", d => d.kind === "definition" ? 0.5 : 1.5)
  .call(d3.drag()
    .on("start", (e, d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on("drag", (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on("end", (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }})
  );

const label = g.selectAll(".node-label")
  .data(nodes).join("text")
  .attr("class", "node-label")
  .attr("dx", d => (kindRadius[d.kind] || 10) + 4)
  .attr("dy", 4)
  .text(d => d.label + (d.version ? " v" + d.version : ""));

const tooltip = document.getElementById("tooltip");
node.on("mouseover", (e, d) => {{
  tooltip.style.display = "block";
  tooltip.innerHTML = `<b>${{d.label}}</b><br>Kind: ${{d.kind}}<br>File: ${{d.file}}` +
    (d.version ? `<br>Version: ${{d.version}}` : "") +
    (d.def_count ? `<br>Definitions: ${{d.def_count}}` : "");
}}).on("mousemove", (e) => {{
  tooltip.style.left = (e.pageX + 12) + "px";
  tooltip.style.top = (e.pageY - 10) + "px";
}}).on("mouseout", () => {{ tooltip.style.display = "none"; }});

sim.on("tick", () => {{
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("cx", d => d.x).attr("cy", d => d.y);
  label.attr("x", d => d.x).attr("y", d => d.y);
}});
</script>
</body>
</html>
"""


# ── Lineage Tree (phylogenetic cladogram) ────────────────────────────────

def render_lineage_tree(graph: SchemaGraph, *, usage: dict | None = None) -> str:
    """
    Render a self-contained HTML phylogenetic lineage tree.

    Layout: horizontal cladogram (left-to-right).
    - Root schemas on the left, derived schemas/defs branch right
    - Branch thickness = number of descendants
    - Node size = property count
    - Color = file of origin
    - Tooltip with full metadata
    - Collapsible subtrees
    """

    # ── Build hierarchical tree data ──────────────────────────────────────
    # Strategy: find root schemas (no incoming evolves/patches),
    # then attach children via evolves/inherits/patches/defines edges.

    file_nodes = {n.id: n for n in graph.nodes.values() if n.kind in ("schema", "patch", "vocabulary")}
    def_nodes = {n.id: n for n in graph.nodes.values() if n.kind == "definition"}

    # Find which nodes have incoming lineage edges
    has_incoming = set()
    lineage_map: dict[str, list[str]] = defaultdict(list)  # parent → [children]
    for e in graph.edges:
        if e.relation in ("evolves", "patches"):
            has_incoming.add(e.target)
            lineage_map[e.source].append(e.target)

    # Inheritance tree: base → subtypes
    inherit_map: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        if e.relation == "inherits":
            inherit_map[e.target].append(e.source)

    # Defines: schema → defs
    defines_map: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        if e.relation == "defines":
            defines_map[e.source].append(e.target)

    def _build_node(nid: str, depth: int = 0) -> dict | None:
        n = graph.nodes.get(nid)
        if not n or depth > 6:
            return None

        # Get usage info
        u = (usage or {}).get(n.file, {})
        lifecycle = u.get("lifecycle", "")

        children = []

        # File-level lineage children (evolves, patches)
        for child_id in lineage_map.get(nid, []):
            child = _build_node(child_id, depth + 1)
            if child:
                children.append(child)

        # For schemas: show top-level base types as branches
        if n.kind in ("schema", "patch") and depth < 3:
            # Find base types defined in this file (definitions with >2 subtypes)
            for def_id in defines_map.get(nid, []):
                subtypes = inherit_map.get(def_id, [])
                if len(subtypes) >= 2:
                    def_node = graph.nodes.get(def_id)
                    if def_node:
                        sub_children = []
                        for st_id in sorted(subtypes, key=lambda x: graph.nodes.get(x, SchemaNode(id=x, label=x, file="")).label):
                            st_node = graph.nodes.get(st_id)
                            if st_node:
                                sub_children.append({
                                    "name": st_node.label,
                                    "id": st_id,
                                    "kind": st_node.kind,
                                    "file": st_node.file,
                                    "props": st_node.property_count,
                                    "version": st_node.version,
                                    "lifecycle": "",
                                })
                        children.append({
                            "name": def_node.label,
                            "id": def_id,
                            "kind": "base_type",
                            "file": def_node.file,
                            "props": def_node.property_count,
                            "version": "",
                            "lifecycle": "",
                            "children": sub_children,
                        })

        result = {
            "name": n.label + (f" v{n.version}" if n.version else ""),
            "id": nid,
            "kind": n.kind,
            "file": n.file,
            "props": n.property_count,
            "version": n.version,
            "lifecycle": lifecycle,
        }
        if children:
            result["children"] = children
        return result

    # Find roots: file nodes with no incoming lineage
    roots = [nid for nid in file_nodes if nid not in has_incoming]
    if not roots:
        roots = list(file_nodes.keys())[:1]

    tree_data: dict
    if len(roots) == 1:
        tree_data = _build_node(roots[0]) or {"name": "root", "children": []}
    else:
        # Multiple roots — create a virtual root
        children = []
        for rid in sorted(roots, key=lambda x: file_nodes.get(x, SchemaNode(id=x, label=x, file="")).version or "0"):
            child = _build_node(rid)
            if child:
                children.append(child)
        tree_data = {"name": "Schema Ecosystem", "id": "_root", "kind": "root",
                     "file": "", "props": 0, "version": "", "lifecycle": "",
                     "children": children}

    tree_json = json.dumps(tree_data, indent=2)

    # ── Collect unique files for color mapping ────────────────────────────
    all_files = sorted(set(n.file for n in graph.nodes.values()))
    file_colors = {}
    palette = ["#4a90d9", "#e94560", "#7ed321", "#f5a623", "#9b59b6",
               "#00bcd4", "#ff7043", "#ab47bc", "#26a69a", "#ef5350"]
    for i, f in enumerate(all_files):
        file_colors[f] = palette[i % len(palette)]
    colors_json = json.dumps(file_colors)

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Schema Lineage Tree</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace; background: #0d1117; color: #c9d1d9; }}
  h1 {{ text-align: center; padding: 16px; font-size: 1.3em; color: #58a6ff;
       border-bottom: 1px solid #21262d; }}
  #tree-container {{ width: 100%; height: calc(100vh - 56px); overflow: hidden; }}
  .node circle {{ cursor: pointer; stroke-width: 2px; }}
  .node text {{ font-size: 11px; fill: #c9d1d9; }}
  .node--internal text {{ font-weight: 600; }}
  .node--collapsed circle {{ fill-opacity: 0.4; }}
  .link {{ fill: none; stroke-opacity: 0.35; }}
  .tooltip {{
    position: absolute; background: #161b22; border: 1px solid #30363d;
    padding: 10px 14px; border-radius: 8px; font-size: 12px; line-height: 1.5;
    pointer-events: none; display: none; max-width: 320px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  }}
  .tooltip b {{ color: #58a6ff; }}
  .tooltip .badge {{
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 10px; margin-left: 4px;
  }}
  .badge-active {{ background: #238636; color: #fff; }}
  .badge-superseded {{ background: #6e4600; color: #ffa657; }}
  .badge-orphaned {{ background: #6e1b1b; color: #f85149; }}
  .legend {{
    position: fixed; bottom: 12px; left: 12px; background: #161b22;
    padding: 12px 16px; border-radius: 8px; border: 1px solid #30363d;
    font-size: 11px;
  }}
  .legend div {{ margin: 4px 0; display: flex; align-items: center; gap: 8px; }}
  .legend .swatch {{ width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }}
  .controls {{
    position: fixed; top: 60px; right: 16px; background: #161b22;
    padding: 8px 12px; border-radius: 8px; border: 1px solid #30363d;
    font-size: 11px;
  }}
  .controls button {{
    background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
    padding: 4px 10px; border-radius: 4px; cursor: pointer; margin: 2px;
  }}
  .controls button:hover {{ background: #30363d; }}
</style>
</head>
<body>
<h1>Schema Lineage Tree</h1>
<div class="tooltip" id="tooltip"></div>
<div class="controls">
  <button onclick="expandAll()">Expand All</button>
  <button onclick="collapseAll()">Collapse All</button>
  <button onclick="resetZoom()">Reset Zoom</button>
</div>
<div class="legend" id="legend"></div>
<div id="tree-container"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const treeData = {tree_json};
const fileColors = {colors_json};

const container = document.getElementById("tree-container");
const width = container.clientWidth;
const height = container.clientHeight;
const margin = {{ top: 20, right: 220, bottom: 20, left: 160 }};

const svg = d3.select("#tree-container").append("svg")
  .attr("width", width).attr("height", height);

const g = svg.append("g").attr("transform", `translate(${{margin.left}}, ${{margin.top}})`);

// Zoom
const zoom = d3.zoom().scaleExtent([0.2, 4]).on("zoom", (e) => g.attr("transform", e.transform));
svg.call(zoom);
svg.call(zoom.transform, d3.zoomIdentity.translate(margin.left, height / 4).scale(0.85));

const tooltip = document.getElementById("tooltip");

// Build legend
const legendEl = document.getElementById("legend");
Object.entries(fileColors).forEach(([file, color]) => {{
  const div = document.createElement("div");
  div.innerHTML = `<span class="swatch" style="background:${{color}}"></span>${{file.replace('.json','').substring(0,30)}}`;
  legendEl.appendChild(div);
}});

// Tree layout
const treemap = d3.tree().nodeSize([28, 280]);

let root = d3.hierarchy(treeData, d => d.children);
root.x0 = height / 2;
root.y0 = 0;

function update(source) {{
  const treeNodes = treemap(root);
  const nodes = treeNodes.descendants();
  const links = treeNodes.links();

  // Normalize y-depth
  nodes.forEach(d => {{ d.y = d.depth * 260; }});

  // ── Nodes ──────────────────────────────────────────────────────────
  const node = g.selectAll("g.node").data(nodes, d => d.data.id || d.data.name);

  const nodeEnter = node.enter().append("g")
    .attr("class", d => "node" + (d.children ? " node--internal" : "") + (d._children ? " node--collapsed" : ""))
    .attr("transform", d => `translate(${{source.y0 || 0}},${{source.x0 || 0}})`)
    .on("click", (e, d) => {{
      if (d.children) {{ d._children = d.children; d.children = null; }}
      else if (d._children) {{ d.children = d._children; d._children = null; }}
      update(d);
    }})
    .on("mouseover", (e, d) => {{
      const data = d.data;
      let html = `<b>${{data.name}}</b>`;
      if (data.file) html += `<br>File: ${{data.file}}`;
      if (data.kind) html += `<br>Kind: ${{data.kind}}`;
      if (data.props) html += `<br>Properties: ${{data.props}}`;
      if (data.version) html += `<br>Version: ${{data.version}}`;
      if (data.lifecycle) {{
        const cls = {{"active":"badge-active","superseded":"badge-superseded","orphaned":"badge-orphaned"}}[data.lifecycle] || "";
        html += `<br>Status: <span class="badge ${{cls}}">${{data.lifecycle}}</span>`;
      }}
      if (d.children || d._children) {{
        const count = (d.children || d._children).length;
        html += `<br>Subtypes: ${{count}}`;
      }}
      tooltip.innerHTML = html;
      tooltip.style.display = "block";
    }})
    .on("mousemove", (e) => {{
      tooltip.style.left = (e.pageX + 14) + "px";
      tooltip.style.top = (e.pageY - 10) + "px";
    }})
    .on("mouseout", () => {{ tooltip.style.display = "none"; }});

  // Circle
  nodeEnter.append("circle")
    .attr("r", d => {{
      if (d.data.kind === "root") return 12;
      if (d.data.kind === "schema" || d.data.kind === "patch" || d.data.kind === "vocabulary") return 10;
      if (d.data.kind === "base_type") return 8;
      return Math.max(4, Math.min(7, (d.data.props || 0) / 3));
    }})
    .attr("fill", d => {{
      if (d.data.kind === "root") return "#30363d";
      if (d._children) return "#6e7681";
      return fileColors[d.data.file] || "#555";
    }})
    .attr("stroke", d => d._children ? "#f5a623" : (fileColors[d.data.file] || "#555"))
    .attr("stroke-width", d => d.data.kind === "root" ? 3 : 2);

  // Label
  nodeEnter.append("text")
    .attr("dy", ".35em")
    .attr("x", d => (d.children || d._children) ? -14 : 14)
    .attr("text-anchor", d => (d.children || d._children) ? "end" : "start")
    .text(d => d.data.name);

  // Update positions
  const nodeUpdate = nodeEnter.merge(node);
  nodeUpdate.transition().duration(500)
    .attr("transform", d => `translate(${{d.y}},${{d.x}})`);

  nodeUpdate.select("circle")
    .attr("fill", d => {{
      if (d.data.kind === "root") return "#30363d";
      if (d._children) return "#6e7681";
      return fileColors[d.data.file] || "#555";
    }});

  // Remove old
  node.exit().transition().duration(300)
    .attr("transform", d => `translate(${{source.y}},${{source.x}})`)
    .remove();

  // ── Links (curved) ─────────────────────────────────────────────────
  const link = g.selectAll("path.link").data(links, d => d.target.data.id || d.target.data.name);

  const linkEnter = link.enter().insert("path", "g")
    .attr("class", "link")
    .attr("d", () => {{
      const o = {{ x: source.x0 || 0, y: source.y0 || 0 }};
      return diagonal(o, o);
    }})
    .attr("stroke", d => fileColors[d.target.data.file] || "#444")
    .attr("stroke-width", d => {{
      const count = (d.target.children || d.target._children || []).length;
      return Math.max(1, Math.min(4, 1 + count * 0.3));
    }});

  linkEnter.merge(link).transition().duration(500)
    .attr("d", d => diagonal(d.source, d.target));

  link.exit().transition().duration(300)
    .attr("d", () => {{
      const o = {{ x: source.x, y: source.y }};
      return diagonal(o, o);
    }}).remove();

  // Save positions for transitions
  nodes.forEach(d => {{ d.x0 = d.x; d.y0 = d.y; }});
}}

function diagonal(s, d) {{
  return `M ${{s.y}} ${{s.x}}
          C ${{(s.y + d.y) / 2}} ${{s.x}},
            ${{(s.y + d.y) / 2}} ${{d.x}},
            ${{d.y}} ${{d.x}}`;
}}

function expandAll() {{
  function expand(d) {{ if (d._children) {{ d.children = d._children; d._children = null; }} if (d.children) d.children.forEach(expand); }}
  expand(root);
  update(root);
}}

function collapseAll() {{
  function collapse(d) {{ if (d.children && d.depth > 0) {{ d._children = d.children; d.children = null; }} if (d._children) d._children.forEach(collapse); }}
  root.children.forEach(collapse);
  update(root);
}}

function resetZoom() {{
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(margin.left, height / 4).scale(0.85));
}}

// Initial render
update(root);
</script>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════
# 6. CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Schema genealogy / tree-of-life builder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python schema_tree.py session-02/schemas/              # ASCII tree
  python schema_tree.py session-02/schemas/ --mermaid    # Mermaid diagram
  python schema_tree.py session-02/schemas/ --dot        # Graphviz DOT
  python schema_tree.py session-02/schemas/ --html       # Interactive HTML
  python schema_tree.py session-02/schemas/ --json       # JSON graph
  python schema_tree.py session-02/schemas/ -v           # verbose ASCII
  python schema_tree.py session-02/schemas/ --report     # Markdown analysis report
  python schema_tree.py session-02/schemas/ --report -o report.md
""",
    )
    parser.add_argument("schema_dir", type=Path,
                        help="Directory containing JSON Schema files.")
    parser.add_argument("--mermaid", action="store_true",
                        help="Output as Mermaid flowchart.")
    parser.add_argument("--dot", action="store_true",
                        help="Output as Graphviz DOT.")
    parser.add_argument("--html", action="store_true",
                        help="Output as self-contained HTML with D3 force graph.")
    parser.add_argument("--tree", action="store_true",
                        help="Output as self-contained HTML lineage tree (phylogenetic cladogram).")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON graph.")
    parser.add_argument("--report", action="store_true",
                        help="Output a comprehensive Markdown analysis report.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show extra detail (properties, edge reasons).")
    parser.add_argument("--detail", choices=["files", "defs", "full"], default="defs",
                        help="Detail level for Mermaid/DOT (default: defs).")
    parser.add_argument("--usage", action="store_true",
                        help="Grep parent directory for code references to each schema file.")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Write output to file instead of stdout.")

    args = parser.parse_args()
    schema_dir = args.schema_dir.resolve()

    if not schema_dir.is_dir():
        print(f"ERROR: Not a directory: {schema_dir}", file=sys.stderr)
        return 1

    # Find all JSON files
    json_files = sorted(schema_dir.glob("*.json"))
    if not json_files:
        print(f"ERROR: No .json files found in {schema_dir}", file=sys.stderr)
        return 1

    # Build graph
    graph = SchemaGraph()
    graph._schema_dir = str(schema_dir)
    for jf in json_files:
        parse_schema_file(jf, graph)

    detect_lineage(graph)

    # Detect hints file
    hints_path = schema_dir / ".schema-hints.yaml"
    if not hints_path.is_file():
        hints_path = schema_dir / ".schema-hints.yml"
    if not hints_path.is_file():
        hints_path = schema_dir / ".schema-hints.json"
    if not hints_path.is_file():
        hints_path = None
    else:
        if not args.json:
            print(f"  Using hints: {hints_path}")

    # Optional: scan usage in parent directory
    usage_data = None
    if args.usage or args.report:
        usage_data = scan_usage(graph, schema_dir)

    # Render
    if args.report:
        output = render_report(graph, schema_dir, hints_path=hints_path, usage=usage_data)
    elif args.mermaid:
        output = render_mermaid(graph, detail=args.detail)
    elif args.dot:
        output = render_dot(graph, detail=args.detail)
    elif args.html:
        output = render_html(graph)
    elif args.tree:
        output = render_lineage_tree(graph, usage=usage_data)
    elif args.json:
        output = render_json(graph)
    else:
        output = render_ascii(graph, verbose=args.verbose, hints_path=hints_path)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"  Written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
