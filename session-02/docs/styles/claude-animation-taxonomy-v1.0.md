---
title: "Animation Taxonomy — Formal Definitions"
version: "1.0.0"
status: draft
companion: "20-styles-video-v1.1.md, 20-styles-scene-v1.0.md, 20-styles-camera-v1.0.md"
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

# Animation Taxonomy — Formal Definitions

## 0. Foundational Apparatus

### 0.1 The Animation Artifact

An **animation artifact** $\mathcal{A}$ is an 8-tuple:

$$\mathcal{A} = (F_\mathcal{A},\; T_\mathcal{A},\; \mu_\mathcal{A},\; \mathbf{s},\; \iota,\; \chi_\mathcal{A},\; \beta_\mathcal{A},\; \delta_\mathcal{A})$$

| Symbol | Domain | Meaning |
|--------|--------|---------|
| $F_\mathcal{A}$ | $\mathbb{Z}_{\geq 0} \to \text{Image} \cup \{\bot\}$ | Ordered sequence of rendered frames; $\bot$ if non-frame output (spatial/interactive) |
| $T_\mathcal{A}$ | $\mathbb{R}_{\geq 0} \cup \{\infty\}$ | Temporal extent in seconds; $\infty$ for indefinitely looping or interactive works |
| $\mu_\mathcal{A}$ | $\mathcal{M}$ | Production method specification (§0.2) |
| $\mathbf{s}$ | $\mathcal{S}$ | Subject and application specification (§0.3) |
| $\iota$ | $\mathcal{I}$ | Visual style specification (§0.4) |
| $\chi_\mathcal{A}$ | $\mathcal{X}$ | Delivery channel and format specification (§0.5) |
| $\beta_\mathcal{A}$ | $\{\texttt{fixed},\; \texttt{interactive},\; \texttt{generative},\; \texttt{live-rendered}\}$ | Playback modality |
| $\delta_\mathcal{A}$ | $\mathcal{D}$ | Distribution context (audience contract, channel) |

$\mathcal{A}$ generalises the video tuple $V$ defined in the companion document. Every $V$ is an $\mathcal{A}$ with $F_\mathcal{A} \neq \bot$, $T_\mathcal{A} < \infty$, and $\beta_\mathcal{A} = \texttt{fixed}$. The converse does not hold: interactive experiences ($\beta_\mathcal{A} = \texttt{interactive}$), spatial installations ($\chi_\mathcal{A} \in \{\texttt{projection-mapped},\;\texttt{holographic}\}$), and real-time generative works ($\beta_\mathcal{A} \in \{\texttt{generative},\; \texttt{live-rendered}\}$) satisfy $\mathcal{A}$ but not $V$.

### 0.2 Production Method Specification $\mathcal{M}$

$$\mu_\mathcal{A} = (\mathfrak{g},\; \mathfrak{p},\; \mathfrak{t},\; \mathfrak{d})$$

| Component | Domain | Meaning |
|-----------|--------|---------|
| $\mathfrak{g}$ | $\mathcal{G}$ | Frame generation method (§0.2.1) |
| $\mathfrak{p}$ | $\mathcal{P}_\mathcal{A}$ | Physical substrate of production |
| $\mathfrak{t}$ | $\{\texttt{frame-by-frame},\; \texttt{rigged},\; \texttt{procedural},\; \texttt{real-time},\; \texttt{continuous-capture}\}$ | Temporal production mode |
| $\mathfrak{d}$ | $[0,1]$ | Automation degree: $0$ = fully manual; $1$ = fully algorithmic |

#### 0.2.1 Frame Generation Method $\mathcal{G}$

$$\mathcal{G} = \{\texttt{optical},\; \texttt{drawn-2d},\; \texttt{rendered-3d},\; \texttt{physical-manipulation},\; \texttt{direct-on-medium},\; \texttt{screen-capture},\; \texttt{hybrid}\}$$

- $\mathfrak{g} = \texttt{optical}$: frames produced by optical capture of a physical scene or physical animation medium (stop motion, pixilation, live-action compositing base)
- $\mathfrak{g} = \texttt{drawn-2d}$: frames produced by drawing or painting on a 2D surface, whether physical or digital
- $\mathfrak{g} = \texttt{rendered-3d}$: frames produced by algorithmic rendering of a 3D scene description; no optical capture
- $\mathfrak{g} = \texttt{physical-manipulation}$: frames produced by photographing physical objects (clay, puppets, cut-outs, objects) repositioned between exposures
- $\mathfrak{g} = \texttt{direct-on-medium}$: frames produced by drawing, scratching, burning, or otherwise modifying the recording medium directly — film stock, sand, glass — without an intermediate optical path
- $\mathfrak{g} = \texttt{screen-capture}$: frames produced by recording the pixel output of a computing device (see screencast, $S_{\text{sc}}$, in the companion video document)
- $\mathfrak{g} = \texttt{hybrid}$: $F_\mathcal{A}$ is produced by a combination of $\geq 2$ of the above methods

**Physical substrate $\mathcal{P}_\mathcal{A}$** is the material or computational medium in which the animation is authored:

$$\mathcal{P}_\mathcal{A} \in \{\texttt{paper},\; \texttt{cel},\; \texttt{film-stock},\; \texttt{digital-raster},\; \texttt{digital-vector},\; \texttt{3d-scene-graph},\; \texttt{physical-material},\; \texttt{game-engine},\; \texttt{shader/gpu}\}$$

### 0.3 Subject and Application Specification $\mathcal{S}$

$$\mathbf{s} = (\sigma_{\text{content}},\; \sigma_{\text{use}})$$

where $\sigma_{\text{content}} \in \Sigma_C$ is the **content domain** (what the animation depicts) and $\sigma_{\text{use}} \in \Sigma_U$ is the **use case** (the functional role for which $\mathcal{A}$ was produced). These are formally independent: the same content domain may serve different use cases.

### 0.4 Visual Style Specification $\mathcal{I}$

$$\iota = (\iota_{\text{render}},\; \iota_{\text{line}},\; \iota_{\text{color}},\; \iota_{\text{form}},\; \iota_{\text{ref}})$$

| Component | Domain | Meaning |
|-----------|--------|---------|
| $\iota_{\text{render}}$ | $\mathbb{R}_{[0,1]}$ | Realism index: $0$ = maximally abstract/symbolic; $1$ = photorealistic |
| $\iota_{\text{line}}$ | $\mathcal{L}_{\text{qual}}$ | Line quality descriptor (presence, weight, hardness, regularity) |
| $\iota_{\text{color}}$ | $\mathcal{C}_{\text{pal}}$ | Color palette regime (flat, graded, limited, photographic, monochrome) |
| $\iota_{\text{form}}$ | $\{\texttt{figurative},\; \texttt{caricatured},\; \texttt{abstract},\; \texttt{symbolic},\; \texttt{typographic}\}$ | Formal mode of representation |
| $\iota_{\text{ref}}$ | $\mathcal{R}_{\text{trad}}$ | Reference aesthetic tradition (e.g. UPA, Disney, anime, Bauhaus, pixel art) |

$\iota_{\text{ref}}$ is an open-ended reference to an aesthetic lineage; it is not enumerable in advance. Visual style predicates (§§D1–D10) are conditions on combinations of these components.

### 0.5 Delivery Format Specification $\mathcal{X}$

