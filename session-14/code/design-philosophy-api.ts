/**
 * ============================================================================
 * DISCLAIMER
 * No information within this document should be taken for granted. Any
 * statement or premise not backed by a real logical definition or verifiable
 * reference may be invalid, erroneous, or a hallucination. This API design
 * is a first-principles proposal — not an implementation specification.
 * Design decisions cite the source documents where applicable.
 * ============================================================================
 *
 * Design Philosophy API — Interface Contract
 *
 * PURPOSE:
 *   Define the HTTP API contract for creating, reading, updating, comparing,
 *   and AI-populating Design Philosophy instances. The API serves two consumer
 *   classes simultaneously:
 *     1. Human developers via SDKs or direct HTTP
 *     2. LLM-driven agents via tool-calling and orchestration interfaces
 *        (MCP, function calling, and A2A-style delegation surfaces)
 *
 *   The second class demands verification-first design per PALS's Law §8.4:
 *   "Silent acceptance is an architectural defect." Every mutation surface
 *   must expose enough structure for a fallible model to be checked, bounded,
 *   and audited.
 *
 * SOURCE DOCUMENTS:
 *   - api-design-research.md v1.2 (§1.3, §2.4, §6.2, §8, §9.1)
 *   - PALS_LAW-v1.5.4.pdf (§5 error taxonomy, §8 corollaries, §9 contracts)
 *   - design-philosophy-schema.ts v1.0.0 (the data model this API exposes)
 *
 * ARCHITECTURAL STYLE: REST (Richardson Level 2) with explicit verification
 *   boundaries. GraphQL rejected for initial version: the data model is
 *   resource-oriented with low relationship fan-out, and the primary use case
 *   (side-by-side comparison) benefits from pre-composed response shapes
 *   rather than ad-hoc field selection. See §A.1 for rationale.
 *
 * Schema language: TypeScript
 * API version: v1
 */

// ─────────────────────────────────────────────────────────────────────────────
// §0 — Imports (from the data model)
// ─────────────────────────────────────────────────────────────────────────────

// These types come from design-philosophy-schema.ts
import type {
  DesignPhilosophy,
  Foundation,
  SpatialModel,
  ColorArchitecture,
  TypographySystem,
  MotionPhilosophy,
  ComponentModel,
  AccessibilityModel,
  TokenArchitecture,
  ResponsiveStrategy,
  ShapeAndSurface,
  DesignDecision,
  Rationale,
  ConcreteExample,
} from "../schemas/design-philosophy-schema.js";

// ─────────────────────────────────────────────────────────────────────────────
// §1 — Shared API Primitives
// ─────────────────────────────────────────────────────────────────────────────

/**
 * API version constant. Appears in the URL path prefix: /v1/...
 *
 * Versioning strategy: path-based (§2.5 of api-design-research.md).
 * Rationale: highest discoverability for both human and machine consumers;
 * simplest routing and caching; the dataset is not HATEOAS-driven.
 */
export const API_VERSION = "v1" as const;

/**
 * Prefixed identifiers à la Stripe (§6.1 of api-design-research.md):
 * "Instant identification of object type from any ID, preventing
 * cross-type confusion and aiding debugging."
 *
 * Pattern: <prefix>_<uuid>
 */
export type PrefixedId<Prefix extends string> = `${Prefix}_${string}`;

export type PhilosophyId = PrefixedId<"dph">;
export type DecisionId = PrefixedId<"ddc">;
export type ComparisonId = PrefixedId<"cmp">;
export type OperationId = PrefixedId<"op">;

/**
 * Every API response includes a standard envelope.
 *
 * Design principle (§6.1): "Every resource includes id, object (type name),
 * created, livemode, and metadata."
 */
