# Session 4 | Three.js Mannequin

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

This session contains a TypeScript + Three.js mannequin study built as a local Vite app rooted in `session-4`.

## Run

```bash
npm install
npm run dev
```

## Notes

- The app uses the local mannequin asset at [`assets/mannequin_v4.glb`](./assets/mannequin_v4.glb).
- Arrow keys control forward, backward, and turning movement.
- `Space` triggers a jump with a simple gravity arc.
- `R` triggers a short forward roll.
- Idle, walk, and jump are driven procedurally from the mannequin rig because this asset does not embed authored animation clips.
- This README links back to the project root: [../README.md](../README.md)
