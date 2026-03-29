import { describe, expect, it, vi } from 'vitest';

import { createEventEmitter } from '../src/eventEmitter';

describe('createEventEmitter', () => {
  it('notifies listeners for emitted events', () => {
    const emitter = createEventEmitter<{ ping: { value: number } }>();
    const listener = vi.fn();

    emitter.on('ping', listener);
    emitter.emit('ping', { value: 7 });

    expect(listener).toHaveBeenCalledWith({ value: 7 });
  });

  it('supports unsubscribing through the returned disposer', () => {
    const emitter = createEventEmitter<{ ping: string }>();
    const listener = vi.fn();

    const dispose = emitter.on('ping', listener);
    dispose();
    emitter.emit('ping', 'later');

    expect(listener).not.toHaveBeenCalled();
  });

  it('supports explicit off calls', () => {
    const emitter = createEventEmitter<{ ping: string }>();
    const listener = vi.fn();

    emitter.on('ping', listener);
    emitter.off('ping', listener);
    emitter.emit('ping', 'later');

    expect(listener).not.toHaveBeenCalled();
  });
});
