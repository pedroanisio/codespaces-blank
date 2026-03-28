# Session 02 — Generative-AI Video Production Pipeline

**A fully operational AI video production pipeline** that takes a one-sentence idea or a structured JSON instance and generates a complete video with real AI-generated shots, dialogue, music, SFX, and cinematic post-production.

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

---

## Quick Start

### 1. Check environment

```bash
cd session-02
python3 -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt
python3 -m pipeline.check_env
```

### 2. Set API keys

Create `session-02/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...       # Required — Claude Sonnet 4.6 (24-skill AI pipeline)
OPENAI_API_KEY=sk-proj-...         # Optional — GPT-Image-1.5 images, TTS-HD, GPT-4.1 vision
GEMINI_API_KEY=AIza...             # Optional — Gemini 2.5 Flash, Imagen 4, Veo 3.1 video
DEEPSEEK_API_KEY=sk-...            # Optional — DeepSeek V3.2 text/JSON fallback
ELEVENLABS_API_KEY=sk_...          # Optional — Eleven v3 TTS, SFX, music generation
RUNWAY_API_KEY=key_...             # Optional — Runway Gen4.5 video generation
BRAVE_API_KEY=BSA...               # Optional — web research for creative skills
XAI_API_KEY=sk-...                 # Optional — Grok 4 text/JSON + Aurora images
SUNO_COOKIE=...                    # Optional — Suno music generation
DESCRIPT_API_KEY=...               # Optional — Descript transcription + AI editing
```

### 3. Generate a video

**Full pipeline** — idea → AI script → generate → assemble:

```bash
python3 -m pipeline.run --idea "A lone astronaut discovers a garden growing on Mars"
```

**Creative only** — AI writes the script, stops before rendering:

```bash
python3 -m pipeline.run --idea "A robot learning to paint" --creative-only
```

**Render only** — from an existing JSON instance:

```bash
python3 -m pipeline.run render instance.json --output-dir ./output-demo
```

**Refine** — re-run specific skills then re-render:

```bash
python3 -m pipeline.run refine instance.json --start-from s07-director
```

**Dry run** — see what would happen without spending API credits:

```bash
python3 -m pipeline.run --idea "A robot" --dry-run
```

**Stub-only mode** (no API costs — colored rectangles + silence):

```bash
python3 -m pipeline.run render demo-30s.json --stub-only
```

**Check** — validate instance against schema only:

```bash
python3 -m pipeline.run check instance.json
```

### 4. Run tests

```bash
python3 -m pytest tests/ pipeline/test_assemble.py -v
```

---

## Pipeline Architecture

### Modes

| Mode | Command | What it does |
|------|---------|--------------|
| **creative+render** | `--idea "text"` | Full pipeline: 24 skills → generate → assemble → final video (default) |
| **creative** | `--idea "text" --creative-only` | AI writes the v3 instance JSON, stops before rendering |
| **render** | `render instance.json` | Generate + assemble from a pre-built instance JSON |
| **refine** | `refine instance.json --start-from s07` | Re-run specific skills on an existing instance, then re-render |
| **check** | `check instance.json` | Validate instance against the schema (no generation) |

