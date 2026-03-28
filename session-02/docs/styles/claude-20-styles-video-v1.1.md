---
title: "20 Styles of Video — Formal Definitions"
version: "1.1.0"
status: draft
changelog: >
  v1.1.0 — Fixed eight issues identified in peer review: (1) biconditional
  self-contradiction resolved by committing to full stipulative biconditionals
  and removing the inconsistent necessary-conditions disclaimer; (2) P and D
  given explicit type signatures; (3) composite modality given a boundary
  condition; (4) W_0 defined via possible-worlds semantics; (5) "lattice"
  replaced with the correct mathematical term; (6) empirical duration bounds
  removed from formal conditions and relegated to footnotes; (7) music-video
  synchronisation condition replaced with a well-formed production-intent
  formulation; (8) 4π steradian idealisation qualified; (9) incommensurability
  of predicate axes made explicit.
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

# 20 Styles of Video — Formal Definitions

## 0. Foundational Apparatus

Let a **video** $V$ be a 6-tuple:

$$V = (F,\, T,\, \alpha,\, \kappa,\, \pi,\, \delta)$$

where:

| Symbol | Domain | Meaning |
|--------|--------|---------|
| $F$ | $\mathbb{Z}_{>0} \to \text{Image}$ | Ordered finite sequence of raster frames |
| $T = [t_0, t_1]$ | $\mathbb{R}_{\geq 0}$ | Temporal extent (seconds) |
| $\alpha$ | $\{0, 1\}$ | Audio present ($1$) or absent ($0$) |
| $\kappa$ | $\{\text{live-action}, \text{synthetic}, \text{composite}\}$ | Capture modality |
| $\pi$ | $\mathcal{P}$ | Production intent (see §0.1) |
| $\delta$ | $\mathcal{D}$ | Distribution context (see §0.2) |

A **video style** $S$ is a predicate $S : V \to \{0, 1\}$.  The definitions below are **stipulative biconditionals**: each specifies necessary *and* sufficient conditions jointly.  A video $V$ belongs to style $S$ if and only if it satisfies every stated condition.

### 0.1 Capture Modality — Boundary Conditions

The three values of $\kappa$ are defined as follows:

- $\kappa = \text{live-action}$: every frame $F(i)$ is produced by optical projection of a physical scene onto a photosensitive or electronic sensor.
- $\kappa = \text{synthetic}$: every frame $F(i)$ is produced by algorithmic or manual image synthesis without optical capture of a physical scene.  This includes 2-D animation, CGI rendering, and screen recording.
- $\kappa = \text{composite}$: $F$ contains both optically captured frames and synthetically generated frames, with neither class comprising 100% of the sequence.  Formally: $\exists\, i, j \in \text{dom}(F)$ such that $F(i)$ is optically captured and $F(j)$ is synthetically generated.

### 0.2 Production Intent — $\mathcal{P}$

$\mathcal{P}$ is a set of production intent specifications.  Each element $\pi \in \mathcal{P}$ is a triple:

$$\pi = (\mathfrak{a},\, \mathfrak{g},\, \mathfrak{m})$$

where:
- $\mathfrak{a} \in \text{Agent}$: the authorial agent (human, collective, or automated system) who determines $F$.
- $\mathfrak{g} \in \text{Goal}$: the communicative or functional goal of the production.
- $\mathfrak{m} \in \mathcal{M}$: the epistemic modality of the production, with $\mathcal{M} = \{\texttt{assert},\, \texttt{persuade},\, \texttt{entertain},\, \texttt{demonstrate},\, \texttt{record\text{-}automated}\}$.

When definitions below make claims of the form "$\pi$ asserts …" or "$\pi$ deploys …", these are shorthand for conditions on the components of this triple.  In particular, $\mathfrak{m} = \texttt{record\text{-}automated}$ is the degenerate case in which $\mathfrak{a}$ makes no moment-to-moment authorial decisions (see §16, Surveillance).

