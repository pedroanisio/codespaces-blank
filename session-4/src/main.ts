import './style.css';

import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

import { KeyboardController } from './keyboard';
import { resolveMovement } from './motion';

const MODEL_URL = '/assets/mannequin_v4.glb';
const TARGET_MODEL_HEIGHT = 1.8;
const CAMERA_OFFSET = new THREE.Vector3(0, 2.6, -6.5);
const CAMERA_LOOK_AT_OFFSET = new THREE.Vector3(0, 1.4, 4);
const GRAVITY = 18;
const JUMP_VELOCITY = 6.25;
const ROLL_DURATION = 0.62;
const ROLL_SPEED = 4.8;
const FORWARD_VECTOR = new THREE.Vector3(0, 0, 1);

type RigBoneKey =
  | 'hips'
  | 'spine'
  | 'chest'
  | 'neck'
  | 'head'
  | 'upperArmL'
  | 'lowerArmL'
  | 'handL'
  | 'upperArmR'
  | 'lowerArmR'
  | 'handR'
  | 'upperLegL'
  | 'lowerLegL'
  | 'footL'
  | 'upperLegR'
  | 'lowerLegR'
  | 'footR';

type CharacterRig = {
  model: THREE.Object3D;
  bones: Partial<Record<RigBoneKey, THREE.Object3D>>;
  baseRotations: Map<RigBoneKey, THREE.Euler>;
  elapsed: number;
  missingBones: RigBoneKey[];
};

const mount = document.querySelector<HTMLDivElement>('#app');

if (!mount) {
  throw new Error('Missing #app mount node.');
}

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
mount.append(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color('#c7d2df');
scene.fog = new THREE.Fog('#c7d2df', 10, 38);

const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 2.8, -7);

const hemisphereLight = new THREE.HemisphereLight('#f5f5f5', '#617389', 2.4);
scene.add(hemisphereLight);

const sunlight = new THREE.DirectionalLight('#fff2d9', 2.8);
sunlight.position.set(6, 12, 4);
sunlight.castShadow = true;
sunlight.shadow.mapSize.setScalar(2048);
sunlight.shadow.camera.left = -20;
sunlight.shadow.camera.right = 20;
sunlight.shadow.camera.top = 20;
sunlight.shadow.camera.bottom = -20;
scene.add(sunlight);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(30, 96),
  new THREE.MeshStandardMaterial({
    color: '#5f7a56',
    roughness: 0.95,
    metalness: 0.02,
  }),
);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

const floorRing = new THREE.Mesh(
  new THREE.RingGeometry(16, 23, 96),
  new THREE.MeshBasicMaterial({
    color: '#7e9a71',
    transparent: true,
    opacity: 0.45,
    side: THREE.DoubleSide,
  }),
);
floorRing.rotation.x = -Math.PI / 2;
floorRing.position.y = 0.01;
scene.add(floorRing);

const grid = new THREE.GridHelper(40, 40, '#2f3f4d', '#617389');
grid.position.y = 0.02;
scene.add(grid);

const keyboard = new KeyboardController();
keyboard.attach();

let character: CharacterRig | null = null;
let verticalVelocity = 0;
let isAirborne = false;
let groundY = 0;
let rollTimeRemaining = 0;

function getBone(root: THREE.Object3D, name: string): THREE.Object3D | undefined {
  const candidate = root.getObjectByName(name);

  if (candidate) {
    return candidate;
  }

  let match: THREE.Object3D | undefined;

  root.traverse((child) => {
    if (match || child.name !== name) {
      return;
    }

    match = child;
  });

  if (match) {
    return match;
  }

  root.traverse((child) => {
    if (!(child instanceof THREE.SkinnedMesh) || !child.skeleton) {
      return;
    }

    const skeletonMatch = child.skeleton.bones.find((bone) => bone.name === name);

    if (skeletonMatch) {
      match = skeletonMatch;
    }
  });

  return match;
}

function getBoneByAliases(root: THREE.Object3D, names: string[]): THREE.Object3D | undefined {
  for (const name of names) {
    const bone = getBone(root, name);

    if (bone) {
      return bone;
    }
  }

  return undefined;
}

