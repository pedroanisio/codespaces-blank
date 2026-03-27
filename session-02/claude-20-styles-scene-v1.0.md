---
title: "20 Styles of Scene — Formal Definitions"
version: "1.0.0"
status: draft
companion: "20-styles-video-v1.1.md"
disclaimer: >
  No information within this document should be taken for granted.
  Any statement or premise not backed by a real logical definition or
  verifiable reference may be invalid, erroneous, or a hallucination.
  Definitions here are analytical and stipulative; they are not citations
  of any single external authority unless explicitly stated. The reader
  is responsible for independent verification of any claim before relying
  on it.
---

---

# 20 Styles of Scene — Formal Definitions

## 0. Foundational Apparatus

### 0.1 The Scene Tuple

A **scene** $\Sigma$ is a 9-tuple:

$$\Sigma = (F_\Sigma,\; T_\Sigma,\; \alpha_\Sigma,\; \lambda,\; \tau_d,\; \omega,\; \eta,\; \psi,\; \rho)$$

| Symbol | Domain | Meaning |
|--------|--------|---------|
| $F_\Sigma$ | $\mathbb{Z}_{>0} \to \text{Image}$ | Ordered finite sequence of frames |
| $T_\Sigma = [s_0, s_1]$ | $\mathbb{R}_{\geq 0}$ | Temporal extent within parent video |
| $\alpha_\Sigma$ | $\{0, 1\}$ | Audio present ($1$) or absent ($0$) |
| $\lambda$ | $\Lambda$ | Diegetic location (§0.3) |
| $\tau_d$ | $\mathcal{T}_\mathcal{W} \cup \{\bot\}$ | Diegetic time (§0.3); $\bot$ if non-diegetic |
| $\omega$ | $\Omega$ | Ontological status (§0.4) |
| $\eta$ | $\mathcal{N}$ | Narrative function (§0.7) |
| $\psi$ | $\Psi$ | Camera grammar (§0.5) |
| $\rho$ | $\mathcal{R}$ | Editing grammar (§0.6) |

The **granularity** of $\Sigma$ is not fixed at a single level of the classical shot/scene/sequence hierarchy. A scene style predicate $\mathfrak{S}$ is a predicate $\mathfrak{S} : \Sigma \to \{0, 1\}$. All definitions below are **stipulative biconditionals**: each specifies necessary *and* sufficient conditions jointly. $\Sigma$ belongs to style $\mathfrak{S}$ if and only if it satisfies every stated condition.

### 0.2 Scene–Parent Relationship

The video tuple $V = (F, T, \alpha, \kappa, \pi, \delta)$ is as defined in the companion document *20 Styles of Video*. $\mathcal{W}_0$, $\mathcal{W}$, and the possible-worlds apparatus are used here as defined there without redefinition.

$\Sigma$ is a **sub-scene** of $V$, written $\Sigma \hookrightarrow V$, iff:

$$T_\Sigma \subseteq T_V, \quad F_\Sigma = F_V\big|_{T_\Sigma}, \quad \alpha_\Sigma = \alpha_V\big|_{T_\Sigma}$$

The attributes $(\lambda, \tau_d, \omega, \eta, \psi, \rho)$ are not derivable from $V$ alone; they require analysis of the scene's content and context. Some scene style predicates are defined **relative to** $V$: they quantify over properties of the parent video (e.g. structural position relative to the title sequence, or deviation from the film's mean cut rate). In such cases the definition makes the dependence on $V$ explicit.

A **scene segmentation** of $V$ is a partition $\{\Sigma_1, \ldots, \Sigma_n\}$ such that $T_{\Sigma_i} \cap T_{\Sigma_j} = \emptyset$ for $i \neq j$ and $\bigcup_i T_{\Sigma_i} = T_V$. No unique canonical segmentation exists; it is an analytic choice.

### 0.3 Diegetic Location and Diegetic Time

- $\Lambda$ is the set of **diegetic locations** — distinct places within the storyworld $\mathcal{W}$ (or $\mathcal{W}_0$ for documentary). $\lambda \in \Lambda$ is the primary location of $\Sigma$.
- $\mathcal{T}_\mathcal{W}$ is the **diegetic timeline** — a totally ordered set $(\mathcal{T}_\mathcal{W}, \prec)$ representing time within $\mathcal{W}$. $\tau_d \in \mathcal{T}_\mathcal{W}$ is the diegetic time at which the events of $\Sigma$ are set.
- The **narrative present** $\tau_{\text{narr}}(\Sigma) \in \mathcal{T}_\mathcal{W}$ is the diegetic time established as "now" by the most recent narrative event in $V$ preceding $s_0$.

