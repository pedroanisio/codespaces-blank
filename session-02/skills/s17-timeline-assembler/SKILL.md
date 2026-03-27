---
name: timeline-assembler
description: >
  Assemble generated video and audio assets into timelines — place clips at correct
  positions with layer ordering, sync points, transitions, and stream bindings.
  Creates TimelineEntity and EditVersionEntity (layers 1-2 of the 4-layer assembly
  model). Use when generated assets need to be organized into a playable sequence.
  Trigger on "assemble the timeline", "build the edit", "sequence the clips",
  "create the timeline". Trigger after S14 has generated video clips and audio
  skills (S10-S12) have produced audio assets.
---

# Timeline Assembler (S17)

## Purpose

Create `TimelineEntity` and `EditVersionEntity` entries by placing all generated
video and audio clips onto tracks with correct timing, synchronization, and layering.

## Schema Surface

### Writes (primary owner)
- `assembly.timelines[]` → `TimelineEntity[]`:
  - `durationSec`, `frameRate`, `resolution`, `aspectRatio`
  - `videoClips[]` → `TimelineClip[]` (clipId, sourceRef, sourceIn/Out, timelineStart, duration, layerOrder, transform, syncPoints, transitions, assemblyHints)
  - `audioClips[]` → `TimelineClip[]` (dialogue, music, SFX on separate layers)
  - `subtitleClips[]` → `TimelineClip[]` (if applicable)
  - `streamBindings[]` → `StreamBinding[]` (codec-level detail)
  - `operations[]` → initial `Operation[]` (concat ops for shot sequences)
- `assembly.editVersions[]` → `EditVersionEntity[]`:
  - `timelineRef`: Points to the timeline
  - `changeList[]`: Description of edit decisions
  - `approvedForRender`: false (pending review)

### Reads
- `production.scenes[]` (shot ordering, transitions, planned positions)
- `production.shots[]` (assembly hints, target durations)
- `assetLibrary.visualAssets[]` where `modality: "video"` (generated clips)
- `assetLibrary.audioAssets[]` (all audio — dialogue, music, SFX, ambient)
- `canonicalDocuments.script` (for subtitle generation timing)
- `qualityProfiles[]` (resolution, frame rate, aspect ratio)

## Preconditions

- S14 has completed: video assets exist for all shots
- S10, S11, S12 have completed: audio assets exist
- S09 has completed: scenes define shot ordering

## Procedure

### Step 1: Create timeline structure

```
timeline: {
  id: "timeline-main-v1.0.0",
  entityType: "timeline",
  durationSec: project.targetRuntimeSec,
  frameRate: qualityProfile.video.frameRate,
  resolution: qualityProfile.video.resolution,
  aspectRatio: qualityProfile.video.aspectRatio
}
```

### Step 2: Place video clips

For each scene (in order), for each shot (in order):
- Find the corresponding video `VisualAssetEntity`
- Create a `TimelineClip`:
  ```
  {
    clipId: "vclip-{scene}-{shot}",
    sourceRef: { id: video-asset-id },
    timelineStartSec: cumulative position,
    durationSec: shot.targetDurationSec,
    layerOrder: 0  // base video layer
  }
  ```
- Apply transitions from `shot.assemblyHints` or `scene.transitionIn/Out`

### Step 3: Place audio clips

Layer audio on separate tracks:
- **Layer 1**: Dialogue/VO — sync to script segment timing
- **Layer 2**: Music — align sync points to scene boundaries
- **Layer 3**: SFX/Foley — sync to shot events
- **Layer 4**: Ambient — continuous per-scene fills

Use `syncPoints[]` to lock audio to visual events.

### Step 4: Place subtitle clips (if applicable)

From script dialogue segments, create subtitle clips:
- Time to speech audio duration
- Position on subtitle track

### Step 5: Create concat operations

For sequential shots within scenes:
```
{ opType: "concat", clipRefs: [shot-1-ref, shot-2-ref, ...], method: "chain" }
```

### Step 6: Create edit version

```
editVersion: {
  id: "edit-v1.0.0",
  entityType: "editVersion",
  timelineRef: { id: timeline-id },
  changeList: ["Initial assembly from generated assets"],
  approvedForRender: false
}
```

### Step 7: Set stream bindings

Bind video and audio streams with codec-level detail for downstream rendering.

## Output Contract

- One `TimelineEntity` with all clips placed
- Video clips cover the full runtime with no gaps
- Audio clips are layered correctly (dialogue > music > SFX > ambient)
- Sync points align audio to visual events
- One `EditVersionEntity` references the timeline
- Timeline `durationSec` ≈ `project.targetRuntimeSec`

## Downstream Dependencies

After S17: S18 (Post-Production), S19 (Audio Mixer), S20 (Render Plan Builder)
