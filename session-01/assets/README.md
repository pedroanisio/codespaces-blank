---
title: "Research Source Map — Schema Documentation"
version: "3.0.0 (sources) / 1.0.0 (assessment)"
authors: []
date: "2026-03-26"
disclaimer: >
  This document is a structural proposal. No statement, premise, design
  decision, enum value, or architectural claim herein should be taken for
  granted. Any assertion not backed by a real logical definition or
  verifiable reference (ISO standard, peer-reviewed methodology, formal
  specification) may be invalid, erroneous, or a hallucination. The
  conceptual framework references E. P. Thompson, Subaltern Studies,
  standpoint epistemology, and archival-silence theory, but does NOT
  implement any of these as formal systems. Validate everything against
  your domain requirements before adoption.
---

# Research Source Map

A pair of schemas for building, auditing, and remediating research
source collections across written, oral, visual, and time-based media.

## The problem

Research maps inherit the biases of whoever builds them. A literature
review conducted through database search finds what databases index —
overwhelmingly institutional, English-language, text-based, and
produced by people with access to publication infrastructure. The map
silently excludes everyone else: the illiterate, the colonized, the
censored, the oral, the visual, the destroyed.

Most source-management tools treat this as someone else's problem. These
schemas treat it as a structural property of the map itself — something
that can be measured, named, and acted on.

## Two schemas, one workflow

```
┌─────────────────────────┐        ┌─────────────────────────┐
│                         │        │                         │
│   research-source-      │  ref   │   research-map-         │
│   schema.ts             │◄───────│   assessment.ts         │
│                         │ mapId  │                         │
│   "What do we have?"    │        │   "What are we missing  │
│                         │        │    and what do we do     │
│   Sources, agents,      │        │    about it?"           │
│   claims, relations,    │        │                         │
│   oral context, media   │        │   Blind spots, axes,    │
│   context, provenance   │        │   remediation, verdict  │
│                         │        │                         │
└─────────────────────────┘        └─────────────────────────┘
```

The source schema (`research-source-schema.ts`) defines **what you
have**: the sources themselves, their metadata, their relationships, and
the domain-specific context needed to handle oral traditions, visual art,
music, and film alongside conventional academic literature.

The assessment schema (`research-map-assessment.ts`) defines **what you
don't have and why**: the epistemic audit that measures balance, names
blind spots, and tracks concrete remediation actions.

They are separate files because the assessment is performed *on* a
completed or in-progress map, not embedded within it. A single map may
have multiple assessments over time as gaps are filled.

## Schema 1: research-source-schema.ts

**Version:** 3.0.0
**Runtime:** Zod v4 (`zod@^4.0.0`)
**Compiles with:** TypeScript 5.x / 6.x (`moduleResolution: "bundler"`)

### Purpose

Define a single, typed container (`ResearchMap`) that holds an array of
`ResearchSource` records spanning the full range of human knowledge
production — from DOI-backed journal articles to Yoruba praise poems to
Picasso's Guernica to Alan Lomax field recordings.

### Architecture

The schema is organized into 19 sections. Each source record
(`ResearchSource`) composes optional sub-objects around a small required
core.

**Required fields on every source:**

| Field         | Type              | Why required                                    |
|---------------|-------------------|-------------------------------------------------|
| `id`          | UUID v4           | Primary key within the map                      |
| `kind`        | `SourceKind`      | Determines which optional contexts apply        |
| `title`       | Non-empty string  | Every source has a name, even if approximate     |
| `attribution` | `Attribution`     | At least one agent or communal attribution       |
| `provenance`  | `Provenance`      | How and when this source entered the map         |

Everything else is optional. A sparse early-stage entry and a fully
annotated archival record use the same type.

**Key design decisions:**

**FuzzyDate replaces ISO dates globally.** Every temporal field accepts
either `{ kind: "exact", value: "2024-03-15" }` or
`{ kind: "approximate", label: "before the war", notBefore: "1935-01-01",
notAfter: "1939-09-01", confidence: 0.4 }`. This is necessary because
oral sources, pre-modern documents, and many artworks have no precise
dates.

