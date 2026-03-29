import { z } from "zod";
import {
  BoneId,
  Vector3Schema,
  QuaternionSchema,
  ExtensionsSchema,
} from "./shared";

// =============================================================================
// Geometry Module — Bone Shape Representation
//
// This module adds geometric shape data to bones via a discriminated union
// on `geometryType`. Three representations are supported, each targeting
// a different fidelity/portability tradeoff:
//
//   1. `parametric_csg`    — Compact, self-contained, low fidelity.
//   2. `indexed_mesh`      — Self-contained, high fidelity, heavy payload.
//   3. `external_asset`    — Lightweight reference, requires asset pipeline.
//
// The discriminated union pattern follows the same design as VesselSchema
// (discriminated on `vesselType`) and ForceSchema (discriminated on
// `forceType`). Consumers switch on `geometryType` and get type-safe
// access to the fields relevant to each representation.
//
// Coordinate convention:
//   All geometry is expressed in the bone's LOCAL coordinate frame.
//   The bone's `transform` (from skeletal.ts) positions the geometry
//   in world space. This avoids redundant world-space vertices and
//   ensures geometry moves with the bone during pose changes.
//
// References:
//   - Lorensen & Cline, "Marching Cubes: A High Resolution 3D Surface
//     Construction Algorithm", SIGGRAPH '87, 163–169 (mesh representation).
//   - Requicha, "Representations for Rigid Solids: Theory, Methods, and
//     Systems", ACM Comput. Surv. 12(4):437–464, 1980 (CSG theory).
//   - Khronos Group, "glTF 2.0 Specification", 2017 (external asset format).
// =============================================================================

// --- Branded ID ---

const GeometryId = z.string().uuid().describe("Opaque unique identifier (GeometryId)");

// =============================================================================
// Representation 1: Parametric CSG
//
// Compose a bone's approximate shape from geometric primitives combined
// via boolean operations. Self-contained — no external files — and compact
// enough (~200–500 bytes per bone) that it adds negligible weight to the
// JSON document. Fidelity ceiling is low: a femur becomes a tapered
// cylinder with two sphere caps, not a condylar surface. Suitable for
// Tier 2 procedural rendering and physics collision hulls.
//
// Design note: primitives are intentionally limited to shapes that have
// closed-form volume, surface area, and inertia tensor calculations.
// This means a renderer OR a physics engine can consume them without
// mesh conversion.
// =============================================================================

export const CSGPrimitiveTypeEnum = z.enum([
  "cylinder",     // Tapered cylinder (r1 ≠ r2 for conical frustum)
  "sphere",       // Full or partial sphere (wedge via arc angles)
  "ellipsoid",    // Tri-axial ellipsoid
  "box",          // Axis-aligned box in local frame
  "capsule",      // Cylinder + hemisphere caps (common for long bones)
  "torus",        // Ring-shaped (e.g., vertebral body approximation)
]);

export const CSGPrimitiveSchema = z.discriminatedUnion("primitiveType", [
  z.object({
    primitiveType: z.literal("cylinder"),
    radiusTop: z.number().nonnegative().describe("Top radius in cm (0 = cone apex)"),
    radiusBottom: z.number().nonnegative().describe("Bottom radius in cm"),
    height: z.number().positive().describe("Height along local Y axis in cm"),
    position: Vector3Schema.describe("Center position in bone-local frame (cm)"),
    orientation: QuaternionSchema.optional().describe("Orientation in bone-local frame (identity = Y-up)"),
  }),
  z.object({
    primitiveType: z.literal("sphere"),
    radius: z.number().positive().describe("Radius in cm"),
    position: Vector3Schema.describe("Center position in bone-local frame (cm)"),
  }),
  z.object({
    primitiveType: z.literal("ellipsoid"),
    radii: Vector3Schema.describe("Semi-axis radii (x, y, z) in cm"),
    position: Vector3Schema.describe("Center position in bone-local frame (cm)"),
    orientation: QuaternionSchema.optional().describe("Orientation in bone-local frame"),
  }),
  z.object({
    primitiveType: z.literal("box"),
    halfExtents: Vector3Schema.describe("Half-widths along each axis in cm"),
    position: Vector3Schema.describe("Center position in bone-local frame (cm)"),
    orientation: QuaternionSchema.optional().describe("Orientation in bone-local frame"),
  }),
  z.object({
    primitiveType: z.literal("capsule"),
    radius: z.number().positive().describe("Cylinder and hemisphere radius in cm"),
    height: z.number().positive().describe("Total height including caps in cm"),
    position: Vector3Schema.describe("Center position in bone-local frame (cm)"),
    orientation: QuaternionSchema.optional().describe("Orientation in bone-local frame (identity = Y-up)"),
  }),
  z.object({
    primitiveType: z.literal("torus"),
    majorRadius: z.number().positive().describe("Distance from center to tube center in cm"),
    minorRadius: z.number().positive().describe("Tube cross-section radius in cm"),
    position: Vector3Schema.describe("Center position in bone-local frame (cm)"),
    orientation: QuaternionSchema.optional().describe("Orientation in bone-local frame (identity = ring in XZ plane)"),
  }),
]);

