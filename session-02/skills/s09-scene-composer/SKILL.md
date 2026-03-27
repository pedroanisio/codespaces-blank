---
name: scene-composer
description: >
  Compose scenes by organizing shots into coherent dramatic units — assigns scene
  numbers, shot ordering, character/environment/prop refs, mood, time of day, weather,
  transitions, QA gate configuration, and target durations. Use when shots exist and
  need to be organized into scenes. Trigger on "compose the scenes", "organize shots
  into scenes", "build scene structure". Trigger after S08 (Cinematographer).
---

# Scene Composer (S09)

## Purpose

Create `SceneEntity` entries that organize shots into dramatic units with
continuity, transitions, and quality gates.

## Schema Surface

### Writes (primary owner)
- `production.scenes[]` → `SceneEntity[]`:
  - `sceneNumber`, `synopsis`, `storyBeatRefs[]`, `scriptSegmentRefs[]`
  - `directorNoteRefs[]`, `characterRefs[]`, `environmentRef`, `propRefs[]`
  - `timeOfDay`, `weather`, `mood`, `targetDurationSec`
  - `plannedPosition` → `TimeRange`
  - `shotRefs[]` (ordered), `transitionIn`, `transitionOut`
  - `qaGate` → `QaGate` (required checks, pass threshold)
- `production.shots[].qaGate` → `QaGate` (shot-level quality gates, one per shot)

### Reads
- `production.shots[]` (from S08)
- `canonicalDocuments.story` (beats)
- `canonicalDocuments.script` (scene headings, segments)
- `canonicalDocuments.directorInstructions` (quality rules, targeted notes)
- `production.characters[]`, `production.environments[]`, `production.props[]`

## Preconditions

- S08 has completed: `production.shots[]` is populated

## Procedure

### Step 1: Map shots to scenes

Group shots by their `sceneRef`. Order shots within each scene by `shotNumber`.

### Step 2: Populate scene metadata

For each scene, extract from script scene_heading segments:
- `timeOfDay`, `weather` (from heading or environment defaults)
- `mood` (from beat's emotionalObjective)
- `synopsis` (from script action descriptions)
- All character/environment/prop refs present in the scene's shots

### Step 3: Set transitions

Apply director's editing language:
- Between scenes: dissolve, fade, cut, or as specified in targeted notes
- Opening scene: fade from black
- Closing scene: fade to black

### Step 4: Configure QA gates

For each **scene**, set `qaGate`:
```
qaGate: {
  requiredChecks: ["temporal_consistency", "character_coherence", "audio_sync"],
  passThreshold: 0.8
}
```

For each **shot** within the scene, also set `qaGate` using the director's quality rules:
```
qaGate: {
  requiredChecks: ["temporal_consistency", "character_coherence", "duration_compliance", "resolution_compliance"],
  passThreshold: 0.8
}
```

Include any additional checks from `directorInstructions.qualityRules[]` in both scene and shot gates.

### Step 5: Calculate planned positions

Sequence scenes and compute cumulative `plannedPosition` TimeRanges.

## Output Contract

- One `SceneEntity` per distinct scene in the script
- `shotRefs[]` are ordered and reference existing shots
- Every scene has `qaGate` configured with ≥2 required checks
- Every shot within each scene has `qaGate` configured with ≥2 required checks
- Scene durations sum to ≈ `project.targetRuntimeSec`
- Every scene has `environmentRef` and ≥1 `characterRef`

## Downstream Dependencies

After S09: S17 (Timeline Assembler)