interface ApiResourceBase {
  /** Prefixed opaque identifier. */
  id: string;
  /** Type discriminator — the API resource kind. */
  object: string;
  /** ISO 8601 creation timestamp (UTC). */
  createdAt: string;
  /** ISO 8601 last-modification timestamp (UTC). */
  updatedAt: string;
  /** Whether this resource exists in test mode (§6.1: Stripe pattern). */
  livemode: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// §2 — Provenance & Verification (PALS's Law Integration)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * PALS's Law §8.4: "Any production system that passes LLM output directly
 * to downstream consumers without a declared verification boundary has an
 * architectural omission."
 *
 * Every field that *can* be populated by an LLM carries provenance metadata.
 * This is not optional annotation — it is a structural requirement of the
 * API contract.
 */

/**
 * Who authored this content.
 *
 * The distinction matters because LLM-generated content triggers
 * verification requirements that human-authored content does not.
 */
export type AuthoringSource =
  | { kind: "human"; actorId: string }
  | { kind: "llm"; modelId: string; modelVersion: string; promptHash: string }
  | { kind: "mixed"; humanActorId: string; modelId: string };

/**
 * Verification status of a piece of content.
 *
 * PALS's Law §8.1: "Appearance of correctness is not correctness."
 * PALS's Law §8.2: "Trust accumulation is prohibited."
 *
 * A field that was verified yesterday against documentation that has since
 * changed is no longer verified. Verification is time-bound and scoped.
 */
export type VerificationStatus =
  | {
      state: "unverified";
    }
  | {
      state: "verified";
      verifiedBy: string;
      verifiedAt: string; // ISO 8601
      /** What evidence the verifier checked. */
      verificationScope: string;
    }
  | {
      state: "contested";
      contestedBy: string;
      contestedAt: string;
      reason: string;
    }
  | {
      state: "stale";
      /** When the upstream source was last known to match. */
      lastKnownValidAt: string;
    };

/**
 * Provenance wrapper — attaches authoring and verification metadata
 * to any content field.
 *
 * This wrapper applies at the *dimension* level, not the individual field
 * level, because verification is operationally performed per-dimension
 * (a reviewer checks "color architecture" as a unit, not individual enum
 * values within it).
 */
export interface Provenance {
  source: AuthoringSource;
  verification: VerificationStatus;
}

/**
 * A dimension with provenance tracking.
 *
 * Every dimension on a DesignPhilosophy resource carries this wrapper
 * in the API representation (even though the data model itself does not —
 * provenance is an API-layer concern, not a domain-model concern).
 */
export interface ProvenancedDimension<T> {
  data: T;
  provenance: Provenance;
}

// ─────────────────────────────────────────────────────────────────────────────
// §3 — Error Model
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Error response structure — RFC 9457 (Problem Details for HTTP APIs)
 * extended with machine-actionable recovery semantics.
 *
 * api-design-research.md §6.2: "the error model should tell the caller
 * whether the failure is retryable, whether the request was applied,
 * whether user confirmation is required, and whether the state should
 * be re-fetched before a follow-up action."
 */
export interface ApiError {
  /** RFC 9457: URI identifying the error type. */
  type: string;
  /** RFC 9457: short human-readable summary. */
  title: string;
  /** RFC 9457: HTTP status code. */
  status: number;
  /** RFC 9457: human-readable explanation. */
  detail: string;
  /** RFC 9457: URI identifying the specific occurrence. */
  instance: string;

  // ── Extensions beyond RFC 9457 ──

  /** Machine-readable error code for programmatic handling. */
  code: ApiErrorCode;
  /** Which request parameter or field caused the error, if applicable. */
  field?: string;
  /** Request ID for audit trail correlation. */
  requestId: string;

