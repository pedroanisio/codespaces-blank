/**
 * ─────────────────────────────────────────────────────────────────────────────
 * DISCLAIMER
 * ─────────────────────────────────────────────────────────────────────────────
 * No information within this file should be taken for granted. Any statement
 * or premise not backed by a real logical definition or verifiable reference
 * may be invalid, erroneous, or a hallucination.
 *
 * gvpp-integrity.ts — Referential integrity validation for v3 GVPP packages.
 *
 * Depends on: gvpp-schema.ts, gvpp-entities.ts
 * ─────────────────────────────────────────────────────────────────────────────
 */

import type {
  UnifiedVideoProjectPackage,
  EntityRef,
  TimelineClip,
} from "./gvpp-schema.js";
import { buildEntityIndex, type EntityIndex } from "./gvpp-entities.js";

// ═══════════════════════════════════════════════════════════════════════════════
// §1  RESULT TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type Severity = "error" | "warning" | "info";

export interface IntegrityIssue {
  readonly severity: Severity;
  readonly code: string;
  readonly path: string;
  readonly message: string;
  readonly ref?: EntityRef;
}

export interface IntegrityResult {
  readonly valid: boolean;
  readonly issues: readonly IntegrityIssue[];
  readonly counts: {
    readonly errors: number;
    readonly warnings: number;
    readonly info: number;
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// §2  REF EXTRACTION
// ═══════════════════════════════════════════════════════════════════════════════

interface LocatedRef {
  path: string;
  ref: EntityRef;
}

function extractRefs(value: unknown, basePath: string): LocatedRef[] {
  const results: LocatedRef[] = [];

  if (value === null || value === undefined || typeof value !== "object") {
    return results;
  }

  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      results.push(...extractRefs(value[i], `${basePath}[${i}]`));
    }
    return results;
  }

  const obj = value as Record<string, unknown>;

  const hasId = typeof obj["id"] === "string";
  const hasLogicalId = typeof obj["logicalId"] === "string";
  const hasEntityType = "entityType" in obj;

  if ((hasId || hasLogicalId) && !hasEntityType) {
    const keys = Object.keys(obj);
    const refKeys = new Set([
      "id", "logicalId", "versionSelector", "role", "notes",
    ]);
    const isLikelyRef =
      keys.length <= 5 && keys.every((k) => refKeys.has(k));

    if (isLikelyRef) {
      results.push({ path: basePath, ref: obj as unknown as EntityRef });
      return results;
    }
  }

  for (const [key, val] of Object.entries(obj)) {
    results.push(...extractRefs(val, `${basePath}.${key}`));
  }

  return results;
}

// ═══════════════════════════════════════════════════════════════════════════════
// §3  VALIDATION PASSES
// ═══════════════════════════════════════════════════════════════════════════════

function checkRefResolution(
  pkg: UnifiedVideoProjectPackage,
  index: EntityIndex
): IntegrityIssue[] {
  const issues: IntegrityIssue[] = [];
  const allRefs = extractRefs(pkg, "$");

  for (const { path, ref } of allRefs) {
    const refId = ref.id;
    const refLogicalId = ref.logicalId;
    let resolved = false;

    if (refId !== undefined && index.byId.has(refId)) resolved = true;
    if (refLogicalId !== undefined && index.byLogicalId.has(refLogicalId))
      resolved = true;

    if (!resolved) {
      const target = refId ?? refLogicalId ?? "(empty ref)";
      issues.push({
        severity: "error",
        code: "UNRESOLVED_REF",
        path,
        message: `EntityRef target "${target}" does not resolve to any entity in the package.`,
        ref,
      });
    }
  }

  return issues;
}

function checkIdUniqueness(
  _pkg: UnifiedVideoProjectPackage,
  index: EntityIndex
): IntegrityIssue[] {
  const issues: IntegrityIssue[] = [];
  const seen = new Map<string, string[]>();

  for (const entity of index.all) {
    const id = entity.id;
    const paths = seen.get(id);
    if (paths) {
      paths.push(`${entity.entityType}:${entity.name}`);
    } else {
      seen.set(id, [`${entity.entityType}:${entity.name}`]);
    }
  }

  for (const [id, locations] of seen) {
    if (locations.length > 1) {
      issues.push({
        severity: "error",
        code: "DUPLICATE_ID",
        path: "$",
        message:
          `Entity id "${id}" is used by ${locations.length} entities: ` +
          locations.join(", ") + ".",
      });
    }
  }

  return issues;
}

