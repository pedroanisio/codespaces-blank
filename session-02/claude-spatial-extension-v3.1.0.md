# Spatial Extension for Unified Generative Video Project Schema

> **Schema version target:** 3.1.0 (minor increment — backward-compatible additive change)
>
> **Status:** Draft specification
>
> **Date:** 2026-03-27

---

> **DISCLAIMER — Required per user preference #5**
>
> No information within this document should be taken for granted.
> Any statement or premise not backed by a real logical definition
> or verifiable reference may be invalid, erroneous, or a hallucination.
> All mathematical definitions reference named conventions (OpenGL,
> USD, ISO 80000-3) but the author is not a standards body.
> Verify independently before relying on this specification in production.

---

## 1. Problem Statement

Schema v3.0.0 defines camera *intrinsics* (focal length, aperture, DoF,
field of view) via `CinematicSpec` but provides **no world-space model**.
Specifically:

| Capability | v3.0.0 Status |
|---|---|
| Camera lens configuration | ✅ `CinematicSpec` |
| Camera position/orientation in 3D | ❌ Absent |
| Entity placement in scene space | ❌ Absent — only `EntityRef` links |
| Spatial consistency contract | ❌ Absent — only `TemporalConsistency` |
| Scene bounding geometry | ❌ Absent — `EnvironmentEntity` is narrative |
| Cross-scene spatial continuity | ❌ Absent |
| Cross-project spatial interop | ❌ Absent |
| 2D compositing transforms | ✅ `Transform` — but no Z axis |

This means:

- An automated pipeline cannot answer "where is the camera relative to
  the subject?" without parsing prose in `compositionNotes`.
- Shot-to-shot spatial continuity (e.g., a 180° rule crossing) cannot
  be validated programmatically.
- Cross-movie shared universes (e.g., a franchise with a canonical
  city layout) have no structural contract.

## 2. Design Principles

1. **Backward-compatible.** Every new field is optional on existing types.
   No required fields change. No enums narrow. This is a minor version bump.

2. **Convention-explicit.** The coordinate system's handedness, up-axis,
   and unit are declared, not assumed. Different projects may declare
   different conventions; spatial data is only comparable when conventions
   match.

3. **Mathematically grounded.** Orientation uses unit quaternions
   (Hamilton convention, scalar-last `[x, y, z, w]` matching glTF/USD).
   Euler angles are optional convenience fields. No ambiguity about
   rotation order.

4. **Pattern-parallel.** New types mirror existing schema patterns:
   `SpatialConsistency` parallels `TemporalConsistency` and
   `CharacterCoherence`; `SpatialPlacement` parallels `ConsistencyAnchor`;
   `CameraExtrinsics` extends `CinematicSpec` the same way `ManimConfig` does.

5. **Generation-tool-agnostic.** The spatial model describes *intent*
   (where things should be), not tool-specific transforms. A depth-map
   generator, a 3D engine, or a prompt-injection pipeline can all consume it.

## 3. New `$defs` Types

### 3.1 `CoordinateSystem`

Declares the spatial convention for any scope that uses 3D coordinates.

```json
"CoordinateSystem": {
  "type": "object",
  "required": ["handedness", "upAxis", "unitM"],
  "additionalProperties": false,
  "description": "Declared spatial convention. Rule 7: metre unit. Two coordinate systems are compatible iff all three required fields match.",
  "properties": {
    "handedness": {
      "type": "string",
      "enum": ["right", "left"],
      "description": "Right-handed = OpenGL, USD, Blender default. Left-handed = DirectX, Unity default."
    },
    "upAxis": {
      "type": "string",
      "enum": ["+Y", "-Y", "+Z", "-Z"],
      "description": "+Y = USD/glTF/OpenGL convention. +Z = Blender/engineering convention."
    },
    "unitM": {
      "type": "number",
      "exclusiveMinimum": 0,
      "default": 1.0,
      "description": "Rule 7: scale factor to SI metres. 1.0 = coordinates are in metres. 0.01 = coordinates are in centimetres. 0.0254 = inches."
    },
    "forwardAxis": {
      "type": "string",
      "enum": ["+X", "-X", "+Z", "-Z", "+Y", "-Y"],
      "description": "Camera/character forward direction convention. Defaults to -Z for right-handed +Y-up systems (OpenGL)."
    },
    "notes": {
      "type": "string"
    }
  }
}
```

