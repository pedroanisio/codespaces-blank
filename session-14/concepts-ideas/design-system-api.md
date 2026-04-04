---
title: "Design System API — Interface Design (PALS's Law Compliant)"
date: 2026-04-04
type: api-design
status: draft
pals_law_version: 1.5.4
schema_version: 2.1.0
disclaimer: >
  **DISCLAIMER**: No information within this document should be taken for
  granted. Any statement or premise not backed by a real logical definition
  or verifiable reference may be invalid, erroneous, or a hallucination.
  Design decisions reference the companion research document
  (api-design-research.md), the v2.1 design system schema
  (design-system-schema.ts), and PALS's Law v1.5.4. All three are
  approximations — not authoritative sources. The API design herein has
  not been implemented or validated against production traffic.
---

# Design System API — Interface Design

```
ARCHITECTURAL CONTRACT — PALS's LAW

Principle authored by: Pedro Anisio de Luna e Silva
PALS_LAW_VERSION: 1.5.4

INVARIANT (operative form):
  E[ε(M(x), x)] ≥ δ > 0

Every pipeline, agent, or workflow that accepts LLM output MUST treat
that output as untrusted, incomplete, and unverified by default.
Verification is not optional post-processing — it is a first-class
design concern.

This API consumes input from LLM-backed tools (design plugins, code
generators, AI agents). PALS's Law compliance is therefore not
optional — it is a structural requirement.
```

---

## 1. Domain Analysis

*(Unchanged from v1 of this document — see original for the full
decision framework analysis. Summary: hybrid GraphQL + REST, batch-first
mutations, Stripe-style conventions.)*

### 1.1 PALS's Law Implications for API Design

The design system API has two LLM-adjacent attack surfaces:

1. **Write path**: AI agents, Figma plugins with LLM backends, and
   code generators call mutations that ingest LLM-generated payloads
   into the design system state.
2. **Derivation path**: The `/resolved` endpoint and `resolveToken`
   query serve data downstream to CI/CD and code generators. If the
   underlying data was LLM-sourced and unverified, the API launders
   unverified output into trusted infrastructure.

PALS's Law requires that both surfaces have declared, auditable
verification boundaries. The following sections describe how this is
implemented.

---

## 2. PALS's Law Verification Architecture

### 2.1 Design Principles

The verification layer follows five constraints derived directly from
PALS's Law corollaries:

1. **No silent acceptance** (Corollary 4): Every mutation response
   includes a `VerificationBoundary` declaring which of the 9 error
   classes were checked and which are accepted risks.
2. **No trust accumulation** (Corollary 2): The verification audit log
   is append-only. Past success never reduces future verification
   requirements.
3. **Scope matches taxonomy** (Corollary 3): The boundary contains
   exactly 9 entries — one per PALS's Law error class. Omitting a
   class is a type error.
4. **Source provenance** (Corollary 5): Every mutation carries a
   `MutationSource` declaring who/what produced the data. LLM-sourced
   mutations require a `modelVersion` and trigger elevated verification.
5. **Publish gates** (Corollary 4 extended): Snapshot creation requires
   a `SnapshotVerificationDeclaration` — the publisher must state
   what was verified before the snapshot enters the deployment pipeline.

### 2.2 Verification Flow

```
Mutation arrives
      │
      ▼
┌──────────────┐     Missing?     ┌─────────────────────┐
│ DS-Source-Type│────────────────▶ │ 400: source metadata │
│ header check │                  │     required         │
└──────┬───────┘                  └─────────────────────┘
       │ Present
       ▼
┌──────────────┐
│ Schema       │──── ERR_SCHEMA, ERR_TRUNCATION
│ validation   │     (Zod runtime validation)
└──────┬───────┘
       │ Pass
       ▼
┌──────────────┐     sourceType    ┌──────────────────────┐
│ Source type   │─── = "llm" ─────▶│ Run ALL semantic     │
│ routing      │                   │ checks (elevated)    │
└──────┬───────┘                   └──────────┬───────────┘
       │ other                                │
       ▼                                      ▼
┌──────────────┐                   ┌──────────────────────┐
│ Run enabled  │                   │ Run full suite:      │
│ semantic     │                   │ 13 domain checks     │
│ checks only  │                   │ + completeness       │
└──────┬───────┘                   └──────────┬───────────┘
       │                                      │
       ▼                                      ▼
┌──────────────────────────────────────────────────────────┐
│              Build VerificationBoundary                   │
│  • 9 entries (one per PALS error class)                   │
│  • Each: passed / failed / skipped / not_applicable       │
│  • Aggregate: passed = (no class failed)                  │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                  Apply policy                             │
│  • enforce: reject if !boundary.passed (HTTP 422)         │
│  • warn:    proceed, include boundary in response         │
│  • audit:   proceed, boundary only in audit log           │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│          Append VerificationAuditEntry                    │
│  (immutable, always, regardless of policy)                │
└──────────────────────────────────────────────────────────┘
```

