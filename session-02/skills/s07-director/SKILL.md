---
name: director
description: >
  Establish the directorial vision for the entire video production — vision statement,
  must-haves, must-avoids, camera language, editing language, performance direction,
  music direction, color direction, targeted notes (per entity, prioritized), and
  quality rules that propagate to QA gates. Use this skill when the pipeline needs
  creative direction established, or when the user says "set the creative direction",
  "direct this", "define the vision", "establish the style". Trigger after S03
  (Scriptwriter) and ideally after S04-S06 (world building). This skill's output
  governs every downstream production skill.
---

# Director (S07)

## Purpose

Synthesize all creative inputs (story, script, characters, environments) into a
unified creative vision that binds every downstream generation and assembly skill.

## Schema Surface

### Writes (primary owner)
- `canonicalDocuments.directorInstructions` → `DirectorInstructionsEntity`:
  - `visionStatement`: The creative north star (1-2 paragraphs)
  - `mustHaves[]`: Non-negotiable creative requirements
  - `mustAvoid[]`: Explicit prohibitions
  - `cameraLanguage`: How the camera tells the story
  - `editingLanguage`: Pacing and cutting style
  - `performanceDirection`: Character acting guidance
  - `musicDirection`: Score and sound aesthetic
  - `colorDirection`: Color palette and grading intent
  - `targetedNotes[]` → `TargetedNote[]` (per-entity notes with priority)
  - `qualityRules[]` → `ValidationRule[]` (propagated to QaGates)

### Reads
- `canonicalDocuments.story` (complete)
- `canonicalDocuments.script` (complete)
- `production.characters[]` (if available)
- `production.environments[]` (if available)
- `project` (genres, audiences, targetRuntimeSec)
- `qualityProfiles[]`

## Preconditions

- S03 has completed (minimum requirement)
- S04, S05 recommended but not required

## Procedure

### Step 1: Write the vision statement

A 1-2 paragraph declaration of the creative intent. This is the single document
every other skill references when making subjective decisions. It should establish:
- The emotional experience the audience should have
- The visual world and its rules
- The tonal register (grounded, heightened, surreal, etc.)
- References to existing works if helpful (but as direction, not imitation)

### Step 2: Define must-haves and must-avoids

**mustHaves**: Array of non-negotiable creative constraints:
- "Consistent warm color palette throughout"
- "Character faces always clearly visible in dialogue shots"
- "Musical silence in the final 5 seconds"

**mustAvoid**: Array of explicit prohibitions:
- "No Dutch angles except in the nightmare sequence"
- "Never show character X and character Y in the same frame before act 3"
- "No lens flares"

### Step 3: Define language directives

**cameraLanguage**: How the camera behaves:
- "Mostly static, observational. Slow dolly moves for emotional beats. No handheld."

**editingLanguage**: Cutting style and pacing:
- "Long takes in dialogue scenes (8-12s). Rapid cutting (2-3s) in action. Match cuts for transitions."

**performanceDirection**: Acting guidance:
- "Naturalistic, understated. Characters don't explain their emotions — they show them."

**musicDirection**: Score and sound aesthetic:
- "Minimal piano-based score. Ambient synth pads for tension. No percussion until the climax."

**colorDirection**: Color and grading:
- "Desaturated cool tones for reality, warm saturated tones for memory sequences. Final grade targets a film look with lifted blacks."

### Step 4: Create targeted notes

For specific entities (characters, scenes, shots), create `TargetedNote[]`:
```
{
  targetRef: { logicalId: "scene-003" },
  category: "lighting",
  priority: "high",
  note: "This scene must be backlit — silhouettes against the window"
}
```

### Step 5: Define quality rules

Create `ValidationRule[]` that flow to QaGates:
```
{
  name: "minimum-shot-duration",
  severity: "warning",
  metric: "shot.durationSec",
  operator: "gte",
  targetValue: 2.0,
  notes: "No shot shorter than 2 seconds except in the montage sequence"
}
```

### Step 6: Set version

```
version: { number: "1.0.0", state: "in_progress" }
```

## Output Contract

- `visionStatement` is non-empty and ≥100 words
- `mustHaves[]` has ≥3 entries
- `mustAvoid[]` has ≥2 entries
- All five language directives are non-empty strings
- `qualityRules[]` has ≥2 entries
- Every `targetedNote` references an existing or planned entity

## Iteration Rules

Re-run when:
- Creative direction fundamentally changes
- User overrides stylistic choices
- QA results reveal systemic quality issues traceable to directorial decisions

## Downstream Dependencies

After S07 completes, virtually every downstream skill is affected:
- **S08** (Cinematographer): Camera and style direction
- **S10** (Music): Music direction
- **S11** (Sound): Atmospheric guidance
- **S12** (Voice): Performance direction
- **S13** (Reference Assets): Style and color direction
- **S14** (Shot Video Gen): All visual direction
- **S18** (Post-Production): Color direction → grading
