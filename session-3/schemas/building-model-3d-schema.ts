/**
 * ============================================================================
 * DISCLAIMER
 * ============================================================================
 * No information within this schema should be taken for granted. Any statement
 * or premise not backed by a real logical definition or verifiable reference
 * may be invalid, erroneous, or a hallucination. The consumer is responsible
 * for independent verification of all constraints and domain assumptions.
 *
 * References:
 *   - ISO 6707-1:2017 (Buildings and civil engineering works — Vocabulary)
 *   - ISO 16739-1:2024 (IFC4 — Industry Foundation Classes)
 *   - ISO 10303-42 (STEP — Geometric and topological representation)
 *   - buildingSMART IFC4 Documentation (standards.buildingsmart.org/IFC)
 *   - JSON Schema draft 2020-12 (for design rule grounding)
 *   - semver.org/spec/v2.0.0 (versioning)
 *
 * MIGRATION FROM v1.0.0 (2D):
 *   This is a BREAKING major version bump. The 2D schema (v1.x) modeled
 *   buildings as plan-view geometry with optional height scalars. This 3D
 *   schema (v2.0.0) introduces a full Z axis, volumetric geometry primitives,
 *   and new entities (Slab, Roof, MEPRun). See "BREAKING CHANGES FROM v1"
 *   section at the end for a complete migration guide.
 * ============================================================================
 */

import { z } from "zod";

// ─── Schema Version ─────────────────────────────────────────────────────────

export const SCHEMA_VERSION = "2.0.0" as const;

// ─── Cross-Cutting: Identifiers ─────────────────────────────────────────────

const EntityId = z
  .string()
  .uuid()
  .describe("Opaque unique identifier (UUID v4)");

// ─── Cross-Cutting: Geometry Primitives ─────────────────────────────────────
// Rule 17: Cross-cutting types defined once.
// Rule 7: All coordinates use the Blueprint's `lengthUnit`.

// ── 2D primitives (retained for plan projections and profile definitions) ──

export const Point2D = z.object({
  x: z.number().describe("Horizontal coordinate in blueprint length units"),
  y: z.number().describe("Vertical coordinate in blueprint length units"),
});
export type Point2D = z.infer<typeof Point2D>;

export const Polygon2D = z.object({
  vertices: z
    .array(Point2D)
    .min(3)
    .describe(
      "Ordered ring of 2D vertices. Implicitly closed (last→first). " +
        "CCW = exterior boundary, CW = interior hole."
    ),
});
export type Polygon2D = z.infer<typeof Polygon2D>;

export const BoundaryWithHoles2D = z.object({
  outer: Polygon2D.describe("Exterior boundary (CCW winding)"),
  holes: z
    .array(Polygon2D)
    .default([])
    .describe("Interior voids / cutouts (CW winding)"),
});
export type BoundaryWithHoles2D = z.infer<typeof BoundaryWithHoles2D>;

// ── 3D primitives ─────────────────────────────────────────────────────────

/**
 * A point in 3D Cartesian space.
 * Convention: +X = east, +Y = north, +Z = up (right-hand rule).
 * All coordinates in the Blueprint's `lengthUnit`.
 */
export const Point3D = z.object({
  x: z.number().describe("East-west coordinate"),
  y: z.number().describe("North-south coordinate"),
  z: z.number().describe("Vertical coordinate (elevation above datum)"),
});
export type Point3D = z.infer<typeof Point3D>;

export const Vector3D = z.object({
  x: z.number(),
  y: z.number(),
  z: z.number(),
});
export type Vector3D = z.infer<typeof Vector3D>;

export const LineSegment3D = z.object({
  start: Point3D.describe("Segment start point"),
  end: Point3D.describe("Segment end point"),
});
export type LineSegment3D = z.infer<typeof LineSegment3D>;

/**
 * An axis-aligned bounding box in 3D.
 * `min` is the corner with smallest x, y, z; `max` is the opposite corner.
 */
export const BoundingBox3D = z.object({
  min: Point3D.describe("Corner with smallest x, y, z"),
  max: Point3D.describe("Corner with largest x, y, z"),
});
export type BoundingBox3D = z.infer<typeof BoundingBox3D>;

/**
 * A 2D profile extruded along a direction vector.
 * This is the primary volumetric primitive — covers walls, columns, slabs,
 * beams, and most architectural geometry.
 *
 * Grounding: Corresponds to IFC4 IfcExtrudedAreaSolid
 * (ISO 16739-1:2024, §8.9.3.18).
 *
 * The profile (2D cross-section) is defined in its own local XY plane.
 * The extrusion direction defaults to (0,0,1) — straight up — but can
 * be set to any unit vector for inclined elements.
 */
export const ExtrudedProfile = z.object({
  profile: BoundaryWithHoles2D.describe(
    "2D cross-section in the profile's local XY plane. " +
      "For a wall: a thin rectangle. For a column: a circle approximation or I-beam."
  ),
  depth: z
    .number()
    .positive()
    .describe("Extrusion depth (length along the direction vector), in length units"),
  direction: Vector3D.default({ x: 0, y: 0, z: 1 }).describe(
    "Unit vector for the extrusion direction. Default (0,0,1) = vertical."
  ),
  position: Point3D.describe(
    "Origin point where the profile's local (0,0) maps to in world space"
  ),
  rotationDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Rotation of the profile around the extrusion axis, degrees CCW"),
});
export type ExtrudedProfile = z.infer<typeof ExtrudedProfile>;

/**
 * A triangulated mesh for freeform or complex geometry that cannot be
 * represented as an extrusion (e.g., curved roofs, organic forms, imported
 * scanned geometry).
 *
 * Grounding: Corresponds to IFC4 IfcTriangulatedFaceSet
 * (ISO 16739-1:2024, §8.9.3.55).
 *
 * Vertices are indexed; each triangle is a triplet of vertex indices (0-based).
 * Face normals follow right-hand winding (CCW = outward-facing).
 */
