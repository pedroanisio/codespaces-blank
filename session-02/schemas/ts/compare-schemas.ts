/**
 * compare-schemas.ts — Deep semantic comparison of generated vs original JSON Schema.
 *
 * Usage: npx tsx compare-schemas.ts
 */

import * as fs from "fs";
import * as path from "path";

const generated = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, "../generated-v3.schema.json"), "utf8")
);
const original = JSON.parse(
  fs.readFileSync(
    path.resolve(__dirname, "../claude-unified-video-project-v3.schema.json"),
    "utf8"
  )
);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function resolveDef(schema: any, root: any): any {
  if (schema && schema.$ref && typeof schema.$ref === "string") {
    const refPath = schema.$ref.replace("#/", "").split("/");
    let resolved = root;
    for (const seg of refPath) {
      resolved = resolved?.[seg];
    }
    return resolved ?? schema;
  }
  return schema;
}

interface Diff {
  path: string;
  kind: string;
  detail: string;
}

const diffs: Diff[] = [];

function compareSchemas(
  genSchema: any,
  origSchema: any,
  origRoot: any,
  path: string,
  depth: number = 0
): void {
  if (depth > 15) return; // prevent infinite recursion

  // Resolve $ref in original
  const orig = resolveDef(origSchema, origRoot);
  const gen = genSchema;

  if (!gen && !orig) return;
  if (!gen && orig) {
    diffs.push({ path, kind: "MISSING_IN_GENERATED", detail: `Original has schema but generated is missing` });
    return;
  }
  if (gen && !orig) {
    diffs.push({ path, kind: "MISSING_IN_ORIGINAL", detail: `Generated has schema but original is missing` });
    return;
  }

  // Compare type
  if (gen.type !== orig.type && orig.type !== undefined) {
    // Check if it's an enum that appears differently
    if (!(gen.enum && orig.enum)) {
      diffs.push({
        path,
        kind: "TYPE_MISMATCH",
        detail: `gen: ${gen.type}, orig: ${orig.type}`,
      });
    }
  }

  // Compare required arrays
  const genReq = new Set(gen.required ?? []);
  const origReq = new Set(orig.required ?? []);
  for (const r of genReq) {
    if (!origReq.has(r)) {
      diffs.push({ path, kind: "EXTRA_REQUIRED_GEN", detail: `"${r}" is required in generated but not original` });
    }
  }
  for (const r of origReq) {
    if (!genReq.has(r)) {
      diffs.push({ path, kind: "MISSING_REQUIRED_GEN", detail: `"${r}" is required in original but not generated` });
    }
  }

  // Compare additionalProperties
  if (gen.additionalProperties !== orig.additionalProperties) {
    if (gen.additionalProperties === false && orig.additionalProperties === undefined) {
      // Zod strictObject → additionalProperties:false is stricter, note it
    } else if (gen.additionalProperties !== undefined && orig.additionalProperties !== undefined) {
      diffs.push({
        path,
        kind: "ADDITIONAL_PROPS_DIFF",
        detail: `gen: ${JSON.stringify(gen.additionalProperties)}, orig: ${JSON.stringify(orig.additionalProperties)}`,
      });
    }
  }

  // Compare enum values
  if (gen.enum || orig.enum) {
    const genEnum = JSON.stringify(gen.enum?.sort?.() ?? gen.enum);
    const origEnum = JSON.stringify(orig.enum?.sort?.() ?? orig.enum);
    if (genEnum !== origEnum) {
      diffs.push({
        path,
        kind: "ENUM_DIFF",
        detail: `gen: ${gen.enum?.length ?? 0} values, orig: ${orig.enum?.length ?? 0} values\n  gen:  ${JSON.stringify(gen.enum)}\n  orig: ${JSON.stringify(orig.enum)}`,
      });
    }
  }

  // Compare const
  if (gen.const !== orig.const && (gen.const !== undefined || orig.const !== undefined)) {
    diffs.push({ path, kind: "CONST_DIFF", detail: `gen: ${gen.const}, orig: ${orig.const}` });
  }

  // Compare pattern
  if (gen.pattern && orig.pattern && gen.pattern !== orig.pattern) {
    // Only report if they're meaningfully different (not just the zod datetime mega-pattern)
    if (!gen.pattern.includes("2468") || orig.pattern !== undefined) {
      diffs.push({
        path,
        kind: "PATTERN_DIFF",
        detail: `gen: ${gen.pattern.slice(0, 60)}...\n  orig: ${orig.pattern?.slice(0, 60)}...`,
      });
    }
  }

  // Compare numeric constraints
  for (const k of ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "minItems", "maxItems"]) {
    if (gen[k] !== orig[k] && (gen[k] !== undefined || orig[k] !== undefined)) {
      diffs.push({
        path,
        kind: "CONSTRAINT_DIFF",
        detail: `${k}: gen=${gen[k]}, orig=${orig[k]}`,
      });
    }
  }

  // Compare properties recursively
  if (gen.properties || orig.properties) {
    const genProps = Object.keys(gen.properties ?? {});
    const origProps = Object.keys(orig.properties ?? {});
    const allProps = new Set([...genProps, ...origProps]);

    for (const prop of allProps) {
      const gp = gen.properties?.[prop];
      const op = orig.properties?.[prop];

      if (!gp && op) {
        diffs.push({ path: `${path}.${prop}`, kind: "PROP_MISSING_IN_GEN", detail: `Property exists in original but not generated` });
      } else if (gp && !op) {
        diffs.push({ path: `${path}.${prop}`, kind: "PROP_EXTRA_IN_GEN", detail: `Property exists in generated but not original` });
      } else if (gp && op) {
        compareSchemas(gp, op, origRoot, `${path}.${prop}`, depth + 1);
      }
    }
  }

  // Compare items (arrays)
  if (gen.items || orig.items) {
    const genItems = gen.items;
    const origItems = resolveDef(orig.items, origRoot);
    if (genItems && origItems) {
      compareSchemas(genItems, origItems, origRoot, `${path}[items]`, depth + 1);
    }
  }

  // Compare anyOf/oneOf
  for (const key of ["anyOf", "oneOf"]) {
    if (gen[key] || orig[key]) {
      const genVariants = gen[key]?.length ?? 0;
      const origVariants = orig[key]?.length ?? 0;
      if (genVariants !== origVariants) {
        diffs.push({
          path,
          kind: `${key.toUpperCase()}_COUNT_DIFF`,
          detail: `gen: ${genVariants} variants, orig: ${origVariants} variants`,
        });
      }
    }
  }
}

