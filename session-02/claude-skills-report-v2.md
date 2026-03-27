---
title: "Autonomous Video Production Pipeline — Skill Decomposition Analysis"
version: "1.0.0"
schema_reference: "unified-video-project-v3.schema.json (v3.0.0)"
date: "2026-03-27"
disclaimer: >
  No information within this document should be taken for granted.
  Any statement or premise not backed by a real logical definition
  or verifiable reference may be invalid, erroneous, or a hallucination.
  This analysis is derived from structural inspection of the referenced
  JSON Schema and standard software decomposition heuristics — not from
  empirical validation of a running system.
---

# Autonomous Video Production Pipeline — Skill Decomposition

## 1. The Question

> Given the unified-video-project-v3 schema: how many distinct skills
> (modular AI agents / components) are required to take a single
> high-level creative idea and autonomously produce a fully populated
> schema instance that a downstream renderer can consume?

## 2. Decomposition Method

Skills were derived by applying three orthogonal criteria simultaneously:

| Criterion | Rule |
|---|---|
| **Domain Boundary** | If two functions require fundamentally different expertise (narrative writing vs. cinematography vs. audio engineering), they are separate skills. |
| **Schema Surface** | If two functions write to non-overlapping sets of entity types in the schema, they are separate skills — unless they always co-occur. |
| **Iteration Cycle** | If two functions have different refinement loops (e.g., story beats iterate independently of shot generation), they are separate skills even if they touch adjacent schema regions. |

A function is merged into another only when all three criteria overlap (same domain, same schema surface, same iteration cycle).

## 3. Answer

**24 skills**, organized into 8 pipeline tiers plus 1 meta-orchestration tier.

The range of defensible answers is **21–27**, depending on three boundary decisions documented in §5. The number 24 represents the decomposition that most faithfully follows the schema's own entity boundaries.

## 4. The 24 Skills

### Tier 1 — Creative Foundation

These skills transform a raw idea into structured narrative documents.

#### S01: Concept Seed Developer

- **Input:** Raw creative idea (free text)
- **Output:** `project` entity (summary, genres, audiences, languages, targetRuntimeSec, defaultQualityProfileRef) + initial `qualityProfiles[]` + initial `story` stub (logline, premise, themes, tone)
- **Schema surface:** `ProjectEntity`, `QualityProfileEntity`, `StoryEntity` (partial), `PackageInfo`
- **Rationale:** Project-level decisions (runtime target, audience, genre, quality profile) are architectural choices that constrain everything downstream. They require a different kind of reasoning than narrative development.

#### S02: Story Architect

- **Input:** `story` stub from S01, `project` constraints
- **Output:** Complete `story` entity — beats with ordering and emotional objectives, narrative arcs with character trajectories, scene references, marketing hooks
- **Schema surface:** `StoryEntity` (full), `StoryBeat[]`, `NarrativeArc[]`
- **Rationale:** Story structure (beat sheets, three-act architecture, arc design) is a distinct narrative-design discipline. Iteration here is about structural completeness and emotional pacing — different from both concept ideation and line-level writing.

#### S03: Scriptwriter

- **Input:** Complete `story`, `project` constraints
- **Output:** `script` entity — ordered segments (scene headings, actions, dialogue, voice-over, parentheticals, transitions, title cards, on-screen text) with scene/shot/speaker references and timing
- **Schema surface:** `ScriptEntity`, `ScriptSegment[]`
- **Rationale:** Scriptwriting is line-level composition with format constraints (Fountain, FDX, etc.). Its iteration cycle is dialogue polish and pacing — orthogonal to beat-level structural changes.

---

### Tier 2 — World Building

These skills create the persistent entities that populate the story world.

#### S04: Character Designer

- **Input:** `story`, `script` (character mentions), `directorInstructions` (if available)
- **Output:** `characters[]` — appearance, wardrobe, personality traits, age range, voice profile, canonical prompt fragments (weighted, ordered, categorized), banned traits, coherence requirements
- **Schema surface:** `CharacterEntity`, `VoiceProfile`, `PromptFragment[]`, `CharacterCoherence`
- **Rationale:** Character design requires visual-conceptual reasoning (appearance → prompt fragments) and consistency-constraint specification. Distinct from environment and prop design both in domain expertise and iteration cycle (characters refine through script revisions; environments are more static).

