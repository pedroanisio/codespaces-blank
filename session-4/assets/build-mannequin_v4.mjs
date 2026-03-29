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

// ─── 2. Mannequin bone hierarchy (data-driven) ─────────────────────

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

  // Armor overlays
  world.shoulderPadL = [world.upperArmL[0] + 0.02,  world.upperArmL[1] + 0.06, 0];
  world.shoulderPadR = [world.upperArmR[0] - 0.02,  world.upperArmR[1] + 0.06, 0];
  world.chestPlate   = [0, chestY + 0.04, chestD / 2 + 0.02];
  world.beltFront    = [0, hipCenterY + 0.02, hipD / 2 + 0.02];
  world.pouchL       = [ 0.14, hipCenterY, hipD / 2 - 0.01];
  world.pouchR       = [-0.14, hipCenterY, hipD / 2 - 0.01];
  world.kneePadL     = [ hipJointX, kneeY + 0.10, 0.05];
  world.kneePadR     = [-hipJointX, kneeY + 0.10, 0.05];
  world.visor        = [0, headBaseY - 0.01, headRz + 0.02];
  world.helmetCrest  = [0, headBaseY + headRy * 0.8, -0.02];

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

    // Armor detail pieces (rigid skinning only)
    ["shoulderPadL", "upperArmL",   "box",        [0.14, 0.05, 0.14],                           "armor",    null],
    ["shoulderPadR", "upperArmR",   "box",        [0.14, 0.05, 0.14],                           "armor",    null],
    ["chestPlate",   "chest",       "box",        [chestW*0.65, 0.16, 0.04],                    "armorDark",null],
    ["beltFront",    "hips",        "box",        [hipW*0.65, 0.06, 0.04],                      "belt",     null],
    ["pouchL",       "hips",        "box",        [0.06, 0.08, 0.06],                           "armorDark",null],
    ["pouchR",       "hips",        "box",        [0.06, 0.08, 0.06],                           "armorDark",null],
    ["kneePadL",     "lowerLegL",   "box",        [0.08, 0.10, 0.04],                           "armor",    null],
    ["kneePadR",     "lowerLegR",   "box",        [0.08, 0.10, 0.04],                           "armor",    null],
    ["visor",        "head",        "box",        [headRx*1.8, 0.06, 0.04],                     "visor",    null],
    ["helmetCrest",  "head",        "box",        [0.04, 0.04, headRz*1.4],                     "accent",   null],
  ];

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

// ─── 7. Build GLB ───────────────────────────────────────────────────

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