function cloneEuler(source: THREE.Euler): THREE.Euler {
  return new THREE.Euler(source.x, source.y, source.z, source.order);
}

function addOffset(base: THREE.Euler, x = 0, y = 0, z = 0): THREE.Euler {
  return new THREE.Euler(base.x + x, base.y + y, base.z + z, base.order);
}

function applyRotation(
  rig: CharacterRig,
  key: RigBoneKey,
  target: THREE.Euler,
  delta: number,
  responsiveness = 12,
): void {
  const bone = rig.bones[key];

  if (!bone) {
    return;
  }

  const alpha = 1 - Math.exp(-delta * responsiveness);
  bone.rotation.x += (target.x - bone.rotation.x) * alpha;
  bone.rotation.y += (target.y - bone.rotation.y) * alpha;
  bone.rotation.z += (target.z - bone.rotation.z) * alpha;
}

function animateRig(
  rig: CharacterRig,
  delta: number,
  speed: number,
  isJumping: boolean,
  jumpVelocity: number,
  isRolling: boolean,
  rollProgress: number,
): void {
  rig.elapsed += delta;

  const bases = rig.baseRotations;
  const swing = rig.elapsed * 7;
  const walkAmount = THREE.MathUtils.clamp(Math.abs(speed) / 2.4, 0, 1);
  const phase = speed >= 0 ? 1 : -1;
  const stride = Math.sin(swing) * 0.7 * walkAmount * phase;
  const counterStride = Math.sin(swing + Math.PI) * 0.7 * walkAmount * phase;
  const kneeLiftL = Math.max(0, -stride) * 0.65;
  const kneeLiftR = Math.max(0, -counterStride) * 0.65;
  const armSwingL = Math.sin(swing + Math.PI) * 0.5 * walkAmount * phase;
  const armSwingR = Math.sin(swing) * 0.5 * walkAmount * phase;
  const idleBreath = Math.sin(rig.elapsed * 1.8) * 0.03;
  const idleSway = Math.sin(rig.elapsed * 0.9) * 0.02;

  if (isRolling) {
    const fold = Math.sin(rollProgress * Math.PI);
    const spin = rollProgress * Math.PI * 2;

    applyRotation(rig, 'hips', addOffset(bases.get('hips')!, 0.45 + fold * 0.55, 0, 0), delta, 18);
    applyRotation(rig, 'spine', addOffset(bases.get('spine')!, 0.15 + Math.sin(spin) * 0.25, 0, 0), delta, 18);
    applyRotation(rig, 'chest', addOffset(bases.get('chest')!, -0.25 + Math.sin(spin) * 0.18, 0, 0), delta, 18);
    applyRotation(rig, 'neck', addOffset(bases.get('neck')!, -0.2, 0, 0), delta, 16);
    applyRotation(rig, 'head', addOffset(bases.get('head')!, -0.28, 0, 0), delta, 16);

    applyRotation(rig, 'upperLegL', addOffset(bases.get('upperLegL')!, -0.9 + fold * 0.25, 0, 0.12), delta, 18);
    applyRotation(rig, 'upperLegR', addOffset(bases.get('upperLegR')!, -0.9 + fold * 0.25, 0, -0.12), delta, 18);
    applyRotation(rig, 'lowerLegL', addOffset(bases.get('lowerLegL')!, 1.3 - fold * 0.35, 0, 0), delta, 18);
    applyRotation(rig, 'lowerLegR', addOffset(bases.get('lowerLegR')!, 1.3 - fold * 0.35, 0, 0), delta, 18);
    applyRotation(rig, 'footL', addOffset(bases.get('footL')!, -0.55, 0, 0), delta, 18);
    applyRotation(rig, 'footR', addOffset(bases.get('footR')!, -0.55, 0, 0), delta, 18);

    applyRotation(rig, 'upperArmL', addOffset(bases.get('upperArmL')!, -1.1, 0, 0.45), delta, 18);
    applyRotation(rig, 'upperArmR', addOffset(bases.get('upperArmR')!, -1.1, 0, -0.45), delta, 18);
    applyRotation(rig, 'lowerArmL', addOffset(bases.get('lowerArmL')!, 0.9, 0, 0), delta, 18);
    applyRotation(rig, 'lowerArmR', addOffset(bases.get('lowerArmR')!, 0.9, 0, 0), delta, 18);
    applyRotation(rig, 'handL', addOffset(bases.get('handL')!, 0.2, 0, 0), delta, 16);
    applyRotation(rig, 'handR', addOffset(bases.get('handR')!, 0.2, 0, 0), delta, 16);
    return;
  }

  if (isJumping) {
    const takeoff = jumpVelocity > 1;
    const apex = Math.abs(jumpVelocity) <= 1;
    const landing = jumpVelocity < -1;
    const hipPitch = takeoff ? -0.3 : apex ? -0.12 : 0.22;
    const legPitch = takeoff ? 0.55 : apex ? 0.25 : -0.42;
    const kneeBend = takeoff ? -0.2 : apex ? 0.15 : 0.62;
    const armPitch = takeoff ? -1.2 : apex ? -0.7 : -0.25;

    applyRotation(rig, 'hips', addOffset(bases.get('hips')!, hipPitch, 0, 0), delta, 16);
    applyRotation(rig, 'spine', addOffset(bases.get('spine')!, -hipPitch * 0.45, 0, 0), delta, 16);
    applyRotation(rig, 'chest', addOffset(bases.get('chest')!, -hipPitch * 0.3, 0, 0), delta, 16);
    applyRotation(rig, 'neck', addOffset(bases.get('neck')!, apex ? 0.06 : 0, 0, 0), delta, 14);
    applyRotation(rig, 'head', addOffset(bases.get('head')!, landing ? -0.08 : 0.04, 0, 0), delta, 14);

    applyRotation(rig, 'upperLegL', addOffset(bases.get('upperLegL')!, legPitch, 0, 0), delta, 16);
    applyRotation(rig, 'upperLegR', addOffset(bases.get('upperLegR')!, legPitch, 0, 0), delta, 16);
    applyRotation(rig, 'lowerLegL', addOffset(bases.get('lowerLegL')!, kneeBend, 0, 0), delta, 16);
    applyRotation(rig, 'lowerLegR', addOffset(bases.get('lowerLegR')!, kneeBend, 0, 0), delta, 16);
    applyRotation(rig, 'footL', addOffset(bases.get('footL')!, takeoff ? -0.22 : 0.18, 0, 0), delta, 16);
    applyRotation(rig, 'footR', addOffset(bases.get('footR')!, takeoff ? -0.22 : 0.18, 0, 0), delta, 16);

    applyRotation(rig, 'upperArmL', addOffset(bases.get('upperArmL')!, armPitch, 0, 0.12), delta, 16);
    applyRotation(rig, 'upperArmR', addOffset(bases.get('upperArmR')!, armPitch, 0, -0.12), delta, 16);
    applyRotation(rig, 'lowerArmL', addOffset(bases.get('lowerArmL')!, apex ? -0.18 : -0.38, 0, 0), delta, 16);
    applyRotation(rig, 'lowerArmR', addOffset(bases.get('lowerArmR')!, apex ? -0.18 : -0.38, 0, 0), delta, 16);
    applyRotation(rig, 'handL', cloneEuler(bases.get('handL')!), delta, 12);
    applyRotation(rig, 'handR', cloneEuler(bases.get('handR')!), delta, 12);
    return;
  }

  applyRotation(rig, 'hips', addOffset(bases.get('hips')!, idleBreath * 0.2, 0, idleSway * (1 - walkAmount)), delta);
  applyRotation(rig, 'spine', addOffset(bases.get('spine')!, idleBreath * 0.6, 0, idleSway), delta);
  applyRotation(rig, 'chest', addOffset(bases.get('chest')!, idleBreath, 0, idleSway * 1.2), delta);
  applyRotation(rig, 'neck', addOffset(bases.get('neck')!, idleBreath * 0.25, 0, 0), delta);
  applyRotation(rig, 'head', addOffset(bases.get('head')!, idleBreath * 0.35, 0, -idleSway * 0.5), delta);

  applyRotation(rig, 'upperLegL', addOffset(bases.get('upperLegL')!, stride, 0, 0), delta);
  applyRotation(rig, 'upperLegR', addOffset(bases.get('upperLegR')!, counterStride, 0, 0), delta);
  applyRotation(rig, 'lowerLegL', addOffset(bases.get('lowerLegL')!, kneeLiftL, 0, 0), delta);
  applyRotation(rig, 'lowerLegR', addOffset(bases.get('lowerLegR')!, kneeLiftR, 0, 0), delta);
  applyRotation(rig, 'footL', addOffset(bases.get('footL')!, -kneeLiftL * 0.4, 0, 0), delta);
  applyRotation(rig, 'footR', addOffset(bases.get('footR')!, -kneeLiftR * 0.4, 0, 0), delta);

  applyRotation(rig, 'upperArmL', addOffset(bases.get('upperArmL')!, armSwingL, 0, 0.05), delta);
  applyRotation(rig, 'upperArmR', addOffset(bases.get('upperArmR')!, armSwingR, 0, -0.05), delta);
  applyRotation(rig, 'lowerArmL', addOffset(bases.get('lowerArmL')!, Math.max(0, -armSwingL) * 0.2, 0, 0), delta);
  applyRotation(rig, 'lowerArmR', addOffset(bases.get('lowerArmR')!, Math.max(0, -armSwingR) * 0.2, 0, 0), delta);
  applyRotation(rig, 'handL', cloneEuler(bases.get('handL')!), delta, 10);
  applyRotation(rig, 'handR', cloneEuler(bases.get('handR')!), delta, 10);
}

