---
title: "Human Body Schema — v3.0.0 Changelog & Scorecard"
version: "3.0.0"
date: "2026-03-28"
disclaimer: >
  No information within this document should be taken for granted.
  Any statement or premise not backed by a real logical definition
  or verifiable reference may be invalid, erroneous, or a hallucination.
---

# Changelog: v2.0.0 → v3.0.0 (Breaking)

## What v3.0.0 Adds

Two new subsystems — **kinematics** and **dynamics** — turning the schema
from a static anatomical description into a full biomechanical model
capable of representing any body configuration under any loading.

### New Module: `kinematics.ts`

| Entity | Purpose |
|--------|---------|
| `ReferenceFrame` | Coordinate systems (global, segment, joint, custom). Follows ISB convention: +X anterior, +Y superior, +Z right lateral. Ref: Wu & Cavanagh, J Biomech 28(10):1257–1261, 1995. |
| `BodySegment` | Rigid body between adjacent joints. Carries mass, center of mass, inertia tensor, radius of gyration ratios. Maps 1-to-many onto bones. Ref: De Leva, J Biomech 29(9):1223–1230, 1996. |
| `JointState` | Instantaneous angles (+ optional ω, α) per DOF for one joint, using Grood-Suntay joint coordinate system convention. Ref: Grood & Suntay, J Biomech Eng 105(2):136–144, 1983. |
| `SegmentSpatialState` | World-space pose + linear/angular velocity/acceleration of a segment. Derived from forward kinematics (marked computed per Rule 18). |
| `Pose` | Complete body configuration: root segment pose + all joint states. Represents "the body in any position." |
| `MotionSequence` | Time-ordered series of poses for animation or motion capture. |
| `StandardPoseEnum` | Named preset configurations (anatomical, T-pose, A-pose, seated, supine, prone). |

### New Module: `dynamics.ts`

| Entity | Purpose |
|--------|---------|
| `ForceSchema` | **Discriminated union** (on `forceType`) of 10 force types — not a single schema with optional fields. Each variant carries only the fields relevant to its physics. |
| `GravitationalForce` | Weight acting on a segment's CoM. |
| `MuscleForce` | Active + passive components, activation level, moment arm, current length, contraction velocity. |
| `GroundReactionForce` | GRF with center of pressure, directional components (vertical, A-P, M-L), free moment. Standard gait analysis output. |
| `JointReactionForce` | Resultant joint force from inverse dynamics, with optional JCS decomposition (compression, shear). |
| `ExternalForce` | Arbitrary applied loads (carried objects, resistance bands, wind). |
| `LigamentousForce` | Passive restraint from ligaments, with strain and stiffness. |
| `InertialForce` | d'Alembert pseudo-force for non-inertial frame analysis. |
| `ContactForce` | Generic contact with normal/friction decomposition and friction coefficients. |
| `AerodynamicDrag` | Fd = ½ρCdAv² with all parameters explicit. |
| `BuoyancyForce` | Archimedes' principle with displaced volume and fluid density. |
| `Moment` | Torque about a joint or point, with optional JCS decomposition. Typed by source (resultant, muscle contribution, external, gravitational, inertial). |
| `Contact` | Contact definition with surface properties (friction coefficients, restitution). |
| `LoadingCondition` | **The primary analysis entity.** Pairs a `Pose` with all forces, moments, and contacts at that instant. Includes equilibrium check (ΣF, ΣM residuals). |
| `FreeBodyDiagram` | Per-segment isolation of forces and moments. The fundamental unit for Newton-Euler inverse dynamics. |

### Changes to Existing Modules

| Module | Change | Category |
|--------|--------|----------|
| `shared.ts` | Added `QuaternionSchema` (Hamilton convention, unit-length enforced) | New type |
| `shared.ts` | Added `RigidPoseSchema` (position + quaternion orientation) | New type |
| `shared.ts` | Added `SymmetricTensor3Schema` (6-component inertia tensor) | New type |
| `shared.ts` | Added branded IDs: `SegmentId`, `PoseId`, `ForceId`, `MomentId`, `LoadingConditionId`, `ContactId` | New IDs |
| `shared.ts` | `SCHEMA_VERSION` → `"3.0.0"` | Version bump |
| `skeletal.ts` | `BoneSchema` gains `centerOfMass` and `inertiaTensor` (optional) | New optional fields (safe) |
| `skeletal.ts` | `JointSchema` gains `axes` (Grood-Suntay JCS axes) | New optional field (safe) |
| `body.ts` | Root entity gains: `referenceFrames`, `segments`, `currentPose`, `savedPoses`, `motionSequences`, `loadingConditions`, `freeBodyDiagrams` | New optional fields (safe) |
| `body.ts` | Cross-validation expanded for segment→bone, segment→joint, pose→segment, pose→joint, loadingCondition→pose references | Validation |

