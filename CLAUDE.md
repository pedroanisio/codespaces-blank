# CLAUDE.md — Project Guidelines

## Disclaimer Reference (Required in all READMEs)

Every README file in this repository **must** reference `@DISCLAIMER.md` at the root of the project. This is a mandatory project convention.

### Rule

When creating or editing any `README.md` file (root or session-level), include a disclaimer reference section. Use the following block:

```markdown
## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.
```

Adjust the relative path to `DISCLAIMER.md` to match the file's depth in the directory tree:
- Root `README.md` → `[DISCLAIMER.md](./DISCLAIMER.md)`
- One level deep (e.g. `session-02/README.md`) → `[DISCLAIMER.md](../DISCLAIMER.md)`
- Two levels deep (e.g. `session-01/assets/README.md`) → `[DISCLAIMER.md](../../DISCLAIMER.md)`

Place the disclaimer reference **after the title and before the first content section**, or at the very end as a footer — whichever is more natural for the document. Never omit it.

### Why

`DISCLAIMER.md` encodes the project's epistemic integrity commitments: non-definitiveness, openness to revision, interdisciplinarity as method, and the principle that AI-generated content may contain hallucinations. These apply to every document in the project without exception.

---

## Project Overview

**SAFE AI Production** — a multi-session workspace exploring epistemic integrity, bias auditing, type-safe data schemas, and responsible knowledge representation for AI systems.

```
.
├── DISCLAIMER.md            ← Methodological caveats (all READMEs must reference this)
├── README.md
├── session-01/              # Epistemic Justice & Research Source Schemas
│   └── assets/              # TypeScript schemas, PDFs, media, research data
├── session-02/              # Generative-AI Video Production Schema
├── tools/                   # Reusable Python utilities
├── content/                 # Scraped source content
├── transcripts/             # Media transcriptions
└── results/                 # Pipeline output reports
```

## General Conventions

- All schema files use semantic versioning (`major.minor.patch`).
- Bilingual content (PT-BR + EN-US) is standard for project-level documentation.
- AI-generated artifacts must be labeled with their source model/tool in file metadata or frontmatter.
- Every README linking to session sub-directories should also link back up to the root `README.md`.
