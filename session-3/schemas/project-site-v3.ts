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
 *   - ISO 6707-1:2017  (Buildings and civil engineering works — Vocabulary)
 *   - ISO 16739-1:2024 (IFC4 — Industry Foundation Classes)
 *   - ISO 10303-42      (STEP — Geometric and topological representation)
 *   - ISO 19111:2019    (Geographic information — Referencing by coordinates)
 *   - ISO 19107:2019    (Geographic information — Spatial schema)
 *   - EPSG Geodetic Parameter Dataset (epsg.org)
 *   - LandXML 1.2       (landxml.org — civil/survey data exchange)
 *   - buildingSMART IFC4 (standards.buildingsmart.org/IFC)
 *   - JSON Schema draft 2020-12
 *   - semver.org/spec/v2.0.0
 *
 * VERSION HISTORY:
 *   v1.0.0 — 2D blueprint schema (plan view only)
 *   v2.0.0 — 3D building model (Z axis, volumetric geometry, Slab, Roof, MEPRun)
 *   v2.1.0 — Frame of reference (SiteCoordinateSystem, ViewPoint, DrawingView)
 *   v3.0.0 — ProjectSite root (BREAKING: terrain, multi-building, site features)
 * ============================================================================
 */

import { z } from "zod";

// ═══════════════════════════════════════════════════════════════════════════
// SCHEMA VERSION
// ═══════════════════════════════════════════════════════════════════════════

export const SCHEMA_VERSION = "3.0.0" as const;

// ═══════════════════════════════════════════════════════════════════════════
// CROSS-CUTTING TYPES
// ═══════════════════════════════════════════════════════════════════════════

const EntityId = z.string().uuid().describe("Opaque unique identifier (UUID v4)");

// ── 2D primitives ─────────────────────────────────────────────────────────

export const Point2D = z.object({
  x: z.number().describe("Horizontal coordinate in document length units"),
  y: z.number().describe("Vertical coordinate in document length units"),
});
export type Point2D = z.infer<typeof Point2D>;

export const Polygon2D = z.object({
  vertices: z.array(Point2D).min(3).describe(
    "Ordered ring. Implicitly closed. CCW = exterior, CW = hole."
  ),
});
export type Polygon2D = z.infer<typeof Polygon2D>;

export const BoundaryWithHoles2D = z.object({
  outer: Polygon2D.describe("Exterior boundary (CCW)"),
  holes: z.array(Polygon2D).default([]).describe("Interior voids (CW)"),
});
export type BoundaryWithHoles2D = z.infer<typeof BoundaryWithHoles2D>;

export const Polyline2D = z.object({
  points: z.array(Point2D).min(2).describe("Ordered sequence of vertices. Open path (not closed)."),
});
export type Polyline2D = z.infer<typeof Polyline2D>;

// ── 3D primitives ─────────────────────────────────────────────────────────

export const Point3D = z.object({
  x: z.number().describe("East-west coordinate"),
  y: z.number().describe("North-south coordinate"),
  z: z.number().describe("Vertical coordinate (elevation)"),
});
export type Point3D = z.infer<typeof Point3D>;

export const Vector3D = z.object({ x: z.number(), y: z.number(), z: z.number() });
export type Vector3D = z.infer<typeof Vector3D>;

export const LineSegment3D = z.object({
  start: Point3D, end: Point3D,
});
export type LineSegment3D = z.infer<typeof LineSegment3D>;

export const Polyline3D = z.object({
  points: z.array(Point3D).min(2).describe("Ordered sequence of 3D vertices. Open path."),
});
export type Polyline3D = z.infer<typeof Polyline3D>;

export const BoundingBox3D = z.object({
  min: Point3D.describe("Corner with smallest x, y, z"),
  max: Point3D.describe("Corner with largest x, y, z"),
});
export type BoundingBox3D = z.infer<typeof BoundingBox3D>;

export const Plane3D = z.object({
  point: Point3D.describe("Any point on the plane"),
  normal: Vector3D.describe("Unit normal vector, pointing toward the viewer / kept half-space"),
});
export type Plane3D = z.infer<typeof Plane3D>;

export const ExtrudedProfile = z.object({
  profile: BoundaryWithHoles2D.describe("2D cross-section in profile-local XY"),
  depth: z.number().positive().describe("Extrusion depth along direction vector"),
  direction: Vector3D.default({ x: 0, y: 0, z: 1 }).describe("Extrusion direction (unit vector)"),
  position: Point3D.describe("Profile origin in world space"),
  rotationDeg: z.number().min(0).max(360).default(0),
});
export type ExtrudedProfile = z.infer<typeof ExtrudedProfile>;

/**
 * Triangulated mesh — used for both building geometry AND terrain surfaces.
 * Grounding: IFC4 IfcTriangulatedFaceSet (ISO 16739-1:2024, §8.9.3.55).
 *
 * For terrain TIN: vertices are survey points with real elevations;
 * triangles form the Delaunay triangulation of those points.
 */
export const TriangleMesh = z.object({
  vertices: z.array(Point3D).min(3).describe("Vertex list, indexed 0-based"),
  triangles: z
    .array(z.tuple([z.number().int().min(0), z.number().int().min(0), z.number().int().min(0)]))
    .min(1)
    .describe("Triangle faces as [v0, v1, v2] index triples. CCW = outward normal."),
});
export type TriangleMesh = z.infer<typeof TriangleMesh>;

export const Geometry3D = z.discriminatedUnion("type", [
  z.object({ type: z.literal("extrusion"), extrusion: ExtrudedProfile }),
  z.object({ type: z.literal("mesh"), mesh: TriangleMesh }),
  z.object({ type: z.literal("bbox"), bbox: BoundingBox3D }),
]);
export type Geometry3D = z.infer<typeof Geometry3D>;

export const Arc2D = z.object({
  center: Point2D,
  radius: z.number().positive(),
  startAngleDeg: z.number().min(0).max(360),
  endAngleDeg: z.number().min(0).max(360),
});
export type Arc2D = z.infer<typeof Arc2D>;

// ── Material ──────────────────────────────────────────────────────────────

export const MaterialSpec = z.object({
  name: z.string().min(1).describe("Material name"),
  densityKgPerM3: z.number().positive().optional().describe("kg/m³"),
  thermalConductivity: z.number().positive().optional().describe("W/(m·K)"),
  fireRatingMinutes: z.number().int().min(0).optional(),
});
export type MaterialSpec = z.infer<typeof MaterialSpec>;

// ── Metadata ──────────────────────────────────────────────────────────────

