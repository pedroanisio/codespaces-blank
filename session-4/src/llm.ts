import {
  chooseAiAction,
  type ActionName,
  type FighterRuntime,
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

const AI_BRIDGE_URL = (import.meta.env.VITE_FIGHT_AI_URL as string | undefined) ?? 'http://127.0.0.1:8787/decide';

function normalizeAction(value: unknown): ActionName | null {
  if (typeof value !== 'string') {
    return null;
  }

  switch (value) {
    case 'guard':
    case 'jab':
    case 'cross':
    case 'hook':
    case 'uppercut':
    case 'bodyShot':
    case 'slip':
    case 'block':
    case 'duck':
    case 'parry':
    case 'advance':
    case 'retreat':
      return value;
    default:
      return null;
  }
}

export async function requestFightDecision(
  provider: 'anthropic' | 'openai',
  payload: BridgePayload,
  fallbackRng?: () => number,
): Promise<LlmDecision> {
  try {
    const response = await fetch(AI_BRIDGE_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        provider,
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
    return {
      action: chooseAiAction(payload.fighter as FighterRuntime, payload.opponent as FighterRuntime, fallbackRng),
      reasoning: 'Local fallback policy.',
      provider,
      source: 'fallback',
    };
  }
}