$$\chi_\mathcal{A} = (\chi_{\text{channel}},\; \chi_{\text{structure}},\; \chi_{\text{duration}},\; \chi_{\text{aspect}})$$

| Component | Domain | Meaning |
|-----------|--------|---------|
| $\chi_{\text{channel}}$ | $\mathcal{C}_{\text{ch}}$ | Distribution channel (broadcast, streaming, theatrical, social, web, installation, game engine, AR/VR device) |
| $\chi_{\text{structure}}$ | $\{\texttt{standalone},\; \texttt{episodic},\; \texttt{loop},\; \texttt{interactive},\; \texttt{spatial}\}$ | Structural organisation |
| $\chi_{\text{duration}}$ | $T_\mathcal{A}$ | Delivered temporal extent |
| $\chi_{\text{aspect}}$ | $\mathbb{Q}_{>0}$ | Delivered aspect ratio (width/height); $\chi_{\text{aspect}} < 1$ is portrait/vertical |

### 0.6 The Four-Axis Tag System

A **tag** $\tau$ is a pair $\tau = (\text{axis},\; \text{label})$ where axis $\in \{A, B, C, D\}$ and label is an element of the axis's predicate set. A **tag assignment** for $\mathcal{A}$ is a set $\mathcal{T}(\mathcal{A}) \subseteq \mathcal{T}_A \cup \mathcal{T}_B \cup \mathcal{T}_C \cup \mathcal{T}_D$ such that $\mathcal{T}(\mathcal{A}) \cap \mathcal{T}_X \neq \emptyset$ for at least three of the four axes — no production work is adequately described by a single axis alone.

**All definitions below are stipulative biconditionals.** $\mathcal{A}$ receives tag $\tau_X$ if and only if every stated condition for $\tau_X$ holds. Conditions are necessary and sufficient jointly.

**The axes are orthogonal:** conditions on $\mu_\mathcal{A}$ (Axis A) do not constrain $\iota$ (Axis D), and vice versa. A given work may receive any combination of tags from different axes. Axis A and Axis D are the most commonly confused — the production method and the visual style are independent dimensions. Rotoscope (A) can produce any visual style; pixel art (D) can be produced by multiple methods.

---

## Axis A — Production Method / Animation Medium

### A1. 2D Animation

$$\mathfrak{T}_{A1}(\mathcal{A}) = 1 \iff$$

- $\mathfrak{g} \in \{\texttt{drawn-2d},\; \texttt{hybrid}\}$: frames are produced in whole or in significant part by 2D image synthesis
- $\mathfrak{p} \in \{\texttt{paper},\; \texttt{cel},\; \texttt{digital-raster},\; \texttt{digital-vector}\}$: the authoring medium is a 2D surface
- No 3D scene graph is the primary spatial representation: $\mathfrak{p} \neq \texttt{3d-scene-graph}$ as the sole substrate

$\mathfrak{T}_{A1}$ is the axis-level predicate. The following are specialisations (sub-predicates satisfying $\mathfrak{T}_{A1}$ plus additional conditions):

#### A1.1 Traditional Hand-Drawn Animation

$$\mathfrak{T}_{A1.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A1}(\mathcal{A}) \wedge \mathfrak{p} \in \{\texttt{paper},\; \texttt{cel}\} \wedge \mathfrak{t} = \texttt{frame-by-frame} \wedge \mathfrak{d} \approx 0$$

Each frame is drawn manually on a physical surface by a human artist, without algorithmic assistance in frame generation. The industry canonical substrate is cel (cellulose acetate sheet) with paper for rough animation; both satisfy this predicate.

#### A1.2 Cel Animation

$$\mathfrak{T}_{A1.2}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A1.1}(\mathcal{A}) \wedge \mathfrak{p} = \texttt{cel}$$

A strict sub-predicate of $A1.1$ requiring the cel substrate specifically. The cel system separates character layers from backgrounds, enabling reuse of background art. This is primarily a historical production method — standard in studio animation from the 1910s through the 1980s; largely supplanted by digital methods from the 1990s onward. References: Barrier (2003, *Hollywood Cartoons*, Oxford University Press).

#### A1.3 Digital Frame-by-Frame Animation

$$\mathfrak{T}_{A1.3}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A1}(\mathcal{A}) \wedge \mathfrak{p} = \texttt{digital-raster} \wedge \mathfrak{t} = \texttt{frame-by-frame} \wedge \mathfrak{d} < 0.5$$

Each frame is drawn digitally by a human artist (Photoshop, Clip Studio, TVPaint, Procreate) without relying on automated in-betweening or rigging to generate intermediate frames. The digital raster substrate distinguishes this from $A1.1$.

#### A1.4 Vector Animation

$$\mathfrak{T}_{A1.4}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A1}(\mathcal{A}) \wedge \mathfrak{p} = \texttt{digital-vector}$$

Frames are defined as vector graphics — mathematical descriptions of curves and shapes — rather than pixel grids. The frame content is resolution-independent. Authoring tools include Adobe Animate, Inkscape, and SVG-based workflows. Vector animation may use frame-by-frame drawing, rigging, or procedural interpolation; $\mathfrak{t}$ is unconstrained beyond membership in $\mathfrak{T}_{A1}$.

#### A1.5 Rigged / Bone-Based 2D Animation

$$\mathfrak{T}_{A1.5}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A1}(\mathcal{A}) \wedge \mathfrak{t} = \texttt{rigged}$$

A hierarchical skeleton $\mathcal{R} = (J,\; E,\; \mathbf{b})$ is constructed, where $J$ is a set of joints, $E \subseteq J \times J$ is a directed parent-child edge set forming a tree, and $\mathbf{b} : J \to \mathbb{R}^3$ assigns a rest pose. Frames are generated by animating joint angles rather than redrawing shapes. The artwork (body parts, clothing, hair) is attached to joints; the rig deforms or repositions artwork as joints rotate. This is $\mathfrak{d} \in (0, 1)$: partially automated (the system interpolates joint states between keyframes) but manually authored (the artist sets keyframe poses).

#### A1.6 Cut-Out Animation

$$\mathfrak{T}_{A1.6}(\mathcal{A}) = 1 \iff$$
- $\mathfrak{T}_{A1}(\mathcal{A})$
- The subject is represented as a set of discrete, pre-drawn or pre-photographed **parts** $\{P_1, \ldots, P_n\}$ — head, torso, limbs, etc.
- Parts are repositioned, rotated, or scaled between frames rather than redrawn
- $\mathfrak{p} \in \{\texttt{paper},\; \texttt{digital-raster},\; \texttt{digital-vector}\}$

This predicate covers both physical cut-out animation (paper parts on a surface, as in Terry Gilliam's Monty Python sequences) and digital equivalents (repositioned PNGs or vectors in software). It is distinct from $A1.5$: cut-out animation repositions rigid parts; rigged animation deforms continuously interpolated mesh or skeleton.

#### A1.7 Rotoscope Animation

$$\mathfrak{T}_{A1.7}(\mathcal{A}) = 1 \iff$$
- $\mathfrak{T}_{A1}(\mathcal{A})$
- There exists a reference footage sequence $F_{\text{ref}}$ (live-action or other) such that frames of $F_\mathcal{A}$ are produced by tracing or algorithmically deriving drawn frames from $F_{\text{ref}}$ on a frame-by-frame basis
- The reference footage determines the motion and spatial relationships of the output frames

Rotoscoping is a **hybrid production method** in which live-action footage provides reference motion data, and drawn frames provide the visual output. The output $F_\mathcal{A}$ is $\mathfrak{g} = \texttt{drawn-2d}$; the process requires $F_{\text{ref}}$ as input. The technique was patented by Max Fleischer (US Patent 1,242,674, 1917).

#### A1.8 Silhouette Animation

$$\mathfrak{T}_{A1.8}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A1}(\mathcal{A}) \wedge \iota_{\text{color}}(\mathcal{A}) = \texttt{monochrome} \wedge \iota_{\text{render}}(\mathcal{A}) \approx 0.2$$