  /**
   * Recovery semantics — the critical extension for AI-heavy systems,
   * agentic AI workflows, and AI-agent consumers.
   * api-design-research.md §6.2: "explicit recovery semantics"
   */
  recovery: RecoverySemantic;
}

/**
 * Machine-readable error codes.
 *
 * api-design-research.md §6.2: "Include a machine-readable error type
 * or code." These are partitioned by the operational taxonomy from §6.2.
 */
export type ApiErrorCode =
  // ── Validation failures ──
  | "validation_error"
  | "schema_violation"
  | "invalid_dimension"
  | "invalid_enum_value"
  | "missing_required_field"
  // ── Auth failures ──
  | "authentication_required"
  | "insufficient_permissions"
  // ── State/conflict failures ──
  | "resource_not_found"
  | "resource_already_exists"
  | "version_conflict"
  | "concurrent_modification"
  // ── Rate limit / transient ──
  | "rate_limited"
  | "service_unavailable"
  | "upstream_timeout"
  // ── LLM-specific (PALS's Law integration) ──
  | "llm_generation_failed"
  | "llm_output_unverifiable"
  | "llm_verification_rejected"
  // ── Internal ──
  | "internal_error";

/**
 * Recovery semantics — what the caller should do next.
 *
 * api-design-research.md §6.2 taxonomy:
 *   - Validation: retry after modification
 *   - Auth: retry after credential/permission change
 *   - Conflict: refresh state before retry
 *   - Rate limit: back off per server guidance
 *   - Internal: cannot assume side effect status
 */
export type RecoverySemantic =
  | { action: "modify_and_retry"; guidance: string }
  | { action: "refresh_credentials" }
  | { action: "refresh_state_and_retry" }
  | { action: "backoff_and_retry"; retryAfterMs: number }
  | { action: "do_not_retry"; reason: string }
  | {
      action: "check_operation_status";
      operationId: OperationId;
      statusEndpoint: string;
    };

// ─────────────────────────────────────────────────────────────────────────────
// §4 — Pagination
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Cursor-based pagination (§2.3 of api-design-research.md):
 * "Cursor-based pagination (keyset pagination) is more robust for
 * datasets that change during traversal."
 */
export interface PaginatedList<T> {
  object: "list";
  data: T[];
  hasMore: boolean;
  /** Opaque cursor — pass as ?cursor= to get the next page. */
  nextCursor: string | null;
  /** Total count, if computable without full scan. Null otherwise. */
  totalCount: number | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// §5 — Resource Representations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The API representation of a DesignPhilosophy.
 *
 * Differs from the domain model in two ways:
 *   1. Each dimension is wrapped in ProvenancedDimension<T>
 *   2. Includes API-layer fields (id, timestamps, livemode)
 *
 * This separation follows the api-design-research.md §3.2 principle:
 * "Design for the consumer, not the storage layer."
 */
export interface DesignPhilosophyResource extends ApiResourceBase {
  object: "design_philosophy";
  id: PhilosophyId;

  // ── Core identity (from domain model) ──
  systemName: string;
  systemVersion: string;
  schemaVersion: string;
  documentationUrl: string;
  capturedAt: string;

  // ── Dimensions with provenance ──
  foundation: ProvenancedDimension<Foundation>;
  spatialModel: ProvenancedDimension<SpatialModel>;
  colorArchitecture: ProvenancedDimension<ColorArchitecture>;
  typographySystem: ProvenancedDimension<TypographySystem>;
  motionPhilosophy: ProvenancedDimension<MotionPhilosophy>;
  componentModel: ProvenancedDimension<ComponentModel>;
  accessibilityModel: ProvenancedDimension<AccessibilityModel>;
  tokenArchitecture: ProvenancedDimension<TokenArchitecture>;
  responsiveStrategy: ProvenancedDimension<ResponsiveStrategy>;
  shapeAndSurface: ProvenancedDimension<ShapeAndSurface>;

  // ── Extension point ──
  designDecisions: DesignDecisionResource[];

