# PALS's Law

**A Formal Specification of LLM Output Unreliability as an Architectural Invariant**

> Across any realistic deployment, LLMs reliably produce errors — at a rate that
> is non-zero and non-negligible. Failing to verify LLM output is not a bug in
> the generated artifact. It is an **architectural omission** in the system that
> consumed it.

---

## What is PALS's Law?

PALS's Law is an engineering principle — in the tradition of Hyrum's Law,
Postel's Law, and Zawinski's Law — asserting that LLM output error is a
**statistical invariant** of the model class, not an exceptional condition
to be debugged away.

Any system that consumes LLM output without a declared verification boundary
contains a **structural defect**, regardless of how correct the output appears.

**The operative claim (formal):**

$$
\forall M \in \mathcal{M},\ \forall \text{ realistic } \mathcal{D} \text{ over } \mathcal{X}:
\quad \mathbb{E}_{x \sim \mathcal{D}}\!\bigl[\varepsilon(M(x), x)\bigr] \geq \delta > 0
$$

The expected error rate is non-negligible for every model on every realistic
task distribution. Published benchmarks confirm δ is well above zero for all
models tested to date.

## What's in this repository?

| File | Description |
|------|-------------|
| [`PALS_LAW-v1.5.4.md`](./PALS_LAW-v1.5.4.md) | Full specification (682 lines) |
| [`pals_law_schema.json`](./pals_law_schema.json) | Machine-readable symbol table |
| [`pals_law_report.json`](./pals_law_report.json) | Reference verification report (12 refs, 10 verified, 2 partial) |
| [`pals_law_certificate.json`](./pals_law_certificate.json) | Integrity certificate (SHA-256 binding) |
| [`latex/`](./latex/) | arXiv-ready LaTeX source |

## Error Taxonomy (9 classes)

The specification defines nine distinct LLM error classes, each requiring a
different detection strategy:

| Class | ID | One-line |
|-------|----|----------|
| Hallucination | `ERR_HALLUCINATION` | False factual claims with apparent confidence |
| Omission | `ERR_OMISSION` | Silently dropped content or constraints |
| Schema violation | `ERR_SCHEMA` | Output structurally non-conformant |
| Partial completion | `ERR_TRUNCATION` | Output cut short |
| Sycophantic drift | `ERR_SYCOPHANCY` | Output shaped by perceived preference over truth |
| Instruction failure | `ERR_INSTRUCTION` | Explicit prompt constraints violated |
| Calibration failure | `ERR_CALIBRATION` | Expressed confidence misaligned with reliability |
| Reasoning failure | `ERR_REASONING` | Correct facts, invalid composition |
| Semantic drift | `ERR_SEMANTIC` | Correct surface form, wrong meaning |

**No single verifier can detect all classes.**

## Quick-Start: Practitioner Artifacts

### Inline banner (code comment)

```typescript
// ⚠ PALS's LAW: LLM output is untrusted by default. Verify before use.
```

### Short-form (PR descriptions, commit messages)

```
ARCHITECTURAL REQUIREMENT (PALS's LAW):
LLM error rates are non-negligible across realistic deployments.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
```

### Full contract block

See [`PALS_LAW-v1.5.4.md` §9.1](./PALS_LAW-v1.5.4.md) for the complete
TypeScript contract block with per-error-class verification checklist.

### CLAUDE.md integration

See [`PALS_LAW-v1.5.4.md` §9.4](./PALS_LAW-v1.5.4.md) for a drop-in block
for any `CLAUDE.md` project configuration.

## Theoretical Foundations

PALS's Law does not claim theoretical novelty. The inevitability of LLM
hallucination has been independently established by:

- **Kalai & Vempala (STOC 2024)** — statistical lower bound for calibrated LMs
- **Xu, Jain & Kankanhalli (2024)** — computability-theoretic diagonalization
- **Karpowicz (2025)** — impossibility via mechanism design theory

The law's contribution is packaging these results into a **named, testable,
enforceable architectural contract** with a concrete error taxonomy and
practitioner artifacts.

## 5 Architectural Corollaries

1. **Appearance of correctness is not correctness** — finite test sets prove nothing about the long tail.
2. **Trust accumulation is prohibited** — correct history provides no guarantee on unseen inputs.
3. **Verification scope must match error taxonomy** — partial verification must be scoped honestly.
4. **Silent acceptance is an architectural defect** — equivalent to missing authentication.
5. **Capability growth shifts the verification problem** — more capable models produce harder-to-detect errors.

## Citation

```bibtex
@misc{pals_law_2026,
  author       = {de Luna e Silva, Pedro Anisio},
  title        = {{PALS's Law}: A Formal Specification of {LLM} Output
                  Unreliability as an Architectural Invariant},
  year         = {2026},
  version      = {1.5.4},
  howpublished = {\url{https://github.com/<username>/pals-law}},
  note         = {Version 1.5.4, April 2026}
}
```

## License

This specification is licensed under [CC BY 4.0](./LICENSE). You are free to
share and adapt it, with attribution.

The practitioner artifacts (§9) are additionally released under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) — copy-paste
without attribution.

## Author

**Pedro Anisio de Luna e Silva (PALS)**

---

*Document generated with assistance from Claude (Anthropic). All claims,
references, and formal content have been authored and reviewed by the named
author. See the disclaimer in the document frontmatter.*