// ─── Run comparison ──────────────────────────────────────────────────────────

compareSchemas(generated, original, original, "$", 0);

// ─── Report ──────────────────────────────────────────────────────────────────

console.log(`\n${"=".repeat(80)}`);
console.log(`GVPP v3 Schema Comparison: Generated (Zod) vs Original (JSON Schema)`);
console.log(`${"=".repeat(80)}\n`);
console.log(`Generated: ${JSON.stringify(generated).length.toLocaleString()} bytes, no $defs (fully inlined)`);
console.log(`Original:  ${JSON.stringify(original).length.toLocaleString()} bytes, ${Object.keys(original.$defs ?? {}).length} $defs\n`);

// Group by kind
const byKind = new Map<string, Diff[]>();
for (const d of diffs) {
  const list = byKind.get(d.kind) ?? [];
  list.push(d);
  byKind.set(d.kind, list);
}

for (const [kind, items] of byKind) {
  console.log(`\n── ${kind} (${items.length}) ${"─".repeat(Math.max(0, 60 - kind.length))}`);
  for (const item of items.slice(0, 30)) {
    console.log(`  ${item.path}`);
    console.log(`    ${item.detail}`);
  }
  if (items.length > 30) {
    console.log(`  ... and ${items.length - 30} more`);
  }
}

console.log(`\n${"=".repeat(80)}`);
console.log(`TOTAL: ${diffs.length} differences found`);

// Summary by severity
const structural = diffs.filter(d => ["PROP_MISSING_IN_GEN", "PROP_EXTRA_IN_GEN", "MISSING_REQUIRED_GEN", "EXTRA_REQUIRED_GEN", "TYPE_MISMATCH"].includes(d.kind));
const constraints = diffs.filter(d => ["CONSTRAINT_DIFF", "PATTERN_DIFF", "ENUM_DIFF"].includes(d.kind));
const other = diffs.filter(d => !structural.includes(d) && !constraints.includes(d));

console.log(`  Structural (missing/extra props, type mismatches): ${structural.length}`);
console.log(`  Constraint (enum, pattern, min/max):               ${constraints.length}`);
console.log(`  Other:                                              ${other.length}`);
console.log(`${"=".repeat(80)}\n`);
