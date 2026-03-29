import { z } from "zod";
import {
  BoneId,
  JointId,
  Vector3Schema,
  UnitVector3Schema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Connective Tissue — Ligaments, Cartilage, Fascia
//
// Ligaments are passive structures that resist motion beyond physiological
// limits. The dynamics module models ligamentous *forces*; this module
// models the ligament as an anatomical entity with material properties.
//
// Cartilage covers articulating bone surfaces and absorbs load. Joint
// cartilage thickness and stiffness matter for contact mechanics and
// joint reaction force distribution.
//
// References:
//   - Woo et al., "Biomechanics of knee ligaments", Am J Sports Med
//     27(4):533–543, 1999.
//   - Mow & Huiskes, "Basic Orthopaedic Biomechanics and Mechano-Biology",
//     3rd ed. (2005), Chapters 5 (ligament) and 4 (cartilage).
// =============================================================================

const brandedUuid = (brand: string) =>
  z.string().uuid().describe(`Opaque unique identifier (${brand})`);

export const LigamentId = brandedUuid("LigamentId");
export const CartilageId = brandedUuid("CartilageId");

// --- Ligament ---

export const LigamentSchema = z.object({
  id: LigamentId,
  name: z.string().min(1).describe("Anatomical name (e.g. 'anterior cruciate ligament', 'medial collateral ligament')"),

  // Attachments — ligaments connect bone to bone
  originBoneId: BoneId.describe("Bone at the origin attachment"),
  originPosition: Vector3Schema.describe("Attachment point on the origin bone in its local frame (cm)"),
  insertionBoneId: BoneId.describe("Bone at the insertion attachment"),
  insertionPosition: Vector3Schema.describe("Attachment point on the insertion bone in its local frame (cm)"),

  // Which joint this ligament stabilizes
  jointId: JointId.describe("Joint this ligament spans and stabilizes"),

  // Geometry
  restingLength: z.number().positive().describe("Resting (slack) length in cm"),
  crossSectionalArea: z.number().positive().optional().describe("Mid-substance cross-sectional area in mm²"),
  fiberDirection: UnitVector3Schema.optional().describe("Primary fiber orientation (unit vector in global frame at rest)"),

  // Material properties — for force computation
  // Ligaments exhibit nonlinear viscoelastic behavior but are commonly
  // approximated as piecewise linear for musculoskeletal simulation.
  linearStiffness: z
    .number()
    .positive()
    .optional()
    .describe("Linear region stiffness in N/mm (slope of the force-displacement curve past the toe region)"),
  toeRegionStrain: z
    .number()
    .min(0)
    .max(0.1)
    .optional()
    .describe("Strain at which the toe region ends and linear region begins (dimensionless, typically 0.03–0.06)"),
  ultimateLoad: z
    .number()
    .positive()
    .optional()
    .describe("Load at failure in N"),
  ultimateStrain: z
    .number()
    .min(0)
    .optional()
    .describe("Strain at failure (dimensionless, typically 0.10–0.15 for healthy ligament)"),

  // Slack length ratio — some ligaments are pre-tensioned at rest
  referenceStrain: z
    .number()
    .optional()
    .describe("Strain at the reference pose (anatomical position). Negative = slack, positive = pre-tensioned."),

  // Function
  primaryRestraint: z
    .enum([
      "anterior_translation",
      "posterior_translation",
      "medial_translation",
      "lateral_translation",
      "varus",
      "valgus",
      "internal_rotation",
      "external_rotation",
      "distraction",
      "hyperextension",
      "hyperflexion",
    ])
    .optional()
    .describe("Primary motion this ligament resists"),

  extensions: ExtensionsSchema,
});

// --- Cartilage ---

export const CartilageTypeEnum = z.enum([
  "hyaline",        // Articular cartilage on joint surfaces
  "fibrocartilage", // Menisci, intervertebral discs, labrum
  "elastic",        // External ear, epiglottis
]);

export const CartilageSchema = z.object({
  id: CartilageId,
  name: z.string().min(1).describe("Anatomical name (e.g. 'femoral condyle articular cartilage', 'medial meniscus')"),
  type: CartilageTypeEnum,

  // Location
  boneId: BoneId.optional().describe("Bone this cartilage covers (for articular cartilage)"),
  jointId: JointId.optional().describe("Joint this cartilage is associated with"),

  // Geometry
  thickness: z.number().positive().optional().describe("Average thickness in mm (articular cartilage: typically 1–7 mm)"),
  surfaceArea: z.number().positive().optional().describe("Contact surface area in cm²"),

  // Material properties — biphasic (solid + fluid) model parameters
  // Reference: Mow et al., J Biomech Eng 102(1):73–84, 1980.
  youngsModulus: z
    .number()
    .positive()
    .optional()
    .describe("Equilibrium aggregate modulus in MPa (articular cartilage: 0.5–1.5 MPa)"),
  poissonRatio: z
    .number()
    .min(0)
    .max(0.5)
    .optional()
    .describe("Poisson's ratio (articular cartilage: ~0.1–0.4)"),
  permeability: z
    .number()
    .positive()
    .optional()
    .describe("Hydraulic permeability in mm⁴/(N·s) (articular cartilage: ~10⁻¹⁵)"),

  extensions: ExtensionsSchema,
});

// --- Inferred Types ---

export type Ligament = z.infer<typeof LigamentSchema>;
export type Cartilage = z.infer<typeof CartilageSchema>;
