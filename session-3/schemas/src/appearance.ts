import { z } from "zod";
import {
  MuscleId,
  BoneId,
  OrganId,
  VesselId,
  ClothingId,
  ColorSchema,
  TransformSchema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Exterior Appearance (domain layer — anatomical description of surface)
// =============================================================================

export const HairSchema = z.object({
  style: z.string().min(1),
  color: ColorSchema,
  length: z.number().nonnegative().describe("Hair length in cm"),
  density: z.number().min(0).max(1).describe("Hair density (0 = absent, 1 = very thick)"),
  transform: TransformSchema,
  extensions: ExtensionsSchema,
});

export const ClothingTypeEnum = z.enum([
  "headwear",
  "top",
  "bottom",
  "footwear",
  "accessory",
  "fullbody",
]);

export const ClothingSchema = z.object({
  id: ClothingId,
  name: z.string().min(1),
  type: ClothingTypeEnum,
  color: ColorSchema,
  transform: TransformSchema,
  fabric: z.string().min(1),
  fit: z.enum(["tight", "regular", "loose", "oversized"]),
  extensions: ExtensionsSchema,
});

// =============================================================================
// Rendering Layer (presentation concern — separated from anatomy)
//
// Waiver: Rule 30 suggests access patterns should not dictate structure.
// By extracting rendering into its own layer, we comply — anatomical entities
// carry no rendering state. This layer references entities by ID and overlays
// visual properties.
// =============================================================================

export const SkinningWeightSchema = z.object({
  vertexId: z.number().int().nonnegative(),
  weight: z.number().min(0).max(1),
});

export const PBRMaterialSchema = z.object({
  baseColor: ColorSchema.optional(),
  metalness: z.number().min(0).max(1).optional(),
  roughness: z.number().min(0).max(1).optional(),
  clearcoat: z.number().min(0).max(1).optional(),
  clearcoatRoughness: z.number().min(0).max(1).optional(),
  transmission: z.number().min(0).max(1).optional(),
  thickness: z.number().nonnegative().optional(),
  sheen: z.number().min(0).max(1).optional(),
  sheenRoughness: z.number().min(0).max(1).optional(),
  sheenColor: ColorSchema.optional(),
  emissive: ColorSchema.optional(),
  emissiveIntensity: z.number().min(0).optional(),
}).describe("Portable PBR material override for renderers that support physically based shading");

export const EntityRenderOverride = z.object({
  entityId: z.string().uuid().describe("ID of the anatomical entity"),
  color: ColorSchema.optional(),
  opacity: z.number().min(0).max(1).optional(),
  visible: z.boolean().default(true),
  material: PBRMaterialSchema.optional(),
  skinningWeights: z
    .array(SkinningWeightSchema)
    .optional()
    .describe("Vertex weights for mesh deformation"),
  extensions: ExtensionsSchema,
});

export const RenderingLayerSchema = z.object({
  muscleOverrides: z.array(EntityRenderOverride).optional(),
  boneOverrides: z.array(EntityRenderOverride).optional(),
  organOverrides: z.array(EntityRenderOverride).optional(),
  vesselOverrides: z.array(EntityRenderOverride).optional(),
  globalOpacity: z.number().min(0).max(1).default(1),
  extensions: ExtensionsSchema,
});

// --- Inferred Types ---

export type Hair = z.infer<typeof HairSchema>;
export type Clothing = z.infer<typeof ClothingSchema>;
export type RenderingLayer = z.infer<typeof RenderingLayerSchema>;
