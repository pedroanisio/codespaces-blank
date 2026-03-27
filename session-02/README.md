# Session 02 — Generative-AI Video Production Schema

**Objective:** Design a tool-agnostic, extensible data model for orchestrating generative-AI video production — from narrative arc and script through per-shot generation parameters, asset versioning, quality controls, and programmatic assembly — supporting any current or future AI video tool (Runway, Kling, Luma, Pika, Midjourney, ElevenLabs, Stable Diffusion) and Python assembly libraries (MoviePy, Movis, OpenCV, PyAV, Manim).

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

---

## Quick Start

The canonical production schema is **[video-project-schema-v2.json](./video-project-schema-v2.json)**.
Production terminology is defined in **[term-map.json](./term-map.json)**.

```
prompt-video-schema.md          ← original requirements
        ↓
[AI schema drafts]              ← grok, manus, perplexity, claude v1
        ↓
video-project-schema-v2.json    ← unified v2 (canonical)
term-map.json                   ← machine-readable vocabulary
```

---

## File Index

### Schemas

| File | Version | Size | Description |
|------|---------|------|-------------|
| [video-project-schema-v2.json](./video-project-schema-v2.json) | **v2.0.0** | 54 KB | **Canonical unified schema.** Merges all drafts and adds cost tracking, retry/async logic, rights, collaboration, QA gates, platform delivery, localization, accessibility. |
| [grok-video-schema.json](./grok-video-schema.json) | v1.0 + patch | 19 KB | Grok draft — strict `additionalProperties: false`. Patched with canonical status enum, `cost`, `retryConfig`, `asyncConfig`, `promptVersion`. |
| [claude-video-production-schema-v1.0.json](./claude-video-production-schema-v1.0.json) | v1.0 | 49 KB | Claude v1 draft — comprehensive GenParams, temporal bridge pattern, asset registry, CinematicSpec, Manim integration. |
| [manus-video_orchestration_schema_complete.md](./manus-video_orchestration_schema_complete.md) | v1.0 | 48 KB | Manus draft — full entity-relationship model, assembly instructions, Python library bindings, usage examples. |
| [perplexity-VideoProject JSON Schema — Comprehensive Generative-AI Video Production Schema.md](./perplexity-VideoProject%20JSON%20Schema%20%E2%80%94%20Comprehensive%20Generative-AI%20Video%20Production%20Schema.md) | v1.0 | 50 KB | Perplexity draft — five design principles, temporal bridge pattern, QualitySpec presets, CinematicSpec, LoRA/ControlNet anchors. Updated with v2 navigation banner. |
| [prompt-video-schema.md](./prompt-video-schema.md) | — | 2 KB | Original requirements spec: what the schema must support. Start here for context. |

### Taxonomies

| File | Version | Size | Description |
|------|---------|------|-------------|
| [term-map.json](./term-map.json) | v1.0.0 | 13 KB | **Machine-readable term map.** Defines 10 production vocabulary terms across 4 axes (domain, vocabulary type, diegetic status, pipeline stage) with corrected misuses and overlap types. |
| [claude-corrected_term_map.html](./claude-corrected_term_map.html) | v1.0 | 21 KB | Interactive HTML version of the term map with clickable definitions. Human-facing counterpart to term-map.json. |
| [claude-20-styles-video-v1.1.md](./claude-20-styles-video-v1.1.md) | v1.1 | 26 KB | Formal mathematical definitions of 20 video styles (documentary, fiction, animation, vlog, VR, surveillance, etc.) as biconditional predicates using possible-worlds semantics. |
| [claude-20-styles-camera-v1.0.md](./claude-20-styles-camera-v1.0.md) | v1.0 | 35 KB | Formal definitions of camera angles, movements, and optical effects using 3D coordinate systems and paraxial optics equations (DOF, hyperfocal distance, AoV). |
| [claude-20-styles-scene-v1.0.md](./claude-20-styles-scene-v1.0.md) | v1.0 | 31 KB | Scene ontology: diegetic location/time (Genette), ontological status (objective/subjective/non-diegetic), editing grammar, shot-scale taxonomy. |
| [claude-animation-taxonomy-v1.0.md](./claude-animation-taxonomy-v1.0.md) | v1.0 | 53 KB | Animation as an artifact class `A` — production method, visual style, content domain, delivery channel, playback modality. Covers traditional 2D through generative/live-rendered. |

### Research Data

| File | Size | Description |
|------|------|-------------|
| [perplexity-youtube_styles_research.xlsx](./perplexity-youtube_styles_research.xlsx) | 22 KB | Empirical research dataset on YouTube video styles. Informs the style taxonomy and schema design decisions. |

---

## Schema Architecture (v2.0.0)

