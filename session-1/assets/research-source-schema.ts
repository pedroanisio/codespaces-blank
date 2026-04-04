/**
 * research-source-schema.ts
 *
 * DISCLAIMER: This schema is a structural proposal. No claim, default value,
 * enum member, or design decision herein should be taken as authoritative.
 * Any element not backed by a verifiable standard (ISO 8601, DOI spec,
 * BibTeX fields, SPDX, ICOM object ID, etc.) may be arbitrary, incomplete,
 * or wrong. Validate against your domain requirements before adoption.
 *
 * The oral-source extensions draw on practices from oral history methodology
 * and archival ethics. The visual-arts and media extensions draw loosely on
 * museum cataloguing conventions (CDWA, Dublin Core, ICOM). Neither set
 * implements any specific standard. Verify fitness for your institutional
 * requirements.
 *
 * Zod v4 — import path: "zod" (stable ≥ 4.0.0)
 * Reference: https://zod.dev/api
 *
 * Schema version: 3.0.0
 */

import * as z from "zod";

// ═════════════════════════════════════════════
// §0. Reusable atoms
// ═════════════════════════════════════════════

const ISODateish = z.union([z.iso.date(), z.iso.datetime({ offset: true })]);

const ApproximateDate = z.object({
  kind: z.literal("approximate"),
  label: z.string().trim().min(1),
  notBefore: ISODateish.optional(),
  notAfter: ISODateish.optional(),
  confidence: z.number().min(0).max(1).optional(),
});

const ExactDate = z.object({
  kind: z.literal("exact"),
  value: ISODateish,
});

const FuzzyDate = z.union([ExactDate, ApproximateDate]);

const NonEmpty = z.string().trim().min(1);

const LanguageTag = z
  .string()
  .regex(/^[a-z]{2,3}(-[A-Za-z0-9]{1,8})*$/, {
    error: "Expected a BCP 47-like language tag (e.g. 'en', 'pt-BR')",
  });

// ═════════════════════════════════════════════
// §1. Identifiers
// ═════════════════════════════════════════════

const SourceIdentifiers = z.object({
  // ── Academic / publishing ──
  doi: z
    .string()
    .regex(/^10\.\d{4,9}\/[^\s]+$/, { error: "Invalid DOI format" })
    .optional(),
  isbn: z.string().optional(),
  issn: z.string().optional(),
  pmid: z.string().optional(),
  pmcid: z.string().optional(),
  arxivId: z.string().optional(),
  ssrn: z.string().optional(),
  url: z.url().optional(),
  urn: z.string().optional(),
  handle: z.string().optional(),
  // ── Museum / art / archive ──
  /** Museum or institution accession number. */
  accessionNumber: z.string().optional(),
  /** Catalogue raisonné reference (e.g. "Zervos II, 305" for Guernica). */
  catalogueRaisonne: z.string().optional(),
  /** ISAN for audiovisual works (ISO 15706). */
  isan: z.string().optional(),
  /** ISRC for sound recordings (ISO 3901). */
  isrc: z.string().optional(),
  /** ISWC for musical compositions (ISO 15707). */
  iswc: z.string().optional(),
  /** EIDR for film/TV (Entertainment Identifier Registry). */
  eidr: z.string().optional(),
  /** Catch-all for domain-specific IDs. */
  custom: z.record(z.string(), z.string()).optional(),
});

export type SourceIdentifiers = z.infer<typeof SourceIdentifiers>;

// ═════════════════════════════════════════════
// §2. Agents
// ═════════════════════════════════════════════