async function loadCharacter(): Promise<CharacterRig> {
  const loader = new GLTFLoader();
  const gltf = await loader.loadAsync(MODEL_URL);
  const model = gltf.scene;
  model.position.set(0, 0, 0);

  model.traverse((child: THREE.Object3D) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.SkinnedMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });

  const initialBounds = new THREE.Box3().setFromObject(model);
  const initialSize = initialBounds.getSize(new THREE.Vector3());
  const height = Math.max(initialSize.y, 0.001);
  const scale = TARGET_MODEL_HEIGHT / height;
  model.scale.setScalar(scale);

  const scaledBounds = new THREE.Box3().setFromObject(model);
  const scaledCenter = scaledBounds.getCenter(new THREE.Vector3());
  model.position.x = -scaledCenter.x;
  model.position.z = -scaledCenter.z;
  model.position.y = -scaledBounds.min.y;

  scene.add(model);

  const bones: Partial<Record<RigBoneKey, THREE.Object3D>> = {
    hips: getBoneByAliases(model, ['hips', 'Hips']),
    spine: getBoneByAliases(model, ['spine', 'Spine']),
    chest: getBoneByAliases(model, ['chest', 'Chest']),
    neck: getBoneByAliases(model, ['neck', 'Neck']),
    head: getBoneByAliases(model, ['head', 'Head']),
    upperArmL: getBoneByAliases(model, ['upperArmL', 'UpperArmL', 'upper_arm.L', 'LeftArm']),
    lowerArmL: getBoneByAliases(model, ['lowerArmL', 'LowerArmL', 'lower_arm.L', 'LeftForeArm']),
    handL: getBoneByAliases(model, [
      'handL',
      'HandL',
      'hand.L',
      'LeftHand',
      'thumb_metaL',
      'index_metaL',
      'middle_metaL',
    ]),
    upperArmR: getBoneByAliases(model, ['upperArmR', 'UpperArmR', 'upper_arm.R', 'RightArm']),
    lowerArmR: getBoneByAliases(model, ['lowerArmR', 'LowerArmR', 'lower_arm.R', 'RightForeArm']),
    handR: getBoneByAliases(model, [
      'handR',
      'HandR',
      'hand.R',
      'RightHand',
      'thumb_metaR',
      'index_metaR',
      'middle_metaR',
    ]),
    upperLegL: getBoneByAliases(model, ['upperLegL', 'UpperLegL', 'upper_leg.L', 'LeftUpLeg']),
    lowerLegL: getBoneByAliases(model, ['lowerLegL', 'LowerLegL', 'lower_leg.L', 'LeftLeg']),
    footL: getBoneByAliases(model, ['footL', 'FootL', 'foot.L', 'LeftFoot', 'midfootL', 'heelL', 'hallux_metaL']),
    upperLegR: getBoneByAliases(model, ['upperLegR', 'UpperLegR', 'upper_leg.R', 'RightUpLeg']),
    lowerLegR: getBoneByAliases(model, ['lowerLegR', 'LowerLegR', 'lower_leg.R', 'RightLeg']),
    footR: getBoneByAliases(model, ['footR', 'FootR', 'foot.R', 'RightFoot', 'midfootR', 'heelR', 'hallux_metaR']),
  };

  const baseRotations = new Map<RigBoneKey, THREE.Euler>();
  const missingBones: RigBoneKey[] = [];

  (Object.keys(bones) as RigBoneKey[]).forEach((key) => {
    const bone = bones[key];

    if (bone) {
      baseRotations.set(key, cloneEuler(bone.rotation));
    } else {
      missingBones.push(key);
    }
  });

  if (missingBones.length > 0) {
    console.warn('Mannequin rig loaded with missing joints:', missingBones);
  }

  return {
    model,
    bones,
    baseRotations,
    elapsed: 0,
    missingBones,
  };
}