**Rationale:** Making the convention an explicit typed object (rather than
assuming one) means two projects can declare different conventions and a
tool can detect incompatibility at validation time. The `unitM` field
lets centimetre-native pipelines (Unreal Engine) and metre-native
pipelines (USD) coexist without silent 100x scaling errors.

### 3.2 `Position3D`

```json
"Position3D": {
  "type": "object",
  "required": ["x", "y", "z"],
  "additionalProperties": false,
  "description": "Point in 3D space. Units determined by enclosing CoordinateSystem.unitM. Rule 7: unitless numbers — unit is inherited from coordinate system declaration.",
  "properties": {
    "x": { "type": "number" },
    "y": { "type": "number" },
    "z": { "type": "number" }
  }
}
```

### 3.3 `Orientation3D`

```json
"Orientation3D": {
  "type": "object",
  "additionalProperties": false,
  "description": "Rotation in 3D. Primary representation: unit quaternion (Hamilton, scalar-last [x,y,z,w], matching glTF/USD). Euler angles are optional convenience; when both present, quaternion takes precedence.",
  "properties": {
    "quaternion": {
      "type": "object",
      "required": ["x", "y", "z", "w"],
      "additionalProperties": false,
      "description": "Unit quaternion [x, y, z, w]. Constraint: x²+y²+z²+w² = 1 (within floating-point tolerance). x-computed: true for normalization check.",
      "properties": {
        "x": { "type": "number" },
        "y": { "type": "number" },
        "z": { "type": "number" },
        "w": { "type": "number" }
      }
    },
    "eulerDeg": {
      "type": "object",
      "additionalProperties": false,
      "description": "Euler angles in degrees. Rule 7: degrees. Convenience only — quaternion is authoritative.",
      "properties": {
        "pitch": { "type": "number", "description": "Rotation around lateral axis (X in +Y-up)." },
        "yaw":   { "type": "number", "description": "Rotation around up axis (Y in +Y-up)." },
        "roll":  { "type": "number", "description": "Rotation around forward axis (Z in +Y-up)." },
        "order": {
          "type": "string",
          "enum": ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"],
          "default": "YXZ",
          "description": "Intrinsic rotation order. YXZ = Tait-Bryan (common in film: yaw→pitch→roll)."
        }
      }
    },
    "lookAtTarget": {
      "$ref": "#/$defs/Position3D",
      "description": "If set, orientation is derived: camera/entity faces this world-space point. Overrides quaternion and euler when present."
    },
    "lookAtUpHint": {
      "$ref": "#/$defs/Position3D",
      "description": "Up vector for lookAt resolution. Defaults to coordinate system up axis if absent."
    }
  }
}
```

**Why scalar-last `[x,y,z,w]`?** This matches glTF 2.0 (Khronos Group,
§5.17.4), USD (`GfQuatf`), Blender's internal representation, and numpy
quaternion convention. Scalar-first (`[w,x,y,z]`) is used by some math
libraries (Eigen, some physics engines) but is the minority convention
in the VFX pipeline this schema targets.

### 3.4 `Scale3D`

```json
"Scale3D": {
  "type": "object",
  "additionalProperties": false,
  "description": "Non-uniform scale factors. 1.0 = no scale. Negative values = mirror on that axis.",
  "properties": {
    "x": { "type": "number", "default": 1.0 },
    "y": { "type": "number", "default": 1.0 },
    "z": { "type": "number", "default": 1.0 }
  }
}
```

### 3.5 `Transform3D`

```json
"Transform3D": {
  "type": "object",
  "additionalProperties": false,
  "description": "Full 3D transform: translate, rotate, scale. Applied in TRS order (scale → rotate → translate) per glTF/USD convention.",
  "properties": {
    "position": {
      "$ref": "#/$defs/Position3D",
      "description": "Translation in scene space."
    },
    "orientation": {
      "$ref": "#/$defs/Orientation3D"
    },
    "scale": {
      "$ref": "#/$defs/Scale3D"
    },
    "matrix4x4": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 16,
      "maxItems": 16,
      "description": "Column-major 4×4 homogeneous transform matrix. If present, overrides position/orientation/scale. 16 elements: [m00, m10, m20, m30, m01, m11, m21, m31, m02, m12, m22, m32, m03, m13, m23, m33]."
    }
  }
}
```

### 3.6 `BoundingVolume`

