/**
 * ─────────────────────────────────────────────────────────────────────────────
 * DISCLAIMER
 * ─────────────────────────────────────────────────────────────────────────────
 * No information within this file should be taken for granted. Any statement
 * or premise not backed by a real logical definition or verifiable reference
 * may be invalid, erroneous, or a hallucination.
 *
 * This file is a manual Zod v4 translation of the JSON Schema (draft 2020-12)
 * for the Unified Generative Video Project Package v3.0.0.
 *
 * Source: claude-unified-video-project-v3.schema.json
 * Zod version: 4.x (tested against 4.3.6)
 *
 * For known semantic differences between this Zod schema and the original
 * JSON Schema, see DIFFERENCES.md.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { z } from "zod";

// ═══════════════════════════════════════════════════════════════════════════════
// §1  PRIMITIVE / UTILITY TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const IdentifierSchema = z
  .string()
  .regex(/^[A-Za-z0-9._:-]{1,200}$/);

export const SemVerSchema = z
  .string()
  .regex(/^\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?(?:\+[A-Za-z0-9.-]+)?$/);

export const ISOTimestampSchema = z.iso.datetime();

/** additionalProperties: true → looseObject (passthrough unknown keys) */
export const ExtensionsSchema = z.looseObject({});

/** additionalProperties: { type: "string" } → record<string, string> */
export const StringMapSchema = z.record(z.string(), z.string());

// ═══════════════════════════════════════════════════════════════════════════════
// §2  COMMON STRUCTURAL TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const ContributorSchema = z.strictObject({
  id: IdentifierSchema.optional(),
  name: z.string(),
  role: z.string().optional(),
  organization: z.string().optional(),
  contact: z.string().optional(),
});

export const VersionSelectorSchema = z.strictObject({
  mode: z.enum([
    "exact",
    "latest",
    "latestApproved",
    "latestPublished",
    "semverRange",
    "tag",
    "branch",
  ]),
  value: z.string().optional(),
});

export const EntityRefSchema = z
  .strictObject({
    id: IdentifierSchema.optional(),
    logicalId: IdentifierSchema.optional(),
    versionSelector: VersionSelectorSchema.optional(),
    role: z.string().optional(),
    notes: z.string().optional(),
  })
  .refine((v) => v.id !== undefined || v.logicalId !== undefined, {
    message: "EntityRef requires at least one of 'id' or 'logicalId'",
    path: ["id"],
  });

export const ChecksumSchema = z.strictObject({
  algorithm: z.enum(["sha256", "sha512", "md5", "blake3"]),
  value: z.string(),
});

export const ApprovalSchema = z.strictObject({
  status: z
    .enum(["unreviewed", "needs_changes", "approved", "rejected", "waived"])
    .optional(),
  approvedBy: z.array(ContributorSchema).optional(),
  approvedAt: ISOTimestampSchema.optional(),
  notes: z.string().optional(),
});

export const ApprovalRecordSchema = z.strictObject({
  role: z.string(),
  status: z.enum(["pending", "approved", "rejected", "waived"]),
  approvedBy: ContributorSchema.optional(),
  approvedAt: ISOTimestampSchema.optional(),
  deadline: ISOTimestampSchema.optional(),
  notes: z.string().optional(),
});

export const RightsSchema = z.strictObject({
  owner: z.string().optional(),
  license: z.string().optional(),
  usageRestrictions: z.array(z.string()).optional(),
  expiresAt: ISOTimestampSchema.optional(),
  talentRelease: z.boolean().optional(),
  territory: z.array(z.string()).optional(),
});

export const VersionInfoSchema = z.strictObject({
  number: SemVerSchema,
  state: z.enum([
    "draft",
    "in_progress",
    "generating",
    "review",
    "changes_requested",
    "approved",
    "published",
    "archived",
    "deprecated",
  ]),
  branch: z.string().optional(),
  labels: z.array(z.string()).optional(),
  changeSummary: z.string().optional(),
  derivedFrom: z.array(EntityRefSchema).optional(),
  supersedes: z.array(EntityRefSchema).optional(),
  contentHash: z.string().optional(),
  releasedAt: ISOTimestampSchema.optional(),
});

export const CommentSchema = z.strictObject({
  commentId: IdentifierSchema,
  authorRef: EntityRefSchema.optional(),
  createdAt: ISOTimestampSchema.optional(),
  updatedAt: ISOTimestampSchema.optional(),
  timecodeRef: z.lazy(() => TimeRangeSchema).optional(),
  entityRef: EntityRefSchema.optional(),
  body: z.string(),
  parentCommentId: IdentifierSchema.optional(),
  resolved: z.boolean().optional(),
});

