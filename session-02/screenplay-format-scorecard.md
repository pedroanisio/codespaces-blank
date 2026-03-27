---
title: "Screenplay Format Specification — Scorecard & Design Assumptions"
schema_version: "1.0.0"
date: "2026-03-27"
disclaimer: >
  No information within this document should be taken for granted.
  Any statement or premise not backed by a real logical definition
  or verifiable reference may be invalid, erroneous, or a hallucination.
  The reader is responsible for independent verification.
---

# Screenplay Format Specification — Scorecard & Assumptions

## Design Assumptions

The following decisions were made where the user did not specify a
preference. Each is documented so the consumer can override
deliberately.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **JSON Schema draft 2020-12** as the schema language. | User asked for "schema json". JSON Schema is the most portable JSON-native contract language. |
| 2 | **UUIDs** for `format_id`. | Opaque, collision-resistant. Switch to ULIDs if lexicographic ordering is needed. |
| 3 | **Measurement** as a dedicated type with explicit `unit`. | Screenplay formatting spans US (inches) and European (cm/mm) traditions; a bare number would be ambiguous. |
| 4 | **`additionalProperties: false`** on all objects. | Closed schema for strict validation. Add `x-extension-point: true` if open extensibility is needed. |
| 5 | **Element list is ordered but order is advisory.** | The schema defines formatting rules per element type; it does not constrain content sequencing (that's the screenplay itself). |
| 6 | **TV-specific elements** (act_break, cold_open_header, etc.) are in the `ElementType` enum but only appear in TV variant instances. | A single enum keeps the schema unified; variant-specific applicability is documented, not structurally enforced. This is an intentional deviation from strict discriminated-union purity (Rule 8 waiver). |
| 7 | **Revision color sequence** is modeled as an ordered array, not a fixed enum. | Studios occasionally modify the sequence; an array is more evolvable. |
| 8 | **No PII fields exist** in this schema. | Screenplay format specs describe formatting rules, not personal data. Rule 23 scored as N/A. |
| 9 | **ContinuationRules** are optional on elements. | Only dialogue and character_name elements use continuation tags. Forcing them on all elements would add noise. |
| 10 | **`content_pattern` uses regex** for machine-checkable syntax. | Human-readable `structural_pattern` is provided alongside for documentation. |

---

## Review Scorecard

```
┌─────┬──────────────────────────────────────────┬──────────┬────────┐
│  #  │ Rule (short form)                        │ Tier     │ Score  │
├─────┼──────────────────────────────────────────┼──────────┼────────┤
│     │ PART I — TYPE SAFETY AND PRECISION       │          │        │
│  1  │ Unambiguous field types                  │ MUST     │ Pass   │
│  2  │ Constraints in schema                    │ MUST     │ Pass   │
│  3  │ Closed, versioned enums                  │ MUST     │ Pass   │
│  4  │ Nullable ≠ optional ≠ absent             │ MUST     │ Pass   │
│  5  │ Arrays: item type + cardinality + order  │ MUST     │ Pass   │
│  6  │ Temporal precision and format            │ MUST     │ Pass   │
│  7  │ Numeric units declared                   │ MUST     │ Pass   │
│  8  │ Discriminated polymorphism               │ MUST     │ Warn   │
│  9  │ Defaults declared in schema              │ SHOULD   │ Pass   │
├─────┼──────────────────────────────────────────┼──────────┼────────┤
│     │ PART II — IDENTITY AND RELATIONSHIPS     │          │        │
│ 10  │ Stable, opaque identity                  │ MUST     │ Pass   │
│ 11  │ Navigable relationships                  │ MUST     │ Pass   │
│ 12  │ Explicit lifecycle ownership             │ MUST     │ Pass   │
│ 13  │ FK targets declared                      │ MUST     │ Pass   │
│ 14  │ Cyclic graph constraints                 │ MUST     │ Pass   │
├─────┼──────────────────────────────────────────┼──────────┼────────┤
│     │ PART III — NORMALIZATION AND COHERENCE   │          │        │
│ 15  │ Single source of truth                   │ MUST     │ Pass   │
│ 16  │ No bag-of-arrays entities                │ SHOULD   │ Pass   │
│ 17  │ Cross-cutting types defined once         │ SHOULD   │ Pass   │
│ 18  │ Computed vs. stored distinguished        │ SHOULD   │ Pass   │
├─────┼──────────────────────────────────────────┼──────────┼────────┤
│     │ PART IV — EVOLUTION AND COMPATIBILITY    │          │        │
│ 19  │ Explicit, monotonic versioning           │ MUST     │ Pass   │
│ 20  │ No duplicate-version entities            │ MUST     │ Pass   │
│ 21  │ Breaking changes classified              │ MUST     │ Pass   │
│ 22  │ Field deprecation annotated              │ MUST     │ Pass   │
├─────┼──────────────────────────────────────────┼──────────┼────────┤
│     │ PART V — OPERATIONAL ANNOTATIONS         │          │        │
│ 23  │ Sensitive fields classified              │ MAY*     │ N/A    │
│ 24  │ Identity/provenance immutability         │ SHOULD   │ Pass   │
│ 25  │ Localization strategy declared           │ SHOULD   │ Pass   │
│ 26  │ Multi-actor provenance metadata          │ SHOULD   │ Warn   │
├─────┼──────────────────────────────────────────┼──────────┼────────┤
│     │ PART VI — DOCUMENTATION AND GENERABILITY │          │        │
│ 27  │ Consistent naming                        │ MUST     │ Pass   │
│ 28  │ Mechanically generatable validators      │ MUST     │ Pass   │
│ 29  │ Intentional extension points             │ MUST     │ Pass   │
│ 30  │ Access patterns don't dictate structure  │ SHOULD   │ Pass   │
│ 31  │ Readable as standalone artifact          │ MUST     │ Pass   │
├─────┼──────────────────────────────────────────┼──────────┼────────┤
│     │ TOTALS                                   │          │        │
│     │ MUST Pass:  19/19 (no PII)               │          │        │
│     │ SHOULD Pass or Documented: 11/11         │          │        │
└─────┴──────────────────────────────────────────┴──────────┴────────┘

* Rule 23 is MUST for PII-bearing schemas. This schema has no PII.
```

### Warn Explanations

**Rule 8 (Discriminated polymorphism) — Warn:**
The `ElementType` enum contains TV-specific values (e.g., `act_break`,
`cold_open_header`) that are semantically invalid for film variants.
A strict discriminated union would split `ElementFormat` into
`FilmElementFormat | TVElementFormat` with separate enum subsets. This
was intentionally deferred to keep the schema simpler and more
evolvable — adding a new medium shouldn't require a new union branch.
The `variant.variant_type` field serves as a soft discriminator:
consumers can validate element applicability against the variant at
the application layer.

**Rule 26 (Multi-actor provenance) — Warn:**
This schema models a *format specification*, not a collaboratively
edited document. Provenance metadata (who defined which formatting
rule) is not meaningful at this level. If the schema were extended to
track per-studio overrides or per-production customizations, Rule 26
would become relevant and a `provenance` field should be added to
`ElementFormat`.

---

## What the Schema Covers

| Domain Concept | Schema Location |
|---|---|
| Page dimensions and paper size | `page_setup.paper_size` |
| Margins (incl. binding offset) | `page_setup.margins` |
| Font (family, size, monospace, density) | `page_setup.font` |
| Line spacing (single/double/exact) | `page_setup.line_spacing`, per-element overrides |
| Physical binding | `page_setup.binding` |
| Regional/medium variants | `variant` (Hollywood, BBC, French, TV, etc.) |
| Page-per-minute ratio | `variant.page_time_ratio` |
| All element types (24 types) | `elements[].element_type` enum |
| Per-element indentation | `elements[].indentation` |
| Per-element capitalization + exceptions | `elements[].capitalization` |
| Per-element spacing (before/after) | `elements[].spacing_before`, `.spacing_after` |
| Per-element alignment | `elements[].alignment` |
| Dialogue width constraints | `elements[].max_width` |
| Scene heading syntax (INT./EXT., time-of-day) | `elements[].syntax` |
| Continuation tags (MORE, CONT'D) | `elements[].continuation_rules` |
| Page break behavior per element | `elements[].page_break_behavior` |
| Typographic modifiers (bold/italic/underline) | `elements[].style_modifiers` |
| Pagination (numbering, position, headers) | `pagination` |
| Scene numbering (shooting scripts) | `scene_numbering` |
| Title page layout and required fields | `title_page` |
| Revision color sequence | `revision_tracking.color_sequence` |
| Revision marks (asterisks) | `revision_tracking.revision_mark` |

---

## What the Schema Does NOT Cover

These are explicitly out of scope and would require separate schemas:

- **Screenplay content** — the actual scenes, dialogue, and action.
  This schema defines *how* to format, not *what* to write.
- **Fountain markup syntax** — Fountain is a plain-text authoring
  format that *produces* screenplays; this schema defines the
  *output* format rules.
- **Software-specific features** — Final Draft `.fdx` XML structure,
  Highland's Fountain extensions, WriterSolo internals.
- **Copyright and rights metadata** — WGA registration is a title
  page field but chain-of-title, option agreements, etc. are legal
  domain objects.
- **Localization of element labels** — the schema uses English labels;
  a companion i18n mapping could translate "Scene Heading" → "En-tête
  de scène" for French UI contexts.
