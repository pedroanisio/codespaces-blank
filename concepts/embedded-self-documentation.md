# Embedded Self-Documentation (ESD)

## Disclaimer

This work is subject to the methodological caveats and commitments described in [@DISCLAIMER.md](../DISCLAIMER.md).
> No statement or premise not backed by a real logical definition or verifiable reference should be taken for granted.

---

## Definition

A source file whose **module-level docstring** functions as a complete, standalone reference manual — eliminating the need for an external README, man page, or wiki entry for that file.

---

## Structural Contract

The docstring MUST contain these sections, in order:

| #  | Section                  | Purpose                                                                  | Required       |
|----|--------------------------|--------------------------------------------------------------------------|----------------|
| 1  | **Title + one-liner**    | What the tool is, in one sentence                                        | Yes            |
| 2  | **Table of Contents**    | Numbered index of all sections                                           | Yes            |
| 3  | **Quick Start**          | Minimum viable invocation (copy-paste-run)                               | Yes            |
| 4  | **CLI / API Reference**  | Every flag, argument, method, or entry point                             | Yes            |
| 5  | **Config / Input Format**| Full spec of any input the tool consumes (schema, config, env vars)      | If applicable  |
| 6  | **Concept Reference**    | Exhaustive definition of every domain concept (rule types, modes, enums) | If applicable  |
| 7  | **Behavioral Semantics** | How ambiguity is resolved (priority, fallback, defaults, discovery)      | Yes            |
| 8  | **Examples**             | Minimal, real-world, edge-case — at least 3                             | Yes            |
| 9  | **Internals & Extension**| Code architecture + how to add new behavior without modifying existing   | Yes            |
| 10 | **Limitations**          | What the tool explicitly does NOT do                                     | Yes            |
| 11 | **Dependencies**         | Runtime requirements (language version, packages)                        | Yes            |

---

## Rules

1. **Self-contained**: `python -c "import X; help(X)"` or reading the raw file gives you everything. No "see README" links.

2. **No duplication**: The docstring IS the docs. There is no separate README for the file. If the file lives inside a directory with a README, the README may link to the file but must not repeat its content.

3. **Prose over code in examples**: Show the shell command or config snippet, not the implementation. The reader is a user, not a maintainer.

4. **Exhaustive on interface, minimal on internals**: Every input/output/flag/config key is documented. Internal architecture gets one paragraph + a map, not a walkthrough.

5. **Structured for scanning**: Numbered sections, box-drawing separators, tables where density helps. A reader skimming at speed should find what they need by visual structure alone.

6. **Raw-string docstring** (`r"""..."""`): Avoids backslash-escape noise in regex examples and path separators.

---

## When to Apply

- Single-file tools meant to be invoked directly (`python tool.py`)
- Utility modules with a public interface used across sessions
- Any file where you'd otherwise create a paired `TOOL-README.md`

## When NOT to Apply

- Library modules consumed only by other code (use standard docstrings per function/class)
- Files whose behavior is already fully described by a parent project's README
- Trivial scripts under ~50 lines

---

## Reference Implementation

The first file in this project to implement ESD:

- [`tools/organize.py`](../tools/organize.py) — 15-section embedded manual covering CLI, config format, 10 rule types, 4 examples, extension guide, and limitations.
