# CLAUDE.md — Project Guidelines

## Disclaimer Reference (Required in all READMEs)

Every README file in this repository **must** reference `@DISCLAIMER.md` at the root of the project.

When creating or editing any `README.md`, include:

```markdown
## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.
```

Adjust the relative path to match depth: root → `./DISCLAIMER.md`, one level → `../DISCLAIMER.md`, two levels → `../../DISCLAIMER.md`. Place after the title, before the first content section. Never omit it.

---

## Project Overview

**SAFE AI Production** — a multi-session workspace exploring epistemic integrity, bias auditing, type-safe data schemas, and responsible knowledge representation for AI systems.

```
.
├── CLAUDE.md                # This file — project guidelines for AI agents
├── DISCLAIMER.md            # Methodological caveats (all READMEs must reference)
├── README.md
├── lib/                     # Shared Python library
│   ├── file_info.py         #   FileInfo dataclass + load_file_info()
│   ├── rules.py             #   Declarative rule engine (Rule, RuleGroup, 10 evaluators)
│   ├── config.py            #   YAML/JSON config loader with auto-discovery
│   ├── file_meta.py         #   Pydantic schema for FLAM (FileMeta, FileRule, FileRelation)
│   └── meta_reader.py       #   CLI + library for extracting/displaying FLAM
├── concepts/                # Formalized project concepts
│   ├── embedded-self-documentation.md   # ESD — docstrings as complete manuals
���   └── file-level-agent-metadata.md     # FLAM — structured metadata for AI agents
├── session-01/              # Epistemic Justice & Research Source Schemas
│   └── assets/              #   TypeScript schemas, PDFs, media, research data
├── session-02/              # Generative-AI Video Production Schema & Pipeline
│   ├── pipeline/            #   Python CLI: create, run, check, validate
│   ├── skills/              #   24 AI agent skill specifications
│   ├── schemas/             #   JSON Schema v3 + predecessors
│   └── examples/            #   Example project instances
├── tools/                   # Reusable Python utilities (imports from lib/)
├── content/                 # Scraped source content
├── transcripts/             # Media transcriptions
└── results/                 # Pipeline output reports
```

---

## User Preferences (ranked by priority)

1. **Unbiased over flattering.**
2. **Formalization means research** — concrete and correct math, full data provenance, and references. Never hallucination.
3. **English over Portuguese.**
4. **Markdown over DOCX; TypeScript over JavaScript.**
5. All Markdown documents must include a disclaimer stating that no information should be taken for granted and that any statement not backed by a real logical definition or verifiable reference may be invalid or a hallucination.
6. **Feedback is not a source of truth.** If sound, accept it and improve. If not, refute it and clarify objections.

---

## File-Level Agent Metadata (FLAM)

**Before editing any file**, check for embedded metadata that defines constraints:

- **Python files**: Look for `__file_meta__` module-level variable
- **Markdown files**: Look for YAML frontmatter with `role`/`rules` fields
- **Any file**: Look for a `<filename>.meta.json` sidecar

When present, you MUST:

1. **Respect `status`**: `frozen` = do not edit; `deprecated` = warn user
2. **Follow `rules`**: `error` severity = hard constraint, fail if violated; `warning` = should follow
3. **Check `forbidden_patterns`**: verify none match in your output before committing
4. **Run `test_ref`**: if a test file is referenced, run it after editing
5. **Never remove or weaken** existing `__file_meta__` blocks

```bash
python -m lib.meta_reader <file>            # show metadata
python -m lib.meta_reader <file> --rules    # rules only
python -m lib.meta_reader <dir> -r          # scan directory
```

Schema: `lib/file_meta.py` · Reader: `lib/meta_reader.py` · Concept: `concepts/file-level-agent-metadata.md`

---

## Core Principles

These principles have zero exceptions:

1. **Fix root causes, never symptoms.** Investigate with 5-Whys before patching. If a test fails, understand why — don't just make it pass.
2. **Test-Driven Development.** Red → Green → Refactor → Cleanup. Write the failing test first. No code ships without tests.
3. **Production-ready code only.** No placeholders, no `TODO: implement later`, no incomplete stubs. Every commit must be deployable.

---

## Development Standards

### Testing
- 80% coverage for libraries, 60% for CLIs
- Unit, integration, and E2E tests
- Tests must be deterministic, isolated, and realistic
- Run tests after every change — don't batch validation to the end

### Code Quality
- Typed errors in libraries, graceful handling in applications
- Automated formatting and linting
- No unnecessary dependencies

### Version Control
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- Semantic versioning for schemas (`major.minor.patch`)
- AI-generated artifacts must be labeled with their source model/tool

### Architecture Decisions
- Document significant decisions with rationale
- When multiple approaches exist, state the trade-offs and ask before proceeding
- When scope is ambiguous ("finish everything", "complete this"), stop and clarify before starting

---

## AI Agent Guidance

### Context Management
- Priority reading order: `CLAUDE.md` → `__file_meta__` → Tests → Code
- Read existing code before suggesting modifications
- Check FLAM metadata before editing any file

### Confidence & Decision Making
- **Proceed** when requirements are clear and approach is obvious
- **State assumptions** when proceeding with medium confidence
- **Ask** when multiple valid approaches exist or scope is ambiguous
- **Never provide time estimates** (hours/days/weeks) — use complexity: XS/S/M/L/XL

### Delivery
- Deliver complete, atomic work — no batching across responses
- Break large work into complete subtasks, each independently useful
- For M/L/XL tasks: plan first, then execute

---

## General Conventions

- All schema files use semantic versioning (`major.minor.patch`)
- Bilingual content (PT-BR + EN-US) is standard for project-level documentation
- AI-generated artifacts must be labeled with their source model/tool in metadata or frontmatter
- Every README linking to session sub-directories should also link back up to root `README.md`

---

## Document Relationships

| Document | Audience | Defines |
|----------|----------|---------|
| `DISCLAIMER.md` | Everyone | Epistemic integrity commitments |
| `CLAUDE.md` | AI agents + devs | HOW to build (process, standards, enforcement) |
| `README.md` | Humans | WHAT the project does (usage, overview) |
| `concepts/*.md` | Everyone | Formalized project concepts (ESD, FLAM) |
| `__file_meta__` | AI agents | Per-file constraints and relationships |