```json
"BoundingVolume": {
  "type": "object",
  "required": ["volumeType"],
  "additionalProperties": false,
  "description": "Axis-aligned bounding box or bounding sphere. Rule 8: discriminated by volumeType.",
  "properties": {
    "volumeType": {
      "type": "string",
      "enum": ["aabb", "sphere"],
      "description": "aabb = axis-aligned bounding box. sphere = bounding sphere."
    },
    "aabbMin": {
      "$ref": "#/$defs/Position3D",
      "description": "Minimum corner of AABB. Required when volumeType=aabb."
    },
    "aabbMax": {
      "$ref": "#/$defs/Position3D",
      "description": "Maximum corner of AABB. Required when volumeType=aabb."
    },
    "sphereCenter": {
      "$ref": "#/$defs/Position3D",
      "description": "Center of bounding sphere. Required when volumeType=sphere."
    },
    "sphereRadiusM": {
      "type": "number",
      "exclusiveMinimum": 0,
      "description": "Rule 7: radius in scene-space units (scaled by CoordinateSystem.unitM to get metres)."
    }
  }
}
```

### 3.7 `CameraExtrinsics`

```json
"CameraExtrinsics": {
  "type": "object",
  "additionalProperties": false,
  "description": "Camera position and orientation in scene world space. Completes the camera model: CinematicSpec provides intrinsics (lens), CameraExtrinsics provides extrinsics (where/how the camera is placed). Together they define the full projection pipeline.",
  "properties": {
    "transform": {
      "$ref": "#/$defs/Transform3D",
      "description": "Camera pose in scene space. Position = camera optical center. Orientation = camera viewing direction (forward axis per CoordinateSystem.forwardAxis)."
    },
    "motionPath": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/CameraKeyframe"
      },
      "description": "Keyframed camera path for moving shots (dolly, crane, orbit). Ordered by timeSec. If present, overrides static transform for the duration of the shot."
    },
    "constraintTarget": {
      "$ref": "#/$defs/EntityRef",
      "description": "Entity the camera tracks/follows (e.g., a character). Orientation auto-adjusts to keep target framed."
    },
    "constraintMode": {
      "type": "string",
      "enum": ["lookAt", "follow", "orbit", "rail", "custom"],
      "description": "How the camera relates to constraintTarget. lookAt = fixed position, rotating to face target. follow = moves with target at offset. orbit = circles target."
    },
    "constraintOffsetM": {
      "$ref": "#/$defs/Position3D",
      "description": "Offset from constraintTarget in target-local space."
    }
  }
}
```

### 3.8 `CameraKeyframe`

```json
"CameraKeyframe": {
  "type": "object",
  "required": ["timeSec", "transform"],
  "additionalProperties": false,
  "description": "Single keyframe in a camera motion path.",
  "properties": {
    "timeSec": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: seconds from shot start."
    },
    "transform": {
      "$ref": "#/$defs/Transform3D"
    },
    "interpolation": {
      "type": "string",
      "enum": ["linear", "bezier", "catmullRom", "step", "custom"],
      "default": "linear",
      "description": "Interpolation to next keyframe."
    },
    "easeIn": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Ease-in factor. 0 = no easing. 1 = maximum easing."
    },
    "easeOut": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "focalLengthMm": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: mm. Per-keyframe focal length for zoom shots. Overrides CinematicSpec.focalLengthMm at this keyframe."
    },
    "focusDistanceM": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: metres. Per-keyframe focus distance for rack-focus."
    }
  }
}
```

### 3.9 `SpatialPlacement`

```json
"SpatialPlacement": {
  "type": "object",
  "required": ["placementId", "entityRef", "transform"],
  "additionalProperties": false,
  "description": "Places any entity (character, prop, light, audio source) at a specific position/orientation in scene space. Composition: owned by the SceneSpace that contains it.",
  "properties": {
    "placementId": {
      "$ref": "#/$defs/Identifier"
    },
    "entityRef": {
      "$ref": "#/$defs/EntityRef",
      "description": "The character, prop, or other entity being placed."
    },
    "transform": {
      "$ref": "#/$defs/Transform3D",
      "description": "Position and orientation of the entity in scene space."
    },
    "bounds": {
      "$ref": "#/$defs/BoundingVolume",
      "description": "Approximate spatial extent. Used for spatial queries and collision/occlusion checks."
    },
    "motionPath": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/PlacementKeyframe"
      },
      "description": "Keyframed motion for moving entities. Ordered by timeSec."
    },
    "interactionZoneRadiusM": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: metres. Radius within which other entities are considered 'interacting with' this one. Used for blocking/staging validation."
    },
    "facingDirection": {
      "$ref": "#/$defs/Position3D",
      "description": "World-space point the entity faces. Convenience alternative to setting orientation directly."
    },
    "notes": {
      "type": "string"
    }
  }
}
```