### Entity-Relationship Model

```
VideoProject
├── project_meta          client, code, budget, compliance, localization
├── team                  members with roles + permissions
├── global_specs          quality_spec, temporal_consistency, render_constraints
├── story                 logline, synopsis, narrative_arc acts/beats
├── script                lines (scene_heading, action, dialogue…) with timing
├── director_notes        vision, tone, quality_rules, per-scene overrides
├── asset_registry
│   ├── characters[]      visual sheets, voice ref, consistency anchors, rights
│   ├── environments[]    location references, rights
│   ├── props[]           object references, rights
│   └── style_guides[]    color palette, art style, cinematic_spec
├── scenes[]
│   ├── qa_gate           required checks, pass threshold, per-check scores
│   ├── approval_chain[]  per-role decisions with deadlines
│   ├── comments[]        timecoded, threaded annotations
│   └── shots[]
│       ├── cinematic_spec  shot type, lens, lighting, color palette
│       ├── gen_params      tool, prompt + history, anchors, LoRA, cost, retry, async
│       ├── assembly        timeline, layer, blend_mode, transitions, color_grade
│       ├── qa_gate
│       └── approval_chain[]
├── visual_assets{}       images, clips, storyboards — with rights + approval
├── audio_assets{}        VO, dialogue, music, SFX — with sync + rights
├── marketing_materials{} trailers, thumbnails, social clips + platform deliveries
├── render_pipeline       structured steps (MoviePy/OpenCV/PyAV/Manim) + validation
└── outputs[]
    ├── quality_metrics   coherence scores, prompt adherence, QA passed
    ├── platform_deliveries[]  per-platform metadata + publish schedule
    ├── localization      subtitle tracks, dubbed audio per language
    └── accessibility     WCAG level, captions, audio descriptions
```

### Key Design Principles

| # | Principle | Detail |
|---|-----------|--------|
| 1 | **Tool-agnosticism** | `gen_params.extra` accepts any provider-specific key without schema changes |
| 2 | **Asset-First decomposition** | Characters/environments defined once in registry; referenced everywhere. Dropping anchors drops coherence scores from 7.99 → 0.55 |
| 3 | **Temporal Bridge pattern** | Each shot's `anchor_frame_ref` conditions generation on the last frame of the preceding shot |
| 4 | **Semantic versioning everywhere** | `VersionRecord` with `parent_version_id` on every entity; canonical `StatusEnum` across all |
| 5 | **Programmatic assembly** | `AssemblyInstruction` fields map directly to MoviePy, Movis, OpenCV, PyAV, Manim — no translation layer |
| 6 | **Cost-aware generation** | `GenerationCost` + `GenerationAttempt[]` on every gen call — full cost audit trail |
| 7 | **Resilient async orchestration** | `RetryConfig` (backoff, fallback tool) + `AsyncConfig` (webhook, polling) for long-running jobs |
| 8 | **Rights-first assets** | Every asset carries `Rights` (license type, expiry, talent release, territory) |
| 9 | **Collaborative review** | `Team`, timecoded `Comment[]`, `ApprovalRecord[]` with deadlines on every entity |
| 10 | **Quality-gated assembly** | `QaGate` on scenes and shots; `ValidationResult` on the render pipeline |
| 11 | **Multi-platform delivery** | `PlatformDelivery[]`, `LocalizationConfig`, `AccessibilityConfig` on every output |

### Canonical Status Lifecycle

```
draft → generating → review → changes_requested → approved → archived
```

All versioned entities (assets, scenes, shots, outputs) share this enum.

### Supported Generative-AI Tools

`gen_params.tool` accepts any string. Documented integrations:

| Category | Tools |
|----------|-------|
| Video generation | Runway Gen-4, Kling v3, Luma Dream Machine, Pika 2.2 |
| Image generation | Midjourney v7, Stable Diffusion XL, DALL·E, Firefly |
| Audio / Voice | ElevenLabs, Suno, Udio |
| Animation / Math | Manim CE, ComfyUI |
| Custom pipelines | Any tool via `gen_params.extra` |

### Python Assembly Libraries

| Library | Operations |
|---------|-----------|
| **MoviePy** | concat, overlay_audio, add_transition, apply_effect |
| **Movis** | timeline compositing, layer management |
| **OpenCV** | frame-by-frame filters (`opencv_filters[]`) |
| **PyAV** | low-level codec control (`pyav_stream_params`) |
| **Manim** | mathematical/data animation (`manim_config` in CinematicSpec) |
| **FFmpeg** | encode, package, format conversion |

---

## Vocabulary Reference

The [term-map.json](./term-map.json) defines terms along four axes:

