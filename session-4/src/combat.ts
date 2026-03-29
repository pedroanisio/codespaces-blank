export type ActionName =
  | 'guard'
  | 'jab'
  | 'cross'
  | 'hook'
  | 'earSlap'
  | 'uppercut'
  | 'bodyShot'
  | 'sideKick'
  | 'headKick'
  | 'kickL'
  | 'kickR'
  | 'slip'
  | 'block'
  | 'duck'
  | 'parry'
  | 'advance'
  | 'retreat';

export type ActionKind = 'stance' | 'attack' | 'defense' | 'movement';

export type CombatAction = {
  name: ActionName;
  kind: ActionKind;
  staminaCost: number;
  clipName: ActionName;
  duration: number;
  speed?: number;
  power?: number;
  reach?: number;
  defenseVs?: ActionName[];
  forwardStep?: number;
};

export type FighterRuntime = {
  name: string;
  hp: number;
  stamina: number;
  positionZ: number;
  currentAction: ActionName;
  actionTimer: number;
  wins: number;
};

export type ExchangeOutcome = {
  actionA: CombatAction;
  actionB: CombatAction;
  damageA: number;
  damageB: number;
  costA: number;
  costB: number;
  positionDeltaA: number;
  positionDeltaB: number;
  narrative: string;
  outcome:
    | 'neutral'
    | 'a_wins'
    | 'b_wins'
    | 'a_defends'
    | 'b_defends'
    | 'a_grazes'
    | 'b_grazes';
};

export const FIGHTER_MAX_HP = 100;
export const FIGHTER_MAX_STAMINA = 100;
export const ATTACK_RANGE = 2.45;
export const BODYSHOT_RANGE = 2.15;
export const EXCHANGE_COOLDOWN = 0.85;
export const KNOCKOUT_HP = 0;

export const ACTIONS: Record<ActionName, CombatAction> = {
  guard: {
    name: 'guard',
    kind: 'stance',
    staminaCost: 0,
    clipName: 'guard',
    duration: 0.9,
  },
  jab: {
    name: 'jab',
    kind: 'attack',
    staminaCost: 5,
    clipName: 'jab',
    duration: 0.48,
    speed: 9,
    power: 12,
    reach: 2.45,
  },
  cross: {
    name: 'cross',
    kind: 'attack',
    staminaCost: 10,
    clipName: 'cross',
    duration: 0.62,
    speed: 7,
    power: 22,
    reach: 2.55,
  },
  hook: {
    name: 'hook',
    kind: 'attack',
    staminaCost: 14,
    clipName: 'hook',
    duration: 0.72,
    speed: 5,
    power: 28,
    reach: 2.2,
  },
  earSlap: {
    name: 'earSlap',
    kind: 'attack',
    staminaCost: 11,
    clipName: 'hook',
    duration: 0.64,
    speed: 8,
    power: 20,
    reach: 2.28,
  },
  uppercut: {
    name: 'uppercut',
    kind: 'attack',
    staminaCost: 16,
    clipName: 'uppercut',
    duration: 0.76,
    speed: 4,
    power: 30,
    reach: 2.1,
  },
  bodyShot: {
    name: 'bodyShot',
    kind: 'attack',
    staminaCost: 10,
    clipName: 'bodyShot',
    duration: 0.68,
    speed: 6,
    power: 18,
    reach: 2.15,
  },
  sideKick: {
    name: 'sideKick',
    kind: 'attack',
    staminaCost: 17,
    clipName: 'kickL',
    duration: 0.74,
    speed: 5,
    power: 32,
    reach: 2.75,
  },
  headKick: {
    name: 'headKick',
    kind: 'attack',
    staminaCost: 20,
    clipName: 'kickR',
    duration: 0.8,
    speed: 4,
    power: 38,
    reach: 2.82,
  },
  kickL: {
    name: 'kickL',
    kind: 'attack',
    staminaCost: 18,
    clipName: 'kickL',
    duration: 0.72,
    speed: 3,
    power: 35,
    reach: 2.7,
  },
  kickR: {
    name: 'kickR',
    kind: 'attack',
    staminaCost: 18,
    clipName: 'kickR',
    duration: 0.72,
    speed: 3,
    power: 35,
    reach: 2.7,
  },
  slip: {
    name: 'slip',
    kind: 'defense',
    staminaCost: 4,
    clipName: 'slip',
    duration: 0.54,
    defenseVs: ['jab', 'cross'],
  },
  block: {
    name: 'block',
    kind: 'defense',
    staminaCost: 6,
    clipName: 'block',
    duration: 0.58,
    defenseVs: ['hook', 'earSlap', 'cross', 'jab', 'sideKick', 'headKick', 'kickL', 'kickR'],
  },
  duck: {
    name: 'duck',
    kind: 'defense',
    staminaCost: 6,
    clipName: 'duck',
    duration: 0.58,
    defenseVs: ['hook', 'earSlap', 'jab', 'sideKick', 'headKick', 'kickL', 'kickR'],
  },
  parry: {
    name: 'parry',
    kind: 'defense',
    staminaCost: 3,
    clipName: 'parry',
    duration: 0.5,
    defenseVs: ['jab', 'cross', 'bodyShot'],
  },
  advance: {
    name: 'advance',
    kind: 'movement',
    staminaCost: 3,
    clipName: 'advance',
    duration: 0.52,
    forwardStep: 0.42,
  },
  retreat: {
    name: 'retreat',
    kind: 'movement',
    staminaCost: 3,
    clipName: 'retreat',
    duration: 0.52,
    forwardStep: -0.48,
  },
};

