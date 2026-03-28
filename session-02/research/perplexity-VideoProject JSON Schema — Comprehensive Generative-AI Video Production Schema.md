# VideoProject JSON Schema
## Comprehensive Schema for Generative-AI Video Production, Assembly & Orchestration

> **v1.0 — Reference document.** The production-ready, fully enhanced schema is **[video-project-schema-v2.json](./video-project-schema-v2.json)** (v2.0.0), which extends this document with: cost tracking, retry/async logic, rights management, collaborative workflow (roles, comments, approval chains), QA gates, prompt versioning, platform delivery, localization, and accessibility. The terminology used here is formally defined in **[term-map.json](./term-map.json)**.

---
## 1. Design Principles & Architecture
This schema is structured around five foundational principles derived from research into generative-AI video pipelines, post-production workflows, and JSON Schema best practices:[^1][^2][^3]

1. **Tool-agnosticism via open `params` envelopes** — every generative node carries a freeform `gen_params` object alongside typed fields, ensuring future models plug in without schema changes.
2. **Asset-First decomposition** — characters and environments are defined once in a registry and referenced by `$id` throughout, mirroring the "visual anchoring" mechanism proven essential for cross-scene character consistency (dropping it reduces consistency scores from 7.99 to 0.55).[^3]
3. **Temporal Bridge pattern** — each scene explicitly references the `anchor_frame` (last generated frame) of its predecessor, enabling visual conditioning between clips.[^3]
4. **Semantic versioning on every entity** — using URI-based `$id` keys and a `schema_version` field as recommended by JSON Schema maintainers.[^2][^4]
5. **Programmatic assembly metadata** — every clip carries native fields consumed directly by MoviePy, Movis, OpenCV, PyAV, and Manim without intermediate translation.[^5][^6]

### v2.0 Additions (see video-project-schema-v2.json)
Six additional design principles were added in v2.0:

6. **Cost-aware generation** — every `gen_params` node carries `cost` (estimated + actual USD, tokens, GPU seconds, provider job ID) and `attempts[]` for full retry audit trails.
7. **Resilient async orchestration** — `retry_config` (max attempts, backoff, fallback tool) and `async_config` (webhook URL, events, timeout) enable robust long-running generation pipelines.
8. **Rights-first asset management** — every asset carries a `rights` object (source, license type/URL, expiry, talent release, territory) to prevent downstream IP violations.
9. **Collaborative review workflow** — `team` (roles + permissions), `comments[]` (timecoded annotations with threading), and `approval_chain[]` (per-role decisions with deadlines) on every entity.
10. **Quality-gated assembly** — `qa_gate` on every scene and shot with required checks, pass thresholds, and per-check scores; `validation_result` on the render pipeline.
11. **Multi-platform delivery** — `platform_deliveries[]` on outputs (YouTube, TikTok, Instagram, broadcast, etc.), `localization` (subtitle + dubbed audio tracks), and `accessibility` (WCAG level, captions, audio descriptions).

***
## 2. Entity-Relationship Overview
```
VideoProject
├── project_meta          (identity, quality specs, delivery targets)
├── story                 (narrative arc, acts, beats)
├── script                (lines, action descriptions, timing)
├── director_notes        (creative direction, style, quality rules)
├── asset_registry
│   ├── characters[]      (visual sheets, consistency anchors)
│   ├── environments[]    (location references)
│   ├── props[]           (object references)
│   └── style_guides[]    (color, mood, lighting)
├── scenes[]
│   └── shots[]           (per-shot visual + gen_params + assembly)
├── audio_assets[]        (voice-over, music, SFX + sync metadata)
├── visual_assets[]       (images, storyboards, references)
├── marketing_materials[] (trailers, thumbnails, social clips)
├── render_pipeline       (assembly instructions, tool bindings)
└── outputs[]             (versioned final renders)
```

Relationships are expressed via `$ref`-style `id` strings so any processor can resolve them without a database.[^4][^7]