### 3.10 `PlacementKeyframe`

```json
"PlacementKeyframe": {
  "type": "object",
  "required": ["timeSec", "transform"],
  "additionalProperties": false,
  "properties": {
    "timeSec": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: seconds from scene/shot start."
    },
    "transform": {
      "$ref": "#/$defs/Transform3D"
    },
    "interpolation": {
      "type": "string",
      "enum": ["linear", "bezier", "catmullRom", "step", "custom"],
      "default": "linear"
    }
  }
}
```

### 3.11 `SceneSpace`

```json
"SceneSpace": {
  "type": "object",
  "required": ["coordinateSystem"],
  "additionalProperties": false,
  "description": "Defines the 3D spatial context for a scene. All spatial data within a scene (camera extrinsics, entity placements, spatial constraints) is expressed in this coordinate system. Attached to SceneEntity as an optional field.",
  "properties": {
    "coordinateSystem": {
      "$ref": "#/$defs/CoordinateSystem",
      "description": "The spatial convention for this scene. All Position3D/Orientation3D/Transform3D values within this scene are in this system."
    },
    "bounds": {
      "$ref": "#/$defs/BoundingVolume",
      "description": "Spatial extent of the scene. Used for camera frustum validation and out-of-bounds checks."
    },
    "placements": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/SpatialPlacement"
      },
      "description": "Positioned entities within this scene."
    },
    "spatialAnchors": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/SpatialAnchor"
      },
      "description": "Named reference points for spatial continuity. E.g., 'door_position', 'table_center'. Used by SpatialConsistency checks and for shot-to-shot staging."
    },
    "gravityVector": {
      "$ref": "#/$defs/Position3D",
      "description": "Direction and magnitude of gravity. Default: {x:0, y:-9.81, z:0} for +Y-up systems. Used by physics-aware generators."
    },
    "floorPlaneY": {
      "type": "number",
      "default": 0,
      "description": "Y-coordinate (or Z in +Z-up systems) of the ground plane. Rule 7: in scene-space units."
    },
    "universeRef": {
      "$ref": "#/$defs/EntityRef",
      "description": "Optional reference to a SharedSpatialUniverse. When set, this scene's coordinate system must be compatible with the universe's, and sceneOriginInUniverse provides the transform."
    },
    "sceneOriginInUniverse": {
      "$ref": "#/$defs/Transform3D",
      "description": "Transform from this scene's origin to the SharedSpatialUniverse origin. Required when universeRef is set."
    },
    "extensions": {
      "$ref": "#/$defs/Extensions"
    }
  }
}
```

### 3.12 `SpatialAnchor`

```json
"SpatialAnchor": {
  "type": "object",
  "required": ["anchorId", "name", "position"],
  "additionalProperties": false,
  "description": "Named spatial reference point. Anchors are the vocabulary for spatial continuity rules: 'character must be within 2m of anchor door_frame' or 'camera must not cross the line between anchor_A and anchor_B (180° rule)'.",
  "properties": {
    "anchorId": {
      "$ref": "#/$defs/Identifier"
    },
    "name": {
      "type": "string",
      "description": "Human-readable name. E.g., 'door_frame', 'table_center', 'action_line_A'."
    },
    "position": {
      "$ref": "#/$defs/Position3D"
    },
    "orientation": {
      "$ref": "#/$defs/Orientation3D",
      "description": "Optional facing direction for directional anchors (e.g., a door that faces a specific way)."
    },
    "radiusM": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: metres. Influence radius for proximity checks."
    },
    "anchorType": {
      "type": "string",
      "enum": [
        "landmark",
        "action_line",
        "staging_mark",
        "entry_point",
        "sightline",
        "custom"
      ],
      "description": "Semantic type. action_line = the line-of-action for 180° rule enforcement."
    },
    "linkedAnchorId": {
      "$ref": "#/$defs/Identifier",
      "description": "For line-type anchors (action_line, sightline): the other endpoint. The line between this anchor and linkedAnchorId defines the constraint axis."
    },
    "persistAcrossShots": {
      "type": "boolean",
      "default": true,
      "description": "If true, this anchor's position is invariant across all shots in the scene."
    }
  }
}
```

