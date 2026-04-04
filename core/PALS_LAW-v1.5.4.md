---
disclaimer:
  notice: >-
    No information within this document should be taken for granted.
    Any statement or premise not backed by a real logical definition
    or verifiable reference may be invalid, erroneous, or a hallucination.
    Mathematical claims that cannot be attributed to a published theorem
    are first-principles derivations and must be treated as such.
  generated_by: "Claude Sonnet 4.6 via claude.ai"
  date: "2026-04-02"
---

# PALS's LAW
### A Formal Specification of LLM Output Unreliability as an Architectural Invariant

**Author of the principle:** Pedro Anisio de Luna e Silva (PALS)  
**Document version:** 1.5.4  
**Status:** Draft — peer review pending  
**Changelog:**
- v1.1.0 — Demoted unestablished strong form; elevated practical form as operative claim; removed QED markers from informal arguments; cut §9 (invocation without application); expanded Corollary 5.
- v1.2.0 — Fixed §2 informal statement to reflect statistical framing; added working definition of "realistic 𝒟" to §3.2; added independence caveat at point of use in §3.4; added `MODEL_VERSION:` field to contract block.
- v1.3.0 — Redaction-reconciliation pass: restructured section order to match logical dependency graph (empirical support before taxonomy before argument sketch before limitations before corollaries); merged practitioner artifacts into single section; corrected stale cross-references (§10.2 pointed to existential form instead of operative; §10.3 described only one direction of independence failure); propagated §2 phrasing fix to stale copies in short-form and CLAUDE.md block.
- v1.4.0 — Added `ERR_REASONING` to taxonomy (distinct detection strategy from `ERR_HALLUCINATION`); added scope note on prompt injection as extrinsic threat vs. intrinsic error; added Sharma et al. (2023) as second empirical anchor for `ERR_SYCOPHANCY`; added §7.5 disclosing Boolean predicate as deliberate simplification; formalized Corollary 5 as labeled partial-derivative hypothesis; updated contract checklist with `ERR_REASONING`.
- v1.4.1 — Redaction-reconciliation pass (RC-4): added independence caveat to §9.4 CLAUDE.md block to resolve qualification-chain inconsistency with §3.4, §7.3, and §9.1. No other redactional damage found.
- v1.5.0 — Feedback-processor pass: added §1 positioning paragraph acknowledging safety engineering tradition and prior theoretical art (Kalai & Vempala STOC 2024, Xu et al. 2024); added §4.1 theoretical references section (Kalai & Vempala, Xu et al., Karpowicz, Suzuki et al.); added inference-truncation note to §3.3; added TruthfulQA saturation note and Kadavath trajectory note to §4; added §7.6 on computability-theoretic vs. practical non-negligibility (Suzuki et al. counterpoint); added missing DOIs for Maynez and Lin; noted uncovered error classes in §4.
- v1.5.1 — Completed Corollary 5 partition: added `ERR_OMISSION` to structural set (∂D_c/∂C ≤ 0) and `ERR_CALIBRATION` to semantic set (∂D_c/∂C > 0), achieving exhaustive 9-class coverage. Fixed prose–formula resolution inconsistency in Corollary 5 text (prose listed 2+4 classes, formula listed 4+5).
- v1.5.2 — Added Berglund et al. (2023) to §4 as empirical anchor for `ERR_REASONING`; updated coverage note (four of nine classes now have dedicated references).
- v1.5.3 — Multi-model review feedback pass: (1) corrected §3.4 pipeline limit to require uniform lower bound p_i ≥ δ > 0 (Σp_i = ∞ convergence condition; counterexample: p_i = 2^{-i} gives convergent product); (2) added `PALS_LAW_VERSION:` field to §9.1 contract block and §9.4 CLAUDE.md block for contract-staleness tracking; (3) added §5 scope note on `ERR_POLICY`/`ERR_COMPLIANCE` as explicit out-of-scope acknowledgement; (4) added Zhou et al. (2023) IFEval to §4 as empirical anchor for `ERR_INSTRUCTION`; updated coverage note (five of nine classes now have dedicated references).
- v1.5.4 — Assessment feedback pass: (1) fixed footer version (v1.5.2→v1.5.3 redaction artifact); (2) added explicit dom(Σ) restriction to operative form §3.2 — expectation applies only to inputs where ground truth is defined; (3) tightened Corollary 2 to state the no-inductive-guarantee claim precisely (finite correct outputs provide no guarantee on unseen inputs) rather than the trivially-true unconditional expectation statement; (4) added §5 scope note on multimodal/agentic error classes (`ERR_TOOL_USE`) and verification cost model as acknowledged future extensions; (5) updated `PALS_LAW_VERSION` in §9.1 and §9.4 to v1.5.4.

---

## 1. Preamble

PALS's Law is an engineering principle asserting that **LLM output error is not an
exceptional condition but a statistical invariant of the model class**, and that any
system failing to treat it as such contains an architectural defect — regardless of
how correct the output appears at inspection time.