**Attribution supports communal, anonymous, and mixed authorship.** The
`Attribution` object holds an optional `agents[]` array and an optional
`CommunalAttribution`, with a refinement requiring at least one of the
two. A Yoruba proverb can be attributed to a community with no named
individuals. A recorded interview can carry both a named narrator and
the tradition they speak from. Agents carry an `anonymized` flag for
pseudonymized identities.

**Structured Locator replaces plain-string locators.** A discriminated
union of five types: `page` (text documents), `time` (audio/video in
seconds), `spatial` (normalized 0–1 bounding box within a visual work),
`section` (named divisions like movements or acts), and `free`
(catch-all). Claims and annotations point at specific regions of any
source type with appropriate precision.

**Three domain-specific context objects:**

- `OralContext` — fixation layers (the chain of medium transformations
  from live performance through recording to transcription), transmission
  chain (person-to-person handoffs with acknowledged gaps), performed
  languages, oral genre, performance context, and community restrictions.

- `MediaContext` — physical description (medium, support, dimensions,
  condition), holding history (current and prior institutional custody),
  exhibition records, and time-based media specifics (duration, aspect
  ratio, color mode, key, tempo, instrumentation, named sections).

- Both can coexist on the same source — a field recording of a folk song
  crosses oral and media concerns simultaneously.

**Relations form a directed graph.** `SourceRelation[]` connects sources
within the same map by UUID. Relation types cover academic citation,
oral transmission (`transmitted-from`, `variant-of`), and arts lineage
(`study-for`, `inspired-by`, `reproduction-of`, `cover-of`,
`remix-of`).

**EthicsInfo captures consent, sensitivity, and access restrictions.**
Seven consent statuses (including `community-consent-obtained` and
`posthumous-no-consent-possible`), five sensitivity levels, and a
free-text restrictions array. This exists because oral testimony,
indigenous knowledge, and material involving living persons carry
obligations that journal articles do not.

### Source kind coverage

The `SourceKind` enum spans three families plus a catch-all:

- **Written/digital** (24 kinds): journal article through archival document
- **Oral/performed** (8 kinds): oral testimony, oral tradition, folk song, speech, sermon, ritual text, radio broadcast
- **Visual arts** (13 kinds): painting, drawing, print, sculpture, installation, mural, photograph, poster, cartographic map, and others
- **Music/audio** (7 kinds): musical composition, score, album, single track, sound recording, podcast, field recording
- **Film/video/performance** (10 kinds): film, documentary, animation, television program, performance, dance, and others

### Agent roles

Roles span writing (`author`, `editor`, `translator`), fieldwork
(`narrator`, `informant`, `interviewer`, `transcriber`, `custodian`),
visual arts (`artist`, `sculptor`, `photographer`, `curator`,
`restorer`), music (`composer`, `conductor`, `performer`, `producer`),
and film (`director`, `screenwriter`, `cinematographer`).

## Schema 2: research-map-assessment.ts

**Version:** 1.0.0
**Runtime:** Zod v4 (`zod@^4.0.0`)

### Purpose

Force the researcher to answer: *whose voice is in this map, whose
isn't, why, and what am I going to do about it?*

The conceptual foundation is "history from below" — E. P. Thompson's
1966 argument that conventional historiography systematically writes
ordinary people out of history by relying on sources produced by and
about elites. The assessment schema operationalizes this concern (and
its successors in Subaltern Studies, feminist historiography, and
postcolonial theory) as structured data.

### Architecture

The `MapAssessment` object references a `ResearchMap` by `mapId` and
contains seven sections that flow from self-awareness to action:

```
 PositionalityStatement     "Who am I? What can I see?"
         │
         ▼
 AxisAssessment[]           "Along each power axis, who speaks
         │                   and who is silenced?"
         │
 SourceTypeDistribution     "How concentrated are my source types?"
         │
 MethodBias[]               "What do my retrieval methods miss?"
         │
 CoverageGap[]              "Where are the temporal, geographic,
         │                   linguistic holes?"
         ▼
 BlindSpot[]                "Named, specific epistemic gaps with
         │                   consequences for my claims"
         ▼
 RemediationAction[]        "Concrete tasks to reduce each gap"
         │
         ▼
 AssessmentVerdict           "Can this map support its own claims?"
```