Figures are rendered as solid dark silhouettes against a lighter background; internal detail is suppressed. The constraint on $\iota$ crosses into Axis D — silhouette animation is one of the few production methods that formally entails a visual style constraint. The canonical practitioner is Lotte Reiniger (*The Adventures of Prince Achmed*, 1926).

#### A1.9 Loop Animation

$$\mathfrak{T}_{A1.9}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A1}(\mathcal{A}) \wedge F_\mathcal{A}(0) \approx F_\mathcal{A}(\lvert T_\mathcal{A}\rvert) \wedge \chi_{\text{structure}} = \texttt{loop}$$

The final frame of $F_\mathcal{A}$ is identical or perceptually continuous with the first frame such that repeated playback is seamless. The loop constraint is on the output, not the production method; it is a delivery-format constraint that may be satisfied by 2D animation of any sub-type.

---

### A2. 3D / CGI Animation

$$\mathfrak{T}_{A2}(\mathcal{A}) = 1 \iff \mathfrak{g} = \texttt{rendered-3d} \wedge \mathfrak{p} = \texttt{3d-scene-graph}$$

Frames are produced by rendering a three-dimensional scene description — geometry, materials, lighting, cameras — through a rendering pipeline (rasterisation or ray-tracing). No optical capture of physical scenes is required.

#### A2.1 Keyframed 3D Animation

$$\mathfrak{T}_{A2.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A2}(\mathcal{A}) \wedge \mathfrak{t} = \texttt{rigged} \wedge \mathfrak{d} \in (0, 0.8)$$

An animator manually sets keyframe values (position, rotation, scale, blend shapes) at discrete time points; the system interpolates between keyframes using spline curves. The motion is authored by a human animator working within a DCC (digital content creation) tool such as Maya, Blender, or Cinema 4D.

#### A2.2 Motion Capture Animation

$$\mathfrak{T}_{A2.2}(\mathcal{A}) = 1 \iff$$
- $\mathfrak{T}_{A2}(\mathcal{A})$
- The skeletal motion driving the 3D rig is derived from **marker data** $M = \{(\mathbf{m}_j(t),\; j \in J)\}$ recorded from a physical performer wearing optical, inertial, or magnetic tracking markers
- The mapping $M \to \text{rig}$ is the motion solve; human performance is the primary source of motion data

**Distinction from Performance Capture:** Motion capture ($A2.2$) records body skeletal data; performance capture additionally records facial performance data (expressions, micro-expressions) enabling full-body + facial driven digital character performance. Performance capture is a strict superset: $\mathfrak{T}_{A2.3} \Rightarrow \mathfrak{T}_{A2.2}$.

#### A2.3 Simulation-Based Animation

$$\mathfrak{T}_{A2.3}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A2}(\mathcal{A}) \wedge \mathfrak{d} > 0.8 \wedge \mathfrak{t} = \texttt{procedural}$$

Motion is generated by physical simulation rather than by manual keyframing or performance capture: fluid dynamics, rigid body, soft body, cloth, or crowd simulation systems governed by differential equations. The animator sets initial conditions and simulation parameters; the motion emerges from the simulation. No keyframe animation of individual entities is required.

#### A2.4 Procedural Animation

$$\mathfrak{T}_{A2.4}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A2}(\mathcal{A}) \wedge \mathfrak{t} = \texttt{procedural} \wedge \mathfrak{d} \geq 0.5$$

Motion is generated by algorithmic rules rather than by manual authorship. This includes noise-driven motion, IK (inverse kinematics) solvers, constraint-based systems, and rule-based crowd and agent systems. The boundary between $A2.3$ and $A2.4$ is that simulation is governed by physical laws; procedural animation may use arbitrary rules without physical accuracy.

#### A2.5 Real-Time / Game-Engine Animation

$$\mathfrak{T}_{A2.5}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A2}(\mathcal{A}) \wedge \mathfrak{p} = \texttt{game-engine} \wedge \beta_\mathcal{A} \in \{\texttt{live-rendered},\; \texttt{interactive}\}$$

Frames are rendered in real-time by a game engine (Unreal, Unity, Godot) at the moment of playback, not pre-rendered offline. The scene graph exists as runtime data in the engine; the output frame rate is determined by the rendering hardware at playback time, not the production pipeline.

**Formal consequence:** $F_\mathcal{A}$ is not fixed at production time for $\beta_\mathcal{A} = \texttt{live-rendered}$; it is a function of both the scene state and the viewer's runtime hardware. This breaks the definition $F_\mathcal{A} : \mathbb{Z}_{\geq 0} \to \text{Image}$ in the general tuple; more precisely, $F_\mathcal{A}$ is a stochastic function conditioned on render hardware $h$: $F_\mathcal{A}(i) = \text{Render}(i, h)$.

---

### A3. Stop Motion & Physical Animation

$$\mathfrak{T}_{A3}(\mathcal{A}) = 1 \iff \mathfrak{g} = \texttt{physical-manipulation} \wedge \mathfrak{t} = \texttt{frame-by-frame}$$

Frames are produced by photographing physical objects or materials that are repositioned between exposures. No continuous optical capture of motion: the motion is produced entirely by the discrete repositioning of physical matter between still exposures.

#### A3.1 Clay Animation / Claymation

$$\mathfrak{T}_{A3.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A3}(\mathcal{A}) \wedge \mathfrak{p} = \texttt{physical-material} \wedge \text{material}(\mathfrak{p}) = \texttt{clay or plasticine}$$

The animated subjects are made from clay or a clay-like mouldable material (plasticine, oil-based clay). The material is deformable and reshaped between frames. The term "Claymation" is a registered trademark of Laika (formerly Will Vinton Studios); the generic term is clay animation.[^claymation]

[^claymation]: "Claymation" is a trademark registered by Will Vinton Productions (now Laika). The generic term is "clay animation." Using "Claymation" as a generic label is technically inaccurate.

#### A3.2 Puppet Animation

$$\mathfrak{T}_{A3.2}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A3}(\mathcal{A}) \wedge \text{subject is a rigid or semi-rigid armature-based puppet with defined joints}$$

Subjects are three-dimensional puppets with internal armatures (wire, ball-and-socket) that allow controlled repositioning of limbs and body between frames. Distinct from clay animation by the rigidity of the form: puppet forms are not freely reshaped but positioned via their armature. Associated with studios including Laika (*Coraline*, 2009; *Kubo and the Two Strings*, 2016) and Aardman Animations.

#### A3.3 Pixilation

$$\mathfrak{T}_{A3.3}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A3}(\mathcal{A}) \wedge \text{primary animated subject is a living human being}$$

Live human actors are treated as stop-motion subjects: they pose, remain still, the camera captures one frame, and the actor repositions. The result produces impossible or surreal motion for live human figures. The technique is attributed to Norman McLaren (*Neighbours*, 1952, National Film Board of Canada).

