---
name: character-designer
description: >
  Design and fully specify characters for autonomous video production — appearance,
  wardrobe, personality, age, voice profile, canonical prompt fragments (weighted,
  ordered, categorized), banned traits, reference asset refs, and coherence
  requirements. Use this skill when characters need to be created from a script
  and story, when the user says "design the characters", "create character sheets",
  "define character appearance", "build the cast". Trigger after S03 (Scriptwriter)
  has produced a script with character references. Also trigger when characters
  need visual refinement or consistency adjustments.
---

# Character Designer (S04)

## Purpose

Create fully specified `CharacterEntity` entries for every character mentioned in
the script, with detailed visual descriptors encoded as weighted prompt fragments
for downstream generative models.

## Schema Surface

### Writes (primary owner)
- `production.characters[]` → `CharacterEntity[]`:
  - `appearance`: Free-text visual description
  - `wardrobe`: Clothing and accessories
  - `personality`: Trait array
  - `ageRange`: Age descriptor
  - `voiceProfile` → `VoiceProfile` (description, accent, pitch, speaking rate, reference audio refs)
  - `canonicalPromptFragments[]` → `PromptFragment[]` (weighted, ordered, categorized, lockable)
  - `bannedTraits[]`: Visual attributes to explicitly avoid
  - `referenceAssetRefs[]`: Will point to reference images (S13 creates them)
  - `coherenceRequirements` → `CharacterCoherence` (required, minSimilarityScore, lockedAttributes)
- Updates `project.globalCharacterRefs[]` with refs to created characters

### Reads
- `canonicalDocuments.script` (speaker refs, dialogue, parentheticals, performance notes)
- `canonicalDocuments.story` (arcs with character trajectories, beats)
- `project` (genres, audiences)
- `canonicalDocuments.directorInstructions` (if available — style direction)

## Preconditions

- S03 has completed: `script.segments[]` contains dialogue segments with `speakerRef`
- `story.arcs[]` exists (from S02)

## Procedure

### Step 1: Extract character roster

Scan `script.segments[]` for unique `speakerRef` values and action descriptions
mentioning character names. Build a roster with:
- Character identifier (from speakerRef logicalId)
- Dialogue volume (line count)
- Narrative role (from `story.arcs[]`)
- First appearance (segment order)

### Step 2: Design each character

For each character, generate:

**Identity:**
- `id`: `char-{slug}-v1.0.0`
- `logicalId`: `char-{slug}`
- `name`: Character name
- `ageRange`: e.g., "mid-30s", "elderly", "young adult"

**Visual design:**
- `appearance`: Detailed paragraph covering face, build, hair, skin, distinguishing features
- `wardrobe`: Primary costume description

**Personality:**
- `personality`: Array of 3-5 trait keywords (e.g., ["determined", "sardonic", "empathetic"])

**Voice:**
- `voiceProfile`:
  - `voiceDescription`: Textual voice character (e.g., "warm baritone with slight gravel")
  - `accent`: If relevant
  - `pitchRange`: "low", "mid", "high"
  - `speakingRateWpm`: Derived from character personality (nervous=180, calm=130, default=150)

### Step 3: Generate canonical prompt fragments

For each character, create `PromptFragment[]` with categories:

```
[
  { fragment: "a 35-year-old woman with sharp cheekbones and dark auburn hair",
    weight: 1.0, insertionOrder: 0, category: "appearance", locked: true },
  { fragment: "wearing a tailored navy blazer over a cream silk blouse",
    weight: 0.8, insertionOrder: 1, category: "appearance", locked: false },
  { fragment: "confident posture, direct eye contact",
    weight: 0.6, insertionOrder: 2, category: "action", locked: false },
  { fragment: "warm cinematic lighting",
    weight: 0.4, insertionOrder: 3, category: "style", locked: false }
]
```

Rules:
- `appearance` fragments should be `locked: true` (identity-defining)
- Order by importance (`insertionOrder` 0 = highest priority)
- Weight 1.0 for core identity, 0.3-0.8 for contextual attributes

### Step 4: Define banned traits

`bannedTraits[]`: Attributes that would break character identity:
- Opposite physical characteristics (if "dark hair" → ban "blonde", "platinum")
- Inconsistent age markers
- Culturally inappropriate attributes

### Step 5: Set coherence requirements

```
coherenceRequirements: {
  required: true,
  minSimilarityScore: 0.8,  // 0.85 for protagonists
  lockedAttributes: ["face_structure", "hair_color", "skin_tone", "body_type"]
}
```

### Step 6: Set version and status

```
version: { number: "1.0.0", state: "draft" }
status: "draft"
```

## Output Contract

- One `CharacterEntity` per unique speaker in the script
- Every character has non-empty `appearance`, `canonicalPromptFragments[]`, and `voiceProfile`
- `canonicalPromptFragments[]` has ≥2 fragments with `category: "appearance"` and `locked: true`
- `coherenceRequirements.required` is `true` for all characters
- `bannedTraits[]` has ≥1 entry per character
- `project.globalCharacterRefs[]` references all created characters

## Iteration Rules

Re-run when:
- S07 (Director) adjusts visual style (may change wardrobe, style fragments)
- S13 (Reference Asset Generator) produces images that require prompt fragment tuning
- S16 (Consistency Enforcer) reports coherence failures
- User changes character descriptions

## Downstream Dependencies

After S04 completes:
- **S07** (Director): Uses characters for performance direction
- **S08** (Cinematographer): Uses characters for shot framing decisions
- **S12** (Voice Producer): Uses voiceProfile for TTS generation
- **S13** (Reference Asset Generator): Uses prompt fragments for reference images
- **S15** (Prompt Composer): Assembles character fragments into generation prompts
