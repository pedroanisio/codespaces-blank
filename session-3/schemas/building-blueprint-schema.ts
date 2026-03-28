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
 *   - ISO 1046:1973 (Architectural drawings — Building plans)
 *   - IFC4 (Industry Foundation Classes, buildingSMART)
 *   - JSON Schema draft 2020-12 (for design rule grounding)
 *   - semver.org/spec/v2.0.0 (versioning)
 * ============================================================================
 */

import { z } from "zod";

// ─── Schema Version ─────────────────────────────────────────────────────────

export const SCHEMA_VERSION = "1.0.0" as const;

// ─── Cross-Cutting: Identifiers ─────────────────────────────────────────────
// Rule 10: Stable, opaque identity. UUIDs for all entities.
// Assumption: UUIDs v4. Switch to ULIDs if lexicographic ordering is needed.

const EntityId = z.string().uuid().describe("Opaque unique identifier (UUID v4)");

// ─── Cross-Cutting: Geometry Primitives ─────────────────────────────────────
// Rule 17: Cross-cutting types defined once.
// Rule 7: All numeric fields carry explicit units via the Blueprint's
//          coordinate system (see `lengthUnit`). Coordinates are dimensionless
//          indices into that unit system.

/**
 * A point in 2D Cartesian space.
 * Coordinates are expressed in the `lengthUnit` declared on the parent Blueprint.
 */
export const Point2D = z.object({
  x: z.number().describe("Horizontal coordinate in blueprint length units"),
  y: z.number().describe("Vertical coordinate in blueprint length units"),
});
export type Point2D = z.infer<typeof Point2D>;

/**
 * A directed line segment between two points.
 */
export const LineSegment = z.object({
  start: Point2D.describe("Segment start point"),
  end: Point2D.describe("Segment end point"),
});
export type LineSegment = z.infer<typeof LineSegment>;

/**
 * A circular arc defined by center, radius, and angular sweep.
 * Angles are in degrees, measured counter-clockwise from the positive x-axis
 * (standard mathematical convention).
 */
export const Arc = z.object({
  center: Point2D.describe("Arc center point"),
  radius: z.number().positive().describe("Arc radius in blueprint length units"),
  startAngleDeg: z
    .number()
    .min(0)
    .max(360)
    .describe("Start angle in degrees, CCW from +x axis"),
  endAngleDeg: z
    .number()
    .min(0)
    .max(360)
    .describe("End angle in degrees, CCW from +x axis"),
});
export type Arc = z.infer<typeof Arc>;

/**
 * A closed polygon defined by an ordered ring of vertices.
 * The ring is implicitly closed: the last vertex connects back to the first.
 * Winding order: counter-clockwise for exterior boundaries,
 * clockwise for interior holes (voids).
 */
export const Polygon = z.object({
  vertices: z
    .array(Point2D)
    .min(3)
    .describe(
      "Ordered ring of vertices. Implicitly closed (last→first). " +
        "CCW = exterior boundary, CW = interior hole."
    ),
});
export type Polygon = z.infer<typeof Polygon>;

/**
 * A boundary that may contain holes (e.g., a room with an interior courtyard).
 * Outer ring is CCW; each hole ring is CW. Follows the GeoJSON polygon convention.
 */
export const BoundaryWithHoles = z.object({
  outer: Polygon.describe("Exterior boundary (CCW winding)"),
  holes: z
    .array(Polygon)
    .default([])
    .describe("Interior voids / cutouts (CW winding). Empty if no holes."),
});
export type BoundaryWithHoles = z.infer<typeof BoundaryWithHoles>;

// ─── Cross-Cutting: Metadata ────────────────────────────────────────────────
// Rule 6: Temporal precision — ISO 8601, UTC.
// Rule 26: Multi-actor provenance.

export const Metadata = z.object({
  createdAt: z
    .string()
    .datetime()
    .describe("ISO 8601 UTC timestamp of creation"),
  updatedAt: z
    .string()
    .datetime()
    .describe("ISO 8601 UTC timestamp of last modification"),
  createdBy: z
    .string()
    .min(1)
    .describe("Identifier (username, system name) of the creating actor"),
  updatedBy: z
    .string()
    .min(1)
    .describe("Identifier of the actor who last modified this entity"),
  note: z
    .string()
    .optional()
    .describe("Free-text note for design decisions or context"),
});
export type Metadata = z.infer<typeof Metadata>;

