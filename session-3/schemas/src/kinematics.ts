import { z } from "zod";
import {
  BoneId,
  JointId,
  SegmentId,
  PoseId,
  Vector3Schema,
  RigidPoseSchema,
  QuaternionSchema,
  SymmetricTensor3Schema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Kinematics — Positions, Orientations, Poses, Motion
//
// This module models the *configuration space* of the body: how every rigid
// segment is positioned and oriented in space at any instant, and how those
// configurations change over time.
//
// Coordinate convention follows the International Society of Biomechanics
// (ISB) recommendations:
//   - Wu & Cavanagh, J Biomech 28(10):1257–1261, 1995 (general)
//   - Wu et al., J Biomech 35(4):543–548, 2002 (upper extremity)
//   - Wu et al., J Biomech 38(5):981–992, 2005 (lower extremity)
//
// Global frame: +X = anterior, +Y = superior (up), +Z = right lateral.
// This matches ISB and most musculoskeletal simulation tools (OpenSim, AnyBody).
// =============================================================================

// --- Reference Frame ---

export const ReferenceFrameTypeEnum = z.enum([
  "global",            // Lab/world fixed frame
  "segment_anatomical", // Anatomical coordinate system (ACS) of a body segment
  "segment_technical",  // Marker-based technical frame
  "joint",             // Joint coordinate system (JCS) per Grood-Suntay
  "custom",            // User-defined
]);

export const ReferenceFrameSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  type: ReferenceFrameTypeEnum,

  // Pose of this frame expressed in its parent frame.
  // For the global frame, this is identity (position = 0, orientation = identity quaternion).
  parentFrameId: z
    .string()
    .uuid()
    .nullable()
    .describe("Parent frame ID; null = this IS the global frame"),
  poseInParent: RigidPoseSchema.describe(
    "Pose (position + orientation) of this frame's origin in the parent frame",
  ),

  // Axis labels — ISB convention by default, but customizable
  axisLabels: z
    .object({
      x: z.string().default("anterior").describe("Semantic label for +X"),
      y: z.string().default("superior").describe("Semantic label for +Y"),
      z: z.string().default("right_lateral").describe("Semantic label for +Z"),
    })
    .optional(),

  // Which anatomical entity this frame is attached to
  attachedBoneId: BoneId.optional().describe("Bone this frame is rigidly attached to (if segment frame)"),
  attachedJointId: JointId.optional().describe("Joint this frame describes (if JCS)"),

  extensions: ExtensionsSchema,
});

// --- Body Segment ---
// A rigid body between adjacent joints. This is the fundamental unit of
// multibody dynamics. Each segment has mass, center of mass, inertia, and
// a local coordinate frame.
//
// Note: segments are NOT bones — a segment may span multiple bones (e.g.
// the "foot" segment includes tarsals, metatarsals, and phalanges treated
// as a single rigid body for gait analysis). Conversely, a single bone
// like the femur IS a segment.