export const FuzzyDateSchema = z.strictObject({
  kind: z.enum(["exact", "approximate", "range", "unknown"]),
  exact: ISOTimestampSchema.optional(),
  label: z.string().optional(),
  rangeStart: ISOTimestampSchema.optional(),
  rangeEnd: ISOTimestampSchema.optional(),
  confidence: z.number().gte(0).lte(1).optional(),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §3  TECHNICAL / TEMPORAL TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const FrameRateSchema = z.strictObject({
  fps: z.number().gt(0),
  mode: z.enum(["constant", "variable"]).optional(),
  timebaseNumerator: z.number().int().gte(1).optional(),
  timebaseDenominator: z.number().int().gte(1).optional(),
});

export const ResolutionSchema = z.strictObject({
  preset: z.enum(["4K_UHD", "2K_DCI", "1080p", "720p", "480p", "custom"]).optional(),
  widthPx: z.number().int().gte(1),
  heightPx: z.number().int().gte(1),
  pixelAspectRatio: z.number().gt(0).optional(),
});

export const AspectRatioSchema = z.strictObject({
  preset: z.enum(["16:9", "9:16", "4:3", "1:1", "2.35:1", "2.39:1", "custom"]).optional(),
  expression: z.string(),
  numerator: z.number().int().gte(1).optional(),
  denominator: z.number().int().gte(1).optional(),
});

export const TimecodeSchema = z.strictObject({
  value: z.string().regex(/^\d{2}:\d{2}:\d{2}[:;]\d{2}$/),
  dropFrame: z.boolean().optional(),
});

export const TimeRangeSchema = z
  .strictObject({
    startSec: z.number().gte(0).optional(),
    endSec: z.number().gte(0).optional(),
    durationSec: z.number().gte(0).optional(),
    startTimecode: TimecodeSchema.optional(),
    endTimecode: TimecodeSchema.optional(),
    toleranceFrames: z.number().int().gte(0).optional(),
  })
  .refine(
    (v) => {
      if (
        v.startSec !== undefined &&
        v.endSec !== undefined &&
        v.durationSec !== undefined
      ) {
        return Math.abs(v.endSec - v.startSec - v.durationSec) < 0.001;
      }
      if (v.startSec !== undefined && v.endSec !== undefined) {
        return v.endSec >= v.startSec;
      }
      return true;
    },
    {
      message:
        "TimeRange: when startSec, endSec, and durationSec are all present, " +
        "endSec - startSec must equal durationSec (±1ms). " +
        "When startSec and endSec are present, endSec must be >= startSec.",
      path: ["durationSec"],
    }
  );

export const TemporalConsistencySchema = z.strictObject({
  required: z.boolean(),
  minConsistencyScore: z.number().gte(0).lte(1).optional(),
  maxFlickerScore: z.number().gte(0).optional(),
  maxIdentityDriftScore: z.number().gte(0).optional(),
  strategies: z.array(z.string()).optional(),
  anchorRefs: z.array(EntityRefSchema).optional(),
});

export const CharacterCoherenceSchema = z.strictObject({
  required: z.boolean(),
  characterRefs: z.array(EntityRefSchema).optional(),
  minSimilarityScore: z.number().gte(0).lte(1).optional(),
  lockedAttributes: z.array(z.string()).optional(),
  anchorRefs: z.array(EntityRefSchema).optional(),
});

export const LightingGuidelinesSchema = z.strictObject({
  mood: z.string().optional(),
  style: z.string().optional(),
  keyToFillRatio: z.number().gt(0).optional(),
  backlightRatio: z.number().gte(0).optional(),
  colorTemperatureKelvin: z.number().int().gte(1000).optional(),
  contrastStyle: z.string().optional(),
  referenceRefs: z.array(EntityRefSchema).optional(),
});

export const StyleGuidelinesSchema = z.strictObject({
  genres: z.array(z.string()).optional(),
  adjectives: z.array(z.string()).optional(),
  palette: z.array(z.string()).optional(),
  textureDescriptors: z.array(z.string()).optional(),
  cameraLanguage: z.string().optional(),
  editingLanguage: z.string().optional(),
  referenceRefs: z.array(EntityRefSchema).optional(),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §4  SPATIAL / 3D TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const Position3DSchema = z.strictObject({
  x: z.number(),
  y: z.number(),
  z: z.number(),
});

export const QuaternionSchema = z.strictObject({
  x: z.number(),
  y: z.number(),
  z: z.number(),
  w: z.number(),
});

export const EulerAnglesDegSchema = z.strictObject({
  pitch: z.number().optional(),
  yaw: z.number().optional(),
  roll: z.number().optional(),
  order: z.string().optional(),
});

export const Scale3DSchema = z.strictObject({
  x: z.number().optional(),
  y: z.number().optional(),
  z: z.number().optional(),
});

export const Orientation3DSchema = z.strictObject({
  quaternion: QuaternionSchema.optional(),
  eulerDeg: EulerAnglesDegSchema.optional(),
  lookAtTarget: Position3DSchema.optional(),
  lookAtUpHint: Position3DSchema.optional(),
});

export const Transform3DSchema = z.strictObject({
  position: Position3DSchema.optional(),
  orientation: Orientation3DSchema.optional(),
  scale: Scale3DSchema.optional(),
  matrix4x4: z.array(z.number()).optional(),
});

export const BoundingVolumeSchema = z.strictObject({
  volumeType: z.enum(["aabb", "sphere"]),
  aabbMin: Position3DSchema.optional(),
  aabbMax: Position3DSchema.optional(),
  sphereCenter: Position3DSchema.optional(),
  sphereRadiusM: z.number().gt(0).optional(),
});

export const CoordinateSystemSchema = z.strictObject({
  handedness: z.enum(["right", "left"]),
  upAxis: z.enum(["+Y", "-Y", "+Z", "-Z"]),
  unitM: z.number().gt(0),
  forwardAxis: z.enum(["+X", "-X", "+Y", "-Y", "+Z", "-Z"]).optional(),
  notes: z.string().optional(),
});

export const SpatialAnchorSchema = z.strictObject({
  anchorId: IdentifierSchema,
  name: z.string(),
  position: Position3DSchema,
  orientation: Orientation3DSchema.optional(),
  radiusM: z.number().optional(),
  anchorType: z.enum(["landmark", "action_line", "staging_mark", "entry_point", "sightline", "eyeline", "pov", "custom"]).optional(),
  linkedAnchorId: IdentifierSchema.optional(),
  persistAcrossShots: z.boolean().optional(),
});

export const PlacementKeyframeSchema = z.strictObject({
  timeSec: z.number(),
  transform: Transform3DSchema,
  interpolation: z.string().optional(),
});

export const SpatialPlacementSchema = z.strictObject({
  placementId: IdentifierSchema,
  entityRef: EntityRefSchema,
  transform: Transform3DSchema,
  bounds: BoundingVolumeSchema.optional(),
  motionPath: z.array(PlacementKeyframeSchema).optional(),
  interactionZoneRadiusM: z.number().optional(),
  facingDirection: Position3DSchema.optional(),
  notes: z.string().optional(),
});

export const SpatialRuleSchema = z.strictObject({
  ruleType: z.string(),
  subjectRef: EntityRefSchema.optional(),
  targetRef: EntityRefSchema.optional(),
  distanceMinM: z.number().optional(),
  distanceMaxM: z.number().optional(),
  angleToleranceDeg: z.number().optional(),
  severity: z.string().optional(),
  notes: z.string().optional(),
});

export const SpatialConsistencySchema = z.strictObject({
  required: z.boolean(),
  rules: z.array(SpatialRuleSchema).optional(),
  maxPositionDriftM: z.number().optional(),
  enforce180DegreeRule: z.boolean().optional(),
  enforceScreenDirection: z.boolean().optional(),
  anchorRefs: z.array(EntityRefSchema).optional(),
  strategies: z.array(z.string()).optional(),
});

export const CameraKeyframeSchema = z.strictObject({
  timeSec: z.number(),
  transform: Transform3DSchema,
  interpolation: z.string().optional(),
  easeIn: z.number().optional(),
  easeOut: z.number().optional(),
  focalLengthMm: z.number().optional(),
  focusDistanceM: z.number().optional(),
});

export const CameraExtrinsicsSchema = z.strictObject({
  transform: Transform3DSchema.optional(),
  motionPath: z.array(CameraKeyframeSchema).optional(),
  constraintTarget: EntityRefSchema.optional(),
  constraintMode: z.string().optional(),
  constraintOffsetM: Position3DSchema.optional(),
});

export const SceneSpaceSchema = z.strictObject({
  coordinateSystem: CoordinateSystemSchema,
  bounds: BoundingVolumeSchema.optional(),
  placements: z.array(SpatialPlacementSchema).optional(),
  spatialAnchors: z.array(SpatialAnchorSchema).optional(),
  gravityVector: Position3DSchema.optional(),
  floorPlaneCoord: z.number().optional(),
  universeRef: EntityRefSchema.optional(),
  sceneOriginInUniverse: Transform3DSchema.optional(),
  extensions: ExtensionsSchema.optional(),
});

export const SharedSpatialUniverseSchema = z.strictObject({
  universeId: IdentifierSchema,
  name: z.string(),
  description: z.string().optional(),
  coordinateSystem: CoordinateSystemSchema,
  bounds: BoundingVolumeSchema.optional(),
  landmarks: z.array(SpatialAnchorSchema).optional(),
  version: VersionInfoSchema.optional(),
  extensions: ExtensionsSchema.optional(),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §5  QUALITY / VALIDATION TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const MotionBlurControlSchema = z.strictObject({
  enabled: z.boolean().optional(),
  shutterAngleDegrees: z.number().gte(0).optional(),
  syntheticAllowed: z.boolean().optional(),
});

export const CompressionControlsSchema = z.strictObject({
  codec: z.string().optional(),
  profile: z.string().optional(),
  bitrateMbps: z.number().gte(0).optional(),
  maxBitrateMbps: z.number().gte(0).optional(),
  gopLength: z.number().int().gte(1).optional(),
  crf: z.number().gte(0).lte(63).optional(),
});

export const VideoQualityControlsSchema = z.strictObject({
  colorGradingIntent: z.string().optional(),
  lutRefs: z.array(EntityRefSchema).optional(),
  motionBlur: MotionBlurControlSchema.optional(),
  denoiseLevel: z.number().gte(0).optional(),
  sharpenLevel: z.number().gte(0).optional(),
  stabilizationMaxCropPercent: z.number().gte(0).lte(100).optional(),
  antiFlicker: z.boolean().optional(),
  maxNoiseLevel: z.number().gte(0).optional(),
  continuityChecks: z.array(z.string()).optional(),
  compression: CompressionControlsSchema.optional(),
});

export const AudioQualityControlsSchema = z.strictObject({
  sampleRateHz: z.number().int().gte(1).optional(),
  bitDepth: z.number().int().gte(1).optional(),
  channelLayout: z.string().optional(),
  loudnessIntegratedLUFS: z.number().optional(),
  truePeakDbTP: z.number().optional(),
  dialogIntelligibilityMinScore: z.number().gte(0).lte(1).optional(),
});

export const ValidationRuleSchema = z.strictObject({
  id: IdentifierSchema.optional(),
  name: z.string(),
  severity: z.enum(["info", "warning", "error"]).optional(),
  metric: z.string().optional(),
  operator: z
    .enum(["eq", "neq", "gt", "gte", "lt", "lte", "in", "nin", "matches", "exists"])
    .optional(),
  targetValue: z.unknown().optional(),
  expression: z.string().optional(),
  notes: z.string().optional(),
  extensions: ExtensionsSchema.optional(),
});

export const QCResultSchema = z.strictObject({
  metric: z.string(),
  actualValue: z.unknown().optional(),
  expectedValue: z.unknown().optional(),
  pass: z.boolean(),
  severity: z.enum(["info", "warning", "error"]).optional(),
  measuredAt: ISOTimestampSchema.optional(),
  notes: z.string().optional(),
  evidenceRefs: z.array(EntityRefSchema).optional(),
});

export const QaCheckSchema = z.strictObject({
  name: z.string(),
  score: z.number().optional(),
  pass: z.boolean(),
  notes: z.string().optional(),
  evidenceRefs: z.array(EntityRefSchema).optional(),
});

export const QaGateSchema = z.strictObject({
  requiredChecks: z.array(z.string()),
  passThreshold: z.number(),
  checks: z.array(QaCheckSchema).optional(),
  overallPass: z.boolean().optional(),
  evaluatedAt: ISOTimestampSchema.optional(),
});

export const QualityProfileSchema = z.strictObject({
  name: z.string(),
  video: z
    .strictObject({
      resolution: ResolutionSchema.optional(),
      aspectRatio: AspectRatioSchema.optional(),
      frameRate: FrameRateSchema.optional(),
      scanType: z.string().optional(),
      bitDepth: z.number().int().gte(1).optional(),
      colorSpace: z.string().optional(),
      dynamicRange: z.string().optional(),
      runtimeTargetSec: z.number().gt(0).optional(),
      runtimeToleranceSec: z.number().gte(0).optional(),
      temporalConsistency: TemporalConsistencySchema.optional(),
      characterCoherence: CharacterCoherenceSchema.optional(),
      lighting: LightingGuidelinesSchema.optional(),
      style: StyleGuidelinesSchema.optional(),
      qualityControls: VideoQualityControlsSchema.optional(),
      spatialConsistency: SpatialConsistencySchema.optional(),
    })
    .optional(),
  audio: AudioQualityControlsSchema.optional(),
  validationRules: z.array(ValidationRuleSchema).optional(),
  extensions: ExtensionsSchema.optional(),
});

export const AccessibilityConfigSchema = z.strictObject({
  wcagLevel: z.string().optional(),
  closedCaptions: z.boolean().optional(),
  openCaptions: z.boolean().optional(),
  audioDescriptionRef: EntityRefSchema.optional(),
  signLanguageRef: EntityRefSchema.optional(),
  notes: z.string().optional(),
});

export const LocalizationConfigSchema = z.strictObject({
  language: z.string(),
  subtitleTrackRefs: z.array(EntityRefSchema).optional(),
  dubbedAudioRef: EntityRefSchema.optional(),
  adaptedMarketingRef: EntityRefSchema.optional(),
  notes: z.string().optional(),
});

export const PlatformDeliverySchema = z.strictObject({
  platform: z.string(),
  format: z.string().optional(),
  aspectRatio: AspectRatioSchema.optional(),
  resolution: ResolutionSchema.optional(),
  frameRate: FrameRateSchema.optional(),
  maxDurationSec: z.number().optional(),
  publishSchedule: FuzzyDateSchema.optional(),
  metadata: StringMapSchema.optional(),
});

export const ComplianceSchema = z.strictObject({
  classifications: z.array(z.string()).optional(),
  certifications: z.array(z.string()).optional(),
  notes: z.string().optional(),
  reviewedAt: ISOTimestampSchema.optional(),
  reviewedBy: ContributorSchema.optional(),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §6  GENERATION / PROVENANCE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const ModelDescriptorSchema = z.strictObject({
  provider: z.string().optional(),
  tool: z.string().optional(),
  modelId: z.string().optional(),
  modelVersion: z.string().optional(),
  checkpoint: z.string().optional(),
  endpoint: z.string().optional(),
  adapterRefs: z.array(EntityRefSchema).optional(),
  parameters: z.looseObject({}).optional(),
});

export const ReferenceInputSchema = z.strictObject({
  ref: EntityRefSchema,
  role: z.string().optional(),
  weight: z.number().gte(0).optional(),
  lockAttributes: z.array(z.string()).optional(),
});

export const ConsistencyAnchorSchema = z.strictObject({
  anchorType: z.enum([
    "character",
    "style",
    "environment",
    "prop",
    "camera",
    "spatial",
    "custom",
  ]),
  name: z.string().optional(),
  ref: EntityRefSchema.optional(),
  weight: z.number().gte(0).optional(),
  lockLevel: z.enum(["soft", "medium", "hard"]).optional(),
  attributes: z.array(z.string()).optional(),
});

export const AdapterInputSchema = z.strictObject({
  adapterType: z.string(),
  ref: EntityRefSchema.optional(),
  weight: z.number().gte(0).optional(),
  parameters: z.looseObject({}).optional(),
});

export const LogEntrySchema = z.strictObject({
  timestamp: ISOTimestampSchema.optional(),
  level: z.string().optional(),
  message: z.string(),
  data: z.looseObject({}).optional(),
});

export const PromptFragmentSchema = z.strictObject({
  fragment: z.string(),
  weight: z.number().optional(),
  insertionOrder: z.number().int().optional(),
  category: z.string().optional(),
  locked: z.boolean().optional(),
});

export const PromptRecordSchema = z.strictObject({
  versionId: IdentifierSchema,
  prompt: z.string(),
  negativePrompt: z.string().optional(),
  createdAt: ISOTimestampSchema.optional(),
  parentVersionId: IdentifierSchema.optional(),
  changeNote: z.string().optional(),
});

export const GenerationCostSchema = z.strictObject({
  currency: z.string(),
  amount: z.number(),
  provider: z.string().optional(),
  units: z.string().optional(),
  unitCount: z.number().optional(),
  billedAt: ISOTimestampSchema.optional(),
});

export const RetryConfigSchema = z.strictObject({
  maxAttempts: z.number().int(),
  backoffStrategy: z.string().optional(),
  initialDelayMs: z.number().int().optional(),
  maxDelayMs: z.number().int().optional(),
  fallbackTool: z.string().optional(),
  retryOnStatuses: z.array(z.string()).optional(),
});

export const AsyncConfigSchema = z.strictObject({
  mode: z.string(),
  pollingIntervalMs: z.number().int().optional(),
  webhookUrl: z.string().optional(),
  timeoutMs: z.number().int().optional(),
});

export const GenerationStepSchema = z.strictObject({
  stepId: IdentifierSchema,
  operationType: z.string(),
  provider: z.string().optional(),
  tool: z.string().optional(),
  model: ModelDescriptorSchema.optional(),
  executionEnvironment: z.looseObject({}).optional(),
  inputRefs: z.array(EntityRefSchema).optional(),
  outputRefs: z.array(EntityRefSchema).optional(),
  prompt: z.string().optional(),
  negativePrompt: z.string().optional(),
  systemPrompt: z.string().optional(),
  structuredPrompt: z.looseObject({}).optional(),
  promptHistory: z.array(PromptRecordSchema).optional(),
  seed: z.union([z.number().int(), z.string()]).optional(),
  guidanceScale: z.number().optional(),
  inferenceSteps: z.number().int().gte(1).optional(),
  sampler: z.string().optional(),
  scheduler: z.string().optional(),
  strength: z.number().optional(),
  cfg: z.number().optional(),
  durationSec: z.number().gte(0).optional(),
  resolution: ResolutionSchema.optional(),
  aspectRatio: AspectRatioSchema.optional(),
  frameRate: FrameRateSchema.optional(),
  referenceAssets: z.array(ReferenceInputSchema).optional(),
  consistencyAnchors: z.array(ConsistencyAnchorSchema).optional(),
  adapterInputs: z.array(AdapterInputSchema).optional(),
  voiceSettings: z.looseObject({}).optional(),
  cameraMotionHints: z.looseObject({}).optional(),
  parameters: z.looseObject({}).optional(),
  costEstimate: GenerationCostSchema.optional(),
  costActual: GenerationCostSchema.optional(),
  retryConfig: RetryConfigSchema.optional(),
  asyncConfig: AsyncConfigSchema.optional(),
  status: z
    .enum(["pending", "running", "succeeded", "failed", "cancelled"])
    .optional(),
  metrics: z.looseObject({}).optional(),
  logs: z.array(LogEntrySchema).optional(),
  extensions: ExtensionsSchema.optional(),
});

export const GenerationManifestSchema = z.strictObject({
  mode: z
    .enum([
      "manual",
      "ai_generated",
      "hybrid",
      "captured",
      "licensed",
      "procedural",
      "unknown",
    ])
    .optional(),
  steps: z.array(GenerationStepSchema).optional(),
  consistencyAnchors: z.array(ConsistencyAnchorSchema).optional(),
  reproducibility: z
    .strictObject({
      deterministic: z.boolean().optional(),
      requiresExactModelVersion: z.boolean().optional(),
      requiresExactSeed: z.boolean().optional(),
      notes: z.string().optional(),
    })
    .optional(),
  extensions: ExtensionsSchema.optional(),
});

export const FileObjectSchema = z.strictObject({
  uri: z.string(),
  storageProvider: z.string().optional(),
  mediaType: z.string(),
  fileRole: z.string().optional(),
  byteSize: z.number().int().gte(0).optional(),
  checksum: ChecksumSchema.optional(),
  containerFormat: z.string().optional(),
  codec: z.string().optional(),
  width: z.number().int().gte(1).optional(),
  height: z.number().int().gte(1).optional(),
  durationSec: z.number().gte(0).optional(),
  frameRate: FrameRateSchema.optional(),
  sampleRateHz: z.number().int().gte(1).optional(),
  bitDepth: z.number().int().gte(1).optional(),
  channelLayout: z.string().optional(),
  language: z.string().optional(),
  metadata: z.looseObject({}).optional(),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §7  BASE ENTITY
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * v3 BaseEntity (23 props).
 *
 * Changes from v1:
 * - qualityProfile (inline QualityProfile) → qualityProfileRef (EntityRef)
 * - +approvalChain: array<ApprovalRecord>
 * - +comments: array<Comment>
 */
export const BaseEntityShape = {
  id: IdentifierSchema,
  logicalId: IdentifierSchema,
  entityType: z.string(),
  name: z.string(),
  description: z.string().optional(),
  status: z
    .enum([
      "draft",
      "in_progress",
      "review",
      "approved",
      "published",
      "archived",
      "deprecated",
    ])
    .optional(),
  tags: z.array(z.string()).optional(),
  createdAt: ISOTimestampSchema.optional(),
  updatedAt: ISOTimestampSchema.optional(),
  createdBy: z.array(ContributorSchema).optional(),
  owners: z.array(ContributorSchema).optional(),
  version: VersionInfoSchema,
  approval: ApprovalSchema.optional(),
  approvalChain: z.array(ApprovalRecordSchema).optional(),
  qualityProfileRef: EntityRefSchema.optional(),
  sourceRefs: z.array(EntityRefSchema).optional(),
  dependencyRefs: z.array(EntityRefSchema).optional(),
  generation: GenerationManifestSchema.optional(),
  storage: z.array(FileObjectSchema).optional(),
  rights: RightsSchema.optional(),
  comments: z.array(CommentSchema).optional(),
  metadata: z.looseObject({}).optional(),
  extensions: ExtensionsSchema.optional(),
} as const;

export const BaseEntityObject = z.object(BaseEntityShape);

// ═══════════════════════════════════════════════════════════════════════════════
// §8  OPERATIONS (OperationBase + 10 discriminated subtypes)
// ═══════════════════════════════════════════════════════════════════════════════

const OperationBaseShape = {
  opId: IdentifierSchema,
  opType: z.string(),
  compatibleRuntimes: z.array(z.string()).optional(),
  runtimeHints: z.looseObject({}).optional(),
} as const;

const OperationBaseObject = z.object(OperationBaseShape);

export const ConcatOpSchema = OperationBaseObject.extend({
  opType: z.literal("concat"),
  clipRefs: z.array(EntityRefSchema),
  method: z.string().optional(),
  outputRef: EntityRefSchema.optional(),
}).strict();

export const OverlayOpSchema = OperationBaseObject.extend({
  opType: z.literal("overlay"),
  backgroundRef: EntityRefSchema,
  foregroundRef: EntityRefSchema,
  transform: z.lazy(() => TransformSchema).optional(),
  timeRange: TimeRangeSchema.optional(),
  outputRef: EntityRefSchema.optional(),
}).strict();

export const ColorGradeOpSchema = OperationBaseObject.extend({
  opType: z.literal("colorGrade"),
  inputRef: EntityRefSchema,
  lutRef: EntityRefSchema.optional(),
  intent: z.string().optional(),
  strength: z.number().optional(),
  outputRef: EntityRefSchema.optional(),
}).strict();

export const AudioMixTrackSchema = z.strictObject({
  audioRef: EntityRefSchema,
  gainDb: z.number().optional(),
  pan: z.number().optional(),
  timeRange: TimeRangeSchema.optional(),
  syncPoints: z.array(z.lazy(() => SyncPointSchema)).optional(),
});

export const AudioMixOpSchema = OperationBaseObject.extend({
  opType: z.literal("audioMix"),
  tracks: z.array(AudioMixTrackSchema),
  outputRef: EntityRefSchema.optional(),
}).strict();

export const TransitionSpecSchema = z.strictObject({
  type: z.string().optional(),
  durationSec: z.number().gte(0).optional(),
  parameters: z.looseObject({}).optional(),
});

export const TransitionOpSchema = OperationBaseObject.extend({
  opType: z.literal("transition"),
  fromRef: EntityRefSchema,
  toRef: EntityRefSchema,
  spec: TransitionSpecSchema,
  outputRef: EntityRefSchema.optional(),
}).strict();

export const FilterOpSchema = OperationBaseObject.extend({
  opType: z.literal("filter"),
  inputRef: EntityRefSchema,
  filterType: z.string(),
  parameters: z.looseObject({}).optional(),
  outputRef: EntityRefSchema.optional(),
}).strict();

export const EncodeOpSchema = OperationBaseObject.extend({
  opType: z.literal("encode"),
  inputRef: EntityRefSchema,
  compression: CompressionControlsSchema,
  targetQualityProfileRef: EntityRefSchema.optional(),
  outputRef: EntityRefSchema.optional(),
}).strict();

export const ManimConfigSchema = z.strictObject({
  sceneClass: z.string().optional(),
  rendererBackend: z.string().optional(),
  outputFormat: z.string().optional(),
  parameters: z.looseObject({}).optional(),
});

export const ManimOpSchema = OperationBaseObject.extend({
  opType: z.literal("manim"),
  sceneClass: z.string(),
  manimConfig: ManimConfigSchema,
  outputRef: EntityRefSchema.optional(),
}).strict();

export const RetimeSpecSchema = z.strictObject({
  speedPercent: z.number().gt(0).optional(),
  reverse: z.boolean().optional(),
  frameInterpolation: z.string().optional(),
  freezeFrames: z.array(z.number().gte(0)).optional(),
});

export const RetimeOpSchema = OperationBaseObject.extend({
  opType: z.literal("retime"),
  inputRef: EntityRefSchema,
  retime: RetimeSpecSchema,
  outputRef: EntityRefSchema.optional(),
}).strict();

export const CustomOpSchema = OperationBaseObject.extend({
  opType: z.literal("custom"),
  executor: z.string(),
  inputRefs: z.array(EntityRefSchema).optional(),
  outputRefs: z.array(EntityRefSchema).optional(),
  parameters: z.looseObject({}).optional(),
}).strict();

/**
 * Discriminated union of all operation types, discriminated on `opType`.
 * JSON Schema: Operation → oneOf[ConcatOp, OverlayOp, ...].
 */
export const OperationSchema = z.discriminatedUnion("opType", [
  ConcatOpSchema,
  OverlayOpSchema,
  ColorGradeOpSchema,
  AudioMixOpSchema,
  TransitionOpSchema,
  FilterOpSchema,
  EncodeOpSchema,
  ManimOpSchema,
  RetimeOpSchema,
  CustomOpSchema,
]);

// ═══════════════════════════════════════════════════════════════════════════════
// §9  WORKFLOW TYPES (WorkflowNodeBase + 7 discriminated subtypes)
// ═══════════════════════════════════════════════════════════════════════════════

const WorkflowNodeBaseShape = {
  nodeId: IdentifierSchema,
  name: z.string().optional(),
  nodeType: z.string(),
  inputs: z.array(EntityRefSchema).optional(),
  outputs: z.array(EntityRefSchema).optional(),
  retryPolicy: RetryConfigSchema.optional(),
  cacheKey: z.string().optional(),
  extensions: ExtensionsSchema.optional(),
} as const;

const WorkflowNodeBaseObject = z.object(WorkflowNodeBaseShape);

export const GenerationNodeSchema = WorkflowNodeBaseObject.extend({
  nodeType: z.literal("generation"),
  generationStep: GenerationStepSchema,
  model: ModelDescriptorSchema.optional(),
}).strict();

export const ApprovalNodeSchema = WorkflowNodeBaseObject.extend({
  nodeType: z.literal("approval"),
  role: z.string(),
  assigneeRefs: z.array(EntityRefSchema).optional(),
  deadline: ISOTimestampSchema.optional(),
  approvalStatus: z.string(),
  notes: z.string().optional(),
}).strict();

export const TransformNodeSchema = WorkflowNodeBaseObject.extend({
  nodeType: z.literal("transform"),
  operation: OperationSchema,
  executor: z.looseObject({}).optional(),
}).strict();

export const RenderNodeSchema = WorkflowNodeBaseObject.extend({
  nodeType: z.literal("render"),
  renderPlanRef: EntityRefSchema,
  executor: z.looseObject({}).optional(),
}).strict();

export const ValidationNodeSchema = WorkflowNodeBaseObject.extend({
  nodeType: z.literal("validation"),
  validationRules: z.array(ValidationRuleSchema),
  qaGate: QaGateSchema.optional(),
  qcResults: z.array(QCResultSchema).optional(),
}).strict();

export const NotificationNodeSchema = WorkflowNodeBaseObject.extend({
  nodeType: z.literal("notification"),
  channel: z.string(),
  recipients: z.array(z.string()).optional(),
  template: z.string().optional(),
  payload: z.looseObject({}).optional(),
}).strict();

export const CustomWorkflowNodeSchema = WorkflowNodeBaseObject.extend({
  nodeType: z.literal("custom"),
  executor: z.looseObject({}),
  parameters: z.looseObject({}).optional(),
}).strict();

/**
 * Discriminated union of all workflow node types, discriminated on `nodeType`.
 * JSON Schema: WorkflowNode → oneOf[GenerationNode, ApprovalNode, ...].
 */
export const WorkflowNodeSchema = z.discriminatedUnion("nodeType", [
  GenerationNodeSchema,
  ApprovalNodeSchema,
  TransformNodeSchema,
  RenderNodeSchema,
  ValidationNodeSchema,
  NotificationNodeSchema,
  CustomWorkflowNodeSchema,
]);

export const WorkflowEdgeSchema = z.strictObject({
  fromNodeId: IdentifierSchema,
  toNodeId: IdentifierSchema,
  condition: z.string().optional(),
  notes: z.string().optional(),
});

export const WorkflowGraphSchema = z.strictObject({
  workflowId: IdentifierSchema,
  name: z.string().optional(),
  status: z
    .enum(["pending", "running", "paused", "succeeded", "failed", "cancelled"])
    .optional(),
  nodes: z.array(WorkflowNodeSchema),
  edges: z.array(WorkflowEdgeSchema),
  runtimeHints: z.looseObject({}).optional(),
});

export const OrchestrationSchema = z.strictObject({
  workflows: z.array(WorkflowGraphSchema),
  extensions: ExtensionsSchema.optional(),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §10  PACKAGE / PROJECT / GOVERNANCE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const NamingConventionsSchema = z.strictObject({
  idPrefix: z.string().optional(),
  separator: z.string().optional(),
  caseStyle: z.string().optional(),
  fileNameTemplate: z.string().optional(),
  versionSuffix: z.boolean().optional(),
  extensions: ExtensionsSchema.optional(),
});

export const VersioningPolicySchema = z.strictObject({
  immutablePublishedVersions: z.boolean().optional(),
  defaultReferenceMode: z
    .enum([
      "exact",
      "latestApproved",
      "latestPublished",
      "semverRange",
      "tag",
      "branch",
    ])
    .optional(),
  requireContentHashForPublished: z.boolean().optional(),
  requireSupersedesForSameLogicalId: z.boolean().optional(),
  allowParallelBranches: z.boolean().optional(),
  approvalRequiredForDeliverables: z.boolean().optional(),
  notes: z.string().optional(),
});

export const GovernanceSchema = z.strictObject({
  namingConventions: NamingConventionsSchema.optional(),
  releaseCriteria: z.array(z.string()).optional(),
  validationRules: z.array(ValidationRuleSchema).optional(),
  extensions: ExtensionsSchema.optional(),
});

export const BudgetSchema = z.strictObject({
  currency: z.string().optional(),
  totalAmount: z.number().optional(),
  spentAmount: z.number().optional(),
  breakdown: z.looseObject({}).optional(),
});

export const TeamMemberSchema = z.strictObject({
  memberId: IdentifierSchema,
  name: z.string(),
  role: z.string(),
  permissions: z.array(z.string()).optional(),
  contact: z.string().optional(),
  organization: z.string().optional(),
});

export const TeamSchema = z.strictObject({
  members: z.array(TeamMemberSchema),
  extensions: ExtensionsSchema.optional(),
});

export const PackageInfoSchema = z.strictObject({
  packageId: IdentifierSchema,
  createdAt: ISOTimestampSchema,
  updatedAt: ISOTimestampSchema.optional(),
  scheduledStartDate: FuzzyDateSchema.optional(),
  scheduledDeliveryDate: FuzzyDateSchema.optional(),
  createdBy: z.array(ContributorSchema).optional(),
  schemaUri: z.string().optional(),
  versioningPolicy: VersioningPolicySchema,
  governance: GovernanceSchema.optional(),
  budget: BudgetSchema.optional(),
  compliance: ComplianceSchema.optional(),
  extensions: ExtensionsSchema.optional(),
});

export const ProjectEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("project"),
  summary: z.string().optional(),
  languages: z.array(z.string()).optional(),
  genres: z.array(z.string()).optional(),
  audiences: z.array(z.string()).optional(),
  targetRuntimeSec: z.number().gt(0),
  defaultQualityProfileRef: EntityRefSchema,
  globalCharacterRefs: z.array(EntityRefSchema).optional(),
  globalEnvironmentRefs: z.array(EntityRefSchema).optional(),
  globalStyleRefs: z.array(EntityRefSchema).optional(),
  governance: GovernanceSchema.optional(),
}).strict();

export const QualityProfileEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("qualityProfile"),
  profile: QualityProfileSchema,
}).strict();

// ═══════════════════════════════════════════════════════════════════════════════
// §11  STORY / SCRIPT / DIRECTOR TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const StoryBeatSchema = z.strictObject({
  beatId: IdentifierSchema,
  name: z.string(),
  order: z.number().int().gte(1),
  description: z.string().optional(),
  purpose: z.string().optional(),
  targetRange: TimeRangeSchema.optional(),
  scheduledRange: FuzzyDateSchema.optional(),
  sceneRefs: z.array(EntityRefSchema).optional(),
  emotionalObjective: z.string().optional(),
});

export const NarrativeArcSchema = z.strictObject({
  arcId: IdentifierSchema,
  name: z.string(),
  description: z.string().optional(),
  characterRefs: z.array(EntityRefSchema).optional(),
  startBeatRef: EntityRefSchema.optional(),
  endBeatRef: EntityRefSchema.optional(),
  trajectory: z.array(z.string()).optional(),
});

export const StoryEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("story"),
  logline: z.string(),
  synopsis: z.string().optional(),
  premise: z.string().optional(),
  themes: z.array(z.string()).optional(),
  tone: z.array(z.string()).optional(),
  beats: z.array(StoryBeatSchema),
  arcs: z.array(NarrativeArcSchema).optional(),
  sceneRefs: z.array(EntityRefSchema).optional(),
  marketingHooks: z.array(z.string()).optional(),
}).strict();

export const ScriptSegmentSchema = z.strictObject({
  segmentId: IdentifierSchema,
  order: z.number().int().gte(1),
  segmentType: z.enum([
    "scene_heading",
    "action",
    "dialogue",
    "parenthetical",
    "transition",
    "title_card",
    "voice_over",
    "on_screen_text",
    "custom",
  ]),
  sceneRef: EntityRefSchema.optional(),
  shotRef: EntityRefSchema.optional(),
  speakerRef: EntityRefSchema.optional(),
  text: z.string().optional(),
  spokenText: z.string().optional(),
  actionDescription: z.string().optional(),
  onScreenText: z.string().optional(),
  language: z.string().optional(),
  timing: TimeRangeSchema.optional(),
  performanceNotes: z.string().optional(),
  audioAssetRef: EntityRefSchema.optional(),
  subtitleText: z.string().optional(),
});

export const ScriptEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("script"),
  format: z.string().optional(),
  segments: z.array(ScriptSegmentSchema),
  sceneRefs: z.array(EntityRefSchema).optional(),
  language: z.string().optional(),
}).strict();

export const TargetedNoteSchema = z.strictObject({
  targetRef: EntityRefSchema.optional(),
  category: z.string().optional(),
  priority: z.enum(["low", "medium", "high", "critical"]).optional(),
  note: z.string(),
});

export const DirectorInstructionsEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("directorInstructions"),
  visionStatement: z.string(),
  mustHaves: z.array(z.string()).optional(),
  mustAvoid: z.array(z.string()).optional(),
  cameraLanguage: z.string().optional(),
  editingLanguage: z.string().optional(),
  performanceDirection: z.string().optional(),
  musicDirection: z.string().optional(),
  colorDirection: z.string().optional(),
  targetedNotes: z.array(TargetedNoteSchema).optional(),
  qualityRules: z.array(ValidationRuleSchema).optional(),
}).strict();

