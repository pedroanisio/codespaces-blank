/**
 * human-body-schema — Rendering Extensions
 * 
 * Schema version: 3.1.0+ (additive to existing v3.0.0)
 * 
 * DISCLAIMER: No type definition within this file should be taken for granted.
 * These types represent a proposed extension to the existing human-body-schema.
 * Material constants, optical parameters, and anatomical reference values
 * cited in comments must be verified against primary sources before use.
 * 
 * All numeric fields carry implicit unit annotations in their names (_mm, _kPa, etc.)
 * following the existing schema convention.
 */

// ─────────────────────────────────────────────
// Layer 0 — Mesh Geometry
// ─────────────────────────────────────────────

/** Supported mesh interchange formats */
export type MeshFormat = "glTF" | "OBJ" | "FBX" | "PLY";

/** Inline mesh for small entities (< ~10k vertices).
 *  Uses typed arrays for GPU-friendliness. */
export interface InlineMesh {
  readonly format: "indexed_triangle_list";
  /** Interleaved [x,y,z, x,y,z, ...] in entity-local coordinates (cm) */
  vertices: number[];
  /** Per-vertex normals [nx,ny,nz, ...] */
  normals: number[];
  /** Per-vertex UV coordinates [u,v, ...] — required for texturing (Layer 2+) */
  uvs?: number[];
  /** Triangle index buffer */
  indices: number[];
  /** Per-vertex tangent vectors [tx,ty,tz,tw, ...] for tangent-space normal mapping */
  tangents?: number[];
  /** Total vertex count (= vertices.length / 3) */
  vertexCount: number;
  /** Total triangle count (= indices.length / 3) */
  triangleCount: number;
}

/** External mesh file reference for large or pre-built meshes */
export interface ExternalMeshRef {
  format: MeshFormat;
  /** Relative file path or URL to the mesh asset */
  uri: string;
  /** SHA-256 hash of the file for integrity verification */
  hash: string;
  /** Level-of-detail chain (optional). Level 0 = highest detail. */
  lodLevels?: LODLevel[];
}

export interface LODLevel {
  level: number;
  uri: string;
  vertexCount: number;
  /** Screen-space threshold: switch to this LOD when the entity
   *  subtends fewer than this many pixels on screen */
  screenSizeThreshold?: number;
}

/** Discriminated union for mesh data source */
export type MeshSource =
  | { readonly type: "inline"; mesh: InlineMesh }
  | { readonly type: "external"; ref: ExternalMeshRef };

/** Skinning weights for skeletal deformation.
 *  Maps each vertex to bone influences. */
export interface SkinningData {
  /** Number of bone influences per vertex (typically 4) */
  maxInfluencesPerVertex: number;
  /** Bone indices per vertex [b0,b1,b2,b3, b0,b1,b2,b3, ...] */
  boneIndices: number[];
  /** Corresponding weights per vertex [w0,w1,w2,w3, ...], sum to 1.0 */
  boneWeights: number[];
  /** Bone ID ordering — maps boneIndices values to skeleton bone IDs */
  boneIdMap: string[];
  /** Inverse bind matrices per bone (4×4 column-major) */
  inverseBindMatrices: number[][];
}

// ─────────────────────────────────────────────
// Layer 1 — Skin System
// ─────────────────────────────────────────────

export interface SkinSystem {
  /** The outer body surface mesh — the primary renderable */
  surfaceMesh: MeshSource;

  /** Skinning weights binding the surface mesh to the skeleton */
  skinning: SkinningData;

  /** Blend shapes for expression, muscle flexion, breathing, etc. */
  blendShapes?: BlendShape[];

  /** Regional properties — different body areas have different optical
   *  and biomechanical characteristics */
  regions: SkinRegion[];

  /** Per-vertex region assignment (index into regions[]) */
  vertexRegionMap?: number[];

  /** Overall skin tone baseline */
  fitzpatrickType?: 1 | 2 | 3 | 4 | 5 | 6;

