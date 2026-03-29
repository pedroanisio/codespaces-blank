import type { MovementInput } from './motion';

export class KeyboardController {
  private readonly pressed = new Set<string>();
  private jumpQueued = false;
  private rollQueued = false;

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

    return {
      forward: this.pressed.has('ArrowUp'),
      backward: this.pressed.has('ArrowDown'),
      turnLeft: this.pressed.has('ArrowLeft'),
      turnRight: this.pressed.has('ArrowRight'),
      jump,
      roll,
    };
  }

  private readonly handleKeyDown = (event: KeyboardEvent): void => {
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
  };
}
