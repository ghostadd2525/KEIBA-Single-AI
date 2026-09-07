/**
 * Single-AI · PredictionService
 * GET /api/predictions → PredictionBundle[]
 *
 * 内部実装は PredictionAdapter（python → mock）。契約・パスは不変。
 * Phase7-08: meta.items に race_id ごとの provenance。
 * Version7: 空 Projection 混入を拒否。全滅時は PREDICTION_PENDING。
 */
import {
  PredictionAdapter,
  mergeListProvenanceMeta,
} from "../../_lib/adapters/predictionAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { isReadyPredictionBundle } from "../../_lib/predictionReady.js";
import { applyBundleValidation } from "../../_lib/validateBundle.js";

function respondBundles(context, items, meta) {
  const checked = applyBundleValidation(context, items, meta);
  if (checked.errorResponse) return checked.errorResponse;
  return jsonOk(checked.data, checked.meta);
}

function jsonListPending(meta = {}, message = "Prediction list pending") {
  return new Response(
    JSON.stringify({
      ok: false,
      error: {
        code: "PREDICTION_PENDING",
        message,
        details: { reason: meta.reason || "pending" },
      },
      meta: {
        generated_at: new Date().toISOString(),
        prediction_status: "pending",
        service: "PredictionService",
        adapter: "PredictionAdapter",
        ...meta,
      },
    }),
    {
      status: 202,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
      },
    }
  );
}

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const date = url.searchParams.get("date") || "";
  const venue = url.searchParams.get("venue") || "";

  const result = await PredictionAdapter.list(context, { date, venue });
  if (result.errorResponse) return result.errorResponse;

  if (result.pending || result.code === "PREDICTION_PENDING") {
    return jsonListPending(
      mergeListProvenanceMeta(
        {
          source: result.source || "pi-keibanet-api",
          provider: result.provider || "pi",
        },
        result.provenanceMeta || {}
      ),
      result.error || "Prediction list pending"
    );
  }

  if (!result.ok) {
    return jsonError(
      "MOCK_MISSING",
      result.error || "predictions unavailable",
      result.status || 500
    );
  }

  const base = {
    source: result.source,
    service: "PredictionService",
    provider: result.provider,
    adapter: "PredictionAdapter",
  };
  const merged = mergeListProvenanceMeta(base, result.provenanceMeta || {});
  const itemsMeta = Array.isArray(merged.items) ? merged.items : [];
  const readyBundles = (result.bundles || []).filter(function (b) {
    const item =
      itemsMeta.find(function (it) {
        return it && b && String(it.race_id) === String(b.race_id);
      }) || {};
    return isReadyPredictionBundle(b, Object.assign({}, merged, item));
  });

  if (!readyBundles.length) {
    return jsonListPending(
      Object.assign({}, merged, { reason: "no_ready_prediction_bundles" }),
      "Prediction list pending"
    );
  }

  const readyIds = new Set(
    readyBundles.map(function (b) {
      return String(b.race_id);
    })
  );
  const readyMeta = Object.assign({}, merged, {
    items: itemsMeta.filter(function (it) {
      return it && readyIds.has(String(it.race_id));
    }),
  });

  return respondBundles(context, readyBundles, readyMeta);
}
