---
name: environment-designer
description: >
  Design and specify environments/locations for video production — location type,
  architecture style, time-of-day defaults, weather defaults, continuity notes,
  and canonical prompt fragments. Use this skill when environments need to be created
  from script scene headings and story context. Trigger on "design the environments",
  "create locations", "define the settings", "build the world". Trigger after S03
  (Scriptwriter) has produced scene headings. Also trigger for environment refinement
  or when adding new locations.
---

# Environment Designer (S05)

## Purpose

Create `EnvironmentEntity` entries for every distinct location in the script,
with visual descriptors encoded as prompt fragments for consistent generation.

## Schema Surface

### Writes (primary owner)
- `production.environments[]` → `EnvironmentEntity[]`:
  - `locationType`: interior / exterior / mixed / virtual / abstract
  - `architectureStyle`: Architectural description
  - `timeOfDayDefaults[]`: Default lighting times
  - `weatherDefaults[]`: Default weather conditions
  - `continuityNotes`: Spatial consistency notes
  - `canonicalPromptFragments[]` → `PromptFragment[]`
  - `referenceAssetRefs[]`: Refs to reference images (S13 creates)
- Updates `project.globalEnvironmentRefs[]`

### Reads
- `canonicalDocuments.script` (scene_heading segments, action descriptions)
- `canonicalDocuments.story` (beats with setting context)
- `project` (genres — influences architectural choices)
- `canonicalDocuments.directorInstructions` (if available)

## Preconditions

- S03 has completed: `script.segments[]` contains `scene_heading` segments

## Procedure

### Step 1: Extract locations

Parse all `scene_heading` segments for location patterns (INT./EXT., location name, time of day). Deduplicate locations that appear in multiple scenes.

### Step 2: Design each environment

For each unique location:
- `id`: `env-{slug}-v1.0.0`
- `logicalId`: `env-{slug}`
- `locationType`: Classify from scene heading (INT.=interior, EXT.=exterior)
- `architectureStyle`: Infer from genre and script context
- `timeOfDayDefaults`: Extract from scene headings (DAY, NIGHT, DAWN, etc.)
- `weatherDefaults`: Extract or infer from script and genre
- `continuityNotes`: Document spatial layout, key features, spatial relationships

### Step 3: Generate canonical prompt fragments

Create `PromptFragment[]` per environment:
- `category: "environment"` fragments for spatial description (locked: true)
- `category: "style"` fragments for visual atmosphere (locked: false)
- `category: "mood"` fragments for emotional quality (locked: false)

### Step 4: Set version

```
version: { number: "1.0.0", state: "draft" }
```

## Output Contract

- One `EnvironmentEntity` per distinct location in the script
- Every environment has `locationType`, `canonicalPromptFragments[]` (≥2 fragments)
- `continuityNotes` is non-empty
- `project.globalEnvironmentRefs[]` references all created environments

## Downstream Dependencies

After S05: S07, S08, S09, S13, S15