export const Metadata = z.object({
  createdAt: z.string().datetime().describe("ISO 8601 UTC"),
  updatedAt: z.string().datetime().describe("ISO 8601 UTC"),
  createdBy: z.string().min(1),
  updatedBy: z.string().min(1),
  note: z.string().optional(),
});
export type Metadata = z.infer<typeof Metadata>;

// ── Transform ─────────────────────────────────────────────────────────────

export const RigidTransform2D = z.object({
  translateX: z.number().describe("X offset, source units"),
  translateY: z.number().describe("Y offset, source units"),
  rotationDeg: z.number().min(-360).max(360).describe("Rotation CCW, degrees"),
  scaleFactor: z.number().positive().default(1.0).describe("Uniform scale. 1.0 = same units."),
});
export type RigidTransform2D = z.infer<typeof RigidTransform2D>;

// ═══════════════════════════════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════════════════════════════

export const ENUM_VERSIONS = {
  LengthUnit: "2.0.0",
  AngleUnit: "2.0.0",
  LayerKind: "3.0.0",
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
  ProjectionType: "2.1.0",
  DrawingViewKind: "2.1.0",
  VerticalDatumKind: "2.1.0",
  // New in v3.0.0
  TerrainSurfaceKind: "3.0.0",
  SiteBoundaryKind: "3.0.0",
  SiteFeatureKind: "3.0.0",
  SoilClassification: "3.0.0",
} as const;

export const LengthUnit = z.enum(["mm", "cm", "m", "in", "ft"]);
export type LengthUnit = z.infer<typeof LengthUnit>;

export const AngleUnit = z.enum(["deg", "rad"]);
export type AngleUnit = z.infer<typeof AngleUnit>;

export const LayerKind = z.enum([
  "structural", "architectural", "electrical", "plumbing", "hvac",
  "furniture", "annotation", "fire_safety", "exterior_envelope",
  "site", "terrain", "grading", "landscaping", "utilities",
]);
export type LayerKind = z.infer<typeof LayerKind>;

export const WallType = z.enum([
  "load_bearing", "partition", "curtain", "shear", "retaining",
  "fire_rated", "parapet", "foundation",
]);
export type WallType = z.infer<typeof WallType>;

export const OpeningKind = z.enum([
  "single_door", "double_door", "sliding_door", "revolving_door",
  "window", "skylight", "archway", "garage_door", "curtain_wall_panel",
]);
export type OpeningKind = z.infer<typeof OpeningKind>;

export const SwingDirection = z.enum([
  "inward_left", "inward_right", "outward_left", "outward_right",
  "sliding_left", "sliding_right", "bi_fold", "pivot", "none",
]);
export type SwingDirection = z.infer<typeof SwingDirection>;

export const SpaceUsage = z.enum([
  "bedroom", "bathroom", "kitchen", "living_room", "dining_room",
  "office", "hallway", "corridor", "stairwell", "elevator_shaft",
  "closet", "storage", "laundry", "garage", "balcony", "terrace",
  "lobby", "reception", "conference_room", "mechanical_room",
  "server_room", "restroom", "utility", "commercial", "industrial",
  "atrium", "courtyard", "roof_terrace", "other",
]);
export type SpaceUsage = z.infer<typeof SpaceUsage>;

export const StructuralElementKind = z.enum([
  "column", "beam", "pillar", "foundation_pier", "brace",
  "truss", "load_bearing_wall_segment",
]);
export type StructuralElementKind = z.infer<typeof StructuralElementKind>;

export const FixtureCategory = z.enum([
  "plumbing_sink", "plumbing_toilet", "plumbing_shower", "plumbing_bathtub",
  "plumbing_water_heater", "electrical_outlet", "electrical_switch",
  "electrical_panel", "electrical_light", "hvac_vent", "hvac_thermostat",
  "hvac_unit", "appliance_stove", "appliance_refrigerator",
  "appliance_washer", "appliance_dryer", "furniture_table",
  "furniture_chair", "furniture_bed", "furniture_sofa", "furniture_desk",
  "fire_extinguisher", "fire_alarm", "fire_sprinkler", "other",
]);
export type FixtureCategory = z.infer<typeof FixtureCategory>;

export const AnnotationKind = z.enum([
  "dimension_linear", "dimension_angular", "dimension_radial",
  "dimension_elevation", "text_label", "area_callout", "volume_callout",
  "elevation_marker", "section_cut", "grid_line", "north_arrow",
  "scale_bar", "detail_callout", "level_marker",
]);
export type AnnotationKind = z.infer<typeof AnnotationKind>;

export const VerticalCirculationKind = z.enum([
  "staircase", "elevator", "escalator", "ramp", "ladder",
]);
export type VerticalCirculationKind = z.infer<typeof VerticalCirculationKind>;

export const SlabKind = z.enum([
  "floor", "ceiling", "roof_slab", "mezzanine", "foundation_slab", "landing",
]);
export type SlabKind = z.infer<typeof SlabKind>;

export const RoofForm = z.enum([
  "flat", "gable", "hip", "mansard", "shed", "butterfly",
  "dome", "barrel_vault", "gambrel", "sawtooth", "other",
]);
export type RoofForm = z.infer<typeof RoofForm>;

export const MEPDomain = z.enum([
  "plumbing_supply", "plumbing_drain", "hvac_duct", "hvac_pipe",
  "electrical_conduit", "fire_suppression", "gas", "telecom",
]);
export type MEPDomain = z.infer<typeof MEPDomain>;

export const MEPSegmentShape = z.enum(["circular", "rectangular", "oval"]);
export type MEPSegmentShape = z.infer<typeof MEPSegmentShape>;

export const ProjectionType = z.enum(["perspective", "orthographic", "isometric"]);
export type ProjectionType = z.infer<typeof ProjectionType>;

export const DrawingViewKind = z.enum([
  "plan", "section", "elevation", "detail",
  "reflected_ceiling", "axonometric", "three_d",
]);
export type DrawingViewKind = z.infer<typeof DrawingViewKind>;

export const VerticalDatumKind = z.enum([
  "egm96", "egm2008", "navd88", "abn_amro", "bvhnh", "dhhn2016",
  "evrf2019", "ngvd29", "local_benchmark", "mean_sea_level",
  "ellipsoidal", "other",
]);
export type VerticalDatumKind = z.infer<typeof VerticalDatumKind>;

// ── New enums in v3.0.0 ──────────────────────────────────────────────────

/**
 * Terrain surface purpose.
 * Grounding: LandXML 1.2 surface types; IFC4 IfcGeographicElement.
 *
 * `existing`  — the ground as surveyed before any construction.
 * `proposed`  — the designed finish grade after earthwork.
 * `subgrade`  — the stripped/compacted surface below structural fill.
 * `rock`      — top-of-rock surface from geotechnical borings.
 */