Temporal displacement relations, following Genette (1980):

$$\text{Analeptic (flashback):}\quad \tau_d \prec \tau_{\text{narr}}(\Sigma)$$
$$\text{Proleptic (flash-forward):}\quad \tau_d \succ \tau_{\text{narr}}(\Sigma)$$
$$\text{Synchronous (present-tense):}\quad \tau_d = \tau_{\text{narr}}(\Sigma)$$

When $\omega = \texttt{non-diegetic}$ (§0.4), $\tau_d = \bot$: the concept of diegetic time does not apply.

### 0.4 Ontological Status $\omega$

$$\omega \in \Omega = \{\texttt{objective},\; \texttt{subjective},\; \texttt{non-diegetic}\}$$

- $\omega = \texttt{objective}$: the events of $\Sigma$ are asserted to have occurred in $\mathcal{W}$ (or $\mathcal{W}_0$ for documentary) as facts accessible in principle to any agent within $\mathcal{W}$.
- $\omega = \texttt{subjective}$: the content of $\Sigma$ is the mental representation of a specific diegetic agent $a$ — a dream, hallucination, memory, or imagining. It may or may not correspond to events that occurred in $\mathcal{W}$.
- $\omega = \texttt{non-diegetic}$: the content of $\Sigma$ is not part of $\mathcal{W}$ — title cards, credit sequences, abstract graphic inserts, or frames addressed directly to the audience outside any storyworld.

### 0.5 Camera Grammar $\psi$

$$\psi = (\sigma,\; \mu,\; \nu_{\text{cam}})$$

| Component | Domain | Meaning |
|-----------|--------|---------|
| $\sigma$ | $\mathcal{S}_{\text{scale}} = \{\texttt{XCU}, \texttt{CU}, \texttt{MCU}, \texttt{MS}, \texttt{MWS}, \texttt{WS}, \texttt{EWS}\}$ | Dominant shot scale (extreme close-up through extreme wide shot) |
| $\mu$ | $\mathcal{M}_{\text{cam}} = \{\texttt{static}, \texttt{handheld}, \texttt{tracking}, \texttt{crane/aerial}, \texttt{rig-mounted}\}$ | Dominant camera movement type |
| $\nu_{\text{cam}}$ | $\{\texttt{objective}, \texttt{subjective}, \texttt{semi-subjective}\}$ | Perspective type |

Perspective type definitions:
- $\nu_{\text{cam}} = \texttt{objective}$: camera position is not associated with any diegetic agent's perceptual position.
- $\nu_{\text{cam}} = \texttt{subjective}$: camera position and movement are coincident with the perceptual position of a diegetic agent $a$ — the viewer is presented with $a$'s visual field.
- $\nu_{\text{cam}} = \texttt{semi-subjective}$: camera is proximate to but not coincident with $a$'s position (e.g. over-the-shoulder); the viewer shares $a$'s spatial orientation without being identified with $a$'s gaze.

### 0.6 Editing Grammar $\rho$

$$\rho = (C_\Sigma,\; \gamma_\Sigma)$$

| Component | Domain | Meaning |
|-----------|--------|---------|
| $C_\Sigma = \{c_1, \ldots, c_k\}$ | $\mathcal{P}(T_\Sigma)$ | Set of cut times within $T_\Sigma$; $k = \lvert C_\Sigma \rvert$ |
| $\gamma_\Sigma$ | $\Gamma = \{\texttt{continuity},\, \texttt{discontinuity},\, \texttt{associative},\, \texttt{parallel},\, \texttt{none}\}$ | Editing grammar class |

Cut frequency: $\nu_c = k \,/\, \lvert T_\Sigma \rvert$ (cuts per second).

Grammar class definitions:
- $\gamma_\Sigma = \texttt{continuity}$: cuts maintain spatial, temporal, and directional coherence (180-degree rule, eyeline match, match-on-action).
- $\gamma_\Sigma = \texttt{discontinuity}$: cuts violate one or more continuity conventions (jump cut, axis crossing, unmotivated non-diegetic insert).
- $\gamma_\Sigma = \texttt{associative}$: cuts are motivated by thematic, metaphorical, or temporal association rather than spatial or temporal continuity.
- $\gamma_\Sigma = \texttt{parallel}$: cuts alternate between $\geq 2$ distinct spatial locations to assert their simultaneity in $\mathcal{T}_\mathcal{W}$.
- $\gamma_\Sigma = \texttt{none}$: $k = 0$; the scene is a single uninterrupted shot.

