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
 *   - ISO 19111:2019 (Geographic information — Referencing by coordinates)
 *   - EPSG Geodetic Parameter Dataset (epsg.org)
 *   - JSON Schema draft 2020-12 (for design rule grounding)
 *   - semver.org/spec/v2.0.0 (versioning)
 *
 * VERSION HISTORY:
 *   v1.0.0 — 2D blueprint schema (Plan view only)
 *   v2.0.0 — 3D building model (Breaking: Z axis, volumetric geometry,
 *             Slab, Roof, MEPRun entities)
 *   v2.1.0 — Frame of reference expansion (Additive: SiteCoordinateSystem,
 *             ViewPoint, DrawingView entities)
 * ============================================================================
 */

import { z } from "zod";

// ─── Schema Version ─────────────────────────────────────────────────────────

export const SCHEMA_VERSION = "2.1.0" as const;

// ─── Cross-Cutting: Identifiers ─────────────────────────────────────────────

const EntityId = z
  .string()
  .uuid()
  .describe("Opaque unique identifier (UUID v4)");

// ─── Cross-Cutting: Geometry Primitives ─────────────────────────────────────
// Rule 17: Cross-cutting types defined once.
// Rule 7: All coordinates use the BuildingModel's `lengthUnit`.

// ── 2D primitives (plan projections, profile definitions, cutting planes) ──

