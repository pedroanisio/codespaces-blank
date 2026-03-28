---
name: file-agent-metadata
description: Check, create, and enforce File-Level Agent Metadata (FLAM). Use when opening a file for editing, creating new files, auditing metadata coverage, or verifying constraints before committing. Triggers on "check meta", "add metadata", "file rules", "FLAM", or when editing files that have __file_meta__.
---

# File-Level Agent Metadata (FLAM)

Structured metadata blocks embedded in source files that tell AI agents what constraints apply when editing. See `concepts/file-level-agent-metadata.md` for the full concept.

## When to Use This Skill

- **Before editing a file**: Check if it has `__file_meta__` and read its rules
- **After creating a new file**: Add `__file_meta__` if the file has non-obvious constraints
- **Before committing**: Verify no `forbidden_patterns` are violated and `error`-severity rules are satisfied
- **When asked**: "check meta", "add metadata", "show rules for X", "audit FLAM coverage"

## Protocol: Before Editing Any File

1. Check for `__file_meta__` (Python), YAML frontmatter (Markdown), or `.meta.json` sidecar
2. If `status` is `frozen` — **refuse to edit** without explicit user override
3. If `status` is `deprecated` — warn the user, suggest alternatives
4. Read all `rules` — treat `error` severity as hard constraints
5. Read `forbidden_patterns` — verify none match in the final output
6. Read `relations` — if `tested_by` exists, run those tests after editing
7. **Never remove or weaken existing `__file_meta__`** during edits

## Reading Metadata

```bash
# Pretty-print all metadata
python -m lib.meta_reader <file>

# JSON output (machine-readable)
python -m lib.meta_reader <file> --json

# Rules only
python -m lib.meta_reader <file> --rules

# CI gate: exit 1 if ERROR-severity rules exist
python -m lib.meta_reader <file> --check

# Scan a directory recursively
python -m lib.meta_reader <dir> --recursive
```

```python
# Programmatic access
from lib.meta_reader import extract_meta
from pathlib import Path

meta = extract_meta(Path("tools/organize.py"))
for rule in meta.rules:
    print(f"[{rule.severity.value}] {rule.rule}")
```

## Creating Metadata for a Python File

Add a `__file_meta__` block after imports, before the first class/function:

```python
from lib.file_meta import FileMeta, FileRule, FileRelation, FileStatus, Severity, RelationType

__file_meta__ = FileMeta(
    role="<what this file does in one phrase>",
    domain="<problem domain>",
    status=FileStatus.STABLE,  # DRAFT | STABLE | FROZEN | DEPRECATED | EXPERIMENTAL
    owner="<team or session>",
    tags=["<tag1>", "<tag2>"],
    rules=[
        FileRule(
            rule="<actionable, verifiable constraint>",
            severity=Severity.ERROR,  # INFO | WARNING | ERROR
            rationale="<why this rule exists>",
            applies_to=["<function_or_class_glob>"],  # empty = entire file
        ),
    ],
    forbidden_patterns=[
        r"<regex that must never appear>",
    ],
    relations=[
        FileRelation(
            target="<relative/path/to/related/file>",
            relation=RelationType.TESTED_BY,  # IMPORTS | IMPORTED_BY | TESTS | TESTED_BY | CONFIGURES | etc.
            notes="<optional context>",
        ),
    ],
    schema_ref="<path/to/schema.json>",
    test_ref="<path/to/test_file.py>",
)
```

## Creating Metadata for Markdown

Add YAML frontmatter at the top of the file:

```markdown
---
role: Schema specification document
domain: video-production
status: stable
rules:
  - rule: All schema changes must bump schemaVersion
    severity: error
    rationale: Downstream validators rely on version detection
tags: [schema, v3]
---
```

## Creating Metadata via Sidecar

For files that don't support inline metadata, create `<filename>.meta.json`:

```json
{
  "role": "Environment configuration",
  "domain": "infrastructure",
  "status": "stable",
  "rules": [
    {"rule": "Never commit real API keys", "severity": "error"}
  ],
  "forbidden_patterns": ["sk-[a-zA-Z0-9]{20,}"]
}
```

## Status Semantics

| Status | Agent behavior |
|--------|---------------|
| `draft` | Edit freely, suggest improvements |
| `stable` | Edit carefully, changes need tests |
| `frozen` | **Do not edit** without explicit user override |
| `deprecated` | Warn user, suggest migration, do not extend |
| `experimental` | Edit freely, may be discarded |

## Severity Semantics

| Severity | Agent behavior |
|----------|---------------|
| `info` | May ignore with stated reason |
| `warning` | Should follow; log if violated |
| `error` | **Must follow** — fail the task if violated |

## Verification Checklist (Pre-Commit)

After editing a file with `__file_meta__`, verify:

- [ ] No `forbidden_patterns` match anywhere in the file
- [ ] All `error`-severity rules are satisfied
- [ ] `status` was not changed to a weaker state without user approval
- [ ] If `test_ref` is set, those tests pass
- [ ] `__file_meta__` block itself was not removed or weakened

## Deciding When to Add FLAM

Add `__file_meta__` when:
- The file has constraints an agent wouldn't know from reading the code alone
- The file is edited frequently across sessions
- A mistake in this file is expensive (data loss, API cost, broken pipeline)
- The file has specific test coverage or schema conformance requirements

Do NOT add `__file_meta__` to:
- Trivial scripts under ~30 lines
- Generated files (add it to the generator instead)
- Test files (they are `relations` of the files they test)
- Files whose constraints are already fully in CLAUDE.md

## Schema Reference

Full Pydantic schema: `lib/file_meta.py`
Reader/CLI: `lib/meta_reader.py`
Concept doc: `concepts/file-level-agent-metadata.md`