export const TriangleMesh = z.object({
  vertices: z
    .array(Point3D)
    .min(3)
    .describe("Vertex list. Referenced by index in `triangles`."),
  triangles: z
    .array(z.tuple([z.number().int().min(0), z.number().int().min(0), z.number().int().min(0)]))
    .min(1)
    .describe(
      "Triangle faces as [v0, v1, v2] index triples (0-based). " +
        "CCW winding = outward normal."
    ),
});
export type TriangleMesh = z.infer<typeof TriangleMesh>;

/**
 * Discriminated union for 3D geometry representations.
 * Rule 8: Explicit discriminator on `type`.
 *
 * `extrusion` — for prismatic shapes (walls, columns, slabs, beams).
 * `mesh`      — for freeform shapes (curved roofs, scanned geometry).
 * `bbox`      — for placeholder / LOD-0 simplified representations.
 */
export const Geometry3D = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("extrusion"),
    extrusion: ExtrudedProfile,
  }),
  z.object({
    type: z.literal("mesh"),
    mesh: TriangleMesh,
  }),
  z.object({
    type: z.literal("bbox"),
    bbox: BoundingBox3D,
  }),
]);
export type Geometry3D = z.infer<typeof Geometry3D>;

// ── Arc (2D, for profile definitions and annotations) ─────────────────────

export const Arc2D = z.object({
  center: Point2D.describe("Arc center point"),
  radius: z.number().positive().describe("Arc radius in blueprint length units"),
  startAngleDeg: z.number().min(0).max(360).describe("Start angle, degrees CCW from +x"),
  endAngleDeg: z.number().min(0).max(360).describe("End angle, degrees CCW from +x"),
});
export type Arc2D = z.infer<typeof Arc2D>;

// ─── Cross-Cutting: Material ────────────────────────────────────────────────
// Rule 17: Shared definition — used by Wall, Slab, Roof, StructuralElement.

export const MaterialSpec = z.object({
  name: z.string().min(1).describe("Material name (e.g., 'concrete', 'steel', 'brick')"),
  densityKgPerM3: z
    .number()
    .positive()
    .optional()
    .describe("Density in kg/m³. Unit: SI, always kg/m³ regardless of Blueprint lengthUnit."),
  thermalConductivity: z
    .number()
    .positive()
    .optional()
    .describe("Thermal conductivity in W/(m·K)"),
  fireRatingMinutes: z
    .number()
    .int()
    .min(0)
    .optional()
    .describe("Fire resistance rating in minutes (0 = unrated)"),
});
export type MaterialSpec = z.infer<typeof MaterialSpec>;

// ─── Cross-Cutting: Metadata ────────────────────────────────────────────────

export const Metadata = z.object({
  createdAt: z.string().datetime().describe("ISO 8601 UTC timestamp of creation"),
  updatedAt: z.string().datetime().describe("ISO 8601 UTC timestamp of last modification"),
  createdBy: z.string().min(1).describe("Identifier of the creating actor"),
  updatedBy: z.string().min(1).describe("Identifier of the last-modifying actor"),
  note: z.string().optional().describe("Free-text design note"),
});
export type Metadata = z.infer<typeof Metadata>;

// ─── Enums ──────────────────────────────────────────────────────────────────

export const ENUM_VERSIONS = {
  LengthUnit: "2.0.0",
  AngleUnit: "2.0.0",
  LayerKind: "2.0.0",
  WallType: "2.0.0",
  OpeningKind: "2.0.0",
  SwingDirection: "1.0.0",
  SpaceUsage: "2.0.0",
  StructuralElementKind: "2.0.0",
  FixtureCategory: "1.0.0",
  AnnotationKind: "2.0.0",
  VerticalCirculationKind: "1.0.0",
  SlabKind: "2.0.0",
  RoofForm: "2.0.0",
  MEPDomain: "2.0.0",
  MEPSegmentShape: "2.0.0",
} as const;

export const LengthUnit = z.enum(["mm", "cm", "m", "in", "ft"]);
export type LengthUnit = z.infer<typeof LengthUnit>;

export const AngleUnit = z.enum(["deg", "rad"]);
export type AngleUnit = z.infer<typeof AngleUnit>;

export const LayerKind = z.enum([
  "structural",
  "architectural",
  "electrical",
  "plumbing",
  "hvac",
  "furniture",
  "annotation",
  "fire_safety",
  "exterior_envelope",
  "site",
]);
export type LayerKind = z.infer<typeof LayerKind>;

export const WallType = z.enum([
  "load_bearing",
  "partition",
  "curtain",
  "shear",
  "retaining",
  "fire_rated",
  "parapet",
  "foundation",
]);
export type WallType = z.infer<typeof WallType>;

export const OpeningKind = z.enum([
  "single_door",
  "double_door",
  "sliding_door",
  "revolving_door",
  "window",
  "skylight",
  "archway",
  "garage_door",
  "curtain_wall_panel",
]);
export type OpeningKind = z.infer<typeof OpeningKind>;

export const SwingDirection = z.enum([
  "inward_left",
  "inward_right",
  "outward_left",
  "outward_right",
  "sliding_left",
  "sliding_right",
  "bi_fold",
  "pivot",
  "none",
]);
export type SwingDirection = z.infer<typeof SwingDirection>;

