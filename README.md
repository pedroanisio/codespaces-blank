# SAFE AI Production — Working Sessions

A multi-session workspace exploring themes critical to safe, production-ready AI systems: epistemic integrity, bias auditing, type-safe data schemas, and responsible knowledge representation.

---

## Project Philosophy

AI systems inherit the biases of their training data and the research maps that inform them. This workspace operationalizes a core principle:

> **Making invisible biases visible and actionable is a prerequisite for safe AI.**

Each session investigates a specific theme through concrete tooling, schemas, and documentation — not as abstract principle, but as working code.

---

## Repository Structure

```
.
├── session-01/          # Epistemic Justice & Research Source Schemas
│   └── assets/          # TypeScript schemas, PDFs, media, research data
├── tools/               # Reusable Python utilities
├── content/             # Scraped source content (197 documents)
├── transcripts/         # Media transcriptions
├── results/             # Pipeline output reports
└── .agents/skills/      # AI agent skill definitions
```

---

## Sessions

### Session 01 — Engineering Epistemic Justice

**Theme**: Type-safe representation of archival silence and research bias.

**Core question**: How do you build a research database that doesn't silently inherit the biases of its creators?

**Key outputs**:

| File | Description |
|------|-------------|
| [session-01/assets/research-source-schema.ts](session-01/assets/research-source-schema.ts) | Zod v4 schema for any knowledge type (text, oral, visual, audio, film) |
| [session-01/assets/research-map-assessment.ts](session-01/assets/research-map-assessment.ts) | Epistemic audit schema — forces named blind spots + remediation actions |
| [session-01/assets/README.md](session-01/assets/README.md) | Full schema documentation (v3.0.0) |
| [session-01/assets/perplexity-1990-research-map-rc-3.ts](session-01/assets/perplexity-1990-research-map-rc-3.ts) | 200-source research map on German Reunification (1990), HHI 0.071 |

**Design highlights**:

- **FuzzyDate**: Represents temporal uncertainty (`{ kind: "approximate", label: "early 1940s", confidence: 0.4 }`) rather than forcing false precision
- **62 SourceKind types**: Covers written, oral, visual arts, music, and film — not just journal articles
- **HHI concentration index**: Detects information monopolies in source distributions (87% journal articles = 0.76 HHI = monopoly)
- **7 BlindSpot types**: `source-absence`, `interpretive-frame`, `archival-destruction`, `language-barrier`, `access-restriction`, `question-framing`, `survivorship-bias`
- **Performative epistemology is forbidden**: Naming a blind spot without a concrete remediation action fails schema validation

---

## Tools

Reusable utilities available across all sessions.

### [tools/playwright_pipeline.py](tools/playwright_pipeline.py)

Web scraper and URL verifier for research source validation.

```bash
python tools/playwright_pipeline.py session-01/assets/perplexity-1990-research-map-rc-3.ts \
  --content --concurrency 3
```

**Features**: Headless Chrome via Playwright, concurrent processing, retry with exponential backoff, JSON report generation, content extraction using semantic HTML selectors.

**Session 01 results**: 197 sources verified, 83.8% success rate, 3.6M characters of content saved to `content/`.

---

### [tools/transcribe_media.py](tools/transcribe_media.py)

Audio/video transcription using OpenAI Whisper.

```bash
python tools/transcribe_media.py --dir session-01/assets --model base --format txt
```

**Supported formats**: mp3, mp4, m4a, wav, webm, ogg, flac, mkv, avi, mov, wma, aac, opus
**Output formats**: TXT, JSON (with segment timing), SRT subtitles
**Models**: tiny, base, small, medium, large, large-v2, large-v3

---

### [tools/verify_pdf_orientation.py](tools/verify_pdf_orientation.py)

Checks PDF page orientations (Portrait/Landscape/Square), accounting for rotation metadata.

```bash
python tools/verify_pdf_orientation.py session-01/assets/notebook-Engineering_Epistemic_Justice.pdf
```

---

## Agent Skills

Reusable skill definitions for Claude Code agents.

| Skill | Description |
|-------|-------------|
| [.agents/skills/python-design-patterns/](.agents/skills/python-design-patterns/) | KISS, SRP, composition over inheritance, separation of concerns, rule of three |
| [.agents/skills/dataverse-python-production-code/](.agents/skills/dataverse-python-production-code/) | Production Python patterns for Microsoft Dataverse SDK |

---

## Setup

```bash
# Python dependencies
pip install playwright whisper pypdf

# Playwright browser
playwright install chromium

# TypeScript / Zod (for schema validation)
npm install zod
```

---

## SAFE AI Themes Addressed

| Theme | Where |
|-------|-------|
| Bias visibility and auditability | `research-map-assessment.ts` — structured epistemic audit |
| Knowledge representation fairness | `research-source-schema.ts` — 62 source kinds, oral/visual/music |
| Epistemic uncertainty | `FuzzyDate` type — rejects false precision |
| Source diversity metrics | HHI concentration index in `MapAssessment` |
| Actionable accountability | `RemediationAction[]` — effort-estimated concrete steps |
| Production code quality | Python design pattern skills, type hints, error handling |

---

## Session Roadmap

Sessions are added as new themes are explored. Each session is self-contained with its own `assets/` directory and a session-specific README.

- **Session 01**: Epistemic justice schemas (complete)
- **Session 02**: *(upcoming)*
- **Session 03**: *(upcoming)*
