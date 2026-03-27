---
name: deliverable-packager
description: >
  Package rendered outputs into final deliverables with platform-specific
  configurations, localization targets, accessibility config, and publication
  metadata. Creates FinalOutputEntity entries (layer 4 of the 4-layer assembly
  model). Use when rendered videos need to be packaged for distribution. Trigger
  on "package deliverables", "prepare for distribution", "configure platforms",
  "set up localization". Trigger after S21 (QA Validator) passes.
---

# Deliverable Packager (S22)

## Purpose

Create `FinalOutputEntity` entries that configure rendered outputs for specific
platforms, with localization, accessibility, and publication metadata.

## Schema Surface

### Writes (primary owner)
- `deliverables[]` → `FinalOutputEntity[]`:
  - `outputType`, `platform`, `releaseChannel`
  - `runtimeSec`: Final runtime
  - `sourceTimelineRef`, `sourceEditRef`, `renderPlanRef`
  - `qcResults[]`: From S21
  - `localizationTargets[]` → `LocalizationConfig[]`:
    - `language` (BCP-47), `subtitleTrackRefs[]`, `dubbedAudioRef`, `adaptedMarketingRef`
  - `accessibilityConfig` → `AccessibilityConfig`:
    - `wcagLevel`, `closedCaptions`, `openCaptions`, `audioDescriptionRef`, `signLanguageRef`
  - `platformDeliveries[]` → `PlatformDelivery[]`:
    - `platform` (youtube|instagram|tiktok|vimeo|broadcast|theatrical|streaming)
    - `format`, `aspectRatio`, `resolution`, `frameRate`, `maxDurationSec`
    - `publishSchedule` → `FuzzyDate`

### Reads
- `assembly.renderPlans[]` (rendered output references)
- `project` (languages, audiences, genres)
- `qualityProfiles[]` (platform-specific specs)
- `canonicalDocuments.directorInstructions` (release preferences)

## Preconditions

- S20 has completed: render plan exists
- S21 has passed: quality gates are green

## Procedure

### Step 1: Determine target platforms

From `project.audiences` and any explicit platform targets:
- YouTube: 16:9, 1080p/4K, -14 LUFS, max 30 min
- Instagram: 9:16 or 1:1, 1080p, -14 LUFS, max 60s (reels) or 60 min (IGTV)
- TikTok: 9:16, 1080p, -14 LUFS, max 10 min
- Broadcast: per spec (often 1080i, -24 LUFS)

### Step 2: Create platform deliveries

For each platform, create `PlatformDelivery` with format-specific settings.

### Step 3: Configure localization

For each target language (from `project.languages`):
- Subtitle tracks (if available)
- Dubbed audio (if S12 produced multi-language)
- Adapted marketing materials

### Step 4: Configure accessibility

```
accessibilityConfig: {
  wcagLevel: "AA",
  closedCaptions: true,
  openCaptions: false,
  audioDescriptionRef: null  // or ref if audio description track exists
}
```

### Step 5: Create FinalOutputEntity

One per platform × format combination.

## Output Contract

- ≥1 `FinalOutputEntity` with all required fields
- Every deliverable has `sourceTimelineRef` and `renderPlanRef`
- `platformDeliveries[]` covers all target platforms
- `localizationTargets[]` covers all `project.languages`
- `accessibilityConfig` is present

## Downstream Dependencies

S22 produces the final pipeline output. No downstream skills depend on it.