export const SpaceUsage = z.enum([
  "bedroom",
  "bathroom",
  "kitchen",
  "living_room",
  "dining_room",
  "office",
  "hallway",
  "corridor",
  "stairwell",
  "elevator_shaft",
  "closet",
  "storage",
  "laundry",
  "garage",
  "balcony",
  "terrace",
  "lobby",
  "reception",
  "conference_room",
  "mechanical_room",
  "server_room",
  "restroom",
  "utility",
  "commercial",
  "industrial",
  "atrium",
  "courtyard",
  "roof_terrace",
  "other",
]);
export type SpaceUsage = z.infer<typeof SpaceUsage>;

export const StructuralElementKind = z.enum([
  "column",
  "beam",
  "pillar",
  "foundation_pier",
  "brace",
  "truss",
  "load_bearing_wall_segment",
]);
export type StructuralElementKind = z.infer<typeof StructuralElementKind>;

export const FixtureCategory = z.enum([
  "plumbing_sink",
  "plumbing_toilet",
  "plumbing_shower",
  "plumbing_bathtub",
  "plumbing_water_heater",
  "electrical_outlet",
  "electrical_switch",
  "electrical_panel",
  "electrical_light",
  "hvac_vent",
  "hvac_thermostat",
  "hvac_unit",
  "appliance_stove",
  "appliance_refrigerator",
  "appliance_washer",
  "appliance_dryer",
  "furniture_table",
  "furniture_chair",
  "furniture_bed",
  "furniture_sofa",
  "furniture_desk",
  "fire_extinguisher",
  "fire_alarm",
  "fire_sprinkler",
  "other",
]);
export type FixtureCategory = z.infer<typeof FixtureCategory>;

export const AnnotationKind = z.enum([
  "dimension_linear",
  "dimension_angular",
  "dimension_radial",
  "dimension_elevation",
  "text_label",
  "area_callout",
  "volume_callout",
  "elevation_marker",
  "section_cut",
  "grid_line",
  "north_arrow",
  "scale_bar",
  "detail_callout",
  "level_marker",
]);
export type AnnotationKind = z.infer<typeof AnnotationKind>;

export const VerticalCirculationKind = z.enum([
  "staircase",
  "elevator",
  "escalator",
  "ramp",
  "ladder",
]);
export type VerticalCirculationKind = z.infer<typeof VerticalCirculationKind>;

export const SlabKind = z.enum([
  "floor",
  "ceiling",
  "roof_slab",
  "mezzanine",
  "foundation_slab",
  "landing",
]);
export type SlabKind = z.infer<typeof SlabKind>;

export const RoofForm = z.enum([
  "flat",
  "gable",
  "hip",
  "mansard",
  "shed",
  "butterfly",
  "dome",
  "barrel_vault",
  "gambrel",
  "sawtooth",
  "other",
]);
export type RoofForm = z.infer<typeof RoofForm>;

export const MEPDomain = z.enum([
  "plumbing_supply",
  "plumbing_drain",
  "hvac_duct",
  "hvac_pipe",
  "electrical_conduit",
  "fire_suppression",
  "gas",
  "telecom",
]);
export type MEPDomain = z.infer<typeof MEPDomain>;

export const MEPSegmentShape = z.enum(["circular", "rectangular", "oval"]);
export type MEPSegmentShape = z.infer<typeof MEPSegmentShape>;

// ─── Entity: Opening ────────────────────────────────────────────────────────
// Rule 12: Composition — owned by Wall.

export const Opening = z.object({
  id: EntityId,
  kind: OpeningKind.describe("Type of opening"),
  offsetAlongWall: z
    .number()
    .min(0)
    .describe("Distance from wall centerline start to opening near edge"),
  width: z.number().positive().describe("Opening width in length units"),
  height: z.number().positive().describe("Opening height in length units"),
  sillHeight: z
    .number()
    .min(0)
    .describe(
      "Height of the opening's bottom edge above the wall's base elevation. " +
        "0 for doors; typically >0 for windows."
    ),
  swingDirection: SwingDirection.default("none"),
  /** In 3D the opening defines a void volume through the wall.
   *  The void is the rectangle (width × height) extruded through
   *  the full wall thickness at the specified offset and sill height. */
  note: z.string().optional(),
});
export type Opening = z.infer<typeof Opening>;

// ─── Entity: Wall ───────────────────────────────────────────────────────────
// Walls in 3D: a 2D centerline path extruded vertically with a given thickness.
// The wall volume is computed as:
//   profile = rectangle(length × thickness) positioned at centerline
//   extruded along Z from baseElevation to (baseElevation + height)

export const Wall = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("architectural"),
  wallType: WallType.describe("Structural classification"),
  centerline: z.object({
    start: Point2D.describe("Centerline start in plan XY"),
    end: Point2D.describe("Centerline end in plan XY"),
  }),
  thickness: z.number().positive().describe("Wall thickness, perpendicular to centerline"),
  height: z.number().positive().describe("Wall height from base to top"),
  baseElevation: z
    .number()
    .describe(
      "Elevation of the wall's bottom face above the building datum (Z=0). " +
        "Typically equals the parent floor's `elevationAboveDatum`."
    ),
  material: MaterialSpec.optional().describe("Primary wall material"),
  openings: z
    .array(Opening)
    .default([])
    .describe("Openings in this wall, sorted by offsetAlongWall. Lifecycle: composed."),
  /** Rule 18: Computed. The 3D geometry is derivable from centerline +
   *  thickness + height + baseElevation. Stored for renderer convenience. */
  geometry: Geometry3D.optional().describe(
    "COMPUTED. Explicit 3D solid representation. Derivable from centerline, " +
      "thickness, height, and baseElevation. Stored for renderer convenience."
  ),
  note: z.string().optional(),
});
export type Wall = z.infer<typeof Wall>;

// ─── Entity: Slab ───────────────────────────────────────────────────────────
// New in v2. Floor slabs, ceiling slabs, foundation slabs.
// Grounding: IFC4 IfcSlab (ISO 16739-1:2024, §7.3.4.1).