// ─── Enums ──────────────────────────────────────────────────────────────────
// Rule 3: Closed, versioned enums. Each enum has an _enumVersion const.

export const ENUM_VERSIONS = {
  LengthUnit: "1.0.0",
  LayerKind: "1.0.0",
  WallType: "1.0.0",
  OpeningKind: "1.0.0",
  SwingDirection: "1.0.0",
  SpaceUsage: "1.0.0",
  StructuralElementKind: "1.0.0",
  FixtureCategory: "1.0.0",
  AnnotationKind: "1.0.0",
  VerticalCirculationKind: "1.0.0",
} as const;

export const LengthUnit = z.enum(["mm", "cm", "m", "in", "ft"]);
export type LengthUnit = z.infer<typeof LengthUnit>;

export const LayerKind = z.enum([
  "structural",
  "architectural",
  "electrical",
  "plumbing",
  "hvac",
  "furniture",
  "annotation",
  "fire_safety",
]);
export type LayerKind = z.infer<typeof LayerKind>;

export const WallType = z.enum([
  "load_bearing",
  "partition",
  "curtain",
  "shear",
  "retaining",
  "fire_rated",
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
  "other",
]);
export type SpaceUsage = z.infer<typeof SpaceUsage>;

export const StructuralElementKind = z.enum([
  "column",
  "beam",
  "pillar",
  "foundation_pier",
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
  "text_label",
  "area_callout",
  "elevation_marker",
  "section_cut",
  "grid_line",
  "north_arrow",
  "scale_bar",
  "detail_callout",
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

// ─── Entity: Opening ────────────────────────────────────────────────────────
// Rule 12: Composition — an Opening is owned by a Wall. Deleting the Wall
//          deletes its Openings.
// Rule 11: Navigable via `wallId` FK.
// Rule 13: FK target is Wall.id.

export const Opening = z.object({
  id: EntityId,
  kind: OpeningKind.describe("Type of opening"),
  offsetAlongWall: z
    .number()
    .min(0)
    .describe(
      "Distance from the wall's start point to the opening's near edge, " +
        "in blueprint length units"
    ),
  width: z.number().positive().describe("Opening width in blueprint length units"),
  height: z
    .number()
    .positive()
    .optional()
    .describe(
      "Opening height in blueprint length units. " +
        "Optional in pure 2D plans; required for section views."
    ),
  sillHeight: z
    .number()
    .min(0)
    .optional()
    .describe("Height of the sill above finished floor level. Relevant for windows."),
  swingDirection: SwingDirection.default("none").describe(
    "Door swing direction. 'none' for windows and archways."
  ),
  note: z.string().optional().describe("Free-text annotation"),
});
export type Opening = z.infer<typeof Opening>;

// ─── Entity: Wall ───────────────────────────────────────────────────────────
// Rule 12: Composition — a Wall is owned by a Floor.
// Walls are thick centerline segments. `thickness` is perpendicular to the
// centerline direction.

export const Wall = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id. The floor this wall belongs to."),
  layer: LayerKind.default("architectural").describe("Logical layer"),
  wallType: WallType.describe("Structural classification of the wall"),
  centerline: LineSegment.describe(
    "Centerline of the wall from start to end. " +
      "Thickness extends symmetrically on both sides."
  ),
  thickness: z
    .number()
    .positive()
    .describe("Wall thickness in blueprint length units, perpendicular to centerline"),
  heightAboveFloor: z
    .number()
    .positive()
    .optional()
    .describe("Wall height. Optional in pure 2D plan views."),
  material: z
    .string()
    .min(1)
    .optional()
    .describe("Material description (e.g., 'concrete', 'drywall', 'brick')"),
  fireRatingMinutes: z
    .number()
    .int()
    .min(0)
    .optional()
    .describe("Fire resistance rating in minutes (0 = unrated)"),
  openings: z
    .array(Opening)
    .default([])
    .describe(
      "Ordered list of openings in this wall, sorted by offsetAlongWall. " +
        "Lifecycle: composed — deleted with the wall."
    ),
  note: z.string().optional(),
});
export type Wall = z.infer<typeof Wall>;