### 0.3 Distribution Context — $\mathcal{D}$

$\mathcal{D}$ is a set of distribution context specifications.  Each element $\delta \in \mathcal{D}$ is a pair:

$$\delta = (\chi,\, \epsilon)$$

where:
- $\chi \in \text{Channel}$: the physical or platform channel through which $V$ reaches its audience (broadcast network, streaming platform, social feed, closed-circuit system, etc.).
- $\epsilon \in \mathcal{E}$: the epistemic contract between producer and audience, with $\mathcal{E} = \{\texttt{truth\text{-}claim},\, \texttt{fiction},\, \texttt{persuasive},\, \texttt{restricted\text{-}access},\, \texttt{algorithmic\text{-}feed}\}$.

When definitions below make claims of the form "$\delta$ addresses …" or "$\delta$ involves …", these are conditions on $(\chi, \epsilon)$.

### 0.4 The Actual World — $\mathcal{W}_0$

Several definitions distinguish content about the actual world from content about a fictional storyworld.  This document adopts the standard possible-worlds framework (Lewis, 1986, *On the Plurality of Worlds*; Kripke, 1980, *Naming and Necessity*) in the following minimal sense:

- $\mathcal{W}_0$ denotes the unique world that obtains — the actual world.
- A proposition $p$ is *true in* $\mathcal{W}_0$ (written $\mathcal{W}_0 \models p$) if $p$ holds under the actual state of affairs.
- A video $V$ makes a **truth claim about** $\mathcal{W}_0$ iff the authorial agent $\mathfrak{a}$ is committed, via $\mathfrak{m} = \texttt{assert}$, to the truth of the propositional content of $V$ in $\mathcal{W}_0$.
- A **storyworld** $\mathcal{W} \neq \mathcal{W}_0$ is a possible world constructed by a narrative; propositions true in $\mathcal{W}$ need not be true in $\mathcal{W}_0$.

This apparatus is used only to draw the documentary/fiction distinction; no commitment to modal realism beyond these definitions is required.

---

## 1. Documentary

$$S_{\text{doc}}(V) = 1 \iff$$

- $\kappa \in \{\text{live-action}, \text{composite}\}$
- $\mathfrak{m} = \texttt{assert}$: $\pi$ carries a truth claim — the authorial agent is committed to the propositional content of $V$ holding in $\mathcal{W}_0$
- The diegetic world of $V$ is not principally scripted fiction
- $\epsilon = \texttt{truth\text{-}claim}$: the audience is invited to form beliefs about $\mathcal{W}_0$ on the basis of $V$

**Core tension:** the truth claim is a *performative* commitment, not a logical guarantee. Docudramas and reconstructions satisfy $S_{\text{doc}}$ only if clearly framed as approximations to factual record.

---

## 2. Narrative Fiction Film

$$S_{\text{narr}}(V) = 1 \iff$$

- $\kappa \in \{\text{live-action}, \text{synthetic}, \text{composite}\}$
- $\pi$ constructs a **storyworld** $\mathcal{W} \neq \mathcal{W}_0$ (possibly overlapping with $\mathcal{W}_0$ in setting or historical fact, but not asserted to hold in $\mathcal{W}_0$)
- $V$ contains a causally structured sequence of events $e_1, e_2, \ldots, e_n$ with at least one agent whose goal-directed behaviour generates conflict
- $\epsilon = \texttt{fiction}$: no truth claim about $\mathcal{W}_0$ is asserted; the audience's epistemic contract is one of willing suspension

---

## 3. Animation

$$S_{\text{anim}}(V) = 1 \iff$$

- $\kappa = \text{synthetic}$ **or** ($\kappa = \text{composite}$ and, for more than half of the frames in $F$ by count, the frame is synthetically generated rather than optically captured)
- Each such synthetically generated frame is constructed by non-photographic image synthesis — drawing, computer rendering, stop-motion, puppet, or equivalent method — rather than optical capture