| Axis | Values |
|------|--------|
| **Domain** | `audio` / `visual` |
| **Vocabulary Type** | `aesthetic` / `operational` |
| **Diegetic Status** | `diegetic` / `non_diegetic` / `either` |
| **Pipeline Stage** | `pre_production` / `production` / `post_production` / `distribution` |

### Key Corrected Distinctions

| ❌ Common Confusion | ✅ Correct Distinction |
|---|---|
| VFX = color grading | VFX is compositing/CGI (post, visual, operational). Color grading is a DI session (post, visual, aesthetic). Separate departments. |
| "Graphic novel style" | Graphic novel is a **format**, not a style. Specify: "Frank Miller noir ink", "Moebius ligne claire", etc. |
| Soundtrack = all film audio | Soundtrack = music specifically. Sound FX, dialogue, and foley are separate. |
| Motion graphics ⊂ VFX | Motion graphics **hand off to** VFX for compositing — collaboration, not containment. |
| Light style = light FX | Light style = DP's aesthetic language (pre-production). Light FX = specific phenomena (lens flares, god rays) — practical or synthetic. |

---

## Taxonomy Coverage

### 20 Video Styles ([claude-20-styles-video-v1.1.md](./claude-20-styles-video-v1.1.md))

Defined as formal biconditional predicates on capture modality × epistemic contract × temporal coupling × distribution format × production intent:

Documentary · Narrative Fiction · Animation · Commercial · Music Video · News Broadcast · Essay Film · Experimental · Tutorial · Vlog · Live Stream · Short-Form Vertical · Interview · Motion Graphics · Sports Broadcast · Surveillance/CCTV · 360°/VR · Screencast · Found Footage · Mockumentary

### Camera System ([claude-20-styles-camera-v1.0.md](./claude-20-styles-camera-v1.0.md))

Shot tuple `Ξ = (F, T, α, p, R, L, A_sub)` with full 3D coordinate system:
- **Angles:** eye-level, low, high, dutch/canted, over-the-shoulder
- **Movements:** static, pan, tilt, dolly, crane, orbit, handheld, zoom
- **Optics:** focal length, f-number, DOF (paraxial), hyperfocal distance, AoV
- **Effects:** lens flare, bokeh, chromatic aberration, anamorphic squeeze, rack focus

### Scene Grammar ([claude-20-styles-scene-v1.0.md](./claude-20-styles-scene-v1.0.md))

Scene tuple `Σ = (F, T, α, λ, τ_d, ω, η, ψ, ρ)`:
- **Ontological status:** objective, subjective, non-diegetic
- **Temporal displacement:** analeptic (flashback), proleptic (flash-forward), synchronous
- **Shot scale:** XCU → CU → MCU → MS → MWS → WS → EWS
- **Editing grammar:** continuity, discontinuity, associative, parallel

### Animation Taxonomy ([claude-animation-taxonomy-v1.0.md](./claude-animation-taxonomy-v1.0.md))

Animation artifact `A = (F, T, μ, s, ι, χ, β, δ)`:
- **Production methods:** drawn-2d, rendered-3d, stop-motion, physical-manipulation, screen-capture, hybrid, generative
- **Automation degree:** 0 (fully manual) → 1 (fully algorithmic)
- **Playback modality:** fixed, interactive, generative, live-rendered
- **Delivery channels:** linear, interactive, spatial, real-time

---

## How the Files Relate

```
perplexity-youtube_styles_research.xlsx
        │  (empirical data)
        ▼
prompt-video-schema.md ──────────────────────────────────────────────────┐
        │  (requirements)                                                  │
        ▼                                                                  │
┌───────────────────────────────────────────────┐                         │
│  AI Schema Drafts (v1)                        │                         │
│  ├── grok-video-schema.json                   │  (formal taxonomy)      │
│  ├── manus-video_orchestration_schema...md    │◄────────────────────────┤
│  ├── perplexity-VideoProject...md             │  claude-20-styles-*.md  │
│  └── claude-video-production-schema-v1.0.json │  claude-animation-*.md  │
└───────────────────────────────────────────────┘                         │
        │  (merged + enhanced)                                             │
        ▼                                                                  │
video-project-schema-v2.json  ◄──── term-map.json ◄── claude-corrected_  │
   (canonical schema v2)             (vocabulary)      term_map.html      │
```

---

## Session Context

This session is part of the **SAFE AI Production** project. See [session-01](../session-01/) for the project overview and [../README.md](../README.md) for the full project structure.

**Next steps for session-03:**
- Pydantic v2 models generated from `video-project-schema-v2.json`
- TypeScript types (`zod` schema) for frontend tooling
- Example project instance (a complete 3-minute short film JSON)
- Validation CLI: `vidproject validate <project.json>`
- Integration guide for each supported AI tool
