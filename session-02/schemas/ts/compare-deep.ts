/**
 * compare-deep.ts — Smarter comparison that handles $ref/$defs/allOf in original.
 *
 * Usage: npx tsx compare-deep.ts
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

// ─── $ref resolver with allOf merging ─────────────────────────────────────────

function resolve(schema: any, root: any): any {
  if (!schema || typeof schema !== "object") return schema;

  if (schema.$ref) {
    const refPath = schema.$ref.replace("#/", "").split("/");
    let resolved = root;
    for (const seg of refPath) resolved = resolved?.[seg];
    return resolve(resolved, root);
  }

  if (schema.allOf) {
    // Merge all allOf branches
    let merged: any = {};
    for (const branch of schema.allOf) {
      const resolved = resolve(branch, root);
      if (resolved.properties) {
        merged.properties = { ...merged.properties, ...resolved.properties };
      }
      if (resolved.required) {
        merged.required = [...(merged.required ?? []), ...resolved.required];
      }
      if (resolved.additionalProperties !== undefined) {
        merged.additionalProperties = resolved.additionalProperties;
      }
      if (resolved.type) merged.type = resolved.type;
      // Copy other keys
      for (const k of Object.keys(resolved)) {
        if (!["properties", "required", "additionalProperties", "type", "allOf", "$ref"].includes(k)) {
          merged[k] = resolved[k];
        }
      }
    }
    return merged;
  }

  return schema;
}

interface Diff {
  path: string;
  severity: "error" | "warning" | "info";
  kind: string;
  detail: string;
}

const diffs: Diff[] = [];

function compare(gen: any, origRaw: any, root: any, path: string, depth: number = 0): void {
  if (depth > 20) return;

  const orig = resolve(origRaw, root);
  if (!gen && !orig) return;

  if (!gen && orig) {
    diffs.push({ path, severity: "error", kind: "MISSING_IN_GENERATED", detail: "Exists in original only" });
    return;
  }
  if (gen && !orig) {
    diffs.push({ path, severity: "error", kind: "MISSING_IN_ORIGINAL", detail: "Exists in generated only" });
    return;
  }

  // ── Type ────────────────────────────────────────────────────────────────
  const genType = gen.type;
  const origType = orig.type;
  if (genType && origType && genType !== origType) {
    diffs.push({ path, severity: "error", kind: "TYPE_MISMATCH", detail: `gen: ${genType}, orig: ${origType}` });
  }

  // ── Properties ──────────────────────────────────────────────────────────
  if (gen.properties || orig.properties) {
    const genProps = new Set(Object.keys(gen.properties ?? {}));
    const origProps = new Set(Object.keys(orig.properties ?? {}));

    for (const p of genProps) {
      if (!origProps.has(p)) {
        diffs.push({ path: `${path}.${p}`, severity: "warning", kind: "PROP_EXTRA_IN_GEN", detail: "Property in generated but not original" });
      }
    }
    for (const p of origProps) {
      if (!genProps.has(p)) {
        diffs.push({ path: `${path}.${p}`, severity: "error", kind: "PROP_MISSING_IN_GEN", detail: "Property in original but not generated" });
      }
    }

    // Recurse into shared properties
    for (const p of genProps) {
      if (origProps.has(p)) {
        compare(gen.properties[p], orig.properties[p], root, `${path}.${p}`, depth + 1);
      }
    }
  }

  // ── Required ────────────────────────────────────────────────────────────
  const genReq = new Set<string>(gen.required ?? []);
  const origReq = new Set<string>(orig.required ?? []);
  for (const r of genReq) {
    if (!origReq.has(r)) {
      diffs.push({ path, severity: "warning", kind: "EXTRA_REQUIRED_GEN", detail: `"${r}" required in gen only` });
    }
  }
  for (const r of origReq) {
    if (!genReq.has(r)) {
      diffs.push({ path, severity: "error", kind: "MISSING_REQUIRED_GEN", detail: `"${r}" required in orig only` });
    }
  }

  // ── Enum ────────────────────────────────────────────────────────────────
  if (orig.enum && !gen.enum) {
    diffs.push({
      path,
      severity: "warning",
      kind: "ENUM_MISSING_IN_GEN",
      detail: `Original constrains to enum ${JSON.stringify(orig.enum)}, generated is open string`,
    });
  } else if (gen.enum && orig.enum) {
    const gSet = new Set(gen.enum);
    const oSet = new Set(orig.enum);
    const extra = gen.enum.filter((v: any) => !oSet.has(v));
    const missing = orig.enum.filter((v: any) => !gSet.has(v));
    if (extra.length || missing.length) {
      diffs.push({
        path,
        severity: "warning",
        kind: "ENUM_VALUES_DIFF",
        detail: `extra in gen: [${extra}], missing in gen: [${missing}]`,
      });
    }
  }

  // ── Numeric constraints ─────────────────────────────────────────────────
  for (const k of ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "minItems", "maxItems"]) {
    if (orig[k] !== undefined && gen[k] === undefined) {
      diffs.push({ path, severity: "warning", kind: "CONSTRAINT_MISSING_GEN", detail: `${k}=${orig[k]} in original, absent in generated` });
    } else if (gen[k] !== undefined && orig[k] !== undefined && gen[k] !== orig[k]) {
      diffs.push({ path, severity: "warning", kind: "CONSTRAINT_DIFF", detail: `${k}: gen=${gen[k]}, orig=${orig[k]}` });
    }
  }

  // ── additionalProperties ────────────────────────────────────────────────
  const genAP = gen.additionalProperties;
  const origAP = orig.additionalProperties;
  if (genAP !== undefined && origAP !== undefined) {
    const genIsOpen = genAP === true || (typeof genAP === "object" && Object.keys(genAP).length === 0);
    const origIsOpen = origAP === true || (typeof origAP === "object" && Object.keys(origAP).length === 0);
    if (!genIsOpen && !origIsOpen && JSON.stringify(genAP) !== JSON.stringify(origAP)) {
      diffs.push({ path, severity: "info", kind: "ADDITIONAL_PROPS_DIFF", detail: `gen: ${JSON.stringify(genAP)}, orig: ${JSON.stringify(origAP)}` });
    }
    // Special case: budget.breakdown has additionalProperties: {"type":"number"} in original
    if (typeof origAP === "object" && origAP.type && genIsOpen) {
      diffs.push({ path, severity: "warning", kind: "ADDITIONAL_PROPS_TYPE_LOST", detail: `Original restricts additionalProperties to type="${origAP.type}", generated allows any` });
    }
  }

  // ── Items (arrays) ──────────────────────────────────────────────────────
  if (gen.items || orig.items) {
    compare(gen.items, orig.items, root, `${path}[items]`, depth + 1);
  }

  // ── oneOf / anyOf ──────────────────────────────────────────────────────
  for (const key of ["oneOf", "anyOf"] as const) {
    if (gen[key] && orig[key]) {
      const genLen = gen[key].length;
      const origLen = orig[key].length;
      if (genLen !== origLen) {
        diffs.push({ path, severity: "warning", kind: `${key.toUpperCase()}_COUNT_DIFF`, detail: `gen: ${genLen}, orig: ${origLen}` });
      }
    } else if (!gen[key] && orig[key]) {
      diffs.push({ path, severity: "info", kind: `${key.toUpperCase()}_MISSING_GEN`, detail: `Original has ${key} with ${orig[key].length} branches` });
    }
  }
}

// ─── Run ──────────────────────────────────────────────────────────────────────

compare(generated, original, original, "$", 0);

// ─── Report ───────────────────────────────────────────────────────────────────

console.log(`\n${"═".repeat(80)}`);
console.log(`  GVPP v3 Schema Comparison (with $ref/allOf resolution)`);
console.log(`${"═".repeat(80)}\n`);

const errors = diffs.filter(d => d.severity === "error");
const warnings = diffs.filter(d => d.severity === "warning");
const infos = diffs.filter(d => d.severity === "info");

function printGroup(title: string, items: Diff[]) {
  if (items.length === 0) return;
  const byKind = new Map<string, Diff[]>();
  for (const d of items) {
    const list = byKind.get(d.kind) ?? [];
    list.push(d);
    byKind.set(d.kind, list);
  }
  console.log(`\n┌─ ${title} (${items.length}) ${"─".repeat(Math.max(0, 65 - title.length))}`);
  for (const [kind, kindItems] of byKind) {
    console.log(`│`);
    console.log(`│  ${kind} (${kindItems.length}):`);
    for (const item of kindItems.slice(0, 20)) {
      console.log(`│    ${item.path}`);
      console.log(`│      → ${item.detail}`);
    }
    if (kindItems.length > 20) {
      console.log(`│    ... and ${kindItems.length - 20} more`);
    }
  }
  console.log(`└${"─".repeat(79)}`);
}

printGroup("ERRORS — structural mismatches", errors);
printGroup("WARNINGS — looser constraints in generated", warnings);
printGroup("INFO — cosmetic / encoding differences", infos);

console.log(`\n${"═".repeat(80)}`);
console.log(`  SUMMARY`);
console.log(`${"═".repeat(80)}`);
console.log(`  Errors:   ${errors.length}`);
console.log(`  Warnings: ${warnings.length}`);
console.log(`  Info:     ${infos.length}`);
console.log(`  Total:    ${diffs.length}`);
console.log(`${"═".repeat(80)}\n`);
