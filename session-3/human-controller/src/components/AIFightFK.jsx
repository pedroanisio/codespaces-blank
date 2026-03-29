import { useState, useEffect, useRef, useCallback } from "react";
import * as THREE from "three";

/* ═══════════════════════════════════════════════════════════════════════
   AI FIGHT v3 — Forward Kinematics from Human Body Schema v3
   
   Key difference from v2: NO hardcoded positions.
   All body positions derived from joint angles via FK solver.
   
   Joint definitions from schema: DOFs, ROM limits, axes.
   Segment chain from schema: 15 segments, mass, lengths.
   Actions = JointState[] targets (schema-native).
   ═══════════════════════════════════════════════════════════════════════ */

const DEG = Math.PI / 180;

// ═══════════════════════════════════════════════════════════════════════
// 1. KINEMATIC CHAIN — from schema joints/segments
//    Body-local frame: +X forward (facing), +Y up, +Z left
//    Joint rotation order: ZXY (Grood-Suntay biomechanical convention)
//      Z = flexion/extension (sagittal)
//      X = ab/adduction (frontal)
//      Y = int/ext rotation (transverse)
// ═══════════════════════════════════════════════════════════════════════

// Joint ROM from schema (degrees)
const JOINTS = {
  L5S1:      { dof:3, rom:{fe:[-15,25], aa:[-8,8],  ie:[-12,12]} },
  C7T1:      { dof:3, rom:{fe:[-60,60], aa:[-40,40],ie:[-70,70]} },
  shoulderR: { dof:3, rom:{fe:[-60,180],aa:[-10,180],ie:[-90,90]} },
  shoulderL: { dof:3, rom:{fe:[-60,180],aa:[-10,180],ie:[-90,90]} },
  elbowR:    { dof:1, rom:{fe:[0,150]} },
  elbowL:    { dof:1, rom:{fe:[0,150]} },
  wristR:    { dof:2, rom:{fe:[-80,70], aa:[-20,30]} },
  wristL:    { dof:2, rom:{fe:[-80,70], aa:[-20,30]} },
  hipR:      { dof:3, rom:{fe:[-15,125],aa:[-30,45],ie:[-45,45]} },
  hipL:      { dof:3, rom:{fe:[-15,125],aa:[-30,45],ie:[-45,45]} },
  kneeR:     { dof:1, rom:{fe:[0,140]} },
  kneeL:     { dof:1, rom:{fe:[0,140]} },
  ankleR:    { dof:2, rom:{fe:[-50,20], aa:[-35,25]} },
  ankleL:    { dof:2, rom:{fe:[-50,20], aa:[-35,25]} },
};

// Segment lengths (meters) from schema generator proportions
// De Leva (1996) segment parameters
const SEG = {
  trunk:    0.53,   // L5-S1 to C7-T1 level
  headNeck: 0.24,   // C7-T1 to vertex
  upperArm: 0.33,   // shoulder to elbow (humerus ~36cm adjusted)
  forearm:  0.26,   // elbow to wrist
  hand:     0.19,   // wrist to fingertip
  thigh:    0.43,   // hip to knee (femur ~45cm adjusted)
  shank:    0.39,   // knee to ankle
  foot:     0.20,   // ankle to toe (horizontal)
};

// Joint attachment points in parent segment's local frame (meters)
const ATTACH = {
  L5S1:      [0, 0, 0],          // at pelvis origin
  C7T1:      [0, SEG.trunk, 0],  // top of trunk
  shoulderR: [0, SEG.trunk * 0.92, -0.19],  // ~92% up trunk, 19cm right
  shoulderL: [0, SEG.trunk * 0.92, 0.19],
  hipR:      [0, -0.02, -0.09],  // slightly below pelvis center, 9cm right
  hipL:      [0, -0.02, 0.09],
};

// Rest directions (unit vectors) — where segment points at 0° angles
// Arms/legs hang DOWN, trunk points UP, feet point FORWARD
const REST = {
  trunk:    [0, 1, 0],
  headNeck: [0, 1, 0],
  upperArm: [0,-1, 0],
  forearm:  [0,-1, 0],
  hand:     [0,-1, 0],
  thigh:    [0,-1, 0],
  shank:    [0,-1, 0],
  foot:     [0.97,-0.26, 0],  // slightly angled down to reach ground
};

// ═══════════════════════════════════════════════════════════════════════
// 2. FORWARD KINEMATICS SOLVER
// ═══════════════════════════════════════════════════════════════════════

function clampAngle(val, min, max) {
  return Math.max(min, Math.min(max, val || 0));
}

function clampJoint(name, angles) {
  const j = JOINTS[name];
  if (!j) return angles;
  const out = { ...angles };
  if (j.rom.fe) out.fe = clampAngle(out.fe, j.rom.fe[0], j.rom.fe[1]);
  if (j.rom.aa) out.aa = clampAngle(out.aa, j.rom.aa[0], j.rom.aa[1]);
  if (j.rom.ie) out.ie = clampAngle(out.ie, j.rom.ie[0], j.rom.ie[1]);
  return out;
}

function jointQuaternion(parentQuat, fe, aa, ie) {
  // ZXY Euler: flex/ext(Z), ab/ad(X), int/ext rot(Y)
  const euler = new THREE.Euler(
    (aa || 0) * DEG,
    (ie || 0) * DEG,
    (fe || 0) * DEG,
    'ZXY'
  );
  const jq = new THREE.Quaternion().setFromEuler(euler);
  return parentQuat.clone().multiply(jq);
}

function transformPoint(origin, quat, localPt) {
  const v = new THREE.Vector3(localPt[0], localPt[1], localPt[2]);
  v.applyQuaternion(quat);
  return origin.clone().add(v);
}

function segEnd(origin, quat, restDir, length) {
  const d = new THREE.Vector3(restDir[0], restDir[1], restDir[2]);
  d.applyQuaternion(quat).multiplyScalar(length);
  return origin.clone().add(d);
}

/**
 * Forward Kinematics: joint angles → world-space landmarks
 * @param rootPos  THREE.Vector3 — pelvis world position
 * @param rootYaw  number — facing direction in radians (0 = +X)
 * @param angles   object — { jointName: { fe, aa, ie } }
 * @returns object — { landmark: THREE.Vector3, ... }
 */
