/**
 * I3 — GET/POST /api/single/detail/:raceId
 * Detail-only Bundle resolution (Single preferred when core_payload provided).
 * List routes / race list cache are never touched.
 */
import { SingleDetailAdapter } from "../../../_lib/adapters/singleDetailAdapter.js";
import { mergeGetProvenanceMeta } from "../../../_lib/adapters/predictionAdapter.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import {
  isReadyPredictionBundle,
  warnProjectionSuppressed,
} from "../../../_lib/predictionReady.js";
import { applyBundleValidation } from "../../../_lib/validateBundle.js";
import { normalizeRaceIdYear } from "../../../_lib/raceIdYear.js";

function jsonPredictionPending(meta = {}, message = "Prediction pending") {
  return new Response(
    JSON.stringify({
      ok: false,
      error: {
        code: "PREDICTION_PENDING",
        message,
        details: {
          race_id: meta.race_id || null,
          reason: meta.reason || meta.fallback_reason || "pending",
        },
      },
      meta: {
        generated_at: new Date().toISOString(),
        prediction_status: "pending",
        service: "SingleDetailAdapter",
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

async function respondBundle(context, result, raceId) {
  if (result.errorResponse) return result.errorResponse;
  if (result.pending || result.code === "PREDICTION_PENDING") {
    return jsonPredictionPending(
      mergeGetProvenanceMeta(
        { service: "SingleDetailAdapter", adapter: "SingleDetailAdapter" },
        result.provenanceMeta || {}
      ),
      result.error || "Prediction pending"
    );
  }
  if (!result.ok) {
    return jsonError(
      result.code || "NOT_FOUND",
      result.error || "Bundle not found",
      result.status || 404
    );
  }

  const meta = mergeGetProvenanceMeta(
    {
      source: result.source,
      service: "SingleDetailAdapter",
      provider: result.provider,
      adapter: "SingleDetailAdapter",
    },
    result.provenanceMeta || {}
  );

  if (!isReadyPredictionBundle(result.bundle, meta)) {
    warnProjectionSuppressed({
      race_id: raceId,
      reason: "single_detail_not_ready",
    });
    return jsonPredictionPending({ ...meta, reason: "not_ready" }, "Prediction pending");
  }

  const checked = applyBundleValidation(context, result.bundle, meta);
  if (checked.errorResponse) return checked.errorResponse;
  return jsonOk(checked.data, checked.meta, { cacheControl: "no-store" });
}

export async function onRequestGet(context) {
  const raceId = normalizeRaceIdYear(String(context.params.raceId || "").trim());
  if (!raceId) return jsonError("BAD_RACE_ID", "race_id required", 400);
  // GET: no core → Prediction fallback path (safe detail Flag ON)
  const result = await SingleDetailAdapter.resolve(context, raceId, {});
  return respondBundle(context, result, raceId);
}

export async function onRequestPost(context) {
  const raceId = normalizeRaceIdYear(String(context.params.raceId || "").trim());
  if (!raceId) return jsonError("BAD_RACE_ID", "race_id required", 400);

  let body = {};
  try {
    const text = await context.request.text();
    body = text ? JSON.parse(text) : {};
  } catch {
    return jsonError("BAD_REQUEST", "JSON body required", 400);
  }
  if (!body || typeof body !== "object") body = {};

  const result = await SingleDetailAdapter.resolve(context, raceId, {
    core_payload: body.core_payload,
    force: body.force,
    timeout_ms: body.timeout_ms,
    options: body.options,
  });
  return respondBundle(context, result, raceId);
}
