# Scene-Parallel Render: Independent Multi-Run Project Rendering

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

---

## 1. Problem Statement

The current pipeline executes rendering as a monolithic process: all shots are generated, all audio is generated, then the entire project is assembled in one pass (concat → audioMix → colorGrade → encode). This means:

- **No partial render recovery.** If shot 7 of 8 fails, all prior generation work is wasted unless the user manually re-invokes.
- **No horizontal scaling.** A project with 40 shots across 10 scenes cannot distribute generation work across multiple machines or processes.
- **No incremental preview.** A director cannot see scene 1 fully assembled while scene 4 is still generating.
- **No scene-level iteration.** Re-rendering scene 3 with a revised shot forces re-assembly of all 4 scenes.

### Goal

Enable a project render to be decomposed into **N independent sub-renders** (one per scene), each self-contained and executable in isolation, with a final **stitch operation** that joins pre-rendered scene segments into the deliverable.

---

## 2. Current Architecture

### 2.1 Pipeline Flow (as-is)

```
┌─────────────────────────────────────────────────────────┐
│  run.py::_run_render(instance, output_dir)              │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐                     │
│  │generate_shots│  │generate_audio│   (parallel)        │
│  │ ALL shots    │  │ ALL audio    │                     │
│  └──────┬──────┘  └──────┬───────┘                     │
│         └────────┬───────┘                              │
│                  ▼                                      │
│         assemble(instance, output_dir,                  │
│                  shot_clips, audio_files)               │
│                  │                                      │
│         ┌───────┴────────┐                              │
│         │execute_operation│                              │
│         │      _dag()    │                              │
│         └───────┬────────┘                              │
│                 │                                       │
│    concat ──► audioMix ──► colorGrade ──► encode        │
│   (all 8       (all 11      (full          (final       │
│    shots)       tracks)      timeline)      output)     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key files:**

| File | Responsibility |
|------|---------------|
| `pipeline/run.py:175-221` | `_run_render()` — orchestrates generate + assemble |
| `pipeline/generate.py` | `generate_shots()`, `generate_audio()` — media generation |
| `pipeline/assemble.py:1276-1470` | `execute_operation_dag()` — FFmpeg operations |
| `pipeline/skills.py:54-80` | `PIPELINE_PHASES` — skill execution order |

### 2.2 Entity Relationships in spark.gvpp.json

```
project (prj-spark, 15s)
 ├── scene-01 "Desolation"  (4s)  → shot-0101 (2.5s), shot-0102 (1.5s)
 ├── scene-02 "Discovery"   (4s)  → shot-0201 (2.0s), shot-0202 (2.0s)
 ├── scene-03 "Sacrifice"   (4s)  → shot-0301 (2.0s), shot-0302 (2.0s)
 └── scene-04 "Light"       (3s)  → shot-0401 (1.5s), shot-0402 (1.5s)

timeline (tl-master, 15s)
 ├── videoClips: vc-01..vc-08 (sequential, no overlap on layer 0)
 └── audioClips: ac-score (0-15s), ac-ambient-grey (0-12.5s),
                 ac-ambient-warm (12-15s), ac-footsteps (0.5-8s),
                 ac-servo (4-12s), ac-debris-* (8-11s), ac-click, ac-clang, ac-crackle

renderPlan (rp-master)
 └── operations: audioMix → colorGrade → encode
```

### 2.3 Dependency Graph

```
                    Shot Generation (per shot, independent)
                    ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
                    │0101  │0102  │0201  │0202  │0301  │0302  │0401  │0402  │
                    └──┬───┴──┬───┴──┬───┴──┬───┴──┬───┴──┬───┴──┬───┴──┬───┘
                       │      │      │      │      │      │      │      │
                    Audio Generation (per track, independent of shots)
                    ┌──────┬──────┬──────┬──────┬──────┬──────┬──────────┐
                    │score │amb-g │amb-w │foot  │servo │debris│click/clng│
                    └──┬───┴──┬───┴──┬───┴──┬───┴──┬───┴──┬───┴──────┬───┘
                       └──────┴──────┴──────┴──────┴──────┴──────────┘
                                             │
                                     ┌───────▼────────┐
                                     │ concat (all 8)  │
                                     └───────┬────────┘
                                     ┌───────▼────────┐
                                     │ audioMix (11)   │
                                     └───────┬────────┘
                                     ┌───────▼────────┐
                                     │ colorGrade      │
                                     └───────┬────────┘
                                     ┌───────▼────────┐
                                     │ encode (final)  │
                                     └────────────────┘
