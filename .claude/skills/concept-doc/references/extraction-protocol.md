# Extraction Protocol — Quick Reference

Step-by-step checklist for extracting a concept document from source code.

## Pre-flight

- [ ] Confirm scope with user: which files/dirs to analyze
- [ ] Read all source files in scope (do not skim — read fully)
- [ ] Read associated tests (they reveal invariants the code enforces)
- [ ] Read config files (they reveal the configuration surface)
- [ ] Read README or docstrings (they reveal stated intent)

## Phase 1: Survey — Fill This Table

For each element, note the **code evidence** (file:line or function name).

| Element | Finding | Evidence |
|---------|---------|----------|
| Entry points | | |
| Inputs (args, files, env, APIs) | | |
| Outputs (files, side effects, returns) | | |
| Core data structures | | |
| Processing steps (in order) | | |
| Configuration knobs | | |
| Invariants / validations | | |
| External dependencies | | |
| Error handling strategy | | |

## Phase 2: Separation — Apply the 4 Questions

For each finding from Phase 1:

```
1. Could this work in another language?          → Yes = concept
2. Is this a design decision or library choice?  → Design = concept
3. Would a re-implementer need to know this?     → Yes = concept
4. Domain logic or framework convention?          → Domain = concept
```

Mark each finding as **C** (concept) or **I** (implementation detail).

## Phase 3: Name the Concept

Test candidate names against:

- [ ] Is it a noun phrase? (not a verb or sentence)
- [ ] Does it use problem-domain words? (not solution-domain)
- [ ] Would a non-developer understand the name?
- [ ] Does it scope to ONE idea?

## Phase 4: Write

Use the output template from SKILL.md. Write sections in this order:

1. Problem (forces you to articulate WHY before WHAT)
2. Core Idea (the whiteboard explanation)
3. Domain Vocabulary (define terms before using them)
4. Data Model (entities and relationships)
5. Processing Phases (with invariants)
6. Classification Rules (if applicable)
7. Configuration Surface
8. Boundary Conditions
9. Provenance (last — after you've internalized the code)

## Phase 5: Validate

Run the validation checklist from SKILL.md. Common failures:

| Check | How to test |
|-------|------------|
| No language syntax | Ctrl+F for `def `, `fn `, `class `, `import `, `->`, `=>` |
| No tool names in core | Ctrl+F for library names in Problem/Core Idea/Data Model/Phases |
| Traceable | For each claim, can you cite file:line? |
| Re-implementable | Could you build this in a language you've never used for this domain? |

## Common Extraction Patterns

### Pattern: CLI Tool → Concept

| Code element | Maps to concept section |
|-------------|----------------------|
| argparse / clap definitions | Configuration Surface |
| main() dispatch logic | Processing Phases |
| Dataclass / struct | Data Model |
| if/elif chains on file types | Classification Rules |
| sys.exit / error returns | Boundary Conditions |
| --help text | Problem (sometimes) |

### Pattern: Config-Driven System → Concept

| Code element | Maps to concept section |
|-------------|----------------------|
| YAML/JSON config schema | Configuration Surface + Data Model |
| Config loader + validator | Processing Phase 1 (Parse + Validate) |
| Rule/matcher engine | Classification Rules |
| Default config | Configuration Surface (defaults column) |

### Pattern: Pipeline / Workflow → Concept

| Code element | Maps to concept section |
|-------------|----------------------|
| Stage functions | Processing Phases (one per stage) |
| Stage input/output types | Phase contracts (Input/Output) |
| Assertions / guards | Invariants |
| Skip/filter logic | Boundary Conditions |
| Retry / error handling | Boundary Conditions (error categories) |