#### S05: Environment Designer

- **Input:** `story`, `script` (scene headings, action descriptions), `directorInstructions`
- **Output:** `environments[]` — location type (interior/exterior/mixed/virtual/abstract), architecture style, time-of-day defaults, weather defaults, continuity notes, canonical prompt fragments
- **Schema surface:** `EnvironmentEntity`, `PromptFragment[]`
- **Rationale:** Environment design is spatial/architectural reasoning. The schema treats environments as persistent entities referenced by scenes, not as per-shot properties — so their creation is a discrete, reusable step.

#### S06: Prop Designer

- **Input:** `script` (action lines mentioning objects), `story`, `environments[]`
- **Output:** `props[]` — category, continuity notes, canonical prompt fragments, reference asset refs
- **Schema surface:** `PropEntity`, `PromptFragment[]`
- **Merge candidate:** Could merge into S05 (World Builder). See §5.

---

### Tier 3 — Direction

These skills establish the creative and technical vision that governs all downstream generation.

#### S07: Director

- **Input:** `story`, `script`, `characters[]`, `environments[]`, `project` (genre, audience)
- **Output:** `directorInstructions` — vision statement, must-haves, must-avoids, camera language, editing language, performance direction, music direction, color direction, targeted notes (with priority and category), quality rules. Also creates `production.styleGuides[]` — versioned, scoped style guides that carry rights provenance and approval workflow.
- **Schema surface:** `DirectorInstructionsEntity`, `TargetedNote[]`, `ValidationRule[]`, `StyleGuideEntity[]` (→ `production.styleGuides`), `StyleGuidelines`
- **Rationale:** The director skill synthesizes all creative inputs into binding constraints. It operates at the level of intent ("I want chiaroscuro lighting in act 2") rather than parameter specification ("f/2.8, 3200K"). Its output governs every downstream skill. Style guides are a director's creative authority artifact — registering them as `StyleGuideEntity` (with `scope`, `rights`, `approvalChain`, `version`) restores rights provenance and approval workflow that was lost when style was modelled as an inline embed (`StyleGuidelines`) in v3.0.0.

#### S08: Cinematographer

- **Input:** `script`, `directorInstructions`, `characters[]`, `environments[]`, `story.beats[]`, `production.styleGuides[]` (from S07)
- **Output:** `shots[]` — shot number, purpose, description, target duration, character/environment/prop refs, cinematic spec (shot type, camera angle, camera movement, focal length, aperture, DOF, sensor format, hyperfocal distance, FOV, stabilization, focus mode, framing, composition, lighting guidelines, style guidelines, color palette, temporal bridge anchor refs), VFX notes, continuity notes
- **Schema surface:** `ShotEntity`, `CinematicSpec`, `LightingGuidelines`, `StyleGuidelines` (inline), `CinematicSpec.styleGuideRef` → `StyleGuideEntity`, `ManimConfig` (if procedural)
- **Rationale:** Shot design is technical cinematography — optics (the formal tuple Ξ = (F, T, α, p, R, L, A_sub) referenced in the schema), camera movement vocabulary, and visual storytelling through framing. Fundamentally different expertise from narrative direction. The cinematographer selects which `StyleGuideEntity` from the registry (by `styleGuideRef`) applies to each shot, overriding it inline via `style` only for shot-specific deviations.

---

### Tier 4 — Scene Composition

#### S09: Scene Composer

- **Input:** `shots[]`, `story.beats[]`, `script`, `directorInstructions`, `characters[]`, `environments[]`, `props[]`
- **Output:** `scenes[]` — scene number, synopsis, story beat refs, script segment refs, director note refs, character/environment/prop refs, time of day, weather, mood, target duration, planned position, shot refs (ordered), transition in/out specs, QA gate configuration
- **Schema surface:** `SceneEntity`, `TransitionSpec`, `QaGate`
- **Rationale:** Scene composition is an editorial/continuity function: it organizes shots into coherent dramatic units, enforces spatial and temporal continuity, assigns transitions, and configures quality gates. This is distinct from both shot design (S08) and timeline assembly (S17).

---

### Tier 5 — Audio Production