### 0.7 Narrative Function $\eta$

$\eta \in \mathcal{N}$, where $\mathcal{N}$ is an open-ended set of narrative function labels. The following are used in this document:

$$\mathcal{N} \supseteq \{\texttt{orient},\; \texttt{advance},\; \texttt{develop},\; \texttt{inform},\; \texttt{climax},\; \texttt{connect},\; \texttt{paratext},\; \texttt{compress},\; \texttt{resolve},\; \texttt{respond},\; \texttt{establish\text{-}premise}\}$$

Definitions are given intensionally where each style is introduced.

---

## 1. Establishing Scene

$$\mathfrak{S}_{\text{est}}(\Sigma) = 1 \iff$$

- The scene introduces a diegetic location $\lambda \in \Lambda$ not previously shown in $V$ before $s_0$: $\lambda \notin \Lambda_{\text{prev}}(T_\Sigma)$, where $\Lambda_{\text{prev}}(T_\Sigma) = \{\lambda' \mid \lambda' \text{ established in } V \text{ before } s_0\}$
- $\sigma \in \{\texttt{WS}, \texttt{EWS}\}$: dominant shot is wide or extreme-wide, providing spatial context for the new location
- $\eta = \texttt{orient}$: the primary narrative function is spatial orientation; no significant plot action is advanced within $\Sigma$ itself
- $\omega = \texttt{objective}$

---

## 2. Dialogue Scene

$$\mathfrak{S}_{\text{dial}}(\Sigma) = 1 \iff$$

- $F_\Sigma$ primarily depicts $\geq 2$ diegetic agents $\{a_1, a_2, \ldots\}$ in verbal exchange
- $\alpha_\Sigma = 1$ and the primary audio content is the speech of $\{a_i\}$
- $\gamma_\Sigma = \texttt{continuity}$; the dominant shot pattern is shot/reverse-shot or ensemble framing
- $\omega = \texttt{objective}$
- $\eta \in \{\texttt{advance},\; \texttt{develop}\}$: the exchange advances plot or develops character through speech acts

---

## 3. Action Sequence

$$\mathfrak{S}_{\text{act}}(\Sigma) = 1 \iff$$

- The primary content of $F_\Sigma$ is physical activity of high kinetic energy — fight, chase, pursuit, stunt, or large-scale destruction — occurring in $\mathcal{W}$
- $\nu_c > \bar{\nu}_c(V)$: cut frequency exceeds the mean cut frequency of $V$[^act-nu]
- $\mu \in \{\texttt{handheld},\; \texttt{tracking},\; \texttt{rig-mounted}\}$: camera movement is dynamic, not static
- $\omega = \texttt{objective}$

[^act-nu]: $\bar{\nu}_c(V)$ is the mean cut frequency computed over the full segmentation of $V$. This is a relational condition: an action sequence is defined by elevated cut rate relative to its host video, not by any absolute value. The condition is sensitive to the overall editing style of $V$ — a hyperkinetically edited film sets a higher baseline.

---

## 4. Montage Sequence

$$\mathfrak{S}_{\text{mont}}(\Sigma) = 1 \iff$$

- $\gamma_\Sigma = \texttt{associative}$: cuts are motivated by thematic, temporal, or metaphorical association, not spatial or temporal continuity
- Temporal compression holds: the diegetic duration $\lvert \tau_d^{\text{end}} - \tau_d^{\text{start}} \rvert$ substantially exceeds $\lvert T_\Sigma \rvert$ — a large span of diegetic time is compressed into short screen time[^mont-compress]
- $k$ is large relative to $\lvert T_\Sigma \rvert$: cut density is high
- $\omega = \texttt{objective}$

**Genealogy:** The montage sequence as a formal device is associated with the Soviet school (Eisenstein, *Film Form*, 1949; Pudovkin, *Film Technique*, 1929). In the Hollywood tradition the term designates primarily temporal compression; it does not invoke the full Eisensteinian theory of intellectual collision montage, which is a distinct (and more general) doctrine.

[^mont-compress]: "Substantially exceeds" is intentionally not given a formal ratio: no canonical threshold exists in the literature. The condition requires that the compression be perceptible and intended; a scene in which $\lvert T_\Sigma \rvert \approx \lvert \tau_d^{\text{end}} - \tau_d^{\text{start}} \rvert$ is not a montage sequence.

