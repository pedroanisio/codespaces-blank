import { z } from "zod";
import {
  BoneId,
  JointId,
  TransformSchema,
  Vector3Schema,
  SymmetricTensor3Schema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Skeletal System
// =============================================================================

// --- Bone ---

export const BoneClassEnum = z.enum([
  "long",       // femur, humerus
  "short",      // carpals, tarsals
  "flat",       // scapula, sternum
  "irregular",  // vertebrae, sacrum
  "sesamoid",   // patella
]);

export const BoneRegionEnum = z.enum([
  "axial_cranium",
  "axial_face",
  "axial_vertebral",
  "axial_thorax",
  "appendicular_upper",
  "appendicular_lower",
  "appendicular_pelvic",
  "appendicular_pectoral",
]);

export const BoneSchema = z.object({
  id: BoneId,
  name: z.string().min(1),
  classification: BoneClassEnum,
  region: BoneRegionEnum,
  transform: TransformSchema,

  // Dimensions — units explicit per Rule 7
  length: z.number().positive().describe("Length in cm"),
  width: z.number().positive().describe("Maximum width in cm"),
  depth: z.number().positive().optional().describe("Maximum depth in cm (for non-cylindrical bones)"),
  mass: z.number().positive().describe("Mass in grams"),

  // Inertial properties — required for inverse dynamics.
  // Reference: De Leva, "Adjustments to Zatsiorsky-Seluyanov's segment
  // inertia parameters", J Biomech 29(9):1223–1230, 1996.
  centerOfMass: Vector3Schema
    .optional()
    .describe("Center of mass position in the bone's local frame (cm). " +
      "Typically expressed as a fraction of segment length from proximal end. " +
      "[Authority: subordinate to BodySegment.centerOfMass for dynamics — " +
      "segment-level values are authoritative for multibody analysis; " +
      "bone-level values are anatomical detail for single-bone models.]"),
  inertiaTensor: SymmetricTensor3Schema
    .optional()
    .describe("Moment of inertia tensor about the center of mass in the bone's local frame (g·cm²). " +
      "[Authority: subordinate to BodySegment.inertiaTensor for dynamics — " +
      "a segment may aggregate multiple bones into a single rigid body.]"),

  // Hierarchy — bones form a tree (acyclic by definition: Rule 14)
  parentBoneId: BoneId.nullable().describe("Parent bone in the skeletal hierarchy; null for root (e.g. pelvis)"),

  extensions: ExtensionsSchema,
});

// --- Joint ---

export const JointTypeEnum = z.enum([
  "ball_and_socket",  // shoulder, hip
  "hinge",            // elbow, knee
  "pivot",            // atlas-axis
  "condyloid",        // wrist
  "saddle",           // thumb CMC
  "plane",            // intercarpal
  "fixed",            // skull sutures
  "cartilaginous",    // intervertebral discs
]);

export const JointLimitSchema = z.object({
  min: z.number().describe("Minimum angle in degrees"),
  max: z.number().describe("Maximum angle in degrees"),
}).refine((l) => l.min <= l.max, {
  message: "Joint limit min must be ≤ max",
});

export const JointSchema = z.object({
  id: JointId,
  name: z.string().min(1),
  type: JointTypeEnum,
  transform: TransformSchema,

  // Bones articulated by this joint. Most joints connect 2, but composite
  // joints (e.g. knee: femur, tibia, patella) may articulate 3.
  connectedBoneIds: z
    .array(BoneId)
    .min(2)
    .max(4)
    .describe("IDs of bones articulated by this joint (2–4, ordered: proximal first)"),

  degreesOfFreedom: z.number().int().min(0).max(6).describe("0 = fixed (synarthrosis), 1–3 typical, up to 6 theoretical"),

  // Joint axes — local rotation axes in the proximal segment's coordinate frame.
  // For a hinge joint, only primaryAxis is needed. For ball-and-socket, all three.
  // Reference: Grood & Suntay, "A joint coordinate system for the clinical
  // description of three-dimensional motions", J Biomech Eng 105(2):136–144, 1983.
  axes: z
    .object({
      primary: Vector3Schema.optional().describe("Primary rotation axis in proximal segment frame (e.g. flexion/extension)"),
      secondary: Vector3Schema.optional().describe("Secondary axis (e.g. abduction/adduction) — floating axis in JCS"),
      tertiary: Vector3Schema.optional().describe("Tertiary axis (e.g. internal/external rotation) — distal segment axis"),
    })
    .optional()
    .describe("Joint coordinate system axes per Grood-Suntay convention"),

  limits: z
    .object({
      flexionExtension: JointLimitSchema.optional().describe("Sagittal plane"),
      abductionAdduction: JointLimitSchema.optional().describe("Frontal plane"),
      internalExternalRotation: JointLimitSchema.optional().describe("Transverse plane"),
    })
    .optional()
    .describe("Range of motion limits by anatomical plane"),

  extensions: ExtensionsSchema,
});

// --- Inferred Types ---

export type Bone = z.infer<typeof BoneSchema>;
export type Joint = z.infer<typeof JointSchema>;
