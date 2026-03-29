import { useMemo } from "react"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, PerspectiveCamera } from "@react-three/drei"
import * as THREE from "three"
import type { BuildingModel, Floor, Wall, Space, HumanFigure } from "../types"
import { wallLength, usageColor3D, extractHumans } from "../utils"

interface Props {
  model: BuildingModel
}

export default function ModelView3D({ model }: Props) {
  // Compute center for camera target
  const center = useMemo(() => {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    let maxZ = 0
    for (const floor of model.floors) {
      maxZ = Math.max(maxZ, floor.elevationAboveDatum + floor.floorToFloorHeight)
      for (const sp of floor.spaces ?? []) {
        for (const v of sp.boundary.outer.vertices) {
          minX = Math.min(minX, v.x); minY = Math.min(minY, v.y)
          maxX = Math.max(maxX, v.x); maxY = Math.max(maxY, v.y)
        }
      }
    }
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2
    const size = Math.max(maxX - minX, maxY - minY, maxZ)
    return { x: cx, y: cy, z: maxZ / 2, size }
  }, [model])

  return (
    <Canvas style={{ borderRadius: 8, background: "#0f1a2e" }}>
      <PerspectiveCamera
        makeDefault
        position={[center.x + center.size, center.y - center.size * 0.8, center.size * 1.2]}
        fov={45}
        near={0.1}
        far={500}
      />
      <OrbitControls target={[center.x, center.y, center.z]} />
      <ambientLight intensity={0.5} />
      <directionalLight position={[20, -15, 25]} intensity={0.8} />
      <directionalLight position={[-10, 10, 15]} intensity={0.3} />

      {model.floors.map((floor) => (
        <FloorGroup key={floor.id} floor={floor} />
      ))}

      {/* Human figures from extensions */}
      {extractHumans(model).map((human) => (
        <HumanMesh key={human.id} figure={human} />
      ))}
    </Canvas>
  )
}

function FloorGroup({ floor }: { floor: Floor }) {
  return (
    <group>
      <FloorSlab floor={floor} />
      {(floor.spaces ?? []).map((sp) => (
        <SpaceMesh key={sp.id} space={sp} />
      ))}
      {(floor.walls ?? []).map((wall) => (
        <WallMesh key={wall.id} wall={wall} />
      ))}
      {(floor.fixtures ?? []).map((fx) => (
        <FixtureDot key={fx.id} position={fx.position} />
      ))}
    </group>
  )
}

function FloorSlab({ floor }: { floor: Floor }) {
  // Build a simple slab from the overall bounding box of spaces
  const shape = useMemo(() => {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const sp of floor.spaces ?? []) {
      for (const v of sp.boundary.outer.vertices) {
        minX = Math.min(minX, v.x); minY = Math.min(minY, v.y)
        maxX = Math.max(maxX, v.x); maxY = Math.max(maxY, v.y)
      }
    }
    const w = maxX - minX, d = maxY - minY
    const geo = new THREE.BoxGeometry(w, d, 0.15)
    return { geo, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 }
  }, [floor])

  return (
    <mesh
      geometry={shape.geo}
      position={[shape.cx, shape.cy, floor.elevationAboveDatum - 0.075]}
    >
      <meshStandardMaterial color={0x283a5c} transparent opacity={0.8} />
    </mesh>
  )
}