#### A3.4 Animatronics

$$\mathfrak{T}_{A3.4}(\mathcal{A}) = 1 \iff$$
- $\mathfrak{g} = \texttt{optical}$: frames are produced by live-action optical capture
- The animated subject is a **self-actuating mechanical puppet** driven by servomechanisms, hydraulics, pneumatics, or cable mechanisms
- Motion is continuous (not frame-by-frame in the stop-motion sense); the mechanism produces the motion during the camera exposure
- $\beta_\mathcal{A} = \texttt{fixed}$ or $\beta_\mathcal{A} = \texttt{interactive}$

**Note on classification:** Animatronics is strictly not stop motion ($\mathfrak{T}_{A3}$ requires $\mathfrak{t} = \texttt{frame-by-frame}$; animatronics operates continuously). It is placed in the A3 group by thematic proximity (physical, practical effects) but is formally distinct: $\mathfrak{T}_{A3.4} \not\Rightarrow \mathfrak{T}_{A3}$.

**Sub-types** (Disney-specific trademarked variants; cited as proper names, not generic terms):
- **Audio-Animatronics**: Walt Disney Company's term for animatronic figures synchronised to pre-recorded audio tracks. Trademark of The Walt Disney Company; the generic term is "audio-synchronised animatronics."[^audio-animatronics]
- **Autonomatronics**: Disney's term for figures incorporating sensor-based reactive behaviour. Trademark of The Walt Disney Company.[^autonomatronics]

[^audio-animatronics]: "Audio-Animatronics" is a registered trademark of The Walt Disney Company. First deployed at the 1964 World's Fair (Ford Pavilion). It is not a generic industry term.
[^autonomatronics]: "Autonomatronics" is a registered trademark of The Walt Disney Company. It refers to animatronic figures with real-time reactive sensor systems. It is not a generic industry term.

#### A3.5 Chuckimation

$$\mathfrak{T}_{A3.5}(\mathcal{A}) = 1 \iff$$
- $\mathfrak{g} = \texttt{optical}$: live-action capture
- Objects or figures are moved by being physically thrown, dropped, or pushed by a human hand into the frame rather than repositioned between frames or mechanically actuated
- Motion within a frame is produced by the physical trajectory of the thrown object, not by frame-by-frame repositioning

**Provenance note:** The term originates with the web series *Action League Now!* (Nickelodeon, 1994–1997), produced by Benderspink. It is an extremely narrow technique designation and is not a standard industry term.[^chuckimation] It is formalised here for completeness.

[^chuckimation]: "Chuckimation" is credited to the creators of *Action League Now!* It does not appear in major animation studies references (e.g., Furniss, 2008, *A New History of Animation*, Thames & Hudson). Its inclusion in the source taxonomy is unusual; it is formalised here as a stipulative definition.

---

### A4. Motion Design & Graphic Animation

$$\mathfrak{T}_{A4}(\mathcal{A}) = 1 \iff$$
- $\mathfrak{g} \in \{\texttt{drawn-2d},\; \texttt{rendered-3d},\; \texttt{hybrid}\}$
- $\iota_{\text{form}} \in \{\texttt{abstract},\; \texttt{symbolic},\; \texttt{typographic}\}$ or the primary content of $F_\mathcal{A}$ is graphic design elements (typography, icons, shapes, data) rather than characters or environments
- $\sigma_{\text{use}} \in \{\texttt{broadcast},\; \texttt{branding},\; \texttt{communication},\; \texttt{informational}\}$

Motion design is formally distinguished from character animation by $\iota_{\text{form}}$: the primary content is graphic rather than figurative. It is distinguished from experimental animation by $\sigma_{\text{use}}$: motion design serves communicative or commercial functions.

#### A4.1 Motion Graphics

$$\mathfrak{T}_{A4.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A4}(\mathcal{A}) \wedge \iota_{\text{form}} \in \{\texttt{abstract},\; \texttt{symbolic}\}$$

The general class of motion design in which graphic elements (shapes, icons, abstract forms) are animated. No constraint on $\mathfrak{g}$: motion graphics may be produced in 2D or 3D or hybrid methods.

#### A4.2 Kinetic Typography

$$\mathfrak{T}_{A4.2}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A4}(\mathcal{A}) \wedge \iota_{\text{form}} = \texttt{typographic} \wedge \text{primary content of } F_\mathcal{A} \text{ is animated text}$$

Text is the primary animated element; motion is used to convey rhythm, emphasis, tone, or meaning through the kinetic behaviour of letterforms. Distinct from a static title card by the requirement that the motion of the text is itself communicative.

---

### A5. Experimental / Direct / Optical Animation

$$\mathfrak{T}_{A5}(\mathcal{A}) = 1 \iff \mathfrak{g} = \texttt{direct-on-medium}$$

**or**

$$\mathfrak{T}_{A5}(\mathcal{A}) = 1 \iff \pi_\mathcal{A} \text{ refuses or interrogates at least one normative constraint of mainstream animation production}$$

The second clause mirrors $\mathfrak{S}_{\text{exp}}$ from the scene document: experimental animation is relationally defined as indexed to normative production conventions. $\mathfrak{g} = \texttt{direct-on-medium}$ is the formal criterion for the direct sub-class; the experimental sub-class is the relational criterion.

**Note on the disjunction:** The two clauses are not jointly required. Direct-on-medium work (sand animation, drawn-on-film) is experimental by method; works using conventional methods (frame-by-frame 2D, rendered 3D) may satisfy the experimental predicate by intent without satisfying $\mathfrak{g} = \texttt{direct-on-medium}$.

#### A5.1 Sand Animation

$$\mathfrak{T}_{A5.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A5}(\mathcal{A}) \wedge \mathfrak{p} = \texttt{physical-material} \wedge \text{material}(\mathfrak{p}) = \texttt{sand or fine powder} \wedge \mathfrak{g} \in \{\texttt{direct-on-medium},\; \texttt{optical}\}$$

Sand or fine powder is spread on a light table or surface and shaped by hand between frame captures. The artist directly manipulates the medium; the camera records the result. Frames may be captured on film or digitally.

#### A5.2 Drawn-on-Film / Scratch-on-Film Animation

$$\mathfrak{T}_{A5.2}(\mathcal{A}) = 1 \iff \mathfrak{g} = \texttt{direct-on-medium} \wedge \mathfrak{p} = \texttt{film-stock}$$

Images are created by drawing on, scratching into, or otherwise physically modifying the emulsion surface of motion picture film stock. The film stock is both the production medium and the exhibition medium. Associated with Norman McLaren (*Begone Dull Care*, 1949, NFB) and Len Lye (*Free Radicals*, 1958).

#### A5.3 Optical Device Animations (Zoetrope, Praxinoscope, Phenakistoscope)

$$\mathfrak{T}_{A5.3}(\mathcal{A}) = 1 \iff$$
- The animation is designed to be viewed through a **pre-cinematic optical device** that produces the illusion of motion through stroboscopic or persistence-of-vision principles
- The device is one of: zoetrope (slotted rotating drum), praxinoscope (mirrored rotating drum), phenakistoscope (slotted rotating disc), or an equivalent pre-cinematic mechanism
- $T_\mathcal{A}$ is short and the sequence is inherently looping ($\chi_{\text{structure}} = \texttt{loop}$)

