import { z } from "zod";
import {
  BoneId,
  MuscleId,
  TendonId,
  NerveId,
  VesselId,
  Vector3Schema,
  UnitVector3Schema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Muscular System
// =============================================================================

// --- Tendon ---

export const TendonSchema = z.object({
  id: TendonId,
  name: z.string().min(1),
  attachedBoneId: BoneId.describe("Bone this tendon connects to"),
  localPosition: Vector3Schema.describe("Local position on the bone surface (cm)"),
  surfaceArea: z.number().positive().optional().describe("Surface area of attachment in cm²"),
  length: z.number().positive().describe("Tendon length in cm"),
  crossSectionalArea: z.number().positive().optional().describe("Cross-sectional area in cm²"),
  extensions: ExtensionsSchema,
});

// --- Fascicle Architecture ---
// Determines force production characteristics. This is not just
// a cosmetic label — pennation angle directly affects the physiological
// cross-sectional area (PCSA) calculation.

export const FascicleArchitectureEnum = z.enum([
  "parallel",       // sartorius — long excursion, lower force
  "convergent",     // pectoralis major
  "unipennate",     // extensor digitorum longus
  "bipennate",      // rectus femoris
  "multipennate",   // deltoid
  "circular",       // orbicularis oris
  "fusiform",       // biceps brachii
]);

// --- Muscle Enums ---

export const MuscleRegionEnum = z.enum([
  "head_and_neck",
  "face",
  "thorax_anterior",
  "thorax_posterior",
  "abdomen",
  "back_superficial",
  "back_deep",
  "shoulder",
  "arm_anterior",
  "arm_posterior",
  "forearm_anterior",
  "forearm_posterior",
  "hand_intrinsic",
  "hip",
  "thigh_anterior",
  "thigh_posterior",
  "thigh_medial",
  "leg_anterior",
  "leg_posterior",
  "leg_lateral",
  "foot_intrinsic",
]);

export const MuscleTypeEnum = z.enum([
  "skeletal",
  "smooth",
  "cardiac",
]);

export const MuscleActionEnum = z.enum([
  "flexion",
  "extension",
  "abduction",
  "adduction",
  "medial_rotation",
  "lateral_rotation",
  "circumduction",
  "elevation",
  "depression",
  "protraction",
  "retraction",
  "supination",
  "pronation",
  "inversion",
  "eversion",
  "opposition",
  "reposition",
  "dorsiflexion",
  "plantarflexion",
  "lateral_flexion",
]);

export const FiberCompositionEnum = z.enum([
  "type_I",     // slow-twitch oxidative
  "type_IIa",   // fast-twitch oxidative-glycolytic
  "type_IIx",   // fast-twitch glycolytic
  "mixed",      // predominant mix (most muscles)
]);

// --- Innervation ---
// First-class entity so the nerve can be referenced consistently across
// muscles, dermatomes, and future nervous system modeling.

export const InnervationSchema = z.object({
  nerveId: NerveId.optional().describe("Reference to a Nerve entity if the nervous system is modeled"),
  nerveName: z.string().min(1).describe("Anatomical nerve name (e.g. 'musculocutaneous nerve')"),
  spinalRoots: z
    .array(z.string().regex(/^([CTLS]\d{1,2}|CN\d{1,2})$/))
    .min(1)
    .describe("Nerve roots: spinal (C/T/L/S + level, e.g. 'C5') or cranial (CN + number, e.g. 'CN5')"),
});

// --- Muscle Schema ---

export const MuscleSchema = z.object({
  id: MuscleId,
  name: z.string().min(1),
  region: MuscleRegionEnum,
  type: MuscleTypeEnum.default("skeletal"),

  // Attachments — via tendons (composition) rather than bare bone references.
  // A muscle attaches to bone *through* a tendon (or aponeurosis).
  origin: z
    .object({
      tendonId: TendonId.describe("Tendon at the origin (stationary end)"),
      description: z.string().optional().describe("Anatomical description, e.g. 'lateral epicondyle of humerus'"),
    })
    .describe("Where the muscle originates — typically the proximal, more stable attachment"),
  insertion: z
    .object({
      tendonId: TendonId.describe("Tendon at the insertion (mobile end)"),
      description: z.string().optional(),
    })
    .describe("Where the muscle inserts — typically the distal, more mobile attachment"),

  // Morphology
  fascicleArchitecture: FascicleArchitectureEnum,
  pennationAngle: z
    .number()
    .min(0)
    .max(90)
    .optional()
    .describe("Angle of fibers relative to the force-generating axis (degrees). 0 = parallel."),
  fiberDirection: UnitVector3Schema.optional().describe("Primary direction of force generation (unit vector)"),
  fiberComposition: FiberCompositionEnum.default("mixed"),

  // Dimensions — units explicit
  restingLength: z.number().positive().describe("Resting length in cm"),
  optimalFiberLength: z.number().positive().optional().describe("Optimal sarcomere length for max force in cm"),
  volume: z.number().positive().describe("Volume in cm³"),
  mass: z.number().positive().describe("Mass in grams"),
  pcsa: z.number().positive().optional().describe("Physiological cross-sectional area in cm² (computed: volume / optimalFiberLength)"),

  // Force characteristics
  maxIsometricForce: z.number().positive().optional().describe("Peak isometric force in Newtons"),
  maxContractionVelocity: z.number().positive().optional().describe("V_max in optimal fiber lengths per second (L₀/s)"),

  // Innervation and vascular supply
  innervation: InnervationSchema,
  bloodSupply: z.object({
    primaryArteryId: VesselId.optional().describe("Primary arterial supply if vascular system is modeled"),
    primaryArteryName: z.string().min(1).describe("Anatomical name of primary artery"),
    secondaryArteries: z.array(z.string().min(1)).optional(),
  }),

  // Functional relationships
  primaryActions: z.array(MuscleActionEnum).min(1).describe("Primary actions this muscle produces"),
  secondaryActions: z.array(MuscleActionEnum).optional(),
  antagonistIds: z.array(MuscleId).optional().describe("Muscles opposing this muscle's primary action"),
  synergistIds: z.array(MuscleId).optional().describe("Muscles assisting this muscle's primary action"),

  extensions: ExtensionsSchema,
});

// --- Inferred Types ---

export type Tendon = z.infer<typeof TendonSchema>;
export type Muscle = z.infer<typeof MuscleSchema>;