### 2.3 The 13 Semantic Checks

These domain-specific checks cover error classes that schema validation
cannot reach:

| Check | Detects | PALS Class |
|-------|---------|------------|
| `dangling_reference` | FK points to non-existent entity | ERR_HALLUCINATION |
| `nonexistent_css_variable` | variableName not in known set | ERR_HALLUCINATION |
| `unreachable_component` | type referenced but not in manifest | ERR_HALLUCINATION |
| `hsl_range_sanity` | lightness >80% in dark theme token | ERR_SEMANTIC |
| `contrast_ratio_minimum` | WCAG AA failure between fg/bg | ERR_SEMANTIC |
| `duplicate_variable_name` | two tokens, same CSS variable | ERR_SEMANTIC |
| `circular_resolution` | resolution rules creating loops | ERR_REASONING |
| `contradictory_adaptations` | conflicting responsive rules | ERR_REASONING |
| `slot_type_mismatch` | slot references undefined types | ERR_REASONING |
| `unreachable_state` | interaction state with no path in | ERR_REASONING |
| `incomplete_theme_coverage` | theme missing token overrides | ERR_OMISSION |
| `missing_required_slot` | required slot with no default | ERR_OMISSION |
| `orphaned_resolution_rule` | rule targets non-existent entity | ERR_OMISSION |

### 2.4 Error Class Coverage Map

After verification runs, the boundary maps error classes to coverage:

| Error Class | How Covered | Check Type |
|---|---|---|
| ERR_SCHEMA | Zod runtime validation | Automatic |
| ERR_TRUNCATION | Required fields, `.min(1)` arrays | Automatic |
| ERR_HALLUCINATION | 3 semantic checks | Semantic |
| ERR_SEMANTIC | 3 semantic checks | Semantic |
| ERR_REASONING | 4 semantic checks | Semantic |
| ERR_OMISSION | 3 semantic checks + completeness | Semantic + Custom |
| ERR_INSTRUCTION | Not applicable (no prompt contract) | Skipped |
| ERR_SYCOPHANCY | Not applicable (API has no preference signal) | Skipped |
| ERR_CALIBRATION | Not applicable (API has no confidence signal) | Skipped |

7 of 9 classes are actively checked. 2 are structurally not applicable
to API input (they concern the model's internal behavior, not the data
it produces). The boundary explicitly marks these as `not_applicable`
rather than silently omitting them — Corollary 3 compliance.

---

## 3. Identity and Object Conventions

### 3.1 Prefixed IDs

*(Same as v1 — see original document. All entities get type-prefixed,
K-Sortable IDs.)*

New prefix additions for verification entities:

| Entity                         | Prefix   | Example                |
|--------------------------------|----------|------------------------|
| VerificationAuditEntry         | `vae_`   | `vae_3kMo5qSu7wYa`    |
| CompletenessAssertion          | `cpa_`   | `cpa_1bDf3hJl5nPr`    |
| SnapshotVerificationDeclaration| `svd_`   | `svd_8tVx0yBd2fGh`    |

### 3.2 Consistent Object Envelope

*(Same as v1, plus verification metadata on mutation responses.)*

Every mutation response now includes:

```jsonc
{
  "id": "ct_8fGh3jKl0pQr",
  "object": "color_token",
  "created_at": "2026-04-04T12:00:00Z",
  "updated_at": "2026-04-04T14:30:00Z",
  "design_system_id": "ds_2bXk9mQz4nRp",
  // ... entity-specific fields ...

  // PALS's Law verification boundary (always present on mutations)
  "_verification": {
    "pals_law_version": "1.5.4",
    "verified_at": "2026-04-04T14:30:00.123Z",
    "source": {
      "source_type": "llm",
      "model_version": "claude-sonnet-4.6",
      "actor": "figma-plugin-v3"
    },
    "passed": true,
    "summary": {
      "classes_checked": 7,
      "classes_passed": 7,
      "classes_failed": 0,
      "classes_skipped": 0,
      "total_findings": 0
    },
    "checks": [
      { "error_class": "ERR_SCHEMA",         "status": "passed",         "findings": [] },
      { "error_class": "ERR_TRUNCATION",      "status": "passed",         "findings": [] },
      { "error_class": "ERR_HALLUCINATION",   "status": "passed",         "findings": [] },
      { "error_class": "ERR_OMISSION",        "status": "passed",         "findings": [] },
      { "error_class": "ERR_SEMANTIC",         "status": "passed",         "findings": [] },
      { "error_class": "ERR_REASONING",        "status": "passed",         "findings": [] },
      { "error_class": "ERR_INSTRUCTION",      "status": "not_applicable", "findings": [] },
      { "error_class": "ERR_SYCOPHANCY",       "status": "not_applicable", "findings": [] },
      { "error_class": "ERR_CALIBRATION",      "status": "not_applicable", "findings": [] }
    ]
  }
}
```

