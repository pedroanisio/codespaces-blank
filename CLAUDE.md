# CLAUDE.md — Project Guidelines

## Disclaimer Reference (Required in all READMEs)

Every README file in this repository **must** reference `@DISCLAIMER.md` at the root of the project. This is a mandatory project convention.

### Rule

When creating or editing any `README.md` file (root or session-level), include a disclaimer reference section. Use the following block:

```markdown
## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.
```

Adjust the relative path to `DISCLAIMER.md` to match the file's depth in the directory tree:
- Root `README.md` → `[DISCLAIMER.md](./DISCLAIMER.md)`
- One level deep (e.g. `session-02/README.md`) → `[DISCLAIMER.md](../DISCLAIMER.md)`
- Two levels deep (e.g. `session-01/assets/README.md`) → `[DISCLAIMER.md](../../DISCLAIMER.md)`

Place the disclaimer reference **after the title and before the first content section**, or at the very end as a footer — whichever is more natural for the document. Never omit it.

### Why

`DISCLAIMER.md` encodes the project's epistemic integrity commitments: non-definitiveness, openness to revision, interdisciplinarity as method, and the principle that AI-generated content may contain hallucinations. These apply to every document in the project without exception.

---

## Project Overview

**SAFE AI Production** — a multi-session workspace exploring epistemic integrity, bias auditing, type-safe data schemas, and responsible knowledge representation for AI systems.

```
.
├── DISCLAIMER.md            ← Methodological caveats (all READMEs must reference this)
├── README.md
├── lib/                     # Shared Python library (file_info, rules, config, file_meta)
├── concepts/                # Project concepts (ESD, FLAM)
├── session-01/              # Epistemic Justice & Research Source Schemas
│   └── assets/              # TypeScript schemas, PDFs, media, research data
├── session-02/              # Generative-AI Video Production Schema
├── tools/                   # Reusable Python utilities (imports from lib/)
├── content/                 # Scraped source content
├── transcripts/             # Media transcriptions
└── results/                 # Pipeline output reports
```

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

Quick commands:
```bash
python -m lib.meta_reader <file>            # show metadata
python -m lib.meta_reader <file> --rules    # rules only
python -m lib.meta_reader <dir> -r          # scan directory
```

Schema: `lib/file_meta.py` · Reader: `lib/meta_reader.py` · Concept: `concepts/file-level-agent-metadata.md`

---

## Shared Library (`lib/`)

Reusable Python modules at the project root. Import with `from lib.<module> import ...`:

| Module | Purpose |
|--------|---------|
| `lib.file_info` | `FileInfo` dataclass + `load_file_info()` for file metadata extraction |
| `lib.rules` | Declarative rule engine: `Rule`, `RuleGroup`, 10 evaluators, `parse_rule()` |
| `lib.config` | YAML/JSON config loader with auto-discovery |
| `lib.file_meta` | Pydantic schema for FLAM (`FileMeta`, `FileRule`, `FileRelation`) |
| `lib.meta_reader` | CLI + library for extracting/displaying FLAM from files |

---

## General Conventions

- All schema files use semantic versioning (`major.minor.patch`).
- Bilingual content (PT-BR + EN-US) is standard for project-level documentation.
- AI-generated artifacts must be labeled with their source model/tool in file metadata or frontmatter.
- Every README linking to session sub-directories should also link back up to the root `README.md`.

# AI Agent Development Guide

**Version:** 2.3.0
**Purpose:** Universal development standards for AI coding agents working on software projects.

---

## User Preferences

**Preferences — ranked by priority**

  1. Unbiased over flattering.

  2. Formalization means research, concrete and correct math, full
     data provenance, and references — never hallucination.

  3. English over Portuguese.

  4. Markdown over DOCX; TypeScript over JavaScript.

  5. All Markdown documents, unless explicitly told otherwise, must
     include a full header (frontmatte) disclaimer stating that no information
     within should be taken for granted and that any statement or
     premise not backed by a real logical definition or verifiable
     reference may be invalid, erroneous, or a hallucination.

6. Feedback is not a source of truth. Feedback must be processed:
     if its content — in full or in part — is sound, accept it and
     improve accordingly; if not, refute it and clarify the
     objections.


---

## Document Relationships