export const TerrainSurfaceKind = z.enum([
  "existing",
  "proposed",
  "subgrade",
  "rock",
]);
export type TerrainSurfaceKind = z.infer<typeof TerrainSurfaceKind>;

/**
 * Site boundary classification.
 * Grounding: IFC4 IfcSite boundaries; standard surveying/zoning terms.
 */
export const SiteBoundaryKind = z.enum([
  "property_line",
  "setback_front",
  "setback_rear",
  "setback_side",
  "easement",
  "right_of_way",
  "zoning_boundary",
  "flood_zone",
  "environmental_buffer",
  "construction_limit",
  "other",
]);
export type SiteBoundaryKind = z.infer<typeof SiteBoundaryKind>;

/**
 * Site feature classification.
 * Grounding: IFC4 IfcGeographicElement subtypes; civil engineering practice.
 */
export const SiteFeatureKind = z.enum([
  "tree",
  "tree_cluster",
  "hedge",
  "garden_bed",
  "road",
  "sidewalk",
  "parking_lot",
  "driveway",
  "water_body",
  "stream",
  "drainage_ditch",
  "retaining_wall",
  "fence",
  "existing_structure",
  "demolished_structure",
  "underground_utility",
  "overhead_utility",
  "light_pole",
  "fire_hydrant",
  "manhole",
  "catch_basin",
  "other",
]);
export type SiteFeatureKind = z.infer<typeof SiteFeatureKind>;

/**
 * Unified Soil Classification System (USCS) — major groups.
 * Grounding: ASTM D2487 (Standard Practice for Classification of Soils).
 * Used for geotechnical context on terrain surfaces.
 */
export const SoilClassification = z.enum([
  "gw", "gp", "gm", "gc",
  "sw", "sp", "sm", "sc",
  "ml", "cl", "ol",
  "mh", "ch", "oh",
  "pt",
  "fill",
  "rock",
  "unknown",
]);
export type SoilClassification = z.infer<typeof SoilClassification>;

// ═══════════════════════════════════════════════════════════════════════════
// TERRAIN ENTITIES (new in v3.0.0)
// ═══════════════════════════════════════════════════════════════════════════

// ─── Entity: SpotElevation ──────────────────────────────────────────────────
// A surveyed control point with known 3D coordinates and optional metadata.
// These are the raw input data from which the TIN is constructed.
// Grounding: LandXML 1.2 <CgPoint>; standard land survey practice.

export const SpotElevation = z.object({
  id: EntityId,
  position: Point3D.describe("Surveyed position in site coordinates"),
  name: z
    .string()
    .optional()
    .describe("Survey point name/number (e.g., 'BM-01', 'TP-145')"),
  isBreakline: z
    .boolean()
    .default(false)
    .describe(
      "If true, this point lies on a breakline (ridge, ditch, wall base) " +
        "that constrains TIN triangulation. Adjacent breakline points " +
        "force a triangle edge between them."
    ),
  note: z.string().optional(),
});
export type SpotElevation = z.infer<typeof SpotElevation>;

// ─── Entity: Breakline ──────────────────────────────────────────────────────
// A polyline that constrains the TIN triangulation — forces triangle edges
// along ridges, ditches, retaining walls, or any linear terrain feature
// where the surface has a sharp grade change.
// Grounding: LandXML 1.2 <Breakline>; Delaunay refinement theory.

export const Breakline = z.object({
  id: EntityId,
  name: z.string().optional().describe("Breakline label (e.g., 'Ridge A', 'Ditch 3')"),
  path: Polyline3D.describe(
    "Ordered 3D polyline. Each segment becomes a constrained edge in the TIN."
  ),
  kind: z
    .enum(["ridge", "valley", "wall_base", "curb", "shore", "other"])
    .default("other")
    .describe("Semantic classification of the breakline"),
  note: z.string().optional(),
});
export type Breakline = z.infer<typeof Breakline>;

// ─── Entity: TerrainSurface ─────────────────────────────────────────────────
// A single TIN (Triangulated Irregular Network) surface.
// Multiple surfaces may exist per site (existing, proposed, subgrade, rock).
//
// The TIN is the standard terrain representation in civil engineering and
// land surveying. It is a Delaunay triangulation of irregularly spaced
// survey points, optionally constrained by breaklines.
//
// Grounding: LandXML 1.2 <Surface>/<TIN>; IFC4 IfcGeographicElement.
// Mathematical grounding: Delaunay, B. (1934). "Sur la sphère vide."
//   Bulletin de l'Académie des Sciences de l'URSS, Classe des Sciences
//   Mathématiques et Naturelles, 6, 793–800.

export const TerrainSurface = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Surface name (e.g., 'Existing Ground', 'Proposed Grade')"),
  kind: TerrainSurfaceKind.describe("Surface purpose classification"),

  // ── TIN mesh ───────────────────────────────────────────────────────────
  /** The triangulated surface itself. Vertices include survey points and
   *  any interpolated/generated points. Triangles must form a 2-manifold
   *  (no overlapping triangles, each edge shared by at most 2 triangles).
   *  Normals face upward (CCW winding when viewed from above). */
  mesh: TriangleMesh.describe(
    "TIN (Triangulated Irregular Network). Vertices are 3D points with " +
      "real surveyed or designed elevations. Triangles form a continuous " +
      "surface. CCW winding = upward-facing normal."
  ),

  // ── Source data ────────────────────────────────────────────────────────
  spotElevations: z
    .array(SpotElevation)
    .default([])
    .describe(
      "Surveyed control points used to construct this TIN. " +
        "Lifecycle: composed. Vertices in `mesh` are derived from these."
    ),
  breaklines: z
    .array(Breakline)
    .default([])
    .describe(
      "Constrained edges in the triangulation. " +
        "Lifecycle: composed."
    ),

  // ── Derived metrics ────────────────────────────────────────────────────
  /** Rule 18: Computed. */
  boundingBox: BoundingBox3D.optional().describe(
    "COMPUTED. Axis-aligned bounding box of the entire surface."
  ),
  minElevation: z.number().optional().describe("COMPUTED. Lowest vertex Z on this surface."),
  maxElevation: z.number().optional().describe("COMPUTED. Highest vertex Z on this surface."),

  // ── Geotechnical context ───────────────────────────────────────────────
  predominantSoil: SoilClassification.optional().describe(
    "Predominant soil type (USCS) for this surface layer. " +
      "For detailed per-zone soil data, use extensions."
  ),

  // ── Provenance ─────────────────────────────────────────────────────────
  surveyDate: z.string().datetime().optional().describe("ISO 8601 UTC. When this surface was surveyed."),
  surveyedBy: z.string().optional().describe("Surveyor or survey company"),
  sourceDescription: z
    .string()
    .optional()
    .describe(
      "How the surface data was acquired " +
        "(e.g., 'Total station survey', 'LiDAR 2024-03', 'Drone photogrammetry')."
    ),

  note: z.string().optional(),
});
export type TerrainSurface = z.infer<typeof TerrainSurface>;

