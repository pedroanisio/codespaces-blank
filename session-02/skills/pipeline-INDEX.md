---
title: "Video Production Pipeline — Master Skill Index"
version: "1.0.0"
schema_reference: "unified-video-project-v3.schema.json (v3.0.0)"
date: "2026-03-27"
disclaimer: >
  No information within this document should be taken for granted.
  Any statement or premise not backed by a real logical definition
  or verifiable reference may be invalid, erroneous, or a hallucination.
---

# Video Production Pipeline — Master Skill Index

## Overview

24 modular skills that autonomously transform a single creative idea into a
fully populated `unified-video-project-v3` schema instance consumable by a
downstream renderer.

## Directory Structure

```
skills/
├── schema.json                          ← shared schema (symlinked into each skill)
├── pipeline-skill-decomposition.md      ← full decomposition analysis
│
├── s01-concept-seed/SKILL.md            ← Tier 1: Creative Foundation
├── s02-story-architect/SKILL.md
├── s03-scriptwriter/SKILL.md
│
├── s04-character-designer/SKILL.md      ← Tier 2: World Building
├── s05-environment-designer/SKILL.md
├── s06-prop-designer/SKILL.md
│
├── s07-director/SKILL.md                ← Tier 3: Direction
├── s08-cinematographer/SKILL.md
│
├── s09-scene-composer/SKILL.md          ← Tier 4: Scene Composition
│
├── s10-music-composer/SKILL.md          ← Tier 5: Audio Production
├── s11-sound-designer/SKILL.md
├── s12-voice-producer/SKILL.md
│
├── s13-reference-asset-gen/SKILL.md     ← Tier 6: Visual Generation
├── s14-shot-video-gen/SKILL.md
│
├── s15-prompt-composer/SKILL.md         ← Cross-cutting: Prompt & Consistency
├── s16-consistency-enforcer/SKILL.md
│
├── s17-timeline-assembler/SKILL.md      ← Tier 8: Assembly & Post-production
├── s18-post-production/SKILL.md
├── s19-audio-mixer/SKILL.md
├── s20-render-plan-builder/SKILL.md
│
├── s21-qa-validator/SKILL.md            ← Tier 9: Quality Assurance
│
├── s22-deliverable-packager/SKILL.md    ← Tier 10: Packaging & Delivery
├── s23-marketing-asset-gen/SKILL.md
│
└── s24-pipeline-orchestrator/SKILL.md   ← Meta: Orchestration
```

## Execution Order (Topological)

```
Phase 1 — Sequential foundation:
  S01 (Concept Seed) → S02 (Story Architect) → S03 (Scriptwriter)

Phase 2 — Parallel world building:
  S04 (Character) ∥ S05 (Environment) ∥ S06 (Props)
  All depend on S03.

Phase 3 — Direction:
  S07 (Director) — depends on S03, benefits from S04-S06
  S08 (Cinematographer) — depends on S07

Phase 4 — Scene composition + Audio (parallel):
  S09 (Scene Composer) — depends on S08
  S10 (Music) ∥ S11 (Sound Design) — depend on S07
  S12 (Voice/Dialogue) — depends on S03 + S04

Phase 5 — Visual generation:
  S13 (Reference Assets) — depends on S04-S07
  S15 (Prompt Composer) — cross-cutting, feeds S13 + S14
  S14 (Shot Video Gen) — depends on S13
  S16 (Consistency Enforcer) — loops with S14

Phase 6 — Assembly:
  S17 (Timeline) — depends on S14, S10-S12
  S18 (Post-Production) ∥ S19 (Audio Mixer) — depend on S17
  S20 (Render Plan) — depends on S18 + S19

Phase 7 — Quality + Delivery:
  S21 (QA Validator) — depends on S20
  S22 (Deliverable Packager) — depends on S21
  S23 (Marketing Assets) — depends on S02, can run partially parallel

Phase ∞ — Meta:
  S24 (Pipeline Orchestrator) — manages all phases
```

## Schema Coverage Matrix

| Schema Property                        | Writing Skill(s)          |
|----------------------------------------|---------------------------|
| `schemaVersion`                        | S24                       |
| `package`                              | S01 + S24                 |
| `project`                              | S01                       |
| `qualityProfiles[]`                    | S01 + S24                 |
| `team`                                 | S24                       |
| `canonicalDocuments.story`             | S01 (stub) + S02 (full)   |
| `canonicalDocuments.script`            | S03                       |
| `canonicalDocuments.directorInstructions` | S07                    |
| `production.characters[]`              | S04                       |
| `production.environments[]`            | S05                       |
| `production.props[]`                   | S06                       |
| `production.scenes[]`                  | S09                       |
| `production.shots[]`                   | S08                       |
| `assetLibrary.visualAssets[]`          | S13 + S14                 |
| `assetLibrary.audioAssets[]`           | S10 + S11 + S12           |
| `assetLibrary.marketingAssets[]`       | S23                       |
| `assetLibrary.genericAssets[]`         | S18 (LUTs) + S24          |
| `orchestration`                        | S24                       |
| `assembly.timelines[]`                 | S17                       |
| `assembly.editVersions[]`             | S17                       |
| `assembly.renderPlans[]`              | S20                       |
| `deliverables[]`                       | S22                       |
| `relationships[]`                      | S24                       |
| `dependencies[]`                       | S24                       |

## Skill Interface Contract

Every skill:

1. **Receives**: Schema instance reference + orchestrator execution context
2. **Validates preconditions**: Required upstream entities exist in acceptable state
3. **Produces**: New/updated entities with VersionInfo, GenerationManifest (if generative), timestamps, EntityRef links
4. **Reports**: Status, cost, QA results, entities created/modified
5. **Idempotency**: Same inputs + version selectors → deterministic output (or declares non-deterministic)

## Cross-cutting Patterns

| Pattern                  | Handling Skill |
|--------------------------|----------------|
| Prompt fragment assembly | S15            |
| Generation audit trail   | S13, S14, S15  |
| Consistency enforcement  | S16            |
| Quality gating           | S21            |
| Version management       | S24            |
| Approval workflows       | S24            |
| Cost tracking            | S24            |
| Rights / compliance      | S24            |

## Critical Path

The longest sequential dependency chain determines minimum pipeline duration:

```
S01 → S02 → S03 → S04 → S07 → S08 → S09 → S13 → S14 → S17 → S18 → S20 → S21 → S22
 │                                                   │
 14 sequential steps                          (S16 loop adds iterations)
```

## Parallelizable Groups

| After            | Can run in parallel          |
|------------------|------------------------------|
| S03 completes    | S04 ∥ S05 ∥ S06              |
| S07 completes    | S10 ∥ S11 ∥ S08 ∥ S13        |
| S03 + S04        | S12 (parallel with Tier 3+)  |
| S17 completes    | S18 ∥ S19                    |
| S02 completes    | S23 (independent side-chain) |
