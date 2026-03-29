import * as THREE from "three";

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export type CSGPrimitive =
  | { primitiveType: "cylinder"; radiusTop: number; radiusBottom: number; height: number; position: Vec3; orientation?: { w: number; x: number; y: number; z: number } }
  | { primitiveType: "sphere"; radius: number; position: Vec3 }
  | { primitiveType: "ellipsoid"; radii: Vec3; position: Vec3; orientation?: { w: number; x: number; y: number; z: number } }
  | { primitiveType: "box"; halfExtents: Vec3; position: Vec3; orientation?: { w: number; x: number; y: number; z: number } }
  | { primitiveType: "capsule"; radius: number; height: number; position: Vec3; orientation?: { w: number; x: number; y: number; z: number } }
  | { primitiveType: "torus"; majorRadius: number; minorRadius: number; position: Vec3; orientation?: { w: number; x: number; y: number; z: number } };

export type CSGNode =
  | { nodeType: "primitive"; primitive: CSGPrimitive }
  | { nodeType: "operation"; operation: "union" | "subtract" | "intersect"; children: CSGNode[] };

function mergeBufferGeometries(geos: THREE.BufferGeometry[]): THREE.BufferGeometry {
  if (geos.length === 0) return new THREE.BufferGeometry();
  if (geos.length === 1) return geos[0]!;

  let totalVerts = 0;
  const nonIndexed: THREE.BufferGeometry[] = [];
  const disposeList: THREE.BufferGeometry[] = [];

  for (const g of geos) {
    const ni = g.index ? g.toNonIndexed() : g;
    if (ni !== g) disposeList.push(ni);
    nonIndexed.push(ni);
    totalVerts += ni.attributes.position!.count;
  }

  const positions = new Float32Array(totalVerts * 3);
  const normals = new Float32Array(totalVerts * 3);
  let offset = 0;

  for (const ni of nonIndexed) {
    const pos = ni.attributes.position as THREE.BufferAttribute;
    const norm = ni.attributes.normal as THREE.BufferAttribute | undefined;
    positions.set(pos.array as Float32Array, offset * 3);
    if (norm) normals.set(norm.array as Float32Array, offset * 3);
    offset += pos.count;
  }

  for (const d of disposeList) d.dispose();

  const merged = new THREE.BufferGeometry();
  merged.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  merged.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  if (normals.every((v) => v === 0)) merged.computeVertexNormals();
  return merged;
}

export function csgPrimitiveToGeometry(prim: CSGPrimitive): THREE.BufferGeometry {
  let geo: THREE.BufferGeometry;

  switch (prim.primitiveType) {
    case "capsule":
      geo = new THREE.CapsuleGeometry(
        prim.radius,
        Math.max(0.01, prim.height - 2 * prim.radius),
        Math.max(4, Math.ceil(prim.radius * 6)),
        Math.max(8, Math.ceil(prim.radius * 10)),
      );
      break;
    case "sphere":
      geo = new THREE.SphereGeometry(prim.radius, 20, 14);
      break;
    case "ellipsoid": {
      const sp = new THREE.SphereGeometry(1, 20, 14);
      sp.scale(prim.radii.x, prim.radii.y, prim.radii.z);
      geo = sp;
      break;
    }
    case "box":
      geo = new THREE.BoxGeometry(
        prim.halfExtents.x * 2,
        prim.halfExtents.y * 2,
        prim.halfExtents.z * 2,
        2, 2, 2,
      );
      break;
    case "cylinder":
      geo = new THREE.CylinderGeometry(
        prim.radiusTop, prim.radiusBottom, prim.height,
        Math.max(12, Math.ceil(Math.max(prim.radiusTop, prim.radiusBottom) * 8)),
        1,
      );
      break;
    case "torus":
      geo = new THREE.TorusGeometry(prim.majorRadius, prim.minorRadius, 14, 24);
      break;
    default:
      geo = new THREE.SphereGeometry(0.5, 10, 8);
  }

  geo.translate(prim.position.x, prim.position.y, prim.position.z);

  if ("orientation" in prim && prim.orientation) {
    const q = new THREE.Quaternion(
      prim.orientation.x, prim.orientation.y, prim.orientation.z, prim.orientation.w,
    );
    geo.applyQuaternion(q);
  }

  return geo;
}

