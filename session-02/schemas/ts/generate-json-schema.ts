/**
 * generate-json-schema.ts — Export the Zod v4 GVPP schema as JSON Schema (draft 2020-12).
 *
 * Usage:  npx tsx generate-json-schema.ts > ../generated-v3.schema.json
 */

import { z } from "zod";
import { UnifiedVideoProjectPackageSchema } from "./gvpp-schema.js";

const jsonSchema = z.toJSONSchema(UnifiedVideoProjectPackageSchema, {
  unrepresentable: "any",
  io: "input",
});

// Add the $id and metadata to match the existing schema
const enriched = {
  $schema: jsonSchema.$schema,
  $id: "https://example.org/schemas/unified-video-project-v3.schema.json",
  title: "Unified Generative Video Project Package",
  description:
    "Tool-agnostic, Draft 2020-12 JSON Schema for autonomous generative-AI video production. " +
    "Generated from Zod v4 TypeScript source (gvpp-schema.ts). Schema version 3.0.0.",
  ...jsonSchema,
};

console.log(JSON.stringify(enriched, null, 2));
