import { Document, NodeIO } from "@gltf-transform/core";
import { readFileSync } from "node:fs";

// ════════════════════════════════════════════════════════════════════
// build-mannequin v4 — data-driven proportions, capsule limbs,
//                       multi-bone deformation skinning
// ════════════════════════════════════════════════════════════════════

const SKELETON_PATH = process.argv[2] || "./skeleton.json";

// ─── Color palette ──────────────────────────────────────────────────
const PALETTE = {
  armor:     [0.76, 0.68, 0.55, 1.0],
  armorDark: [0.40, 0.38, 0.32, 1.0],
  visor:     [0.15, 0.18, 0.22, 1.0],
  accent:    [0.72, 0.22, 0.18, 1.0],
  belt:      [0.12, 0.12, 0.12, 1.0],
  sole:      [0.30, 0.28, 0.24, 1.0],
  skin:      [0.55, 0.48, 0.40, 1.0],
};

// ─── Boxing actions extracted from session-3/human-controller ───────
// Source: session-3/human-controller/src/components/AIFightFK.jsx
const BOXING_ACTIONS = {
  guard: {
    type: "stance",
    joints: {
      L5S1:{fe:3,aa:0,ie:0}, C7T1:{fe:-5,aa:0,ie:0},
      shoulderR:{fe:25,aa:12,ie:10}, elbowR:{fe:125}, wristR:{fe:-5},
      shoulderL:{fe:35,aa:18,ie:5},  elbowL:{fe:115}, wristL:{fe:-5},
      hipR:{fe:12,aa:-5,ie:0}, kneeR:{fe:18}, ankleR:{fe:5},
      hipL:{fe:8,aa:5,ie:0},  kneeL:{fe:14}, ankleL:{fe:5},
    },
  },
  jab: {
    type: "attack",
    joints: {
      L5S1:{fe:5,aa:0,ie:12},  C7T1:{fe:-3,aa:2,ie:5},
      shoulderL:{fe:85,aa:5,ie:15}, elbowL:{fe:8}, wristL:{fe:-5,aa:0},
      shoulderR:{fe:18,aa:10,ie:5}, elbowR:{fe:128}, wristR:{fe:-5},
      hipR:{fe:15,aa:-3,ie:10}, kneeR:{fe:20}, ankleR:{fe:8},
      hipL:{fe:6,aa:3,ie:0},   kneeL:{fe:14}, ankleL:{fe:5},
    },
  },
  cross: {
    type: "attack",
    joints: {
      L5S1:{fe:8,aa:-2,ie:-18}, C7T1:{fe:-5,aa:-3,ie:-8},
      shoulderR:{fe:90,aa:5,ie:20}, elbowR:{fe:10}, wristR:{fe:-8,aa:-10},
      shoulderL:{fe:15,aa:15,ie:0}, elbowL:{fe:120}, wristL:{fe:-5},
      hipR:{fe:14,aa:-5,ie:20}, kneeR:{fe:22}, ankleR:{fe:10},
      hipL:{fe:8,aa:3,ie:-5},  kneeL:{fe:16}, ankleL:{fe:6},
    },
  },
  hook: {
    type: "attack",
    joints: {
      L5S1:{fe:4,aa:0,ie:25}, C7T1:{fe:-5,aa:3,ie:10},
      shoulderL:{fe:75,aa:-15,ie:45}, elbowL:{fe:92}, wristL:{fe:-10,aa:15},
      shoulderR:{fe:20,aa:10,ie:0}, elbowR:{fe:125}, wristR:{fe:-5},
      hipR:{fe:14,aa:-5,ie:15}, kneeR:{fe:20}, ankleR:{fe:8},
      hipL:{fe:10,aa:5,ie:-10}, kneeL:{fe:16}, ankleL:{fe:6},
    },
  },
  uppercut: {
    type: "attack",
    joints: {
      L5S1:{fe:-5,aa:0,ie:-10}, C7T1:{fe:-8,aa:-2,ie:-5},
      shoulderR:{fe:110,aa:5,ie:10}, elbowR:{fe:65}, wristR:{fe:-15},
      shoulderL:{fe:20,aa:15,ie:0}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:5,aa:-3,ie:8}, kneeR:{fe:8}, ankleR:{fe:12},
      hipL:{fe:6,aa:3,ie:0},  kneeL:{fe:10}, ankleL:{fe:8},
    },
  },
  bodyShot: {
    type: "attack",
    joints: {
      L5S1:{fe:15,aa:-3,ie:-12}, C7T1:{fe:-10,aa:-3,ie:-5},
      shoulderR:{fe:70,aa:-5,ie:10}, elbowR:{fe:25}, wristR:{fe:-10,aa:-5},
      shoulderL:{fe:25,aa:12,ie:0}, elbowL:{fe:115}, wristL:{fe:-5},
      hipR:{fe:20,aa:-5,ie:12}, kneeR:{fe:30}, ankleR:{fe:10},
      hipL:{fe:15,aa:3,ie:0},  kneeL:{fe:25}, ankleL:{fe:8},
    },
  },
  slip: {
    type: "defense",
    joints: {
      L5S1:{fe:8,aa:-8,ie:5}, C7T1:{fe:-5,aa:30,ie:10},
      shoulderR:{fe:22,aa:10,ie:5}, elbowR:{fe:120}, wristR:{fe:-5},
      shoulderL:{fe:28,aa:15,ie:5}, elbowL:{fe:110}, wristL:{fe:-5},
      hipR:{fe:15,aa:-8,ie:0}, kneeR:{fe:35}, ankleR:{fe:10,aa:-15},
      hipL:{fe:12,aa:8,ie:0},  kneeL:{fe:30}, ankleL:{fe:8,aa:10},
    },
  },
  block: {
    type: "defense",
    joints: {
      L5S1:{fe:2,aa:0,ie:0}, C7T1:{fe:-8,aa:0,ie:0},
      shoulderR:{fe:40,aa:15,ie:10}, elbowR:{fe:140}, wristR:{fe:10},
      shoulderL:{fe:45,aa:20,ie:5},  elbowL:{fe:140}, wristL:{fe:10},
      hipR:{fe:10,aa:-5,ie:0}, kneeR:{fe:15}, ankleR:{fe:5},
      hipL:{fe:8,aa:5,ie:0},  kneeL:{fe:12}, ankleL:{fe:5},
    },
  },
  duck: {
    type: "defense",
    joints: {
      L5S1:{fe:20,aa:0,ie:0}, C7T1:{fe:-15,aa:0,ie:0},
      shoulderR:{fe:25,aa:10,ie:5}, elbowR:{fe:120}, wristR:{fe:-5},
      shoulderL:{fe:30,aa:15,ie:5}, elbowL:{fe:115}, wristL:{fe:-5},
      hipR:{fe:55,aa:-5,ie:0}, kneeR:{fe:65}, ankleR:{fe:15},
      hipL:{fe:50,aa:5,ie:0},  kneeL:{fe:60}, ankleL:{fe:12},
    },
  },
  parry: {
    type: "defense",
    joints: {
      L5S1:{fe:3,aa:0,ie:-5}, C7T1:{fe:-5,aa:0,ie:-3},
      shoulderR:{fe:55,aa:10,ie:5}, elbowR:{fe:80}, wristR:{fe:-5,aa:20},
      shoulderL:{fe:32,aa:15,ie:5}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:12,aa:-5,ie:0}, kneeR:{fe:18}, ankleR:{fe:5},
      hipL:{fe:8,aa:5,ie:0},  kneeL:{fe:14}, ankleL:{fe:5},
    },
  },
  advance: {
    type: "movement",
    joints: {
      L5S1:{fe:5,aa:0,ie:0}, C7T1:{fe:-3,aa:0,ie:0},
      shoulderR:{fe:22,aa:10,ie:5}, elbowR:{fe:125}, wristR:{fe:-5},
      shoulderL:{fe:30,aa:15,ie:5}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:5,aa:-3,ie:0},  kneeR:{fe:25}, ankleR:{fe:-15},
      hipL:{fe:25,aa:3,ie:0},  kneeL:{fe:20}, ankleL:{fe:8},
    },
  },
  retreat: {
    type: "movement",
    joints: {
      L5S1:{fe:0,aa:0,ie:0}, C7T1:{fe:-5,aa:0,ie:0},
      shoulderR:{fe:22,aa:10,ie:5}, elbowR:{fe:125}, wristR:{fe:-5},
      shoulderL:{fe:30,aa:15,ie:5}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:-5,aa:-3,ie:0}, kneeR:{fe:10}, ankleR:{fe:5},
      hipL:{fe:10,aa:5,ie:0},  kneeL:{fe:20}, ankleL:{fe:-10},
    },
  },
  kickL: {
    type: "attack",
    joints: {
      L5S1:{fe:5,aa:5,ie:8}, C7T1:{fe:5,aa:0,ie:3},
      shoulderR:{fe:25,aa:12,ie:10}, elbowR:{fe:125}, wristR:{fe:-5},
      shoulderL:{fe:35,aa:18,ie:5},  elbowL:{fe:115}, wristL:{fe:-5},
      hipR:{fe:15,aa:-5,ie:0}, kneeR:{fe:25}, ankleR:{fe:8},
      hipL:{fe:-95,aa:5,ie:0},  kneeL:{fe:-12}, ankleL:{fe:20},
    },
  },
  kickR: {
    type: "attack",
    joints: {
      L5S1:{fe:5,aa:-5,ie:-8}, C7T1:{fe:5,aa:0,ie:-3},
      shoulderR:{fe:35,aa:18,ie:5}, elbowR:{fe:115}, wristR:{fe:-5},
      shoulderL:{fe:25,aa:12,ie:10}, elbowL:{fe:125}, wristL:{fe:-5},
      hipR:{fe:-95,aa:-5,ie:0},  kneeR:{fe:-12}, ankleR:{fe:20},
      hipL:{fe:15,aa:5,ie:0},   kneeL:{fe:25}, ankleL:{fe:8},
    },
  },
};