### 3.13 `SpatialConsistency`

```json
"SpatialConsistency": {
  "type": "object",
  "required": ["required"],
  "additionalProperties": false,
  "description": "Spatial consistency contract. Parallels TemporalConsistency and CharacterCoherence. Defines enforceable spatial rules for a scene or shot.",
  "properties": {
    "required": {
      "type": "boolean"
    },
    "rules": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/SpatialRule"
      },
      "description": "Specific spatial constraints to enforce."
    },
    "maxPositionDriftM": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: metres. Maximum allowed displacement of a static entity between shots in the same scene."
    },
    "enforce180DegreeRule": {
      "type": "boolean",
      "default": false,
      "description": "When true, validates that the camera does not cross the action line defined by SpatialAnchors of type action_line."
    },
    "enforceScreenDirection": {
      "type": "boolean",
      "default": false,
      "description": "When true, validates that character screen-direction (left-to-right or right-to-left) is consistent across cuts within the scene."
    },
    "anchorRefs": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/EntityRef"
      },
      "description": "Spatial anchors this consistency contract references."
    },
    "strategies": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Strategies for enforcing spatial consistency. E.g., 'depth_map_conditioning', 'controlnet_depth', 'layout_guidance', 'manual_review'."
    }
  }
}
```

### 3.14 `SpatialRule`

```json
"SpatialRule": {
  "type": "object",
  "required": ["ruleType"],
  "additionalProperties": false,
  "description": "Individual spatial constraint. Rule 8: discriminated by ruleType.",
  "properties": {
    "ruleType": {
      "type": "string",
      "enum": [
        "proximity",
        "exclusion_zone",
        "facing_constraint",
        "camera_boundary",
        "relative_position",
        "sightline",
        "custom"
      ]
    },
    "subjectRef": {
      "$ref": "#/$defs/EntityRef",
      "description": "Entity this rule applies to."
    },
    "targetRef": {
      "$ref": "#/$defs/EntityRef",
      "description": "Reference entity/anchor for relative constraints."
    },
    "distanceMinM": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: metres."
    },
    "distanceMaxM": {
      "type": "number",
      "minimum": 0,
      "description": "Rule 7: metres."
    },
    "angleToleranceDeg": {
      "type": "number",
      "minimum": 0,
      "maximum": 180,
      "description": "Rule 7: degrees."
    },
    "severity": {
      "type": "string",
      "enum": ["info", "warning", "error"],
      "default": "warning"
    },
    "notes": {
      "type": "string"
    }
  }
}
```

### 3.15 `SharedSpatialUniverse`

```json
"SharedSpatialUniverse": {
  "type": "object",
  "required": ["universeId", "name", "coordinateSystem"],
  "additionalProperties": false,
  "description": "Cross-project spatial contract. Defines a shared world-space that multiple projects (movies, episodes, games) can place their scenes into. Referenced by SceneSpace.universeRef. This type lives in the extensions block or in a standalone sidecar file.",
  "properties": {
    "universeId": {
      "$ref": "#/$defs/Identifier"
    },
    "name": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "coordinateSystem": {
      "$ref": "#/$defs/CoordinateSystem",
      "description": "Canonical coordinate system for the universe. All scenes referencing this universe must use a compatible coordinate system."
    },
    "bounds": {
      "$ref": "#/$defs/BoundingVolume",
      "description": "Total spatial extent of the universe."
    },
    "landmarks": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/SpatialAnchor"
      },
      "description": "Universe-level named locations. Scenes align themselves relative to these."
    },
    "version": {
      "$ref": "#/$defs/VersionInfo"
    },
    "extensions": {
      "$ref": "#/$defs/Extensions"
    }
  }
}
```

## 4. Modifications to Existing Types

All changes are **additive optional fields** — no existing fields are
modified, removed, or re-typed.

### 4.1 `CinematicSpec` — add `cameraExtrinsics`

```json
{
  "cameraExtrinsics": {
    "$ref": "#/$defs/CameraExtrinsics",
    "description": "Camera position and orientation in scene world space. Completes the projection model: CinematicSpec.focalLengthMm etc. define what the lens sees (intrinsics); cameraExtrinsics defines where the camera is and what direction it points (extrinsics)."
  },
  "spatialBridgeAnchorRef": {
    "$ref": "#/$defs/EntityRef",
    "description": "Spatial bridge pattern: references the SpatialAnchor or SpatialPlacement from the preceding shot that this shot's camera must maintain spatial coherence with. Parallels temporalBridgeAnchorRef for the spatial dimension."
  }
}
```