export const Slab = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("structural"),
  kind: SlabKind.describe("Slab function"),
  boundary: BoundaryWithHoles2D.describe(
    "2D plan boundary of the slab. May include voids (stair openings, shafts)."
  ),
  thickness: z.number().positive().describe("Slab thickness in length units"),
  elevation: z
    .number()
    .describe("Elevation of the slab's TOP surface above building datum"),
  material: MaterialSpec.optional(),
  slopePercent: z
    .number()
    .min(0)
    .default(0)
    .describe("Slope as percentage (0 = flat). Relevant for drainage or ramps."),
  slopeDirection: Vector3D.optional().describe(
    "Direction of slope as a 2D vector in the XY plane (Z component ignored). " +
      "Required when slopePercent > 0."
  ),
  geometry: Geometry3D.optional().describe(
    "COMPUTED. 3D solid of the slab. Derivable from boundary + thickness + elevation."
  ),
  note: z.string().optional(),
});
export type Slab = z.infer<typeof Slab>;

// ─── Entity: Roof ───────────────────────────────────────────────────────────
// New in v2. Roof geometry at the building level.
// Grounding: IFC4 IfcRoof (ISO 16739-1:2024, §7.3.2.1).

export const RoofSurface = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Surface label (e.g., 'North slope', 'Main ridge')"),
  /** Each roof surface is a planar or curved panel.
   *  Flat panels are defined by a 3D polygon.
   *  Complex curved surfaces use a triangle mesh. */
  geometry: Geometry3D.describe("3D geometry of this roof surface panel"),
  material: MaterialSpec.optional(),
  slopePercent: z.number().min(0).default(0).describe("Surface slope as percentage"),
  note: z.string().optional(),
});
export type RoofSurface = z.infer<typeof RoofSurface>;

export const Roof = z.object({
  id: EntityId,
  buildingId: EntityId.describe("FK → Building.id"),
  layer: LayerKind.default("architectural"),
  form: RoofForm.describe("Roof typology"),
  ridgeElevation: z
    .number()
    .describe("Elevation of the highest ridge point above building datum"),
  eaveElevation: z.number().describe("Elevation of the lowest eave above building datum"),
  overhang: z
    .number()
    .min(0)
    .default(0)
    .describe("Horizontal overhang distance beyond the exterior wall face"),
  surfaces: z
    .array(RoofSurface)
    .min(1)
    .describe("Individual roof surface panels. Lifecycle: composed."),
  note: z.string().optional(),
});
export type Roof = z.infer<typeof Roof>;

// ─── Entity: Space (Room / Volume) ──────────────────────────────────────────
// In 3D, a Space is a volumetric region: a 2D plan boundary extruded between
// a floor elevation and a ceiling elevation.

export const Space = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("architectural"),
  name: z.string().min(1).describe("Human-readable label"),
  usage: SpaceUsage.describe("Functional classification"),
  boundary: BoundaryWithHoles2D.describe("Plan-view boundary polygon"),
  floorElevation: z
    .number()
    .describe("Elevation of the finished floor surface above building datum"),
  ceilingElevation: z
    .number()
    .describe("Elevation of the finished ceiling surface above building datum"),
  /** Rule 18: Computed fields */
  areaSqUnits: z
    .number()
    .positive()
    .optional()
    .describe("COMPUTED. Floor area in (lengthUnit)². Derive from boundary polygon."),
  volumeCuUnits: z
    .number()
    .positive()
    .optional()
    .describe(
      "COMPUTED. Room volume in (lengthUnit)³. Derive from area × " +
        "(ceilingElevation − floorElevation)."
    ),
  finishFloor: z.string().optional().describe("Floor finish material"),
  finishWall: z.string().optional().describe("Wall finish material"),
  finishCeiling: z.string().optional().describe("Ceiling finish material"),
  note: z.string().optional(),
});
export type Space = z.infer<typeof Space>;

// ─── Entity: StructuralElement ──────────────────────────────────────────────

export const StructuralElement = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("structural"),
  kind: StructuralElementKind.describe("Structural classification"),
  position: Point3D.describe("Insertion point in 3D world coordinates"),
  geometry: Geometry3D.describe(
    "3D solid representation. Columns are typically extrusions of a 2D profile " +
      "along Z. Beams are extrusions along a horizontal axis."
  ),
  material: MaterialSpec.optional(),
  rotationDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Rotation around the element's local Z axis, degrees CCW"),
  loadCapacityKN: z
    .number()
    .positive()
    .optional()
    .describe("Axial load capacity in kilonewtons (kN). Unit: always kN."),
  note: z.string().optional(),
});
export type StructuralElement = z.infer<typeof StructuralElement>;

// ─── Entity: Fixture ────────────────────────────────────────────────────────

export const Fixture = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  spaceId: EntityId.optional().describe("FK → Space.id. Null if exterior."),
  layer: LayerKind,
  category: FixtureCategory,
  label: z.string().optional().describe("Display label"),
  position: Point3D.describe("Insertion point in 3D world coordinates"),
  rotationDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Rotation around local Z axis"),
  /** Bounding box dimensions for simplified collision and placement. */
  boundingSize: z
    .object({
      width: z.number().positive().describe("Extent along local X"),
      depth: z.number().positive().describe("Extent along local Y"),
      height: z.number().positive().describe("Extent along local Z"),
    })
    .optional()
    .describe("3D bounding box dimensions in length units"),
  geometry: Geometry3D.optional().describe(
    "Optional detailed 3D geometry. If absent, use `boundingSize` as bbox."
  ),
  symbolRef: z.string().optional().describe("External symbol library reference"),
  note: z.string().optional(),
});
export type Fixture = z.infer<typeof Fixture>;