const BOXING_MOTION = {
  guard:    { offset:[0, 0, 0],           yaw: 0,     duration: 0.8 },
  jab:      { offset:[0.11, 0.01, -0.01], yaw: 0.06,  duration: 0.5 },
  cross:    { offset:[0.16, 0.015,-0.02], yaw: 0.16,  duration: 0.6 },
  hook:     { offset:[0.10, 0.02, -0.12], yaw: 0.22,  duration: 0.7 },
  uppercut: { offset:[0.09,-0.06,-0.015], yaw: 0.10,  duration: 0.7 },
  bodyShot: { offset:[0.12,-0.045,-0.03], yaw: 0.11,  duration: 0.65 },
  slip:     { offset:[-0.03,-0.03,-0.12], yaw:-0.10,  duration: 0.55 },
  block:    { offset:[-0.04, 0.01, 0],    yaw: 0,     duration: 0.55 },
  duck:     { offset:[-0.02,-0.11, 0],    yaw: 0.04,  duration: 0.65 },
  parry:    { offset:[0.025,-0.01,-0.08], yaw: 0.05,  duration: 0.5 },
  advance:  { offset:[0.18,-0.015, 0],    yaw: 0.03,  duration: 0.75 },
  retreat:  { offset:[-0.16,0, 0],        yaw:-0.04,  duration: 0.75 },
  kickL:    { offset:[0.08, 0.02, -0.05], yaw: 0.08,  duration: 0.7 },
  kickR:    { offset:[0.08, 0.02, 0.05],  yaw:-0.08,  duration: 0.7 },
};

// ─── 1b. Digit data extraction (fingers & toes) ───────────────────

/**
 * Extract digit (finger or toe) bone positions, lengths, widths from skeleton.
 * Returns { L: [...digits], R: [...digits] } where each digit has
 * { name, bones: [{ name, x, y, z, length, width, radius }] }
 *
 * For "hand": extracts metacarpals + phalanges for thumb, index, middle, ring, little
 * For "foot": extracts metatarsals + phalanges for hallux, 2nd-5th toes
 */
function extractDigitData(byName, b, type) {
  const sides = { L: [], R: [] };

  if (type === "hand") {
    const fingerDefs = [
      { name: "thumb",  meta: "Metacarpal I",   phalanges: ["Thumb proximal phalanx", "Thumb distal phalanx"] },
      { name: "index",  meta: "Metacarpal II",  phalanges: ["Index proximal phalanx", "Index middle phalanx", "Index distal phalanx"] },
      { name: "middle", meta: "Metacarpal III", phalanges: ["Middle proximal phalanx", "Middle middle phalanx", "Middle distal phalanx"] },
      { name: "ring",   meta: "Metacarpal IV",  phalanges: ["Ring proximal phalanx", "Ring middle phalanx", "Ring distal phalanx"] },
      { name: "little", meta: "Metacarpal V",   phalanges: ["Little proximal phalanx", "Little middle phalanx", "Little distal phalanx"] },
    ];

    for (const side of ["L", "R"]) {
      for (const fd of fingerDefs) {
        const bones = [];
        const meta = b(`${fd.meta} (${side})`);
        bones.push({ label: "meta", x: meta.x, y: meta.y, z: meta.z, length: meta.length, width: meta.width });
        for (let i = 0; i < fd.phalanges.length; i++) {
          const ph = b(`${fd.phalanges[i]} (${side})`);
          const label = i === 0 ? "prox" : i === 1 && fd.phalanges.length === 3 ? "mid" : "dist";
          bones.push({ label, x: ph.x, y: ph.y, z: ph.z, length: ph.length, width: ph.width });
        }
        sides[side].push({ name: fd.name, bones });
      }
    }
  } else {
    // foot — toes
    const toeDefs = [
      { name: "hallux", meta: "Metatarsal I",  phalanges: ["Hallux proximal phalanx", "Hallux distal phalanx"] },
      { name: "toe2",   meta: "Metatarsal II", phalanges: ["Second toe proximal phalanx", "Second toe middle phalanx", "Second toe distal phalanx"] },
      { name: "toe3",   meta: "Metatarsal III",phalanges: ["Third toe proximal phalanx", "Third toe middle phalanx", "Third toe distal phalanx"] },
      { name: "toe4",   meta: "Metatarsal IV", phalanges: ["Fourth toe proximal phalanx", "Fourth toe middle phalanx", "Fourth toe distal phalanx"] },
      { name: "toe5",   meta: "Metatarsal V",  phalanges: ["Fifth toe proximal phalanx", "Fifth toe middle phalanx", "Fifth toe distal phalanx"] },
    ];

    for (const side of ["L", "R"]) {
      for (const td of toeDefs) {
        const bones = [];
        const meta = b(`${td.meta} (${side})`);
        bones.push({ label: "meta", x: meta.x, y: meta.y, z: meta.z, length: meta.length, width: meta.width });
        for (let i = 0; i < td.phalanges.length; i++) {
          const ph = b(`${td.phalanges[i]} (${side})`);
          const label = i === 0 ? "prox" : i === 1 && td.phalanges.length === 3 ? "mid" : "dist";
          bones.push({ label, x: ph.x, y: ph.y, z: ph.z, length: ph.length, width: ph.width });
        }
        sides[side].push({ name: td.name, bones });
      }
    }
  }

  return sides;
}

// ─── 1. Skeleton landmark extraction ────────────────────────────────

function loadSkeleton(path) {
  const data = JSON.parse(readFileSync(path, "utf8"));
  const byName = new Map(data.skeleton.map(b => [b.name, b]));
  return { proportions: data.proportions, byName };
}

function extractLandmarks(skel) {
  const { proportions: p, byName } = skel;

  /** Bone position in metres + bone dimensions */
  const b = (name) => {
    const bone = byName.get(name);
    if (!bone) throw new Error(`Bone "${name}" not found in skeleton`);
    const { x, y, z } = bone.transform.position;
    return {
      x: x / 100, y: y / 100, z: z / 100,
      length: bone.length / 100, width: bone.width / 100, depth: bone.depth / 100,
    };
  };

  /** Optional bone lookup — returns null when absent */
  const bOpt = (name) => byName.has(name) ? b(name) : null;

  const hipL = b("Hip bone (L)"), hipR = b("Hip bone (R)");
  const femurL = b("Femur (L)"),   femurR = b("Femur (R)");
  const tibiaL = b("Tibia (L)"),   tibiaR = b("Tibia (R)");
  const humL = b("Humerus (L)"),   humR = b("Humerus (R)");
  const radL = b("Radius (L)"),    radR = b("Radius (R)");
  const clavL = b("Clavicle (L)"), clavR = b("Clavicle (R)");
  const sternum = b("Sternum");
  const c7 = b("C7 vertebra"),  l1 = b("L1 vertebra");
  const scaphL = b("Scaphoid (L)"), scaphR = b("Scaphoid (R)");
  const calcL = b("Calcaneus (L)"), calcR = b("Calcaneus (R)");

  const shoulderW = p.shoulderWidth / 100;     // m

  // ── Derived soft-tissue radii (proportional to shoulder width) ──
  const thighRTop  = shoulderW * 0.165;  // proximal thigh
  const thighRBot  = shoulderW * 0.120;  // distal (knee)
  const calfRTop   = shoulderW * 0.120;
  const calfRBot   = shoulderW * 0.087;
  const uArmRTop   = shoulderW * 0.110;  // proximal upper arm (shoulder)
  const uArmRBot   = shoulderW * 0.087;  // distal (elbow)
  const fArmRTop   = shoulderW * 0.090;
  const fArmRBot   = shoulderW * 0.070;
  const neckR      = shoulderW * 0.115;

  // ── Torso widths ──
  const chestW   = shoulderW * 0.74;
  const waistW   = shoulderW * 0.55;
  const hipW     = shoulderW * 0.65;
  const chestD   = shoulderW * 0.48;
  const waistD   = shoulderW * 0.39;
  const hipD     = shoulderW * 0.44;

  // ── Key Y positions (metres) ──
  const hipCenterY  = (hipL.y + hipR.y) / 2;
  const spineY      = l1.y;
  const chestY      = sternum.y;
  const neckBaseY   = c7.y;

  // Derive skull base from actual bone positions (atlas → occipital)
  const atlas    = bOpt("C1 vertebra");
  const occip    = bOpt("Occipital bone");
  const headBaseY = atlas  ? atlas.y
                  : occip  ? occip.y - occip.length / 2  // bottom of occipital
                  :          neckBaseY + 0.12;            // fallback: ~12 cm above C7

  const shoulderY   = (humL.y + humR.y) / 2;         // glenohumeral joint height
  const shoulderX   = Math.abs(humL.x);               // lateral offset from centre
  const kneeY       = (tibiaL.y + tibiaR.y) / 2;
  const hipJointX   = Math.abs(femurL.x);
  const hipJointY   = (femurL.y + femurR.y) / 2;

  // Derive ankle Y from talus if available; otherwise fall back to tibia distal end
  const talusL = bOpt("Talus (L)"), talusR = bOpt("Talus (R)");
  const ankleY      = talusL && talusR
                      ? (talusL.y + talusR.y) / 2
                      : kneeY - tibiaL.length;

  const footY       = (calcL.y + calcR.y) / 2;
  const toeY        = 0.005;

  // ── Segment lengths (joint-to-joint distance) ──
  const humerusLen = humL.length;
  const forearmLen = radL.length;
  const femurLen   = hipJointY - kneeY;               // hip joint → knee
  const tibiaLen   = kneeY - ankleY;                   // knee → ankle

  // ── Finger/toe bone data from skeleton ──
  const fingerData = extractDigitData(byName, b, "hand");
  const toeData    = extractDigitData(byName, b, "foot");

  // Wrist reference position in skeleton space (for T-pose remapping)
  const wristRefL = { x: scaphL.x, y: (scaphL.y + b("Lunate (L)").y) / 2, z: scaphL.z };
  const wristRefR = { x: scaphR.x, y: (scaphR.y + b("Lunate (R)").y) / 2, z: scaphR.z };

  return {
    // joint positions (world, metres)
    hipCenterY, spineY, chestY, neckBaseY, headBaseY,
    shoulderY, shoulderX,
    kneeY, ankleY, footY, toeY, hipJointX, hipJointY,
    // segment lengths
    humerusLen, forearmLen, femurLen, tibiaLen,
    // radii
    thighRTop, thighRBot, calfRTop, calfRBot,
    uArmRTop, uArmRBot, fArmRTop, fArmRBot, neckR,
    // torso
    chestW, waistW, hipW, chestD, waistD, hipD,
    // head
    headRx: (p.headCircumference / 100) / (2 * Math.PI),   // ≈ radius from circumference
    headRy: (p.headCircumference / 100) / (2 * Math.PI) * 1.15,
    headRz: (p.headCircumference / 100) / (2 * Math.PI) * 1.05,
    // raw proportions
    totalHeight: p.totalHeight / 100,
    clavicleLen: clavL.length,
    clavicleY: clavL.y,
    clavicleZ: clavL.z,
    // articulated digits
    fingerData, toeData, wristRefL, wristRefR,
    // foot landmark positions for heel/midfoot sizing
    calcL, calcR,
    ankleX: hipJointX,         // lateral offset for foot placement
  };
}