**Historical note:** These devices predate cinema; they exploit the persistence of vision (more accurately, the phi phenomenon and beta movement — the neurological mechanisms are discussed in Wertheimer, 1912, "Experimentelle Studien über das Sehen von Bewegung"). Their inclusion in a contemporary taxonomy is as historical antecedents and contemporary art/installation practices.

---

### A6. Immersive & Interactive Animation

$$\mathfrak{T}_{A6}(\mathcal{A}) = 1 \iff \beta_\mathcal{A} \in \{\texttt{interactive},\; \texttt{live-rendered}\} \vee \chi_{\text{channel}} \in \{\texttt{ar-device},\; \texttt{vr-device},\; \texttt{installation},\; \texttt{projection-mapped}\}$$

The defining property is a **non-passive viewer relationship**: either the viewer's behaviour affects the output ($\beta_\mathcal{A} = \texttt{interactive}$), or the frame is rendered in real time ($\beta_\mathcal{A} = \texttt{live-rendered}$), or the delivery context requires a spatial or immersive medium.

#### A6.1 360° Animation

$$\mathfrak{T}_{A6.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A6}(\mathcal{A}) \wedge F_\mathcal{A}(t) \text{ encodes omnidirectional imagery (equirectangular or cubemap)} \wedge \chi_{\text{channel}} \in \{\texttt{vr-device},\; \texttt{360-player}\}$$

The output image covers approximately the full sphere of view. The viewer's rendered viewport is a function of head orientation at playback time: $F_{\text{viewed}}(t) = F_\mathcal{A}(t)\big|_{\theta(t),\phi(t)}$. This extends $\mathfrak{C}_{\text{vr}}$ from the camera document to the animation production domain.

#### A6.2 Projection Mapping Animation

$$\mathfrak{T}_{A6.2}(\mathcal{A}) = 1 \iff \mathfrak{T}_{A6}(\mathcal{A}) \wedge \chi_{\text{channel}} = \texttt{projection-mapped}$$

$F_\mathcal{A}$ is designed to be projected onto a non-planar physical surface $\mathcal{S} \subset \mathbb{R}^3$ such that the projected image appears spatially coherent on $\mathcal{S}$. The production requires a 3D model $\hat{\mathcal{S}}$ of the target surface; $F_\mathcal{A}$ is pre-warped such that $\text{Project}(F_\mathcal{A}, \mathcal{S}) \approx \text{undistorted image}$ when projected from the specified projector position.

---

### A7. Hybrid / Composited Animation

$$\mathfrak{T}_{A7}(\mathcal{A}) = 1 \iff \mathfrak{g} = \texttt{hybrid} \wedge \lvert\{\text{distinct generation methods in } F_\mathcal{A}\}\rvert \geq 2$$

No single frame generation method accounts for 100% of $F_\mathcal{A}$; at least two methods contribute to the final output. The specific combination determines the sub-predicate:

| Sub-predicate | Combination |
|--------------|-------------|
| $\mathfrak{T}_{A7.1}$ (2D+3D Hybrid) | $\mathfrak{g}$ combines $\texttt{drawn-2d}$ and $\texttt{rendered-3d}$ |
| $\mathfrak{T}_{A7.2}$ (Live-Action + Animation) | $\mathfrak{g}$ combines $\texttt{optical}$ with any synthetic method |
| $\mathfrak{T}_{A7.3}$ (Stop Motion + CG) | $\mathfrak{g}$ combines $\texttt{physical-manipulation}$ and $\texttt{rendered-3d}$ |

---

## Axis B — Subject / Application

$$\mathfrak{T}_{B}(\mathcal{A}) = (\sigma_{\text{content}},\; \sigma_{\text{use}})$$

Axis B predicates are conditions on the **semantic content** and **functional use** of $\mathcal{A}$. They are independent of Axis A (how it is made) and Axis D (what it looks like).

### B1. Character & Performance

$$\mathfrak{T}_{B1}(\mathcal{A}) = 1 \iff \sigma_{\text{content}} \supset \{\text{diegetic agents with goal-directed behaviour}\} \wedge \sigma_{\text{use}} \in \{\texttt{narrative},\; \texttt{entertainment},\; \texttt{game}\}$$

The primary content is the performance of animated characters — human, creature, or anthropomorphised objects — whose physical and expressive behaviour is the subject. The following are specialisations requiring no additional formal apparatus:

- **Character Animation** ($B1.1$): general; no constraint beyond $B1$.
- **Facial Animation** ($B1.2$): the primary content is facial expression and lip movement. $\iota_{\text{render}}$ is typically high.
- **Lip-Sync Animation** ($B1.3$): strict sub-predicate of $B1.2$; facial animation is driven by a specific audio phoneme sequence.
- **Creature Animation** ($B1.4$): subjects are non-human creatures (real or fantastical); no constraint on $\iota$.

### B2. Technical & Industrial

$$\mathfrak{T}_{B2}(\mathcal{A}) = 1 \iff \sigma_{\text{content}} \supset \{\text{physical objects, mechanisms, or processes existing or designed in }\mathcal{W}_0\} \wedge \sigma_{\text{use}} \in \{\texttt{engineering},\; \texttt{manufacturing},\; \texttt{product-communication},\; \texttt{training}\}$$

The animation depicts real-world objects, mechanical systems, or industrial processes for technical communication rather than entertainment. No constraint on Axis A or D.

### B3. Built Environment

$$\mathfrak{T}_{B3}(\mathcal{A}) = 1 \iff \sigma_{\text{content}} \supset \{\text{architectural spaces, urban forms, or landscapes}\} \wedge \sigma_{\text{use}} \in \{\texttt{architectural-visualisation},\; \texttt{urban-planning},\; \texttt{real-estate}\}$$

Typically high $\iota_{\text{render}}$ (photorealistic or near-photorealistic); typically $\mathfrak{g} = \texttt{rendered-3d}$. Neither condition is formally required, but both are strong empirical regularities.

### B4. Scientific & Informational

$$\mathfrak{T}_{B4}(\mathcal{A}) = 1 \iff \sigma_{\text{use}} \in \{\texttt{scientific},\; \texttt{medical},\; \texttt{educational},\; \texttt{legal-forensic},\; \texttt{data-visualisation}\} \wedge \mathfrak{m} = \texttt{assert}$$

The epistemic contract (borrowing $\mathfrak{m}$ from the companion video document) is $\texttt{assert}$: the animation makes truth claims about $\mathcal{W}_0$. This constrains the content to depict real phenomena as accurately as the production allows.

**Critical property:** $\mathfrak{T}_{B4}$ introduces an epistemic obligation absent from all other B-axis predicates. A medical animation asserting anatomical structure makes a factual claim; errors are not merely aesthetic failures but epistemic failures. This connects Axis B to the companion video document's apparatus: $\mathfrak{m} = \texttt{assert}$ is a condition inherited from $\pi_V$.

### B5. Media & Commercial Use

$$\mathfrak{T}_{B5}(\mathcal{A}) = 1 \iff \sigma_{\text{use}} \in \{\texttt{advertising},\; \texttt{broadcast},\; \texttt{film-tv},\; \texttt{social-media},\; \texttt{game},\; \texttt{music}\}$$

The animation is produced for commercial media distribution with a defined audience and monetisation model.

---

## Axis C — Delivery Format / Output Type