***
## 3. Full JSON Schema Definition
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.vidproject.io/video-project/1.0.0",
  "title": "VideoProject",
  "description": "Comprehensive schema for generative-AI video production up to 30 minutes. Tool-agnostic and fully extensible.",
  "type": "object",
  "required": ["schema_version", "project_meta", "story", "script", "asset_registry", "scenes"],
  "additionalProperties": false,

  "$defs": {

    "SemVer": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(-[a-zA-Z0-9.]+)?(\\+[a-zA-Z0-9.]+)?$",
      "description": "Semantic version string e.g. '1.0.0', '2.3.1-rc.1'"
    },

    "ISOTimestamp": {
      "type": "string",
      "format": "date-time"
    },

    "UUID": {
      "type": "string",
      "format": "uuid"
    },

    "AssetRef": {
      "type": "object",
      "description": "Pointer to any registered asset by its UUID and type.",
      "required": ["id", "type"],
      "properties": {
        "id":   { "$ref": "#/$defs/UUID" },
        "type": {
          "type": "string",
          "enum": ["character","environment","prop","style_guide",
                   "visual_asset","audio_asset","shot","scene","output"]
        },
        "label": { "type": "string" }
      }
    },

    "FileLocator": {
      "type": "object",
      "description": "Resolves a file from local path, remote URL, or object-storage URI.",
      "required": ["uri"],
      "properties": {
        "uri":       { "type": "string", "format": "uri" },
        "mime_type": { "type": "string" },
        "checksum":  { "type": "string", "description": "SHA-256 hex digest" },
        "size_bytes":{ "type": "integer", "minimum": 0 }
      },
      "additionalProperties": false
    },

    "VersionRecord": {
      "type": "object",
      "required": ["version", "created_at", "author"],
      "properties": {
        "version":    { "$ref": "#/$defs/SemVer" },
        "created_at": { "$ref": "#/$defs/ISOTimestamp" },
        "author":     { "type": "string" },
        "change_log": { "type": "string" },
        "parent_version": { "$ref": "#/$defs/SemVer" }
      },
      "additionalProperties": false
    },

    "QualitySpec": {
      "type": "object",
      "description": "Reusable quality specification applicable at project or asset level.",
      "properties": {
        "resolution": {
          "type": "object",
          "properties": {
            "preset":  { "type": "string", "enum": ["4K","2K","1080p","720p","480p","custom"] },
            "width_px":  { "type": "integer", "minimum": 1 },
            "height_px": { "type": "integer", "minimum": 1 }
          },
          "additionalProperties": false
        },
        "aspect_ratio": {
          "type": "object",
          "properties": {
            "preset":  { "type": "string", "enum": ["16:9","9:16","1:1","4:3","2.35:1","2.39:1","custom"] },
            "width":   { "type": "number" },
            "height":  { "type": "number" }
          },
          "additionalProperties": false
        },
        "frame_rate": {
          "type": "object",
          "properties": {
            "fps":    { "type": "number", "enum": [23.976, 24, 25, 29.97, 30, 48, 59.94, 60, 120] },
            "custom_fps": { "type": "number", "exclusiveMinimum": 0 }
          },
          "additionalProperties": false
        },
        "color_space":    { "type": "string", "enum": ["sRGB","Rec.709","Rec.2020","DCI-P3","custom"] },
        "bit_depth":      { "type": "integer", "enum": [8, 10, 12, 16] },
        "hdr_format":     { "type": "string", "enum": ["SDR","HDR10","HLG","Dolby Vision","none"] },
        "codec_video":    { "type": "string", "examples": ["H.264","H.265","VP9","AV1","ProRes 422","ProRes 4444"] },
        "codec_audio":    { "type": "string", "examples": ["AAC","PCM","FLAC","Opus"] },
        "bitrate_video_mbps": { "type": "number", "exclusiveMinimum": 0 },
        "bitrate_audio_kbps": { "type": "number", "exclusiveMinimum": 0 },
        "motion_blur":    { "type": "boolean" },
        "motion_blur_shutter_angle": { "type": "number", "minimum": 0, "maximum": 360 },
        "grain_level":    { "type": "string", "enum": ["none","subtle","medium","heavy"] }
      },
      "additionalProperties": false
    },

    "ColorGrade": {
      "type": "object",
      "description": "LUT and color-grading parameters usable by DaVinci Resolve, FFmpeg, MoviePy, or OpenCV.",
      "properties": {
        "lut_file":    { "$ref": "#/$defs/FileLocator" },
        "lut_strength": { "type": "number", "minimum": 0, "maximum": 1 },
        "brightness":   { "type": "number", "minimum": -1, "maximum": 1 },
        "contrast":     { "type": "number", "minimum": -1, "maximum": 1 },
        "saturation":   { "type": "number", "minimum": -1, "maximum": 1 },
        "temperature_k":{ "type": "number", "minimum": 1000, "maximum": 20000 },
        "tint":         { "type": "number", "minimum": -1, "maximum": 1 },
        "shadows":      { "type": "number", "minimum": -1, "maximum": 1 },
        "midtones":     { "type": "number", "minimum": -1, "maximum": 1 },
        "highlights":   { "type": "number", "minimum": -1, "maximum": 1 },
        "vignette":     { "type": "number", "minimum": 0, "maximum": 1 }
      },
      "additionalProperties": false
    },

    "GenParams": {
      "type": "object",
      "description": "Universal generative-AI parameters envelope. Typed fields cover common properties; 'extra' is a freeform bag for tool-specific parameters (e.g. Runway, Kling, Luma, Pika, ElevenLabs, Midjourney, SD, Manim, etc.).",
      "properties": {
        "tool":          { "type": "string", "description": "Tool identifier e.g. 'runway-gen4', 'kling-v3.0', 'luma-dream-machine-1.6', 'pika-2.2', 'midjourney-v7', 'stable-diffusion-xl-1.0', 'elevenlabs-multilingual-v2', 'manim-ce-0.18', 'comfyui'" },
        "model_id":      { "type": "string", "description": "Model name or HuggingFace path" },
        "model_version": { "type": "string" },
        "api_endpoint":  { "type": "string", "format": "uri" },
        "prompt":        { "type": "string" },
        "negative_prompt":{ "type": "string" },
        "seed":          { "type": "integer", "description": "Deterministic seed for reproducibility" },
        "cfg_scale":     { "type": "number", "minimum": 0, "description": "Classifier-free guidance scale" },
        "steps":         { "type": "integer", "minimum": 1 },
        "sampler":       { "type": "string" },
        "scheduler":     { "type": "string" },
        "strength":      { "type": "number", "minimum": 0, "maximum": 1, "description": "Img2img / I2V denoising strength" },
        "duration_sec":  { "type": "number", "minimum": 0 },
        "consistency_anchors": {
          "type": "array",
          "description": "Reference assets used to lock visual identity (IP-Adapter, ControlNet, Runway reference images, Kling Identity-Lock, etc.)",
          "items": {
            "type": "object",
            "required": ["asset_ref","role"],
            "properties": {
              "asset_ref": { "$ref": "#/$defs/AssetRef" },
              "role": {
                "type": "string",
                "enum": ["character","style","scene","subject","ip_adapter","controlnet","depth_map","pose","face_id","temporal_bridge_frame","custom"]
              },
              "adapter_type": { "type": "string", "description": "e.g. 'ip-adapter-plus-face', 'controlnet-openpose'" },
              "weight":       { "type": "number", "minimum": 0, "maximum": 1 }
            },
            "additionalProperties": false
          }
        },
        "lora": {
          "type": "array",
          "description": "LoRA weights to load",
          "items": {
            "type": "object",
            "required": ["path","weight"],
            "properties": {
              "path":   { "$ref": "#/$defs/FileLocator" },
              "weight": { "type": "number" }
            },
            "additionalProperties": false
          }
        },
        "camera_motion": {
          "type": "object",
          "description": "Camera movement directives for models supporting them (Runway Gen-4, Kling Motion Control 2.6, etc.)",
          "properties": {
            "move_type": { "type": "string", "enum": ["static","pan_left","pan_right","tilt_up","tilt_down","zoom_in","zoom_out","dolly_in","dolly_out","truck_left","truck_right","crane_up","crane_down","arc_left","arc_right","handheld","custom"] },
            "speed":     { "type": "string", "enum": ["ultra_slow","slow","moderate","fast","snap"] },
            "duration_sec": { "type": "number", "minimum": 0 },
            "custom_path_uri": { "type": "string", "format": "uri", "description": "3D camera path file (e.g. Runway precision director path)" }
          },
          "additionalProperties": false
        },
        "sound_generation": {
          "type": "object",
          "description": "Native audio synthesis flags (e.g. Kling 3.0 spatial audio, ElevenLabs voice params)",
          "properties": {
            "enabled":     { "type": "boolean" },
            "lip_sync":    { "type": "boolean" },
            "voice_id":    { "type": "string" },
            "voice_stability":   { "type": "number", "minimum": 0, "maximum": 1 },
            "voice_similarity":  { "type": "number", "minimum": 0, "maximum": 1 },
            "voice_style":       { "type": "number", "minimum": 0, "maximum": 1 },
            "voice_use_speaker_boost": { "type": "boolean" }
          },
          "additionalProperties": false
        },
        "extra": {
          "type": "object",
          "description": "Freeform bag for any tool-specific or future parameters not yet typed in this schema.",
          "additionalProperties": true
        }
      },
      "additionalProperties": false
    },

    "TemporalConsistency": {
      "type": "object",
      "description": "Requirements and enforcement controls for cross-shot and cross-scene consistency.",
      "properties": {
        "character_coherence_min_score": {
          "type": "number", "minimum": 0, "maximum": 10,
          "description": "Minimum DINO cosine similarity score threshold for character identity (0-10 scale). Research baseline: 7.99 for full-pipeline."
        },
        "world_consistency_min_score":  { "type": "number", "minimum": 0, "maximum": 1 },
        "temporal_bridge_enabled":      { "type": "boolean", "description": "Condition each scene's first frame on the last frame of the previous scene." },
        "optical_flow_validation":      { "type": "boolean" },
        "max_dynamic_degree":           { "type": "number", "minimum": 0, "description": "Optical flow magnitude ceiling for motion stress control." },
        "face_consistency_required":    { "type": "boolean" },
        "clothing_consistency_required":{ "type": "boolean" },
        "style_consistency_required":   { "type": "boolean" }
      },
      "additionalProperties": false
    },

    "CinematicSpec": {
      "type": "object",
      "description": "Visual and directorial specification for a shot or scene.",
      "properties": {
        "shot_type":    { "type": "string", "enum": ["extreme_wide","wide","medium_wide","medium","medium_close","close_up","extreme_close_up","aerial","pov","over_the_shoulder","two_shot","insert","cutaway"] },
        "lens_focal_mm":{ "type": "number", "exclusiveMinimum": 0 },
        "aperture_f":   { "type": "number", "exclusiveMinimum": 0 },
        "depth_of_field":{ "type": "string", "enum": ["shallow","medium","deep"] },
        "lighting_style":{ "type": "string", "examples": ["golden_hour","blue_hour","high_key","low_key","rembrandt","practical_lights","neon","overcast","hard_noon","candlelight"] },
        "lighting_direction": { "type": "string", "enum": ["front","45_front","side","backlit","top","bottom","rim"] },
        "color_palette":   { "type": "array", "items": { "type": "string", "description": "CSS hex color e.g. '#2A3D6B'" } },
        "mood":            { "type": "string" },
        "film_grain":      { "type": "string", "enum": ["none","subtle","medium","heavy"] },
        "lens_flare":      { "type": "boolean" },
        "anamorphic":      { "type": "boolean" },
        "vfx_notes":       { "type": "string" },
        "manim_config": {
          "type": "object",
          "description": "Manim-specific rendering config for animated/data-visualization shots.",
          "properties": {
            "background_color": { "type": "string" },
            "pixel_height":     { "type": "integer" },
            "pixel_width":      { "type": "integer" },
            "frame_rate":       { "type": "number" },
            "scene_class":      { "type": "string", "description": "Python class name of the Manim Scene to render" },
            "quality":          { "type": "string", "enum": ["low_quality","medium_quality","high_quality","production_quality"] }
          },
          "additionalProperties": false
        }
      },
      "additionalProperties": false
    },

    "AssemblyInstruction": {
      "type": "object",
      "description": "Instructions consumed by MoviePy, Movis, OpenCV, or PyAV during programmatic assembly.",
      "properties": {
        "clip_in_sec":   { "type": "number", "minimum": 0 },
        "clip_out_sec":  { "type": "number", "minimum": 0 },
        "timeline_in_sec":{ "type": "number", "minimum": 0 },
        "timeline_out_sec":{ "type": "number" },
        "layer":         { "type": "integer", "minimum": 0, "description": "Z-order layer, 0 = base" },
        "transition_in": {
          "type": "object",
          "properties": {
            "type":       { "type": "string", "enum": ["cut","dissolve","fade_in","fade_from_black","wipe_left","wipe_right","cross_zoom","dip_to_black","custom"] },
            "duration_sec":{ "type": "number", "minimum": 0 }
          },
          "additionalProperties": false
        },
        "transition_out": {
          "type": "object",
          "properties": {
            "type":       { "type": "string", "enum": ["cut","dissolve","fade_out","fade_to_black","wipe_left","wipe_right","cross_zoom","dip_to_black","custom"] },
            "duration_sec":{ "type": "number", "minimum": 0 }
          },
          "additionalProperties": false
        },
        "speed_factor":  { "type": "number", "exclusiveMinimum": 0, "description": "1.0 = normal; 0.5 = half speed; 2.0 = double speed" },
        "reverse":       { "type": "boolean" },
        "crop": {
          "type": "object",
          "properties": {
            "x1": { "type": "number" }, "y1": { "type": "number" },
            "x2": { "type": "number" }, "y2": { "type": "number" }
          },
          "additionalProperties": false
        },
        "resize": {
          "type": "object",
          "properties": {
            "width":  { "type": "integer" },
            "height": { "type": "integer" },
            "method": { "type": "string", "enum": ["lanczos","bilinear","bicubic","nearest"] }
          },
          "additionalProperties": false
        },
        "opacity":      { "type": "number", "minimum": 0, "maximum": 1 },
        "color_grade":  { "$ref": "#/$defs/ColorGrade" },
        "opencv_filters": {
          "type": "array",
          "description": "List of OpenCV filter pipelines to apply frame-by-frame.",
          "items": { "type": "string", "description": "Filter descriptor, e.g. 'bilateral_filter(d=9,sigmaColor=75)'" }
        },
        "pyav_stream_params": {
          "type": "object",
          "description": "PyAV muxing/demuxing overrides (codec, bitrate, etc.)",
          "additionalProperties": true
        }
      },
      "additionalProperties": false
    },

    "Character": {
      "type": "object",
      "required": ["id","name","physical_description"],
      "properties": {
        "id":   { "$ref": "#/$defs/UUID" },
        "name": { "type": "string" },
        "role": { "type": "string", "enum": ["protagonist","antagonist","supporting","narrator","background","custom"] },
        "physical_description": { "type": "string" },
        "visual_notes":   { "type": "string", "description": "Costume, distinctive features, style anchors" },
        "personality":    { "type": "string" },
        "arc":            { "type": "string", "description": "Character's arc across the story" },
        "reference_images": {
          "type": "array",
          "description": "Character sheet images (front, side, back, expressions). Used as consistency anchors.",
          "items": { "$ref": "#/$defs/FileLocator" }
        },
        "voice_ref": { "$ref": "#/$defs/AssetRef", "description": "Reference to an AudioAsset defining voice characteristics" },
        "gen_params":    { "$ref": "#/$defs/GenParams" },
        "versions":      { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata":      { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "Environment": {
      "type": "object",
      "required": ["id","name","description"],
      "properties": {
        "id":          { "$ref": "#/$defs/UUID" },
        "name":        { "type": "string" },
        "description": { "type": "string" },
        "time_of_day": { "type": "string" },
        "weather":     { "type": "string" },
        "reference_images": {
          "type": "array",
          "items": { "$ref": "#/$defs/FileLocator" }
        },
        "gen_params":  { "$ref": "#/$defs/GenParams" },
        "versions":    { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata":    { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "Prop": {
      "type": "object",
      "required": ["id","name"],
      "properties": {
        "id":          { "$ref": "#/$defs/UUID" },
        "name":        { "type": "string" },
        "description": { "type": "string" },
        "reference_images": {
          "type": "array",
          "items": { "$ref": "#/$defs/FileLocator" }
        },
        "gen_params":  { "$ref": "#/$defs/GenParams" },
        "metadata":    { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "StyleGuide": {
      "type": "object",
      "required": ["id","name"],
      "properties": {
        "id":            { "$ref": "#/$defs/UUID" },
        "name":          { "type": "string" },
        "art_style":     { "type": "string", "description": "e.g. 'Gritty Epic CGI', 'Pixar 3D', 'Film Noir', 'Anime'" },
        "visual_references": {
          "type": "array",
          "description": "Reference films, artworks, or images",
          "items": { "type": "string" }
        },
        "color_palette": { "type": "array", "items": { "type": "string" } },
        "negative_style_prompt": { "type": "string" },
        "lighting_default": { "type": "string" },
        "cinematic_spec": { "$ref": "#/$defs/CinematicSpec" },
        "metadata":       { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "VisualAsset": {
      "type": "object",
      "required": ["id","type","file"],
      "properties": {
        "id":    { "$ref": "#/$defs/UUID" },
        "type":  { "type": "string", "enum": ["image","storyboard_frame","character_sheet","environment_ref","prop_ref","concept_art","thumbnail","promotional_still"] },
        "label": { "type": "string" },
        "file":  { "$ref": "#/$defs/FileLocator" },
        "quality_spec": { "$ref": "#/$defs/QualitySpec" },
        "gen_params":   { "$ref": "#/$defs/GenParams" },
        "references":   { "type": "array", "items": { "$ref": "#/$defs/AssetRef" } },
        "versions":     { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "tags":         { "type": "array", "items": { "type": "string" } },
        "metadata":     { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "AudioAsset": {
      "type": "object",
      "required": ["id","type"],
      "properties": {
        "id":        { "$ref": "#/$defs/UUID" },
        "type":      { "type": "string", "enum": ["voice_over","dialogue","music","sfx","ambient","foley"] },
        "label":     { "type": "string" },
        "file":      { "$ref": "#/$defs/FileLocator" },
        "transcript":{ "type": "string" },
        "language":  { "type": "string", "description": "BCP-47 language tag e.g. 'en-US'" },
        "sync": {
          "type": "object",
          "description": "Synchronisation anchor to the timeline",
          "properties": {
            "timeline_in_sec":  { "type": "number", "minimum": 0 },
            "timeline_out_sec": { "type": "number", "minimum": 0 },
            "shot_ref":    { "$ref": "#/$defs/AssetRef" },
            "beat_offset_sec": { "type": "number" },
            "loop":        { "type": "boolean" },
            "fade_in_sec": { "type": "number", "minimum": 0 },
            "fade_out_sec":{ "type": "number", "minimum": 0 }
          },
          "additionalProperties": false
        },
        "gen_params": { "$ref": "#/$defs/GenParams" },
        "versions":   { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "tags":       { "type": "array", "items": { "type": "string" } },
        "metadata":   { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "ScriptLine": {
      "type": "object",
      "required": ["id","line_type"],
      "properties": {
        "id":        { "$ref": "#/$defs/UUID" },
        "line_type": { "type": "string", "enum": ["dialogue","action","direction","title_card","caption","transition","parenthetical"] },
        "character_ref": { "$ref": "#/$defs/AssetRef" },
        "text":      { "type": "string" },
        "timing": {
          "type": "object",
          "properties": {
            "start_sec": { "type": "number", "minimum": 0 },
            "end_sec":   { "type": "number", "minimum": 0 },
            "duration_sec": { "type": "number", "minimum": 0 }
          },
          "additionalProperties": false
        },
        "notes":     { "type": "string" },
        "metadata":  { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "Shot": {
      "type": "object",
      "description": "Atomic generative unit. Each shot maps 1:1 to a generative API call and an assembly clip.",
      "required": ["id","shot_number","duration_sec"],
      "properties": {
        "id":           { "$ref": "#/$defs/UUID" },
        "shot_number":  { "type": "integer", "minimum": 1 },
        "label":        { "type": "string" },
        "duration_sec": { "type": "number", "exclusiveMinimum": 0, "maximum": 120 },
        "script_lines": {
          "type": "array",
          "items": { "$ref": "#/$defs/AssetRef" }
        },
        "characters_present": {
          "type": "array",
          "items": { "$ref": "#/$defs/AssetRef" }
        },
        "environment_ref": { "$ref": "#/$defs/AssetRef" },
        "props_present": {
          "type": "array",
          "items": { "$ref": "#/$defs/AssetRef" }
        },
        "action_description": { "type": "string" },
        "cinematic_spec": { "$ref": "#/$defs/CinematicSpec" },
        "quality_spec":   { "$ref": "#/$defs/QualitySpec" },
        "temporal_consistency": { "$ref": "#/$defs/TemporalConsistency" },
        "anchor_frame": {
          "type": "object",
          "description": "Temporal Bridge: first frame seed for this shot. Typically the last frame of the preceding shot.",
          "properties": {
            "file":           { "$ref": "#/$defs/FileLocator" },
            "source_shot_id": { "$ref": "#/$defs/UUID" },
            "auto_extract":   { "type": "boolean", "description": "If true, pipeline extracts last frame of source_shot_id automatically." }
          },
          "additionalProperties": false
        },
        "gen_params":     { "$ref": "#/$defs/GenParams" },
        "output_file":    { "$ref": "#/$defs/FileLocator" },
        "assembly":       { "$ref": "#/$defs/AssemblyInstruction" },
        "audio_assets": {
          "type": "array",
          "items": { "$ref": "#/$defs/AssetRef" }
        },
        "status": {
          "type": "string",
          "enum": ["pending","generating","review","approved","rejected","assembled"]
        },
        "versions":  { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata":  { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "Scene": {
      "type": "object",
      "required": ["id","scene_number","title","shots"],
      "properties": {
        "id":           { "$ref": "#/$defs/UUID" },
        "scene_number": { "type": "integer", "minimum": 1 },
        "title":        { "type": "string" },
        "act_ref":      { "type": "string", "description": "e.g. 'act_1', 'act_2'" },
        "description":  { "type": "string" },
        "setting":      { "type": "string" },
        "time_of_day":  { "type": "string" },
        "emotional_tone":{ "type": "string" },
        "style_guide_ref": { "$ref": "#/$defs/AssetRef" },
        "temporal_consistency": { "$ref": "#/$defs/TemporalConsistency" },
        "shots": {
          "type": "array",
          "items": { "$ref": "#/$defs/Shot" },
          "minItems": 1
        },
        "duration_sec": { "type": "number", "minimum": 0, "description": "Computed; equals sum of shot durations" },
        "audio_assets": {
          "type": "array",
          "items": { "$ref": "#/$defs/AssetRef" }
        },
        "dependencies": {
          "type": "array",
          "description": "IDs of scenes that must be rendered before this one (e.g. for temporal bridge).",
          "items": { "$ref": "#/$defs/UUID" }
        },
        "storyboard": {
          "type": "array",
          "items": { "$ref": "#/$defs/AssetRef" }
        },
        "versions":  { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata":  { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "MarketingMaterial": {
      "type": "object",
      "required": ["id","type"],
      "properties": {
        "id":    { "$ref": "#/$defs/UUID" },
        "type":  { "type": "string", "enum": ["trailer","teaser","thumbnail","promotional_still","social_clip","chapter_preview","behind_the_scenes","custom"] },
        "label": { "type": "string" },
        "target_platform": {
          "type": "array",
          "items": { "type": "string", "enum": ["youtube","instagram","tiktok","twitter_x","linkedin","facebook","website","broadcast","custom"] }
        },
        "quality_spec":   { "$ref": "#/$defs/QualitySpec" },
        "file":           { "$ref": "#/$defs/FileLocator" },
        "source_shot_refs": {
          "type": "array",
          "description": "Shots from which this material is derived.",
          "items": { "$ref": "#/$defs/AssetRef" }
        },
        "assembly":       { "$ref": "#/$defs/AssemblyInstruction" },
        "gen_params":     { "$ref": "#/$defs/GenParams" },
        "copy_text":      { "type": "string", "description": "Headline, caption or call-to-action text" },
        "versions":       { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata":       { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "RenderOutput": {
      "type": "object",
      "required": ["id","version","quality_spec"],
      "properties": {
        "id":           { "$ref": "#/$defs/UUID" },
        "version":      { "$ref": "#/$defs/SemVer" },
        "label":        { "type": "string" },
        "file":         { "$ref": "#/$defs/FileLocator" },
        "quality_spec": { "$ref": "#/$defs/QualitySpec" },
        "color_grade":  { "$ref": "#/$defs/ColorGrade" },
        "assembly_tool":{ "type": "string", "enum": ["moviepy","movis","opencv","pyav","manim","ffmpeg","custom"] },
        "assembly_script": { "$ref": "#/$defs/FileLocator", "description": "Path to the assembly script that produced this render." },
        "scene_order": {
          "type": "array",
          "description": "Ordered list of scene IDs as assembled in this output.",
          "items": { "$ref": "#/$defs/UUID" }
        },
        "total_duration_sec": { "type": "number", "minimum": 0, "maximum": 1800 },
        "rendered_at":    { "$ref": "#/$defs/ISOTimestamp" },
        "parent_version": { "$ref": "#/$defs/SemVer" },
        "change_log":     { "type": "string" },
        "validation": {
          "type": "object",
          "properties": {
            "character_consistency_score": { "type": "number" },
            "world_consistency_score":     { "type": "number" },
            "prompt_adherence_score":      { "type": "number" },
            "script_adherence_score":      { "type": "number" },
            "quality_check_passed":        { "type": "boolean" },
            "validator_notes":             { "type": "string" }
          },
          "additionalProperties": false
        },
        "metadata": { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    }
  },

  "properties": {

    "schema_version": {
      "$ref": "#/$defs/SemVer",
      "description": "Version of THIS schema document (URI-based identity via $id)."
    },

    "project_meta": {
      "type": "object",
      "required": ["id","title","created_at"],
      "properties": {
        "id":          { "$ref": "#/$defs/UUID" },
        "title":       { "type": "string" },
        "logline":     { "type": "string", "maxLength": 500 },
        "genre":       { "type": "array", "items": { "type": "string" } },
        "target_audience": { "type": "string" },
        "platform":    { "type": "array", "items": { "type": "string" } },
        "created_at":  { "$ref": "#/$defs/ISOTimestamp" },
        "updated_at":  { "$ref": "#/$defs/ISOTimestamp" },
        "authors":     { "type": "array", "items": { "type": "string" } },
        "tags":        { "type": "array", "items": { "type": "string" } },
        "project_quality_spec": {
          "$ref": "#/$defs/QualitySpec",
          "description": "Default quality specification for all assets and outputs. Can be overridden per-shot."
        },
        "max_duration_sec": {
          "type": "number",
          "maximum": 1800,
          "description": "Hard cap of 1800 seconds (30 minutes) enforced at validation time."
        },
        "default_style_guide": { "$ref": "#/$defs/AssetRef" },
        "versions": { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } }
      },
      "additionalProperties": false
    },

    "story": {
      "type": "object",
      "required": ["id","synopsis","acts"],
      "properties": {
        "id":       { "$ref": "#/$defs/UUID" },
        "synopsis": { "type": "string" },
        "theme":    { "type": "string" },
        "tone":     { "type": "string" },
        "acts": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["act_id","label"],
            "properties": {
              "act_id":      { "type": "string" },
              "label":       { "type": "string" },
              "description": { "type": "string" },
              "beats": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["beat_id","description"],
                  "properties": {
                    "beat_id":     { "type": "string" },
                    "description": { "type": "string" },
                    "scene_refs":  { "type": "array", "items": { "$ref": "#/$defs/AssetRef" } }
                  },
                  "additionalProperties": false
                }
              }
            },
            "additionalProperties": false
          }
        },
        "versions": { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata": { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "script": {
      "type": "object",
      "required": ["id","lines"],
      "properties": {
        "id":         { "$ref": "#/$defs/UUID" },
        "format":     { "type": "string", "enum": ["screenplay","vlog","documentary","explainer","custom"] },
        "total_pages":{ "type": "number" },
        "lines": {
          "type": "array",
          "items": { "$ref": "#/$defs/ScriptLine" },
          "minItems": 1
        },
        "versions":   { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata":   { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "director_notes": {
      "type": "object",
      "required": ["id"],
      "properties": {
        "id":                  { "$ref": "#/$defs/UUID" },
        "overall_vision":      { "type": "string" },
        "creative_direction":  { "type": "string" },
        "style_guide_ref":     { "$ref": "#/$defs/AssetRef" },
        "quality_rules": {
          "type": "array",
          "description": "Mandatory quality rules applied to every asset before approval.",
          "items": {
            "type": "object",
            "required": ["rule_id","description"],
            "properties": {
              "rule_id":      { "type": "string" },
              "description":  { "type": "string" },
              "enforcement":  { "type": "string", "enum": ["hard_block","warning","log_only"] },
              "applies_to":   { "type": "array", "items": { "type": "string" } }
            },
            "additionalProperties": false
          }
        },
        "global_negative_prompt": { "type": "string", "description": "Negative prompt appended to every generative call." },
        "global_style_prompt":    { "type": "string" },
        "temporal_consistency":   { "$ref": "#/$defs/TemporalConsistency" },
        "forbidden_elements":     { "type": "array", "items": { "type": "string" } },
        "versions":  { "type": "array", "items": { "$ref": "#/$defs/VersionRecord" } },
        "metadata":  { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "asset_registry": {
      "type": "object",
      "required": ["id"],
      "properties": {
        "id":          { "$ref": "#/$defs/UUID" },
        "characters":  { "type": "array", "items": { "$ref": "#/$defs/Character" } },
        "environments":{ "type": "array", "items": { "$ref": "#/$defs/Environment" } },
        "props":       { "type": "array", "items": { "$ref": "#/$defs/Prop" } },
        "style_guides":{ "type": "array", "items": { "$ref": "#/$defs/StyleGuide" } }
      },
      "additionalProperties": false
    },

    "visual_assets": {
      "type": "array",
      "items": { "$ref": "#/$defs/VisualAsset" }
    },

    "audio_assets": {
      "type": "array",
      "items": { "$ref": "#/$defs/AudioAsset" }
    },

    "scenes": {
      "type": "array",
      "items": { "$ref": "#/$defs/Scene" },
      "minItems": 1
    },

    "marketing_materials": {
      "type": "array",
      "items": { "$ref": "#/$defs/MarketingMaterial" }
    },

    "render_pipeline": {
      "type": "object",
      "required": ["id"],
      "description": "Top-level orchestration contract for the assembly pipeline.",
      "properties": {
        "id":              { "$ref": "#/$defs/UUID" },
        "primary_tool":    { "type": "string", "enum": ["moviepy","movis","opencv","pyav","manim","ffmpeg","custom"] },
        "fallback_tool":   { "type": "string" },
        "pipeline_script": { "$ref": "#/$defs/FileLocator" },
        "environment_file":{ "$ref": "#/$defs/FileLocator", "description": "requirements.txt or environment.yml" },
        "execution_order": {
          "type": "array",
          "description": "Topologically sorted list of scene IDs for rendering.",
          "items": { "$ref": "#/$defs/UUID" }
        },
        "parallelism": {
          "type": "object",
          "properties": {
            "max_concurrent_jobs": { "type": "integer", "minimum": 1 },
            "gpu_required":        { "type": "boolean" },
            "min_vram_gb":         { "type": "number" }
          },
          "additionalProperties": false
        },
        "post_processing": {
          "type": "object",
          "properties": {
            "global_color_grade": { "$ref": "#/$defs/ColorGrade" },
            "audio_mix_preset":   { "type": "string", "enum": ["stereo","5.1","7.1","atmos","mono","custom"] },
            "subtitles_file":     { "$ref": "#/$defs/FileLocator" },
            "watermark": {
              "type": "object",
              "properties": {
                "file":     { "$ref": "#/$defs/FileLocator" },
                "position": { "type": "string", "enum": ["top_left","top_right","bottom_left","bottom_right","center"] },
                "opacity":  { "type": "number", "minimum": 0, "maximum": 1 }
              },
              "additionalProperties": false
            }
          },
          "additionalProperties": false
        },
        "delivery_targets": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["target_id","platform","quality_spec"],
            "properties": {
              "target_id":    { "type": "string" },
              "platform":     { "type": "string" },
              "quality_spec": { "$ref": "#/$defs/QualitySpec" },
              "color_grade":  { "$ref": "#/$defs/ColorGrade" },
              "output_path":  { "type": "string" }
            },
            "additionalProperties": false
          }
        },
        "metadata": { "type": "object", "additionalProperties": true }
      },
      "additionalProperties": false
    },

    "outputs": {
      "type": "array",
      "description": "Versioned final renders. A new entry is appended on every re-render.",
      "items": { "$ref": "#/$defs/RenderOutput" }
    }
  }
}
```

***
## 4. Key Design Decisions
### 4.1 Tool-Agnosticism
The `gen_params` object appears on every generative asset (characters, environments, shots, audio, marketing materials). Its `tool` and `model_id` strings accept any present or future identifier — `"runway-gen4"`, `"kling-v3.0-std"`, `"luma-dream-machine-1.6"`, `"elevenlabs-multilingual-v2"`, `"manim-ce-0.18"`, or any future model — without schema modification. The `extra` bag absorbs arbitrarily deep tool-specific parameters not yet typed.[^8][^9][^10]
### 4.2 Temporal Bridge & Character Consistency
Research confirms that removing the visual seed frame from a generative pipeline reduces character consistency from 7.99 to 0.55 on a 0–10 scale. The `anchor_frame` field on every `Shot`, combined with the `temporal_consistency` object (including `temporal_bridge_enabled`, `character_coherence_min_score`, and `face_consistency_required`), provides machine-enforced controls for this requirement. The `consistency_anchors` array within `gen_params` maps to Runway Gen-4's reference image system (up to 3 images), Kling's Identity-Lock, SD's IP-Adapter, and ControlNet in a single unified structure.[^11][^9][^3][^10]
### 4.3 Semantic Versioning
Every entity (project, character, shot, output) carries a `versions` array with `VersionRecord` objects. The schema document itself uses a URI-based `$id` containing the semver string as recommended by JSON Schema maintainers. The `parent_version` field on `VersionRecord` enables a full DAG of revision history.[^1][^2][^4][^12]
### 4.4 Assembly Tool Bindings
The `AssemblyInstruction` object on each `Shot` provides first-class fields for MoviePy (`clip_in_sec`, `clip_out_sec`, `timeline_in_sec`, `transition_in/out`, `speed_factor`), Movis (layer compositing via `layer` and `opacity`), OpenCV (`opencv_filters` pipeline descriptors), and PyAV (`pyav_stream_params`). Manim integration is handled via `CinematicSpec.manim_config` which specifies the Python scene class, quality preset, and render dimensions.[^5][^13][^6]
### 4.5 Quality Specification Hierarchy
`QualitySpec` is defined once as a `$def` and applied at three levels: `project_meta.project_quality_spec` (global default), `Shot.quality_spec` (per-clip override), and `RenderOutput.quality_spec` (per-delivery-target override). This cascade eliminates redundancy while preserving the ability to downscale for social clips without modifying the source. `ColorGrade` lives separately and can be applied at the shot level (via `AssemblyInstruction`), at the scene level, or globally in `render_pipeline.post_processing`.[^14][^6]
### 4.6 Audio Synchronisation
`AudioAsset.sync` carries both absolute timeline anchors (`timeline_in_sec`, `timeline_out_sec`) and relative anchors (`shot_ref`, `beat_offset_sec`). This supports the two dominant sync patterns: time-code-based alignment (used by MoviePy and PyAV) and beat-relative alignment (used in music-driven videos). ElevenLabs-specific voice parameters (`voice_id`, `voice_stability`, `voice_similarity`, `voice_style`, `voice_use_speaker_boost`) are typed inside `gen_params.sound_generation`.[^6][^15]
### 4.7 Dependency Graph & Execution Order
`Scene.dependencies` records which scenes must be rendered before the current one — enabling the orchestrator to build a topological sort. `render_pipeline.execution_order` materialises that sorted list at pipeline-compile time, enabling both sequential and parallel (up to `max_concurrent_jobs`) rendering strategies.[^8][^3]

***
## 5. Extensibility Contract
Any future generative tool integrates by:

1. Setting `gen_params.tool` to a new identifier string.
2. Placing tool-specific parameters inside `gen_params.extra`.
3. Optionally proposing a typed PR to the `gen_params` definition to promote stable fields from `extra` to first-class properties.

No existing consumers of the schema break because `extra` carries `"additionalProperties": true`.[^2][^7]

***
## 6. Validation Rules (Non-Schema Constraints)
These invariants should be enforced by a schema validator or pipeline guard at runtime:

| Rule | Scope | Rationale |
|---|---|---|
| `sum(scene.shots.duration_sec) ≤ project_meta.max_duration_sec` | Project | 30-minute hard cap |
| All `AssetRef.id` values resolve to a registered entity | Document | Referential integrity |
| `Shot.anchor_frame.source_shot_id` must precede this shot in topological order | Shot | Temporal bridge validity[^3] |
| `gen_params.seed` must be set on all approved shots | Shot | Reproducibility[^16] |
| `character_coherence_min_score` gate before scene approval | Scene | Identity consistency[^3] |
| `RenderOutput.total_duration_sec ≤ 1800` | Output | Delivery constraint |
| `VersionRecord.version` must be strictly monotonically increasing | All entities | Version integrity[^2] |

---

## References

1. [Digital Asset Management for Video Production - Aprimo](https://www.aprimo.com/blog/digital-asset-management-for-video-a-guide-to-streamlining-workflows) - Streamline digital asset management video production workflows. Discover AI-powered solutions, integ...

2. [Achieving Semantic Versioning for JSON Schema - YouTube](https://www.youtube.com/watch?v=5pDGkwLc2zc) - Discover how to implement `semantic versioning` for your JSON schema validations, ensuring data inte...

3. [A Multistage Pipeline for Character-Stable AI Video Stories - arXiv](https://arxiv.org/html/2512.16954v1) - This script guides a text-to-image model in creating consistent visuals for each character, which th...

4. [JSON Schema Semantic Versioning - Stack Overflow](https://stackoverflow.com/questions/70772942/json-schema-semantic-versioning) - My question is, how can I achieve semantic versioning for the JSON schema and check if the json data...

5. [Automated Video Editing with MoviePy in Python - YouTube](https://www.youtube.com/watch?v=Q2d1tYvTjRw) - Today we learn how to automate video editing using Python and MoviePy. ◾◾◾◾◾◾◾◾◾◾◾◾◾◾◾◾◾ Programming...

6. [Here Is Your Ultimate Post-Production Workflow Guide - MASV](https://massive.io/workflow/post-production-workflow/) - Read on for a step-by-step breakdown of the vital steps of any good post-production workflow, includ...

7. [An Introduction to JSON Schema - YouTube](https://www.youtube.com/watch?v=dtLl37W68g8) - Share your videos with friends, family, and the world.

8. [10 Core Concepts Every Video Creator Should Know in 2025](https://sbnmedia.in/ai-agents-in-video-production-10-core-concepts-every-video-creator-should-know-in-2025) - Discover how AI agents are revolutionizing video production in 2025. Learn 10 essential concepts tha...

9. [Runway Gen-4 API : Next-Gen Video & Image Generation API](https://aimlapi.com/create-with-runway-4) - Gen-4 offers sophisticated camera control capabilities, allowing users to dictate camera movements w...

10. [Runway Gen-4 vs. Kling 3.0: Which Image to Video AI Wins for ...](https://www.atlascloud.ai/pl/blog/runway-gen-4-vs-kling-3-0-which-image-to-video-ai-wins-for-professional-filmmaking) - Unlike models that process visuals and motion separately, Kling's framework simultaneously optimizes...

11. [Negative image prompt for Stable Diffusion using the IP-adapter.](https://github.com/sagiodev/IP-Adapter-Negative) - We present IP-Adapter, an effective and lightweight adapter to achieve image prompt capability for t...

12. [Using JSON SCHEMAS and SEMVER for IoT and Event ... - YouTube](https://www.youtube.com/watch?v=-C7G41L_uQ8) - This video demonstrates how to use JSON Schemas and Semantic Versioning (Semver) to create powerful,...

13. [Combine and synchronise manim and matplotlib animations ...](https://www.reddit.com/r/manim/comments/sq67j5/combine_and_synchronise_manim_and_matplotlib/) - I want to combine two separate animations from manim and matplotlib (each currently give separate .m...

14. [VideoObject - Schema.org Type](https://schema.org/VideoObject) - A video file. Instances of VideoObject may appear as a value for the following properties More speci...

15. [List LLMs | ElevenLabs Documentation](https://elevenlabs.io/docs/api-reference/llm/list) - Returns a list of available LLM models that can be used with agents, including their capabilities an...

16. [How to Use Seed and Negative Prompt to Generate Consistent AI ...](https://www.youtube.com/watch?v=hNFCLiloMeo) - Step-by-Step Guide to Generating AI Images Consistently Are you struggling to keep your AI images co...