### Why All New Root Fields Are Optional

Every kinematics/dynamics field on the root entity is optional. This is intentional: the schema serves two audiences. For anatomical modeling (rigging, visualization, medical education), kinematics and dynamics are irrelevant noise. For biomechanical analysis, they're essential. Making them optional means v3.0.0 is **backward-compatible with all valid v2.0.0 instances** — you only need to update `schemaVersion` to `"3.0.0"`.

---

## Breaking Changes in v3.0.0

| Change | Category | Migration |
|--------|----------|-----------|
| `schemaVersion` must now be `"3.0.0"` | Literal type change | Update the field value |

All other changes are additive (new optional fields, new modules). This is technically a **minor** version bump in terms of instance compatibility, but a **major** bump in terms of schema surface area and conceptual scope — the schema now models physics, not just anatomy.

---

## Scorecard (v3.0.0)

### Part I — Type Safety and Precision

| # | Rule | Score | Notes |
|---|------|-------|-------|
| 1 | Every field has a single unambiguous type | **Pass** | All new fields fully typed |
| 2 | Constraints live in the schema | **Pass** | Quaternion unit-length refine, gyration ratios [0,1], friction coefficients ≥0 |
| 3 | Enums closed, versioned, not overloaded | **Pass** | `ForceTypeEnum` (10 values), `MomentTypeEnum` (5), `ContactTypeEnum` (6), `ReferenceFrameTypeEnum` (5), `StandardPoseEnum` (7) |
| 4 | Nullable ≠ optional ≠ absent | **Pass** | `proximalJointId: nullable` (root segment has no proximal joint) vs optional computed fields |
| 5 | Arrays: item type + cardinality + order | **Pass** | `jointStates.min(1)`, `boneIds.min(1)`, `forces.min(1)` on FBD, `poses.min(1)` on sequence |
| 6 | Temporal: precision, timezone, format | **Pass** | `timestamp` is seconds (float), `sampleRate` is Hz. No calendar dates. |
| 7 | Numeric units declared | **Pass** | Every numeric field annotated: N, cm, cm/s, cm/s², deg, deg/s, deg/s², g·cm², kg·cm², N·cm, g/cm³, Hz |
| 8 | Polymorphism: explicit discriminator | **Pass** | `ForceSchema = z.discriminatedUnion("forceType", [...])` with 10 variants |
| 9 | Defaults declared in schema | **Pass** | `gravitationalAcceleration: 981`, `fluidDensity: 0.001225`, `interpolation: "linear"`, etc. |

### Part II — Identity and Relationships

| # | Rule | Score | Notes |
|---|------|-------|-------|
| 10 | Stable, opaque identity | **Pass** | Branded UUIDs on all new entities |
| 11 | Relationships navigable ≥1 dir | **Pass** | Pose→JointState→Joint, Segment→Bone, Segment→Joint, LoadingCondition→Pose, Force→Segment/Muscle/Joint, FBD→Segment+LoadingCondition |
| 12 | Composition/aggregation/association | **Pass** | Body *composes* segments, poses, loading conditions. LoadingCondition *aggregates* forces. MuscleForce *associates* with Muscle by ID. |
| 13 | FK targets declared | **Pass** | superRefine validates: segment→bone, segment→joint, pose→segment, pose→joint, loadingCondition→pose |
| 14 | Cyclic graph constraints | **Pass** | Reference frames form a tree (parentFrameId, null root). Bone hierarchy still acyclic. |

### Part III — Normalization and Coherence

| # | Rule | Score | Notes |
|---|------|-------|-------|
| 15 | Single source of truth | **Pass** | Segment inertial properties live on `BodySegment`, not duplicated on bones |
| 16 | No bag-of-arrays | **Warn** | Root entity has 7+ optional arrays. Rationale: these are distinct subsystems, not repetitions of the same concept. A body genuinely *is* a composition of subsystems. |
| 17 | Cross-cutting types defined once | **Pass** | `Vector3`, `RigidPose`, `Quaternion`, `SymmetricTensor3` shared across kinematics and dynamics |
| 18 | Computed vs. stored | **Pass** | `segmentStates`, `wholeBodyCenterOfMass`, `globalCenterOfMass`, `equilibrium`, FBD residuals all annotated `[Computed]` |

### Part IV — Evolution and Compatibility

