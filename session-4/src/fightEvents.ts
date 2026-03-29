import type { ActionName } from './combat';
import { createEventEmitter } from './eventEmitter';

export type DecisionEvent = {
  fighter: string;
  provider: 'anthropic' | 'openai';
  action: ActionName;
  reasoning: string;
  source: 'remote' | 'fallback';
};

export type FightEventMap = {
  decisionRequested: {
    round: number;
    exchange: number;
  };
  decisionResolved: DecisionEvent;
  exchangeResolved: {
    round: number;
    exchange: number;
    narrative: string;
  };
  knockout: {
    round: number;
    winner: string;
  };
  roundReset: {
    round: number;
  };
  annotation: {
    message: string;
  };
};

export const fightEvents = createEventEmitter<FightEventMap>();