// ─── 2a. Clip registry utility ──────────────────────────────────────

/**
 * Process a declarative clip registry, adding world positions and bone defs.
 * Each clip: { name, parent, mirror?, pos, dims, color, shape? }
 * - mirror: true  → L/R variants (R negates X). Parent gets L/R suffix
 *                    when world[parent+"L"] exists, otherwise shared parent.
 * - mirror: false → single clip, name and parent used as-is.
 */
function addClips(clips, world, defs) {
  for (const clip of clips) {
    const shape = clip.shape || "box";
    if (clip.mirror) {
      const nameL = clip.name + "L", nameR = clip.name + "R";
      const hasLR = world[clip.parent + "L"] !== undefined;
      const parentL = hasLR ? clip.parent + "L" : clip.parent;
      const parentR = hasLR ? clip.parent + "R" : clip.parent;
      world[nameL] = clip.pos;
      world[nameR] = [-clip.pos[0], clip.pos[1], clip.pos[2]];
      defs.push([nameL, parentL, shape, clip.dims, clip.color, null]);
      defs.push([nameR, parentR, shape, clip.dims, clip.color, null]);
    } else {
      world[clip.name] = clip.pos;
      defs.push([clip.name, clip.parent, shape, clip.dims, clip.color, null]);
    }
  }
}

// ─── 2b. Mannequin bone hierarchy (data-driven) ────────────────────

/**
 * Build bone table from anatomical landmarks.
 * Returns array of: [name, parentIdx, [tx,ty,tz], shape, dims, colorKey, blendCfg]
 *   blendCfg: null (rigid) | { childIdx, zone } (smooth)
 */
function buildBoneTable(lm) {
  const {
    hipCenterY, spineY, chestY, neckBaseY, headBaseY,
    shoulderY, shoulderX,
    kneeY, ankleY, footY, toeY, hipJointX, hipJointY,
    humerusLen, forearmLen, femurLen, tibiaLen,
    thighRTop, thighRBot, calfRTop, calfRBot,
    uArmRTop, uArmRBot, fArmRTop, fArmRBot, neckR,
    chestW, waistW, hipW, chestD, waistD, hipD,
    headRx, headRy, headRz,
    clavicleLen, clavicleY, clavicleZ,
    fingerData, toeData, wristRefL, wristRefR,
    calcL, calcR, ankleX,
  } = lm;

  const world = {};
  world.root       = [0, 0, 0];
  world.hips       = [0, hipCenterY, 0];
  world.spine      = [0, spineY, 0];
  world.chest      = [0, chestY, 0];
  world.neck       = [0, neckBaseY, 0];
  world.head       = [0, headBaseY, 0];

  const clavOffX = clavicleLen * 0.45;
  const clavYw   = clavicleY;
  world.clavicleL  = [ clavOffX, clavYw, clavicleZ];
  world.clavicleR  = [-clavOffX, clavYw, clavicleZ];

  world.upperArmL  = [ shoulderX,               shoulderY, 0];
  world.lowerArmL  = [ shoulderX + humerusLen,   shoulderY, 0];
  world.palmL      = [ shoulderX + humerusLen + forearmLen, shoulderY, 0];
  world.upperArmR  = [-shoulderX,               shoulderY, 0];
  world.lowerArmR  = [-shoulderX - humerusLen,   shoulderY, 0];
  world.palmR      = [-shoulderX - humerusLen - forearmLen, shoulderY, 0];

  world.upperLegL  = [ hipJointX, hipJointY, 0];
  world.lowerLegL  = [ hipJointX, kneeY,     0];
  world.upperLegR  = [-hipJointX, hipJointY, 0];
  world.lowerLegR  = [-hipJointX, kneeY,     0];

  // ── Foot world positions (from skeleton calcaneus/talus) ──
  world.heelL      = [ hipJointX,  calcL.y,  calcL.z];
  world.heelR      = [-hipJointX,  calcR.y,  calcR.z];
  world.midfootL   = [ hipJointX,  0.015,    0.05];
  world.midfootR   = [-hipJointX,  0.015,    0.05];

  // ── Finger world positions (anatomical → T-pose) ──
  function fingerWorldPos(bone, side) {
    const wristRef = side === "L" ? wristRefL : wristRefR;
    const palmW    = side === "L" ? world.palmL : world.palmR;
    // Relative to wrist in anatomical pose (metres)
    const dx = bone.x - wristRef.x;
    const dy = bone.y - wristRef.y;
    const dz = bone.z - wristRef.z;
    // Rotate to T-pose: left(sign=1): tpose=(-dy, dx, dz), right(sign=-1): tpose=(dy, -dx, dz)
    if (side === "L") return [palmW[0] - dy, palmW[1] + dx, palmW[2] + dz];
    else              return [palmW[0] + dy, palmW[1] - dx, palmW[2] + dz];
  }

  // ── Toe world positions (no rotation, just use skeleton absolute pos) ──
  function toeWorldPos(bone, side) {
    const sign = side === "L" ? 1 : -1;
    // Use skeleton absolute positions — X is mirrored for left/right
    return [sign * Math.abs(bone.x), bone.y, bone.z];
  }

  // ── Generate finger bone world positions ──
  for (const side of ["L", "R"]) {
    const digits = fingerData[side];
    for (const digit of digits) {
      for (const bone of digit.bones) {
        const key = `${digit.name}_${bone.label}${side}`;
        world[key] = fingerWorldPos(bone, side);
      }
    }
  }

  // ── Generate toe bone world positions ──
  for (const side of ["L", "R"]) {
    const digits = toeData[side];
    for (const digit of digits) {
      for (const bone of digit.bones) {
        const key = `${digit.name}_${bone.label}${side}`;
        world[key] = toeWorldPos(bone, side);
      }
    }
  }

  // ── Compute palm dimensions from metacarpal spread ──
  const metaII_L  = fingerData.L.find(d => d.name === "index").bones[0];
  const metaV_L   = fingerData.L.find(d => d.name === "little").bones[0];
  const palmSpread = Math.abs(metaV_L.x - metaII_L.x);   // lateral spread in metres
  const palmLen    = metaII_L.length * 0.85;                // metacarpal length ≈ palm length
  // In T-pose: spread → Y dimension (vertical fan), length → X dimension (outward)
  const palmH = palmSpread + 0.010;   // height (vertical, was lateral spread)
  const palmW = palmLen;              // width (outward extension)
  const palmD = 0.020;                // depth (thickness)

  // ── Heel / midfoot dimensions ──
  const heelW = calcL.width;
  const heelH = calcL.y + 0.005;     // calcaneus sits slightly above ground
  const heelD = calcL.length * 0.70;
  const midfootW = heelW * 0.85;
  const midfootH = 0.018;
  const midfootD = 0.055;

  // Armor overlays — world positions + bone defs added via clip registry below

  // ── Static bone definitions ──
  const defs = [
    ["root",         null,          "box",        [0.01, 0.01, 0.01],                           "armor",    null],
    ["hips",         "root",        "trapezoid",  [waistW*0.9, hipCenterY-hipJointY+0.06, hipD, hipW], "belt", null],
    ["spine",        "hips",        "trapezoid",  [waistW*0.85, spineY-hipCenterY, waistD, waistW], "skin",   "chest"],
    ["chest",        "spine",       "trapezoid",  [chestW, chestY-spineY+0.04, chestD, waistW*0.95], "armor",  "neck"],
    ["neck",         "chest",       "capsule",    [neckR*0.9, neckR, neckBaseY-chestY-0.06],    "skin",     "head"],
    ["head",         "neck",        "helmet",     [headRx, headRy, headRz],                     "armorDark", null],

    ["clavicleL",    "chest",       "box",        [clavicleLen*0.5, 0.06, 0.08],                "armor",    null],
    ["upperArmL",    "clavicleL",   "capsule",    [uArmRBot, uArmRTop, humerusLen],             "armor",    "lowerArmL"],
    ["lowerArmL",    "upperArmL",   "capsule",    [fArmRBot, fArmRTop, forearmLen],              "armorDark","palmL"],
    ["palmL",        "lowerArmL",   "box",        [palmW, palmD, palmH],                         "skin",     null],

    ["clavicleR",    "chest",       "box",        [clavicleLen*0.5, 0.06, 0.08],                "armor",    null],
    ["upperArmR",    "clavicleR",   "capsule",    [uArmRBot, uArmRTop, humerusLen],             "armor",    "lowerArmR"],
    ["lowerArmR",    "upperArmR",   "capsule",    [fArmRBot, fArmRTop, forearmLen],              "armorDark","palmR"],
    ["palmR",        "lowerArmR",   "box",        [palmW, palmD, palmH],                         "skin",     null],

    ["upperLegL",    "hips",        "capsule",    [thighRTop, thighRBot, femurLen],              "armor",    "lowerLegL"],
    ["lowerLegL",    "upperLegL",   "capsule",    [calfRTop, calfRBot, tibiaLen],                "armorDark","heelL"],
    ["heelL",        "lowerLegL",   "box",        [heelW, heelH, heelD],                         "sole",     null],
    ["midfootL",     "heelL",       "box",        [midfootW, midfootH, midfootD],                 "sole",     null],

    ["upperLegR",    "hips",        "capsule",    [thighRTop, thighRBot, femurLen],              "armor",    "lowerLegR"],
    ["lowerLegR",    "upperLegR",   "capsule",    [calfRTop, calfRBot, tibiaLen],                "armorDark","heelR"],
    ["heelR",        "lowerLegR",   "box",        [heelW, heelH, heelD],                         "sole",     null],
    ["midfootR",     "heelR",       "box",        [midfootW, midfootH, midfootD],                 "sole",     null],

  ];

  // ── Armor clip registry (add new clips here — one entry per piece) ──
  addClips([
    { name: "shoulderPad", parent: "upperArm", mirror: true,
      pos: [world.upperArmL[0] + 0.02, world.upperArmL[1] + 0.06, 0],
      dims: [0.14, 0.05, 0.14], color: "armor" },
    { name: "chestPlate", parent: "chest",
      pos: [0, chestY + 0.04, chestD / 2 + 0.02],
      dims: [chestW * 0.65, 0.16, 0.04], color: "armorDark" },
    { name: "beltFront", parent: "hips",
      pos: [0, hipCenterY + 0.02, hipD / 2 + 0.02],
      dims: [hipW * 0.65, 0.06, 0.04], color: "belt" },
    { name: "pouch", parent: "hips", mirror: true,
      pos: [0.14, hipCenterY, hipD / 2 - 0.01],
      dims: [0.06, 0.08, 0.06], color: "armorDark" },
    { name: "kneePad", parent: "lowerLeg", mirror: true,
      pos: [hipJointX, kneeY + 0.10, 0.05],
      dims: [0.08, 0.10, 0.04], color: "armor" },
    { name: "visor", parent: "head",
      pos: [0, headBaseY - 0.01, headRz + 0.02],
      dims: [headRx * 1.8, 0.06, 0.04], color: "visor" },
    { name: "helmetCrest", parent: "head",
      pos: [0, headBaseY + headRy * 0.8, -0.02],
      dims: [0.04, 0.04, headRz * 1.4], color: "accent" },
  ], world, defs);

  // ── Generate finger bone defs (capsules with smooth skinning) ──
  for (const side of ["L", "R"]) {
    const digits = fingerData[side];
    const parentBone = `palm${side}`;
    for (const digit of digits) {
      const bones = digit.bones;
      for (let i = 0; i < bones.length; i++) {
        const bone = bones[i];
        const boneName = `${digit.name}_${bone.label}${side}`;
        const parent = i === 0 ? parentBone : `${digit.name}_${bones[i - 1].label}${side}`;
        const childName = i < bones.length - 1 ? `${digit.name}_${bones[i + 1].label}${side}` : null;
        const r = bone.width / 2 * 1.3;        // soft-tissue radius (slightly larger than bone)
        const rChild = i < bones.length - 1 ? bones[i + 1].width / 2 * 1.3 : r * 0.85;
        // Capsule dims: [rTop, rBot, bodyH] — rTop is proximal (at this joint), rBot is distal
        // Body height = distance to child bone (computed later from world positions)
        const nextBone = i < bones.length - 1 ? bones[i + 1] : null;
        let bodyH;
        if (nextBone) {
          // Distance between this bone's position and next bone's position in skeleton
          const ddx = nextBone.x - bone.x, ddy = nextBone.y - bone.y, ddz = nextBone.z - bone.z;
          bodyH = Math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz);
        } else {
          bodyH = bone.length * 0.8;           // terminal phalanx: use bone length
        }
        // For fingers, capsules are placed in T-pose; arm capsules get rotated Z90.
        // Finger capsules also need rotation since they extend along ±X, not Y.
        // We'll handle this in the geometry assembly by detecting finger bones.
        defs.push([boneName, parent, "capsule", [r, rChild, bodyH], "skin", childName]);
      }
    }
  }

  // ── Generate toe bone defs (capsules, extend along Z) ──
  for (const side of ["L", "R"]) {
    const digits = toeData[side];
    const parentBone = `midfoot${side}`;
    for (const digit of digits) {
      const bones = digit.bones;
      for (let i = 0; i < bones.length; i++) {
        const bone = bones[i];
        const boneName = `${digit.name}_${bone.label}${side}`;
        const parent = i === 0 ? parentBone : `${digit.name}_${bones[i - 1].label}${side}`;
        const childName = i < bones.length - 1 ? `${digit.name}_${bones[i + 1].label}${side}` : null;
        const r = bone.width / 2 * 1.2;
        const rChild = i < bones.length - 1 ? bones[i + 1].width / 2 * 1.2 : r * 0.80;
        const nextBone = i < bones.length - 1 ? bones[i + 1] : null;
        let bodyH;
        if (nextBone) {
          const ddx = nextBone.x - bone.x, ddy = nextBone.y - bone.y, ddz = nextBone.z - bone.z;
          bodyH = Math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz);
        } else {
          bodyH = bone.length * 0.75;
        }
        defs.push([boneName, parent, "capsule", [r, rChild, bodyH], "sole", childName]);
      }
    }
  }

  // Build name→index map
  const nameToIdx = new Map();
  defs.forEach(([name], i) => nameToIdx.set(name, i));

  // Validate: every parentName and childName must resolve
  for (const [name, parentName, , , , childName] of defs) {
    if (parentName !== null && !nameToIdx.has(parentName))
      throw new Error(`Bone "${name}": parent "${parentName}" not found in bone table`);
    if (childName && !nameToIdx.has(childName))
      throw new Error(`Bone "${name}": blend child "${childName}" not found in bone table`);
  }

  // Reference blend-zone size: 3.5 cm (parametric fraction varies by segment length)
  const BLEND_ZONE_CM = 0.035; // metres

  // Convert to final BONES array
  const BONES = defs.map(([name, parentName, shape, dims, color, childName]) => {
    const parentIdx = parentName === null ? -1 : nameToIdx.get(parentName);
    const wp = world[name];
    const pp = parentName === null ? [0, 0, 0] : world[parentName];
    const local = [wp[0] - pp[0], wp[1] - pp[1], wp[2] - pp[2]];
    const childIdx = childName ? nameToIdx.get(childName) : null;

    let blend = null;
    if (childIdx !== null) {
      const cw = world[childName];
      const dx = cw[0] - wp[0], dy = cw[1] - wp[1], dz = cw[2] - wp[2];
      const segLen = Math.sqrt(dx * dx + dy * dy + dz * dz);
      // Zone as fraction of segment: clamp to [0.08, 0.35] to avoid extremes
      const zone = segLen > 1e-4
        ? Math.max(0.08, Math.min(0.35, BLEND_ZONE_CM / segLen))
        : 0.22;
      blend = { childIdx, zone };
    }
    return [name, parentIdx, local, shape, dims, color, blend];
  });

  return { BONES, world };
}

