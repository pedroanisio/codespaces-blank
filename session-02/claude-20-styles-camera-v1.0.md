---
title: "20 Definitions of Camera Angle, Movement, and Optical Effect — Formal Definitions"
version: "1.0.0"
status: draft
companion: "20-styles-video-v1.1.md, 20-styles-scene-v1.0.md"
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

# 20 Definitions of Camera Angle, Movement, and Optical Effect

## 0. Foundational Apparatus

### 0.1 The Shot

The fundamental unit of analysis in this document is the **shot** $\Xi$ — a single continuous camera exposure with no intra-unit cuts. This is strictly finer than the scene $\Sigma$ defined in the companion document: a scene $\Sigma$ is a temporally contiguous sequence of one or more shots; a shot is the minimal unit at which camera configuration has a stable description.

A **shot** $\Xi$ is a 7-tuple:

$$\Xi = (F_\Xi,\; T_\Xi,\; \alpha_\Xi,\; \mathbf{p},\; R,\; \mathcal{L},\; \mathcal{A}_{\text{sub}})$$

| Symbol | Domain | Meaning |
|--------|--------|---------|
| $F_\Xi$ | $\mathbb{Z}_{>0} \to \text{Image}$ | Ordered finite sequence of frames; no cut within $T_\Xi$ |
| $T_\Xi = [s_0, s_1]$ | $\mathbb{R}_{\geq 0}$ | Temporal extent; $s_1 > s_0$ |
| $\alpha_\Xi$ | $\{0,1\}$ | Audio present ($1$) or absent ($0$) |
| $\mathbf{p}$ | $T_\Xi \to \mathbb{R}^3$ | Camera nodal-point position trajectory in world coordinates |
| $R$ | $T_\Xi \to SO(3)$ | Camera orientation trajectory; $R(t)$ maps camera-space to world-space |
| $\mathcal{L}$ | $\mathcal{F}$ | Lens specification (§0.3) |
| $\mathcal{A}_{\text{sub}}$ | $\mathcal{A}$ | Subject arrangement (§0.4) |

The **no-cut condition** is the defining property of $\Xi$: $F_\Xi$ is produced by a single continuous recording; the pixel content of $F_\Xi(i+1)$ is the optical successor of $F_\Xi(i)$ for all $i$ within $\text{dom}(F_\Xi)$.

A **camera configuration predicate** $\mathfrak{C}$ is a predicate $\mathfrak{C} : \Xi \to \{0,1\}$. All definitions below are **stipulative biconditionals**: $\Xi$ belongs to configuration class $\mathfrak{C}$ if and only if every stated condition holds.

### 0.2 Coordinate System and Derived Angles

Let $\mathbb{R}^3$ be equipped with a right-handed world coordinate frame: $\mathbf{e}_x$ (right), $\mathbf{e}_y$ (up), $\mathbf{e}_z$ (backward, i.e. the camera looks in the $-\mathbf{e}_z$ direction by convention). The camera-space forward direction is $\mathbf{e}_3 = (0, 0, -1)^T$ in camera space; its world-space instantiation at time $t$ is the **optical axis direction**:

$$\hat{\mathbf{o}}(t) = R(t)\,\mathbf{e}_3, \quad \hat{\mathbf{o}}(t) \in S^2$$

Three scalar angles are derived from $\hat{\mathbf{o}}(t)$ and $R(t)$:

$$\theta_{\text{el}}(t) = \arcsin\!\bigl(\hat{\mathbf{o}}(t) \cdot \mathbf{e}_y\bigr) \in \left[-\tfrac{\pi}{2},\, \tfrac{\pi}{2}\right]$$

$$\theta_{\text{az}}(t) = \text{atan2}\!\bigl(-\hat{\mathbf{o}}(t) \cdot \mathbf{e}_z,\; \hat{\mathbf{o}}(t) \cdot \mathbf{e}_x\bigr) \in (-\pi,\, \pi]$$

$$\theta_{\text{roll}}(t) = \text{atan2}\!\bigl((R(t)\,\mathbf{e}_2) \cdot \mathbf{e}_z,\; (R(t)\,\mathbf{e}_2) \cdot \mathbf{e}_y\bigr) \in (-\pi,\, \pi]$$

where $\mathbf{e}_2 = (0,1,0)^T$ in camera space is the camera's "up" vector. Conventions:

- $\theta_{\text{el}} < 0$: optical axis points downward (camera looks down on subject)
- $\theta_{\text{el}} > 0$: optical axis points upward (camera looks up at subject)
- $\theta_{\text{el}} = 0$: optical axis is horizontal
- $\theta_{\text{roll}} = 0$: camera is level (horizon is horizontal in frame)
- $\theta_{\text{roll}} \neq 0$: camera is canted; positive roll is clockwise viewed from behind the camera

For shots with a **static** camera orientation (§8), $\theta_{\text{el}}$, $\theta_{\text{az}}$, and $\theta_{\text{roll}}$ are constants. For moving shots, angle conditions apply to the **mean** value over $T_\Xi$ unless stated otherwise:

$$\bar{\theta}_{\text{el}} = \frac{1}{|T_\Xi|} \int_{s_0}^{s_1} \theta_{\text{el}}(t)\, dt$$

and analogously for $\bar{\theta}_{\text{az}}$ and $\bar{\theta}_{\text{roll}}$.

