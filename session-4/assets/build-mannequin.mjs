import {
  Document,
  NodeIO,
  Buffer as GltfBuffer,
} from "@gltf-transform/core";

// ─── Bone definitions ───────────────────────────────────────────────
// Each bone: [name, parentIndex, [tx, ty, tz], [sx, sy, sz]]
//   position = LOCAL offset from parent (meters, Y-up, T-pose)
//   size     = box dimensions for the mannequin visual

const BONES = [
  // 0: root
  ["root",           -1,  [0,    0,     0],     [0.01, 0.01, 0.01]],   // invisible root
  // 1: hips
  ["hips",            0,  [0,    1.0,   0],     [0.28, 0.16, 0.18]],
  // 2: spine
  ["spine",           1,  [0,    0.12,  0],     [0.24, 0.16, 0.16]],
  // 3: chest
  ["chest",           2,  [0,    0.16,  0],     [0.30, 0.20, 0.18]],
  // 4: neck
  ["neck",            3,  [0,    0.14,  0],     [0.08, 0.08, 0.08]],
  // 5: head
  ["head",            4,  [0,    0.08,  0],     [0.18, 0.22, 0.20]],

  // Left arm chain
  // 6: clavicleL
  ["clavicleL",       3,  [0.15, 0.10,  0],     [0.12, 0.06, 0.06]],
  // 7: upperArmL
  ["upperArmL",       6,  [0.12, 0,     0],     [0.24, 0.08, 0.08]],
  // 8: lowerArmL
  ["lowerArmL",       7,  [0.26, 0,     0],     [0.22, 0.07, 0.07]],
  // 9: handL
  ["handL",           8,  [0.24, 0,     0],     [0.10, 0.05, 0.08]],

  // Right arm chain
  // 10: clavicleR
  ["clavicleR",       3,  [-0.15, 0.10, 0],     [0.12, 0.06, 0.06]],
  // 11: upperArmR
  ["upperArmR",      10,  [-0.12, 0,    0],     [0.24, 0.08, 0.08]],
  // 12: lowerArmR
  ["lowerArmR",      11,  [-0.26, 0,    0],     [0.22, 0.07, 0.07]],
  // 13: handR
  ["handR",          12,  [-0.24, 0,    0],     [0.10, 0.05, 0.08]],

  // Left leg chain
  // 14: upperLegL
  ["upperLegL",       1,  [0.10, -0.08, 0],     [0.12, 0.40, 0.12]],
  // 15: lowerLegL
  ["lowerLegL",      14,  [0,    -0.42, 0],     [0.10, 0.38, 0.10]],
  // 16: footL
  ["footL",          15,  [0,    -0.40, 0.06],  [0.10, 0.06, 0.22]],
  // 17: toeL
  ["toeL",           16,  [0,     0,    0.12],  [0.08, 0.04, 0.08]],

  // Right leg chain
  // 18: upperLegR
  ["upperLegR",       1,  [-0.10, -0.08, 0],    [0.12, 0.40, 0.12]],
  // 19: lowerLegR
  ["lowerLegR",      18,  [0,     -0.42, 0],    [0.10, 0.38, 0.10]],
  // 20: footR
  ["footR",          19,  [0,     -0.40, 0.06], [0.10, 0.06, 0.22]],
  // 21: toeR
  ["toeR",           20,  [0,      0,    0.12], [0.08, 0.04, 0.08]],
];

// ─── Geometry helpers ───────────────────────────────────────────────

function makeBox(sx, sy, sz) {
  // centered box, returns {positions, normals, indices}
  const hx = sx / 2, hy = sy / 2, hz = sz / 2;

  // 8 corners
  const corners = [
    [-hx, -hy, -hz], [ hx, -hy, -hz], [ hx,  hy, -hz], [-hx,  hy, -hz],
    [-hx, -hy,  hz], [ hx, -hy,  hz], [ hx,  hy,  hz], [-hx,  hy,  hz],
  ];

  // 6 faces: [v0,v1,v2,v3], normal
  const faces = [
    [[1,0,3,2], [ 0, 0,-1]], // back
    [[4,5,6,7], [ 0, 0, 1]], // front
    [[0,4,7,3], [-1, 0, 0]], // left
    [[5,1,2,6], [ 1, 0, 0]], // right
    [[3,7,6,2], [ 0, 1, 0]], // top
    [[0,1,5,4], [ 0,-1, 0]], // bottom
  ];

  const positions = [];
  const normals = [];
  const indices = [];

  for (const [verts, n] of faces) {
    const base = positions.length / 3;
    for (const vi of verts) {
      positions.push(...corners[vi]);
      normals.push(...n);
    }
    indices.push(base, base+1, base+2, base, base+2, base+3);
  }

  return {
    positions: new Float32Array(positions),
    normals:   new Float32Array(normals),
    indices:   new Uint16Array(indices),
  };
}

// ─── Compute world-space position of each bone ──────────────────────

function computeWorldPositions() {
  const world = new Array(BONES.length);
  for (let i = 0; i < BONES.length; i++) {
    const [, parentIdx, local] = BONES[i];
    if (parentIdx < 0) {
      world[i] = [...local];
    } else {
      world[i] = [
        world[parentIdx][0] + local[0],
        world[parentIdx][1] + local[1],
        world[parentIdx][2] + local[2],
      ];
    }
  }
  return world;
}

// ─── Inverse bind matrix (4x4 column-major) ────────────────────────

