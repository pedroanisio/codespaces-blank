# File-Level Agent Metadata (FLAM)

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

---

## Definition

A **structured metadata block** embedded in or alongside a source file that tells AI coding agents what the file IS, what rules to FOLLOW, what to NEVER do, and how it RELATES to other files — without requiring the agent to read the entire codebase or consult external documentation.

Where [Embedded Self-Documentation](./embedded-self-documentation.md) targets **human readers** (complete manual in the docstring), FLAM targets **machine readers** (structured, parseable contract for automated agents).

---

## Problem Statement

AI coding agents operate on files without persistent memory of project conventions. Every session starts cold. The agent must re-discover:

- What role this file plays in the system
- What constraints apply when editing it
- What patterns are forbidden
- What other files will break if this one changes
- Whether the file is stable, experimental, or frozen

This information currently lives in READMEs, CLAUDE.md, tribal knowledge, or nowhere. FLAM moves it to the **only place that's always available when the file is open**: the file itself.

---

## Structural Contract

A FLAM block is a dictionary conforming to the `FileMeta` Pydantic schema (`lib/file_meta.py`). It contains these sections:

| # | Section | Type | Purpose | Required |
|----|---------|------|---------|----------|
| 1 | **role** | `string` | What the file does, in one phrase | Yes |
| 2 | **domain** | `string` | Problem domain (e.g. `video-production`, `schema-validation`) | Yes |
| 3 | **status** | `enum` | Lifecycle: `draft`, `stable`, `frozen`, `deprecated`, `experimental` | Yes |
| 4 | **owner** | `string` | Team, session, or person responsible | No |
| 5 | **tags** | `string[]` | Free-form tags for search and classification | No |
| 6 | **rules** | `FileRule[]` | Constraints for agents editing this file | Yes (if any) |
| 7 | **forbidden_patterns** | `string[]` | Regex patterns that must NEVER appear after editing | No |
| 8 | **relations** | `FileRelation[]` | Typed links to other files (imports, tests, configures) | No |
| 9 | **schema_ref** | `string` | Path to the schema this file conforms to | No |
| 10 | **test_ref** | `string` | Path to the primary test file | No |
| 11 | **extra** | `dict` | Open extension point for project-specific metadata | No |

---

## Rule Model

Each rule in `rules[]` has:

| Field | Type | Purpose |
|-------|------|---------|
| `rule` | `string` | The constraint in plain English. Must be actionable and verifiable. |
| `severity` | `enum` | `info` (suggestion), `warning` (should follow), `error` (must follow — fail CI if violated) |
| `applies_to` | `string[]` | Glob patterns for which functions/classes this rule applies to. Empty = entire file. |
| `rationale` | `string` | Why this rule exists — helps the agent judge edge cases. |

### Severity semantics

- **`info`** — The agent MAY ignore with a stated reason. Example: *"Prefer f-strings over .format()"*
- **`warning`** — The agent SHOULD follow. Log if violated. Example: *"Avoid adding new dependencies without updating requirements.txt"*
- **`error`** — The agent MUST follow. Fail the task if violated. Example: *"Test coverage must remain above 90%"*

---

## Relation Model

Each relation in `relations[]` has:

| Field | Type | Purpose |
|-------|------|---------|
| `target` | `string` | Relative path to the related file from the project root |
| `relation` | `enum` | How this file relates to the target |
| `notes` | `string` | Additional context |

### Relation types

| Type | Meaning | Example |
|------|---------|---------|
| `imports` | This file imports from the target | `assemble.py` → `lib/rules.py` |
| `imported_by` | The target imports from this file | `lib/rules.py` → `organize.py` |
| `tests` | This file tests the target | `test_assemble.py` → `assemble.py` |
| `tested_by` | The target tests this file | `assemble.py` → `test_assemble.py` |
| `configures` | This file configures the target | `.env` → `providers.py` |
| `configured_by` | The target configures this file | `providers.py` → `.env` |
| `generates` | This file produces the target as output | `create.py` → `project.json` |
| `generated_from` | This file was generated from the target | `project.json` → `create.py` |
| `supersedes` | This file replaces the target | `assemble_v2.py` → `assemble.py` |
| `documents` | This file documents the target | `README.md` → `pipeline/` |

---

## Embedding Strategies