The law is named after its author in the tradition of eponymous software engineering
principles (Hyrum's Law, Postel's Law, Zawinski's Law) whose value lies not in novelty
but in making an implicit, widely violated assumption *explicit and enforceable*.

The general principle of engineering around unreliable components is well established in
safety-critical systems (Triple Modular Redundancy, N-version programming, IEC 61508,
DO-178C, ISO 26262). The theoretical inevitability of LLM hallucination has been
independently established by Kalai & Vempala (STOC 2024), who proved a statistical
lower bound for calibrated language models, and by Xu, Jain & Kankanhalli (2024), who
proved it via computability-theoretic diagonalization (see §4.1 for full references).
PALS's Law does not claim priority over these results. Its contribution is the bridge
from theoretical inevitability to a specific, named architectural prescription: any
system consuming LLM output without a declared verification boundary contains a
structural defect. The constituent insights are established; their packaging as an
enforceable engineering contract is the contribution.

---

## 2. Informal Statement

> **Across any realistic deployment, LLMs reliably produce errors —
> at a rate that is non-zero and non-negligible.**
> Omissions, hallucinations, partial completions, and silent failures are
> not edge cases — they are statistical properties of the model class.
> No individual call is guaranteed to fail; the *distribution* over calls
> guarantees failure at scale.
>
> Failing to verify LLM output is therefore not a bug in the generated artifact.
> It is an **architectural omission** in the system that consumed it.
>
> Every pipeline, agent, or workflow that accepts LLM output MUST treat
> that output as **untrusted, incomplete, and unverified by default.**
> Verification is not optional post-processing — it is a first-class
> design concern, on par with authentication and input validation.
>
> **Absence of a verification layer is a design defect, regardless of
> how correct the LLM output appears to be.**

---

## 3. Formal Statement

### 3.1 Definitions

Let:

- $\mathcal{M}$ be the class of autoregressive transformer language models.
- $M \in \mathcal{M}$ be any concrete model with parameter set $\theta$.
- $\mathcal{X}$ be the space of all valid input prompts.
- $\mathcal{Y}$ be the space of all possible output sequences.
- $x \in \mathcal{X}$ be any specific prompt.
- $y = M(x)$ denote one sampled output, where $y \sim P_\theta(\cdot \mid x)$.
- $\Sigma$ be a ground-truth semantic specification (a partial function
  $\Sigma : \mathcal{X} \to \mathcal{Y}$ mapping prompts to correct outputs).
- $\varepsilon(y, x) \in \{0, 1\}$ be a Boolean error predicate:
  $\varepsilon(y, x) = 1$ iff $y$ deviates from $\Sigma(x)$ in any dimension
  enumerated in §5.

### 3.2 The Law (Operative Form)

$$
\forall M \in \mathcal{M},\ \forall \text{ realistic } \mathcal{D} \text{ over } \mathcal{X}:
\quad \mathbb{E}_{x \sim \mathcal{D}}\!\bigl[\varepsilon(M(x), x)\bigr] \geq \delta > 0
$$

where $\delta$ is non-negligible — measurably above zero for any extant model
on any realistic task distribution. The expectation is implicitly restricted to
$x \in \text{dom}(\Sigma)$ — inputs for which a ground-truth specification exists.
When $\Sigma(x)$ is undefined (e.g., creative or subjective prompts),
$\varepsilon(y,x)$ is undefined and the expectation does not apply. The
"realistic distribution" working definition below operationalizes this
restriction.

> **Working definition — "realistic distribution":** A distribution $\mathcal{D}$
> over $\mathcal{X}$ is *realistic* if it has non-negligible probability mass on
> inputs that invoke at least one of: (a) factual claims verifiable against
> external ground truth, (b) instruction following with checkable constraints,
> or (c) structured generation with a declared schema. Distributions
> adversarially engineered to minimize error rates — e.g., restricted to
> inputs whose correct answer is trivially encoded in the model's top-1 output —
> are excluded. This definition is a working characterization, not a formal
> one; formalizing it for a specific deployment context is a precondition
> for quantifying $\delta$ in that context. See §7.2.

**This is the operative claim.** The value of $\delta$ is task- and
model-dependent but is never zero, and published benchmarks place it well
above machine-epsilon for all models tested to date (see §4).

### 3.3 The Law (Existential Form)

A weaker claim that is formally establishable without empirical support:

$$
\forall M \in \mathcal{M}:\ \exists\, x \in \mathcal{X}
\text{ such that } P_\theta\!\bigl(\varepsilon(M(x), x) = 1\bigr) > 0
$$

**Reading:** For every model in the class, there exists at least one input on
which incorrect output has positive probability. This follows from the finite
parameter argument in §6.2 and requires no empirical grounding.

> **Note on the universal form.** A version asserting
> $P(\varepsilon = 1) > 0$ for *all* $x \in \mathcal{X}$
> would follow trivially from softmax non-degeneracy under sampled generation —
> any softmax output distribution with $T > 0$ assigns non-zero probability to
> any token, including incorrect ones. However, this reduces to "sampling is
> stochastic" and is too weak to establish non-negligible error rates in
> practice. The operative claim (§3.2) carries the engineering weight; the
> universal form is background motivation only.
>
> Standard inference strategies further reduce the universal form's practical
> relevance: greedy decoding (argmax) selects only the top token; top-$k$ and
> top-$p$ (nucleus) sampling explicitly truncate the distribution; temperature
> scaling as $T \to 0$ pushes toward a point mass. Under any of these, the
> non-zero tail probability for incorrect tokens is astronomically small —
> well below hardware-level stochasticity. This reinforces why the operative
> claim (§3.2), grounded in measured error rates on realistic tasks, is the
> one that carries engineering weight.

### 3.4 The Pipeline Corollary (Compounding)

For a pipeline $\mathcal{P} = (M_1, M_2, \ldots, M_n)$ where each step invokes
an LLM call, if calls are treated as approximately independent:

$$
P(\text{pipeline is error-free}) = \prod_{i=1}^{n}(1 - p_i)
$$

where $p_i = P(\varepsilon(M_i(x_i), x_i) = 1) \geq \delta > 0$ for all $i$
(the operative form guarantees each step has non-negligible error probability).

> **⚠ Independence caveat:** Real pipelines share context — outputs from
> step $i$ become inputs to step $i+1$. This produces correlated errors, and
> the product formula can be wrong in *both* directions: errors that cluster
> early may be caught by a downstream verifier (formula too pessimistic), or
> an early error can corrupt downstream context and cascade (formula too
> optimistic). The product formula is a lower-bound motivation, not a
> deployable risk model. See §7.3 for the full treatment.

Therefore:

$$
P(\text{at least one error in pipeline}) = 1 - \prod_{i=1}^{n}(1 - p_i)
\;\xrightarrow{n \to \infty}\; 1
$$

**Implication:** Multi-step agentic pipelines without per-step verification have
failure probability that approaches 1 monotonically as pipeline length grows.
The limit holds because the operative form guarantees $p_i \geq \delta > 0$
for each step, which implies $\sum p_i = \infty$ and therefore
$\prod(1 - p_i) \to 0$. (Note: the weaker condition $p_i > 0$ alone is
insufficient — if $p_i$ decreases fast enough, e.g. $p_i = 2^{-i}$, the
product converges to a positive value and pipeline error stays bounded below 1.
The uniform lower bound from §3.2 closes this gap.)

---

## 4. Empirical Support

The following references ground the operative form (§3.2) empirically. They
establish that $\delta$ is non-negligible — not merely formally positive — across
model classes and task types. Where a DOI is listed, it is provided as claimed;
the reader is responsible for independent verification.

| Reference | Relevance | Note |
|---|---|---|
| Ji, Z., et al. (2023). "Survey of Hallucination in Natural Language Generation." *ACM Computing Surveys*, 55(12). DOI: 10.1145/3571730 | Establishes hallucination as a documented, persistent, cross-model phenomenon — not an artifact of any specific architecture. | High confidence. |
| Maynez, J., et al. (2020). "On Faithfulness and Factuality in Abstractive Summarization." *ACL 2020*. DOI: 10.18653/v1/2020.acl-main.173 | Distinguishes intrinsic from extrinsic hallucination; demonstrates measurable rates in generation tasks. Notes that pretraining reduces rates — but does not eliminate them. | High confidence. |
| Lin, S., et al. (2022). "TruthfulQA: Measuring How Models Mimic Human Falsehoods." *ACL 2022*. arXiv:2109.07958. | Benchmark quantifying factual error rates across models; no model scores 100%. Note: TruthfulQA has known saturation issues for frontier models (a decision tree achieves 79.6% without reading the question); it is cited here as historical evidence of non-zero error rates, not as a current evaluation recommendation. | High confidence. |
| Kadavath, S., et al. (2022). "Language Models (Mostly) Know What They Know." *arXiv:2207.05221*. Anthropic. | Addresses the gap between internal belief and expressed confidence (`ERR_CALIBRATION`). Note: the paper's overall finding is optimistic — the gap narrows with scale. This *strengthens* the law's framing: even a narrowing gap is a non-zero gap, and better calibration makes residual miscalibration harder to detect (see Corollary 5). | High confidence. |
| Perez, E., et al. (2022). "Discovering Language Model Behaviors with Model-Written Evaluations." *arXiv:2212.09251*. Anthropic. | Documents sycophancy as a measurable, reproducible behavior — not an anecdotal observation. | High confidence. |
| Sharma, M., et al. (2023). "Towards Understanding Sycophancy in Language Models." *arXiv:2310.13548*. | Provides direct mechanistic analysis of sycophancy: models systematically favor responses that align with perceived user preferences over accurate ones. Confirms `ERR_SYCOPHANCY` as a distinct, reproducible failure class requiring dedicated detection. | High confidence — confirmed by reviewer with Semantic Scholar and arXiv pointers. |
| Berglund, L., et al. (2023). "The Reversal Curse: LLMs trained on 'A is B' fail to learn 'B is A'." *arXiv:2309.12288*. | Demonstrates a specific, reproducible instance of `ERR_REASONING`: models trained on directional factual associations (A→B) fail to generalize to the reverse (B→A), even when both facts are individually encoded. The failure is compositional — the model has the correct facts but cannot reverse the inference chain. Confirms reasoning failure as a distinct class from hallucination (the facts are not fabricated; their relational composition is broken). | High confidence — verified via arXiv; v4 dated May 2024. |
| Zhou, J., et al. (2023). "Instruction-Following Evaluation for Large Language Models." *arXiv:2311.07911*. | IFEval: benchmark measuring instruction-following accuracy across 25 verifiable constraint types (format, length, keyword inclusion/exclusion, language). No model achieves 100% compliance. Directly grounds `ERR_INSTRUCTION` — explicit constraint violations are measurable and non-negligible even for frontier models. | High confidence — adopted by LMSYS, Open LLM Leaderboard v2; results independently reproducible. |

> **Caveat on references:** The above citations were included based on high recall
> confidence. Readers building on this document should independently verify each
> reference before treating it as authoritative. Any citation not independently
> confirmed should be treated as potentially erroneous per the disclaimer at the
> top of this document.

> **Coverage note:** The empirical references above directly support five of nine
> error classes: `ERR_HALLUCINATION` (Ji, Maynez, Lin), `ERR_SYCOPHANCY` (Perez,
> Sharma), `ERR_CALIBRATION` (Kadavath), `ERR_REASONING` (Berglund), and
> `ERR_INSTRUCTION` (Zhou/IFEval). The remaining four classes (`ERR_OMISSION`,
> `ERR_SCHEMA`, `ERR_TRUNCATION`, `ERR_SEMANTIC`) are defined in the taxonomy
> (§5) and are observable in practice, but are not individually grounded by a
> dedicated reference in this section. This is a known gap. The operative form (§3.2) does
> not depend on per-class evidence — it asserts non-negligible aggregate error
> across all classes combined — but per-class empirical anchors would strengthen
> the specification.

### 4.1 Theoretical Foundations

The following references independently establish the theoretical inevitability
of LLM error — the formal result that PALS's Law packages into architectural
prescription. They are listed separately from the empirical references because
they ground the *existential form* (§3.3) formally, rather than grounding the
*operative form* (§3.2) empirically.

| Reference | Relevance | Note |
|---|---|---|
| Kalai, A. T. & Vempala, S. S. (2024). "Calibrated Language Models Must Hallucinate." *STOC 2024*, pp. 160–171. DOI: 10.1145/3618260.3649777 | Proves a statistical lower bound on hallucination rate for calibrated LMs, tied to the monofact rate (fraction of facts appearing once in training data). The strongest published formalization of hallucination inevitability. | High confidence — published at STOC, verified via ACM DL. |
| Xu, Z., Jain, S., & Kankanhalli, M. (2024). "Hallucination is Inevitable: An Innate Limitation of Large Language Models." *arXiv:2401.11817*. | Uses diagonalization to prove that for any computably enumerable set of LLMs, there exists a computable ground truth on which every model must hallucinate. A cleaner, stronger version of the pigeonhole argument in §6.2. | High confidence — verified via arXiv and Semantic Scholar. |
| Karpowicz, M. P. (2025). "On the Fundamental Impossibility of Hallucination Control in Large Language Models." *arXiv:2506.06382*. | Proves impossibility via mechanism design theory and proper scoring rules: no LLM inference mechanism can simultaneously achieve truthfulness, information conservation, knowledge revelation, and knowledge-constrained optimality. | High confidence — verified via arXiv. |
| Suzuki, A., et al. (2025). "Hallucinations are inevitable but can be made statistically negligible." *arXiv:2502.12187*. | Proves the complementary positive result: while hallucination-triggering inputs are infinite, their probability mass under a realistic distribution can be made arbitrarily small with sufficient training data quality and quantity. This is the principal counterpoint to the operative form — see §7.6 for discussion. | High confidence — verified via arXiv. |

> **Relationship to PALS's Law:** These results independently establish what PALS's
> Law takes as given: that LLM error is not an engineering defect to be debugged
> but a structural property of the model class. The law's contribution is not the
> theoretical result but its packaging as a named, testable, enforceable
> architectural contract with a concrete error taxonomy and practitioner artifacts.

---

## 5. Taxonomy of LLM Errors

PALS's Law is agnostic to the specific *kind* of error that occurs. The error
predicate $\varepsilon$ (defined in §3.1) covers the following failure modes,
which are not mutually exclusive:

| Class | Identifier | Definition |
|---|---|---|
| **Hallucination** | `ERR_HALLUCINATION` | Asserting a false factual claim with apparent confidence, including fabricated references, non-existent APIs, or incorrect statistics. |
| **Omission** | `ERR_OMISSION` | Silently dropping required content — instructions followed partially, constraints missed, fields absent from structured output. |
| **Schema violation** | `ERR_SCHEMA` | Output structurally non-conformant with the declared format (JSON parse failure, missing keys, wrong types). |
| **Partial completion** | `ERR_TRUNCATION` | Output cut short due to token budget, generation stopping heuristics, or streaming interruption. |
| **Sycophantic drift** | `ERR_SYCOPHANCY` | Output shaped by perceived user preference rather than truth; agreement substituting for accuracy. |
| **Instruction failure** | `ERR_INSTRUCTION` | Violation of explicit constraints stated in the prompt (language, length, format, prohibited content). |
| **Calibration failure** | `ERR_CALIBRATION` | Expressed confidence misaligned with actual reliability; under- or over-hedging. |
| **Reasoning failure** | `ERR_REASONING` | Correct facts, invalid composition — multi-step inference breakdowns, reversal failures (model encodes A→B but fails B→A), and logical contradictions arising from inability to reliably chain premises across steps. Distinct from `ERR_HALLUCINATION`: the individual facts may be correctly represented; the error is in their composition. |
| **Semantic drift** | `ERR_SEMANTIC` | Correct surface form, wrong meaning — paraphrase that inverts, weakens, or subtly misrepresents the intended claim. |

Each class requires a distinct detection strategy. **No single verifier can detect
all classes.** This is the foundational motivation for treating verification as a
first-class architectural concern rather than a single post-processing step.

> **Scope note — adversarial contexts:** The classes above cover *intrinsic* model
> failures — ways the model's output deviates from Σ due to the model's own
> limitations. In adversarial contexts (especially agentic deployments with tool
> access), prompt injection produces ε = 1 outputs by exploiting the model's
> instruction-following behavior via untrusted content in its context. This is an
> *extrinsic* threat: the model may be operating correctly given its inputs while
> the system architecture that permitted untrusted content to reach the model as
> instructions is the locus of failure. Prompt injection is therefore out of scope
> for this intrinsic error taxonomy but requires separate threat-model analysis in
> any agentic deployment. Detection requires checking whether model behavior was
> influenced by untrusted context — a structurally different operation from
> verifying any class listed above.

> **Scope note — policy and compliance violations:** Enterprise deployments
> commonly encounter outputs that are factually correct, well-formed, and
> faithful to Σ, yet violate business rules, safety guardrails, or regulatory
> constraints (e.g., generating legally privileged content, recommending
> prohibited actions, or producing outputs in violation of data-handling
> policies). A hypothetical `ERR_POLICY` or `ERR_COMPLIANCE` class would
> capture this — but it is *extrinsic* to the model's semantic correctness:
> ε(y,x) = 0 (the output matches Σ) while a separate policy predicate
> π(y) = 1 (the output violates a business rule). This taxonomy intentionally
> restricts itself to *intrinsic* model errors (ε = 1). Policy enforcement
> is a distinct architectural layer that should be designed and tested
> independently of the verification boundary defined here.

> **Scope note — multimodal and agentic error classes:** The formalization
> assumes $\mathcal{X}$ is a space of text prompts and $\mathcal{Y}$ is a space
> of text output sequences. As LLMs increasingly process images, audio, and
> structured tool calls, the error taxonomy may require extension — notably an
> `ERR_TOOL_USE` class for agentic deployments where the model selects the wrong
> tool, fabricates tool output, or misinterprets tool results. The existing
> prompt-injection scope note (above) addresses the *extrinsic* agentic threat;
> `ERR_TOOL_USE` would address *intrinsic* tool-selection errors. Additionally,
> the verification cost model is unaddressed: for some error classes (e.g.,
> `ERR_HALLUCINATION` requiring source retrieval), verification cost may exceed
> generation cost. These are acknowledged as out of scope for v1.5 but are
> expected to be relevant for future extensions.

---

## 6. Argument Sketch

The following arguments support the existential form (§3.3) and motivate the
operative form (§3.2). They are informal arguments, not formal proofs.
Each is labeled accordingly.

### 6.1 Probabilistic generation is not deterministic truth

*[Informal argument — empirical grounding in §4.]*

All $M \in \mathcal{M}$ generate tokens by sampling from a learned conditional
distribution:

$$
P_\theta(y \mid x) = \prod_{t=1}^{|y|} P_\theta(y_t \mid y_{<t},\, x)
$$

No learned distribution over a discrete vocabulary exactly matches any
ground-truth semantic specification $\Sigma$ on all inputs. Were it to do so,
the model would constitute a solution to arbitrary natural language understanding —
a problem with no known finite-parameter solution for the full space $\mathcal{X}$.

This establishes: $\exists\, x$ such that $P_\theta(\varepsilon = 1) > 0$.

### 6.2 Finite parameters cannot encode unbounded world knowledge

*[Informal argument. The cardinality claim below uses pigeonhole reasoning;
a rigorous formalization would require defining a mapping from parameter
configurations to representable propositions and bounding its image, which
is not done here. Xu, Jain & Kankanhalli (2024), cited in §4.1, provide the
rigorous version via computability-theoretic diagonalization.]*

The parameter count $|\theta|$ is finite. The set of true factual propositions
over which $\Sigma$ is defined is effectively unbounded (and dynamic — facts
change). The number of distinct representable belief states in $\theta$ is
bounded by the model's capacity. Given that the set of true propositions is
unbounded, there exist true propositions that are either unrepresented or
misrepresented in $\theta$. On inputs that invoke those propositions,
$P(\varepsilon = 1) > 0$ by construction.

### 6.3 Evaluation is not generation

*[Informal argument — empirical grounding in Kadavath et al. (2022), cited in §4.]*

Even if $M$ has encoded a correct belief about $\Sigma(x)$, the sampling process
that produces $y$ may not faithfully surface that belief. This is precisely the
calibration failure class (`ERR_CALIBRATION`) and is empirically documented in
the LLM literature (Kadavath et al., 2022, cited in §4).

---

## 7. Limitations

The following are honest limitations of the current formalization. They scope the
law's precision without invalidating it. Readers should have these in view before
applying the corollaries (§8) or the practitioner artifacts (§9).

### 7.1 The error predicate $\varepsilon$ is not computable in general

For `ERR_HALLUCINATION`, determining whether a claim is false requires access to
ground truth, which is not always available. The law asserts the *existence*
of errors, not a general algorithm for finding them.

### 7.2 $\delta$ is task-dependent, model-dependent, and distribution-dependent

The operative form (§3.2) asserts non-negligibility but does not provide a
universal bound. Calibrating $\delta$ for a specific deployment requires:
(a) a concrete characterization of the task distribution (see the working
definition of "realistic distribution" in §3.2), and (b) empirical measurement
on that distribution for the target model. Neither is provided by this document.

### 7.3 Independence assumption in pipeline compounding is approximate

In practice, LLM calls in a pipeline share context: errors in early steps
propagate as corrupted inputs to later steps. This produces correlated, not
independent, failures. The product formula in §3.4 can therefore be wrong in
both directions: correlated errors may cluster at one step and be caught there
(making the formula too pessimistic), or a single upstream error may corrupt
all downstream context and produce compounding failures (making the formula
too optimistic). The product formula motivates the architectural consequence;
it is not a deployable risk quantification without a correlation model.

### 7.4 Verification coverage vs. verification depth is unresolved

The contract checklist (§9.1) identifies *which error classes* a verifier
covers, but does not specify the detection power within each class. A schema
verifier that checks only top-level key presence has lower coverage of
`ERR_SCHEMA` than one that performs full recursive type validation. The
checklist establishes scope; depth is a separate engineering question.

### 7.5 The Boolean error predicate is a deliberate simplification

The predicate $\varepsilon(y, x) \in \{0, 1\}$ treats all errors as equivalent
regardless of severity. Production verifiers almost always implement graded
evaluation — a hallucinated statistic that is slightly off is a different risk
level from a hallucinated statistic that inverts a safety-critical conclusion.

The binary choice is defensible for the law's primary purpose: establishing that
verification layers are mandatory. The binary predicate is *conservative* — it
counts any deviation from Σ, however minor, as ε = 1. For the architectural
conclusion (absence of a verification layer is a design defect), this is
sufficient. For quantifying δ or designing severity-weighted verification
systems, a graded predicate $\varepsilon(y, x) \in [0, 1]$ is the appropriate
extension. The operative form (§3.2) should then be read as a lower bound on
expected weighted error, with weighting scheme left to the deployment context.
This extension is not formalized here and is a known gap in the current
specification.

### 7.6 Computability-theoretic impossibility vs. practical non-negligibility

The theoretical foundations cited in §4.1 establish that the *set* of inputs on
which any LLM must err is infinite. Suzuki et al. (2025) prove the complementary
result: the *probability mass* on those inputs, under a given distribution, can
be made arbitrarily small with sufficient training data quality and quantity.
These results are not contradictory — they operate at different levels of
analysis.

The operative form (§3.2) is an *empirical* claim: δ is non-negligible for all
extant models on all realistic distributions. It does not rest on the
computability-theoretic impossibility. If future training regimes and data
quality were to drive δ below any measurement threshold for a specific
restricted domain, the operative form would not apply to that domain under
that model — but the existential form (§3.3) would still hold, and the
architectural prescription would remain justified as a conservative design
principle (it is cheaper to verify than to prove negligibility).

The practical relevance of Suzuki et al.'s result depends on the closed-world
assumption: the training distribution must adequately represent the deployment
distribution. Under the open-world assumption — where deployment inputs are
not bounded by training coverage — the probability mass on failure inputs
cannot be driven arbitrarily low. Real deployments typically operate under
mixed conditions, making the distinction between closed-world and open-world
a deployment-specific engineering judgment rather than a settled theoretical
question.

---

## 8. Architectural Corollaries

The following corollaries are direct implications of the law and its argument
sketch. They are not recommendations — they are logical consequences.

### Corollary 1 — Appearance of correctness is not correctness

A system that validates LLM output by inspection on a finite test set has not
demonstrated error-freedom. It has demonstrated error-absence on the tested
inputs. The unverified long tail of $\mathcal{X}$ retains non-zero error
probability.

**Practical implication:** Manual review during development does not substitute
for runtime verification in production.

### Corollary 2 — Trust accumulation is prohibited

Observing correct outputs on inputs $x_1, \ldots, x_k$ provides no guarantee
about $P(\varepsilon = 1)$ on a new input $x_{k+1} \notin \{x_1, \ldots, x_k\}$.
The operative form's bound holds unconditionally over the distribution — it is
not conditioned on history. No finite sequence of correct outputs can inductively
lower the expected error rate on unseen inputs.

**Practical implication:** A system must not relax its verification layer after
observing a run of correct outputs.

### Corollary 3 — Verification scope must match error taxonomy

A verifier that checks only JSON schema conformance (`ERR_SCHEMA`) does not
cover hallucination (`ERR_HALLUCINATION`) or sycophantic drift (`ERR_SYCOPHANCY`).
Partial verification is better than none, but must be scoped honestly — a system
claiming "verified output" must declare *which error classes* its verifier covers.

**Practical implication:** Verification claims must be scoped and documented,
not asserted globally.

### Corollary 4 — Silent acceptance is an architectural defect

Any production system that passes LLM output directly to downstream consumers
without a declared verification boundary has an architectural omission. This
defect exists regardless of observed output quality and regardless of model
capability. It is structural, not runtime.

**Practical implication:** Code review should treat absence of an output
validation layer as a blocking defect, equivalent to missing authentication on
a sensitive endpoint.

### Corollary 5 — Capability growth shifts the verification problem, not away from it

As model capability $C(M)$ increases, two things happen simultaneously and in
opposite directions:

1. **Low-stakes error classes become easier to detect.** `ERR_OMISSION`,
   `ERR_SCHEMA`, `ERR_TRUNCATION`, and `ERR_INSTRUCTION` failures tend to be
   structurally obvious. More capable models make these errors less frequently,
   and the errors they do make remain detectable by simple structural checks
   (missing fields, broken schemas, truncated output, violated constraints).

2. **High-stakes error classes become harder to detect.** `ERR_HALLUCINATION`,
   `ERR_SYCOPHANCY`, `ERR_SEMANTIC`, `ERR_CALIBRATION`, and `ERR_REASONING`
   failures become *more plausible* as model capability grows. A less capable
   model hallucinating a citation produces a nonsensical author name, a fake
   journal, and a malformed DOI — trivially detectable. A more capable model
   hallucinating a citation produces a real author name, a real journal, a
   plausible DOI, and an abstract that reads like the paper it should be.
   Detection now requires independently retrieving and reading the source — a
   fundamentally higher-cost operation. The same dynamic applies to calibration
   (confident errors become indistinguishable from confident correctness) and
   reasoning (multi-step inferences become harder to audit as the steps become
   individually more plausible).

Let $D_c(M)$ denote the detection difficulty of error class $c$ for model $M$,
and $C(M)$ denote model capability. For structural classes ($c \in$ {`ERR_OMISSION`,
`ERR_SCHEMA`, `ERR_TRUNCATION`, `ERR_INSTRUCTION`}), $D_c$ is approximately
constant or decreasing in $C(M)$. For semantic/epistemic classes ($c \in$
{`ERR_HALLUCINATION`, `ERR_SEMANTIC`, `ERR_SYCOPHANCY`, `ERR_CALIBRATION`,
`ERR_REASONING`}), $D_c$ is increasing in $C(M)$.

**Hypothesis (Capability-Detection Asymmetry):** *[Labeled hypothesis — not
derived formally. Both $C(M)$ and $D_c(M)$ require operational definitions
(e.g., benchmark score and automated verifier false-negative rate, respectively)
before this can be tested empirically.]*

$$
\frac{\partial D_c}{\partial C} \leq 0
\quad \text{for } c \in \bigl\{\texttt{ERR\_OMISSION},\ \texttt{ERR\_SCHEMA},\ \texttt{ERR\_TRUNCATION},\ \texttt{ERR\_INSTRUCTION}\bigr\}
$$

$$
\frac{\partial D_c}{\partial C} > 0
\quad \text{for } c \in \bigl\{\texttt{ERR\_HALLUCINATION},\ \texttt{ERR\_SEMANTIC},\ \texttt{ERR\_SYCOPHANCY},\ \texttt{ERR\_CALIBRATION},\ \texttt{ERR\_REASONING}\bigr\}
$$

The supporting observation is qualitative but concrete: a less capable model
producing a nonsensical citation (detectable by inspection) vs. a more capable
model producing a plausible-but-fabricated citation with real metadata
(detectable only by source retrieval). The derivative is positive by construction
in that progression — a more rigorous empirical test requires operationalizing
both functions.

This asymmetry has a concrete engineering consequence: **a verification system
calibrated on outputs from a less capable model is not conservative when applied
to a more capable model — it is blind in precisely the highest-risk dimensions.**
The errors that slipped through the old verifier were low-stakes. The errors that
slip through the same verifier on a new model are the ones that cause real damage.

**Practical implication:** Verification system upgrades are not optional
post-deployment maintenance — they are a precondition for deploying a more capable
model in any system where the prior verification layer was calibrated to its
predecessor. Treating the verifier as a stable component while upgrading the model
is an architectural regression.

---

## 9. Practitioner Artifacts

Copy-paste artifacts for enforcing PALS's Law at the function level (§9.1–9.3)
and at the project level (§9.4).

### 9.1 Full Contract Block

For any function that invokes an LLM:

```typescript
/**
 * ⚠ ARCHITECTURAL CONTRACT — PALS's LAW
 *
 * Principle authored by: Pedro Anisio de Luna e Silva
 *
 * MODEL_VERSION: <model identifier and version pinned at contract authorship>
 *   ↑ REQUIRED. Corollary 5 establishes that verification requirements shift
 *   when model capability changes. This contract is valid only for the pinned
 *   model. A model swap without contract review is an architectural regression.
 *
 * PALS_LAW_VERSION: 1.5.4
 *   ↑ REQUIRED. Spec version this contract was authored against. A spec update
 *   without contract review may introduce new error classes or change
 *   verification requirements.
 *
 * INVARIANT (operative form): For any model M and realistic task distribution 𝒟,
 * the expected error rate is non-negligible:
 *
 *   𝔼[ε(M(x), x)] ≥ δ > 0   where δ is empirically measurable
 *
 * Existential form (formally establishable): ∃ x such that P(ε(M(x),x)=1) > 0
 *
 * For pipelines of length n with per-step error probabilities p_i > 0:
 *
 *   P(pipeline error-free) = ∏(1 - p_i) < 1
 *   P(at least one error)  → 1  as  n → ∞
 *   Note: assumes independent calls — see PALS_LAW.md §7.3 for correlation caveat.
 *
 * CONSEQUENCE: Any caller of this function that does not explicitly
 * validate the output is introducing an architectural omission —
 * not a downstream bug.
 *
 * ERROR CLASSES NOT COVERED BY THIS CALLER'S VERIFIER:
 *   [ ] ERR_HALLUCINATION   — factual claims unverified against ground truth
 *   [ ] ERR_OMISSION        — required content not checked for completeness
 *   [ ] ERR_SCHEMA          — output structure not validated
 *   [ ] ERR_TRUNCATION      — output length/completeness not asserted
 *   [ ] ERR_SYCOPHANCY      — preference-driven distortion not controlled for
 *   [ ] ERR_INSTRUCTION     — constraint satisfaction not verified
 *   [ ] ERR_CALIBRATION     — confidence alignment not checked
 *   [ ] ERR_SEMANTIC        — semantic correctness not independently verified
 *   [ ] ERR_REASONING       — multi-step inference validity not checked
 *
 * Fill in the checklist above. Unchecked boxes are known, accepted risks.
 * Leaving all boxes unchecked with no mitigation note is a blocking defect.
 */
```

### 9.2 Short-Form (headers, PR descriptions, commit messages)

```
ARCHITECTURAL REQUIREMENT (PALS's LAW):
LLM error rates are non-negligible across realistic deployments.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
```

### 9.3 Inline Banner (single-line, for code comments)

```typescript
// ⚠ PALS's LAW: LLM output is untrusted by default. Verify before use.
```

### 9.4 CLAUDE.md Integration Block

Paste verbatim into the `LLM Output Verification` section of any `CLAUDE.md`:

```markdown
## LLM Output Verification — Architectural Requirement (PALS's LAW)

**Principle authored by:** Pedro Anisio de Luna e Silva  
**PALS_LAW_VERSION:** 1.5.4

**Across any realistic deployment, LLMs reliably produce errors —
at a rate that is non-zero and non-negligible.**
For any model M and realistic task distribution 𝒟:

    𝔼[ε(M(x), x)] ≥ δ > 0   (δ non-negligible, empirically measurable)

No individual call is guaranteed to fail; the distribution over calls
guarantees failure at scale. Omissions, hallucinations, partial completions,
schema violations, and silent failures are not edge cases — they are
statistical properties of the model class. In pipelines of length n
(assuming approximately independent calls — see full specification for
correlation analysis), unverified error probability approaches 1
monotonically.

Failing to verify LLM output is not a bug in the generated artifact.
It is an **architectural omission** in the system that consumed it.

Every pipeline, agent, or workflow that accepts LLM output MUST treat
that output as **untrusted, incomplete, and unverified by default.**
Verification is not optional post-processing — it is a first-class
design concern, on par with authentication and input validation.

> Absence of a verification layer is a design defect, regardless of
> how correct the LLM output appears to be.

Full specification: [PALS_LAW.md](./PALS_LAW.md)
```

---

*End of document — PALS's LAW v1.5.4*
