import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { validateDef, validateWithSchema } from "../../contracts/lib/schema-validate.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const ROOT = join(__dirname, "../..");

export function readJson(rel) {
  return JSON.parse(readFileSync(join(ROOT, rel), "utf8"));
}

export function loadSchemas() {
  return {
    predictionBundle: readJson("contracts/single-prediction-bundle/2.0/schema.json"),
    analysis: readJson("contracts/expect-analysis/1.0/schema.json"),
    auth: readJson("contracts/expect-auth/1.0/schema.json"),
    kaoba: readJson("contracts/expect-kaoba/1.0/schema.json"),
  };
}

export function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

export { validateDef, validateWithSchema };
