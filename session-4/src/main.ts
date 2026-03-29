import './style.css';

import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { clone } from 'three/examples/jsm/utils/SkeletonUtils.js';

import {
  ACTIONS,
  type ActionName,
  applyExchange,
  createFighter,
  createStrategy,
  distanceBetween,
  EXCHANGE_COOLDOWN,
  type FighterStrategy,
  recoverStamina,
  resetFighters,
  resolveExchange,
  shouldResetRound,
  updateStrategy,
  type FighterRuntime,
} from './combat';
import { fightEvents } from './fightEvents';
import { requestFightDecision, resetStrategies, type LlmDecision } from './llm';

const MODEL_URL = '/assets/mannequin_v4.glb';
const TARGET_MODEL_HEIGHT = 1.82;
const CAMERA_POSITION = new THREE.Vector3(0, 4.6, -9.5);
const CAMERA_LOOK_AT = new THREE.Vector3(0, 1.35, 0);
const FLOOR_RADIUS = 26;
const ROUND_RESET_DELAY = 3.0;
const REQUIRED_CLIPS: ActionName[] = [
  'guard',
  'jab',
  'cross',
  'hook',
  'uppercut',
  'bodyShot',
  'kickL',
  'kickR',
  'slip',
  'block',
  'duck',
  'parry',
  'advance',
  'retreat',
];

type FighterActor = {
  runtime: FighterRuntime;
  strategy: FighterStrategy;
  anchor: THREE.Group;
  mixer: THREE.AnimationMixer;
  actions: Partial<Record<ActionName, THREE.AnimationAction>>;
  koAction: THREE.AnimationAction | null;
};

type DuelState = {
  actorA: FighterActor;
  actorB: FighterActor;
  exchangeCount: number;
  round: number;
  resetTimer: number;
  decisionPending: boolean;
  lastNarrative: string;
  clipWarnings: string[];
  providerStatus: string;
  history: string[];
  lastDecisionA: string;
  lastDecisionB: string;
};

declare global {
  interface Window {
    __session4FightEvents?: typeof fightEvents;
  }
}

const mountElement = document.querySelector<HTMLDivElement>('#app');
const hudElement = document.querySelector<HTMLDivElement>('.hud');

if (!mountElement || !hudElement) {
  throw new Error('Missing application mount nodes.');
}

const mount = mountElement;
const hud = hudElement;

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
mount.append(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color('#d4dde6');
scene.fog = new THREE.Fog('#d4dde6', 12, 36);

const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.copy(CAMERA_POSITION);
camera.lookAt(CAMERA_LOOK_AT);

scene.add(new THREE.HemisphereLight('#fbfbf2', '#607488', 2.2));

const keyLight = new THREE.DirectionalLight('#fff5df', 2.6);
keyLight.position.set(6, 12, -2);
keyLight.castShadow = true;
keyLight.shadow.mapSize.setScalar(2048);
keyLight.shadow.camera.left = -16;
keyLight.shadow.camera.right = 16;
keyLight.shadow.camera.top = 16;
keyLight.shadow.camera.bottom = -16;
scene.add(keyLight);

const rimLight = new THREE.DirectionalLight('#d8e7ff', 1.2);
rimLight.position.set(-9, 7, 6);
scene.add(rimLight);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(FLOOR_RADIUS, 96),
  new THREE.MeshStandardMaterial({
    color: '#446148',
    roughness: 0.94,
    metalness: 0.03,
  }),
);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

const ringFill = new THREE.Mesh(
  new THREE.CircleGeometry(5.8, 96),
  new THREE.MeshStandardMaterial({
    color: '#d9dfdd',
    roughness: 0.88,
    metalness: 0.02,
  }),
);
ringFill.rotation.x = -Math.PI / 2;
ringFill.position.y = 0.015;
ringFill.receiveShadow = true;
scene.add(ringFill);

const ringLine = new THREE.Mesh(
  new THREE.RingGeometry(5.7, 5.92, 96),
  new THREE.MeshBasicMaterial({
    color: '#1f2b35',
    transparent: true,
    opacity: 0.72,
    side: THREE.DoubleSide,
  }),
);
ringLine.rotation.x = -Math.PI / 2;
ringLine.position.y = 0.02;
scene.add(ringLine);

const centerMark = new THREE.Mesh(
  new THREE.RingGeometry(0.1, 0.16, 48),
  new THREE.MeshBasicMaterial({
    color: '#b6503d',
    side: THREE.DoubleSide,
  }),
);
centerMark.rotation.x = -Math.PI / 2;
centerMark.position.y = 0.025;
scene.add(centerMark);

