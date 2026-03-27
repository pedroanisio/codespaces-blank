---
name: qa-validator
description: >
  Run automated quality validation on scenes, shots, and deliverables — execute
  QA gate checks, produce QCResult entries, enforce validation rules from director
  and quality profiles. Blocks downstream progression when quality thresholds are
  not met. Use when entities need quality verification before proceeding. Trigger
  on "validate quality", "run QA checks", "check quality gates", "verify the output".
  Trigger after render plan is built and before deliverable packaging.
---

# QA Validator (S21)

## Purpose

Execute automated quality checks at scene, shot, and deliverable levels.
Gate downstream progression based on pass/fail thresholds.

## Schema Surface

### Writes (primary owner)
- `QaGate` on scenes and shots:
  - `checks[]` → `QaCheck[]` (name, score, pass, notes, evidenceRefs)
  - `overallPass`: Computed from checks vs `passThreshold`
  - `evaluatedAt`: Timestamp
- `QCResult[]` on deliverables:
  - `metric`, `actualValue`, `expectedValue`, `pass`, `severity`
  - `measuredAt`, `notes`, `evidenceRefs`
- `ValidationNode` outputs in workflow graphs

### Reads
- `production.scenes[].qaGate` (required checks, pass threshold)
- `production.shots[].qaGate` (required checks, pass threshold)
- `canonicalDocuments.directorInstructions.qualityRules[]` → `ValidationRule[]`
- `qualityProfiles[]` (all quality targets)
- Generated assets (visual + audio)
- Render plan outputs

## Preconditions

- Assets to validate exist (video, audio, or rendered output)
- QA gates are configured on scenes/shots (from S09)

## Procedure

### Step 1: Shot-level checks

For each shot with a `qaGate`, run:
- **temporal_consistency**: Frame-to-frame stability within the shot
- **character_coherence**: Character identity preserved (from S16 scores)
- **duration_compliance**: Duration within tolerance of target
- **resolution_compliance**: Meets quality profile resolution
- **audio_sync**: Audio alignment with visual events

### Step 2: Scene-level checks

For each scene, run:
- **shot_continuity**: Visual continuity across shots in the scene
- **timing_compliance**: Scene duration within tolerance
- **transition_quality**: Transitions render correctly
- **all shots pass**: Aggregate shot-level results

### Step 3: Deliverable-level checks

For rendered outputs:
- **loudness_compliance**: LUFS within target ±1
- **true_peak**: Below ceiling
- **resolution_match**: Output matches quality profile
- **frame_rate_match**: FPS matches target
- **runtime_compliance**: Duration within tolerance
- **codec_compliance**: Correct codec and profile

### Step 4: Evaluate gates

For each `QaGate`:
```
overallPass = (passing_checks / total_required_checks) ≥ passThreshold
```

### Step 5: Report and gate

- If `overallPass: true` → entity proceeds to next stage
- If `overallPass: false` → entity is blocked, upstream skills notified
- Write `evaluatedAt` timestamp

## Output Contract

- Every scene and shot with a `qaGate` has populated `checks[]`
- `overallPass` is computed for all gates
- Deliverables have `qcResults[]` for all measurable metrics
- Failed gates block downstream progression
- All results include `measuredAt` timestamps

## Downstream Dependencies

After S21 passes: S22 (Deliverable Packager)
S21 failure: triggers re-generation or adjustment in upstream skills