export const CSGOperationEnum = z.enum([
  "union",        // A ∪ B
  "subtract",     // A \ B (remove B from A)
  "intersect",    // A ∩ B
]);

// CSG tree node: either a leaf (primitive) or an internal node (operation on children)
export const CSGNodeSchema: z.ZodType<CSGNode> = z.lazy(() =>
  z.discriminatedUnion("nodeType", [
    z.object({
      nodeType: z.literal("primitive"),
      primitive: CSGPrimitiveSchema,
    }),
    z.object({
      nodeType: z.literal("operation"),
      operation: CSGOperationEnum,
      children: z.array(CSGNodeSchema).min(2).max(8)
        .describe("Operands. For 'subtract': children[0] is the base, children[1..n] are subtracted."),
    }),
  ]),
);

type CSGNode = 
  | { nodeType: "primitive"; primitive: z.infer<typeof CSGPrimitiveSchema> }
  | { nodeType: "operation"; operation: z.infer<typeof CSGOperationEnum>; children: CSGNode[] };

// --- CSG tree size/depth guards ---
// Exported as utilities for use in body.ts superRefine, since adding
// .refine() to ParametricCSGGeometrySchema would turn it into ZodEffects
// and break the discriminatedUnion.

export function countCSGNodes(node: CSGNode): number {
  if (node.nodeType === "primitive") return 1;
  return 1 + node.children.reduce((sum, child) => sum + countCSGNodes(child), 0);
}

export function csgTreeDepth(node: CSGNode): number {
  if (node.nodeType === "primitive") return 1;
  return 1 + Math.max(...node.children.map(csgTreeDepth));
}

export const CSG_MAX_NODE_COUNT = 64 as const;
export const CSG_MAX_DEPTH = 8 as const;

export const ParametricCSGGeometrySchema = z.object({
  geometryType: z.literal("parametric_csg"),
  id: GeometryId,
  boneId: BoneId.describe("Bone this geometry represents"),
  csgTree: CSGNodeSchema.describe("Root of the CSG tree defining the bone shape"),

  // Convex hull hint — optional simplified shape for broad-phase collision detection.
  // Cheaper to test than the full CSG tree.
  collisionHull: z
    .enum(["aabb", "obb", "convex_hull", "sphere"])
    .optional()
    .describe("Preferred broad-phase collision shape (computed from CSG tree if absent)"),

  extensions: ExtensionsSchema,
});

// =============================================================================
// Representation 2: Indexed Triangle Mesh
//
// The standard representation for high-fidelity bone geometry. Vertices,
// face indices, and per-vertex normals are stored inline in the JSON
// document. This makes the schema fully self-contained — no external
// files — at the cost of payload size (~50–500 KB per bone depending
// on triangle count).
//
// Data layout follows the interleaved vertex buffer convention used by
// glTF, OpenGL, and WebGPU: positions are separate from normals and UVs
// so that renderers can bind them to separate attribute slots without
// de-interleaving.
//
// Level-of-detail (LOD) support is built in via the `lods` array.
// Each LOD is a complete mesh at a specific triangle budget. Renderers
// select the appropriate LOD based on camera distance. LOD 0 is always
// the highest resolution.
//
// Vertex count constraints:
//   - min: 4 (tetrahedron — minimum closed surface)
//   - max: 500,000 (practical limit for inline JSON; beyond this, use
//     external_asset with binary glTF)
//
// Reference: Garland & Heckbert, "Surface Simplification Using Quadric
// Error Metrics", SIGGRAPH '97, 209–216 (LOD generation).
// =============================================================================

