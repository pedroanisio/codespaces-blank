I structured this as a normalized asset graph on JSON Schema Draft 2020-12. That draft is the current published JSON Schema version, and its composability features such as `unevaluatedProperties` make it a strong fit for a strict core schema with controlled extension points. ([JSON Schema][1])

I also split assembly into four neutral layers: timeline composition, stream/time-base bindings, frame-level operations, and procedural nodes. That maps cleanly to MoviePy and Movis composition workflows, PyAV’s container/stream/frame model and time-base handling, OpenCV’s video/image-sequence I/O, and Manim’s scene-based programmatic animation model. ([Zulko][2])

Full machine-readable schema: [agnostic_video_project_schema.json](sandbox:/mnt/data/agnostic_video_project_schema.json)

Top-level layout of the schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/schemas/agnostic-video-project.schema.json",
  "type": "object",
  "required": [
    "schema_version",
    "project",
    "continuity_registry",
    "story_assets",
    "script_assets",
    "direction_assets",
    "scene_assets",
    "shot_assets",
    "visual_assets",
    "audio_assets",
    "marketing_assets",
    "assembly_assets",
    "workflow_steps",
    "final_output_assets",
    "relationships"
  ],
  "properties": {
    "schema_version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "project": { "$ref": "#/$defs/Project" },
    "continuity_registry": { "$ref": "#/$defs/ContinuityRegistry" },
    "story_assets": { "type": "array", "items": { "$ref": "#/$defs/StoryAsset" } },
    "script_assets": { "type": "array", "items": { "$ref": "#/$defs/ScriptAsset" } },
    "direction_assets": { "type": "array", "items": { "$ref": "#/$defs/DirectionAsset" } },
    "scene_assets": { "type": "array", "items": { "$ref": "#/$defs/SceneAsset" } },
    "shot_assets": { "type": "array", "items": { "$ref": "#/$defs/ShotAsset" } },
    "visual_assets": { "type": "array", "items": { "$ref": "#/$defs/VisualAsset" } },
    "audio_assets": { "type": "array", "items": { "$ref": "#/$defs/AudioAsset" } },
    "marketing_assets": { "type": "array", "items": { "$ref": "#/$defs/MarketingAsset" } },
    "assembly_assets": { "type": "array", "items": { "$ref": "#/$defs/AssemblyAsset" } },
    "workflow_steps": { "type": "array", "items": { "$ref": "#/$defs/WorkflowStep" } },
    "final_output_assets": { "type": "array", "items": { "$ref": "#/$defs/FinalOutputAsset" } },
    "validation_rules": { "type": "array", "items": { "$ref": "#/$defs/ValidationRule" } },
    "relationships": { "type": "array", "items": { "$ref": "#/$defs/Relationship" } },
    "extensions": { "type": "object", "additionalProperties": true }
  }
}
```

What the schema does:

* Every logical asset has a stable `asset_id`; every concrete revision lives in `versions[]` with an immutable `version_id`, lineage, representations, approvals, QC results, and generation metadata.
* Story, script, direction, scenes, shots, visuals, audio, marketing, assembly plans, and final outputs are all first-class managed asset types.
* Project-level and asset-level `QualityProfile` objects explicitly carry resolution, aspect ratio, frame rate, temporal consistency, character coherence, cinematic lighting, color grading, motion blur, loudness, and other measurable QC targets.
* Tool/model details are isolated in `GenerationSpec` and `GenerationRun`, with generic fields for prompts, negative prompts, seeds, anchors/conditioning, provider/model IDs, plus free-form `parameters`, `request_payload`, and `response_payload` so future tools fit without schema changes.
* Assembly is handled by `AssemblyAssetVersion` with `video_tracks`, `audio_tracks`, `subtitle_tracks`, `operations`, `stream_bindings`, `procedural_nodes`, and `render_profile`, which makes the same document usable for clip-based editing, stream-level processing, frame operations, or procedural animation.

The entity relationships are:

* `project` points to primary story/script/direction assets and establishes global quality/versioning policy.
* `story_assets` contain acts and beats; beats can point to scenes.
* `script_assets` contain timed `segments`; segments can point to scenes and shots.
* `scene_assets` hold ordered `shot_sequence` references.
* `shot_assets` define visual spec, audio plan, continuity references, and generation requirements.
* `visual_assets` and `audio_assets` hold source, reference, generated, intermediate, and deliverable media.
* `marketing_assets` derive from scenes, shots, outputs, or dedicated assembly plans.
* `assembly_assets` compose pinned asset versions into timelines.
* `final_output_assets` pin an assembly asset plus render profile and selected source versions.
* `workflow_steps` and `relationships` provide orchestration, provenance, dependency tracking, and reproducibility.

The versioning and dependency rules are:

1. `asset_id` is the stable logical identity. `version_id` is the immutable revision identity.
2. Any revision after the first should set `parent_version_id`; transforms and derivations should also populate `derived_from` and, when replacing another revision, `supersedes`.
3. Any assembly asset or final output should pin concrete `version_id` values for all source refs it depends on, not just logical `asset_id` values.
4. Approved revisions should be frozen (`is_frozen: true`) and accompanied by file-level checksums and content hashes.
5. `current_version_id` must match one of the asset’s defined versions.
6. JSON Schema should validate structure; a second referential-integrity pass should validate foreign keys, dangling `AssetPointer`s, cyclic dependency rules, and runtime constraints such as final outputs not exceeding the project maximum.

The most important extension points in the schema are `extensions`, `parameters`, `request_payload`, `response_payload`, `metadata`, and open string fields like `task_type`, `relationship_type`, `marketing_type`, `visual_type`, and `audio_type`. That is what keeps it tool-agnostic while still being strict enough for programmatic validation and rendering.

[1]: https://json-schema.org/specification "https://json-schema.org/specification"
[2]: https://zulko.github.io/moviepy/user_guide/index.html "https://zulko.github.io/moviepy/user_guide/index.html"


Here it is: [generative_video_project_package.schema.json](sandbox:/mnt/data/generative_video_project_package.schema.json)

It is a full Draft 2020-12 JSON Schema for a tool-agnostic video project package covering story, script, director guidance, scenes, shots, visual assets, audio assets, marketing assets, orchestration workflows, assembly timelines/render plans, relationships, and final deliverables. It also includes per-project and per-asset quality profiles, generative-AI step metadata, lineage/versioning, and runtime hints for MoviePy, Movis, OpenCV, PyAV, Manim, or any future renderer/orchestrator.

The key versioning and composition rules encoded by the schema are:

* `id` is the immutable versioned entity ID; `logicalId` is the stable conceptual asset ID across versions.
* `version.derivedFrom` and `version.supersedes` carry lineage for prompts, edits, renders, and derived assets.
* `EntityRef` supports exact references or selectors like `latestApproved`, `latestPublished`, `semverRange`, `tag`, and `branch`.
* `package.versioningPolicy` defines whether published assets are immutable, whether content hashes are required, and what reference mode is default.
* `renderPlan`, `timeline`, `editVersion`, and `finalOutput` are explicit first-class entities, so final videos can be programmatically assembled and reproduced.

The full schema file is the primary artifact. The top-level structure is:

```json
{
  "schemaVersion": "1.0.0",
  "package": { "...": "package metadata + versioning policy" },
  "project": { "...": "project metadata + default quality profile" },
  "qualityProfiles": [ "... reusable quality profiles ..." ],
  "canonicalDocuments": {
    "story": { "...": "narrative arc, beats, arcs" },
    "script": { "...": "dialogue, action, timing" },
    "directorInstructions": { "...": "creative direction + targeted notes" }
  },
  "production": {
    "characters": [ "... character bible/coherence ..." ],
    "environments": [ "... environment references ..." ],
    "props": [ "... continuity props ..." ],
    "scenes": [ "... scene-level planning ..." ],
    "shots": [ "... shot-level visual/technical/style specs ..." ]
  },
  "assetLibrary": {
    "visualAssets": [ "... storyboards, refs, images, videos, plates ..." ],
    "audioAssets": [ "... VO, music, SFX, stems ..." ],
    "marketingAssets": [ "... trailers, thumbnails, social clips ..." ],
    "genericAssets": [ "... LUTs, subtitles, fonts, custom artifacts ..." ]
  },
  "orchestration": {
    "workflows": [ "... DAG of generation/transform/approval/render nodes ..." ]
  },
  "assembly": {
    "timelines": [ "... track/clip based edit graphs ..." ],
    "editVersions": [ "... versioned edits ..." ],
    "renderPlans": [ "... operations + compatible runtimes ..." ]
  },
  "deliverables": [ "... final outputs + QC + publication metadata ..." ],
  "relationships": [ "... explicit graph edges across all entities ..." ],
  "extensions": { "... open-ended future fields ..." }
}
```

The file is intentionally extensible through `extensions`, `parameters`, `runtimeHints`, open-ended `operationType`, `visualType`, `audioType`, `marketingType`, and generic workflow executor metadata, so new AI tools and pipelines can be added without changing the schema itself.
