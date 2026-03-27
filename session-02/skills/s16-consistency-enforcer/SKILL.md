---
name: consistency-enforcer
description: >
  Verify visual consistency across generated assets by comparing against reference
  anchors — character coherence scores, temporal consistency scores, flicker
  detection, identity drift measurement. Operates as a verification loop tightly
  coupled with S14 (Shot Video Generator) — triggers re-generation when thresholds
  are violated. Use when generated visuals need consistency validation. Trigger on
  "check consistency", "validate visual coherence", "enforce character consistency",
  or automatically after every generation pass from S14.
---

# Consistency Enforcer (S16)

## Purpose

Verify that generated visual assets maintain consistency with canonical reference
images and with each other across shots. Trigger re-generation when consistency
thresholds are violated.

## Schema Surface

### Writes
- Updates `ConsistencyAnchor[]` on generated assets (lock levels, weights)
- Writes consistency scores to entity metadata:
  - `CharacterCoherence.minSimilarityScore` results
  - `TemporalConsistency.minConsistencyScore` results
  - Flicker scores (`maxFlickerScore`)
  - Identity drift scores (`maxIdentityDriftScore`)
- Writes to `QaCheck` results within `QaGate` on shots/scenes

### Reads
- `assetLibrary.visualAssets[]` where `isCanonicalReference: true` (anchors)
- `assetLibrary.visualAssets[]` where `modality: "video"` (generated clips)
- `production.characters[].coherenceRequirements`
- `qualityProfiles[].video.temporalConsistency`
- `qualityProfiles[].video.characterCoherence`
- `production.shots[].cinematicSpec.temporalBridgeAnchorRef`

## Preconditions

- S13 has completed: reference assets exist
- S14 has produced ≥1 video asset to validate

## Procedure

### Step 1: Character coherence check

For each generated video containing a character:
- Compare character appearance against canonical reference (face embedding similarity)
- Score against `coherenceRequirements.minSimilarityScore`
- Check `lockedAttributes` (face_structure, hair_color, etc.)
- Result: PASS if score ≥ threshold, FAIL otherwise

### Step 2: Temporal consistency check

For sequential shots within a scene:
- Compare last frame of shot N with first frame of shot N+1
- Score scene-level temporal consistency
- Check for flicker (frame-to-frame instability within a shot)
- Check identity drift (gradual character change over shot duration)

### Step 3: Cross-shot environment consistency

For shots sharing an environment:
- Compare environment appearance against environment reference
- Score architectural consistency, lighting consistency, color palette adherence

### Step 4: Report results

For each check, write:
```
{
  name: "character_coherence_char-protagonist",
  score: 0.87,
  pass: true,  // score ≥ threshold
  notes: "Minor wardrobe variation in shot-007, within tolerance",
  evidenceRefs: [{ id: "ref-img-protagonist-front" }]
}
```

### Step 5: Trigger re-generation if needed

If any `lockLevel: "hard"` anchor is violated (score < threshold):
- Flag the shot for re-generation
- Adjust `ConsistencyAnchor` weights (increase problem areas)
- Adjust prompt fragments via S15
- Request S14 to regenerate the specific shot

If `lockLevel: "medium"`: warn but allow progression.
If `lockLevel: "soft"`: log only.

## Output Contract

- Every generated video asset has consistency scores recorded
- Hard-anchor violations trigger re-generation requests
- All checks produce `QaCheck` entries with scores and evidence
- No shot with hard-anchor violations proceeds to timeline assembly

## Iteration Rules

This skill runs after every generation pass from S14.
It forms a feedback loop: S14 → S16 → (adjust) → S14 → S16 until pass.

## Downstream Dependencies

S16 gates S17: shots only proceed to timeline assembly after consistency passes.