- **PURPOSE.md**: Defines WHY the project exists (vision, mission, principles)
- **CLAUDE.md**: Defines HOW to build (process, standards, tools, enforcement)
- **README.md**: Defines WHAT the project does (usage, installation)

**When in conflict:** PURPOSE.md defines intent; CLAUDE.md defines execution standards.

---

## Quick Start

**For AI Agents:**
1. Read [Core Principles](./_specs/principles/core-principles.md) - Non-negotiable requirements
2. Read [Context Management](./_specs/ai-agents/context-management.md) - Prioritize information efficiently
3. Read [When in Doubt](./_specs/workflows/when-in-doubt.md) - Decision-making guide
4. For L/XL tasks: Build a [Mental Model](./_specs/ai-agents/mental-model-protocol.md) first, then a [Plan](./_specs/ai-agents/plan-generation.md)
5. For M tasks: Read [Plan Generation Protocol](./_specs/ai-agents/plan-generation.md) — mental model optional
6. Follow workflows for your task type

**For Human Developers:**
1. Read [Core Principles](./_specs/principles/core-principles.md) - Understand the standards
2. Review [Testing Standards](./_specs/development/testing-standards.md) - Coverage requirements
3. Follow [Git Workflow](./_specs/development/git-workflow.md) - Version control practices
4. Check [ADRs & Proposals](./_specs/development/adrs-and-proposals.md) - Architectural decisions

---

## Core Principles (Non-Negotiable)

These principles have zero exceptions:

