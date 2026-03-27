---
name: s13-reference-asset-gen
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
  - `visualType`: "character_reference" | "environment_reference" | "environment_pov_plate" | "prop_reference"
  - `modality`: "image"
  - `purpose`: "canonical_reference"
  - `characterRefs[]`: Back-references for character reference images
  - `environmentRefs[]`: Back-references for environment reference images
  - `povCharacterRef`: EntityRef to the character whose POV defines the camera (for `environment_pov_plate`)
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

For each environment, generate 2 reference images (NO characters present):
- Wide establishing shot — full spatial extent, lighting, atmosphere
- Detail/atmosphere shot — textures, distinctive elements, mood

**Important**: Environment plates must contain absolutely NO people, NO human
figures, NO characters. They are background plates for spatial/lighting reference.

### Step 3b: Generate POV environment plates

For each (character, environment) pair where the character appears in scenes
using that environment, generate 1 POV plate:
- Camera at character eye-level: `character.heightM × 0.94` (eye-to-height ratio)
- Camera facing the direction the character would look in their primary scene
- First-person perspective — what the character sees when they enter the space
- Same lighting/atmosphere as environment plates
- `visualType: "environment_pov_plate"`
- `povCharacterRef`: EntityRef to the character defining the viewpoint

**Why**: POV plates anchor the spatial relationship between character and
environment. When S14 generates a shot where the character looks around,
the POV plate ensures the environment matches what was established. Critical
for `shotType: "POV"` and subjective camera sequences.

### Step 4: Generate prop references (in-environment)

For significant props, generate 1 reference image each, rendered **inside
their scene environment** — NOT in isolation:
- Find which environment the prop appears in via `scene.propRefs[]`
- Render the prop with the environment's lighting, color temperature, and atmosphere
- Close-up framing showing the prop with environment visible behind it
- Same ambient lighting as the environment plates from Step 3
- NO people, NO hands — focus on the object

**Why**: Props rendered with studio lighting look disconnected when composited
into the scene. By rendering them in-context, the lighting, shadows, and color
temperature match the environment plates, maintaining visual coherence.

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

- ≥3 reference images per character (front, 3/4, full body)
- ≥2 plates per environment (wide, detail) — NO characters in frame
- ≥1 POV plate per (character, environment) pair appearing in the same scene
- ≥1 render per significant prop (isolated, studio lighting)
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