| # | Rule | Score | Notes |
|---|------|-------|-------|
| 19 | Explicit versioning | **Pass** | `SCHEMA_VERSION = "3.0.0"` |
| 20 | No duplicate-version entities | **Pass** | |
| 21 | Breaking changes classified | **Pass** | See table above — only `schemaVersion` literal is breaking |
| 22 | Field deprecation | **Pass** | No fields deprecated in this version |

### Part V — Operational Annotations

| # | Rule | Score | Notes |
|---|------|-------|-------|
| 23 | Sensitive fields classified | **Pass** | No PII. Motion capture data could be re-identifying in some contexts — noted but not classified as PII for general use. |
| 24 | Identity/provenance immutability | **Warn** | `id`, `schemaVersion`, `forceType` should be immutable. Zod cannot enforce at runtime. Documented. |
| 25 | Localization strategy | **Pass** | N/A — physics terms are universal |
| 26 | Multi-actor provenance | **Pass** | N/A |

### Part VI — Documentation and Generability

| # | Rule | Score | Notes |
|---|------|-------|-------|
| 27 | Consistent naming | **Pass** | camelCase fields, PascalCase schemas throughout |
| 28 | Mechanically generatable | **Pass** | All Zod schemas produce validators + TS types |
| 29 | Extension points | **Pass** | `ExtensionsSchema` on every new entity |
| 30 | Access patterns don't dictate | **Pass** | FBD is a view/projection of LoadingCondition, not a denormalization |
| 31 | Readable as standalone | **Pass** | Each module self-documenting with ISB/biomechanics references |

### Totals

- **MUST Pass**: 19/19
- **SHOULD Pass or Documented**: 11/11 (2 Warn with rationale)

---

## Design Decisions

1. **Quaternions over Euler angles for kinematics.** The existing `TransformSchema` uses Euler angles (fine for authoring). The new `RigidPoseSchema` uses unit quaternions because they avoid gimbal lock, compose correctly, and interpolate via SLERP. Both coexist — transforms are for static bone placement, rigid poses are for kinematic state.

2. **Segment ≠ Bone.** In biomechanics, a "segment" is a rigid body assumed between two joints. The foot (26 bones) is typically one segment. The femur is also one segment. This distinction matters for dynamics — you compute Newton-Euler equations per *segment*, not per *bone*.

3. **Forces as discriminated union.** A gravitational force has no application point (it acts on the CoM). A muscle force has activation level, moment arm, and contraction velocity. A ground reaction force has center of pressure. Putting all of these behind `forceType: string` with optional fields would make the schema structurally ambiguous. The discriminated union gives each variant exactly the fields it needs.

4. **LoadingCondition as the primary analysis entity.** This is where pose meets forces. Every biomechanical question ("what forces does the ACL experience at mid-stance?") is answered by constructing a LoadingCondition: pick a pose, enumerate all forces, solve for unknowns via Newton-Euler.

5. **Gravitational acceleration in cm/s².** The schema uses centimeters throughout (bone length, position, etc.). Using 9.81 m/s² would require unit conversion at every force calculation. 981 cm/s² is consistent with the schema's length unit.

6. **All new root fields optional.** This preserves backward compatibility and makes the schema usable for pure anatomy (no physics needed for a rigging pipeline) and pure biomechanics (just populate segments + poses + forces).

7. **De Leva (1996) for segment inertial properties.** This is the standard reference for body segment parameters, adjusting Zatsiorsky's earlier cadaver measurements. The `gyrationRatios` field directly maps to De Leva's Table 4.

8. **Grood-Suntay for joint angles.** The standard clinical convention for reporting 3D joint angles. The three axes (body-fixed, floating, body-fixed) avoid sequence dependency issues of Euler angles while remaining anatomically interpretable.

---

## v3.0.0-patch.1 — Derivation Graph (2026-03-28)

Implements **C1 (Declarative Derivation Graph)** from the step-change
contribution analysis. Addresses gaps G1, G4, G7, and G8.

### New Module: `derivations.ts`