  /** Microstructure detail maps (pores, wrinkles) */
  microstructure?: SkinMicrostructure;
}

export interface BlendShape {
  id: string;
  name: string;
  /** Per-vertex deltas [dx,dy,dz, ...] — same ordering as surfaceMesh vertices */
  deltas: number[];
  /** Optional per-vertex normal deltas */
  normalDeltas?: number[];
}

export interface SkinRegion {
  id: string;
  name: string;

  // Biomechanical
  /** Epidermis + dermis combined thickness */
  thickness_mm: number;
  /** Young's modulus (skin elasticity) */
  elasticity_kPa: number;

  // Optical — these drive the SSS and shading pipeline
  /** Melanin concentration: 0 (albino) .. 1 (darkest) */
  melaninConcentration: number;
  /** Hemoglobin concentration: 0 (pale) .. 1 (highly vascular, e.g. lips) */
  hemoglobinConcentration: number;
  /** Surface oiliness: 0 (dry) .. 1 (very oily). Drives specular intensity. */
  oiliness: number;
}

export interface SkinMicrostructure {
  /** Macro displacement map — wrinkles, creases, scars */
  displacementMap: TextureRef;
  /** Maximum displacement amplitude in mm */
  displacementAmplitude_mm: number;

  /** Pore-level normal map */
  normalMap: TextureRef;

  /** Cavity / AO map for pores and fine creases */
  cavityMap?: TextureRef;

  /** Joint-driven dynamic wrinkle maps */
  dynamicWrinkles?: DynamicWrinkle[];
}

export interface DynamicWrinkle {
  /** Joint that drives this wrinkle region */
  jointId: string;
  /** Which joint axis activates the wrinkle */
  activationAxis: "flexion" | "extension" | "abduction" | "adduction";
  /** Wrinkle normal map (blended with base normal map) */
  wrinkleNormalMap: TextureRef;
  /** Activation curve: maps joint angle (degrees) to wrinkle intensity (0..1) */
  activationCurve: { angle_deg: number; intensity: number }[];
}

// ─────────────────────────────────────────────
// Layer 2 — PBR Material System
// ─────────────────────────────────────────────

export interface TextureRef {
  /** Path or URL to texture file */
  uri: string;
  /** SHA-256 hash for integrity */
  hash: string;
  /** Which channel(s) to sample */
  channel?: "r" | "g" | "b" | "a" | "rgb" | "rgba";
  /** Color space of the texture data */
  colorSpace: "sRGB" | "linear";
  /** Texture resolution in pixels [width, height] */
  resolution: [number, number];
}

export type ColorSource =
  | { readonly type: "constant"; rgba: [number, number, number, number] }
  | { readonly type: "texture"; ref: TextureRef };

export type ScalarOrTexture = number | TextureRef;

export interface PBRMaterial {
  id: string;
  name: string;

  /** Base color / albedo */
  baseColor: ColorSource;

  /** 0.0 = dielectric (all biological tissue), 1.0 = metal */
  metalness: ScalarOrTexture;

  /** 0.0 = mirror, 1.0 = fully diffuse */
  roughness: ScalarOrTexture;

  /** Tangent-space normal map for surface micro-detail */
  normalMap?: TextureRef;

  /** Displacement / height map for surface macro-deformation */
  displacementMap?: TextureRef;
  displacementScale_mm?: number;

  /** Ambient occlusion map */
  aoMap?: TextureRef;

  /** Opacity map (useful for thin membranes, ear pinna, etc.) */
  opacityMap?: TextureRef;

  /** Emissive map (rarely used in anatomy — possibly for bioluminescence vis) */
  emissiveMap?: TextureRef;
  emissiveIntensity?: number;

  /** SSS profile reference (see Layer 4) */
  sssProfileId?: string;
}

/** Enhanced rendering override replacing the current flat color+opacity */
export interface RenderingOverrideV2 {
  entityId: string;
  /** Legacy flat color (kept for backward compat) */
  color?: { r: number; g: number; b: number; a: number };
  opacity?: number;
  visible?: boolean;
  /** New: full PBR material definition */
  material?: PBRMaterial;
}

