import { z } from "zod";
import {
  VesselId,
  Vector3Schema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Vascular System
// =============================================================================

// Discriminated union replaces the boolean `isArtery` anti-pattern.
// Arteries, veins, and capillaries have different properties — modeling them
// as a single entity with a boolean flag loses type information and makes it
// impossible to enforce vessel-specific constraints.

export const VesselTypeEnum = z.enum([
  "artery",
  "arteriole",
  "vein",
  "venule",
  "capillary",
]);

const BaseVesselFields = {
  id: VesselId,
  name: z.string().min(1),
  path: z.array(Vector3Schema).min(2).describe("Centerline path as ordered control points (cm)"),
  averageLumenRadius: z.number().positive().describe("Average inner radius in mm"),
  wallThickness: z.number().positive().optional().describe("Vessel wall thickness in mm"),
  parentVesselId: VesselId.nullable().optional().describe("Upstream vessel this branches from; null for aorta/vena cava"),
  extensions: ExtensionsSchema,
};

export const ArterySchema = z.object({
  ...BaseVesselFields,
  vesselType: z.literal("artery"),
  systolicPressure: z.number().positive().optional().describe("Typical systolic pressure in mmHg"),
  diastolicPressure: z.number().positive().optional().describe("Typical diastolic pressure in mmHg"),
  oxygenSaturation: z.number().min(0).max(100).optional().describe("O₂ saturation percentage (typically 95–100%)"),
});

export const VeinSchema = z.object({
  ...BaseVesselFields,
  vesselType: z.literal("vein"),
  hasValves: z.boolean().default(true).describe("Whether the vein has anti-reflux valves"),
  oxygenSaturation: z.number().min(0).max(100).optional().describe("O₂ saturation percentage (typically 60–80%)"),
});

export const CapillaryBedSchema = z.object({
  ...BaseVesselFields,
  vesselType: z.literal("capillary"),
  density: z.number().positive().optional().describe("Capillary density in vessels per mm²"),
});

export const VesselSchema = z.discriminatedUnion("vesselType", [
  ArterySchema,
  VeinSchema,
  CapillaryBedSchema,
]);

// --- Inferred Types ---

export type Artery = z.infer<typeof ArterySchema>;
export type Vein = z.infer<typeof VeinSchema>;
export type CapillaryBed = z.infer<typeof CapillaryBedSchema>;
export type Vessel = z.infer<typeof VesselSchema>;
