import { z } from "zod";
import { SCHEMA_VERSION, ExtensionsSchema } from "./shared";
import { BoneSchema, JointSchema } from "./skeletal";
import { MuscleSchema, TendonSchema } from "./muscular";
import { OrganSchema } from "./organs";
import { VesselSchema } from "./vascular";
import { LigamentSchema, CartilageSchema } from "./connective";
import { NerveSchema } from "./nervous";
import { HairSchema, ClothingSchema, RenderingLayerSchema } from "./appearance";
import { BodySegmentSchema, PoseSchema, MotionSequenceSchema, ReferenceFrameSchema } from "./kinematics";
import { LoadingConditionSchema, FreeBodyDiagramSchema } from "./dynamics";
import { DerivationGraphSchema } from "./derivations";
import { ConstitutiveLawsSchema } from "./constitutive";
import { BoneGeometrySchema, countCSGNodes, csgTreeDepth, CSG_MAX_NODE_COUNT, CSG_MAX_DEPTH } from "./geometry";

// =============================================================================
// Proportions
// =============================================================================

export const SexEnum = z.enum(["male", "female", "intersex"]);

export const ProportionsSchema = z.object({
  biologicalSex: SexEnum.optional().describe("Biological sex — affects default proportional ratios"),
  totalHeight: z.number().positive().describe("Standing height in cm"),
  weight: z.number().positive().describe("Total body mass in kg"),
  shoulderWidth: z.number().positive().describe("Biacromial width in cm"),
  armLength: z.number().positive().describe("Acromion to fingertip in cm"),
  legLength: z.number().positive().describe("Greater trochanter to floor in cm"),
  headCircumference: z.number().positive().describe("Head circumference in cm"),
  muscleMassPercentage: z
    .number()
    .min(10)
    .max(60)
    .optional()
    .describe("Percentage of body mass that is skeletal muscle (typical: 30–45%)"),
  fatPercentage: z
    .number()
    .min(3)
    .max(55)
    .optional()
    .describe("Body fat percentage (essential fat: ~3% male, ~12% female)"),
});

// =============================================================================
// Root Entity: HumanBody
// =============================================================================