### 3.3 Metadata Field

*(Same as v1 — arbitrary key-value store on every entity.)*

---

## 4. Required Headers

### 4.1 Source Metadata Header

**Every mutation** must carry source provenance:

```http
DS-Source-Type: llm
DS-Model-Version: claude-sonnet-4.6
DS-Actor: figma-plugin-v3
```

| Header | Required | Values | Notes |
|--------|----------|--------|-------|
| `DS-Source-Type` | Yes (configurable) | `human`, `llm`, `automated`, `unknown` | Corollary 5 compliance |
| `DS-Model-Version` | When `DS-Source-Type: llm` | Model identifier string | PALS's Law §8.5 |
| `DS-Actor` | No | Free-form string | Audit trail correlation |

If `DS-Source-Type` is `llm` and `DS-Model-Version` is missing, the API
returns `400` with error type `pals_source_metadata_incomplete`:

```jsonc
{
  "type": "https://api.designsystem.dev/errors/pals-source-metadata-incomplete",
  "title": "PALS's Law: model version required for LLM sources",
  "status": 400,
  "detail": "DS-Source-Type is 'llm' but DS-Model-Version header is missing. PALS's Law Corollary 5 requires model version tracking for LLM-sourced mutations.",
  "param": "DS-Model-Version"
}
```

### 4.2 Other Headers

*(Idempotency-Key, DS-API-Version, Authorization — same as v1.)*

---

## 5. GraphQL Interface

### 5.1 Root Operations

```graphql
type Query {
  # ── Core queries (unchanged from v1) ──
  designSystem(id: ID!): DesignSystem
  designSystems(first: Int, after: String, filter: DesignSystemFilter): DesignSystemConnection!
  resolveToken(
    designSystemId: ID!
    componentType: ComponentTypeName!
    property: String!
    conditions: TokenResolutionConditions
  ): ResolvedToken
  snapshot(id: ID!): DesignSystemSnapshot
  diffSnapshots(baseId: ID!, headId: ID!): SnapshotDiff!
  componentManifest(designSystemId: ID!): ComponentManifest!

  # ── PALS's Law verification queries [NEW] ──

  """
  Run verification checks against the current design system state
  without mutating anything. Returns a full VerificationBoundary.
  Use this for CI gates and pre-publish validation.
  """
  verifyDesignSystem(
    designSystemId: ID!
    """Override which semantic checks to run (default: all enabled in config)."""
    checks: [SemanticCheckKind!]
  ): VerificationReport!

  """
  Run completeness assertions and return what's missing.
  """
  checkCompleteness(
    designSystemId: ID!
    assertions: [CompletenessAssertionInput!]
  ): [CompletenessResult!]!

  """
  Query the verification audit log for a design system.
  """
  verificationAuditLog(
    designSystemId: ID!
    first: Int
    after: String
    filter: AuditLogFilter
  ): VerificationAuditConnection!
}

type Mutation {
  # ── Design System lifecycle ──
  createDesignSystem(input: CreateDesignSystemInput!): DesignSystemPayload!
  updateDesignSystem(id: ID!, input: UpdateDesignSystemInput!): DesignSystemPayload!
  deleteDesignSystem(id: ID!): DeletePayload!

  # ── Token operations (batch-first) ──
  upsertTokens(designSystemId: ID!, tokens: [TokenInput!]!): TokenBatchPayload!
  deleteTokens(designSystemId: ID!, ids: [ID!]!): DeleteBatchPayload!

  # ── Theme operations ──
  upsertTheme(designSystemId: ID!, input: ThemeInput!): ThemePayload!
  deleteTheme(id: ID!): DeletePayload!

  # ── Component operations ──
  upsertComponent(designSystemId: ID!, input: ComponentInput!): ComponentPayload!
  deleteComponent(id: ID!): DeletePayload!

  # ── Resolution & adaptation rules ──
  upsertTokenResolutions(designSystemId: ID!, rules: [TokenResolutionRuleInput!]!): TokenResolutionBatchPayload!
  upsertResponsiveAdaptations(designSystemId: ID!, adaptations: [ResponsiveAdaptationInput!]!): ResponsiveAdaptationBatchPayload!

  # ── Snapshot (PALS-compliant) ──

  """
  Create an immutable snapshot. REQUIRES a verification declaration.
  Snapshots without a verification declaration are rejected (HTTP 422)
  when snapshotPolicy = "enforce".

  PALS's Law §8.4: Snapshots are what downstream consumers deploy
  against. Publishing without a verification declaration is the exact
  architectural omission Corollary 4 describes.
  """
  createSnapshot(
    designSystemId: ID!
    input: CreateSnapshotInput!
    """REQUIRED. Declares the verification status of this snapshot."""
    verification: SnapshotVerificationDeclarationInput!
  ): SnapshotPayload!

  # ── Atomic batch ──
  applyBatch(designSystemId: ID!, operations: [BatchOperation!]!): BatchPayload!

  # ── PALS's Law configuration [NEW] ──

  """Update the verification configuration for a design system."""
  updateVerificationConfig(
    designSystemId: ID!
    config: VerificationConfigInput!
  ): VerificationConfigPayload!

  """
  Add or update a completeness assertion. These run automatically
  on snapshot creation and can be triggered manually.
  """
  upsertCompletenessAssertion(
    designSystemId: ID!
    assertion: CompletenessAssertionInput!
  ): CompletenessAssertionPayload!
}

type Subscription {
  designSystemChanged(id: ID!): DesignSystemChangeEvent!
  """
  Subscribe to verification events. Useful for dashboards monitoring
  verification health across design systems.
  """
  verificationCompleted(designSystemId: ID!): VerificationAuditEntry!
}
```

