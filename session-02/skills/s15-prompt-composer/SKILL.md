---
name: prompt-composer
description: >
  Assemble, optimize, and version prompts for all generative skills by composing
  weighted PromptFragments from characters, environments, and props with directorial
  style direction. Manages fragment ordering, weighting, locked-fragment preservation,
  negative prompt generation, and prompt versioning via PromptRecord[]. This is a
  cross-cutting skill used by S13, S14, and any future generative skills. Trigger
  on "compose prompts", "optimize the prompts", "assemble generation prompts",
  or whenever a generative skill needs assembled prompts.
---

# Prompt Composer (S15)

## Purpose

Central prompt assembly service. Combines entity-level prompt fragments with
directorial constraints into optimized, model-appropriate prompts with full
version tracking.

## Schema Surface

### Writes
- `GenerationStep.prompt` and `GenerationStep.negativePrompt` on any generating entity
- `GenerationStep.promptHistory[]` → `PromptRecord[]` (versioned audit trail)
- Reads and respects `PromptFragment.locked` — never modifies locked fragments

### Reads
- `production.characters[].canonicalPromptFragments[]`
- `production.environments[].canonicalPromptFragments[]`
- `production.props[].canonicalPromptFragments[]`
- `canonicalDocuments.directorInstructions` (style, color, must-haves, must-avoids)
- `production.shots[].cinematicSpec` (camera-specific terms)
- `qualityProfiles[].video.style` → `StyleGuidelines`

## Preconditions

- Entities with `canonicalPromptFragments[]` exist (S04, S05, S06)
- S07 has completed (directorial style direction)

## Procedure

### Step 1: Collect fragments for a generation target

Given a shot (or reference image request), collect all relevant fragments:
1. Character fragments for characters in the shot
2. Environment fragments for the shot's environment
3. Prop fragments for props in the shot
4. Shot-specific terms from `cinematicSpec` (shot type, camera angle, lighting)
5. Director's style fragments (from `directorInstructions`)

### Step 2: Order and weight

Sort fragments by `insertionOrder`. Apply weights:
- `locked: true` fragments: Always included at full weight, position preserved
- High-weight (≥0.8): Core identity descriptors — always included
- Medium-weight (0.4-0.7): Contextual modifiers — included if prompt budget allows
- Low-weight (<0.4): Optional enhancements — included only if space permits

### Step 3: Compose positive prompt

Concatenate fragments in insertion order, respecting token/character limits
of the target model. Apply category-based structuring:
```
[appearance fragments], [environment fragments], [action fragments],
[style fragments], [mood fragments], [constraint fragments]
```

### Step 4: Compose negative prompt

Build from:
- Character `bannedTraits[]`
- Director's `mustAvoid[]`
- Generic quality negatives (blur, distortion, artifacts — model-dependent)

### Step 5: Version the prompt

Create a `PromptRecord`:
```
{
  versionId: "prompt-{target}-{timestamp}",
  prompt: assembled positive prompt,
  negativePrompt: assembled negative prompt,
  createdAt: now,
  parentVersionId: previous version if iterating,
  changeNote: "Initial assembly" or "Adjusted weights for consistency"
}
```

Append to `generationStep.promptHistory[]`.

### Step 6: Validate

- Check that locked fragments appear unchanged in the final prompt
- Check that must-have terms from director are present
- Check that must-avoid terms are in the negative prompt
- Estimate token count against model limits

## Output Contract

- Assembled prompt respects all `locked: true` fragments verbatim
- Negative prompt includes all `bannedTraits` and `mustAvoid` items
- `PromptRecord` is created and appended to history
- Token count is within target model's limits
- All `insertionOrder` values are respected in final ordering

## Iteration Rules

Re-run when:
- Entity prompt fragments change (character redesign, etc.)
- Director updates style direction
- S16 identifies consistency issues traceable to prompt quality
- Target model changes (different token limits, different prompt syntax)

## Downstream Dependencies

S15 is consumed by: S13, S14 (and any future generative skills)
