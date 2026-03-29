---
disclaimer: >
  No information within this document should be taken for granted.
  Any statement or premise not backed by a real logical definition or
  verifiable reference may be invalid, erroneous, or a hallucination.
  This analysis represents one model's assessment of leverage and
  novelty — it may be wrong. Verify independently.
title: "Step-Change Contribution: HumanBody Schema v3.0.0"
date: 2026-03-28
method: step-change-contributor/v1
source_document: "human-body-schema/src/ (11 TypeScript/Zod modules, ~2,190 lines)"
---

# Step-Change Contribution: HumanBody Schema v3.0.0

---

## 1. Gap Analysis

### 1.1 Structural Map

The schema is an 11-module Zod/TypeScript domain model for the human body,
organized into six layers:

1. **Primitives** (`shared.ts`) — Vector3, Quaternion, RigidPose,
   SymmetricTensor3, Color, branded UUID types, extension points.
2. **Anatomical structure** (`skeletal.ts`, `muscular.ts`, `connective.ts`,
   `nervous.ts`, `organs.ts`, `vascular.ts`) — static physical entities:
   bones, joints, muscles, tendons, ligaments, cartilage, nerves, organs,
   vessels.
3. **Appearance** (`appearance.ts`) — hair, clothing, rendering overlay.
4. **Kinematics** (`kinematics.ts`) — reference frames, body segments, joint
   states, poses, motion sequences.
5. **Dynamics** (`dynamics.ts`) — forces (10-variant discriminated union),
   moments, contacts, loading conditions, free body diagrams.
6. **Root composition** (`body.ts`) — HumanBodySchema assembles all
   subsystems with cross-entity referential integrity validation via
   `superRefine`.

The schema's implicit claim: it is a *complete structural contract* for
representing a human body's anatomy, configuration, and mechanical loading
at any instant.

### 1.2 Strengths

**Core strengths:**

- Rigorous type safety: discriminated unions for forces and vessels,
  branded UUID types for cross-entity FK safety, unit-length refinements
  on quaternions and direction vectors.
- Genuine anatomical modeling: tendons as first-class entities mediating
  muscle→bone attachment, fascicle architecture, Grood-Suntay joint
  coordinates, De Leva segment inertial parameters.
- Separation of concerns: rendering extracted from anatomy, computed fields
  annotated, extension points on every entity.
- The Farnese Atlas instance demonstrates the schema works end-to-end for
  a nontrivial case (52 bones, 53 muscles, 31 joint states, 35 forces in
  static equilibrium).

**Implicit competencies:**

- The authors understand multibody dynamics (the segment/joint/force
  decomposition follows the standard inverse dynamics formulation).
- The module boundaries follow natural physical subsystem boundaries, not
  arbitrary code organization.

**Structural virtues:**

- Schema versioning with literal type enforcement on the root entity.
- Scorecard-audited compliance with 31 design rules.
- Modular files that can be consumed independently.

### 1.3 Gap Inventory