### 5.2 Verification Types (GraphQL SDL)

```graphql
# ── PALS's Law error taxonomy ──

enum PALSErrorClass {
  ERR_HALLUCINATION
  ERR_OMISSION
  ERR_SCHEMA
  ERR_TRUNCATION
  ERR_SYCOPHANCY
  ERR_INSTRUCTION
  ERR_CALIBRATION
  ERR_SEMANTIC
  ERR_REASONING
}

enum VerificationCheckStatus {
  PASSED
  FAILED
  SKIPPED
  NOT_APPLICABLE
}

enum MutationSourceType {
  HUMAN
  LLM
  AUTOMATED
  UNKNOWN
}

enum VerificationPolicy {
  ENFORCE
  WARN
  AUDIT
  DISABLED
}

enum SnapshotVerificationStatus {
  FULLY_VERIFIED
  PARTIALLY_VERIFIED
  UNVERIFIED
  VERIFIED_WITH_ACCEPTED_RISKS
}

enum SemanticCheckKind {
  DANGLING_REFERENCE
  NONEXISTENT_CSS_VARIABLE
  UNREACHABLE_COMPONENT
  HSL_RANGE_SANITY
  CONTRAST_RATIO_MINIMUM
  DUPLICATE_VARIABLE_NAME
  CIRCULAR_RESOLUTION
  CONTRADICTORY_ADAPTATIONS
  SLOT_TYPE_MISMATCH
  UNREACHABLE_STATE
  INCOMPLETE_THEME_COVERAGE
  MISSING_REQUIRED_SLOT
  ORPHANED_RESOLUTION_RULE
}

# ── Source provenance ──

type MutationSource {
  sourceType: MutationSourceType!
  modelVersion: String
  apiKeyPrefix: String
  actor: String
}

# ── Verification boundary (on every mutation response) ──

type VerificationBoundary {
  palsLawVersion: String!
  verifiedAt: DateTime!
  source: MutationSource!
  checks: [VerificationCheckResult!]!
  passed: Boolean!
  summary: VerificationSummary!
}

type VerificationCheckResult {
  errorClass: PALSErrorClass!
  status: VerificationCheckStatus!
  skipRationale: String
  findings: [VerificationFinding!]!
}

type VerificationFinding {
  severity: FindingSeverity!
  errorClass: PALSErrorClass!
  message: String!
  path: String
  entityId: ID
}

enum FindingSeverity { ERROR WARNING INFO }

type VerificationSummary {
  classesChecked: Int!
  classesPassed: Int!
  classesFailed: Int!
  classesSkipped: Int!
  totalFindings: Int!
}

# ── Verification report (from verifyDesignSystem query) ──

type VerificationReport {
  designSystemId: ID!
  boundary: VerificationBoundary!
  semanticChecks: [SemanticCheckResult!]!
  completenessResults: [CompletenessResult!]!
  """
  Overall health score: fraction of applicable classes that passed.
  E.g., 7 applicable, 6 passed → 0.857
  """
  healthScore: Float!
}

type SemanticCheckResult {
  kind: SemanticCheckKind!
  coversErrorClass: PALSErrorClass!
  passed: Boolean!
  findings: [VerificationFinding!]!
}

# ── Completeness ──

type CompletenessResult {
  assertionId: ID!
  description: String!
  passed: Boolean!
  missing: [MissingItem!]!
}

type MissingItem {
  category: String!
  expected: String!
  description: String
}

input CompletenessAssertionInput {
  description: String!
  expectedColorRoles: [ColorRole!]
  expectedColorScales: [String!]
  expectedComponentTypes: [ComponentTypeName!]
  expectedBreakpoints: [String!]
  expectedThemeModes: [ThemeMode!]
}

# ── Snapshot verification declaration ──

input SnapshotVerificationDeclarationInput {
  """
  Must accurately reflect the verification state. Misrepresenting
  status is an integrity violation (but cannot be enforced by the
  API — it is a process discipline).
  """
  status: SnapshotVerificationStatus!
  """
  The verification boundary at snapshot time. If a
  verifyDesignSystem query was run immediately before, pass its
  boundary here.
  """
  boundary: VerificationBoundaryInput!
  acceptedRisks: [AcceptedRiskInput!]
}

input AcceptedRiskInput {
  errorClass: PALSErrorClass!
  rationale: String!
}

input VerificationBoundaryInput {
  checks: [VerificationCheckResultInput!]!
}

input VerificationCheckResultInput {
  errorClass: PALSErrorClass!
  status: VerificationCheckStatus!
  skipRationale: String
}

# ── Audit log ──

type VerificationAuditEntry {
  id: ID!
  trigger: AuditTrigger!
  operationId: String
  boundary: VerificationBoundary!
  semanticChecks: [SemanticCheckResult!]!
  completenessResults: [CompletenessResult!]!
  timestamp: DateTime!
}

enum AuditTrigger {
  MUTATION
  SNAPSHOT_CREATION
  MANUAL_RUN
  SCHEDULED
}

type VerificationAuditConnection {
  edges: [VerificationAuditEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type VerificationAuditEdge {
  node: VerificationAuditEntry!
  cursor: String!
}

input AuditLogFilter {
  """Filter by trigger type."""
  trigger: AuditTrigger
  """Only entries where at least one check failed."""
  failedOnly: Boolean
  """Only entries from a specific source type."""
  sourceType: MutationSourceType
  """Time range."""
  after: DateTime
  before: DateTime
}

# ── Configuration ──

type VerificationConfig {
  palsLawVersion: String!
  mutationPolicy: VerificationPolicy!
  snapshotPolicy: VerificationPolicy!
  enabledSemanticChecks: [SemanticCheckKind!]!
  requireSourceMetadata: Boolean!
  elevatedLLMVerification: Boolean!
}

input VerificationConfigInput {
  mutationPolicy: VerificationPolicy
  snapshotPolicy: VerificationPolicy
  enabledSemanticChecks: [SemanticCheckKind!]
  requireSourceMetadata: Boolean
  elevatedLLMVerification: Boolean
}
```