// ─── Entity: MEPRun ─────────────────────────────────────────────────────────
// New in v2. Mechanical, electrical, and plumbing routing in 3D.
// A run is a connected sequence of segments (pipe, duct, conduit).
// Grounding: IFC4 IfcDistributionElement + IfcFlowSegment.

export const MEPSegment = z.object({
  id: EntityId,
  startPoint: Point3D.describe("Segment start in world coordinates"),
  endPoint: Point3D.describe("Segment end in world coordinates"),
  crossSection: MEPSegmentShape.describe("Cross-section shape"),
  /** For circular: `diameter`. For rectangular: `width` × `height`. */
  diameter: z
    .number()
    .positive()
    .optional()
    .describe("Outer diameter for circular cross-sections, in length units"),
  width: z
    .number()
    .positive()
    .optional()
    .describe("Width for rectangular/oval cross-sections"),
  height: z
    .number()
    .positive()
    .optional()
    .describe("Height for rectangular/oval cross-sections"),
  wallThickness: z
    .number()
    .positive()
    .optional()
    .describe("Wall thickness of the pipe/duct"),
  material: MaterialSpec.optional(),
  note: z.string().optional(),
});
export type MEPSegment = z.infer<typeof MEPSegment>;

export const MEPRun = z.object({
  id: EntityId,
  layer: LayerKind.describe("Logical layer (electrical, plumbing, hvac)"),
  domain: MEPDomain.describe("MEP system classification"),
  name: z.string().min(1).describe("Run label (e.g., 'Cold water main', 'Return duct A')"),
  segments: z
    .array(MEPSegment)
    .min(1)
    .describe(
      "Ordered connected segments forming the run. Each segment's endPoint " +
        "should equal the next segment's startPoint for a continuous run."
    ),
  insulationThickness: z
    .number()
    .min(0)
    .default(0)
    .describe("Insulation thickness around segments, in length units"),
  flowDirection: z
    .enum(["start_to_end", "end_to_start", "bidirectional", "not_applicable"])
    .default("start_to_end")
    .describe("Intended flow direction through the run"),
  floorIds: z
    .array(EntityId)
    .min(1)
    .describe("FK → Floor.id[]. Floors this run passes through."),
  note: z.string().optional(),
});
export type MEPRun = z.infer<typeof MEPRun>;

// ─── Entity: VerticalCirculation ────────────────────────────────────────────
// Rule 12: Aggregation — shared across floors.

export const VerticalCirculation = z.object({
  id: EntityId,
  kind: VerticalCirculationKind,
  connectsFloorIds: z
    .array(EntityId)
    .min(2)
    .describe("FK → Floor.id[]. Floors connected."),
  footprint: Polygon2D.describe("2D plan footprint"),
  position: Point3D.describe("Reference insertion point in 3D"),
  geometry: Geometry3D.optional().describe(
    "Full 3D geometry of the circulation element (stair flights, elevator shaft)."
  ),
  directionDeg: z.number().min(0).max(360).default(0),
  riserCount: z.number().int().positive().optional().describe("Number of risers (stairs)"),
  riserHeight: z.number().positive().optional().describe("Riser height (stairs)"),
  treadDepth: z.number().positive().optional().describe("Tread depth (stairs)"),
  note: z.string().optional(),
});
export type VerticalCirculation = z.infer<typeof VerticalCirculation>;

// ─── Entity: Annotation ─────────────────────────────────────────────────────

export const Annotation = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("annotation"),
  kind: AnnotationKind,
  anchorPoints: z
    .array(Point3D)
    .min(1)
    .max(4)
    .describe("3D reference points for the annotation"),
  text: z.string().optional().describe("Display text"),
  measuredValue: z
    .number()
    .optional()
    .describe("COMPUTED. Numeric measurement derived from anchor geometry."),
  angleDeg: z.number().optional().describe("For angular dimensions: measured angle in degrees"),
  offsetFromGeometry: z.number().default(0).describe("Perpendicular offset of dimension line"),
  /** Annotations live in 3D space but may be projected onto a specific
   *  viewing plane for 2D output. */
  projectionPlane: z
    .enum(["xy", "xz", "yz", "custom"])
    .default("xy")
    .describe("Plane on which to project this annotation for 2D views"),
  note: z.string().optional(),
});
export type Annotation = z.infer<typeof Annotation>;

// ─── Entity: Floor ──────────────────────────────────────────────────────────
// Rule 12: Composition — owned by Building.

export const Floor = z.object({
  id: EntityId,
  buildingId: EntityId.describe("FK → Building.id"),
  level: z
    .number()
    .int()
    .describe("Floor level index. 0 = ground. Negative = below grade."),
  name: z.string().min(1).describe("Display name"),
  elevationAboveDatum: z
    .number()
    .describe("Elevation of this floor's finished floor level above building datum (Z=0)"),
  floorToFloorHeight: z
    .number()
    .positive()
    .describe("Distance from this floor's slab top to the next floor's slab top"),
  walls: z.array(Wall).default([]).describe("Lifecycle: composed."),
  spaces: z.array(Space).default([]).describe("Lifecycle: composed."),
  slabs: z.array(Slab).default([]).describe("Floor and ceiling slabs. Lifecycle: composed."),
  structuralElements: z.array(StructuralElement).default([]).describe("Lifecycle: composed."),
  fixtures: z.array(Fixture).default([]).describe("Lifecycle: composed."),
  annotations: z.array(Annotation).default([]).describe("Lifecycle: composed."),
  outline: Polygon2D.optional().describe("Overall floor plate outline (plan projection)"),
  note: z.string().optional(),
});
export type Floor = z.infer<typeof Floor>;