Three skills, split by the three fundamentally different audio disciplines.

#### S10: Music Composer

- **Input:** `story` (themes, tone), `directorInstructions` (music direction), `scenes[]` (mood, timing)
- **Output:** `audioAssets[]` where audioType ∈ {music, stem} — mood, lyrics (if applicable), sync points (beat-locked), scene/shot refs, technical spec (sample rate, bit depth, channel layout, loudness, codec)
- **Schema surface:** `AudioAssetEntity` (music/stem subtypes), `SyncPoint`, `AudioTechnicalSpec`
- **Rationale:** Music composition requires understanding of harmony, rhythm, emotional mapping to narrative beats, and sync-point specification. A categorically different discipline from SFX or dialogue.

#### S11: Sound Designer

- **Input:** `script` (action descriptions), `shots[]`, `scenes[]`, `environments[]`, `directorInstructions`
- **Output:** `audioAssets[]` where audioType ∈ {sfx, foley, ambient} — purpose, mood, sync points, scene/shot refs, technical spec
- **Schema surface:** `AudioAssetEntity` (sfx/foley/ambient subtypes), `SyncPoint`, `AudioTechnicalSpec`
- **Rationale:** Sound design (foley, SFX, ambience) requires understanding of diegetic/non-diegetic sound, spatial audio, and emotional reinforcement through sound. Different from music composition in both skill set and iteration cycle.

#### S12: Voice / Dialogue Producer

- **Input:** `script` (dialogue/VO segments), `characters[]` (voice profiles), `directorInstructions` (performance direction)
- **Output:** `audioAssets[]` where audioType ∈ {voice_over, dialogue} — speaker ref, character ref, transcript, language, sync points, technical spec. Also updates `script.segments[].audioAssetRef` with generated audio references.
- **Schema surface:** `AudioAssetEntity` (voice_over/dialogue subtypes), `VoiceProfile`, `ScriptSegment.audioAssetRef`
- **Rationale:** Voice production involves TTS model selection, voice cloning, performance direction interpretation, and timing alignment to visuals. It reads from character voice profiles and writes audio assets with precise sync points.

---

### Tier 6 — Visual Generation

#### S13: Reference Asset Generator

- **Input:** `characters[]` (prompt fragments), `environments[]` (prompt fragments), `props[]`, `directorInstructions` (style, color direction)
- **Output:** `visualAssets[]` where isCanonicalReference=true, modality=image — character reference sheets, environment concept art, prop references. Sets up `ConsistencyAnchor[]` at entity level.
- **Schema surface:** `VisualAssetEntity` (reference subset), `ConsistencyAnchor`, `GenerationManifest`, `GenerationStep`
- **Rationale:** Reference image generation is a one-time-per-entity process that produces the visual anchors all subsequent generation depends on. It requires careful prompt engineering for consistency and typically uses different models/workflows than video generation.

#### S14: Shot Video Generator

- **Input:** `shots[]` (cinematic spec, gen params), reference `visualAssets[]`, `consistencyAnchors[]`, `directorInstructions`
- **Output:** `visualAssets[]` where modality=video — per-shot generated video clips with full generation manifests (steps, seeds, prompts, costs, retry config, async config, model descriptors, adapter inputs)
- **Schema surface:** `VisualAssetEntity` (video subset), `GenerationManifest`, `GenerationStep`, `ModelDescriptor`, `AdapterInput`, `ReferenceInput`, `GenerationCost`, `RetryConfig`, `AsyncConfig`
- **Rationale:** Shot video generation is the most computationally expensive and iteration-heavy step. It requires temporal consistency enforcement, character coherence, temporal bridge patterns (conditioning on last frame of preceding shot), and manages the full generation audit trail. Different models, different parameters, different failure modes from reference image generation.

---

### Tier 7 — Prompt Engineering & Consistency

#### S15: Prompt Composer