### 0.3 Lens Specification $\mathcal{L}$

$$\mathcal{L} = (f,\; N,\; d_f,\; \phi_{\text{fmt}},\; \beta)$$

| Symbol | Domain | Meaning |
|--------|--------|---------|
| $f$ | $\mathbb{R}_{>0}$ | Focal length (mm); specified as 35 mm full-frame equivalent |
| $N$ | $\mathbb{R}_{>0}$ | F-number (relative aperture): $N = f / D_{\text{eff}}$ where $D_{\text{eff}}$ is effective entrance pupil diameter |
| $d_f$ | $T_\Xi \to \mathbb{R}_{>0}$ | Focus distance trajectory (metres from nodal point to plane of focus); may be time-varying |
| $\phi_{\text{fmt}}$ | $\Phi$ | Optical format and aspect ratio specification |
| $\beta$ | $\{\texttt{spherical},\; \texttt{anamorphic},\; \texttt{fisheye},\; \texttt{macro}\}$ | Lens class (§0.3.1) |

**Derived quantities:**

*Angle of View* (horizontal):
$$\theta_{\text{aov}} = 2 \arctan\!\left(\frac{d_h}{2f}\right)$$
where $d_h$ is the horizontal dimension of the imaging sensor or film gate. Wider $\theta_{\text{aov}}$ corresponds to shorter $f$ ("wide angle"); narrower corresponds to longer $f$ ("telephoto").

*Circle of Confusion* $c$ is the maximum acceptable blur-spot diameter on the imaging medium, conventionally $c = d_{\text{diag}} / 1500$ for motion picture use (industry convention; no universal authority).[^coc]

*Depth of Field*:
$$\text{DOF}(f, N, d_f, c) = \frac{2 N c\, d_f^2\,(f^{-2} - c^2 N^2)^{-1/2}}{f^2} \approx \frac{2 N c\, d_f^2}{f^2} \quad \text{(paraxial approximation, } d_f \gg f\text{)}$$

This is the standard lens optics result; see Smith (2008, *Modern Optical Engineering*, 4th ed., McGraw-Hill, pp. 138–141) for the full derivation.

*Hyperfocal Distance*:
$$H = \frac{f^2}{N \cdot c} + f \approx \frac{f^2}{N \cdot c} \quad (f \ll H)$$

When $d_f = H$, the depth of field extends from $H/2$ to $\infty$ (paraxial approximation).

#### 0.3.1 Lens Class $\beta$

- $\beta = \texttt{spherical}$: rotationally symmetric optical design; rectilinear projection (straight lines in the world map to straight lines in the image)
- $\beta = \texttt{anamorphic}$: optically asymmetric; compresses one axis of the scene onto the film/sensor and is de-squeezed in post-production; produces characteristic horizontal lens flares and oval bokeh
- $\beta = \texttt{fisheye}$: extreme short focal length with equisolid or equidistant (non-rectilinear) projection; severe barrel distortion; $\theta_{\text{aov}} > 100°$ typically
- $\beta = \texttt{macro}$: optimised for focus distances $d_f \leq 0.5\,\text{m}$; reproduction ratio $m \geq 1:2$ (subject size on sensor $\geq$ half actual size)

### 0.4 Subject Arrangement $\mathcal{A}_{\text{sub}}$

$$\mathcal{A}_{\text{sub}} = \{\mathbf{q}_1, \mathbf{q}_2, \ldots, \mathbf{q}_n\}$$

where $\mathbf{q}_i \in \mathbb{R}^3$ is the world-space position of the $i$-th diegetic subject at a reference time within $T_\Xi$. The **camera-to-subject vector** for subject $i$ at time $t$ is:

$$\mathbf{d}_i(t) = \mathbf{q}_i - \mathbf{p}(t)$$

The **subject elevation angle** $\theta_{\text{sub},i}(t)$ is the angle between $\hat{\mathbf{o}}(t)$ and the horizontal plane at $\mathbf{p}(t)$, relative to subject $i$:

$$\theta_{\text{sub},i}(t) = \arcsin\!\left(\frac{(\mathbf{q}_i - \mathbf{p}(t)) \cdot \mathbf{e}_y}{\|\mathbf{q}_i - \mathbf{p}(t)\|}\right)$$

This is the elevation angle *from the camera to the primary subject*. Angle predicates (§§1–7) are stated in terms of $\theta_{\text{sub},i}$.

---

## Part I — Camera Angle Predicates

*Angle predicates are conditions on $(\bar{\theta}_{\text{el}},\; \bar{\theta}_{\text{roll}},\; \mathcal{A}_{\text{sub}})$, and in the case of relational predicates (§7), on the positional relationship between $\mathbf{p}$ and elements of $\mathcal{A}_{\text{sub}}$.*

---

## 1. Bird's Eye View

$$\mathfrak{C}_{\text{bev}}(\Xi) = 1 \iff$$