```

**Observation:** Shot generation is already independent per-shot. Audio generation is independent per-track. The bottleneck is the assembly DAG, which treats the entire timeline as one atomic unit.

---

## 3. Independence Analysis

### 3.1 What Is Already Independent

| Component | Granularity | Evidence |
|-----------|------------|---------|
| Shot video generation | Per-shot | `generate.py` generates each shot from its own `cinematicSpec` + `generation.steps[].prompt`. No shot reads another shot's output. |
| Audio generation | Per-track | Each audio asset has its own `generation` config. Music, SFX, dialogue are independent. |
| Skill pipeline (creative) | Per-phase | `skills.py:54-80` runs parallel skills within each phase. `--start-from` enables resume. |
| Creative vs. render | Full split | `--creative-only` and `render instance.json` already exist. |

### 3.2 What Blocks Per-Scene Independence

**Problem 1: Cross-scene audio assets.**
The timeline's audio clips span scene boundaries:

| Audio track | Timeline span | Scenes covered |
|------------|--------------|----------------|
| `aa-score` | 0–15s | All 4 scenes |
| `aa-sfx-ambient` | 0–12.5s | Scenes 1–3 |
| `aa-ambient-warm` | 12–15s | Scenes 3–4 (overlaps!) |
| `aa-sfx-footsteps` | 0.5–8s | Scenes 1–2 |
| `aa-sfx-servo` | 4–12s | Scenes 2–3 |
| `aa-sfx-debris-groan` | 8.3–9.5s | Scene 3 only |
| `aa-sfx-click` | 10.5–10.8s | Scene 3 only |

A per-scene render must know which audio tracks intersect its time range, and must slice them to the scene's temporal window.

**Problem 2: Cross-scene transitions.**
Scenes define `transitionOut` and `transitionIn` (dissolve 0.3–0.5s in spark.gvpp.json). A dissolve requires frames from both the outgoing and incoming scene — the last N frames of scene K and first N frames of scene K+1 must be rendered together.

**Problem 3: Color grade applies globally.**
The color grade operation in `rp-master` has a single `intent`: "Desaturated blue-grey scenes 1-3, golden warmth introduced at 12s." This describes a *temporal arc* across the whole timeline. Splitting into per-scene grades is feasible but requires decomposing the intent.

**Problem 4: Render plan is not scene-scoped.**
The current `renderPlan` has one set of operations applied to the full timeline. There's no schema mechanism for per-scene render plans.

### 3.3 Classification

| Aspect | Splittable? | Constraint |
|--------|------------|------------|
| Shot generation | **Yes** (already) | None |
| Audio generation | **Yes** (already) | None |
| Concat (within scene) | **Yes** | Each scene's shots are sequential and self-contained |
| Concat (cross-scene) | **Needs work** | Transitions require shared frames at boundaries |
| Audio mix | **Needs work** | Tracks must be sliced to scene time ranges |
| Color grade | **Needs work** | Global intent must decompose into per-scene params |
| Encode | **Yes** | Per-scene encode is trivially independent |
| Final stitch | **New** | Must join scene segments + apply cross-scene transitions |

---

## 4. Proposed Architecture

### 4.1 Conceptual Model

```
┌──────────────────────────────────────────────────────────────┐
│                    Scene-Parallel Render                      │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Scene 01  │ │ Scene 02  │ │ Scene 03  │ │ Scene 04  │  ← independent │
│  │           │ │           │ │           │ │           │     │
│  │ gen shots │ │ gen shots │ │ gen shots │ │ gen shots │     │
│  │ slice aud │ │ slice aud │ │ slice aud │ │ slice aud │     │
│  │ concat    │ │ concat    │ │ concat    │ │ concat    │     │
│  │ audio mix │ │ audio mix │ │ audio mix │ │ audio mix │     │
│  │ color grd │ │ color grd │ │ color grd │ │ color grd │     │
│  │ encode    │ │ encode    │ │ encode    │ │ encode    │     │
│  │  ↓        │ │  ↓        │ │  ↓        │ │  ↓        │     │
│  │scene-01.  │ │scene-02.  │ │scene-03.  │ │scene-04.  │     │
│  │  mp4      │ │  mp4      │ │  mp4      │ │  mp4      │     │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘     │
│        └─────────────┬┴─────────────┴──────────────┘         │
│                      ▼                                       │
│              ┌───────────────┐                                │
│              │  Stitch Pass  │  ← cross-scene transitions    │
│              │  + final enc  │    + global normalization      │
│              └───────┬───────┘                                │
│                      ▼                                       │
│                  spark.mp4                                    │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 New Schema Concepts