const AgentRole = z.literal([
  // ── Writing / research ──
  "author",
  "editor",
  "translator",
  "compiler",
  "reviewer",
  "contributor",
  // ── Oral / fieldwork ──
  "narrator",
  "informant",
  "interviewer",
  "transcriber",
  "custodian",
  // ── Visual arts ──
  "artist",
  "printmaker",
  "engraver",
  "sculptor",
  "photographer",
  "illustrator",
  "curator",
  "restorer",
  // ── Music / audio ──
  "composer",
  "lyricist",
  "arranger",
  "conductor",
  "performer",
  "sound-engineer",
  "producer",
  // ── Film / video ──
  "director",
  "screenwriter",
  "cinematographer",
  "film-editor",
  "animator",
  // ── General creative ──
  "choreographer",
  "designer",
  "architect",
]);

const Agent = z.object({
  name: NonEmpty,
  anonymized: z.boolean().optional(),
  orcid: z
    .string()
    .regex(/^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/)
    .optional(),
  affiliation: z.string().optional(),
  roles: z.array(AgentRole).min(1).optional(),
});

export type Agent = z.infer<typeof Agent>;

// ═════════════════════════════════════════════
// §2a. Communal & anonymous attribution
// ═════════════════════════════════════════════

const CommunalAttribution = z.object({
  type: z.literal([
    "community",
    "ethnic-group",
    "organization",
    "collective",
    "workshop",
    "studio",
    "anonymous",
    "unknown",
  ]),
  label: NonEmpty,
  region: z.string().optional(),
  reason: z
    .literal([
      "collective-authorship",
      "lost-to-time",
      "anonymity-for-safety",
      "cultural-convention",
      "workshop-production",
      "unknown",
    ])
    .optional(),
});

export type CommunalAttribution = z.infer<typeof CommunalAttribution>;

const Attribution = z.object({
  agents: z.array(Agent).optional(),
  communal: CommunalAttribution.optional(),
}).refine(
  (val) => (val.agents && val.agents.length > 0) || val.communal != null,
  {
    error:
      "Attribution requires at least one named agent or a communal attribution",
  },
);

export type Attribution = z.infer<typeof Attribution>;

// ═════════════════════════════════════════════
// §3. Source kind taxonomy
// ═════════════════════════════════════════════

const SourceKind = z.literal([
  // ── Written / digital ──
  "journal-article",
  "conference-paper",
  "preprint",
  "book",
  "book-chapter",
  "thesis",
  "dissertation",
  "report",
  "technical-report",
  "white-paper",
  "working-paper",
  "patent",
  "standard",
  "legislation",
  "court-case",
  "dataset",
  "software",
  "web-page",
  "blog-post",
  "news-article",
  "slide-deck",
  "correspondence",
  "archival-document",
  // ── Oral / performed ──
  "oral-testimony",
  "oral-history-interview",
  "oral-tradition",
  "folk-song",
  "proverb-collection",
  "speech",
  "sermon",
  "ritual-text",
  "radio-broadcast",
  // ── Visual arts ──
  "painting",
  "drawing",
  "print",
  "engraving",
  "sculpture",
  "installation",
  "mural",
  "mosaic",
  "textile",
  "mixed-media",
  "photograph",
  "poster",
  "map-cartographic",
  // ── Music / audio ──
  "musical-composition",
  "score",
  "album",
  "single-track",
  "sound-recording",
  "podcast",
  "audio-field-recording",
  // ── Film / video / performance ──
  "film",
  "documentary",
  "animation",
  "short-film",
  "music-video",
  "video",
  "television-program",
  "performance",
  "interview",
  "dance",
  // ── Catch-all ──
  "other",
]);

export type SourceKind = z.infer<typeof SourceKind>;

// ═════════════════════════════════════════════
// §4. Publication context
// ═════════════════════════════════════════════

const PublicationContext = z.object({
  journal: z.string().optional(),
  publisher: z.string().optional(),
  volume: z.string().optional(),
  issue: z.string().optional(),
  pages: z.string().optional(),
  edition: z.string().optional(),
  series: z.string().optional(),
  conferenceTitle: z.string().optional(),
  institution: z.string().optional(),
  country: z.string().optional(),
  /**
   * For recorded media: label / distributor.
   * E.g. "Blue Note Records", "A24", "BBC".
   */
  label: z.string().optional(),
  /** Catalog number from the label/distributor. */
  catalogNumber: z.string().optional(),
});