### 5.3 All Mutation Payloads Include Verification

Every mutation payload type follows this pattern:

```graphql
type TokenBatchPayload {
  tokens: [Token!]!
  """
  PALS's Law verification boundary for this mutation.
  Always present. Inspect this to know what was checked.
  """
  verification: VerificationBoundary!
}

type SnapshotPayload {
  snapshot: DesignSystemSnapshot!
  verification: VerificationBoundary!
  """
  The declaration the publisher provided at creation time.
  """
  snapshotVerification: SnapshotVerificationDeclaration!
}

type BatchPayload {
  success: Boolean!
  operationsApplied: Int!
  results: [BatchOperationResult!]!
  errors: [BatchOperationError!]
  """Single boundary covering all operations in the batch."""
  verification: VerificationBoundary!
}
```

---

## 6. REST Interface

### 6.1 Resource Endpoints

*(Core CRUD endpoints unchanged from v1.)*

New verification endpoints:

```
# ── Verification ──
GET    /v1/design-systems/:id/verify                # Run verification checks
POST   /v1/design-systems/:id/verify                # Run with custom check config
GET    /v1/design-systems/:id/completeness           # Run completeness assertions
GET    /v1/design-systems/:id/verification-audit     # Query audit log
GET    /v1/design-systems/:id/verification-config    # Read config
PATCH  /v1/design-systems/:id/verification-config    # Update config

# ── Completeness assertions ──
GET    /v1/design-systems/:id/completeness-assertions
POST   /v1/design-systems/:id/completeness-assertions
DELETE /v1/design-systems/:id/completeness-assertions/:assertionId
```

