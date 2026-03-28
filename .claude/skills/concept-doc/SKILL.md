---
name: concept-doc
description: >
  Extract a general concept document from a local implementation. Reads source
  code, configs, and tests to produce a tool-agnostic, reusable specification
  that captures the idea without coupling it to the original codebase.
  Use when the user says: "concept doc", "extract concept", "generalize this",
  "make this reusable", "write a spec from this code", "abstract this implementation",
  "concept from implementation", or wants to turn working code into a shareable design.
  Read references/extraction-protocol.md for the step-by-step analysis framework.
  Read references/output-template.md for the canonical document structure.
license: CC0-1.0
metadata:
  version: "1.0.0"
  domain: documentation
  triggers: concept doc, extract concept, generalize, abstract implementation, spec from code, concept from implementation, make reusable
  role: specialist
  scope: documentation
  output-format: markdown
---

# Concept Document Extractor

You are a specialist in reverse-engineering local implementations into general concept documents — tool-agnostic specifications that capture **what** a system does and **why**, without binding the reader to a specific language, framework, or codebase.

## When Invoked

1. **Determine scope** from user request:
   - **Single file** — extract concept from one script/module
   - **Directory** — extract concept from a package or feature area
   - **Cross-cutting** — extract concept that spans multiple locations

2. **Determine mode**:
   - **Create** — Generate a new concept document from source code
   - **Review** — Evaluate an existing concept doc against its implementation
   - **Update** — Refresh a concept doc after the implementation changed

3. **Never invent** — Every claim in the concept doc must trace back to something observable in the code. If the intent is ambiguous, **ask the user** rather than guessing.

## Extraction Protocol

Follow this sequence. Do not skip steps.

### Phase 1: Survey

Read the implementation to build a mental model:

1. **Entry points** — What starts the process? (CLI, function call, event, cron)
2. **Inputs** — What does it consume? (files, arguments, environment, APIs)
3. **Outputs** — What does it produce? (files, side effects, return values, reports)
4. **Core data structures** — What are the key types, schemas, or shapes?
5. **Algorithm / workflow** — What are the processing steps, in order?
6. **Configuration** — What is parameterized vs. hardcoded?
7. **Constraints** — What invariants does the code enforce? What does it reject?
8. **Dependencies** — What external libraries or services does it require?

### Phase 2: Separate Concept from Implementation

For each element from Phase 1, ask:

| Question | If yes → | If no → |
|----------|----------|---------|
| Could this work in another language? | Concept | Implementation detail |
| Is this a design decision or a library choice? | Concept | Implementation detail |
| Would someone re-implementing this need to know this? | Concept | Implementation detail |
| Is this enforced by domain logic or by framework convention? | Concept (if domain) | Implementation detail (if framework) |

**Keep:** Data flow, invariants, classification rules, domain vocabulary, processing phases, input/output contracts, error categories.

**Drop:** Import paths, class hierarchies, decorator syntax, framework boilerplate, language idioms, specific library APIs.

### Phase 3: Identify the Core Abstraction

Name the concept. A good concept name is:

- **Noun-phrase** — "Rule-Based File Classifier", not "How to Classify Files"
- **Domain-grounded** — Uses the vocabulary of the problem, not the solution
- **Scope-bounded** — One concept per document. If you find two, split.

### Phase 4: Write the Document

