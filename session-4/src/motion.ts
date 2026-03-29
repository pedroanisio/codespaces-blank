export type MovementInput = {
  forward: boolean;
  backward: boolean;
  turnLeft: boolean;
  turnRight: boolean;
  jump: boolean;
  roll: boolean;
};

export type MovementState = {
  speed: number;
  turnSpeed: number;
  animation: 'Idle' | 'Walk' | 'Jump' | 'Roll';
  jumpRequested: boolean;
  rollRequested: boolean;
};

const WALK_SPEED = 2.4;
const BACKWARD_SPEED = -1.4;
const TURN_SPEED = 2.2;

export function resolveMovement(input: MovementInput, airborne = false): MovementState {
  const speed = input.forward ? WALK_SPEED : input.backward ? BACKWARD_SPEED : 0;
  const turnSpeed =
    input.turnLeft && !input.turnRight
      ? TURN_SPEED
      : input.turnRight && !input.turnLeft
        ? -TURN_SPEED
        : 0;
  const jumpRequested = input.jump && !airborne;
  const rollRequested = input.roll && !airborne && !jumpRequested;
  const animation = jumpRequested || airborne ? 'Jump' : rollRequested ? 'Roll' : speed === 0 && turnSpeed === 0 ? 'Idle' : 'Walk';

  return {
    speed,
    turnSpeed,
    animation,
    jumpRequested,
    rollRequested,
  };
}