// ─────────────────────────────────────────────
// Layer 3 — Adipose Distribution
// ─────────────────────────────────────────────

export interface AdiposeSystem {
  /** Total body fat mass (derived from proportions.fatPercentage × weight) */
  totalMass_kg: number;

  /** Per-region subcutaneous fat thickness */
  regions: AdiposeRegion[];

  /** Optional volumetric mesh of the fat layer
   *  (lies between muscle surface meshes and skin surface mesh) */
  volumeMesh?: MeshSource;
}

export interface AdiposeRegion {
  id: string;
  name: string;
  /** FK → SkinRegion.id — which skin region overlies this fat depot */
  skinRegionId: string;
  /** Subcutaneous fat thickness at this region */
  thickness_mm: number;
  /** Adipose tissue density (typically ~0.9 g/cm³ = 900 kg/m³) */
  density_kg_m3: number;
}

// ─────────────────────────────────────────────
// Layer 4 — Subsurface Scattering
// ─────────────────────────────────────────────

/** Diffusion model selection */
export type SSSModel = "dipole" | "normalized_diffusion" | "random_walk";

export interface SSSProfile {
  id: string;
  name: string;

  /** Diffusion model type.
   *  - "dipole": Jensen 2001. Fastest, least accurate at edges.
   *  - "normalized_diffusion": Christensen 2015. Good balance.
   *  - "random_walk": d'Eon & Irving 2011. Most accurate, slowest. */
  model: SSSModel;

  /** Mean free path per RGB channel (mm).
   *  How far light travels on average before scattering.
   *  Red > Green > Blue for skin (red penetrates deepest). */
  scatterDistance_mm: { r: number; g: number; b: number };

  /** Absorption coefficient per channel (1/mm).
   *  Higher absorption = less light transmitted. */
  absorptionCoefficient?: { r: number; g: number; b: number };

  /** Per-region scale modifiers.
   *  Thin regions (eyelids) scatter more per unit thickness. */
  regionScales?: {
    skinRegionId: string;
    scale: number;
  }[];
}

// ─────────────────────────────────────────────
// Layer 5 — Fascia System
// ─────────────────────────────────────────────

export type FasciaType = "superficial" | "deep" | "visceral" | "septum";

export interface FascialLayer {
  id: string;
  name: string;
  type: FasciaType;

  /** Muscle IDs enclosed by this fascial compartment */
  enclosedMuscleIds: string[];

  /** Surface mesh (thin sheet geometry) */
  mesh?: MeshSource;

  /** Fascial sheet thickness */
  thickness_mm: number;

  /** Optical transmittance: 0 (opaque) .. 1 (fully transparent) */
  opticalTransmittance: number;

  /** Material properties */
  material?: PBRMaterial;
}

// ─────────────────────────────────────────────
// Layer 6 — Eye, Teeth, Nail Geometry
// ─────────────────────────────────────────────

export interface EyeModel {
  id: string;
  laterality: "left" | "right";

  /** Eyeball globe mesh */
  globeMesh: MeshSource;
  globeRadius_mm: number;

  /** Clear front surface — primary refractive element */
  cornea: {
    mesh: MeshSource;
    refractiveIndex: number;
    thickness_mm: number;
    roughness: number;
  };

  /** Colored disk with pupil aperture */
  iris: {
    mesh: MeshSource;
    colorMap: TextureRef;
    pupilDiameter_mm: number;
    /** Fine radial/circular patterns in the iris stroma */
    cryptPattern?: TextureRef;
  };

  /** White of the eye */
  sclera: {
    color: [number, number, number];
    veinMap?: TextureRef;
    roughness: number;
  };

  /** Internal lens (affects caustics / light focusing) */
  lens: {
    refractiveIndex: number;
  };

  /** Tear film — thin wet layer over cornea and sclera */
  tearFilm?: {
    thickness_um: number;
    refractiveIndex: number;
  };
}

