---
name: pipeline-orchestrator
description: >
  Meta-orchestration skill that manages the entire video production pipeline —
  sequences skills as a DAG, manages workflow graphs with typed nodes (Generation,
  Approval, Transform, Render, Validation, Notification), enforces governance,
  tracks costs, manages entity versioning, resolves EntityRefs via VersionSelector,
  validates DAG acyclicity (Rule 14), handles retries and async patterns, and
  manages the dependency graph. This skill does not create content — it coordinates
  all other skills. Use when initializing, monitoring, or controlling the pipeline.
  Trigger on "orchestrate the pipeline", "run the production", "manage the workflow",
  "start the pipeline", "check pipeline status". Always active as the meta-controller.
---

# Pipeline Orchestrator (S24)

## Purpose

Coordinate all 23 production skills as a directed acyclic graph, manage state
transitions, enforce governance, track costs, and ensure the pipeline produces
a complete, valid schema instance.

## Schema Surface

### Writes (primary owner)
- `orchestration` → `Orchestration`:
  - `workflows[]` → `WorkflowGraph[]`:
    - `workflowId`, `name`, `status`
    - `nodes[]` → `WorkflowNode[]` (discriminated: GenerationNode, ApprovalNode, TransformNode, RenderNode, ValidationNode, NotificationNode, CustomWorkflowNode)
    - `edges[]` → `WorkflowEdge[]` (with conditional expressions)
- `dependencies[]` → `DependencyEdge[]`:
  - `fromRef`, `toRef`, `dependencyType` (requires|blocks|derives_from|supersedes|references|syncs_with)
- `relationships[]` → `Relationship[]`
- `package.budget` → `Budget` (cost tracking across all skills)
- `team` → `Team` (if configured)
- Entity lifecycle state transitions on all entities
- `VersionInfo` management (branching, supersession, derivation)
- Content hash computation for published entities

### Reads
- All schema state (monitors everything)
- Skill status reports
- QA gate results (from S21)
- Cost reports (from S14 and other generative skills)

## Preconditions

- S01 has initialized the schema instance (minimum)

## Procedure

### Step 1: Build the pipeline DAG

Create a `WorkflowGraph` representing the full pipeline:

```
Nodes (one per skill):
  S01 → S02 → S03 → [S04, S05, S06] (parallel)
  [S03, S04, S05] → S07 → [S08, S10, S11, S13] (fan-out)
  S08 → S09
  [S04, S05, S06] → S13 → S14 (with S15, S16 loop)
  S03 → S12
  [S14, S10, S11, S12] → S17 → [S18, S19] (parallel)
  [S18, S19] → S20 → S21 → S22
  S02 → S23 (parallel side-chain)

Edges:
  Typed as "requires" (hard dependency) or "references" (soft, can start early)
  Conditional edges: "S14 → S17 only when S16 consistency passes"
```

### Step 2: Validate DAG acyclicity (Rule 14)

Run topological sort on the workflow graph.
If a cycle is detected → error, restructure dependencies.

### Step 3: Execute pipeline

For each tier (topological order):
1. Check preconditions for all unblocked skills
2. Execute parallelizable skills concurrently
3. Collect outputs and update schema state
4. Run validation (S16/S21) where required
5. Gate progression based on QA results
6. Track costs in `package.budget`

### Step 4: Manage entity lifecycle

Track state transitions for every entity:
```
draft → in_progress → generating → review → approved → published
```

Enforce rules:
- Published entities are immutable (`versioningPolicy.immutablePublishedVersions`)
- Content hashes required for published entities
- Supersession chain maintained for versioned updates

### Step 5: Handle failures

- Skill failure → check `RetryConfig`, attempt retry with backoff
- Persistent failure → notify via `NotificationNode`, escalate to user
- Budget exhaustion → pause pipeline, report cost status

### Step 6: Resolve EntityRefs

When skills reference other entities via `EntityRef`:
- `mode: "exact"` → direct ID lookup
- `mode: "latestApproved"` → find latest entity with `approval.status: "approved"`
- `mode: "latestPublished"` → find latest with `version.state: "published"`
- `mode: "semverRange"` → resolve against version numbers

### Step 7: Track costs

Aggregate `GenerationCost` from all generative skills:
```
budget: {
  currency: "USD",
  totalAmount: allocated budget,
  spentAmount: sum of all costActual amounts,
  breakdown: {
    "video_generation": sum from S14,
    "audio_generation": sum from S10+S11+S12,
    "image_generation": sum from S13
  }
}
```

### Step 8: Enforce governance

- Naming conventions applied to all generated IDs
- Approval chains enforced for deliverables
- Compliance classifications maintained
- Rights and license tracking on all assets

### Step 9: Pipeline completion

When all skills have completed and QA passes:
1. Set all entity states to "approved" or "published"
2. Compute content hashes for published entities
3. Set `package.updatedAt` to current timestamp
4. Validate complete schema instance against JSON Schema
5. Report final status, cost summary, and quality metrics

## Output Contract

- `orchestration.workflows[]` has ≥1 workflow with all skill nodes
- `dependencies[]` captures all inter-skill dependencies
- All entity version states are consistent
- `budget` reflects actual costs
- Final schema instance validates against `unified-video-project-v3.schema.json`
- DAG is acyclic (topological sort succeeds)
- All required top-level properties are populated

## Dependency Graph Summary

```
Tier 1: S01 → S02 → S03
Tier 2: S03 → [S04 ∥ S05 ∥ S06]
Tier 3: [S03,S04,S05] → S07 → S08
Tier 4: [S08,S04-S06] → S09
Tier 5: S07 → [S10 ∥ S11], S03+S04 → S12
Tier 6: [S04-S07] → S13 → S14 ⟲ S16
Tier 7: S15 feeds S13,S14 (cross-cutting)
Tier 8: [S14,S10-S12] → S17 → [S18 ∥ S19] → S20
Tier 9: S20 → S21
Tier 10: S21 → S22, S02 → S23
```

## Iteration Rules

The orchestrator runs continuously throughout the pipeline.
It re-evaluates after every skill completion or failure event.