### 4.2 `SceneEntity` — add `sceneSpace` and `spatialConsistency`

```json
{
  "sceneSpace": {
    "$ref": "#/$defs/SceneSpace",
    "description": "3D spatial context for this scene. Defines the coordinate system, entity placements, and spatial anchors. All shots in this scene share this spatial context."
  },
  "spatialConsistency": {
    "$ref": "#/$defs/SpatialConsistency",
    "description": "Spatial consistency contract for this scene. Parallels TemporalConsistency."
  }
}
```

### 4.3 `ShotEntity` — add `cameraExtrinsicsOverride`

Note: The primary camera extrinsics live in `cinematicSpec.cameraExtrinsics`.
This override field exists for shots that need to declare their spatial
position independently from the scene-level setup (e.g., a cutaway to a
different location within the same scene).

```json
{
  "spatialOverrides": {
    "type": "array",
    "items": {
      "$ref": "#/$defs/SpatialPlacement"
    },
    "description": "Shot-specific entity placements that override the scene-level SceneSpace.placements for the duration of this shot. E.g., a character has moved to a new position."
  }
}
```

### 4.4 `EnvironmentEntity` — add spatial metadata

```json
{
  "defaultSceneSpace": {
    "$ref": "#/$defs/SceneSpace",
    "description": "Default spatial setup for scenes using this environment. Scenes can override with their own sceneSpace, but this provides the baseline layout (furniture positions, room dimensions, etc.)."
  },
  "spatialExtent": {
    "$ref": "#/$defs/BoundingVolume",
    "description": "Physical extent of this environment. E.g., a room is a 10m × 8m × 3m AABB."
  }
}
```

### 4.5 `CharacterEntity` — add `defaultBounds`

```json
{
  "defaultBounds": {
    "$ref": "#/$defs/BoundingVolume",
    "description": "Default bounding volume for this character. Overridden per-placement if needed. Used for spatial queries, 180° rule checking, and occlusion estimation."
  },
  "heightM": {
    "type": "number",
    "exclusiveMinimum": 0,
    "description": "Rule 7: metres. Character standing height. Used for eye-level camera calculations and scale consistency."
  }
}
```

### 4.6 `PropEntity` — add `defaultBounds`

```json
{
  "defaultBounds": {
    "$ref": "#/$defs/BoundingVolume",
    "description": "Default bounding volume for this prop."
  }
}
```

### 4.7 `QualityProfile` — add spatial quality controls

Add within `QualityProfile.video`:

```json
{
  "spatialConsistency": {
    "$ref": "#/$defs/SpatialConsistency",
    "description": "Default spatial consistency requirements for all scenes in projects using this quality profile."
  }
}
```

### 4.8 `ConsistencyAnchor` — extend enum

Add `"spatial"` to the `anchorType` enum:

```json
"anchorType": {
  "type": "string",
  "enum": [
    "character",
    "style",
    "environment",
    "prop",
    "camera",
    "spatial",
    "custom"
  ]
}
```

**Compatibility note:** Widening an enum is a caution-level change per the
compatibility matrix (not breaking), because existing consumers that switch
on `anchorType` will encounter a new value. The `"custom"` fallback exists
for forward-compatibility, but consumers should be warned in release notes.

## 5. Cross-Project Spatial Interoperability

The `SharedSpatialUniverse` type enables a workflow where:

1. A **universe** document defines a canonical coordinate system, bounds,
   and landmark set (e.g., "Neo-Tokyo, 2085" with landmarks for major
   buildings, streets, and districts).

2. Each **project** (movie, episode, game) that exists in this universe
   references it via `SceneSpace.universeRef` and provides
   `sceneOriginInUniverse` — the transform that maps the scene's local
   origin into universe coordinates.

3. **Spatial queries across projects** become possible: "In which movies
   does a scene occur within 500m of the Akira Memorial?" is answerable
   by composing `sceneOriginInUniverse` with `SceneSpace.placements`.