// ─── 3. Geometry generators ─────────────────────────────────────────

function makeBox(sx, sy, sz) {
  const hx = sx / 2, hy = sy / 2, hz = sz / 2;
  const c = [[-hx,-hy,-hz],[hx,-hy,-hz],[hx,hy,-hz],[-hx,hy,-hz],
             [-hx,-hy, hz],[hx,-hy, hz],[hx,hy, hz],[-hx,hy, hz]];
  const faces = [[[1,0,3,2],[0,0,-1]],[[4,5,6,7],[0,0,1]],[[0,4,7,3],[-1,0,0]],
                 [[5,1,2,6],[1,0,0]],[[3,7,6,2],[0,1,0]],[[0,1,5,4],[0,-1,0]]];
  const faceUVs = [[0,0],[1,0],[1,1],[0,1]]; // per-face quad UVs
  const pos = [], norm = [], uv = [], idx = [];
  for (const [v, n] of faces) {
    const b = pos.length / 3;
    for (let k = 0; k < v.length; k++) { pos.push(...c[v[k]]); norm.push(...n); uv.push(...faceUVs[k]); }
    idx.push(b, b+1, b+2, b, b+2, b+3);
  }
  return { positions: new Float32Array(pos), normals: new Float32Array(norm), uvs: new Float32Array(uv), indices: new Uint16Array(idx) };
}

function makeTrapezoid(topW, h, depth, bottomW) {
  const htw = topW / 2, hbw = bottomW / 2, hh = h / 2, hd = depth / 2;
  const c = [[-hbw,-hh,-hd],[hbw,-hh,-hd],[hbw,-hh,hd],[-hbw,-hh,hd],
             [-htw, hh,-hd],[htw, hh,-hd],[htw, hh,hd],[-htw, hh,hd]];

  // Side-face normals accounting for taper angle
  const sideLen = Math.sqrt(h * h + (hbw - htw) * (hbw - htw)) || 1;
  const sNY = (hbw - htw) / sideLen;   // tilt component
  const sNX = h / sideLen;             // lateral component

  const faces = [
    [[0,1,5,4],[0,  0, -1]],         // back   (flat at z = -hd)
    [[2,3,7,6],[0,  0,  1]],         // front  (flat at z = +hd)
    [[3,0,4,7],[-sNX, sNY, 0]],     // left   (tapered)
    [[1,2,6,5],[ sNX, sNY, 0]],     // right  (tapered)
    [[4,5,6,7],[0,  1,  0]],         // top    (flat)
    [[3,2,1,0],[0, -1,  0]],         // bottom (flat)
  ];

  const faceUVs = [[0,0],[1,0],[1,1],[0,1]];
  const pos = [], norm = [], uv = [], idx = [];
  for (const [v, n] of faces) {
    const b = pos.length / 3;
    for (let k = 0; k < v.length; k++) { pos.push(...c[v[k]]); norm.push(...n); uv.push(...faceUVs[k]); }
    idx.push(b, b+1, b+2, b, b+2, b+3);
  }
  return { positions: new Float32Array(pos), normals: new Float32Array(norm), uvs: new Float32Array(uv), indices: new Uint16Array(idx) };
}

/**
 * Tapered capsule: hemisphere caps + conical body.
 * rTop = radius at +Y end, rBot = radius at -Y end, bodyH = cylinder section height.
 * Total height = bodyH + rTop + rBot.
 */