// ═══════════════════════════════════════════════════════════════════════════════
// §12  PRODUCTION TYPES (Character, Environment, Prop, Scene, Shot, StyleGuide)
// ═══════════════════════════════════════════════════════════════════════════════

export const VoiceProfileSchema = z.strictObject({
  voiceDescription: z.string().optional(),
  accent: z.string().optional(),
  pitchRange: z.string().optional(),
  speakingRateWpm: z.number().gte(0).optional(),
  referenceAudioRefs: z.array(EntityRefSchema).optional(),
});

export const CharacterEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("character"),
  appearance: z.string().optional(),
  wardrobe: z.string().optional(),
  personality: z.array(z.string()).optional(),
  ageRange: z.string().optional(),
  voiceProfile: VoiceProfileSchema.optional(),
  canonicalPromptFragments: z.array(PromptFragmentSchema).optional(),
  bannedTraits: z.array(z.string()).optional(),
  referenceAssetRefs: z.array(EntityRefSchema).optional(),
  coherenceRequirements: CharacterCoherenceSchema.optional(),
  defaultBounds: BoundingVolumeSchema.optional(),
  heightM: z.number().optional(),
}).strict();

export const EnvironmentEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("environment"),
  locationType: z.string().optional(),
  architectureStyle: z.string().optional(),
  timeOfDayDefaults: z.array(z.string()).optional(),
  weatherDefaults: z.array(z.string()).optional(),
  continuityNotes: z.string().optional(),
  canonicalPromptFragments: z.array(PromptFragmentSchema).optional(),
  referenceAssetRefs: z.array(EntityRefSchema).optional(),
  defaultSceneSpace: SceneSpaceSchema.optional(),
  spatialExtent: BoundingVolumeSchema.optional(),
}).strict();

