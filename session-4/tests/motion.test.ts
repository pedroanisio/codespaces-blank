import { describe, expect, it } from 'vitest';

import { resolveMovement } from '../src/motion';

describe('resolveMovement', () => {
  it('returns idle when no keys are pressed', () => {
    expect(
      resolveMovement({
        forward: false,
        backward: false,
        turnLeft: false,
        turnRight: false,
        jump: false,
        roll: false,
        moonwalk: false,
        kickL: false,
        kickR: false,
      }),
    ).toEqual({
      speed: 0,
      turnSpeed: 0,
      animation: 'Idle',
      jumpRequested: false,
      rollRequested: false,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });

  it('moves forward and turns left', () => {
    expect(
      resolveMovement({
        forward: true,
        backward: false,
        turnLeft: true,
        turnRight: false,
        jump: false,
        roll: false,
        moonwalk: false,
        kickL: false,
        kickR: false,
      }),
    ).toEqual({
      speed: 2.4,
      turnSpeed: 2.2,
      animation: 'Walk',
      jumpRequested: false,
      rollRequested: false,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });

  it('backs up and turns right', () => {
    expect(
      resolveMovement({
        forward: false,
        backward: true,
        turnLeft: false,
        turnRight: true,
        jump: false,
        roll: false,
        moonwalk: false,
        kickL: false,
        kickR: false,
      }),
    ).toEqual({
      speed: -1.4,
      turnSpeed: -2.2,
      animation: 'Walk',
      jumpRequested: false,
      rollRequested: false,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });

  it('prioritizes jump when requested from the ground', () => {
    expect(
      resolveMovement({
        forward: true,
        backward: false,
        turnLeft: false,
        turnRight: false,
        jump: true,
        roll: false,
        moonwalk: false,
        kickL: false,
        kickR: false,
      }),
    ).toEqual({
      speed: 2.4,
      turnSpeed: 0,
      animation: 'Jump',
      jumpRequested: true,
      rollRequested: false,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });

  it('does not re-trigger jump while airborne', () => {
    expect(
      resolveMovement(
        {
          forward: false,
          backward: false,
          turnLeft: false,
          turnRight: false,
          jump: true,
          roll: false,
          moonwalk: false,
          kickL: false,
          kickR: false,
        },
        true,
      ),
    ).toEqual({
      speed: 0,
      turnSpeed: 0,
      animation: 'Jump',
      jumpRequested: false,
      rollRequested: false,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });

  it('requests a roll on the ground', () => {
    expect(
      resolveMovement({
        forward: true,
        backward: false,
        turnLeft: false,
        turnRight: false,
        jump: false,
        roll: true,
        moonwalk: false,
        kickL: false,
        kickR: false,
      }),
    ).toEqual({
      speed: 2.4,
      turnSpeed: 0,
      animation: 'Roll',
      jumpRequested: false,
      rollRequested: true,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });

  it('does not roll while airborne', () => {
    expect(
      resolveMovement(
        {
          forward: false,
          backward: false,
          turnLeft: false,
          turnRight: false,
          jump: false,
          roll: true,
          moonwalk: false,
          kickL: false,
          kickR: false,
        },
        true,
      ),
    ).toEqual({
      speed: 0,
      turnSpeed: 0,
      animation: 'Jump',
      jumpRequested: false,
      rollRequested: false,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });

  it('prioritizes jump over roll when both are queued', () => {
    expect(
      resolveMovement({
        forward: false,
        backward: false,
        turnLeft: false,
        turnRight: false,
        jump: true,
        roll: true,
        moonwalk: false,
        kickL: false,
        kickR: false,
      }),
    ).toEqual({
      speed: 0,
      turnSpeed: 0,
      animation: 'Jump',
      jumpRequested: true,
      rollRequested: false,
      moonwalk: false,
      kickL: false,
      kickR: false,
    });
  });
});