const grid = new THREE.GridHelper(32, 32, '#31404d', '#687787');
grid.position.y = 0.02;
scene.add(grid);

const warningPanel = document.createElement('div');
warningPanel.className = 'warning-panel';
warningPanel.hidden = true;
document.body.append(warningPanel);

const errorPanel = document.createElement('div');
errorPanel.className = 'error-panel';
errorPanel.hidden = true;
document.body.append(errorPanel);

window.__session4FightEvents = fightEvents;

function normalizeModel(model: THREE.Object3D): void {
  const initialBounds = new THREE.Box3().setFromObject(model);
  const size = initialBounds.getSize(new THREE.Vector3());
  const height = Math.max(size.y, 0.001);
  const scale = TARGET_MODEL_HEIGHT / height;
  model.scale.setScalar(scale);

  const scaledBounds = new THREE.Box3().setFromObject(model);
  const center = scaledBounds.getCenter(new THREE.Vector3());
  model.position.x = -center.x;
  model.position.z = -center.z;
  model.position.y = -scaledBounds.min.y;
}

function collectActions(
  mixer: THREE.AnimationMixer,
  clips: THREE.AnimationClip[],
): Partial<Record<ActionName, THREE.AnimationAction>> {
  const actions: Partial<Record<ActionName, THREE.AnimationAction>> = {};

  for (const name of REQUIRED_CLIPS) {
    const clip = clips.find((candidate) => candidate.name === name);

    if (!clip) {
      continue;
    }

    const action = mixer.clipAction(clip);
    action.setLoop(name === 'guard' ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
    action.clampWhenFinished = true;
    action.enabled = true;
    action.setEffectiveWeight(1);
    action.stop();
    actions[name] = action;
  }

  return actions;
}

function tintFighter(model: THREE.Object3D, color: string): void {
  const tint = new THREE.Color(color);

  model.traverse((child) => {
    if (!(child instanceof THREE.Mesh || child instanceof THREE.SkinnedMesh)) {
      return;
    }

    child.castShadow = true;
    child.receiveShadow = true;

    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials) {
      if (!(material instanceof THREE.MeshStandardMaterial)) {
        continue;
      }

      material.color = material.color.clone().lerp(tint, 0.28);
      material.roughness = Math.min(material.roughness + 0.06, 1);
    }
  });
}

function rotateIfFound(model: THREE.Object3D, name: string, x = 0, y = 0, z = 0): void {
  const joint = model.getObjectByName(name);
  if (!joint) {
    return;
  }

  joint.rotation.x += x;
  joint.rotation.y += y;
  joint.rotation.z += z;
}

function applyRelaxedFightStance(model: THREE.Object3D): void {
  // Pull the mannequin out of the bind/T pose before any clips run.
  rotateIfFound(model, 'hips', 0.05, 0, 0);
  rotateIfFound(model, 'spine', -0.06, 0, 0);
  rotateIfFound(model, 'chest', -0.05, 0, 0);
  rotateIfFound(model, 'neck', 0.02, 0, 0);

  rotateIfFound(model, 'clavicleL', 0.08, 0, -0.12);
  rotateIfFound(model, 'clavicleR', 0.08, 0, 0.12);
  rotateIfFound(model, 'upperArmL', -0.25, 0, -1.18);
  rotateIfFound(model, 'upperArmR', -0.25, 0, 1.18);
  rotateIfFound(model, 'lowerArmL', -0.1, 0, -0.4);
  rotateIfFound(model, 'lowerArmR', -0.1, 0, 0.4);

  rotateIfFound(model, 'upperLegL', 0.06, 0, 0.04);
  rotateIfFound(model, 'upperLegR', 0.06, 0, -0.04);
  rotateIfFound(model, 'lowerLegL', 0.12, 0, 0);
  rotateIfFound(model, 'lowerLegR', 0.12, 0, 0);
  rotateIfFound(model, 'footL', -0.08, 0, 0);
  rotateIfFound(model, 'footR', -0.08, 0, 0);
}

function createActor(
  template: THREE.Object3D,
  clips: THREE.AnimationClip[],
  runtime: FighterRuntime,
  rotationY: number,
  tint: string,
): FighterActor {
  const anchor = new THREE.Group();
  const model = clone(template);
  const mixer = new THREE.AnimationMixer(model);
  const actions = collectActions(mixer, clips);

  tintFighter(model, tint);
  applyRelaxedFightStance(model);
  model.rotation.y = rotationY;
  anchor.position.set(0, 0, runtime.positionZ);
  anchor.add(model);
  scene.add(anchor);

  // Set up KO animation clip
  const koClip = clips.find((c) => c.name === 'ko');
  let koAction: THREE.AnimationAction | null = null;
  if (koClip) {
    koAction = mixer.clipAction(koClip);
    koAction.loop = THREE.LoopOnce;
    koAction.clampWhenFinished = true;
  }

  const actor: FighterActor = {
    runtime,
    strategy: createStrategy(),
    anchor,
    mixer,
    actions,
    koAction,
  };

  playAction(actor, 'guard', true);
  mixer.update(1 / 60);
  return actor;
}