No constraint is placed on $\pi$ or $\delta$: animation is a **capture-modality class**, not an intent class, and may serve any of the other styles.

**Note:** Animation is orthogonal to content: $S_{\text{anim}} \cap S_{\text{doc}} \neq \emptyset$ (e.g. animated documentaries), $S_{\text{anim}} \cap S_{\text{narr}} \neq \emptyset$, etc.

---

## 4. Commercial / Advertisement

$$S_{\text{ad}}(V) = 1 \iff$$

- $\mathfrak{m} = \texttt{persuade}$: $\pi$ contains a persuasive intent targeting the viewer's disposition toward a product, service, brand, or idea
- $\delta$ involves a **paid placement** contract: a sponsor compensates a channel $\chi$ for distribution of $V$
- $\epsilon = \texttt{persuasive}$: the epistemic contract is one of rhetorical address, not factual transfer; $\pi$ deploys desire, identification, or affect rather than primarily epistemic transfer

> **Note on duration.** Broadcast advertisements are conventionally short (often $\leq 120\text{s}$ in many markets), but this is an industry convention, not a necessary condition. Duration is not part of the formal definition.[^ad-duration]

[^ad-duration]: Duration norms vary by network, country, regulatory regime, and era. Digital-native platforms impose no upper bound. No citation for a universal norm is available; the condition is omitted accordingly.

---

## 5. Music Video

$$S_{\text{mv}}(V) = 1 \iff$$

- $\alpha = 1$ and the primary audio track is a pre-existing musical work $M$ with temporal extent $|T_M|$ approximately equal to $|T|$
- $\mathfrak{g}$ is subordinate to $M$: the visual sequence $F$ is produced *in service of* $M$, commissioned or constructed to accompany, promote, or interpret it
- $\delta$ typically targets audiences of $M$'s artist and $\epsilon = \texttt{persuasive}$ in the sense that $V$ functions as promotional material for $M$
- The editing of $F$ is *governed* by the structure of $M$: cuts, transitions, and visual events are determined by musical or lyrical markers of $M$, not by an independent visual logic[^mv-sync]

[^mv-sync]: A statistical operationalisation of "governed by" would require specifying a null model of random edits, a measurable event set of musical markers, and a significance threshold — none of which are fixed by this definition. The condition as stated is a production-intent requirement ($\mathfrak{g}$ is subordinate to $M$), not a statistical claim. Empirical verification would require a corpus study and an agreed synchronisation metric.

---

## 6. News Broadcast

$$S_{\text{news}}(V) = 1 \iff$$

- $\mathfrak{m} = \texttt{assert}$: $\pi$ asserts current truth claims about $\mathcal{W}_0$; $T$ is proximate to the production date
- $\kappa \in \{\text{live-action}, \text{composite}\}$
- $\epsilon = \texttt{truth\text{-}claim}$ under a **journalistic epistemic contract**: claims are attributed, sourced, or explicitly marked as unverified
- Production is episodic and recurrent (not a one-off work), addressing a mass, non-specialist audience

---

## 7. Essay Film

$$S_{\text{essay}}(V) = 1 \iff$$

- $\pi$ articulates a **first-person discursive argument** — a claim or set of claims about $\mathcal{W}_0$ or about ideas — through the interplay of image, sound, and spoken/written text
- The argument is neither purely journalistic (no neutrality constraint) nor purely fictional ($\mathcal{W}_0 \models p$ for at least some propositional content of $V$)
- $F$ often includes archival material, personal footage, and abstract imagery serving the argument rather than documenting events
- $\delta$ assumes a viewer willing to engage with discursive ambiguity

*Genealogy:* The essay film as a distinct form is associated with filmmakers such as Chris Marker (*Sans Soleil*, 1983) and Agnès Varda. Rascaroli (2009, *The Personal Camera*, Wallflower Press) formalises it as distinct from documentary by the centrality of a subjective authorial voice.