export interface ToothModel {
  id: string;
  name: string;
  /** FK → skeleton bone (dental bones already exist in your model) */
  boneId: string;

  /** Surface mesh (outer enamel shape) */
  mesh: MeshSource;

  /** Enamel material — semi-translucent, hard, smooth */
  enamel: {
    thickness_mm: number;
    roughness: number;
    /** SSS profile for enamel translucency */
    sssProfileId?: string;
  };

  /** Dentin material — underlying yellow layer */
  dentin: {
    color: [number, number, number];
    sssProfileId?: string;
  };
}

export interface NailModel {
  id: string;
  laterality: "left" | "right";
  /** "fingernail" or "toenail" */
  type: "fingernail" | "toenail";
  /** Which digit (1=thumb/hallux, 5=little finger/toe) */
  digitIndex: number;

  /** Thin shell mesh */
  mesh: MeshSource;

  /** Nail plate material — layered keratin */
  material: {
    thickness_mm: number;
    roughness: number;
    /** Slight pink tint from underlying nail bed vasculature */
    nailBedColor: [number, number, number];
    /** Lunula (white crescent) opacity */
    lunulaOpacity: number;
  };
}

// ─────────────────────────────────────────────
// Layer 7 — Hair System
// ─────────────────────────────────────────────

export interface HairSystem {
  /** Scalp hair — enhanced from current single descriptor */
  scalp: HairPatch;

  /** Facial hair patches (beard zones, mustache, sideburns) */
  facial?: HairPatch[];

  /** Body hair patches (chest, forearms, legs, etc.) */
  body?: HairPatch[];

  /** Eyebrows [left, right] */
  eyebrows: [HairPatch, HairPatch];

  /** Eyelashes [left, right] */
  eyelashes: [HairPatch, HairPatch];
}

export interface HairPatch {
  id: string;
  name: string;

  /** Skin region where this hair grows */
  skinRegionId: string;

  /** Pre-groomed strand data (for strand-based renderers like TressFX / HairWorks) */
  strands?: {
    /** Number of pre-authored guide curves */
    guideCount: number;
    /** Guide curve geometry (line strips) */
    guideCurves: MeshSource;
    /** Density of interpolated strands between guides (strands/cm²) */
    interpolatedDensity: number;
  };

  /** Procedural groom parameters (for runtime generation) */
  groom: {
    /** Follicle density */
    density_per_cm2: number;
    /** Strand length range */
    length_mm: { min: number; max: number };
    /** Individual strand diameter */
    thickness_um: number;
    /** Curvature: 0 (straight) .. 1 (tightly curled) */
    curvature: number;
    /** Clumping factor: 0 (independent) .. 1 (strongly clumped) */
    clumping: number;
    /** Strand color */
    color: { r: number; g: number; b: number; a: number };
    /** Melanin ratio: 0 (pure pheomelanin / blond-red) .. 1 (pure eumelanin / black) */
    melaninRatio: number;
  };
}

// ─────────────────────────────────────────────
// Root Schema Extension
// ─────────────────────────────────────────────

/**
 * New top-level fields added to the HumanBody schema.
 * In v3.1.0–v3.2.0 these are all optional (backward-compatible).
 * In v4.0.0, skinSystem.surfaceMesh becomes required.
 */
export interface HumanBodyRenderingExtensions {
  /** The skin as a first-class renderable system */
  skinSystem?: SkinSystem;

  /** Subcutaneous fat distribution */
  adiposeSystem?: AdiposeSystem;

  /** Fascial compartments and sheets */
  fascialLayers?: FascialLayer[];

  /** Eye geometry and materials */
  eyes?: [EyeModel, EyeModel];

  /** Per-tooth geometry with enamel/dentin layering */
  teeth?: ToothModel[];

  /** Fingernail and toenail geometry */
  nails?: NailModel[];

  /** Enhanced hair system replacing the current single descriptor */
  hairSystem?: HairSystem;

  /** SSS profile library (referenced by materials) */
  sssProfiles?: SSSProfile[];
}