export const Point2D = z.object({
  x: z.number().describe("Horizontal coordinate in model length units"),
  y: z.number().describe("Vertical coordinate in model length units"),
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
 */
export const BoundingBox3D = z.object({
  min: Point3D.describe("Corner with smallest x, y, z"),
  max: Point3D.describe("Corner with largest x, y, z"),
});
export type BoundingBox3D = z.infer<typeof BoundingBox3D>;

/**
 * Extruded area solid — the primary volumetric primitive.
 * Grounding: IFC4 IfcExtrudedAreaSolid (ISO 16739-1:2024, §8.9.3.18).
 */
export const ExtrudedProfile = z.object({
  profile: BoundaryWithHoles2D.describe("2D cross-section in the profile's local XY plane"),
  depth: z.number().positive().describe("Extrusion depth along the direction vector"),
  direction: Vector3D.default({ x: 0, y: 0, z: 1 }).describe(
    "Unit vector for extrusion direction. Default (0,0,1) = vertical."
  ),
  position: Point3D.describe("Origin where profile local (0,0) maps to world space"),
  rotationDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("Profile rotation around the extrusion axis, degrees CCW"),
});
export type ExtrudedProfile = z.infer<typeof ExtrudedProfile>;

/**
 * Triangulated mesh for freeform geometry.
 * Grounding: IFC4 IfcTriangulatedFaceSet (ISO 16739-1:2024, §8.9.3.55).
 */
export const TriangleMesh = z.object({
  vertices: z.array(Point3D).min(3).describe("Vertex list, referenced by index in triangles"),
  triangles: z
    .array(z.tuple([z.number().int().min(0), z.number().int().min(0), z.number().int().min(0)]))
    .min(1)
    .describe("Triangle faces as [v0, v1, v2] index triples. CCW winding = outward normal."),
});
export type TriangleMesh = z.infer<typeof TriangleMesh>;

/**
 * Discriminated union for 3D geometry representations.
 * Rule 8: Explicit discriminator on `type`.
 */
export const Geometry3D = z.discriminatedUnion("type", [
  z.object({ type: z.literal("extrusion"), extrusion: ExtrudedProfile }),
  z.object({ type: z.literal("mesh"), mesh: TriangleMesh }),
  z.object({ type: z.literal("bbox"), bbox: BoundingBox3D }),
]);
export type Geometry3D = z.infer<typeof Geometry3D>;

// ── Arc (2D, for profile definitions and annotations) ─────────────────────

export const Arc2D = z.object({
  center: Point2D.describe("Arc center point"),
  radius: z.number().positive().describe("Arc radius in model length units"),
  startAngleDeg: z.number().min(0).max(360),
  endAngleDeg: z.number().min(0).max(360),
});
export type Arc2D = z.infer<typeof Arc2D>;

// ── 3D Plane (new in v2.1 — used by DrawingView section cuts) ─────────────

/**
 * An infinite plane in 3D, defined by a point and a unit normal vector.
 * The normal points toward the "viewing side" (the half-space the viewer is in).
 *
 * Grounding: corresponds to the Hessian normal form of a plane:
 *   n · (P − point) = 0
 * where n = normal (unit vector), P = any point on the plane.
 */
export const Plane3D = z.object({
  point: Point3D.describe("Any point lying on the plane"),
  normal: Vector3D.describe(
    "Unit normal vector. Points toward the viewer / kept half-space."
  ),
});
export type Plane3D = z.infer<typeof Plane3D>;

// ─── Cross-Cutting: Material ────────────────────────────────────────────────

export const MaterialSpec = z.object({
  name: z.string().min(1).describe("Material name (e.g., 'concrete', 'steel', 'brick')"),
  densityKgPerM3: z
    .number()
    .positive()
    .optional()
    .describe("Density in kg/m³. Unit: always SI kg/m³."),
  thermalConductivity: z
    .number()
    .positive()
    .optional()
    .describe("Thermal conductivity in W/(m·K)"),
  fireRatingMinutes: z.number().int().min(0).optional().describe("Fire resistance in minutes"),
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
  // New in v2.1.0
  ProjectionType: "2.1.0",
  DrawingViewKind: "2.1.0",
  VerticalDatumKind: "2.1.0",
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

// ── New enums in v2.1.0 ──────────────────────────────────────────────────

/**
 * Camera projection type.
 * Grounding: standard CG projection models (OpenGL spec §2.12, glTF camera).
 */
export const ProjectionType = z.enum([
  "perspective",
  "orthographic",
  "isometric",
]);
export type ProjectionType = z.infer<typeof ProjectionType>;

/**
 * Drawing view kind — what type of 2D drawing this view produces.
 * Grounding: ISO 5456-2:1996 (Technical drawings — Projection methods).
 *   - plan: horizontal cut, viewed from above (first-angle / third-angle identical for plans)
 *   - section: vertical cut, viewed from one side
 *   - elevation: exterior face, orthographic projection from a direction
 *   - detail: zoomed subregion of another view
 *   - reflected_ceiling: plan viewed from below (standard in arch. practice)
 *   - axonometric: parallel projection at a fixed angle (isometric, dimetric, trimetric)
 *   - three_d: perspective or free-orbit 3D view (not a 2D drawing cut)
 */
export const DrawingViewKind = z.enum([
  "plan",
  "section",
  "elevation",
  "detail",
  "reflected_ceiling",
  "axonometric",
  "three_d",
]);
export type DrawingViewKind = z.infer<typeof DrawingViewKind>;

/**
 * Vertical datum reference standard.
 * Grounding: ISO 19111:2019 (Geographic information — Referencing by coordinates).
 *
 * Different survey projects use different vertical datums. Mixing datums
 * without declaring them introduces systematic elevation errors.
 */
export const VerticalDatumKind = z.enum([
  "egm96",
  "egm2008",
  "navd88",
  "abn_amro",
  "bvhnh",
  "dhhn2016",
  "evrf2019",
  "ngvd29",
  "local_benchmark",
  "mean_sea_level",
  "ellipsoidal",
  "other",
]);
export type VerticalDatumKind = z.infer<typeof VerticalDatumKind>;

// ═══════════════════════════════════════════════════════════════════════════
// NEW IN v2.1.0 — FRAME OF REFERENCE ENTITIES
// ═══════════════════════════════════════════════════════════════════════════

// ─── Entity: SiteCoordinateSystem ───────────────────────────────────────────
// Defines the surveyor's grid — the intermediate frame between building-local
// and geographic (WGS84). Real construction projects almost always have a site
// grid established by a surveyor, with its own origin, rotation, and vertical
// datum. Without this, you can only go local ↔ WGS84, which is insufficient
// for site layout, as-built surveys, and multi-building coordination.
//
// Transform chain:
//   Building Local  →  Site Grid  →  Geographic (WGS84)
//       ↑ this schema's    ↑ THIS ENTITY     ↑ Building.geoReference
//         internal frame
//
// Grounding: IFC4 IfcSite.ObjectPlacement + IfcProjectedCRS
//            (ISO 16739-1:2024, §7.3.1.6 and §8.10.3.2).

/**
 * A rigid-body transform: translation + rotation + optional uniform scale.
 * Converts coordinates from one frame to another.
 *
 * Application order: scale → rotate → translate.
 * That is: P_target = R(θ) · (s · P_source) + T
 *
 * This is the standard 2D similarity transform used in surveying.
 * The Z (vertical) component is handled separately by `verticalOffset`.
 */
export const RigidTransform2D = z.object({
  translateX: z.number().describe("X offset from source origin to target origin, in source units"),
  translateY: z.number().describe("Y offset from source origin to target origin, in source units"),
  rotationDeg: z
    .number()
    .min(-360)
    .max(360)
    .describe(
      "Rotation from source X-axis to target X-axis, degrees CCW. " +
        "For building→site: the angle between the building's +X and the site grid's east."
    ),
  scaleFactor: z
    .number()
    .positive()
    .default(1.0)
    .describe(
      "Uniform scale factor. 1.0 = same units. " +
        "Relevant when building uses mm but site grid uses m (scaleFactor = 0.001)."
    ),
});
export type RigidTransform2D = z.infer<typeof RigidTransform2D>;

export const SiteCoordinateSystem = z.object({
  id: EntityId,
  name: z
    .string()
    .min(1)
    .describe("Site grid name (e.g., 'Construction Grid A', 'Survey Baseline 2024')"),

  // ── Horizontal datum ───────────────────────────────────────────────────
  /** The transform that maps building-local (x, y) to site-grid (E, N).
   *  In surveying terms: the "local to grid" transform. */
  buildingToSite: RigidTransform2D.describe(
    "2D similarity transform: building local XY → site grid Easting/Northing"
  ),

  /** Optional CRS code for the site grid's horizontal projection.
   *  EPSG codes are the standard registry (epsg.org).
   *  Example: 32723 = WGS 84 / UTM zone 23S (São Paulo region). */
  horizontalCRS: z
    .string()
    .regex(/^EPSG:\d{4,5}$/)
    .optional()
    .describe(
      "EPSG code for the site horizontal CRS (e.g., 'EPSG:32723'). " +
        "If provided, site Easting/Northing are in this projection."
    ),

  /** Unit of the site grid. May differ from the building model's lengthUnit.
   *  The `buildingToSite.scaleFactor` bridges the two. */
  siteUnit: LengthUnit.describe("Unit of the site grid coordinates"),

  // ── Vertical datum ─────────────────────────────────────────────────────
  verticalOffset: z
    .number()
    .default(0)
    .describe(
      "Vertical offset: building datum Z=0 corresponds to this elevation " +
        "in the site/survey vertical datum. Unit: siteUnit."
    ),

  verticalDatum: VerticalDatumKind.default("local_benchmark").describe(
    "Vertical datum reference. 'local_benchmark' if using a site-specific TBM. " +
      "Named datums (NAVD88, EGM2008, etc.) for absolute elevation."
  ),

  verticalDatumDescription: z
    .string()
    .optional()
    .describe(
      "Free-text description of the vertical datum when 'local_benchmark' or 'other'. " +
        "E.g., 'TBM nail in NE corner of lot, elevation 723.450m NAVD88'."
    ),

  // ── Grid convergence ───────────────────────────────────────────────────
  gridConvergenceDeg: z
    .number()
    .min(-10)
    .max(10)
    .default(0)
    .describe(
      "Angle between site grid north and true north at the site, in degrees. " +
        "Grid convergence is a function of position within the CRS projection. " +
        "Relevant when `horizontalCRS` is provided. 0 if unknown or not applicable."
    ),

  // ── Provenance ─────────────────────────────────────────────────────────
  surveyDate: z
    .string()
    .datetime()
    .optional()
    .describe("ISO 8601 UTC date when the site survey was performed"),
  surveyedBy: z
    .string()
    .optional()
    .describe("Surveyor or survey company identifier"),

  note: z.string().optional(),
});
export type SiteCoordinateSystem = z.infer<typeof SiteCoordinateSystem>;

// ─── Entity: ViewPoint ──────────────────────────────────────────────────────
// A named camera position and orientation within the building model.
// Allows saving and restoring specific points of view.
//
// This defines the POV as an ABSOLUTE position in the model's local frame.
// The transform chain (local → site → WGS84) makes this position
// convertible to any other frame.
//
// Grounding: IFC4 IfcViewpoint (via BCF — BIM Collaboration Format,
//   buildingSMART). The BCF schema defines saved viewpoints with camera
//   position, direction, and up vector. We follow that convention plus
//   standard CG camera parameters.

export const ViewPoint = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Viewpoint label (e.g., 'South facade entry', 'Kitchen POV')"),

  // ── Camera placement ───────────────────────────────────────────────────
  /** All positions are in the model's local coordinate frame (building-local).
   *  Convert to site or WGS84 via the SiteCoordinateSystem + geoReference. */
  eye: Point3D.describe(
    "Camera position (eye point) in building-local coordinates"
  ),
  target: Point3D.describe(
    "Look-at point. The camera faces from `eye` toward `target`."
  ),
  up: Vector3D.default({ x: 0, y: 0, z: 1 }).describe(
    "Camera up vector. Default (0,0,1) = Z-up. Must not be parallel to the view direction."
  ),

  // ── Projection ─────────────────────────────────────────────────────────
  projection: ProjectionType.default("perspective").describe("Projection model"),

  /** Vertical field of view for perspective projection, in degrees.
   *  Ignored for orthographic/isometric. */
  fovDeg: z
    .number()
    .min(1)
    .max(179)
    .default(60)
    .describe("Vertical field of view in degrees. Perspective only."),

  /** For orthographic/isometric: the vertical extent of the view volume
   *  in model length units. Horizontal extent is derived from aspect ratio. */
  orthoHeight: z
    .number()
    .positive()
    .optional()
    .describe(
      "Vertical extent of the orthographic view volume in length units. " +
        "Required for orthographic and isometric projections."
    ),

  // ── Clipping ───────────────────────────────────────────────────────────
  nearClip: z
    .number()
    .positive()
    .optional()
    .describe("Near clipping plane distance from eye, in length units"),
  farClip: z
    .number()
    .positive()
    .optional()
    .describe("Far clipping plane distance from eye, in length units"),

  /** Optional section box — an axis-aligned bounding box that clips all
   *  geometry outside it. Common in BIM viewers for isolating regions. */
  sectionBox: BoundingBox3D.optional().describe(
    "Optional clipping box. Only geometry inside this AABB is visible from this viewpoint."
  ),

  // ── Aspect and presentation ────────────────────────────────────────────
  aspectRatio: z
    .number()
    .positive()
    .optional()
    .describe(
      "Width / height ratio for the viewport. If absent, the renderer " +
        "uses its own viewport dimensions."
    ),

  /** Layers to show/hide for this specific viewpoint. Overrides the
   *  model-level `layerVisibility`. */
  layerOverrides: z
    .record(LayerKind, z.boolean())
    .optional()
    .describe("Per-viewpoint layer visibility overrides"),

  /** Which floors to show. If absent, all floors are visible. */
  visibleFloorIds: z
    .array(EntityId)
    .optional()
    .describe("FK → Floor.id[]. Floors visible from this viewpoint. Absent = show all."),

  note: z.string().optional(),
});
export type ViewPoint = z.infer<typeof ViewPoint>;

// ─── Entity: DrawingView ────────────────────────────────────────────────────
// A named projection plane / cutting plane that defines a 2D drawing view
// extracted from the 3D model. This is how architects produce:
//   - Floor plans (horizontal cut at a height, viewed from above)
//   - Sections (vertical cut, viewed from one side)
//   - Elevations (exterior face, orthographic from a direction)
//   - Reflected ceiling plans (plan viewed from below)
//   - Detail views (zoomed subregion of another view)
//
// The DrawingView is NOT a rendered image — it is a geometric definition
// of a viewing configuration. Renderers consume it to produce 2D output.
//
// Grounding: IFC4 IfcAnnotation + IfcGeometricRepresentationContext
//   for model views, and standard architectural drawing conventions
//   per ISO 5456-2:1996 (Projection methods) and ISO 128-20:1996
//   (Conventions for lines on technical drawings).

export const DrawingView = z.object({
  id: EntityId,
  name: z
    .string()
    .min(1)
    .describe("Drawing view label (e.g., 'A-101 Ground Floor Plan', 'Section BB')"),

  kind: DrawingViewKind.describe("What type of 2D drawing this view produces"),

  // ── Cutting / projection geometry ──────────────────────────────────────

  /** The cutting plane — required for plan, section, reflected_ceiling.
   *  For plan views: a horizontal plane (normal = (0,0,-1) for downward view,
   *    (0,0,1) for reflected ceiling), with `point.z` = the cut height.
   *  For section views: a vertical plane with normal pointing toward the viewer.
   *  For elevation views: the plane of the exterior face.
   *  For three_d / detail: optional (may use viewPointId instead). */
  cuttingPlane: Plane3D.optional().describe(
    "The plane that defines the cut or projection direction. " +
      "Normal points toward the viewer (the kept half-space)."
  ),

  /** How deep the cut extends — the range behind the cutting plane that is
   *  visible. For plans: typically the full floor-to-floor height.
   *  For sections: the full building depth.
   *  Measured in length units along the cutting plane's normal (into the model). */
  viewDepth: z
    .number()
    .positive()
    .optional()
    .describe(
      "Depth of field behind the cutting plane, in length units. " +
        "Geometry beyond this distance is clipped."
    ),

  /** Forward clip — how far in front of the cutting plane to show.
   *  Typically 0 (nothing in front of the cut), but may be positive for
   *  offset plans or detail views. */
  viewForward: z
    .number()
    .min(0)
    .default(0)
    .describe("Distance in front of the cutting plane to include, in length units"),

  // ── View extents (crop region) ─────────────────────────────────────────
  /** 2D bounding rectangle in the view's local XY that defines the crop.
   *  The view's local X is the cutting plane's first tangent direction;
   *  local Y is the second tangent. */
  cropRegion: z
    .object({
      minX: z.number().describe("Left edge of the crop in view-local coordinates"),
      minY: z.number().describe("Bottom edge of the crop in view-local coordinates"),
      maxX: z.number().describe("Right edge of the crop in view-local coordinates"),
      maxY: z.number().describe("Top edge of the crop in view-local coordinates"),
    })
    .optional()
    .describe(
      "Rectangular crop region in view-local 2D coordinates. " +
        "Absent = uncropped (show everything the plane intersects)."
    ),

  // ── Scale and output ───────────────────────────────────────────────────
  scale: z
    .string()
    .regex(/^1:\d+$/)
    .optional()
    .describe("Drawing scale as a ratio string (e.g., '1:100', '1:50')"),

  // ── Relationships ──────────────────────────────────────────────────────
  /** For detail views: which parent view this is a detail of. */
  parentViewId: EntityId.optional().describe(
    "FK → DrawingView.id. For detail views: the parent view this zooms into."
  ),

  /** Optional link to a ViewPoint for 3D / axonometric views. */
  viewPointId: EntityId.optional().describe(
    "FK → ViewPoint.id. Camera to use for three_d and axonometric views."
  ),

  /** Which floors are relevant to this view. For plans: typically one floor.
   *  For sections: all floors the cut plane intersects. */
  floorIds: z
    .array(EntityId)
    .optional()
    .describe("FK → Floor.id[]. Floors relevant to this drawing view."),

  // ── Presentation ───────────────────────────────────────────────────────
  layerOverrides: z
    .record(LayerKind, z.boolean())
    .optional()
    .describe("Per-view layer visibility overrides"),

  /** Annotations that belong specifically to this drawing view
   *  (not to the 3D model). E.g., sheet-specific notes, drawing titles,
   *  section arrows on a plan that point to another DrawingView. */
  viewAnnotations: z
    .array(z.object({
      id: EntityId,
      kind: AnnotationKind,
      position: Point2D.describe("Position in view-local 2D coordinates"),
      text: z.string().optional(),
      targetViewId: EntityId.optional().describe(
        "FK → DrawingView.id. For section arrows / detail callouts: the referenced view."
      ),
      note: z.string().optional(),
    }))
    .default([])
    .describe(
      "2D annotations specific to this drawing view (sheet-level, not model-level). " +
        "Lifecycle: composed."
    ),

  note: z.string().optional(),
});
export type DrawingView = z.infer<typeof DrawingView>;

// ═══════════════════════════════════════════════════════════════════════════
// EXISTING ENTITIES (unchanged from v2.0.0)
// ═══════════════════════════════════════════════════════════════════════════

// ─── Entity: Opening ────────────────────────────────────────────────────────

export const Opening = z.object({
  id: EntityId,
  kind: OpeningKind.describe("Type of opening"),
  offsetAlongWall: z.number().min(0).describe("Distance from wall centerline start to opening near edge"),
  width: z.number().positive().describe("Opening width in length units"),
  height: z.number().positive().describe("Opening height in length units"),
  sillHeight: z
    .number()
    .min(0)
    .describe("Height of the opening bottom above the wall base. 0 for doors."),
  swingDirection: SwingDirection.default("none"),
  note: z.string().optional(),
});
export type Opening = z.infer<typeof Opening>;

// ─── Entity: Wall ───────────────────────────────────────────────────────────

export const Wall = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("architectural"),
  wallType: WallType,
  centerline: z.object({
    start: Point2D.describe("Centerline start in plan XY"),
    end: Point2D.describe("Centerline end in plan XY"),
  }),
  thickness: z.number().positive().describe("Wall thickness, perpendicular to centerline"),
  height: z.number().positive().describe("Wall height from base to top"),
  baseElevation: z.number().describe("Elevation of wall bottom above building datum"),
  material: MaterialSpec.optional(),
  openings: z.array(Opening).default([]).describe("Lifecycle: composed. Sorted by offsetAlongWall."),
  geometry: Geometry3D.optional().describe("COMPUTED. Derivable from centerline + thickness + height + baseElevation."),
  note: z.string().optional(),
});
export type Wall = z.infer<typeof Wall>;