function inverseBindMatrix(worldPos) {
  // The joint transform is a pure translation, so the inverse is just negated translation.
  // Column-major 4x4 identity with -translation in last column.
  return new Float32Array([
    1, 0, 0, 0,
    0, 1, 0, 0,
    0, 0, 1, 0,
    -worldPos[0], -worldPos[1], -worldPos[2], 1,
  ]);
}

// ─── Build the GLB ──────────────────────────────────────────────────

async function main() {
  const doc = new Document();
  const buffer = doc.createBuffer("buffer");
  const scene = doc.createScene("Scene");

  const worldPositions = computeWorldPositions();

  // --- Create joint nodes ---
  const jointNodes = BONES.map(([name, , local], i) => {
    const node = doc.createNode(name);
    node.setTranslation(local);
    return node;
  });

  // Parent them
  for (let i = 0; i < BONES.length; i++) {
    const parentIdx = BONES[i][1];
    if (parentIdx >= 0) {
      jointNodes[parentIdx].addChild(jointNodes[i]);
    } else {
      scene.addChild(jointNodes[i]);
    }
  }

  // --- Create skin ---
  const skin = doc.createSkin("Armature");

  // Inverse bind matrices
  const ibmData = new Float32Array(BONES.length * 16);
  for (let i = 0; i < BONES.length; i++) {
    const ibm = inverseBindMatrix(worldPositions[i]);
    ibmData.set(ibm, i * 16);
  }

  const ibmAccessor = doc.createAccessor("IBM")
    .setType("MAT4")
    .setArray(ibmData)
    .setBuffer(buffer);

  skin.setInverseBindMatrices(ibmAccessor);
  for (const jn of jointNodes) {
    skin.addJoint(jn);
  }
  skin.setSkeleton(jointNodes[0]);

  // --- Build merged mannequin mesh ---
  // Each bone gets a box positioned at its world location.
  // All boxes merged into one mesh, each vertex assigned to its bone.

  const allPositions = [];
  const allNormals = [];
  const allIndices = [];
  const allJoints = [];   // vec4 (joint indices)
  const allWeights = [];  // vec4 (weights)

  let vertexOffset = 0;

  for (let i = 0; i < BONES.length; i++) {
    const [name, , , size] = BONES[i];
    if (name === "root") continue; // skip invisible root

    const box = makeBox(size[0], size[1], size[2]);
    const wp = worldPositions[i];
    const vertCount = box.positions.length / 3;

    // Offset positions to world space
    for (let v = 0; v < vertCount; v++) {
      allPositions.push(
        box.positions[v * 3 + 0] + wp[0],
        box.positions[v * 3 + 1] + wp[1],
        box.positions[v * 3 + 2] + wp[2],
      );
      allNormals.push(
        box.normals[v * 3 + 0],
        box.normals[v * 3 + 1],
        box.normals[v * 3 + 2],
      );
      // Rigid binding: 100% weight to bone i
      allJoints.push(i, 0, 0, 0);
      allWeights.push(1, 0, 0, 0);
    }

    // Offset indices
    for (const idx of box.indices) {
      allIndices.push(idx + vertexOffset);
    }

    vertexOffset += vertCount;
  }

  // Create accessors
  const posAccessor = doc.createAccessor("POSITION")
    .setType("VEC3")
    .setArray(new Float32Array(allPositions))
    .setBuffer(buffer);

  const normAccessor = doc.createAccessor("NORMAL")
    .setType("VEC3")
    .setArray(new Float32Array(allNormals))
    .setBuffer(buffer);

  const idxAccessor = doc.createAccessor("indices")
    .setType("SCALAR")
    .setArray(new Uint16Array(allIndices))
    .setBuffer(buffer);

  const jointAccessor = doc.createAccessor("JOINTS_0")
    .setType("VEC4")
    .setArray(new Uint16Array(allJoints))
    .setBuffer(buffer);

  const weightAccessor = doc.createAccessor("WEIGHTS_0")
    .setType("VEC4")
    .setArray(new Float32Array(allWeights))
    .setBuffer(buffer);

  // Primitive
  const prim = doc.createPrimitive()
    .setIndices(idxAccessor)
    .setAttribute("POSITION", posAccessor)
    .setAttribute("NORMAL", normAccessor)
    .setAttribute("JOINTS_0", jointAccessor)
    .setAttribute("WEIGHTS_0", weightAccessor);

  // Material — neutral gray
  const mat = doc.createMaterial("Mannequin")
    .setBaseColorFactor([0.6, 0.6, 0.6, 1.0])
    .setRoughnessFactor(0.8)
    .setMetallicFactor(0.1);
  prim.setMaterial(mat);

  // Mesh
  const mesh = doc.createMesh("MannequinBody").addPrimitive(prim);

  // Mesh node
  const meshNode = doc.createNode("MannequinMesh")
    .setMesh(mesh)
    .setSkin(skin);
  scene.addChild(meshNode);

  // --- Write GLB ---
  const io = new NodeIO();
  await io.write("/home/claude/mannequin.glb", doc);

  // --- Validation: log bone hierarchy and stats ---
  console.log(`✓ GLB written`);
  console.log(`  Bones:    ${BONES.length}`);
  console.log(`  Vertices: ${vertexOffset}`);
  console.log(`  Triangles: ${allIndices.length / 3}`);
  console.log(`\nBone hierarchy:`);
  function printTree(idx, indent) {
    console.log(`${indent}${BONES[idx][0]}  @ world [${worldPositions[idx].map(v => v.toFixed(3)).join(", ")}]`);
    for (let c = 0; c < BONES.length; c++) {
      if (BONES[c][1] === idx) printTree(c, indent + "  ");
    }
  }
  printTree(0, "  ");
}

main().catch(err => { console.error(err); process.exit(1); });