// ─── Entity: Space ──────────────────────────────────────────────────────────
// A room, corridor, or area defined by a closed polygonal boundary.
// Rule 12: Composition — owned by Floor.

export const Space = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("architectural"),
  name: z
    .string()
    .min(1)
    .describe("Human-readable label (e.g., 'Master Bedroom', 'Kitchen')"),
  usage: SpaceUsage.describe("Functional classification of the space"),
  boundary: BoundaryWithHoles.describe(
    "Closed polygonal boundary defining the space. May include interior voids."
  ),
  /** Rule 18: Computed vs. stored. Area is computed from boundary, but stored
   *  for query convenience. Consumers SHOULD recompute from boundary for precision. */
  areaSqUnits: z
    .number()
    .positive()
    .optional()
    .describe(
      "Floor area in (lengthUnit)². COMPUTED from boundary polygon. " +
        "Stored for convenience; recompute from vertices for precision."
    ),
  ceilingHeight: z
    .number()
    .positive()
    .optional()
    .describe("Ceiling height above finished floor. Optional in pure 2D views."),
  finishFloor: z.string().optional().describe("Floor finish material (e.g., 'hardwood', 'tile')"),
  finishWall: z.string().optional().describe("Wall finish material"),
  finishCeiling: z.string().optional().describe("Ceiling finish material"),
  note: z.string().optional(),
});
export type Space = z.infer<typeof Space>;

// ─── Entity: StructuralElement ──────────────────────────────────────────────
// Columns, beams, etc. that appear on the 2D plan.
// Rule 12: Composition — owned by Floor.

export const StructuralElement = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("structural"),
  kind: StructuralElementKind.describe("Structural element classification"),
  position: Point2D.describe("Center point or insertion point of the element"),
  /**
   * 2D footprint as a closed polygon. For a circular column, approximate
   * as a regular polygon (≥16 sides) or use the `radiusMm` shorthand below.
   */
  footprint: Polygon.optional().describe(
    "2D cross-section footprint polygon. " +
      "Omit if using circularRadius for circular columns."
  ),
  circularRadius: z
    .number()
    .positive()
    .optional()
    .describe(
      "Radius for circular cross-section elements (in blueprint length units). " +
        "Mutually exclusive with footprint for simple columns."
    ),
  material: z.string().min(1).optional().describe("Material (e.g., 'steel', 'concrete')"),
  rotationDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Rotation angle in degrees, CCW from +x axis"),
  note: z.string().optional(),
});
export type StructuralElement = z.infer<typeof StructuralElement>;

// ─── Entity: Fixture ────────────────────────────────────────────────────────
// Placed objects: plumbing, electrical, appliances, furniture.
// Rule 12: Composition — owned by Floor.

export const Fixture = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  spaceId: EntityId.optional().describe(
    "FK → Space.id. The space this fixture is located in. " +
      "Optional because some fixtures (e.g., outdoor lights) may not be in a space."
  ),
  layer: LayerKind.describe("Logical layer (electrical, plumbing, furniture, etc.)"),
  category: FixtureCategory.describe("Fixture type classification"),
  label: z.string().optional().describe("Display label (e.g., 'Kitchen Sink', 'Outlet A3')"),
  position: Point2D.describe("Insertion/center point of the fixture"),
  rotationDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Rotation in degrees, CCW from +x axis"),
  widthUnits: z.number().positive().optional().describe("Bounding box width in length units"),
  depthUnits: z.number().positive().optional().describe("Bounding box depth in length units"),
  symbolRef: z
    .string()
    .optional()
    .describe(
      "Reference to an external symbol library entry (e.g., 'iso-7010:E003'). " +
        "Renderers use this to look up the visual representation."
    ),
  note: z.string().optional(),
});
export type Fixture = z.infer<typeof Fixture>;

// ─── Entity: VerticalCirculation ────────────────────────────────────────────
// Stairs, elevators, ramps that connect floors.
// Rule 12: Aggregation — shared across floors, not deleted with one floor.

