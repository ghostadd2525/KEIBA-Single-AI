/**
 * SingleSiteAdapter — Existing Site → Single AI (I1)
 *
 * Browser stays same-origin (/api/single/*).
 * BFF → Python /v1/site/* with X-AI-Key + timeout.
 * Does not change PredictionBundle contract or PredictionAdapter.
 */
import { aiFetch } from "../aiProxy.js";
import { getEnv, useAiProxy } from "../env.js";
import { normalizeRaceIdYear } from "../raceIdYear.js";

const DEFAULT_TIMEOUT_MS = 12000;

export function useSingleSite(env) {
  return Boolean(env && env.AI_BASE_URL && useAiProxy(env));
}

/**
 * @param {any} context
 * @param {{ race_id: string, core_payload: object, options?: object, force?: boolean, timeout_ms?: number }} body
 */
export async function callSiteSingle(context, body) {
  const env = getEnv(context);
  if (!useSingleSite(env)) {
    return {
      ok: false,
      status: 503,
      code: "AI_BASE_URL_MISSING",
      error: "AI_BASE_URL not configured for Single Site Integration",
    };
  }

  const raceId = normalizeRaceIdYear(String((body && body.race_id) || "").trim());
  if (!raceId) {
    return { ok: false, status: 400, code: "BAD_RACE_ID", error: "race_id required" };
  }
  if (!body || !body.core_payload || typeof body.core_payload !== "object") {
    return {
      ok: false,
      status: 400,
      code: "CORE_PAYLOAD_REQUIRED",
      error: "core_payload required until Core PROMOTE Gate",
    };
  }

  const timeoutMs =
    typeof body.timeout_ms === "number" && body.timeout_ms > 0
      ? body.timeout_ms
      : DEFAULT_TIMEOUT_MS;

  const payload = {
    race_id: raceId,
    core_payload: body.core_payload,
    options: body.options || {},
    force: Boolean(body.force),
    timeout_ms: timeoutMs,
  };

  const proxied = await aiFetch(context, `/v1/site/single/${encodeURIComponent(raceId)}`, {
    method: "POST",
    body: JSON.stringify(payload),
    timeoutMs,
    headers: {
      "X-Request-Timeout-Ms": String(timeoutMs),
    },
  });

  if (proxied instanceof Response) {
    let code = "AI_ERROR";
    let message = "Single Site Integration failed";
    let details = null;
    try {
      const body = await proxied.clone().json();
      code = (body && body.error && body.error.code) || code;
      message = (body && body.error && body.error.message) || message;
      details = body;
    } catch {
      /* ignore */
    }
    return {
      ok: false,
      status: proxied.status || 502,
      code,
      error: message,
      details,
      errorResponse: proxied,
    };
  }

  if (!proxied || proxied.ok === false) {
    return {
      ok: false,
      status: (proxied && proxied.status) || 502,
      code: (proxied && proxied.error && proxied.error.code) || "AI_ERROR",
      error:
        (proxied && proxied.error && proxied.error.message) ||
        "Single Site Integration failed",
      details: proxied,
    };
  }

  return {
    ok: true,
    payload: proxied.payload,
    source: "win5-ai-site",
    race_id: raceId,
  };
}

export async function siteHealth(context) {
  const env = getEnv(context);
  if (!useSingleSite(env)) {
    return { ok: false, status: 503, code: "AI_BASE_URL_MISSING", error: "AI unavailable" };
  }
  const proxied = await aiFetch(context, "/v1/site/health", { timeoutMs: 5000 });
  if (proxied instanceof Response) {
    return {
      ok: false,
      status: proxied.status || 502,
      code: "AI_ERROR",
      error: "site health failed",
      errorResponse: proxied,
    };
  }
  if (!proxied || proxied.ok === false) {
    return {
      ok: false,
      status: (proxied && proxied.status) || 502,
      code: (proxied && proxied.error && proxied.error.code) || "AI_ERROR",
      error: "site health failed",
    };
  }
  return { ok: true, payload: proxied.payload };
}

export async function siteVersion(context) {
  const env = getEnv(context);
  if (!useSingleSite(env)) {
    return { ok: false, status: 503, code: "AI_BASE_URL_MISSING", error: "AI unavailable" };
  }
  const proxied = await aiFetch(context, "/v1/site/version", { timeoutMs: 5000 });
  if (proxied instanceof Response) {
    return {
      ok: false,
      status: proxied.status || 502,
      code: "AI_ERROR",
      error: "site version failed",
      errorResponse: proxied,
    };
  }
  if (!proxied || proxied.ok === false) {
    return {
      ok: false,
      status: (proxied && proxied.status) || 502,
      code: (proxied && proxied.error && proxied.error.code) || "AI_ERROR",
      error: "site version failed",
    };
  }
  return { ok: true, payload: proxied.payload };
}

export const SingleSiteAdapter = {
  call: callSiteSingle,
  health: siteHealth,
  version: siteVersion,
};
