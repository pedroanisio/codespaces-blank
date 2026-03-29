import { describe, expect, it } from 'vitest';

import {
  ACTIONS,
  applyExchange,
  ATTACK_RANGE,
  BODYSHOT_RANGE,
  chooseAiAction,
  createFighter,
  distanceBetween,
  FIGHTER_MAX_STAMINA,
  recoverStamina,
  resetFighters,
  resolveExchange,
  shouldResetRound,
} from '../src/combat';

describe('combat', () => {
  it('prefers advance when fighters are out of range', () => {
    const alpha = createFighter('Alpha', -3.2);
    const beta = createFighter('Beta', 3.2);

    expect(chooseAiAction(alpha, beta, () => 0.1)).toBe('advance');
  });

  it('returns a guarded fallback when stamina is exhausted', () => {
    const alpha = createFighter('Alpha', -1.2);
    const beta = createFighter('Beta', 1.2);
    alpha.stamina = 0;

    expect(chooseAiAction(alpha, beta, () => 0.9)).toBe('guard');
  });

  it('lets the faster punch win when both attacks are in range', () => {
    const outcome = resolveExchange('jab', 'hook', 2.1);

    expect(outcome.damageA).toBe(Math.round((ACTIONS.hook.power ?? 0) * 0.5));
    expect(outcome.damageB).toBe(ACTIONS.jab.power);
    expect(outcome.outcome).toBe('a_wins');
  });

  it('lets a matching defense nullify an attack', () => {
    const outcome = resolveExchange('cross', 'slip', ATTACK_RANGE - 0.1);

    expect(outcome.damageA).toBe(0);
    expect(outcome.damageB).toBe(0);
    expect(outcome.outcome).toBe('b_defends');
  });

  it('clips a retreat instead of landing full power', () => {
    const outcome = resolveExchange('cross', 'retreat', ATTACK_RANGE - 0.1);

    expect(outcome.damageB).toBe(Math.round((ACTIONS.cross.power ?? 0) * 0.3));
    expect(outcome.outcome).toBe('a_grazes');
  });

  it('misses when a short-range attack is thrown from too far away', () => {
    const outcome = resolveExchange('bodyShot', 'guard', BODYSHOT_RANGE + 0.4);

    expect(outcome.damageA).toBe(0);
    expect(outcome.damageB).toBe(0);
    expect(outcome.outcome).toBe('neutral');
  });

  it('applies exchange costs, damage, and movement deltas', () => {
    const alpha = createFighter('Alpha', -1.5);
    const beta = createFighter('Beta', 1.5);
    const outcome = resolveExchange('advance', 'jab', ATTACK_RANGE - 0.1);

    applyExchange(alpha, beta, outcome);

    expect(alpha.hp).toBeLessThan(100);
    expect(alpha.stamina).toBe(100 - ACTIONS.advance.staminaCost);
    expect(beta.stamina).toBe(100 - ACTIONS.jab.staminaCost);
    expect(distanceBetween(alpha, beta)).toBeGreaterThan(1.5);
  });

  it('recovers stamina over time without exceeding the cap', () => {
    const alpha = createFighter('Alpha', -1.5);
    alpha.stamina = 88;
    alpha.currentAction = 'guard';

    recoverStamina(alpha, 1);
    recoverStamina(alpha, 1);

    expect(alpha.stamina).toBe(FIGHTER_MAX_STAMINA);
  });

  it('signals and resets a knockout round', () => {
    const alpha = createFighter('Alpha', -1.5);
    const beta = createFighter('Beta', 1.5);
    beta.hp = 0;

    expect(shouldResetRound(alpha, beta)).toBe(true);

    alpha.wins += 1;
    resetFighters(alpha, beta);

    expect(alpha.hp).toBe(100);
    expect(beta.hp).toBe(100);
    expect(alpha.positionZ).toBe(-1.5);
    expect(beta.positionZ).toBe(1.5);
  });
});
