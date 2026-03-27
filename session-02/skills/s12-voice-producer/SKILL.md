---
name: voice-producer
description: >
  Produce voice-over and dialogue audio from script segments and character voice
  profiles. Creates AudioAssetEntity entries of type voice_over/dialogue with
  speaker refs, transcripts, sync points, and TTS generation manifests. Use when
  the pipeline needs spoken audio generated. Trigger on "generate the dialogue",
  "produce voice-over", "create the narration", "generate TTS audio".
  Trigger after S03 (Scriptwriter) and S04 (Character Designer).
---

# Voice / Dialogue Producer (S12)

## Purpose

Generate spoken audio for every dialogue and voice-over segment in the script,
using character voice profiles for consistent TTS generation.

## Schema Surface

### Writes (primary owner)
- `assetLibrary.audioAssets[]` → `AudioAssetEntity[]` where `audioType ∈ {voice_over, dialogue}`:
  - `speakerRef`, `characterRef` → EntityRef to CharacterEntity
  - `transcript`: Clean spoken text
  - `language`: From script segment or project
  - `syncPoints[]`: Timing alignment points
  - `technicalSpec`: Audio specifications
  - `generation` → `GenerationManifest` (TTS model, voice cloning params)
- Updates `script.segments[].audioAssetRef` with refs to generated audio

### Reads
- `canonicalDocuments.script` (dialogue, voice_over, parenthetical segments)
- `production.characters[]` (voiceProfile for each speaker)
- `canonicalDocuments.directorInstructions` (performanceDirection)
- `qualityProfiles[]` (audio quality targets — dialog intelligibility)

## Preconditions

- S03 has completed: dialogue/VO segments exist in script
- S04 has completed: characters have voice profiles

## Procedure

### Step 1: Extract speech segments

Filter `script.segments[]` for `segmentType ∈ {dialogue, voice_over}`.
Group by speaker for batch processing with consistent voice settings.

### Step 2: Configure TTS per character

From each character's `voiceProfile`:
- Select TTS model/provider matching voice description
- Set speaking rate from `speakingRateWpm`
- Apply accent and pitch range settings
- Apply `performanceDirection` from director as emotional guidance

### Step 3: Generate audio assets

For each speech segment:
- `transcript`: `segment.spokenText` (clean version without parentheticals)
- `characterRef`: Points to the speaking character
- Apply performance notes from `segment.performanceNotes`
- Calculate duration from word count / speaking rate
- Create sync points for word-level or phrase-level alignment

### Step 4: Update script cross-references

Set `segment.audioAssetRef` pointing to the generated audio asset.

### Step 5: Quality checks

- Verify pronunciation of character/place names
- Check timing against shot durations
- Verify dialog intelligibility meets quality profile threshold

## Output Contract

- One audio asset per speech segment in the script
- Every asset has `transcript`, `characterRef`, `technicalSpec`
- `script.segments[].audioAssetRef` populated for all dialogue/VO segments
- Audio durations are within ±10% of calculated timing
- Dialog intelligibility score ≥ quality profile minimum

## Downstream Dependencies

After S12: S19 (Audio Mixer), S17 (Timeline Assembler)