export const PropEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("prop"),
  category: z.string().optional(),
  continuityNotes: z.string().optional(),
  canonicalPromptFragments: z.array(PromptFragmentSchema).optional(),
  referenceAssetRefs: z.array(EntityRefSchema).optional(),
  defaultBounds: BoundingVolumeSchema.optional(),
}).strict();

/**
 * CinematicSpec replaces v1's ShotTechnicalSpec.
 * 24 properties — a superset of the original 15.
 */
export const CinematicSpecSchema = z.strictObject({
  shotType: z.string().optional(),
  cameraAngle: z.string().optional(),
  cameraMovement: z.string().optional(),
  focalLengthMm: z.number().gte(0).optional(),
  aperture: z.number().gt(0).optional(),
  sensorFormat: z.string().optional(),
  depthOfField: z.string().optional(),
  hyperfocalDistanceM: z.number().optional(),
  fieldOfViewDeg: z.number().optional(),
  stabilization: z.string().optional(),
  focusMode: z.string().optional(),
  focusDistanceM: z.number().gte(0).optional(),
  whiteBalanceKelvin: z.number().int().gte(1000).optional(),
  exposureNotes: z.string().optional(),
  framing: z.string().optional(),
  compositionNotes: z.string().optional(),
  lighting: LightingGuidelinesSchema.optional(),
  style: StyleGuidelinesSchema.optional(),
  styleGuideRef: EntityRefSchema.optional(),
  colorPalette: z.array(z.string()).optional(),
  temporalBridgeAnchorRef: EntityRefSchema.optional(),
  manim: ManimConfigSchema.optional(),
  cameraExtrinsics: CameraExtrinsicsSchema.optional(),
  spatialBridgeAnchorRef: EntityRefSchema.optional(),
});