function updateCamera(target: THREE.Object3D, delta: number): void {
  const desiredPosition = CAMERA_OFFSET.clone().applyQuaternion(target.quaternion).add(target.position);
  const lookAtTarget = CAMERA_LOOK_AT_OFFSET.clone().applyQuaternion(target.quaternion).add(target.position);

  camera.position.lerp(desiredPosition, 1 - Math.exp(-delta * 6));
  camera.lookAt(lookAtTarget);
}

const clock = new THREE.Clock();

function animate(): void {
  requestAnimationFrame(animate);

  const delta = Math.min(clock.getDelta(), 0.05);

  if (character) {
    const movement = resolveMovement(keyboard.snapshot(), isAirborne);
    const isRolling = rollTimeRemaining > 0;

    if (!isRolling) {
      character.model.rotation.y += movement.turnSpeed * delta;
    }

    if (movement.rollRequested && rollTimeRemaining <= 0 && !isAirborne) {
      rollTimeRemaining = ROLL_DURATION;
    }

    if (movement.speed !== 0 && !isRolling) {
      const forward = FORWARD_VECTOR.clone().applyQuaternion(character.model.quaternion);
      character.model.position.addScaledVector(forward, movement.speed * delta);
    }

    if (isRolling) {
      rollTimeRemaining = Math.max(0, rollTimeRemaining - delta);
      const rollForward = FORWARD_VECTOR.clone().applyQuaternion(character.model.quaternion);
      const burst = ROLL_SPEED * (0.35 + (rollTimeRemaining / ROLL_DURATION) * 0.65);
      character.model.position.addScaledVector(rollForward, burst * delta);
    }

    if (movement.jumpRequested) {
      verticalVelocity = JUMP_VELOCITY;
      isAirborne = true;
      groundY = character.model.position.y;
    }

    if (isAirborne) {
      verticalVelocity -= GRAVITY * delta;
      character.model.position.y += verticalVelocity * delta;

      if (character.model.position.y <= groundY) {
        character.model.position.y = groundY;
        verticalVelocity = 0;
        isAirborne = false;
      }
    }

    const rollProgress = rollTimeRemaining > 0 ? 1 - rollTimeRemaining / ROLL_DURATION : 0;
    animateRig(
      character,
      delta,
      movement.speed,
      isAirborne,
      verticalVelocity,
      rollTimeRemaining > 0,
      rollProgress,
    );
    updateCamera(character.model, delta);
  }

  renderer.render(scene, camera);
}

loadCharacter()
  .then((rig) => {
    character = rig;
    groundY = rig.model.position.y;

    if (rig.missingBones.length > 0) {
      const warningPanel = document.createElement('div');
      warningPanel.className = 'warning-panel';
      warningPanel.textContent = `Mannequin loaded with partial rig support. Missing joints: ${rig.missingBones.join(', ')}`;
      document.body.append(warningPanel);
    }
  })
  .catch((error: unknown) => {
    const message = error instanceof Error ? error.message : 'Unknown loading error.';
    const errorPanel = document.createElement('div');
    errorPanel.className = 'error-panel';
    errorPanel.textContent = `Failed to load character: ${message}`;
    document.body.append(errorPanel);
  });

animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