function makeCapsule(rTop, rBot, bodyH, lonSegs = 12, capRows = 5, bodyRows = 4) {
  const pos = [], norm = [], uv = [], idx = [];
  const halfH = bodyH / 2;

  // Cone normal tilt for body section
  const dr = rBot - rTop;
  const slant = Math.sqrt(bodyH * bodyH + dr * dr) || 1;
  const coneNY = dr / slant;
  const coneNR = bodyH / slant;

  const totalRows = capRows + bodyRows + capRows;

  for (let i = 0; i <= totalRows; i++) {
    let y, r, ny, nr;

    if (i <= capRows) {
      // Bottom hemisphere (south pole → equator)
      const t = i / capRows;
      const a = (1 - t) * Math.PI / 2;
      y  = -halfH - rBot * Math.sin(a);
      r  = rBot * Math.cos(a);
      ny = -Math.sin(a);
      nr = Math.cos(a);
    } else if (i <= capRows + bodyRows) {
      // Tapered body
      const t = (i - capRows) / bodyRows;
      y  = -halfH + bodyH * t;
      r  = rBot + (rTop - rBot) * t;
      ny = coneNY;
      nr = coneNR;
    } else {
      // Top hemisphere (equator → north pole)
      const t = (i - capRows - bodyRows) / capRows;
      const a = t * Math.PI / 2;
      y  = halfH + rTop * Math.sin(a);
      r  = rTop * Math.cos(a);
      ny = Math.sin(a);
      nr = Math.cos(a);
    }

    for (let j = 0; j <= lonSegs; j++) {
      const phi = (j / lonSegs) * Math.PI * 2;
      const cp = Math.cos(phi), sp = Math.sin(phi);
      pos.push(r * cp, y, r * sp);
      norm.push(nr * cp, ny, nr * sp);
      uv.push(j / lonSegs, i / totalRows);   // cylindrical UV
    }
  }

  const vpr = lonSegs + 1;
  for (let i = 0; i < totalRows; i++) {
    for (let j = 0; j < lonSegs; j++) {
      const a = i * vpr + j, b = a + vpr;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }

  return { positions: new Float32Array(pos), normals: new Float32Array(norm), uvs: new Float32Array(uv), indices: new Uint16Array(idx) };
}

function makeHelmet(rx, ry, rz) {
  const lat = 14, lon = 18;
  const pos = [], norm = [], uv = [], idx = [];
  for (let i = 0; i <= lat; i++) {
    const t = (i / lat) * Math.PI, st = Math.sin(t), ct = Math.cos(t);
    for (let j = 0; j <= lon; j++) {
      const p = (j / lon) * Math.PI * 2;
      const sx = st * Math.cos(p), sy = ct, sz = st * Math.sin(p);
      pos.push(sx * rx, sy * ry, sz * rz);
      // Ellipsoid surface normal ∝ (x/rx², y/ry², z/rz²) = (sx/rx, sy/ry, sz/rz)
      const enx = sx / rx, eny = sy / ry, enz = sz / rz;
      const len = Math.sqrt(enx * enx + eny * eny + enz * enz) || 1;
      norm.push(enx / len, eny / len, enz / len);
      uv.push(j / lon, i / lat);   // spherical UV
    }
  }
  for (let i = 0; i < lat; i++) {
    for (let j = 0; j < lon; j++) {
      const a = i * (lon + 1) + j, b = a + lon + 1;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }
  return { positions: new Float32Array(pos), normals: new Float32Array(norm), uvs: new Float32Array(uv), indices: new Uint16Array(idx) };
}

function generateShape(shape, dims) {
  switch (shape) {
    case "box":       return makeBox(dims[0], dims[1], dims[2]);
    case "trapezoid": return makeTrapezoid(dims[0], dims[1], dims[2], dims[3]);
    case "capsule":   return makeCapsule(dims[0], dims[1], dims[2]);
    case "helmet":    return makeHelmet(dims[0], dims[1], dims[2]);
    default:          return makeBox(dims[0], dims[1], dims[2]);
  }
}

// ─── 4. Geometry transforms ─────────────────────────────────────────

/** Rotate capsule from Y-axis to ±X-axis (for T-pose arms and fingers) */
function rotateGeomZ90(geom, sign) {
  const p = geom.positions, n = geom.normals;
  for (let i = 0; i < p.length; i += 3) {
    const x = p[i], y = p[i + 1];
    p[i] = -y * sign; p[i + 1] = x * sign;
    const nx = n[i], ny = n[i + 1];
    n[i] = -ny * sign; n[i + 1] = nx * sign;
  }
}

// ─── 4b. Boxing animation helpers ───────────────────────────────────

const DEG = Math.PI / 180;

function quatFromEulerXYZ(x = 0, y = 0, z = 0) {
  const c1 = Math.cos(x / 2), c2 = Math.cos(y / 2), c3 = Math.cos(z / 2);
  const s1 = Math.sin(x / 2), s2 = Math.sin(y / 2), s3 = Math.sin(z / 2);
  return [
    s1 * c2 * c3 + c1 * s2 * s3,
    c1 * s2 * c3 - s1 * c2 * s3,
    c1 * c2 * s3 + s1 * s2 * c3,
    c1 * c2 * c3 - s1 * s2 * s3,
  ];
}

function quatFromYaw(yaw = 0) {
  return quatFromEulerXYZ(0, yaw, 0);
}

function emptyPoseMap() {
  return new Map();
}

function addPoseEuler(pose, name, x = 0, y = 0, z = 0) {
  const current = pose.get(name) || { x: 0, y: 0, z: 0 };
  current.x += x;
  current.y += y;
  current.z += z;
  pose.set(name, current);
}

function applyBoxingJointPose(pose, jointName, values) {
  let fe = (values.fe || 0) * DEG;
  let aa = (values.aa || 0) * DEG;
  let ie = (values.ie || 0) * DEG;

  if (jointName === "shoulderL" || jointName === "hipL") {
    aa *= -1;
    ie *= -1;
  } else if (jointName === "wristL" || jointName === "ankleL") {
    aa *= -1;
  }

  switch (jointName) {
    case "L5S1":
      addPoseEuler(pose, "hips",  fe * 0.35, ie * 0.55, aa * 0.35);
      addPoseEuler(pose, "spine", fe * 0.40, ie * 0.30, aa * 0.40);
      addPoseEuler(pose, "chest", fe * 0.25, ie * 0.15, aa * 0.25);
      break;
    case "C7T1":
      addPoseEuler(pose, "neck", fe * 0.65, ie * 0.60, aa * 0.75);
      addPoseEuler(pose, "head", fe * 0.25, ie * 0.25, aa * 0.20);
      break;
    case "shoulderL":
      addPoseEuler(pose, "clavicleL", fe * 0.18, ie * 0.15, aa * 0.25);
      addPoseEuler(pose, "upperArmL", fe * 0.82, ie * 0.85, aa * 0.75);
      break;
    case "shoulderR":
      addPoseEuler(pose, "clavicleR", fe * 0.18, ie * 0.15, aa * 0.25);
      addPoseEuler(pose, "upperArmR", fe * 0.82, ie * 0.85, aa * 0.75);
      break;
    case "elbowL":
      addPoseEuler(pose, "lowerArmL", fe * 0.95, 0, 0);
      break;
    case "elbowR":
      addPoseEuler(pose, "lowerArmR", fe * 0.95, 0, 0);
      break;
    case "wristL":
      addPoseEuler(pose, "handL", fe * 0.85, 0, aa * 0.8);
      break;
    case "wristR":
      addPoseEuler(pose, "handR", fe * 0.85, 0, aa * 0.8);
      break;
    case "hipL":
      addPoseEuler(pose, "upperLegL", fe * 0.90, ie * 0.80, aa * 0.65);
      break;
    case "hipR":
      addPoseEuler(pose, "upperLegR", fe * 0.90, ie * 0.80, aa * 0.65);
      break;
    case "kneeL":
      addPoseEuler(pose, "lowerLegL", fe * 0.95, 0, 0);
      break;
    case "kneeR":
      addPoseEuler(pose, "lowerLegR", fe * 0.95, 0, 0);
      break;
    case "ankleL":
      addPoseEuler(pose, "footL", fe * 0.75, 0, aa * 0.75);
      addPoseEuler(pose, "toeL", fe * 0.25, 0, 0);
      break;
    case "ankleR":
      addPoseEuler(pose, "footR", fe * 0.75, 0, aa * 0.75);
      addPoseEuler(pose, "toeR", fe * 0.25, 0, 0);
      break;
  }
}

function poseFromActionJoints(action) {
  const pose = emptyPoseMap();
  for (const [jointName, values] of Object.entries(action.joints || {})) {
    applyBoxingJointPose(pose, jointName, values);
  }
  return pose;
}

function animationTimes(actionName) {
  const motion = BOXING_MOTION[actionName];
  const duration = motion?.duration || 0.6;
  if (actionName === "guard") {
    return new Float32Array([0, duration]);
  }
  const attack = BOXING_ACTIONS[actionName]?.type === "attack";
  const movement = BOXING_ACTIONS[actionName]?.type === "movement";
  if (movement) {
    return new Float32Array([0, duration * 0.45, duration]);
  }
  if (attack) {
    return new Float32Array([0, duration * 0.35, duration * 0.6, duration]);
  }
  return new Float32Array([0, duration * 0.4, duration]);
}

function translationFrames(actionName) {
  const motion = BOXING_MOTION[actionName] || BOXING_MOTION.guard;
  const [x, y, z] = motion.offset;
  if (actionName === "guard") {
    return [0, 0, 0, 0, 0, 0];
  }
  if (BOXING_ACTIONS[actionName]?.type === "movement") {
    return [0, 0, 0, x, y, z, 0, 0, 0];
  }
  if (BOXING_ACTIONS[actionName]?.type === "attack") {
    return [0, 0, 0, x * 0.8, y, z * 0.8, x, y, z, 0, 0, 0];
  }
  return [0, 0, 0, x, y, z, 0, 0, 0];
}

function yawFrames(actionName) {
  const motion = BOXING_MOTION[actionName] || BOXING_MOTION.guard;
  if (actionName === "guard") {
    return [0, 0];
  }
  if (BOXING_ACTIONS[actionName]?.type === "movement") {
    return [0, motion.yaw, 0];
  }
  if (BOXING_ACTIONS[actionName]?.type === "attack") {
    return [0, motion.yaw * 0.75, motion.yaw, 0];
  }
  return [0, motion.yaw, 0];
}

function quaternionFramesFromEulerMaps(keys, poseMaps) {
  const out = [];
  for (const pose of poseMaps) {
    const e = pose.get(keys) || { x: 0, y: 0, z: 0 };
    out.push(...quatFromEulerXYZ(e.x, e.y, e.z));
  }
  return out;
}

/** Rotate capsule from Y-axis to +Z-axis (for toes extending forward) */
function rotateGeomX90(geom) {
  const p = geom.positions, n = geom.normals;
  for (let i = 0; i < p.length; i += 3) {
    const y = p[i + 1], z = p[i + 2];
    p[i + 1] = -z; p[i + 2] = y;
    const ny = n[i + 1], nz = n[i + 2];
    n[i + 1] = -nz; n[i + 2] = ny;
  }
}

// ─── 5. World positions & IBM ───────────────────────────────────────

function computeWorldPositions(BONES) {
  const w = new Array(BONES.length);
  for (let i = 0; i < BONES.length; i++) {
    const [, pi, l] = BONES[i];
    w[i] = pi < 0 ? [...l] : [w[pi][0] + l[0], w[pi][1] + l[1], w[pi][2] + l[2]];
  }
  return w;
}

/**
 * Inverse bind matrix for a bone at world position `wp`.
 *
 * INVARIANT: All bones have identity rotation in bind pose.
 * If any bone were rotated at bind time, this function would produce
 * incorrect skinning — the full 4×4 inverse world transform would
 * be needed instead of a pure translation negation.
 */
function ibm(wp) {
  return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, -wp[0],-wp[1],-wp[2],1]);
}

// ─── 6. Multi-bone skinning ─────────────────────────────────────────

/** Hermite smoothstep for blend transitions */
function smoothstep(t) {
  const c = Math.max(0, Math.min(1, t));
  return c * c * (3 - 2 * c);
}

/**
 * Compute skinning weights for a vertex.
 *
 * @param vWorld  – vertex position in world space [x,y,z]
 * @param boneIdx – index of the bone that owns this vertex
 * @param wp      – world positions array
 * @param BONES   – bone table
 * @returns { joints: [j0,j1,j2,j3], weights: [w0,w1,w2,w3] }
 */
