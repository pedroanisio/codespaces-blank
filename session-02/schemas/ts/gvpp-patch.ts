/**
 * ─────────────────────────────────────────────────────────────────────────────
 * DISCLAIMER
 * ─────────────────────────────────────────────────────────────────────────────
 * No information within this file should be taken for granted. Any statement
 * or premise not backed by a real logical definition or verifiable reference
 * may be invalid, erroneous, or a hallucination.
 *
 * gvpp-patch.ts — Partial/patch schemas for incremental entity updates,
 * and diff types for package versioning. Targets v3 schema.
 *
 * Depends on: gvpp-schema.ts, gvpp-entities.ts
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { z } from "zod";
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

import type { AnyEntity, EntityType } from "./gvpp-entities.js";

// ═══════════════════════════════════════════════════════════════════════════════
// §1  PATCH SCHEMAS
// ═══════════════════════════════════════════════════════════════════════════════

function makePatchSchema<T extends z.ZodObject<any>>(schema: T) {
  return schema.partial().required({ id: true, entityType: true });
}

export const ProjectPatchSchema = makePatchSchema(ProjectEntitySchema);
export const QualityProfilePatchSchema = makePatchSchema(QualityProfileEntitySchema);
export const StoryPatchSchema = makePatchSchema(StoryEntitySchema);
export const ScriptPatchSchema = makePatchSchema(ScriptEntitySchema);
export const DirectorInstructionsPatchSchema = makePatchSchema(DirectorInstructionsEntitySchema);
export const CharacterPatchSchema = makePatchSchema(CharacterEntitySchema);
export const EnvironmentPatchSchema = makePatchSchema(EnvironmentEntitySchema);
export const PropPatchSchema = makePatchSchema(PropEntitySchema);
export const ScenePatchSchema = makePatchSchema(SceneEntitySchema);
export const ShotPatchSchema = makePatchSchema(ShotEntitySchema);
export const StyleGuidePatchSchema = makePatchSchema(StyleGuideEntitySchema);
export const VisualAssetPatchSchema = makePatchSchema(VisualAssetEntitySchema);
export const AudioAssetPatchSchema = makePatchSchema(AudioAssetEntitySchema);
export const MarketingAssetPatchSchema = makePatchSchema(MarketingAssetEntitySchema);
export const GenericAssetPatchSchema = makePatchSchema(GenericAssetEntitySchema);
export const TimelinePatchSchema = makePatchSchema(TimelineEntitySchema);
export const EditVersionPatchSchema = makePatchSchema(EditVersionEntitySchema);
export const RenderPlanPatchSchema = makePatchSchema(RenderPlanEntitySchema);
export const FinalOutputPatchSchema = makePatchSchema(FinalOutputEntitySchema);

export type ProjectPatch = z.infer<typeof ProjectPatchSchema>;
export type QualityProfilePatch = z.infer<typeof QualityProfilePatchSchema>;
export type StoryPatch = z.infer<typeof StoryPatchSchema>;
export type ScriptPatch = z.infer<typeof ScriptPatchSchema>;
export type DirectorInstructionsPatch = z.infer<typeof DirectorInstructionsPatchSchema>;
export type CharacterPatch = z.infer<typeof CharacterPatchSchema>;
export type EnvironmentPatch = z.infer<typeof EnvironmentPatchSchema>;
export type PropPatch = z.infer<typeof PropPatchSchema>;
export type ScenePatch = z.infer<typeof ScenePatchSchema>;
export type ShotPatch = z.infer<typeof ShotPatchSchema>;
export type StyleGuidePatch = z.infer<typeof StyleGuidePatchSchema>;
export type VisualAssetPatch = z.infer<typeof VisualAssetPatchSchema>;
export type AudioAssetPatch = z.infer<typeof AudioAssetPatchSchema>;
export type MarketingAssetPatch = z.infer<typeof MarketingAssetPatchSchema>;
export type GenericAssetPatch = z.infer<typeof GenericAssetPatchSchema>;
export type TimelinePatch = z.infer<typeof TimelinePatchSchema>;
export type EditVersionPatch = z.infer<typeof EditVersionPatchSchema>;
export type RenderPlanPatch = z.infer<typeof RenderPlanPatchSchema>;
export type FinalOutputPatch = z.infer<typeof FinalOutputPatchSchema>;

// ═══════════════════════════════════════════════════════════════════════════════
// §2  DIFF TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export interface FieldChange {
  readonly field: string;
  readonly before: unknown;
  readonly after: unknown;
}

export interface EntityChange {
  readonly operation: "added" | "removed" | "modified";
  readonly entityType: EntityType;
  readonly entityId: string;
  readonly entityLogicalId: string;
  readonly entityName: string;
  readonly fieldChanges?: readonly FieldChange[];
}

export interface CollectionDiff {
  readonly path: string;
  readonly added: number;
  readonly removed: number;
  readonly modified: number;
}

export interface PackageDiff {
  readonly packageId: string;
  readonly beforeSchemaVersion: string;
  readonly afterSchemaVersion: string;
  readonly computedAt: string;
  readonly summary: {
    readonly totalChanges: number;
    readonly entitiesAdded: number;
    readonly entitiesRemoved: number;
    readonly entitiesModified: number;
    readonly collections: readonly CollectionDiff[];
  };
  readonly changes: readonly EntityChange[];
}

export function shallowEntityDiff(
  before: AnyEntity,
  after: AnyEntity
): FieldChange[] {
  const changes: FieldChange[] = [];
  const allKeys = new Set([
    ...Object.keys(before),
    ...Object.keys(after),
  ]);

  for (const key of allKeys) {
    const bVal = (before as Record<string, unknown>)[key];
    const aVal = (after as Record<string, unknown>)[key];
    if (bVal === aVal) continue;
    const bJson = JSON.stringify(bVal);
    const aJson = JSON.stringify(aVal);
    if (bJson !== aJson) {
      changes.push({ field: key, before: bVal, after: aVal });
    }
  }

  return changes;
}
