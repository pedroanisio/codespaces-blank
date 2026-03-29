# Session 4 | AI Fight Study

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

This session contains a TypeScript + Three.js `AI vs AI` mannequin fight study built as a local Vite app rooted in `session-4`.

## Run

```bash
npm install
npm run dev
```

## Notes

- The app uses the local mannequin asset at [`assets/mannequin_v4.glb`](./assets/mannequin_v4.glb).
- The mannequins use embedded boxing clips: `guard`, `jab`, `cross`, `hook`, `uppercut`, `bodyShot`, `slip`, `block`, `duck`, `parry`, `advance`, and `retreat`.
- Combat decisions are selected by a deterministic local AI policy, then resolved by a tested exchange model in [`src/combat.ts`](./src/combat.ts).
- The scene runs two fighters, tracks HP, stamina, wins, and resets each round after a knockout.
- This README links back to the project root: [../README.md](../README.md)