function computeSkinWeights(vWorld, boneIdx, wp, BONES) {
  const [, parentIdx, , , , , blend] = BONES[boneIdx];
  const joints  = [boneIdx, 0, 0, 0];
  const weights = [1, 0, 0, 0];

  if (!blend) return { joints, weights };

  const { childIdx, zone } = blend;
  if (childIdx === null) return { joints, weights };

  // Segment vector: from this bone's joint to the child's joint
  const bx = wp[boneIdx][0], by = wp[boneIdx][1], bz = wp[boneIdx][2];
  const cx = wp[childIdx][0], cy = wp[childIdx][1], cz = wp[childIdx][2];
  const dx = cx - bx, dy = cy - by, dz = cz - bz;
  const segLen = Math.sqrt(dx * dx + dy * dy + dz * dz);
  if (segLen < 1e-6) return { joints, weights };

  // Project vertex onto segment axis → normalized parameter t ∈ [0, 1]
  // t=0 at this bone's joint (proximal), t=1 at child's joint (distal)
  const rx = vWorld[0] - bx, ry = vWorld[1] - by, rz = vWorld[2] - bz;
  const t = Math.max(0, Math.min(1, (rx * dx + ry * dy + rz * dz) / (segLen * segLen)));

  if (t < zone && parentIdx >= 0) {
    // Proximal blend: this bone ↔ parent bone
    const f = smoothstep(t / zone);
    weights[0] = f;
    weights[1] = 1 - f;
    joints[1]  = parentIdx;
  } else if (t > 1 - zone) {
    // Distal blend: this bone ↔ child bone
    const f = smoothstep((t - (1 - zone)) / zone);
    weights[0] = 1 - f;
    weights[1] = f;
    joints[1]  = childIdx;
  }

  return { joints, weights };
}

// ─── 7. Moonwalk animation clip ────────────────────────────────────

/**
 * Add a looping moonwalk animation to the GLB.
 *
 * 9 keyframes over a 1.6 s cycle (two half-strides).
 * Phase A (0.0–0.8 s): right foot slides back, left foot pops.
 * Phase B (0.8–1.6 s): mirror.
 *
 * Animated bones: root (translation), hips (rotation + bob),
 * spine, head, upper/lower arms, upper/lower legs, heels, midfoot.
 */
function addMoonwalkAnimation(doc, buffer, BONES, nodes) {
  const anim = doc.createAnimation("Moonwalk");

  // ── Quaternion helpers ──
  const deg = d => d * Math.PI / 180;

  function qaa(ax, ay, az, angleDeg) {
    const ha = deg(angleDeg) / 2, s = Math.sin(ha);
    return [ax * s, ay * s, az * s, Math.cos(ha)];
  }

  function qmul(a, b) {
    return [
      a[3]*b[0] + a[0]*b[3] + a[1]*b[2] - a[2]*b[1],
      a[3]*b[1] - a[0]*b[2] + a[1]*b[3] + a[2]*b[0],
      a[3]*b[2] + a[0]*b[1] - a[1]*b[0] + a[2]*b[3],
      a[3]*b[3] - a[0]*b[0] - a[1]*b[1] - a[2]*b[2],
    ];
  }

  function qnorm(q) {
    const len = Math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]) || 1;
    return [q[0]/len, q[1]/len, q[2]/len, q[3]/len];
  }

  /** Euler XYZ → quaternion.  q = Qz · Qy · Qx  (extrinsic XYZ). */
  function euler(xd, yd, zd) {
    let q = qaa(1, 0, 0, xd);
    if (yd) q = qmul(qaa(0, 1, 0, yd), q);
    if (zd) q = qmul(qaa(0, 0, 1, zd), q);
    return qnorm(q);
  }

  // ── Name → index ──
  const nameIdx = new Map();
  BONES.forEach(([name], i) => nameIdx.set(name, i));

  // ── Shared keyframe times (9 frames, 0.2 s apart) ──
  const times = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6];
  const K = times.length;
  const timeAcc = doc.createAccessor("mw_time")
    .setType("SCALAR").setArray(new Float32Array(times)).setBuffer(buffer);

  // ── Channel factories ──

  function addRot(name, quats) {
    if (!nameIdx.has(name)) return;
    const arr = new Float32Array(K * 4);
    quats.forEach((q, i) => arr.set(q, i * 4));
    const samp = doc.createAnimationSampler()
      .setInput(timeAcc)
      .setOutput(doc.createAccessor(`mw_r_${name}`).setType("VEC4").setArray(arr).setBuffer(buffer))
      .setInterpolation("LINEAR");
    const chan = doc.createAnimationChannel()
      .setTargetNode(nodes[nameIdx.get(name)])
      .setTargetPath("rotation").setSampler(samp);
    anim.addSampler(samp);
    anim.addChannel(chan);
  }

  /** Translation channel — offsets are ADDED to the bone's bind-pose local translation. */
  function addTrans(name, offsets) {
    if (!nameIdx.has(name)) return;
    const base = BONES[nameIdx.get(name)][2];
    const arr  = new Float32Array(K * 3);
    offsets.forEach(([dx, dy, dz], i) => {
      arr[i * 3]     = base[0] + dx;
      arr[i * 3 + 1] = base[1] + dy;
      arr[i * 3 + 2] = base[2] + dz;
    });
    const samp = doc.createAnimationSampler()
      .setInput(timeAcc)
      .setOutput(doc.createAccessor(`mw_t_${name}`).setType("VEC3").setArray(arr).setBuffer(buffer))
      .setInterpolation("LINEAR");
    const chan = doc.createAnimationChannel()
      .setTargetNode(nodes[nameIdx.get(name)])
      .setTargetPath("translation").setSampler(samp);
    anim.addSampler(samp);
    anim.addChannel(chan);
  }

  // ════════════════════════════════════════════════════════════════
  // K E Y F R A M E   D A T A
  // indices:              0     1     2     3     4     5     6     7     8
  // times (s):          0.0   0.2   0.4   0.6   0.8   1.0   1.2   1.4   1.6
  // Phase A (R slides): ├─────────────────────────┤
  // Phase B (L slides):                           ├─────────────────────────┤
  // ════════════════════════════════════════════════════════════════

  // ── Root: backward glide (-Z) ──
  const stride = 0.60;                                  // metres per cycle
  addTrans("root", times.map(t => [0, 0, -(t / 1.6) * stride]));

  // ── Hips: Y swagger + Z tilt + vertical bob ──
  addRot("hips", [
    euler(0,  0,  0),
    euler(0,  2, -1),
    euler(0,  4, -2),
    euler(0,  2, -1),
    euler(0,  0,  0),
    euler(0, -2,  1),
    euler(0, -4,  2),
    euler(0, -2,  1),
    euler(0,  0,  0),
  ]);
  addTrans("hips", [
    [0, 0,     0], [0, 0.003, 0], [0, 0.006, 0], [0, 0.003, 0],
    [0, 0,     0], [0, 0.003, 0], [0, 0.006, 0], [0, 0.003, 0],
    [0, 0,     0],
  ]);

  // ── Spine: counter-swagger + slight forward lean ──
  addRot("spine", [
    euler(3,  0, 0), euler(3, -1, 0), euler(3, -2, 0), euler(3, -1, 0),
    euler(3,  0, 0), euler(3,  1, 0), euler(3,  2, 0), euler(3,  1, 0),
    euler(3,  0, 0),
  ]);

  // ── Head: subtle counter to keep gaze stable ──
  addRot("head", [
    euler(-3, 0, 0), euler(-3, 1, 0), euler(-3, 2, 0), euler(-3, 1, 0),
    euler(-3, 0, 0), euler(-3,-1, 0), euler(-3,-2, 0), euler(-3,-1, 0),
    euler(-3, 0, 0),
  ]);

  // ── Upper arms: bring down from T-pose (Z) + swing (X) ──
  //   Left arm:  Z = −75° constant, X oscillates
  //   Right arm: Z = +75° constant, opposite phase
  addRot("upperArmL", [
    euler( 5, 0, -75), euler(-3, 0, -75), euler(-15, 0, -75), euler(-8, 0, -75),
    euler( 5, 0, -75), euler(12, 0, -75), euler( 18, 0, -75), euler(12, 0, -75),
    euler( 5, 0, -75),
  ]);
  addRot("upperArmR", [
    euler( 5, 0, 75), euler(12, 0, 75), euler( 18, 0, 75), euler(12, 0, 75),
    euler( 5, 0, 75), euler(-3, 0, 75), euler(-15, 0, 75), euler(-8, 0, 75),
    euler( 5, 0, 75),
  ]);

  // ── Lower arms: constant elbow bend ──
  addRot("lowerArmL", Array(K).fill(euler(0, 0, -25)));
  addRot("lowerArmR", Array(K).fill(euler(0, 0,  25)));

  // ── Upper legs (hip flexion +X = forward) ──
  //   R: sliding 0→0.8 (flex→ext), non-sliding 0.8→1.6
  //   L: shifted half-cycle
  addRot("upperLegR", [15, 8, 2, -5, -10, -2, 5, 10, 15].map(x => euler(x, 0, 0)));
  addRot("upperLegL", [-10, -2, 5, 10, 15, 8, 2, -5, -10].map(x => euler(x, 0, 0)));

  // ── Lower legs (knee flexion +X = bend) ──
  //   Sliding phase: nearly straight ≈ 3°
  //   Pop phase:     bent ≈ 30° (heel lifts off ground)
  addRot("lowerLegR", [5, 3, 3, 4, 8, 18, 30, 20, 5].map(x => euler(x, 0, 0)));
  addRot("lowerLegL", [8, 18, 30, 20, 5, 3, 3, 4, 8].map(x => euler(x, 0, 0)));

  // ── Heels (ankle plantarflexion +X = toes down / heel up) ──
  //   Sliding: flat (0°)
  //   Pop:     plantarflexed ≈ 20° (on ball of foot)
  addRot("heelR", [0, 0, 0, 0, 0, 10, 20, 10, 0].map(x => euler(x, 0, 0)));
  addRot("heelL", [0, 10, 20, 10, 0, 0, 0, 0, 0].map(x => euler(x, 0, 0)));

  // ── Midfoot: counter-rotate slightly to keep toe contact plausible ──
  addRot("midfootR", [0, 0, 0, 0, 0, -5, -10, -5, 0].map(x => euler(x, 0, 0)));
  addRot("midfootL", [0, -5, -10, -5, 0, 0, 0, 0, 0].map(x => euler(x, 0, 0)));

  // ── Palms: slight wrist flexion for style (constant) ──
  addRot("palmL", Array(K).fill(euler(0, 0, -10)));
  addRot("palmR", Array(K).fill(euler(0, 0,  10)));

  return anim;
}