function playAction(actor: FighterActor, actionName: ActionName, immediate = false): void {
  const nextClip = ACTIONS[actionName].clipName;
  const currentClip = ACTIONS[actor.runtime.currentAction].clipName;
  const nextAction = actor.actions[nextClip] ?? actor.actions.guard;
  const currentAction = actor.actions[currentClip];

  actor.runtime.currentAction = actionName;

  if (!nextAction) {
    return;
  }

  if (currentAction && currentAction !== nextAction) {
    if (immediate) {
      currentAction.stop();
    } else {
      currentAction.fadeOut(0.08);
    }
  }

  nextAction.reset();
  nextAction.paused = false;
  nextAction.enabled = true;
  nextAction.setEffectiveTimeScale(1);
  nextAction.setEffectiveWeight(1);
  nextAction.fadeIn(immediate ? 0 : 0.08);
  nextAction.play();

  if (immediate) {
    actor.mixer.update(1 / 60);
  }
}

function updateActorTransform(actor: FighterActor, delta: number): void {
  actor.anchor.position.z += (actor.runtime.positionZ - actor.anchor.position.z) * (1 - Math.exp(-delta * 8));
}

function updateHud(duel: DuelState): void {
  const { actorA, actorB } = duel;
  const distance = distanceBetween(actorA.runtime, actorB.runtime);

  hud.innerHTML = `
    <p class="eyebrow">Session 4</p>
    <h1>AI Fight Study</h1>
    <p class="instructions">Two mannequins now pick boxing actions from the embedded v4 clips and resolve each exchange deterministically.</p>
    <div class="scoreboard">
      <section class="fighter-card fighter-card-a">
        <h2>${actorA.runtime.name}</h2>
        <p class="fighter-meta">Wins ${actorA.runtime.wins} · HP ${actorA.runtime.hp} · STA ${Math.round(actorA.runtime.stamina)}</p>
        <div class="bar"><span class="bar-fill bar-fill-hp" style="width:${actorA.runtime.hp}%"></span></div>
        <div class="bar"><span class="bar-fill bar-fill-stamina" style="width:${actorA.runtime.stamina}%"></span></div>
        <p class="fighter-action">Action: ${actorA.runtime.currentAction}</p>
        <p class="fighter-action">Decision: ${duel.lastDecisionA}</p>
      </section>
      <section class="fighter-card fighter-card-b">
        <h2>${actorB.runtime.name}</h2>
        <p class="fighter-meta">Wins ${actorB.runtime.wins} · HP ${actorB.runtime.hp} · STA ${Math.round(actorB.runtime.stamina)}</p>
        <div class="bar"><span class="bar-fill bar-fill-hp" style="width:${actorB.runtime.hp}%"></span></div>
        <div class="bar"><span class="bar-fill bar-fill-stamina" style="width:${actorB.runtime.stamina}%"></span></div>
        <p class="fighter-action">Action: ${actorB.runtime.currentAction}</p>
        <p class="fighter-action">Decision: ${duel.lastDecisionB}</p>
      </section>
    </div>
    <p class="logline">Round ${duel.round} · Exchange ${duel.exchangeCount} · Distance ${distance.toFixed(2)}m · ${duel.providerStatus} · ${duel.lastNarrative}</p>
    <div class="event-log">${duel.history.map((entry) => `<p>${entry}</p>`).join('')}</div>
  `;

  warningPanel.hidden = duel.clipWarnings.length === 0;
  warningPanel.textContent = duel.clipWarnings.length === 0
    ? ''
    : `Mannequin loaded with partial clip support. Missing clips: ${duel.clipWarnings.join(', ')}`;
}

async function loadModel(): Promise<{ scene: THREE.Object3D; animations: THREE.AnimationClip[] }> {
  const loader = new GLTFLoader();
  const gltf = await loader.loadAsync(MODEL_URL);
  normalizeModel(gltf.scene);
  return { scene: gltf.scene, animations: gltf.animations };
}