- **Input:** All entities with `canonicalPromptFragments` (characters, environments, props), `directorInstructions`, `shots[].cinematicSpec`, quality profiles
- **Output:** Assembled, optimized prompts and negative prompts written into `GenerationStep.prompt`, `GenerationStep.negativePrompt`, `PromptRecord[]` (versioned audit trail). Manages `PromptFragment` ordering, weighting, and locked-fragment preservation.
- **Schema surface:** `PromptFragment`, `PromptRecord`, `GenerationStep` (prompt fields only)
- **Rationale:** Prompt composition is a cross-cutting concern. Every generation skill (S13, S14, S10, S11, S12) needs assembled prompts, but the logic of combining weighted fragments, respecting insertion order, honoring locked fragments, and optimizing for specific models is a single, reusable discipline. Centralizing it ensures prompt consistency and enables systematic prompt versioning.

#### S16: Consistency Enforcer

- **Input:** Generated `visualAssets[]`, `characters[]` (coherence requirements), quality profiles (temporal consistency, character coherence), `shots[]` (temporal bridge anchors)
- **Output:** Updated `ConsistencyAnchor[]` (with lock levels: soft/medium/hard), coherence scores, temporal consistency scores, flicker scores, identity drift scores. Triggers re-generation when thresholds are violated.
- **Schema surface:** `ConsistencyAnchor`, `CharacterCoherence`, `TemporalConsistency`, `ShotEntity.cinematicSpec.temporalBridgeAnchorRef`
- **Rationale:** Consistency enforcement is a verification loop that runs after every generation pass. It compares generated outputs against anchors and coherence requirements, using different metrics (similarity scores, flicker detection, identity drift) than the QA validator (which checks technical quality). Its iteration cycle is tightly coupled with S14 but its logic is distinct.

---

### Tier 8 — Assembly & Post-Production

#### S17: Timeline Assembler

- **Input:** Generated video `visualAssets[]`, audio `audioAssets[]`, `scenes[]` (shot order, transitions), `shots[]` (assembly hints, planned positions)
- **Output:** `assembly.timelines[]` — timeline entities with video/audio/subtitle clips placed at correct positions, layer orders, sync points, transitions, stream bindings. Also creates `assembly.editVersions[]` with change lists.
- **Schema surface:** `TimelineEntity`, `TimelineClip`, `StreamBinding`, `EditVersionEntity`, `TransitionSpec`, `SyncPoint`, `AssemblyHints`
- **Rationale:** Timeline assembly is an editorial function: placing clips on tracks with correct timing, layering, and synchronization. The 4-layer assembly model (Timeline → EditVersion → RenderPlan → FinalOutput) makes this a distinct architectural concern.

#### S18: Post-Production Processor

- **Input:** Assembled `timelines[]`, `directorInstructions` (color direction), quality profiles (video quality controls), `genericAssets[]` (LUTs)
- **Output:** Operations added to timelines and render plans — `ColorGradeOp`, `OverlayOp`, `FilterOp`, `RetimeOp` with appropriate parameters, LUT references, and compatible runtimes specified.
- **Schema surface:** `ColorGradeOp`, `OverlayOp`, `FilterOp`, `RetimeOp`, `Transform`, `RetimeSpec`, `CompressionControls`
- **Rationale:** Post-production (color grading, compositing, filtering, speed ramping) is a distinct craft with its own vocabulary and toolchain. The schema models these as discriminated `Operation` types, each with specific parameters. Merging them into timeline assembly would conflate clip placement with visual treatment.

#### S19: Audio Mixer

- **Input:** All `audioAssets[]`, `timelines[]` (for sync), `directorInstructions`, quality profiles (audio quality controls — loudness targets, true peak limits, dialog intelligibility)
- **Output:** `AudioMixOp` operations — track references with gain, pan, time ranges, sync points. Manages the final mix to target loudness (LUFS), true peak (dBTP), and dialog clarity.
- **Schema surface:** `AudioMixOp`, `AudioMixTrack`, `AudioQualityControls`
- **Rationale:** Audio mixing is a dedicated engineering discipline. It requires understanding of loudness standards (EBU R128 / ATSC A/85), frequency management, spatial placement, and ducking. The schema models it as a specific operation type with precise technical parameters.

#### S20: Render Plan Builder