| G-ID | Dimension | Description | Severity | Evidence |
|------|-----------|-------------|----------|----------|
| G1 | **Formalization** | The schema has 7+ fields annotated `[Computed]` whose derivation equations exist only in `.describe()` strings — the mathematical relationships between fields are documentation, not schema. | Critical | `pcsa` described as "computed: volume / optimalFiberLength"; `equilibrium.netForce` described as "Resultant of all forces"; `segmentStates` described as "derived from rootPose + jointStates via FK"; FBD residuals described as "ΣF - ma" — all in prose, none enforceable. |
| G2 | **Mechanism** | The schema stores muscle forces and joint angles but does not express the causal mechanism linking them: the force-length-velocity relationship (Hill model), the moment arm geometry, the activation dynamics. A `MuscleForce` of 2,200 N at activation 0.88 is accepted without any check that this force is physiologically achievable given the muscle's current length and maximum isometric force. | Critical | `MuscleForceSchema` has `activationLevel`, `currentLength`, `contractionVelocity`, and references `maxIsometricForce` on `MuscleSchema` — all the ingredients — but no relation connecting them. |
| G3 | **Boundary** | The schema never declares when its model breaks down. Bones are rigid bodies — but bones flex under load. Joints are perfect constraints — but real joints have laxity. Segments are rigid — but soft tissue deforms. The boundary between "valid rigid-body model" and "invalid because deformation matters" is unexamined. | Moderate | No documentation of model validity domain. |
| G4 | **Abstraction** | Every `[Computed]` annotation is a specific instance of a general pattern: *derived field = f(stored fields)*. The schema handles each derivation as a one-off comment. The general pattern — a **computation graph** where nodes are schema fields and edges are functional dependencies — is never named or reified. | Critical | Seven independent `[Computed]` annotations with no unifying structure. |
| G5 | **Cross-domain** | The schema reinvents elements of spatial algebra (Featherstone, 2008) without referencing it. Force and Moment are separate entity types, but in spatial algebra they are one object (a 6D **wrench** = [moment; force]). Similarly, linear velocity and angular velocity are separate fields on `SegmentSpatialState`, but in spatial algebra they are one object (a 6D **twist**). | Moderate | `ForceSchema` and `MomentSchema` as separate discriminated unions; `SegmentSpatialStateSchema` with separate `linearVelocity` + `angularVelocity` fields. |
| G6 | **Temporal** | The schema can represent a sequence of poses (`MotionSequence`) but cannot express how the *forces* evolve across a motion — only `LoadingCondition` at a single instant. There is no entity for a time-series of loading conditions paired with a motion sequence. | Moderate | `MotionSequence` contains poses but not forces. `LoadingCondition` references one pose. No entity bridges the two across time. |
| G7 | **Asymmetry** | `BoneSchema` has optional `centerOfMass` and `inertiaTensor` (added for dynamics), but `BodySegmentSchema` has *required* `centerOfMass` and `inertiaTensor`. A segment composed of one bone may have inconsistent inertial data in both places. The schema does not declare which is authoritative. | Minor | `BoneSchema.centerOfMass` is optional; `BodySegmentSchema.centerOfMass` is required. No annotation resolving the redundancy. |
| G8 | **Falsifiability** | The `equilibrium` object on `LoadingCondition` stores residuals but nothing enforces that these residuals are actually computed from the forces. The Farnese Atlas instance has `residualForceMagnitude: 0` and `isStatic: true`, but these are *declared* values, not derived values. The schema cannot distinguish a correctly balanced loading from one where someone typed `0`. | Critical | `equilibrium` is a plain data object with no derivation constraint tying it to the `forces` array. |

### 1.4 Honesty Check

- **G3** (boundary conditions) — **[possibly intentional]**. Declaring model
  validity bounds is arguably an application-layer concern, not a schema
  concern. The schema design rules explicitly exclude "application-layer
  business logic."
- **G5** (spatial algebra) — **[possibly intentional]**. Wrench/twist
  unification is elegant but forces a 6D representation that is less
  readable for non-specialists. The current Force/Moment separation may be
  a deliberate readability trade-off.
- **G6** (temporal force series) — **[possibly intentional]**. The schema
  may intend for consumers to compose `MotionSequence` + `LoadingCondition[]`
  at the application layer.

G1, G2, G4, and G8 are not plausibly intentional. They represent structural
deficiencies that limit what the schema can guarantee about its own data.

---

## 2. Leverage Ranking

### 2.1 Candidate Contributions

**C1 — Declarative Derivation Graph**
A new module (`derivations.ts`) that reifies the computation graph of the
schema's derived fields. Each derivation is a schema entity that declares:
which stored fields are inputs, which computed field is the output, and the
mathematical function relating them — expressed as a symbolic equation string
plus a reference to the governing physical law. This turns `[Computed]`
annotations from documentation into enforceable structure.
- Addresses: G1, G4, G8
- Form: New schema module + root entity field
- Cross-domain source: Dataflow programming, constraint propagation
  (Sussman & Steele, 1980), equation-based modeling (Modelica)
- Novelty claim: Schema design standards (the 31 rules) don't address
  inter-field functional dependencies because most schemas don't have
  physics. This schema does, and the rules it follows (Rule 2: constraints
  in schema; Rule 18: computed vs. stored) demand a mechanism for
  expressing derivations that doesn't yet exist in the Zod ecosystem.