function solveFK(rootPos, rootYaw, angles) {
  const rq = new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(0, 1, 0), rootYaw
  );

  const L = {};  // landmarks
  const JQ = {}; // joint quaternions (for debug/display)

  L.pelvis = rootPos.clone();

  // ── Trunk (L5-S1) ──
  const a_l5 = clampJoint('L5S1', angles.L5S1 || {});
  JQ.L5S1 = jointQuaternion(rq, a_l5.fe, a_l5.aa, a_l5.ie);
  const l5Pos = transformPoint(rootPos, rq, ATTACH.L5S1);

  // Shoulder and neck attachment points (in trunk frame)
  L.shoulderR = transformPoint(l5Pos, JQ.L5S1, ATTACH.shoulderR);
  L.shoulderL = transformPoint(l5Pos, JQ.L5S1, ATTACH.shoulderL);
  L.c7t1 = transformPoint(l5Pos, JQ.L5S1, ATTACH.C7T1);

  // ── Head-neck (C7-T1) ──
  const a_c7 = clampJoint('C7T1', angles.C7T1 || {});
  JQ.C7T1 = jointQuaternion(JQ.L5S1, a_c7.fe, a_c7.aa, a_c7.ie);
  L.headTop = segEnd(L.c7t1, JQ.C7T1, REST.headNeck, SEG.headNeck);
  L.headCenter = segEnd(L.c7t1, JQ.C7T1, REST.headNeck, SEG.headNeck * 0.65);

  // ── Right arm chain ──
  const a_shR = clampJoint('shoulderR', angles.shoulderR || {});
  JQ.shoulderR = jointQuaternion(JQ.L5S1, a_shR.fe, a_shR.aa, a_shR.ie);
  L.elbowR = segEnd(L.shoulderR, JQ.shoulderR, REST.upperArm, SEG.upperArm);

  const a_elR = clampJoint('elbowR', angles.elbowR || {});
  JQ.elbowR = jointQuaternion(JQ.shoulderR, a_elR.fe, 0, 0);
  L.wristR = segEnd(L.elbowR, JQ.elbowR, REST.forearm, SEG.forearm);

  const a_wrR = clampJoint('wristR', angles.wristR || {});
  JQ.wristR = jointQuaternion(JQ.elbowR, a_wrR.fe, a_wrR.aa, 0);
  L.handR = segEnd(L.wristR, JQ.wristR, REST.hand, SEG.hand);

  // ── Left arm chain (mirror aa & ie for bilateral symmetry) ──
  const a_shL = clampJoint('shoulderL', angles.shoulderL || {});
  JQ.shoulderL = jointQuaternion(JQ.L5S1, a_shL.fe, -(a_shL.aa||0), -(a_shL.ie||0));
  L.elbowL = segEnd(L.shoulderL, JQ.shoulderL, REST.upperArm, SEG.upperArm);

  const a_elL = clampJoint('elbowL', angles.elbowL || {});
  JQ.elbowL = jointQuaternion(JQ.shoulderL, a_elL.fe, 0, 0);
  L.wristL = segEnd(L.elbowL, JQ.elbowL, REST.forearm, SEG.forearm);

  const a_wrL = clampJoint('wristL', angles.wristL || {});
  JQ.wristL = jointQuaternion(JQ.elbowL, a_wrL.fe, -(a_wrL.aa||0), 0);
  L.handL = segEnd(L.wristL, JQ.wristL, REST.hand, SEG.hand);

  // ── Right leg chain ──
  const hipRPos = transformPoint(rootPos, rq, ATTACH.hipR);
  L.hipR = hipRPos;
  const a_hR = clampJoint('hipR', angles.hipR || {});
  JQ.hipR = jointQuaternion(rq, a_hR.fe, a_hR.aa, a_hR.ie);
  L.kneeR = segEnd(hipRPos, JQ.hipR, REST.thigh, SEG.thigh);

  const a_kR = clampJoint('kneeR', angles.kneeR || {});
  JQ.kneeR = jointQuaternion(JQ.hipR, a_kR.fe, 0, 0);
  L.ankleR = segEnd(L.kneeR, JQ.kneeR, REST.shank, SEG.shank);

  const a_aR = clampJoint('ankleR', angles.ankleR || {});
  JQ.ankleR = jointQuaternion(JQ.kneeR, a_aR.fe, a_aR.aa, 0);
  L.footR = segEnd(L.ankleR, JQ.ankleR, REST.foot, SEG.foot);

  // ── Left leg chain (mirror aa & ie for bilateral symmetry) ──
  const hipLPos = transformPoint(rootPos, rq, ATTACH.hipL);
  L.hipL = hipLPos;
  const a_hL = clampJoint('hipL', angles.hipL || {});
  JQ.hipL = jointQuaternion(rq, a_hL.fe, -(a_hL.aa||0), -(a_hL.ie||0));
  L.kneeL = segEnd(hipLPos, JQ.hipL, REST.thigh, SEG.thigh);

  const a_kL = clampJoint('kneeL', angles.kneeL || {});
  JQ.kneeL = jointQuaternion(JQ.hipL, a_kL.fe, 0, 0);
  L.ankleL = segEnd(L.kneeL, JQ.kneeL, REST.shank, SEG.shank);

  const a_aL = clampJoint('ankleL', angles.ankleL || {});
  JQ.ankleL = jointQuaternion(JQ.kneeL, a_aL.fe, -(a_aL.aa||0), 0);
  L.footL = segEnd(L.ankleL, JQ.ankleL, REST.foot, SEG.foot);

  return { landmarks: L, jointQuats: JQ };
}

// ═══════════════════════════════════════════════════════════════════════
// 3. ACTIONS — defined as JointState[] targets (schema-native)
//    Orthodox stance: L hand leads, R hand rear
// ═══════════════════════════════════════════════════════════════════════

