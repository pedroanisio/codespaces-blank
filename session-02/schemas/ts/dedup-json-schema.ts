/**
 * dedup-json-schema.ts — Post-processor that transforms the inlined Zod v4
 * JSON Schema output into a compact, $defs/$ref form matching the structure
 * of the hand-written JSON Schema.
 *
 * Usage: npx tsx dedup-json-schema.ts > ../gvpp-v3.schema.json
 *
 * Improvements over raw Zod toJSONSchema():
 *   1. Extracts shared types into $defs and replaces with $ref
 *   2. Extracts BaseEntity/OperationBase/WorkflowNodeBase and uses allOf composition
 *   3. Extracts Identifier and Extensions as $defs
 *   4. Strips JS safe-integer bounds (±9007199254740991) from z.number().int()
 *   5. Strips redundant Zod datetime regex patterns (format: date-time suffices)
 *   6. Injects anyOf on EntityRef for the id|logicalId constraint
 */

import { z } from "zod";
import * as schemaModule from "./gvpp-schema.js";

// ═════════════════════════════════════════════════════════════════════════════
// §1  CONFIGURATION
// ═════════════════════════════════════════════════════════════════════════════

const SKIP_EXPORTS = new Set([
  "UnifiedVideoProjectPackageSchema",
  "GenerativeVideoProjectPackageSchema",
  "BaseEntityShape",
  "BaseEntityObject",
]);

// Schemas that map to abstract base types in the original — these become
// allOf bases, not standalone defs resolved by fingerprint.
const ABSTRACT_BASES: Record<string, string> = {
  // Zod export name → $def name
  "BaseEntityObject": "BaseEntity",
};

// The base property keys for each abstract base (derived from the original schema)
const BASE_ENTITY_PROPS = [
  "id", "logicalId", "entityType", "name", "description", "status", "tags",
  "createdAt", "updatedAt", "createdBy", "owners", "version", "approval",
  "approvalChain", "qualityProfileRef", "sourceRefs", "dependencyRefs",
  "generation", "storage", "rights", "comments", "metadata", "extensions",
];
const BASE_ENTITY_REQUIRED = ["id", "logicalId", "entityType", "name", "version"];

const OP_BASE_PROPS = ["opId", "opType", "compatibleRuntimes", "runtimeHints"];
const OP_BASE_REQUIRED = ["opId", "opType"];

const WF_NODE_BASE_PROPS = ["nodeId", "name", "nodeType", "inputs", "outputs", "retryPolicy", "cacheKey", "extensions"];
const WF_NODE_BASE_REQUIRED = ["nodeId", "nodeType"];

// Entity def names that extend BaseEntity
const ENTITY_DEF_NAMES = new Set([
  "ProjectEntity", "QualityProfileEntity", "StoryEntity", "ScriptEntity",
  "DirectorInstructionsEntity", "CharacterEntity", "EnvironmentEntity",
  "PropEntity", "SceneEntity", "ShotEntity", "StyleGuideEntity",
  "VisualAssetEntity", "AudioAssetEntity", "MarketingAssetEntity",
  "GenericAssetEntity", "TimelineEntity", "EditVersionEntity",
  "RenderPlanEntity", "FinalOutputEntity",
]);

// Operation def names that extend OperationBase
const OP_DEF_NAMES = new Set([
  "ConcatOp", "OverlayOp", "ColorGradeOp", "AudioMixOp", "TransitionOp",
  "FilterOp", "EncodeOp", "ManimOp", "RetimeOp", "CustomOp",
]);

// Workflow node def names that extend WorkflowNodeBase
const WF_NODE_DEF_NAMES = new Set([
  "GenerationNode", "ApprovalNode", "TransformNode", "RenderNode",
  "ValidationNode", "NotificationNode", "CustomNode",
]);

// JS safe integer bounds emitted by Zod for z.number().int()
const JS_SAFE_INT_MAX = 9007199254740991;
const JS_SAFE_INT_MIN = -9007199254740991;

// ═════════════════════════════════════════════════════════════════════════════
// §2  GENERATE INDIVIDUAL JSON SCHEMAS
// ═════════════════════════════════════════════════════════════════════════════

