import { z } from "zod";
import {
  OrganId,
  TransformSchema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Organ Systems
// =============================================================================

export const OrganSystemEnum = z.enum([
  "cardiovascular",
  "respiratory",
  "digestive",
  "nervous",
  "endocrine",
  "integumentary",
  "lymphatic",
  "urinary",
  "reproductive",
]);
// Note: "skeletal" and "muscular" removed — those are modeled as first-class
// subsystems, not as organs. Including them here would violate Rule 15
// (single source of truth) and Rule 3 (enum not overloaded).

export const OrganSchema = z.object({
  id: OrganId,
  name: z.string().min(1),
  system: OrganSystemEnum,
  transform: TransformSchema,
  volume: z.number().positive().describe("Volume in cm³"),
  mass: z.number().positive().describe("Mass in grams"),
  isVital: z.boolean().default(true).describe("Whether destruction of this organ is immediately life-threatening"),
  pairedOrgan: z
    .boolean()
    .default(false)
    .describe("Whether this organ exists bilaterally (e.g. kidneys, lungs)"),
  laterality: z
    .enum(["left", "right", "midline"])
    .optional()
    .describe("Anatomical side; required when pairedOrgan is true"),
  extensions: ExtensionsSchema,
});

export type Organ = z.infer<typeof OrganSchema>;
