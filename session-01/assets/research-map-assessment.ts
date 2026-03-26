/**
 * research-map-assessment.ts
 *
 * DISCLAIMER: This schema is a structural proposal for epistemic
 * self-assessment of research source maps. No claim, enum value,
 * or design decision herein should be taken as authoritative.
 *
 * The conceptual framework draws on:
 *   - E. P. Thompson's "history from below" (1966)
 *   - Subaltern Studies (Guha, Spivak, Chakrabarty)
 *   - Standpoint epistemology (Harding, Haraway)
 *   - Archival silences literature (Trouillot, Fuentes)
 *
 * None of these frameworks are formally implemented here.
 * The schema operationalizes their *concerns* as structured
 * data — it does not claim to encode their theoretical content.
 * Any axis, metric, or category not grounded in a verifiable
 * definition may be arbitrary or incomplete.
 *
 * This schema is designed to be used alongside the ResearchMap
 * schema (research-source-schema.ts v3.0.0), referencing it
 * by map ID.
 *
 * Zod v4 — import path: "zod" (stable ≥ 4.0.0)
 * Reference: https://zod.dev/api
 *
 * Schema version: 1.0.0
 */

import * as z from "zod";

// ═════════════════════════════════════════════
// §0. Shared atoms (same as source schema)
// ═════════════════════════════════════════════

const ISODateish = z.union([z.iso.date(), z.iso.datetime({ offset: true })]);
const ExactDate = z.object({ kind: z.literal("exact"), value: ISODateish });
const ApproximateDate = z.object({
  kind: z.literal("approximate"),
  label: z.string().trim().min(1),
  notBefore: ISODateish.optional(),
  notAfter: ISODateish.optional(),
  confidence: z.number().min(0).max(1).optional(),
});
const FuzzyDate = z.union([ExactDate, ApproximateDate]);
const NonEmpty = z.string().trim().min(1);

// ═════════════════════════════════════════════
// §1. Power axes
// ═════════════════════════════════════════════

/**
 * An axis along which sources can be unevenly distributed.
 *
 * "History from below" originally focused on class, but
 * subsequent work (feminist historiography, Subaltern Studies,
 * postcolonial theory) expanded the relevant axes. This list
 * is not exhaustive — `custom` exists for domain-specific axes.
 *
 * Each axis is a dimension of potential silencing. The question
 * is always: along this axis, whose voice is present in the map
 * and whose is absent?
 */
const PowerAxisKind = z.literal([
  "class",
  "race-ethnicity",
  "gender",
  "sexuality",
  "age-generation",
  "disability",
  "religion",
  "language",
  "literacy",
  "colonial-position",
  "geographic-center-periphery",
  "institutional-affiliation",
  "political-power",
  "economic-power",
  "caste",
  "indigenous-status",
  "migration-status",
  "incarceration-status",
  "custom",
]);

/**
 * Assessment of source distribution along a single power axis.
 *
 * This is necessarily interpretive. The schema captures the
 * researcher's *judgment* about distribution, not an automated
 * measurement. Automation would require external classification
 * of every source, which is both impractical and epistemically
 * fraught (who decides which "class" a source represents?).
 */
const AxisAssessment = z.object({
  axis: PowerAxisKind,
  /** If axis is "custom", name it here. */
  customLabel: z.string().optional(),

  /**
   * Who or what is *over-represented* along this axis?
   * E.g. "institutional academic voices", "urban literate elites",
   *      "colonial administrators", "male perspectives".
   */
  overrepresented: z.array(z.string()).optional(),

  /**
   * Who or what is *under-represented* or entirely absent?
   * E.g. "rural peasant experience", "women's domestic labor",
   *      "enslaved persons' testimony", "oral-only communities".
   */
  underrepresented: z.array(z.string()).optional(),

  /**
   * Who or what is *structurally silenced* — not merely absent
   * from this map, but absent from the archival record itself?
   *
   * Trouillot's distinction: some silences are in *this* archive
   * (and can be fixed by searching harder); others are in
   * *the* archive (the sources were never created, or were
   * destroyed, and no amount of searching will find them).
   *
   * Thompson: "the enormous condescension of posterity" toward
   * those who left no written record.
   */
  structurallySilenced: z.array(z.string()).optional(),

  /**
   * 0 = completely one-sided (only one position represented)
   * 1 = maximally balanced (full spectrum represented)
   *
   * This is a subjective self-assessment, not a computed metric.
   * Its value is in forcing the researcher to commit to a number.
   */
  balanceScore: z.number().min(0).max(1).optional(),

  /** Reasoning behind the balance assessment. */
  justification: z.string().optional(),
});