async function createDuel(): Promise<DuelState> {
  // Load GLB twice so each fighter owns its scene graph and bone bindings work
  const [modelA, modelB] = await Promise.all([loadModel(), loadModel()]);

  const runtimeA = createFighter('Alpha', -1.5);
  const runtimeB = createFighter('Beta', 1.5);
  const actorA = createActor(modelA.scene, modelA.animations, runtimeA, 0, '#4f76a8');
  const actorB = createActor(modelB.scene, modelB.animations, runtimeB, Math.PI, '#a86457');
  const clipWarnings = REQUIRED_CLIPS.filter(
    (clipName) => !modelA.animations.some((clip: THREE.AnimationClip) => clip.name === clipName),
  );

  return {
    actorA,
    actorB,
    exchangeCount: 0,
    round: 1,
    resetTimer: 0,
    decisionPending: false,
    lastNarrative: 'Fighters enter guard.',
    clipWarnings,
    providerStatus: 'Anthropic vs OpenAI',
    history: ['System: fight runtime ready.'],
    lastDecisionA: 'Awaiting Anthropic.',
    lastDecisionB: 'Awaiting OpenAI.',
  };
}

async function requestExchange(duel: DuelState): Promise<void> {
  const { actorA, actorB } = duel;
  duel.decisionPending = true;
  duel.providerStatus = 'Requesting Anthropic and OpenAI decisions';
  fightEvents.emit('decisionRequested', {
    round: duel.round,
    exchange: duel.exchangeCount + 1,
  });
  updateHud(duel);

  const [decisionA, decisionB] = await Promise.all([
    requestFightDecision('anthropic', {
      fighter: actorA.runtime,
      opponent: actorB.runtime,
      round: duel.round,
      exchange: duel.exchangeCount + 1,
    }),
    requestFightDecision('openai', {
      fighter: actorB.runtime,
      opponent: actorA.runtime,
      round: duel.round,
      exchange: duel.exchangeCount + 1,
    }),
  ]);

  const actionA = decisionA.action;
  const actionB = decisionB.action;
  duel.lastDecisionA = `${decisionA.provider}:${actionA} (${decisionA.source})`;
  duel.lastDecisionB = `${decisionB.provider}:${actionB} (${decisionB.source})`;
  fightEvents.emit('decisionResolved', {
    fighter: actorA.runtime.name,
    provider: decisionA.provider,
    action: actionA,
    reasoning: decisionA.reasoning,
    source: decisionA.source,
  });
  fightEvents.emit('decisionResolved', {
    fighter: actorB.runtime.name,
    provider: decisionB.provider,
    action: actionB,
    reasoning: decisionB.reasoning,
    source: decisionB.source,
  });
  const outcome = resolveExchange(
    actionA,
    actionB,
    distanceBetween(actorA.runtime, actorB.runtime),
  );

  applyExchange(actorA.runtime, actorB.runtime, outcome);

  // Update strategies based on exchange results
  const outcomeForA = outcome.damageB > 0 ? 'hit' : outcome.outcome === 'a_defends' ? 'defended' : outcome.damageA > 0 ? 'missed' : 'neutral';
  const outcomeForB = outcome.damageA > 0 ? 'hit' : outcome.outcome === 'b_defends' ? 'defended' : outcome.damageB > 0 ? 'missed' : 'neutral';
  updateStrategy(actorA.strategy, actorA.runtime, actorB.runtime, outcomeForA as 'hit' | 'missed' | 'defended' | 'neutral');
  updateStrategy(actorB.strategy, actorB.runtime, actorA.runtime, outcomeForB as 'hit' | 'missed' | 'defended' | 'neutral');

  playAction(actorA, actionA);
  playAction(actorB, actionB);

  actorA.runtime.actionTimer = Math.max(outcome.actionA.duration, EXCHANGE_COOLDOWN);
  actorB.runtime.actionTimer = Math.max(outcome.actionB.duration, EXCHANGE_COOLDOWN);
  duel.exchangeCount += 1;
  duel.lastNarrative = `${outcome.narrative} Alpha:${decisionA.reasoning || actionA}. Beta:${decisionB.reasoning || actionB}.`;
  duel.providerStatus = providerStatusLabel(decisionA, decisionB);
  duel.decisionPending = false;
  fightEvents.emit('exchangeResolved', {
    round: duel.round,
    exchange: duel.exchangeCount,
    narrative: duel.lastNarrative,
  });
}

function providerStatusLabel(decisionA: LlmDecision, decisionB: LlmDecision): string {
  const labelA = decisionA.source === 'remote' ? 'Anthropic' : 'Anthropic fallback';
  const labelB = decisionB.source === 'remote' ? 'OpenAI' : 'OpenAI fallback';
  return `${labelA} vs ${labelB}`;
}