### Key concepts

**Power axes** — dimensions along which sources can be unevenly
distributed: class, race-ethnicity, gender, sexuality, age, disability,
religion, language, literacy, colonial position, geographic
center-periphery, institutional affiliation, political power, economic
power, caste, indigenous status, migration status, incarceration status,
and a custom catch-all. Each axis gets three lists: `overrepresented`,
`underrepresented`, and `structurallySilenced`.

**The structurally silenced distinction** is critical. Some absences are
in *this map* — fixable by searching harder. Others are in *the record
itself* — the sources were never created, or were destroyed, and no
amount of effort will find them. Franco-era destruction of Republican
municipal records is structural. Missing Moroccan soldiers' testimony
is partially fixable through oral history work. The schema forces the
researcher to commit to which kind of absence they face.

**Source type concentration** is measured by the Herfindahl-Hirschman
Index (HHI): the sum of squared shares of each source kind. HHI
approaches 1.0 when one kind dominates. A map of 87% journal articles
has an HHI around 0.76 — meaning it can only see what academic
publishing can see.

**Blind spots** are named as first-class objects, not footnotes. Seven
kinds:

| Kind                   | What it means                                                |
|------------------------|--------------------------------------------------------------|
| `source-absence`       | The voices are not in the map                                |
| `interpretive-frame`   | The sources are present but read through the wrong lens      |
| `archival-destruction` | The sources no longer exist                                  |
| `language-barrier`     | The sources exist in inaccessible languages                  |
| `access-restriction`   | The sources are sealed or community-controlled               |
| `question-framing`     | The research question excludes certain evidence by design    |
| `survivorship-bias`    | The map reflects what survived, not what existed             |

Each blind spot declares its severity, its fixability, which power axes
it implicates, and which claims it weakens.

**Remediation actions** are the operational core. Nine types:
`additional-search`, `fieldwork`, `community-engagement`, `translation`,
`capacity-building`, `expert-consultation`, `reframing`, `disclosure`,
and `other`. Each carries estimated effort in researcher-days, expected
impact on the blind spot, obstacles, and a status tracker. The schema's
position: noting a blind spot without proposing action is performative
epistemology.

**The verdict** aggregates everything: `overallBalance`,
`sourceDiversity`, counts of addressed vs. unaddressed blind spots, and
a `claimsSupported` field with four levels from `well-supported` to
`unsupported-for-stated-scope`. The last level is the Thompson verdict:
you claimed to study "civilian experience" but your sources are all
parliamentary debates and journal articles.

## Usage

### Installation

```bash
npm install zod@^4.0.0
```

### Import

```typescript
// Source schema
import {
  ResearchMapSchema,
  ResearchSourceSchema,
  AttributionSchema,
  OralContextSchema,
  MediaContextSchema,
  LocatorSchema,
} from "./research-source-schema";

// Assessment schema
import {
  MapAssessmentSchema,
  BlindSpotSchema,
  RemediationActionSchema,
  AxisAssessmentSchema,
} from "./research-map-assessment";
```

### Parse and validate

```typescript
const result = ResearchMapSchema.safeParse(data);

if (!result.success) {
  console.error(result.error.issues);
} else {
  const map = result.data;
  // map is fully typed as ResearchMap
}
```

### Type inference

```typescript
import type {
  ResearchMap,
  ResearchSource,
  Attribution,
  Locator,
  BlindSpot,
  MapAssessment,
} from "./research-source-schema";
// (or from assessment schema for assessment types)
```

### Workflow sketch

```
1. Build the ResearchMap
   - Add sources as you find them
   - Use OralContext / MediaContext as needed
   - Link sources via relations[]

2. Assess the map
   - Write your PositionalityStatement
   - Walk each power axis: who speaks? who doesn't?
   - Compute source type distribution and HHI
   - Name each blind spot explicitly
   - Propose remediation actions

3. Act on remediations
   - Track status: proposed → in-progress → completed
   - Re-assess periodically
   - Narrow scope claims if gaps can't be filled

4. Publish with the assessment attached
   - The verdict is part of the deliverable, not metadata
```

## Design principles

