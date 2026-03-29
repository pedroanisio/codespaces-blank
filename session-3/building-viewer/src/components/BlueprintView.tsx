import { useEffect, useRef } from "react"
import type { BuildingModel, Wall, HumanFigure } from "../types"
import { polygonArea, polygonCentroid, wallLength, usageColor, extractHumans } from "../utils"

const BG = "#182848"
const WALL_CLR = "#c8d7eb"
const LABEL_CLR = "#dce6f5"
const DIM_CLR = "#8ca5c8"
const GRID_CLR = "#1e3052"

interface Props {
  model: BuildingModel
  width: number
  height: number
}

export default function BlueprintView({ model, width, height }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Compute bounds
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const floor of model.floors) {
      for (const space of floor.spaces ?? []) {
        for (const v of space.boundary.outer.vertices) {
          minX = Math.min(minX, v.x); minY = Math.min(minY, v.y)
          maxX = Math.max(maxX, v.x); maxY = Math.max(maxY, v.y)
        }
      }
    }
    const planW = maxX - minX
    const planH = maxY - minY
    const pad = 60
    const scale = Math.min((width - pad * 2) / planW, (height - pad * 2 - 60) / planH)

    const toX = (x: number) => pad + (x - minX) * scale
    const toY = (y: number) => pad + 40 + (y - minY) * scale

    // Background
    ctx.fillStyle = BG
    ctx.fillRect(0, 0, width, height)

    // Grid
    ctx.strokeStyle = GRID_CLR
    ctx.lineWidth = 0.5
    for (let m = 0; m <= planW; m++) {
      const px = toX(minX + m)
      ctx.beginPath(); ctx.moveTo(px, toY(minY)); ctx.lineTo(px, toY(maxY)); ctx.stroke()
    }
    for (let m = 0; m <= planH; m++) {
      const py = toY(minY + m)
      ctx.beginPath(); ctx.moveTo(toX(minX), py); ctx.lineTo(toX(maxX), py); ctx.stroke()
    }

    for (const floor of model.floors) {
      // Spaces
      for (const space of floor.spaces ?? []) {
        const verts = space.boundary.outer.vertices
        ctx.fillStyle = usageColor(space.usage)
        ctx.beginPath()
        ctx.moveTo(toX(verts[0].x), toY(verts[0].y))
        for (let i = 1; i < verts.length; i++) ctx.lineTo(toX(verts[i].x), toY(verts[i].y))
        ctx.closePath()
        ctx.fill()
        ctx.strokeStyle = WALL_CLR; ctx.lineWidth = 2; ctx.stroke()

        // Labels
        const c = polygonCentroid(space.boundary.outer)
        const cx = toX(c.x), cy = toY(c.y)
        const area = space.areaSqUnits ?? polygonArea(space.boundary.outer)
        const bb = space.boundary.outer.vertices
        const bw = (Math.max(...bb.map(v => v.x)) - Math.min(...bb.map(v => v.x))) * scale
        const bh = (Math.max(...bb.map(v => v.y)) - Math.min(...bb.map(v => v.y))) * scale

        if (bw > 50 && bh > 30) {
          ctx.fillStyle = LABEL_CLR; ctx.font = "bold 11px sans-serif"; ctx.textAlign = "center"
          ctx.fillText(space.name, cx, cy - 6)
          ctx.fillStyle = DIM_CLR; ctx.font = "10px sans-serif"
          ctx.fillText(`${area.toFixed(1)} m²`, cx, cy + 8)
        }
      }

      // Walls
      for (const wall of floor.walls ?? []) {
        drawWall2D(ctx, wall, toX, toY, scale)
      }

      // Fixtures
      for (const fx of floor.fixtures ?? []) {
        const px = toX(fx.position.x), py = toY(fx.position.y)
        ctx.fillStyle = "#6482aa"; ctx.beginPath()
        ctx.arc(px, py, 3, 0, Math.PI * 2); ctx.fill()
        if (fx.label && scale > 3) {
          ctx.fillStyle = DIM_CLR; ctx.font = "8px sans-serif"; ctx.textAlign = "center"
          ctx.fillText(fx.label, px, py + 10)
        }
      }
    }

    // Human figures
    const humans = extractHumans(model)
    for (const human of humans) {
      drawHuman2D(ctx, human, toX, toY, scale)
    }

    // Title
    ctx.fillStyle = LABEL_CLR; ctx.font = "bold 16px sans-serif"; ctx.textAlign = "center"
    ctx.fillText(model.title, width / 2, 24)
    const totalArea = model.floors.flatMap(f => f.spaces ?? [])
      .reduce((s, sp) => s + (sp.areaSqUnits ?? polygonArea(sp.boundary.outer)), 0)
    ctx.fillStyle = DIM_CLR; ctx.font = "11px sans-serif"
    ctx.fillText(`${model.building.name}  |  ~${Math.round(totalArea)} m²`, width / 2, 38)

  }, [model, width, height])

  return <canvas ref={ref} width={width} height={height} style={{ borderRadius: 8 }} />
}