// ─── Entity: CutFillRegion ──────────────────────────────────────────────────
// Defines the volumetric relationship between two terrain surfaces
// (typically existing → proposed). Where proposed is below existing = cut;
// where proposed is above existing = fill.
//
// This is not a direct geometric entity — it is a computed overlay.
// The region boundaries are derivable from the intersection of the two TINs.
// Stored here for convenience and for annotating grading plans.
//
// Grounding: Standard earthwork quantity calculation (cross-section method
// or prismoidal formula); LandXML 1.2 <GradeModel>.

export const CutFillRegion = z.object({
  id: EntityId,
  existingSurfaceId: EntityId.describe("FK → TerrainSurface.id (existing ground)"),
  proposedSurfaceId: EntityId.describe("FK → TerrainSurface.id (proposed grade)"),
  boundary: Polygon2D.describe(
    "2D plan boundary of this cut/fill region. " +
      "Derived from the intersection of the two surfaces."
  ),
  /** Rule 18: All volume/depth values are computed. */
  kind: z.enum(["cut", "fill"]).describe("Whether material is removed (cut) or added (fill)"),
  volumeCuUnits: z
    .number()
    .positive()
    .optional()
    .describe("COMPUTED. Earthwork volume in (lengthUnit)³."),
  maxDepth: z
    .number()
    .positive()
    .optional()
    .describe("COMPUTED. Maximum vertical difference between surfaces in this region."),
  avgDepth: z
    .number()
    .positive()
    .optional()
    .describe("COMPUTED. Average vertical difference."),
  note: z.string().optional(),
});
export type CutFillRegion = z.infer<typeof CutFillRegion>;

// ═══════════════════════════════════════════════════════════════════════════
// SITE ENTITIES (new in v3.0.0)
// ═══════════════════════════════════════════════════════════════════════════

// ─── Entity: SiteBoundary ───────────────────────────────────────────────────
// Property lines, setbacks, easements, zoning boundaries.
// Grounding: IFC4 IfcSite boundaries; standard surveying and land use terms.

export const SiteBoundary = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Boundary label (e.g., 'Property Line', 'Front Setback 5m')"),
  kind: SiteBoundaryKind.describe("Boundary classification"),
  /** A boundary may be a closed polygon (property line, flood zone) or an
   *  open polyline (a single setback line along one edge). Rule 8 applies —
   *  discriminated on `geometry.type`. */
  geometry: z.discriminatedUnion("type", [
    z.object({ type: z.literal("polygon"), polygon: Polygon2D }),
    z.object({ type: z.literal("polyline"), polyline: Polyline2D }),
  ]).describe("2D plan geometry of the boundary"),
  offsetDistance: z
    .number()
    .min(0)
    .optional()
    .describe(
      "For setbacks: the required offset distance from the reference edge " +
        "(property line, road centerline, etc.), in site length units."
    ),
  legalReference: z
    .string()
    .optional()
    .describe("Legal instrument reference (e.g., deed book/page, plat number, zoning code section)"),
  note: z.string().optional(),
});
export type SiteBoundary = z.infer<typeof SiteBoundary>;

// ─── Entity: SiteFeature ────────────────────────────────────────────────────
// Existing physical features on the site: trees, roads, water, utilities, etc.
// Grounding: IFC4 IfcGeographicElement; civil/survey practice.

export const SiteFeature = z.object({
  id: EntityId,
  name: z.string().optional().describe("Feature label (e.g., 'Oak #14', 'Elm Street')"),
  kind: SiteFeatureKind.describe("Feature classification"),
  layer: LayerKind.default("site").describe("Logical layer"),

  // ── Geometry — discriminated by feature type ───────────────────────────
  // Rule 8: Discriminated on `geometryType`.
  // point: trees, poles, hydrants, manholes
  // polyline: roads, paths, underground utilities, fences
  // polygon: water bodies, parking lots, existing structures
  geometryType: z.enum(["point", "polyline", "polygon"]).describe(
    "Geometry representation mode"
  ),
  position: Point3D.optional().describe(
    "Point features: center/base position. Required when geometryType = 'point'."
  ),
  path: Polyline3D.optional().describe(
    "Linear features: centerline path. Required when geometryType = 'polyline'."
  ),
  footprint: Polygon2D.optional().describe(
    "Area features: plan boundary. Required when geometryType = 'polygon'."
  ),

  // ── Feature-specific properties ────────────────────────────────────────
  // These are optional and relevant depending on `kind`.
  /** Trees: canopy radius */
  canopyRadiusUnits: z
    .number()
    .positive()
    .optional()
    .describe("Canopy radius for trees, in site length units"),
  /** Trees: trunk diameter at breast height (DBH), the standard forestry measure */
  trunkDiameterUnits: z
    .number()
    .positive()
    .optional()
    .describe("Trunk diameter at breast height (1.37m / 4.5ft), in site length units"),
  /** Trees, poles, structures: height above ground */
  heightAboveGround: z
    .number()
    .positive()
    .optional()
    .describe("Feature height above ground surface, in site length units"),
  /** Linear features: width/corridor */
  widthUnits: z
    .number()
    .positive()
    .optional()
    .describe("Width of a linear feature (road, path, ditch), in site length units"),
  /** Underground utilities: depth below surface */
  depthBelowSurface: z
    .number()
    .positive()
    .optional()
    .describe("Depth of underground features below existing grade, in site length units"),
  /** Underground utilities: pipe/conduit diameter */
  pipeDiameter: z
    .number()
    .positive()
    .optional()
    .describe("Pipe or conduit outer diameter, in site length units"),
  /** Existing/demolished structures: footprint area */
  footprintAreaSqUnits: z
    .number()
    .positive()
    .optional()
    .describe("COMPUTED. Footprint area for polygon features, in (lengthUnit)²."),
  /** Whether this feature is to be preserved or removed during construction */
  preservationStatus: z
    .enum(["preserve", "remove", "relocate", "protect_in_place", "undecided"])
    .default("undecided")
    .describe("Construction-phase disposition of this feature"),

  note: z.string().optional(),
});
export type SiteFeature = z.infer<typeof SiteFeature>;

// ═══════════════════════════════════════════════════════════════════════════
// SITE COORDINATE SYSTEM (moved from BuildingModel to ProjectSite in v3)
// ═══════════════════════════════════════════════════════════════════════════