#### 4.2.1 Scene Render Plan (`SceneRenderPlan`)

A new entity type that scopes a render plan to a single scene's time range. Added as an optional field on `SceneEntity`.

```typescript
// Addition to the v3 schema (gvpp-schema.ts)

const SceneRenderPlanSchema = z.object({
  renderPlanId: EntityIdSchema,
  sceneRef: EntityRefSchema,
  timeRange: TimeRangeSchema,        // scene's absolute start/end on master timeline
  audioSlices: z.array(z.object({
    audioRef: EntityRefSchema,        // reference to audioAsset
    sourceTimeRange: TimeRangeSchema, // absolute range in master timeline
    localTimeRange: TimeRangeSchema,  // remapped to scene-local 0-based time
    gainDb: z.number().default(0),
    pan: z.number().min(-1).max(1).default(0),
  })),
  operations: z.array(RenderOperationSchema),  // reuses existing operation types
  transitionHandles: z.object({
    head: z.object({                  // frames needed from previous scene
      durationSec: z.number().default(0),
      type: TransitionTypeSchema,
    }).optional(),
    tail: z.object({                  // frames to export for next scene
      durationSec: z.number().default(0),
      type: TransitionTypeSchema,
    }).optional(),
  }).optional(),
});
```

#### 4.2.2 Stitch Operation (`StitchOp`)

A new operation type for the master render plan that joins pre-rendered scene segments.

```typescript
const StitchOpSchema = z.object({
  opId: z.string(),
  opType: z.literal("stitch"),
  sceneSegments: z.array(z.object({
    sceneRef: EntityRefSchema,
    filePath: z.string(),             // path to pre-rendered scene segment
    transitionIn: TransitionSpecSchema.optional(),
    transitionOut: TransitionSpecSchema.optional(),
  })),
  method: z.enum(["concat", "xfade"]).default("xfade"),
});
```

### 4.3 Pipeline Changes

#### 4.3.1 New Module: `pipeline/scene_splitter.py`

Responsible for decomposing an instance into N scene-scoped sub-instances.

```
Input:  Full v3 instance (spark.gvpp.json)
Output: List[SceneRenderContext], one per scene

SceneRenderContext:
  - scene: SceneEntity
  - shots: list[ShotEntity]        (only this scene's shots)
  - audioSlices: list[AudioSlice]  (tracks sliced to scene time range)
  - colorGradeParams: dict         (scene-specific grade derived from global intent)
  - transitionHandles: {head, tail}
  - qualityProfile: QualityProfileEntity
```

**Audio slicing algorithm:**

```python
def slice_audio_for_scene(
    scene_start: float,
    scene_end: float,
    timeline_audio_clips: list[dict],
    render_plan_tracks: list[dict],
) -> list[AudioSlice]:
    """
    For each audio clip that overlaps [scene_start, scene_end]:
      1. Compute intersection: max(clip_start, scene_start) .. min(clip_end, scene_end)
      2. Remap to scene-local time: subtract scene_start
      3. Apply fade-in/out if the slice starts/ends mid-track
      4. Preserve gainDb and pan from the render plan
    """
```

**Color grade decomposition:**

The global intent "Desaturated blue-grey scenes 1-3, golden warmth at 12s" is parsed into per-scene parameters by evaluating the scene's midpoint time against the color arc:

| Scene | Time range | Grade |
|-------|-----------|-------|
| scene-01 | 0–4s | brightness=-0.03, contrast=1.0, saturation=0.75 |
| scene-02 | 4–8s | brightness=-0.02, contrast=1.0, saturation=0.78 |
| scene-03 | 8–12s | brightness=0.0, contrast=1.02, saturation=0.82 |
| scene-04 | 12–15s | brightness=0.05, contrast=1.05, saturation=1.0 |

