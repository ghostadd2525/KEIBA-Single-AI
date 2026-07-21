/**
 * fixtures + 代表 mock を Schema で検証
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { validateDef, validateWithSchema } from "../contracts/lib/schema-validate.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readJson(rel) {
  return JSON.parse(readFileSync(join(root, rel), "utf8"));
}

const pbSchema = readJson("contracts/single-prediction-bundle/2.0/schema.json");
const analysisSchema = readJson("contracts/expect-analysis/1.0/schema.json");
const authSchema = readJson("contracts/expect-auth/1.0/schema.json");
const kaobaSchema = readJson("contracts/expect-kaoba/1.0/schema.json");

const jobs = [
  ["fixtures/prediction-bundle/valid-hanshin-11.json", () => validateWithSchema(pbSchema, readJson("fixtures/prediction-bundle/valid-hanshin-11.json"))],
  ["public/data/mocks/bundle-20260719_hanshin_11.json", () => validateWithSchema(pbSchema, readJson("public/data/mocks/bundle-20260719_hanshin_11.json"))],
  ["public/data/sample_prediction_bundle.json", () => validateWithSchema(pbSchema, readJson("public/data/sample_prediction_bundle.json"))],
  ["fixtures/analysis/valid-hanshin-11.json", () => validateWithSchema(analysisSchema, readJson("fixtures/analysis/valid-hanshin-11.json"))],
  ["fixtures/auth/login-response.json", () => validateDef(authSchema, "AuthLoginResponse", readJson("fixtures/auth/login-response.json"))],
  ["fixtures/auth/me-response.json", () => validateDef(authSchema, "AuthMeResponse", readJson("fixtures/auth/me-response.json"))],
  ["fixtures/auth/logout-response.json", () => validateDef(authSchema, "AuthLogoutResponse", readJson("fixtures/auth/logout-response.json"))],
  ["fixtures/auth/favorites-state.json", () => validateDef(authSchema, "FavoritesState", readJson("fixtures/auth/favorites-state.json"))],
  ["fixtures/kaoba/chat-request.json", () => validateDef(kaobaSchema, "KaobaChatRequest", readJson("fixtures/kaoba/chat-request.json"))],
  ["fixtures/kaoba/chat-response.json", () => validateDef(kaobaSchema, "KaobaChatResponse", readJson("fixtures/kaoba/chat-response.json"))],
  ["fixtures/kaoba/chat-response-no-race.json", () => validateDef(kaobaSchema, "KaobaChatResponse", readJson("fixtures/kaoba/chat-response-no-race.json"))],
];

let failed = 0;
for (const [rel, run] of jobs) {
  const r = run();
  if (r.ok) {
    console.log("OK  ", rel);
  } else {
    failed += 1;
    console.error("FAIL", rel);
    r.errors.slice(0, 20).forEach((e) => console.error(" ", e));
  }
}

process.exit(failed ? 1 : 0);