- **Input:** `assembly.timelines[]`, `assembly.editVersions[]`, post-production `Operation[]`, quality profiles, `project` constraints
- **Output:** `assembly.renderPlans[]` — typed operation sequences, compatible runtimes (moviepy/movis/opencv/pyav/manim/ffmpeg), color pipeline configuration, runtime hints. Links to target output refs.
- **Schema surface:** `RenderPlanEntity`, `Operation[]` (ordered), compatible runtimes enum
- **Rationale:** Render planning translates an edit + post-production operations into an executable, runtime-specific plan. It must select compatible runtimes, order operations for efficiency, and validate that all operations are supported by the chosen runtime. This is build-system logic, distinct from creative editorial decisions.

---

### Tier 9 — Quality Assurance

#### S21: QA Validator

- **Input:** All entities with QA gates (`scenes[]`, `shots[]`), quality profiles, validation rules, generated assets
- **Output:** Populated `QaGate` objects (required checks, pass threshold, individual `QaCheck` results with scores, overall pass boolean), `QCResult[]` on deliverables, `ValidationNode` outputs in workflow graphs
- **Schema surface:** `QaGate`, `QaCheck`, `QCResult`, `ValidationRule`, `ValidationNode`
- **Rationale:** Quality validation is an automated verification gate that blocks downstream progression (assembly, rendering, delivery) when quality thresholds are not met. It is the enforcement mechanism for the director's quality rules and the project's quality profiles. Its logic (run checks, compare to thresholds, gate/pass) is fundamentally different from both consistency enforcement (S16, which deals with visual similarity) and creative evaluation.

---

### Tier 10 — Packaging & Delivery

#### S22: Deliverable Packager

- **Input:** `assembly.renderPlans[]`, rendered outputs, `project` (languages, audiences), `directorInstructions`
- **Output:** `deliverables[]` (FinalOutputEntity) — output type, platform, release channel, runtime, source timeline/edit/render plan refs, QC results, localization targets (language, subtitle track refs, dubbed audio refs, adapted marketing refs), accessibility config (WCAG level, closed/open captions, audio description, sign language), platform deliveries (per-platform format, aspect ratio, resolution, frame rate, max duration, publish schedule)
- **Schema surface:** `FinalOutputEntity`, `LocalizationConfig`, `AccessibilityConfig`, `PlatformDelivery`
- **Rationale:** Deliverable packaging is the final mile: adapting the rendered output for specific platforms (YouTube, Instagram, TikTok, broadcast, theatrical, streaming) with correct format specs, scheduling publication, and configuring localization/accessibility. This is a distribution-engineering concern, not a creative one.

#### S23: Marketing Asset Generator

- **Input:** `story` (marketing hooks), `scenes[]`, `shots[]`, `visualAssets[]`, `audioAssets[]`, `project`
- **Output:** `marketingAssets[]` — type (trailer, teaser, thumbnail, social clip, poster, banner, press kit), campaign ID, target platforms, duration, story ref, originating hook, source scene/shot/asset refs, copy pack (headline, caption, body, CTA, hashtags, alt text), assembly plan ref, thumbnail source ref
- **Schema surface:** `MarketingAssetEntity`, `CopyPack`
- **Rationale:** Marketing asset creation requires understanding of platform-specific best practices (thumbnail psychology, trailer pacing, social clip hooks), copy writing, and campaign strategy. It is downstream of the main production pipeline and references completed production entities.

---

### Meta-Tier — Orchestration

#### S24: Pipeline Orchestrator

- **Input:** All schema state, skill status reports, QA gate results
- **Output:** `orchestration.workflows[]` — workflow graphs with typed nodes (GenerationNode, ApprovalNode, TransformNode, RenderNode, ValidationNode, NotificationNode, CustomWorkflowNode) and conditional edges. Manages `dependencies[]` (typed DAG edges: requires, blocks, derives_from, supersedes, references, syncs_with), `relationships[]`, entity lifecycle state transitions, cost tracking via `budget`, and governance enforcement.
- **Schema surface:** `Orchestration`, `WorkflowGraph`, `WorkflowNode` (all 7 discriminated subtypes), `WorkflowEdge`, `DependencyEdge`, `Relationship`, `Budget`, `Governance`, `VersioningPolicy`, `NamingConventions`
- **Also responsible for:** DAG acyclicity validation (Rule 14), EntityRef resolution via VersionSelector, content hash computation for published entities, version management (branching, supersession, derivation), approval chain orchestration.
- **Rationale:** The orchestrator is the meta-skill. It does not create content — it sequences skills, manages the dependency graph, enforces governance policies, resolves version references, tracks costs, and handles retry/async patterns for long-running generation calls. Every other skill operates within the context the orchestrator provides.


