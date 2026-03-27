---
name: render-plan-builder
description: >
  Build render plans from timelines — ordered operation sequences with compatible
  runtimes (moviepy/movis/opencv/pyav/manim/ffmpeg), color pipeline config, and
  runtime hints. Layer 3 of the 4-layer assembly model. Use when a timeline needs
  to be converted into an executable render specification. Trigger on "build render
  plan", "prepare for rendering", "create render spec". Trigger after S18 and S19.
---

# Render Plan Builder (S20)

## Purpose

Translate an edit (timeline + post-production operations + audio mix) into an
executable, runtime-specific render plan.

## Schema Surface

### Writes (primary owner)
- `assembly.renderPlans[]` → `RenderPlanEntity[]`:
  - `sourceTimelineRef`: Points to the timeline
  - `targetOutputRefs[]`: Points to planned deliverables
  - `compatibleRuntimes[]`: moviepy|movis|opencv|pyav|manim|ffmpeg|custom
  - `operations[]` → ordered `Operation[]` (typed, discriminated)
  - `colorPipeline`: Color management config
  - `runtimeHints`: Executor-specific parameters

### Reads
- `assembly.timelines[]` (clips, operations, stream bindings)
- `assembly.editVersions[]` (must be approvedForRender)
- Operations from S18 (post-production) and S19 (audio mix)
- `qualityProfiles[]` (target specs for final output)
- `project` (target runtime, quality requirements)

## Preconditions

- S17, S18, S19 have completed
- An `EditVersionEntity` exists

## Procedure

### Step 1: Collect all operations

Gather operations from:
- Timeline (concat ops from S17)
- Post-production (color grade, filter, overlay, retime from S18)
- Audio mix (audio mix ops from S19)

### Step 2: Order operations

Sort into execution order:
1. Source preparation (decode, retime)
2. Visual processing (filter, stabilize, denoise)
3. Compositing (overlay, titles)
4. Color grading (LUT application)
5. Audio mixing
6. Concatenation (final assembly)
7. Encoding (final output format)

### Step 3: Select compatible runtimes

For each operation, check `compatibleRuntimes[]`:
- `ConcatOp` → moviepy, movis, ffmpeg
- `ColorGradeOp` → opencv, ffmpeg
- `AudioMixOp` → moviepy, ffmpeg
- `FilterOp` → opencv
- `ManimOp` → manim only
- `EncodeOp` → pyav, ffmpeg

Find the intersection of runtimes that can handle all operations.
Prefer `ffmpeg` as universal fallback.

### Step 4: Add encode operation

Create `EncodeOp` for final output:
```
{
  opType: "encode",
  inputRef: last-operation-output,
  compression: {
    codec: "h264" or "h265",
    profile: "high",
    bitrateMbps: from quality profile
  },
  targetQualityProfileRef: quality-profile-ref
}
```

### Step 5: Set runtime hints

Provider-specific configuration:
```
runtimeHints: {
  preferredRuntime: "ffmpeg",
  threads: 4,
  gpuAcceleration: true,
  tempDir: "/tmp/render"
}
```

## Output Contract

- One `RenderPlanEntity` per target output format
- `operations[]` are ordered for correct execution
- `compatibleRuntimes[]` is non-empty (at least one runtime can execute all ops)
- Final operation is an `EncodeOp`
- `sourceTimelineRef` points to a valid timeline

## Downstream Dependencies

After S20: S21 (QA Validator), S22 (Deliverable Packager)