const clock = new THREE.Clock();
let duel: DuelState | null = null;

function pushHistory(duelState: DuelState, line: string): void {
  duelState.history = [line, ...duelState.history].slice(0, 6);
}

fightEvents.on('decisionRequested', ({ round, exchange }) => {
  if (!duel) {
    return;
  }

  pushHistory(duel, `Round ${round} exchange ${exchange}: requesting decisions.`);
});

fightEvents.on('decisionResolved', ({ fighter, provider, action, source }) => {
  if (!duel) {
    return;
  }

  pushHistory(duel, `${fighter}: ${provider} chose ${action} (${source}).`);
});

fightEvents.on('exchangeResolved', ({ round, exchange, narrative }) => {
  if (!duel) {
    return;
  }

  pushHistory(duel, `Round ${round} exchange ${exchange}: ${narrative}`);
});

fightEvents.on('knockout', ({ round, winner }) => {
  if (!duel) {
    return;
  }

  pushHistory(duel, `Round ${round}: ${winner} scored the knockout.`);
});

fightEvents.on('roundReset', ({ round }) => {
  if (!duel) {
    return;
  }

  pushHistory(duel, `Round ${round}: reset to guard.`);
});

fightEvents.on('annotation', ({ message }) => {
  if (!duel) {
    return;
  }

  pushHistory(duel, `Note: ${message}`);
});

function animate(): void {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.05);

  if (duel) {
    const { actorA, actorB } = duel;

    actorA.mixer.update(delta);
    actorB.mixer.update(delta);
    recoverStamina(actorA.runtime, delta);
    recoverStamina(actorB.runtime, delta);

    actorA.runtime.actionTimer = Math.max(0, actorA.runtime.actionTimer - delta);
    actorB.runtime.actionTimer = Math.max(0, actorB.runtime.actionTimer - delta);

    if (duel.resetTimer > 0) {
      duel.resetTimer = Math.max(0, duel.resetTimer - delta);
      if (duel.resetTimer === 0) {
        resetFighters(actorA.runtime, actorB.runtime);
        actorA.strategy = createStrategy();
        actorB.strategy = createStrategy();
        resetStrategies();
        // Stop KO animation and reset to guard
        actorA.mixer.stopAllAction();
        actorB.mixer.stopAllAction();
        playAction(actorA, 'guard', true);
        playAction(actorB, 'guard', true);
        duel.exchangeCount = 0;
        duel.round += 1;
        duel.decisionPending = false;
        duel.lastNarrative = 'New round begins from guard.';
        duel.lastDecisionA = 'Awaiting Anthropic.';
        duel.lastDecisionB = 'Awaiting OpenAI.';
        fightEvents.emit('roundReset', { round: duel.round });
      }
    } else if (shouldResetRound(actorA.runtime, actorB.runtime)) {
      const loser = actorA.runtime.hp <= actorB.runtime.hp ? actorA : actorB;
      const winner = loser === actorA ? actorB : actorA;
      winner.runtime.wins += 1;
      duel.lastNarrative = `${winner.runtime.name} scores the knockout.`;
      fightEvents.emit('knockout', {
        round: duel.round,
        winner: winner.runtime.name,
      });

      // Play KO animation on the loser
      if (loser.koAction) {
        // Stop all current actions on the loser's mixer
        loser.mixer.stopAllAction();
        loser.koAction.reset();
        loser.koAction.play();
      }

      duel.resetTimer = ROUND_RESET_DELAY;
    } else if (!duel.decisionPending && actorA.runtime.actionTimer === 0 && actorB.runtime.actionTimer === 0) {
      void requestExchange(duel);
    }

    if (actorA.runtime.actionTimer === 0 && actorA.runtime.currentAction !== 'guard') {
      playAction(actorA, 'guard');
    }

    if (actorB.runtime.actionTimer === 0 && actorB.runtime.currentAction !== 'guard') {
      playAction(actorB, 'guard');
    }

    updateActorTransform(actorA, delta);
    updateActorTransform(actorB, delta);
    updateHud(duel);
  }

  camera.position.lerp(CAMERA_POSITION, 1 - Math.exp(-delta * 3));
  camera.lookAt(CAMERA_LOOK_AT);
  renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

createDuel()
  .then((state) => {
    duel = state;
    updateHud(state);
  })
  .catch((error: unknown) => {
    const message = error instanceof Error ? error.message : 'Unknown loading error.';
    errorPanel.hidden = false;
    errorPanel.textContent = `Failed to load fight scene: ${message}`;
  });

animate();
