import { z } from "zod";

// =============================================================================
// human-body-schema / shared.ts
// Schema version: 2.0.0 (breaking changes from 1.x — see CHANGELOG.md)
// =============================================================================

export const SCHEMA_VERSION = "3.0.0" as const;

// --- Branded ID Types ---
// Provide semantic safety over raw UUID strings. Consumers can cast
// `string` → `BoneId` only intentionally, preventing accidental cross-entity
// references at the type level.

const brandedUuid = (brand: string) =>
  z.string().uuid().describe(`Opaque unique identifier (${brand})`);

export const BoneId = brandedUuid("BoneId");
export const MuscleId = brandedUuid("MuscleId");
export const JointId = brandedUuid("JointId");
export const OrganId = brandedUuid("OrganId");
export const VesselId = brandedUuid("VesselId");
export const NerveId = brandedUuid("NerveId");
export const TendonId = brandedUuid("TendonId");
export const ClothingId = brandedUuid("ClothingId");
export const SegmentId = brandedUuid("SegmentId");
export const PoseId = brandedUuid("PoseId");
export const ForceId = brandedUuid("ForceId");
export const MomentId = brandedUuid("MomentId");
export const LoadingConditionId = brandedUuid("LoadingConditionId");
export const ContactId = brandedUuid("ContactId");

// --- Geometry Primitives ---

export const Vector3Schema = z.object({
  x: z.number(),
  y: z.number(),
  z: z.number(),
});

/** Unit-length direction vector. Consumer code should normalize; the schema
 *  records the constraint but Zod cannot enforce magnitude at parse time
 *  without a `refine`, which is added below. */
export const UnitVector3Schema = Vector3Schema.refine(
  (v) => {
    const mag = Math.sqrt(v.x ** 2 + v.y ** 2 + v.z ** 2);
    return Math.abs(mag - 1.0) < 1e-3;
  },
  { message: "Vector must be unit-length (magnitude ≈ 1.0)" },
);

export const TransformSchema = z.object({
  position: Vector3Schema.describe("Position in 3D space (cm)"),
  rotation: Vector3Schema.describe("Rotation as Euler angles (degrees, XYZ intrinsic order)"),
  scale: Vector3Schema.describe("Per-axis scale multiplier (1.0 = identity)"),
});

// --- Quaternion ---
// For rotation representation without gimbal lock. Hamilton convention (w, x, y, z).
// Reference: Kuipers, "Quaternions and Rotation Sequences" (1999).

export const QuaternionSchema = z
  .object({
    w: z.number().describe("Scalar (real) component"),
    x: z.number().describe("i component"),
    y: z.number().describe("j component"),
    z: z.number().describe("k component"),
  })
  .refine(
    (q) => {
      const mag = Math.sqrt(q.w ** 2 + q.x ** 2 + q.y ** 2 + q.z ** 2);
      return Math.abs(mag - 1.0) < 1e-3;
    },
    { message: "Quaternion must be unit-length (magnitude ≈ 1.0)" },
  );

// --- Rigid Body Pose (SE(3) element) ---
// Position + orientation without scale. Used for kinematics where scale is
// meaningless (a bone's pose in space has no "scale" — it has a position and
// an orientation).

export const RigidPoseSchema = z.object({
  position: Vector3Schema.describe("Translation from the parent frame origin (cm)"),
  orientation: QuaternionSchema.describe("Rotation from the parent frame (unit quaternion, Hamilton convention)"),
});

// --- Symmetric 3×3 Tensor ---
// Used for inertia tensors. A symmetric 3×3 matrix has 6 independent
// components: Ixx, Iyy, Izz (diagonal) and Ixy, Ixz, Iyz (off-diagonal).
// Reference: Goldstein, "Classical Mechanics", 3rd ed. (2002), Ch. 5.

export const SymmetricTensor3Schema = z.object({
  xx: z.number().describe("Diagonal component (row 1, col 1)"),
  yy: z.number().describe("Diagonal component (row 2, col 2)"),
  zz: z.number().describe("Diagonal component (row 3, col 3)"),
  xy: z.number().describe("Off-diagonal (row 1, col 2) = (row 2, col 1)"),
  xz: z.number().describe("Off-diagonal (row 1, col 3) = (row 3, col 1)"),
  yz: z.number().describe("Off-diagonal (row 2, col 3) = (row 3, col 2)"),
});

export const ColorSchema = z.object({
  r: z.number().int().min(0).max(255),
  g: z.number().int().min(0).max(255),
  b: z.number().int().min(0).max(255),
  a: z.number().min(0).max(1).default(1),
});

// --- Extension Point (Rule 29) ---
// Consumers can attach arbitrary domain metadata to any entity that includes
// this field. Keys SHOULD be namespaced ("vendor:key") to avoid collisions.

export const ExtensionsSchema = z
  .record(z.string(), z.unknown())
  .optional()
  .describe("Namespaced extension metadata (vendor:key → value)");

// --- Inferred Shared Types ---

export type Vector3 = z.infer<typeof Vector3Schema>;
export type Transform = z.infer<typeof TransformSchema>;
export type Quaternion = z.infer<typeof QuaternionSchema>;
export type RigidPose = z.infer<typeof RigidPoseSchema>;
export type SymmetricTensor3 = z.infer<typeof SymmetricTensor3Schema>;
export type Color = z.infer<typeof ColorSchema>;