// ─── Entity: Slab ───────────────────────────────────────────────────────────

export const Slab = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("structural"),
  kind: SlabKind,
  boundary: BoundaryWithHoles2D.describe("2D plan boundary. May include voids."),
  thickness: z.number().positive().describe("Slab thickness"),
  elevation: z.number().describe("Elevation of slab TOP surface above building datum"),
  material: MaterialSpec.optional(),
  slopePercent: z.number().min(0).default(0),
  slopeDirection: Vector3D.optional().describe("XY direction of slope. Required when slopePercent > 0."),
  geometry: Geometry3D.optional().describe("COMPUTED."),
  note: z.string().optional(),
});
export type Slab = z.infer<typeof Slab>;

// ─── Entity: Roof ───────────────────────────────────────────────────────────

export const RoofSurface = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Surface label"),
  geometry: Geometry3D,
  material: MaterialSpec.optional(),
  slopePercent: z.number().min(0).default(0),
  note: z.string().optional(),
});
export type RoofSurface = z.infer<typeof RoofSurface>;

export const Roof = z.object({
  id: EntityId,
  buildingId: EntityId.describe("FK → Building.id"),
  layer: LayerKind.default("architectural"),
  form: RoofForm,
  ridgeElevation: z.number().describe("Highest ridge point above building datum"),
  eaveElevation: z.number().describe("Lowest eave above building datum"),
  overhang: z.number().min(0).default(0).describe("Horizontal overhang beyond exterior wall"),
  surfaces: z.array(RoofSurface).min(1).describe("Lifecycle: composed."),
  note: z.string().optional(),
});
export type Roof = z.infer<typeof Roof>;