export type AxisAssessment = z.infer<typeof AxisAssessment>;

// ═════════════════════════════════════════════
// §2. Source-type concentration
// ═════════════════════════════════════════════

/**
 * Measures how concentrated the map is in particular source types.
 *
 * A map of 100 journal articles and 0 oral testimonies is not
 * "rigorous" — it is *epistemically narrow*. It systematically
 * excludes everyone who doesn't produce journal articles.
 *
 * Thompson's method explicitly drew on "pamphlets, personal
 * letters, newspapers, and court records" — not because they
 * were better sources, but because they were where ordinary
 * people's voices survived.
 */
const SourceTypeDistribution = z.object({
  /**
   * Map from SourceKind → count.
   * E.g. { "journal-article": 45, "oral-testimony": 2, "painting": 1 }
   */
  counts: z.record(z.string(), z.number().int().nonnegative()),

  /** Total number of sources in the map. */
  total: z.number().int().nonnegative(),

  /**
   * Herfindahl-Hirschman Index of source-type concentration.
   * Sum of squared shares. Range: 1/n (perfectly even) to 1 (all one type).
   *
   * HHI > 0.5 signals high concentration — most voices come
   * through the same kind of record, with the same production biases.
   *
   * This IS a computable metric: HHI = Σ(count_i / total)².
   * The schema stores the result; computation is the consumer's job.
   */
  hhi: z.number().min(0).max(1).optional(),

  /**
   * Which source types dominate and why that matters.
   * E.g. "87% journal articles — systematically excludes non-academic
   *        knowledge production, oral traditions, and visual culture."
   */
  interpretation: z.string().optional(),
});

export type SourceTypeDistribution = z.infer<typeof SourceTypeDistribution>;

// ═════════════════════════════════════════════
// §3. Methodological self-critique
// ═════════════════════════════════════════════

/**
 * Every retrieval method has structural biases.
 *
 * Database search → finds what's indexed → excludes oral,
 *   informal, non-English, pre-digital, non-institutional sources.
 * Citation chaining → follows the network of those who cite
 *   each other → excludes those outside the citation network.
 * Fieldwork → limited by access, language competence, trust.
 *
 * This section forces the researcher to name what their
 * methods cannot see.
 */
const MethodBias = z.object({
  /** Which retrieval method (from ResearchMap's RetrievalMethod enum). */
  method: NonEmpty,

  /** What percentage of the map's sources came from this method. */
  sharePercent: z.number().min(0).max(100).optional(),

  /**
   * What this method systematically finds.
   * E.g. "Peer-reviewed English-language scholarship indexed in Scopus."
   */
  reaches: z.string().optional(),

  /**
   * What this method systematically misses.
   * E.g. "Non-indexed journals, grey literature, oral sources,
   *        sources in non-Latin scripts, community knowledge."
   */
  misses: z.string().optional(),

  /** Any mitigations applied (e.g. "supplemented with fieldwork"). */
  mitigation: z.string().optional(),
});

export type MethodBias = z.infer<typeof MethodBias>;

// ═════════════════════════════════════════════
// §4. Temporal & geographic coverage
// ═════════════════════════════════════════════

/**
 * Identifies temporal and geographic holes in the map.
 *
 * A map covering 1780–1832 England (Thompson's period) that
 * ignores simultaneous events in India is not "focused" — it
 * is reproducing an insular frame. The Aeon critique of Thompson
 * makes exactly this point: "the industrial revolution that
 * produced the English working class simultaneously ruined the
 * Indian handloom textile industry."
 */