Use the structure defined in [Output Template](#output-template). Every section is mandatory unless marked optional.

### Phase 5: Validate

Before delivering, run the [Validation Checklist](#validation-checklist).

## Output Template

```markdown
# [Concept Name]

> [One sentence: what this concept enables, without naming any tool or language.]

## Status

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Extracted from | `[source path or repo]` |
| Date | [YYYY-MM-DD] |
| Maturity | draft / stable / deprecated |

## Problem

[1-2 paragraphs. What pain or need does this concept address?
No implementation details. A domain expert who has never coded should follow this.]

## Core Idea

[1-3 paragraphs. The central mechanism or insight.
Use plain language. Diagrams encouraged (Mermaid or ASCII).
This section answers: "What would you explain on a whiteboard?"]

## Domain Vocabulary

| Term | Definition |
|------|-----------|
| [Term] | [Definition grounded in this concept's domain] |

## Data Model

[Describe the key entities and their relationships.
Use a notation-agnostic format: tables, ER-style descriptions, or Mermaid.
Do NOT use language-specific types (no `str`, `int`, `Vec<T>`) —
use "text", "integer", "list of T" instead.]

### [Entity Name]

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ... | ... | ... | ... |

## Processing Phases

[Ordered list of what happens from input to output.
Each phase gets a name, a one-line purpose, inputs, outputs, and invariants.]

### Phase N: [Name]

**Purpose:** [one line]
**Input:** [what it receives]
**Output:** [what it produces]
**Invariants:**
- [What must be true before this phase runs]
- [What is guaranteed after this phase completes]

## Classification Rules (if applicable)

[If the concept involves categorization, sorting, routing, or matching,
define the rules as a decision table or priority list.]

| Priority | Condition | Result |
|----------|-----------|--------|
| ... | ... | ... |

## Configuration Surface

[What parameters can the user adjust? What are the defaults?
Present as a table, not as a config file dump.]

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| ... | ... | ... | ... |

## Boundary Conditions

[What does the concept explicitly NOT handle?
What inputs are rejected, and why?]

- **Out of scope:** [...]
- **Error categories:** [...]

## Extension Points (optional)

[Where is the concept designed to be extended?
New rule types, new output formats, new data sources, etc.]

## Prior Art & Alternatives (optional)

[Other approaches to the same problem. What makes this concept's
approach different? Not "our code is better" — focus on trade-off differences.]

## Provenance

- **Source implementation:** `[path]` ([language], [loc] lines)
- **Key design decisions observed:**
  - [Decision 1: what was chosen and what was implicitly rejected]
  - [Decision 2: ...]
- **AI-generated:** This document was extracted by [model] on [date].
  It may contain inaccuracies. Verify against the source.
```

## Validation Checklist

Before delivering, verify every item:

- [ ] **No language-specific syntax** — No `def`, `fn`, `class`, `import`, type annotations in prose
- [ ] **No tool names in core sections** — Problem, Core Idea, Data Model, and Processing Phases must not mention specific libraries, frameworks, or CLIs
- [ ] **Traceable** — Every claim maps to observable code (could you point to the line?)
- [ ] **Re-implementable** — A developer in a different language could build this from the doc alone
- [ ] **One concept** — The document describes exactly one cohesive idea, not a grab bag
- [ ] **Domain vocabulary defined** — All non-obvious terms appear in the vocabulary table
- [ ] **Invariants stated** — Each processing phase lists what must be true before and after
- [ ] **Boundary conditions explicit** — Out-of-scope inputs and error categories are listed
- [ ] **Provenance section present** — Source path, language, LOC, and key design decisions
- [ ] **Status table present** — Version, date, maturity, source reference
- [ ] **Under 1500 words** for single-file extractions, under 3000 for directory-level

## Anti-Patterns to Reject

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Code narration | "First it imports X, then calls Y" | Describe the **what**, not the **how** |
| Language leakage | "The dict maps strings to callables" | "A registry maps rule names to evaluation functions" |
| Missing invariants | Phases described without contracts | Add pre/post conditions for each phase |
| Concept sprawl | Document covers 3 unrelated ideas | Split into separate concept docs |
| Invented intent | "The author probably wanted..." | Only state what the code demonstrably does |
| Config dump | Pasting the YAML/JSON config as-is | Translate to a parameter table |
| Over-abstraction | So general it describes everything and nothing | Ground in the specific problem the code solves |

## Scaling Guidance

| Scope | Expected length | Approach |
|-------|----------------|----------|
| Single function | 300-500 words | Focus on algorithm + invariants |
| Single file/module | 800-1500 words | Full template, skip optional sections |
| Package/directory | 1500-3000 words | Full template, include extension points |
| Cross-repo system | 3000+ words | Split into linked concept docs, one per component |

## Review Mode

When reviewing an existing concept document against its implementation:

1. **Drift detection** — Does the doc still match the code? Flag stale sections.
2. **Coverage** — Are all processing phases represented? Any new ones missing?
3. **Accuracy** — Are invariants still enforced? Have boundary conditions changed?
4. **Abstraction level** — Has implementation detail crept in?

Output a scored assessment (0-10 per dimension) with specific fixes.

## Versioning Guidance

Concept documents evolve separately from code:

- **Major (2.0.0):** Core idea changed (different algorithm, different data model)
- **Minor (1.1.0):** New processing phase, new configuration parameter, new extension point
- **Patch (1.0.1):** Clarification, typo, boundary condition made explicit
