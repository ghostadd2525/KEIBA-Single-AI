/**
 * Single-AI · PredictionService
 * GET /api/predictions → PredictionBundle[]
 *
 * 内部実装は PredictionAdapter（python → mock）。契約・パスは不変。
 * Phase7-08: meta.items に race_id ごとの provenance。
 */
import {
  PredictionAdapter,
  mergeListProvenanceMeta,
} from "../../_lib/adapters/predictionAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { applyBundleValidation } from "../../_lib/validateBundle.js";

function respondBundles(context, items, meta) {
  const checked = applyBundleValidation(context, items, meta);
  if (checked.errorResponse) return checked.errorResponse;
  return jsonOk(checked.data, checked.meta);
}

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const date = url.searchParams.get("date") || "";
  const venue = url.searchParams.get("venue") || "";

  const result = await PredictionAdapter.list(context, { date, venue });
  if (result.errorResponse) return result.errorResponse;
  if (!result.ok) {
    return jsonError("MOCK_MISSING", result.error || "predictions unavailable", result.status || 500);
  }

  const base = {
    source: result.source,
    service: "PredictionService",
    provider: result.provider,
    adapter: "PredictionAdapter",
  };

  return respondBundles(
    context,
    result.bundles,
    mergeListProvenanceMeta(base, result.provenanceMeta || {})
  );
}