- $\bar{\theta}_{\text{el}} \leq -\Theta_{\text{bev}}$ where $\Theta_{\text{bev}} \in \left[\frac{5\pi}{12},\frac{\pi}{2}\right]$ (i.e. $75° \leq |\bar{\theta}_{\text{el}}| \leq 90°$): the optical axis is directed steeply downward, approaching nadir[^bev-threshold]
- The primary subject(s) $\mathcal{A}_{\text{sub}}$ are visible from above; the ground plane or floor is the dominant background element
- The camera position $\mathbf{p}(t) \cdot \mathbf{e}_y > \max_i \mathbf{q}_i \cdot \mathbf{e}_y + h_{\text{sub}}$ for all $t \in T_\Xi$, where $h_{\text{sub}}$ is the height of the tallest subject: the camera is strictly above all subjects

**Perceptual function:** The bird's eye view denies subjects their full height; it can produce a God-like or surveillance perspective, or render subjects as abstract pattern elements (figures seen purely as shapes against ground).

[^bev-threshold]: No single authority defines the boundary between high-angle and bird's eye view. The range $[75°, 90°]$ is a reasonable analytic stipulation. At exactly $\theta_{\text{el}} = -90°$ the camera points to nadir and the shot is sometimes called "top-down" or "overhead."

---

## 2. High Angle

$$\mathfrak{C}_{\text{high}}(\Xi) = 1 \iff$$

- $-\Theta_{\text{bev}} < \bar{\theta}_{\text{el}} < 0$: the optical axis is directed downward but not steeply enough to satisfy $\mathfrak{C}_{\text{bev}}$
- $\mathbf{p}(t) \cdot \mathbf{e}_y > \mathbf{q}_i \cdot \mathbf{e}_y$ for the primary subject $i$: the camera is above the subject's eye level[^high-angle-threshold]

**Formal consequence of elevation:** By the perspective projection equations, subjects shot from a high angle appear foreshortened vertically and contextualised by the ground plane or floor, producing an impression of reduced stature relative to environment.

[^high-angle-threshold]: "Eye level" of subject $i$ is $\mathbf{q}_i \cdot \mathbf{e}_y + h_{\text{eye},i}$ where $h_{\text{eye},i}$ is the subject's eye height above their reference point. This is an anatomical constant per subject, not a formal parameter of $\Xi$.

---

## 3. Eye-Level Shot

$$\mathfrak{C}_{\text{eye}}(\Xi) = 1 \iff$$

- $|\bar{\theta}_{\text{el}}| < \Theta_{\text{eye}}$ where $\Theta_{\text{eye}}$ is a small tolerance (typically $< 15°$, platform- and context-dependent)[^eye-threshold]: the optical axis is approximately horizontal
- The camera height $\mathbf{p}(t) \cdot \mathbf{e}_y$ is approximately equal to the eye level of the primary subject: $|\mathbf{p}(t) \cdot \mathbf{e}_y - (\mathbf{q}_i \cdot \mathbf{e}_y + h_{\text{eye},i})| < h_{\text{tol}}$

**Perceptual function:** The eye-level shot establishes parity between viewer and subject; the viewer is neither above nor below the subject. In continuity editing this is the default angle because it minimises perceptible spatial distortion.

[^eye-threshold]: The tolerance $\Theta_{\text{eye}}$ is intentionally not fixed. A shot that is $5°$ off horizontal is conventionally still "eye level"; $30°$ is not. Context determines the threshold; no universal value is available in the literature.

---

## 4. Low Angle

$$\mathfrak{C}_{\text{low}}(\Xi) = 1 \iff$$

- $0 < \bar{\theta}_{\text{el}} < \Theta_{\text{wev}}$ where $\Theta_{\text{wev}}$ is the lower bound of the worm's eye view (see §5): the optical axis is directed upward but not steeply
- $\mathbf{p}(t) \cdot \mathbf{e}_y < \mathbf{q}_i \cdot \mathbf{e}_y$ for the primary subject $i$: the camera is below the subject's eye level

**Perceptual function:** The low angle makes subjects appear taller and more dominant relative to their environment; the sky, ceiling, or architectural canopy replaces the ground plane as background, diminishing contextual anchoring.

---

## 5. Worm's Eye View

$$\mathfrak{C}_{\text{wev}}(\Xi) = 1 \iff$$

- $\bar{\theta}_{\text{el}} \geq \Theta_{\text{wev}}$ where $\Theta_{\text{wev}} \in \left[\frac{5\pi}{12}, \frac{\pi}{2}\right]$ (i.e. $\bar{\theta}_{\text{el}} \geq 75°$): the optical axis approaches the zenith
- The camera position is at or near the ground plane: $\mathbf{p}(t) \cdot \mathbf{e}_y \approx 0$ (relative to subject base)

**Formal symmetry with $\mathfrak{C}_{\text{bev}}$:** These predicates are dual under a $180°$ elevation reversal: $\mathfrak{C}_{\text{bev}}$ has $\bar{\theta}_{\text{el}} \to -\tfrac{\pi}{2}$; $\mathfrak{C}_{\text{wev}}$ has $\bar{\theta}_{\text{el}} \to +\tfrac{\pi}{2}$. They cannot intersect: $\mathfrak{C}_{\text{bev}} \cap \mathfrak{C}_{\text{wev}} = \emptyset$ (the sign of $\theta_{\text{el}}$ differs by necessity).

---

## 6. Dutch Angle (Canted Angle)

$$\mathfrak{C}_{\text{dutch}}(\Xi) = 1 \iff$$