---

## 5. Flashback Scene

$$\mathfrak{S}_{\text{fl}}(\Sigma) = 1 \iff$$

- $\omega \in \{\texttt{objective},\; \texttt{subjective}\}$: the depicted events occurred — in $\mathcal{W}$ as objective fact, or in the memory/record of an agent $a$ — prior to the narrative present
- $\tau_d \prec \tau_{\text{narr}}(\Sigma)$: diegetic time of $\Sigma$ is strictly earlier than the narrative present at the insertion point
- The temporal displacement is marked by at least one diegetic or non-diegetic cue — voiceover, visual effect, title card, or editing convention — that signals departure from the narrative present

**Note:** When $\omega = \texttt{subjective}$, $\tau_d$ refers to the time of the *remembered event*, not the time of remembering. The flashback may be unreliable: the depicted event need not have occurred in $\mathcal{W}$ (cf. the unreliable narrator in literary theory).

---

## 6. Flash-Forward Scene

$$\mathfrak{S}_{\text{ffw}}(\Sigma) = 1 \iff$$

- $\omega \in \{\texttt{objective},\; \texttt{subjective}\}$
- $\tau_d \succ \tau_{\text{narr}}(\Sigma)$: diegetic time of $\Sigma$ is strictly later than the narrative present at the insertion point
- The temporal displacement is marked as a proleptic departure from the narrative present

**Epistemic status:** When $\omega = \texttt{objective}$, the flash-forward carries a strong commitment — the depicted events are asserted to *will* occur in $\mathcal{W}$, which constrains subsequent narrative. When $\omega = \texttt{subjective}$ (vision, premonition, anxiety), no such commitment is asserted, and the events may not occur.

---

## 7. Dream / Fantasy Insert

$$\mathfrak{S}_{\text{drm}}(\Sigma) = 1 \iff$$

- $\omega = \texttt{subjective}$: the content of $\Sigma$ is the mental representation — dream, hallucination, fantasy, or imagining — of a specific diegetic agent $a$
- $F_\Sigma$ is marked by one or more perceptual distortion indicators that distinguish it from $\omega = \texttt{objective}$ footage: atypical colour grading, non-Euclidean spatial relations, physically impossible events, or a stylistic discontinuity with surrounding scenes
- The subjective source $a$ is identifiable: $a$ is either shown entering the mental state (falling asleep, losing consciousness) or established by unambiguous narrative context

**Formal intersection:** $\mathfrak{S}_{\text{drm}} \cap \mathfrak{S}_{\text{fl}} \neq \emptyset$ — a memory-dream satisfies both predicates when $\tau_d \prec \tau_{\text{narr}}(\Sigma)$.

**Distinction from $\mathfrak{S}_{\text{pov}}$:** A POV scene (§10) depicts what $a$ *perceives* in $\mathcal{W}$; a dream insert depicts what $a$ *represents mentally*. Hallucination may satisfy both simultaneously.

---

## 8. Long Take (Oner)

$$\mathfrak{S}_{\text{lt}}(\Sigma) = 1 \iff$$

- $\gamma_\Sigma = \texttt{none}$: $k = 0$; $F_\Sigma$ is produced by a single continuous shot with no cuts
- The absence of cuts is **constitutive**: $\pi_V$ deploys the unbroken take as a deliberate formal choice, not as a default for a short scene[^lt-intent]
- $\lvert T_\Sigma \rvert$ is sufficient for the absence of cuts to be perceptible as a stylistic decision; no formal lower bound is specified[^lt-duration]

No constraint is placed on $\omega$, $\eta$, $\lambda$, or the components of $\psi$ beyond the above.

[^lt-intent]: Distinguishes from scenes that are single shots merely because they are brief (e.g. a two-second insert). The intentionality condition is grounded in $\pi_V$ — the production intent of the parent video — as defined in the companion document.
[^lt-duration]: Canonical examples include *Rope* (Hitchcock, 1948), the Copa shot in *GoodFellas* (Scorsese, 1990), and the hospital corridor in *Children of Men* (Cuarón, 2006). No authoritative minimum duration is defined in the scholarly literature; the condition is qualitative.

---

## 9. Cross-Cut Sequence

$$\mathfrak{S}_{\text{xcut}}(\Sigma) = 1 \iff$$

