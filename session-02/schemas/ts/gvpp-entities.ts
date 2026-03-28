/**
 * ─────────────────────────────────────────────────────────────────────────────
 * DISCLAIMER
 * ─────────────────────────────────────────────────────────────────────────────
 * No information within this file should be taken for granted. Any statement
 * or premise not backed by a real logical definition or verifiable reference
 * may be invalid, erroneous, or a hallucination.
 *
 * gvpp-entities.ts — Discriminated entity union, type guards, and index
 * builder for the Unified GVPP v3 schema.
 *
 * Depends on: gvpp-schema.ts
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { z } from "zod";
import type {
  UnifiedVideoProjectPackage,
  ProjectEntity,
  QualityProfileEntity,
  StoryEntity,
  ScriptEntity,
  DirectorInstructionsEntity,
  CharacterEntity,
  EnvironmentEntity,
  PropEntity,
  SceneEntity,
  ShotEntity,
  StyleGuideEntity,
  VisualAssetEntity,
  AudioAssetEntity,
  MarketingAssetEntity,
  GenericAssetEntity,
  TimelineEntity,
  EditVersionEntity,
  RenderPlanEntity,
  FinalOutputEntity,
} from "./gvpp-schema.js";

import {
  ProjectEntitySchema,
  QualityProfileEntitySchema,
  StoryEntitySchema,
  ScriptEntitySchema,
  DirectorInstructionsEntitySchema,
  CharacterEntitySchema,
  EnvironmentEntitySchema,
  PropEntitySchema,
  SceneEntitySchema,
  ShotEntitySchema,
  StyleGuideEntitySchema,
  VisualAssetEntitySchema,
  AudioAssetEntitySchema,
  MarketingAssetEntitySchema,
  GenericAssetEntitySchema,
  TimelineEntitySchema,
  EditVersionEntitySchema,
  RenderPlanEntitySchema,
  FinalOutputEntitySchema,
} from "./gvpp-schema.js";

// ═══════════════════════════════════════════════════════════════════════════════
// §1  DISCRIMINATED ENTITY UNION
// ═══════════════════════════════════════════════════════════════════════════════

export const AnyEntitySchema = z.discriminatedUnion("entityType", [
  ProjectEntitySchema,
  QualityProfileEntitySchema,
  StoryEntitySchema,
  ScriptEntitySchema,
  DirectorInstructionsEntitySchema,
  CharacterEntitySchema,
  EnvironmentEntitySchema,
  PropEntitySchema,
  SceneEntitySchema,
  ShotEntitySchema,
  StyleGuideEntitySchema,
  VisualAssetEntitySchema,
  AudioAssetEntitySchema,
  MarketingAssetEntitySchema,
  GenericAssetEntitySchema,
  TimelineEntitySchema,
  EditVersionEntitySchema,
  RenderPlanEntitySchema,
  FinalOutputEntitySchema,
]);

export type AnyEntity = z.infer<typeof AnyEntitySchema>;

export interface EntityByType {
  project: ProjectEntity;
  qualityProfile: QualityProfileEntity;
  story: StoryEntity;
  script: ScriptEntity;
  directorInstructions: DirectorInstructionsEntity;
  character: CharacterEntity;
  environment: EnvironmentEntity;
  prop: PropEntity;
  scene: SceneEntity;
  shot: ShotEntity;
  styleGuide: StyleGuideEntity;
  visualAsset: VisualAssetEntity;
  audioAsset: AudioAssetEntity;
  marketingAsset: MarketingAssetEntity;
  genericAsset: GenericAssetEntity;
  timeline: TimelineEntity;
  editVersion: EditVersionEntity;
  renderPlan: RenderPlanEntity;
  finalOutput: FinalOutputEntity;
}

export type EntityType = keyof EntityByType;

export const ENTITY_TYPES: readonly EntityType[] = [
  "project",
  "qualityProfile",
  "story",
  "script",
  "directorInstructions",
  "character",
  "environment",
  "prop",
  "scene",
  "shot",
  "styleGuide",
  "visualAsset",
  "audioAsset",
  "marketingAsset",
  "genericAsset",
  "timeline",
  "editVersion",
  "renderPlan",
  "finalOutput",
] as const;

// ═══════════════════════════════════════════════════════════════════════════════
// §2  TYPE GUARDS
// ═══════════════════════════════════════════════════════════════════════════════

export function isProjectEntity(e: AnyEntity): e is ProjectEntity { return e.entityType === "project"; }
export function isQualityProfileEntity(e: AnyEntity): e is QualityProfileEntity { return e.entityType === "qualityProfile"; }
export function isStoryEntity(e: AnyEntity): e is StoryEntity { return e.entityType === "story"; }
export function isScriptEntity(e: AnyEntity): e is ScriptEntity { return e.entityType === "script"; }
export function isDirectorInstructionsEntity(e: AnyEntity): e is DirectorInstructionsEntity { return e.entityType === "directorInstructions"; }
export function isCharacterEntity(e: AnyEntity): e is CharacterEntity { return e.entityType === "character"; }
export function isEnvironmentEntity(e: AnyEntity): e is EnvironmentEntity { return e.entityType === "environment"; }
export function isPropEntity(e: AnyEntity): e is PropEntity { return e.entityType === "prop"; }
export function isSceneEntity(e: AnyEntity): e is SceneEntity { return e.entityType === "scene"; }
export function isShotEntity(e: AnyEntity): e is ShotEntity { return e.entityType === "shot"; }
export function isStyleGuideEntity(e: AnyEntity): e is StyleGuideEntity { return e.entityType === "styleGuide"; }
export function isVisualAssetEntity(e: AnyEntity): e is VisualAssetEntity { return e.entityType === "visualAsset"; }
export function isAudioAssetEntity(e: AnyEntity): e is AudioAssetEntity { return e.entityType === "audioAsset"; }
export function isMarketingAssetEntity(e: AnyEntity): e is MarketingAssetEntity { return e.entityType === "marketingAsset"; }
export function isGenericAssetEntity(e: AnyEntity): e is GenericAssetEntity { return e.entityType === "genericAsset"; }
export function isTimelineEntity(e: AnyEntity): e is TimelineEntity { return e.entityType === "timeline"; }
export function isEditVersionEntity(e: AnyEntity): e is EditVersionEntity { return e.entityType === "editVersion"; }
export function isRenderPlanEntity(e: AnyEntity): e is RenderPlanEntity { return e.entityType === "renderPlan"; }
export function isFinalOutputEntity(e: AnyEntity): e is FinalOutputEntity { return e.entityType === "finalOutput"; }

export function isEntityOfType<T extends EntityType>(
  type: T
): (e: AnyEntity) => e is EntityByType[T] {
  return (e): e is EntityByType[T] => e.entityType === type;
}

// ═══════════════════════════════════════════════════════════════════════════════
// §3  ENTITY INDEX
// ═══════════════════════════════════════════════════════════════════════════════

export interface EntityIndex {
  readonly byId: ReadonlyMap<string, AnyEntity>;
  readonly byLogicalId: ReadonlyMap<string, readonly AnyEntity[]>;
  readonly byType: ReadonlyMap<EntityType, readonly AnyEntity[]>;
  readonly all: readonly AnyEntity[];
}

/**
 * Extract every entity from a parsed v3 package and build a flat index.
 *
 * Collection order:
 *   project → qualityProfiles → canonicalDocuments (story, script,
 *   directorInstructions) → production (characters, environments,
 *   props, scenes, shots, styleGuides) → assetLibrary (visual, audio,
 *   marketing, generic) → assembly (timelines, editVersions,
 *   renderPlans) → deliverables
 */