**C2 — Constitutive Law Layer**
A new module (`constitutive.ts`) encoding the material and physiological
laws that constrain field values: the Hill muscle model (force-length-velocity),
ligament force-strain curves, cartilage stress-strain, bone yield criteria.
Each law is a schema entity that references the fields it constrains and
includes the functional form.
- Addresses: G2, G3
- Form: New schema module
- Cross-domain source: Continuum mechanics, muscle physiology (Zajac, 1989)
- Novelty claim: Constitutive laws are usually embedded in simulation code,
  not declared in the data schema. Putting them in the schema makes the
  physics auditable without running a simulator.

**C3 — Spatial Algebra Primitives**
Replace Force+Moment with a unified `Wrench` (6D spatial force) and
add `Twist` (6D spatial velocity), following Featherstone (2008). Restructure
dynamics around spatial quantities.
- Addresses: G5
- Form: Refactored primitives + dynamics module
- Cross-domain source: Spatial vector algebra (Featherstone, 2008)
- Novelty claim: Standard in robotics; rarely applied to anatomical schemas.

**C4 — Dynamic Motion Record**
An entity that pairs a `MotionSequence` with a time-aligned series of
`LoadingCondition`s, creating a complete kinetic+kinematic record (the
output of inverse dynamics over a full movement).
- Addresses: G6
- Form: New schema entity
- Cross-domain source: Standard gait analysis output (C3D format)
- Novelty claim: Low — this is the obvious next step for anyone doing
  motion analysis.

**C5 — Physical Consistency Validator**
Combine C1 and C2: a module that declares both the derivation graph (C1)
and the constitutive constraints (C2), enabling a consumer to verify
that a `LoadingCondition` is *physically consistent* — not just
referentially intact, but mechanically valid.
- Addresses: G1, G2, G4, G8
- Form: New module that subsumes C1 and C2
- Cross-domain source: Constraint satisfaction (CSP), equation-based
  modeling, formal verification
- Novelty claim: This transforms the schema from a passive data container
  (stores whatever you put in it) to a self-verifying physical model
  (can distinguish mechanically valid states from invalid ones). No
  biomechanical data schema I'm aware of includes its own physics as
  declarative constraints.

### 2.2 Falsifiability Gate

**C1 — Declarative Derivation Graph — [Falsifiable]**
Refuting observation: Construct a `LoadingCondition` whose `equilibrium.netForce`
field is declared as `{x:0, y:0, z:0}` but whose `forces` array sums to a
non-zero resultant. If the derivation graph cannot detect this inconsistency,
the contribution is refuted.

**C2 — Constitutive Law Layer — [Falsifiable]**
Refuting observation: Instantiate a `MuscleForce` with `magnitude` exceeding
`maxIsometricForce × activation × f(length) × f(velocity)` by a factor of 2.
If the constitutive law schema cannot flag this as a violation, the
contribution is refuted.

**C3 — Spatial Algebra Primitives — [Reformulable]**
As stated ("use wrenches and twists"), this is a representation choice, not a
falsifiable claim. Reformulation: "Wrench/twist representation enables
detection of inconsistencies between force and moment fields that the
current separate-entity representation cannot detect." Refuting observation:
produce an inconsistency detectable under the current schema but not under
the wrench representation. This seems unlikely — the wrench is strictly more
informative — but the contribution is primarily aesthetic, not epistemic.
**[Advances as reformulated, but weak.]**

**C4 — Dynamic Motion Record — [Falsifiable]**
Refuting observation: trivially falsifiable (produce a motion with no
temporal force data and see if the entity can represent it). But this is an
incremental entity addition, not a step-change. **Advances but low-impact.**

**C5 — Physical Consistency Validator — [Falsifiable]**
Refuting observation (composite): Take the Farnese Atlas JSON. Modify one
muscle force to be 10× its physiologically achievable maximum. Modify the
equilibrium residual to still claim `isStatic: true`. A schema with the
C5 module should flag both violations; the current schema accepts the file
silently. If C5 cannot flag either violation, it is refuted.

### 2.3 Scoring and Selection

| C-ID | Gaps | Impact | Uniqueness | Realizability | Leverage (I×U×R) |
|------|------|--------|------------|---------------|------------------|
| C1 | G1,G4,G8 | 4 | 4 | 5 | **80** |
| C2 | G2,G3 | 3 | 3 | 3 | 27 |
| C3 | G5 | 2 | 2 | 4 | 16 |
| C4 | G6 | 2 | 1 | 5 | 10 |
| C5 | G1,G2,G4,G8 | 5 | 4 | 3 | 60 |

