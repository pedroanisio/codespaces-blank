# Session 4 | AI Fight Study

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

This session contains a TypeScript + Three.js `AI vs AI` mannequin fight study built as a local Vite app rooted in `session-4`.

## Run

```bash
npm install
npm run ai:bridge
npm run dev
```

Open the bridge and Vite in separate terminals.

## Notes

- The app uses the local mannequin asset at [`assets/mannequin_v4.glb`](./assets/mannequin_v4.glb).
- The mannequins use embedded boxing clips: `guard`, `jab`, `cross`, `hook`, `uppercut`, `bodyShot`, `slip`, `block`, `duck`, `parry`, `advance`, and `retreat`.
- `earSlap` is now a valid close-range attack in the combat system; until the asset has its own clip, it reuses the `hook` animation as a visual fallback.
- `sideKick` and `headKick` are now valid attacks; until the asset has dedicated clips, they reuse `kickL` and `kickR` as visual fallbacks.
- `Alpha` requests actions from Anthropic and `Beta` requests actions from OpenAI through the local bridge at [`ai_bridge.py`](./ai_bridge.py), which reuses the provider helpers from [`../session-02/pipeline/providers.py`](../session-02/pipeline/providers.py).
- If the bridge is down or either provider/key is unavailable, the app falls back to the local deterministic policy in [`src/combat.ts`](./src/combat.ts).
- The scene runs two fighters, tracks HP, stamina, wins, and resets each round after a knockout.
- This README links back to the project root: [../README.md](../README.md)

## Environment

The bridge expects the same server-side keys used by `session-02`:

```bash
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

## Events

The runtime exposes a typed event bus on `window.__session4FightEvents`.

Supported events:
- `decisionRequested`
- `decisionResolved`
- `exchangeResolved`
- `knockout`
- `roundReset`
- `annotation`

Example:

```js
const stop = window.__session4FightEvents?.on('exchangeResolved', (event) => {
  console.log(event.narrative);
});

window.__session4FightEvents?.emit('annotation', {
  message: 'External observer attached.',
});
```
