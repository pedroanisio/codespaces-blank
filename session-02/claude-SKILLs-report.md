Now I have full context. Let me design the complete answer.Now I have everything needed: the full session-02 context, the canonical `video-project-schema-v2.json` entity graph, and the taxonomy files. This answer can be grounded precisely in the schema.

---

> **Frontmatter notice (per project DISCLAIMER.md v1.0):** No statement below should be taken for granted. Skill count and topology are derived from the entity graph of `video-project-schema-v2.json` and the SRP as a formal criterion. Any claim not backed by that schema or a stated logical argument may be invalid.

---

## Answer: 20 distinct skills (minimum irreducible set)

**The formal criterion used:** a skill is irreducible iff merging it with any other skill would force it to have at least two of: (a) incompatible input types, (b) disjoint output schema entities, (c) different generation primitives, or (d) mutually exclusive execution-time requirements (e.g., "needs full shot graph" vs. "runs per shot"). This is the Single Responsibility Principle applied as a decision procedure, not as a slogan.

**Why 20 is a lower bound, not a preference:** every entity in `video-project-schema-v2.json` must be populated by exactly one skill. There are 20 non-overlapping entity clusters in that schema. Below that count, at least two disjoint clusters would be conflated into one skill, violating (b) above.

The 20 skills are organized across 7 phases, where phases 2–4 contain skills that can run in parallel (no intra-phase data dependency), and phases 1 and 5 are strictly sequential (each skill requires the output of the preceding one).

Here's the full pipeline:---

## Why exactly 20, not fewer

The schema's entity graph has 20 non-overlapping production clusters. Every attempt to merge two skills collapses one of these boundaries:

**Narrative merges fail** because `narrative-architect` reasons about dramatic shape globally (the whole arc), while `scriptwriter` generates prose locally (line by line). These are different generation modes — one constrains, the other produces. Merging them means the writer grades its own structure.

**Creative vision merges fail** because `director`, `character-architect`, and `world-builder` have a strict topological relationship: director_notes is read by both character-architect and world-builder, but is produced by director. If any of the three were merged, you'd get a circular data dependency where a skill both produces and consumes the same entity.

**Audio merges fail** because voice, music, and SFX operate at different temporal granularities: voice is at the utterance level (per dialogue line), SFX is at the event level (per shot action), and music is at the narrative arc level (spanning multiple scenes). A single "audio" skill would need to switch reasoning modes mid-execution — that's not one skill, it's three in a trench coat.

**Phase 5 merges fail** because the four validation/assembly skills form a strict sequential chain: continuity-enforcer → quality-critic → dependency-resolver → assembly-planner. Each one requires the output of the preceding skill as input, and none of them generate content (they audit, score, resolve, and translate). Merging any two would hide the intermediate audit artifact that the next step depends on.

---

## Parallelization structure

The 20 skills decompose into three parallelization windows:

**Window A (phases 2–4)** unlocks after `script-validator` passes. Phases 2, 3, and 4 can run as a waterfall — phase 3 starts as soon as phase 2 delivers its entities, phase 4 as soon as phase 3 does. Within each phase, all skills run concurrently. At peak: 4 agents running simultaneously in phase 4.

**Window B (phase 6)** unlocks after `assembly-planner` completes. `schema-assembler` and `marketing-director` have no dependency on each other and can deliver concurrently.

**Serialized chokepoints** are `script-validator` (blocks all creative vision work) and `continuity-enforcer` (blocks the entire assembly chain). These are the two hardest-to-parallelize nodes in the DAG — both require full-graph visibility.

---

## Schema coverage map

Every skill maps to entities that already exist in your `video-project-schema-v2.json` (confirmed against the `$defs` list extracted above):

| Skill | Primary `$defs` entities populated |
|---|---|
| concept-expander | `ProjectMeta`, `Story` (logline, synopsis), `GlobalSpecs` (draft) |
| narrative-architect | `Story.narrative_arc` |
| scriptwriter | `Script` |
| script-validator | `ValidationResult` |
| director | `DirectorNotes` |
| character-architect | `Character[]` in `AssetRegistry` |
| world-builder | `Environment[]`, `Prop[]` in `AssetRegistry` |
| art-director | `StyleGuide[]` in `AssetRegistry` |
| cinematographer | `CinematicSpec` per `Shot` |
| shot-designer | `Scene[]`, `Shot[]` (structure + `Transition[]`) |
| prompt-engineer | `GenParams`, `PromptRecord`, `GenerationCost` per `Shot` |
| voice-director | `AudioAsset[type=voice_over, dialogue]` |
| music-director | `AudioAsset[type=music]` |
| sfx-designer | `AudioAsset[type=sfx, ambient]` |
| continuity-enforcer | `TemporalConsistency`, `anchor_frame_ref` corrections |
| quality-critic | `QaGate` results per `Scene` and `Shot` |
| dependency-resolver | `DependencyEdge[]` |
| assembly-planner | `RenderPipeline`, `RenderPipelineStep[]`, `AssemblyErrorHandling` |
| schema-assembler | `VideoProject` (top-level validated instance) |
| marketing-director | `MarketingMaterial[]`, `PlatformDelivery[]`, `RenderOutput[]` |

No entity in the schema is left unassigned. No two skills write to the same entity cluster. This is the session-02 schema doing exactly what it was designed to do — acting as the single source of truth that forces the pipeline's structure to be explicit.

---

## What this implies for implementation

The three files from session-02 that most directly constrain the skill interfaces are: `video-project-schema-v2.json` (defines every skill's typed output), `term-map.json` (enforces vocabulary — e.g., `script-validator` must use `ValidationResult`, not some ad-hoc object), and `claude-20-styles-camera-v1.0.md` (the cinematographer skill must produce `CinematicSpec.shot_type` values from the formal taxonomy defined there, not free text).

A natural next step for session-03 — which the session-02 README already flagged — is to generate the TypeScript `zod` interfaces for each skill's input and output types directly from the `video-project-schema-v2.json`, so that the 20 skill contracts are machine-enforced rather than documented-and-hoped-for.