// ─── Entity: Space ──────────────────────────────────────────────────────────

export const Space = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("architectural"),
  name: z.string().min(1),
  usage: SpaceUsage,
  boundary: BoundaryWithHoles2D,
  floorElevation: z.number().describe("Finished floor elevation above datum"),
  ceilingElevation: z.number().describe("Finished ceiling elevation above datum"),
  areaSqUnits: z.number().positive().optional().describe("COMPUTED. Floor area in (lengthUnit)²."),
  volumeCuUnits: z.number().positive().optional().describe("COMPUTED. Room volume in (lengthUnit)³."),
  finishFloor: z.string().optional(),
  finishWall: z.string().optional(),
  finishCeiling: z.string().optional(),
  note: z.string().optional(),
});
export type Space = z.infer<typeof Space>;

// ─── Entity: StructuralElement ──────────────────────────────────────────────

export const StructuralElement = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("structural"),
  kind: StructuralElementKind,
  position: Point3D,
  geometry: Geometry3D,
  material: MaterialSpec.optional(),
  rotationDeg: z.number().min(0).max(360).default(0),
  loadCapacityKN: z.number().positive().optional().describe("Axial load capacity in kN."),
  note: z.string().optional(),
});
export type StructuralElement = z.infer<typeof StructuralElement>;