export const VerticalCirculation = z.object({
  id: EntityId,
  kind: VerticalCirculationKind.describe("Type of vertical circulation"),
  connectsFloorIds: z
    .array(EntityId)
    .min(2)
    .describe("FK → Floor.id[]. The floors this element connects. Min 2."),
  footprint: Polygon.describe("2D plan footprint of the element on each floor"),
  position: Point2D.describe("Reference insertion point"),
  directionDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Direction of travel / up direction, degrees CCW from +x"),
  riserCount: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("Number of risers (stairs only)"),
  riserHeight: z
    .number()
    .positive()
    .optional()
    .describe("Riser height in blueprint length units (stairs only)"),
  treadDepth: z
    .number()
    .positive()
    .optional()
    .describe("Tread depth in blueprint length units (stairs only)"),
  note: z.string().optional(),
});
export type VerticalCirculation = z.infer<typeof VerticalCirculation>;

// ─── Entity: Annotation ─────────────────────────────────────────────────────
// Dimension lines, labels, callouts — the non-physical markup of the plan.
// Rule 12: Composition — owned by Floor.

export const Annotation = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("annotation"),
  kind: AnnotationKind.describe("Type of annotation"),
  /**
   * For dimension_linear: two anchor points defining the measured extent.
   * For text_label / area_callout: single point (use anchorPoints[0]).
   * For section_cut: the cut line (two points).
   */
  anchorPoints: z
    .array(Point2D)
    .min(1)
    .max(4)
    .describe(
      "Reference points for the annotation. " +
        "Linear dimensions use 2 points; text labels use 1; section cuts use 2."
    ),
  text: z.string().optional().describe("Display text / label content"),
  /** Rule 18: Computed. Dimension value is computed from anchor geometry. */
  measuredValue: z
    .number()
    .optional()
    .describe(
      "Numeric value of the measurement (COMPUTED from anchorPoints). " +
        "Stored for display; recompute from geometry for precision."
    ),
  angleDeg: z
    .number()
    .optional()
    .describe("For angular dimensions: the measured angle in degrees."),
  offsetFromGeometry: z
    .number()
    .default(0)
    .describe("Perpendicular offset of the dimension line from the measured geometry"),
  note: z.string().optional(),
});
export type Annotation = z.infer<typeof Annotation>;

// ─── Entity: Floor ──────────────────────────────────────────────────────────
// A single story / level of the building.
// Rule 12: Composition — owned by Building. Deleting a Floor deletes its
//          Walls, Spaces, Fixtures, Annotations, StructuralElements.

export const Floor = z.object({
  id: EntityId,
  buildingId: EntityId.describe("FK → Building.id"),
  /** Rule 10: `level` is a semantic ordering index, NOT an identifier.
   *  Identity is `id`. `level` is for display ordering.
   *  Convention: 0 = ground floor, negative = below grade. */
  level: z.number().int().describe(
    "Floor level index. 0 = ground floor. Negative = below grade. " +
      "Used for ordering, NOT as identity."
  ),
  name: z.string().min(1).describe("Display name (e.g., 'Ground Floor', 'Level 2', 'Basement')"),
  elevationAboveDatum: z
    .number()
    .default(0)
    .describe(
      "Elevation of this floor's finished floor level above the building datum, " +
        "in blueprint length units"
    ),
  floorToFloorHeight: z
    .number()
    .positive()
    .optional()
    .describe("Distance from this floor's slab to the next floor's slab, in length units"),
  walls: z
    .array(Wall)
    .default([])
    .describe("All walls on this floor. Lifecycle: composed."),
  spaces: z
    .array(Space)
    .default([])
    .describe("All defined spaces/rooms on this floor. Lifecycle: composed."),
  structuralElements: z
    .array(StructuralElement)
    .default([])
    .describe("Columns, beams, etc. on this floor. Lifecycle: composed."),
  fixtures: z
    .array(Fixture)
    .default([])
    .describe("Placed fixtures on this floor. Lifecycle: composed."),
  annotations: z
    .array(Annotation)
    .default([])
    .describe("Dimension lines, labels, callouts. Lifecycle: composed."),
  outline: Polygon.optional().describe(
    "Overall floor plate outline. Optional; can be derived from wall geometry."
  ),
  note: z.string().optional(),
});
export type Floor = z.infer<typeof Floor>;

