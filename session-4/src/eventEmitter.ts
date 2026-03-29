export type EventMap = Record<string, unknown>;

type Listener<T> = (payload: T) => void;

export type EventEmitter<TEvents extends EventMap> = {
  on<TKey extends keyof TEvents>(event: TKey, listener: Listener<TEvents[TKey]>): () => void;
  off<TKey extends keyof TEvents>(event: TKey, listener: Listener<TEvents[TKey]>): void;
  emit<TKey extends keyof TEvents>(event: TKey, payload: TEvents[TKey]): void;
};

export function createEventEmitter<TEvents extends EventMap>(): EventEmitter<TEvents> {
  const listeners = new Map<keyof TEvents, Set<Listener<unknown>>>();

  return {
    on(event, listener) {
      const bucket = listeners.get(event) ?? new Set<Listener<unknown>>();
      bucket.add(listener as Listener<unknown>);
      listeners.set(event, bucket);

      return () => {
        bucket.delete(listener as Listener<unknown>);
        if (bucket.size === 0) {
          listeners.delete(event);
        }
      };
    },

    off(event, listener) {
      const bucket = listeners.get(event);
      if (!bucket) {
        return;
      }

      bucket.delete(listener as Listener<unknown>);
      if (bucket.size === 0) {
        listeners.delete(event);
      }
    },

    emit(event, payload) {
      const bucket = listeners.get(event);
      if (!bucket) {
        return;
      }

      for (const listener of bucket) {
        listener(payload);
      }
    },
  };
}