Axis C predicates are conditions on $\chi_\mathcal{A}$ and structural properties of $\mathcal{A}$. They are independent of Axes A, B, and D.

### C1. Narrative Formats

$$\mathfrak{T}_{C1}(\mathcal{A}) = 1 \iff \chi_{\text{structure}} \in \{\texttt{standalone},\; \texttt{episodic}\} \wedge \text{primary content is a diegetic storyworld } \mathcal{W}$$

The work presents a narrative — a causally structured sequence of events in a storyworld. Sub-predicates:

| Sub-predicate | Condition |
|--------------|-----------|
| Short Film | $T_\mathcal{A} \leq 40\,\text{min}$[^short-film] |
| Feature Film | $T_\mathcal{A} > 40\,\text{min}$ |
| Series / Episodic | $\chi_{\text{structure}} = \texttt{episodic}$; multiple episodes sharing a storyworld |
| Pilot | Single episode produced as proof-of-concept for a series; may not be broadcast |

[^short-film]: The Academy of Motion Picture Arts and Sciences defines a short film as $\leq 40$ minutes (Rule Fifteen, AMPAS). This is the most widely cited threshold but is not universal; the BFI and BAFTA use different criteria.

### C2. Commercial Formats

$$\mathfrak{T}_{C2}(\mathcal{A}) = 1 \iff \chi_{\text{channel}} \in \{\texttt{broadcast},\; \texttt{digital-paid},\; \texttt{social-paid}\} \wedge \sigma_{\text{use}} \in \{\texttt{advertising},\; \texttt{branding},\; \texttt{product-communication}\}$$

The work is produced for paid distribution to promote a product, service, brand, or organisation. Mirrors the video-document $S_{\text{ad}}$ predicate at the animation-production level.

### C3. Broadcast & Entertainment Formats

$$\mathfrak{T}_{C3}(\mathcal{A}) = 1 \iff \chi_{\text{channel}} = \texttt{broadcast} \vee \chi_{\text{channel}} \in \{\texttt{streaming},\; \texttt{theatrical}\}$$

Short-form broadcast components (title sequences, bumpers, idents) are all $C3$ with $\chi_{\text{structure}} = \texttt{standalone}$ and short $T_\mathcal{A}$. Duration notes are relegated to footnotes: no duration is placed in formal conditions.

### C4. Social & Short-Form Formats

$$\mathfrak{T}_{C4}(\mathcal{A}) = 1 \iff \chi_{\text{channel}} \in \{\texttt{social-feed},\; \texttt{messaging}\} \wedge \chi_{\text{aspect}} \leq 1$$

The work is produced for social media distribution, typically in portrait orientation. Duration norms are platform-specific and temporally unstable (see companion video document §12 footnote); they are not formal conditions.

### C5. Interactive & Spatial Formats

$$\mathfrak{T}_{C5}(\mathcal{A}) = 1 \iff \beta_\mathcal{A} \in \{\texttt{interactive},\; \texttt{live-rendered}\} \vee \chi_{\text{channel}} \in \{\texttt{ar-device},\; \texttt{vr-device},\; \texttt{installation},\; \texttt{projection-mapped}\}$$

Formally identical to $\mathfrak{T}_{A6}$ at the axis level; $C5$ is the delivery-format predicate and $A6$ is the production-method predicate. A work may satisfy one without the other (a game-engine cinematic pre-rendered to video satisfies $A2.5$ but may not satisfy $C5$; a pre-rendered 360° experience satisfies $C5$ but may not satisfy $A6$ if no real-time rendering is involved).

---

## Axis D — Visual Style

Visual style predicates are conditions on $\iota = (\iota_{\text{render}},\; \iota_{\text{line}},\; \iota_{\text{color}},\; \iota_{\text{form}},\; \iota_{\text{ref}})$. They are fully independent of Axes A, B, and C.

**Critical property of Axis D:** Visual style and production method are orthogonal. Any style may in principle be produced by multiple methods; any method may produce multiple styles. This is the most commonly violated assumption in practice — "pixel art" is treated as both a style (D) and a production method (A) in informal usage. The formal system keeps them separate.

### D1. Realism Spectrum

The realism spectrum is a one-dimensional continuum indexed by $\iota_{\text{render}} \in [0,1]$. Predicates on this axis are thresholded conditions:

| Predicate | Condition | Notes |
|-----------|-----------|-------|
| Photorealistic | $\iota_{\text{render}} \geq 0.95$ | Output is visually indistinguishable from photography under casual inspection |
| Realistic | $0.80 \leq \iota_{\text{render}} < 0.95$ | High fidelity; identifiable stylisation present but subdued |
| Stylized Realism | $0.60 \leq \iota_{\text{render}} < 0.80$ | Real-world proportions and lighting, but visible stylistic departure |
| Semi-Realistic | $0.40 \leq \iota_{\text{render}} < 0.60$ | Equal presence of realistic and stylised elements |
| Realistic Cartoon | $0.20 \leq \iota_{\text{render}} < 0.40$ | Cartoon form, but with proportional or lighting cues from realism |
| Caricatured | $\iota_{\text{render}} < 0.20$ | Extreme exaggeration of form relative to any real-world referent |

**Note:** The $\iota_{\text{render}}$ thresholds above are stipulative. No empirical or perceptual science defines these exact values; they are operational boundaries for this taxonomy. Any measurement of $\iota_{\text{render}}$ would require a well-defined perceptual experiment.

### D2. Cartoon & Comic Styles

$$\mathfrak{T}_{D2}(\mathcal{A}) = 1 \iff \iota_{\text{form}} = \texttt{figurative} \wedge \iota_{\text{ref}} \in \mathcal{R}_{\text{western-cartoon}} \wedge \iota_{\text{render}} \in [0.05, 0.50]$$

The subject is represented in figurative form drawing on the visual conventions of Western commercial cartooning — simplified or exaggerated forms, closed outlines, limited colour palettes, expressive deformation.

#### D2.1 Rubber Hose Style