const ACTIONS = {
  guard: {
    type:"stance", staminaCost:0,
    schema:"Neutral guard. All joints within 15% ROM. Tonic muscle activation ~15%.",
    joints: {
      L5S1:{fe:3,aa:0,ie:0}, C7T1:{fe:-5,aa:0,ie:0},
      shoulderR:{fe:25,aa:12,ie:10}, elbowR:{fe:125}, wristR:{fe:-5},
      shoulderL:{fe:35,aa:18,ie:5},  elbowL:{fe:115}, wristL:{fe:-5},
      hipR:{fe:12,aa:-5,ie:0}, kneeR:{fe:18}, ankleR:{fe:5},
      hipL:{fe:8,aa:5,ie:0},  kneeL:{fe:14}, ankleL:{fe:5},
    }
  },
  jab: {
    type:"attack", power:12, speed:9, staminaCost:5,
    schema:"L shoulder flexion→85°, elbow ext→8°. L5S1 ie→12° (trunk rotation). Deltoid 0.8, triceps 0.7. Wrist neutral for alignment.",
    joints: {
      L5S1:{fe:5,aa:0,ie:12},  C7T1:{fe:-3,aa:2,ie:5},
      shoulderL:{fe:85,aa:5,ie:15}, elbowL:{fe:8}, wristL:{fe:-5,aa:0},
      shoulderR:{fe:18,aa:10,ie:5}, elbowR:{fe:128}, wristR:{fe:-5},
      hipR:{fe:15,aa:-3,ie:10}, kneeR:{fe:20}, ankleR:{fe:8},
      hipL:{fe:6,aa:3,ie:0},   kneeL:{fe:14}, ankleL:{fe:5},
    }
  },
  cross: {
    type:"attack", power:22, speed:7, staminaCost:10,
    schema:"R shoulder flex→90°, elbow ext→10°. L5S1 ie→-18° (full trunk rotation). Hip R ie→20° (kinetic chain). Pectoralis 0.9, triceps 0.85. Wrist slight ulnar deviation for alignment. ~3200N peak.",
    joints: {
      L5S1:{fe:8,aa:-2,ie:-18}, C7T1:{fe:-5,aa:-3,ie:-8},
      shoulderR:{fe:90,aa:5,ie:20}, elbowR:{fe:10}, wristR:{fe:-8,aa:-10},
      shoulderL:{fe:15,aa:15,ie:0}, elbowL:{fe:120}, wristL:{fe:-5},
      hipR:{fe:14,aa:-5,ie:20}, kneeR:{fe:22}, ankleR:{fe:10},
      hipL:{fe:8,aa:3,ie:-5},  kneeL:{fe:16}, ankleL:{fe:6},
    }
  },
  hook: {
    type:"attack", power:28, speed:5, staminaCost:14,
    schema:"L shoulder flex→75° + horizontal adduction (aa→-15°, ie→45°). L5S1 ie→25° (massive trunk rotation). Elbow fixed ~90°. Pectoralis 0.95, obliques 0.8. Arc trajectory ~4100N.",
    joints: {
      L5S1:{fe:4,aa:0,ie:25}, C7T1:{fe:-5,aa:3,ie:10},
      shoulderL:{fe:75,aa:-15,ie:45}, elbowL:{fe:92}, wristL:{fe:-10,aa:15},
      shoulderR:{fe:20,aa:10,ie:0}, elbowR:{fe:125}, wristR:{fe:-5},
      hipR:{fe:14,aa:-5,ie:15}, kneeR:{fe:20}, ankleR:{fe:8},
      hipL:{fe:10,aa:5,ie:-10}, kneeL:{fe:16}, ankleL:{fe:6},
    }
  },
  uppercut: {
    type:"attack", power:30, speed:4, staminaCost:16,
    schema:"R shoulder flex→110° (rising arc from below). Knee ext→8° (drive up). L5S1 fe→-5° (extension), ie→-10°. Quadriceps 0.9, deltoid 0.85. Vertical force ~4500N. No perfect defense.",
    joints: {
      L5S1:{fe:-5,aa:0,ie:-10}, C7T1:{fe:-8,aa:-2,ie:-5},
      shoulderR:{fe:110,aa:5,ie:10}, elbowR:{fe:65}, wristR:{fe:-15},
      shoulderL:{fe:20,aa:15,ie:0}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:5,aa:-3,ie:8}, kneeR:{fe:8}, ankleR:{fe:12},
      hipL:{fe:6,aa:3,ie:0},  kneeL:{fe:10}, ankleL:{fe:8},
    }
  },
  bodyShot: {
    type:"attack", power:18, speed:6, staminaCost:10,
    schema:"Level change: L5S1 fe→15° (trunk flexion). R shoulder flex→70° targeting solar plexus. Knee flex→30° (crouch). Targets floating ribs / liver.",
    joints: {
      L5S1:{fe:15,aa:-3,ie:-12}, C7T1:{fe:-10,aa:-3,ie:-5},
      shoulderR:{fe:70,aa:-5,ie:10}, elbowR:{fe:25}, wristR:{fe:-10,aa:-5},
      shoulderL:{fe:25,aa:12,ie:0}, elbowL:{fe:115}, wristL:{fe:-5},
      hipR:{fe:20,aa:-5,ie:12}, kneeR:{fe:30}, ankleR:{fe:10},
      hipL:{fe:15,aa:3,ie:0},  kneeL:{fe:25}, ankleL:{fe:8},
    }
  },
  slip: {
    type:"defense", defenseVs:["jab","cross"], staminaCost:4,
    schema:"Head off centerline: C7T1 aa→30° (lateral flexion). L5S1 aa→-8°, fe→8° (spine lateral bend). Knee flex→35° (level drop). ContactForce: zero (miss).",
    joints: {
      L5S1:{fe:8,aa:-8,ie:5}, C7T1:{fe:-5,aa:30,ie:10},
      shoulderR:{fe:22,aa:10,ie:5}, elbowR:{fe:120}, wristR:{fe:-5},
      shoulderL:{fe:28,aa:15,ie:5}, elbowL:{fe:110}, wristL:{fe:-5},
      hipR:{fe:15,aa:-8,ie:0}, kneeR:{fe:35}, ankleR:{fe:10,aa:-15},
      hipL:{fe:12,aa:8,ie:0},  kneeL:{fe:30}, ankleL:{fe:8,aa:10},
    }
  },
  block: {
    type:"defense", defenseVs:["hook","cross","jab"], staminaCost:6,
    schema:"High guard: both shoulder flex→40°, elbow flex→140° (forearms shield head). Biceps 0.5, deltoid 0.4. Absorbs ~40% via padding.",
    joints: {
      L5S1:{fe:2,aa:0,ie:0}, C7T1:{fe:-8,aa:0,ie:0},
      shoulderR:{fe:40,aa:15,ie:10}, elbowR:{fe:140}, wristR:{fe:10},
      shoulderL:{fe:45,aa:20,ie:5},  elbowL:{fe:140}, wristL:{fe:10},
      hipR:{fe:10,aa:-5,ie:0}, kneeR:{fe:15}, ankleR:{fe:5},
      hipL:{fe:8,aa:5,ie:0},  kneeL:{fe:12}, ankleL:{fe:5},
    }
  },
  duck: {
    type:"defense", defenseVs:["hook","jab"], staminaCost:6,
    schema:"Deep level change: L5S1 fe→20° (trunk flexion). Knee flex→65° (deep squat). Head drops below strike plane. Quadriceps eccentric 0.7.",
    joints: {
      L5S1:{fe:20,aa:0,ie:0}, C7T1:{fe:-15,aa:0,ie:0},
      shoulderR:{fe:25,aa:10,ie:5}, elbowR:{fe:120}, wristR:{fe:-5},
      shoulderL:{fe:30,aa:15,ie:5}, elbowL:{fe:115}, wristL:{fe:-5},
      hipR:{fe:55,aa:-5,ie:0}, kneeR:{fe:65}, ankleR:{fe:15},
      hipL:{fe:50,aa:5,ie:0},  kneeL:{fe:60}, ankleL:{fe:12},
    }
  },
  parry: {
    type:"defense", defenseVs:["jab","cross","bodyShot"], staminaCost:3,
    schema:"R hand deflects: shoulder flex→55°, elbow→80°, wrist radial deviation (aa→20°). Minimal energy. Opens counter window.",
    joints: {
      L5S1:{fe:3,aa:0,ie:-5}, C7T1:{fe:-5,aa:0,ie:-3},
      shoulderR:{fe:55,aa:10,ie:5}, elbowR:{fe:80}, wristR:{fe:-5,aa:20},
      shoulderL:{fe:32,aa:15,ie:5}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:12,aa:-5,ie:0}, kneeR:{fe:18}, ankleR:{fe:5},
      hipL:{fe:8,aa:5,ie:0},  kneeL:{fe:14}, ankleL:{fe:5},
    }
  },
  advance: {
    type:"movement", staminaCost:3,
    schema:"Step forward: L hip flex→25° (lead step), R ankle plantarflex→-15° (push). Weight shifts anterior. CoM moves +15cm.",
    joints: {
      L5S1:{fe:5,aa:0,ie:0}, C7T1:{fe:-3,aa:0,ie:0},
      shoulderR:{fe:22,aa:10,ie:5}, elbowR:{fe:125}, wristR:{fe:-5},
      shoulderL:{fe:30,aa:15,ie:5}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:5,aa:-3,ie:0},  kneeR:{fe:25}, ankleR:{fe:-15},
      hipL:{fe:25,aa:3,ie:0},  kneeL:{fe:20}, ankleL:{fe:8},
    }
  },
  retreat: {
    type:"movement", staminaCost:3,
    schema:"Step back: R hip flex→-5° (extend rear), L ankle push→-10°. Creates distance. CoM moves -15cm.",
    joints: {
      L5S1:{fe:0,aa:0,ie:0}, C7T1:{fe:-5,aa:0,ie:0},
      shoulderR:{fe:22,aa:10,ie:5}, elbowR:{fe:125}, wristR:{fe:-5},
      shoulderL:{fe:30,aa:15,ie:5}, elbowL:{fe:118}, wristL:{fe:-5},
      hipR:{fe:-5,aa:-3,ie:0}, kneeR:{fe:10}, ankleR:{fe:5},
      hipL:{fe:10,aa:5,ie:0},  kneeL:{fe:20}, ankleL:{fe:-10},
    }
  },
};

const RECOIL_JOINTS = {
  L5S1:{fe:-8,aa:8,ie:-5}, C7T1:{fe:10,aa:25,ie:15},
  shoulderR:{fe:15,aa:20,ie:-10}, elbowR:{fe:100}, wristR:{fe:10},
  shoulderL:{fe:20,aa:25,ie:-5},  elbowL:{fe:105}, wristL:{fe:10},
  hipR:{fe:8,aa:-8,ie:-5}, kneeR:{fe:20}, ankleR:{fe:8},
  hipL:{fe:5,aa:8,ie:5},   kneeL:{fe:18}, ankleL:{fe:5},
};

const ACTION_NAMES = Object.keys(ACTIONS).filter(k => k !== 'guard');

// ═══════════════════════════════════════════════════════════════════════
// 4. INTERPOLATION
// ═══════════════════════════════════════════════════════════════════════

function lerpAngles(a1, a2, t) {
  const out = {};
  const allKeys = new Set([...Object.keys(a1 || {}), ...Object.keys(a2 || {})]);
  for (const jn of allKeys) {
    const j1 = a1?.[jn] || {};
    const j2 = a2?.[jn] || {};
    out[jn] = {};
    for (const dof of ['fe','aa','ie']) {
      const v1 = j1[dof] || 0;
      const v2 = j2[dof] || 0;
      out[jn][dof] = v1 + (v2 - v1) * t;
    }
  }
  return out;
}

function smoothstep(t) { const c = Math.max(0, Math.min(1, t)); return c * c * (3 - 2 * c); }

function cloneAngles(angles) {
  const out = {};
  for (const [joint, values] of Object.entries(angles || {})) out[joint] = { ...(values || {}) };
  return out;
}

function zeroAngleVelocities(template) {
  const out = {};
  for (const joint of Object.keys(template || {})) out[joint] = { fe: 0, aa: 0, ie: 0 };
  return out;
}

function springValue(current, target, velocity, omega, zeta, dt) {
  const accel = (omega * omega) * (target - current) - 2 * zeta * omega * velocity;
  const nextVelocity = velocity + accel * dt;
  return {
    value: current + nextVelocity * dt,
    velocity: nextVelocity,
  };
}

function springAngles(current, target, velocity, dt, omega = 15, zeta = 0.82) {
  const next = {};
  const nextVelocity = {};
  const allKeys = new Set([...Object.keys(current || {}), ...Object.keys(target || {})]);
  for (const joint of allKeys) {
    const cur = current?.[joint] || {};
    const tgt = target?.[joint] || {};
    const vel = velocity?.[joint] || {};
    next[joint] = {};
    nextVelocity[joint] = {};
    for (const dof of ["fe", "aa", "ie"]) {
      const sprung = springValue(cur[dof] || 0, tgt[dof] || 0, vel[dof] || 0, omega, zeta, dt);
      next[joint][dof] = sprung.value;
      nextVelocity[joint][dof] = sprung.velocity;
    }
  }
  return { angles: next, velocity: nextVelocity };
}

function springVec3(current, target, velocity, dt, omega = 12, zeta = 0.84) {
  const sx = springValue(current.x, target.x, velocity.x, omega, zeta, dt);
  const sy = springValue(current.y, target.y, velocity.y, omega, zeta, dt);
  const sz = springValue(current.z, target.z, velocity.z, omega, zeta, dt);
  return {
    value: new THREE.Vector3(sx.value, sy.value, sz.value),
    velocity: new THREE.Vector3(sx.velocity, sy.velocity, sz.velocity),
  };
}

