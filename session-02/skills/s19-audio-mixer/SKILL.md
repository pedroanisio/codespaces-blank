---
name: audio-mixer
description: >
  Mix all audio tracks to target loudness and dynamics — creates AudioMixOp
  operations with per-track gain, pan, time ranges, and sync points. Manages
  final mix to LUFS targets, true peak limits, and dialog intelligibility.
  Use when audio tracks need to be balanced and mixed. Trigger on "mix the audio",
  "balance the tracks", "master the audio", "set loudness levels".
  Trigger after S17 (Timeline Assembler) and audio skills (S10-S12).
---

# Audio Mixer (S19)

## Purpose

Create `AudioMixOp` operations that balance all audio tracks (dialogue, music,
SFX, ambient) to meet loudness standards and dialog intelligibility targets.

## Schema Surface

### Writes (primary owner)
- `AudioMixOp` operations added to timeline/render plan:
  - `tracks[]` → `AudioMixTrack[]`:
    - `audioRef`: Points to audio asset
    - `gainDb`: Per-track gain adjustment
    - `pan`: Stereo positioning (-1 to 1)
    - `timeRange`: When this track is active
    - `syncPoints[]`: Beat-locked alignment points

### Reads
- `assetLibrary.audioAssets[]` (all audio tracks)
- `assembly.timelines[]` (clip placement and timing)
- `qualityProfiles[].audio` (loudness targets, true peak, dialog intelligibility)
- `canonicalDocuments.directorInstructions` (music direction, sonic priorities)

## Preconditions

- S17 has completed: audio clips are placed on the timeline
- Audio assets exist from S10, S11, S12

## Procedure

### Step 1: Set mix hierarchy

Priority order (highest to lowest gain):
1. Dialogue / Voice-over
2. Sound effects / Foley
3. Music
4. Ambient

### Step 2: Set per-track levels

Based on `qualityProfiles[].audio`:
- Target integrated loudness: `loudnessIntegratedLUFS` (e.g., -14 LUFS for YouTube)
- True peak ceiling: `truePeakDbTP` (e.g., -1.0 dBTP)
- Dialogue target: -6 to -12 dB relative to full scale
- Music bed: -18 to -24 dB (ducked under dialogue)
- SFX: -12 to -18 dB (punchy but not overwhelming)
- Ambient: -24 to -30 dB (subtle presence)

### Step 3: Create AudioMixOp

```
{
  opType: "audioMix",
  tracks: [
    { audioRef: dialogue-ref, gainDb: -8, pan: 0, timeRange: {startSec: 0, endSec: ...} },
    { audioRef: music-ref, gainDb: -20, pan: 0, syncPoints: [...] },
    { audioRef: sfx-ref, gainDb: -14, pan: 0.3, timeRange: {...} },
    { audioRef: ambient-ref, gainDb: -26, pan: 0, timeRange: {...} }
  ]
}
```

### Step 4: Dynamic mixing

Apply ducking: reduce music gain during dialogue segments.
Apply swells: increase music gain during non-dialogue dramatic moments.

### Step 5: Validate against standards

Check that the final mix meets:
- Integrated loudness target (±1 LUFS)
- True peak ≤ ceiling
- Dialog intelligibility ≥ minimum score

## Output Contract

- One `AudioMixOp` per timeline
- All audio assets are represented in the mix
- Gain values produce a mix within loudness targets
- Dialogue is always intelligible above other layers

## Downstream Dependencies

After S19: S20 (Render Plan Builder)
