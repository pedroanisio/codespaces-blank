# Comprehensive Video Orchestration JSON Schema

**Version:** 1.0  
**Author:** Manus AI  
**Date:** March 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Entity-Relationship Model](#entity-relationship-model)
3. [JSON Schema Definition](#json-schema-definition)
4. [Core Definitions](#core-definitions)
5. [Field-Level Annotations and Constraints](#field-level-annotations-and-constraints)
6. [Dependency and Versioning Rules](#dependency-and-versioning-rules)
7. [Extensibility Patterns](#extensibility-patterns)
8. [Programmatic Assembly Integration](#programmatic-assembly-integration)
9. [Usage Examples](#usage-examples)

---

## Overview

This schema provides a **tool-agnostic, extensible framework** for the programmatic creation, storage, management, versioning, and orchestration of all assets required to generate high-quality videos up to 30 minutes in length. The design supports any current or future generative-AI tool, pipeline, or model without modification, and is optimized for integration with Python video assembly libraries including MoviePy, Movis, OpenCV, PyAV, and Manim.

### Key Design Principles

- **Hierarchical Structure**: Organized from project-level metadata down to individual asset specifications.
- **Tool-Agnosticism**: Generative parameters are extensible and do not depend on specific tool implementations.
- **Versioning and Provenance**: Every asset maintains a complete version history with parent references and status tracking.
- **Quality Specifications**: Measurable, hierarchical quality controls at both global and asset levels.
- **Dependency Management**: Explicit relationships between assets enable validation and orchestration.
- **Programmatic Assembly**: Assembly instructions provide a structured timeline for video composition.

---

## Entity-Relationship Model

The schema is organized as a hierarchical tree with the following relationships:

```
Project (root)
├── Story
├── Script
├── DirectorInstructions
├── Scenes (array)
│   └── Scene
│       └── Shots (array)
│           └── Shot
│               ├── VisualAssets (array)
│               ├── AudioAssets (array)
│               └── Dependencies (array of asset IDs)
├── GlobalAudio (array)
├── MarketingMaterials (array)
└── FinalOutputs (array)
```

### Entity Descriptions

| Entity | Purpose | Cardinality | Key Relationships |
|--------|---------|-------------|-------------------|
| **Project** | Root container for all project metadata and assets | 1 per project | Contains Story, Script, DirectorInstructions, Scenes, GlobalAudio, MarketingMaterials, FinalOutputs |
| **Story** | Narrative structure, character profiles, and thematic elements | 1 per Project | References character assets; referenced by Scenes |
| **Script** | Full dialogue, action descriptions, and timing information | 1 per Project | Provides timing for Shots; referenced by DirectorInstructions |
| **DirectorInstructions** | Global creative direction, pacing, and stylistic guidelines | 1 per Project | Applies to all Scenes; overridable at Shot level |
| **Scene** | Logical grouping of Shots in a specific location and time | Multiple per Project | Contains Shots; belongs to Project |
| **Shot** | Fundamental unit of video generation | Multiple per Scene | Contains VisualAssets, AudioAssets; depends on other assets |
| **VisualAsset** | Generated video clips, images, storyboards, references | Multiple per Shot | Versioned; includes generative parameters; may depend on other assets |
| **AudioAsset** | Voice-over, music, sound effects | Multiple per Shot or Global | Versioned; includes generative parameters; synchronized via offset |
| **MarketingMaterial** | Promotional assets (trailers, thumbnails, social clips) | Multiple per Project | References VisualAssets and AudioAssets from Shots |
| **FinalOutput** | Assembled video render with assembly instructions | Multiple per Project | References all assets used; includes timeline and render settings |

---

## JSON Schema Definition

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/video-orchestration.schema.json",
  "title": "Video Orchestration Project",
  "description": "A comprehensive schema for programmatic video creation, management, and orchestration supporting up to 30-minute videos.",
  "type": "object",
  "properties": {
    "projectId": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the project"
    },
    "title": {
      "type": "string",
      "description": "Human-readable project title"
    },
    "description": {
      "type": "string",
      "description": "Project description and context"
    },
    "version": {
      "type": "string",
      "description": "Semantic version of the project (e.g., 1.0.0, 1.2.3-beta)"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "createdAt": { "type": "string", "format": "date-time" },
        "updatedAt": { "type": "string", "format": "date-time" },
        "author": { "type": "string" },
        "tags": { "type": "array", "items": { "type": "string" } }
      }
    },
    "globalQualitySpecs": {
      "$ref": "#/$defs/QualitySpecifications",
      "description": "Default quality specifications applied to all assets unless overridden"
    },
    "story": {
      "$ref": "#/$defs/Story",
      "description": "Narrative arc, synopsis, and character definitions"
    },
    "script": {
      "$ref": "#/$defs/Script",
      "description": "Full script with dialogue, action, and timing"
    },
    "directorInstructions": {
      "$ref": "#/$defs/DirectorInstructions",
      "description": "Global creative direction and stylistic guidelines"
    },
    "scenes": {
      "type": "array",
      "items": { "$ref": "#/$defs/Scene" },
      "description": "Array of scenes, each containing shots"
    },
    "globalAudio": {
      "type": "array",
      "items": { "$ref": "#/$defs/AudioAsset" },
      "description": "Background music, ambient soundscapes, or global audio tracks"
    },
    "marketingMaterials": {
      "type": "array",
      "items": { "$ref": "#/$defs/MarketingMaterial" },
      "description": "Promotional assets derived from the project"
    },
    "finalOutputs": {
      "type": "array",
      "items": { "$ref": "#/$defs/FinalOutput" },
      "description": "Assembled video renders with versioning and assembly instructions"
    }
  },
  "required": ["projectId", "title", "version", "globalQualitySpecs", "scenes"],
  
  "$defs": {
    "QualitySpecifications": {
      "type": "object",
      "description": "Measurable quality specifications for video output.",
      "properties": {
        "resolution": {
          "type": "object",
          "description": "Output resolution specifications",
          "properties": {
            "width": {
              "type": "integer",
              "minimum": 320,
              "description": "Width in pixels"
            },
            "height": {
              "type": "integer",
              "minimum": 240,
              "description": "Height in pixels"
            },
            "standard": {
              "type": "string",
              "enum": ["4K", "1080p", "720p", "480p", "Custom"],
              "description": "Standard resolution designation"
            }
          },
          "required": ["width", "height"]
        },
        "aspectRatio": {
          "type": "string",
          "pattern": "^\\d+(\\.\\d+)?:\\d+(\\.\\d+)?$",
          "examples": ["16:9", "9:16", "2.35:1", "1:1"],
          "description": "Aspect ratio as width:height ratio"
        },
        "frameRate": {
          "type": "number",
          "enum": [24, 25, 30, 48, 50, 60],
          "description": "Frames per second (fps)"
        },
        "codec": {
          "type": "string",
          "enum": ["h264", "h265", "prores", "dnxhd", "custom"],
          "description": "Video codec for output"
        },
        "bitrate": {
          "type": "string",
          "description": "Target bitrate (e.g., '5000k', '10M')"
        },
        "temporalConsistency": {
          "type": "object",
          "description": "Requirements for frame-to-frame stability and flicker reduction",
          "properties": {
            "enabled": { "type": "boolean" },
            "threshold": { "type": "number", "description": "Allowed pixel variance between frames (0-255)" }
          }
        },
        "characterCoherence": {
          "type": "object",
          "description": "Guidelines for maintaining character likeness across shots",
          "properties": {
            "enabled": { "type": "boolean" },
            "method": { "type": "string", "enum": ["ipAdapter", "controlNet", "styleReference"] },
            "consistencyWeight": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        },
        "cinematicLighting": {
          "type": "object",
          "description": "Lighting style and mood specifications",
          "properties": {
            "style": { "type": "string", "examples": ["high contrast", "neon", "volumetric", "natural"] },
            "colorTemperature": { "type": "string", "examples": ["warm", "cool", "neutral"] },
            "intensity": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        },
        "colorGrading": {
          "type": "object",
          "description": "Color space and grading specifications",
          "properties": {
            "colorSpace": { "type": "string", "enum": ["rec709", "dci-p3", "rec2020", "srgb"] },
            "lutFile": { "type": "string", "format": "uri", "description": "Optional LUT file URI" },
            "saturation": { "type": "number", "minimum": -1, "maximum": 2 },
            "contrast": { "type": "number", "minimum": 0.5, "maximum": 2 }
          }
        },
        "motionBlur": {
          "type": "object",
          "description": "Motion blur settings",
          "properties": {
            "enabled": { "type": "boolean" },
            "shutterAngle": { "type": "number", "description": "Shutter angle in degrees (0-360)" }
          }
        },
        "denoise": {
          "type": "object",
          "description": "Noise reduction settings",
          "properties": {
            "enabled": { "type": "boolean" },
            "strength": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        }
      },
      "required": ["resolution", "aspectRatio", "frameRate"]
    },

    "GenerativeParameters": {
      "type": "object",
      "description": "Tool-agnostic parameters for AI-based asset generation. Extensible to support any current or future generative-AI tool.",
      "properties": {
        "toolName": {
          "type": "string",
          "examples": ["Runway Gen-2", "Runway Gen-3", "Kling", "Luma Dream Machine", "Pika", "Midjourney v6", "DALL-E 3", "Stable Diffusion 3.5", "ElevenLabs", "Eleven Multilingual v2"],
          "description": "Name of the generative-AI tool or service"
        },
        "modelVersion": {
          "type": "string",
          "description": "Specific model version identifier (e.g., 'gpt-4-turbo', 'claude-3-opus', 'flux-pro')"
        },
        "prompt": {
          "type": "string",
          "description": "Primary generation prompt describing the desired output"
        },
        "negativePrompt": {
          "type": "string",
          "description": "Negative prompt specifying what to avoid in generation"
        },
        "seed": {
          "type": "integer",
          "minimum": 0,
          "description": "Random seed for reproducibility"
        },
        "steps": {
          "type": "integer",
          "minimum": 1,
          "description": "Number of inference steps (higher = more detailed but slower)"
        },
        "cfgScale": {
          "type": "number",
          "minimum": 0,
          "description": "Classifier-free guidance scale (higher = more adherence to prompt)"
        },
        "temperature": {
          "type": "number",
          "minimum": 0,
          "maximum": 2,
          "description": "Sampling temperature for text-based generation (lower = more deterministic)"
        },
        "topP": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Top-p (nucleus) sampling parameter"
        },
        "consistencyAnchors": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "type": {
                "type": "string",
                "enum": ["characterReference", "styleReference", "ipAdapter", "controlNet", "styleTransfer", "lora", "embedding"],
                "description": "Type of consistency anchor"
              },
              "assetId": {
                "type": "string",
                "format": "uuid",
                "description": "Reference to the anchor asset (image, style, or model)"
              },
              "weight": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Influence weight of the anchor (0 = no influence, 1 = maximum influence)"
              },
              "description": {
                "type": "string",
                "description": "Human-readable description of the anchor's purpose"
              }
            },
            "required": ["type", "assetId"]
          },
          "description": "Array of consistency anchors for maintaining coherence across generations"
        },
        "customParameters": {
          "type": "object",
          "description": "Extensible key-value pairs for tool-specific API parameters. Examples: { 'cameraMotion': 'pan_left', 'duration': 5, 'motionBucket': 127, 'voiceId': 'en_US_male_1', 'speed': 1.2 }",
          "additionalProperties": true
        },
        "generationConfig": {
          "type": "object",
          "description": "Additional generation configuration",
          "properties": {
            "maxTokens": { "type": "integer", "description": "Maximum tokens for text generation" },
            "stopSequences": { "type": "array", "items": { "type": "string" } },
            "repetitionPenalty": { "type": "number" }
          }
        }
      },
      "required": ["toolName", "prompt"]
    },

    "Versioning": {
      "type": "object",
      "description": "Version control and provenance tracking for assets.",
      "properties": {
        "versionId": {
          "type": "string",
          "format": "uuid",
          "description": "Unique identifier for this version"
        },
        "versionNumber": {
          "type": "string",
          "description": "Human-readable version number (e.g., '1.0', '1.2.3')"
        },
        "parentVersionId": {
          "type": "string",
          "format": "uuid",
          "nullable": true,
          "description": "ID of the parent version (for tracking derivations)"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "Creation timestamp of this version"
        },
        "status": {
          "type": "string",
          "enum": ["draft", "generating", "review", "approved", "rejected", "archived"],
          "description": "Current status of the version"
        },
        "author": {
          "type": "string",
          "description": "Creator or modifier of this version"
        },
        "notes": {
          "type": "string",
          "description": "Release notes or change log for this version"
        },
        "metadata": {
          "type": "object",
          "description": "Additional version metadata",
          "properties": {
            "generationTime": { "type": "number", "description": "Time taken to generate in seconds" },
            "cost": { "type": "number", "description": "Cost of generation (if applicable)" },
            "qualityScore": { "type": "number", "minimum": 0, "maximum": 1 }
          }
        }
      },
      "required": ["versionId", "timestamp", "status"]
    },

    "Story": {
      "type": "object",
      "description": "Narrative structure, character profiles, and thematic elements.",
      "properties": {
        "storyId": {
          "type": "string",
          "format": "uuid"
        },
        "logline": {
          "type": "string",
          "description": "One-sentence summary of the story"
        },
        "synopsis": {
          "type": "string",
          "description": "Extended summary of the narrative"
        },
        "narrativeArc": {
          "type": "string",
          "description": "Description of the story structure (exposition, rising action, climax, resolution)"
        },
        "theme": {
          "type": "string",
          "description": "Central theme or message"
        },
        "characters": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "characterId": {
                "type": "string",
                "format": "uuid"
              },
              "name": {
                "type": "string"
              },
              "role": {
                "type": "string",
                "enum": ["protagonist", "antagonist", "supporting", "extra"]
              },
              "description": {
                "type": "string",
                "description": "Physical and personality description"
              },
              "referenceAssetIds": {
                "type": "array",
                "items": { "type": "string", "format": "uuid" },
                "description": "IDs of visual reference assets (images, concept art)"
              }
            },
            "required": ["characterId", "name"]
          }
        }
      }
    },

    "Script": {
      "type": "object",
      "description": "Full screenplay with dialogue, action, and timing.",
      "properties": {
        "scriptId": {
          "type": "string",
          "format": "uuid"
        },
        "format": {
          "type": "string",
          "enum": ["screenplay", "storyboard", "shot-list"],
          "description": "Script format type"
        },
        "elements": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "elementId": {
                "type": "string",
                "format": "uuid"
              },
              "type": {
                "type": "string",
                "enum": ["sceneHeading", "action", "character", "dialogue", "parenthetical", "transition", "note"]
              },
              "content": {
                "type": "string"
              },
              "estimatedDurationSeconds": {
                "type": "number",
                "description": "Estimated duration for this element"
              },
              "sceneReference": {
                "type": "string",
                "format": "uuid",
                "description": "Reference to the corresponding Scene"
              }
            },
            "required": ["type", "content"]
          }
        }
      }
    },

    "DirectorInstructions": {
      "type": "object",
      "description": "Global creative direction, pacing, and stylistic guidelines.",
      "properties": {
        "directorId": {
          "type": "string",
          "format": "uuid"
        },
        "pacing": {
          "type": "string",
          "description": "Overall pacing guidance (e.g., 'fast-paced', 'contemplative', 'rhythmic')"
        },
        "visualStyle": {
          "type": "string",
          "description": "Visual style description (e.g., 'cyberpunk neon', 'naturalistic', 'surreal')"
        },
        "cameraWork": {
          "type": "string",
          "description": "General camera movement and framing guidelines"
        },
        "soundDesign": {
          "type": "string",
          "description": "Audio atmosphere and sound design approach"
        },
        "moodAndTone": {
          "type": "string",
          "description": "Emotional tone and mood of the piece"
        },
        "referenceAssets": {
          "type": "array",
          "items": { "type": "string", "format": "uuid" },
          "description": "IDs of reference images or videos"
        }
      }
    },

    "Scene": {
      "type": "object",
      "description": "Logical grouping of shots in a specific location and time.",
      "properties": {
        "sceneId": {
          "type": "string",
          "format": "uuid"
        },
        "sceneNumber": {
          "type": "integer",
          "description": "Sequential scene number"
        },
        "heading": {
          "type": "string",
          "description": "Scene heading (e.g., 'INT. COFFEE SHOP - DAY')"
        },
        "description": {
          "type": "string",
          "description": "Scene description and context"
        },
        "location": {
          "type": "string",
          "description": "Physical location of the scene"
        },
        "timeOfDay": {
          "type": "string",
          "enum": ["day", "night", "dawn", "dusk", "custom"]
        },
        "environmentReferenceAssets": {
          "type": "array",
          "items": { "type": "string", "format": "uuid" },
          "description": "IDs of environment reference images"
        },
        "shots": {
          "type": "array",
          "items": { "$ref": "#/$defs/Shot" },
          "description": "Array of shots within this scene"
        },
        "estimatedDurationSeconds": {
          "type": "number",
          "description": "Estimated total duration of the scene"
        }
      },
      "required": ["sceneId", "sceneNumber", "shots"]
    },

    "Shot": {
      "type": "object",
      "description": "Fundamental unit of video generation and composition.",
      "properties": {
        "shotId": {
          "type": "string",
          "format": "uuid"
        },
        "shotNumber": {
          "type": "string",
          "description": "Shot identifier (e.g., '1A', '2.1')"
        },
        "durationSeconds": {
          "type": "number",
          "minimum": 0.1,
          "description": "Duration of the shot in seconds"
        },
        "actionDescription": {
          "type": "string",
          "description": "Detailed description of the action occurring in the shot"
        },
        "cameraInstruction": {
          "type": "string",
          "description": "Specific camera movement or framing instructions (e.g., 'slow pan left', 'push in on face')"
        },
        "qualitySpecsOverride": {
          "$ref": "#/$defs/QualitySpecifications",
          "description": "Quality specifications specific to this shot (overrides global specs)"
        },
        "visualAssets": {
          "type": "array",
          "items": { "$ref": "#/$defs/VisualAsset" },
          "description": "Visual assets (video clips, images, storyboards) for this shot"
        },
        "audioAssets": {
          "type": "array",
          "items": { "$ref": "#/$defs/AudioAsset" },
          "description": "Audio assets (voice-over, sound effects, music) for this shot"
        },
        "dependencies": {
          "type": "array",
          "items": { "type": "string", "format": "uuid" },
          "description": "IDs of assets this shot depends on (e.g., character references, style guides)"
        },
        "metadata": {
          "type": "object",
          "properties": {
            "retakes": { "type": "integer", "description": "Number of generation retakes" },
            "notes": { "type": "string" }
          }
        }
      },
      "required": ["shotId", "durationSeconds", "visualAssets"]
    },

    "VisualAsset": {
      "type": "object",
      "description": "Visual media asset (video clip, image, storyboard, or reference).",
      "properties": {
        "assetId": {
          "type": "string",
          "format": "uuid"
        },
        "type": {
          "type": "string",
          "enum": ["videoClip", "image", "storyboard", "environmentReference", "characterReference", "styleReference"],
          "description": "Type of visual asset"
        },
        "uri": {
          "type": "string",
          "format": "uri",
          "description": "URI to the asset file (local path or remote URL)"
        },
        "duration": {
          "type": "number",
          "description": "Duration in seconds (for video clips)"
        },
        "versioning": {
          "$ref": "#/$defs/Versioning"
        },
        "generativeParameters": {
          "$ref": "#/$defs/GenerativeParameters",
          "description": "Parameters used to generate this asset (if AI-generated)"
        },
        "metadata": {
          "type": "object",
          "properties": {
            "width": { "type": "integer" },
            "height": { "type": "integer" },
            "format": { "type": "string", "examples": ["mp4", "png", "jpg", "webp"] },
            "fileSize": { "type": "integer", "description": "File size in bytes" },
            "colorSpace": { "type": "string" }
          }
        }
      },
      "required": ["assetId", "type", "versioning"]
    },

    "AudioAsset": {
      "type": "object",
      "description": "Audio asset (voice-over, music, sound effect) with synchronization metadata.",
      "properties": {
        "assetId": {
          "type": "string",
          "format": "uuid"
        },
        "type": {
          "type": "string",
          "enum": ["voiceOver", "music", "soundEffect", "ambience", "dialogue"],
          "description": "Type of audio asset"
        },
        "uri": {
          "type": "string",
          "format": "uri",
          "description": "URI to the audio file"
        },
        "duration": {
          "type": "number",
          "description": "Duration in seconds"
        },
        "syncOffsetSeconds": {
          "type": "number",
          "description": "Time offset relative to the start of the shot or scene"
        },
        "volume": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Volume level (0 = silent, 1 = full)"
        },
        "fadeIn": {
          "type": "number",
          "description": "Fade-in duration in seconds"
        },
        "fadeOut": {
          "type": "number",
          "description": "Fade-out duration in seconds"
        },
        "versioning": {
          "$ref": "#/$defs/Versioning"
        },
        "generativeParameters": {
          "$ref": "#/$defs/GenerativeParameters",
          "description": "Parameters used to generate this asset (if AI-generated)"
        },
        "metadata": {
          "type": "object",
          "properties": {
            "sampleRate": { "type": "integer", "description": "Sample rate in Hz (e.g., 44100, 48000)" },
            "channels": { "type": "integer", "description": "Number of audio channels (1 = mono, 2 = stereo)" },
            "format": { "type": "string", "examples": ["mp3", "wav", "aac", "flac"] },
            "fileSize": { "type": "integer" }
          }
        }
      },
      "required": ["assetId", "type", "versioning"]
    },

    "MarketingMaterial": {
      "type": "object",
      "description": "Promotional assets derived from the project.",
      "properties": {
        "materialId": {
          "type": "string",
          "format": "uuid"
        },
        "type": {
          "type": "string",
          "enum": ["trailer", "thumbnail", "promotionalStill", "socialClip", "behind-the-scenes"],
          "description": "Type of marketing material"
        },
        "targetPlatform": {
          "type": "string",
          "examples": ["YouTube", "TikTok", "Instagram", "Twitter", "LinkedIn", "generic"],
          "description": "Target platform for the material"
        },
        "assetRefs": {
          "type": "array",
          "items": { "type": "string", "format": "uuid" },
          "description": "IDs of assets used in this material"
        },
        "uri": {
          "type": "string",
          "format": "uri",
          "description": "URI to the generated material"
        },
        "qualitySpecs": {
          "$ref": "#/$defs/QualitySpecifications",
          "description": "Quality specifications for this material"
        },
        "versioning": {
          "$ref": "#/$defs/Versioning"
        }
      },
      "required": ["materialId", "type"]
    },

    "FinalOutput": {
      "type": "object",
      "description": "Assembled video render with versioning and programmatic assembly instructions.",
      "properties": {
        "outputId": {
          "type": "string",
          "format": "uuid"
        },
        "title": {
          "type": "string",
          "description": "Title of this output"
        },
        "versioning": {
          "$ref": "#/$defs/Versioning"
        },
        "uri": {
          "type": "string",
          "format": "uri",
          "description": "URI to the rendered video file"
        },
        "assemblyInstructions": {
          "type": "object",
          "description": "Programmatic instructions for video composition using libraries like MoviePy, Movis, PyAV, Manim, or OpenCV.",
          "properties": {
            "library": {
              "type": "string",
              "enum": ["moviepy", "movis", "opencv", "pyav", "manim", "custom"],
              "description": "Target Python library for assembly"
            },
            "timeline": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "assetId": {
                    "type": "string",
                    "format": "uuid",
                    "description": "ID of the asset to include"
                  },
                  "startTime": {
                    "type": "number",
                    "description": "Start time in the final video (seconds)"
                  },
                  "endTime": {
                    "type": "number",
                    "description": "End time in the final video (seconds)"
                  },
                  "track": {
                    "type": "integer",
                    "description": "Track number (0 = video track 1, 1 = video track 2, etc.; negative = audio tracks)"
                  },
                  "position": {
                    "type": "object",
                    "description": "Position and size on screen (for video assets)",
                    "properties": {
                      "x": { "type": "number" },
                      "y": { "type": "number" },
                      "width": { "type": "number" },
                      "height": { "type": "number" }
                    }
                  },
                  "opacity": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Opacity/alpha value"
                  },
                  "transitions": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "type": {
                          "type": "string",
                          "enum": ["cut", "fade", "dissolve", "wipeLeft", "wipeRight", "slideIn", "slideOut", "zoomIn", "zoomOut"],
                          "description": "Transition type"
                        },
                        "duration": {
                          "type": "number",
                          "description": "Transition duration in seconds"
                        },
                        "easing": {
                          "type": "string",
                          "enum": ["linear", "easeIn", "easeOut", "easeInOut"],
                          "description": "Easing function"
                        }
                      },
                      "required": ["type"]
                    }
                  }
                },
                "required": ["assetId", "startTime", "endTime"]
              },
              "description": "Timeline of assets and their placement in the final video"
            },
            "renderSettings": {
              "$ref": "#/$defs/QualitySpecifications",
              "description": "Final render quality specifications"
            },
            "audioMix": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "assetId": { "type": "string", "format": "uuid" },
                  "volume": { "type": "number", "minimum": 0, "maximum": 1 },
                  "pan": { "type": "number", "minimum": -1, "maximum": 1 }
                }
              },
              "description": "Audio mixing instructions"
            },
            "effects": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "type": { "type": "string", "examples": ["colorGrade", "blur", "sharpen", "denoise"] },
                  "assetId": { "type": "string", "format": "uuid" },
                  "parameters": { "type": "object", "additionalProperties": true }
                }
              },
              "description": "Post-processing effects"
            }
          },
          "required": ["timeline"]
        }
      },
      "required": ["outputId", "versioning", "assemblyInstructions"]
    }
  }
}
```

---

## Core Definitions

### QualitySpecifications

Defines measurable quality parameters at both global and asset levels. Includes resolution, aspect ratio, frame rate, codec, temporal consistency, character coherence, lighting, color grading, motion blur, and denoising. All parameters are optional except resolution, aspect ratio, and frame rate, allowing flexible specification at different hierarchy levels.

### GenerativeParameters

Provides a tool-agnostic interface for all generative-AI parameters. The `customParameters` object enables extensibility for any tool-specific API parameters without modifying the core schema. Includes support for consistency anchors (character references, style references, IP adapters, ControlNets, LoRAs, embeddings).

### Versioning

Tracks the complete version history of every asset, including version ID, parent version, timestamp, status, author, and metadata. Supports draft, generating, review, approved, rejected, and archived states.

### Story

Defines narrative structure with logline, synopsis, narrative arc, theme, and character profiles. Characters include references to visual assets for consistency.

### Script

Full screenplay with support for multiple formats (screenplay, storyboard, shot-list). Elements include scene headings, action, character, dialogue, parentheticals, transitions, and notes, each with estimated duration and scene references.

### DirectorInstructions

Global creative direction covering pacing, visual style, camera work, sound design, mood/tone, and reference assets.

### Scene

Logical grouping of shots with scene number, heading, description, location, time of day, environment references, and an array of shots.

### Shot

Fundamental unit containing action description, camera instructions, visual and audio assets, quality spec overrides, dependencies, and metadata.

### VisualAsset

Represents video clips, images, storyboards, or references with versioning, generative parameters, and metadata (resolution, format, file size, color space).

### AudioAsset

Represents voice-over, music, sound effects, ambience, or dialogue with synchronization offset, volume, fade-in/out, versioning, generative parameters, and metadata (sample rate, channels, format).

### MarketingMaterial

Promotional assets (trailers, thumbnails, social clips) derived from the project, with target platform specification and asset references.

### FinalOutput

Assembled video render with versioning and comprehensive assembly instructions including timeline, render settings, audio mix, and post-processing effects.

---

## Field-Level Annotations and Constraints

| Field | Type | Constraints | Purpose |
|-------|------|-----------|---------|
| `projectId` | UUID | Required, unique | Unique project identifier |
| `title` | String | Required | Human-readable project name |
| `version` | String | Semantic versioning | Project version tracking |
| `globalQualitySpecs` | QualitySpecifications | Required | Default quality for all assets |
| `scenes` | Array[Scene] | Required, non-empty | Video content structure |
| `sceneNumber` | Integer | Required, sequential | Scene ordering |
| `shotId` | UUID | Required, unique | Unique shot identifier |
| `durationSeconds` | Number | Required, > 0 | Shot length in seconds |
| `assetId` | UUID | Required, unique | Unique asset identifier |
| `versionId` | UUID | Required, unique | Unique version identifier |
| `status` | Enum | One of: draft, generating, review, approved, rejected, archived | Asset lifecycle state |
| `toolName` | String | Required | Generative-AI tool identifier |
| `prompt` | String | Required | Generation instruction |
| `seed` | Integer | Optional, ≥ 0 | Reproducibility control |
| `consistencyAnchors` | Array | Optional | References for coherence |
| `customParameters` | Object | Extensible key-value pairs | Tool-specific parameters |
| `frameRate` | Number | Enum: 24, 25, 30, 48, 50, 60 | Video frame rate |
| `aspectRatio` | String | Pattern: `\d+(\.\d+)?:\d+(\.\d+)?` | Video aspect ratio |
| `syncOffsetSeconds` | Number | Optional, any value | Audio synchronization |
| `timeline` | Array | Required, non-empty | Asset composition sequence |
| `startTime` | Number | Required, ≥ 0 | Asset start in final video |
| `endTime` | Number | Required, > startTime | Asset end in final video |

---

## Dependency and Versioning Rules

### Dependency Management

1. **Explicit Dependencies**: Every shot includes a `dependencies` array referencing assets it depends on (e.g., character references, style guides).
2. **Transitive Dependencies**: Tools processing the schema must resolve transitive dependencies (e.g., if Shot A depends on Asset B, and Asset B depends on Asset C, then Shot A implicitly depends on Asset C).
3. **Circular Dependency Prevention**: Validation rules must prevent circular dependencies (A depends on B, B depends on A).
4. **Asset Validation**: Before rendering, all referenced assets must be available and in an "approved" status.

### Versioning Rules

1. **Version Immutability**: Once a version is created, its content is immutable. Modifications create new versions.
2. **Parent Tracking**: Every version includes a `parentVersionId` enabling lineage tracking.
3. **Status Progression**: Versions follow a lifecycle: `draft` → `generating` → `review` → `approved` or `rejected`. Rejected versions can revert to `draft`.
4. **Timestamp Ordering**: Versions are ordered by timestamp; later timestamps indicate newer versions.
5. **Cascading Updates**: If a parent asset is updated, dependent assets may require re-generation or re-approval.

### Asset Composition Rules

1. **Timeline Ordering**: Assets in the final output timeline must be ordered by `startTime`.
2. **No Overlaps (Video Tracks)**: Video assets on the same track must not overlap unless intentional (for compositing).
3. **Audio Synchronization**: Audio assets use `syncOffsetSeconds` to align with video; offsets are relative to shot start.
4. **Duration Validation**: The sum of all shot durations must equal the final video duration (accounting for transitions).

---

## Extensibility Patterns

### Adding New Generative-AI Tools

To support a new generative-AI tool without modifying the core schema:

1. **Populate `toolName`** with the new tool identifier (e.g., "MyNewAITool v1.0").
2. **Use `customParameters`** to inject tool-specific parameters:
   ```json
   {
     "toolName": "MyNewAITool v1.0",
     "prompt": "A futuristic city at sunset",
     "customParameters": {
       "myToolParam1": "value1",
       "myToolParam2": 42,
       "myToolParam3": { "nested": "object" }
     }
   }
   ```

### Adding New Quality Specifications

Extend the `QualitySpecifications` object by adding new properties:

```json
{
  "resolution": { "width": 3840, "height": 2160 },
  "aspectRatio": "16:9",
  "frameRate": 24,
  "customQualityMetric": {
    "type": "perceptualQuality",
    "score": 0.95
  }
}
```

### Adding New Asset Types

Extend the `type` enum in `VisualAsset` or `AudioAsset`:

```json
{
  "assetId": "uuid-here",
  "type": "newAssetType",
  "uri": "path/to/asset",
  "versioning": { ... }
}
```

### Adding New Transition Types

Extend the `transitions` array in the `FinalOutput` assembly instructions:

```json
{
  "type": "customTransition",
  "duration": 1.5,
  "easing": "easeInOut",
  "customParameters": {
    "direction": "diagonal",
    "intensity": 0.8
  }
}
```

---

## Programmatic Assembly Integration

### MoviePy Integration

The `assemblyInstructions` timeline can be directly mapped to MoviePy's `CompositeVideoClip` and `CompositeAudioFileClip` structures:

- **Timeline items** → `CompositeVideoClip` clips with `pos` and `duration`.
- **Transitions** → MoviePy's `concatenate_videoclips` with `transition` parameter.
- **Audio mix** → `CompositeAudioFileClip` with volume adjustments.

### Movis Integration

Movis supports a declarative timeline approach compatible with the schema:

- **Timeline** → Movis `Composition` with layered clips.
- **Effects** → Movis effect chain applied per asset.

### OpenCV Integration

For frame-level processing:

- **Timeline** → Frame-by-frame composition using OpenCV's `cv2.addWeighted` for blending.
- **Transitions** → Custom transition logic per frame.

### PyAV Integration

For lower-level codec control:

- **Render settings** → PyAV container and codec configuration.
- **Timeline** → Frame-accurate asset sequencing.

### Manim Integration

For animated content:

- **Shots with Manim parameters** → Manim scene generation.
- **Timeline** → Manim animation sequencing.

---

## Usage Examples

### Example 1: Simple Two-Shot Video

```json
{
  "projectId": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Product Demo",
  "version": "1.0.0",
  "globalQualitySpecs": {
    "resolution": { "width": 1920, "height": 1080, "standard": "1080p" },
    "aspectRatio": "16:9",
    "frameRate": 30
  },
  "scenes": [
    {
      "sceneId": "550e8400-e29b-41d4-a716-446655440001",
      "sceneNumber": 1,
      "heading": "INT. STUDIO - DAY",
      "shots": [
        {
          "shotId": "550e8400-e29b-41d4-a716-446655440002",
          "shotNumber": "1A",
          "durationSeconds": 5,
          "actionDescription": "Product appears on screen",
          "visualAssets": [
            {
              "assetId": "550e8400-e29b-41d4-a716-446655440003",
              "type": "videoClip",
              "uri": "s3://bucket/product_intro.mp4",
              "versioning": {
                "versionId": "v1",
                "timestamp": "2026-03-27T10:00:00Z",
                "status": "approved"
              },
              "generativeParameters": {
                "toolName": "Runway Gen-3",
                "modelVersion": "gen3-turbo",
                "prompt": "A sleek product on a white background, rotating slowly"
              }
            }
          ],
          "audioAssets": []
        }
      ]
    }
  ],
  "finalOutputs": [
    {
      "outputId": "550e8400-e29b-41d4-a716-446655440004",
      "versioning": {
        "versionId": "v1",
        "timestamp": "2026-03-27T11:00:00Z",
        "status": "approved"
      },
      "assemblyInstructions": {
        "library": "moviepy",
        "timeline": [
          {
            "assetId": "550e8400-e29b-41d4-a716-446655440003",
            "startTime": 0,
            "endTime": 5,
            "track": 0
          }
        ],
        "renderSettings": {
          "resolution": { "width": 1920, "height": 1080 },
          "aspectRatio": "16:9",
          "frameRate": 30
        }
      }
    }
  ]
}
```

### Example 2: Multi-Scene Video with Consistency Anchors

```json
{
  "projectId": "550e8400-e29b-41d4-a716-446655440010",
  "title": "Character-Driven Narrative",
  "version": "2.1.0",
  "story": {
    "logline": "A hero's journey through a mystical realm.",
    "characters": [
      {
        "characterId": "char-001",
        "name": "Hero",
        "description": "A brave warrior with blue eyes and long dark hair",
        "referenceAssetIds": ["ref-char-001-image"]
      }
    ]
  },
  "globalQualitySpecs": {
    "resolution": { "width": 3840, "height": 2160, "standard": "4K" },
    "aspectRatio": "16:9",
    "frameRate": 24,
    "characterCoherence": {
      "enabled": true,
      "method": "ipAdapter",
      "consistencyWeight": 0.9
    }
  },
  "scenes": [
    {
      "sceneId": "scene-001",
      "sceneNumber": 1,
      "heading": "EXT. MYSTICAL FOREST - DAY",
      "shots": [
        {
          "shotId": "shot-001",
          "shotNumber": "1A",
          "durationSeconds": 8,
          "actionDescription": "Hero emerges from the forest",
          "visualAssets": [
            {
              "assetId": "asset-001",
              "type": "videoClip",
              "versioning": {
                "versionId": "v1",
                "timestamp": "2026-03-27T10:00:00Z",
                "status": "approved"
              },
              "generativeParameters": {
                "toolName": "Luma Dream Machine",
                "modelVersion": "1.0",
                "prompt": "A hero with blue eyes and long dark hair emerges from a mystical forest, walking slowly",
                "consistencyAnchors": [
                  {
                    "type": "characterReference",
                    "assetId": "ref-char-001-image",
                    "weight": 1.0
                  }
                ]
              }
            }
          ],
          "audioAssets": [
            {
              "assetId": "audio-001",
              "type": "voiceOver",
              "versioning": {
                "versionId": "v1",
                "timestamp": "2026-03-27T10:30:00Z",
                "status": "approved"
              },
              "generativeParameters": {
                "toolName": "ElevenLabs",
                "modelVersion": "eleven_multilingual_v2",
                "prompt": "A deep, heroic voice saying: 'I must find the ancient temple.'",
                "customParameters": {
                  "voiceId": "en_US_male_hero",
                  "stability": 0.75,
                  "similarity_boost": 0.85
                }
              }
            }
          ]
        }
      ]
    }
  ],
  "finalOutputs": [
    {
      "outputId": "output-001",
      "versioning": {
        "versionId": "v1",
        "timestamp": "2026-03-27T12:00:00Z",
        "status": "approved"
      },
      "assemblyInstructions": {
        "library": "moviepy",
        "timeline": [
          {
            "assetId": "asset-001",
            "startTime": 0,
            "endTime": 8,
            "track": 0,
            "transitions": [
              {
                "type": "fade",
                "duration": 0.5,
                "easing": "easeIn"
              }
            ]
          }
        ],
        "audioMix": [
          {
            "assetId": "audio-001",
            "volume": 1.0,
            "pan": 0
          }
        ],
        "renderSettings": {
          "resolution": { "width": 3840, "height": 2160 },
          "aspectRatio": "16:9",
          "frameRate": 24
        }
      }
    }
  ]
}
```

---

## Conclusion

This comprehensive JSON Schema provides a robust, extensible foundation for programmatic video creation and orchestration. By separating concerns (narrative, script, direction, assets, versioning, and assembly), the schema enables:

- **Tool-agnostic asset generation** through flexible generative parameters.
- **Version control and provenance** for all assets and outputs.
- **Hierarchical quality specifications** with override capabilities.
- **Programmatic composition** via structured assembly instructions.
- **Extensibility** without schema modification through custom parameters and enums.

The schema is production-ready and designed to scale from simple two-shot videos to complex 30-minute productions with multiple scenes, characters, and audio tracks.
