---
name: shot-video-gen
description: >
  Generate video clips for every shot in the production using reference assets,
  consistency anchors, cinematic specs, and assembled prompts. Creates VisualAssetEntity
  entries with modality=video and full GenerationManifest audit trails. This is the
  most computationally expensive skill — manages temporal bridge patterns, adapter
  inputs (LoRA, ControlNet, IP-Adapter), retry/async configs, and cost tracking.
  Use when the pipeline needs shot videos generated. Trigger on "generate the videos",
  "create shot clips", "render the shots", "produce the video clips". Trigger after
  S13 (Reference Assets) and S15 (Prompt Composer).
---

# Shot Video Generator (S14)

## Purpose

Generate a video clip for every shot in the production, enforcing visual consistency
through reference assets, consistency anchors, and temporal bridge patterns.

## Schema Surface

### Writes (primary owner)
- `assetLibrary.visualAssets[]` → `VisualAssetEntity[]` where `modality: "video"`:
  - `visualType`: "shot_clip"
  - `shotRefs[]`, `sceneRefs[]`, `characterRefs[]`, `environmentRefs[]`
  - `spec` → `VisualAssetSpec`
  - `generation` → `GenerationManifest`:
    - `mode`: "ai_generated"
    - `steps[]` → `GenerationStep[]`:
      - Full prompt + negative prompt (from S15)
      - `seed`, `guidanceScale`, `inferenceSteps`, `sampler`, `scheduler`
      - `strength`, `cfg`, `durationSec`
      - `resolution`, `aspectRatio`, `frameRate`
      - `referenceAssets[]` → `ReferenceInput[]` (from S13)
      - `consistencyAnchors[]` → `ConsistencyAnchor[]`
      - `adapterInputs[]` → `AdapterInput[]` (LoRA, ControlNet, IP-Adapter)
      - `cameraMotionHints`: From cinematicSpec
      - `costEstimate`, `costActual` → `GenerationCost`
      - `retryConfig` → `RetryConfig`
      - `asyncConfig` → `AsyncConfig`
      - `promptHistory[]` → `PromptRecord[]` (full audit trail)
      - `status`, `metrics`, `logs[]`
    - `reproducibility`: determinism declarations

### Reads
- `production.shots[]` (cinematicSpec, genParams, target duration)
- `assetLibrary.visualAssets[]` where `isCanonicalReference: true` (from S13)
- `production.characters[]`, `environments[]`, `props[]` (for consistency anchors)
- `canonicalDocuments.directorInstructions` (visual constraints)
- `qualityProfiles[]` (resolution, frame rate, temporal consistency thresholds)

## Preconditions

- S13 has completed: reference assets exist
- S15 has provided assembled prompts
- S08 has completed: shots have cinematicSpec

## Procedure

### Step 1: Order shots for generation

Sort shots to respect temporal bridge pattern:
- Generate shots in scene order, first shot to last
- Each subsequent shot uses the last frame of the previous shot as anchor

### Step 2: Assemble generation parameters per shot

For each shot, build a `GenerationStep`:
- **Prompt**: From S15 (assembled from entity fragments + director style)
- **Reference assets**: Character ref images with appropriate weights
- **Consistency anchors**: Hard anchors from S13, plus soft anchors from preceding shots
- **Adapter inputs**: LoRA for style, ControlNet for pose/depth, IP-Adapter for face
- **Camera motion hints**: Translated from `cinematicSpec.cameraMovement`
- **Duration**: From `shot.targetDurationSec`
- **Resolution/FPS**: From quality profile

### Step 3: Configure retry and async

```
retryConfig: {
  maxAttempts: 3,
  backoffStrategy: "exponential",
  initialDelayMs: 2000,
  fallbackTool: "alternative-video-model"
}
asyncConfig: {
  mode: "polling",
  pollingIntervalMs: 5000,
  timeoutMs: 300000
}
```

### Step 4: Execute generation

- Record `costEstimate` before generation
- Execute with full logging
- Record `costActual` after generation
- Store seed and all parameters for reproducibility
- Save prompt to `promptHistory[]`

### Step 5: Apply temporal bridge

After each shot generates:
- Extract last frame
- Store as `temporalBridgeAnchorRef` for the next shot
- S16 validates consistency before proceeding

### Step 6: Quality check

Invoke S16 (Consistency Enforcer) and S21 (QA Validator) on each generated clip.
If quality gates fail, adjust prompts/parameters and retry.

## Output Contract

- One video `VisualAssetEntity` per shot
- Each has complete `GenerationManifest` with reproducibility info
- All videos meet quality profile resolution and frame rate
- Temporal bridge pattern is applied (each shot conditioned on predecessor)
- Cost tracking is complete (estimate + actual)
- `promptHistory[]` preserves full prompt evolution

## Iteration Rules

This skill has the tightest iteration loop in the pipeline:
- S16 failure → adjust anchors/weights → regenerate
- S21 failure → adjust quality parameters → regenerate
- Director feedback → adjust prompts → regenerate
- Budget exhaustion → reduce quality settings or shot count

## Downstream Dependencies

After S14: S17 (Timeline Assembler), S16 (Consistency loop)