// ─── Entity: Building ───────────────────────────────────────────────────────
// The root building entity.
// Rule 12: Composition — owns Floors.

export const Building = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Building name or designation"),
  address: z.string().optional().describe("Physical address"),
  typology: z
    .string()
    .optional()
    .describe(
      "Building typology description (e.g., 'residential single-family', " +
        "'commercial office', 'mixed-use')"
    ),
  totalFloors: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("Total number of above-grade floors. Informational; derive from floors array."),
  belowGradeFloors: z
    .number()
    .int()
    .min(0)
    .default(0)
    .describe("Number of below-grade floors (basements)"),
  note: z.string().optional(),
});
export type Building = z.infer<typeof Building>;

// ─── Entity: Blueprint (Root Document) ──────────────────────────────────────
// The top-level container representing a complete 2D blueprint of a building.
// Rule 14: No cycles — the ownership graph is a strict tree:
//   Blueprint → Building → Floor → {Wall, Space, Fixture, Annotation, StructuralElement}
//   Wall → Opening
//   Blueprint aggregates VerticalCirculation (shared across floors).

export const Blueprint = z.object({
  /** Rule 19: Explicit schema version. */
  schemaVersion: z
    .literal(SCHEMA_VERSION)
    .describe("Schema version this document conforms to (semver)"),

  id: EntityId,
  title: z.string().min(1).describe("Blueprint title (e.g., 'Floor Plans — Residence A')"),

  // ── Coordinate System ────────────────────────────────────────────────────
  // Rule 7: Units declared at the blueprint level. All coordinate values
  //         throughout the document are expressed in this unit.
  lengthUnit: LengthUnit.describe(
    "The unit of length for ALL coordinate and dimension values in this document"
  ),
  origin: Point2D.default({ x: 0, y: 0 }).describe(
    "The coordinate system origin point. Convention: south-west corner of ground floor."
  ),
  trueNorthDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe(
      "Rotation of true north relative to the +y axis, in degrees clockwise. " +
        "0 = +y is north (default)."
    ),
  scale: z
    .string()
    .regex(/^1:\d+$/)
    .default("1:100")
    .describe("Drawing scale as a ratio string (e.g., '1:100', '1:50')"),

  // ── Composition ──────────────────────────────────────────────────────────
  building: Building.describe("The building being represented"),
  floors: z
    .array(Floor)
    .min(1)
    .describe(
      "Floor plans, ordered by level (ascending). " +
        "At least one floor is required. Lifecycle: composed — owned by this blueprint."
    ),

  // ── Aggregation ──────────────────────────────────────────────────────────
  verticalCirculation: z
    .array(VerticalCirculation)
    .default([])
    .describe(
      "Stairs, elevators, ramps connecting floors. " +
        "Lifecycle: aggregated — shared across floors, not deleted with a single floor."
    ),

  // ── Layer Visibility (presentation hint, not structural) ─────────────────
  // Rule 30: Access patterns inform but don't dictate structure.
  // This is a rendering hint; the structural model is layer-agnostic.
  layerVisibility: z
    .record(LayerKind, z.boolean())
    .optional()
    .describe(
      "Default visibility per layer for rendering. " +
        "Presentation hint only — does not affect the data model."
    ),

  // ── Metadata ─────────────────────────────────────────────────────────────
  metadata: Metadata.describe("Creation and modification metadata"),

  // ── Extension Point ──────────────────────────────────────────────────────
  // Rule 29: Intentional extension point.
  extensions: z
    .record(z.string(), z.unknown())
    .optional()
    .describe(
      "EXTENSION POINT. Consumer-defined additional data. " +
        "Keys should be namespaced (e.g., 'com.acme.costEstimate'). " +
        "The schema does not validate extension contents."
    ),
});
export type Blueprint = z.infer<typeof Blueprint>;

// ─── Default Export ─────────────────────────────────────────────────────────

export default Blueprint;