$$\mathfrak{T}_{D2.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{D2}(\mathcal{A}) \wedge \iota_{\text{ref}} = \texttt{early-american-cartoon-1920s-30s}$$

Limbs are represented as uniform-width cylinders without joints or anatomical structure; forms are boneless and bend freely in any direction. Associated with the Fleischer Studios, early Disney shorts, and the broader American cartoon production of the 1920s–1930s. Named by contemporary practitioners; the term is retrospective, not a contemporary production label.

#### D2.2 Classic Western Cartoon / Modern TV Cartoon

These predicates are conditions on $\iota_{\text{ref}}$: the reference tradition is the American studio cartoon of the classical Hollywood era ($\iota_{\text{ref}} = \texttt{golden-age-american}$) or contemporary television animation ($\iota_{\text{ref}} \in \mathcal{R}_{\text{contemporary-tv}}$) respectively. Formal conditions on $\iota_{\text{render}}$, $\iota_{\text{line}}$, and $\iota_{\text{form}}$ follow the parent $\mathfrak{T}_{D2}$ predicate.

### D3. Anime & Manga Styles

$$\mathfrak{T}_{D3}(\mathcal{A}) = 1 \iff \iota_{\text{ref}} \in \mathcal{R}_{\text{japanese-animation}}$$

The reference tradition is Japanese animation or manga graphic style. The specific conventions vary across sub-predicates:

#### D3.1 Classic Manga / Retro Anime

$$\mathfrak{T}_{D3.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{D3}(\mathcal{A}) \wedge \iota_{\text{ref}} \in \{\texttt{showa-era-manga},\; \texttt{1960s-80s-anime}\}$$

Visual conventions of pre-1990 Japanese animation and manga: limited colour palette, heavy ink outlines, flat fills, characteristic eye designs from the Tezuka tradition. References: Natsume (1997, *Tezuka wa Shindeiru*, Shogakukan).

#### D3.2 Chibi

$$\mathfrak{T}_{D3.2}(\mathcal{A}) = 1 \iff \mathfrak{T}_{D3}(\mathcal{A}) \wedge \iota_{\text{form}} = \texttt{figurative} \wedge \text{head-to-body ratio} \gg 1$$

Characters are rendered with heads disproportionately large relative to body height (head-to-body ratio $\geq 1:2$, compared to realistic $\approx 1:7.5$). Features are simplified; the form is strongly caricatured ($\iota_{\text{render}} \approx 0.10$).

### D4. Minimal & Graphic Styles

$$\mathfrak{T}_{D4}(\mathcal{A}) = 1 \iff \iota_{\text{form}} \in \{\texttt{abstract},\; \texttt{symbolic},\; \texttt{typographic}\} \wedge \iota_{\text{color}} \in \{\texttt{flat},\; \texttt{limited},\; \texttt{monochrome}\}$$

The visual language is reduced to essential graphic elements; detail is suppressed in favour of clarity or formal elegance. Sub-predicates include:

| Sub-predicate | Additional condition |
|--------------|---------------------|
| Minimalist Style | $\lvert\text{distinct visual elements per frame}\rvert \ll$ domain mean |
| Flat Vector Style | $\iota_{\text{render}} \approx 0$; no gradients; fills are uniform |
| Geometric Style | $\iota_{\text{form}} = \texttt{abstract}$; forms are regular polygons, circles, or composed thereof |
| Isometric Style | Spatial grammar is isometric projection; no perspective convergence |
| Line Art Style | $\iota_{\text{color}} = \texttt{monochrome}$; form is conveyed exclusively by line, not fill |

### D5. Painterly & Handmade Styles

$$\mathfrak{T}_{D5}(\mathcal{A}) = 1 \iff \iota_{\text{line}}(\mathcal{A}) \text{ is irregular, variable in weight, and non-mechanical} \wedge \iota_{\text{ref}} \in \mathcal{R}_{\text{fine-art-media}}$$

The visual style references fine-art media — watercolour, gouache, oil paint, ink wash, graphite — in line quality, colour behaviour, or both. No constraint on Axis A: a painterly style may be produced digitally, by hand, or through simulation.

### D6. CG Render Styles

$$\mathfrak{T}_{D6}(\mathcal{A}) = 1 \iff \iota_{\text{ref}} \in \mathcal{R}_{\text{cg-non-photoreal}} \wedge \mathfrak{g} \neq \texttt{drawn-2d}$$

Styles that exploit the conventions of CG rendering while avoiding photorealism. All sub-predicates require $\mathfrak{g} \in \{\texttt{rendered-3d},\; \texttt{hybrid}\}$.

| Sub-predicate | Formal condition |
|--------------|-----------------|
| Cel-Shaded | Diffuse shading is quantised to $n$ discrete tonal steps ($n \leq 4$ typically) |
| Toon-Shaded | Cel-shading plus explicit outline rendering via normal discontinuity detection |
| Low-Poly | Polygon count $\ll$ photorealistic norm; polygonal faces are visibly discrete |
| Voxel Style | 3D content represented as discrete cubic volume elements |
| NPR (Non-Photoreal Rendering) | General class: any 3D rendering intentionally departing from photorealism |

### D7. Dark, Gothic & Surreal Styles

$$\mathfrak{T}_{D7}(\mathcal{A}) = 1 \iff \iota_{\text{ref}} \in \mathcal{R}_{\text{gothic-surreal}} \wedge \iota_{\text{color}} \in \{\texttt{desaturated},\; \texttt{high-contrast},\; \texttt{monochrome}\}$$

Sub-predicates:

#### D7.1 Gothic Whimsical / Burtonesque-Inspired Style

$$\mathfrak{T}_{D7.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{D7}(\mathcal{A}) \wedge \iota_{\text{ref}} \in \{\texttt{german-expressionism},\; \texttt{edward-gorey},\; \texttt{gothic-illustration}\} \wedge \iota_{\text{form}} = \texttt{figurative}$$

Tall, elongated, exaggerated forms with angular construction; desaturated or monochromatic palette with high contrast; gothic or macabre motifs combined with a childlike or whimsical narrative register.

**Naming note:** The source taxonomy used the label "Tim Burton's Style," which was renamed here to "Gothic Whimsical / Burtonesque-Inspired." The formal predicate is not defined by reference to a single living director's personal style; it is defined by the aesthetic tradition ($\iota_{\text{ref}}$) that Burton's work draws on, which predates his output and extends to other practitioners (Henry Selick, Guillermo del Toro). Naming a style after a single living practitioner is a categorical error that confuses the container with an instance.

### D8. Futuristic & Tech Styles

$$\mathfrak{T}_{D8}(\mathcal{A}) = 1 \iff \iota_{\text{ref}} \in \mathcal{R}_{\text{futurist-tech}} \wedge \iota_{\text{color}} \in \{\texttt{neon},\; \texttt{high-saturation},\; \texttt{dark-background}\}$$

Sub-predicates:

| Sub-predicate | Additional condition |
|--------------|---------------------|
| HUD / FUI Sci-Fi | $\iota_{\text{form}} \in \{\texttt{symbolic},\; \texttt{typographic}\}$; imagery imitates heads-up display or fictional user interface conventions |
| Cyberpunk / Neon | Palette dominated by saturated neons on dark fields; urban dystopian motifs |
| Glitch Style | $F_\mathcal{A}$ contains deliberate simulated digital artefacts (pixel displacement, colour channel separation, data moshing) as constitutive aesthetic elements |
| Plexus / Network | Forms are particle networks with connecting edges; typically $\mathfrak{g} = \texttt{rendered-3d}$ |

### D9. Retro & Nostalgic Styles

$$\mathfrak{T}_{D9}(\mathcal{A}) = 1 \iff \iota_{\text{ref}} \in \mathcal{R}_{\text{historical-media}} \wedge \iota_{\text{render}}(\mathcal{A}) < 0.40$$

The visual language deliberately references a prior media-historical moment through characteristic visual conventions of that moment's production technology.

#### D9.1 Pixel Art Style

$$\mathfrak{T}_{D9.1}(\mathcal{A}) = 1 \iff \mathfrak{T}_{D9}(\mathcal{A}) \wedge \iota_{\text{ref}} = \texttt{early-raster-game-graphics} \wedge$$
$$\text{each frame } F_\mathcal{A}(i) \text{ is composed of a discrete pixel grid at low effective resolution, with each pixel individually distinguishable at normal viewing size}$$

**Critical methodological note:** Pixel art is classified under Axis D (visual style), not Axis A (production method). A work may simulate pixel art style using high-resolution raster tools (Aseprite, Photoshop), or even vector tools, or 3D rendering at low resolution. The style condition is on the output frame $F_\mathcal{A}(i)$; the production method is unconstrained. This is the clearest example of Axis A/D orthogonality in the taxonomy.

### D10. Cute / Decorative Styles

$$\mathfrak{T}_{D10}(\mathcal{A}) = 1 \iff \iota_{\text{ref}} \in \mathcal{R}_{\text{cute-decorative}} \wedge \iota_{\text{render}} < 0.30 \wedge \iota_{\text{color}} \in \{\texttt{pastel},\; \texttt{high-saturation-warm}\}$$

Sub-predicates:

| Sub-predicate | Additional condition |
|--------------|---------------------|
| Kawaii Style | $\iota_{\text{ref}} = \texttt{japanese-kawaii}$; forms are rounded, features are large-eyed and soft |
| Super-Deformed | $\mathfrak{T}_{D3.2}(\mathcal{A})$ with $\iota_{\text{color}} \in \mathcal{R}_{\text{cute-decorative}}$; intersection of chibi and cute/decorative |
| Pastel Cute | $\iota_{\text{color}} = \texttt{pastel}$; palette is exclusively desaturated warm pastels |

---

## Summary: Taxonomy Structure

### Four-Axis Formal Structure

The taxonomy is a **4-axis tag system** $(\mathcal{T}_A, \mathcal{T}_B, \mathcal{T}_C, \mathcal{T}_D)$ where each axis is a set of predicates on $\mathcal{A}$:

| Axis | Predicates on | Primary formal constraint | Axes it depends on |
|------|--------------|--------------------------|-------------------|
| A — Production Method | $\mu_\mathcal{A} = (\mathfrak{g}, \mathfrak{p}, \mathfrak{t}, \mathfrak{d})$ | Frame generation and physical substrate | None |
| B — Subject / Application | $\mathbf{s} = (\sigma_{\text{content}}, \sigma_{\text{use}})$ | What is depicted and for what purpose | None |
| C — Delivery Format | $\chi_\mathcal{A}$, $\beta_\mathcal{A}$ | Channel, structure, duration, aspect ratio | None |
| D — Visual Style | $\iota = (\iota_{\text{render}}, \iota_{\text{line}}, \iota_{\text{color}}, \iota_{\text{form}}, \iota_{\text{ref}})$ | Output frame aesthetics | None |

All four axes are mutually independent by construction. A tag from one axis does not constrain the others **unless explicitly stated** in a biconditional condition.

### Proved Exceptions to Orthogonality

Two predicates in this taxonomy formally cross axes:

1. **$\mathfrak{T}_{A1.8}$ (Silhouette Animation)** crosses A into D: it requires $\iota_{\text{color}} = \texttt{monochrome}$, a visual style condition. This is the only production-method predicate that formally entails a style constraint.

2. **$\mathfrak{T}_{B4}$ (Scientific / Informational)** crosses B into the epistemic apparatus of Axes B and the companion video document: it requires $\mathfrak{m} = \texttt{assert}$, inheriting the possible-worlds apparatus. This is the only subject predicate that imports an epistemic commitment.

All other axis-crossings stated in informal taxonomies are resolved here as follows: "pixel art" is Axis D only; "rotoscope" is Axis A only; "explainer video" appears in both A ($A4$) and C ($C2$) but is defined independently on each axis with different formal conditions.

### Proved Disjunctions

Within Axis A:
$$\mathfrak{T}_{A3}(\text{stop motion}) \cap \mathfrak{T}_{A3.4}(\text{animatronics}) = \emptyset$$

because $\mathfrak{T}_{A3}$ requires $\mathfrak{t} = \texttt{frame-by-frame}$ and animatronics requires $\mathfrak{g} = \texttt{optical}$ with continuous motion.

Within Axis D:
$$\mathfrak{T}_{D1}(\text{photorealistic}) \cap \mathfrak{T}_{D2}(\text{cartoon}) = \emptyset$$

because $D1$ requires $\iota_{\text{render}} \geq 0.95$ and $D2$ requires $\iota_{\text{render}} \leq 0.50$; the ranges do not overlap.

### Notable Proved Non-Empty Intersections

| Pair | Basis |
|------|-------|
| $\mathfrak{T}_{A1.7} \cap \mathfrak{T}_{D5}$ | Rotoscoped painterly animation (*Waking Life*, Linklater, 2001) |
| $\mathfrak{T}_{A2.5} \cap \mathfrak{T}_{D6}$ | Real-time cel-shaded game cinematics |
| $\mathfrak{T}_{A3.1} \cap \mathfrak{T}_{D5}$ | Clay animation with painterly surface texture (*Harvie Krumpet*, 2003) |
| $\mathfrak{T}_{A6.1} \cap \mathfrak{T}_{D1}$ | Photorealistic 360° environment animation |
| $\mathfrak{T}_{B4} \cap \mathfrak{T}_{A2.1}$ | Keyframed 3D medical animation with $\mathfrak{m} = \texttt{assert}$ |
| $\mathfrak{T}_{D9.1} \cap \mathfrak{T}_{A4}$ | Pixel-art motion graphics (retro-aesthetic broadcast packages) |
| $\mathfrak{T}_{D3.2} \cap \mathfrak{T}_{D10}$ | Chibi and kawaii overlap: $\mathfrak{T}_{D10} \supset \mathfrak{T}_{D3.2}$ as a special case |

### Three Structural Observations

**First:** Axis A is the only axis in which a predicate ($\mathfrak{T}_{A3.4}$, animatronics) is formally excluded from the group it is conventionally placed in ($A3$, stop motion). This is not a taxonomic error in the source — it is a genuine edge case where industrial convention and formal definition diverge. The solution is to retain the conventional grouping as a navigational convenience while making the formal exclusion explicit.

**Second:** Axis D contains the only continuous-valued predicate domain ($\iota_{\text{render}} \in [0,1]$). All predicates in Axes A, B, and C are defined on discrete domains. This means Axis D predicates are inherently threshold-based and their boundaries are stipulative, not derived. This is stated explicitly in the D1 table and applies to all D-axis predicates.

**Third:** The source taxonomy contains two trademarked terms used as generic labels: "Claymation" (Laika) and "Audio-Animatronics" / "Autonomatronics" (The Walt Disney Company). Both are formalised here with the correct generic terms as primary labels and the trademarks noted in footnotes. Using trademarks as generic labels is a category error that confuses proprietary instances with the general predicate.

---

## References

- AMPAS (Academy of Motion Picture Arts and Sciences). (2024). *Rule Fifteen: Short Films and Feature Films*, Academy Awards Rules. [Short film duration threshold.]
- Barrier, M. (2003). *Hollywood Cartoons: American Animation in Its Golden Age*. Oxford University Press.
- Crafton, D. (1993). *Before Mickey: The Animated Film 1898–1928*. University of Chicago Press.
- Fleischer, M. (1917). *Method of Producing Moving-Picture Cartoons*. US Patent 1,242,674.
- Furniss, M. (2008). *A New History of Animation*. Thames & Hudson.
- Furniss, M. (1998). *Art in Motion: Animation Aesthetics*. John Libbey.
- Natsume, F. (1997). *Tezuka wa Shindeiru* [Tezuka Is Dead]. Shogakukan.
- Wertheimer, M. (1912). "Experimentelle Studien über das Sehen von Bewegung." *Zeitschrift für Psychologie*, 61, 161–265. [Phi phenomenon; the perceptual basis of motion from discrete frames.]
- Wells, P. (1998). *Understanding Animation*. Routledge.