---

## 8. Experimental / Avant-Garde Film

$$S_{\text{exp}}(V) = 1 \iff$$

- $\pi$ **refuses or interrogates** at least one normative constraint of the dominant distribution context $\delta$ — such as narrative causality, photographic realism, synchronised sound, stable frame rate, or coherent diegesis — where "normative" is relative to the conventions dominant at the time of production
- The refusal is *intentional* (part of $\mathfrak{g}$) and *constitutive* of the work's meaning, not incidental

No constraint on $\kappa$; experimental work spans all capture modes.

**Caution:** This is a relational definition — "experimental" is indexed to a historical norm. A technique experimental in 1920 (multiple exposure) may be conventional today.

---

## 9. Tutorial / Instructional Video

$$S_{\text{tut}}(V) = 1 \iff$$

- $\mathfrak{m} = \texttt{demonstrate}$: $\pi$ aims to transfer **procedural knowledge** — a sequence of steps $\sigma_1, \ldots, \sigma_n$ such that a viewer who executes $\sigma_1, \ldots, \sigma_n$ achieves a specified outcome state $O$
- $F$ is organised around the procedure: each temporal segment of $F$ corresponds to at least one $\sigma_i$
- $\epsilon$ addresses a viewer who lacks the procedural knowledge and intends to acquire it

---

## 10. Vlog (Video Blog)

$$S_{\text{vlog}}(V) = 1 \iff$$

- $\mathfrak{g}$ is **first-person diaristic**: the camera is presented as an extension of the author's perspective; $\mathfrak{a}$ is usually visible and audible on screen
- $\delta$ is a subscribing audience with parasocial expectations of continuity over time (a vlog is an entry in a series, not a standalone work)
- Production is low-formality: handheld or stationary personal camera, direct address, minimal post-production
- $\mathfrak{m} = \texttt{assert}$ in the weak sense of sincere first-person assertion; no claim beyond the author's own testimony is advanced

---

## 11. Live Stream

$$S_{\text{live}}(V) = 1 \iff$$

- $T_{\text{capture}} \approx T_{\text{broadcast}}$: frames are transmitted to $\delta$ at the moment of capture, with latency $\epsilon_\ell \leq \ell_{\max}$ where $\ell_{\max}$ is the platform's broadcast delay (typically $< 30\text{s}$)
- $\delta$ is a co-present, real-time audience capable of interacting with the production (chat, reactions, etc.)
- The temporal order of $F$ is fixed by the order of events; post-production editing does not determine $F$

**Implication:** $S_{\text{live}}$ is defined by a *production-distribution coupling*, not by content. A live stream may simultaneously satisfy $S_{\text{news}}$, $S_{\text{sport}}$, or $S_{\text{vlog}}$.

> **Notation note.** The symbol $\epsilon_\ell$ (latency bound) is distinct from $\epsilon$ (epistemic contract component of $\delta$). The two are disambiguated by subscript throughout.

---

## 12. Short-Form Vertical Video

$$S_{\text{sfv}}(V) = 1 \iff$$

- Frame aspect ratio $r = \text{width}/\text{height} < 1$ (portrait orientation; the canonical value is $9:16$)
- $\chi$ is an algorithmic-feed platform: the viewer did not specifically request $V$; $V$ is served by a recommendation system
- $\epsilon = \texttt{algorithmic\text{-}feed}$
- $\mathfrak{g}$ is optimised for immediate retention: the first two seconds of $F$ must prevent the viewer from advancing to the next item in the feed

No constraint is placed on $|T|$ as a formal condition: duration norms are platform-specific and have changed materially since 2020.[^sfv-duration] Duration is an empirical regularity, not a necessary condition of the style.

