/**
 * BFF jsonOk 相当のエンベロープを組み立て（Workers なしでスナップショット）
 */
import { validateDef, validateWithSchema } from "../../contracts/lib/schema-validate.mjs";

const GENERATED_AT = "2026-07-20T00:00:00.000Z";

export function jsonOkEnvelope(data, meta = {}) {
  return {
    ok: true,
    meta: {
      generated_at: GENERATED_AT,
      source: meta.source || "mock",
      cache: meta.cache || "miss",
      ...meta,
    },
    data,
  };
}

/** Phase7-08: BFF mock 経路の provenance（live PredictionAdapter と同等） */
export function predictionGetEnvelope(bundle, schemas) {
  const validation = validateWithSchema(schemas.predictionBundle, bundle);
  return jsonOkEnvelope(bundle, {
    source: "mock",
    service: "PredictionService",
    provider: "mock",
    adapter: "PredictionAdapter",
    engine: "n/a",
    engine_source: "bff_mock",
    model_version: bundle.model_version ?? null,
    inference_generated_at: bundle.generated_at ?? null,
    race_id: bundle.race_id,
    contract: "PredictionBundle",
    schema_version: "single-prediction-bundle/2.0",
    contract_validated: true,
    contract_ok: validation.ok,
    ...(validation.ok ? {} : { contract_errors: validation.errors.slice(0, 40) }),
  });
}

export function predictionListEnvelope(bundles, schemas) {
  const results = bundles.map((b) => validateWithSchema(schemas.predictionBundle, b));
  const ok = results.every((r) => r.ok);
  const errors = [];
  results.forEach((r, i) => {
    r.errors.forEach((e) => errors.push(`[${i} ${bundles[i].race_id || "?"}] ${e}`));
  });
  return jsonOkEnvelope(bundles, {
    source: "mock",
    service: "PredictionService",
    provider: "mock",
    adapter: "PredictionAdapter",
    engine: "n/a",
    items: bundles.map((b) => ({
      race_id: b.race_id,
      engine_source: "bff_mock",
      model_version: b.model_version ?? null,
      inference_generated_at: b.generated_at ?? null,
    })),
    contract: "PredictionBundle",
    schema_version: "single-prediction-bundle/2.0",
    contract_validated: true,
    contract_ok: ok,
    ...(ok ? {} : { contract_errors: errors.slice(0, 40) }),
  });
}

export function analysisGetEnvelope(analysis, schemas) {
  const validation = validateWithSchema(schemas.analysis, analysis);
  return jsonOkEnvelope(analysis, {
    source: "mock",
    service: "AnalysisService",
    contract: "Analysis",
    contract_ref: "PredictionBundle.race_id",
    schema_version: "expect-analysis/1.0",
    contract_validated: true,
    contract_ok: validation.ok,
    race_id: analysis.race_id,
    ...(validation.ok ? {} : { contract_errors: validation.errors.slice(0, 40) }),
  });
}

export function authLoginEnvelope(login, schemas) {
  const validation = validateDef(schemas.auth, "AuthLoginResponse", login);
  return jsonOkEnvelope(login, {
    source: "stub-auth",
    service: "AuthService",
    contract: "AuthLoginResponse",
    cache: "bypass",
    contract_validated: true,
    contract_ok: validation.ok,
  });
}

export function authMeEnvelope(me, schemas) {
  const validation = validateDef(schemas.auth, "AuthMeResponse", me);
  return jsonOkEnvelope(me, {
    source: "stub-auth",
    service: "AuthService",
    contract: "AuthMeResponse",
    cache: "bypass",
    contract_validated: true,
    contract_ok: validation.ok,
  });
}

export function authLogoutEnvelope(logout, schemas) {
  const validation = validateDef(schemas.auth, "AuthLogoutResponse", logout);
  return jsonOkEnvelope(logout, {
    source: "stub-auth",
    service: "AuthService",
    contract: "AuthLogoutResponse",
    cache: "bypass",
    contract_validated: true,
    contract_ok: validation.ok,
  });
}

export function kaobaChatEnvelope(response, schemas, raceId) {
  const validation = validateDef(schemas.kaoba, "KaobaChatResponse", response);
  return jsonOkEnvelope(response, {
    source: "mock",
    service: "KaobaService",
    contract: "KaobaChatResponse",
    race_id: raceId || response.referenced_race_id || null,
    contract_ref: raceId ? "PredictionBundle.race_id" : null,
    cache: "bypass",
    provider: response.provider || "rule",
    contract_validated: true,
    contract_ok: validation.ok,
  });
}

export function stableStringify(obj) {
  return JSON.stringify(obj, null, 2) + "\n";
}