This is already how `_parse_color_direction()` works in `assemble.py:959-985`, but applied once globally. The change extends it to accept a time offset.

#### 4.3.2 Modified: `pipeline/generate.py`

Add a `--scene` filter to `generate_shots()`:

```python
def generate_shots(
    instance: dict,
    output_dir: Path,
    *,
    scene_filter: str | None = None,  # NEW: only generate shots for this scene ID
) -> dict[str, Path]:
```

When `scene_filter` is set, `_shots_in_order()` returns only the shots belonging to that scene. No other logic changes — shot generation is already independent.

#### 4.3.3 Modified: `pipeline/assemble.py`

Add `assemble_scene()` function:

```python
def assemble_scene(
    context: SceneRenderContext,
    shot_clips: dict[str, Path],
    audio_files: dict[str, Path],
    output_dir: Path,
) -> Path:
    """
    Render a single scene to an independent MP4 segment.

    Steps:
      1. Concat this scene's shots (with intra-scene cuts)
      2. Slice and mix only the audio tracks overlapping this scene
      3. Apply scene-scoped color grade
      4. Encode to intermediate quality (CRF 1 for lossless intermediate,
         or scene-level encode if this is a terminal single-scene project)
      5. Export transition handles (head/tail frames) for the stitch pass

    Returns path to the rendered scene segment.
    """
```

Add `stitch_scenes()` function:

```python
def stitch_scenes(
    scene_segments: list[Path],
    transitions: list[dict],  # transition specs between consecutive scenes
    output_dir: Path,
    instance: dict,
) -> Path:
    """
    Join pre-rendered scene segments into the final deliverable.

    Steps:
      1. Apply xfade transitions between consecutive segments
      2. Apply global audio normalization (LUFS target from qualityProfile)
      3. Final encode per qualityProfile specs

    Returns path to the final output file.
    """
```

#### 4.3.4 Modified: `pipeline/run.py`

New `--scene` flag and `--parallel-scenes` mode:

```python
# New CLI arguments
parser.add_argument("--scene", metavar="SCENE_ID",
                    help="Render only this scene (e.g., scene-01)")
parser.add_argument("--parallel-scenes", action="store_true",
                    help="Render all scenes as independent sub-processes, then stitch")
```

**Single-scene mode (`--scene scene-02`):**

```
python -m pipeline run render spark.gvpp.json --scene scene-02
```

Produces `output/scene-02.mp4` — a self-contained preview of scene 2 with its own audio mix and color grade.

**Parallel-scenes mode (`--parallel-scenes`):**

```
python -m pipeline run render spark.gvpp.json --parallel-scenes
```

1. Splits instance into N scene contexts
2. Launches N sub-processes (or threads), each running `assemble_scene()`
3. Waits for all to complete
4. Runs `stitch_scenes()` to produce the final deliverable

### 4.4 Cross-Scene Transition Strategy

Transitions (dissolve, fade, wipe) require overlapping frames between adjacent scenes. Two approaches:

**Option A: Handle padding (chosen).**
Each scene renders extra frames at its boundaries:
- Scene K exports `tail_handle` = last `transition_duration_sec` of its video
- Scene K+1 exports `head_handle` = first `transition_duration_sec` of its video
- The stitch pass uses these handles to compute the xfade

This keeps scene renders independent. The handle is just extra frames — the scene MP4 contains them, and the stitch pass knows where to cut.

For spark.gvpp.json, transitions are 0.3–0.5s, so handles are at most 12 frames at 24fps. Negligible overhead.

**Option B: Transition pre-render (rejected).**
Pre-render just the transition region as a separate job. This adds complexity (3 jobs per transition boundary instead of 1 stitch pass) for no benefit at this scale.

### 4.5 Audio Slicing Detail

Given spark.gvpp.json's timeline:

```
Scene 01: 0.0s – 4.0s
Scene 02: 4.0s – 8.0s
Scene 03: 8.0s – 12.0s
Scene 04: 12.0s – 15.0s
```

Audio slicing for **scene-02** (4.0–8.0s):