export type PublicationContext = z.infer<typeof PublicationContext>;

// ═════════════════════════════════════════════
// §5. Access & licensing
// ═════════════════════════════════════════════

const AccessLevel = z.literal([
  "open",
  "green-oa",
  "gold-oa",
  "bronze-oa",
  "restricted",
  "paywalled",
  "embargoed",
  "unknown",
]);

const LicenseInfo = z.object({
  spdx: z.string().optional(),
  name: z.string().optional(),
  url: z.url().optional(),
});

const AccessInfo = z.object({
  level: AccessLevel.optional(),
  license: LicenseInfo.optional(),
  embargoUntil: FuzzyDate.optional(),
});

export type AccessInfo = z.infer<typeof AccessInfo>;

// ═════════════════════════════════════════════
// §5a. Ethical & sensitivity metadata
// ═════════════════════════════════════════════

const ConsentStatus = z.literal([
  "informed-consent-obtained",
  "verbal-consent-obtained",
  "consent-implied",
  "consent-unknown",
  "consent-refused",
  "posthumous-no-consent-possible",
  "community-consent-obtained",
]);

const SensitivityLevel = z.literal([
  "public",
  "restricted-researcher",
  "restricted-community",
  "sealed",
  "anonymized",
]);

const EthicsInfo = z.object({
  consent: ConsentStatus.optional(),
  consentDate: FuzzyDate.optional(),
  approvedBy: z.string().optional(),
  ethicsRef: z.string().optional(),
  sensitivity: SensitivityLevel.optional(),
  restrictions: z.array(z.string()).optional(),
  anonymized: z.boolean().optional(),
  notes: z.string().optional(),
});

export type EthicsInfo = z.infer<typeof EthicsInfo>;

// ═════════════════════════════════════════════
// §6. Provenance — how the source was found
// ═════════════════════════════════════════════

const RetrievalMethod = z.literal([
  "database-search",
  "citation-chaining",
  "recommendation",
  "manual-entry",
  "web-scrape",
  "api-import",
  "rss-feed",
  "alert-service",
  // ── Fieldwork / oral ──
  "fieldwork-interview",
  "community-referral",
  "archival-listening",
  "participant-observation",
  // ── Visual / media ──
  "museum-visit",
  "exhibition-catalog",
  "auction-record",
  "collection-survey",
  "other",
]);

const Provenance = z.object({
  retrievedAt: FuzzyDate,
  method: RetrievalMethod.optional(),
  retrievedFrom: z.string().optional(),
  query: z.string().optional(),
  addedBy: z.string().optional(),
  lastVerifiedAt: FuzzyDate.optional(),
});

export type Provenance = z.infer<typeof Provenance>;

// ═════════════════════════════════════════════
// §7. Quality & reliability signals
// ═════════════════════════════════════════════

const PeerReviewStatus = z.literal([
  "peer-reviewed",
  "editorial-reviewed",
  "not-reviewed",
  "retracted",
  "unknown",
]);

const TransmissionFidelity = z.literal([
  "verbatim-recording",
  "contemporaneous-transcription",
  "recalled-transcription",
  "second-hand-account",
  "multi-generational",
  "reconstructed",
  "unknown",
]);

const QualitySignals = z.object({
  peerReview: PeerReviewStatus.optional(),
  citationCount: z.number().int().nonnegative().optional(),
  citationCountAsOf: FuzzyDate.optional(),
  impactFactor: z.number().nonnegative().optional(),
  hIndex: z.number().int().nonnegative().optional(),
  altmetricScore: z.number().nonnegative().optional(),
  reliabilityRating: z.number().min(0).max(1).optional(),
  transmissionFidelity: TransmissionFidelity.optional(),
  corroborated: z
    .literal(["yes", "partially", "no", "not-attempted", "unknown"])
    .optional(),
  notes: z.string().optional(),
});