export const SyncPointSchema = z.strictObject({
  label: z.string().optional(),
  time: TimeRangeSchema.optional(),
  anchorRef: EntityRefSchema.optional(),
  toleranceFrames: z.number().int().gte(0).optional(),
  beat: z.number().gte(0).optional(),
});

export const AssemblyHintsSchema = z.strictObject({
  track: z.string().optional(),
  layerOrder: z.number().int().optional(),
  speedPercent: z.number().gt(0).optional(),
  reverse: z.boolean().optional(),
  opacity: z.number().gte(0).lte(1).optional(),
  blendMode: z.string().optional(),
  transitionIn: TransitionSpecSchema.optional(),
  transitionOut: TransitionSpecSchema.optional(),
  runtimeHints: z.looseObject({}).optional(),
});

export const SceneEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("scene"),
  sceneNumber: z.number().int().gte(1),
  synopsis: z.string().optional(),
  storyBeatRefs: z.array(EntityRefSchema).optional(),
  scriptSegmentRefs: z.array(EntityRefSchema).optional(),
  directorNoteRefs: z.array(EntityRefSchema).optional(),
  characterRefs: z.array(EntityRefSchema).optional(),
  environmentRef: EntityRefSchema.optional(),
  propRefs: z.array(EntityRefSchema).optional(),
  timeOfDay: z.string().optional(),
  weather: z.string().optional(),
  mood: z.string().optional(),
  targetDurationSec: z.number().gt(0),
  plannedPosition: TimeRangeSchema.optional(),
  shotRefs: z.array(EntityRefSchema),
  transitionIn: TransitionSpecSchema.optional(),
  transitionOut: TransitionSpecSchema.optional(),
  qaGate: QaGateSchema.optional(),
  sceneSpace: SceneSpaceSchema.optional(),
  spatialConsistency: SpatialConsistencySchema.optional(),
}).strict();

