export { SCHEMA_VERSION } from "./shared";
export type { Vector3, Transform, Quaternion, RigidPose, SymmetricTensor3, Color } from "./shared";
export {
  Vector3Schema,
  UnitVector3Schema,
  TransformSchema,
  QuaternionSchema,
  RigidPoseSchema,
  SymmetricTensor3Schema,
  ColorSchema,
  ExtensionsSchema,
} from "./shared";

// --- Skeletal ---
export type { Bone, Joint } from "./skeletal";
export {
  BoneSchema,
  BoneClassEnum,
  BoneRegionEnum,
  JointSchema,
  JointTypeEnum,
  JointLimitSchema,
} from "./skeletal";

// --- Muscular ---
export type { Tendon, Muscle } from "./muscular";
export {
  TendonSchema,
  MuscleSchema,
  MuscleRegionEnum,
  MuscleTypeEnum,
  MuscleActionEnum,
  FascicleArchitectureEnum,
  FiberCompositionEnum,
  InnervationSchema,
} from "./muscular";

// --- Connective Tissue ---
export type { Ligament, Cartilage } from "./connective";
export {
  LigamentSchema,
  LigamentId,
  CartilageSchema,
  CartilageId,
  CartilageTypeEnum,
} from "./connective";

// --- Nervous System ---
export type { Nerve } from "./nervous";
export {
  NerveSchema,
  NerveTypeEnum,
  NervePlexusEnum,
} from "./nervous";

// --- Organs ---
export type { Organ } from "./organs";
export { OrganSchema, OrganSystemEnum } from "./organs";

// --- Vascular ---
export type { Artery, Vein, CapillaryBed, Vessel } from "./vascular";
export {
  ArterySchema,
  VeinSchema,
  CapillaryBedSchema,
  VesselSchema,
  VesselTypeEnum,
} from "./vascular";

// --- Appearance ---
export type { Hair, Clothing, RenderingLayer } from "./appearance";
export {
  HairSchema,
  ClothingSchema,
  ClothingTypeEnum,
  RenderingLayerSchema,
  EntityRenderOverride,
  SkinningWeightSchema,
} from "./appearance";

// --- Kinematics ---
export type {
  ReferenceFrame,
  BodySegment,
  JointState,
  SegmentSpatialState,
  Pose,
  MotionSequence,
} from "./kinematics";
export {
  ReferenceFrameSchema,
  ReferenceFrameTypeEnum,
  BodySegmentSchema,
  JointStateSchema,
  SegmentSpatialStateSchema,
  PoseSchema,
  MotionSequenceSchema,
  StandardPoseEnum,
} from "./kinematics";

// --- Dynamics ---
export type {
  Force,
  GravitationalForce,
  MuscleForce,
  GroundReactionForce,
  JointReactionForce,
  ExternalForce,
  LigamentousForce,
  InertialForce,
  ContactForce,
  AerodynamicDrag,
  BuoyancyForce,
  Moment,
  Contact,
  LoadingCondition,
  FreeBodyDiagram,
} from "./dynamics";
export {
  ForceTypeEnum,
  ForceSchema,
  GravitationalForceSchema,
  MuscleForceSchema,
  GroundReactionForceSchema,
  JointReactionForceSchema,
  ExternalForceSchema,
  LigamentousForceSchema,
  InertialForceSchema,
  ContactForceSchema,
  AerodynamicDragSchema,
  BuoyancyForceSchema,
  MomentTypeEnum,
  MomentSchema,
  ContactTypeEnum,
  ContactSchema,
  LoadingConditionSchema,
  FreeBodyDiagramSchema,
} from "./dynamics";

// --- Derivations ---
export type { FieldRef, PhysicalLaw, DerivationRule, DerivationGraph } from "./derivations";
export {
  DERIVATION_GRAPH_VERSION,
  FieldRefSchema,
  PhysicalLawSchema,
  DerivationRuleSchema,
  DerivationGraphSchema,
} from "./derivations";

// --- Constitutive Laws ---
export type {
  ViolationSeverity,
  ValidityBoundary,
  HillMuscleLaw,
  LigamentForceStrainLaw,
  CartilageStressStrainLaw,
  BoneYieldCriterion,
  JointRangeLimit,
  ConstitutiveLaw,
  ConstitutiveLaws,
} from "./constitutive";
export {
  CONSTITUTIVE_LAWS_VERSION,
  ViolationSeverityEnum,
  ValidityBoundarySchema,
  ConstitutiveLawTypeEnum,
  HillMuscleLawSchema,
  LigamentForceStrainLawSchema,
  CartilageStressStrainLawSchema,
  BoneYieldCriterionSchema,
  JointRangeLimitSchema,
  ConstitutiveLawSchema,
  ConstitutiveLawsSchema,
  STANDARD_VALIDITY_BOUNDARIES,
} from "./constitutive";

// --- Geometry ---
export type {
  BoneGeometry,
  ParametricCSGGeometry,
  IndexedMeshGeometry,
  ExternalAssetGeometry,
  MeshLOD,
  AnatomicalLandmark,
  SurfaceRegion,
  CSGPrimitive,
} from "./geometry";
export {
  BoneGeometrySchema,
  ParametricCSGGeometrySchema,
  IndexedMeshGeometrySchema,
  ExternalAssetGeometrySchema,
  MeshLODSchema,
  MeshVertexSchema,
  AnatomicalLandmarkSchema,
  SurfaceRegionSchema,
  CSGPrimitiveSchema,
  CSGNodeSchema,
  CSGPrimitiveTypeEnum,
  CSGOperationEnum,
  MeshFormatEnum,
  countCSGNodes,
  csgTreeDepth,
  CSG_MAX_NODE_COUNT,
  CSG_MAX_DEPTH,
} from "./geometry";

// --- Root ---
export type { HumanBody } from "./body";
export {
  HumanBodySchema,
  ProportionsSchema,
  SexEnum,
} from "./body";