- $|\bar{\theta}_{\text{roll}}| > \Theta_{\text{dutch}}$ where $\Theta_{\text{dutch}}$ is a perceptibility threshold[^dutch-threshold]: the camera is rotated around the optical axis such that the horizon (or any horizontal reference line in the scene) is not parallel to the horizontal edges of the frame
- The roll is **constitutive** of the shot's intent: $\theta_{\text{roll}} \neq 0$ is a deliberate choice in $\pi_V$, not a production error

**Formal independence:** $\mathfrak{C}_{\text{dutch}}$ is independent of $\bar{\theta}_{\text{el}}$: a dutch angle may be combined with any of $\mathfrak{C}_{\text{bev}}$, $\mathfrak{C}_{\text{high}}$, $\mathfrak{C}_{\text{eye}}$, $\mathfrak{C}_{\text{low}}$, $\mathfrak{C}_{\text{wev}}$.

[^dutch-threshold]: $\Theta_{\text{dutch}}$ is conventionally taken to be $\approx 5°$–$10°$ in practice — below this range the canting reads as a levelling error rather than a stylistic choice. No authoritative source defines a universal threshold; the intentionality condition in $\pi_V$ is the operative criterion, not the angle magnitude alone.

---

## 7. Over-the-Shoulder Shot (OTS)

$$\mathfrak{C}_{\text{ots}}(\Xi) = 1 \iff$$