function primitiveLocalPoint(point: THREE.Vector3, prim: CSGPrimitive): THREE.Vector3 {
  const local = point.clone();
  if ("orientation" in prim && prim.orientation) {
    const inv = new THREE.Quaternion(
      prim.orientation.x,
      prim.orientation.y,
      prim.orientation.z,
      prim.orientation.w,
    ).invert();
    local.applyQuaternion(inv);
  }
  local.sub(new THREE.Vector3(prim.position.x, prim.position.y, prim.position.z));
  return local;
}

function pointInPrimitive(point: THREE.Vector3, prim: CSGPrimitive): boolean {
  const p = primitiveLocalPoint(point, prim);
  const eps = 1e-4;

  switch (prim.primitiveType) {
    case "sphere":
      return p.lengthSq() <= (prim.radius * prim.radius) + eps;
    case "ellipsoid": {
      const rx = Math.max(prim.radii.x, eps);
      const ry = Math.max(prim.radii.y, eps);
      const rz = Math.max(prim.radii.z, eps);
      const q = (p.x * p.x) / (rx * rx) + (p.y * p.y) / (ry * ry) + (p.z * p.z) / (rz * rz);
      return q <= 1 + eps;
    }
    case "box":
      return (
        Math.abs(p.x) <= prim.halfExtents.x + eps &&
        Math.abs(p.y) <= prim.halfExtents.y + eps &&
        Math.abs(p.z) <= prim.halfExtents.z + eps
      );
    case "cylinder": {
      const halfH = prim.height * 0.5;
      const radial = Math.sqrt((p.x * p.x) + (p.z * p.z));
      const t = THREE.MathUtils.clamp((p.y + halfH) / Math.max(prim.height, eps), 0, 1);
      const radius = THREE.MathUtils.lerp(prim.radiusBottom, prim.radiusTop, t);
      return Math.abs(p.y) <= halfH + eps && radial <= radius + eps;
    }
    case "capsule": {
      const halfSegment = Math.max(0, (prim.height * 0.5) - prim.radius);
      const cy = THREE.MathUtils.clamp(p.y, -halfSegment, halfSegment);
      const dx = p.x;
      const dy = p.y - cy;
      const dz = p.z;
      return (dx * dx) + (dy * dy) + (dz * dz) <= (prim.radius * prim.radius) + eps;
    }
    case "torus": {
      const radial = Math.sqrt((p.x * p.x) + (p.z * p.z));
      const qx = radial - prim.majorRadius;
      return (qx * qx) + (p.y * p.y) <= (prim.minorRadius * prim.minorRadius) + eps;
    }
    default:
      return false;
  }
}

function pointInCSG(point: THREE.Vector3, node: CSGNode): boolean {
  if (node.nodeType === "primitive") {
    return pointInPrimitive(point, node.primitive);
  }

  const { children } = node;
  if (children.length === 0) return false;
  if (node.operation === "union") return children.some((child) => pointInCSG(point, child));
  if (node.operation === "intersect") return children.every((child) => pointInCSG(point, child));

  const [head, ...tail] = children;
  return pointInCSG(point, head!) && tail.every((child) => !pointInCSG(point, child));
}

function ensureNonIndexedGeometry(geo: THREE.BufferGeometry): THREE.BufferGeometry {
  const next = geo.index ? geo.toNonIndexed() : geo.clone();
  if (!next.getAttribute("normal")) next.computeVertexNormals();
  return next;
}

