import { aiFetch, loadAssetJson } from "../../_lib/aiProxy.js";
import { normalizePredictionBundle, projectConfidence } from "../../_lib/domain.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

/**
 * ConfidenceService — GET /api/confidence/:raceId
 * PredictionBundle.race_id をキーに、同 Bundle の ai_confidence を投影
 */
export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);

  const proxied = await aiFetch(context, `/v1/confidence/${encodeURIComponent(id)}`);
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    const data = proxied.payload.data != null ? proxied.payload.data : proxied.payload;
    return jsonOk(data, {
      source: "win5-ai",
      service: "ConfidenceService",
      race_id: id,
    }, { cacheControl: "public, max-age=120" });
  }

  let bundle = await loadAssetJson(context, `/data/mocks/bundle-${id}.json`);
  if (!bundle) {
    bundle = await loadAssetJson(context, "/data/mocks/bundle-20260719_hanshin_11.json");
  }
  if (!bundle) return jsonError("NOT_FOUND", "PredictionBundle not found for race_id", 404);

  const normalized = normalizePredictionBundle(bundle, id);
  const races = await loadAssetJson(context, "/data/mocks/races.json");
  const meta = ((races && races.races) || []).find((r) => r.race_id === id);
  if (meta && meta.ai_confidence != null) {
    normalized.ai_confidence = {
      ...(normalized.ai_confidence || {}),
      score: Number(meta.ai_confidence) / 100,
      status: "ok",
    };
  }

  return jsonOk(projectConfidence(normalized), {
    source: "mock",
    service: "ConfidenceService",
    race_id: id,
    contract_ref: "PredictionBundle.ai_confidence",
  }, { cacheControl: "public, max-age=120" });
}
