---
name: scriptwriter
description: >
  Write a complete production script with ordered segments — scene headings, action
  lines, dialogue, voice-over, parentheticals, transitions, title cards, and on-screen
  text — all linked to scenes, shots, and characters via EntityRefs. Use this skill
  when the pipeline needs a script written from a completed story structure, or when
  the user says "write the script", "create dialogue", "draft the screenplay",
  "script this story". Trigger after S02 (Story Architect) has produced beats and
  arcs. Also trigger for script revisions, dialogue polish, or pacing adjustments.
---

# Scriptwriter (S03)

## Purpose

Transform the story's beat sheet and synopsis into a line-level production script
with typed segments, timing, speaker references, and performance notes.

## Schema Surface

### Writes (primary owner)
- `canonicalDocuments.script` → `ScriptEntity`:
  - `format`: "markdown" (default) or as specified
  - `segments[]` → `ScriptSegment[]` with full typing
  - `sceneRefs[]` → Links to scene entities
  - `language`: From `project.languages[0]`

### Reads
- `canonicalDocuments.story` (beats, arcs, synopsis, logline)
- `project` (genres, audiences, targetRuntimeSec, languages)
- `qualityProfiles[]` (runtime constraints)

## Preconditions

- S02 has completed: `story.beats[]` is populated with ≥3 beats
- `story.synopsis` exists

## Procedure

### Step 1: Scene breakdown

Map each story beat to one or more scenes. For each scene, generate a `scene_heading`
segment:

```
segmentType: "scene_heading"
text: "INT. COFFEE SHOP - DAY"  (or equivalent for non-live-action)
sceneRef: { logicalId: "scene-{number}" }
order: sequential
```

### Step 2: Write action and dialogue segments

For each scene, write the content segments in screenplay order:

- **action**: Describes what is visually happening. Links to `shotRef` when a specific
  shot is implied. Includes `actionDescription` for visual direction.
- **dialogue**: Character speech. Sets `speakerRef` (logicalId placeholder for S04),
  `spokenText` (clean text for TTS), `performanceNotes` (emotion, pacing).
- **parenthetical**: Delivery instructions embedded in dialogue blocks.
- **voice_over**: Narration. Sets `speakerRef` if narrator is a character.
- **transition**: Edit transitions between scenes (CUT TO, DISSOLVE TO, etc.)
- **title_card**: On-screen text cards.
- **on_screen_text**: Lower thirds, labels, captions within scenes.

### Step 3: Calculate timing

For each segment, estimate `timing` (TimeRange):
- Action lines: ~3 seconds per sentence
- Dialogue: Word count / speaking rate (default 150 WPM)
- Transitions: 0.5-2 seconds
- Title cards: 3-5 seconds per card

Validate that total segment timing ≈ `project.targetRuntimeSec` ± tolerance.

### Step 4: Assign segment ordering

Set `order` as sequential integers across the entire script.
Ensure scene_heading segments precede their scene's content segments.

### Step 5: Cross-reference

- Every dialogue segment should have a `speakerRef` (use logicalId placeholders
  like `char-narrator`, `char-protagonist` — S04 will create the actual entities)
- Every segment within a scene should have `sceneRef`
- Key segments should have `shotRef` suggestions (logicalId placeholders for S08)

### Step 6: Set metadata

```
script.format: "markdown"
script.language: project.languages[0]
script.version: { number: "1.0.0", state: "in_progress" }
```

## Output Contract

- `segments[]` is non-empty and covers every story beat
- Every segment has `segmentId`, `order`, and `segmentType`
- Segment `order` values are sequential with no gaps
- Every `dialogue` segment has `speakerRef` and `spokenText`
- Every `action` segment has `actionDescription`
- Total estimated timing is within ±15% of `project.targetRuntimeSec`
- At least one `scene_heading` exists per story beat

## Iteration Rules

Re-run when:
- S07 (Director) requests dialogue changes or restructuring
- S12 (Voice Producer) reports timing mismatches
- User provides dialogue or pacing feedback
- Character names change after S04 creates character entities

## Downstream Dependencies

After S03 completes:
- **S04** (Character Designer): Extracts character list from speaker refs and descriptions
- **S05** (Environment Designer): Extracts locations from scene headings
- **S06** (Prop Designer): Extracts objects from action descriptions
- **S07** (Director): Uses script for directorial vision
- **S08** (Cinematographer): Uses action descriptions for shot design
- **S12** (Voice Producer): Uses dialogue/VO segments for audio generation