function SpaceMesh({ space }: { space: Space }) {
  const geo = useMemo(() => {
    const shape = new THREE.Shape()
    const verts = space.boundary.outer.vertices
    shape.moveTo(verts[0].x, verts[0].y)
    for (let i = 1; i < verts.length; i++) shape.lineTo(verts[i].x, verts[i].y)
    shape.closePath()
    return new THREE.ShapeGeometry(shape)
  }, [space])

  return (
    <mesh
      geometry={geo}
      position={[0, 0, space.floorElevation + 0.01]}
      rotation={[0, 0, 0]}
    >
      <meshStandardMaterial
        color={usageColor3D(space.usage)}
        transparent
        opacity={0.6}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

function WallMesh({ wall }: { wall: Wall }) {
  const geo = useMemo(() => {
    const wl = wallLength(wall)
    if (wl < 0.01) return null

    const dx = wall.centerline.end.x - wall.centerline.start.x
    const dy = wall.centerline.end.y - wall.centerline.start.y
    const angle = Math.atan2(dy, dx)

    // Wall body (subtract openings via geometry)
    const shape = new THREE.Shape()
    shape.moveTo(0, 0)
    shape.lineTo(wl, 0)
    shape.lineTo(wl, wall.height)
    shape.lineTo(0, wall.height)
    shape.closePath()

    // Cut openings as holes
    for (const op of wall.openings ?? []) {
      const hole = new THREE.Path()
      const ox = op.offsetAlongWall
      const oy = op.sillHeight
      hole.moveTo(ox, oy)
      hole.lineTo(ox + op.width, oy)
      hole.lineTo(ox + op.width, oy + op.height)
      hole.lineTo(ox, oy + op.height)
      hole.closePath()
      shape.holes.push(hole)
    }

    const extrudeSettings = { depth: wall.thickness, bevelEnabled: false }
    const extGeo = new THREE.ExtrudeGeometry(shape, extrudeSettings)

    // Transform: rotate to align with wall direction, position at start
    const matrix = new THREE.Matrix4()
    // First rotate wall plane from XY to XZ (wall is vertical)
    // Wall shape is in XY, we need it standing up along the wall direction
    matrix.makeRotationX(-Math.PI / 2)

    const m2 = new THREE.Matrix4()
    m2.makeRotationZ(angle)
    matrix.premultiply(m2)

    const m3 = new THREE.Matrix4()
    m3.makeTranslation(wall.centerline.start.x, wall.centerline.start.y, wall.baseElevation)
    matrix.premultiply(m3)

    extGeo.applyMatrix4(matrix)
    return extGeo
  }, [wall])

  if (!geo) return null

  const isExterior = wall.wallType === "load_bearing" || wall.layer === "exterior_envelope"

  return (
    <mesh geometry={geo}>
      <meshStandardMaterial
        color={isExterior ? 0xb0c0d8 : 0x90a8c8}
        transparent
        opacity={0.85}
        side={THREE.DoubleSide}
      />
    </mesh>
  )
}

function FixtureDot({ position }: { position: { x: number; y: number; z: number } }) {
  return (
    <mesh position={[position.x, position.y, position.z + 0.4]}>
      <sphereGeometry args={[0.15, 8, 8]} />
      <meshStandardMaterial color={0x6688bb} />
    </mesh>
  )
}

/**
 * Human figure rendered as a simplified body:
 * - Capsule torso (cylinder + hemisphere caps)
 * - Sphere head
 * - Cylinder legs
 *
 * Positioned using HumanFigure.position (building coords, meters).
 * Proportions derived from HumanBody.proportions.totalHeight.
 */
function HumanMesh({ figure }: { figure: HumanFigure }) {
  const h = figure.heightM
  const headR = h * 0.07
  const torsoH = h * 0.3
  const torsoR = h * 0.09
  const legH = h * 0.47
  const legR = h * 0.04
  const legSpacing = h * 0.06

  const clothColor = figure.clothingColor
    ? (figure.clothingColor.r << 16) | (figure.clothingColor.g << 8) | figure.clothingColor.b
    : 0x4466aa
  const skinColor = figure.skinColor
    ? (figure.skinColor.r << 16) | (figure.skinColor.g << 8) | figure.skinColor.b
    : 0xd4a574

  const px = figure.position.x
  const py = figure.position.y
  const pz = figure.position.z
  const rot = ((figure.rotationDeg ?? 0) * Math.PI) / 180

  const isSeated = figure.pose === "seated"
  const torsoZ = isSeated ? pz + legH * 0.5 : pz + legH
  const headZ = torsoZ + torsoH + headR * 0.8

  return (
    <group position={[px, py, 0]} rotation={[0, 0, rot]}>
      {/* Head */}
      <mesh position={[0, 0, headZ]}>
        <sphereGeometry args={[headR, 12, 12]} />
        <meshStandardMaterial color={skinColor} />
      </mesh>

      {/* Torso */}
      <mesh position={[0, 0, torsoZ + torsoH / 2]}>
        <capsuleGeometry args={[torsoR, torsoH, 6, 12]} />
        <meshStandardMaterial color={clothColor} />
      </mesh>

      {/* Left leg */}
      <mesh position={[-legSpacing, 0, pz + legH / 2]}>
        <capsuleGeometry args={[legR, isSeated ? legH * 0.5 : legH, 4, 8]} />
        <meshStandardMaterial color={0x2a3a5a} />
      </mesh>

      {/* Right leg */}
      <mesh position={[legSpacing, 0, pz + legH / 2]}>
        <capsuleGeometry args={[legR, isSeated ? legH * 0.5 : legH, 4, 8]} />
        <meshStandardMaterial color={0x2a3a5a} />
      </mesh>
    </group>
  )
}