export const MeshVertexSchema = z.object({
  positions: z
    .array(z.number())
    .describe(
      "Flat array of vertex positions [x0,y0,z0, x1,y1,z1, ...] in cm, bone-local frame. " +
      "Length must be 3 × vertexCount.",
    ),
  normals: z
    .array(z.number())
    .optional()
    .describe(
      "Flat array of vertex normals [nx0,ny0,nz0, ...]. " +
      "Length must equal positions.length. Unit-length vectors.",
    ),
  uvs: z
    .array(z.number())
    .optional()
    .describe(
      "Flat array of UV coordinates [u0,v0, u1,v1, ...] for texture mapping. " +
      "Length must be 2 × vertexCount.",
    ),
  colors: z
    .array(z.number().int().min(0).max(255))
    .optional()
    .describe(
      "Flat array of per-vertex colors [r0,g0,b0,a0, ...] as uint8. " +
      "Length must be 4 × vertexCount. Useful for encoding bone density maps.",
    ),
});

export const MeshLODSchema = z.object({
  level: z.number().int().min(0).describe("LOD level: 0 = highest resolution"),
  vertexCount: z.number().int().min(4).max(500_000),
  triangleCount: z.number().int().min(1),
  vertices: MeshVertexSchema,
  indices: z
    .array(z.number().int().min(0))
    .describe(
      "Triangle indices into the vertex arrays. Length must be 3 × triangleCount. " +
      "Winding order: counter-clockwise (right-hand rule for outward normals).",
    ),
}).refine(
  (lod) => lod.indices.length === lod.triangleCount * 3,
  { message: "indices.length must equal triangleCount × 3" },
).refine(
  (lod) => lod.vertices.positions.length === lod.vertexCount * 3,
  { message: "positions.length must equal vertexCount × 3" },
).refine(
  (lod) => !lod.vertices.normals || lod.vertices.normals.length === lod.vertexCount * 3,
  { message: "normals.length must equal vertexCount × 3 when present" },
).refine(
  (lod) => !lod.vertices.uvs || lod.vertices.uvs.length === lod.vertexCount * 2,
  { message: "uvs.length must equal vertexCount × 2 when present" },
).refine(
  (lod) => !lod.vertices.colors || lod.vertices.colors.length === lod.vertexCount * 4,
  { message: "colors.length must equal vertexCount × 4 when present" },
).refine(
  (lod) => lod.indices.every((idx) => idx < lod.vertexCount),
  { message: "All face indices must be < vertexCount (index out of bounds)" },
);

// Anatomical landmarks — named points on the bone surface that are
// clinically or biomechanically significant. These survive LOD changes
// (they reference vertex indices per LOD) and are essential for:
//   - Registering meshes to imaging data
//   - Defining anatomical coordinate systems (ISB recommendations)
//   - Placing muscle/ligament attachment points precisely on the surface
//
// Reference: Wu et al., J Biomech 35(4):543–548, 2002 (ISB landmark definitions).

export const AnatomicalLandmarkSchema = z.object({
  name: z.string().min(1).describe(
    "Standard anatomical name (e.g., 'lateral_epicondyle', 'greater_trochanter', " +
    "'medial_malleolus'). Use snake_case ISB terminology.",
  ),
  position: Vector3Schema.describe("Position in bone-local frame (cm)"),
  nearestVertexByLOD: z
    .record(z.string(), z.number().int().min(0))
    .optional()
    .describe(
      "Map from LOD level (as string key '0', '1', ...) to nearest vertex index in that LOD. " +
      "Allows snapping the landmark to the mesh surface at any resolution.",
    ),
  surfaceNormal: Vector3Schema.optional().describe("Outward surface normal at this landmark (unit vector)"),
});

// Surface regions — semantically meaningful areas on the bone surface.
// Used for: articular surface identification, muscle attachment footprints,
// fracture zone classification, cortical vs. trabecular zone mapping.