- $|\mathcal{A}_{\text{sub}}| \geq 2$: at least two diegetic subjects $a_1$ (foreground) and $a_2$ (background) are in the scene
- The camera position $\mathbf{p}$ is behind and lateral to $a_1$: $(\mathbf{p} - \mathbf{q}_1) \cdot \hat{\mathbf{o}} < 0$ (camera is behind $a_1$ relative to the optical axis) and $\|(\mathbf{p} - \mathbf{q}_1) - [(\mathbf{p} - \mathbf{q}_1) \cdot \hat{\mathbf{o}}]\hat{\mathbf{o}}\| > 0$ (camera is laterally displaced from $a_1$'s axis)
- The frame contains both the shoulder/back of $a_1$ and the face of $a_2$ simultaneously
- $\nu_{\text{cam}} = \texttt{semi-subjective}$ (as defined in the companion scene document): the viewer shares $a_1$'s spatial orientation without being identified with $a_1$'s gaze

**Functional role:** The OTS is a fundamental unit of the shot/reverse-shot grammar; it establishes the **eyeline vector** between $a_1$ and $a_2$ and locks in the 180° spatial axis, satisfying the continuity editing contract.

---

## Part II — Camera Movement Predicates

*Movement predicates are conditions on the trajectories $\mathbf{p}(t)$ and $R(t)$ over $T_\Xi$. Let $\dot{\mathbf{p}}(t) = d\mathbf{p}/dt$ (translational velocity) and $\boldsymbol{\omega}(t) \in \mathbb{R}^3$ be the angular velocity vector such that $\dot{R}(t) = [\boldsymbol{\omega}(t)]_\times R(t)$, where $[\cdot]_\times$ is the skew-symmetric matrix operator.*

---

## 8. Static Shot

$$\mathfrak{C}_{\text{static}}(\Xi) = 1 \iff$$

- $\mathbf{p}(t) = \mathbf{p}_0 \in \mathbb{R}^3$ for all $t \in T_\Xi$: translational velocity is zero throughout
- $R(t) = R_0 \in SO(3)$ for all $t \in T_\Xi$: angular velocity is zero throughout
- Formally: $\|\dot{\mathbf{p}}(t)\| = 0$ and $\|\boldsymbol{\omega}(t)\| = 0$ for all $t \in T_\Xi$

**Idealisation note:** In practice, no camera support eliminates vibration entirely; the condition $\|\dot{\mathbf{p}}\| = 0$ is a limit. The operative condition is that any residual movement is below the perceptual threshold of stabilisation — i.e. the camera appears static to the viewer. This is an idealised definition.

**Formal consequence:** $\mathfrak{C}_{\text{static}}$ is the unique predicate under which both $\mathbf{p}$ and $R$ are constant. All other movement predicates require at least one non-zero derivative.

---

## 9. Pan

$$\mathfrak{C}_{\text{pan}}(\Xi) = 1 \iff$$

- $\mathbf{p}(t) = \mathbf{p}_0$ for all $t$: no translational movement (camera position is fixed)
- $\boldsymbol{\omega}(t) \cdot \mathbf{e}_y \neq 0$ for at least some $t \in T_\Xi$: there is rotation around the vertical world axis $\mathbf{e}_y$
- The $\mathbf{e}_y$-component of $\boldsymbol{\omega}$ dominates: $|\boldsymbol{\omega}(t) \cdot \mathbf{e}_y| \geq |\boldsymbol{\omega}(t) \cdot \mathbf{e}_j|$ for $j \in \{x, z\}$ and all $t$ at which $\|\boldsymbol{\omega}(t)\| > 0$

**Perceptual consequence:** A pan produces horizontal apparent motion of all elements in $F_\Xi$ at a rate proportional to their angular distance from the optical axis; distant objects move more slowly than proximate ones, encoding depth through differential parallax.

---

## 10. Tilt

$$\mathfrak{C}_{\text{tilt}}(\Xi) = 1 \iff$$

- $\mathbf{p}(t) = \mathbf{p}_0$ for all $t$: no translational movement
- The dominant rotation is around a horizontal axis perpendicular to $\hat{\mathbf{o}}$: $|\boldsymbol{\omega}(t) \cdot \mathbf{e}_x| \geq |\boldsymbol{\omega}(t) \cdot \mathbf{e}_j|$ for $j \in \{y, z\}$ and all $t$ at which $\|\boldsymbol{\omega}(t)\| > 0$
- This produces a change in $\theta_{\text{el}}(t)$ over $T_\Xi$: $|\theta_{\text{el}}(s_1) - \theta_{\text{el}}(s_0)| > 0$

**Formal distinction from pan:** Pan rotates around $\mathbf{e}_y$ (vertical axis); tilt rotates around a horizontal axis. Purity of the distinction: a shot may simultaneously pan and tilt; in that case, the dominant-axis condition identifies which predicate applies.

---

## 11. Camera Roll (In-Camera Roll)

$$\mathfrak{C}_{\text{roll}}(\Xi) = 1 \iff$$

- $\mathbf{p}(t) = \mathbf{p}_0$ for all $t$: no translational movement
- The dominant rotation is around the optical axis $\hat{\mathbf{o}}$: $|\boldsymbol{\omega}(t) \cdot \hat{\mathbf{o}}(t)| \geq |\boldsymbol{\omega}(t) \cdot \mathbf{e}_j|$ for the axes perpendicular to $\hat{\mathbf{o}}$
- $|\theta_{\text{roll}}(s_1) - \theta_{\text{roll}}(s_0)| > 0$: there is net change in roll over $T_\Xi$

**Distinction from $\mathfrak{C}_{\text{dutch}}$:** The dutch angle ($\mathfrak{C}_{\text{dutch}}$) is a static condition on $\bar{\theta}_{\text{roll}}$; the camera roll ($\mathfrak{C}_{\text{roll}}$) is a dynamic condition on $d\theta_{\text{roll}}/dt$. A shot may begin as a dutch angle and execute a roll to return to level, satisfying $\mathfrak{C}_{\text{dutch}}$ on average but also $\mathfrak{C}_{\text{roll}}$ by movement.

---

## 12. Dolly / Tracking Shot

$$\mathfrak{C}_{\text{dolly}}(\Xi) = 1 \iff$$

- $\|\dot{\mathbf{p}}(t)\| > 0$ for at least a substantial portion of $T_\Xi$: the camera undergoes significant translational movement
- The movement is smooth and mechanically stabilised: $\ddot{\mathbf{p}}(t)$ is bounded and does not exhibit the stochastic high-frequency component characteristic of handheld movement (§14)[^dolly-smooth]
- $R(t)$ may or may not change: dolly shots may track a subject with counter-rotation (keeping subject centred) or maintain a fixed orientation

**Sub-types by direction** (not separate predicates but descriptive labels):
- **Dolly in / push in:** $\dot{\mathbf{p}}(t) \cdot \hat{\mathbf{o}}(t) > 0$ (camera moves toward subject)
- **Dolly out / pull back:** $\dot{\mathbf{p}}(t) \cdot \hat{\mathbf{o}}(t) < 0$ (camera moves away from subject)
- **Tracking / follow:** $\dot{\mathbf{p}}(t)$ is approximately parallel to the subject's movement vector (camera follows subject laterally)
- **Trucking:** lateral movement, approximately perpendicular to $\hat{\mathbf{o}}$

[^dolly-smooth]: The distinction between dolly and handheld movement is operationally the power spectral density of $\|\dot{\mathbf{p}}\|$: dolly movement has low power at frequencies $> 1\,\text{Hz}$; handheld movement has substantial power at $1$–$10\,\text{Hz}$. No universal threshold is given here.

---

## 13. Crane / Jib Shot

$$\mathfrak{C}_{\text{crane}}(\Xi) = 1 \iff$$

- $\dot{\mathbf{p}}(t) \cdot \mathbf{e}_y \neq 0$ for at least a substantial portion of $T_\Xi$: the camera undergoes vertical translational movement (upward or downward)
- The vertical component of movement is the dominant component: $|\dot{\mathbf{p}}(t) \cdot \mathbf{e}_y| \geq |\dot{\mathbf{p}}(t) \cdot \mathbf{e}_j|$ for $j \in \{x, z\}$ over the dominant portion of $T_\Xi$
- Movement is smooth and mechanically stabilised (same stochastic condition as §12)

**Note:** Aerial camera systems (helicopter, drone) satisfy $\mathfrak{C}_{\text{crane}}$ if vertical movement is dominant; they may additionally involve lateral translation, in which case the dominant-axis condition determines the primary classification. Unmanned aerial vehicles are a realisation of crane functionality, not a formally distinct predicate class.

---

## 14. Handheld Shot

$$\mathfrak{C}_{\text{hh}}(\Xi) = 1 \iff$$

- $\mathbf{p}(t)$ and $R(t)$ are both time-varying, with neither constrained to zero velocity
- The power spectral density $S_{\dot{\mathbf{p}}}(\nu)$ of $\|\dot{\mathbf{p}}(t)\|$ has substantial energy at frequencies $\nu \in [1\,\text{Hz},\, 10\,\text{Hz}]$: there is characteristic micro-tremor
- The movement is not mechanically stabilised by a dolly, jib, or gyroscopic rig; it is produced by human operator hold[^hh-stabilise]
- The handheld quality is **constitutive** in $\pi_V$: the unstabilised appearance is intentional, not a correctable error

[^hh-stabilise]: Post-production digital stabilisation (e.g. warp stabilise) can reduce the apparent handheld quality. If post-production stabilisation is applied to the point where the stochastic high-frequency component is removed, the shot no longer satisfies $\mathfrak{C}_{\text{hh}}$ in its exhibited form, even if it was captured handheld. The predicate is defined on the exhibited $F_\Xi$, not on the capture method alone.

---

## 15. Dolly Zoom (Contra-Zoom / Vertigo Effect)

$$\mathfrak{C}_{\text{dz}}(\Xi) = 1 \iff$$

- $f(t)$ and $d_f(t)$ are both time-varying over $T_\Xi$
- The camera position $\mathbf{p}(t)$ moves along the optical axis: $\dot{\mathbf{p}}(t) \cdot \hat{\mathbf{o}}(t) \neq 0$
- The change in $f(t)$ (zoom) is **opposed** to the change in $d_f(t)$ (camera-to-subject distance) such that the primary subject $a_i$ maintains approximately constant angular size in the frame:

$$\frac{d}{dt}\left(\frac{h_{\text{sub},i}}{d_{f,i}(t)} \cdot f(t)\right) \approx 0$$

where $h_{\text{sub},i}$ is the physical height of subject $a_i$ and $d_{f,i}(t) = \|\mathbf{q}_i - \mathbf{p}(t)\|$

**Perceptual consequence:** Because the subject's angular size is held constant while the focal length changes, the background undergoes apparent spatial compression or expansion (the perspective distortion changes while the subject remains fixed). This dissociation — constant foreground, changing background perspective — is the defining perceptual effect. It was formalised as a technique by Irmin Roberts on *Vertigo* (Hitchcock, 1958) and was independently used on *Jaws* (Spielberg, 1975).

---

## Part III — Optical and Lens Effect Predicates

*These predicates are conditions on $\mathcal{L}$ and on derived quantities of $F_\Xi$.*

---

## 16. Shallow Depth of Field

$$\mathfrak{C}_{\text{sdof}}(\Xi) = 1 \iff$$

- The depth of field satisfies $\text{DOF}(f, N, d_f, c) < \Delta_{\text{sdof}}$, where $\Delta_{\text{sdof}}$ is the depth threshold below which background elements are perceivably out of focus[^sdof-threshold]
- Equivalently: the background region $\{q \in \mathbb{R}^3 : (q - \mathbf{p}) \cdot \hat{\mathbf{o}} > d_f + \text{DOF}/2\}$ produces blur-spot diameters $> c$ on the image plane
- The shallow depth is **constitutive**: $N$ is small (wide aperture) and/or $f$ is long and/or $d_f$ is short, in a combination that renders background elements perceptibly blurred ("bokeh")

[^sdof-threshold]: The threshold $\Delta_{\text{sdof}}$ is a perceptual threshold, not a fixed optical value. It depends on the size of $F_\Xi$ as viewed. No universal value exists; the operative condition is perceivable background defocus.

---

## 17. Deep Focus

$$\mathfrak{C}_{\text{df}}(\Xi) = 1 \iff$$

- $\text{DOF}(f, N, d_f, c)$ is sufficient to render all primary subjects $\{\mathbf{q}_1, \ldots, \mathbf{q}_n\}$ in acceptably sharp focus simultaneously, where "acceptably sharp" means blur-spot diameter $\leq c$ for all subjects: $\forall i,\; \|\mathbf{q}_i - \mathbf{p}\| \in [d_f - \text{DOF}/2,\; d_f + \text{DOF}/2]$
- The subjects span a substantial depth range: $\max_i \|\mathbf{q}_i - \mathbf{p}\| - \min_i \|\mathbf{q}_i - \mathbf{p}\| \gg 0$ — the sharpness across subjects is perceptively meaningful, not trivially achieved by proximity

**Optical conditions:** Deep focus typically requires small $N$ (narrow aperture, high f-number) and/or short $f$, and/or $d_f \geq H$ (focus at hyperfocal distance). The canonical achievement is associated with Gregg Toland's cinematography on *Citizen Kane* (Welles, 1941), which combined wide lenses, small apertures, and high-intensity arc lighting.

**Formal complement:** $\mathfrak{C}_{\text{sdof}}$ and $\mathfrak{C}_{\text{df}}$ are not strict complements — they are conditions on opposite ends of a continuous scale. A shot satisfies neither if it has moderate depth of field where only mid-range subjects are sharp.

---

## 18. Rack Focus

$$\mathfrak{C}_{\text{rf}}(\Xi) = 1 \iff$$

- $d_f(t)$ is time-varying over $T_\Xi$: $\exists\, t_1, t_2 \in T_\Xi$ such that $d_f(t_1) \neq d_f(t_2)$
- The change in $d_f$ transfers perceivable sharp focus from one subject $a_i$ (in focus at $t_1$) to a different subject $a_j$ (in focus at $t_2$), where $\|\mathbf{q}_i - \mathbf{p}\| \neq \|\mathbf{q}_j - \mathbf{p}\|$
- The depth of field is shallow enough ($\text{DOF} < |\|\mathbf{q}_i - \mathbf{p}\| - \|\mathbf{q}_j - \mathbf{p}\||$) that both subjects cannot be simultaneously sharp: this is the necessary condition for the focus transfer to be perceivable
- The change in $d_f$ is **constitutive** and deliberate, not a focus-hunting artefact

**Formal relationship with $\mathfrak{C}_{\text{sdof}}$:** $\mathfrak{C}_{\text{rf}} \Rightarrow \mathfrak{C}_{\text{sdof}}(t)$ for at least some $t \in T_\Xi$. A rack focus is not meaningful unless at least one subject is out of focus at some point; shallow DOF is a prerequisite.

---

## 19. Telephoto Compression

$$\mathfrak{C}_{\text{tele}}(\Xi) = 1 \iff$$

- $f > f_{\text{tele}}$ where $f_{\text{tele}}$ is the focal length above which perspective compression becomes perceptually significant[^tele-threshold]
- The shot exhibits perceivable **perspective compression**: the apparent depth distance between objects at different depths is reduced relative to their actual depth separation; objects appear spatially stacked

**Optical basis:** Perspective compression is a property of camera-to-subject distance and frame size, not focal length alone — a long focal length compels the operator to move the camera far from the subject to achieve a given framing, and it is the large camera-to-subject distance that produces compression. Formally, if two subjects at distances $d_1$ and $d_2$ from the camera ($d_1 < d_2$) are both in frame, their apparent depth ratio is:

$$\frac{d_2'}{d_1'} \propto \frac{d_1}{d_2}$$

This ratio approaches 1 as both $d_1$ and $d_2$ increase (camera is far away). The long focal length is an instrumental cause (it forces large $d_1, d_2$), not the direct optical cause.

[^tele-threshold]: Conventionally, $f > 85\,\text{mm}$ (35 mm equivalent) begins to produce compression effects; $f \geq 200\,\text{mm}$ is strongly compressive. These are industry conventions, not optical theorems; no authoritative source defines an absolute threshold.

---

## 20. Wide-Angle Distortion

$$\mathfrak{C}_{\text{wide}}(\Xi) = 1 \iff$$

- $f < f_{\text{wide}}$ where $f_{\text{wide}}$ is the focal length below which perspective exaggeration becomes perceptually significant[^wide-threshold]
- The shot exhibits perceivable **perspective exaggeration**: apparent depth distance between objects is expanded relative to their actual depth separation; foreground objects are enlarged relative to background objects beyond what is reproduced at longer focal lengths

**Optical basis:** Perspective exaggeration is the inverse of telephoto compression and arises by the same mechanism: the short focal length compels the camera to be placed close to the subject (small $d_1$), magnifying the ratio $d_2/d_1$. Barrel distortion (straight lines bowing outward at the frame periphery) is a separate optical phenomenon associated with short focal lengths and with $\beta = \texttt{fisheye}$; it is a lens aberration, not a perspective effect.

**Formal distinction:** For $\beta = \texttt{fisheye}$, barrel distortion is severe and non-rectilinear; the perspective exaggeration is accompanied by geometric deformation of straight lines. For $\beta = \texttt{spherical}$ with short $f$, perspective exaggeration occurs without barrel distortion (or with mild correctable distortion).

[^wide-threshold]: Conventionally, $f < 35\,\text{mm}$ (35 mm equivalent) begins to produce noticeable exaggeration; $f \leq 24\,\text{mm}$ is strongly exaggerated. These are industry conventions, not optical theorems.

---

## Summary: Configuration Predicate Space

### Formal Hierarchy

The 20 predicates partition into three axes:

| Axis | Predicates | Primary formal constraint |
|------|-----------|--------------------------|
| **Angle** | $\mathfrak{C}_{\text{bev}},\; \mathfrak{C}_{\text{high}},\; \mathfrak{C}_{\text{eye}},\; \mathfrak{C}_{\text{low}},\; \mathfrak{C}_{\text{wev}},\; \mathfrak{C}_{\text{dutch}},\; \mathfrak{C}_{\text{ots}}$ | Conditions on $\bar{\theta}_{\text{el}},\; \bar{\theta}_{\text{roll}},\; \mathcal{A}_{\text{sub}}$ |
| **Movement** | $\mathfrak{C}_{\text{static}},\; \mathfrak{C}_{\text{pan}},\; \mathfrak{C}_{\text{tilt}},\; \mathfrak{C}_{\text{roll}},\; \mathfrak{C}_{\text{dolly}},\; \mathfrak{C}_{\text{crane}},\; \mathfrak{C}_{\text{hh}},\; \mathfrak{C}_{\text{dz}}$ | Conditions on $\dot{\mathbf{p}}(t),\; \boldsymbol{\omega}(t)$ |
| **Optical / Lens** | $\mathfrak{C}_{\text{sdof}},\; \mathfrak{C}_{\text{df}},\; \mathfrak{C}_{\text{rf}},\; \mathfrak{C}_{\text{tele}},\; \mathfrak{C}_{\text{wide}}$ | Conditions on $\mathcal{L}$ and derived quantities |

The axes are **orthogonal**: conditions on $\bar{\theta}_{\text{el}}$ do not constrain $\dot{\mathbf{p}}$ or $\mathcal{L}$, and vice versa. This means **cross-axis composition is free**: any angle predicate may be combined with any movement predicate and any optical predicate to describe a fully specified shot configuration.

### Proved Disjunctions

Within each axis, some predicates are mutually exclusive by construction:

**Angle axis:**

$$\mathfrak{C}_{\text{bev}} \cap \mathfrak{C}_{\text{wev}} = \emptyset$$

because $\mathfrak{C}_{\text{bev}}$ requires $\bar{\theta}_{\text{el}} \leq -75°$ and $\mathfrak{C}_{\text{wev}}$ requires $\bar{\theta}_{\text{el}} \geq +75°$; both cannot hold simultaneously.

$$\mathfrak{C}_{\text{bev}} \cap \mathfrak{C}_{\text{eye}} = \emptyset, \quad \mathfrak{C}_{\text{wev}} \cap \mathfrak{C}_{\text{eye}} = \emptyset, \quad \mathfrak{C}_{\text{bev}} \cap \mathfrak{C}_{\text{high}} = \emptyset, \quad \mathfrak{C}_{\text{wev}} \cap \mathfrak{C}_{\text{low}} = \emptyset$$

by the non-overlapping elevation ranges.

**Movement axis:**

$$\mathfrak{C}_{\text{static}} \cap \mathfrak{C}_X = \emptyset \quad \text{for all } X \in \{\text{pan},\; \text{tilt},\; \text{roll},\; \text{dolly},\; \text{crane},\; \text{hh},\; \text{dz}\}$$

because $\mathfrak{C}_{\text{static}}$ requires $\|\dot{\mathbf{p}}\| = \|\boldsymbol{\omega}\| = 0$ everywhere; every other movement predicate requires at least one non-zero derivative.

**Optical axis:**

$$\mathfrak{C}_{\text{sdof}} \cap \mathfrak{C}_{\text{df}} = \emptyset$$

cannot be formally proved from the definitions without a specific scene: the boundary between shallow and deep depth of field is a continuous optical parameter, not a discrete partition. The two predicates define opposite ends of the DOF spectrum; whether a gap exists between them depends on the operative thresholds $\Delta_{\text{sdof}}$ and the multi-subject span condition in $\mathfrak{C}_{\text{df}}$.

### Notable Non-Empty Intersections

| Pair | Basis |
|------|-------|
| $\mathfrak{C}_{\text{dutch}} \cap \mathfrak{C}_{\text{low}}$ | Canted low angle — common in genre cinema |
| $\mathfrak{C}_{\text{ots}} \cap \mathfrak{C}_{\text{sdof}}$ | Shallow-focus OTS foregrounds subject separation |
| $\mathfrak{C}_{\text{hh}} \cap \mathfrak{C}_{\text{low}}$ | Low handheld — documentary and action usage |
| $\mathfrak{C}_{\text{tele}} \cap \mathfrak{C}_{\text{sdof}}$ | Long lens telephoto with wide aperture — portrait and surveillance aesthetics |
| $\mathfrak{C}_{\text{crane}} \cap \mathfrak{C}_{\text{bev}}$ | Crane descending from overhead approaching nadir |
| $\mathfrak{C}_{\text{dz}} \cap \mathfrak{C}_{\text{rf}}$ | Dolly zoom with simultaneous focus pull — rare; requires coordinated focus and dolly operation |

### Three Structural Observations

**First:** The movement axis is the only axis where one predicate — $\mathfrak{C}_{\text{static}}$ — **excludes all others** in its class by a zero condition ($\|\dot{\mathbf{p}}\| = 0$, $\|\boldsymbol{\omega}\| = 0$). The angle axis has no such predicate: all angle predicates admit intersection with $\mathfrak{C}_{\text{dutch}}$. The optical axis has no such predicate either: all optical predicates may in principle co-occur.

**Second:** $\mathfrak{C}_{\text{dz}}$ is the only predicate that **requires two components of $\mathcal{L}$ to be co-varying** ($f(t)$ and $d_f(t)$ both time-varying, in opposition). All other optical predicates are conditions on $\mathcal{L}$ at a single time. This makes $\mathfrak{C}_{\text{dz}}$ uniquely a predicate on a *trajectory in lens space*, not a snapshot.

**Third:** $\mathfrak{C}_{\text{ots}}$ is the only angle predicate that requires $|\mathcal{A}_{\text{sub}}| \geq 2$ — i.e., it is **irreducibly relational** between two subjects. All other angle predicates can in principle be defined for a single-subject shot. This structural dependence on subject multiplicity makes $\mathfrak{C}_{\text{ots}}$ categorically distinct from the other angle predicates, even though it belongs to the same axis.

---

## References

- Smith, W. J. (2008). *Modern Optical Engineering*, 4th ed. McGraw-Hill. [Depth-of-field derivation, pp. 138–141.]
- Hecht, E. (2017). *Optics*, 5th ed. Pearson. [Lens optics, thin-lens equation, aberrations.]
- Bordwell, D. & Thompson, K. (2010). *Film Art: An Introduction*, 9th ed. McGraw-Hill. [Shot scale conventions, editing grammar, pp. 185–232.]
- Brown, B. (2012). *Cinematography: Theory and Practice*, 2nd ed. Focal Press. [Practical lens and camera movement conventions.]
- Mascelli, J. V. (1965). *The Five C's of Cinematography*. Silman-James Press. [Camera angles, continuity, and composition conventions.]