export const AI_ACTION_POOL: ActionName[] = [
  'jab',
  'cross',
  'hook',
  'earSlap',
  'uppercut',
  'bodyShot',
  'sideKick',
  'headKick',
  'kickL',
  'kickR',
  'slip',
  'block',
  'duck',
  'parry',
  'advance',
  'retreat',
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function weightedPick<T>(options: Array<{ value: T; weight: number }>, rng: () => number): T {
  const total = options.reduce((sum, option) => sum + option.weight, 0);

  if (total <= 0) {
    return options[0]!.value;
  }

  let cursor = rng() * total;
  for (const option of options) {
    cursor -= option.weight;
    if (cursor <= 0) {
      return option.value;
    }
  }

  return options[options.length - 1]!.value;
}

// ─── Strategy Layer ─────────────────────────────────────────────────

export type FightPhase = 'close_in' | 'engage' | 'pressure' | 'defensive' | 'finishing';

export type FighterStrategy = {
  phase: FightPhase;
  comboStep: number;
  comboChain: ActionName[];
  opponentHistory: ActionName[];
  lastAction: ActionName;
  consecutiveHits: number;
  consecutiveMisses: number;
};

const COMBO_CHAINS: ActionName[][] = [
  ['jab', 'cross', 'hook'],
  ['jab', 'earSlap', 'cross'],
  ['jab', 'jab', 'cross'],
  ['jab', 'bodyShot', 'uppercut'],
  ['jab', 'sideKick', 'retreat'],
  ['cross', 'hook', 'kickL'],
  ['jab', 'kickR', 'retreat'],
  ['bodyShot', 'uppercut', 'cross'],
  ['kickL', 'jab', 'cross'],
  ['sideKick', 'jab', 'cross'],
  ['hook', 'bodyShot', 'kickR'],
  ['bodyShot', 'headKick', 'retreat'],
];

const MAX_HISTORY = 8;

export function createStrategy(): FighterStrategy {
  return {
    phase: 'close_in',
    comboStep: 0,
    comboChain: [],
    opponentHistory: [],
    lastAction: 'guard',
    consecutiveHits: 0,
    consecutiveMisses: 0,
  };
}

export function updateStrategy(
  strategy: FighterStrategy,
  fighter: FighterRuntime,
  opponent: FighterRuntime,
  lastOutcome: 'hit' | 'missed' | 'defended' | 'neutral',
): void {
  const distance = distanceBetween(fighter, opponent);

  // Track hits/misses for phase transitions
  if (lastOutcome === 'hit') {
    strategy.consecutiveHits++;
    strategy.consecutiveMisses = 0;
  } else if (lastOutcome === 'missed' || lastOutcome === 'defended') {
    strategy.consecutiveMisses++;
    strategy.consecutiveHits = 0;
  }

  // Record opponent action
  strategy.opponentHistory.push(opponent.currentAction);
  if (strategy.opponentHistory.length > MAX_HISTORY) {
    strategy.opponentHistory.shift();
  }

  // Determine fight phase
  if (opponent.hp <= 25) {
    strategy.phase = 'finishing';
  } else if (fighter.hp <= 30 || fighter.stamina <= 15) {
    strategy.phase = 'defensive';
  } else if (distance > ATTACK_RANGE) {
    strategy.phase = 'close_in';
  } else if (strategy.consecutiveHits >= 2 || opponent.hp <= 50) {
    strategy.phase = 'pressure';
  } else {
    strategy.phase = 'engage';
  }

  // Reset combo if phase changed to defensive or close_in
  if (strategy.phase === 'defensive' || strategy.phase === 'close_in') {
    strategy.comboStep = 0;
    strategy.comboChain = [];
  }
}

function opponentFavors(history: ActionName[], kind: ActionKind): number {
  if (history.length === 0) return 0;
  const recent = history.slice(-4);
  return recent.filter((a) => ACTIONS[a].kind === kind).length / recent.length;
}

function pickCounter(history: ActionName[]): ActionName | null {
  const attackRate = opponentFavors(history, 'attack');
  const defenseRate = opponentFavors(history, 'defense');

  if (attackRate >= 0.6) {
    // Opponent is aggressive — counter with defense
    const lastAttack = [...history].reverse().find((a) => ACTIONS[a].kind === 'attack');
    if (lastAttack === 'jab' || lastAttack === 'cross') return 'slip';
    if (lastAttack === 'hook' || lastAttack === 'earSlap' || lastAttack === 'sideKick' || lastAttack === 'headKick' || lastAttack === 'kickL' || lastAttack === 'kickR') return 'duck';
    if (lastAttack === 'bodyShot') return 'parry';
    return 'block';
  }

  if (defenseRate >= 0.5) {
    // Opponent is defensive — use kicks or bodyshots to break through
    return 'kickL';
  }

  return null;
}

export function chooseStrategicAction(
  strategy: FighterStrategy,
  fighter: FighterRuntime,
  opponent: FighterRuntime,
  rng: () => number = Math.random,
): ActionName {
  const distance = distanceBetween(fighter, opponent);
  const inRange = distance <= ATTACK_RANGE;
  const tightRange = distance <= BODYSHOT_RANGE;

  const affordable = (name: ActionName) => canAfford(ACTIONS[name], fighter);

  // ── Phase: Close In ──
  if (strategy.phase === 'close_in') {
    if (affordable('advance')) {
      // Mix in feint jabs while advancing
      return rng() < 0.75 ? 'advance' : affordable('jab') ? 'jab' : 'advance';
    }
    return 'guard';
  }

  // ── Phase: Finishing ──
  if (strategy.phase === 'finishing') {
    // All-out aggression with highest damage moves
    const finisherCandidates: Array<{ value: ActionName; weight: number }> = [
      { value: 'cross', weight: affordable('cross') ? 4 : 0 },
      { value: 'hook', weight: affordable('hook') && tightRange ? 5 : 0 },
      { value: 'earSlap', weight: affordable('earSlap') && inRange ? 4.5 : 0 },
      { value: 'uppercut', weight: affordable('uppercut') && tightRange ? 6 : 0 },
      { value: 'sideKick', weight: affordable('sideKick') && inRange ? 4.2 : 0 },
      { value: 'headKick', weight: affordable('headKick') && inRange ? 3.8 : 0 },
      { value: 'kickL', weight: affordable('kickL') && inRange ? 4 : 0 },
      { value: 'kickR', weight: affordable('kickR') && inRange ? 4 : 0 },
      { value: 'jab', weight: affordable('jab') && inRange ? 2 : 0 },
      { value: 'advance', weight: !inRange && affordable('advance') ? 5 : 0 },
    ];
    const finishers = finisherCandidates.filter((o) => o.weight > 0);

    if (finishers.length > 0) return weightedPick(finishers, rng);
    return 'guard';
  }

  // ── Phase: Defensive ──
  if (strategy.phase === 'defensive') {
    // Retreat and recover stamina, throw counters opportunistically
    const counter = pickCounter(strategy.opponentHistory);
    if (counter && affordable(counter) && rng() < 0.5) return counter;

    if (fighter.stamina <= 20) return 'guard';
    if (distance <= BODYSHOT_RANGE && affordable('retreat')) return rng() < 0.6 ? 'retreat' : 'block';
    if (affordable('retreat') && rng() < 0.4) return 'retreat';
    if (affordable('block')) return 'block';
    return 'guard';
  }

  // ── Phase: Pressure (opponent is hurt or we're on a streak) ──
  if (strategy.phase === 'pressure') {
    // Continue combo if active
    if (strategy.comboChain.length > 0 && strategy.comboStep < strategy.comboChain.length) {
      const next = strategy.comboChain[strategy.comboStep];
      if (affordable(next) && inRange) {
        strategy.comboStep++;
        return next;
      }
    }

    // Start a new combo
    if (strategy.comboStep === 0 || strategy.comboStep >= strategy.comboChain.length) {
      const chain = COMBO_CHAINS[Math.floor(rng() * COMBO_CHAINS.length)];
      if (affordable(chain[0])) {
        strategy.comboChain = chain;
        strategy.comboStep = 1;
        return chain[0];
      }
    }

    // Fallback: fast attacks
    if (affordable('jab') && inRange) return 'jab';
    if (affordable('advance') && !inRange) return 'advance';
    return 'guard';
  }

  // ── Phase: Engage (standard fighting) ──

  // Try to read and counter opponent patterns
  const counter = pickCounter(strategy.opponentHistory);
  if (counter && affordable(counter) && rng() < 0.35) return counter;

  // Start a combo ~40% of the time
  if (inRange && rng() < 0.4 && strategy.comboStep === 0) {
    const chain = COMBO_CHAINS[Math.floor(rng() * COMBO_CHAINS.length)];
    if (affordable(chain[0])) {
      strategy.comboChain = chain;
      strategy.comboStep = 1;
      return chain[0];
    }
  }

  // Continue active combo
  if (strategy.comboChain.length > 0 && strategy.comboStep < strategy.comboChain.length) {
    const next = strategy.comboChain[strategy.comboStep];
    if (affordable(next) && inRange) {
      strategy.comboStep++;
      return next;
    }
    // Combo broken — reset
    strategy.comboStep = 0;
    strategy.comboChain = [];
  }

  // Situational picks
  const weightedOptions: Array<{ value: ActionName; weight: number }> = [
    { value: 'jab', weight: inRange ? 5 : 1 },
    { value: 'cross', weight: inRange ? 3 : 0.5 },
    { value: 'hook', weight: tightRange ? 3 : 0.3 },
    { value: 'earSlap', weight: inRange ? 2.8 : 0.35 },
    { value: 'uppercut', weight: tightRange ? 2 : 0.2 },
    { value: 'bodyShot', weight: tightRange ? 2.5 : 0.3 },
    { value: 'sideKick', weight: inRange ? 2.3 : 0.7 },
    { value: 'headKick', weight: inRange ? 1.8 : 0.45 },
    { value: 'kickL', weight: inRange ? 1.8 : 0.5 },
    { value: 'kickR', weight: inRange ? 1.8 : 0.5 },
    { value: 'slip', weight: inRange ? 1.5 : 0.3 },
    { value: 'block', weight: inRange ? 1.2 : 0.3 },
    { value: 'duck', weight: inRange ? 1 : 0.2 },
    { value: 'parry', weight: inRange ? 1 : 0.2 },
    { value: 'advance', weight: !inRange ? 4 : 0.5 },
    { value: 'retreat', weight: tightRange ? 1.5 : 0.3 },
  ];
  const options = weightedOptions
    .filter((o) => affordable(o.value))
    .filter((o) => o.weight > 0);

  if (options.length === 0) return 'guard';
  return weightedPick(options, rng);
}

export function createFighter(name: string, positionZ: number): FighterRuntime {
  return {
    name,
    hp: FIGHTER_MAX_HP,
    stamina: FIGHTER_MAX_STAMINA,
    positionZ,
    currentAction: 'guard',
    actionTimer: 0,
    wins: 0,
  };
}

export function distanceBetween(a: FighterRuntime, b: FighterRuntime): number {
  return Math.abs(a.positionZ - b.positionZ);
}

export function recoverStamina(fighter: FighterRuntime, delta: number): void {
  const regenRate = fighter.currentAction === 'guard' ? 16 : 10;
  fighter.stamina = clamp(fighter.stamina + delta * regenRate, 0, FIGHTER_MAX_STAMINA);
}

function canAfford(action: CombatAction, fighter: FighterRuntime): boolean {
  return fighter.stamina >= action.staminaCost;
}

export function chooseAiAction(
  fighter: FighterRuntime,
  opponent: FighterRuntime,
  rng: () => number = Math.random,
): ActionName {
  const distance = distanceBetween(fighter, opponent);
  const opponentLow = opponent.hp <= 35;
  const selfLow = fighter.hp <= 35;
  const staminaLow = fighter.stamina <= 18;
  const inBoxingRange = distance <= ATTACK_RANGE;
  const tightRange = distance <= BODYSHOT_RANGE;

  const candidates = AI_ACTION_POOL
    .map((name) => ACTIONS[name])
    .filter((action) => canAfford(action, fighter))
    .map((action) => {
      let weight = 1;

      if (action.kind === 'attack') {
        weight += inBoxingRange ? 3 : 0;
        weight += tightRange && action.name === 'bodyShot' ? 2.5 : 0;
        weight += inBoxingRange && action.name === 'earSlap' ? 2.2 : 0;
        weight += inBoxingRange && action.name === 'sideKick' ? 1.9 : 0;
        weight += inBoxingRange && action.name === 'headKick' ? 1.5 : 0;
        weight += opponentLow ? 1.5 : 0;
        weight -= staminaLow ? 2.5 : 0;
      }

      if (action.kind === 'movement') {
        weight += inBoxingRange ? (action.name === 'retreat' && selfLow ? 3 : 0.5) : action.name === 'advance' ? 4 : 0.6;
      }

      if (action.kind === 'defense') {
        weight += selfLow ? 2.4 : 0.6;
        weight += opponent.currentAction === 'advance' ? 0.3 : 1;
      }

      if (action.name === 'jab') {
        weight += 1.5;
      }

      if (action.name === 'cross' && !inBoxingRange) {
        weight -= 1.5;
      }

      if ((action.name === 'hook' || action.name === 'uppercut') && !tightRange) {
        weight -= 2.2;
      }

      if (action.name === 'earSlap' && !inBoxingRange) {
        weight -= 1.8;
      }

      if ((action.name === 'sideKick' || action.name === 'headKick') && !inBoxingRange) {
        weight -= 1.4;
      }

      return {
        value: action.name,
        weight: Math.max(weight, 0.05),
      };
    });

  if (candidates.length === 0) {
    return 'guard';
  }

  if (staminaLow && rng() < 0.55) {
    return selfLow ? 'retreat' : 'guard';
  }

  if (!inBoxingRange && rng() < 0.7) {
    return candidates.some((candidate) => candidate.value === 'advance') ? 'advance' : 'guard';
  }

  return weightedPick(candidates, rng);
}

function attackInRange(action: CombatAction, distance: number): boolean {
  return distance <= (action.reach ?? ATTACK_RANGE);
}

export function resolveExchange(actionAName: ActionName, actionBName: ActionName, distance: number): ExchangeOutcome {
  const actionA = ACTIONS[actionAName];
  const actionB = ACTIONS[actionBName];
  let damageA = 0;
  let damageB = 0;
  let outcome: ExchangeOutcome['outcome'] = 'neutral';
  let narrative = 'Both fighters reset.';

  const attackA = actionA.kind === 'attack' && attackInRange(actionA, distance);
  const attackB = actionB.kind === 'attack' && attackInRange(actionB, distance);

  if (actionA.kind === 'attack' && actionB.kind === 'attack') {
    if (!attackA && !attackB) {
      narrative = 'Both punches fall short.';
    } else if (!attackA) {
      damageA = Math.round((actionB.power ?? 0) * 0.7);
      narrative = `${actionB.name} lands while ${actionA.name} falls short.`;
      outcome = 'b_wins';
    } else if (!attackB) {
      damageB = Math.round((actionA.power ?? 0) * 0.7);
      narrative = `${actionA.name} lands while ${actionB.name} falls short.`;
      outcome = 'a_wins';
    } else if ((actionA.speed ?? 0) >= (actionB.speed ?? 0)) {
      damageB = actionA.power ?? 0;
      damageA = Math.round((actionB.power ?? 0) * 0.5);
      narrative = `${actionA.name} lands first and beats ${actionB.name}.`;
      outcome = 'a_wins';
    } else {
      damageA = actionB.power ?? 0;
      damageB = Math.round((actionA.power ?? 0) * 0.5);
      narrative = `${actionB.name} lands first and beats ${actionA.name}.`;
      outcome = 'b_wins';
    }
  } else if (actionA.kind === 'attack' && actionB.kind === 'defense') {
    if (!attackA) {
      narrative = `${actionA.name} misses outside range.`;
    } else if (actionB.defenseVs?.includes(actionA.name)) {
      narrative = `${actionB.name} neutralizes ${actionA.name}.`;
      outcome = 'b_defends';
    } else {
      damageB = Math.round((actionA.power ?? 0) * 0.7);
      narrative = `${actionA.name} beats the wrong defense.`;
      outcome = 'a_wins';
    }
  } else if (actionB.kind === 'attack' && actionA.kind === 'defense') {
    if (!attackB) {
      narrative = `${actionB.name} misses outside range.`;
    } else if (actionA.defenseVs?.includes(actionB.name)) {
      narrative = `${actionA.name} neutralizes ${actionB.name}.`;
      outcome = 'a_defends';
    } else {
      damageA = Math.round((actionB.power ?? 0) * 0.7);
      narrative = `${actionB.name} beats the wrong defense.`;
      outcome = 'b_wins';
    }
  } else if (actionA.kind === 'attack' && actionB.kind === 'stance') {
    if (!attackA) {
      narrative = `${actionA.name} misses outside range.`;
    } else {
      damageB = Math.round((actionA.power ?? 0) * 0.85);
      narrative = `${actionA.name} lands on a passive guard.`;
      outcome = 'a_wins';
    }
  } else if (actionB.kind === 'attack' && actionA.kind === 'stance') {
    if (!attackB) {
      narrative = `${actionB.name} misses outside range.`;
    } else {
      damageA = Math.round((actionB.power ?? 0) * 0.85);
      narrative = `${actionB.name} lands on a passive guard.`;
      outcome = 'b_wins';
    }
  } else if (actionA.kind === 'attack' && actionB.kind === 'movement') {
    if (!attackA) {
      narrative = `${actionA.name} does not reach.`;
    } else if (actionB.name === 'retreat') {
      damageB = Math.round((actionA.power ?? 0) * 0.3);
      narrative = `${actionA.name} clips the retreat.`;
      outcome = 'a_grazes';
    } else {
      damageB = Math.round((actionA.power ?? 0) * 1.1);
      narrative = `${actionB.name} walks into ${actionA.name}.`;
      outcome = 'a_wins';
    }
  } else if (actionB.kind === 'attack' && actionA.kind === 'movement') {
    if (!attackB) {
      narrative = `${actionB.name} does not reach.`;
    } else if (actionA.name === 'retreat') {
      damageA = Math.round((actionB.power ?? 0) * 0.3);
      narrative = `${actionB.name} clips the retreat.`;
      outcome = 'b_grazes';
    } else {
      damageA = Math.round((actionB.power ?? 0) * 1.1);
      narrative = `${actionA.name} walks into ${actionB.name}.`;
      outcome = 'b_wins';
    }
  } else {
    narrative = 'Both fighters reposition cautiously.';
  }

  return {
    actionA,
    actionB,
    damageA,
    damageB,
    costA: actionA.staminaCost,
    costB: actionB.staminaCost,
    positionDeltaA: actionA.forwardStep ?? 0,
    positionDeltaB: -(actionB.forwardStep ?? 0),
    narrative,
    outcome,
  };
}

export function applyExchange(a: FighterRuntime, b: FighterRuntime, outcome: ExchangeOutcome): void {
  a.hp = clamp(a.hp - outcome.damageA, KNOCKOUT_HP, FIGHTER_MAX_HP);
  b.hp = clamp(b.hp - outcome.damageB, KNOCKOUT_HP, FIGHTER_MAX_HP);
  a.stamina = clamp(a.stamina - outcome.costA, 0, FIGHTER_MAX_STAMINA);
  b.stamina = clamp(b.stamina - outcome.costB, 0, FIGHTER_MAX_STAMINA);
  a.positionZ += outcome.positionDeltaA;
  b.positionZ += outcome.positionDeltaB;

  const halfSpan = 3.4;
  a.positionZ = clamp(a.positionZ, -halfSpan, -0.9);
  b.positionZ = clamp(b.positionZ, 0.9, halfSpan);
}

export function shouldResetRound(a: FighterRuntime, b: FighterRuntime): boolean {
  return a.hp <= KNOCKOUT_HP || b.hp <= KNOCKOUT_HP;
}

export function resetFighters(a: FighterRuntime, b: FighterRuntime): void {
  a.hp = FIGHTER_MAX_HP;
  b.hp = FIGHTER_MAX_HP;
  a.stamina = FIGHTER_MAX_STAMINA;
  b.stamina = FIGHTER_MAX_STAMINA;
  a.positionZ = -1.5;
  b.positionZ = 1.5;
  a.currentAction = 'guard';
  b.currentAction = 'guard';
  a.actionTimer = 0;
  b.actionTimer = 0;
}