  // ── Computed metadata ──
  /** Number of dimensions currently verified. */
  verifiedDimensionCount: number;
  /** Number of dimensions with LLM-generated content. */
  llmGeneratedDimensionCount: number;
}

export interface DesignDecisionResource extends ApiResourceBase {
  object: "design_decision";
  id: DecisionId;
  philosophyId: PhilosophyId;
  data: DesignDecision;
  provenance: Provenance;
}

// ─────────────────────────────────────────────────────────────────────────────
// §6 — Comparison Resource
// ─────────────────────────────────────────────────────────────────────────────

/**
 * The comparison resource — the primary consumer-facing deliverable.
 *
 * A Comparison is a *derived* resource: it does not own the philosophies,
 * it references them (association, not composition).
 *
 * The comparison computes per-dimension deltas and optionally generates
 * an LLM-authored narrative summary. The narrative is explicitly marked
 * as LLM-generated and unverified per PALS's Law §8.1.
 */

/** What the dimension comparison reveals. */
export type DimensionAlignment =
  | "identical"
  | "same_approach_different_parameters"
  | "fundamentally_different"
  | "incomparable"; // one or both dimensions missing

export interface DimensionDelta {
  dimension: DimensionName;
  alignment: DimensionAlignment;
  /** The key differentiating fields within this dimension. */
  differingFields: Array<{
    fieldPath: string;
    values: Record<PhilosophyId, unknown>;
  }>;
  /**
   * LLM-generated interpretive summary of why this difference matters.
   * PALS's Law: this field is ALWAYS { source: { kind: "llm", ... },
   * verification: { state: "unverified" } } on first generation.
   */
  narrativeSummary?: ProvenancedDimension<string>;
}

export interface ComparisonResource extends ApiResourceBase {
  object: "comparison";
  id: ComparisonId;
  /** The philosophies being compared. Min 2, max 6. */
  philosophyIds: PhilosophyId[];
  /**
   * Per-dimension deltas — the structured, machine-readable comparison.
   * One entry per dimension, ordered as in the schema.
   */
  dimensionDeltas: DimensionDelta[];
  /**
   * Overall LLM-generated narrative. Explicitly unverified on creation.
   */
  overallNarrative?: ProvenancedDimension<string>;
}

// ─────────────────────────────────────────────────────────────────────────────
// §7 — Operations (Long-Running)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Long-running operations for LLM-assisted population.
 *
 * api-design-research.md §2.4: "idempotency should be paired with
 * observable write state: a request identifier, a stable operation
 * identifier, and a way to determine whether a write was proposed,
 * accepted, committed, rejected, or only partially applied."
 *
 * LLM population is async because it may take 10–60 seconds. The API
 * returns an Operation resource immediately; the client polls or
 * subscribes for completion.
 */
export type OperationStatus =
  | "proposed" // request received, not yet started
  | "in_progress" // LLM generation underway
  | "awaiting_review" // generation complete, human review required
  | "committed" // accepted and applied to the philosophy
  | "rejected" // review rejected the generated content
  | "failed"; // generation or application failed

export interface OperationResource extends ApiResourceBase {
  object: "operation";
  id: OperationId;
  /** What kind of operation this is. */
  operationType: OperationType;
  status: OperationStatus;
  /** The target resource being modified. */
  targetId: PhilosophyId;
  /** The dimension being populated, if applicable. */
  targetDimension?: DimensionName;
  /** Progress indicator for multi-step operations. */
  progress?: {
    completedSteps: number;
    totalSteps: number;
    currentStepLabel: string;
  };
  /** The generated result, available when status is "awaiting_review". */
  result?: {
    /** The proposed dimension data. */
    proposedData: unknown;
    /** PALS's Law compliance: which error classes this generation is exposed to. */
    palsErrorExposure: PalsErrorExposure;
  };
  /** Error details if status is "failed". */
  error?: ApiError;
  /** ISO 8601 timestamp when status last changed. */
  statusChangedAt: string;
}

export type OperationType =
  | "populate_dimension"
  | "populate_all_dimensions"
  | "generate_comparison"
  | "regenerate_narrative";

/**
 * PALS's Law §8.3: "Verification scope must match error taxonomy."
 *
 * Every LLM-generated artifact declares which PALS error classes it is
 * exposed to and which verifiers (if any) have been applied.
 *
 * This is the API's implementation of the PALS's Law contract block (§9.1).
 */
export interface PalsErrorExposure {
  palsLawVersion: "1.5.4";
  modelVersion: string;
  /**
   * Per the §9.1 contract checklist. true = this error class is covered
   * by a verifier. false = known accepted risk.
   */
  coverage: {
    ERR_HALLUCINATION: boolean;
    ERR_OMISSION: boolean;
    ERR_SCHEMA: boolean;
    ERR_TRUNCATION: boolean;
    ERR_SYCOPHANCY: boolean;
    ERR_INSTRUCTION: boolean;
    ERR_CALIBRATION: boolean;
    ERR_SEMANTIC: boolean;
    ERR_REASONING: boolean;
  };
  /** Free-text note explaining uncovered classes (§9.1: "Leaving all boxes
   * unchecked with no mitigation note is a blocking defect.") */
  mitigationNotes: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// §8 — Dimension Names (Utility Type)
// ─────────────────────────────────────────────────────────────────────────────

export type DimensionName =
  | "foundation"
  | "spatialModel"
  | "colorArchitecture"
  | "typographySystem"
  | "motionPhilosophy"
  | "componentModel"
  | "accessibilityModel"
  | "tokenArchitecture"
  | "responsiveStrategy"
  | "shapeAndSurface";

// ─────────────────────────────────────────────────────────────────────────────
// §9 — Request Types
// ─────────────────────────────────────────────────────────────────────────────

// ── 9.1 Create Philosophy ──

/**
 * POST /v1/philosophies
 *
 * Idempotency: client MUST provide Idempotency-Key header (§2.4).
 * The server stores the key for 24 hours and replays the stored
 * response on duplicate requests.
 */
export interface CreatePhilosophyRequest {
  systemName: string;
  systemVersion: string;
  documentationUrl: string;
  /**
   * Dimensions can be provided at creation time or populated later.
   * Omitted dimensions are null — the resource exists but is incomplete.
   */
  foundation?: Foundation;
  spatialModel?: SpatialModel;
  colorArchitecture?: ColorArchitecture;
  typographySystem?: TypographySystem;
  motionPhilosophy?: MotionPhilosophy;
  componentModel?: ComponentModel;
  accessibilityModel?: AccessibilityModel;
  tokenArchitecture?: TokenArchitecture;
  responsiveStrategy?: ResponsiveStrategy;
  shapeAndSurface?: ShapeAndSurface;
  designDecisions?: DesignDecision[];
}

// ── 9.2 Update a Single Dimension ──

/**
 * PUT /v1/philosophies/{id}/dimensions/{dimensionName}
 *
 * Full replacement of a single dimension. PUT is idempotent by HTTP
 * semantics (§2.3). The request body is the dimension data plus
 * authoring source declaration.
 *
 * Version conflict protection via If-Match header (ETag).
 */
export interface UpdateDimensionRequest<T> {
  data: T;
  source: AuthoringSource;
}

// ── 9.3 AI-Populate a Dimension ──

/**
 * POST /v1/philosophies/{id}/dimensions/{dimensionName}/populate
 *
 * Triggers LLM-assisted population of a dimension from the design
 * system's documentation. Returns an Operation resource.
 *
 * This is the primary LLM interaction surface and therefore the
 * primary PALS's Law verification boundary.
 *
 * Idempotency: requires Idempotency-Key header.
 */
export interface PopulateDimensionRequest {
  /**
   * URLs the LLM should consult when populating this dimension.
   * E.g. the Material Design 3 color page for colorArchitecture.
   */
  sourceUrls: string[];
  /**
   * Optional additional context or constraints for generation.
   */
  instructions?: string;
  /**
   * Whether to auto-commit the result or hold for review.
   * Default: "awaiting_review" (safe default per PALS's Law §8.4).
   *
   * "auto_commit" is only available for dimensions with a structural
   * verifier (ERR_SCHEMA, ERR_OMISSION covered). It is NEVER available
   * for narrative/rationale content (ERR_HALLUCINATION uncovered).
   */
  commitPolicy: "auto_commit" | "awaiting_review";
}

// ── 9.4 Verify a Dimension ──

/**
 * POST /v1/philosophies/{id}/dimensions/{dimensionName}/verify
 *
 * Records that a human has verified the dimension content.
 *
 * PALS's Law §8.2: "Trust accumulation is prohibited." Verification
 * expires — re-verification is required when the upstream design system
 * documentation changes or after a configurable TTL.
 */
export interface VerifyDimensionRequest {
  verifiedBy: string;
  verificationScope: string;
  /**
   * Optional: override the TTL for this verification.
   * Default: 90 days.
   */
  expiresAfterDays?: number;
}

// ── 9.5 Contest a Dimension ──

/**
 * POST /v1/philosophies/{id}/dimensions/{dimensionName}/contest
 *
 * Records that a reviewer disagrees with the current dimension content.
 * Moves verification status to "contested".
 */
export interface ContestDimensionRequest {
  contestedBy: string;
  reason: string;
}

// ── 9.6 Create Comparison ──

/**
 * POST /v1/comparisons
 *
 * Creates a comparison between 2–6 design philosophies.
 * Structural deltas are computed synchronously.
 * Narrative summaries are generated asynchronously (returns Operation).
 *
 * Idempotency: requires Idempotency-Key header.
 */
export interface CreateComparisonRequest {
  philosophyIds: PhilosophyId[];
  /** Whether to generate LLM narrative summaries. Default: true. */
  includeNarratives?: boolean;
  /** Which dimensions to compare. Default: all. */
  dimensions?: DimensionName[];
}

// ── 9.7 Review an Operation ──

/**
 * POST /v1/operations/{id}/review
 *
 * Accepts or rejects an LLM-generated result.
 * Only applicable when operation status is "awaiting_review".
 */
export interface ReviewOperationRequest {
  decision: "accept" | "reject";
  /** Required when rejecting — why the generated content is wrong. */
  rejectionReason?: string;
  /**
   * Optional edits to apply before accepting.
   * Partial patch on the proposed data.
   */
  edits?: Record<string, unknown>;
}

// ─────────────────────────────────────────────────────────────────────────────
// §10 — Endpoint Catalog
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Complete endpoint catalog.
 *
 * Naming: plural nouns, max 2 nesting levels (§2.3).
 * Methods: standard HTTP semantics (§2.3 table).
 *
 * Every mutating endpoint:
 *   - Requires Idempotency-Key header (POST only)
 *   - Supports If-Match for optimistic concurrency (PUT, DELETE)
 *   - Returns a request ID in X-Request-Id header
 *   - Returns rate limit state in X-RateLimit-* headers
 *
 * ┌─────────────────────────────────────────────────────────────────────┐
 * │ Method │ Path                                        │ Idempotent │
 * ├────────┼─────────────────────────────────────────────┼────────────┤
 * │ POST   │ /v1/philosophies                            │ Key req'd  │
 * │ GET    │ /v1/philosophies                            │ Yes        │
 * │ GET    │ /v1/philosophies/{id}                       │ Yes        │
 * │ DELETE │ /v1/philosophies/{id}                       │ Yes        │
 * │        │                                             │            │
 * │ GET    │ /v1/philosophies/{id}/dimensions/{name}     │ Yes        │
 * │ PUT    │ /v1/philosophies/{id}/dimensions/{name}     │ Yes        │
 * │ POST   │ /v1/philosophies/{id}/dimensions/{name}/    │ Key req'd  │
 * │        │   populate                                  │            │
 * │ POST   │ /v1/philosophies/{id}/dimensions/{name}/    │ Key req'd  │
 * │        │   verify                                    │            │
 * │ POST   │ /v1/philosophies/{id}/dimensions/{name}/    │ Key req'd  │
 * │        │   contest                                   │            │
 * │        │                                             │            │
 * │ POST   │ /v1/philosophies/{id}/decisions              │ Key req'd  │
 * │ GET    │ /v1/philosophies/{id}/decisions              │ Yes        │
 * │ GET    │ /v1/philosophies/{id}/decisions/{decisionId} │ Yes        │
 * │ PUT    │ /v1/philosophies/{id}/decisions/{decisionId} │ Yes        │
 * │ DELETE │ /v1/philosophies/{id}/decisions/{decisionId} │ Yes        │
 * │        │                                             │            │
 * │ POST   │ /v1/comparisons                             │ Key req'd  │
 * │ GET    │ /v1/comparisons                             │ Yes        │
 * │ GET    │ /v1/comparisons/{id}                        │ Yes        │
 * │ DELETE │ /v1/comparisons/{id}                        │ Yes        │
 * │        │                                             │            │
 * │ GET    │ /v1/operations/{id}                         │ Yes        │
 * │ POST   │ /v1/operations/{id}/review                  │ Key req'd  │
 * │ POST   │ /v1/operations/{id}/cancel                  │ Key req'd  │
 * └─────────────────────────────────────────────────────────────────────┘
 *
 * Query parameters for GET /v1/philosophies:
 *   ?cursor=<opaque>       Cursor-based pagination
 *   &limit=<1-100>         Page size (default 20)
 *   &systemName=<string>   Filter by system name (exact match)
 *   &sort=createdAt        Sort field
 *   &order=asc|desc        Sort direction (default desc)
 */

// ─────────────────────────────────────────────────────────────────────────────
// §11 — Response Headers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Standard response headers (documented here for completeness; these
 * are HTTP headers, not body fields).
 *
 * Required on every response:
 *   X-Request-Id: <uuid>               Audit correlation
 *   Content-Type: application/json      Always JSON
 *   ETag: "<hash>"                      For conditional requests
 *
 * Required on rate-limited responses:
 *   Retry-After: <seconds>              §6.3: explicit retry guidance
 *   X-RateLimit-Remaining: <number>     Budget remaining
 *   X-RateLimit-Reset: <epoch>          Reset timestamp
 *
 * Required on mutating responses:
 *   X-Operation-Id: <op_uuid>           Observable write state
 *   X-Idempotency-Key: <echoed>         Echoed back for confirmation
 */

// ─────────────────────────────────────────────────────────────────────────────
// §A — Design Decision Appendix
// ─────────────────────────────────────────────────────────────────────────────

/**
 * §A.1 — Why REST over GraphQL for v1
 *
 * The api-design-research.md decision framework (§3.5, §8, §9.1)
 * identifies these criteria:
 *
 * 1. Client diversity: initially low (SDK + direct HTTP). GraphQL's
 *    client-driven field selection adds complexity without proportional
 *    benefit when the primary use case requests full resources.
 *
 * 2. Over/under-fetching: minimal concern. Each philosophy is a single
 *    document with 10 dimensions. The ?expand= pattern (Stripe-style)
 *    covers the one relationship (decisions). The comparison resource
 *    is pre-composed by design.
 *
 * 3. Caching: REST benefits from HTTP-native caching. Philosophy resources
 *    change infrequently and benefit from ETag-based conditional requests.
 *    GraphQL's POST-based model would require custom caching.
 *
 * 4. Verification boundary: REST with explicit schemas, stable identifiers,
 *    machine-readable error classes, and observable write state satisfies
 *    the §9.1 PALS-aligned checklist more directly. GraphQL introspection
 *    is powerful, but mutation side effects and recovery semantics are
 *    harder to reason about for agent callers in this domain.
 *
 * 5. Simplicity of the domain: 3 top-level resource types, 2 sub-resources,
 *    no deep relationship graphs. GraphQL federation is unnecessary.
 *
 * Decision: REST for v1. Revisit if client diversity increases or if
 * comparison queries become complex enough to warrant flexible field
 * selection.
 *
 * Scope note from api-design-research.md v1.2:
 *   - MCP and A2A are complementary integration surfaces, but neither
 *     changes the underlying API contract requirements.
 *   - Event-driven patterns matter, but this v1 contract chooses
 *     polling + subscriptions over outbound webhooks for long-running
 *     generation because the primary consumers are SDKs, CI, and
 *     review tooling that already maintain authenticated sessions.
 *     Webhook delivery can be added later if cross-system automation
 *     becomes a first-class integration path.
 *
 *
 * §A.2 — Why dimension-level provenance, not field-level
 *
 * Field-level provenance (tracking authoring source per individual enum
 * value or rationale string) would be more precise but creates severe
 * practical problems:
 *   - Write amplification: updating one field requires provenance update
 *     on that field plus version bump on the dimension.
 *   - Review burden: verifiers review dimensions as coherent units, not
 *     individual fields in isolation.
 *   - Storage overhead: 10 dimensions × ~15 fields each × provenance
 *     metadata = 150 provenance records per philosophy. Dimension-level
 *     gives 10.
 *
 * Tradeoff: if a human edits 3 fields in a dimension that was LLM-generated,
 * the provenance becomes { kind: "mixed" }. Acceptable because the
 * verification status still requires re-verification of the whole dimension.
 *
 *
 * §A.3 — Why the Operation resource for LLM population
 *
 * api-design-research.md §2.4: "For AI-heavy systems, idempotency
 * should be paired with observable write state."
 *
 * LLM generation is:
 *   - Slow (10–60s) → cannot block the HTTP request
 *   - Non-deterministic → cannot be replayed without explicit idempotency
 *   - Untrusted → requires a review gate before commit (PALS §8.4)
 *   - Partially observable → needs progress reporting
 *
 * The Operation resource pattern (§6.5 plus the v1.2 long-running
 * operations guidance in api-design-research.md §8) addresses all four
 * constraints:
 *   1. POST returns 202 Accepted with the Operation resource
 *   2. Client polls GET /v1/operations/{id} for status
 *   3. When status is "awaiting_review", client calls POST .../review
 *   4. Accept commits the data; reject discards it
 *   5. Idempotency-Key prevents duplicate generation on retry
 *
 * Why polling/subscriptions first, not webhooks:
 *   - Webhooks are valuable for event-driven automation, but they add
 *     signing, replay protection, delivery retry, and subscription
 *     lifecycle concerns.
 *   - For v1, polling plus authenticated subscriptions is the simpler
 *     contract because operation state is already a first-class
 *     resource. This keeps observable write state explicit without
 *     introducing webhook delivery semantics prematurely.
 *
 *
 * §A.4 — PALS-Aligned Checklist (api-design-research.md §9.1)
 *
 * ✅ Can every request and response be validated mechanically against
 *    an explicit schema?
 *    → Yes. All request/response types are defined in this contract.
 *      The domain model uses Zod schemas that generate validators.
 *
 * ✅ Can the caller distinguish validation, authorization, conflict,
 *    transient, and internal failure classes without interpreting prose?
 *    → Yes. ApiErrorCode enum partitions all failures. RecoverySemantic
 *      tells the caller what to do next.
 *
 * ✅ Are mutating operations replay-safe?
 *    → Yes. POST requires Idempotency-Key. PUT is idempotent by spec.
 *      DELETE is idempotent.
 *
 * ✅ Can the system determine whether a write actually committed?
 *    → Yes. Operation resource tracks status from proposed → committed.
 *      X-Operation-Id header on mutation responses.
 *
 * ✅ Are destructive actions bounded?
 *    → Yes. DELETE requires If-Match (optimistic concurrency).
 *      LLM population defaults to "awaiting_review" (confirmation-gated).
 *
 * ✅ Does the API expose stable identifiers, pagination, and state
 *    inspection sufficient for post-call verification?
 *    → Yes. Prefixed IDs, cursor pagination, GET on all resources,
 *      GET /v1/operations/{id} for write state inspection.
 */