const CoverageGap = z.object({
  /** What kind of gap. */
  dimension: z.literal(["temporal", "geographic", "linguistic", "thematic"]),

  /** Human-readable description of the gap. */
  description: NonEmpty,

  /**
   * Why this gap exists.
   * E.g. "No sources in Arabic were searched",
   *      "Pre-1900 records for this region were destroyed",
   *      "The project scope excluded colonial periphery by design".
   */
  cause: z.string().optional(),

  /**
   * How severe is this gap for the map's stated research question?
   * 0 = negligible, 1 = fundamentally undermines the map's claims.
   */
  severity: z.number().min(0).max(1).optional(),

  /**
   * Is this gap fixable with additional effort, or is it
   * a structural absence in the historical record itself?
   */
  fixability: z.literal([
    "fixable-with-effort",
    "partially-fixable",
    "structural-absence",
    "unknown",
  ]).optional(),
});

export type CoverageGap = z.infer<typeof CoverageGap>;

// ═════════════════════════════════════════════
// §5. Blind spots
// ═════════════════════════════════════════════

/**
 * A blind spot is a *named, specific* gap in the map's
 * epistemic coverage — not a vague worry, but a concrete
 * absence with a concrete consequence.
 *
 * The distinction from CoverageGap: a coverage gap is about
 * *what's missing* (a time period, a region). A blind spot
 * is about *whose experience is invisible* and *what claims
 * are therefore unsupported or distorted*.
 *
 * Spivak's question: "Can the subaltern speak?" is not
 * rhetorical — it asks whether the conceptual apparatus of
 * the researcher can even *register* certain kinds of voice.
 * A blind spot may be a gap in sources, or it may be a gap
 * in the researcher's capacity to interpret what's already there.
 */
const BlindSpotKind = z.literal([
  /** Source gap: the voices are absent from the map. */
  "source-absence",
  /** Interpretive gap: the sources are present but misread
   *  or read through an inappropriate frame. */
  "interpretive-frame",
  /** Archival gap: the sources never existed or were destroyed. */
  "archival-destruction",
  /** Language gap: the sources exist but in inaccessible languages. */
  "language-barrier",
  /** Access gap: the sources exist but are sealed, restricted,
   *  or controlled by communities who have not granted access. */
  "access-restriction",
  /** Conceptual gap: the research question itself is framed in
   *  a way that excludes certain kinds of evidence. */
  "question-framing",
  /** Survivorship: the map reflects what survived, not what existed. */
  "survivorship-bias",
]);

const BlindSpot = z.object({
  id: z.uuidv4(),
  kind: BlindSpotKind,
  title: NonEmpty,

  /**
   * Detailed description of what is missing or distorted.
   * E.g. "The map contains no first-person accounts from
   *        enslaved persons. All references to slavery come
   *        from plantation owners' records and abolitionist
   *        literature — both of which impose external frames
   *        on the enslaved experience."
   */
  description: NonEmpty,

  /**
   * Which power axes are implicated.
   * E.g. ["class", "race-ethnicity", "literacy"]
   */
  axes: z.array(PowerAxisKind).optional(),

  /**
   * What claims in the map are weakened or invalidated by this blind spot.
   * References to Claim IDs in the source map, or free-text descriptions.
   */
  affectedClaims: z.array(z.string()).optional(),

  severity: z.number().min(0).max(1).optional(),
  fixability: z
    .literal([
      "fixable-with-effort",
      "partially-fixable",
      "structural-absence",
      "unknown",
    ])
    .optional(),

  /**
   * What would be needed to address this blind spot.
   * Pointers to RemediationAction IDs.
   */
  remediationIds: z.array(z.uuidv4()).optional(),
});

export type BlindSpot = z.infer<typeof BlindSpot>;

// ═════════════════════════════════════════════
// §6. Remediation actions
// ═════════════════════════════════════════════

