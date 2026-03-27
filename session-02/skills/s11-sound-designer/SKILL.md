---
name: sound-designer
description: >
  Design sound effects, foley, and ambient audio for video production. Creates
  AudioAssetEntity entries of type sfx/foley/ambient. Use when the production
  needs sound effects and atmospheric audio. Trigger on "design the sound",
  "create sound effects", "add SFX", "design foley", "build the soundscape".
  Trigger after S07 (Director) and S08 (Cinematographer).
---

# Sound Designer (S11)

## Purpose

Create sound effects, foley, and ambient audio assets with precise sync points
for integration into the video timeline.

## Schema Surface

### Writes (primary owner)
- `assetLibrary.audioAssets[]` → `AudioAssetEntity[]` where `audioType ∈ {sfx, foley, ambient}`:
  - `purpose`, `mood`
  - `sceneRefs[]`, `shotRefs[]`
  - `syncPoints[]` → `SyncPoint[]`
  - `technicalSpec` → `AudioTechnicalSpec`
  - `generation` → `GenerationManifest`

### Reads
- `canonicalDocuments.script` (action descriptions — what happens physically)
- `production.shots[]` (what's visible — drives foley needs)
- `production.scenes[]` (mood, environment)
- `production.environments[]` (ambient sound context)
- `canonicalDocuments.directorInstructions` (sonic aesthetic)

## Preconditions

- S08 has completed: shots exist with action descriptions
- S07 has completed: directorial vision establishes sonic aesthetic

## Procedure

### Step 1: Analyze sound needs per shot

For each shot, identify:
- **SFX**: Discrete sound events (door slam, explosion, typing)
- **Foley**: Character-driven sounds (footsteps, clothing rustle, breathing)
- **Ambient**: Continuous environmental audio (traffic, wind, room tone)

### Step 2: Create audio assets

For each sound:
- Set `audioType` correctly (sfx vs foley vs ambient)
- Create precise `syncPoints[]` matching visual events in shots
- Set `technicalSpec` from quality profile audio controls

### Step 3: Layer plan

Document layering intent in `purpose` — how sounds combine:
- Room tone base layer
- Foley mid layer
- SFX accent layer

## Output Contract

- Every scene has ≥1 ambient audio asset
- Action sequences have corresponding SFX assets
- Dialogue scenes have foley assets for character presence
- All sync points reference valid shot/scene timing
- Technical specs match quality profile

## Downstream Dependencies

After S11: S19 (Audio Mixer), S17 (Timeline Assembler)