[^sfv-duration]: As of 2024: TikTok permits uploads up to 10 minutes (extended from 60 seconds in 2022); YouTube Shorts is capped at 60 seconds; Instagram Reels at 90 seconds. These bounds are subject to continued revision and are not stable enough to serve as formal conditions.

**Note:** This is a *distribution-format* class, not a content class. No constraint is placed on $\mathfrak{m}$ beyond the retention requirement.

---

## 13. Interview / Talking Head

$$S_{\text{int}}(V) = 1 \iff$$

- The primary visual subject is one or more persons speaking directly to camera or to an off-camera interlocutor
- $\mathfrak{g}$ aims to elicit and record the subject's **verbal testimony** on a specified topic
- $F$ is dominated by a stationary or minimally moving shot of the subject's face and upper body
- May function as a component of $S_{\text{doc}}$, $S_{\text{news}}$, or as a standalone form

---

## 14. Motion Graphics / Explainer Video

$$S_{\text{mg}}(V) = 1 \iff$$

- $\kappa \in \{\text{synthetic}, \text{composite}\}$: images are entirely or primarily computer-generated graphics, typography, and illustration
- $\mathfrak{m} = \texttt{demonstrate}$ in the declarative sense: $\pi$ aims to communicate a **concept, process, or data set** through animated graphic form
- $\alpha = 1$ with a voiceover narration temporally synchronised to $F$

**Distinction from $S_{\text{tut}}$:** An explainer transfers *declarative* knowledge (what $X$ is, or how $X$ works conceptually); a tutorial transfers *procedural* knowledge (how to perform $X$). The distinction maps to the classical declarative/procedural memory distinction.

> **Note on duration.** Explainer videos are conventionally short (often in the range 60–300 seconds), but this is a production norm, not a necessary condition, and is omitted from the formal definition for the same reasons as §4.[^mg-duration]

[^mg-duration]: No authoritative source defines a canonical duration range for motion graphics or explainer videos. The range 60–300 seconds is a common industry heuristic but varies widely.

---

## 15. Sports Broadcast

$$S_{\text{sport}}(V) = 1 \iff$$

- $\mathfrak{g}$ captures and presents an **athletic competition** $C$ occurring in $\mathcal{W}_0$
- $F$ is produced from multiple simultaneous camera angles with real-time switching
- $\delta$ includes a live or near-live audience with a shared interest in the outcome of $C$
- Typically satisfies $S_{\text{live}}$ during the competition; may include pre/post-production segments satisfying $S_{\text{news}}$ or $S_{\text{int}}$

---

## 16. Surveillance / CCTV Video

$$S_{\text{surv}}(V) = 1 \iff$$

- $\kappa = \text{live-action}$
- $\mathfrak{m} = \texttt{record\text{-}automated}$: $\mathfrak{a}$ makes no moment-to-moment authorial decisions about $F$; capture is automated and continuous
- $\chi$ is a security or monitoring system; $\epsilon = \texttt{restricted\text{-}access}$: distribution is access-restricted and not addressed to a public audience
- $F$ is not edited for communicative intent; footage is raw and unprocessed

**Formal consequence:** $S_{\text{surv}}$ is the limiting case where authorship is vacuous: $\mathfrak{a}$ has no active communicative role, and $\epsilon = \texttt{restricted\text{-}access}$ closes the distribution context. This distinguishes it from all other styles, every one of which requires a non-null $\mathfrak{m}$ and a non-restricted $\epsilon$.

---

## 17. 360° / VR Video

$$S_{\text{vr}}(V) = 1 \iff$$

- $F$ is a sequence of equirectangular or omnidirectional frames encoding, approximately, the full solid angle of a scene; specifically, the encoded solid angle $\Omega_{\text{enc}}$ satisfies $\Omega_{\text{enc}} \geq \Omega_{\min}$ for some platform-specified minimum coverage threshold $\Omega_{\min} < 4\pi$ steradians[^vr-omega]
- The viewer's rendered viewport is a dynamic function of the viewer's head orientation at playback time: $F_{\text{viewed}}(t) = F(t)\big|_{\theta(t), \phi(t)}$ where $(\theta, \phi)$ are the viewer's azimuth and elevation at time $t$
- $\delta$ requires a head-mounted display or interactive omnidirectional player for full realisation; flat-screen playback degrades the experience to panning