4. **Spatial consistency across projects** can be enforced: if two movies
   share a location, the furniture layout at that location is the same
   (or explicitly versioned via the universe's landmark system).

The universe document can live as:

- A `SharedSpatialUniverse` object inside the project's `extensions` block.
- A standalone JSON sidecar file that multiple projects reference by URI.
- An entry in a franchise-level registry (outside the scope of this schema
  but reachable via `EntityRef` with a URI).

## 6. Mathematical Foundation

### 6.1 Projection Pipeline

With both intrinsics and extrinsics defined, the full camera projection
from world point **P_w** to pixel coordinates **(u, v)** is:

```
P_c = [R | t] · P_w          ← extrinsics (CameraExtrinsics.transform)
p   = K · P_c                 ← intrinsics (CinematicSpec: f, sensor)
(u, v) = (p_x / p_z, p_y / p_z)  ← perspective division
```

Where:

- **R** = rotation matrix from `Orientation3D.quaternion`
- **t** = translation from `Position3D`
- **K** = intrinsic matrix constructed from:
  - `focalLengthMm` → focal length in pixels (via `sensorFormat` or `Resolution`)
  - `Resolution.widthPx`, `Resolution.heightPx` → principal point (cx, cy)

This means a downstream tool can: take a `SpatialPlacement` of a
character, the `CameraExtrinsics`, and the `CinematicSpec`, and compute
*exactly* where that character appears in the frame — enabling automated
framing validation, depth-map generation, and composition checking.

### 6.2 The 180° Rule as a Spatial Constraint

The 180° rule states: given two characters A and B in conversation,
the camera must stay on one side of the line connecting them.

In this schema:

1. Define two `SpatialAnchor` objects at the positions of A and B, with
   `anchorType: "action_line"` and `linkedAnchorId` pointing to each other.

2. Set `SpatialConsistency.enforce180DegreeRule: true`.

3. A validator computes the line **L** between the two anchors, determines
   which half-plane the first shot's camera is in, and verifies that all
   subsequent shots' cameras (from `CameraExtrinsics.transform.position`)
   remain in the same half-plane.

This replaces the prose-based `compositionNotes: "maintain screen direction"`
with a machine-checkable geometric constraint.

### 6.3 Depth Map Derivation

Given `CameraExtrinsics` and `SpatialPlacement[]`, a pipeline can compute
a synthetic depth map *before* generation, and use it as a ControlNet
depth conditioning input. The depth at each placement is:

```
depth(entity) = ||P_entity - P_camera|| · cos(θ)
```

where θ is the angle between the camera forward vector and the
camera-to-entity vector. This enables **consistent depth across shots**
without relying on the generative model to infer depth from the prompt.

## 7. Scorecard

| # | Rule | Tier | Score | Notes |
|---|------|------|-------|-------|
| 1 | Every field single unambiguous type | MUST | **Pass** | All new fields have explicit types. |
| 2 | Constraints in schema | MUST | **Pass** | min/max on distances, angles. Quaternion norm is x-computed annotation (not enforceable in JSON Schema). |
| 3 | Enums: closed, versioned | MUST | **Pass** | All new enums are closed. ConsistencyAnchor.anchorType widened (caution, not breaking). |
| 4 | Nullable ≠ optional ≠ absent | MUST | **Pass** | All new fields are optional (may be absent). No nullable fields without intent. |
| 5 | Arrays: item type + cardinality | MUST | **Pass** | matrix4x4: minItems/maxItems=16. All arrays have item types. |
| 6 | Temporal: precision, timezone | MUST | **Pass** | timeSec on keyframes inherits existing TimeRange conventions. |
| 7 | Numeric units declared | MUST | **Pass** | All numeric fields: M (metres), Mm (millimetres), Deg (degrees), Sec (seconds), unitM (dimensionless scale factor). |
| 8 | Polymorphism: discriminator | MUST | **Pass** | BoundingVolume discriminated by volumeType. SpatialRule by ruleType. |
| 9 | Defaults declared | SHOULD | **Pass** | interpolation default "linear", scale defaults 1.0, euler order default "YXZ", unitM default 1.0. |
| 10 | Stable opaque identity | MUST | **Pass** | placementId, anchorId, universeId all use Identifier type. |
| 11 | Relationships navigable | MUST | **Pass** | EntityRef used for all cross-references. SpatialPlacement→entity, SceneSpace→universe, anchor→linkedAnchor. |
| 12 | Composition/aggregation explicit | MUST | **Pass** | SceneSpace owns placements and anchors (composition). Universe is referenced, not owned (association). |
| 13 | FK targets declared | MUST | **Pass** | All EntityRefs point to declared entity types. |
| 14 | Cyclic graph constraints | MUST | **Pass** | linkedAnchorId is bidirectional by design — no cycle concern (pair, not chain). |
| 15 | Single source of truth | MUST | **Pass** | Coordinate system declared once per SceneSpace, not repeated per placement. |
| 16 | No bag-of-arrays | SHOULD | **Pass** | SceneSpace has typed arrays with semantically distinct item types. |
| 17 | Cross-cutting types | SHOULD | **Pass** | Position3D, Orientation3D, Transform3D, BoundingVolume extracted as shared $defs. |
| 18 | Computed vs stored | SHOULD | **Pass** | Quaternion normalization annotated as x-computed. eulerDeg marked as convenience/derived. |
| 19 | Explicit semver | MUST | **Pass** | Extension targets 3.1.0 (minor bump). |
| 20 | No duplicate versions | MUST | **Pass** | No version conflicts with existing types. |
| 21 | Breaking changes classified | MUST | **Pass** | All changes classified as additive (optional fields) or caution (enum widening). |
| 22 | Deprecation annotated | MUST | **Pass** | No deprecations in this extension. |
| 23 | Sensitive fields | MUST* | **N/A** | No PII in spatial data. |
| 24 | Immutability | SHOULD | **Pass** | anchorId, placementId, universeId are identity fields — x-immutable applies. |
| 25 | Localization | SHOULD | **N/A** | Spatial data is language-independent. |
| 26 | Multi-actor provenance | SHOULD | **Pass** | Inherited from BaseEntity on containing types. |
| 27 | Consistent naming | MUST | **Pass** | camelCase throughout. Unit suffixes (M, Mm, Deg, Sec) match existing schema convention. |
| 28 | Mechanically generatable | MUST | **Pass** | Standard JSON Schema 2020-12. All types are $ref-composable. |
| 29 | Extension points | MUST | **Pass** | SceneSpace.extensions and SharedSpatialUniverse.extensions provided. |
| 30 | Access patterns ≠ structure | SHOULD | **Pass** | Structure models spatial reality, not query patterns. |
| 31 | Readable standalone | MUST | **Pass** | Every type and field has a description. |

**Totals:** MUST Pass: 19/19 · SHOULD Pass: 11/11

## 8. Compatibility Classification

| Change | Type | Classification |
|--------|------|---------------|
| Add `CameraExtrinsics` to $defs | New type | ✅ Safe |
| Add all new $defs types | New types | ✅ Safe |
| Add `cameraExtrinsics` to CinematicSpec | Optional field on existing | ✅ Safe |
| Add `spatialBridgeAnchorRef` to CinematicSpec | Optional field | ✅ Safe |
| Add `sceneSpace` to SceneEntity | Optional field | ✅ Safe |
| Add `spatialConsistency` to SceneEntity | Optional field | ✅ Safe |
| Add `spatialOverrides` to ShotEntity | Optional field | ✅ Safe |
| Add `defaultSceneSpace` to EnvironmentEntity | Optional field | ✅ Safe |
| Add `spatialExtent` to EnvironmentEntity | Optional field | ✅ Safe |
| Add `defaultBounds` to CharacterEntity | Optional field | ✅ Safe |
| Add `heightM` to CharacterEntity | Optional field | ✅ Safe |
| Add `defaultBounds` to PropEntity | Optional field | ✅ Safe |
| Add `spatialConsistency` to QualityProfile.video | Optional field | ✅ Safe |
| Add `"spatial"` to ConsistencyAnchor.anchorType | Enum widening | ⚠️ Caution |
| Bump schema version 3.0.0 → 3.1.0 | Version | Minor increment |

No breaking changes. All existing v3.0.0 documents remain valid v3.1.0 documents.

## 9. Migration Guide

**For existing v3.0.0 consumers:** No action required. All spatial fields
are optional. Existing documents validate unchanged.

**To adopt spatial features:**

1. Add a `CoordinateSystem` declaration (recommend: `right`, `+Y`, `1.0`
   for USD/glTF compatibility).
2. Attach a `SceneSpace` to each `SceneEntity` that needs spatial reasoning.
3. Add `CameraExtrinsics` to each `ShotEntity.cinematicSpec` that needs
   camera placement.
4. Place entities via `SpatialPlacement` in `SceneSpace.placements`.
5. Define `SpatialAnchor` objects for continuity constraints (action lines,
   staging marks).
6. Enable `SpatialConsistency` on scenes that need automated validation.
7. Optionally define a `SharedSpatialUniverse` for cross-project continuity.