function filterTriangles(
  geo: THREE.BufferGeometry,
  keepTriangle: (centroid: THREE.Vector3) => boolean,
): THREE.BufferGeometry {
  const source = ensureNonIndexedGeometry(geo);
  const pos = source.getAttribute("position") as THREE.BufferAttribute;
  const norm = source.getAttribute("normal") as THREE.BufferAttribute | undefined;
  const keptPositions: number[] = [];
  const keptNormals: number[] = [];
  const centroid = new THREE.Vector3();

  for (let i = 0; i < pos.count; i += 3) {
    centroid.set(0, 0, 0);
    for (let j = 0; j < 3; j++) {
      centroid.x += pos.getX(i + j);
      centroid.y += pos.getY(i + j);
      centroid.z += pos.getZ(i + j);
    }
    centroid.multiplyScalar(1 / 3);
    if (!keepTriangle(centroid)) continue;

    for (let j = 0; j < 3; j++) {
      keptPositions.push(pos.getX(i + j), pos.getY(i + j), pos.getZ(i + j));
      if (norm) keptNormals.push(norm.getX(i + j), norm.getY(i + j), norm.getZ(i + j));
    }
  }

  source.dispose();

  const filtered = new THREE.BufferGeometry();
  filtered.setAttribute("position", new THREE.Float32BufferAttribute(keptPositions, 3));
  if (keptNormals.length === keptPositions.length) {
    filtered.setAttribute("normal", new THREE.Float32BufferAttribute(keptNormals, 3));
  } else if (keptPositions.length > 0) {
    filtered.computeVertexNormals();
  }
  return filtered;
}

function invertGeometry(geo: THREE.BufferGeometry): THREE.BufferGeometry {
  const source = ensureNonIndexedGeometry(geo);
  const pos = source.getAttribute("position") as THREE.BufferAttribute;
  const norm = source.getAttribute("normal") as THREE.BufferAttribute | undefined;
  const positions: number[] = [];
  const normals: number[] = [];

  for (let i = 0; i < pos.count; i += 3) {
    for (const j of [0, 2, 1]) {
      positions.push(pos.getX(i + j), pos.getY(i + j), pos.getZ(i + j));
      if (norm) normals.push(-norm.getX(i + j), -norm.getY(i + j), -norm.getZ(i + j));
    }
  }

  source.dispose();

  const inverted = new THREE.BufferGeometry();
  inverted.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  if (normals.length === positions.length) {
    inverted.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  } else if (positions.length > 0) {
    inverted.computeVertexNormals();
  }
  return inverted;
}

function subtractCSGGeometries(children: CSGNode[]): THREE.BufferGeometry {
  const [positive, ...subtractors] = children;
  if (!positive) return new THREE.BufferGeometry();

  const positiveGeo = filterTriangles(
    csgTreeToGeometry(positive),
    (centroid) => !subtractors.some((child) => pointInCSG(centroid, child)),
  );

  const cavityGeos = subtractors.map((child, idx) => {
    const cavity = filterTriangles(
      csgTreeToGeometry(child),
      (centroid) =>
        pointInCSG(centroid, positive) &&
        !subtractors.some((other, otherIdx) => otherIdx !== idx && pointInCSG(centroid, other)),
    );
    const inverted = invertGeometry(cavity);
    cavity.dispose();
    return inverted;
  });

  const merged = mergeBufferGeometries(
    [positiveGeo, ...cavityGeos].filter((geo) => geo.getAttribute("position").count > 0),
  );
  positiveGeo.dispose();
  cavityGeos.forEach((geo) => geo.dispose());
  return merged;
}

export function csgTreeToGeometry(node: CSGNode): THREE.BufferGeometry {
  if (node.nodeType === "primitive") {
    return csgPrimitiveToGeometry(node.primitive);
  }

  const childGeos = node.children.map(csgTreeToGeometry);

  if (node.operation === "union" || node.operation === "intersect") {
    const merged = mergeBufferGeometries(childGeos);
    childGeos.forEach((g) => g.dispose());
    return merged;
  }

  childGeos.forEach((g) => g.dispose());
  return subtractCSGGeometries(node.children);
}
