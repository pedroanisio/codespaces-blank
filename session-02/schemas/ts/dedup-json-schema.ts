/**
 * dedup-json-schema.ts — Post-processor that builds a $defs/$ref JSON Schema
 * from the Zod schemas, then replaces repeated structural subtrees with $ref.
 *
 * Usage: npx tsx dedup-json-schema.ts > ../gvpp-v3.schema.json
 *
 * Strategy:
 *   1. Generate individual JSON Schema for each named Zod export
 *   2. Build a canonical fingerprint → defName map
 *   3. Walk each def and the root schema, replacing matching subtrees with $ref
 *   4. Iteratively dedup until stable (handles nested shared types)
 *   5. Inject anyOf for EntityRef
 */

import { z } from "zod";
import * as schemaModule from "./gvpp-schema.js";

// ─── Config ──────────────────────────────────────────────────────────────────

const SKIP_EXPORTS = new Set([
  "UnifiedVideoProjectPackageSchema",
  "GenerativeVideoProjectPackageSchema",
  "BaseEntityShape",
  "BaseEntityObject",
]);

// Primitives too small to be worth a $def
const INLINE_THRESHOLD = 80; // chars of JSON — below this, don't extract

// ─── §1: Generate individual JSON Schemas ────────────────────────────────────

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

// ─── §2: Build fingerprint maps ─────────────────────────────────────────────

function canonicalize(obj: unknown): string {
  if (obj === null || obj === undefined) return String(obj);
  if (typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) {
    return "[" + obj.map(canonicalize).join(",") + "]";
  }
  const sorted = Object.keys(obj as any).sort();
  return "{" + sorted.map(k => JSON.stringify(k) + ":" + canonicalize((obj as any)[k])).join(",") + "}";
}

// Map from canonical fingerprint → def name (first wins = most specific)
// Sort entries: largest schemas first so they get priority
entries.sort((a, b) => canonicalize(b.schema).length - canonicalize(a.schema).length);

const fpToDef = new Map<string, string>();
const defs: Record<string, any> = {};

for (const entry of entries) {
  const fp = canonicalize(entry.schema);
  if (fp.length < INLINE_THRESHOLD) continue; // too small
  if (!fpToDef.has(fp)) {
    fpToDef.set(fp, entry.name);
  }
  // Always store the def under its own name — even if fingerprint matches another
  defs[entry.name] = JSON.parse(JSON.stringify(entry.schema));
}

// ─── §3: Recursive replacement ──────────────────────────────────────────────

function replaceSubtrees(node: unknown, skipRoot: boolean = false): unknown {
  if (node === null || node === undefined || typeof node !== "object") return node;

  if (Array.isArray(node)) {
    return node.map(item => replaceSubtrees(item));
  }

  const obj = node as Record<string, unknown>;

  // If this node already is a $ref, leave it
  if (obj.$ref) return obj;

  // Try to match this node against known defs
  if (!skipRoot) {
    const fp = canonicalize(obj);
    const defName = fpToDef.get(fp);
    if (defName && fp.length >= INLINE_THRESHOLD) {
      return { $ref: `#/$defs/${defName}` };
    }
  }

  // Recurse into children
  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(obj)) {
    result[key] = replaceSubtrees(val);
  }
  return result;
}

// Iteratively dedup: first pass replaces in root, subsequent passes replace inside defs
// Keep going until no more replacements happen
function dedupPass(): number {
  let count = 0;

  // Dedup inside each def
  for (const [defName, defSchema] of Object.entries(defs)) {
    const before = canonicalize(defSchema);
    // Don't replace the def's own root (skipRoot=true) — only its children
    const after = replaceSubtrees(defSchema, true);
    const afterFp = canonicalize(after);
    if (before !== afterFp) {
      defs[defName] = after;
      count++;
    }
  }

  return count;
}

// Run passes until stable
for (let pass = 0; pass < 10; pass++) {
  const changes = dedupPass();
  if (changes === 0) {
    process.stderr.write(`[dedup] Stabilized after ${pass + 1} pass(es)\n`);
    break;
  }
}

// ─── §4: Remove duplicate defs that are now identical to another ─────────────

// After dedup passes, some defs may have become identical $ref wrappers or
// have the same structure. Merge them.
const fpToCanonicalName = new Map<string, string>();
const aliasMap = new Map<string, string>(); // defName → canonical defName

