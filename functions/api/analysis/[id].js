/**
 * AnalysisService — GET /api/analysis/:raceId
 *
 * 内部実装は AnalysisAdapter（python → mock）。契約・パスは不変。
 * キー = PredictionBundle.race_id
 */
import { AnalysisAdapter } from "../../_lib/adapters/analysisAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);

  const result = await AnalysisAdapter.get(context, id);
  if (result.errorResponse) return result.errorResponse;
  if (!result.ok) {
    return jsonError("MOCK_MISSING", result.error || "analysis unavailable", result.status || 500);
  }

  return jsonOk(result.analysis, {
    source: result.source,
    service: "AnalysisService",
    race_id: id,
    contract: "Analysis",
    contract_ref: "PredictionBundle.race_id",
    provider: result.provider,
    adapter: "AnalysisAdapter",
  }, {
    cacheControl: "public, max-age=120",
  });
}