export const BodySegmentSchema = z.object({
  id: SegmentId,
  name: z.string().min(1).describe("Anatomical name (e.g. 'thigh', 'shank', 'foot', 'head-neck')"),

  // Which bones compose this segment (1 or more, treated as rigid)
  boneIds: z
    .array(BoneId)
    .min(1)
    .describe("Bones that compose this rigid segment (ordered: proximal first)"),

  // Joints at proximal and distal ends
  proximalJointId: JointId.nullable().describe("Joint at the proximal end; null for root segment (pelvis)"),
  distalJointIds: z
    .array(JointId)
    .describe("Joints at the distal end(s). Usually 1, but pelvis has 2 (L/R hip) + spine."),

  // Segment coordinate system
  coordinateFrame: ReferenceFrameSchema.optional().describe(
    "Anatomical coordinate system of this segment. If omitted, derived from bone transforms.",
  ),

  // Inertial properties of the segment as a whole
  // Reference: De Leva, J Biomech 29(9):1223–1230, 1996.
  mass: z.number().positive().describe("Segment mass in kg"),
  centerOfMass: Vector3Schema.describe(
    "Center of mass in the segment's local frame (cm). " +
    "Convention: expressed as offset from proximal joint center. " +
    "[Authority: authoritative for multibody dynamics — " +
    "overrides per-bone centerOfMass when a segment aggregates multiple bones.]",
  ),
  centerOfMassRatio: z
    .number()
    .min(0)
    .max(1)
    .optional()
    .describe(
      "CoM position as fraction of segment length from proximal end (0 = proximal, 1 = distal). " +
      "De Leva (1996) tables provide standard values per segment.",
    ),
  inertiaTensor: SymmetricTensor3Schema.describe(
    "Moment of inertia tensor about the CoM in the segment's local frame (kg·cm²). " +
    "[Authority: authoritative for multibody dynamics — " +
    "overrides per-bone inertiaTensor when a segment aggregates multiple bones.]",
  ),
  segmentLength: z.number().positive().describe("Length from proximal to distal joint center (cm)"),

  // Radius of gyration ratios — alternative to full tensor, commonly
  // used in biomechanics for quick estimation.
  // ρ = k/L where k = radius of gyration, L = segment length.
  gyrationRatios: z
    .object({
      sagittal: z.number().min(0).max(1).describe("ρ about the mediolateral axis (sagittal plane motion)"),
      frontal: z.number().min(0).max(1).describe("ρ about the anteroposterior axis (frontal plane motion)"),
      transverse: z.number().min(0).max(1).describe("ρ about the longitudinal axis (transverse plane rotation)"),
    })
    .optional()
    .describe("Normalized radii of gyration (k/L). See De Leva 1996, Table 4."),

  extensions: ExtensionsSchema,
});

// --- Joint State ---
// The instantaneous configuration of a single joint: angles for each
// degree of freedom and optionally angular velocities/accelerations.

export const JointStateSchema = z.object({
  jointId: JointId,

  // Angles follow the Grood-Suntay joint coordinate system convention.
  // Sign: positive = flexion, abduction, internal rotation (right-hand rule
  // about the respective axis).
  angles: z.object({
    flexionExtension: z.number().default(0).describe("Angle about primary axis (degrees)"),
    abductionAdduction: z.number().default(0).describe("Angle about floating axis (degrees)"),
    internalExternalRotation: z.number().default(0).describe("Angle about distal axis (degrees)"),
  }),

  // First and second time derivatives (optional — present during motion analysis)
  angularVelocity: z
    .object({
      flexionExtension: z.number().describe("deg/s"),
      abductionAdduction: z.number().describe("deg/s"),
      internalExternalRotation: z.number().describe("deg/s"),
    })
    .optional()
    .describe("Joint angular velocity per DOF (degrees/s)"),

  angularAcceleration: z
    .object({
      flexionExtension: z.number().describe("deg/s²"),
      abductionAdduction: z.number().describe("deg/s²"),
      internalExternalRotation: z.number().describe("deg/s²"),
    })
    .optional()
    .describe("Joint angular acceleration per DOF (degrees/s²)"),

  extensions: ExtensionsSchema,
});

// --- Segment Spatial State ---
// The instantaneous position, orientation, and motion of a body segment
// in the global reference frame.

export const SegmentSpatialStateSchema = z.object({
  segmentId: SegmentId,

  // Pose in global frame
  globalPose: RigidPoseSchema.describe("Position + orientation of the segment's local frame in the global frame"),

  // Computed world-space CoM position
  globalCenterOfMass: Vector3Schema.optional().describe(
    "Center of mass position in global frame (cm) — computed from globalPose + local CoM",
  ),

  // Linear kinematics of the CoM
  linearVelocity: Vector3Schema.optional().describe("Velocity of the CoM in global frame (cm/s)"),
  linearAcceleration: Vector3Schema.optional().describe("Acceleration of the CoM in global frame (cm/s²)"),

  // Angular kinematics of the segment
  angularVelocity: Vector3Schema.optional().describe("Angular velocity in global frame (deg/s)"),
  angularAcceleration: Vector3Schema.optional().describe("Angular acceleration in global frame (deg/s²)"),

  extensions: ExtensionsSchema,
});