**Sparse by default.** Only five fields are required on a source record.
Everything else is optional. A URL-and-title stub and a fully annotated
museum catalog entry use the same type.

**No false precision.** FuzzyDate exists because "sometime in the early
1940s" is honest and "1940-01-01" is a lie. ApproximateDate with
confidence bounds is more informative than a fabricated ISO string.

**Agents are not always individuals.** Attribution supports named
individuals, communal ownership, anonymized identities, and any
combination. The schema does not force Western authorship conventions
onto sources that don't follow them.

**Locators match the medium.** Pages for text, timestamps for audio/video,
bounding boxes for visual art, named sections for structured works. The
same Claim type points precisely at a figure in Guernica's lower-left
quadrant and at bars 1–5 of Beethoven's Fifth.

**Blind spots are first-class objects.** Not comments, not footnotes, not
a paragraph in the methodology section. Named, typed, severity-scored,
linked to affected claims, and connected to concrete remediation actions.

**Assessment is separate from the map.** The map is what you have. The
assessment is what you know about what you don't have. They evolve on
different timelines. A map may have multiple assessments as gaps are
filled or new ones discovered.

**Remediation is not optional.** The schema provides `disclosure` as an
action type — explicitly stating the limitation — because some gaps
cannot be filled. But it requires that even structural absences be
*named* and *acknowledged*, not silently absorbed into the map's
apparent completeness.

## Limitations of these schemas

These schemas have their own blind spots:

- **No formal ontology.** Power axes, source kinds, and relation types
  are flat enums, not a formal taxonomy. There is no inheritance, no
  subsumption, no reasoning over the type system. This is a deliberate
  trade-off for simplicity, but it means the schema cannot answer
  questions like "is a folk-song a subtype of oral-tradition?"

- **Assessment is self-reported.** The AxisAssessment balance scores,
  blind spot severities, and remediation impact estimates are all the
  researcher's own judgment. There is no external validation mechanism
  built into the schema. Peer review of assessments remains a social
  process, not a structural one.

- **Western-framework bias.** The power axes reflect categories legible
  to Western academic frameworks. The `custom` axis exists as an escape
  hatch, but the defaults privilege a particular way of slicing social
  reality. A researcher working within an indigenous knowledge system
  may find these categories alien or insufficient.

- **No automated computation.** HHI, balance scores, and claim-support
  verdicts are stored, not computed. The schema is a data structure,
  not an analysis engine. Consumers must implement their own aggregation
  logic.

- **English-centric documentation.** The schema, its comments, and this
  README are in English. The enum labels are in English. This is itself
  a form of the linguistic bias the assessment schema aims to detect.

## References

The following works informed the conceptual framework. The schemas do
not implement any of them formally.

- Thompson, E. P. "History from Below." *The Times Literary Supplement*, 1966.
- Thompson, E. P. *The Making of the English Working Class*. London: Victor Gollancz, 1963.
- Guha, Ranajit. *Elementary Aspects of Peasant Insurgency in Colonial India*. Delhi: OUP, 1983.
- Spivak, Gayatri Chakravorty. "Can the Subaltern Speak?" In *Marxism and the Interpretation of Culture*, edited by C. Nelson and L. Grossberg, 271–313. Macmillan, 1988.
- Trouillot, Michel-Rolph. *Silencing the Past: Power and the Production of History*. Boston: Beacon Press, 1995.
- Fuentes, Marisa J. *Dispossessed Lives: Enslaved Women, Violence, and the Archive*. Philadelphia: University of Pennsylvania Press, 2016.
- Harding, Sandra. *Whose Science? Whose Knowledge?* Ithaca: Cornell University Press, 1991.
- Haraway, Donna. "Situated Knowledges: The Science Question in Feminism and the Privilege of Partial Perspective." *Feminist Studies* 14, no. 3 (1988): 575–599.
- Zinn, Howard. *A People's History of the United States*. New York: Harper & Row, 1980.
- Sharpe, Jim. "History from Below." In *New Perspectives on Historical Writing*, edited by Peter Burke, 24–41. Cambridge: Polity Press, 1991.

## License

Unlicensed. Use, modify, and redistribute without restriction.