/**
 * Single-AI · PredictionService
 * GET /api/predictions/:id → PredictionBundle
 *
 * 内部実装は PredictionAdapter（python → mock）。契約・パスは不変。
 * Phase7-08: meta.engine_source 等をフラットに返す。
 */
import {
  PredictionAdapter,
  mergeGetProvenanceMeta,
} from "../../_lib/adapters/predictionAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { applyBundleValidation } from "../../_lib/validateBundle.js";

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);

  const result = await PredictionAdapter.get(context, id);
  if (result.errorResponse) return result.errorResponse;
  if (!result.ok) {
    return jsonError(
      result.status === 404 ? "NOT_FOUND" : "MOCK_MISSING",
      result.error || "PredictionBundle not found",
      result.status || 500
    );
  }

  const base = {
    source: result.source,
    service: "PredictionService",
    provider: result.provider,
    adapter: "PredictionAdapter",
  };

  const checked = applyBundleValidation(
    context,
    result.bundle,
    mergeGetProvenanceMeta(base, result.provenanceMeta || {})
  );
  if (checked.errorResponse) return checked.errorResponse;
  return jsonOk(checked.data, checked.meta, { cacheControl: "public, max-age=120" });
}