// --- Pose ---
// A complete snapshot of the body's configuration at one instant.
// Contains joint angles for every articulated joint and the resulting
// segment positions. This is the primary entity for representing
// "any body position."

export const PoseSchema = z.object({
  id: PoseId,
  name: z.string().optional().describe("Human-readable label (e.g. 'anatomical_position', 'mid_stance', 'seated_relaxed')"),

  // Timestamp — optional. Present for motion capture data, absent for
  // static named poses.
  timestamp: z.number().nonnegative().optional().describe("Time in seconds from the start of a recording or sequence"),

  // The global pose of the root segment (typically pelvis). All other
  // segment positions are derived from this + joint angles via forward
  // kinematics.
  rootSegmentId: SegmentId.describe("Which segment is the kinematic root (usually pelvis)"),
  rootPose: RigidPoseSchema.describe(
    "Position and orientation of the root segment in the global frame. " +
    "This anchors the entire kinematic chain in world space.",
  ),

  // Joint states — one per articulated joint
  jointStates: z
    .array(JointStateSchema)
    .min(1)
    .describe("Joint angle state for every articulated joint (ordered: proximal to distal)"),

  // Segment spatial states — derived from forward kinematics but stored
  // for quick access. Marked as computed (Rule 18).
  segmentStates: z
    .array(SegmentSpatialStateSchema)
    .optional()
    .describe("[Computed] World-space state of each segment, derived from rootPose + jointStates via FK"),

  // Whole-body center of mass — computed from segment masses and positions
  wholeBodyCenterOfMass: Vector3Schema
    .optional()
    .describe("[Computed] Whole-body CoM in global frame (cm). Σ(mᵢ·rᵢ) / Σ(mᵢ)"),

  extensions: ExtensionsSchema,
});

// --- Motion Sequence ---
// An ordered, time-indexed series of poses representing continuous
// movement. This is what you get from motion capture, animation
// keyframes, or biomechanical simulation output.

export const MotionSequenceSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).describe("Descriptive name (e.g. 'normal_gait_cycle', 'squat_3RM')"),

  sampleRate: z.number().positive().optional().describe("Capture/sample rate in Hz"),
  duration: z.number().positive().optional().describe("Total duration in seconds"),

  // Ordered poses — must be chronologically sorted by timestamp
  poses: z
    .array(PoseSchema)
    .min(1)
    .describe("Ordered sequence of poses (ascending timestamp)"),

  // Interpolation hint for consumers
  interpolation: z
    .enum(["linear", "cubic_spline", "slerp", "none"])
    .default("linear")
    .describe("Recommended interpolation between keyframes. 'slerp' for rotations, 'linear'/'cubic_spline' for positions."),

  extensions: ExtensionsSchema,
});

// --- Named Pose Presets ---
// Standard anatomical positions that serve as reference configurations.

export const StandardPoseEnum = z.enum([
  "anatomical",         // Standing upright, palms forward
  "neutral_standing",   // Standing relaxed, arms at sides
  "t_pose",            // Arms extended laterally (common in rigging)
  "a_pose",            // Arms ~30° abducted (common in animation)
  "seated_upright",    // 90° hip and knee flexion
  "supine",            // Lying face up
  "prone",             // Lying face down
]);

// --- Inferred Types ---

export type ReferenceFrame = z.infer<typeof ReferenceFrameSchema>;
export type BodySegment = z.infer<typeof BodySegmentSchema>;
export type JointState = z.infer<typeof JointStateSchema>;
export type SegmentSpatialState = z.infer<typeof SegmentSpatialStateSchema>;
export type Pose = z.infer<typeof PoseSchema>;
export type MotionSequence = z.infer<typeof MotionSequenceSchema>;