/**
 * A concrete, actionable step to reduce a blind spot.
 * Not a wish — a task that can be assigned, scheduled,
 * and verified as done or not done.
 *
 * Thompson didn't just *note* that working-class voices
 * were absent — he went to the pamphlets, court records,
 * and personal letters. Remediation is the Thompson move.
 */
const RemediationStatus = z.literal([
  "proposed",
  "in-progress",
  "completed",
  "blocked",
  "abandoned",
]);

const RemediationAction = z.object({
  id: z.uuidv4(),

  /** Which blind spot(s) this addresses. */
  blindSpotIds: z.array(z.uuidv4()).min(1),

  title: NonEmpty,

  /**
   * What specifically needs to be done.
   * E.g. "Conduct interviews with surviving members of the
   *        textile workers' cooperative in Łódź. Contact the
   *        Łódź City Museum oral history program for referrals."
   */
  description: NonEmpty,

  /**
   * What kind of action is this?
   */
  type: z.literal([
    /** Search additional databases, archives, or collections. */
    "additional-search",
    /** Conduct fieldwork, interviews, or site visits. */
    "fieldwork",
    /** Engage with community members, elders, or custodians. */
    "community-engagement",
    /** Commission or arrange translation of existing sources. */
    "translation",
    /** Learn or recruit competence in a language or method. */
    "capacity-building",
    /** Consult domain experts outside the researcher's field. */
    "expert-consultation",
    /** Reframe the research question to acknowledge the gap. */
    "reframing",
    /** Explicitly state the limitation in the map's conclusions. */
    "disclosure",
    /** Other. */
    "other",
  ]),

  /**
   * Estimated effort (researcher-days).
   * Forces prioritization — not all gaps are equally worth filling.
   */
  estimatedEffortDays: z.number().positive().optional(),

  /**
   * Expected impact on the blind spot's severity.
   * 0 = negligible, 1 = fully resolves the blind spot.
   */
  expectedImpact: z.number().min(0).max(1).optional(),

  /**
   * What obstacles exist.
   * E.g. "Community gatekeepers have not responded to contact",
   *      "Archive is sealed until 2045",
   *      "No funding for fieldwork travel".
   */
  obstacles: z.array(z.string()).optional(),

  status: RemediationStatus,
  assignedTo: z.string().optional(),
  dueDate: FuzzyDate.optional(),
  completedDate: FuzzyDate.optional(),
  notes: z.string().optional(),
});

export type RemediationAction = z.infer<typeof RemediationAction>;

// ═════════════════════════════════════════════
// §7. Positionality statement
// ═════════════════════════════════════════════

/**
 * The researcher's own epistemic position — who they are,
 * what they can see, and what they probably can't.
 *
 * Standpoint epistemology (Harding) argues that knowledge is
 * always situated. The positionality statement makes this
 * explicit rather than pretending to a "view from nowhere."
 *
 * This is uncomfortable by design. The schema exists to
 * prevent the researcher from hiding behind false neutrality.
 */
const PositionalityStatement = z.object({
  /**
   * Who is the researcher / research team?
   * Relevant background: institutional affiliation, discipline,
   * geographic location, languages spoken, relevant identities.
   *
   * This is not a CV — it's the information needed to
   * understand what the researcher can and cannot access.
   */
  background: NonEmpty,

  /**
   * What is the researcher's relationship to the subject?
   * Insider, outsider, adjacent, commissioned, adversarial?
   */
  relationToSubject: z.string().optional(),

  /**
   * What languages can the researcher read / speak / understand?
   * This directly constrains which sources are accessible.
   */
  languages: z.array(z.string()).optional(),

  /**
   * What institutional resources does the researcher have access to?
   * Database subscriptions, archive access, funding, travel capacity.
   */
  institutionalAccess: z.array(z.string()).optional(),

  /**
   * Known limitations that flow from the researcher's position.
   * E.g. "I cannot read Arabic, so all Ottoman-era sources are
   *        mediated through English translations."
   */
  knownLimitations: z.array(z.string()).optional(),

  /**
   * What motivated this research? Funding source? Political commitment?
   * Personal connection? Institutional requirement?
   *
   * Thompson was explicit that his history was politically motivated.
   * The schema does not require political commitment — it requires
   * transparency about motivation.
   */
  motivation: z.string().optional(),
});