function drawWall2D(
  ctx: CanvasRenderingContext2D,
  wall: Wall,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
) {
  const sx = toX(wall.centerline.start.x)
  const sy = toY(wall.centerline.start.y)
  const ex = toX(wall.centerline.end.x)
  const ey = toY(wall.centerline.end.y)
  const w = Math.max(2, wall.thickness * scale)

  ctx.strokeStyle = WALL_CLR; ctx.lineWidth = w; ctx.lineCap = "round"
  ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke()

  // Openings
  const wl = wallLength(wall)
  if (wl === 0) return
  const ux = (wall.centerline.end.x - wall.centerline.start.x) / wl
  const uy = (wall.centerline.end.y - wall.centerline.start.y) / wl
  const nx = -uy, ny = ux

  for (const op of wall.openings ?? []) {
    const osx = wall.centerline.start.x + ux * op.offsetAlongWall
    const osy = wall.centerline.start.y + uy * op.offsetAlongWall
    const oex = wall.centerline.start.x + ux * (op.offsetAlongWall + op.width)
    const oey = wall.centerline.start.y + uy * (op.offsetAlongWall + op.width)
    const psx = toX(osx), psy = toY(osy), pex = toX(oex), pey = toY(oey)

    // Erase wall at opening
    ctx.strokeStyle = BG; ctx.lineWidth = w + 2
    ctx.beginPath(); ctx.moveTo(psx, psy); ctx.lineTo(pex, pey); ctx.stroke()

    if (op.kind === "window") {
      // Double line + ticks
      const t = wall.thickness * scale * 0.3
      const pnx = nx * t, pny = ny * t
      ctx.strokeStyle = WALL_CLR; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(psx + pnx, psy + pny); ctx.lineTo(pex + pnx, pey + pny); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(psx - pnx, psy - pny); ctx.lineTo(pex - pnx, pey - pny); ctx.stroke()
      const tick = wall.thickness * scale * 0.6
      const tnx = nx * tick, tny = ny * tick
      ctx.beginPath(); ctx.moveTo(psx - tnx, psy - tny); ctx.lineTo(psx + tnx, psy + tny); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(pex - tnx, pey - tny); ctx.lineTo(pex + tnx, pey + tny); ctx.stroke()
    } else if (op.kind.includes("door") || op.kind === "archway") {
      // Door arc
      const dp = op.width * scale
      const half = dp / 2
      const mcx = (psx + pex) / 2, mcy = (psy + pey) / 2
      ctx.strokeStyle = DIM_CLR; ctx.lineWidth = 1
      ctx.beginPath(); ctx.arc(mcx, mcy, half, Math.PI, Math.PI * 1.5); ctx.stroke()
    }
  }
}

/**
 * Draw a human figure on the 2D blueprint as a circle (head) + shoulders icon.
 * Uses the architectural convention of a filled circle with a direction indicator.
 */
function drawHuman2D(
  ctx: CanvasRenderingContext2D,
  human: HumanFigure,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
) {
  const px = toX(human.position.x)
  const py = toY(human.position.y)
  const r = Math.max(4, human.heightM * scale * 0.04)

  const cc = human.clothingColor
  const color = cc ? `rgb(${cc.r},${cc.g},${cc.b})` : "#cc8844"

  // Body circle
  ctx.fillStyle = color
  ctx.globalAlpha = 0.9
  ctx.beginPath()
  ctx.arc(px, py, r * 1.3, 0, Math.PI * 2)
  ctx.fill()

  // Head (smaller, skin-colored)
  const sc = human.skinColor
  ctx.fillStyle = sc ? `rgb(${sc.r},${sc.g},${sc.b})` : "#d4a574"
  ctx.beginPath()
  ctx.arc(px, py - r * 0.5, r * 0.6, 0, Math.PI * 2)
  ctx.fill()
  ctx.globalAlpha = 1

  // Direction indicator
  const rot = ((human.rotationDeg ?? 0) * Math.PI) / 180
  const dx = Math.sin(rot) * r * 1.8
  const dy = -Math.cos(rot) * r * 1.8
  ctx.strokeStyle = color
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.moveTo(px, py)
  ctx.lineTo(px + dx, py + dy)
  ctx.stroke()

  // Name label
  if (human.name && scale > 2) {
    ctx.fillStyle = "#e6dcc8"
    ctx.font = "bold 9px sans-serif"
    ctx.textAlign = "center"
    ctx.fillText(human.name, px, py + r * 2.5)
  }
}
