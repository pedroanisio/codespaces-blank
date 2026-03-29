import type { MovementInput } from './motion';

export class KeyboardController {
  private readonly pressed = new Set<string>();
  private jumpQueued = false;
  private rollQueued = false;
  private _moonwalk = false;
  private _kickL = false;
  private _kickR = false;

  resetMoonwalk(): void {
    this._moonwalk = false;
  }

  attach(): void {
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('blur', this.handleBlur);
  }

  detach(): void {
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    window.removeEventListener('blur', this.handleBlur);
  }

  snapshot(): MovementInput {
    const jump = this.jumpQueued;
    const roll = this.rollQueued;
    this.jumpQueued = false;
    this.rollQueued = false;

    const kickL = this._kickL;
    const kickR = this._kickR;
    this._kickL = false;
    this._kickR = false;

    return {
      forward: this.pressed.has('ArrowUp'),
      backward: this.pressed.has('ArrowDown'),
      turnLeft: this.pressed.has('ArrowLeft'),
      turnRight: this.pressed.has('ArrowRight'),
      jump,
      roll,
      moonwalk: this._moonwalk,
      kickL,
      kickR,
    };
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
    if (event.key === 'm' || event.key === 'M') {
      event.preventDefault();
      this._moonwalk = !this._moonwalk;
      return;
    }

    if (event.key === 'q' || event.key === 'Q') {
      event.preventDefault();
      this._kickL = true;
      return;
    }

    if (event.key === 'e' || event.key === 'E') {
      event.preventDefault();
      this._kickR = true;
      return;
    }

    if (event.key === 'r' || event.key === 'R') {
      event.preventDefault();
      this.rollQueued = true;
      return;
    }

    if (event.key === ' ') {
      event.preventDefault();
      this.jumpQueued = true;
      return;
    }

    if (event.key.startsWith('Arrow')) {
      event.preventDefault();
      this.pressed.add(event.key);
    }
  };

  private readonly handleKeyUp = (event: KeyboardEvent): void => {
    if (event.key === 'r' || event.key === 'R') {
      event.preventDefault();
      return;
    }

    if (event.key === ' ') {
      event.preventDefault();
      return;
    }

    if (event.key.startsWith('Arrow')) {
      event.preventDefault();
      this.pressed.delete(event.key);
    }
  };

  private readonly handleBlur = (): void => {
    this.pressed.clear();
    this.jumpQueued = false;
    this.rollQueued = false;
    this._moonwalk = false;
  };
}