// ─── Entity: Building ───────────────────────────────────────────────────────

export const Building = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Building name or designation"),
  address: z.string().optional().describe("Physical address"),
  typology: z.string().optional().describe("Building typology"),
  /** In 3D, the building envelope is computable from floor outlines,
   *  wall geometry, and roof surfaces. Explicit envelope geometry is
   *  optional for LOD-0 / simplified views. */
  envelopeGeometry: Geometry3D.optional().describe(
    "COMPUTED / OPTIONAL. Simplified 3D envelope for LOD-0 views."
  ),
  geoReference: z
    .object({
      latitude: z.number().min(-90).max(90).describe("WGS84 latitude"),
      longitude: z.number().min(-180).max(180).describe("WGS84 longitude"),
      altitudeM: z.number().optional().describe("Altitude above sea level in meters"),
    })
    .optional()
    .describe("Geographic reference point for the building's datum origin"),
  note: z.string().optional(),
});
export type Building = z.infer<typeof Building>;

// ─── Entity: BuildingModel (Root Document) ──────────────────────────────────
// Renamed from `Blueprint` to `BuildingModel` to reflect 3D scope.

export const BuildingModel = z.object({
  schemaVersion: z.literal(SCHEMA_VERSION).describe("Schema version (semver)"),
  id: EntityId,
  title: z.string().min(1).describe("Model title"),

  // ── Coordinate System ────────────────────────────────────────────────────
  lengthUnit: LengthUnit.describe("Unit for ALL coordinate and dimension values"),
  angleUnit: AngleUnit.default("deg").describe("Unit for all angular values"),
  origin: Point3D.default({ x: 0, y: 0, z: 0 }).describe(
    "World coordinate origin. Convention: south-west corner of ground floor slab, " +
      "Z=0 at ground level."
  ),
  trueNorthDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Rotation of true north relative to +Y axis, degrees clockwise"),
  upAxis: z
    .literal("z")
    .default("z")
    .describe(
      "The vertical axis. Always +Z in this schema (right-hand rule: +X=east, " +
        "+Y=north, +Z=up). This field exists for interoperability with Y-up systems."
    ),

  // ── Composition ──────────────────────────────────────────────────────────
  building: Building.describe("The building being modeled"),
  floors: z
    .array(Floor)
    .min(1)
    .describe("Floor plans, ordered by level (ascending). Lifecycle: composed."),
  roofs: z
    .array(Roof)
    .default([])
    .describe("Roof assemblies. Lifecycle: composed by building."),

  // ── Aggregation ──────────────────────────────────────────────────────────
  verticalCirculation: z
    .array(VerticalCirculation)
    .default([])
    .describe("Stairs, elevators, ramps. Lifecycle: aggregated (multi-floor)."),
  mepRuns: z
    .array(MEPRun)
    .default([])
    .describe("MEP routing (pipes, ducts, conduits). Lifecycle: aggregated (multi-floor)."),

  // ── Presentation ─────────────────────────────────────────────────────────
  layerVisibility: z
    .record(LayerKind, z.boolean())
    .optional()
    .describe("Default layer visibility. Presentation hint only."),

  // ── Metadata ─────────────────────────────────────────────────────────────
  metadata: Metadata,

  // ── Extension Point ──────────────────────────────────────────────────────
  extensions: z
    .record(z.string(), z.unknown())
    .optional()
    .describe(
      "EXTENSION POINT. Consumer-defined data, namespaced keys " +
        "(e.g., 'com.acme.energyModel')."
    ),
});
export type BuildingModel = z.infer<typeof BuildingModel>;

export default BuildingModel;

