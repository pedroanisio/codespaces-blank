---
name: reference-asset-gen
description: >
  Generate canonical reference images for characters, environments, and props —
  the visual anchors all subsequent video generation depends on. Creates
  VisualAssetEntity entries with isCanonicalReference=true, modality=image,
  and sets up ConsistencyAnchors at entity level. Use when the pipeline needs
  reference images generated before shot video generation. Trigger on "generate
  reference images", "create character sheets", "make concept art", "build visual
  references". Trigger after S04-S06 (world building) and S07 (Director).
---

# Reference Asset Generator (S13)

## Purpose

Generate canonical reference images for every character, environment, and
significant prop. These images serve as visual anchors (ConsistencyAnchors)
for all downstream video generation.

## Schema Surface

### Writes (primary owner)
- `assetLibrary.visualAssets[]` → `VisualAssetEntity[]` where `isCanonicalReference: true`:
  - `visualType`: "character_reference" | "environment_reference" | "prop_reference"
  - `modality`: "image"
  - `purpose`: "canonical_reference"
  - `characterRefs[]`: Back-references for character reference images
  - `environmentRefs[]`: Back-references for environment reference images
  - `propRefs[]`: Back-references for prop reference images
  - `spec` → `VisualAssetSpec` (resolution, style, lighting)
  - `generation` → `GenerationManifest`:
    - `mode`: "ai_generated"
    - `steps[]` → `GenerationStep[]` with full audit trail
    - `consistencyAnchors[]` → `ConsistencyAnchor[]`
    - `reproducibility`: Seed + model version for deterministic replay
- Updates entity `referenceAssetRefs[]` on characters, environments, props

### Reads
- `production.characters[]` (canonicalPromptFragments, appearance)
- `production.environments[]` (canonicalPromptFragments)
- `production.props[]` (canonicalPromptFragments)
- `canonicalDocuments.directorInstructions` (style, color direction)
- `qualityProfiles[]` (resolution, style guidelines)

## Preconditions

- S04 has completed: characters have `canonicalPromptFragments[]`
- S05 has completed: environments have `canonicalPromptFragments[]`
- S07 has completed: directorial style direction exists

## Procedure

### Step 1: Assemble prompts per entity

Use S15 (Prompt Composer) to assemble final prompts from each entity's
`canonicalPromptFragments[]`, incorporating director's style direction.

### Step 2: Generate character references

For each character, generate 2-3 reference images:
- Front-facing neutral expression (primary anchor)
- 3/4 view with characteristic expression
- Full body showing wardrobe

Each image gets a `GenerationStep` with:
- Complete prompt + negative prompt
- Seed (stored for reproducibility)
- Model descriptor (provider, model ID, version)
- Resolution from quality profile

### Step 3: Generate environment references

For each environment, generate 1-2 reference images:
- Wide establishing shot
- Detail/atmosphere shot (if complex environment)

### Step 4: Generate prop references

For significant props, generate 1 reference image each.

### Step 5: Create consistency anchors

For each reference image, create `ConsistencyAnchor`:
```
{
  anchorType: "character" | "environment" | "prop",
  name: entity name,
  ref: { id: asset-id },
  weight: 1.0,
  lockLevel: "hard",  // Reference images are hard anchors
  attributes: ["face", "hair", "clothing"]  // What must remain consistent
}
```

### Step 6: Update entity cross-references

Set `referenceAssetRefs[]` on each character, environment, and prop entity.

## Output Contract

- ≥2 reference images per character, ≥1 per environment, ≥1 per significant prop
- All images have `isCanonicalReference: true`
- Each image has a complete `GenerationManifest` with seeds and model info
- `ConsistencyAnchor[]` is populated with `lockLevel: "hard"`
- Entity `referenceAssetRefs[]` are updated with back-references
- All images meet quality profile resolution requirements

## Iteration Rules

Re-run when:
- Character/environment/prop design changes
- Director adjusts style direction
- S16 (Consistency Enforcer) identifies anchor quality issues
- User rejects reference image quality

## Downstream Dependencies

After S13: S14 (Shot Video Generator), S16 (Consistency Enforcer)
