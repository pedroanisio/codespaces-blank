import {
  ACTIONS,
  ATTACK_RANGE,
  BODYSHOT_RANGE,
  chooseStrategicAction,
  createStrategy,
  type ActionName,
  type FighterRuntime,
  type FighterStrategy,
} from './combat';

export type LlmDecision = {
  action: ActionName;
  reasoning: string;
  provider: 'anthropic' | 'openai';
  source: 'remote' | 'fallback';
};

type BridgePayload = {
  fighter: Pick<FighterRuntime, 'name' | 'hp' | 'stamina' | 'positionZ' | 'currentAction' | 'wins'>;
  opponent: Pick<FighterRuntime, 'name' | 'hp' | 'stamina' | 'positionZ' | 'currentAction' | 'wins'>;
  round: number;
  exchange: number;
};

const AI_BRIDGE_URL = (import.meta.env.VITE_FIGHT_AI_URL as string | undefined) ?? '/api/decide';

// Per-provider strategy state for local fallback AI
const strategies: Record<string, FighterStrategy> = {};

function getStrategy(provider: string): FighterStrategy {
  if (!strategies[provider]) {
    strategies[provider] = createStrategy();
  }
  return strategies[provider];
}

export function resetStrategies(): void {
  for (const key of Object.keys(strategies)) {
    strategies[key] = createStrategy();
  }
}

function normalizeAction(value: unknown): ActionName | null {
  if (typeof value !== 'string') {
    return null;
  }

  switch (value) {
    case 'guard':
    case 'jab':
    case 'cross':
    case 'hook':
    case 'earSlap':
    case 'uppercut':
    case 'bodyShot':
    case 'sideKick':
    case 'headKick':
    case 'slip':
    case 'block':
    case 'duck':
    case 'parry':
    case 'advance':
    case 'retreat':
    case 'kickL':
    case 'kickR':
      return value;
    default:
      return null;
  }
}

function buildStrategyPrompt(
  fighter: BridgePayload['fighter'],
  opponent: BridgePayload['opponent'],
  round: number,
  exchange: number,
): string {
  const distance = Math.abs(fighter.positionZ - opponent.positionZ);
  const inRange = distance <= ATTACK_RANGE;
  const tightRange = distance <= BODYSHOT_RANGE;

  const attacks = Object.values(ACTIONS)
    .filter((a) => a.kind === 'attack')
    .map((a) => `${a.name}: power=${a.power} speed=${a.speed} reach=${a.reach}m cost=${a.staminaCost}sta`)
    .join('; ');

  const defenses = Object.values(ACTIONS)
    .filter((a) => a.kind === 'defense')
    .map((a) => `${a.name}: counters [${a.defenseVs?.join(',')}] cost=${a.staminaCost}sta`)
    .join('; ');

  const strategy = getStrategy(fighter.name === 'Alpha' ? 'anthropic' : 'openai');
  const recentOpponent = strategy.opponentHistory.slice(-4).join('→') || 'none';

  return `You are a combat AI controlling fighter "${fighter.name}" in a boxing match.

SITUATION:
- Round ${round}, Exchange ${exchange}
- You: HP ${fighter.hp}/100, Stamina ${fighter.stamina}/100, current=${fighter.currentAction}
- Opponent: HP ${opponent.hp}/100, Stamina ${opponent.stamina}/100, current=${opponent.currentAction}
- Distance: ${distance.toFixed(2)}m (${tightRange ? 'TIGHT range' : inRange ? 'boxing range' : 'OUT of range'})
- Opponent recent actions: ${recentOpponent}
- Strategy phase: ${strategy.phase}${strategy.comboChain.length > 0 ? `, in combo step ${strategy.comboStep}/${strategy.comboChain.length} [${strategy.comboChain.join('→')}]` : ''}

ATTACKS: ${attacks}
DEFENSES: ${defenses}
MOVEMENT: advance (step forward 0.42m, cost=3sta), retreat (step back 0.48m, cost=3sta)
GUARD: recover stamina faster, but vulnerable to attacks (85% damage)

COMBAT RULES:
- Attack vs Attack: faster punch lands first, loser takes 50% damage
- Attack vs correct Defense: attack neutralized
- Attack vs wrong Defense: 70% damage goes through
- Attack vs Guard: 85% damage lands
- Attack vs Retreat: 30% graze damage
- Attack vs Advance: 110% damage (walked into it)
- Out of range: attacks miss entirely

STRATEGY GUIDANCE:
- Out of range? Advance to close distance, mix in jabs
- Opponent low HP (≤25)? Go all-out with power moves
- Your HP low (≤30) or stamina low (≤18)? Guard to recover or retreat
- Opponent favoring attacks? Counter with the right defense
- Opponent turtling? Use kicks/bodyShot to break through
- In tight range? Hook, uppercut, bodyShot are devastating
- Combos: jab→cross→hook, jab→bodyShot→uppercut, cross→hook→kickL

Respond with ONLY a JSON object: {"action": "<action_name>", "reasoning": "<brief reason>"}`;
}

export async function requestFightDecision(
  provider: 'anthropic' | 'openai',
  payload: BridgePayload,
  fallbackRng?: () => number,
): Promise<LlmDecision> {
  const prompt = buildStrategyPrompt(payload.fighter, payload.opponent, payload.round, payload.exchange);

  try {
    const response = await fetch(AI_BRIDGE_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        provider,
        prompt,
        ...payload,
      }),
    });

    if (!response.ok) {
      throw new Error(`Bridge returned ${response.status}`);
    }

    const json = (await response.json()) as {
      action?: unknown;
      reasoning?: unknown;
      source?: unknown;
    };
    const action = normalizeAction(json.action);

    if (!action) {
      throw new Error('Bridge returned an invalid action.');
    }

    return {
      action,
      reasoning: typeof json.reasoning === 'string' ? json.reasoning : '',
      provider,
      source: json.source === 'remote' ? 'remote' : 'fallback',
    };
  } catch {
    const strategy = getStrategy(provider);
    const action = chooseStrategicAction(
      strategy,
      payload.fighter as FighterRuntime,
      payload.opponent as FighterRuntime,
      fallbackRng,
    );
    return {
      action,
      reasoning: `${strategy.phase} phase${strategy.comboChain.length > 0 ? `, combo ${strategy.comboStep}/${strategy.comboChain.length}` : ''}.`,
      provider,
      source: 'fallback',
    };
  }
}
