---
name: concept-seed
description: >
  Initialize a video production project from a raw creative idea. Creates the
  ProjectEntity, initial QualityProfileEntity, PackageInfo, and a StoryEntity stub
  (logline, premise, themes, tone). Use this skill whenever the user provides a
  creative idea, concept, brief, or pitch and wants to start a new autonomous video
  production pipeline. Also trigger when the user says "start a new video project",
  "initialize production", "seed the pipeline", "kick off a video from this idea",
  or any variation of turning a concept into the first structured schema entities.
  This is always the first skill in the pipeline — nothing else runs before it.
---

# Concept Seed Developer (S01)

## Purpose

Transform a raw creative idea (free text) into the foundational schema entities
that constrain and enable every downstream skill. This is the pipeline's entry point.

## Schema Surface

### Writes (primary owner)
- `project` → `ProjectEntity` (summary, genres, audiences, languages, targetRuntimeSec, defaultQualityProfileRef, governance)
- `qualityProfiles[]` → at least one `QualityProfileEntity` with video + audio specs
- `package` → `PackageInfo` (packageId, versioningPolicy, governance, budget stub, compliance stub)
- `canonicalDocuments.story` → `StoryEntity` **stub only** (logline, premise, themes, tone — beats and arcs are S02's job)

### Reads
- Raw creative idea from user input
- Any user-provided constraints (platform, duration, audience, budget)

## Preconditions

- None. This is the root node of the pipeline DAG.

## Procedure

### Step 1: Parse the creative idea

Extract from the user's input:
- **Core concept**: What is this video about? (1-2 sentence logline)
- **Genre signals**: Drama, comedy, horror, educational, documentary, commercial, etc.
- **Audience signals**: Age range, sophistication, platform expectations
- **Duration signals**: Short-form (<60s), medium (1-5 min), long-form (5-30 min)
- **Style signals**: Live-action aesthetic, animated, motion graphics, mixed
- **Platform signals**: YouTube, Instagram, TikTok, broadcast, etc.

If ambiguous, make reasonable defaults and document assumptions in `project.description`.

### Step 2: Create the quality profile

Build a `QualityProfileEntity` with:

```
profile.video:
  resolution: infer from platform (1080p default, 4K for broadcast/theatrical)
  aspectRatio: infer from platform (16:9 default, 9:16 for TikTok/Reels)
  frameRate: { fps: 24 } for cinematic, { fps: 30 } for web content
  colorSpace: "sRGB" default
  dynamicRange: "SDR" default
  runtimeTargetSec: from duration signals
  runtimeToleranceSec: ±10% of target
  temporalConsistency: { required: true, minConsistencyScore: 0.85 }
  characterCoherence: { required: true, minSimilarityScore: 0.8 }

profile.audio:
  sampleRateHz: 44100 (48000 for broadcast)
  bitDepth: 16 (24 for broadcast)
  channelLayout: "stereo"
  loudnessIntegratedLUFS: -14 (YouTube), -16 (podcast), -24 (broadcast)
  truePeakDbTP: -1.0
```

### Step 3: Create the project entity

Build `ProjectEntity` with:
- `id`: Generate unique identifier (e.g., `proj-{slug}-{timestamp}`)
- `logicalId`: Same as id for v1
- `entityType`: "project"
- `name`: Derived from the idea
- `summary`: The user's idea, cleaned up
- `genres`: Array from genre signals
- `audiences`: Array from audience signals
- `languages`: Default `["en-US"]` unless specified
- `targetRuntimeSec`: From duration signals (hard max: 1800)
- `defaultQualityProfileRef`: Points to the quality profile created in Step 2
- `version`: `{ number: "1.0.0", state: "draft" }`

### Step 4: Create the story stub

Build `StoryEntity` with:
- `logline`: One-sentence hook
- `premise`: 2-3 sentence expansion of the concept
- `themes`: Array of thematic keywords
- `tone`: Array of tonal descriptors
- `beats`: Empty array (S02 populates this)
- `arcs`: Empty array (S02 populates this)
- `version`: `{ number: "0.1.0", state: "draft" }`

### Step 5: Create the package

Build `PackageInfo` with:
- `packageId`: Generate unique identifier
- `createdAt`: Current ISO timestamp
- `versioningPolicy`:
  - `immutablePublishedVersions`: true
  - `defaultReferenceMode`: "latestApproved"
  - `requireContentHashForPublished`: true
- `governance`: Default naming conventions (kebab-case, `-` separator)
- `budget`: Stub with currency and zero amounts
- `compliance`: Empty stubs

### Step 6: Initialize remaining required top-level arrays

Create empty arrays for all required top-level properties so the schema instance
is structurally valid from the start:
- `production`: `{ characters: [], environments: [], props: [], scenes: [], shots: [] }`
- `assetLibrary`: `{ visualAssets: [], audioAssets: [], marketingAssets: [], genericAssets: [] }`
- `orchestration`: `{ workflows: [] }`
- `assembly`: `{ timelines: [], editVersions: [], renderPlans: [] }`
- `deliverables`: `[]`
- `relationships`: `[]`

## Output Contract

- A structurally valid (but incomplete) schema instance
- All `required` top-level properties present
- At least one quality profile exists and is referenced by the project
- Story entity has logline, premise, themes, and tone populated
- All version states are `"draft"`

## Iteration Rules

This skill typically runs once. Re-run only if:
- The user fundamentally changes the creative concept
- Platform or audience constraints change (requiring new quality profile)
- Budget constraints are introduced that change runtime or quality targets

## Downstream Dependencies

After S01 completes, the following skills are unblocked:
- **S02** (Story Architect): Needs the story stub, project constraints
- **S07** (Director): Can start with project + story stub, but benefits from waiting for S02+S03