**Selected: C1 — Declarative Derivation Graph.**

C5 scores highest on Impact (5) but Realizability drops to 3 because fully
encoding constitutive laws (Hill model parameters, nonlinear force-strain
curves) requires empirical data and curve-fitting that cannot be rigorously
produced from the schema alone. C1 achieves nearly the same structural
transformation with Realizability 5: every derivation it declares is a
known, closed-form equation already implicit in the schema's own comments.
C1 is also the *precondition* for C2 and C5 — the derivation graph is
the infrastructure on which constitutive laws would later be mounted.
Highest leverage at the highest confidence.

---

## 3. The Contribution

### Derivation Graph: A Declarative Computation Layer for Physical Schemas

#### 3.1 The Problem

The schema currently has 7+ fields annotated `[Computed]`. Each annotation
contains, in a `.describe()` string, the equation that relates the computed
field to its source fields. Examples:

- `pcsa` → `volume / optimalFiberLength`
- `equilibrium.netForce` → `Σ forces[i].magnitude × forces[i].direction`
- `segmentStates[i].globalPose` → `FK(rootPose, jointStates)`
- `wholeBodyCenterOfMass` → `Σ(mᵢ × rᵢ) / Σ(mᵢ)`
- `FBD.translationalResidual` → `Σ F - m × a`
- `FBD.rotationalResidual` → `Σ M - I × α`
- `GravitationalForce.magnitude` → `segment.mass × gravitationalAcceleration`

These equations are the schema's physics. They are what make the schema a
*biomechanical model* rather than a database of numbers. But right now they
live in documentation strings — invisible to validators, invisible to code
generators, invisible to any tooling.

This means:

1. **No consistency checking.** The Farnese Atlas declares
   `equilibrium.isStatic: true` with `residualForceMagnitude: 0`. These
   values are trusted, not verified. A consumer cannot ask: "Is this
   equilibrium field consistent with the forces array?"

2. **No dependency tracking.** If a consumer changes a joint angle in a
   `Pose`, which computed fields are now stale? Without a derivation graph,
   every consumer must independently know the answer.

3. **No derivation ordering.** Some computed fields depend on other computed
   fields (segment global CoM depends on segment global pose, which depends
   on FK from joint angles). The dependency order is implicit knowledge.

4. **Rule 2 violation.** The schema's own design standard says "constraints
   MUST live in the schema, not in documentation." The derivation equations
   are constraints — specifically, functional dependency constraints — and
   they live in documentation.

#### 3.2 The Solution: `derivations.ts`

A new module defining two entities: `DerivationRule` (a single functional
dependency) and `DerivationGraph` (the DAG of all rules for a body model).