export function buildEntityIndex(
  pkg: UnifiedVideoProjectPackage
): EntityIndex {
  const all: AnyEntity[] = [];

  all.push(pkg.project);
  all.push(...pkg.qualityProfiles);

  all.push(pkg.canonicalDocuments.story);
  all.push(pkg.canonicalDocuments.script);
  all.push(pkg.canonicalDocuments.directorInstructions);

  all.push(...pkg.production.characters);
  all.push(...pkg.production.environments);
  all.push(...pkg.production.props);
  all.push(...pkg.production.scenes);
  all.push(...pkg.production.shots);
  all.push(...pkg.production.styleGuides);

  all.push(...pkg.assetLibrary.visualAssets);
  all.push(...pkg.assetLibrary.audioAssets);
  all.push(...pkg.assetLibrary.marketingAssets);
  all.push(...pkg.assetLibrary.genericAssets);

  all.push(...pkg.assembly.timelines);
  all.push(...pkg.assembly.editVersions);
  all.push(...pkg.assembly.renderPlans);

  all.push(...pkg.deliverables);

  const byId = new Map<string, AnyEntity>();
  const byLogicalId = new Map<string, AnyEntity[]>();
  const byType = new Map<EntityType, AnyEntity[]>();

  for (const entity of all) {
    byId.set(entity.id, entity);

    const lid = entity.logicalId;
    const existing = byLogicalId.get(lid);
    if (existing) { existing.push(entity); }
    else { byLogicalId.set(lid, [entity]); }

    const et = entity.entityType as EntityType;
    const typeList = byType.get(et);
    if (typeList) { (typeList as AnyEntity[]).push(entity); }
    else { byType.set(et, [entity]); }
  }

  return { byId, byLogicalId, byType, all };
}

export function getEntitiesOfType<T extends EntityType>(
  index: EntityIndex,
  type: T
): readonly EntityByType[T][] {
  return (index.byType.get(type) ?? []) as readonly EntityByType[T][];
}
