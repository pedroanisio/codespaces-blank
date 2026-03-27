---
name: marketing-asset-gen
description: >
  Generate marketing assets from the production — trailers, teasers, thumbnails,
  social clips, posters, banners, press kits. Creates MarketingAssetEntity entries
  with copy packs (headline, caption, body, CTA, hashtags, alt text), campaign
  grouping, and platform targeting. Use when the production needs marketing
  materials. Trigger on "create marketing assets", "make a trailer", "generate
  thumbnails", "build social clips", "create the press kit". Trigger after main
  production is complete or in parallel with delivery packaging.
---

# Marketing Asset Generator (S23)

## Purpose

Create marketing materials derived from the completed production, using story
marketing hooks and production assets.

## Schema Surface

### Writes (primary owner)
- `assetLibrary.marketingAssets[]` → `MarketingAssetEntity[]`:
  - `marketingType`: trailer|teaser|thumbnail|social_clip|poster|banner|press_kit
  - `campaignId`: Groups related marketing assets
  - `targetPlatforms[]`: Where this asset will be published
  - `durationSec`: For video marketing assets
  - `storyRef`: Back-reference to `StoryEntity`
  - `originatingHook`: Maps to `story.marketingHooks[]` value
  - `sourceSceneRefs[]`, `sourceShotRefs[]`, `sourceAssetRefs[]`
  - `copy` → `CopyPack`:
    - `headline`, `caption`, `body`, `cta`, `hashtags[]`, `altText`
  - `assemblyPlanRef`: Ref to assembly plan for video marketing assets
  - `thumbnailSourceRef`: Ref to source frame for thumbnails

### Reads
- `canonicalDocuments.story` (marketingHooks, logline, synopsis)
- `production.scenes[]` (visually impactful moments)
- `production.shots[]` (key frames for thumbnails)
- `assetLibrary.visualAssets[]` (source material)
- `assetLibrary.audioAssets[]` (for trailer audio)
- `project` (genres, audiences)

## Preconditions

- S02 has completed: `story.marketingHooks[]` exists
- Ideally S14 has completed: video assets available for trailer/clip extraction

## Procedure

### Step 1: Map marketing hooks to assets

For each hook in `story.marketingHooks[]`:
- Identify the best source scenes and shots
- Determine appropriate marketing asset types

### Step 2: Generate thumbnails

Select high-impact frames from key shots:
- Emotional peaks, visual spectacle, character close-ups
- Create `MarketingAssetEntity` with `marketingType: "thumbnail"`
- Set `thumbnailSourceRef` to the source shot/frame

### Step 3: Plan trailers and teasers

Select shots that create intrigue without spoiling:
- Teaser: 15-30s, 3-5 shots, mystery/curiosity
- Trailer: 30-90s, 10-20 shots, full story arc hint
- Create assembly plan references for video marketing assets

### Step 4: Generate social clips

Extract self-contained moments for social platforms:
- 15-60s clips optimized for each platform's aspect ratio
- Vertical crops for TikTok/Reels, square for feed posts

### Step 5: Write copy packs

For each marketing asset, write `CopyPack`:
- `headline`: Attention-grabbing title (platform-appropriate length)
- `caption`: Engagement-driving description
- `body`: Longer form for press kits
- `cta`: Clear call to action ("Watch now", "Coming soon")
- `hashtags[]`: Relevant and discoverable
- `altText`: Accessibility description of the visual

### Step 6: Group into campaigns

Assign `campaignId` to related assets for coordinated release.

## Output Contract

- ≥1 thumbnail per production
- ≥1 social clip if target platforms include social media
- Every marketing asset has `copy` (CopyPack) populated
- `storyRef` and `originatingHook` trace provenance to story
- `targetPlatforms[]` is non-empty for all assets

## Downstream Dependencies

S23 is a terminal skill — no downstream dependencies.