export const ShotEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("shot"),
  sceneRef: EntityRefSchema,
  shotNumber: z.number().int().gte(1),
  purpose: z.string().optional(),
  description: z.string().optional(),
  targetDurationSec: z.number().gt(0),
  plannedPosition: TimeRangeSchema.optional(),
  characterRefs: z.array(EntityRefSchema).optional(),
  environmentRef: EntityRefSchema.optional(),
  propRefs: z.array(EntityRefSchema).optional(),
  scriptSegmentRefs: z.array(EntityRefSchema).optional(),
  audioCueRefs: z.array(EntityRefSchema).optional(),
  referenceAssetRefs: z.array(EntityRefSchema).optional(),
  cinematicSpec: CinematicSpecSchema,
  genParams: GenerationStepSchema.optional(),
  continuityNotes: z.string().optional(),
  vfxNotes: z.string().optional(),
  assemblyHints: AssemblyHintsSchema.optional(),
  qaGate: QaGateSchema.optional(),
  spatialOverrides: z.array(SpatialPlacementSchema).optional(),
}).strict();

export const StyleGuideEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("styleGuide"),
  scope: z.string().optional(),
  guidelines: StyleGuidelinesSchema.optional(),
  negativeStylePrompt: z.string().optional(),
  appliesTo: z.array(EntityRefSchema).optional(),
}).strict();

// ═══════════════════════════════════════════════════════════════════════════════
// §13  ASSET TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const VisualAssetSpecSchema = z.strictObject({
  resolution: ResolutionSchema.optional(),
  aspectRatio: AspectRatioSchema.optional(),
  frameRate: FrameRateSchema.optional(),
  dominantPalette: z.array(z.string()).optional(),
  lighting: LightingGuidelinesSchema.optional(),
  style: StyleGuidelinesSchema.optional(),
  continuityNotes: z.string().optional(),
});

export const VisualAssetEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("visualAsset"),
  visualType: z.string(),
  modality: z.enum([
    "image",
    "video",
    "vector",
    "3d",
    "depth",
    "mask",
    "alpha",
    "document",
    "other",
  ]),
  purpose: z.string().optional(),
  referenceRole: z.string().optional(),
  sceneRefs: z.array(EntityRefSchema).optional(),
  shotRefs: z.array(EntityRefSchema).optional(),
  characterRefs: z.array(EntityRefSchema).optional(),
  environmentRefs: z.array(EntityRefSchema).optional(),
  isCanonicalReference: z.boolean().optional(),
  povCharacterRef: EntityRefSchema.optional(),
  spec: VisualAssetSpecSchema.optional(),
  variantSetId: IdentifierSchema.optional(),
}).strict();

export const AudioTechnicalSpecSchema = z.strictObject({
  sampleRateHz: z.number().int().gte(1).optional(),
  bitDepth: z.number().int().gte(1).optional(),
  channelLayout: z.string().optional(),
  loudnessLUFS: z.number().optional(),
  truePeakDbTP: z.number().optional(),
  tempoBpm: z.number().gte(0).optional(),
  musicalKey: z.string().optional(),
  timeSignature: z.string().optional(),
});

export const AudioAssetEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("audioAsset"),
  audioType: z.string(),
  purpose: z.string().optional(),
  language: z.string().optional(),
  speakerRef: EntityRefSchema.optional(),
  characterRef: EntityRefSchema.optional(),
  transcript: z.string().optional(),
  lyrics: z.string().optional(),
  mood: z.string().optional(),
  sceneRefs: z.array(EntityRefSchema).optional(),
  shotRefs: z.array(EntityRefSchema).optional(),
  syncPoints: z.array(SyncPointSchema).optional(),
  technicalSpec: AudioTechnicalSpecSchema.optional(),
}).strict();

export const CopyPackSchema = z.strictObject({
  headline: z.string().optional(),
  caption: z.string().optional(),
  body: z.string().optional(),
  cta: z.string().optional(),
  hashtags: z.array(z.string()).optional(),
  altText: z.string().optional(),
});

export const MarketingAssetEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("marketingAsset"),
  marketingType: z.enum([
    "trailer",
    "teaser",
    "thumbnail",
    "social_clip",
    "poster",
    "banner",
    "press_kit",
    "custom",
  ]),
  campaignId: IdentifierSchema.optional(),
  targetPlatforms: z.array(z.string()),
  durationSec: z.number().gte(0).lte(1800).optional(),
  storyRef: EntityRefSchema.optional(),
  originatingHook: z.string().optional(),
  sourceSceneRefs: z.array(EntityRefSchema).optional(),
  sourceShotRefs: z.array(EntityRefSchema).optional(),
  sourceAssetRefs: z.array(EntityRefSchema).optional(),
  copy: CopyPackSchema.optional(),
  assemblyPlanRef: EntityRefSchema.optional(),
  thumbnailSourceRef: EntityRefSchema.optional(),
}).strict();

export const GenericAssetEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("genericAsset"),
  assetClass: z.string(),
  modality: z.string().optional(),
  parameters: z.looseObject({}).optional(),
}).strict();