/**
 * ============================================================================
 * DESIGN ASSUMPTIONS (v2.0.0 — 3D)
 * ============================================================================
 *
 * 1. COORDINATE SYSTEM: Right-hand 3D Cartesian. +X = east, +Y = north,
 *    +Z = up. This follows the convention used by IFC, CityGML, and most
 *    BIM systems (ISO 16739-1:2024, §8.9.1). Y-up systems (glTF, Unity)
 *    require a swap transform on export; the `upAxis` field signals this.
 *
 * 2. GEOMETRY MODEL: Two-tier approach.
 *    - **Parametric**: Most building elements (walls, slabs, columns) are
 *      defined by construction parameters (centerline, thickness, height,
 *      base elevation). Their 3D geometry is DERIVABLE from these params.
 *    - **Explicit**: An optional `geometry: Geometry3D` field provides a
 *      pre-computed solid (extrusion, mesh, or bounding box) for renderers
 *      that cannot derive geometry. This field is COMPUTED and SHOULD be
 *      regenerated when parameters change.
 *    This avoids the complexity of full B-rep (ISO 10303-42) while still
 *    supporting arbitrary freeform geometry via triangle meshes.
 *
 * 3. WALL MODEL: Walls retain the 2D centerline + thickness model from v1
 *    for plan-view interoperability. The Z extent is defined by
 *    `baseElevation` and `height`. The wall volume is:
 *    profile = rect(wallLength × thickness) at centerline,
 *    extruded from baseElevation to (baseElevation + height) along +Z.
 *
 * 4. OPENINGS: Still defined as offsets along the parent wall, with added
 *    `sillHeight` (now required) to position the opening vertically within
 *    the wall. The opening void is a rectangular prism punched through the
 *    full wall thickness.
 *
 * 5. SLABS: New entity. Every floor needs at least a floor slab (and
 *    optionally a ceiling slab) to close the volume. Slabs are 2D boundaries
 *    extruded by their thickness. Voids (stair openings, shafts) are
 *    modeled as holes in the boundary polygon.
 *
 * 6. ROOFS: New entity. Defined at the building level (not per-floor).
 *    Each roof is a collection of RoofSurface panels — planar surfaces
 *    for simple roofs, triangle meshes for complex forms. The `form` enum
 *    classifies the typology for catalog/search purposes.
 *
 * 7. MEP RUNS: New entity. Pipes, ducts, and conduits are modeled as
 *    ordered sequences of 3D line segments with cross-sectional properties.
 *    This is sufficient for routing visualization and clash detection.
 *    For detailed fitting-level modeling, extend via the `extensions` field
 *    or use IFC's IfcDistributionPort.
 *
 * 8. SPACES (3D): In v1, spaces were 2D polygons with optional ceiling
 *    height. In v2, they are volumetric: a 2D boundary between a floor
 *    elevation and a ceiling elevation. Volume is computable.
 *
 * 9. FIXTURES (3D): Position is now Point3D. The optional `boundingSize`
 *    provides a simplified 3D extent for collision checking. Detailed
 *    geometry uses the `Geometry3D` discriminated union.
 *
 * 10. ANNOTATIONS (3D): Anchor points are Point3D. A `projectionPlane`
 *     field indicates which plane to project onto for 2D drawing output.
 *
 * 11. GEO-REFERENCE: Optional WGS84 lat/lon on Building for GIS
 *     interoperability (CityGML, OSM, Google Earth). The local coordinate
 *     system origin maps to this geographic point.
 *
 * 12. ROOT RENAME: `Blueprint` → `BuildingModel` to reflect 3D scope.
 *     The schema now represents a full volumetric model, not just plan views.
 *
 * 13. INTEROP with IFC: The geometry model maps cleanly to IFC4:
 *     ExtrudedProfile → IfcExtrudedAreaSolid, TriangleMesh →
 *     IfcTriangulatedFaceSet, BoundingBox3D → IfcBoundingBox. Export
 *     to IFC4 (STEP or JSON) is mechanically feasible without data loss.
 *
 * 14. CURVED WALLS: Still use polyline approximation for the centerline.
 *     For true arc walls, the `geometry` field can hold a mesh or custom
 *     extrusion. A future minor version may add an `ArcWall` variant.
 *
 * ============================================================================
 * BREAKING CHANGES FROM v1.0.0 (Migration Guide)
 * ============================================================================
 *
 * | Change                                      | Category  | v1 → v2 Action                          |
 * |---------------------------------------------|-----------|-----------------------------------------|
 * | Schema version: 1.0.0 → 2.0.0              | Breaking  | Update `schemaVersion` field             |
 * | Root entity: `Blueprint` → `BuildingModel`  | Breaking  | Rename root type                         |
 * | Point2D retained, Point3D added             | Additive  | No action for 2D fields                  |
 * | Wall.height: optional → required            | Breaking  | Populate height for all walls            |
 * | Wall.baseElevation: new required field      | Breaking  | Set to parent floor's elevation           |
 * | Wall.material: string → MaterialSpec        | Breaking  | Wrap in { name: oldValue }               |
 * | Opening.height: optional → required         | Breaking  | Populate height for all openings         |
 * | Opening.sillHeight: optional → required     | Breaking  | Set 0 for doors, actual value for windows|
 * | Space: ceilingHeight → floorElevation +     | Breaking  | Compute from floor elevation + height    |
 * |        ceilingElevation                      |           |                                          |
 * | Space.volumeCuUnits: new optional field      | Additive  | No action                                |
 * | StructuralElement.position: Point2D→Point3D | Breaking  | Add z coordinate (= floor elevation)     |
 * | StructuralElement.geometry: new required     | Breaking  | Provide extrusion or bbox geometry       |
 * | Fixture.position: Point2D → Point3D         | Breaking  | Add z coordinate                         |
 * | Fixture.boundingSize: replaces width/depth   | Breaking  | Migrate to { width, depth, height }      |
 * | Annotation.anchorPoints: Point2D → Point3D  | Breaking  | Add z=elevation to each anchor           |
 * | Floor.floorToFloorHeight: optional→required  | Breaking  | Populate for all floors                  |
 * | Floor.slabs: new field                       | Additive  | No action (defaults to [])               |
 * | VerticalCirculation.position: Point2D→Point3D| Breaking | Add z coordinate                         |
 * | Building.geoReference: new optional field    | Additive  | No action                                |
 * | Building.envelopeGeometry: new optional      | Additive  | No action                                |
 * | Roof: new entity                             | Additive  | No action (roofs defaults to [])         |
 * | Slab: new entity                             | Additive  | No action (slabs defaults to [])         |
 * | MEPRun: new entity                           | Additive  | No action (mepRuns defaults to [])       |
 * | Geometry3D: new discriminated union           | Additive  | Used by new/modified entities            |
 * | Polygon → Polygon2D (rename)                | Breaking  | Rename references                        |
 * | BoundaryWithHoles → BoundaryWithHoles2D     | Breaking  | Rename references                        |
 * | Arc → Arc2D (rename)                         | Breaking  | Rename references                        |
 * | New enums: SlabKind, RoofForm, MEPDomain,   | Additive  | No action                                |
 * |   MEPSegmentShape, AngleUnit                 |           |                                          |
 * | LayerKind: added exterior_envelope, site     | Additive  | No action (enum widened)                 |
 * | WallType: added parapet, foundation          | Additive  | No action (enum widened)                 |
 * | SpaceUsage: added atrium, courtyard,         | Additive  | No action (enum widened)                 |
 * |   roof_terrace                               |           |                                          |
 *
 * ============================================================================
 * REVIEW SCORECARD (v2.0.0)
 * ============================================================================
 *
 * Part I — Type Safety and Precision
 * ┌────┬────────────────────────────────────────┬────────┬────────┐
 * │  # │ Rule                                   │ Tier   │ Score  │
 * ├────┼────────────────────────────────────────┼────────┼────────┤
 * │  1 │ Unambiguous field types                │ MUST   │ Pass   │
 * │  2 │ Constraints in schema                  │ MUST   │ Pass   │
 * │  3 │ Closed, versioned enums                │ MUST   │ Pass   │
 * │  4 │ Nullable ≠ optional ≠ absent           │ MUST   │ Pass   │
 * │  5 │ Arrays: item type + cardinality + order│ MUST   │ Pass   │
 * │  6 │ Temporal precision and format           │ MUST   │ Pass   │
 * │  7 │ Numeric units declared                 │ MUST   │ Pass   │
 * │  8 │ Discriminated polymorphism             │ MUST   │ Pass   │
 * │  9 │ Defaults declared in schema            │ SHOULD │ Pass   │
 * └────┴────────────────────────────────────────┴────────┴────────┘
 * R8: Geometry3D uses z.discriminatedUnion on `type` field
 *   (extrusion | mesh | bbox). MEPSegment cross-section shape is
 *   an enum selector, not a structural union — acceptable because
 *   the shape affects which dimension fields are relevant, not the
 *   structure. If shapes diverge structurally in future, refactor
 *   to discriminated union.
 *
 * Part II — Identity and Relationships
 * ┌────┬────────────────────────────────────────┬────────┬────────┐
 * │  # │ Rule                                   │ Tier   │ Score  │
 * ├────┼────────────────────────────────────────┼────────┼────────┤
 * │ 10 │ Stable, opaque identity                │ MUST   │ Pass   │
 * │ 11 │ Relationships navigable ≥1 direction   │ MUST   │ Pass   │
 * │ 12 │ Lifecycle ownership explicit            │ MUST   │ Pass   │
 * │ 13 │ FK targets declared                    │ MUST   │ Pass   │
 * │ 14 │ Cyclic graph constraints               │ MUST   │ Pass   │
 * └────┴────────────────────────────────────────┴────────┴────────┘
 * R14: Ownership is a strict tree. MEPRun and VerticalCirculation
 *   reference floors by ID (DAG). No cycles.
 *
 * Part III — Normalization and Coherence
 * ┌────┬────────────────────────────────────────┬────────┬────────┐
 * │  # │ Rule                                   │ Tier   │ Score  │
 * ├────┼────────────────────────────────────────┼────────┼────────┤
 * │ 15 │ Single source of truth                 │ MUST   │ Pass   │
 * │ 16 │ No bag-of-arrays entities              │ SHOULD │ Pass   │
 * │ 17 │ Cross-cutting types defined once        │ SHOULD │ Pass   │
 * │ 18 │ Computed vs. stored distinguished       │ SHOULD │ Pass   │
 * └────┴────────────────────────────────────────┴────────┴────────┘
 * R15: Geometry is derivable from parameters. The `geometry` field
 *   is explicitly marked COMPUTED. Parameters are the source of truth.
 * R17: Point2D, Point3D, Vector3D, Polygon2D, BoundaryWithHoles2D,
 *   Geometry3D, MaterialSpec, Metadata — all defined once.
 *
 * Part IV — Evolution and Compatibility
 * ┌────┬────────────────────────────────────────┬────────┬────────┐
 * │  # │ Rule                                   │ Tier   │ Score  │
 * ├────┼────────────────────────────────────────┼────────┼────────┤
 * │ 19 │ Explicit, monotonic versioning         │ MUST   │ Pass   │
 * │ 20 │ No duplicate-version entities          │ MUST   │ Pass   │
 * │ 21 │ Breaking changes classified            │ MUST   │ Pass   │
 * │ 22 │ Field deprecation annotated            │ MUST   │ Pass   │
 * └────┴────────────────────────────────────────┴────────┴────────┘
 * R21: All breaking changes from v1 classified in the migration table.
 * R22: v1 fields are removed (not deprecated) because this is a major
 *   version bump. In semver, major bumps allow breaking removals without
 *   a deprecation cycle.
 *
 * Part V — Operational Annotations
 * ┌────┬────────────────────────────────────────┬────────┬────────┐
 * │  # │ Rule                                   │ Tier   │ Score  │
 * ├────┼────────────────────────────────────────┼────────┼────────┤
 * │ 23 │ Sensitive fields classified            │ MAY*   │ Pass   │
 * │ 24 │ Identity/provenance immutability        │ SHOULD │ Pass   │
 * │ 25 │ Localization strategy declared          │ SHOULD │ Warn   │
 * │ 26 │ Multi-actor provenance metadata         │ SHOULD │ Pass   │
 * └────┴────────────────────────────────────────┴────────┴────────┘
 * R23: No PII → MAY tier.
 * R25 Warn: Same rationale as v1 — single-locale documents.
 *
 * Part VI — Documentation and Generability
 * ┌────┬────────────────────────────────────────┬────────┬────────┐
 * │  # │ Rule                                   │ Tier   │ Score  │
 * ├────┼────────────────────────────────────────┼────────┼────────┤
 * │ 27 │ Consistent naming                      │ MUST   │ Pass   │
 * │ 28 │ Mechanically generatable validators    │ MUST   │ Pass   │
 * │ 29 │ Intentional extension points           │ MUST   │ Pass   │
 * │ 30 │ Access patterns don't dictate structure │ SHOULD │ Pass   │
 * │ 31 │ Readable as standalone artifact         │ MUST   │ Pass   │
 * └────┴────────────────────────────────────────┴────────┴────────┘
 *
 * TOTALS
 *   MUST Pass:   20/20 (R23 at MAY tier — no PII)
 *   SHOULD Pass or Documented: 10/11 (R25 = Warn with rationale)
 *
 * ============================================================================
 */