export const HumanBodySchema = z
  .object({
    schemaVersion: z.literal(SCHEMA_VERSION).describe("Must match the schema version this instance was created against"),
    id: z.string().uuid(),
    name: z.string().optional(),
    proportions: ProportionsSchema,

    // Skeletal subsystem (composition — body owns these exclusively)
    skeleton: z.array(BoneSchema).min(1),
    joints: z.array(JointSchema),

    // Muscular subsystem (composition)
    tendons: z.array(TendonSchema),
    muscles: z.array(MuscleSchema),

    // Organ subsystem (composition)
    organs: z.array(OrganSchema),

    // Vascular subsystem (composition — discriminated union items)
    vascularSystem: z.array(VesselSchema),

    // Connective tissue subsystem (composition)
    ligaments: z.array(LigamentSchema).optional().describe("Joint ligaments — passive restraints connecting bone to bone"),
    cartilage: z.array(CartilageSchema).optional().describe("Articular cartilage and fibrocartilage (menisci, labra, discs)"),

    // Nervous subsystem (composition)
    nerves: z.array(NerveSchema).optional().describe("Peripheral nerves — motor, sensory, mixed, autonomic"),

    // Exterior
    hair: HairSchema.optional(),
    clothing: z.array(ClothingSchema),

    // Rendering — optional presentation overlay, not part of the anatomical model
    rendering: RenderingLayerSchema.optional(),

    // Geometry — optional mesh/CSG data for bone shapes
    boneGeometries: z
      .array(BoneGeometrySchema)
      .optional()
      .describe(
        "Geometric shape data for bones. Each entry references a bone via boneId. " +
        "Supports three representations: parametric_csg (compact procedural), " +
        "indexed_mesh (inline triangles), or external_asset (URI reference).",
      ),

    // =========================================================================
    // Kinematics — position, orientation, and motion of the body
    // =========================================================================

    // Reference frames — global and per-segment coordinate systems
    referenceFrames: z
      .array(ReferenceFrameSchema)
      .optional()
      .describe("Defined coordinate frames (global, segment, joint). At least the global frame should be present for kinematic analysis."),

    // Body segments — rigid bodies for multibody dynamics
    segments: z
      .array(BodySegmentSchema)
      .optional()
      .describe("Rigid body segments (thigh, shank, foot, etc.). Required for kinematics/dynamics analysis."),

    // Current pose or reference pose
    currentPose: PoseSchema
      .optional()
      .describe("Current body configuration. If absent, the body is in the default (anatomical) position defined by bone transforms."),

    // Named/saved poses
    savedPoses: z
      .array(PoseSchema)
      .optional()
      .describe("Library of named poses (e.g. anatomical position, T-pose, seated, mid-stance)"),

    // Motion sequences (animation / motion capture)
    motionSequences: z
      .array(MotionSequenceSchema)
      .optional()
      .describe("Recorded or designed motion sequences"),

    // =========================================================================
    // Dynamics — forces and moments acting on the body
    // =========================================================================

    // Loading conditions — complete force states paired with poses
    loadingConditions: z
      .array(LoadingConditionSchema)
      .optional()
      .describe("Force/moment snapshots. Each references a pose and contains all forces at that instant."),

    // Free body diagrams — per-segment force isolation
    freeBodyDiagrams: z
      .array(FreeBodyDiagramSchema)
      .optional()
      .describe("[Computed] Per-segment FBDs derived from loading conditions"),

    // =========================================================================
    // Derivation Graph — declarative computation layer (derivations.ts)
    // =========================================================================

    // Declares the functional dependencies between stored and computed fields.
    // Each rule maps input fields → output field via a named physical law.
    // The graph enables consistency verification, staleness detection, and
    // physics auditing without application-layer code.
    derivationGraph: DerivationGraphSchema
      .optional()
      .describe(
        "Declarative derivation DAG. Each rule declares: output = f(inputs) " +
        "with a named physical law, tolerance, and dependency ordering. " +
        "Enables mechanical consistency checking of [Computed] fields.",
      ),

    // =========================================================================
    // Constitutive Laws — material and physiological constraints (constitutive.ts)
    // =========================================================================

    // Declares the material laws (Hill muscle model, ligament force-strain,
    // cartilage stress-strain, bone yield) that constrain field values.
    // Unlike the derivation graph (which computes outputs from inputs),
    // constitutive laws define envelopes: field values must fall within
    // the physically achievable range.
    constitutiveLaws: ConstitutiveLawsSchema
      .optional()
      .describe(
        "Constitutive law collection. Each law declares an inequality/envelope " +
        "constraint on field values (e.g. muscle force ≤ Hill model envelope). " +
        "Includes model validity boundaries declaring when assumptions break down.",
      ),

    extensions: ExtensionsSchema,
  })
  .superRefine((body, ctx) => {
    // --- Index construction ---
    const boneIds = new Set(body.skeleton.map((b) => b.id));
    const tendonIds = new Set(body.tendons.map((t) => t.id));
    const muscleIds = new Set(body.muscles.map((m) => m.id));
    const jointIds = new Set(body.joints.map((j) => j.id));
    const segmentIds = new Set((body.segments ?? []).map((s) => s.id));
    const poseIds = new Set<string>();
    if (body.currentPose) poseIds.add(body.currentPose.id);
    (body.savedPoses ?? []).forEach((p) => poseIds.add(p.id));
    (body.motionSequences ?? []).forEach((ms) =>
      ms.poses.forEach((p) => poseIds.add(p.id)),
    );

    // --- Proportion coherence ---

    const armRatio = body.proportions.armLength / body.proportions.totalHeight;
    if (armRatio < 0.35 || armRatio > 0.55) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `Arm/height ratio ${armRatio.toFixed(3)} outside anthropometric range [0.35, 0.55]. ` +
          `Reference: Pheasant & Haslegrave, "Bodyspace" (2006), Table 2.2.`,
        path: ["proportions", "armLength"],
      });
    }

    const legRatio = body.proportions.legLength / body.proportions.totalHeight;
    if (legRatio < 0.40 || legRatio > 0.55) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: `Leg/height ratio ${legRatio.toFixed(3)} outside anthropometric range [0.40, 0.55]. ` +
          `Reference: Pheasant & Haslegrave, "Bodyspace" (2006), Table 2.2.`,
        path: ["proportions", "legLength"],
      });
    }

    if (
      body.proportions.muscleMassPercentage !== undefined &&
      body.proportions.fatPercentage !== undefined
    ) {
      const total = body.proportions.muscleMassPercentage + body.proportions.fatPercentage;
      if (total > 75) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Muscle (${body.proportions.muscleMassPercentage}%) + fat (${body.proportions.fatPercentage}%) = ${total}%, ` +
            `leaving <25% for bone mineral (~5%), organs, water, and connective tissue. Max plausible sum ≈ 75%.`,
          path: ["proportions"],
        });
      }
    }

    // --- Skeletal referential integrity ---

    // Bone parent hierarchy must reference existing bones
    body.skeleton.forEach((bone, i) => {
      if (bone.parentBoneId !== null && !boneIds.has(bone.parentBoneId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Bone '${bone.name}' references non-existent parent bone: ${bone.parentBoneId}`,
          path: ["skeleton", i, "parentBoneId"],
        });
      }
    });

    // Joints must reference existing bones
    body.joints.forEach((joint, i) => {
      joint.connectedBoneIds.forEach((boneId, j) => {
        if (!boneIds.has(boneId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Joint '${joint.name}' references non-existent bone: ${boneId}`,
            path: ["joints", i, "connectedBoneIds", j],
          });
        }
      });
    });

    // --- Tendon referential integrity ---

    body.tendons.forEach((tendon, i) => {
      if (!boneIds.has(tendon.attachedBoneId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Tendon '${tendon.name}' references non-existent bone: ${tendon.attachedBoneId}`,
          path: ["tendons", i, "attachedBoneId"],
        });
      }
    });

    // --- Muscle referential integrity ---

    body.muscles.forEach((muscle, mi) => {
      // Origin and insertion tendons must exist
      if (!tendonIds.has(muscle.origin.tendonId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Muscle '${muscle.name}' origin references non-existent tendon: ${muscle.origin.tendonId}`,
          path: ["muscles", mi, "origin", "tendonId"],
        });
      }
      if (!tendonIds.has(muscle.insertion.tendonId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Muscle '${muscle.name}' insertion references non-existent tendon: ${muscle.insertion.tendonId}`,
          path: ["muscles", mi, "insertion", "tendonId"],
        });
      }

      // Antagonist and synergist references
      muscle.antagonistIds?.forEach((id, j) => {
        if (!muscleIds.has(id)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Muscle '${muscle.name}' antagonist references non-existent muscle: ${id}`,
            path: ["muscles", mi, "antagonistIds", j],
          });
        }
      });
      muscle.synergistIds?.forEach((id, j) => {
        if (!muscleIds.has(id)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Muscle '${muscle.name}' synergist references non-existent muscle: ${id}`,
            path: ["muscles", mi, "synergistIds", j],
          });
        }
      });
    });

    // --- Ligament referential integrity ---

    const nerveIds = new Set((body.nerves ?? []).map((n) => n.id));

    (body.ligaments ?? []).forEach((lig, li) => {
      if (!boneIds.has(lig.originBoneId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Ligament '${lig.name}' origin references non-existent bone: ${lig.originBoneId}`,
          path: ["ligaments", li, "originBoneId"],
        });
      }
      if (!boneIds.has(lig.insertionBoneId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Ligament '${lig.name}' insertion references non-existent bone: ${lig.insertionBoneId}`,
          path: ["ligaments", li, "insertionBoneId"],
        });
      }
      if (!jointIds.has(lig.jointId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Ligament '${lig.name}' references non-existent joint: ${lig.jointId}`,
          path: ["ligaments", li, "jointId"],
        });
      }
    });

    // --- Cartilage referential integrity ---

    (body.cartilage ?? []).forEach((cart, ci) => {
      if (cart.boneId !== undefined && !boneIds.has(cart.boneId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Cartilage '${cart.name}' references non-existent bone: ${cart.boneId}`,
          path: ["cartilage", ci, "boneId"],
        });
      }
      if (cart.jointId !== undefined && !jointIds.has(cart.jointId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Cartilage '${cart.name}' references non-existent joint: ${cart.jointId}`,
          path: ["cartilage", ci, "jointId"],
        });
      }
    });

    // --- Nerve referential integrity ---

    (body.nerves ?? []).forEach((nerve, ni) => {
      if (nerve.parentNerveId !== null && !nerveIds.has(nerve.parentNerveId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Nerve '${nerve.name}' references non-existent parent nerve: ${nerve.parentNerveId}`,
          path: ["nerves", ni, "parentNerveId"],
        });
      }
    });

    // --- Muscle innervation → Nerve integrity ---

    body.muscles.forEach((muscle, mi) => {
      if (muscle.innervation.nerveId !== undefined && nerveIds.size > 0) {
        if (!nerveIds.has(muscle.innervation.nerveId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Muscle '${muscle.name}' innervation references non-existent nerve: ${muscle.innervation.nerveId}`,
            path: ["muscles", mi, "innervation", "nerveId"],
          });
        }
      }
    });

    // --- Segment referential integrity ---

    (body.segments ?? []).forEach((segment, si) => {
      // Every bone in a segment must exist
      segment.boneIds.forEach((boneId, bi) => {
        if (!boneIds.has(boneId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Segment '${segment.name}' references non-existent bone: ${boneId}`,
            path: ["segments", si, "boneIds", bi],
          });
        }
      });

      // Proximal and distal joints must exist
      if (segment.proximalJointId !== null && segment.proximalJointId !== undefined) {
        if (!jointIds.has(segment.proximalJointId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Segment '${segment.name}' proximalJointId references non-existent joint: ${segment.proximalJointId}`,
            path: ["segments", si, "proximalJointId"],
          });
        }
      }
      segment.distalJointIds.forEach((jid, ji) => {
        if (!jointIds.has(jid)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Segment '${segment.name}' distalJointId references non-existent joint: ${jid}`,
            path: ["segments", si, "distalJointIds", ji],
          });
        }
      });
    });

    // --- Pose referential integrity ---

    const validatePoseRefs = (pose: typeof body.currentPose, basePath: string[]) => {
      if (!pose) return;

      // Root segment must exist
      if (segmentIds.size > 0 && !segmentIds.has(pose.rootSegmentId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Pose '${pose.name ?? pose.id}' references non-existent root segment: ${pose.rootSegmentId}`,
          path: [...basePath, "rootSegmentId"],
        });
      }

      // Every joint state must reference an existing joint
      pose.jointStates.forEach((js, ji) => {
        if (!jointIds.has(js.jointId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Pose '${pose.name ?? pose.id}' joint state references non-existent joint: ${js.jointId}`,
            path: [...basePath, "jointStates", ji, "jointId"],
          });
        }
      });
    };

    validatePoseRefs(body.currentPose, ["currentPose"]);
    (body.savedPoses ?? []).forEach((pose, pi) => {
      validatePoseRefs(pose, ["savedPoses", pi.toString()]);
    });

    // --- Loading condition referential integrity ---

    (body.loadingConditions ?? []).forEach((lc, li) => {
      // Pose reference must exist
      if (!poseIds.has(lc.poseId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Loading condition '${lc.name}' references non-existent pose: ${lc.poseId}`,
          path: ["loadingConditions", li, "poseId"],
        });
      }
    });

    // --- Bone geometry referential integrity ---

    // Build allIds set once for surface region relatedEntityId validation (#9)
    const allEntityIds = new Set([
      ...boneIds, ...tendonIds, ...muscleIds, ...jointIds,
      ...(body.ligaments ?? []).map(l => l.id),
      ...(body.cartilage ?? []).map(c => c.id),
    ]);

    const geometryBoneIds = new Set<string>();
    (body.boneGeometries ?? []).forEach((geo, gi) => {
      // Every geometry must reference an existing bone
      if (!boneIds.has(geo.boneId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Bone geometry [${gi}] references non-existent bone: ${geo.boneId}`,
          path: ["boneGeometries", gi, "boneId"],
        });
      }

      // No duplicate geometries for the same bone
      if (geometryBoneIds.has(geo.boneId)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Duplicate geometry for bone ${geo.boneId}. Each bone may have at most one geometry entry.`,
          path: ["boneGeometries", gi, "boneId"],
        });
      }
      geometryBoneIds.add(geo.boneId);

      // CSG tree size/depth guards (#1)
      if (geo.geometryType === "parametric_csg") {
        const nodeCount = countCSGNodes(geo.csgTree);
        if (nodeCount > CSG_MAX_NODE_COUNT) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `CSG tree has ${nodeCount} nodes, exceeding maximum of ${CSG_MAX_NODE_COUNT}. Simplify the geometry.`,
            path: ["boneGeometries", gi, "csgTree"],
          });
        }
        const depth = csgTreeDepth(geo.csgTree);
        if (depth > CSG_MAX_DEPTH) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `CSG tree depth is ${depth}, exceeding maximum of ${CSG_MAX_DEPTH}. Flatten the tree.`,
            path: ["boneGeometries", gi, "csgTree"],
          });
        }
      }

      if (geo.geometryType === "indexed_mesh") {
        const maxVertex = geo.lods[0].vertexCount - 1;

        // Validate surface region vertex indices are within bounds
        (geo.surfaceRegions ?? []).forEach((region, ri) => {
          region.vertexIndices.forEach((vi, vii) => {
            if (vi > maxVertex) {
              ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: `Surface region '${region.name}' vertex index ${vi} exceeds LOD 0 vertex count (${geo.lods[0].vertexCount})`,
                path: ["boneGeometries", gi, "surfaceRegions", ri, "vertexIndices", vii],
              });
            }
          });
        });

        // Validate LODs are sorted by level ascending
        for (let l = 1; l < geo.lods.length; l++) {
          if (geo.lods[l].level <= geo.lods[l - 1].level) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: `LODs must be sorted by level ascending. lods[${l}].level (${geo.lods[l].level}) <= lods[${l - 1}].level (${geo.lods[l - 1].level})`,
              path: ["boneGeometries", gi, "lods", l, "level"],
            });
          }
        }

        // Validate related entity IDs in surface regions
        (geo.surfaceRegions ?? []).forEach((region, ri) => {
          if (region.relatedEntityId !== undefined) {
            if (!allEntityIds.has(region.relatedEntityId)) {
              ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: `Surface region '${region.name}' relatedEntityId references non-existent entity: ${region.relatedEntityId}`,
                path: ["boneGeometries", gi, "surfaceRegions", ri, "relatedEntityId"],
              });
            }
          }
        });
      }
    });
  });

// --- Inferred Type ---

export type HumanBody = z.infer<typeof HumanBodySchema>;
