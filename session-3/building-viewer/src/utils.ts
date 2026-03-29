import type { Point2D, Polygon2D, Wall, BuildingModel, HumanFigure } from "./types"

export function polygonArea(poly: Polygon2D): number {
  const v = poly.vertices
  let area = 0
  for (let i = 0; i < v.length; i++) {
    const j = (i + 1) % v.length
    area += v[i].x * v[j].y - v[j].x * v[i].y
  }
  return Math.abs(area) / 2
}

export function polygonCentroid(poly: Polygon2D): Point2D {
  const v = poly.vertices
  return {
    x: v.reduce((s, p) => s + p.x, 0) / v.length,
    y: v.reduce((s, p) => s + p.y, 0) / v.length,
  }
}

export function wallLength(wall: Wall): number {
  const dx = wall.centerline.end.x - wall.centerline.start.x
  const dy = wall.centerline.end.y - wall.centerline.start.y
  return Math.sqrt(dx * dx + dy * dy)
}

// Space usage → color mapping
const USAGE_COLORS: Record<string, string> = {
  living_room: "#374f78", dining_room: "#374f78",
  bedroom: "#2d466e", kitchen: "#465f82",
  bathroom: "#3c587d", restroom: "#3c587d",
  closet: "#263a5f", storage: "#263a5f",
  hallway: "#23375a", corridor: "#23375a",
  lobby: "#283e64", laundry: "#324872",
  commercial: "#3a5070", office: "#3a5070",
  other: "#30446a",
}

export function usageColor(usage: string): string {
  return USAGE_COLORS[usage] ?? USAGE_COLORS.other
}

// Lighter variant for 3D
export function usageColor3D(usage: string): number {
  const hex = usageColor(usage)
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return ((r + 20) << 16) | ((g + 20) << 8) | (b + 20)
}

/**
 * Extract HumanFigure instances from a BuildingModel.
 *
 * Supports two sources:
 * 1. extensions["com.humans.figures"] — array of HumanFigure objects
 * 2. Full HumanBody instances in extensions["com.humans.bodies"] —
 *    extracts position from currentPose.rootPose, height from proportions,
 *    clothing color from clothing[0].
 */
export function extractHumans(model: BuildingModel): HumanFigure[] {
  const ext = model.extensions
  if (!ext) return []

  // Source 1: pre-simplified figures
  const figures = ext["com.humans.figures"] as HumanFigure[] | undefined
  if (Array.isArray(figures)) return figures

  // Source 2: full HumanBody schema instances
  const bodies = ext["com.humans.bodies"] as Array<Record<string, unknown>> | undefined
  if (!Array.isArray(bodies)) return []

  return bodies.map((body): HumanFigure => {
    const props = body.proportions as Record<string, number> | undefined
    const pose = body.currentPose as Record<string, unknown> | undefined
    const rootPose = pose?.rootPose as Record<string, unknown> | undefined
    const pos = rootPose?.position as { x: number; y: number; z: number } | undefined
    const clothing = body.clothing as Array<Record<string, unknown>> | undefined
    const firstClothing = clothing?.[0]
    const clothColor = firstClothing?.color as { r: number; g: number; b: number } | undefined

    // HumanBody uses cm; building model uses m → convert
    const heightCm = props?.totalHeight ?? 170
    const heightM = heightCm / 100

    return {
      id: (body.id as string) ?? crypto.randomUUID(),
      name: (body.name as string) ?? "Person",
      position: pos
        ? { x: pos.x / 100, y: pos.y / 100, z: pos.z / 100 } // cm → m
        : { x: 0, y: 0, z: 0 },
      heightM,
      clothingColor: clothColor,
      pose: (pose?.name as string) ?? "standing",
      note: body.note as string | undefined,
    }
  })
}