function dampImpulse(value, halflife, dt) {
  const decay = Math.pow(0.5, dt / Math.max(halflife, 1e-3));
  return value.clone().multiplyScalar(decay);
}

function actionMotion(name, side) {
  const toward = side === "A" ? 1 : -1;
  const lateral = side === "A" ? -1 : 1;
  const base = { offset: new THREE.Vector3(0, 0, 0), yaw: 0, jointOmega: 14 };
  switch (name) {
    case "jab":
      return { offset: new THREE.Vector3(0.11 * toward, 0.01, 0.01 * lateral), yaw: 0.06 * toward, jointOmega: 20 };
    case "cross":
      return { offset: new THREE.Vector3(0.16 * toward, 0.015, 0.02 * lateral), yaw: 0.16 * toward, jointOmega: 17 };
    case "hook":
      return { offset: new THREE.Vector3(0.1 * toward, 0.02, 0.12 * lateral), yaw: 0.22 * toward, jointOmega: 15 };
    case "uppercut":
      return { offset: new THREE.Vector3(0.09 * toward, -0.06, 0.015 * lateral), yaw: 0.1 * toward, jointOmega: 13 };
    case "bodyShot":
      return { offset: new THREE.Vector3(0.12 * toward, -0.045, 0.03 * lateral), yaw: 0.11 * toward, jointOmega: 15 };
    case "slip":
      return { offset: new THREE.Vector3(-0.03 * toward, -0.03, 0.12 * lateral), yaw: -0.1 * toward, jointOmega: 12 };
    case "block":
      return { offset: new THREE.Vector3(-0.04 * toward, 0.01, 0), yaw: 0, jointOmega: 12 };
    case "duck":
      return { offset: new THREE.Vector3(-0.02 * toward, -0.11, 0), yaw: 0.04 * toward, jointOmega: 11 };
    case "parry":
      return { offset: new THREE.Vector3(0.025 * toward, -0.01, 0.08 * lateral), yaw: 0.05 * toward, jointOmega: 14 };
    case "advance":
      return { offset: new THREE.Vector3(0.18 * toward, -0.015, 0), yaw: 0.03 * toward, jointOmega: 12 };
    case "retreat":
      return { offset: new THREE.Vector3(-0.16 * toward, 0, 0), yaw: -0.04 * toward, jointOmega: 12 };
    default:
      return base;
  }
}

function resetPoseState(baseYaw = 0) {
  return {
    offset: new THREE.Vector3(0, 0, 0),
    offsetVel: new THREE.Vector3(0, 0, 0),
    targetOffset: new THREE.Vector3(0, 0, 0),
    yaw: baseYaw,
    yawVel: 0,
    targetYaw: baseYaw,
    impulse: new THREE.Vector3(0, 0, 0),
    jointOmega: 14,
  };
}

// ═══════════════════════════════════════════════════════════════════════
// 5. FIGHT RESOLUTION
// ═══════════════════════════════════════════════════════════════════════

function resolveExchange(nameA, nameB) {
  const a = ACTIONS[nameA], b = ACTIONS[nameB];
  if (!a || !b) return {damageA:0,damageB:0,narrative:"Reset.",jointsA:ACTIONS.guard.joints,jointsB:ACTIONS.guard.joints,flash:null,outcome:"neutral",costA:0,costB:0};
  let dA=0,dB=0,narr="",jA=a.joints,jB=b.joints,flash=null,out="neutral";

  if (a.type==="attack"&&b.type==="attack") {
    if (a.speed>=b.speed) {dB=a.power;dA=Math.round(b.power*.5);narr=`A lands ${nameA} first (spd${a.speed}), B's ${nameB} late.`;jB=RECOIL_JOINTS;flash="b";out="a_wins";}
    else {dA=b.power;dB=Math.round(a.power*.5);narr=`B's ${nameB} beats A's ${nameA}.`;jA=RECOIL_JOINTS;flash="a";out="b_wins";}
  } else if (a.type==="attack"&&b.type==="defense") {
    if (b.defenseVs?.includes(nameA)) {narr=`A throws ${nameA} — B ${nameB}s perfectly.`;out="b_defends";}
    else {dB=Math.round(a.power*.7);narr=`A's ${nameA} catches B (wrong defense).`;jB=RECOIL_JOINTS;flash="b";out="a_wins";}
  } else if (b.type==="attack"&&a.type==="defense") {
    if (a.defenseVs?.includes(nameB)) {narr=`B throws ${nameB} — A ${nameA}s perfectly.`;out="a_defends";}
    else {dA=Math.round(b.power*.7);narr=`B's ${nameB} catches A (wrong defense).`;jA=RECOIL_JOINTS;flash="a";out="b_wins";}
  } else if (a.type==="attack"&&b.type==="movement") {
    if (nameB==="retreat") {dB=Math.round(a.power*.3);narr=`A's ${nameA} clips retreating B.`;out="a_grazes";}
    else {dB=Math.round(a.power*1.1);narr=`B walks into A's ${nameA}!`;jB=RECOIL_JOINTS;flash="b";out="a_wins";}
  } else if (b.type==="attack"&&a.type==="movement") {
    if (nameA==="retreat") {dA=Math.round(b.power*.3);narr=`B's ${nameB} clips retreating A.`;out="b_grazes";}
    else {dA=Math.round(b.power*1.1);narr=`A walks into B's ${nameB}!`;jA=RECOIL_JOINTS;flash="a";out="b_wins";}
  } else { narr=`Both ${a.type==="defense"?"play cautious":"reposition"}.`; }
  return {damageA:dA,damageB:dB,narrative:narr,jointsA:jA,jointsB:jB,flash,outcome:out,costA:a.staminaCost,costB:b.staminaCost};
}

// ═══════════════════════════════════════════════════════════════════════
// 6. AI PROMPT
// ═══════════════════════════════════════════════════════════════════════

function buildPrompt(role, state, history) {
  return `You are Fighter ${role}. Choose your next action.
STATE: HP:${state.myHP}/100 STA:${state.mySta}/100 | Opp HP:${state.oppHP}/100 STA:${state.oppSta}/100 | Rd${state.round} Ex${state.ex}/12
HISTORY: ${history.length>0?history.slice(-4).map((h,i)=>`${i+1}.You:${h.my} Opp:${h.opp}→${h.r}`).join("; "):"(none)"}
ACTIONS: jab(s9,p12,c5) cross(s7,p22,c10) hook(s5,p28,c14) uppercut(s4,p30,c16) bodyShot(s6,p18,c10) | slip(vs jab,cross|c4) block(vs hook,cross,jab|c6) duck(vs hook,jab|c6) parry(vs jab,cross,bodyShot|c3) | advance(c3,risky) retreat(c3,30%dmg)
Rules: Faster atk wins. Right def=0dmg. Wrong def=70%. Retreat=30%. Advance into punch=110%.
JSON only: {"action":"NAME","reasoning":"max 12 words"}`;
}

// ═══════════════════════════════════════════════════════════════════════
// 7. THREE.JS RENDERER
// ═══════════════════════════════════════════════════════════════════════

const BODY_SEGS = [
  ['pelvis','c7t1','torso'], ['shoulderR','shoulderL','shoulders'],
  ['hipR','hipL','hips'], ['c7t1','headCenter','neck'], ['headCenter','headTop','head'],
  ['shoulderR','elbowR','uaR'], ['elbowR','wristR','faR'], ['wristR','handR','hdR'],
  ['shoulderL','elbowL','uaL'], ['elbowL','wristL','faL'], ['wristL','handL','hdL'],
  ['hipR','kneeR','thR'], ['kneeR','ankleR','shR'], ['ankleR','footR','ftR'],
  ['hipL','kneeL','thL'], ['kneeL','ankleL','shL'], ['ankleL','footL','ftL'],
];
const SPHERE_MARKS = ['headCenter','handR','handL','shoulderR','shoulderL','elbowR','elbowL','wristR','wristL','hipR','hipL','kneeR','kneeL','ankleR','ankleL'];

const RA = {torso:.065,shoulders:.03,hips:.045,neck:.028,head:.058,uaR:.024,faR:.019,hdR:.022,uaL:.024,faL:.019,hdL:.022,thR:.042,shR:.028,ftR:.02,thL:.042,shL:.028,ftL:.02};