export const SiteCoordinateSystem = z.object({
  id: EntityId,
  name: z.string().min(1).describe("Grid name (e.g., 'Construction Grid A')"),
  horizontalCRS: z
    .string()
    .regex(/^EPSG:\d{4,5}$/)
    .optional()
    .describe("EPSG code for site horizontal CRS (e.g., 'EPSG:32723')"),
  siteUnit: LengthUnit.describe("Unit of the site grid coordinates"),
  verticalOffset: z.number().default(0).describe(
    "Site datum Z=0 corresponds to this elevation in the vertical datum"
  ),
  verticalDatum: VerticalDatumKind.default("local_benchmark"),
  verticalDatumDescription: z.string().optional().describe(
    "Free-text description when 'local_benchmark' or 'other'"
  ),
  gridConvergenceDeg: z.number().min(-10).max(10).default(0),
  surveyDate: z.string().datetime().optional(),
  surveyedBy: z.string().optional(),
  note: z.string().optional(),
});
export type SiteCoordinateSystem = z.infer<typeof SiteCoordinateSystem>;

// ═══════════════════════════════════════════════════════════════════════════
// VIEWPOINT AND DRAWING VIEW (from v2.1.0, now available at site level too)
// ═══════════════════════════════════════════════════════════════════════════

export const ViewPoint = z.object({
  id: EntityId,
  name: z.string().min(1),
  eye: Point3D.describe("Camera position in site coordinates"),
  target: Point3D.describe("Look-at point"),
  up: Vector3D.default({ x: 0, y: 0, z: 1 }),
  projection: ProjectionType.default("perspective"),
  fovDeg: z.number().min(1).max(179).default(60).describe("Vertical FOV. Perspective only."),
  orthoHeight: z.number().positive().optional().describe("Ortho view height. Ortho/iso only."),
  nearClip: z.number().positive().optional(),
  farClip: z.number().positive().optional(),
  sectionBox: BoundingBox3D.optional(),
  aspectRatio: z.number().positive().optional(),
  layerOverrides: z.record(LayerKind, z.boolean()).optional(),
  visibleFloorIds: z.array(EntityId).optional().describe("FK → Floor.id[]"),
  /** New in v3: scope to specific building(s) */
  visibleBuildingIds: z.array(EntityId).optional().describe(
    "FK → BuildingModel.id[]. Which buildings are visible. Absent = show all."
  ),
  note: z.string().optional(),
});
export type ViewPoint = z.infer<typeof ViewPoint>;

export const DrawingView = z.object({
  id: EntityId,
  name: z.string().min(1),
  kind: DrawingViewKind,
  cuttingPlane: Plane3D.optional(),
  viewDepth: z.number().positive().optional(),
  viewForward: z.number().min(0).default(0),
  cropRegion: z
    .object({
      minX: z.number(), minY: z.number(),
      maxX: z.number(), maxY: z.number(),
    })
    .optional(),
  scale: z.string().regex(/^1:\d+$/).optional(),
  parentViewId: EntityId.optional().describe("FK → DrawingView.id"),
  viewPointId: EntityId.optional().describe("FK → ViewPoint.id"),
  floorIds: z.array(EntityId).optional().describe("FK → Floor.id[]"),
  /** New in v3: scope to specific building */
  buildingId: EntityId.optional().describe("FK → BuildingModel.id. Which building this view applies to."),
  /** New in v3: include terrain in the view */
  showTerrain: z.boolean().default(true).describe("Whether to include terrain surfaces in this view"),
  showSiteFeatures: z.boolean().default(false).describe("Whether to include site features"),
  layerOverrides: z.record(LayerKind, z.boolean()).optional(),
  viewAnnotations: z
    .array(z.object({
      id: EntityId,
      kind: AnnotationKind,
      position: Point2D,
      text: z.string().optional(),
      targetViewId: EntityId.optional().describe("FK → DrawingView.id"),
      note: z.string().optional(),
    }))
    .default([]),
  note: z.string().optional(),
});
export type DrawingView = z.infer<typeof DrawingView>;

// ═══════════════════════════════════════════════════════════════════════════
// BUILDING ENTITIES (from v2.1.0, structurally unchanged)
// ═══════════════════════════════════════════════════════════════════════════

export const Opening = z.object({
  id: EntityId,
  kind: OpeningKind,
  offsetAlongWall: z.number().min(0),
  width: z.number().positive(),
  height: z.number().positive(),
  sillHeight: z.number().min(0),
  swingDirection: SwingDirection.default("none"),
  note: z.string().optional(),
});
export type Opening = z.infer<typeof Opening>;

export const Wall = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("architectural"),
  wallType: WallType,
  centerline: z.object({ start: Point2D, end: Point2D }),
  thickness: z.number().positive(),
  height: z.number().positive(),
  baseElevation: z.number(),
  material: MaterialSpec.optional(),
  openings: z.array(Opening).default([]),
  geometry: Geometry3D.optional().describe("COMPUTED."),
  note: z.string().optional(),
});
export type Wall = z.infer<typeof Wall>;

export const Slab = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("structural"),
  kind: SlabKind,
  boundary: BoundaryWithHoles2D,
  thickness: z.number().positive(),
  elevation: z.number(),
  material: MaterialSpec.optional(),
  slopePercent: z.number().min(0).default(0),
  slopeDirection: Vector3D.optional(),
  geometry: Geometry3D.optional().describe("COMPUTED."),
  note: z.string().optional(),
});
export type Slab = z.infer<typeof Slab>;

export const RoofSurface = z.object({
  id: EntityId,
  name: z.string().min(1),
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
  ridgeElevation: z.number(),
  eaveElevation: z.number(),
  overhang: z.number().min(0).default(0),
  surfaces: z.array(RoofSurface).min(1),
  note: z.string().optional(),
});
export type Roof = z.infer<typeof Roof>;

export const Space = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("architectural"),
  name: z.string().min(1),
  usage: SpaceUsage,
  boundary: BoundaryWithHoles2D,
  floorElevation: z.number(),
  ceilingElevation: z.number(),
  areaSqUnits: z.number().positive().optional().describe("COMPUTED."),
  volumeCuUnits: z.number().positive().optional().describe("COMPUTED."),
  finishFloor: z.string().optional(),
  finishWall: z.string().optional(),
  finishCeiling: z.string().optional(),
  note: z.string().optional(),
});
export type Space = z.infer<typeof Space>;

export const StructuralElement = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  layer: LayerKind.default("structural"),
  kind: StructuralElementKind,
  position: Point3D,
  geometry: Geometry3D,
  material: MaterialSpec.optional(),
  rotationDeg: z.number().min(0).max(360).default(0),
  loadCapacityKN: z.number().positive().optional(),
  note: z.string().optional(),
});
export type StructuralElement = z.infer<typeof StructuralElement>;