```typescript
import { z } from "zod";
import { ExtensionsSchema } from "./shared";

// =============================================================================
// Derivation Graph — Declarative Computation Layer
//
// Each DerivationRule declares: "field Y is computed from fields X₁...Xₙ
// by equation E." The set of all rules forms a directed acyclic graph
// (the derivation graph) where edges point from inputs to outputs.
//
// This module does NOT execute computations. It declares them. Execution
// is an application-layer concern. The schema's job is to make the
// derivation structure inspectable, validatable, and mechanically
// traversable.
//
// Cross-domain precedent: Modelica (Elmqvist et al., 1998) separates
// equation declaration from equation solving. Bond graphs (Paynter, 1961)
// separate energy structure from causality assignment. This module
// applies the same principle to a data schema: declare the equations,
// let the consumer choose the solver.
// =============================================================================

export const DERIVATION_GRAPH_VERSION = "1.0.0" as const;

// --- Field Reference ---
// A JSON-path-like reference to a field in the schema.
// Examples:
//   "muscles[*].pcsa"
//   "loadingConditions[*].equilibrium.netForce"
//   "currentPose.segmentStates[*].globalPose"
//   "segments[*].mass"

export const FieldRefSchema = z
  .string()
  .min(1)
  .regex(/^[a-zA-Z_]/)
  .describe(
    "Dot-separated path to a schema field. " +
    "Use [*] for array iteration, [i] for indexed access. " +
    "Examples: 'muscles[*].pcsa', 'loadingConditions[*].equilibrium.netForce'",
  );

// --- Physical Law Reference ---
// Traceability: which law governs this derivation?

export const PhysicalLawSchema = z.object({
  name: z.string().min(1).describe("Name of the physical law or definition"),
  equation: z
    .string()
    .min(1)
    .describe(
      "Symbolic equation in standard math notation. " +
      "Variables correspond to inputFields and outputField. " +
      "Examples: 'PCSA = V / L_opt', 'F_net = Σ Fᵢ', 'r_com = Σ(mᵢrᵢ) / Σ(mᵢ)'",
    ),
  reference: z
    .string()
    .optional()
    .describe(
      "Literature reference. Example: 'Zajac, CRC Crit Rev Biomed Eng 17(4):359–411, 1989'",
    ),
  domain: z
    .enum([
      "kinematics",       // FK, IK, velocity/acceleration propagation
      "rigid_body_dynamics", // Newton-Euler, energy methods
      "muscle_mechanics",  // Hill model, activation dynamics
      "material_mechanics", // Stress-strain, viscoelasticity
      "definition",        // Pure mathematical definitions (PCSA, CoM, etc.)
      "constraint",        // Kinematic constraints (closed loops, ground contact)
    ])
    .describe("Which branch of mechanics this law belongs to"),
});

// --- Derivation Rule ---
// A single functional dependency: output = f(inputs).

export const DerivationRuleSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).describe("Human-readable label (e.g. 'forward_kinematics', 'equilibrium_check')"),

  // What law governs this derivation
  law: PhysicalLawSchema,

  // Input fields (stored or previously computed)
  inputFields: z
    .array(FieldRefSchema)
    .min(1)
    .describe("Schema fields that serve as inputs to this derivation"),

  // Output field (the computed result)
  outputField: FieldRefSchema.describe(
    "Schema field that this derivation computes. Must be a field annotated [Computed].",
  ),

  // Directionality: can this equation be inverted?
  // FK goes joint angles → segment poses. IK goes segment poses → joint angles.
  // Declaring invertibility enables bidirectional use.
  invertible: z
    .boolean()
    .default(false)
    .describe("Whether the equation can be solved in reverse (output → inputs)"),

  // Tolerance for consistency checking.
  // When verifying that a stored computed field matches its derivation,
  // how close is close enough?
  consistencyTolerance: z
    .object({
      absolute: z.number().nonnegative().describe("Absolute tolerance in the output field's units"),
      relative: z.number().min(0).max(1).optional().describe("Relative tolerance (fraction of expected value)"),
    })
    .optional()
    .describe(
      "Tolerance for consistency verification. " +
      "If |stored - derived| > tolerance, the field is inconsistent.",
    ),

  // Dependency: does this rule depend on the output of another rule?
  dependsOn: z
    .array(z.string().uuid())
    .optional()
    .describe("IDs of DerivationRules whose outputs are inputs to this rule (establishes DAG order)"),

  extensions: ExtensionsSchema,
});

// --- Derivation Graph ---
// The complete DAG of all derivation rules for a body model.

export const DerivationGraphSchema = z
  .object({
    version: z.literal(DERIVATION_GRAPH_VERSION),
    rules: z.array(DerivationRuleSchema).min(1),
  })
  .superRefine((graph, ctx) => {
    const ruleIds = new Set(graph.rules.map((r) => r.id));
    const outputFields = new Set<string>();

    graph.rules.forEach((rule, i) => {
      // Each output field should be computed by exactly one rule
      if (outputFields.has(rule.outputField)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Output field '${rule.outputField}' is computed by multiple rules`,
          path: ["rules", i, "outputField"],
        });
      }
      outputFields.add(rule.outputField);

      // Dependency references must exist
      rule.dependsOn?.forEach((depId, j) => {
        if (!ruleIds.has(depId)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Rule '${rule.name}' depends on non-existent rule: ${depId}`,
            path: ["rules", i, "dependsOn", j],
          });
        }
      });
    });

    // Cycle detection (topological sort)
    const adj = new Map<string, string[]>();
    const inDeg = new Map<string, number>();
    for (const r of graph.rules) {
      adj.set(r.id, []);
      inDeg.set(r.id, 0);
    }
    for (const r of graph.rules) {
      for (const dep of r.dependsOn ?? []) {
        adj.get(dep)?.push(r.id);
        inDeg.set(r.id, (inDeg.get(r.id) ?? 0) + 1);
      }
    }
    const queue = [...inDeg.entries()].filter(([, d]) => d === 0).map(([id]) => id);
    let visited = 0;
    while (queue.length > 0) {
      const node = queue.shift()!;
      visited++;
      for (const neighbor of adj.get(node) ?? []) {
        const newDeg = (inDeg.get(neighbor) ?? 1) - 1;
        inDeg.set(neighbor, newDeg);
        if (newDeg === 0) queue.push(neighbor);
      }
    }
    if (visited < graph.rules.length) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Derivation graph contains a cycle — computed fields cannot circularly depend on each other",
        path: ["rules"],
      });
    }
  });

// --- Inferred Types ---

export type FieldRef = z.infer<typeof FieldRefSchema>;
export type PhysicalLaw = z.infer<typeof PhysicalLawSchema>;
export type DerivationRule = z.infer<typeof DerivationRuleSchema>;
export type DerivationGraph = z.infer<typeof DerivationGraphSchema>;
```

#### 3.3 The Standard Derivation Graph for HumanBody v3.0.0

The following derivation rules capture every `[Computed]` annotation
currently in the schema. This is not aspirational — these are the
equations that already exist in `.describe()` strings, now promoted to
schema-level declarations.

**Rule D1: Muscle PCSA**
```
inputFields:  ["muscles[*].volume", "muscles[*].optimalFiberLength"]
outputField:  "muscles[*].pcsa"
law:          { name: "PCSA definition",
                equation: "PCSA = V / L_opt",
                domain: "definition" }
tolerance:    { absolute: 0.01 }
```

**Rule D2: Forward Kinematics**
```
inputFields:  ["currentPose.rootPose",
               "currentPose.jointStates[*].angles",
               "segments[*].proximalJointId",
               "joints[*].axes"]
outputField:  "currentPose.segmentStates[*].globalPose"
law:          { name: "Forward kinematics",
                equation: "T_global(i) = T_parent(i) × R(q_i)",
                reference: "Craig, 'Introduction to Robotics', 3rd ed., Ch. 3",
                domain: "kinematics" }
invertible:   true   // IK is the inverse
dependsOn:    []
```

**Rule D3: Segment Global Center of Mass**
```
inputFields:  ["currentPose.segmentStates[*].globalPose",
               "segments[*].centerOfMass"]
outputField:  "currentPose.segmentStates[*].globalCenterOfMass"
law:          { name: "Coordinate transformation",
                equation: "r_global = R × r_local + p",
                domain: "kinematics" }
dependsOn:    [D2]
```

**Rule D4: Whole-Body Center of Mass**
```
inputFields:  ["currentPose.segmentStates[*].globalCenterOfMass",
               "segments[*].mass"]
outputField:  "currentPose.wholeBodyCenterOfMass"
law:          { name: "Center of mass definition",
                equation: "r_com = Σ(mᵢ × rᵢ) / Σ(mᵢ)",
                domain: "definition" }
dependsOn:    [D3]
```

**Rule D5: Gravitational Force Magnitude**
```
inputFields:  ["segments[*].mass",
               "loadingConditions[*].forces[type=gravitational].gravitationalAcceleration"]
outputField:  "loadingConditions[*].forces[type=gravitational].magnitude"
law:          { name: "Newton's law of gravitation (uniform field)",
                equation: "F = m × g",
                domain: "rigid_body_dynamics" }
```

**Rule D6: Equilibrium Net Force**
```
inputFields:  ["loadingConditions[*].forces[*].magnitude",
               "loadingConditions[*].forces[*].direction"]
outputField:  "loadingConditions[*].equilibrium.netForce"
law:          { name: "Force equilibrium",
                equation: "F_net = Σ(Fᵢ × d̂ᵢ)",
                reference: "Newton's Second Law (static case: F_net = 0)",
                domain: "rigid_body_dynamics" }
tolerance:    { absolute: 1.0 }   // 1 N tolerance for static equilibrium
```

**Rule D7: Equilibrium Residual**
```
inputFields:  ["loadingConditions[*].equilibrium.netForce"]
outputField:  "loadingConditions[*].equilibrium.residualForceMagnitude"
law:          { name: "Vector magnitude",
                equation: "|F_net| = √(Fx² + Fy² + Fz²)",
                domain: "definition" }
dependsOn:    [D6]
```

**Rule D8: Equilibrium Static Check**
```
inputFields:  ["loadingConditions[*].equilibrium.residualForceMagnitude",
               "loadingConditions[*].equilibrium.residualMomentMagnitude"]
outputField:  "loadingConditions[*].equilibrium.isStatic"
law:          { name: "Static equilibrium criterion",
                equation: "isStatic = (|F_net| < ε_F) ∧ (|M_net| < ε_M)",
                domain: "rigid_body_dynamics" }
dependsOn:    [D7]
tolerance:    { absolute: 0 }  // Boolean: exact
```

**Rule D9: FBD Translational Residual**
```
inputFields:  ["freeBodyDiagrams[*].forces[*].magnitude",
               "freeBodyDiagrams[*].forces[*].direction",
               "segments[matched].mass",
               "currentPose.segmentStates[matched].linearAcceleration"]
outputField:  "freeBodyDiagrams[*].translationalResidual"
law:          { name: "Newton's second law",
                equation: "residual = ΣF - m·a",
                domain: "rigid_body_dynamics" }
dependsOn:    [D2]
```

**Rule D10: FBD Rotational Residual**
```
inputFields:  ["freeBodyDiagrams[*].moments[*]",
               "segments[matched].inertiaTensor",
               "currentPose.segmentStates[matched].angularAcceleration"]
outputField:  "freeBodyDiagrams[*].rotationalResidual"
law:          { name: "Euler's equation of rotation",
                equation: "residual = ΣM - I·α",
                reference: "Goldstein, 'Classical Mechanics', 3rd ed., Ch. 5",
                domain: "rigid_body_dynamics" }
dependsOn:    [D2]
```

The dependency DAG:

```
D1 (pcsa)
D2 (FK) → D3 (segment CoM) → D4 (whole-body CoM)
D5 (gravity mag)
D6 (net force) → D7 (residual mag) → D8 (static check)
D2 → D9 (FBD translational)
D2 → D10 (FBD rotational)
```

No cycles. Two independent subgraphs (kinematics chain, dynamics chain)
connected by the dependency of D9/D10 on D2 (you need segment poses
to compute FBD residuals).

#### 3.4 What This Enables

With the derivation graph as a first-class schema entity, consumers can:

1. **Validate consistency.** Given a populated `HumanBody`, traverse the
   derivation graph in topological order and recompute every `[Computed]`
   field from its inputs. Compare against stored values using the declared
   tolerances. Report inconsistencies. This is mechanical — no domain
   knowledge required by the validator, because the domain knowledge is
   in the graph.

2. **Detect staleness.** If a consumer modifies a stored field (e.g., changes
   a joint angle), the derivation graph identifies every downstream computed
   field that is now stale. This is a simple reachability query on the DAG.

3. **Generate solver skeletons.** A code generator can read the derivation
   graph and produce a function stub for each rule: input types, output type,
   equation comment, dependency order. The consumer fills in the numerical
   implementation. The schema guarantees the topology; the consumer supplies
   the numerics.

4. **Audit the physics.** A reviewer can inspect the derivation graph to
   answer: "What physical laws does this model assume?" without reading
   application code. Every assumption is a `PhysicalLaw` with a name, an
   equation, and a literature reference.

**[Falsification criterion]:** Construct a `HumanBody` instance where
`loadingConditions[0].equilibrium.netForce` is `{x:0, y:0, z:0}` but the
forces array sums to a net force of 500 N downward. A tool that traverses
the derivation graph and applies Rule D6 must flag the `netForce` field
as inconsistent (|stored - derived| = 500 N > tolerance of 1 N). If no
such tool can be built from the derivation graph's information alone — if
it requires out-of-band knowledge not captured in the schema — then this
contribution is refuted.

---

## 4. Justification

### 4.1 Step-Change Argument

Without the derivation graph, the HumanBody schema is a **data container** —
it accepts whatever you put in it, enforcing only type constraints and
referential integrity. A `LoadingCondition` where the forces sum to 10,000 N
downward but `equilibrium.isStatic` is `true` parses without error. A muscle
PCSA that contradicts the muscle's own volume and fiber length is accepted
silently. The schema knows these fields are related (the comments say so)
but cannot act on that knowledge.

With the derivation graph, the schema becomes a **self-describing physical
model**. The equations that relate its fields are declared as data, not
buried in code. This is a qualitative shift because it enables a class of
operations that are impossible without it: consistency verification,
staleness detection, solver generation, physics auditing. These operations
are not incremental improvements to existing capabilities — they are new
capabilities that did not exist in any form.

The step-change is analogous to the difference between a spreadsheet with
only values and a spreadsheet with formulas. Both store numbers. But only
the latter can recompute, detect errors, and propagate changes. The
derivation graph gives the HumanBody schema its formulas.

### 4.2 Leverage Audit

- **Impact (scored 4, actual 4).** The contribution does not change the
  schema's data model — it adds a metadata layer. This limits its impact
  to the "major upgrade" tier rather than "transforms core value." It
  would reach 5 if it also included constitutive laws (C2/C5), but that
  was deferred for realizability.

- **Uniqueness (scored 4, actual 4).** The idea of a declarative equation
  layer is standard in simulation (Modelica, Simulink). Applying it to a
  *data schema* (not a simulation tool) is non-obvious. A biomechanics
  engineer would not think to put equations in the Zod schema; a software
  engineer would not know which equations to put. The contribution requires
  both perspectives simultaneously.

- **Realizability (scored 5, actual 5).** Every rule in the standard
  derivation graph is a known, closed-form equation already present in the
  schema's comments. No empirical data, curve-fitting, or domain-specific
  parameter estimation was required. The Zod module compiles.

### 4.3 Falsifiability Audit

**Falsification criterion (restated):** Construct a `HumanBody` instance
with an internally inconsistent `LoadingCondition` (forces that do not sum
to the stored equilibrium value). A tool that reads only the derivation
graph and the instance data — with no hardcoded physics — must detect the
inconsistency. If such a tool cannot be built from the derivation graph's
information, the contribution is refuted.

**Test sketch:** Write a TypeScript function
`validateDerivedFields(body: HumanBody, graph: DerivationGraph): ValidationResult[]`
that performs topological traversal of the graph, evaluates each rule's
equation symbolically or numerically, and compares the result against the
stored value using the rule's declared tolerance. Apply this to the Farnese
Atlas instance with the equilibrium residual intentionally corrupted to 0.
The function should report a violation on rule D6 or D7.

**Strength of test: Strong.** A single counterexample (an inconsistency
the graph cannot detect) refutes the core claim that the derivation graph
makes stored-vs-derived consistency mechanically verifiable.

### 4.4 Limitations and Caveats

1. **The derivation graph declares equations but does not execute them.**
   A consumer still needs a numerical solver. The schema provides the
   topology and the symbolic form; the consumer provides `Math.sqrt` and
   matrix multiplication. This is by design (separation of declaration
   from execution), but it means the schema alone cannot *fix*
   inconsistencies — only *detect* them.

2. **The symbolic equation strings are human-readable, not machine-parseable.**
   A truly mechanized validator would need either: (a) a standardized
   equation syntax (MathML, SymPy string format, LaTeX), or (b) a
   companion code module per rule. The current contribution uses informal
   math notation for readability. This is a known trade-off — formalizing
   the equation language is a natural follow-on.

3. **The graph covers only the equations already implicit in the schema.**
   It does not add constitutive laws (Hill model, ligament force-strain,
   etc.). Adding those would require empirical parameters that vary per
   individual and per muscle. The derivation graph provides the
   infrastructure for later mounting such laws (they would be additional
   `DerivationRule` entries), but does not include them.

4. **Cycle detection is necessary but not sufficient for physical
   correctness.** An acyclic derivation graph can still contain wrong
   equations. The graph guarantees structural validity (no circular
   dependencies, all references resolve), not physical validity (the
   equations are correct implementations of the named laws). Correctness
   of individual equations remains the author's responsibility.

5. **The field reference syntax (`FieldRefSchema`) is a mini-language.**
   Path expressions like `"loadingConditions[*].forces[type=gravitational].magnitude"`
   require a parser. The current regex constraint on `FieldRefSchema`
   validates only the first character. A production implementation would
   need a formal grammar for field paths — essentially a subset of
   JSONPath. This is deferred to avoid over-engineering the initial
   contribution.
