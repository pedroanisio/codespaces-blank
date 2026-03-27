---
name: music-composer
description: >
  Compose music and score for video production — background music, stems, sync points,
  technical specs (sample rate, loudness, codec). Creates AudioAssetEntity entries of
  type music/stem. Use when the production needs a musical score. Trigger on "compose
  the music", "create the score", "make background music", "design the soundtrack".
  Trigger after S07 (Director) has set music direction.
---

# Music Composer (S10)

## Purpose

Create `AudioAssetEntity` entries for the production's musical score — background music,
individual stems, and musical cues with beat-locked sync points.

## Schema Surface

### Writes (primary owner)
- `assetLibrary.audioAssets[]` → `AudioAssetEntity[]` where `audioType ∈ {music, stem}`:
  - `purpose`, `mood`, `lyrics` (if applicable)
  - `sceneRefs[]`, `shotRefs[]`
  - `syncPoints[]` → `SyncPoint[]` (label, time, beat position, tolerance)
  - `technicalSpec` → `AudioTechnicalSpec`
  - `generation` → `GenerationManifest` (if AI-generated)

### Reads
- `canonicalDocuments.story` (themes, tone)
- `canonicalDocuments.directorInstructions` (musicDirection)
- `production.scenes[]` (mood, timing, planned positions)
- `qualityProfiles[]` (audio quality targets)

## Preconditions

- S07 has completed: `directorInstructions.musicDirection` exists
- S09 has completed or scenes have timing information

## Procedure

### Step 1: Plan musical structure

Map the director's music direction to scene moods:
- Identify scenes requiring distinct musical themes
- Plan transitions between musical sections
- Identify sync points (beat drops, musical accents aligned to visual events)

### Step 2: Create music assets

For each musical cue/track:
- `audioType`: "music" for full mixes, "stem" for individual layers
- `mood`: Emotional descriptor matching scene mood
- `syncPoints[]`: Key moments where music must align with visuals
  - Include `beat` field for beat-locked editing
  - Set `toleranceFrames` (typically 2-4 frames)

### Step 3: Set technical specs

```
technicalSpec: {
  sampleRateHz: from qualityProfile.audio.sampleRateHz (default 48000),
  bitDepth: from qualityProfile.audio.bitDepth (default 24),
  channelLayout: "stereo",
  loudnessIntegratedLUFS: -18 (music sits below dialogue),
  codec: "aac" or "flac"
}
```

### Step 4: Configure generation manifest

If AI-generated, populate `generation`:
```
generation: {
  mode: "ai_generated",
  steps: [{ stepId: "music-gen-001", operationType: "music_generation", ... }]
}
```

## Output Contract

- ≥1 music AudioAssetEntity per distinct musical section
- Each has `mood`, `syncPoints[]` (≥1), and `technicalSpec`
- Sync point times align with scene planned positions
- Loudness target is set below dialogue level

## Downstream Dependencies

After S10: S19 (Audio Mixer), S17 (Timeline Assembler)