export type QualitySignals = z.infer<typeof QualitySignals>;

// ═════════════════════════════════════════════
// §8. Structured locator
// ═════════════════════════════════════════════

/**
 * Points at a specific region within a source.
 * Discriminated by `type` so consumers can handle each
 * addressing mode precisely.
 *
 *   Page     → text documents
 *   Time     → audio, video, film
 *   Spatial  → visual art (bounding box within the work)
 *   Section  → named divisions (movements, chapters, acts, stanzas)
 *   Free     → anything else ("third repetition of the chorus")
 */
const LocatorPage = z.object({
  type: z.literal("page"),
  /** Single page or range: "42", "42-45". */
  value: NonEmpty,
});

const LocatorTime = z.object({
  type: z.literal("time"),
  /** Start time in seconds from beginning. */
  startSeconds: z.number().nonnegative(),
  /** End time in seconds (omit for a point reference). */
  endSeconds: z.number().nonnegative().optional(),
  /** Human-readable label: "1:23:04 – 1:24:10". */
  label: z.string().optional(),
});

/**
 * Spatial locator — a bounding box within the visual field of a work.
 * Coordinates are normalized 0–1, origin top-left, so they work
 * regardless of reproduction size. x=0 y=0 is the top-left corner
 * of the work; x=1 y=1 is the bottom-right.
 */
const LocatorSpatial = z.object({
  type: z.literal("spatial"),
  x: z.number().min(0).max(1),
  y: z.number().min(0).max(1),
  width: z.number().min(0).max(1),
  height: z.number().min(0).max(1),
  /** Human label: "weeping woman, lower left". */
  label: z.string().optional(),
});

const LocatorSection = z.object({
  type: z.literal("section"),
  /** E.g. "Movement III", "Act 2 Scene 4", "Verse 3", "Reel 2". */
  value: NonEmpty,
});

const LocatorFree = z.object({
  type: z.literal("free"),
  value: NonEmpty,
});

const Locator = z.union([
  LocatorPage,
  LocatorTime,
  LocatorSpatial,
  LocatorSection,
  LocatorFree,
]);

export type Locator = z.infer<typeof Locator>;

// ═════════════════════════════════════════════
// §9. Claims & annotations
// ═════════════════════════════════════════════

const ClaimStatus = z.literal([
  "accepted",
  "contested",
  "refuted",
  "unverified",
]);

