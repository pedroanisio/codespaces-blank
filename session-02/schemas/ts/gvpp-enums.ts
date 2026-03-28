/**
 * ─────────────────────────────────────────────────────────────────────────────
 * DISCLAIMER
 * ─────────────────────────────────────────────────────────────────────────────
 * No information within this file should be taken for granted. Any statement
 * or premise not backed by a real logical definition or verifiable reference
 * may be invalid, erroneous, or a hallucination.
 *
 * gvpp-enums.ts — Recommended value registries for open string fields
 * and re-exports of closed enums from the v3 GVPP schema.
 *
 * Fields marked "CLOSED" are constrained by the schema itself.
 * Fields marked "OPEN" accept any string — these values are advisory.
 *
 * Depends on: nothing (pure constants)
 * ─────────────────────────────────────────────────────────────────────────────
 */

// ═══════════════════════════════════════════════════════════════════════════════
// §1  OPERATIONS (CLOSED — discriminated on opType)
// ═══════════════════════════════════════════════════════════════════════════════

/** Operation.opType — closed union discriminator */
export const OPERATION_TYPES = [
  "concat", "overlay", "colorGrade", "audioMix", "transition",
  "filter", "encode", "manim", "retime", "custom",
] as const;
export type OperationType = (typeof OPERATION_TYPES)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §2  WORKFLOW NODES (CLOSED — discriminated on nodeType)
// ═══════════════════════════════════════════════════════════════════════════════

/** WorkflowNode.nodeType — closed union discriminator */
export const WORKFLOW_NODE_TYPES = [
  "generation", "approval", "transform", "render",
  "validation", "notification", "custom",
] as const;
export type WorkflowNodeType = (typeof WORKFLOW_NODE_TYPES)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §3  GENERATION / PROVENANCE
// ═══════════════════════════════════════════════════════════════════════════════

/** GenerationStep.operationType (OPEN) */
export const GENERATION_OPERATION_TYPES = [
  "text_to_image", "image_to_image", "text_to_video", "image_to_video",
  "video_to_video", "text_to_audio", "text_to_speech", "speech_to_speech",
  "audio_to_audio", "inpainting", "outpainting", "upscale",
  "interpolation", "style_transfer", "depth_estimation", "segmentation",
  "compositing", "color_grading", "denoising", "stabilization",
  "lip_sync", "face_swap", "motion_transfer", "background_removal",
  "super_resolution", "frame_interpolation", "manual_edit",
  "review", "approval",
] as const;
export type GenerationOperationType = (typeof GENERATION_OPERATION_TYPES)[number];

/** GenerationStep.status (CLOSED in v3) */
export const GENERATION_STEP_STATUSES = [
  "pending", "running", "succeeded", "failed", "cancelled",
] as const;
export type GenerationStepStatus = (typeof GENERATION_STEP_STATUSES)[number];

/** ConsistencyAnchor.anchorType (CLOSED in v3) */
export const CONSISTENCY_ANCHOR_TYPES = [
  "character", "style", "environment", "prop", "camera", "spatial", "custom",
] as const;
export type ConsistencyAnchorType = (typeof CONSISTENCY_ANCHOR_TYPES)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §4  SHOT / CAMERA (OPEN)
// ═══════════════════════════════════════════════════════════════════════════════

/** CinematicSpec.shotType */
export const SHOT_TYPES = [
  "establishing", "wide", "full", "medium_wide", "medium",
  "medium_close_up", "close_up", "extreme_close_up", "insert",
  "cutaway", "over_the_shoulder", "two_shot", "group",
  "aerial", "pov", "reaction",
] as const;
export type ShotType = (typeof SHOT_TYPES)[number];

/** CinematicSpec.cameraAngle */
export const CAMERA_ANGLES = [
  "eye_level", "low_angle", "high_angle", "birds_eye",
  "worms_eye", "dutch_angle", "over_the_shoulder", "top_down",
] as const;
export type CameraAngle = (typeof CAMERA_ANGLES)[number];

/** CinematicSpec.cameraMovement */
export const CAMERA_MOVEMENTS = [
  "static", "pan_left", "pan_right", "tilt_up", "tilt_down",
  "dolly_in", "dolly_out", "truck_left", "truck_right",
  "pedestal_up", "pedestal_down", "crane", "jib", "steadicam",
  "handheld", "zoom_in", "zoom_out", "rack_focus", "follow",
  "orbit", "whip_pan", "roll", "drone_fly_through",
] as const;
export type CameraMovement = (typeof CAMERA_MOVEMENTS)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §5  SCRIPT / NARRATIVE
// ═══════════════════════════════════════════════════════════════════════════════