| Audio track | Global span | Intersection | Local span | Fade |
|------------|-------------|-------------|-----------|------|
| aa-score | 0–15s | 4.0–8.0s | 0–4.0s | none (continuous) |
| aa-sfx-ambient | 0–12.5s | 4.0–8.0s | 0–4.0s | none |
| aa-sfx-footsteps | 0.5–8.0s | 4.0–8.0s | 0–4.0s | fade-out 0.5s at end |
| aa-sfx-servo | 4.0–12.0s | 4.0–8.0s | 0–4.0s | none (starts exactly) |

FFmpeg implementation: `atrim=start=4:end=8,asetpts=PTS-STARTPTS` per track.

---

## 5. Implementation Plan

### Phase 1: Scene Splitter (Complexity: S)

**Files changed:** New `pipeline/scene_splitter.py`

1. Implement `split_instance_by_scene(instance) -> list[SceneRenderContext]`
2. Implement `slice_audio_for_scene()` with correct time remapping
3. Implement `decompose_color_grade()` for per-scene parameters
4. Unit tests: verify scene-02 of spark.gvpp.json gets exactly shots 0201+0202, 6 audio slices, correct time ranges

**Acceptance criteria:**
- `split_instance_by_scene(spark_instance)` returns 4 contexts
- Each context has correct shot count, audio slice count, and time ranges
- Audio slices sum to cover the full timeline with no gaps

### Phase 2: Per-Scene Assembly (Complexity: S)

**Files changed:** `pipeline/assemble.py` (add `assemble_scene()`), `pipeline/generate.py` (add `scene_filter`)

1. Add `assemble_scene()` — concat + slice audio + mix + grade + encode for one scene
2. Add `scene_filter` parameter to `generate_shots()` and `generate_audio()`
3. Integration test: render scene-01 of spark.gvpp.json in stub mode, verify 4s output

**Acceptance criteria:**
- `assemble_scene(scene_01_context, ...)` produces a valid MP4
- FFprobe shows correct duration (4.0s ± 0.1s) and audio tracks
- Color grade matches scene-01 parameters

### Phase 3: Stitch Pass (Complexity: S)

**Files changed:** `pipeline/assemble.py` (add `stitch_scenes()`)

1. Implement `stitch_scenes()` with xfade support
2. Handle transition handles (head/tail frame export)
3. Integration test: stitch 4 pre-rendered scenes with dissolve transitions

**Acceptance criteria:**
- Output matches monolithic render within 0.5s duration tolerance
- Transitions render correctly (dissolve, no visible cut)
- Final encode matches qualityProfile specs

### Phase 4: CLI + Run Integration (Complexity: S)

**Files changed:** `pipeline/run.py`, `pipeline/__main__.py`

1. Add `--scene` and `--parallel-scenes` flags
2. Implement single-scene render path
3. Implement parallel-scenes orchestration (multiprocessing or sequential with flag)
4. E2E test: `--parallel-scenes` on spark.gvpp.json matches monolithic render

**Acceptance criteria:**
- `python -m pipeline run render spark.gvpp.json --scene scene-02` produces scene-02.mp4
- `python -m pipeline run render spark.gvpp.json --parallel-scenes` produces spark.mp4
- `--dry-run` shows per-scene breakdown with estimated costs

### Phase 5: Schema Extension (Complexity: XS)

**Files changed:** `schemas/ts/gvpp-schema.ts`, regenerate `gvpp-v3.schema.json`

1. Add `SceneRenderPlan` type
2. Add `StitchOp` to the RenderOperation discriminated union
3. Add optional `sceneRenderPlan` field to `SceneEntity`
4. Regenerate JSON Schema, validate spark.gvpp.json still passes

**Acceptance criteria:**
- Existing instances validate without changes (new fields are optional)
- New schema supports `opType: "stitch"` in render plans

---

## 6. Trade-offs and Decisions