const Claim = z.object({
  id: z.uuidv4(),
  statement: NonEmpty,
  locator: Locator.optional(),
  status: ClaimStatus.optional(),
  assessment: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

export type Claim = z.infer<typeof Claim>;

const Annotation = z.object({
  id: z.uuidv4(),
  content: NonEmpty,
  locator: Locator.optional(),
  createdAt: FuzzyDate.optional(),
  author: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

export type Annotation = z.infer<typeof Annotation>;

// ═════════════════════════════════════════════
// §10. Relations
// ═════════════════════════════════════════════

const RelationType = z.literal([
  "cites",
  "cited-by",
  "extends",
  "contradicts",
  "corroborates",
  "replicates",
  "retracts",
  "reviews",
  "is-part-of",
  "has-part",
  "is-version-of",
  "derived-from",
  "related-to",
  // ── Oral transmission ──
  "transmitted-from",
  "variant-of",
  "transcription-of",
  "recording-of",
  "translation-of",
  // ── Visual arts / media ──
  "reproduction-of",
  "study-for",
  "sketch-for",
  "inspired-by",
  "commissioned-by",
  "exhibited-with",
  "adaptation-of",
  "restoration-of",
  "cover-of",
  "remix-of",
  "sample-of",
]);

const SourceRelation = z.object({
  targetId: z.uuidv4(),
  relation: RelationType,
  note: z.string().optional(),
});

export type SourceRelation = z.infer<typeof SourceRelation>;

// ═════════════════════════════════════════════
// §11. Fixation layers
// ═════════════════════════════════════════════

const FixationMedium = z.literal([
  // ── Oral ──
  "live-performance",
  "audio-tape",
  "audio-digital",
  "video-tape",
  "video-digital",
  "handwritten-transcription",
  "typed-transcription",
  "digital-transcription",
  "memory",
  // ── Visual / material ──
  "original-work",
  "photograph-of-work",
  "slide-transparency",
  "digital-scan",
  "lithograph",
  "screen-print",
  "cast",
  // ── Film / audio production ──
  "film-negative",
  "film-print",
  "digital-master",
  "vinyl-pressing",
  "cd-pressing",
  "streaming-encode",
  "other",
]);

const FixationLayer = z.object({
  medium: FixationMedium,
  date: FuzzyDate.optional(),
  agent: z.string().optional(),
  location: z.string().optional(),
  lossNotes: z.string().optional(),
  language: LanguageTag.optional(),
});

export type FixationLayer = z.infer<typeof FixationLayer>;

// ═════════════════════════════════════════════
// §12. Transmission chain (unchanged from v2)
// ═════════════════════════════════════════════

const TransmissionLink = z.object({
  from: z.string().optional(),
  to: z.string().optional(),
  date: FuzzyDate.optional(),
  mode: z.string().optional(),
  context: z.string().optional(),
});

const TransmissionChain = z.object({
  links: z.array(TransmissionLink).min(1),
  hasGaps: z.boolean().optional(),
  estimatedDepth: z.number().int().nonnegative().optional(),
  notes: z.string().optional(),
});

export type TransmissionChain = z.infer<typeof TransmissionChain>;

// ═════════════════════════════════════════════
// §13. Oral context (unchanged from v2)
// ═════════════════════════════════════════════

const OralContext = z.object({
  fixations: z.array(FixationLayer).min(1).optional(),
  transmissionChain: TransmissionChain.optional(),
  performedLanguages: z.array(LanguageTag).optional(),
  oralGenre: z.string().optional(),
  performanceContext: z.string().optional(),
  communityRestriction: z.string().optional(),
  notes: z.string().optional(),
});

export type OralContext = z.infer<typeof OralContext>;

// ═════════════════════════════════════════════
// §14. Physical description (NEW)
// ═════════════════════════════════════════════

/**
 * Material properties of a physical work — painting, sculpture,
 * print, textile, mixed media, etc.
 *
 * Loosely modeled on CDWA (Categories for the Description of
 * Works of Art) but drastically simplified. Not an implementation
 * of CDWA, VRA Core, or any other standard.
 */
const Dimensions = z.object({
  /** Height in centimeters. */
  heightCm: z.number().positive().optional(),
  /** Width in centimeters. */
  widthCm: z.number().positive().optional(),
  /** Depth in centimeters (for sculpture, relief, etc.). */
  depthCm: z.number().positive().optional(),
  /** Duration in seconds (for time-based media). */
  durationSeconds: z.number().positive().optional(),
  /** Weight in kilograms (for sculpture, installation). */
  weightKg: z.number().positive().optional(),
  /** Free text for irregular or compound dimensions. */
  note: z.string().optional(),
});

const PhysicalDescription = z.object({
  /**
   * Primary medium / technique.
   * E.g. "oil on canvas", "marble", "gelatin silver print",
   *      "charcoal on paper", "bronze cast", "woodcut".
   */
  medium: z.string().optional(),
  /**
   * Support or substrate.
   * E.g. "canvas", "panel", "paper", "stone", "film stock".
   */
  support: z.string().optional(),
  dimensions: Dimensions.optional(),
  /**
   * Condition as of the last assessment.
   * Free text — no controlled vocabulary enforced.
   */
  condition: z.string().optional(),
  /** Whether the work has been inscribed, signed, or marked. */
  inscriptions: z.string().optional(),
  notes: z.string().optional(),
});

export type PhysicalDescription = z.infer<typeof PhysicalDescription>;

// ═════════════════════════════════════════════
// §15. Holding (NEW)
// ═════════════════════════════════════════════

/**
 * Where a physical or archival work is currently held.
 * Not to be confused with Provenance (how the *researcher*
 * found it) — Holding describes the work's own location
 * in the world.
 */
const Holding = z.object({
  /** Institution name: "Museo Reina Sofía", "Library of Congress". */
  institution: NonEmpty,
  /** Department, room, or gallery within the institution. */
  department: z.string().optional(),
  /** City, country — free text. */
  location: z.string().optional(),
  /** Accession or call number at this institution (may duplicate identifiers). */
  accessionNumber: z.string().optional(),
  /**
   * Is this the current holder, or a historical one?
   * Useful for tracking ownership/custody changes.
   */
  current: z.boolean().optional(),
  /** Date range of this holding. */
  from: FuzzyDate.optional(),
  to: FuzzyDate.optional(),
  notes: z.string().optional(),
});

export type Holding = z.infer<typeof Holding>;

// ═════════════════════════════════════════════
// §16. Exhibition record (NEW)
// ═════════════════════════════════════════════

/**
 * A single exhibition event in the work's history.
 * For paintings, sculptures, and other exhibited works.
 */
const ExhibitionRecord = z.object({
  title: NonEmpty,
  venue: z.string().optional(),
  location: z.string().optional(),
  dateStart: FuzzyDate.optional(),
  dateEnd: FuzzyDate.optional(),
  catalogRef: z.string().optional(),
  notes: z.string().optional(),
});

export type ExhibitionRecord = z.infer<typeof ExhibitionRecord>;

// ═════════════════════════════════════════════
// §17. Media context (NEW)
// ═════════════════════════════════════════════

/**
 * Context specific to visual arts, music, and time-based media.
 * Parallel to OralContext — optional on any ResearchSource.
 *
 * This covers the metadata that makes visual and audio/video
 * sources researchable: physical description, holding information,
 * exhibition history, and technical details for time-based works.
 */
const MediaContext = z.object({
  physical: PhysicalDescription.optional(),
  holdings: z.array(Holding).optional(),
  exhibitions: z.array(ExhibitionRecord).optional(),
  fixations: z.array(FixationLayer).optional(),

  // ── Time-based media specifics ──
  /**
   * Duration in seconds (also available in Dimensions, but
   * repeated here for convenience on time-based sources).
   */
  durationSeconds: z.number().positive().optional(),
  /** Aspect ratio as a string: "16:9", "4:3", "2.39:1". */
  aspectRatio: z.string().optional(),
  /** Color mode. */
  colorMode: z.literal(["color", "black-and-white", "tinted", "mixed"]).optional(),
  /** Resolution or format: "35mm", "4K", "1080p", "78 rpm", etc. */
  format: z.string().optional(),

  // ── Music specifics ──
  /**
   * Key signature: "C major", "A minor", "atonal", etc.
   * Free text — no enforced music theory format.
   */
  key: z.string().optional(),
  /** Tempo indication: "Allegro", "120 BPM", etc. */
  tempo: z.string().optional(),
  /**
   * Instrumentation or ensemble.
   * E.g. "string quartet", "full orchestra", "solo piano",
   *      "voice and guitar", "electronic".
   */
  instrumentation: z.string().optional(),
  /**
   * Named structural divisions: movements, acts, scenes, tracks.
   * Each entry is a label; use Locator to point at specific ones.
   */
  sections: z
    .array(
      z.object({
        label: NonEmpty,
        durationSeconds: z.number().positive().optional(),
      }),
    )
    .optional(),

  notes: z.string().optional(),
});

export type MediaContext = z.infer<typeof MediaContext>;

// ═════════════════════════════════════════════
// §18. The source record
// ═════════════════════════════════════════════

const ResearchSource = z.object({
  id: z.uuidv4(),

  // ── Core ──
  kind: SourceKind,
  title: NonEmpty,
  subtitle: z.string().optional(),
  abstract: z.string().optional(),
  language: LanguageTag.optional(),
  attribution: Attribution,
  datePublished: FuzzyDate.optional(),
  dateAccepted: FuzzyDate.optional(),
  /** Date the work was created (may differ from publication). */
  dateCreated: FuzzyDate.optional(),

  // ── Structured sub-objects ──
  identifiers: SourceIdentifiers.optional(),
  publication: PublicationContext.optional(),
  access: AccessInfo.optional(),
  ethics: EthicsInfo.optional(),
  provenance: Provenance,
  quality: QualitySignals.optional(),

  // ── Domain-specific context ──
  oralContext: OralContext.optional(),
  mediaContext: MediaContext.optional(),

  // ── Content-level data ──
  keywords: z.array(z.string()).optional(),
  topics: z.array(z.string()).optional(),
  claims: z.array(Claim).optional(),
  annotations: z.array(Annotation).optional(),

  // ── Graph edges ──
  relations: z.array(SourceRelation).optional(),

  // ── Extensibility ──
  meta: z.record(z.string(), z.unknown()).optional(),
});

export type ResearchSource = z.infer<typeof ResearchSource>;

// ═════════════════════════════════════════════
// §19. The research map
// ═════════════════════════════════════════════

const ResearchMap = z.object({
  id: z.uuidv4(),
  name: NonEmpty,
  description: z.string().optional(),
  createdAt: FuzzyDate,
  updatedAt: FuzzyDate,
  owner: z.string().optional(),
  schemaVersion: z.literal("3.0.0"),
  sources: z.array(ResearchSource),
});

export type ResearchMap = z.infer<typeof ResearchMap>;

// ═════════════════════════════════════════════
// Exports
// ═════════════════════════════════════════════

export {
  // Atoms
  ISODateish,
  FuzzyDate,
  ExactDate,
  ApproximateDate,
  NonEmpty,
  LanguageTag,
  // Identifiers
  SourceIdentifiers as SourceIdentifiersSchema,
  // Agents & attribution
  Agent as AgentSchema,
  AgentRole,
  CommunalAttribution as CommunalAttributionSchema,
  Attribution as AttributionSchema,
  // Taxonomy
  SourceKind as SourceKindSchema,
  // Publication
  PublicationContext as PublicationContextSchema,
  // Access & ethics
  AccessLevel,
  AccessInfo as AccessInfoSchema,
  ConsentStatus,
  SensitivityLevel,
  EthicsInfo as EthicsInfoSchema,
  // Provenance
  Provenance as ProvenanceSchema,
  RetrievalMethod,
  // Quality
  QualitySignals as QualitySignalsSchema,
  PeerReviewStatus,
  TransmissionFidelity,
  // Locator
  Locator as LocatorSchema,
  LocatorPage,
  LocatorTime,
  LocatorSpatial,
  LocatorSection,
  LocatorFree,
  // Content
  Claim as ClaimSchema,
  ClaimStatus,
  Annotation as AnnotationSchema,
  // Relations
  RelationType,
  SourceRelation as SourceRelationSchema,
  // Fixation
  FixationMedium,
  FixationLayer as FixationLayerSchema,
  // Transmission
  TransmissionLink as TransmissionLinkSchema,
  TransmissionChain as TransmissionChainSchema,
  // Oral context
  OralContext as OralContextSchema,
  // Physical / holdings / exhibitions / media
  Dimensions as DimensionsSchema,
  PhysicalDescription as PhysicalDescriptionSchema,
  Holding as HoldingSchema,
  ExhibitionRecord as ExhibitionRecordSchema,
  MediaContext as MediaContextSchema,
  // Top-level
  ResearchSource as ResearchSourceSchema,
  ResearchMap as ResearchMapSchema,
};
