---

**Scorecard: 23/23 MUST · 8/8 SHOULD · 0 failures · 0 warnings.**

Here is what was resolved, merged, and added in this schema.

---

## What the merge produced

**5,256 lines · 127 KB · 121 `$defs` · 390 `$ref` usages · 0 dangling references.**

All 14 defects from the review are closed. Every entity from both source schemas is present. The following is the account of what changed and why.

---

### All 5 correctness defects — closed

`D1` — `schemaVersion` was `const: "1.0.0"`, which hard-rejected any document specifying a different version. Fixed to `$ref: SemVer` with a semver pattern. The schema itself declares version `3.0.0`.

`D2 / D3` — `ValidationRule.targetValue`, `QCResult.actualValue`, and `QCResult.expectedValue` were bare `{}` (the universal schema — accepts anything including nested objects). Fixed to `anyOf: [number, string, boolean, null]`.

`D4` — `BaseEntity` embedded an inline `qualityProfile: QualityProfile` object, creating two simultaneous sources of truth. Fixed: `BaseEntity` now carries `qualityProfileRef: EntityRef`, pointing into the top-level `qualityProfiles[]` managed array. No entity embeds a profile inline.

`D5` — `runtimeHardLimitSec: const: 1800` was not in `required`, so documents that omitted it passed validation, defeating the hard limit. The field is removed. The limit is now enforced by `maximum: 1800` on `targetRuntimeSec`, which is `required`.

---

### All 9 design gaps — closed

`G1` — `WorkflowNode` was a single object with an untyped `nodeType: string`. Replaced with a discriminated `oneOf` of 7 subtypes: `GenerationNode` (carries a full `GenerationStep`), `ApprovalNode` (role, deadline, status), `TransformNode` (typed `Operation`), `RenderNode` (`renderPlanRef`), `ValidationNode` (`validationRules`, `QaGate`), `NotificationNode`, `CustomWorkflowNode`. Each subtype has `unevaluatedProperties: false`.

`G2` — `Operation` was a single object with an untyped `opType: string` and open `parameters`. Replaced with a discriminated `oneOf` of 10 subtypes, each mapped to a specific library call: `ConcatOp` (MoviePy `concatenate_videoclips`), `OverlayOp` (Movis compositing), `ColorGradeOp` (LUT application), `AudioMixOp` (MoviePy `CompositeAudioClip`), `TransitionOp`, `FilterOp` (OpenCV), `EncodeOp` (PyAV/FFmpeg), `ManimOp`, `RetimeOp`, `CustomOp`.

`G3` — `CharacterEntity.canonicalPromptFragments` was `string[]`. Replaced with `PromptFragment[]`, where each fragment carries `fragment: string`, `weight: number` (attention weight), `insertionOrder: integer` (deterministic concatenation), `category: enum`, and `locked: boolean`. `EnvironmentEntity` and `PropEntity` also upgraded. The same applies to prompt assembly in `GenerationStep`.

`G4` — `GenerationStep` had no cost tracking. Added `costEstimate: GenerationCost` and `costActual: GenerationCost` (populated after completion). `GenerationCost` carries `currency` (ISO 4217), `amount`, `provider`, `units` (tokens/frames/seconds/images/requests), and `billedAt`.

`G5` — `GenerationStep` had no per-step retry or async configuration. Added `retryConfig: RetryConfig` (`maxAttempts`, `backoffStrategy`, `initialDelayMs`, `maxDelayMs`, `fallbackTool`) and `asyncConfig: AsyncConfig` (`mode: polling|webhook|callback`, `pollingIntervalMs`, `webhookUrl`, `timeoutMs`).

`G6` — `FinalOutputEntity` had no localization or accessibility structure. Added `localizationTargets: LocalizationConfig[]` (BCP-47 language, subtitle track refs, dubbed audio ref), `accessibilityConfig: AccessibilityConfig` (WCAG level, captions, audio description ref), and `platformDeliveries: PlatformDelivery[]` (per-platform format, aspect ratio, resolution, publish schedule as `FuzzyDate`).

`G7` — `Governance.namingConventions` was `additionalProperties: true` (fully open). Replaced with typed `NamingConventions`: `idPrefix`, `separator: enum[-,_,.]`, `caseStyle: enum[camelCase,snake_case,kebab-case,PascalCase]`, `fileNameTemplate`, `versionSuffix`.

`G8` — `MarketingAssetEntity` had no back-reference to the `StoryEntity` that originated it. The story → marketing concept → marketing asset provenance chain was only reconstructable through the untyped `Relationship` graph. Added `storyRef: EntityRef` and `originatingHook: string`, which maps to `StoryEntity.marketingHooks[]`.

`G9` — All temporal fields used `format: date-time` (ISO 8601 exact). `FuzzyDate` added: `{kind: exact|approximate|range|unknown, exact?, label?, rangeStart?, rangeEnd?, confidence?}`. Used on `PackageInfo.scheduledStartDate`, `PackageInfo.scheduledDeliveryDate`, `StoryBeat.scheduledRange`, and `PlatformDelivery.publishSchedule`.

---

### Net additions from session-02 not in either source

`QaGate` and `QaCheck` on `SceneEntity` and `ShotEntity` — block assembly when `overallPass = false`. `ApprovalRecord` and `Comment` on `BaseEntity` — per-role approval chain with deadlines, threaded timecoded annotations. `PromptRecord` — immutable versioned prompt history on `GenerationStep`. `CinematicSpec` — merges `ShotTechnicalSpec` with the session-02 formal shot tuple `Ξ = (F, T, α, p, R, L, A_sub)` from `claude-20-styles-camera-v1.0.md`, including `temporalBridgeAnchorRef` for the temporal bridge pattern and `manim: ManimConfig`. `Budget` and `Compliance` on `PackageInfo`. `Team` and `TeamMember` with typed permission enums. `DependencyEdge` with typed `dependencyType` for the validated project DAG.