export const SurfaceRegionSchema = z.object({
  name: z.string().min(1).describe("Region name (e.g., 'articular_surface_medial_condyle', 'deltoid_tuberosity')"),
  vertexIndices: z
    .array(z.number().int().min(0))
    .min(3)
    .max(500_000)
    .describe("Vertex indices (in LOD 0) belonging to this region. Max 500k (matches vertex count ceiling)."),
  regionType: z.enum([
    "articular",      // Joint contact surface (covered by cartilage)
    "attachment",     // Muscle/tendon/ligament attachment footprint
    "cortical",       // Dense outer bone
    "trabecular",     // Spongy inner bone (exposed at cross-sections)
    "periosteal",     // Outer membrane surface
    "endosteal",      // Inner medullary cavity surface
    "fracture_zone",  // Clinically relevant fracture region
    "custom",
  ]),
  relatedEntityId: z
    .string()
    .uuid()
    .optional()
    .describe("ID of the related entity (e.g., TendonId for attachment, CartilageId for articular)"),
});

export const IndexedMeshGeometrySchema = z.object({
  geometryType: z.literal("indexed_mesh"),
  id: GeometryId,
  boneId: BoneId.describe("Bone this geometry represents"),

  // LODs — at least one (the base resolution). Sorted by level ascending.
  lods: z
    .array(MeshLODSchema)
    .min(1)
    .describe("Level-of-detail meshes. lods[0] is the highest resolution."),

  // Anatomical landmarks
  landmarks: z
    .array(AnatomicalLandmarkSchema)
    .optional()
    .describe("Named anatomical landmarks on the bone surface"),

  // Surface regions
  surfaceRegions: z
    .array(SurfaceRegionSchema)
    .optional()
    .describe("Semantically labeled surface regions"),

  // Mesh metadata
  isClosed: z
    .boolean()
    .default(true)
    .describe("Whether the mesh is a closed (watertight) manifold — required for volume calculation"),
  isManifold: z
    .boolean()
    .default(true)
    .describe("Whether the mesh is 2-manifold (every edge shared by exactly 2 triangles)"),
  
  // Source provenance — where did this mesh come from?
  source: z
    .object({
      method: z.enum([
        "ct_segmentation",          // Segmented from CT scan
        "mri_segmentation",         // Segmented from MRI
        "photogrammetry",           // 3D scanned from physical specimen
        "statistical_shape_model",  // Generated from SSM (e.g., Statismo, SPHARM-PDM)
        "manual_modeling",          // Hand-modeled in CAD/DCC tool
        "procedural",              // Generated from parametric rules
        "literature",              // Digitized from published atlas
        "unknown",
      ]).describe("How the mesh geometry was obtained"),
      resolution: z
        .number()
        .positive()
        .optional()
        .describe("Source voxel/scan resolution in mm (for imaging-derived meshes)"),
      datasetId: z
        .string()
        .optional()
        .describe("Identifier of the source dataset (e.g., 'visible_human_male', 'TCIA_LCTSC')"),
      citation: z
        .string()
        .optional()
        .describe("Bibliographic reference for the source data"),
    })
    .optional()
    .describe("Provenance of the mesh data"),

  extensions: ExtensionsSchema,
});

// =============================================================================
// Representation 3: External Asset Reference
//
// A lightweight pointer to an externally hosted mesh file. The schema
// carries only the reference metadata — the actual geometry lives in a
// glTF, OBJ, STL, or PLY file resolved via URI. This is the production
// choice for asset pipelines: the JSON stays small, meshes can be
// versioned and cached independently, and the same schema can reference
// different LOD bundles per platform.
//
// The URI scheme is deliberately format-agnostic. A consumer resolves
// the URI, inspects the content type, and loads accordingly. The schema
// does record the expected format so parsers can fail fast on mismatch.
//
// Security note: consumers MUST validate URIs before fetching. The
// schema does not enforce a URI allowlist — that is a runtime concern.
//
// Reference: Khronos Group, glTF 2.0 §3.1 (asset referencing model).
// =============================================================================