function buildFighter(skinC, shortsC) {
  const group = new THREE.Group();
  const links = {}, spheres = {};
  const mat = (c) => new THREE.MeshPhongMaterial({color:c,shininess:30,specular:0x222222});
  for (const [,,name] of BODY_SEGS) {
    const r = RA[name] || .02;
    const c = (name.includes('th')||name.includes('hip'))?shortsC:skinC;
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r,r,1,8), mat(c));
    m.castShadow = true; group.add(m); links[name] = m;
  }
  for (const mk of SPHERE_MARKS) {
    const r = mk.includes('head')?.06:mk.includes('hand')?.022:mk.includes('shoulder')?.025:mk.includes('hip')?.03:mk.includes('knee')?.025:mk.includes('ankle')?.022:.018;
    const c = (mk.includes('hip')||mk.includes('knee'))?shortsC:skinC;
    const m = new THREE.Mesh(new THREE.SphereGeometry(r,10,10), mat(c));
    m.castShadow = true; group.add(m); spheres[mk] = m;
  }
  return { group, links, spheres };
}

function updateFighter(fighter, landmarks) {
  const v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), up = new THREE.Vector3(0,1,0);
  for (const [from,to,name] of BODY_SEGS) {
    const m = fighter.links[name]; const p1 = landmarks[from], p2 = landmarks[to];
    if (!p1||!p2) continue;
    v1.copy(p1); v2.copy(p2);
    const mid = v1.clone().add(v2).multiplyScalar(.5);
    const dir = v2.clone().sub(v1); const len = dir.length();
    m.position.copy(mid); m.scale.y = len;
    if (len>.001) { dir.normalize(); const q = new THREE.Quaternion(); q.setFromUnitVectors(up,dir); m.quaternion.copy(q); }
  }
  for (const mk of SPHERE_MARKS) {
    if (landmarks[mk]) fighter.spheres[mk].position.copy(landmarks[mk]);
  }
}

// ═══════════════════════════════════════════════════════════════════════
// 8. COMPONENT
// ═══════════════════════════════════════════════════════════════════════

