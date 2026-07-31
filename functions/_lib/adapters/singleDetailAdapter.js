/**
 * I3 — Detail-only Single AI adapter (BFF)
 * I4 — records resolve outcomes via singleDetailObservability (ops only).
 *
 * Flag ON path: try Single → UI1 Mapper → Bundle; else Prediction fallback.
 * Does not touch race list cache or list routes.
 */
import { aiFetch } from "../aiProxy.js";
import { getEnv, useAiProxy } from "../env.js";
import {
  PredictionAdapter,
  mergeGetProvenanceMeta,
} from "./predictionAdapter.js";
import { mapSingleToPredictionBundle } from "../singleToBundleMapper.js";
import { normalizeRaceIdYear } from "../raceIdYear.js";
import { recordSingleDetailEvent } from "../singleDetailObservability.js";

const DEFAULT_TIMEOUT_MS = 12000;

/**
 * @param {any} context
 * @param {string} raceId
 * @param {{ core_payload?: object, force?: boolean, timeout_ms?: number }} [opts]
 */
export async function resolveDetailBundle(context, raceId, opts = {}) {
  const t0 = Date.now();
  const id = normalizeRaceIdYear(String(raceId || "").trim());
  if (!id) {
    recordSingleDetailEvent({
      latency_ms: Date.now() - t0,
      detail_source: "error",
      fallback_reason: "BAD_RACE_ID",
      http_status: 400,
    });
    return { ok: false, status: 400, code: "BAD_RACE_ID", error: "race_id required" };
  }

  const timeoutMs =
    typeof opts.timeout_ms === "number" && opts.timeout_ms > 0
      ? opts.timeout_ms
      : DEFAULT_TIMEOUT_MS;

  // Always resolve Prediction first — fallback + base_bundle for Mapper
  const pred = await PredictionAdapter.get(context, id);
  if (pred.errorResponse) {
    recordSingleDetailEvent({
      latency_ms: Date.now() - t0,
      detail_source: "error",
      single_attempted: false,
      fallback_reason: "PREDICTION_ERROR_RESPONSE",
      http_status: 502,
    });
    return { ok: false, errorResponse: pred.errorResponse };
  }
  if (pred.pending || pred.code === "PREDICTION_PENDING") {
    recordSingleDetailEvent({
      latency_ms: Date.now() - t0,
      detail_source: "prediction_pending",
      fallback_reason: "PREDICTION_PENDING",
      http_status: 202,
    });
    return {
      ok: false,
      pending: true,
      status: 202,
      code: "PREDICTION_PENDING",
      error: pred.error || "Prediction pending",
      provenanceMeta: pred.provenanceMeta,
      source: pred.source,
      provider: pred.provider,
    };
  }
  if (!pred.ok || !pred.bundle) {
    recordSingleDetailEvent({
      latency_ms: Date.now() - t0,
      detail_source: "error",
      fallback_reason: "PREDICTION_NOT_FOUND",
      http_status: pred.status || 404,
    });
    return {
      ok: false,
      status: pred.status || 404,
      code: pred.status === 404 ? "NOT_FOUND" : "PREDICTION_ERROR",
      error: pred.error || "PredictionBundle not found",
    };
  }

  const baseMeta = mergeGetProvenanceMeta(
    {
      source: pred.source,
      service: "SingleDetailAdapter",
      provider: pred.provider,
      adapter: "SingleDetailAdapter",
      detail_flag_path: true,
    },
    pred.provenanceMeta || {}
  );

  const core = opts.core_payload && typeof opts.core_payload === "object" ? opts.core_payload : null;
  const env = getEnv(context);

  function done(result, obs) {
    recordSingleDetailEvent({
      latency_ms: Date.now() - t0,
      detail_source: obs.detail_source,
      single_attempted: !!obs.single_attempted,
      fallback_reason: obs.fallback_reason || null,
      http_status: obs.http_status != null ? obs.http_status : 200,
      timed_out: !!obs.timed_out,
    });
    return result;
  }

  // No core → Prediction fallback (Flag ON still safe; does not invent Core)
  if (!core) {
    return done(
      {
        ok: true,
        bundle: pred.bundle,
        source: pred.source,
        provider: pred.provider,
        provenanceMeta: {
          ...baseMeta,
          detail_source: "prediction_fallback",
          single_attempted: false,
          fallback_reason: "CORE_PAYLOAD_REQUIRED",
        },
      },
      {
        detail_source: "prediction_fallback",
        single_attempted: false,
        fallback_reason: "CORE_PAYLOAD_REQUIRED",
      }
    );
  }

  if (!useAiProxy(env)) {
    return done(
      {
        ok: true,
        bundle: pred.bundle,
        source: pred.source,
        provider: pred.provider,
        provenanceMeta: {
          ...baseMeta,
          detail_source: "prediction_fallback",
          single_attempted: false,
          fallback_reason: "AI_BASE_URL_MISSING",
        },
      },
      {
        detail_source: "prediction_fallback",
        single_attempted: false,
        fallback_reason: "AI_BASE_URL_MISSING",
      }
    );
  }

  // Prefer Python UI mapper with site single assembly
  const siteBody = {
    race_id: id,
    core_payload: core,
    force: Boolean(opts.force),
    timeout_ms: timeoutMs,
    options: opts.options || {},
  };

  const siteProxied = await aiFetch(context, `/v1/site/single/${encodeURIComponent(id)}`, {
    method: "POST",
    body: JSON.stringify(siteBody),
    timeoutMs,
    headers: { "X-Request-Timeout-Ms": String(timeoutMs) },
  });

  if (siteProxied instanceof Response || !siteProxied || siteProxied.ok === false) {
    let reason = "SINGLE_SITE_ERROR";
    let status = 502;
    if (siteProxied instanceof Response) {
      status = siteProxied.status || 502;
      try {
        const body = await siteProxied.clone().json();
        reason = (body && body.error && body.error.code) || reason;
      } catch {
        /* ignore */
      }
    } else if (siteProxied && siteProxied.error && siteProxied.error.code) {
      reason = siteProxied.error.code;
      status = siteProxied.status || 502;
    }
    if (reason === "AI_TIMEOUT" || reason === "TIMEOUT") {
      reason = "TIMEOUT";
    }
    return done(
      {
        ok: true,
        bundle: pred.bundle,
        source: pred.source,
        provider: pred.provider,
        provenanceMeta: {
          ...baseMeta,
          detail_source: "prediction_fallback",
          single_attempted: true,
          fallback_reason: reason,
        },
      },
      {
        detail_source: "prediction_fallback",
        single_attempted: true,
        fallback_reason: reason,
        http_status: status,
        timed_out: reason === "TIMEOUT",
      }
    );
  }

  const sitePayload = siteProxied.payload || {};
  if (sitePayload.ok === false) {
    const code = (sitePayload.error && sitePayload.error.code) || "SINGLE_ERROR";
    const reason = code === "AI_TIMEOUT" || code === "TIMEOUT" ? "TIMEOUT" : code;
    return done(
      {
        ok: true,
        bundle: pred.bundle,
        source: pred.source,
        provider: pred.provider,
        provenanceMeta: {
          ...baseMeta,
          detail_source: "prediction_fallback",
          single_attempted: true,
          fallback_reason: reason,
        },
      },
      {
        detail_source: "prediction_fallback",
        single_attempted: true,
        fallback_reason: reason,
        http_status: reason === "TIMEOUT" ? 504 : 503,
        timed_out: reason === "TIMEOUT",
      }
    );
  }

  const mapProxied = await aiFetch(context, "/v1/ui/prediction-bundle", {
    method: "POST",
    body: JSON.stringify({
      single_response: sitePayload.data || sitePayload,
      race_id: id,
      race_info: pred.bundle.race_info,
      base_bundle: pred.bundle,
    }),
    timeoutMs: Math.min(timeoutMs, 8000),
  });

  let bundle = null;
  if (!(mapProxied instanceof Response) && mapProxied && mapProxied.ok) {
    const mp = mapProxied.payload || {};
    bundle = mp.data != null ? mp.data : mp;
  }

  // Local mapper fallback if Python UI map unavailable
  if (!bundle || !bundle.schema_version) {
    try {
      bundle = mapSingleToPredictionBundle(sitePayload.data || sitePayload, {
        race_id: id,
        race_info: pred.bundle.race_info,
        base_bundle: pred.bundle,
      });
    } catch {
      bundle = null;
    }
  }

  if (!bundle || !bundle.schema_version) {
    return done(
      {
        ok: true,
        bundle: pred.bundle,
        source: pred.source,
        provider: pred.provider,
        provenanceMeta: {
          ...baseMeta,
          detail_source: "prediction_fallback",
          single_attempted: true,
          fallback_reason: "MAP_FAILED",
        },
      },
      {
        detail_source: "prediction_fallback",
        single_attempted: true,
        fallback_reason: "MAP_FAILED",
        http_status: 502,
      }
    );
  }

  return done(
    {
      ok: true,
      bundle,
      source: "single-ai-detail",
      provider: "single",
      provenanceMeta: {
        ...baseMeta,
        engine: baseMeta.engine || "real",
        engine_source: "single_detail",
        detail_source: "single",
        single_attempted: true,
        fallback_reason: null,
        service: "SingleDetailAdapter",
        adapter: "SingleDetailAdapter",
      },
    },
    {
      detail_source: "single",
      single_attempted: true,
      fallback_reason: null,
      http_status: 200,
    }
  );
}

export const SingleDetailAdapter = {
  resolve: resolveDetailBundle,
};