// ═══════════════════════════════════════════════════════════════════════════════
// §14  TIMELINE / ASSEMBLY TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export const TransformSchema = z.strictObject({
  position: z
    .strictObject({
      x: z.number().optional(),
      y: z.number().optional(),
    })
    .optional(),
  scale: z
    .strictObject({
      x: z.number().optional(),
      y: z.number().optional(),
    })
    .optional(),
  rotationDeg: z.number().optional(),
  opacity: z.number().gte(0).lte(1).optional(),
  crop: z.record(z.string(), z.number()).optional(),
  blendMode: z.string().optional(),
  maskRef: EntityRefSchema.optional(),
});

export const TimelineClipSchema = z.strictObject({
  clipId: IdentifierSchema,
  sourceRef: EntityRefSchema,
  sourceInSec: z.number().gte(0).optional(),
  sourceOutSec: z.number().gte(0).optional(),
  timelineStartSec: z.number().gte(0),
  durationSec: z.number().gte(0),
  layerOrder: z.number().int().optional(),
  transform: TransformSchema.optional(),
  retime: RetimeSpecSchema.optional(),
  syncPoints: z.array(SyncPointSchema).optional(),
  transitionIn: TransitionSpecSchema.optional(),
  transitionOut: TransitionSpecSchema.optional(),
  assemblyHints: AssemblyHintsSchema.optional(),
});

export const StreamBindingSchema = z.strictObject({
  streamType: z.string(),
  streamIndex: z.number().int().optional(),
  codec: z.string().optional(),
  timebaseNumerator: z.number().int().optional(),
  timebaseDenominator: z.number().int().optional(),
  parameters: z.looseObject({}).optional(),
});

/**
 * v3 TimelineEntity — restructured from v1.
 *
 * v1 used tracks: array<TimelineTrack> where each track had a `kind` and `clips`.
 * v3 uses typed clip arrays directly: videoClips, audioClips, subtitleClips.
 * v3 also adds streamBindings and operations.
 */
export const TimelineEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("timeline"),
  durationSec: z.number().gte(0),
  frameRate: FrameRateSchema.optional(),
  resolution: ResolutionSchema.optional(),
  aspectRatio: AspectRatioSchema.optional(),
  videoClips: z.array(TimelineClipSchema).optional(),
  audioClips: z.array(TimelineClipSchema).optional(),
  subtitleClips: z.array(TimelineClipSchema).optional(),
  streamBindings: z.array(StreamBindingSchema).optional(),
  operations: z.array(OperationSchema).optional(),
  runtimeHints: z.looseObject({}).optional(),
}).strict();

export const EditVersionEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("editVersion"),
  timelineRef: EntityRefSchema,
  changeList: z.array(z.string()).optional(),
  approvedForRender: z.boolean().optional(),
}).strict();

export const RenderPlanEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("renderPlan"),
  sourceTimelineRef: EntityRefSchema,
  targetOutputRefs: z.array(EntityRefSchema).optional(),
  compatibleRuntimes: z.array(z.string()).optional(),
  operations: z.array(OperationSchema),
  colorPipeline: z.looseObject({}).optional(),
  runtimeHints: z.looseObject({}).optional(),
}).strict();