### 6.2 Source Metadata on All Mutations

Every `POST`, `PATCH`, and `DELETE` against entity endpoints must
include the `DS-Source-Type` header. Example:

```http
POST /v1/design-systems/ds_2bXk9mQz4nRp/tokens
DS-Source-Type: llm
DS-Model-Version: claude-sonnet-4.6
DS-Actor: figma-plugin-v3
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "type": "color_token",
  "variable_name": "--bg-400",
  "role": "bg",
  "scale": "400",
  "hsl_channels": "45, 20%, 88%"
}
```

Response always includes `_verification`:

```jsonc
// 201 Created
{
  "id": "ct_9xYz1aBc3dEf",
  "object": "color_token",
  // ... fields ...
  "_verification": {
    "pals_law_version": "1.5.4",
    "verified_at": "2026-04-04T14:30:00.123Z",
    "passed": false,
    "source": {
      "source_type": "llm",
      "model_version": "claude-sonnet-4.6",
      "actor": "figma-plugin-v3"
    },
    "summary": {
      "classes_checked": 7,
      "classes_passed": 6,
      "classes_failed": 1,
      "classes_skipped": 0,
      "total_findings": 1
    },
    "checks": [
      // ... 9 entries ...
      {
        "error_class": "ERR_SEMANTIC",
        "status": "failed",
        "findings": [
          {
            "severity": "warning",
            "error_class": "ERR_SEMANTIC",
            "message": "HSL lightness 88% is suspiciously high for a 'bg' role token. Dark-mode bg tokens typically have lightness < 30%.",
            "path": "hsl_channels",
            "entity_id": "ct_9xYz1aBc3dEf"
          }
        ]
      }
    ]
  }
}
```

When `mutationPolicy = "enforce"` and verification fails:

```jsonc
// 422 Unprocessable Entity
{
  "type": "https://api.designsystem.dev/errors/verification-failed",
  "title": "PALS's Law verification failed",
  "status": 422,
  "detail": "1 of 7 applicable error classes failed verification. Policy is 'enforce'; mutation rejected.",
  "request_id": "req_7xYz9aBc1dEf",
  "_verification": {
    // ... full boundary, same structure as above ...
  }
}
```

### 6.3 Snapshot Creation Requires Verification Declaration

```http
POST /v1/design-systems/ds_2bXk9mQz4nRp/snapshots
DS-Source-Type: human
Content-Type: application/json

{
  "version": "2.1.0",
  "label": "Q2 rebrand — dark mode refinement",
  "verification_declaration": {
    "status": "verified_with_accepted_risks",
    "boundary": {
      "checks": [
        { "error_class": "ERR_SCHEMA",        "status": "passed" },
        { "error_class": "ERR_TRUNCATION",     "status": "passed" },
        { "error_class": "ERR_HALLUCINATION",  "status": "passed" },
        { "error_class": "ERR_OMISSION",       "status": "passed" },
        { "error_class": "ERR_SEMANTIC",        "status": "passed" },
        { "error_class": "ERR_REASONING",       "status": "passed" },
        { "error_class": "ERR_INSTRUCTION",     "status": "not_applicable" },
        { "error_class": "ERR_SYCOPHANCY",      "status": "not_applicable" },
        { "error_class": "ERR_CALIBRATION",     "status": "skipped",
          "skip_rationale": "No confidence signals in design token data" }
      ]
    },
    "accepted_risks": [
      {
        "error_class": "ERR_CALIBRATION",
        "rationale": "Design tokens carry no confidence metadata; class is structurally inapplicable."
      }
    ]
  }
}
```

A snapshot creation request missing `verification_declaration` returns
`422` when `snapshotPolicy = "enforce"`.

---

## 7. Error Design

*(RFC 9457 format — same as v1, with new PALS-specific error types.)*

### 7.1 New Error Types

| HTTP | Error Type | When |
|------|------------|------|
| 400 | `pals_source_metadata_incomplete` | `DS-Source-Type: llm` without `DS-Model-Version` |
| 400 | `pals_source_metadata_missing` | Mutation without `DS-Source-Type` when `requireSourceMetadata = true` |
| 422 | `pals_verification_failed` | Verification check failed and policy is `enforce` |
| 422 | `pals_snapshot_declaration_missing` | Snapshot creation without verification declaration |
| 422 | `pals_snapshot_declaration_invalid` | Declaration claims `fully_verified` but boundary has failures |