// ─── 7b. KO animation clip ──────────────────────────────────────────

/**
 * Add a knockout animation: stagger → buckle → collapse to floor.
 *
 * 6 keyframes over 1.4 s:
 *   0.0 s  guard pose (standing)
 *   0.2 s  head snap back, stagger
 *   0.5 s  knees buckle, torso folds
 *   0.8 s  falling sideways
 *   1.1 s  hitting the ground
 *   1.4 s  lying flat on back
 */
function addKOAnimation(doc, buffer, BONES, nodes) {
  const anim = doc.createAnimation("ko");

  const deg = d => d * Math.PI / 180;

  function qaa(ax, ay, az, angleDeg) {
    const ha = deg(angleDeg) / 2, s = Math.sin(ha);
    return [ax * s, ay * s, az * s, Math.cos(ha)];
  }

  function qmul(a, b) {
    return [
      a[3]*b[0] + a[0]*b[3] + a[1]*b[2] - a[2]*b[1],
      a[3]*b[1] - a[0]*b[2] + a[1]*b[3] + a[2]*b[0],
      a[3]*b[2] + a[0]*b[1] - a[1]*b[0] + a[2]*b[3],
      a[3]*b[3] - a[0]*b[0] - a[1]*b[1] - a[2]*b[2],
    ];
  }

  function qnorm(q) {
    const len = Math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]) || 1;
    return [q[0]/len, q[1]/len, q[2]/len, q[3]/len];
  }

  function euler(xd, yd, zd) {
    let q = qaa(1, 0, 0, xd);
    if (yd) q = qmul(qaa(0, 1, 0, yd), q);
    if (zd) q = qmul(qaa(0, 0, 1, zd), q);
    return qnorm(q);
  }

  const nameIdx = new Map();
  BONES.forEach(([name], i) => nameIdx.set(name, i));

  const times = [0.0, 0.2, 0.5, 0.8, 1.1, 1.4];
  const K = times.length;
  const timeAcc = doc.createAccessor("ko_time")
    .setType("SCALAR").setArray(new Float32Array(times)).setBuffer(buffer);

  function addRot(name, quats) {
    if (!nameIdx.has(name)) return;
    const arr = new Float32Array(K * 4);
    quats.forEach((q, i) => arr.set(q, i * 4));
    const samp = doc.createAnimationSampler()
      .setInput(timeAcc)
      .setOutput(doc.createAccessor(`ko_r_${name}`).setType("VEC4").setArray(arr).setBuffer(buffer))
      .setInterpolation("LINEAR");
    const chan = doc.createAnimationChannel()
      .setTargetNode(nodes[nameIdx.get(name)])
      .setTargetPath("rotation").setSampler(samp);
    anim.addSampler(samp);
    anim.addChannel(chan);
  }

  function addTrans(name, offsets) {
    if (!nameIdx.has(name)) return;
    const base = BONES[nameIdx.get(name)][2];
    const arr = new Float32Array(K * 3);
    offsets.forEach(([dx, dy, dz], i) => {
      arr[i * 3]     = base[0] + dx;
      arr[i * 3 + 1] = base[1] + dy;
      arr[i * 3 + 2] = base[2] + dz;
    });
    const samp = doc.createAnimationSampler()
      .setInput(timeAcc)
      .setOutput(doc.createAccessor(`ko_t_${name}`).setType("VEC3").setArray(arr).setBuffer(buffer))
      .setInterpolation("LINEAR");
    const chan = doc.createAnimationChannel()
      .setTargetNode(nodes[nameIdx.get(name)])
      .setTargetPath("translation").setSampler(samp);
    anim.addSampler(samp);
    anim.addChannel(chan);
  }

  // ════════════════════════════════════════════════════════════════
  // K E Y F R A M E S
  //  idx:    0       1       2       3       4       5
  //  time:  0.0     0.2     0.5     0.8     1.1     1.4
  //         stand   snap    buckle  fall    impact  floor
  // ════════════════════════════════════════════════════════════════

  // ── Root: drop to the ground ──
  addTrans("root", [
    [0, 0,    0],      // standing
    [0, 0,    0.03],   // stagger back slightly
    [0, -0.15, 0.06],  // knees buckling, dropping
    [0, -0.45, 0.10],  // falling
    [0, -0.75, 0.14],  // impact
    [0, -0.82, 0.16],  // lying flat
  ]);

  // ── Hips: tilt back then sideways ──
  addRot("hips", [
    euler(0,  0,  0),      // standing
    euler(-8, 0,  3),      // snap back
    euler(-20, 5, 10),     // buckle back
    euler(-45, 8, 25),     // falling sideways
    euler(-70, 5, 35),     // impact
    euler(-85, 3, 40),     // lying on back
  ]);

  // ── Spine: fold forward then flop ──
  addRot("spine", [
    euler(3,  0, 0),
    euler(10, 0, 2),
    euler(15, -3, 5),
    euler(8,  -5, 8),
    euler(-5, -3, 5),
    euler(-10, 0, 3),
  ]);

  // ── Head: snap back hard, then loll ──
  addRot("head", [
    euler(-3, 0, 0),
    euler(-25, 5, 0),     // head snaps back from hit
    euler(-15, 10, -5),
    euler(-10, 15, -10),
    euler(5,  10, -15),   // head lolls on impact
    euler(10, 8, -12),    // resting
  ]);

  // ── Upper arms: flail then go limp ──
  addRot("upperArmL", [
    euler(5, 0, -75),
    euler(-10, 0, -60),    // arms drop from guard
    euler(-20, -10, -40),  // arms flailing
    euler(-15, -15, -25),
    euler(5,  -10, -15),   // arm hits ground
    euler(10, -5, -10),    // limp on floor
  ]);
  addRot("upperArmR", [
    euler(5, 0, 75),
    euler(-10, 0, 60),
    euler(-20, 10, 40),
    euler(-15, 15, 25),
    euler(5,  10, 15),
    euler(10, 5, 10),
  ]);

  // ── Lower arms: go limp ──
  addRot("lowerArmL", [
    euler(0, 0, -25),
    euler(0, 0, -20),
    euler(0, 0, -10),
    euler(0, 0, -5),
    euler(0, 0, 0),
    euler(0, 0, 0),
  ]);
  addRot("lowerArmR", [
    euler(0, 0, 25),
    euler(0, 0, 20),
    euler(0, 0, 10),
    euler(0, 0, 5),
    euler(0, 0, 0),
    euler(0, 0, 0),
  ]);

  // ── Upper legs: buckle then splay ──
  addRot("upperLegL", [
    euler(0, 0, 0),
    euler(5, 0, 3),
    euler(35, 0, 8),       // knees buckle
    euler(20, -5, 15),
    euler(5,  -8, 20),     // legs splay on ground
    euler(0,  -5, 18),
  ]);
  addRot("upperLegR", [
    euler(0, 0, 0),
    euler(5, 0, -3),
    euler(35, 0, -8),
    euler(20, 5, -15),
    euler(5,  8, -20),
    euler(0,  5, -18),
  ]);

  // ── Lower legs: fold then straighten ──
  addRot("lowerLegL", [
    euler(0, 0, 0),
    euler(8, 0, 0),
    euler(50, 0, 0),       // knees deeply bent
    euler(35, 0, 0),
    euler(10, 0, 0),       // legs unfold on ground
    euler(5, 0, 0),
  ]);
  addRot("lowerLegR", [
    euler(0, 0, 0),
    euler(8, 0, 0),
    euler(50, 0, 0),
    euler(35, 0, 0),
    euler(10, 0, 0),
    euler(5, 0, 0),
  ]);

  // ── Heels: plantarflex during buckle ──
  addRot("heelL", [
    euler(0, 0, 0),
    euler(5, 0, 0),
    euler(20, 0, 0),
    euler(10, 0, 0),
    euler(0, 0, 0),
    euler(0, 0, 0),
  ]);
  addRot("heelR", [
    euler(0, 0, 0),
    euler(5, 0, 0),
    euler(20, 0, 0),
    euler(10, 0, 0),
    euler(0, 0, 0),
    euler(0, 0, 0),
  ]);

  // ── Palms: go limp ──
  addRot("palmL", Array(K).fill(euler(0, 0, 0)));
  addRot("palmR", Array(K).fill(euler(0, 0, 0)));

  return anim;
}

// ─── 8. Build GLB ───────────────────────────────────────────────────