function checkTemporalCoherence(
  pkg: UnifiedVideoProjectPackage,
  _index: EntityIndex
): IntegrityIssue[] {
  const issues: IntegrityIssue[] = [];

  for (const scene of pkg.production.scenes) {
    const shotEntities = pkg.production.shots.filter((s) => {
      const ref = s.sceneRef;
      return ref.id === scene.id || ref.logicalId === scene.logicalId;
    });

    if (shotEntities.length > 0) {
      const shotDurationSum = shotEntities.reduce(
        (sum, s) => sum + s.targetDurationSec, 0
      );
      const tolerance = scene.targetDurationSec * 0.5;
      const diff = Math.abs(shotDurationSum - scene.targetDurationSec);

      if (diff > tolerance) {
        issues.push({
          severity: "warning",
          code: "SHOT_DURATION_MISMATCH",
          path: `$.production.scenes[id=${scene.id}]`,
          message:
            `Scene "${scene.name}" has targetDurationSec=${scene.targetDurationSec} ` +
            `but its ${shotEntities.length} shots sum to ${shotDurationSum.toFixed(2)}s ` +
            `(difference: ${diff.toFixed(2)}s, tolerance: ${tolerance.toFixed(2)}s).`,
        });
      }
    }
  }

  const sceneDurationSum = pkg.production.scenes.reduce(
    (sum, s) => sum + s.targetDurationSec, 0
  );
  const projectTarget = pkg.project.targetRuntimeSec;
  const projectTolerance = projectTarget * 0.5;

  if (Math.abs(sceneDurationSum - projectTarget) > projectTolerance) {
    issues.push({
      severity: "warning",
      code: "SCENE_TOTAL_MISMATCH",
      path: "$.project.targetRuntimeSec",
      message:
        `Project targetRuntimeSec=${projectTarget} but scenes sum to ` +
        `${sceneDurationSum.toFixed(2)}s.`,
    });
  }

  return issues;
}

/**
 * v3 timeline clip overlap detection.
 *
 * v3 separates clips by type (videoClips, audioClips, subtitleClips)
 * rather than using tracks. Overlap is checked within each clip array,
 * grouped by layerOrder.
 */
function checkClipOverlaps(
  pkg: UnifiedVideoProjectPackage
): IntegrityIssue[] {
  const issues: IntegrityIssue[] = [];

  for (const tl of pkg.assembly.timelines) {
    const clipArrays: { name: string; clips: readonly TimelineClip[] }[] = [
      { name: "videoClips", clips: tl.videoClips ?? [] },
      { name: "audioClips", clips: tl.audioClips ?? [] },
      { name: "subtitleClips", clips: tl.subtitleClips ?? [] },
    ];

    for (const { name, clips } of clipArrays) {
      const byLayer = new Map<number, TimelineClip[]>();
      for (const clip of clips) {
        const layer = clip.layerOrder ?? 0;
        const existing = byLayer.get(layer);
        if (existing) { existing.push(clip); }
        else { byLayer.set(layer, [clip]); }
      }

      for (const [layer, layerClips] of byLayer) {
        const sorted = [...layerClips].sort(
          (a, b) => a.timelineStartSec - b.timelineStartSec
        );

        for (let i = 1; i < sorted.length; i++) {
          const prev = sorted[i - 1];
          const curr = sorted[i];
          const prevEnd = prev.timelineStartSec + prev.durationSec;

          if (curr.timelineStartSec < prevEnd) {
            issues.push({
              severity: "warning",
              code: "CLIP_OVERLAP",
              path: `$.assembly.timelines[id=${tl.id}].${name}`,
              message:
                `Clips "${prev.clipId}" and "${curr.clipId}" overlap on ` +
                `layer ${layer}: "${prev.clipId}" ends at ${prevEnd.toFixed(3)}s, ` +
                `"${curr.clipId}" starts at ${curr.timelineStartSec.toFixed(3)}s.`,
            });
          }
        }
      }
    }
  }

  return issues;
}

// ═══════════════════════════════════════════════════════════════════════════════
// §4  PUBLIC API
// ═══════════════════════════════════════════════════════════════════════════════

export interface ValidateOptions {
  skipTemporal?: boolean;
  skipClipOverlaps?: boolean;
  skipIdUniqueness?: boolean;
  strictWarnings?: boolean;
}

export function validateIntegrity(
  pkg: UnifiedVideoProjectPackage,
  options: ValidateOptions = {}
): IntegrityResult {
  const index = buildEntityIndex(pkg);
  const issues: IntegrityIssue[] = [];

  issues.push(...checkRefResolution(pkg, index));

  if (!options.skipIdUniqueness) {
    issues.push(...checkIdUniqueness(pkg, index));
  }
  if (!options.skipTemporal) {
    issues.push(...checkTemporalCoherence(pkg, index));
  }
  if (!options.skipClipOverlaps) {
    issues.push(...checkClipOverlaps(pkg));
  }

  const severityOrder: Record<Severity, number> = {
    error: 0, warning: 1, info: 2,
  };
  issues.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  const counts = {
    errors: issues.filter((i) => i.severity === "error").length,
    warnings: issues.filter((i) => i.severity === "warning").length,
    info: issues.filter((i) => i.severity === "info").length,
  };

  const valid = options.strictWarnings
    ? counts.errors === 0 && counts.warnings === 0
    : counts.errors === 0;

  return { valid, issues, counts };
}

export function assertIntegrity(
  pkg: UnifiedVideoProjectPackage,
  options: ValidateOptions = {}
): void {
  const result = validateIntegrity(pkg, options);
  if (!result.valid) {
    const errorSummary = result.issues
      .filter((i) => i.severity === "error")
      .map((i) => `  [${i.code}] ${i.path}: ${i.message}`)
      .join("\n");
    throw new Error(
      `GVPP integrity validation failed with ${result.counts.errors} error(s):\n${errorSummary}`
    );
  }
}
