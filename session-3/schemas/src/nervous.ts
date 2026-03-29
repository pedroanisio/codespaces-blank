import { z } from "zod";
import {
  NerveId,
  Vector3Schema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Nervous System — Peripheral Nerve Modeling
//
// This module models the peripheral nervous system at the level needed
// for musculoskeletal simulation: motor nerves that innervate muscles,
// and sensory nerves for dermatome mapping.
//
// The central nervous system (brain, spinal cord interneurons, motor
// planning) is out of scope — it would require a fundamentally different
// modeling paradigm (neural networks, not structural anatomy).
//
// References:
//   - Standring, "Gray's Anatomy", 42nd ed. (2020), Ch. 43–46 (peripheral nerves).
//   - Delp et al., "An Interactive Graphics-Based Model of the Lower
//     Extremity to Study Orthopaedic Surgical Procedures", IEEE Trans
//     Biomed Eng 37(8):757–767, 1990 (nerve path modeling).
// =============================================================================

// --- Nerve Type ---

export const NerveTypeEnum = z.enum([
  "motor",           // Efferent — carries signals to muscles
  "sensory",         // Afferent — carries signals from receptors
  "mixed",           // Both motor and sensory (most peripheral nerves)
  "autonomic",       // Sympathetic / parasympathetic
]);

// --- Nerve Plexus ---
// Major nerve networks where spinal roots merge and re-branch.

export const NervePlexusEnum = z.enum([
  "cervical",        // C1–C4 → neck muscles, diaphragm (phrenic)
  "brachial",        // C5–T1 → upper limb
  "lumbar",          // L1–L4 → anterior thigh, medial leg
  "sacral",          // L4–S3 → posterior thigh, entire leg below knee
  "none",            // Direct spinal nerve (intercostals, etc.)
]);

// --- Nerve Schema ---

export const NerveSchema = z.object({
  id: NerveId,
  name: z.string().min(1).describe("Anatomical name (e.g. 'musculocutaneous nerve', 'femoral nerve')"),
  type: NerveTypeEnum,
  plexus: NervePlexusEnum.default("none"),

  // Spinal root composition — which spinal levels contribute to this nerve
  spinalRoots: z
    .array(z.string().regex(/^[CTLS]\d{1,2}$/))
    .min(1)
    .describe("Contributing spinal nerve roots (e.g. ['C5', 'C6'] for musculocutaneous nerve)"),

  // Parent nerve — nerves branch from larger trunks
  parentNerveId: NerveId
    .nullable()
    .describe("Parent nerve this branches from; null for roots/trunks (e.g. sciatic)"),

  // Course / path through the body — ordered waypoints
  path: z
    .array(Vector3Schema)
    .min(2)
    .optional()
    .describe("Centerline path of the nerve as ordered control points (cm, global frame at anatomical position)"),

  // Nerve dimensions
  diameter: z
    .number()
    .positive()
    .optional()
    .describe("Average diameter in mm"),

  // Conduction properties
  conductionVelocity: z
    .number()
    .positive()
    .optional()
    .describe("Motor conduction velocity in m/s (normal: 40–80 m/s for motor, varies by fiber type)"),

  // Clinical: muscles innervated and sensory distribution are navigable
  // through the reverse relationship (Muscle.innervation.nerveId → this nerve).
  // We don't duplicate that list here (Rule 15: single source of truth).

  // Dermatome — sensory territory (for sensory and mixed nerves)
  dermatome: z
    .string()
    .optional()
    .describe("Skin region innervated for sensation (e.g. 'lateral forearm' for musculocutaneous)"),

  extensions: ExtensionsSchema,
});

// --- Inferred Types ---

export type Nerve = z.infer<typeof NerveSchema>;