| Decision | Chosen | Alternative | Rationale |
|----------|--------|------------|-----------|
| Transition handling | Handle padding | Pre-render transitions | Simpler. Handles are just extra frames in each scene MP4. At 0.5s max, overhead is 12 frames. |
| Audio slicing | FFmpeg atrim at assembly time | Pre-slice audio files to disk | Avoids file proliferation. atrim is a zero-copy FFmpeg operation. |
| Color grade decomposition | Time-offset heuristic | Per-scene explicit intent in schema | Works without schema changes for existing instances. New instances can override with explicit per-scene intent. |
| Parallelism mechanism | ThreadPoolExecutor (same as existing) | Multiprocessing / subprocess | Consistent with existing pattern in `skills.py:552` and `run.py:191`. GPU-bound API calls release the GIL. |
| Intermediate codec | CRF 1 x264 (near-lossless) | ProRes / FFV1 | Matches existing intermediate strategy in `assemble.py:1080`. Avoids adding codec dependencies. |
| Schema changes | Optional additive | Required breaking | Backward compatible. Existing instances work unchanged. |

---

## 7. Verification Strategy

### 7.1 Equivalence Test

The primary correctness criterion: **parallel-scene render must produce output equivalent to monolithic render.**

"Equivalent" is defined as:
- Duration within ±0.5s (the existing `runtimeToleranceSec` from qualityProfile)
- SSIM ≥ 0.95 between monolithic and parallel outputs (accounts for floating-point differences in xfade timing)
- Audio LUFS within ±1dB

```python
# test_scene_parallel.py
def test_parallel_matches_monolithic(spark_instance, tmp_path):
    mono_path = render_monolithic(spark_instance, tmp_path / "mono")
    para_path = render_parallel(spark_instance, tmp_path / "para")

    mono_dur = ffprobe_duration(mono_path)
    para_dur = ffprobe_duration(para_path)
    assert abs(mono_dur - para_dur) <= 0.5

    ssim = compute_ssim(mono_path, para_path)
    assert ssim >= 0.95
```

### 7.2 Unit Tests

| Test | Validates |
|------|----------|
| `test_slice_audio_scene_02` | Audio slicing produces correct intersections for scene-02 |
| `test_slice_audio_boundary` | Track starting exactly at scene boundary is included |
| `test_slice_audio_no_overlap` | Track outside scene range produces empty slice |
| `test_decompose_color_scene_04` | Scene-04 (12–15s) gets warm grade, scene-01 gets cool |
| `test_transition_handles` | Dissolve boundary exports correct head/tail frames |
| `test_stitch_no_transitions` | Cut-only stitch matches simple concat |
| `test_single_scene_render` | Single scene renders with correct duration and audio |

### 7.3 Integration Tests

| Test | Validates |
|------|----------|
| `test_stub_parallel_spark` | Full parallel render of spark.gvpp.json in stub mode |
| `test_scene_filter_generates_subset` | `--scene scene-02` generates only 2 shots |
| `test_parallel_dry_run` | `--parallel-scenes --dry-run` shows correct per-scene plan |

---

## 8. Migration and Backward Compatibility

### 8.1 Existing Instances

No changes required. The `SceneRenderPlan` and `StitchOp` are optional schema additions. Existing render plans with `concat → audioMix → colorGrade → encode` continue to work via the monolithic path.

### 8.2 CLI Compatibility

| Command | Before | After |
|---------|--------|-------|
| `run render instance.json` | Monolithic | Monolithic (unchanged) |
| `run render instance.json --scene scene-02` | N/A | New: single-scene render |
| `run render instance.json --parallel-scenes` | N/A | New: parallel + stitch |
| `run render instance.json --dry-run` | Shows global plan | Shows global plan (unchanged) |
| `run render instance.json --parallel-scenes --dry-run` | N/A | New: shows per-scene plan |

### 8.3 Flag Interaction Matrix

| Flag combination | Behavior |
|-----------------|----------|
| `--scene X --parallel-scenes` | Error: mutually exclusive |
| `--scene X --dry-run` | Show plan for scene X only |
| `--scene X --stub-only` | Stub render for scene X only |
| `--parallel-scenes --stub-only` | Stub render all scenes in parallel |

---

## 9. Future Extensions (Not in Scope)

These are documented for context but explicitly excluded from this plan:

- **Distributed rendering across machines.** The scene splitter produces self-contained contexts that *could* be serialized and sent to remote workers, but the orchestration layer (job queue, result collection, failure retry) is out of scope.
- **Incremental re-render.** Detecting which scenes changed and only re-rendering those. Requires content hashing of scene inputs, not addressed here.
- **Real-time preview streaming.** Rendering scenes to HLS segments for live preview. Different output format and delivery mechanism.
- **Per-shot render plans.** Finer granularity than per-scene. Diminishing returns for the added complexity.