## 5. Boundary Decisions (Where Reasonable People Disagree)

Three decomposition decisions shift the count between 21 and 27:

### Decision A: Prop Designer (S06) — Merge or Keep?

**Current:** Separate skill (S06).
**Merge target:** S05 (Environment Designer → World Builder).
**Argument for merging:** `PropEntity` is thin (4 domain-specific fields beyond BaseEntity). Props typically emerge from script analysis alongside environments. Same iteration cycle.
**Argument against:** The schema defines `PropEntity` as a distinct top-level production entity. Props have their own reference assets and consistency anchors. In complex productions, prop continuity (e.g., a sword that appears in multiple scenes) is a genuine tracking concern.
**Impact:** Merge → 23 skills.

### Decision B: Post-Production (S18) + Audio Mixer (S19) — Merge or Keep?

**Current:** Separate skills.
**Merge target:** Combined "Post-Production Processor" handling all operations.
**Argument for merging:** Both are "apply operations to timeline" functions. The schema models them as `Operation` subtypes within the same discriminated union.
**Argument against:** Video post-production (color grading, compositing, filtering) and audio mixing (loudness normalization, spatial placement, track balancing) are entirely different engineering domains. They use different tools, different standards (Rec. 709 vs. EBU R128), and different quality metrics.
**Impact:** Merge → 23 skills.

### Decision C: Consistency Enforcer (S16) — Merge into QA Validator (S21)?

**Current:** Separate skills.
**Argument for merging:** Both are "check quality and gate progression" functions.
**Argument against:** Consistency enforcement operates within the generation loop (it triggers re-generation), while QA validation operates at stage gates (it blocks progression to the next pipeline tier). Different schemas too: S16 works with `ConsistencyAnchor`, `CharacterCoherence`, `TemporalConsistency`; S21 works with `QaGate`, `QaCheck`, `QCResult`. Different scope — S16 is per-shot/per-entity; S21 is per-scene/per-deliverable.
**Impact:** Merge → 23 skills.

### Additional split candidates (would increase count):

- **Splitting S14** into "Image-to-Video Generator" and "Text-to-Video Generator" (different model families, different parameter spaces) → 25 skills.
- **Extracting a dedicated Localization Skill** from S22 (subtitle generation, dubbing, adapted marketing) → 25 skills.
- **Extracting a Schema Integrity Validator** from S24 (pure JSON Schema validation + cross-reference integrity checking as a utility skill) → 25 skills.


## 6. Pipeline DAG

The skills form a directed acyclic graph. Here is the dependency structure (an edge A → B means "A must complete before B can begin"):

```
S01 (Concept)
 ├─→ S02 (Story)
 │    ├─→ S03 (Script)
 │    │    ├─→ S04 (Characters)
 │    │    ├─→ S05 (Environments)
 │    │    ├─→ S06 (Props)
 │    │    └─→ S12 (Voice/Dialogue)
 │    └─→ S23 (Marketing)
 │
 ├─→ S07 (Director) ←── [also depends on S03, S04, S05]
 │    ├─→ S08 (Cinematographer)
 │    │    └─→ S09 (Scene Composer) ←── [also depends on S04, S05, S06]
 │    │         └─→ S17 (Timeline) ←── [depends on all gen outputs]
 │    ├─→ S10 (Music)
 │    ├─→ S11 (Sound Design)
 │    └─→ S13 (Reference Assets) ←── [also depends on S04, S05, S06]
 │         └─→ S14 (Shot Video Gen) ←── [also depends on S08, S15, S16]
 │
 S15 (Prompt Composer) ←── [cross-cutting: depends on S04-S08, feeds S13, S14]
 S16 (Consistency) ←── [loop with S14: runs after each generation pass]
 │
 S17 (Timeline)
  ├─→ S18 (Post-Production)
  ├─→ S19 (Audio Mixer) ←── [depends on S10, S11, S12]
  └─→ S20 (Render Planner) ←── [depends on S18, S19]
       └─→ S21 (QA Validator)
            └─→ S22 (Deliverable Packager)
                 └─→ S23 (Marketing) ←── [can run partially in parallel]

S24 (Orchestrator) ── manages all edges, gates, retries, cost tracking
```