- $\gamma_\Sigma = \texttt{parallel}$: $F_\Sigma$ alternates between $\geq 2$ distinct diegetic locations $\lambda_1, \lambda_2, \ldots \in \Lambda$ with $\lambda_i \neq \lambda_j$ for $i \neq j$
- The alternation asserts **diegetic simultaneity**: events at $\lambda_1, \lambda_2, \ldots$ are presented as co-occurring at the same diegetic time in $\mathcal{T}_\mathcal{W}$
- $k \geq 2p - 1$ where $p$ is the number of distinct location-blocks — the minimum cut count to establish all $p$ locations and complete at least one return alternation[^xcut-min]
- $\omega = \texttt{objective}$

**Distinction from $\mathfrak{S}_{\text{ss}}$ (§16):** Cross-cutting presents locations *sequentially* via cuts, asserting simultaneity through editing grammar. Split-screen presents locations *simultaneously* within a single frame. Both assert simultaneity in $\mathcal{T}_\mathcal{W}$; they differ in the frame-level mechanism.

[^xcut-min]: The minimum bound $2p - 1$ follows from structure: to alternate among $p$ locations you need at least $p - 1$ cuts to introduce each and at least $p - 1$ return cuts. In practice $k \gg 2p - 1$.

---

## 10. Point-of-View (POV) Scene

$$\mathfrak{S}_{\text{pov}}(\Sigma) = 1 \iff$$

- $\nu_{\text{cam}} = \texttt{subjective}$: camera position and movement in $F_\Sigma$ are coincident with the perceptual position of a diegetic agent $a$
- The POV attribution is established by narrative convention: either (a) a cut from a shot of $a$'s face to the POV frame (the Kuleshov construction), or (b) sustained first-person identification maintained over $T_\Sigma$
- $a$ is identifiable; the scene is not an anonymous or authorless gaze

---

## 11. Exposition Scene

$$\mathfrak{S}_{\text{exp}}(\Sigma) = 1 \iff$$

- $\eta = \texttt{inform}$: the primary narrative function is to deliver information $\mathcal{I}$ to the viewer — world-building facts, backstory, character history, or plot prerequisites — that the viewer does not yet possess and that is required to understand subsequent events in $V$
- The information $\mathcal{I}$ is new to the viewer at $s_0$: $\mathcal{I} \cap \mathcal{I}_{\text{prev}} = \emptyset$, where $\mathcal{I}_{\text{prev}}$ is the information established in $V$ before $T_\Sigma$
- Kinetic energy is low: the scene does not advance narrative conflict through physical action; verbal delivery or visual display of information is the dominant mode
- $\omega = \texttt{objective}$

---

## 12. Set Piece

$$\mathfrak{S}_{\text{sp}}(\Sigma) = 1 \iff$$

- $\eta = \texttt{climax}$: $\Sigma$ occupies a narrative peak — the primary locus of conflict, confrontation, or spectacle in $V$ or in a major narrative arc within $V$
- $\lvert T_\Sigma \rvert$ is large relative to the mean scene duration $\overline{\lvert T \rvert}(V)$ in the segmentation of $V$ — the set piece is perceivably extended[^sp-duration]
- $\pi_V$ allocates disproportionate production resources to $\Sigma$: complexity of staging, choreography, visual effects, or location is visibly greater than in surrounding scenes
- $\omega = \texttt{objective}$

[^sp-duration]: "Large relative to the mean" is a relational condition indexed to the specific video, not an absolute threshold. No universal ratio is claimed.

---

## 13. Cold Open

$$\mathfrak{S}_{\text{co}}(\Sigma) = 1 \iff$$

