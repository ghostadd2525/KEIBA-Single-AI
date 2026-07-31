/**
 * Single-AI · PredictionService
 * GET /api/predictions/:id → PredictionBundle
 *
 * 内部実装は PredictionAdapter（python → mock）。契約・パスは不変。
 * Phase7-08: meta.engine_source 等をフラットに返す。
 * Version7: 空 Projection は成功にせず PREDICTION_PENDING (202)。
 */
import {
  PredictionAdapter,
  mergeGetProvenanceMeta,
} from "../../_lib/adapters/predictionAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import {
  isReadyPredictionBundle,
  warnProjectionSuppressed,
} from "../../_lib/predictionReady.js";
import { applyBundleValidation } from "../../_lib/validateBundle.js";

function jsonPredictionPending(meta = {}, message = "Prediction pending") {
  const body = {
    ok: false,
    error: {
      code: "PREDICTION_PENDING",
      message,
      details: {
        race_id: meta.race_id || null,
        numeric_race_id: meta.numeric_race_id || null,
        reason: meta.reason || meta.fallback_reason || "pending",
      },
    },
    meta: {
      generated_at: new Date().toISOString(),
      prediction_status: "pending",
      source: meta.source || "pi-keibanet-api",
      service: "PredictionService",
      provider: meta.provider || "pi",
      adapter: "PredictionAdapter",
      ...meta,
    },
  };
  return new Response(JSON.stringify(body), {
    status: 202,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);

  const result = await PredictionAdapter.get(context, id);
  if (result.errorResponse) return result.errorResponse;

  if (result.pending || result.code === "PREDICTION_PENDING") {
    const meta = mergeGetProvenanceMeta(
      {
        source: result.source || "pi-keibanet-api",
        service: "PredictionService",
        provider: result.provider || "pi",
        adapter: "PredictionAdapter",
      },
      result.provenanceMeta || {}
    );
    return jsonPredictionPending(meta, result.error || "Prediction pending");
  }

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

  const mergedMeta = mergeGetProvenanceMeta(base, result.provenanceMeta || {});

  // 二重ガード: 空 Bundle / Projection は絶対に 200 成功にしない
  if (!isReadyPredictionBundle(result.bundle, mergedMeta)) {
    warnProjectionSuppressed({
      race_id: id,
      numeric_race_id: mergedMeta.numeric_race_id || null,
      reason: "handler_rejected_empty_or_projection",
    });
    return jsonPredictionPending(
      {
        ...mergedMeta,
        reason: "empty_or_projection_rejected",
      },
      "Prediction pending (empty or projection)"
    );
  }

  const checked = applyBundleValidation(context, result.bundle, mergedMeta);
  if (checked.errorResponse) return checked.errorResponse;
  return jsonOk(checked.data, checked.meta, { cacheControl: "public, max-age=120" });
}