**Distinction:** Unlike all other styles, the frame presented to the viewer is not determined solely by $\pi$ but also by the viewer's embodied state at playback time.

[^vr-omega]: No consumer 360° capture system achieves exactly $4\pi$ steradians. Common dual-fisheye devices (e.g. Ricoh Theta, Insta360 ONE X) have nadir blind spots and stitching seams, typically covering $\geq 95\%$ of the sphere. The formal condition uses $\Omega_{\min}$ as a platform-defined threshold rather than the ideal $4\pi$.

---

## 18. Screencast

$$S_{\text{sc}}(V) = 1 \iff$$

- $\kappa = \text{synthetic}$: $F$ is produced by recording the pixel output of a computing device's display, not an optical scene
- The primary content of $F$ is the **state of a software interface** over time
- $\mathfrak{g}$ aims at demonstration ($S_{\text{tut}}$), documentation, or communication about software behaviour
- $\alpha = 1$ is typical (voiceover or system audio), but $\alpha = 0$ is compatible with the definition; no optical camera is required

---

## 19. Found Footage (as genre)

$$S_{\text{ff}}(V) = 1 \iff$$

- $V$ is presented within a fictional storyworld $\mathcal{W} \neq \mathcal{W}_0$ as a recording discovered, recovered, or assembled from archival sources within $\mathcal{W}$
- The fictional conceit holds that $F$ was captured by characters *within* $\mathcal{W}$, not by an external film crew
- $\pi$ deploys this conceit to assert (within the fiction, and falsely relative to $\mathcal{W}_0$) that $V \in S_{\text{surv}}$ or $V \in S_{\text{vlog}}$ — i.e., found footage borrows the aesthetic markers of unmediated capture as a narrative device
- $\epsilon = \texttt{fiction}$: the audience recognises the fictional frame (distinguishing this genre from deliberate hoax)

**Note:** "Found footage" in the archival sense — actual pre-existing footage incorporated into a new work — satisfies different conditions; the above definition applies to the *narrative genre* associated with horror and thriller cinema (e.g. *The Blair Witch Project*, dir. Myrick and Sánchez, 1999; *Cloverfield*, dir. Reeves, 2008).

---

## 20. Mockumentary

$$S_{\text{mock}}(V) = 1 \iff$$

- $V$ deploys all surface-level formal conventions of $S_{\text{doc}}$: handheld camera, $S_{\text{int}}$ segments, direct address, title cards asserting dates/places
- The diegetic world of $V$ is a fictional storyworld $\mathcal{W} \neq \mathcal{W}_0$
- $\mathfrak{g}$ is *parodic or satirical*: the gap between documentary form and fictional content is the primary source of meaning or humour
- $\epsilon = \texttt{fiction}$: $\delta$ recognises the fictional frame, distinguishing the work from deliberate deception

**Formal relation:** $S_{\text{mock}} \subset S_{\text{narr}}$ with documentary *form* borrowed as a rhetorical device. The content is fictional ($\mathcal{W} \neq \mathcal{W}_0$); the form signals truth ($\epsilon$ mimics $\texttt{truth\text{-}claim}$). The tension between these is constitutive.

---

## Summary: Style Space as a Family of Overlapping Predicates

### Correct Mathematical Description

The 20 styles are predicates on the common domain $V$, forming a **family of subsets** $\{S_X \subseteq V\}$ under set inclusion. This is *not* a lattice in the standard sense: a lattice requires that every pair $(S_i, S_j)$ admit a greatest lower bound and least upper bound under the partial order; this has not been established for the full family.