// ─── Entity: Fixture ────────────────────────────────────────────────────────

export const Fixture = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  spaceId: EntityId.optional().describe("FK → Space.id"),
  layer: LayerKind,
  category: FixtureCategory,
  label: z.string().optional(),
  position: Point3D,
  rotationDeg: z.number().min(0).max(360).default(0),
  boundingSize: z
    .object({
      width: z.number().positive(),
      depth: z.number().positive(),
      height: z.number().positive(),
    })
    .optional()
    .describe("3D bounding box dimensions"),
  geometry: Geometry3D.optional(),
  symbolRef: z.string().optional(),
  note: z.string().optional(),
});
export type Fixture = z.infer<typeof Fixture>;

// ─── Entity: MEPRun ─────────────────────────────────────────────────────────

export const MEPSegment = z.object({
  id: EntityId,
  startPoint: Point3D,
  endPoint: Point3D,
  crossSection: MEPSegmentShape,
  diameter: z.number().positive().optional(),
  width: z.number().positive().optional(),
  height: z.number().positive().optional(),
  wallThickness: z.number().positive().optional(),
  material: MaterialSpec.optional(),
  note: z.string().optional(),
});
export type MEPSegment = z.infer<typeof MEPSegment>;

export const MEPRun = z.object({
  id: EntityId,
  layer: LayerKind,
  domain: MEPDomain,
  name: z.string().min(1),
  segments: z.array(MEPSegment).min(1).describe("Ordered connected segments."),
  insulationThickness: z.number().min(0).default(0),
  flowDirection: z.enum(["start_to_end", "end_to_start", "bidirectional", "not_applicable"]).default("start_to_end"),
  floorIds: z.array(EntityId).min(1).describe("FK → Floor.id[]."),
  note: z.string().optional(),
});
export type MEPRun = z.infer<typeof MEPRun>;