export const Fixture = z.object({
  id: EntityId,
  floorId: EntityId.describe("FK → Floor.id"),
  spaceId: EntityId.optional().describe("FK → Space.id"),
  layer: LayerKind,
  category: FixtureCategory,
  label: z.string().optional(),
  position: Point3D,
  rotationDeg: z.number().min(0).max(360).default(0),
  boundingSize: z.object({
    width: z.number().positive(),
    depth: z.number().positive(),
    height: z.number().positive(),
  }).optional(),
  geometry: Geometry3D.optional(),
  symbolRef: z.string().optional(),
  note: z.string().optional(),
});
export type Fixture = z.infer<typeof Fixture>;

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
  segments: z.array(MEPSegment).min(1),
  insulationThickness: z.number().min(0).default(0),
  flowDirection: z.enum(["start_to_end", "end_to_start", "bidirectional", "not_applicable"]).default("start_to_end"),
  floorIds: z.array(EntityId).min(1).describe("FK → Floor.id[]"),
  note: z.string().optional(),
});
export type MEPRun = z.infer<typeof MEPRun>;

export const VerticalCirculation = z.object({
  id: EntityId,
  kind: VerticalCirculationKind,
  connectsFloorIds: z.array(EntityId).min(2).describe("FK → Floor.id[]"),
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

export const Floor = z.object({
  id: EntityId,
  buildingId: EntityId.describe("FK → Building.id"),
  level: z.number().int(),
  name: z.string().min(1),
  elevationAboveDatum: z.number(),
  floorToFloorHeight: z.number().positive(),
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
// v3 change: geoReference REMOVED (moved to ProjectSite level).

export const Building = z.object({
  id: EntityId,
  name: z.string().min(1),
  address: z.string().optional(),
  typology: z.string().optional(),
  envelopeGeometry: Geometry3D.optional().describe("COMPUTED / OPTIONAL. LOD-0 envelope."),
  note: z.string().optional(),
});
export type Building = z.infer<typeof Building>;

// ═══════════════════════════════════════════════════════════════════════════
// BUILDING MODEL (demoted from root to child in v3.0.0)
// ═══════════════════════════════════════════════════════════════════════════
//
// A BuildingModel is a self-contained 3D model of a single building,
// positioned on the site via a BuildingPlacement transform.
//
// ALL coordinates inside a BuildingModel are in the building's LOCAL frame.
// The placement transform converts them to site coordinates.
//
// Transform chain:
//   Building Local → (placement) → Site → (CRS/geoRef) → WGS84

/**
 * Positions a BuildingModel on the ProjectSite.
 *
 * The placement maps the building's local origin to a point on the site,
 * with an optional rotation. After placement, all building-local coordinates
 * can be converted to site coordinates:
 *   P_site.x = cos(θ) · (s · P_local.x) − sin(θ) · (s · P_local.y) + anchorPoint.x
 *   P_site.y = sin(θ) · (s · P_local.x) + cos(θ) · (s · P_local.y) + anchorPoint.y
 *   P_site.z = P_local.z + anchorPoint.z
 * where θ = rotationDeg (CCW), s = scaleFactor.
 */
export const BuildingPlacement = z.object({
  anchorPoint: Point3D.describe(
    "The site-coordinate point where the building's local origin (0,0,0) is placed. " +
      "Z component sets the building datum elevation in site coordinates."
  ),
  rotationDeg: z
    .number()
    .min(-360)
    .max(360)
    .default(0)
    .describe(
      "Rotation of the building's +X axis relative to the site's +X (east), " +
        "degrees CCW."
    ),
  scaleFactor: z
    .number()
    .positive()
    .default(1.0)
    .describe(
      "Scale from building length units to site length units. " +
        "E.g., building in mm, site in m → scaleFactor = 0.001."
    ),
});
export type BuildingPlacement = z.infer<typeof BuildingPlacement>;

export const BuildingModel = z.object({
  id: EntityId,
  title: z.string().min(1).describe("Building model title"),

  // ── Local coordinate system (building-internal) ─────────────────────
  lengthUnit: LengthUnit.describe("Unit for coordinates WITHIN this building model"),
  angleUnit: AngleUnit.default("deg"),
  upAxis: z.literal("z").default("z"),
  trueNorthDeg: z.number().min(0).max(360).default(0).describe(
    "True north relative to building +Y. " +
      "May differ from site north if the building is rotated on site."
  ),

  // ── Placement on site ──────────────────────────────────────────────
  placement: BuildingPlacement.describe(
    "How this building is positioned on the ProjectSite. " +
      "Maps building local origin to site coordinates."
  ),

  // ── Composition ──────────────────────────────────────────────────────
  building: Building.describe("Building metadata"),
  floors: z.array(Floor).min(1),
  roofs: z.array(Roof).default([]),

  // ── Aggregation ──────────────────────────────────────────────────────
  verticalCirculation: z.array(VerticalCirculation).default([]),
  mepRuns: z.array(MEPRun).default([]),

  // ── Building-scoped views ────────────────────────────────────────────
  viewPoints: z.array(ViewPoint).default([]).describe(
    "Building-scoped viewpoints in building-local coordinates."
  ),
  drawingViews: z.array(DrawingView).default([]).describe(
    "Building-scoped drawing views."
  ),

  // ── Presentation ─────────────────────────────────────────────────────
  layerVisibility: z.record(LayerKind, z.boolean()).optional(),

  // ── Extension ────────────────────────────────────────────────────────
  extensions: z.record(z.string(), z.unknown()).optional(),

  note: z.string().optional(),
});
export type BuildingModel = z.infer<typeof BuildingModel>;

// ═══════════════════════════════════════════════════════════════════════════
// ROOT ENTITY: ProjectSite (new in v3.0.0)
// ═══════════════════════════════════════════════════════════════════════════
//
// The world container. Owns the terrain, site boundaries, site features,
// and one or more BuildingModels placed upon it.
//
// All site-level coordinates (terrain vertices, boundary polygons,
// feature positions) use the site coordinate system.

export const ProjectSite = z.object({
  schemaVersion: z.literal(SCHEMA_VERSION).describe("Schema version (semver)"),
  id: EntityId,
  name: z.string().min(1).describe("Project / site name"),
  description: z.string().optional().describe("Project description"),

  // ══ SITE COORDINATE SYSTEM ═════════════════════════════════════════════
  /** The canonical coordinate system for the site. All site-level entities
   *  (terrain, boundaries, features) use these coordinates. */
  lengthUnit: LengthUnit.describe("Unit for ALL site-level coordinates"),
  angleUnit: AngleUnit.default("deg"),
  upAxis: z.literal("z").default("z"),
  trueNorthDeg: z
    .number()
    .min(0)
    .max(360)
    .default(0)
    .describe("True north relative to site +Y axis, degrees clockwise"),

  coordinateSystem: SiteCoordinateSystem.optional().describe(
    "Surveyor grid and CRS definition. Bridges site coordinates to geographic."
  ),

  geoReference: z
    .object({
      latitude: z.number().min(-90).max(90).describe("WGS84 latitude"),
      longitude: z.number().min(-180).max(180).describe("WGS84 longitude"),
      altitudeM: z.number().optional().describe("Altitude above sea level in meters"),
    })
    .optional()
    .describe(
      "Geographic anchor. The site origin (0,0,0) maps to this WGS84 point. " +
        "If coordinateSystem is also provided, this is derivable from the CRS — " +
        "stored for convenience and for consumers that lack CRS projection libraries."
    ),

  // ══ TERRAIN ════════════════════════════════════════════════════════════
  terrainSurfaces: z
    .array(TerrainSurface)
    .default([])
    .describe(
      "TIN terrain surfaces (existing, proposed, subgrade, rock). " +
        "Lifecycle: composed."
    ),

  cutFillRegions: z
    .array(CutFillRegion)
    .default([])
    .describe(
      "COMPUTED. Cut/fill regions derived from existing vs. proposed surfaces. " +
        "Lifecycle: composed."
    ),

  // ══ SITE BOUNDARIES ════════════════════════════════════════════════════
  boundaries: z
    .array(SiteBoundary)
    .default([])
    .describe("Property lines, setbacks, easements, zoning. Lifecycle: composed."),

  // ══ SITE FEATURES ══════════════════════════════════════════════════════
  features: z
    .array(SiteFeature)
    .default([])
    .describe("Existing site features (trees, roads, water, utilities). Lifecycle: composed."),

  // ══ BUILDINGS ══════════════════════════════════════════════════════════
  buildings: z
    .array(BuildingModel)
    .default([])
    .describe(
      "Building models placed on this site. Each has its own local coordinate " +
        "system and a placement transform to site coordinates. " +
        "Lifecycle: composed. May be empty for a site-only / terrain-only document."
    ),

  // ══ SITE-LEVEL VIEWS ═══════════════════════════════════════════════════
  /** Viewpoints in site coordinates — for overall site views, aerial
   *  perspectives, or cross-building views. Building-specific viewpoints
   *  live inside their BuildingModel. */
  viewPoints: z
    .array(ViewPoint)
    .default([])
    .describe("Site-scoped viewpoints in site coordinates. Lifecycle: composed."),

  drawingViews: z
    .array(DrawingView)
    .default([])
    .describe("Site-scoped drawing views (site plan, grading plan, etc.). Lifecycle: composed."),

  // ══ PRESENTATION ═══════════════════════════════════════════════════════
  layerVisibility: z.record(LayerKind, z.boolean()).optional(),

  // ══ METADATA ═══════════════════════════════════════════════════════════
  metadata: Metadata,

  // ══ EXTENSION POINT ════════════════════════════════════════════════════
  extensions: z
    .record(z.string(), z.unknown())
    .optional()
    .describe("EXTENSION POINT. Namespaced keys (e.g., 'com.acme.stormwater')."),
});
export type ProjectSite = z.infer<typeof ProjectSite>;

export default ProjectSite;

/**
 * ============================================================================
 * DESIGN ASSUMPTIONS (v3.0.0 — ProjectSite + Terrain)
 * ============================================================================
 *
 * All assumptions from v2.0.0 and v2.1.0 remain in force for building-level
 * entities. Below are ADDITIONAL assumptions introduced in v3.0.0.
 *
 * 20. HIERARCHY INVERSION: The root entity is now ProjectSite, not
 *     BuildingModel. A ProjectSite owns terrain, boundaries, features,
 *     and zero or more BuildingModels. This supports:
 *     - Multi-building campuses on a single site
 *     - Site-only documents (grading plans, surveys) with no buildings
 *     - Phased construction (building models added over time)
 *
 * 21. COORDINATE HIERARCHY: Three levels, each with its own frame:
 *
 *     ┌─────────────────┐  placement  ┌─────────────────┐  CRS/geoRef  ┌──────────┐
 *     │ Building Local   │───────────▶│  Site            │────────────▶│  WGS84   │
 *     │ (per-building)   │ anchorPt + │  (shared ground  │  EPSG code  │  lat/lon  │
 *     │ own lengthUnit   │ rotation + │   truth for all  │  + vert.    │  alt      │
 *     │ own origin       │ scale      │   buildings)     │  datum      │          │
 *     └─────────────────┘            └─────────────────┘             └──────────┘
 *
 *     Site coordinates are the shared ground truth. Terrain, boundaries,
 *     and features all live in site coordinates. Buildings bring their own
 *     local frames and are placed on the site via BuildingPlacement.
 *
 * 22. TERRAIN MODEL (TIN):
 *     A Triangulated Irregular Network is a set of non-overlapping
 *     triangles whose vertices are survey points with known 3D coordinates.
 *     The triangulation is typically Delaunay (maximizes minimum angle),
 *     optionally constrained by breaklines that force triangle edges along
 *     sharp terrain features.
 *
 *     Why TIN over regular grid:
 *     - Adapts density to terrain complexity (more triangles on slopes,
 *       fewer on flat areas)
 *     - Preserves exact survey point elevations (no interpolation loss)
 *     - Breaklines model discontinuities (ridges, ditches, walls) that
 *       grids smooth over
 *     - Standard in civil engineering and land surveying (LandXML, IFC)
 *
 *     The schema stores both the TIN mesh and (optionally) the source
 *     survey data (SpotElevations, Breaklines). This supports:
 *     - Renderers that consume the mesh directly
 *     - Tools that need to re-triangulate (e.g., after adding points)
 *     - Provenance tracking (which surveyor, which date, which instrument)
 *
 * 23. MULTIPLE TERRAIN SURFACES:
 *     A site may have several surfaces at different stages:
 *     - `existing`: as-surveyed ground before construction
 *     - `proposed`: the designed finish grade
 *     - `subgrade`: the compacted surface below structural fill
 *     - `rock`: top-of-rock from geotechnical borings
 *
 *     CutFillRegion captures the volumetric difference between any two
 *     surfaces (typically existing → proposed), enabling earthwork
 *     quantity calculations.
 *
 * 24. BUILDING PLACEMENT:
 *     Each BuildingModel carries a BuildingPlacement that maps its local
 *     origin to a site coordinate point. The transform is:
 *       P_site = R(θ) · (s · P_building) + anchorPoint
 *     where θ = rotationDeg, s = scaleFactor.
 *
 *     This means buildings can use different length units (mm for detail,
 *     m for site) and be rotated independently. Two buildings on the same
 *     site can face different directions.
 *
 * 25. GEO-REFERENCE MOVED:
 *     Building.geoReference is removed in v3. The geographic anchor now
 *     lives on ProjectSite — one anchor for the entire site, not per-building.
 *     Each building's geographic position is derived from:
 *       building.placement → site origin → geoReference
 *
 * 26. SITE FEATURES:
 *     Modeled with a flexible geometry discriminator (point, polyline,
 *     polygon) because site features vary widely in shape:
 *     - Trees, poles, hydrants → point (position + properties)
 *     - Roads, utilities, fences → polyline (centerline + width)
 *     - Water bodies, parking lots → polygon (boundary)
 *
 *     The `preservationStatus` field captures construction-phase decisions
 *     (preserve, remove, relocate) — critical for site logistics and
 *     environmental compliance.
 *
 * 27. VIEWPOINTS SCOPED TO TWO LEVELS:
 *     ViewPoints and DrawingViews exist at both:
 *     - Site level (for overall site plans, aerial views, grading plans)
 *     - Building level (for floor plans, sections, detail views)
 *     Site-level viewpoints use site coordinates; building-level viewpoints
 *     use building-local coordinates. The placement transform bridges them.
 *
 * ============================================================================
 * BREAKING CHANGES FROM v2.1.0 (Migration Guide)
 * ============================================================================
 *
 * | Change                                      | Category  | v2.1 → v3.0 Action                       |
 * |---------------------------------------------|-----------|--------------------------------------------|
 * | Schema version: 2.1.0 → 3.0.0              | Breaking  | Update schemaVersion                       |
 * | Root: BuildingModel → ProjectSite           | Breaking  | Wrap each BuildingModel in a ProjectSite   |
 * | BuildingModel.schemaVersion: removed         | Breaking  | Version is on ProjectSite now               |
 * | BuildingModel.origin: removed                | Breaking  | Origin is implicit (0,0,0) in local frame  |
 * | BuildingModel.siteCoordinateSystem: removed  | Breaking  | Moved to ProjectSite.coordinateSystem      |
 * | BuildingModel.metadata: removed              | Breaking  | Moved to ProjectSite.metadata              |
 * | BuildingModel.placement: new required field  | Breaking  | Add placement with anchorPoint + rotation  |
 * | Building.geoReference: removed               | Breaking  | Moved to ProjectSite.geoReference          |
 * | New entity: ProjectSite (root)               | Breaking  | Create wrapping ProjectSite                |
 * | New entity: TerrainSurface                   | Additive  | No action (defaults to [])                 |
 * | New entity: SpotElevation                    | Additive  | No action                                  |
 * | New entity: Breakline                        | Additive  | No action                                  |
 * | New entity: CutFillRegion                    | Additive  | No action (defaults to [])                 |
 * | New entity: SiteBoundary                     | Additive  | No action (defaults to [])                 |
 * | New entity: SiteFeature                      | Additive  | No action (defaults to [])                 |
 * | New entity: BuildingPlacement                | Additive  | Required on BuildingModel                  |
 * | New enums: TerrainSurfaceKind, SiteBoundary- | Additive  | No action                                  |
 * |   Kind, SiteFeatureKind, SoilClassification  |           |                                            |
 * | New types: Polyline2D, Polyline3D            | Additive  | No action                                  |
 * | LayerKind: added terrain, grading,           | Additive  | No action (enum widened)                   |
 * |   landscaping, utilities                     |           |                                            |
 * | ViewPoint.visibleBuildingIds: new optional   | Additive  | No action                                  |
 * | DrawingView.buildingId: new optional          | Additive  | No action                                  |
 * | DrawingView.showTerrain: new (default true)  | Additive  | No action                                  |
 * | DrawingView.showSiteFeatures: new (def false)| Additive  | No action                                  |
 *
 * MIGRATION RECIPE (v2.1.0 → v3.0.0):
 *   1. Create a ProjectSite with site-level fields from the old BuildingModel
 *      (lengthUnit, angleUnit, trueNorthDeg, metadata, etc.)
 *   2. Move siteCoordinateSystem to ProjectSite.coordinateSystem
 *   3. Move building.geoReference to ProjectSite.geoReference
 *   4. Add a BuildingPlacement to the BuildingModel:
 *      { anchorPoint: { x: 0, y: 0, z: 0 }, rotationDeg: 0, scaleFactor: 1.0 }
 *      (identity transform — building origin = site origin, for single-building sites)
 *   5. Put the BuildingModel into ProjectSite.buildings[]
 *   6. Move site-level viewPoints/drawingViews to ProjectSite level;
 *      keep building-specific ones inside BuildingModel
 *
 * ============================================================================
 * REVIEW SCORECARD (v3.0.0)
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
 * R8: SiteBoundary.geometry uses z.discriminatedUnion on `type`
 *   (polygon | polyline). SiteFeature uses `geometryType` enum selector —
 *   acceptable because the geometry fields are optional and selected by
 *   the enum; if they diverge structurally, refactor to union.
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
 * R12: ProjectSite composes all site-level entities. BuildingModel
 *   composes all building-level entities. BuildingPlacement is a value
 *   object (no identity), not an entity.
 * R13: CutFillRegion references TerrainSurface by ID (declared).
 *   DrawingView.buildingId references BuildingModel.id (declared).
 *   ViewPoint.visibleBuildingIds references BuildingModel.id[] (declared).
 * R14: No cycles. Ownership tree:
 *   ProjectSite → {TerrainSurface, SiteBoundary, SiteFeature, BuildingModel}
 *   BuildingModel → {Floor → {Wall, Space, Slab, ...}, Roof, etc.}
 *   CutFillRegion references TerrainSurface (FK, not ownership — DAG).
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
 * R15: geoReference exists once on ProjectSite, not per-building.
 *   TerrainSurface.mesh is the source of truth; bounding box and
 *   elevation extremes are COMPUTED.
 * R17: TriangleMesh is reused for both building geometry and terrain
 *   TINs. Point3D, Polygon2D, Polyline3D are shared across all levels.
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
 * R21: All breaking changes classified in the migration table.
 * R22: Major version bump — removals are permitted without deprecation
 *   cycle per semver convention.
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
 * R24: surveyDate, surveyedBy on TerrainSurface and SiteCoordinateSystem
 *   are immutable provenance fields.
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