- $V$ contains an identifiable title sequence $\Sigma_{\text{title}}$ satisfying $\mathfrak{S}_{\text{title}}$ (§18), with $T_{\Sigma_{\text{title}}} = [t_{\text{title}},\, t'_{\text{title}}]$
- $T_\Sigma$ lies entirely before the title sequence: $s_1 < t_{\text{title}}$
- $\Sigma$ contains diegetic narrative content — it is not itself a title or credit sequence
- $\eta \in \{\texttt{establish-premise},\; \texttt{advance}\}$: the cold open establishes a premise, creates a narrative hook, or presents action that precedes the formal introduction of the work

---

## 14. Coda / Tag Scene

$$\mathfrak{S}_{\text{coda}}(\Sigma) = 1 \iff$$

- Let $\Sigma_{\text{res}}$ denote the primary resolution scene of $V$ — the scene in which the main narrative conflict of $V$ is resolved — with $T_{\Sigma_{\text{res}}} = [t_{\text{res,0}},\, t_{\text{res,1}}]$
- $s_0 > t_{\text{res,1}}$: $\Sigma$ begins after $\Sigma_{\text{res}}$ has ended
- $\tau_d \succ \tau_{\text{narr}}(\Sigma_{\text{res}})$: diegetic time of $\Sigma$ is after the narrative conflict has been resolved
- $\eta \in \{\texttt{resolve},\; \texttt{establish-premise}\}$: the coda provides an epilogue, grace note, or sequel setup; it does not introduce new primary conflict

**Note:** Post-credits scenes in franchise films satisfy $\mathfrak{S}_{\text{coda}}$ when $\eta = \texttt{establish-premise}$ for a subsequent work. They are a special case where the coda is spatially separated from the main body of $V$ by the credit sequence.

---

## 15. Musical Number

$$\mathfrak{S}_{\text{mus}}(\Sigma) = 1 \iff$$

- $\alpha_\Sigma = 1$ and the primary audio content is the performance of a musical work $M$ — a song, dance number, or both
- The performance is the **primary** content of $F_\Sigma$: any narrative action within $\Sigma$ is subordinate to the performance, not the reverse
- The performance is either:
  - **Diegetic** ($\omega = \texttt{objective}$): agents within $\mathcal{W}$ are performing $M$; co-present agents could perceive it, or
  - **Non-diegetic**: $M$ accompanies the action but is inaudible within $\mathcal{W}$; agents are unaware of $M$

**Intersection:** $\mathfrak{S}_{\text{mus}} \cap \mathfrak{S}_{\text{sp}} \neq \emptyset$ — a musical number may simultaneously be a set piece when it constitutes the climactic scene of $V$ (canonical in the film musical genre).

---

## 16. Split-Screen Scene

$$\mathfrak{S}_{\text{ss}}(\Sigma) = 1 \iff$$

- For each frame $F_\Sigma(i)$, the image is partitioned into $\geq 2$ simultaneously visible sub-frames $\{f_1(i), f_2(i), \ldots, f_p(i)\}$ with $p \geq 2$
- Each sub-frame $f_j(i)$ depicts a distinct diegetic location $\lambda_j$ or a distinct diegetic temporal position $\tau_j$, with $(\lambda_j, \tau_j) \neq (\lambda_l, \tau_l)$ for $j \neq l$
- The simultaneous display is **constitutive** of the scene's communicative purpose: the meaning of $\Sigma$ depends on the viewer perceiving all sub-frames concurrently

**Formal note:** $\mathfrak{S}_{\text{lt}} \cap \mathfrak{S}_{\text{ss}} \neq \emptyset$ is possible — a split-screen may be constructed as a single continuous shot if the frame partition is achieved in-camera or in post-production without introducing cuts into $C_\Sigma$.

---

## 17. Documentary Insert

$$\mathfrak{S}_{\text{di}}(\Sigma) = 1 \iff$$

- The ontological register of $\Sigma$ differs from the dominant register of its parent video $V$:
  - If $V \in S_{\text{narr}}$: $\Sigma$ imports material from $\mathcal{W}_0$ — archival footage, news footage, interview material, or any content asserting $\mathfrak{m} = \texttt{assert}$ about $\mathcal{W}_0$ — into a diegetic frame asserting $\mathcal{W} \neq \mathcal{W}_0$
  - If $V \in S_{\text{doc}}$: $\Sigma$ is synthetically constructed, staged, or animated material inserted into an otherwise factual frame
- The register shift is **constitutive** of $\Sigma$'s meaning within $V$, whether or not it is explicitly marked to the viewer

**Note on markedness:** The insert may be *marked* (the viewer is told it is archival or constructed) or *unmarked* (it is embedded without explicit signal). Both satisfy $\mathfrak{S}_{\text{di}}$; the ethical and interpretive consequences differ.

---

## 18. Title / Credit Sequence

$$\mathfrak{S}_{\text{title}}(\Sigma) = 1 \iff$$

- $\omega = \texttt{non-diegetic}$: the content of $\Sigma$ is not part of $\mathcal{W}$
- $F_\Sigma$ consists primarily of text — the title of $V$, principal credits, or both — overlaid on image or presented against a dedicated graphical or abstract background
- $\eta = \texttt{paratext}$: the primary function is to frame $V$ for the viewer before narrative content begins (opening titles) or to acknowledge the production after it concludes (closing credits)

**Theoretical basis:** The title sequence is a paratextual device in the sense of Genette (1997, *Paratexts*) — it is not part of the narrative but conditions the terms of its reception.

---

## 19. Transition Scene

$$\mathfrak{S}_{\text{trans}}(\Sigma) = 1 \iff$$

- $\eta = \texttt{connect}$: the primary function of $\Sigma$ is to bridge two adjacent scenes $\Sigma_{\text{prev}}$ and $\Sigma_{\text{next}}$ — conveying temporal displacement, spatial displacement, or both — without itself carrying primary narrative content
- $\Sigma$ does not advance narrative conflict, develop character, or deliver new information $\mathcal{I}$ that is required to understand subsequent events
- Typical realizations: driving or walking shot, time-lapse, exterior establishing bridge, aerial flyover, or abstract dissolve sequence

**Intersection:** $\mathfrak{S}_{\text{trans}} \cap \mathfrak{S}_{\text{est}} \neq \emptyset$ — a transition scene that simultaneously introduces a new location $\lambda \notin \Lambda_{\text{prev}}$ satisfies both predicates.

---

## 20. Reaction Scene

$$\mathfrak{S}_{\text{rx}}(\Sigma) = 1 \iff$$

- $\nu_{\text{cam}} = \texttt{semi-subjective}$: $F_\Sigma$ is dominated by the face or body of a diegetic agent $a$ in the act of responding to a stimulus $\xi$
- The primary communicative content of $\Sigma$ is $a$'s affective or cognitive response to $\xi$, not $\xi$ itself: $\xi$ is either offscreen throughout $T_\Sigma$, or has been presented and $\Sigma$ follows without re-presenting $\xi$
- $\eta = \texttt{respond}$
- $\omega = \texttt{objective}$ or $\omega = \texttt{subjective}$: the reaction may be an objective visible response or a subjective internal state rendered externally (e.g. slow motion, heightened score)

**Theoretical basis:** The reaction scene formalises the Kuleshov effect (Kuleshov, 1929) at scene scale. Kuleshov demonstrated that the meaning produced by juxtaposing a neutral face with an external stimulus is constructed by the viewer, not inherent in the face. The reaction scene is the structural envelope that deploys this mechanism over an extended temporal unit rather than a single cut pair.

---

## Summary: Scene Style Space

### Predicate Family Structure

The 20 scene style predicates form a **family of overlapping sets** $\{\mathfrak{S}_X \subseteq \Sigma\}$ — not a lattice unless containment is specifically proved for a given pair.

**Proved disjunctions** (by formal exclusion from the biconditional conditions):

$$\mathfrak{S}_{\text{lt}} \cap \mathfrak{S}_{\text{xcut}} = \emptyset$$

because $\mathfrak{S}_{\text{lt}}$ requires $k = 0$ and $\mathfrak{S}_{\text{xcut}}$ requires $k \geq 2p - 1 \geq 1$.

**Proved non-empty intersections:**

| Pair | Basis |
|------|-------|
| $\mathfrak{S}_{\text{drm}} \cap \mathfrak{S}_{\text{fl}}$ | Memory-dreams are analeptic |
| $\mathfrak{S}_{\text{xcut}} \cap \mathfrak{S}_{\text{act}}$ | Parallel chase sequences |
| $\mathfrak{S}_{\text{mus}} \cap \mathfrak{S}_{\text{sp}}$ | Climactic musical number |
| $\mathfrak{S}_{\text{trans}} \cap \mathfrak{S}_{\text{est}}$ | Bridge to new location |
| $\mathfrak{S}_{\text{lt}} \cap \mathfrak{S}_{\text{ss}}$ | In-camera split-screen, no cuts |
| $\mathfrak{S}_{\text{mont}} \cap \mathfrak{S}_{\text{act}}$ | Rapid-cut action montage |

### Axes of Predicate Type

The 20 predicates are not commensurable — they operate across orthogonal axes at different levels of abstraction:

| Axis | Predicates | Primary formal constraint |
|------|-----------|--------------------------|
| **Temporal displacement** | $\mathfrak{S}_{\text{fl}},\; \mathfrak{S}_{\text{ffw}}$ | $\tau_d \prec / \succ \tau_{\text{narr}}(\Sigma)$ |
| **Ontological status** | $\mathfrak{S}_{\text{drm}},\; \mathfrak{S}_{\text{di}},\; \mathfrak{S}_{\text{title}}$ | $\omega \in \{\texttt{subjective},\; \texttt{non-diegetic}\}$ |
| **Editing grammar** | $\mathfrak{S}_{\text{mont}},\; \mathfrak{S}_{\text{xcut}},\; \mathfrak{S}_{\text{lt}}$ | $\gamma_\Sigma$ and $\lvert C_\Sigma \rvert$ |
| **Camera grammar** | $\mathfrak{S}_{\text{pov}},\; \mathfrak{S}_{\text{rx}},\; \mathfrak{S}_{\text{est}}$ | $\nu_{\text{cam}}$ and $\sigma$ |
| **Narrative function** | $\mathfrak{S}_{\text{exp}},\; \mathfrak{S}_{\text{sp}},\; \mathfrak{S}_{\text{trans}},\; \mathfrak{S}_{\text{coda}}$ | $\eta$ |
| **Structural position in $V$** | $\mathfrak{S}_{\text{co}},\; \mathfrak{S}_{\text{coda}},\; \mathfrak{S}_{\text{title}}$ | $T_\Sigma$ relative to $T_V$ |
| **Frame geometry** | $\mathfrak{S}_{\text{ss}}$ | Sub-frame partition of $F_\Sigma(i)$ |
| **Content type** | $\mathfrak{S}_{\text{dial}},\; \mathfrak{S}_{\text{act}},\; \mathfrak{S}_{\text{mus}}$ | Dominant content of $F_\Sigma$ |

### Relationship to Video Style Predicates

Scene styles and video styles are defined at different levels of analysis and are formally compatible:

- Video styles $S_X$ are predicates on $V$; scene styles $\mathfrak{S}_X$ are predicates on $\Sigma \hookrightarrow V$.
- Some scene styles are **constitutively dependent** on video styles: $\mathfrak{S}_{\text{di}}$ is defined relative to $V \in S_{\text{narr}}$ or $V \in S_{\text{doc}}$; $\mathfrak{S}_{\text{co}}$ and $\mathfrak{S}_{\text{coda}}$ reference the structural position of $\Sigma$ within $V$.
- Video styles constrain the **distribution** of scene style predicates across a segmentation $\{\Sigma_i\}$: $V \in S_{\text{doc}}$ requires $\omega = \texttt{objective}$ for most $\Sigma_i$; $V \in S_{\text{narr}}$ permits $\omega \in \{\texttt{objective},\; \texttt{subjective}\}$; $V \in S_{\text{surv}}$ entails $\omega = \texttt{objective}$ and $\eta$ is vacuous for all $\Sigma_i$.
- The long take and montage sequence (scene-level predicates) have direct counterparts in video-level style: a video may be characterised globally by these techniques, but the formal scene-level definitions are more precise.

### Three Structural Observations

**First:** Three predicates — $\mathfrak{S}_{\text{fl}}$, $\mathfrak{S}_{\text{ffw}}$, and $\mathfrak{S}_{\text{drm}}$ — are the only ones that require the full diegetic time apparatus $(\tau_d, \tau_{\text{narr}})$. All others can be specified using the remaining components of $\Sigma$ alone. This suggests temporal displacement is a structurally distinct axis from the others.

**Second:** $\mathfrak{S}_{\text{lt}}$ is the only predicate defined by a **zero condition** on a component: $k = 0$. All other predicates make positive assertions about the values of $\Sigma$'s components. This gives the long take a unique logical character — it is defined by the absence of editing, not by the presence of any particular kind.

**Third:** Three predicates — $\mathfrak{S}_{\text{co}}$, $\mathfrak{S}_{\text{coda}}$, and $\mathfrak{S}_{\text{title}}$ — are defined by **structural position** within $V$ rather than by any intrinsic property of $\Sigma$ itself. The same frames, with the same $\omega$, $\eta$, $\psi$, and $\rho$, could satisfy or fail to satisfy these predicates depending solely on where in $V$ they appear. This means these three predicates are **extrinsic**: they are not properties of the scene in isolation.

---

## References

- Eisenstein, S. (1949). *Film Form: Essays in Film Theory*. Trans. Jay Leyda. Harcourt.
- Genette, G. (1980). *Narrative Discourse: An Essay in Method*. Trans. Jane E. Lewin. Cornell University Press.
- Genette, G. (1997). *Paratexts: Thresholds of Interpretation*. Trans. Jane E. Lewin. Cambridge University Press.
- Kuleshov, L. (1929). *The Art of Cinema*. [Russian original; cited in Bordwell, D. & Thompson, K. (2010). *Film Art: An Introduction*, 9th ed. McGraw-Hill, pp. 229–230.]
- Pudovkin, V. (1929). *Film Technique*. Trans. Ivor Montagu. Newnes.