interface DefEntry {
  name: string;
  schema: any;
}

const entries: DefEntry[] = [];

for (const [exportName, value] of Object.entries(schemaModule)) {
  if (!exportName.endsWith("Schema")) continue;
  if (SKIP_EXPORTS.has(exportName)) continue;
  if (!(value instanceof z.ZodType)) continue;

  const defName = exportName.replace(/Schema$/, "");

  try {
    const js = z.toJSONSchema(value, {
      unrepresentable: "any",
      io: "input",
    });
    delete (js as any).$schema;
    entries.push({ name: defName, schema: js });
  } catch {
    // skip unconvertible
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// §3  FINGERPRINTING AND DEDUP MAP
// ═════════════════════════════════════════════════════════════════════════════

function canonicalize(obj: unknown): string {
  if (obj === null || obj === undefined) return String(obj);
  if (typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) {
    return "[" + obj.map(canonicalize).join(",") + "]";
  }
  const sorted = Object.keys(obj as any).sort();
  return (
    "{" +
    sorted
      .map((k) => JSON.stringify(k) + ":" + canonicalize((obj as any)[k]))
      .join(",") +
    "}"
  );
}

// Sort: largest first for priority matching
entries.sort(
  (a, b) => canonicalize(b.schema).length - canonicalize(a.schema).length
);

const fpToDef = new Map<string, string>();
const defs: Record<string, any> = {};

// Lower threshold to capture Identifier and Extensions
const INLINE_THRESHOLD = 30;

for (const entry of entries) {
  const fp = canonicalize(entry.schema);
  if (fp.length < INLINE_THRESHOLD) continue;
  if (!fpToDef.has(fp)) {
    fpToDef.set(fp, entry.name);
  }
  defs[entry.name] = JSON.parse(JSON.stringify(entry.schema));
}

// ═════════════════════════════════════════════════════════════════════════════
// §4  STRIP ZOD ARTIFACTS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Walk any JSON value and:
 *   - Remove minimum/maximum that equal ±MAX_SAFE_INTEGER (Zod .int() artifact)
 *   - Remove redundant datetime regex patterns when format: date-time is present
 */
function stripZodArtifacts(node: unknown): unknown {
  if (node === null || node === undefined || typeof node !== "object") return node;
  if (Array.isArray(node)) return node.map(stripZodArtifacts);

  const obj = node as Record<string, unknown>;
  const result: Record<string, unknown> = {};

  for (const [key, val] of Object.entries(obj)) {
    result[key] = stripZodArtifacts(val);
  }

  // Strip safe-int bounds on integers
  if (result.type === "integer") {
    if (result.minimum === JS_SAFE_INT_MIN) delete result.minimum;
    if (result.maximum === JS_SAFE_INT_MAX) delete result.maximum;
  }

  // Strip Zod datetime mega-pattern when format: date-time is present
  if (
    result.format === "date-time" &&
    typeof result.pattern === "string" &&
    (result.pattern as string).length > 50
  ) {
    delete result.pattern;
  }

  return result;
}

// Apply to all defs
for (const [defName, defSchema] of Object.entries(defs)) {
  defs[defName] = stripZodArtifacts(defSchema);
}

// ═════════════════════════════════════════════════════════════════════════════
// §5  SUBTREE REPLACEMENT ($ref)
// ═════════════════════════════════════════════════════════════════════════════

// Rebuild fingerprint map after stripping artifacts
fpToDef.clear();
for (const entry of entries) {
  const stripped = stripZodArtifacts(entry.schema) as Record<string, unknown>;
  const fp = canonicalize(stripped);
  if (fp.length < INLINE_THRESHOLD) continue;
  if (!fpToDef.has(fp)) {
    fpToDef.set(fp, entry.name);
  }
}

function replaceSubtrees(
  node: unknown,
  skipRoot: boolean = false
): unknown {
  if (node === null || node === undefined || typeof node !== "object") return node;
  if (Array.isArray(node)) return node.map((item) => replaceSubtrees(item));

  const obj = node as Record<string, unknown>;
  if (obj.$ref) return obj;

  if (!skipRoot) {
    const fp = canonicalize(obj);
    const defName = fpToDef.get(fp);
    if (defName && fp.length >= INLINE_THRESHOLD) {
      return { $ref: `#/$defs/${defName}` };
    }
  }

  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(obj)) {
    result[key] = replaceSubtrees(val);
  }
  return result;
}

// Iterative dedup passes
for (let pass = 0; pass < 10; pass++) {
  let changes = 0;
  for (const [defName, defSchema] of Object.entries(defs)) {
    const before = canonicalize(defSchema);
    const after = replaceSubtrees(defSchema, true);
    if (before !== canonicalize(after)) {
      defs[defName] = after;
      changes++;
    }
  }
  if (changes === 0) {
    process.stderr.write(`[dedup] Subtree replacement stabilized after ${pass + 1} pass(es)\n`);
    break;
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// §6  EXTRACT BASE TYPES (allOf COMPOSITION)
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Given a flat entity def, split it into allOf: [$ref base, {extension props}].
 */
function extractBase(
  defSchema: any,
  baseProps: string[],
  baseRequired: string[],
  baseName: string
): any {
  if (!defSchema.properties) return defSchema;

  const props = defSchema.properties as Record<string, unknown>;
  const req: string[] = defSchema.required ?? [];

  const basePropsObj: Record<string, unknown> = {};
  const extPropsObj: Record<string, unknown> = {};

  for (const [key, val] of Object.entries(props)) {
    if (baseProps.includes(key)) {
      basePropsObj[key] = val;
    } else {
      extPropsObj[key] = val;
    }
  }

  // Only extract if there's meaningful overlap
  if (Object.keys(basePropsObj).length < baseProps.length * 0.5) {
    return defSchema;
  }

  const extRequired = req.filter((r) => !baseRequired.includes(r));

  const extension: any = {
    type: "object",
    properties: extPropsObj,
  };
  if (extRequired.length > 0) {
    extension.required = extRequired;
  }
  if (defSchema.additionalProperties !== undefined) {
    extension.additionalProperties = defSchema.additionalProperties;
  }

  return {
    allOf: [
      { $ref: `#/$defs/${baseName}` },
      extension,
    ],
  };
}

// Build the BaseEntity def from the first entity we find
function buildBaseDef(
  baseProps: string[],
  baseRequired: string[],
  sampleDefName: string
): any {
  const sample = defs[sampleDefName];
  if (!sample?.properties) return null;

  const baseDef: any = {
    type: "object",
    properties: {} as Record<string, unknown>,
    required: baseRequired,
    additionalProperties: false,
  };

  for (const prop of baseProps) {
    if (sample.properties[prop] !== undefined) {
      baseDef.properties[prop] = sample.properties[prop];
    }
  }

  return baseDef;
}

// Extract BaseEntity
const sampleEntity = [...ENTITY_DEF_NAMES].find((n) => defs[n]);
if (sampleEntity) {
  const baseDef = buildBaseDef(BASE_ENTITY_PROPS, BASE_ENTITY_REQUIRED, sampleEntity);
  if (baseDef) {
    defs["BaseEntity"] = baseDef;
    for (const entityName of ENTITY_DEF_NAMES) {
      if (defs[entityName]) {
        defs[entityName] = extractBase(
          defs[entityName],
          BASE_ENTITY_PROPS,
          BASE_ENTITY_REQUIRED,
          "BaseEntity"
        );
      }
    }
    process.stderr.write(`[dedup] Extracted BaseEntity from ${ENTITY_DEF_NAMES.size} entity defs\n`);
  }
}

// Extract OperationBase
const sampleOp = [...OP_DEF_NAMES].find((n) => defs[n]);
if (sampleOp) {
  const baseDef = buildBaseDef(OP_BASE_PROPS, OP_BASE_REQUIRED, sampleOp);
  if (baseDef) {
    defs["OperationBase"] = baseDef;
    for (const opName of OP_DEF_NAMES) {
      if (defs[opName]) {
        defs[opName] = extractBase(
          defs[opName],
          OP_BASE_PROPS,
          OP_BASE_REQUIRED,
          "OperationBase"
        );
      }
    }
    process.stderr.write(`[dedup] Extracted OperationBase from ${OP_DEF_NAMES.size} operation defs\n`);
  }
}

// Extract WorkflowNodeBase
const sampleWf = [...WF_NODE_DEF_NAMES].find((n) => defs[n]);
if (sampleWf) {
  const baseDef = buildBaseDef(WF_NODE_BASE_PROPS, WF_NODE_BASE_REQUIRED, sampleWf);
  if (baseDef) {
    defs["WorkflowNodeBase"] = baseDef;
    for (const wfName of WF_NODE_DEF_NAMES) {
      if (defs[wfName]) {
        defs[wfName] = extractBase(
          defs[wfName],
          WF_NODE_BASE_PROPS,
          WF_NODE_BASE_REQUIRED,
          "WorkflowNodeBase"
        );
      }
    }
    process.stderr.write(`[dedup] Extracted WorkflowNodeBase from ${WF_NODE_DEF_NAMES.size} workflow node defs\n`);
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// §7  ADD Identifier AND Extensions $defs
// ═════════════════════════════════════════════════════════════════════════════

// Generate Identifier and Extensions and register them
const identifierSchema = stripZodArtifacts(
  z.toJSONSchema(schemaModule.IdentifierSchema, { unrepresentable: "any", io: "input" })
) as any;
delete identifierSchema.$schema;
defs["Identifier"] = identifierSchema;

// Extensions = looseObject({}) → additionalProperties: true
defs["Extensions"] = {
  type: "object",
  additionalProperties: true,
};

// Register their fingerprints
fpToDef.set(canonicalize(identifierSchema), "Identifier");
fpToDef.set(canonicalize(defs["Extensions"]), "Extensions");

// Run another dedup pass to replace Identifier/Extensions inline occurrences inside defs
for (let pass = 0; pass < 5; pass++) {
  let changes = 0;
  for (const [defName, defSchema] of Object.entries(defs)) {
    if (defName === "Identifier" || defName === "Extensions") continue;
    const before = canonicalize(defSchema);
    const after = replaceSubtrees(defSchema, true);
    if (before !== canonicalize(after)) {
      defs[defName] = after;
      changes++;
    }
  }
  if (changes === 0) break;
}

// Also replace inside allOf extension branches
for (const [defName, defSchema] of Object.entries(defs)) {
  if (defSchema.allOf) {
    defSchema.allOf = defSchema.allOf.map((branch: any) => {
      if (branch.$ref) return branch;
      return replaceSubtrees(branch, true);
    });
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// §8  ALIAS MERGING AND CLEANUP
// ═════════════════════════════════════════════════════════════════════════════

// Remove duplicate defs
const fpToCanonicalName = new Map<string, string>();
const aliasMap = new Map<string, string>();

for (const [defName, defSchema] of Object.entries(defs)) {
  const fp = canonicalize(defSchema);
  const existing = fpToCanonicalName.get(fp);
  if (existing && existing !== defName) {
    aliasMap.set(defName, existing);
  } else {
    fpToCanonicalName.set(fp, defName);
  }
}

for (const alias of aliasMap.keys()) {
  delete defs[alias];
}

function rewriteAliases(node: unknown): unknown {
  if (node === null || node === undefined || typeof node !== "object") return node;
  if (Array.isArray(node)) return node.map(rewriteAliases);
  const obj = node as Record<string, unknown>;
  if (typeof obj.$ref === "string") {
    const refName = (obj.$ref as string).replace("#/$defs/", "");
    const canonical = aliasMap.get(refName);
    if (canonical) return { $ref: `#/$defs/${canonical}` };
    return obj;
  }
  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(obj)) {
    result[key] = rewriteAliases(val);
  }
  return result;
}

for (const [defName, defSchema] of Object.entries(defs)) {
  defs[defName] = rewriteAliases(defSchema);
}

// ═════════════════════════════════════════════════════════════════════════════
// §9  BUILD ROOT SCHEMA
// ═════════════════════════════════════════════════════════════════════════════

const fullInlined = z.toJSONSchema(
  schemaModule.UnifiedVideoProjectPackageSchema,
  { unrepresentable: "any", io: "input" }
) as Record<string, unknown>;

const rootCleaned = stripZodArtifacts(fullInlined) as Record<string, unknown>;
const rootDeduped = replaceSubtrees(rootCleaned, true) as Record<string, unknown>;
const rootFinal = rewriteAliases(rootDeduped) as Record<string, unknown>;

// ═════════════════════════════════════════════════════════════════════════════
// §10  INJECT EntityRef anyOf
// ═════════════════════════════════════════════════════════════════════════════

if (defs["EntityRef"]) {
  defs["EntityRef"] = {
    ...defs["EntityRef"],
    anyOf: [{ required: ["id"] }, { required: ["logicalId"] }],
  };
}

// ═════════════════════════════════════════════════════════════════════════════
// §11  CLEAN UP PASS-THROUGH AND UNREFERENCED DEFS
// ═════════════════════════════════════════════════════════════════════════════

// Remove defs that are just a $ref to another def
for (const [defName, defSchema] of Object.entries(defs)) {
  if (defSchema.$ref && Object.keys(defSchema).length === 1) {
    const target = defSchema.$ref;
    const refStr = `#/$defs/${defName}`;
    const replaceRef = (node: unknown): unknown => {
      if (node === null || node === undefined || typeof node !== "object") return node;
      if (Array.isArray(node)) return node.map(replaceRef);
      const obj = node as Record<string, unknown>;
      if (obj.$ref === refStr) return { $ref: target };
      const result: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(obj)) {
        result[k] = replaceRef(v);
      }
      return result;
    };
    Object.assign(rootFinal, replaceRef(rootFinal));
    for (const [otherName, otherSchema] of Object.entries(defs)) {
      if (otherName !== defName) defs[otherName] = replaceRef(otherSchema);
    }
    delete defs[defName];
  }
}

// Remove unreferenced defs
function collectRefs(node: unknown, refs: Set<string>): void {
  if (node === null || node === undefined || typeof node !== "object") return;
  if (Array.isArray(node)) { node.forEach((n) => collectRefs(n, refs)); return; }
  const obj = node as Record<string, unknown>;
  if (typeof obj.$ref === "string") {
    refs.add((obj.$ref as string).replace("#/$defs/", ""));
  }
  for (const val of Object.values(obj)) collectRefs(val, refs);
}

for (let i = 0; i < 10; i++) {
  const usedRefs = new Set<string>();
  collectRefs(rootFinal, usedRefs);
  for (const defSchema of Object.values(defs)) collectRefs(defSchema, usedRefs);

  let removed = 0;
  for (const defName of Object.keys(defs)) {
    if (!usedRefs.has(defName)) { delete defs[defName]; removed++; }
  }
  if (removed === 0) break;
}

// ═════════════════════════════════════════════════════════════════════════════
// §12  ASSEMBLE AND OUTPUT
// ═════════════════════════════════════════════════════════════════════════════

const final: Record<string, unknown> = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "https://example.org/schemas/unified-video-project-v3.schema.json",
  title: "Unified Generative Video Project Package",
  description:
    "Tool-agnostic, Draft 2020-12 JSON Schema for autonomous generative-AI video production. " +
    "Generated from Zod v4 TypeScript source (gvpp-schema.ts). Schema version 3.0.0.",
};

for (const [key, val] of Object.entries(rootFinal)) {
  if (key === "$schema") continue;
  final[key] = val;
}

const sortedDefs: Record<string, any> = {};
for (const key of Object.keys(defs).sort()) {
  sortedDefs[key] = defs[key];
}
final.$defs = sortedDefs;

const output = JSON.stringify(final, null, 2);
console.log(output);

// ═════════════════════════════════════════════════════════════════════════════
// §13  STATS
// ═════════════════════════════════════════════════════════════════════════════

const origSize = JSON.stringify(fullInlined).length;
process.stderr.write(
  `[dedup] $defs: ${Object.keys(sortedDefs).length}, ` +
  `aliases merged: ${aliasMap.size}, ` +
  `output: ${output.split("\n").length} lines / ${(output.length / 1024).toFixed(1)} KB ` +
  `(was ${(origSize / 1024).toFixed(1)} KB inlined)\n`
);