### 1. Python: `__file_meta__` module-level variable

```python
from lib.file_meta import FileMeta, FileRule, FileStatus, Severity

__file_meta__ = FileMeta(
    role="FFmpeg assembly pipeline",
    domain="video-production",
    status=FileStatus.STABLE,
    rules=[
        FileRule(
            rule="Test coverage must remain above 90%",
            severity=Severity.ERROR,
            rationale="Moves files on disk — misclassification is destructive.",
        ),
    ],
    test_ref="pipeline/test_assemble.py",
    forbidden_patterns=[r"import pdb"],
)
```

### 2. Markdown/MDX: YAML frontmatter

```markdown
---
role: Schema specification document
domain: video-production
status: stable
rules:
  - rule: All schema changes must bump schemaVersion
    severity: error
    rationale: Downstream validators rely on version detection
tags: [schema, v3, json-schema]
---

# Unified Video Project Schema
...
```

### 3. Sidecar: `<filename>.meta.json`

For files that don't support inline metadata (binaries, configs, non-Python):

```json
{
  "role": "Environment configuration",
  "domain": "infrastructure",
  "status": "stable",
  "rules": [
    {
      "rule": "Never commit real API keys",
      "severity": "error"
    }
  ],
  "forbidden_patterns": ["sk-[a-zA-Z0-9]{20,}"]
}
```

---

## Reading Metadata

```bash
# Pretty-print
python -m lib.meta_reader tools/organize.py

# JSON output
python -m lib.meta_reader tools/organize.py --json

# Rules only
python -m lib.meta_reader tools/organize.py --rules

# CI gate: exit 1 if ERROR-severity rules exist
python -m lib.meta_reader tools/organize.py --check

# Scan a directory
python -m lib.meta_reader tools/ --recursive
```

### Programmatic access

```python
from lib.meta_reader import extract_meta
from pathlib import Path

meta = extract_meta(Path("tools/organize.py"))
if meta:
    for rule in meta.rules:
        print(f"[{rule.severity.value}] {rule.rule}")
```

---

## Agent Integration Protocol

When an AI agent opens a file for editing, it SHOULD:

1. **Check for `__file_meta__`** (or sidecar/frontmatter) before making changes
2. **Read `status`** — if `frozen`, refuse to edit without explicit user override
3. **Read `rules`** — apply all `error`-severity rules as hard constraints
4. **Read `forbidden_patterns`** — verify none match in the final output
5. **Read `relations`** — if editing a file with `tested_by`, run those tests after
6. **Preserve `__file_meta__`** — never remove or weaken existing metadata during edits

An agent MAY also:
- Use `domain` and `tags` to scope its responses appropriately
- Use `schema_ref` to validate output against the referenced schema
- Use `rationale` to make informed decisions about edge cases

---

## When to Apply

- Any file that AI agents will edit repeatedly across sessions
- Files with non-obvious constraints (coverage requirements, schema conformance, encoding rules)
- Files where a mistake is expensive or hard to detect (file movers, data transformers, API clients)
- Entry points and public interfaces that many other files depend on

## When NOT to Apply

- Trivial scripts under ~30 lines with no constraints
- Generated files (the generator should have FLAM, not the output)
- Files whose constraints are already fully captured in CLAUDE.md
- Test files (they are relations of other files, not primary subjects)

---

## Relationship to Other Concepts

| Concept | Audience | Format | Scope |
|---------|----------|--------|-------|
| **ESD** (Embedded Self-Documentation) | Human readers | Prose docstring | How to USE the file |
| **FLAM** (File-Level Agent Metadata) | Machine agents | Structured schema | How to EDIT the file |
| **CLAUDE.md** | AI agents | Free-text instructions | Project-wide conventions |
| **README.md** | Human readers | Prose | Directory/project overview |

A file can have both ESD (for humans) and FLAM (for agents). They serve different audiences and don't duplicate each other.

---

## Reference Implementation

- **Schema**: [`lib/file_meta.py`](../lib/file_meta.py) — Pydantic model defining the full `FileMeta` contract
- **Reader**: [`lib/meta_reader.py`](../lib/meta_reader.py) — CLI + library for extracting metadata from files
- **First adopter**: [`tools/organize.py`](../tools/organize.py) — `__file_meta__` with coverage rule, forbidden patterns, and test ref