---

## 8. Authentication, Idempotency, Versioning, Rate Limiting

*(Unchanged from v1 — see original document for: API keys with
live/test split, OAuth 2.0 with PKCE, scoped permissions,
idempotency keys, date-based header versioning, tiered rate limits.)*

New permission scopes for verification:

```
verification:read     verification:write
audit:read
completeness:read     completeness:write
```

---

## 9. SDK Design (TypeScript)

### 9.1 Source Metadata — Built Into the Client

```typescript
import { DesignSystemClient } from "@designsystem/sdk";

// Source metadata is set at client initialization and sent
// on every mutation automatically.
const client = new DesignSystemClient({
  apiKey: "dsk_live_...",
  source: {
    sourceType: "llm",
    modelVersion: "claude-sonnet-4.6",
    actor: "my-design-tool-v2",
  },
});

// Can be overridden per-call:
const token = await client.tokens.create("ds_2bXk9mQz4nRp", {
  type: "color_token",
  variableName: "--bg-400",
  role: "bg",
  scale: "400",
  hslChannels: "45, 20%, 12%",
}, {
  source: { sourceType: "human", actor: "pedro@example.com" },
});
```

### 9.2 Verification Boundary on Every Mutation Response

```typescript
const result = await client.tokens.create("ds_2bXk9mQz4nRp", {
  type: "color_token",
  variableName: "--accent-brand",
  role: "accent",
  scale: "brand",
  hslChannels: "30, 80%, 55%",
});

// Verification boundary is always present
console.log(result.verification.passed);           // true
console.log(result.verification.summary);           // { classesChecked: 7, ... }

// Inspect individual check results
for (const check of result.verification.checks) {
  if (check.status === "failed") {
    console.warn(
      `PALS ${check.errorClass}: ${check.findings.length} findings`
    );
    for (const f of check.findings) {
      console.warn(`  [${f.severity}] ${f.message} (at ${f.path})`);
    }
  }
}
```

### 9.3 Pre-Publish Verification

```typescript
// Run full verification before publishing a snapshot
const report = await client.verification.run("ds_2bXk9mQz4nRp");

console.log(`Health score: ${(report.healthScore * 100).toFixed(1)}%`);
console.log(`Semantic checks: ${report.semanticChecks.length}`);
console.log(`Completeness: ${report.completenessResults.length} assertions`);

if (!report.boundary.passed) {
  console.error("Verification failed. Cannot publish.");
  for (const check of report.boundary.checks) {
    if (check.status === "failed") {
      console.error(`  ${check.errorClass}: FAILED`);
    }
  }
  process.exit(1);
}

// Publish with verification declaration
const snapshot = await client.snapshots.create("ds_2bXk9mQz4nRp", {
  version: "2.1.0",
  label: "Q2 rebrand",
  verificationDeclaration: {
    status: "fully_verified",
    boundary: report.boundary,
    acceptedRisks: [],
  },
});
```

### 9.4 Batch Operations with Verification

```typescript
const batch = await client.batch.apply("ds_2bXk9mQz4nRp", [
  {
    type: "UPSERT_TOKEN",
    upsertToken: {
      type: "color_token",
      variableName: "--accent-200",
      role: "accent",
      scale: "200",
      hslChannels: "30, 50%, 60%",
    },
  },
  {
    type: "UPSERT_RESOLUTION",
    upsertResolution: {
      target: {
        componentType: "Button",
        property: "states.rest.bgTokenId",
        variant: "claude",
      },
      conditions: { themeMode: "dark" },
      resolvedTokenId: "ct_8fGh3jKl0pQr",
    },
  },
]);

// Single verification boundary covers the entire batch
if (!batch.verification.passed) {
  console.error("Batch verification failed:");
  for (const f of batch.verification.checks.flatMap(c => c.findings)) {
    console.error(`  [${f.errorClass}] ${f.message}`);
  }
}
```

### 9.5 Audit Log Query

```typescript
// Query verification history — Corollary 2: trust accumulation
// is prohibited, but you can inspect the trail.
for await (const entry of client.verification.auditLog("ds_2bXk9mQz4nRp", {
  failedOnly: true,
  sourceType: "llm",
  after: "2026-04-01T00:00:00Z",
})) {
  console.log(
    `${entry.timestamp} [${entry.trigger}] ` +
    `passed=${entry.boundary.passed} ` +
    `findings=${entry.boundary.summary.totalFindings}`
  );
}
```

### 9.6 Completeness Assertions

