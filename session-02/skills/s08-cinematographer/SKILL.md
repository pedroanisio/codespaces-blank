---
name: cinematographer
description: >
  Design every shot in the production — shot type, camera angle, camera movement,
  focal length, aperture, depth of field, sensor format, stabilization, framing,
  composition, lighting, and color palette. Populates ShotEntity with full
  CinematicSpec (the formal tuple Ξ). Use this skill when shots need to be designed
  from a script and directorial vision. Trigger on "design the shots", "plan the
  cinematography", "create shot list", "define camera work". Trigger after S07
  (Director) has established the vision.
---

# Cinematographer (S08)

## Purpose

Design every shot in the production with precise cinematic specifications,
implementing the director's camera language through concrete optical and framing
parameters.

## Schema Surface

### Writes (primary owner)
- `production.shots[]` → `ShotEntity[]`:
  - `shotNumber`, `purpose`, `description`, `targetDurationSec`
  - `sceneRef`, `characterRefs[]`, `environmentRef`, `propRefs[]`
  - `scriptSegmentRefs[]`, `audioCueRefs[]`
  - `cinematicSpec` → `CinematicSpec`:
    - `shotType`: XCU|CU|MCU|MS|MWS|WS|EWS|insert|POV|OTS|aerial|dutch
    - `cameraAngle`: eye_level|low|high|dutch|over_the_shoulder|bird_eye|worm_eye
    - `cameraMovement`: static|pan|tilt|dolly|crane|orbit|handheld|zoom|truck|pedestal
    - `focalLengthMm`, `aperture`, `depthOfField`, `sensorFormat`
    - `hyperfocalDistanceM`, `fieldOfViewDeg`
    - `stabilization`: locked|fluid_head|gimbal|handheld|drone
    - `focusMode`, `focusDistanceM`, `whiteBalanceKelvin`
    - `framing`, `compositionNotes`
    - `lighting` → `LightingGuidelines`
    - `style` → `StyleGuidelines`
    - `colorPalette[]`
    - `temporalBridgeAnchorRef` (last frame of preceding shot for continuity)
    - `manim` → `ManimConfig` (if procedural animation)
  - `continuityNotes`, `vfxNotes`
  - `assemblyHints` → `AssemblyHints` (track, layer, speed, transitions)
  - `plannedPosition` → `TimeRange`

### Reads
- `canonicalDocuments.script` (segments — what happens in each shot)
- `canonicalDocuments.directorInstructions` (camera language, style, must-haves, must-avoids)
- `canonicalDocuments.story` (beats — emotional objectives per beat)
- `production.characters[]` (for framing decisions)
- `production.environments[]` (for spatial context)
- `production.props[]` (for insert shots)
- `qualityProfiles[]` (resolution, frame rate, aspect ratio)

## Preconditions

- S07 has completed: `directorInstructions.cameraLanguage` exists
- S03 has completed: `script.segments[]` is populated
- S04, S05 recommended for character/environment-aware framing

## Procedure

### Step 1: Determine shot count per scene

Based on `targetDurationSec` per scene and the director's editing language:
- Long-take style: 1-3 shots per scene
- Standard coverage: 3-8 shots per scene
- Fast-cut style: 8-15 shots per scene

### Step 2: Design each shot

For each shot, apply the cinematographic language:

**Shot type selection** (based on narrative function):
- Establishing → WS or EWS
- Character introduction → MS or MWS
- Dialogue → MCU with OTS coverage
- Emotion → CU or XCU
- Action → MS to WS with movement
- Detail/insert → CU or XCU on prop

**Optics** (the formal tuple):
- `focalLengthMm`: 24-35mm for wide, 50-85mm for portraits, 100-200mm for compression
- `aperture`: f/1.4-2.8 for shallow DOF, f/5.6-11 for deep
- `depthOfField`: Derived from focal length + aperture + sensor format
- `hyperfocalDistanceM`: Computed from f²/(Nc) where N=aperture, c=circle of confusion
- `fieldOfViewDeg`: Computed from focal length and sensor format

**Lighting** per shot (inherits from director + adapts per scene):
- `mood`, `style`, `keyToFillRatio`, `colorTemperatureKelvin`, `contrastStyle`

### Step 3: Set temporal bridge anchors

For every shot except the first in a scene, set:
```
cinematicSpec.temporalBridgeAnchorRef: { logicalId: "shot-{prev}-last-frame" }
```
This conditions generation on the last frame of the preceding shot for continuity.

### Step 4: Set assembly hints

```
assemblyHints: {
  track: "V1",
  layerOrder: 0,
  speedPercent: 100,
  transitionIn: { type: "cut" },  // or dissolve, etc. from director's editing language
  transitionOut: { type: "cut" }
}
```

### Step 5: Calculate planned positions

Distribute shots across the scene's target duration, accounting for transitions.

### Step 6: Set version

```
version: { number: "1.0.0", state: "draft" }
```

## Output Contract

- Every scene in `production.scenes[]` (or scene stubs) has ≥1 shot
- Every shot has all required fields: `sceneRef`, `shotNumber`, `targetDurationSec`, `cinematicSpec`
- `cinematicSpec` has at minimum: `shotType`, `cameraAngle`, `cameraMovement`
- Shot durations within each scene sum to approximately the scene's `targetDurationSec`
- `temporalBridgeAnchorRef` is set for all non-first shots in each scene
- All optical parameters are physically plausible

## Downstream Dependencies

After S08: S09, S14, S15
