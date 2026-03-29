/**
 * TypeScript types for BuildingModel v2.0/v2.1 JSON files.
 * Mirrors building-model-3d-v2.1.ts schema — renderer subset.
 */

export interface Point2D { x: number; y: number }
export interface Point3D { x: number; y: number; z: number }
export interface Vector3D { x: number; y: number; z: number }

export interface Polygon2D { vertices: Point2D[] }
export interface BoundaryWithHoles2D { outer: Polygon2D; holes?: Polygon2D[] }

export interface MaterialSpec {
  name: string
  densityKgPerM3?: number
  fireRatingMinutes?: number
}

export interface Opening {
  id: string
  kind: string
  offsetAlongWall: number
  width: number
  height: number
  sillHeight: number
  swingDirection?: string
  note?: string
}

export interface Wall {
  id: string
  floorId: string
  layer?: string
  wallType: string
  centerline: { start: Point2D; end: Point2D }
  thickness: number
  height: number
  baseElevation: number
  material?: MaterialSpec
  openings?: Opening[]
  note?: string
}

export interface Space {
  id: string
  floorId: string
  layer?: string
  name: string
  usage: string
  boundary: BoundaryWithHoles2D
  floorElevation: number
  ceilingElevation: number
  areaSqUnits?: number
  finishFloor?: string
  note?: string
}

export interface Slab {
  id: string
  floorId: string
  kind: string
  boundary: BoundaryWithHoles2D
  thickness: number
  elevation: number
}

export interface Fixture {
  id: string
  floorId: string
  spaceId?: string
  layer: string
  category: string
  label?: string
  position: Point3D
  rotationDeg?: number
  boundingSize?: { width: number; depth: number; height: number }
  note?: string
}

export interface Floor {
  id: string
  buildingId: string
  level: number
  name: string
  elevationAboveDatum: number
  floorToFloorHeight: number
  walls?: Wall[]
  spaces?: Space[]
  slabs?: Slab[]
  fixtures?: Fixture[]
  outline?: Polygon2D
  note?: string
}

export interface Building {
  id: string
  name: string
  address?: string
  typology?: string
  note?: string
}

export interface Metadata {
  createdAt: string
  updatedAt: string
  createdBy: string
  updatedBy: string
  note?: string
}

export interface BuildingModel {
  schemaVersion: string
  id: string
  title: string
  lengthUnit: string
  building: Building
  floors: Floor[]
  metadata: Metadata
  extensions?: Record<string, unknown>
}

/**
 * Simplified human figure for scene placement.
 * Derived from the full HumanBody schema (schemas/src/body.ts).
 *
 * Position uses the building's lengthUnit (meters).
 * Height from HumanBody.proportions.totalHeight (converted from cm to meters).
 * Clothing colors from HumanBody.clothing[].color.
 */
export interface HumanFigure {
  id: string
  name: string
  position: Point3D
  rotationDeg?: number
  heightM: number
  clothingColor?: { r: number; g: number; b: number }
  hairColor?: { r: number; g: number; b: number }
  skinColor?: { r: number; g: number; b: number }
  pose?: string
  note?: string
}
