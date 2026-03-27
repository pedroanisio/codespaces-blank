---
name: post-production
description: >
  Apply post-production operations to the timeline — color grading (LUT application),
  compositing (overlays), filtering (OpenCV frame-level), speed ramping (retime).
  Creates typed Operation entries (ColorGradeOp, OverlayOp, FilterOp, RetimeOp)
  on timelines and render plans. Use when the assembled timeline needs visual
  treatment. Trigger on "color grade", "apply post-production", "add VFX",
  "composite", "apply LUT", "speed ramp". Trigger after S17 (Timeline Assembler).
---

# Post-Production Processor (S18)

## Purpose

Apply visual post-production operations to the assembled timeline using the
schema's discriminated Operation types.

## Schema Surface

### Writes (primary owner)
- Operations added to `assembly.timelines[].operations[]` and/or render plans:
  - `ColorGradeOp`: LUT refs, intent, strength
  - `OverlayOp`: Foreground/background compositing, transforms, masks
  - `FilterOp`: Frame-level filters (denoise, sharpen, stabilize)
  - `RetimeOp`: Speed changes, reverse, frame interpolation
- `assetLibrary.genericAssets[]`: LUT files, masks, overlay elements

### Reads
- `assembly.timelines[]` (the assembled edit)
- `canonicalDocuments.directorInstructions` (colorDirection, vfxNotes)
- `production.shots[]` (vfxNotes, assemblyHints.speedPercent)
- `qualityProfiles[].video.qualityControls` (color grading intent, denoise, sharpen, stabilization)

## Preconditions

- S17 has completed: a timeline exists

## Procedure

### Step 1: Color grading

Create `ColorGradeOp` for the timeline:
- Select or generate LUT based on `directorInstructions.colorDirection`
- Set grading `intent` and `strength`
- Store LUT as `GenericAssetEntity` in asset library

### Step 2: Compositing

For shots requiring overlays (title cards, on-screen text, VFX elements):
- Create `OverlayOp` with foreground/background refs, transforms, time ranges

### Step 3: Filtering

Apply quality-control filters:
- `FilterOp` for denoise (level from quality profile)
- `FilterOp` for sharpen (level from quality profile)
- `FilterOp` for stabilization (max crop from quality profile)

### Step 4: Retiming

For shots with speed changes:
- Create `RetimeOp` with speed percent, frame interpolation method

### Step 5: Set compatible runtimes

Each operation specifies `compatibleRuntimes[]`: moviepy, movis, opencv, pyav, ffmpeg.

## Output Contract

- ≥1 `ColorGradeOp` for the overall grade
- Filter operations for quality-control processing
- All operations have `compatibleRuntimes[]` specified
- Operations reference valid input/output entities

## Downstream Dependencies

After S18: S20 (Render Plan Builder)