Cross-cutting flags: `--dry-run` (simulate without API calls), `--stub-only` (FFmpeg stubs instead of AI).

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  --idea mode: 24-Skill AI Pipeline (S01 → S24)                 │
│  Claude Sonnet 4.6 / GPT-4.1 / Gemini 2.5 Flash / Grok 4     │
│  generate the full v3 instance JSON                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │ instance.json
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  S13 Reference Generation (sprites + plates)                   │
│  Characters: front, 3/4, full body sprites (#222 background)   │
│  Environments: wide plate, detail plate (NO characters)        │
│  Props: front, 3/4 sprites (lit with environment color)        │
│  POV plates: character eye-level perspective per environment    │
│  Providers: GPT-Image-1.5 → Imagen 4 → Grok Aurora → stub PNG │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Shot Video Generation                                         │
│  Enriched prompts: style preamble + scene context + camera     │
│    + focal length DoF + styleGuideRef + temporal bridge         │
│    + consistency anchors (hard/medium/soft lock levels)         │
│  Reference images passed to video model (max 3)                │
│  Providers: Runway Gen4.5 → Veo 3.1 → FFmpeg stub             │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Audio Generation                                              │
│  Dialogue/VO: ElevenLabs Eleven v3 TTS from transcript         │
│  SFX/Ambient: ElevenLabs sound effects from description/name   │
│  Music: Suno → ElevenLabs Music (from mood/name)               │
│  Fallback: FFmpeg silent stubs                                 │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Assembly (FFmpeg)                                             │
│  1. Concat shots in scene/shot order + fade transitions        │
│  2. Mix audio: timeline timing + gainDb from renderPlan        │
│  3. Color grade: brightness/contrast/saturation from director  │
│  4. Encode: codec + bitrate from renderPlan, resolution from QP│
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
                   final.mp4
```

### Provider Fallback Chains

| Asset Type | Primary | Fallback 1 | Fallback 2 | Stub |
|------------|---------|------------|------------|------|
| **Text/JSON** | Claude Sonnet 4.6 | GPT-4.1 | Gemini 2.5 Flash | DeepSeek V3.2 → Grok 4 |
| **Images** | GPT-Image-1.5 | Imagen 4 | Grok Aurora | Gradient PNG |
| **Video** | Runway Gen4.5 | Veo 3.1 | — | FFmpeg color block |
| **Dialogue** | ElevenLabs Eleven v3 | OpenAI TTS-HD | — | Silent MP3 |
| **SFX/Ambient** | ElevenLabs SFX | — | — | Silent MP3 |
| **Music** | Suno | ElevenLabs Music | — | Silent MP3 |
| **Web Search** | Brave Search | — | — | Skip |
| **Transcription** | Descript | — | — | Skip |

---

## Schema (v3.1.0)

**Canonical schema**: [claude-unified-video-project-v3.schema.json](./schemas/claude-unified-video-project-v3.schema.json)

**Demo instance**: [demo-30s.json](./examples/demo-30s.json) — 30-second sci-fi short, 2 scenes, 6 shots, 4 audio tracks

**Full example**: [example-project.json](./examples/example-project.json) — 90-second "The Last Signal", 3 acts, 9 shots

### Top-Level Structure

```
{
  schemaVersion, package, project, qualityProfiles[],
  canonicalDocuments: { story, script, directorInstructions },
  production: { characters[], environments[], props[], styleGuides[], scenes[], shots[] },
  assetLibrary: { visualAssets[], audioAssets[], marketingAssets[], genericAssets[] },
  orchestration: { workflows[] },
  assembly: { timelines[], editVersions[], renderPlans[] },
  deliverables[], relationships[]
}
```

### Protocol Compliance

The pipeline reads and acts on **36+ protocol fields** from the JSON instance:

| Category | Fields Used |
|----------|-------------|
| **Shot generation** | shotType, cameraAngle, cameraMovement, focalLengthMm (DoF mapping), style.adjectives, style.palette, styleGuideRef (resolved), temporalBridgeAnchorRef (last frame extraction), consistencyAnchors with lockLevel |
| **Scene context** | mood, timeOfDay, weather, environmentRef → description, transitionIn/Out (fade/cut/dissolve) |
| **Audio** | timeline.audioClips timing, renderPlan.audioMix.gainDb per track, audioType routing |
| **Assembly** | qualityProfiles.widthPx/heightPx, frameRate, sampleRateHz, renderPlan.codec/bitrateMbps, colorDirection parsing, deliverables.platform |

**166 regression tests** across two suites verify protocol compliance and assembly correctness — see [Tests](#tests) below.

---

## 24 Skills (S01-S24)

Located in [skills/](./skills/). Each skill is an autonomous AI agent that reads/writes specific parts of the v3 instance.

| Phase | Skills | Function |
|-------|--------|----------|
| 1 | S01 Concept Seed | Logline, genres, themes from idea |
| 2 | S02 Story Architect | Narrative beats, story arcs |
| 3 | S03 Scriptwriter | Dialogue, action lines, scene headings |
| 4 | S04-S06 Character/Environment/Prop Designer | Visual descriptions, prompt fragments |
| 5 | S07 Director | Vision statement, color direction, must-haves/avoids |
| 6 | S08 Cinematographer | Shot list, camera specs, focal lengths |
| 7 | S09-S12 Scene/Music/Sound/Voice | Scene composition, score, SFX, dialogue TTS |
| 8 | S15 Prompt Composer | Enrich prompts from fragments + style |
| 9 | S13 Reference Asset Gen | Character sprites, environment plates, prop renders, POV plates |
| 10 | S14 Shot Video Gen | Generate video clips with reference images |
| 11 | S16 Consistency Enforcer | Validate visual coherence |
| 12-15 | S17-S24 | Timeline assembly, post-production, QA, delivery, marketing |

---

## S13 Reference Protocol

Before video generation, S13 generates canonical reference images:

| Asset Type | Views | Style | Purpose |
|------------|-------|-------|---------|
| **Character** | front, 3/4, full body | Sprite: isolated on #222 dark background, environment color cast | Identity anchor for face/wardrobe consistency |
| **Environment** | wide plate, detail plate | Background plate: NO characters, full spatial extent | Spatial/lighting reference |
| **Prop** | front, 3/4 | Sprite: isolated on #222, lit with environment lighting | Object identity reference |
| **POV plate** | 1 per (character, environment) pair | First-person perspective at character eye height (heightM x 0.94) | Subjective camera anchoring |

For demo-30s.json (1 character, 1 environment, 1 prop): **8 reference images**.

---

## Structured Logging

All pipeline modules use [structlog](https://www.structlog.org/) with structured key-value events.

**Console** — colored, human-readable output to stderr:

```
2026-03-28T11:05:11Z [info     ] shot_generated   [pipeline.generate] shot_id=s01 duration=4.2 provider=runway
```

**Disk** — JSON Lines written to `{output_dir}/pipeline.log`, one object per line:

```json
{"shot_id": "s01", "duration": 4.2, "provider": "runway", "event": "shot_generated", "logger": "pipeline.generate", "level": "info", "timestamp": "2026-03-28T11:05:11.960362Z"}
```

The log file captures all levels (including DEBUG) regardless of console verbosity, making it useful for post-run diagnostics and cost auditing. Enable verbose console output with `-v`.

Configuration lives in [pipeline/logging_config.py](./pipeline/logging_config.py). It is initialised once by the CLI entry point (`run.py`, `skills.py`, `create.py`, or `pipeline_check.py`) and shared by all modules.

---

## File Index

### Pipeline

| File | Description |
|------|-------------|
| [pipeline/run.py](./pipeline/run.py) | CLI entry point — modes: creative, render, refine, check, dry-run |
| [pipeline/skills.py](./pipeline/skills.py) | 24-skill AI pipeline orchestrator |
| [pipeline/generate.py](./pipeline/generate.py) | S13 reference gen + video/audio generation with consistency layer |
| [pipeline/assemble.py](./pipeline/assemble.py) | FFmpeg assembly: concat, audio mix, color grade, encode |
| [pipeline/providers.py](./pipeline/providers.py) | Multi-provider AI layer (Claude, GPT, Gemini, DeepSeek, Grok, Brave, ElevenLabs, Runway, Veo, Descript) |
| [pipeline/derive.py](./pipeline/derive.py) | Auto-populate shots/audio from story beats if production is empty |
| [pipeline/create.py](./pipeline/create.py) | Interactive CLI to create valid v3 instance JSON |
| [pipeline/check_env.py](./pipeline/check_env.py) | Environment readiness checker with live API key validation |
| [pipeline/pipeline_check.py](./pipeline/pipeline_check.py) | E2E pipeline compliance checker with evidence reports |
| [pipeline/logging_config.py](./pipeline/logging_config.py) | Centralized structlog configuration — colored console + JSON Lines to disk |
| [pipeline/requirements.txt](./pipeline/requirements.txt) | Python dependencies |

### Schema & Instances

| File | Description |
|------|-------------|
| [claude-unified-video-project-v3.schema.json](./schemas/claude-unified-video-project-v3.schema.json) | **v3.1.0 canonical schema** — JSON Schema Draft 2020-12 |
| [demo-30s.json](./examples/demo-30s.json) | 30-second demo instance — 2 scenes, 6 shots, 4 audio tracks |
| [example-project.json](./examples/example-project.json) | 90-second "The Last Signal" — 3 acts, 9 shots, full production |
| [video-project-schema-v2.json](./schemas/video-project-schema-v2.json) | Legacy v2 schema (superseded by v3) |

### Skills

| Directory | Description |
|-----------|-------------|
| [skills/](./skills/) | 24 skill definitions (S01-S24), each with SKILL.md spec |
| [skills/INDEX.md](./skills/INDEX.md) | Skill index and dependency graph |

### Tests

| File | Tests | Description |
|------|-------|-------------|
| [tests/test_protocol_compliance.py](./tests/test_protocol_compliance.py) | 66 | Protocol compliance: prompt enrichment, audio mixing, encoding, S13 references, POV plates |
| [pipeline/test_assemble.py](./pipeline/test_assemble.py) | 100 | Assembly compliance: approval gate, spatial consistency, audio timing, color grade, DAG execution, 180-degree rule, channel layout |

### Taxonomies & Research

| File | Description |
|------|-------------|
| [term-map.json](./schemas/term-map.json) | Machine-readable production vocabulary (10 terms, 4 axes) |
| [claude-20-styles-video-v1.1.md](./docs/styles/claude-20-styles-video-v1.1.md) | 20 video styles as formal biconditional predicates |
| [claude-20-styles-camera-v1.0.md](./docs/styles/claude-20-styles-camera-v1.0.md) | Camera angles, movements, optics with 3D coordinates |
| [claude-20-styles-scene-v1.0.md](./docs/styles/claude-20-styles-scene-v1.0.md) | Scene ontology: diegetic location/time, editing grammar |
| [claude-animation-taxonomy-v1.0.md](./docs/styles/claude-animation-taxonomy-v1.0.md) | Animation as artifact class — production methods, playback modalities |

---

## Session Context

Part of the **SAFE AI Production** project. See [../README.md](../README.md) for full project structure, [session-01/](../session-01/) for epistemic justice schemas.