What can be said:

- Where containment has been proved — e.g. $S_{\text{mock}} \subset S_{\text{narr}}$ — a local partial order exists.
- Several pairs have non-empty intersection without either containing the other: $S_{\text{live}} \cap S_{\text{sport}} \neq \emptyset$; $S_{\text{anim}} \cap S_{\text{doc}} \neq \emptyset$; $S_{\text{sc}} \cap S_{\text{tut}} \neq \emptyset$; $S_{\text{sfv}} \cap S_{\text{vlog}} \neq \emptyset$.
- The family is therefore a **hypergraph of overlapping sets**, admitting a partial order only on those pairs where containment has been established.

### Axes of Predicate Type

**The 20 predicates are not commensurable.** They operate at different levels of abstraction across orthogonal axes. A flat numbered list implies commensurability that the taxonomy explicitly denies:

| Axis | Predicates | Remark |
|------|-----------|--------|
| **Capture modality** ($\kappa$) | $S_{\text{surv}}$, $S_{\text{sc}}$, $S_{\text{anim}}$ | Constrain only $\kappa$; no constraint on $\pi$ or $\delta$ |
| **Truth claim / epistemic contract** | $S_{\text{doc}}$, $S_{\text{news}}$, $S_{\text{essay}}$, $S_{\text{int}}$ | Constrain $\mathfrak{m}$ and $\epsilon$ |
| **Temporal coupling** | $S_{\text{live}}$, $S_{\text{sport}}$ | Constrain $T_{\text{capture}} \approx T_{\text{broadcast}}$ |
| **Distribution format** | $S_{\text{sfv}}$, $S_{\text{vr}}$, $S_{\text{sc}}$ | Constrain $\chi$ or frame geometry |
| **Production intent** | $S_{\text{ad}}$, $S_{\text{tut}}$, $S_{\text{mg}}$, $S_{\text{mv}}$, $S_{\text{vlog}}$ | Constrain $\mathfrak{g}$ and/or $\mathfrak{m}$ |
| **Diegetic status** | $S_{\text{narr}}$, $S_{\text{mock}}$, $S_{\text{ff}}$, $S_{\text{exp}}$ | Constrain relationship between $\mathcal{W}$ and $\mathcal{W}_0$ |

Some predicates are **over-determined**: they satisfy conditions on multiple axes simultaneously (e.g. $S_{\text{sc}}$ constrains both $\kappa$ and $\chi$; $S_{\text{sfv}}$ constrains both frame geometry and $\chi$). This is not a deficiency — it reflects that these styles are constitutively multi-axis.

### Three Structural Observations

**First:** $S_{\text{anim}}$ is the only predicate that is **strictly a modality predicate** with no constraint on $\pi$ or $\delta$. This is why $S_{\text{anim}} \cap S_X \neq \emptyset$ for nearly all $X$ — animation composes freely with almost every other style.

**Second:** $S_{\text{surv}}$ is the formal limit at which **authorship collapses** ($\mathfrak{m} = \texttt{record\text{-}automated}$, so $\mathfrak{a}$ has no communicative role) and the audience contract is closed ($\epsilon = \texttt{restricted\text{-}access}$). It is the only predicate defined by the *absence* of properties that all others possess.

**Third:** $S_{\text{exp}}$ is a **relational predicate**: it is indexed to the historically dominant norms of $\delta$ at the time of production. A video satisfying $S_{\text{exp}}$ in 1925 may not satisfy it in 2025 if the same techniques have become conventional. This temporal dependency is a feature, not a defect — it accurately captures the meaning of "experimental."

---

## References

- Kripke, S. (1980). *Naming and Necessity*. Harvard University Press.
- Lewis, D. (1986). *On the Plurality of Worlds*. Blackwell.
- Rascaroli, L. (2009). *The Personal Camera: Subjective Cinema and the Essay Film*. Wallflower Press.