export default function AIFightFK() {
  const mountRef = useRef(null);
  const [fight, setFight] = useState({
    hpA:100,hpB:100,staA:100,staB:100,round:1,ex:0,phase:"idle",
    log:[],hA:[],hB:[],actA:null,actB:null,rsnA:"",rsnB:"",winner:null
  });
  const [debug, setDebug] = useState([]);
  const [showDebug, setShowDebug] = useState(false);
  const [showJoints, setShowJoints] = useState(false);
  const [auto, setAuto] = useState(false);
  const [spd, setSpd] = useState("normal");
  const [apiKey, setApiKey] = useState("");
  const [curAnglesA, setCurAnglesA] = useState(ACTIONS.guard.joints);
  const [curAnglesB, setCurAnglesB] = useState(ACTIONS.guard.joints);

  const anim = useRef({
    anglesA:cloneAngles(ACTIONS.guard.joints), anglesB:cloneAngles(ACTIONS.guard.joints),
    targetA:cloneAngles(ACTIONS.guard.joints), targetB:cloneAngles(ACTIONS.guard.joints),
    velocityA:zeroAngleVelocities(ACTIONS.guard.joints), velocityB:zeroAngleVelocities(ACTIONS.guard.joints),
    poseA:resetPoseState(0), poseB:resetPoseState(Math.PI),
    flashAlpha:0, flashSide:null
  });
  const fRef = useRef(fight); fRef.current = fight;
  const autoRef = useRef(auto); autoRef.current = auto;
  const dbRef = useRef(null);

  const addLog = useCallback((m,l="info")=>{
    const t=new Date().toISOString().slice(11,23);
    console.log(`[${t}][${l}]${m}`);
    setDebug(p=>[...p.slice(-40),{t,m,l}]);
  },[]);

  // ── Three.js ──
  useEffect(()=>{
    const ct=mountRef.current; if(!ct) return;
    const W=ct.clientWidth,H=ct.clientHeight;
    const scene=new THREE.Scene();scene.background=new THREE.Color(0x08080e);scene.fog=new THREE.Fog(0x08080e,7,16);
    const camera=new THREE.PerspectiveCamera(46,W/H,.1,50);camera.position.set(0,1.2,3.6);camera.lookAt(0,.9,0);
    const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(W,H);renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;ct.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0x334466,.6));
    const kl=new THREE.DirectionalLight(0xffeedd,1.0);kl.position.set(3,5,4);kl.castShadow=true;kl.shadow.mapSize.set(1024,1024);kl.shadow.camera.near=.5;kl.shadow.camera.far=15;kl.shadow.camera.left=-3;kl.shadow.camera.right=3;kl.shadow.camera.top=3;kl.shadow.camera.bottom=-1;scene.add(kl);
    const fl=new THREE.DirectionalLight(0x4466aa,.4);fl.position.set(-2,3,-2);scene.add(fl);
    const rl=new THREE.DirectionalLight(0xff6644,.3);rl.position.set(0,2,-4);scene.add(rl);

    const ground=new THREE.Mesh(new THREE.PlaneGeometry(14,14),new THREE.MeshPhongMaterial({color:0x14141e,shininess:60,specular:0x222233}));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
    scene.add(Object.assign(new THREE.GridHelper(8,16,0x222244,0x161628),{position:new THREE.Vector3(0,.002,0)}));

    // Ring
    const pm=new THREE.MeshPhongMaterial({color:0x888888});
    for(const[x,,z]of[[-2.5,0,-2.5],[2.5,0,-2.5],[-2.5,0,2.5],[2.5,0,2.5]]){const p=new THREE.Mesh(new THREE.CylinderGeometry(.03,.03,1.6,6),pm);p.position.set(x,.8,z);p.castShadow=true;scene.add(p);}
    const rm=new THREE.MeshBasicMaterial({color:0x444466});
    for(const ry of[.5,.9,1.3]){const pts=[[-2.5,0,-2.5],[2.5,0,-2.5],[2.5,0,2.5],[-2.5,0,2.5]];for(let i=0;i<4;i++){const[x1,,z1]=pts[i],[x2,,z2]=pts[(i+1)%4];const d=new THREE.Vector3(x2-x1,0,z2-z1);const l=d.length();const r=new THREE.Mesh(new THREE.CylinderGeometry(.008,.008,l,4),rm);r.position.set((x1+x2)/2,ry,(z1+z2)/2);const q=new THREE.Quaternion();q.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());r.quaternion.copy(q);scene.add(r);}}

    const fA = buildFighter(0xd4a574, 0x1a3a6b);
    const fB = buildFighter(0xc49060, 0x6b1a1a);
    scene.add(fA.group); scene.add(fB.group);

    const flashMesh=new THREE.Mesh(new THREE.SphereGeometry(.1,16,16),new THREE.MeshBasicMaterial({color:0xffffcc,transparent:true,opacity:0}));scene.add(flashMesh);

    // Initial FK
    const rootA = new THREE.Vector3(-0.5, 0.95, 0);
    const rootB = new THREE.Vector3(0.5, 0.95, 0);
    let rA = solveFK(rootA, 0, ACTIONS.guard.joints);
    let rB = solveFK(rootB, Math.PI, ACTIONS.guard.joints);
    updateFighter(fA, rA.landmarks);
    updateFighter(fB, rB.landmarks);

    let lastT = 0, rafId;
    function tick(ts) {
      rafId = requestAnimationFrame(tick);
      if (!lastT) { lastT = ts; }
      const dt = Math.min((ts-lastT)/1000, .05); lastT = ts;
      const st = anim.current;

      const sprungA = springAngles(st.anglesA, st.targetA, st.velocityA, dt, st.poseA.jointOmega);
      const sprungB = springAngles(st.anglesB, st.targetB, st.velocityB, dt, st.poseB.jointOmega);
      st.anglesA = sprungA.angles;
      st.anglesB = sprungB.angles;
      st.velocityA = sprungA.velocity;
      st.velocityB = sprungB.velocity;

      const poseSpringA = springVec3(st.poseA.offset, st.poseA.targetOffset, st.poseA.offsetVel, dt);
      const poseSpringB = springVec3(st.poseB.offset, st.poseB.targetOffset, st.poseB.offsetVel, dt);
      st.poseA.offset = poseSpringA.value;
      st.poseA.offsetVel = poseSpringA.velocity;
      st.poseB.offset = poseSpringB.value;
      st.poseB.offsetVel = poseSpringB.velocity;

      const yawA = springValue(st.poseA.yaw, st.poseA.targetYaw, st.poseA.yawVel, 10, 0.86, dt);
      const yawB = springValue(st.poseB.yaw, st.poseB.targetYaw, st.poseB.yawVel, 10, 0.86, dt);
      st.poseA.yaw = yawA.value;
      st.poseA.yawVel = yawA.velocity;
      st.poseB.yaw = yawB.value;
      st.poseB.yawVel = yawB.velocity;

      st.poseA.impulse = dampImpulse(st.poseA.impulse, 0.16, dt);
      st.poseB.impulse = dampImpulse(st.poseB.impulse, 0.16, dt);

      const liveRootA = rootA.clone().add(st.poseA.offset).add(st.poseA.impulse);
      const liveRootB = rootB.clone().add(st.poseB.offset).add(st.poseB.impulse);

      rA = solveFK(liveRootA, st.poseA.yaw, st.anglesA);
      rB = solveFK(liveRootB, st.poseB.yaw, st.anglesB);
      updateFighter(fA, rA.landmarks);
      updateFighter(fB, rB.landmarks);

      if (st.flashAlpha > 0) {
        st.flashAlpha = Math.max(0, st.flashAlpha - dt * 3);
        flashMesh.material.opacity = st.flashAlpha;
        flashMesh.scale.setScalar(1 + (1-st.flashAlpha)*2.5);
        const target = st.flashSide === "a" ? rA.landmarks.headCenter : rB.landmarks.headCenter;
        if (target) flashMesh.position.copy(target);
      }

      const center = liveRootA.clone().add(liveRootB).multiplyScalar(0.5);
      const impactBias = st.poseA.impulse.clone().sub(st.poseB.impulse).multiplyScalar(0.2);
      camera.position.x = center.x * 0.12 + impactBias.x;
      camera.position.y = 1.18 + center.y * 0.04 + Math.sin(ts * 0.0016) * 0.01 + Math.abs(impactBias.x) * 0.12;
      camera.position.z = 3.55 + Math.abs(liveRootA.x - liveRootB.x) * 0.28 - Math.abs(impactBias.x) * 0.4;
      camera.lookAt(center.x, 1.02 + center.y * 0.05, center.z + impactBias.z * 0.5);
      renderer.render(scene, camera);

      // Update angle display (throttled)
      if (Math.floor(ts/200) !== Math.floor((ts-dt*1000)/200)) {
        setCurAnglesA(st.anglesA);
        setCurAnglesB(st.anglesB);
      }
    }
    rafId = requestAnimationFrame(tick);

    const onR=()=>{const w=ct.clientWidth,h=ct.clientHeight;camera.aspect=w/h;camera.updateProjectionMatrix();renderer.setSize(w,h);};
    window.addEventListener("resize",onR);
    return()=>{cancelAnimationFrame(rafId);window.removeEventListener("resize",onR);renderer.dispose();if(ct.contains(renderer.domElement))ct.removeChild(renderer.domElement);};
  },[]);

  // ── AI call ──
  const callAI = useCallback(async(role,state,hist)=>{
    const t0=Date.now(); addLog(`[${role}] calling API...`);
    const ctrl=new AbortController();
    const tid=setTimeout(()=>{ctrl.abort();addLog(`[${role}] TIMEOUT`,"error");},15000);
    try {
      const resp=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",headers:{"Content-Type":"application/json","x-api-key":apiKey,"anthropic-version":"2023-06-01","anthropic-dangerous-direct-browser-access":"true"},body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:150,messages:[{role:"user",content:buildPrompt(role,state,hist)}]}),signal:ctrl.signal});
      clearTimeout(tid);
      addLog(`[${role}] HTTP ${resp.status} (${Date.now()-t0}ms)`,resp.ok?"ok":"error");
      if(!resp.ok){const e=await resp.text().catch(()=>"");addLog(`[${role}] ${e.slice(0,200)}`,"error");return{action:ACTION_NAMES[Math.random()*ACTION_NAMES.length|0],reasoning:"HTTP error"};}
      const data=await resp.json();
      const text=(data.content||[]).map(c=>c.text||"").join("");
      addLog(`[${role}] raw: ${text.slice(0,120)}`);
      const clean=text.replace(/```json\s*|```\s*/g,"").trim();
      try{const p=JSON.parse(clean);if(ACTIONS[p.action]){addLog(`[${role}] ✓ ${p.action}`,"ok");return p;}}catch(e){}
      const found=ACTION_NAMES.find(a=>clean.toLowerCase().includes(a));
      if(found){addLog(`[${role}] extracted: ${found}`,"warn");return{action:found,reasoning:"extracted"};}
      const fb=ACTION_NAMES[Math.random()*ACTION_NAMES.length|0];addLog(`[${role}] fallback: ${fb}`,"warn");return{action:fb,reasoning:"fallback"};
    }catch(e){clearTimeout(tid);addLog(`[${role}] ${e.name}: ${e.message}`,"error");return{action:ACTION_NAMES[Math.random()*ACTION_NAMES.length|0],reasoning:e.name};}
  },[addLog,apiKey]);

  // ── Exchange ──
  const doExchange = useCallback(async()=>{
    const s=fRef.current; if(s.phase!=="idle")return;
    addLog("═══ EXCHANGE ═══");
    setFight(f=>({...f,phase:"thinking"}));
    const results=await Promise.allSettled([
      callAI("A",{myHP:s.hpA,mySta:s.staA,oppHP:s.hpB,oppSta:s.staB,round:s.round,ex:s.ex},s.hA),
      callAI("B",{myHP:s.hpB,mySta:s.staB,oppHP:s.hpA,oppSta:s.staA,round:s.round,ex:s.ex},s.hB)
    ]);
    const dA=results[0].status==="fulfilled"?results[0].value:{action:ACTION_NAMES[Math.random()*ACTION_NAMES.length|0],reasoning:"rejected"};
    const dB=results[1].status==="fulfilled"?results[1].value:{action:ACTION_NAMES[Math.random()*ACTION_NAMES.length|0],reasoning:"rejected"};

    addLog(`Resolve: A=${dA.action} vs B=${dB.action}`);
    const r=resolveExchange(dA.action,dB.action);
    const nhA=Math.max(0,s.hpA-r.damageA),nhB=Math.max(0,s.hpB-r.damageB);
    const nsA=Math.max(0,Math.min(100,s.staA-r.costA+4)),nsB=Math.max(0,Math.min(100,s.staB-r.costB+4));
    const nex=s.ex+1; const nrd=nex>=12?s.round+1:s.round;
    addLog(`A hp${s.hpA}→${nhA} | B hp${s.hpB}→${nhB}`);

    const st=anim.current;
    const motionA = actionMotion(dA.action, "A");
    const motionB = actionMotion(dB.action, "B");
    st.targetA = cloneAngles(r.jointsA);
    st.targetB = cloneAngles(r.jointsB);
    st.poseA.targetOffset = motionA.offset.clone();
    st.poseB.targetOffset = motionB.offset.clone();
    st.poseA.targetYaw = motionA.yaw;
    st.poseB.targetYaw = Math.PI + motionB.yaw;
    st.poseA.jointOmega = motionA.jointOmega;
    st.poseB.jointOmega = motionB.jointOmega;
    if(r.flash){
      st.flashAlpha=1;st.flashSide=r.flash;
      const impulse = new THREE.Vector3(r.flash === "a" ? -0.12 : 0.12, 0.045, 0);
      if (r.flash === "a") st.poseA.impulse.add(impulse);
      if (r.flash === "b") st.poseB.impulse.add(impulse);
    }

    const winner=nhA<=0?"B":nhB<=0?"A":(nrd>3?(nhA>nhB?"A":nhB>nhA?"B":"DRAW"):null);
    const entry={ex:nex,aA:dA.action,aB:dB.action,rA:dA.reasoning,rB:dB.reasoning,dA:r.damageA,dB:r.damageB,narr:r.narrative,out:r.outcome};

    setFight(f=>({...f,hpA:nhA,hpB:nhB,staA:nsA,staB:nsB,round:nrd,ex:nex>=12?0:nex,phase:"animating",actA:dA.action,actB:dB.action,rsnA:dA.reasoning||"",rsnB:dB.reasoning||"",log:[...f.log,entry],hA:[...f.hA,{my:dA.action,opp:dB.action,r:r.narrative}],hB:[...f.hB,{my:dB.action,opp:dA.action,r:r.narrative}],winner}));

    const dl=spd==="fast"?700:spd==="blitz"?350:1400;
    setTimeout(()=>{
      const st2=anim.current;
      st2.targetA=cloneAngles(ACTIONS.guard.joints);st2.targetB=cloneAngles(ACTIONS.guard.joints);
      st2.poseA.targetOffset.set(0,0,0);st2.poseB.targetOffset.set(0,0,0);
      st2.poseA.targetYaw=0;st2.poseB.targetYaw=Math.PI;
      st2.poseA.jointOmega=14;st2.poseB.jointOmega=14;
      setFight(f=>({...f,phase:winner?"finished":"idle"}));
    },dl);
  },[callAI,addLog,spd]);

  useEffect(()=>{
    if(!auto)return;
    const iv=setInterval(()=>{if(autoRef.current&&fRef.current.phase==="idle")doExchange();},spd==="fast"?1400:spd==="blitz"?700:2800);
    return()=>clearInterval(iv);
  },[auto,doExchange,spd]);

  const reset=useCallback(()=>{
    setFight({hpA:100,hpB:100,staA:100,staB:100,round:1,ex:0,phase:"idle",log:[],hA:[],hB:[],actA:null,actB:null,rsnA:"",rsnB:"",winner:null});
    setAuto(false);setDebug([]);
    const st=anim.current;
    st.anglesA=cloneAngles(ACTIONS.guard.joints);st.anglesB=cloneAngles(ACTIONS.guard.joints);
    st.targetA=cloneAngles(ACTIONS.guard.joints);st.targetB=cloneAngles(ACTIONS.guard.joints);
    st.velocityA=zeroAngleVelocities(ACTIONS.guard.joints);st.velocityB=zeroAngleVelocities(ACTIONS.guard.joints);
    st.poseA=resetPoseState(0);st.poseB=resetPoseState(Math.PI);
    st.flashAlpha=0;st.flashSide=null;
    addLog("Reset","ok");
  },[addLog]);

  useEffect(()=>{if(dbRef.current)dbRef.current.scrollTop=dbRef.current.scrollHeight;},[debug]);

  const s=fight;const last=s.log[s.log.length-1];
  const LC={info:"#556688",ok:"#44aa66",warn:"#ccaa33",error:"#cc4444"};

  // Joint display helper
  const JointRow=({name,angles})=>{
    if(!angles)return null;
    const j=JOINTS[name];if(!j)return null;
    return(<div style={{display:"flex",gap:4,fontSize:8,alignItems:"center",marginBottom:1}}>
      <span style={{width:64,color:"#667799",textAlign:"right"}}>{name}</span>
      {['fe','aa','ie'].map(d=>{
        if(!j.rom[d])return null;
        const v=Math.round(angles[d]||0);
        const pct=((v-j.rom[d][0])/(j.rom[d][1]-j.rom[d][0]))*100;
        return(<div key={d} style={{width:48,display:"flex",flexDirection:"column",alignItems:"center"}}>
          <div style={{width:"100%",height:3,background:"rgba(60,70,100,.3)",borderRadius:1,position:"relative"}}>
            <div style={{position:"absolute",height:"100%",borderRadius:1,background:d==='fe'?"#4488cc":d==='aa'?"#44aa66":"#cc8833",width:`${Math.max(2,Math.min(100,pct))}%`}}/>
          </div>
          <span style={{color:"#556677"}}>{v}°</span>
        </div>);
      })}
    </div>);
  };

  return(
    <div style={{width:"100%",height:"100vh",position:"relative",fontFamily:"'JetBrains Mono','SF Mono','Courier New',monospace",background:"#08080e",color:"#c8ccd4",overflow:"hidden"}}>
      <div ref={mountRef} style={{position:"absolute",inset:0,zIndex:1}}/>

      {/* Title */}
      <div style={{position:"absolute",top:8,left:"50%",transform:"translateX(-50%)",zIndex:10,textAlign:"center"}}>
        <div style={{fontSize:9,letterSpacing:3,textTransform:"uppercase",color:"#556688"}}>FK-Driven AI Fight — Schema v3 Joint Angles</div>
        <div style={{fontSize:8,color:"#3a5577",marginTop:2}}>Rd{s.round}/3 Ex{s.ex}/12 <span style={{color:s.phase==="thinking"?"#ccaa33":s.phase==="animating"?"#44aa66":s.phase==="finished"?"#cc4444":"#556688",fontWeight:700}}>{s.phase.toUpperCase()}</span> · 14 joints · {Object.keys(JOINTS).reduce((a,k)=>{const j=JOINTS[k];return a+(j.rom.fe?1:0)+(j.rom.aa?1:0)+(j.rom.ie?1:0);},0)} DOFs · ROM-clamped</div>
      </div>

      {/* Fighter A */}
      <div style={{position:"absolute",top:42,left:6,zIndex:10,background:"rgba(8,8,14,.9)",border:"1px solid rgba(58,123,213,.2)",borderRadius:8,padding:"6px 10px",backdropFilter:"blur(8px)",width:172}}>
        <div style={{fontSize:10,fontWeight:700,color:"#3a7bd5",letterSpacing:1,marginBottom:3}}>FIGHTER A</div>
        <div style={{marginBottom:2}}><div style={{display:"flex",justifyContent:"space-between",fontSize:8,color:"#88aacc"}}><span>HP</span><span>{s.hpA}</span></div><div style={{height:5,background:"rgba(60,70,100,.3)",borderRadius:2,overflow:"hidden"}}><div style={{height:"100%",width:`${s.hpA}%`,background:s.hpA>50?"#22aa55":s.hpA>25?"#cc8822":"#cc3333",borderRadius:2,transition:"width .5s"}}/></div></div>
        <div style={{marginBottom:3}}><div style={{display:"flex",justifyContent:"space-between",fontSize:8,color:"#88aacc"}}><span>STA</span><span>{s.staA}</span></div><div style={{height:3,background:"rgba(60,70,100,.3)",borderRadius:1,overflow:"hidden"}}><div style={{height:"100%",width:`${s.staA}%`,background:"#3388cc",borderRadius:1,transition:"width .5s"}}/></div></div>
        {s.actA&&<div style={{fontSize:9}}><span style={{color:"#3a7bd5",fontWeight:700}}>{s.actA.toUpperCase()}</span>{s.rsnA&&<div style={{fontSize:8,color:"#556688",fontStyle:"italic"}}>"{s.rsnA}"</div>}</div>}
        {s.actA&&ACTIONS[s.actA]&&<div style={{fontSize:7,color:"#445566",marginTop:2,lineHeight:1.4,borderTop:"1px solid rgba(60,80,120,.15)",paddingTop:2}}>{ACTIONS[s.actA].schema.slice(0,120)}</div>}
      </div>

      {/* Fighter B */}
      <div style={{position:"absolute",top:42,right:6,zIndex:10,background:"rgba(8,8,14,.9)",border:"1px solid rgba(213,58,58,.2)",borderRadius:8,padding:"6px 10px",backdropFilter:"blur(8px)",width:172,textAlign:"right"}}>
        <div style={{fontSize:10,fontWeight:700,color:"#d53a3a",letterSpacing:1,marginBottom:3}}>FIGHTER B</div>
        <div style={{marginBottom:2}}><div style={{display:"flex",justifyContent:"space-between",fontSize:8,color:"#cc8888"}}><span>HP</span><span>{s.hpB}</span></div><div style={{height:5,background:"rgba(100,60,60,.3)",borderRadius:2,overflow:"hidden"}}><div style={{height:"100%",width:`${s.hpB}%`,background:s.hpB>50?"#22aa55":s.hpB>25?"#cc8822":"#cc3333",borderRadius:2,transition:"width .5s"}}/></div></div>
        <div style={{marginBottom:3}}><div style={{display:"flex",justifyContent:"space-between",fontSize:8,color:"#cc8888"}}><span>STA</span><span>{s.staB}</span></div><div style={{height:3,background:"rgba(100,60,60,.3)",borderRadius:1,overflow:"hidden"}}><div style={{height:"100%",width:`${s.staB}%`,background:"#cc5533",borderRadius:1,transition:"width .5s"}}/></div></div>
        {s.actB&&<div style={{fontSize:9}}><span style={{color:"#d53a3a",fontWeight:700}}>{s.actB.toUpperCase()}</span>{s.rsnB&&<div style={{fontSize:8,color:"#776655",fontStyle:"italic"}}>"{s.rsnB}"</div>}</div>}
        {s.actB&&ACTIONS[s.actB]&&<div style={{fontSize:7,color:"#554444",marginTop:2,lineHeight:1.4,borderTop:"1px solid rgba(120,60,60,.15)",paddingTop:2}}>{ACTIONS[s.actB].schema.slice(0,120)}</div>}
      </div>

      {/* Narrative */}
      {last&&<div style={{position:"absolute",top:"50%",left:"50%",transform:"translate(-50%,-50%)",zIndex:10,background:"rgba(8,8,14,.92)",border:`1px solid ${last.out?.includes("a_wins")?"rgba(58,123,213,.3)":last.out?.includes("b_wins")?"rgba(213,58,58,.3)":"rgba(100,120,180,.2)"}`,borderRadius:8,padding:"6px 16px",maxWidth:360,textAlign:"center",pointerEvents:"none",opacity:s.phase==="animating"?1:.12,transition:"opacity .5s"}}>
        <div style={{fontSize:10,color:"#c8ccd4",lineHeight:1.4}}>{last.narr}</div>
        <div style={{fontSize:8,color:"#556688",marginTop:2}}>
          {last.dA>0&&<span style={{color:"#cc4444"}}>A:-{last.dA}hp </span>}
          {last.dB>0&&<span style={{color:"#4488cc"}}>B:-{last.dB}hp </span>}
        </div>
      </div>}

      {s.winner&&<div style={{position:"absolute",top:"36%",left:"50%",transform:"translate(-50%,-50%)",zIndex:20,textAlign:"center"}}><div style={{fontSize:26,fontWeight:800,letterSpacing:4,color:s.winner==="A"?"#3a7bd5":s.winner==="B"?"#d53a3a":"#888",textShadow:"0 0 30px rgba(100,100,200,.4)"}}>{s.winner==="DRAW"?"DRAW":`FIGHTER ${s.winner} WINS`}</div></div>}

      {/* Joint Angle Panel */}
      {showJoints&&<div style={{position:"absolute",top:42,left:"50%",transform:"translateX(-50%)",zIndex:15,display:"flex",gap:8}}>
        <div style={{background:"rgba(4,4,8,.95)",border:"1px solid rgba(58,123,213,.2)",borderRadius:6,padding:6,width:200}}>
          <div style={{fontSize:8,color:"#3a7bd5",fontWeight:700,marginBottom:3,letterSpacing:1}}>FIGHTER A — JOINT ANGLES</div>
          <div style={{fontSize:7,color:"#445566",marginBottom:2,display:"flex",gap:4,justifyContent:"flex-end",paddingRight:4}}>
            <span style={{width:48,textAlign:"center",color:"#4488cc"}}>F/E</span>
            <span style={{width:48,textAlign:"center",color:"#44aa66"}}>Ab/Ad</span>
            <span style={{width:48,textAlign:"center",color:"#cc8833"}}>I/E</span>
          </div>
          {Object.keys(JOINTS).map(jn=><JointRow key={jn} name={jn} angles={curAnglesA[jn]}/>)}
        </div>
        <div style={{background:"rgba(4,4,8,.95)",border:"1px solid rgba(213,58,58,.2)",borderRadius:6,padding:6,width:200}}>
          <div style={{fontSize:8,color:"#d53a3a",fontWeight:700,marginBottom:3,letterSpacing:1}}>FIGHTER B — JOINT ANGLES</div>
          <div style={{fontSize:7,color:"#554444",marginBottom:2,display:"flex",gap:4,justifyContent:"flex-end",paddingRight:4}}>
            <span style={{width:48,textAlign:"center",color:"#4488cc"}}>F/E</span>
            <span style={{width:48,textAlign:"center",color:"#44aa66"}}>Ab/Ad</span>
            <span style={{width:48,textAlign:"center",color:"#cc8833"}}>I/E</span>
          </div>
          {Object.keys(JOINTS).map(jn=><JointRow key={jn} name={jn} angles={curAnglesB[jn]}/>)}
        </div>
      </div>}

      {/* Debug */}
      {showDebug&&<div style={{position:"absolute",bottom:110,left:6,zIndex:15,width:320}}>
        <div ref={dbRef} style={{background:"rgba(2,2,6,.97)",border:"1px solid rgba(100,120,180,.15)",borderRadius:6,padding:4,maxHeight:140,overflowY:"auto",fontSize:8,lineHeight:1.5}}>
          {debug.length===0?<div style={{color:"#334455",textAlign:"center",padding:4}}>Press EXCHANGE to start</div>:
          debug.map((d,i)=><div key={i} style={{color:LC[d.l],borderBottom:"1px solid rgba(50,60,80,.1)",wordBreak:"break-all"}}><span style={{color:"#2a3344"}}>{d.t}</span> {d.m}</div>)}
        </div>
      </div>}

      {/* Controls */}
      <div style={{position:"absolute",bottom:0,left:0,right:0,zIndex:10,background:"rgba(8,8,14,.94)",borderTop:"1px solid rgba(100,120,180,.15)",padding:"6px 10px"}}>
        <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
          <button onClick={doExchange} disabled={s.phase!=="idle"||!apiKey} style={{background:s.phase==="thinking"?"rgba(200,170,50,.15)":"rgba(58,123,213,.15)",border:`1px solid ${s.phase==="thinking"?"rgba(200,170,50,.3)":"rgba(58,123,213,.3)"}`,color:s.phase==="thinking"?"#ccaa33":!apiKey?"#556677":"#88bbdd",borderRadius:6,padding:"5px 12px",cursor:s.phase==="idle"&&apiKey?"pointer":"wait",fontSize:10,fontFamily:"inherit"}}>
            {s.phase==="thinking"?"⧖ THINKING":s.phase==="animating"?"⚡ RESOLVING":!apiKey?"🔑 SET KEY":"⚡ EXCHANGE"}
          </button>
          <button onClick={()=>setAuto(!auto)} disabled={s.phase==="finished"} style={{background:auto?"rgba(50,180,80,.15)":"none",border:`1px solid ${auto?"rgba(50,180,80,.3)":"rgba(100,120,180,.2)"}`,color:auto?"#66cc88":"#88aabb",borderRadius:6,padding:"5px 10px",cursor:"pointer",fontSize:10,fontFamily:"inherit"}}>{auto?"■ STOP":"▶ AUTO"}</button>
          <div style={{display:"flex",gap:3}}>
            {[["normal","1×"],["fast","2×"],["blitz","4×"]].map(([v,l])=><button key={v} onClick={()=>setSpd(v)} style={{background:spd===v?"rgba(60,100,180,.2)":"none",border:"1px solid rgba(100,120,180,.15)",color:spd===v?"#88bbdd":"#556677",borderRadius:4,padding:"2px 6px",cursor:"pointer",fontSize:8,fontFamily:"inherit"}}>{l}</button>)}
          </div>
          <button onClick={()=>setShowJoints(!showJoints)} style={{background:showJoints?"rgba(100,100,200,.15)":"none",border:"1px solid rgba(100,120,180,.2)",color:showJoints?"#8899cc":"#556677",borderRadius:6,padding:"5px 8px",cursor:"pointer",fontSize:8,fontFamily:"inherit"}}>
            {showJoints?"HIDE":"SHOW"} JOINTS
          </button>
          <button onClick={()=>setShowDebug(!showDebug)} style={{background:showDebug?"rgba(100,100,200,.15)":"none",border:"1px solid rgba(100,120,180,.2)",color:showDebug?"#8899cc":"#556677",borderRadius:6,padding:"5px 8px",cursor:"pointer",fontSize:8,fontFamily:"inherit"}}>
            DEBUG{debug.filter(d=>d.l==="error").length>0?` (${debug.filter(d=>d.l==="error").length}err)`:""}
          </button>
          <input type="password" placeholder="sk-ant-… API key" value={apiKey} onChange={e=>setApiKey(e.target.value)} style={{background:"rgba(20,20,30,.8)",border:`1px solid ${apiKey?"rgba(50,180,80,.3)":"rgba(180,80,80,.3)"}`,color:"#88aabb",borderRadius:4,padding:"4px 8px",fontSize:9,fontFamily:"inherit",width:140,marginLeft:"auto"}}/>
          <button onClick={reset} style={{background:"none",border:"1px solid rgba(180,80,80,.2)",color:"#aa6666",borderRadius:6,padding:"5px 10px",cursor:"pointer",fontSize:10,fontFamily:"inherit"}}>↺ RESET</button>
        </div>
        {s.log.length>0&&<div style={{marginTop:4,maxHeight:52,overflowY:"auto",fontSize:8,lineHeight:1.4}}>
          {s.log.slice(-4).map((l,i)=><div key={i} style={{color:"#667799",borderBottom:"1px solid rgba(100,120,180,.06)"}}>
            <span style={{color:"#445566"}}>#{l.ex}</span> <span style={{color:"#3a7bd5"}}>A:{l.aA}</span> vs <span style={{color:"#d53a3a"}}>B:{l.aB}</span> <span style={{color:"#88aacc"}}>→ {l.narr}</span>
          </div>)}
        </div>}
      </div>
    </div>
  );
}
