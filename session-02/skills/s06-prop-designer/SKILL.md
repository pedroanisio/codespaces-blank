---
name: prop-designer
description: >
  Design and specify props (objects, items, vehicles) for video production —
  category, continuity notes, canonical prompt fragments, and reference asset refs.
  Use this skill when props need to be extracted from script action lines and
  designed for visual consistency. Trigger on "design the props", "create prop
  sheets", "define the objects". Trigger after S03 (Scriptwriter).
---

# Prop Designer (S06)

## Purpose

Create `PropEntity` entries for significant objects in the script that appear
across multiple shots or have narrative importance.

## Schema Surface

### Writes (primary owner)
- `production.props[]` → `PropEntity[]`:
  - `category`: Object classification
  - `continuityNotes`: How the prop changes or must remain consistent
  - `canonicalPromptFragments[]` → `PromptFragment[]`
  - `referenceAssetRefs[]`: Refs to reference images (S13)

### Reads
- `canonicalDocuments.script` (action segments mentioning objects)
- `canonicalDocuments.story` (narrative-significant objects)
- `production.environments[]` (spatial context)

## Preconditions

- S03 has completed: `script.segments[]` contains action segments

## Procedure

### Step 1: Extract props

Scan action segments for repeatedly mentioned or narratively significant objects.
Filter out generic background items — only create entities for props that:
- Appear in 2+ shots
- Are plot-relevant (e.g., a weapon, a letter, a magical object)
- Have continuity requirements (must look the same across scenes)

### Step 2: Design each prop

For each prop:
- `id`: `prop-{slug}-v1.0.0`, `logicalId`: `prop-{slug}`
- `category`: "weapon", "vehicle", "furniture", "technology", "food", "document", etc.
- `continuityNotes`: Document state changes (e.g., "sword is clean in act 1, bloodied in act 3")
- `canonicalPromptFragments[]`: Visual description fragments (appearance, material, scale)

### Step 3: Set version

```
version: { number: "1.0.0", state: "draft" }
```

## Output Contract

- One `PropEntity` per significant object
- Each has `category`, `continuityNotes`, and ≥1 prompt fragment
- Props with state changes document all states in continuity notes

## Downstream Dependencies

After S06: S07, S08, S09, S13, S15