export type PositionalityStatement = z.infer<typeof PositionalityStatement>;

// ═════════════════════════════════════════════
// §8. Overall assessment verdict
// ═════════════════════════════════════════════

/**
 * A composite judgment on the map's epistemic health.
 * Not a single number — a structured verdict with
 * explicit dimensions.
 */
const AssessmentVerdict = z.object({
  /**
   * Overall balance: 0 = deeply one-sided, 1 = well-balanced.
   * Aggregated from axis assessments. Methodology for
   * aggregation is the consumer's responsibility.
   */
  overallBalance: z.number().min(0).max(1).optional(),

  /**
   * Source diversity (inverse of HHI from §2).
   * 0 = all one type, 1 = maximally diverse.
   */
  sourceDiversity: z.number().min(0).max(1).optional(),

  /**
   * How many blind spots are currently unaddressed?
   */
  unaddressedBlindSpots: z.number().int().nonnegative().optional(),

  /**
   * How many blind spots are structural (archival destruction,
   * no possible sources) vs. fixable with effort?
   */
  structuralBlindSpots: z.number().int().nonnegative().optional(),
  fixableBlindSpots: z.number().int().nonnegative().optional(),

  /**
   * Does the map's evidence base support its stated claims?
   * This is the Thompson test: are you making claims about
   * "the working class" based only on what elites wrote
   * about them?
   */
  claimsSupported: z.literal([
    "well-supported",
    "partially-supported",
    "weakly-supported",
    "unsupported-for-stated-scope",
  ]).optional(),

  /**
   * Free-form summary. This is where the researcher writes
   * the honest paragraph about what the map can and cannot do.
   */
  summary: z.string().optional(),
});

export type AssessmentVerdict = z.infer<typeof AssessmentVerdict>;

// ═════════════════════════════════════════════
// §9. The assessment itself (top-level)
// ═════════════════════════════════════════════

const MapAssessment = z.object({
  id: z.uuidv4(),

  /** Which ResearchMap this assessment applies to. */
  mapId: z.uuidv4(),

  /** When this assessment was performed. */
  assessedAt: FuzzyDate,

  /** Who performed the assessment. */
  assessedBy: z.string().optional(),

  schemaVersion: z.literal("1.0.0"),

  // ── Core sections ──
  positionality: PositionalityStatement,
  axisAssessments: z.array(AxisAssessment).min(1),
  sourceDistribution: SourceTypeDistribution,
  methodBiases: z.array(MethodBias).optional(),
  coverageGaps: z.array(CoverageGap).optional(),
  blindSpots: z.array(BlindSpot).optional(),
  remediations: z.array(RemediationAction).optional(),
  verdict: AssessmentVerdict,

  /** Extensibility. */
  meta: z.record(z.string(), z.unknown()).optional(),
});

export type MapAssessment = z.infer<typeof MapAssessment>;

// ═════════════════════════════════════════════
// Exports
// ═════════════════════════════════════════════

export {
  // Atoms
  FuzzyDate,
  ExactDate,
  ApproximateDate,
  NonEmpty,
  // Power axes
  PowerAxisKind,
  AxisAssessment as AxisAssessmentSchema,
  // Source distribution
  SourceTypeDistribution as SourceTypeDistributionSchema,
  // Method bias
  MethodBias as MethodBiasSchema,
  // Coverage
  CoverageGap as CoverageGapSchema,
  // Blind spots
  BlindSpotKind,
  BlindSpot as BlindSpotSchema,
  // Remediation
  RemediationStatus,
  RemediationAction as RemediationActionSchema,
  // Positionality
  PositionalityStatement as PositionalityStatementSchema,
  // Verdict
  AssessmentVerdict as AssessmentVerdictSchema,
  // Top-level
  MapAssessment as MapAssessmentSchema,
};