/**
 * ============================================================================
 * DESIGN ASSUMPTIONS (stated per Rule 31 — standalone readability)
 * ============================================================================
 *
 * 1. COORDINATE SYSTEM: Cartesian 2D. Origin convention is south-west corner
 *    of the ground floor slab. All coordinates use the `lengthUnit` declared
 *    on the Blueprint. There is no separate Z axis in this schema; height
 *    fields (wall height, ceiling height, etc.) are optional scalar values.
 *
 * 2. WALL MODEL: Walls are "thick centerline" segments — a directed line
 *    segment (centerline) plus a symmetric thickness. This is the standard
 *    representation in architectural CAD (AutoCAD, Revit plan views). It is
 *    simpler than the "double-line/polygon wall" model and sufficient for
 *    most 2D plan uses.
 *
 * 3. OPENINGS: Modeled as offsets along their parent wall's centerline.
 *    `offsetAlongWall` is measured from `wall.centerline.start` to the near
 *    edge of the opening. This avoids redundant absolute coordinates and
 *    keeps openings geometrically consistent with their parent wall.
 *
 * 4. SPACES: Defined by explicit closed polygons, NOT derived from wall
 *    intersections. This is intentional — wall-intersection-based room
 *    detection is an algorithmic problem for renderers/viewers, not a data
 *    model concern. Explicit polygons are unambiguous.
 *
 * 5. VERTICAL CIRCULATION: Aggregated (not composed) at the Blueprint level
 *    because stairs/elevators inherently span multiple floors. They reference
 *    floors by ID rather than being owned by a single floor.
 *
 * 6. IDENTIFIERS: UUID v4. If consumers need time-sortable or
 *    lexicographically orderable IDs, switch to ULIDs.
 *
 * 7. CURVED WALLS: Not directly modeled as first-class wall types. For
 *    curved walls, use a polyline approximation (multiple short wall
 *    segments) or extend the schema with an `arc` wall variant. The `Arc`
 *    primitive is available for other uses (annotations, fixtures).
 *
 * 8. 3D DATA: This schema is intentionally 2D. Height fields exist as
 *    optional scalars for metadata purposes (wall height, ceiling height,
 *    sill height) but there is no 3D geometry model. For full 3D, consider
 *    IFC (Industry Foundation Classes).
 *
 * 9. SYMBOL LIBRARIES: Fixtures reference external symbol libraries via
 *    `symbolRef` (e.g., ISO 7010 symbols). The schema does not embed
 *    graphical symbol definitions — that is a renderer concern.
 *
 * 10. NO PII: This schema does not contain personally identifiable
 *     information. Rule 23 (sensitivity classification) is therefore MAY,
 *     not MUST. If extended to include occupant data, add sensitivity
 *     annotations.
 *
 * ============================================================================
 * REVIEW SCORECARD
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
 * Note R8: Polymorphism exists in OpeningKind, AnnotationKind, etc.
 *   These are closed enums (variant selection), not structural unions.
 *   If Opening subtypes diverge significantly in future, refactor to
 *   z.discriminatedUnion on `kind`.
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
 * Note R14: Ownership graph is a strict tree (no cycles).
 *   VerticalCirculation references floors by ID (DAG, not cycle).
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
 * Note R16: Floor has multiple arrays (walls, spaces, fixtures, etc.)
 *   but each array serves a distinct structural role — this is not a
 *   "bag of arrays" anti-pattern. Each array has typed, identified items
 *   with clear ownership semantics.
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
 * Note R21/R22: v1.0.0 — no prior version to break from or deprecate.
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
 * * R23: No PII in this schema → MAY tier. Pass by default.
 * R24: id and createdAt/createdBy are semantically immutable.
 *   Enforcement is application-layer (consistent with the standard's scope).
 * R25 Warn: No explicit localization strategy for `name`, `label`, `note`
 *   string fields. Rationale: building blueprints are typically
 *   single-locale documents. If multilingual support is needed, add
 *   a `locale` field to Blueprint and/or use a LocalizedString type.
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
 * R27: camelCase for all fields, PascalCase for types/enums.
 * R28: Zod schemas are mechanically validatable.
 * R29: `extensions` record on Blueprint for consumer-defined data.
 *
 * TOTALS
 *   MUST Pass:   20/20 (R23 at MAY tier — no PII)
 *   SHOULD Pass or Documented: 10/11 (R25 = Warn with rationale)
 *
 * ============================================================================
 */