async function main() {
  console.log(`Loading skeleton from ${SKELETON_PATH}…`);
  const skel = loadSkeleton(SKELETON_PATH);
  const lm   = extractLandmarks(skel);
  const { BONES, world } = buildBoneTable(lm);

  const doc    = new Document();
  const buffer = doc.createBuffer("buffer");
  const scene  = doc.createScene("Scene");
  const wp     = computeWorldPositions(BONES);

  // Bones that need rotation for T-pose geometry alignment
  // Arms + fingers: capsule Y-axis → ±X-axis (Z-90 rotation)
  // Toes: capsule Y-axis → +Z-axis (X-90 rotation)
  const isLeftArmOrFinger  = (name) => name === "upperArmL" || name === "lowerArmL" || name.endsWith("L") && /^(thumb|index|middle|ring|little)_/.test(name);
  const isRightArmOrFinger = (name) => name === "upperArmR" || name === "lowerArmR" || name.endsWith("R") && /^(thumb|index|middle|ring|little)_/.test(name);
  const isToeBone          = (name) => /^(hallux|toe[2-5])_/.test(name);

  // ── Nodes ──
  const nodes = BONES.map(([name, , local]) => {
    const n = doc.createNode(name);
    n.setTranslation(local);
    return n;
  });
  const nodeByName = Object.fromEntries(BONES.map(([name], i) => [name, nodes[i]]));
  for (let i = 0; i < BONES.length; i++) {
    const pi = BONES[i][1];
    if (pi >= 0) nodes[pi].addChild(nodes[i]);
    else scene.addChild(nodes[i]);
  }

  // ── Skin ──
  const skin    = doc.createSkin("Armature");
  const ibmArr  = new Float32Array(BONES.length * 16);
  for (let i = 0; i < BONES.length; i++) ibmArr.set(ibm(wp[i]), i * 16);
  skin.setInverseBindMatrices(
    doc.createAccessor("IBM").setType("MAT4").setArray(ibmArr).setBuffer(buffer)
  );
  for (const n of nodes) skin.addJoint(n);
  skin.setSkeleton(nodes[0]);

  // ── Boxing animations ──
  const guardPose = poseFromActionJoints(BOXING_ACTIONS.guard);
  const animatedBoneNames = [
    "hips", "spine", "chest", "neck", "head",
    "clavicleL", "upperArmL", "lowerArmL", "handL",
    "clavicleR", "upperArmR", "lowerArmR", "handR",
    "upperLegL", "lowerLegL", "footL", "toeL",
    "upperLegR", "lowerLegR", "footR", "toeR",
  ];

  for (const [actionName, action] of Object.entries(BOXING_ACTIONS)) {
    const animation = doc.createAnimation(actionName);
    const times = animationTimes(actionName);
    const timeAccessor = doc.createAccessor(`${actionName}_times`)
      .setType("SCALAR")
      .setArray(times)
      .setBuffer(buffer);

    let poseFrames;
    if (actionName === "guard") {
      poseFrames = [guardPose, guardPose];
    } else {
      const actionPose = poseFromActionJoints(action);
      if (action.type === "movement") {
        poseFrames = [guardPose, actionPose, guardPose];
      } else if (action.type === "attack") {
        poseFrames = [guardPose, actionPose, actionPose, guardPose];
      } else {
        poseFrames = [guardPose, actionPose, guardPose];
      }
    }

    for (const boneName of animatedBoneNames) {
      const node = nodeByName[boneName];
      if (!node) continue;

      const rotations = quaternionFramesFromEulerMaps(boneName, poseFrames);
      const rotAccessor = doc.createAccessor(`${actionName}_${boneName}_rot`)
        .setType("VEC4")
        .setArray(new Float32Array(rotations))
        .setBuffer(buffer);

      const sampler = doc.createAnimationSampler(`${actionName}_${boneName}_sampler`)
        .setInput(timeAccessor)
        .setOutput(rotAccessor)
        .setInterpolation("LINEAR");
      const channel = doc.createAnimationChannel(`${actionName}_${boneName}_channel`)
        .setTargetNode(node)
        .setTargetPath("rotation")
        .setSampler(sampler);

      animation.addSampler(sampler).addChannel(channel);
    }

    const translationValues = translationFrames(actionName);
    const translationAccessor = doc.createAccessor(`${actionName}_root_translation`)
      .setType("VEC3")
      .setArray(new Float32Array(translationValues))
      .setBuffer(buffer);
    const translationSampler = doc.createAnimationSampler(`${actionName}_root_translation_sampler`)
      .setInput(timeAccessor)
      .setOutput(translationAccessor)
      .setInterpolation("LINEAR");
    const translationChannel = doc.createAnimationChannel(`${actionName}_root_translation_channel`)
      .setTargetNode(nodeByName.root)
      .setTargetPath("translation")
      .setSampler(translationSampler);
    animation.addSampler(translationSampler).addChannel(translationChannel);

    const yawValues = yawFrames(actionName).flatMap((yaw) => quatFromYaw(yaw));
    const yawAccessor = doc.createAccessor(`${actionName}_root_rotation`)
      .setType("VEC4")
      .setArray(new Float32Array(yawValues))
      .setBuffer(buffer);
    const yawSampler = doc.createAnimationSampler(`${actionName}_root_rotation_sampler`)
      .setInput(timeAccessor)
      .setOutput(yawAccessor)
      .setInterpolation("LINEAR");
    const yawChannel = doc.createAnimationChannel(`${actionName}_root_rotation_channel`)
      .setTargetNode(nodeByName.root)
      .setTargetPath("rotation")
      .setSampler(yawSampler);
    animation.addSampler(yawSampler).addChannel(yawChannel);
  }

  // ── Materials ──
  const mats = {};
  for (const [k, c] of Object.entries(PALETTE)) {
    mats[k] = doc.createMaterial(k).setBaseColorFactor(c)
      .setRoughnessFactor(k === "visor" ? 0.2 : 0.75)
      .setMetallicFactor(k === "visor" ? 0.8 : k === "armor" ? 0.3 : 0.1);
  }

  // ── Geometry assembly (grouped by material) ──
  const groups = {};
  for (const k of Object.keys(PALETTE)) groups[k] = { p: [], n: [], uv: [], i: [], j: [], w: [], vc: 0 };

  for (let i = 0; i < BONES.length; i++) {
    const [name, , , shape, dims, ck, blend] = BONES[i];
    if (name === "root") continue;

    const geom = generateShape(shape, dims);

    // Rotate capsules to match T-pose orientation
    if (shape === "capsule") {
      if (isLeftArmOrFinger(name))       rotateGeomZ90(geom, 1);   // Y → +X
      else if (isRightArmOrFinger(name)) rotateGeomZ90(geom, -1);  // Y → −X
      else if (isToeBone(name))          rotateGeomX90(geom);       // Y → +Z
    }

    // Compute geometry centre offset for capsules.
    // Non-terminal: centre between this joint and child's joint.
    // Terminal (no child): extend outward from joint along parent→bone direction.
    let offX = 0, offY = 0, offZ = 0;
    if (shape === "capsule" && blend && blend.childIdx !== null) {
      const ci = blend.childIdx;
      offX = (wp[ci][0] - wp[i][0]) / 2;
      offY = (wp[ci][1] - wp[i][1]) / 2;
      offZ = (wp[ci][2] - wp[i][2]) / 2;
    } else if (shape === "capsule" && !blend) {
      // Terminal capsule: offset half-length along parent→bone direction
      const pi = BONES[i][1];
      if (pi >= 0) {
        const ddx = wp[i][0] - wp[pi][0], ddy = wp[i][1] - wp[pi][1], ddz = wp[i][2] - wp[pi][2];
        const dist = Math.sqrt(ddx * ddx + ddy * ddy + ddz * ddz) || 1;
        const halfLen = dims[2] / 2;  // bodyH / 2
        offX = (ddx / dist) * halfLen;
        offY = (ddy / dist) * halfLen;
        offZ = (ddz / dist) * halfLen;
      }
    }

    const g  = groups[ck];
    const vc = geom.positions.length / 3;
    const bv = g.vc;

    for (let v = 0; v < vc; v++) {
      // World-space vertex position
      const vx = geom.positions[v * 3]     + wp[i][0] + offX;
      const vy = geom.positions[v * 3 + 1] + wp[i][1] + offY;
      const vz = geom.positions[v * 3 + 2] + wp[i][2] + offZ;
      g.p.push(vx, vy, vz);
      g.n.push(geom.normals[v * 3], geom.normals[v * 3 + 1], geom.normals[v * 3 + 2]);
      g.uv.push(geom.uvs[v * 2], geom.uvs[v * 2 + 1]);

      // Skinning weights
      const { joints, weights } = computeSkinWeights([vx, vy, vz], i, wp, BONES);
      g.j.push(...joints);
      g.w.push(...weights);
    }

    for (const ix of geom.indices) g.i.push(ix + bv);
    g.vc += vc;
  }

  // ── Mesh ──
  const mesh = doc.createMesh("MannequinBody");
  let tv = 0, tt = 0;
  for (const [k, g] of Object.entries(groups)) {
    if (!g.vc) continue;
    // Fix #7: Use Uint32Array if vertex count exceeds Uint16 range
    const IndexArray = g.vc > 65535 ? Uint32Array : Uint16Array;
    const prim = doc.createPrimitive()
      .setIndices(doc.createAccessor(`idx_${k}`).setType("SCALAR").setArray(new IndexArray(g.i)).setBuffer(buffer))
      .setAttribute("POSITION",    doc.createAccessor(`pos_${k}`).setType("VEC3").setArray(new Float32Array(g.p)).setBuffer(buffer))
      .setAttribute("NORMAL",      doc.createAccessor(`nrm_${k}`).setType("VEC3").setArray(new Float32Array(g.n)).setBuffer(buffer))
      .setAttribute("TEXCOORD_0",  doc.createAccessor(`uv_${k}` ).setType("VEC2").setArray(new Float32Array(g.uv)).setBuffer(buffer))
      .setAttribute("JOINTS_0",    doc.createAccessor(`jnt_${k}`).setType("VEC4").setArray(new Uint16Array(g.j)).setBuffer(buffer))
      .setAttribute("WEIGHTS_0",   doc.createAccessor(`wgt_${k}`).setType("VEC4").setArray(new Float32Array(g.w)).setBuffer(buffer))
      .setMaterial(mats[k]);
    mesh.addPrimitive(prim);
    tv += g.vc;
    tt += g.i.length / 3;
  }

  scene.addChild(doc.createNode("MannequinMesh").setMesh(mesh).setSkin(skin));

  // ── Animation ──
  addMoonwalkAnimation(doc, buffer, BONES, nodes);
  addKOAnimation(doc, buffer, BONES, nodes);

  const outPath = "./mannequin_v4.glb";
  await new NodeIO().write(outPath, doc);

  // ── Report ──
  const blendedCount = BONES.filter(b => b[6] !== null).length;
  console.log(`\n✓ Mannequin v4 written to ${outPath}`);
  console.log(`  Skeleton source:  ${SKELETON_PATH}`);
  console.log(`  Subject:          ${skel.proportions.totalHeight}cm / ${skel.proportions.weight}kg ${skel.proportions.biologicalSex}`);
  console.log(`  Bones:            ${BONES.length}  (${blendedCount} with smooth skinning)`);
  console.log(`  Vertices:         ${tv}`);
  console.log(`  Triangles:        ${tt}`);
  console.log(`  Materials:        ${Object.values(groups).filter(g => g.vc > 0).length}`);
  console.log(`  Geometry types:   capsule (limbs), trapezoid (torso), helmet (head), box (armor)`);
  console.log(`  Animations:       ${Object.keys(BOXING_ACTIONS).length} (${Object.keys(BOXING_ACTIONS).join(", ")})`);

  console.log(`\n  Key proportions (from skeleton.json):`);
  console.log(`    Shoulder width: ${(lm.shoulderX * 200).toFixed(1)}cm`);
  console.log(`    Humerus length: ${(lm.humerusLen * 100).toFixed(1)}cm`);
  console.log(`    Forearm length: ${(lm.forearmLen * 100).toFixed(1)}cm`);
  console.log(`    Femur length:   ${(lm.femurLen * 100).toFixed(1)}cm`);
  console.log(`    Tibia length:   ${(lm.tibiaLen * 100).toFixed(1)}cm`);

  console.log(`\n  Hierarchy:`);
  (function tree(i, ind) {
    const blend = BONES[i][6] ? ` ⟷ ${BONES[BONES[i][6].childIdx][0]}` : "";
    console.log(`${ind}${BONES[i][0]} [${BONES[i][3]}] (${BONES[i][5]})${blend}`);
    for (let c = 0; c < BONES.length; c++) if (BONES[c][1] === i) tree(c, ind + "  ");
  })(0, "  ");
}

main().catch(e => { console.error(e); process.exit(1); });