1. **[Root Cause Fixing](./_specs/principles/core-principles.md#1-root-cause-fixing)** - Fix sources, never patch symptoms
2. **[Test-Driven Development](./_specs/principles/core-principles.md#2-test-driven-development-tdd)** - Red → Green → Refactor → Cleanup
3. **[Production-Ready Code Only](./_specs/principles/core-principles.md#3-production-ready-code-only)** - No placeholders, no incomplete code

**Supporting docs:**
- [Anti-Patterns](./_specs/principles/anti-patterns.md) - What to avoid
- [Quality Protocol](./_specs/principles/quality-protocol.md) - Enforcement mechanisms

---

## Development Standards

### Testing
**[Testing Standards](./_specs/development/testing-standards.md)** - Coverage, organization, TDD workflow
- 80% coverage for libraries
- 60% coverage for CLI/applications
- Unit, integration, E2E, and property-based testing
- Deterministic, isolated, realistic tests

### Code Quality
**[Code Quality](./_specs/development/code-quality.md)** - Error handling, linting, dependencies
- Typed errors in libraries
- Graceful error handling in applications
- Automated formatting and linting
- Dependency hygiene and security

### Version Control
**[Git Workflow](./_specs/development/git-workflow.md)** - Commits, branches, releases
- Conventional commits format
- Pre-commit hooks
- Semantic versioning
- Branch protection

### Architecture
**[ADRs & Proposals](./_specs/development/adrs-and-proposals.md)** - Document decisions
- Architecture Decision Records for finalized decisions
- Enhancement Proposals for community review
- Decision workflow and templates

---

## AI Agent-Specific Guidance

### Context Management
**[Context Window Management](./_specs/ai-agents/context-management.md)** - Prioritize information
- Priority reading order: PURPOSE.md → ADRs → Tests → Code
- Context budget allocation strategies
- Efficient reading techniques

### Decision Making
**[Confidence Thresholds](./_specs/ai-agents/confidence-thresholds.md)** - When to ask vs. proceed
- Proceed when requirements are clear
- Ask when multiple approaches exist
- State assumptions when proceeding with medium confidence

### Work Delivery
**[No Batching](./_specs/ai-agents/no-batching.md)** - Complete deliverables only
- Absolute prohibition on splitting work into batches
- Deliver one complete task per response
- Break large work into complete, atomic subtasks

### Estimation
**[Effort Estimation](./_specs/ai-agents/effort-estimation.md)** - T-shirt sizes, priority, sequencing (ZERO TOLERANCE)
- Use XS/S/M/L/XL complexity sizes
- NEVER provide time estimates (hours/days/weeks) or duration references
- Focus on complexity factors, dependencies, and sequencing order
- **M/L/XL tasks MUST use formal plan schema** (plan-schema.ts) with valid JSON
- Violations treated as critical errors

### Mental Model (Pre-Plan Checkpoint)
**[Mental Model Protocol](./_specs/ai-agents/mental-model-protocol.md)** - Validate understanding before planning
- **Mandatory for L/XL tasks** — produce before plan generation
- **Mandatory when scope is ambiguous** — "completion," "finish," "everything"
- **Mandatory when referencing existing plans** — plan reconciliation
- Makes the agent's understanding of baseline, target, entities, and assumptions explicit
- Human reviews ~100 lines instead of ~1500 lines — errors caught at 1/10th the cost
- Schema: [mental-model-schema.ts](./_specs/schemas/mental-model-schema.ts)

### Plan Generation
**[Plan Generation Protocol](./_specs/ai-agents/plan-generation.md)** - How to produce formally sound plans
- §1.0: Resolve scope before anything else — stop and ask when ambiguous
- §1.1: Load schema first (mandatory — do not generate from memory)
- §1.2: Gather domain inputs, verify entities, reconcile with existing plans
- §1.3: Resolve decisions — vendor/cost/infra decisions require human authority
- §2.1: Skeleton-first generation (HARD RULE for plans >400 lines)
- §2.2: Verification economics calibration with default values
- §2.5: Conditional field requirements (stopConditions, handoffTemplate, human verification)
- Domain enumeration confidence gate (NEVER invent entity names — applies continuously)

### Validation
**[Incremental Validation](./_specs/ai-agents/incremental-validation.md)** - Validate continuously
- Validate after each TDD phase
- Don't wait until end to run tests
- Check coverage and ADR compliance incrementally

---

## Workflows

### Feature Development
**[Feature Workflow](./_specs/workflows/feature-workflow.md)** - TDD workflow for new features
1. PLAN: (M/L/XL only) Mental model → human review → plan generation
2. RED: Write failing test
3. GREEN: Implement minimal solution
4. REFACTOR: Optimize while keeping tests green
5. CLEANUP: Remove old/dead code
6. Verify coverage
7. Pre-commit checks
8. Commit with conventional format
9. Update CHANGELOG (if feature complete)

### Bug Fixing
**[Bug Workflow](./_specs/workflows/bug-workflow.md)** - Root cause analysis and fix
1. RED: Write failing test that reproduces bug
2. Investigate root cause (5 Whys)
3. Identify root cause
4. GREEN: Fix root cause
5. Verify no regressions
6. Add edge case tests
7. Update documentation
8. Commit

### Decision Making
**[When in Doubt](./_specs/workflows/when-in-doubt.md)** - Quick reference guide
- Check docs → Follow TDD → Fix root causes → Write tests → Ask questions
- Decision matrix for common scenarios
- Anti-patterns to avoid

---

## Module Index

### Principles (Foundation)
- [core-principles.md](./_specs/principles/core-principles.md) - Root cause fixing, TDD, production-ready code
- [anti-patterns.md](./_specs/principles/anti-patterns.md) - Common mistakes and corrections
- [quality-protocol.md](./_specs/principles/quality-protocol.md) - Zero tolerance enforcement

### Development (Standards)
- [testing-standards.md](./_specs/development/testing-standards.md) - Coverage, organization, quality
- [code-quality.md](./_specs/development/code-quality.md) - Error handling, linting, dependencies
- [git-workflow.md](./_specs/development/git-workflow.md) - Commits, branches, releases
- [adrs-and-proposals.md](./_specs/development/adrs-and-proposals.md) - Architectural decisions

### AI Agents (Specialized Guidance)
- [context-management.md](./_specs/ai-agents/context-management.md) - Context window priorities
- [confidence-thresholds.md](./_specs/ai-agents/confidence-thresholds.md) - When to ask vs. proceed
- [no-batching.md](./_specs/ai-agents/no-batching.md) - Complete deliverables only
- [effort-estimation.md](./_specs/ai-agents/effort-estimation.md) - T-shirt sizing (WHEN plans required)
- [mental-model-protocol.md](./_specs/ai-agents/mental-model-protocol.md) - Pre-plan understanding checkpoint
- [plan-generation.md](./_specs/ai-agents/plan-generation.md) - Producing formally sound plans (HOW)
- [incremental-validation.md](./_specs/ai-agents/incremental-validation.md) - Continuous validation

### Schemas (Formal Contracts)
- [plan-schema.ts](./_specs/schemas/plan-schema.ts) - Plan structure and well-formedness validation
- [mental-model-schema.ts](./_specs/schemas/mental-model-schema.ts) - Mental model structure and readiness validation

### Workflows (Practical Application)
- [feature-workflow.md](./_specs/workflows/feature-workflow.md) - TDD for new features
- [bug-workflow.md](./_specs/workflows/bug-workflow.md) - Root cause bug fixing
- [when-in-doubt.md](./_specs/workflows/when-in-doubt.md) - Decision-making guide

---

## Reading Paths

### New to the Project
1. [Core Principles](./_specs/principles/core-principles.md)
2. [Testing Standards](./_specs/development/testing-standards.md)
3. [Feature Workflow](./_specs/workflows/feature-workflow.md)
4. [When in Doubt](./_specs/workflows/when-in-doubt.md)

### AI Agent Starting Work
1. [Context Management](./_specs/ai-agents/context-management.md)
2. [Core Principles](./_specs/principles/core-principles.md)
3. [Confidence Thresholds](./_specs/ai-agents/confidence-thresholds.md)
4. [No Batching](./_specs/ai-agents/no-batching.md)

### Planning a Complex Task (L/XL)
1. [Effort Estimation](./_specs/ai-agents/effort-estimation.md) — determine if formal plan needed
2. [Mental Model Protocol](./_specs/ai-agents/mental-model-protocol.md) — build and validate understanding
3. *(human review checkpoint)*
4. [Plan Generation Protocol](./_specs/ai-agents/plan-generation.md) — generate formal plan from confirmed model
5. [Plan Schema](./_specs/schemas/plan-schema.ts) — reference during generation

### Planning a Medium Task (M)
1. [Effort Estimation](./_specs/ai-agents/effort-estimation.md) — confirm M sizing
2. [Plan Generation Protocol](./_specs/ai-agents/plan-generation.md) — generate formal plan (mental model optional)
3. [Confidence Thresholds](./_specs/ai-agents/confidence-thresholds.md) — when to stop and ask
4. [No Batching](./_specs/ai-agents/no-batching.md) — deliver complete plan

### Implementing New Feature
1. [Feature Workflow](./_specs/workflows/feature-workflow.md)
2. [Testing Standards](./_specs/development/testing-standards.md)
3. [ADRs & Proposals](./_specs/development/adrs-and-proposals.md)

### Fixing a Bug
1. [Bug Workflow](./_specs/workflows/bug-workflow.md)
2. [Core Principles](./_specs/principles/core-principles.md)
3. [Testing Standards](./_specs/development/testing-standards.md)

### Making Architectural Decision
1. [ADRs & Proposals](./_specs/development/adrs-and-proposals.md)
2. [Core Principles](./_specs/principles/core-principles.md)
3. [When in Doubt](./_specs/workflows/when-in-doubt.md)

---

## The Three Commandments

1. **Fix root causes, never symptoms**
2. **TDD always, no exceptions**
3. **Production-ready code only**

Everything else follows from these.

---

## Version History

### v2.3.0 (Current)
- Added §1.0 Scope Resolution to plan-generation.md (closes dangling CLAUDE.md reference)
- Added scope ambiguity scenario to confidence-thresholds.md
- Updated README.md directory tree (added schemas/, scripts/, mental-model-protocol.md)
- Split feature-workflow.md PLAN phase into L/XL (mental model first) vs. M paths
- Split when-in-doubt.md decision matrix to route L/XL through mental model
- Fixed README.md version (was stale at v2.0.0)

### v2.2.0
- Added mental model protocol (pre-plan checkpoint for L/XL tasks)
- Added mental-model-schema.ts (Zod schema + readiness validation)
- Added Schemas section to Module Index
- Separated reading paths for L/XL vs. M planning
- Updated feature workflow with PLAN phase
- Plan generation protocol hardened: §1.0 scope resolution, skeleton-first hard rule, continuous confidence gate, plan reconciliation support

### v2.1.0
- Added plan-generation.md (bridge between estimation and schema)
- Added plan-generation.md cross-references to 11 existing documents
- Integrated treemeta.sh guidance for domain entity verification
- 9/9 formal constraint coverage at instruction layer

### v2.0.0
- Modular structure with single-concern files
- Skills-like organization
- Improved composability

### v1.0.0 (Deprecated)
- Monolithic CLAUDE.md

---

## License

This document is released under CC0 1.0 Universal (Public Domain).

Use it freely. Build better software.