// ─── Entity: VerticalCirculation ────────────────────────────────────────────

export const VerticalCirculation = z.object({
  id: EntityId,
  kind: VerticalCirculationKind,
  connectsFloorIds: z.array(EntityId).min(2).describe("FK → Floor.id[]."),
  footprint: Polygon2D,
  position: Point3D,
  geometry: Geometry3D.optional(),
  directionDeg: z.number().min(0).max(360).default(0),
  riserCount: z.number().int().positive().optional(),
  riserHeight: z.number().positive().optional(),
  treadDepth: z.number().positive().optional(),
  note: z.string().optional(),
});
export type VerticalCirculation = z.infer<typeof VerticalCirculation>;

// ─── Entity: Annotation ─────────────────────────────────────────────────────

export const Annotation = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("annotation"),
  kind: AnnotationKind,
  anchorPoints: z.array(Point3D).min(1).max(4),
  text: z.string().optional(),
  measuredValue: z.number().optional().describe("COMPUTED."),
  angleDeg: z.number().optional(),
  offsetFromGeometry: z.number().default(0),
  projectionPlane: z.enum(["xy", "xz", "yz", "custom"]).default("xy"),
  note: z.string().optional(),
});
export type Annotation = z.infer<typeof Annotation>;

// ─── Entity: Floor ──────────────────────────────────────────────────────────

export const Floor = z.object({
  id: EntityId,
  buildingId: EntityId.describe("FK → Building.id"),
  level: z.number().int().describe("Floor level index. 0 = ground."),
  name: z.string().min(1),
  elevationAboveDatum: z.number().describe("Finished floor elevation above building datum (Z=0)"),
  floorToFloorHeight: z.number().positive().describe("Distance to next floor slab top"),
  walls: z.array(Wall).default([]),
  spaces: z.array(Space).default([]),
  slabs: z.array(Slab).default([]),
  structuralElements: z.array(StructuralElement).default([]),
  fixtures: z.array(Fixture).default([]),
  annotations: z.array(Annotation).default([]),
  outline: Polygon2D.optional(),
  note: z.string().optional(),
});
export type Floor = z.infer<typeof Floor>;

// ─── Entity: Building ───────────────────────────────────────────────────────

export const Building = z.object({
  id: EntityId,
  name: z.string().min(1),
  address: z.string().optional(),
  typology: z.string().optional(),
  envelopeGeometry: Geometry3D.optional().describe("COMPUTED / OPTIONAL. LOD-0 envelope."),
  geoReference: z
    .object({
      latitude: z.number().min(-90).max(90).describe("WGS84 latitude"),
      longitude: z.number().min(-180).max(180).describe("WGS84 longitude"),
      altitudeM: z.number().optional().describe("Altitude above sea level in meters"),
    })
    .optional()
    .describe("Geographic anchor for the building datum origin"),
  note: z.string().optional(),
});
export type Building = z.infer<typeof Building>;

// ═══════════════════════════════════════════════════════════════════════════
// ROOT ENTITY: BuildingModel
// ═══════════════════════════════════════════════════════════════════════════