| Entity | Purpose |
|--------|---------|
| `FieldRef` | JSON-path-like reference to a schema field (e.g. `"muscles[*].pcsa"`). |
| `PhysicalLaw` | Named physical law with symbolic equation, literature reference, and mechanics domain classification. |
| `DerivationRule` | Single functional dependency: output = f(inputs) governed by a PhysicalLaw, with consistency tolerance and DAG ordering. |
| `DerivationGraph` | Complete DAG of all derivation rules. Validates: unique output fields, referential integrity of `dependsOn`, and acyclicity (Kahn's algorithm). |

Cross-domain precedent: Modelica (Elmqvist et al., 1998), bond graphs
(Paynter, 1961) — separate equation declaration from equation solving.

### Changes to Existing Modules

| Module | Change | Category |
|--------|--------|----------|
| `body.ts` | Root entity gains `derivationGraph` (optional `DerivationGraphSchema`) | New optional field (safe) |
| `skeletal.ts` | `BoneSchema.centerOfMass` and `inertiaTensor` descriptions clarified with `[Authority: subordinate]` annotation — segment-level values are authoritative for dynamics | Documentation (G7) |
| `kinematics.ts` | `BodySegmentSchema.centerOfMass` and `inertiaTensor` descriptions clarified with `[Authority: authoritative]` annotation | Documentation (G7) |
| `index.ts` | Exports: `DerivationGraphSchema`, `DerivationRuleSchema`, `PhysicalLawSchema`, `FieldRefSchema`, `DERIVATION_GRAPH_VERSION`, and inferred types | Re-export |

### What This Enables

1. **Consistency verification** — traverse the DAG in topological order,
   recompute each `[Computed]` field from stored inputs, compare against
   stored values using declared tolerances.
2. **Staleness detection** — when a stored field changes, reachability
   on the DAG identifies all downstream computed fields that are stale.
3. **Solver skeleton generation** — code generators can produce function
   stubs for each rule with correct input/output types and dependency order.
4. **Physics auditing** — reviewers can inspect every physical assumption
   the model makes without reading application code.

Generated by: Claude Opus 4.6 (1M context)

---

## v3.0.0-patch.2 — Constitutive Law Layer (2026-03-28)

Implements **C2 (Constitutive Law Layer)** from the step-change contribution
analysis. Addresses gaps G2 (no mechanism linking muscle forces to physiology)
and G3 (no model validity boundaries).

Cross-domain sources: Hill (1938), Zajac (1989), Woo et al. (1999),
Mow et al. (1980), Reilly & Burstein (1974).

### New Module: `constitutive.ts`

| Entity | Purpose |
|--------|---------|
| `ValidityBoundary` | Declares when a modeling assumption breaks down (G3). Every constitutive law must state its validity domain. |
| `HillMuscleLaw` | Hill three-element muscle model: force-length (Gaussian), force-velocity (Hill's equation), passive elastic element. Constrains `MuscleForce.magnitude ≤ F_max × [a × f_L × f_V + f_PE]`. Ref: Zajac (1989), Thelen (2003). |
| `LigamentForceStrainLaw` | Piecewise nonlinear force-strain: toe region (quadratic) → linear region → failure. Ref: Woo et al. (1999). |
| `CartilageStressStrainLaw` | Biphasic linear elastic model. Contact stress must not exceed damage threshold. Ref: Mow et al. (1980). |
| `BoneYieldCriterion` | Failure envelope for the rigid body assumption. Cortical yield ~130/190 MPa (tension/compression). Ref: Reilly & Burstein (1974). |
| `JointRangeLimit` | Soft constraint: exponential passive resistance torque at ROM boundaries. |
| `ConstitutiveLawSchema` | Discriminated union (on `lawType`) of all five law types. |
| `ConstitutiveLawsSchema` | Collection with unique-ID validation. |
| `STANDARD_VALIDITY_BOUNDARIES` | Reference constants for the four core rigid-body model assumptions. |

### Changes to Existing Modules

| Module | Change | Category |
|--------|--------|----------|
| `body.ts` | Root entity gains `constitutiveLaws` (optional `ConstitutiveLawsSchema`) | New optional field (safe) |
| `index.ts` | Full re-export of all constitutive types, schemas, enums, and constants | Re-export |

### What This Enables

1. **Physiological plausibility checking** — verify that a `MuscleForce`
   magnitude is within the Hill model envelope for the muscle's current
   state (activation, length, velocity). A force exceeding the envelope
   by >10% is flagged as `error`.
2. **Material integrity checking** — verify ligament forces are consistent
   with strain, cartilage contact pressures are below damage thresholds,
   bone stresses are below yield.
3. **Model boundary transparency (G3)** — every constitutive law declares
   when its assumptions break down. Consumers can inspect
   `STANDARD_VALIDITY_BOUNDARIES` for the four core assumptions (rigid
   bodies, perfect joints, rigid segments, quasi-static loading).
4. **C5 readiness** — `ConstitutiveLaws` + `DerivationGraph` together
   provide the infrastructure for C5 (Physical Consistency Validator):
   derivations check computed-vs-stored consistency, constitutive laws
   check field-value plausibility.

### Falsification Criterion

Instantiate a `MuscleForce` with magnitude = 2× the Hill model envelope
(`F_max × activation × f_L × f_V + f_PE`). A tool that reads the
`ConstitutiveLaws` and the instance data must flag this as a violation.
If no such tool can be built from the schema's information alone, C2
is refuted.

Generated by: Claude Opus 4.6 (1M context)