---

## Appendix A: spark.gvpp.json Scene Decomposition

Reference decomposition for the Spark project, showing exact splits:

```
Scene 01: "Desolation" (0.0s – 4.0s)
  Shots: shot-0101 (2.5s), shot-0102 (1.5s)
  Audio slices:
    aa-score         [0.0 – 4.0s] local [0.0 – 4.0s] gain=-3dB
    aa-sfx-ambient   [0.0 – 4.0s] local [0.0 – 4.0s] gain=-8dB
    aa-sfx-eyelight  [0.0 – 4.0s] local [0.0 – 4.0s] gain=-18dB
    aa-sfx-footsteps [0.5 – 4.0s] local [0.5 – 4.0s] gain=-12dB pan=-0.1
  Transition out: dissolve 0.5s → tail handle = 0.5s
  Color grade: brightness=-0.03, contrast=1.0, saturation=0.75

Scene 02: "Discovery" (4.0s – 8.0s)
  Shots: shot-0201 (2.0s), shot-0202 (2.0s)
  Audio slices:
    aa-score         [4.0 – 8.0s] local [0.0 – 4.0s] gain=-3dB
    aa-sfx-ambient   [4.0 – 8.0s] local [0.0 – 4.0s] gain=-8dB
    aa-sfx-eyelight  [4.0 – 8.0s] local [0.0 – 4.0s] gain=-18dB
    aa-sfx-footsteps [4.0 – 8.0s] local [0.0 – 4.0s] gain=-12dB pan=-0.1
    aa-sfx-servo     [4.0 – 8.0s] local [0.0 – 4.0s] gain=-14dB pan=0.05
  Transition in:  dissolve 0.5s → head handle = 0.5s
  Transition out: dissolve 0.3s → tail handle = 0.3s
  Color grade: brightness=-0.02, contrast=1.0, saturation=0.78

Scene 03: "Sacrifice" (8.0s – 12.0s)
  Shots: shot-0301 (2.0s), shot-0302 (2.0s)
  Audio slices:
    aa-score           [8.0 – 12.0s] local [0.0 – 4.0s] gain=-3dB
    aa-sfx-ambient     [8.0 – 12.0s] local [0.0 – 4.0s] gain=-8dB  fade-out 0.5s at 4.0s
    aa-sfx-eyelight    [8.0 – 12.0s] local [0.0 – 4.0s] gain=-18dB
    aa-sfx-servo       [8.0 – 12.0s] local [0.0 – 4.0s] gain=-14dB pan=0.05
    aa-sfx-debris-groan[8.3 – 9.5s]  local [0.3 – 1.5s] gain=-6dB  pan=0.3
    aa-sfx-debris-fall [9.5 – 11.0s] local [1.5 – 3.0s] gain=-4dB  pan=0.2
    aa-sfx-click       [10.5–10.8s]  local [2.5 – 2.8s] gain=-2dB
    aa-sfx-clang       [11.0–11.5s]  local [3.0 – 3.5s] gain=-3dB  pan=0.15
    aa-sfx-crackle     [11.1–12.0s]  local [3.1 – 4.0s] gain=-8dB  pan=-0.05
  Transition in:  dissolve 0.3s → head handle = 0.3s
  Transition out: dissolve 0.5s → tail handle = 0.5s
  Color grade: brightness=0.0, contrast=1.02, saturation=0.82

Scene 04: "Light" (12.0s – 15.0s)
  Shots: shot-0401 (1.5s), shot-0402 (1.5s)
  Audio slices:
    aa-score         [12.0 – 15.0s] local [0.0 – 3.0s] gain=-3dB
    aa-ambient-warm  [12.0 – 15.0s] local [0.0 – 3.0s] gain=-10dB  fade-in 0.8s
    aa-sfx-eyelight  [12.0 – 15.0s] local [0.0 – 3.0s] gain=-18dB
  Transition in:  dissolve 0.5s → head handle = 0.5s
  Color grade: brightness=0.05, contrast=1.05, saturation=1.0
```

---

*Generated by Claude Opus 4.6 — 2026-03-28*