export const MeshFormatEnum = z.enum([
  "gltf2",        // glTF 2.0 JSON + separate .bin (recommended)
  "glb",          // glTF 2.0 binary container
  "obj",          // Wavefront OBJ + MTL
  "stl_binary",   // STL binary (no color, no normals — geometry only)
  "stl_ascii",    // STL ASCII
  "ply",          // Stanford PLY (supports per-vertex color/density)
  "fbx",          // Autodesk FBX (wide tool support, proprietary format)
  "usdz",         // Universal Scene Description (Apple AR ecosystem)
]);

export const ExternalAssetGeometrySchema = z.object({
  geometryType: z.literal("external_asset"),
  id: GeometryId,
  boneId: BoneId.describe("Bone this geometry represents"),

  // Primary asset
  uri: z
    .string()
    .url()
    .regex(
      /^(https?:\/\/|file:\/\/|asset:\/\/)/,
      "URI must use https://, http://, file://, or asset:// scheme",
    )
    .describe("URI to the mesh file (HTTPS, file://, or asset:// scheme)"),
  format: MeshFormatEnum.describe("Expected file format"),
  byteSize: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("Expected file size in bytes (for progress indication and cache validation)"),
  contentHash: z
    .string()
    .optional()
    .describe("SHA-256 hex digest of the file content (for integrity verification)"),

  // LOD variants — additional URIs for lower-resolution versions
  lodVariants: z
    .array(
      z.object({
        level: z.number().int().min(1).describe("LOD level (1 = first reduction from base)"),
        uri: z.string().url(),
        format: MeshFormatEnum,
        approximateTriangleCount: z.number().int().positive().optional(),
      }),
    )
    .optional()
    .describe("Lower-resolution variants for distance-based LOD switching"),

  // Coordinate space contract — what the consumer should expect
  coordinateSpace: z
    .object({
      upAxis: z.enum(["Y", "Z"]).default("Y").describe("Which axis is 'up' in the file (Y = glTF/OpenGL, Z = Blender/3ds Max)"),
      units: z.enum(["cm", "mm", "m", "inches"]).default("cm").describe("Length unit of the vertex coordinates"),
      handedness: z.enum(["right", "left"]).default("right"),
    })
    .optional()
    .describe("Coordinate space metadata — consumer must transform to match schema convention (Y-up, cm, right-handed)"),

  // Landmarks can still be declared even without inline vertices
  landmarks: z
    .array(AnatomicalLandmarkSchema)
    .optional()
    .describe("Anatomical landmarks (positions in bone-local frame, independent of mesh resolution)"),

  extensions: ExtensionsSchema,
});

// =============================================================================
// Discriminated Union — The Single Entry Point
// =============================================================================

export const BoneGeometrySchema = z.discriminatedUnion("geometryType", [
  ParametricCSGGeometrySchema,
  IndexedMeshGeometrySchema,
  ExternalAssetGeometrySchema,
]);

// =============================================================================
// Integration Point — How This Attaches to BoneSchema
//
// This module does NOT modify skeletal.ts. Instead, the HumanBody root
// entity gains a new optional array field:
//
//   boneGeometries: z.array(BoneGeometrySchema).optional()
//
// Each entry references a bone via `boneId` (referential integrity
// checked by the root superRefine). A bone may have 0 or 1 geometry
// entries. Multiple representations for the same bone are not allowed
// in a single document — pick the one that matches your pipeline.
//
// This avoids a breaking change to BoneSchema (which would force all
// existing consumers to update). It also keeps geometry optional: a
// schema instance used purely for biomechanical analysis doesn't need
// meshes, and a schema instance used for rendering doesn't need to
// carry force data.
// =============================================================================

// --- Inferred Types ---

export type CSGPrimitive = z.infer<typeof CSGPrimitiveSchema>;
export type ParametricCSGGeometry = z.infer<typeof ParametricCSGGeometrySchema>;
export type MeshLOD = z.infer<typeof MeshLODSchema>;
export type AnatomicalLandmark = z.infer<typeof AnatomicalLandmarkSchema>;
export type SurfaceRegion = z.infer<typeof SurfaceRegionSchema>;
export type IndexedMeshGeometry = z.infer<typeof IndexedMeshGeometrySchema>;
export type ExternalAssetGeometry = z.infer<typeof ExternalAssetGeometrySchema>;
export type BoneGeometry = z.infer<typeof BoneGeometrySchema>;