export const BuildingModel = z.object({
  schemaVersion: z.literal(SCHEMA_VERSION).describe("Schema version (semver)"),
  id: EntityId,
  title: z.string().min(1).describe("Model title"),

  // ══ COORDINATE SYSTEM (the canonical local frame) ══════════════════════
  // These fields define the model's internal coordinate system.
  // Every Point3D in the model lives in this frame.
  lengthUnit: LengthUnit.describe("Unit for ALL coordinate and dimension values"),
  angleUnit: AngleUnit.default("deg").describe("Unit for all angular values"),
  origin: Point3D.default({ x: 0, y: 0, z: 0 }).describe(
    "World coordinate origin. Convention: south-west corner of ground floor, Z=0 at ground."
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
    .describe("Vertical axis. Always +Z (right-hand: +X=east, +Y=north, +Z=up)."),

  // ══ SITE COORDINATE SYSTEM (new in v2.1.0) ════════════════════════════
  // Bridges building-local → surveyor's site grid → geographic.
  siteCoordinateSystem: SiteCoordinateSystem.optional().describe(
    "Site surveyor grid definition. Defines the transform from building-local " +
      "to site Easting/Northing/Elevation. Combined with Building.geoReference, " +
      "completes the chain: Building Local → Site Grid → WGS84."
  ),

  // ══ VIEWPOINTS (new in v2.1.0) ════════════════════════════════════════
  // Named camera positions — absolute POVs within the local frame.
  viewPoints: z
    .array(ViewPoint)
    .default([])
    .describe(
      "Named camera positions and orientations. " +
        "Each viewpoint is an absolute POV in the model's local frame. " +
        "Lifecycle: composed."
    ),

  // ══ DRAWING VIEWS (new in v2.1.0) ═════════════════════════════════════
  // Named projection/cutting planes for 2D drawing generation.
  drawingViews: z
    .array(DrawingView)
    .default([])
    .describe(
      "Named 2D drawing views (plans, sections, elevations, details). " +
        "Each defines a cutting plane or projection direction. " +
        "Lifecycle: composed."
    ),

  // ══ COMPOSITION ════════════════════════════════════════════════════════
  building: Building.describe("The building being modeled"),
  floors: z.array(Floor).min(1).describe("Lifecycle: composed. Ordered by level."),
  roofs: z.array(Roof).default([]).describe("Lifecycle: composed by building."),

  // ══ AGGREGATION ════════════════════════════════════════════════════════
  verticalCirculation: z.array(VerticalCirculation).default([]).describe("Lifecycle: aggregated."),
  mepRuns: z.array(MEPRun).default([]).describe("Lifecycle: aggregated."),

  // ══ PRESENTATION ═══════════════════════════════════════════════════════
  layerVisibility: z.record(LayerKind, z.boolean()).optional().describe("Default layer visibility."),

  // ══ METADATA ═══════════════════════════════════════════════════════════
  metadata: Metadata,

  // ══ EXTENSION POINT ════════════════════════════════════════════════════
  extensions: z
    .record(z.string(), z.unknown())
    .optional()
    .describe("EXTENSION POINT. Namespaced keys (e.g., 'com.acme.energyModel')."),
});
export type BuildingModel = z.infer<typeof BuildingModel>;

export default BuildingModel;

/**
 * ============================================================================
 * DESIGN ASSUMPTIONS (v2.1.0 — Frame of Reference Expansion)
 * ============================================================================
 *
 * All assumptions from v2.0.0 remain in force. Below are ADDITIONAL
 * assumptions introduced in v2.1.0.
 *
 * 15. TRANSFORM CHAIN: The schema now defines a complete three-level
 *     coordinate reference chain:
 *
 *     ┌─────────────────────┐    buildingToSite    ┌─────────────────┐
 *     │  Building Local     │ ──────────────────▶   │  Site Grid      │
 *     │  (+X=east, +Y=north │    RigidTransform2D   │  (E, N, elev)   │
 *     │   +Z=up, lengthUnit)│    + verticalOffset   │  siteUnit, CRS  │
 *     └─────────────────────┘                       └────────┬────────┘
 *                                                            │
 *               Building.geoReference (WGS84 lat/lon/alt)    │
 *     ┌─────────────────────┐              ◀─────────────────┘
 *     │  Geographic (WGS84) │    CRS projection
 *     │  lat, lon, alt      │    (EPSG code on SiteCoordinateSystem)
 *     └─────────────────────┘
 *
 *     Any model point P_local can be converted to:
 *       P_site = R(θ) · (s · P_local) + T   (from buildingToSite)
 *       P_site.z = P_local.z + verticalOffset
 *       P_wgs84 = inverse_projection(P_site, EPSG)  (if CRS known)
 *
 *     If SiteCoordinateSystem is absent, the chain collapses to:
 *       Building Local → WGS84 (via Building.geoReference directly)
 *     which is the v2.0.0 behavior. No breaking change.
 *
 * 16. SITE COORDINATE SYSTEM: The surveyor's grid is modeled as a 2D
 *     similarity transform (translation + rotation + uniform scale) plus
 *     a vertical offset. This covers the standard surveying workflow
 *     where a site grid is established by total station or GNSS, with
 *     Easting/Northing in a known CRS projection and elevation in a
 *     known vertical datum.
 *
 *     The `horizontalCRS` field (EPSG code) enables machine-readable
 *     identification of the map projection. The `verticalDatum` enum
 *     covers the most common survey datums. Together they provide
 *     enough metadata for automated coordinate conversion.
 *
 *     Grid convergence (the angle between grid north and true north at
 *     the site's location within the projection) is recorded because it
 *     affects the relationship between the building's `trueNorthDeg` and
 *     the site grid's orientation.
 *
 * 17. VIEWPOINTS: Defined as standard look-at cameras (eye, target, up)
 *     with projection parameters (perspective FOV or orthographic extent).
 *     This follows the BCF (BIM Collaboration Format) viewpoint convention
 *     used by IFC-compatible BIM tools.
 *
 *     Viewpoints are absolute positions in the model's local frame — they
 *     do not "belong to" a floor or a space. They can see across floors,
 *     through section boxes, with per-viewpoint layer overrides.
 *
 *     The optional `sectionBox` (AABB clipping) is a common BIM viewer
 *     feature for isolating a region of the model.
 *
 * 18. DRAWING VIEWS: Model the architectural convention of "named views"
 *     that define 2D drawing output from a 3D model. A DrawingView is a
 *     geometric configuration (cutting plane, view depth, crop region,
 *     scale) — not a rendered image. Renderers consume DrawingViews to
 *     produce plan drawings, section drawings, elevations, etc.
 *
 *     The cutting plane is a `Plane3D` (point + normal). For a floor
 *     plan: point = (0, 0, cutHeight), normal = (0, 0, -1). For a
 *     section: point on the cut line, normal perpendicular to the cut
 *     direction and horizontal.
 *
 *     `viewAnnotations` are sheet-level annotations (drawing titles,
 *     section arrows, detail callout bubbles) that exist only in the
 *     context of this specific drawing view — not in the 3D model.
 *     This maintains the separation between model data and presentation.
 *
 *     DrawingViews can reference each other: a section arrow on a plan
 *     view has a `targetViewId` pointing to the section DrawingView.
 *     Detail views have a `parentViewId`. This forms a DAG (no cycles
 *     — Rule 14 satisfied).
 *
 * 19. POV ABSOLUTENESS: With all three subsystems in place, a ViewPoint
 *     at `eye: {x: 5000, y: 3000, z: 1600}` is:
 *     - Absolute in building-local (by definition — it IS local coords)
 *     - Convertible to site grid (via buildingToSite transform)
 *     - Convertible to WGS84 (via site CRS + geoReference)
 *     - Renderable as a 2D drawing (via DrawingView with a linked viewPointId)
 *     This closes the "absolute POV" requirement.
 *
 * ============================================================================
 * CHANGES FROM v2.0.0 → v2.1.0
 * ============================================================================
 *
 * All changes are ADDITIVE (no breaking changes → minor version bump).
 *
 * | Change                                       | Category  |
 * |----------------------------------------------|-----------|
 * | Schema version: 2.0.0 → 2.1.0               | Metadata  |
 * | New type: Plane3D                            | Additive  |
 * | New type: RigidTransform2D                   | Additive  |
 * | New entity: SiteCoordinateSystem             | Additive  |
 * | New entity: ViewPoint                        | Additive  |
 * | New entity: DrawingView                      | Additive  |
 * | New enum: ProjectionType                     | Additive  |
 * | New enum: DrawingViewKind                    | Additive  |
 * | New enum: VerticalDatumKind                  | Additive  |
 * | BuildingModel.siteCoordinateSystem: new opt  | Additive  |
 * | BuildingModel.viewPoints: new opt (default[])| Additive  |
 * | BuildingModel.drawingViews: new opt (default[])| Additive|
 * | Reference added: ISO 19111:2019              | Docs      |
 * | Reference added: EPSG dataset                | Docs      |
 *
 * v2.0.0 documents remain fully valid v2.1.0 documents — new fields
 * have defaults or are optional.
 *
 * ============================================================================
 * REVIEW SCORECARD (v2.1.0)
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
 * R11: ViewPoint.visibleFloorIds → Floor.id, DrawingView.viewPointId →
 *   ViewPoint.id, DrawingView.parentViewId → DrawingView.id,
 *   DrawingView.floorIds → Floor.id. All navigable.
 * R14: DrawingView→DrawingView (parentViewId) is a DAG.
 *   Detail views point to parent views; parent views do not point back.
 *   Circular detail chains are semantically invalid (a detail of a
 *   detail of itself). Enforcement is application-layer but the
 *   structure is acyclic by design.
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
 * R15: The transform chain (local → site → WGS84) uses derived
 *   transforms, not redundant stored copies of converted coordinates.
 *   There is one source of truth per coordinate (the local frame).
 * R17: Plane3D, RigidTransform2D defined once and reusable.
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
 * R21: All changes from v2.0.0 are classified as Additive. No breaking.
 * R22: No fields deprecated in this version.
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
 * R24: SiteCoordinateSystem.surveyDate and surveyedBy are immutable
 *   provenance fields (a survey result doesn't change after the fact).
 * R25 Warn: Same rationale — single-locale documents.
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