export const AssemblySchema = z.strictObject({
  timelines: z.array(TimelineEntitySchema),
  editVersions: z.array(EditVersionEntitySchema),
  renderPlans: z.array(RenderPlanEntitySchema),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §15  DELIVERABLES / RELATIONSHIPS / DEPENDENCIES
// ═══════════════════════════════════════════════════════════════════════════════

export const FinalOutputEntitySchema = BaseEntityObject.extend({
  entityType: z.literal("finalOutput"),
  outputType: z.string(),
  platform: z.string().optional(),
  releaseChannel: z.string().optional(),
  runtimeSec: z.number().gt(0),
  sourceTimelineRef: EntityRefSchema,
  sourceEditRef: EntityRefSchema.optional(),
  renderPlanRef: EntityRefSchema,
  sourceOutputRef: EntityRefSchema.optional(),
  qcResults: z.array(QCResultSchema).optional(),
  localizationTargets: z.array(LocalizationConfigSchema).optional(),
  accessibilityConfig: AccessibilityConfigSchema.optional(),
  platformDeliveries: z.array(PlatformDeliverySchema).optional(),
  publicationMetadata: z.looseObject({}).optional(),
}).strict();

export const RelationshipSchema = z.strictObject({
  relationshipId: IdentifierSchema,
  relationshipType: z.string(),
  from: EntityRefSchema,
  to: EntityRefSchema,
  required: z.boolean().optional(),
  attributes: z.looseObject({}).optional(),
  notes: z.string().optional(),
});

export const DependencyEdgeSchema = z.strictObject({
  edgeId: IdentifierSchema,
  fromRef: EntityRefSchema,
  toRef: EntityRefSchema,
  dependencyType: z.string(),
  required: z.boolean().optional(),
  notes: z.string().optional(),
});

// ═══════════════════════════════════════════════════════════════════════════════
// §16  ROOT SCHEMA
// ═══════════════════════════════════════════════════════════════════════════════

export const UnifiedVideoProjectPackageSchema = z.strictObject({
  schemaVersion: SemVerSchema,

  package: PackageInfoSchema,
  project: ProjectEntitySchema,

  qualityProfiles: z.array(QualityProfileEntitySchema),

  spatialUniverses: z.array(SharedSpatialUniverseSchema).optional(),
  team: TeamSchema.optional(),

  canonicalDocuments: z.strictObject({
    story: StoryEntitySchema,
    script: ScriptEntitySchema,
    directorInstructions: DirectorInstructionsEntitySchema,
  }),

  production: z.strictObject({
    characters: z.array(CharacterEntitySchema),
    environments: z.array(EnvironmentEntitySchema),
    props: z.array(PropEntitySchema),
    scenes: z.array(SceneEntitySchema),
    shots: z.array(ShotEntitySchema),
    styleGuides: z.array(StyleGuideEntitySchema),
  }),

  assetLibrary: z.strictObject({
    visualAssets: z.array(VisualAssetEntitySchema),
    audioAssets: z.array(AudioAssetEntitySchema),
    marketingAssets: z.array(MarketingAssetEntitySchema),
    genericAssets: z.array(GenericAssetEntitySchema),
  }),

  orchestration: OrchestrationSchema,
  assembly: AssemblySchema,
  deliverables: z.array(FinalOutputEntitySchema),
  relationships: z.array(RelationshipSchema),
  dependencies: z.array(DependencyEdgeSchema).optional(),
  extensions: ExtensionsSchema.optional(),
});

/** Backward-compatible alias */
export const GenerativeVideoProjectPackageSchema =
  UnifiedVideoProjectPackageSchema;

// ═══════════════════════════════════════════════════════════════════════════════
// §17  INFERRED TYPES — COMPLETE
// ═══════════════════════════════════════════════════════════════════════════════

// Root
export type UnifiedVideoProjectPackage = z.infer<typeof UnifiedVideoProjectPackageSchema>;
export type GenerativeVideoProjectPackage = UnifiedVideoProjectPackage;

// Primitives
export type Identifier = z.infer<typeof IdentifierSchema>;
export type SemVer = z.infer<typeof SemVerSchema>;
export type ISOTimestamp = z.infer<typeof ISOTimestampSchema>;
export type Extensions = z.infer<typeof ExtensionsSchema>;
export type StringMap = z.infer<typeof StringMapSchema>;

// Common Structural
export type Contributor = z.infer<typeof ContributorSchema>;
export type VersionSelector = z.infer<typeof VersionSelectorSchema>;
export type EntityRef = z.infer<typeof EntityRefSchema>;
export type Checksum = z.infer<typeof ChecksumSchema>;
export type Approval = z.infer<typeof ApprovalSchema>;
export type ApprovalRecord = z.infer<typeof ApprovalRecordSchema>;
export type Rights = z.infer<typeof RightsSchema>;
export type VersionInfo = z.infer<typeof VersionInfoSchema>;
export type Comment = z.infer<typeof CommentSchema>;
export type FuzzyDate = z.infer<typeof FuzzyDateSchema>;

// Technical / Temporal
export type FrameRate = z.infer<typeof FrameRateSchema>;
export type Resolution = z.infer<typeof ResolutionSchema>;
export type AspectRatio = z.infer<typeof AspectRatioSchema>;
export type Timecode = z.infer<typeof TimecodeSchema>;
export type TimeRange = z.infer<typeof TimeRangeSchema>;
export type TemporalConsistency = z.infer<typeof TemporalConsistencySchema>;
export type CharacterCoherence = z.infer<typeof CharacterCoherenceSchema>;
export type LightingGuidelines = z.infer<typeof LightingGuidelinesSchema>;
export type StyleGuidelines = z.infer<typeof StyleGuidelinesSchema>;

// Spatial / 3D
export type Position3D = z.infer<typeof Position3DSchema>;
export type Quaternion = z.infer<typeof QuaternionSchema>;
export type EulerAnglesDeg = z.infer<typeof EulerAnglesDegSchema>;
export type Scale3D = z.infer<typeof Scale3DSchema>;
export type Orientation3D = z.infer<typeof Orientation3DSchema>;
export type Transform3D = z.infer<typeof Transform3DSchema>;
export type BoundingVolume = z.infer<typeof BoundingVolumeSchema>;
export type CoordinateSystem = z.infer<typeof CoordinateSystemSchema>;
export type SpatialAnchor = z.infer<typeof SpatialAnchorSchema>;
export type PlacementKeyframe = z.infer<typeof PlacementKeyframeSchema>;
export type SpatialPlacement = z.infer<typeof SpatialPlacementSchema>;
export type SpatialRule = z.infer<typeof SpatialRuleSchema>;
export type SpatialConsistency = z.infer<typeof SpatialConsistencySchema>;
export type CameraKeyframe = z.infer<typeof CameraKeyframeSchema>;
export type CameraExtrinsics = z.infer<typeof CameraExtrinsicsSchema>;
export type SceneSpace = z.infer<typeof SceneSpaceSchema>;
export type SharedSpatialUniverse = z.infer<typeof SharedSpatialUniverseSchema>;

// Quality / Validation
export type MotionBlurControl = z.infer<typeof MotionBlurControlSchema>;
export type CompressionControls = z.infer<typeof CompressionControlsSchema>;
export type VideoQualityControls = z.infer<typeof VideoQualityControlsSchema>;
export type AudioQualityControls = z.infer<typeof AudioQualityControlsSchema>;
export type ValidationRule = z.infer<typeof ValidationRuleSchema>;
export type QCResult = z.infer<typeof QCResultSchema>;
export type QaCheck = z.infer<typeof QaCheckSchema>;
export type QaGate = z.infer<typeof QaGateSchema>;
export type QualityProfile = z.infer<typeof QualityProfileSchema>;
export type AccessibilityConfig = z.infer<typeof AccessibilityConfigSchema>;
export type LocalizationConfig = z.infer<typeof LocalizationConfigSchema>;
export type PlatformDelivery = z.infer<typeof PlatformDeliverySchema>;
export type Compliance = z.infer<typeof ComplianceSchema>;

// Generation / Provenance
export type ModelDescriptor = z.infer<typeof ModelDescriptorSchema>;
export type ReferenceInput = z.infer<typeof ReferenceInputSchema>;
export type ConsistencyAnchor = z.infer<typeof ConsistencyAnchorSchema>;
export type AdapterInput = z.infer<typeof AdapterInputSchema>;
export type LogEntry = z.infer<typeof LogEntrySchema>;
export type PromptFragment = z.infer<typeof PromptFragmentSchema>;
export type PromptRecord = z.infer<typeof PromptRecordSchema>;
export type GenerationCost = z.infer<typeof GenerationCostSchema>;
export type RetryConfig = z.infer<typeof RetryConfigSchema>;
export type AsyncConfig = z.infer<typeof AsyncConfigSchema>;
export type GenerationStep = z.infer<typeof GenerationStepSchema>;
export type GenerationManifest = z.infer<typeof GenerationManifestSchema>;
export type FileObject = z.infer<typeof FileObjectSchema>;

// Base Entity
export type BaseEntity = z.infer<typeof BaseEntityObject>;

// Operations
export type ConcatOp = z.infer<typeof ConcatOpSchema>;
export type OverlayOp = z.infer<typeof OverlayOpSchema>;
export type ColorGradeOp = z.infer<typeof ColorGradeOpSchema>;
export type AudioMixTrack = z.infer<typeof AudioMixTrackSchema>;
export type AudioMixOp = z.infer<typeof AudioMixOpSchema>;
export type TransitionSpec = z.infer<typeof TransitionSpecSchema>;
export type TransitionOp = z.infer<typeof TransitionOpSchema>;
export type FilterOp = z.infer<typeof FilterOpSchema>;
export type EncodeOp = z.infer<typeof EncodeOpSchema>;
export type ManimConfig = z.infer<typeof ManimConfigSchema>;
export type ManimOp = z.infer<typeof ManimOpSchema>;
export type RetimeSpec = z.infer<typeof RetimeSpecSchema>;
export type RetimeOp = z.infer<typeof RetimeOpSchema>;
export type CustomOp = z.infer<typeof CustomOpSchema>;
export type Operation = z.infer<typeof OperationSchema>;

// Workflow
export type GenerationNode = z.infer<typeof GenerationNodeSchema>;
export type ApprovalNode = z.infer<typeof ApprovalNodeSchema>;
export type TransformNode = z.infer<typeof TransformNodeSchema>;
export type RenderNode = z.infer<typeof RenderNodeSchema>;
export type ValidationNode = z.infer<typeof ValidationNodeSchema>;
export type NotificationNode = z.infer<typeof NotificationNodeSchema>;
export type CustomWorkflowNode = z.infer<typeof CustomWorkflowNodeSchema>;
export type WorkflowNode = z.infer<typeof WorkflowNodeSchema>;
export type WorkflowEdge = z.infer<typeof WorkflowEdgeSchema>;
export type WorkflowGraph = z.infer<typeof WorkflowGraphSchema>;
export type Orchestration = z.infer<typeof OrchestrationSchema>;

// Package / Project / Governance
export type NamingConventions = z.infer<typeof NamingConventionsSchema>;
export type VersioningPolicy = z.infer<typeof VersioningPolicySchema>;
export type Governance = z.infer<typeof GovernanceSchema>;
export type Budget = z.infer<typeof BudgetSchema>;
export type TeamMember = z.infer<typeof TeamMemberSchema>;
export type Team = z.infer<typeof TeamSchema>;
export type PackageInfo = z.infer<typeof PackageInfoSchema>;
export type ProjectEntity = z.infer<typeof ProjectEntitySchema>;
export type QualityProfileEntity = z.infer<typeof QualityProfileEntitySchema>;

// Story / Script / Director
export type StoryBeat = z.infer<typeof StoryBeatSchema>;
export type NarrativeArc = z.infer<typeof NarrativeArcSchema>;
export type StoryEntity = z.infer<typeof StoryEntitySchema>;
export type ScriptSegment = z.infer<typeof ScriptSegmentSchema>;
export type ScriptEntity = z.infer<typeof ScriptEntitySchema>;
export type TargetedNote = z.infer<typeof TargetedNoteSchema>;
export type DirectorInstructionsEntity = z.infer<typeof DirectorInstructionsEntitySchema>;

// Production
export type VoiceProfile = z.infer<typeof VoiceProfileSchema>;
export type CharacterEntity = z.infer<typeof CharacterEntitySchema>;
export type EnvironmentEntity = z.infer<typeof EnvironmentEntitySchema>;
export type PropEntity = z.infer<typeof PropEntitySchema>;
export type CinematicSpec = z.infer<typeof CinematicSpecSchema>;
export type SyncPoint = z.infer<typeof SyncPointSchema>;
export type AssemblyHints = z.infer<typeof AssemblyHintsSchema>;
export type SceneEntity = z.infer<typeof SceneEntitySchema>;
export type ShotEntity = z.infer<typeof ShotEntitySchema>;
export type StyleGuideEntity = z.infer<typeof StyleGuideEntitySchema>;

// Assets
export type VisualAssetSpec = z.infer<typeof VisualAssetSpecSchema>;
export type VisualAssetEntity = z.infer<typeof VisualAssetEntitySchema>;
export type AudioTechnicalSpec = z.infer<typeof AudioTechnicalSpecSchema>;
export type AudioAssetEntity = z.infer<typeof AudioAssetEntitySchema>;
export type CopyPack = z.infer<typeof CopyPackSchema>;
export type MarketingAssetEntity = z.infer<typeof MarketingAssetEntitySchema>;
export type GenericAssetEntity = z.infer<typeof GenericAssetEntitySchema>;

// Timeline / Assembly
export type Transform = z.infer<typeof TransformSchema>;
export type TimelineClip = z.infer<typeof TimelineClipSchema>;
export type StreamBinding = z.infer<typeof StreamBindingSchema>;
export type TimelineEntity = z.infer<typeof TimelineEntitySchema>;
export type EditVersionEntity = z.infer<typeof EditVersionEntitySchema>;
export type RenderPlanEntity = z.infer<typeof RenderPlanEntitySchema>;
export type Assembly = z.infer<typeof AssemblySchema>;

// Deliverables / Relationships
export type FinalOutputEntity = z.infer<typeof FinalOutputEntitySchema>;
export type Relationship = z.infer<typeof RelationshipSchema>;
export type DependencyEdge = z.infer<typeof DependencyEdgeSchema>;