**Critical path** (longest sequential chain):
S01 → S02 → S03 → S04 → S07 → S08 → S09 → S13 → S14 → S17 → S18 → S20 → S21 → S22

**Parallelizable groups** at each tier:
- Tier 2: S04 ∥ S05 ∥ S06 (all depend on S03, independent of each other)
- Tier 5: S10 ∥ S11 ∥ S12 (all audio, independent)
- Tier 6: S13 before S14 (reference images anchor shot generation)
- Tier 8: S18 ∥ S19 (video post and audio mix are independent until render plan)


## 7. Schema Coverage Matrix

Every required top-level property of the schema must be populated by at least one skill. Here is the coverage:

| Schema Top-Level Property | Responsible Skill(s) |
|---|---|
| `schemaVersion` | S24 (Orchestrator) |
| `package` | S01 + S24 |
| `project` | S01 |
| `qualityProfiles` | S01 (initial) + S24 (lifecycle) |
| `team` | S24 (optional, configuration) |
| `canonicalDocuments.story` | S01 + S02 |
| `canonicalDocuments.script` | S03 |
| `canonicalDocuments.directorInstructions` | S07 |
| `production.characters` | S04 |
| `production.environments` | S05 |
| `production.props` | S06 |
| `production.scenes` | S09 |
| `production.shots` | S08 |
| `production.styleGuides` | S07 |
| `assetLibrary.visualAssets` | S13 + S14 |
| `assetLibrary.audioAssets` | S10 + S11 + S12 |
| `assetLibrary.marketingAssets` | S23 |
| `assetLibrary.genericAssets` | S18 (LUTs) + S24 (other) |
| `orchestration` | S24 |
| `assembly.timelines` | S17 |
| `assembly.editVersions` | S17 |
| `assembly.renderPlans` | S20 |
| `deliverables` | S22 |
| `relationships` | S24 |
| `dependencies` | S24 |

**Coverage is complete.** Every required field maps to at least one skill.


## 8. Cross-Cutting Concerns

Several schema patterns appear across multiple entity types. These are handled by dedicated cross-cutting skills:

| Cross-Cutting Concern | Pattern | Handling Skill |
|---|---|---|
| Prompt fragment composition | `canonicalPromptFragments: PromptFragment[]` on Characters, Environments, Props | S15 (Prompt Composer) |
| Generation audit trail | `GenerationManifest` + `GenerationStep` on any generated entity | S13, S14 (write); S15 (prompt fields); S24 (cost tracking) |
| Consistency enforcement | `ConsistencyAnchor`, `CharacterCoherence`, `TemporalConsistency` | S16 (Consistency Enforcer) |
| Quality gating | `QaGate` on Scenes, Shots; `QCResult` on deliverables | S21 (QA Validator) |
| Version management | `VersionInfo`, `VersionSelector`, `EntityRef` resolution | S24 (Orchestrator) |
| Approval workflows | `Approval`, `ApprovalRecord`, `ApprovalNode` | S24 (Orchestrator) |
| Cost tracking | `GenerationCost`, `Budget` | S24 (Orchestrator) |
| Rights / compliance | `Rights`, `Compliance` | S24 (Orchestrator, configuration-level) |


## 9. Skill Interface Contract (Summary)

Every skill operates under the same contract:

1. **Receives:** A reference to the current schema instance (or the relevant subset) + the orchestrator's execution context (which workflow node triggered it, retry count, cost budget remaining).
2. **Validates preconditions:** Checks that all required upstream entities exist and are in an acceptable state (≥ `draft`).
3. **Produces:** New or updated entities written to the schema instance, with:
   - `VersionInfo` (number, state, change summary, derivedFrom/supersedes)
   - `GenerationManifest` (if the skill invokes a generative model)
   - `createdAt` / `updatedAt` timestamps
   - All `EntityRef` links properly resolved
4. **Reports:** Status (succeeded/failed), cost incurred, QA results (if applicable), entities created/modified.
5. **Idempotency:** Re-running a skill with the same inputs and version selectors must produce a deterministic result (or declare `reproducibility.deterministic: false`).