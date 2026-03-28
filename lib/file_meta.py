"""
file_meta — Pydantic schema for file-level metadata and AI agent guidance.

Each source file can embed a structured metadata block (in a docstring,
frontmatter, or sidecar .meta.json) that tells AI coding agents:
  - What the file IS (role, domain, ownership)
  - What rules to FOLLOW when editing it (constraints, style, invariants)
  - What to NEVER do (forbidden patterns, dangerous operations)
  - How it RELATES to other files (dependencies, consumers, tests)
  - Its current STATUS (draft, stable, deprecated, frozen)

This schema is the contract between files and AI agents.

Usage:
    # Parse from a dict (e.g. frontmatter, sidecar JSON, or docstring block):
    meta = FileMeta.model_validate(raw_dict)

    # Parse from a .meta.json sidecar file:
    meta = FileMeta.model_validate_json(Path("foo.py.meta.json").read_text())

    # Create programmatically:
    meta = FileMeta(
        role="pipeline-assembler",
        domain="video-production",
        status=FileStatus.STABLE,
        owner="session-02/pipeline",
        rules=[
            FileRule(
                rule="All FFmpeg commands must read codec from renderPlan, never hardcode",
                severity=Severity.ERROR,
            ),
        ],
    )

    # Dump to JSON for sidecar:
    Path("assemble.py.meta.json").write_text(meta.model_dump_json(indent=2))
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class FileStatus(str, Enum):
    """Lifecycle status of a source file."""
    DRAFT = "draft"                # Work in progress, expect breaking changes
    STABLE = "stable"              # Production-ready, changes need tests
    FROZEN = "frozen"              # Do not modify without explicit approval
    DEPRECATED = "deprecated"      # Scheduled for removal, do not extend
    EXPERIMENTAL = "experimental"  # Proof of concept, may be discarded


class Severity(str, Enum):
    """How strictly a rule must be enforced."""
    INFO = "info"          # Suggestion — may be ignored with reason
    WARNING = "warning"    # Should be followed — log if violated
    ERROR = "error"        # Must be followed — fail if violated


class RelationType(str, Enum):
    """How this file relates to another."""
    IMPORTS = "imports"            # This file imports from the target
    IMPORTED_BY = "imported_by"    # The target imports from this file
    TESTS = "tests"                # This file tests the target
    TESTED_BY = "tested_by"        # The target tests this file
    CONFIGURES = "configures"      # This file configures the target
    CONFIGURED_BY = "configured_by"
    GENERATES = "generates"        # This file produces the target as output
    GENERATED_FROM = "generated_from"
    SUPERSEDES = "supersedes"      # This file replaces the target
    DOCUMENTS = "documents"        # This file documents the target


# ── Rule model ───────────────────────────────────────────────────────────────

class FileRule(BaseModel):
    """A single constraint or guideline for AI agents editing this file."""

    rule: str = Field(
        ...,
        description="The rule in plain English. Must be actionable and verifiable.",
    )
    severity: Severity = Field(
        default=Severity.WARNING,
        description="How strictly this rule must be enforced.",
    )
    applies_to: list[str] = Field(
        default_factory=list,
        description="Glob patterns for which functions/classes/sections this rule applies to. "
                    "Empty = applies to entire file.",
    )
    rationale: str = Field(
        default="",
        description="Why this rule exists — helps the agent judge edge cases.",
    )


# ── Relation model ───────────────────────────────────────────────────────────

class FileRelation(BaseModel):
    """A typed relationship between this file and another."""

    target: str = Field(
        ...,
        description="Relative path to the related file from the project root.",
    )
    relation: RelationType = Field(
        ...,
        description="How this file relates to the target.",
    )
    notes: str = Field(
        default="",
        description="Additional context about the relationship.",
    )


# ── Main schema ──────────────────────────────────────────────────────────────

class FileMeta(BaseModel):
    """Structured metadata for a source file, readable by AI coding agents.

    Can be embedded as:
      - A `__file_meta__` dict in Python files
      - YAML/TOML frontmatter in Markdown files
      - A sidecar `<filename>.meta.json` file
    """

    # ── Identity ─────────────────────────────────────────────────────────
    role: str = Field(
        default="",
        description="What this file does in one phrase (e.g. 'FFmpeg assembly pipeline', "
                    "'JSON schema validator', 'CLI entry point').",
    )
    domain: str = Field(
        default="",
        description="Problem domain this file belongs to (e.g. 'video-production', "
                    "'epistemic-justice', 'schema-validation').",
    )
    owner: str = Field(
        default="",
        description="Team, session, or person responsible (e.g. 'session-02/pipeline').",
    )

    # ── Status ───────────────────────────────────────────────────────────
    status: FileStatus = Field(
        default=FileStatus.DRAFT,
        description="Lifecycle status — controls how aggressively an agent may refactor.",
    )

    # ── Tags ─────────────────────────────────────────────────────────────
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form tags for search and classification "
                    "(e.g. ['cli', 'ffmpeg', 'v3-schema']).",
    )

    # ── Rules ────────────────────────────────────────────────────────────
    rules: list[FileRule] = Field(
        default_factory=list,
        description="Constraints and guidelines for AI agents editing this file.",
    )
    forbidden_patterns: list[str] = Field(
        default_factory=list,
        description="Regex patterns that must NEVER appear in this file after editing. "
                    "Agent must verify before committing. "
                    "Examples: ['hardcoded.*api.key', 'TODO.*HACK', 'import pdb'].",
    )

    # ── Relations ────────────────────────────────────────────────────────
    relations: list[FileRelation] = Field(
        default_factory=list,
        description="Typed relationships to other files in the project.",
    )

    # ── Schema / contract ────────────────────────────────────────────────
    schema_ref: str = Field(
        default="",
        description="Path or URI to the schema this file must conform to "
                    "(e.g. 'session-02/claude-unified-video-project-v3.schema.json').",
    )
    test_ref: str = Field(
        default="",
        description="Path to the primary test file for this module.",
    )

    # ── Extension point ──────────────────────────────────────────────────
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Open extension point for project-specific metadata.",
    )