/** ScriptSegment.segmentType (CLOSED in v3) */
export const SEGMENT_TYPES = [
  "scene_heading", "action", "dialogue", "parenthetical",
  "transition", "title_card", "voice_over", "on_screen_text", "custom",
] as const;
export type SegmentType = (typeof SEGMENT_TYPES)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §6  TRANSITIONS (OPEN)
// ═══════════════════════════════════════════════════════════════════════════════

export const TRANSITION_TYPES = [
  "cut", "dissolve", "crossfade", "fade_in", "fade_out",
  "fade_to_black", "fade_to_white", "wipe_left", "wipe_right",
  "wipe_up", "wipe_down", "iris_in", "iris_out", "push", "slide",
  "morph", "match_cut", "j_cut", "l_cut", "smash_cut", "jump_cut",
] as const;
export type TransitionType = (typeof TRANSITION_TYPES)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §7  ASSETS (OPEN unless noted)
// ═══════════════════════════════════════════════════════════════════════════════

/** MarketingAssetEntity.marketingType (CLOSED in v3) */
export const MARKETING_ASSET_TYPES = [
  "trailer", "teaser", "thumbnail", "social_clip",
  "poster", "banner", "press_kit", "custom",
] as const;
export type MarketingAssetType = (typeof MARKETING_ASSET_TYPES)[number];

/** VisualAssetEntity.visualType (OPEN) */
export const VISUAL_ASSET_TYPES = [
  "reference_image", "style_reference", "character_sheet",
  "environment_concept", "storyboard_frame", "animatic_frame",
  "color_palette", "mood_board", "texture", "lut", "matte",
  "depth_map", "normal_map", "generated_frame", "generated_clip",
  "composited_clip", "final_render",
] as const;
export type VisualAssetType = (typeof VISUAL_ASSET_TYPES)[number];

/** AudioAssetEntity.audioType (OPEN) */
export const AUDIO_ASSET_TYPES = [
  "dialogue", "voiceover", "narration", "music_score",
  "music_licensed", "sound_effect", "ambient", "foley",
  "voice_reference", "mix_stem", "final_mix",
] as const;
export type AudioAssetType = (typeof AUDIO_ASSET_TYPES)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §8  VALIDATION / QUALITY
// ═══════════════════════════════════════════════════════════════════════════════

/** ValidationRule.operator (CLOSED in v3) */
export const VALIDATION_OPERATORS = [
  "eq", "neq", "gt", "gte", "lt", "lte", "in", "nin", "matches", "exists",
] as const;
export type ValidationOperator = (typeof VALIDATION_OPERATORS)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §9  RELATIONSHIPS / DELIVERABLES (OPEN)
// ═══════════════════════════════════════════════════════════════════════════════

export const RELATIONSHIP_TYPES = [
  "depends_on", "derived_from", "supersedes", "references",
  "contains", "variant_of", "alternative_to", "conflicts_with",
  "requires", "enhances", "illustrates", "scored_by",
  "narrated_by", "approved_by",
] as const;
export type RelationshipType = (typeof RELATIONSHIP_TYPES)[number];

export const OUTPUT_TYPES = [
  "master", "distribution", "proxy", "preview",
  "dailies", "archive", "platform_specific",
] as const;
export type OutputType = (typeof OUTPUT_TYPES)[number];

export const RELEASE_CHANNELS = [
  "internal", "staging", "beta", "production", "syndication",
] as const;
export type ReleaseChannel = (typeof RELEASE_CHANNELS)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §10  WORKFLOW STATUS (CLOSED in v3)
// ═══════════════════════════════════════════════════════════════════════════════

export const WORKFLOW_STATUSES = [
  "pending", "running", "paused", "succeeded", "failed", "cancelled",
] as const;
export type WorkflowStatus = (typeof WORKFLOW_STATUSES)[number];

// ═══════════════════════════════════════════════════════════════════════════════
// §11  VERSION / ENTITY LIFECYCLE (CLOSED in v3)
// ═══════════════════════════════════════════════════════════════════════════════

export const VERSION_STATES = [
  "draft", "in_progress", "generating", "review", "changes_requested",
  "approved", "published", "archived", "deprecated",
] as const;
export type VersionState = (typeof VERSION_STATES)[number];

export const ENTITY_STATUSES = [
  "draft", "in_progress", "generating", "review", "changes_requested",
  "approved", "published", "archived", "deprecated",
] as const;
export type EntityStatus = (typeof ENTITY_STATUSES)[number];
