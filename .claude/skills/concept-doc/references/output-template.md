# Output Template — Concept Document

Copy this template and fill in each section. Delete "(optional)" markers and any unused optional sections before delivering.

---

```markdown
# [Concept Name]

> [One sentence: what this concept enables, without naming any tool or language.]

## Status

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Extracted from | `[source path or repo]` |
| Date | [YYYY-MM-DD] |
| Maturity | draft |

## Problem

[1-2 paragraphs. What pain or need motivates this concept?
Write for a domain expert who does not code.
Do not mention tools, libraries, or languages.]

## Core Idea

[1-3 paragraphs. The mechanism or insight — the whiteboard explanation.
Use plain language. A Mermaid or ASCII diagram is encouraged here.
Answer: "If I had 60 seconds to explain this to a colleague, what would I say?"]

## Domain Vocabulary

| Term | Definition |
|------|-----------|
| [Term 1] | [Definition grounded in this concept's domain] |
| [Term 2] | [Definition] |

## Data Model

[Describe entities and their relationships.
Use tables, not code. Use generic types (text, integer, list of T, map of K→V).
If there are many entities, a Mermaid ER diagram helps.]

### [Entity Name]

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| | | | |

## Processing Phases

### Phase 1: [Name]

**Purpose:** [one line]
**Input:** [what this phase receives]
**Output:** [what this phase produces]
**Invariants:**
- [Pre-condition: what must be true before]
- [Post-condition: what is guaranteed after]

### Phase 2: [Name]

**Purpose:**
**Input:**
**Output:**
**Invariants:**
- [...]

## Classification Rules (if applicable)

[If the concept categorizes, routes, matches, or prioritizes items,
express the logic as a decision table.]

| Priority | Condition | Result |
|----------|-----------|--------|
| | | |

## Configuration Surface

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| | | | |

## Boundary Conditions

**Out of scope:**
- [What this concept explicitly does not handle]

**Error categories:**
- [Category 1: when it occurs, what happens]
- [Category 2: ...]

## Extension Points (optional)

[Where is the concept designed to grow?
New rule types, new output formats, new data sources, new phases, etc.]

## Prior Art & Alternatives (optional)

[Other approaches to the same problem.
Focus on trade-off differences, not quality judgments.]

| Approach | Trade-off vs. this concept |
|----------|--------------------------|
| | |

## Provenance

- **Source implementation:** `[path]` ([language], [N] lines)
- **Key design decisions observed:**
  - [Decision 1: what was chosen and what was implicitly rejected]
  - [Decision 2: ...]
- **AI-generated:** This document was extracted by [model] on [date].
  It may contain inaccuracies. Verify against the source.
```

---

## Section-by-Section Guidance

### Problem
- Do NOT start with "This tool..." or "This script..."
- DO start with the pain: "When files accumulate in a flat directory..."
- Test: could a project manager understand this paragraph?

### Core Idea
- Do NOT describe code flow ("first it loads, then it parses...")
- DO describe the mechanism ("Files are classified against an ordered rule set; the highest-priority match wins")
- Test: could you draw this on a whiteboard without any code?

### Data Model
- Use "text" not "str" or "String"
- Use "integer" not "int" or "i32"
- Use "list of X" not "Vec<X>" or "X[]"
- Use "map of K to V" not "Dict[K, V]" or "HashMap<K, V>"
- Use "boolean" not "bool"
- Use "timestamp" not "datetime" or "DateTime<Utc>"

### Processing Phases
- Name phases with verbs: "Parse", "Classify", "Propose", "Apply"
- Every phase MUST have at least one invariant
- Phases should be independently testable

### Classification Rules
- Only include this section if the concept involves categorization
- Rules must be deterministic: same input → same output
- State conflict resolution (priority, first-match, etc.)

### Provenance
- Always include. This grounds the concept in reality.
- The "key design decisions" list is the most valuable part — it captures WHY the code is shaped the way it is, which is harder to recover later.