```typescript
// Define what the design system SHOULD contain
await client.completeness.upsert("ds_2bXk9mQz4nRp", {
  description: "Core color roles must all exist",
  expectedColorRoles: ["bg", "text", "border", "accent"],
  expectedThemeModes: ["light", "dark"],
});

// Run and check
const results = await client.completeness.check("ds_2bXk9mQz4nRp");
for (const r of results) {
  if (!r.passed) {
    console.warn(`Completeness: ${r.description}`);
    for (const m of r.missing) {
      console.warn(`  Missing ${m.category}: ${m.expected}`);
    }
  }
}
```

---

## 10. Summary: API Surface Map

```
┌─────────────────────────────────────────────────────────┐
│                    Consumers                            │
├──────────┬──────────┬───────────┬──────────┬────────────┤
│  Design  │   Code   │   CI/CD   │   Docs   │    AI      │
│  Tools   │   Gen    │ Validators│  Sites   │  Agents    │
├──────────┴──────────┴───────────┴──────────┴────────────┤
│                  TypeScript SDK                          │
│    (source metadata auto-attached to all mutations)      │
├─────────────────────────┬───────────────────────────────┤
│     GraphQL API         │         REST API              │
│                         │                               │
│  • Fine-grained queries │  • /resolved (CDN-cached)     │
│  • Batch mutations      │  • Snapshot download          │
│  • Subscriptions        │  • Token CRUD                 │
│  • Token resolution     │  • Webhooks                   │
│  • Snapshot diffing     │  • Batch operations           │
│  • verifyDesignSystem   │  • /verify                    │
│  • checkCompleteness    │  • /completeness              │
│  • verificationAuditLog │  • /verification-audit        │
├─────────────────────────┴───────────────────────────────┤
│               PALS's Law Verification Layer             │
│                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ Schema       │ │ Semantic     │ │ Completeness     │ │
│  │ Validation   │ │ Checks (13)  │ │ Assertions       │ │
│  │              │ │              │ │                  │ │
│  │ ERR_SCHEMA   │ │ ERR_HALLUC.  │ │ ERR_OMISSION     │ │
│  │ ERR_TRUNC.   │ │ ERR_SEMANTIC │ │ (custom)         │ │
│  │              │ │ ERR_REASON.  │ │                  │ │
│  │              │ │ ERR_OMISSION │ │                  │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
│                         │                               │
│              ┌──────────┴──────────┐                    │
│              │ VerificationBoundary │                    │
│              │ (9 classes, always)  │                    │
│              └──────────┬──────────┘                    │
│                         │                               │
│              ┌──────────┴──────────┐                    │
│              │ VerificationAudit   │                    │
│              │ (append-only log)   │                    │
│              └─────────────────────┘                    │
├─────────────────────────────────────────────────────────┤
│                   Domain Service                        │
│                                                         │
│  • Token resolution engine                              │
│  • Snapshot manager (immutable versioned artifacts)      │
│  • Batch transaction coordinator                        │
│  • Event bus (change propagation)                       │
├─────────────────────────────────────────────────────────┤
│                    Storage                              │
│                                                         │
│  • Design system state (mutable working copy)           │
│  • Snapshots (immutable, content-addressed)             │
│  • Idempotency key store (TTL: 7 days)                  │
│  • Verification audit log (append-only)                 │
│  • Event log (append-only)                              │
└─────────────────────────────────────────────────────────┘
```

---

## 11. PALS's Law Compliance Matrix

Final compliance assessment against each corollary:

| Corollary | Status | Implementation |
|---|---|---|
| **C1** — Appearance ≠ correctness | **COMPLIANT** | 13 semantic checks go beyond schema validation; `hsl_range_sanity`, `contrast_ratio_minimum`, `dangling_reference` detect semantically-valid-but-wrong data |
| **C2** — Trust accumulation prohibited | **COMPLIANT** | `VerificationAuditEntry` is append-only; `MutationSource` tracks provenance per-call; no mechanism to relax checks based on history |
| **C3** — Scope must match taxonomy | **COMPLIANT** | `VerificationBoundary.checks` has exactly 9 entries; every class is `passed` / `failed` / `skipped` / `not_applicable`; skipped classes require `skipRationale` |
| **C4** — Silent acceptance is a defect | **COMPLIANT** | Every mutation response includes `_verification`; snapshots require `SnapshotVerificationDeclaration`; `VerificationPolicy.enforce` rejects unverified mutations |
| **C5** — Capability growth shifts verification | **COMPLIANT** | `DS-Model-Version` required for LLM sources; `elevatedLLMVerification` triggers full semantic suite for LLM input; audit trail records model version per-mutation |