for (const [defName, defSchema] of Object.entries(defs)) {
  const fp = canonicalize(defSchema);
  const existing = fpToCanonicalName.get(fp);
  if (existing && existing !== defName) {
    aliasMap.set(defName, existing);
  } else {
    fpToCanonicalName.set(fp, defName);
  }
}

// Remove aliased defs
for (const alias of aliasMap.keys()) {
  delete defs[alias];
}

// Rewrite $refs pointing to aliases
function rewriteAliases(node: unknown): unknown {
  if (node === null || node === undefined || typeof node !== "object") return node;
  if (Array.isArray(node)) return node.map(rewriteAliases);

  const obj = node as Record<string, unknown>;
  if (typeof obj.$ref === "string") {
    const refName = (obj.$ref as string).replace("#/$defs/", "");
    const canonical = aliasMap.get(refName);
    if (canonical) {
      return { $ref: `#/$defs/${canonical}` };
    }
    return obj;
  }

  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(obj)) {
    result[key] = rewriteAliases(val);
  }
  return result;
}

// Rewrite aliases in all defs
for (const [defName, defSchema] of Object.entries(defs)) {
  defs[defName] = rewriteAliases(defSchema);
}

// ─── §5: Build root schema with refs ─────────────────────────────────────────

const fullInlined = z.toJSONSchema(schemaModule.UnifiedVideoProjectPackageSchema, {
  unrepresentable: "any",
  io: "input",
}) as Record<string, unknown>;

const rootDeduped = replaceSubtrees(fullInlined, true) as Record<string, unknown>;
const rootFinal = rewriteAliases(rootDeduped) as Record<string, unknown>;

// ─── §6: Inject anyOf for EntityRef ──────────────────────────────────────────

if (defs["EntityRef"]) {
  defs["EntityRef"] = {
    ...defs["EntityRef"],
    anyOf: [
      { required: ["id"] },
      { required: ["logicalId"] },
    ],
  };
}

// ─── §7: Clean up defs that are just $ref to another def (pass-through) ──────

for (const [defName, defSchema] of Object.entries(defs)) {
  if (defSchema.$ref && Object.keys(defSchema).length === 1) {
    // This def is just an alias — inline it
    const target = defSchema.$ref;
    // Replace all references to this def with the target
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

    // Replace in root
    Object.assign(rootFinal, replaceRef(rootFinal));

    // Replace in other defs
    for (const [otherName, otherSchema] of Object.entries(defs)) {
      if (otherName !== defName) {
        defs[otherName] = replaceRef(otherSchema);
      }
    }

    delete defs[defName];
  }
}

// ─── §8: Remove unreferenced defs ───────────────────────────────────────────

function collectRefs(node: unknown, refs: Set<string>): void {
  if (node === null || node === undefined || typeof node !== "object") return;
  if (Array.isArray(node)) { node.forEach(n => collectRefs(n, refs)); return; }
  const obj = node as Record<string, unknown>;
  if (typeof obj.$ref === "string") {
    const name = (obj.$ref as string).replace("#/$defs/", "");
    refs.add(name);
  }
  for (const val of Object.values(obj)) {
    collectRefs(val, refs);
  }
}

// Iteratively remove unreferenced defs (removing one may make others unreferenced)
for (let i = 0; i < 10; i++) {
  const usedRefs = new Set<string>();
  collectRefs(rootFinal, usedRefs);
  for (const defSchema of Object.values(defs)) {
    collectRefs(defSchema, usedRefs);
  }

  let removed = 0;
  for (const defName of Object.keys(defs)) {
    if (!usedRefs.has(defName)) {
      delete defs[defName];
      removed++;
    }
  }
  if (removed === 0) break;
}

// ─── §9: Assemble and output ─────────────────────────────────────────────────

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

// Sort $defs alphabetically
const sortedDefs: Record<string, any> = {};
for (const key of Object.keys(defs).sort()) {
  sortedDefs[key] = defs[key];
}
final.$defs = sortedDefs;

const output = JSON.stringify(final, null, 2);
console.log(output);

// ─── Stats ───────────────────────────────────────────────────────────────────

const origSize = JSON.stringify(fullInlined).length;
process.stderr.write(
  `[dedup] $defs: ${Object.keys(sortedDefs).length}, ` +
  `aliases merged: ${aliasMap.size}, ` +
  `output: ${output.split("\n").length} lines / ${(output.length / 1024).toFixed(1)} KB ` +
  `(was ${(origSize / 1024).toFixed(1)} KB inlined)\n`
);
