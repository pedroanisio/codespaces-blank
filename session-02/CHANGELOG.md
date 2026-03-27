# Changelog — Session 02

All notable changes to the Session 02 schema and tooling are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

---

## [Unreleased]

---

## [2026-03-27] — Taxonomy integration, validation tooling, and example instance

### Added

#### `video-project-schema-v2.json`
- **`VideoStyleEnum`** (`$defs`) — 20 slugified video-style identifiers derived from the formal biconditional predicate definitions in `claude-20-styles-video-v1.1.md`. Values: `documentary`, `narrative_fiction`, `animation`, `commercial`, `music_video`, `news_broadcast`, `essay_film`, `experimental`, `tutorial`, `vlog`, `live_stream`, `short_form_vertical`, `interview_talking_head`, `motion_graphics_explainer`, `sports_broadcast`, `surveillance_cctv`, `vr_360`, `screencast`, `found_footage`, `mockumentary`.
- **`AnimationProductionMethodEnum`** (`$defs`) — 7 production-method identifiers derived from the animation artifact taxonomy in `claude-animation-taxonomy-v1.0.md` (field G). Values: `optical`, `drawn_2d`, `rendered_3d`, `physical_manipulation`, `direct_on_medium`, `screen_capture`, `hybrid`.
- **`AnimationPlaybackModalityEnum`** (`$defs`) — 4 playback-modality identifiers derived from `claude-animation-taxonomy-v1.0.md` (field β). Values: `fixed`, `interactive`, `generative`, `live_rendered`.
- **`GlobalSpecs.video_style`** — new optional `array` field referencing `VideoStyleEnum`. Declares the primary video style(s) of the project.
- **`CinematicSpec.animation_method`** — new optional field referencing `AnimationProductionMethodEnum`. Relevant when the shot or asset involves animation.
- **`CinematicSpec.animation_playback_modality`** — new optional field referencing `AnimationPlaybackModalityEnum`.

#### New files
- **`example-project.json`** — fully valid instance document conforming to `video-project-schema-v2.json`. Documents a 90-second sci-fi short film ("The Last Signal") with:
  - 3 acts / 3 scenes / 9 shots
  - Temporal bridge `anchor_frame_ref` chains across Acts 2 and 3
  - Character `face_id` consistency anchors on all close-ups
  - 4 audio assets (ambient, dialogue × 2, score) with sync metadata
  - Full render pipeline (load → overlay_audio → color_grade → encode)
  - Dependency graph (6 edges: `references`, `conditions_on`, `requires`)
  - Platform delivery (YouTube), localization (PT-BR), accessibility (WCAG AA)
- **`validate.py`** — CLI validator using `jsonschema` Draft 2020-12:
  - Accepts any instance path as a positional argument
  - `--schema` flag to override the default schema path
  - `--verbose` / `-v` flag: shows schema path for each error and an instance summary on success
  - Exits `0` on pass, `1` on failure (suitable for CI)

#### Previously untracked files (now committed)
- `chatgpt-generative_video_project_package.schema.json` — ChatGPT v1 draft schema (package-oriented, 21 KB)
- `chatgpt-schema-guide.md` — ChatGPT design rationale (Draft 2020-12 choice, four assembly layers)
- `prompt-create-skills.md` — design prompt: autonomous pipeline skill decomposition

### Changed

#### `README.md`
- Updated **Quick Start** section: added `example-project.json` and `validate.py`, added validator usage block.
- Updated **File Index**: added rows for all new files; updated v2 schema description to note taxonomy enums.
- Added **Design Principle #12** (Formal taxonomy enums) to the Key Design Principles table.
- Updated **Taxonomy Coverage** sections: video styles now show machine-readable slugs; animation taxonomy section notes `$defs` names and wired fields.
- Updated **architecture flow diagram** to include ChatGPT drafts, `example-project.json`, and `validate.py`.
- Updated **Next steps for session-03**: removed completed items (example instance, validation CLI).

---

## [2026-03-26] — Canonical v2 schema, formal taxonomies, and term map

### Added

- **`video-project-schema-v2.json`** (v2.0.0) — Canonical unified schema merging Grok, Claude, Manus, Perplexity, and ChatGPT drafts. Key additions over v1 drafts:
  - `GenerationCost`, `GenerationAttempt[]` for full cost audit
  - `RetryConfig`, `AsyncConfig` for resilient async orchestration
  - `Rights` on all assets (license type, expiry, talent release, territory)
  - `Team`, `Comment[]`, `ApprovalRecord[]` for collaborative review
  - `QaGate` on scenes and shots; `ValidationResult` on render pipeline
  - `PlatformDelivery[]`, `LocalizationConfig`, `AccessibilityConfig` on outputs
  - `PromptRecord[]` prompt history for A/B tracking
  - `DependencyEdge[]` explicit cross-asset dependency graph

- **`term-map.json`** (v1.0.0) — Machine-readable production vocabulary taxonomy. 10 terms across 4 axes (domain, vocabulary type, diegetic status, pipeline stage). Corrects 5 common misuses.
- **`claude-corrected_term_map.html`** (v1.0) — Interactive HTML visualization of the term map.
- **`claude-20-styles-video-v1.1.md`** (v1.1) — Formal biconditional predicate definitions for 20 video styles using possible-worlds semantics (capture modality κ, production intent π, distribution context δ).
- **`claude-20-styles-camera-v1.0.md`** (v1.0) — Formal 3D coordinate system and paraxial optics definitions for camera angles, movements, and optical effects.
- **`claude-20-styles-scene-v1.0.md`** (v1.0) — Scene ontology (Genette-based): diegetic location/time, ontological status, editing grammar, shot-scale taxonomy.
- **`claude-animation-taxonomy-v1.0.md`** (v1.0) — Animation artifact classification using formal tuple A = (F, T, μ, s, ι, χ, β, δ).
- **`perplexity-youtube_styles_research.xlsx`** — Empirical YouTube style dataset informing taxonomy decisions.

### Schema drafts (v1 inputs, preserved for provenance)
- `grok-video-schema.json` (v1.0 + patch)
- `claude-video-production-schema-v1.0.json` (v1.0)
- `manus-video_orchestration_schema_complete.md` (v1.0)
- `perplexity-VideoProject JSON Schema…md` (v1.0)
- `prompt-video-schema.md` — original requirements brief

---

## [2026-03-26] — v3 schema merge, skills report, and ChatGPT draft integration

### Added

- **`claude-unified-video-project-v3.schema.json`** (v3.0.0) — Merges `video-project-schema-v2.json` with `chatgpt-generative_video_project_package.schema.json`. Resolves 14 identified review defects. Supercedes v2 as the most complete schema version.
- **`claude-unified-schema.md`** — Merge review document: lists each defect, its source (v2 or ChatGPT draft), and its resolution in v3.
- **`claude-SKILLs-report.md`** — Full skill decomposition report answering `prompt-create-skills.md`. Derives the required agent skills from the v2 entity graph with formal SRP criterion. Result: 23 MUST-have skills, 8 SHOULD-have skills; 23/23 · 8/8 checks passed.
- **`chatgpt-generative_video_project_package.schema.json`** — ChatGPT v1 draft schema (package-oriented, 21 KB). Added as v1 input.
- **`chatgpt-schema-guide.md`** — ChatGPT design rationale document.
- **`prompt-create-skills.md`** — Design prompt for autonomous pipeline skill decomposition.
