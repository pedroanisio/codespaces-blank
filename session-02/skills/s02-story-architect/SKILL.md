---
name: story-architect
description: >
  Develop a complete narrative structure from a story stub — story beats with ordering
  and emotional objectives, narrative arcs with character trajectories, scene references,
  and marketing hooks. Use this skill whenever the pipeline needs to expand a logline/premise
  into a full beat sheet and arc structure, or when the user says "develop the story",
  "create the beat sheet", "structure the narrative", "plan the story beats", "build
  narrative arcs". Trigger after S01 (Concept Seed) has produced a story stub. Also
  trigger when story structure needs revision due to feedback or scope changes.
---

# Story Architect (S02)

## Purpose

Expand the story stub (logline, premise, themes, tone) into a fully structured
narrative with ordered beats, emotional trajectories, narrative arcs, and scene
breakdowns. This is the structural backbone that every downstream creative skill
depends on.

## Schema Surface

### Writes (primary owner)
- `canonicalDocuments.story` → `StoryEntity` (full population):
  - `beats[]` → `StoryBeat[]` (beatId, name, order, description, purpose, targetRange, emotionalObjective, sceneRefs)
  - `arcs[]` → `NarrativeArc[]` (arcId, name, description, characterRefs, startBeatRef, endBeatRef, trajectory)
  - `sceneRefs[]` → EntityRef[] pointing to scenes (created as stubs for S09)
  - `marketingHooks[]` → string[] (hooks for S23)
  - `synopsis` → Full narrative summary

### Reads
- `canonicalDocuments.story` (stub from S01)
- `project` (genres, audiences, targetRuntimeSec, languages)
- `qualityProfiles[]` (runtime targets and tolerances)

## Preconditions

- S01 has completed: `story.logline` and `story.premise` exist
- `project.targetRuntimeSec` is set

## Procedure

### Step 1: Determine narrative structure

Based on `project.genres` and `project.targetRuntimeSec`:

| Duration | Structure |
|----------|-----------|
| <30s | Single beat (hook → payoff) |
| 30-60s | 3 beats (hook → develop → resolve) |
| 1-3 min | 5 beats (hook → setup → confrontation → climax → resolution) |
| 3-10 min | 7-9 beats (full three-act with midpoint) |
| 10-30 min | 12-15 beats (detailed three-act with subplots) |

### Step 2: Generate story beats

For each beat, create a `StoryBeat`:
- `beatId`: `beat-{order:03d}` (e.g., `beat-001`)
- `name`: Short descriptive name
- `order`: Sequential integer starting at 1
- `description`: What happens in this beat (2-3 sentences)
- `purpose`: Why this beat exists narratively (setup, escalation, reversal, etc.)
- `targetRange`: Calculated from targetRuntimeSec / number of beats (proportional to dramatic weight)
- `emotionalObjective`: Target audience emotion (curiosity, tension, surprise, satisfaction, etc.)

### Step 3: Generate narrative arcs

For each significant character or thematic thread:
- `arcId`: `arc-{slug}`
- `name`: Arc name (e.g., "Protagonist's transformation", "Mystery revelation")
- `description`: The arc's trajectory in 1-2 sentences
- `characterRefs`: EntityRef[] — will be populated when S04 creates characters (use logicalId placeholders)
- `startBeatRef`: EntityRef to the beat where this arc begins
- `endBeatRef`: EntityRef to the beat where this arc resolves
- `trajectory`: Array of stage descriptions across beats

### Step 4: Generate marketing hooks

Analyze the story for moments with marketing potential:
- Visual spectacle moments (thumbnails, teasers)
- Emotionally resonant quotes or lines
- Mystery/curiosity gaps (trailers)
- Each hook is a string stored in `story.marketingHooks[]`

### Step 5: Write synopsis

Compose a `synopsis` (3-5 paragraphs) that covers the entire narrative arc in prose form.
This is the canonical story reference for all downstream skills.

### Step 6: Update version

Set `story.version`:
- `number`: Bump from "0.1.0" to "1.0.0"
- `state`: "draft" → "in_progress"
- `changeSummary`: "Full beat sheet and arc structure generated"

## Output Contract

- `beats[]` has at least 3 entries, each with all required fields
- Beat `order` values are sequential with no gaps
- `targetRange` values across all beats sum to approximately `project.targetRuntimeSec`
- Every `NarrativeArc` has valid `startBeatRef` and `endBeatRef` pointing to existing beats
- `synopsis` is non-empty and consistent with the beats
- `marketingHooks` has at least 2 entries

## Iteration Rules

Re-run when:
- S03 (Scriptwriter) identifies structural problems during script development
- S07 (Director) requests narrative restructuring
- User provides feedback on pacing, tone, or story direction
- Runtime constraints change

## Downstream Dependencies

After S02 completes:
- **S03** (Scriptwriter): Uses beats and synopsis to write the script
- **S07** (Director): Uses beats, arcs, and tone for directorial vision
- **S23** (Marketing): Uses marketingHooks for campaign planning
