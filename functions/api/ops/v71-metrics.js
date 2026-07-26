/**
 * GET /api/ops/v71-metrics — Version7.3 Ops 指標（admin）
 * Prediction Engine / CE / AI ロジック非変更。集計のみ。
 * Version8.5.1: fail-closed admin。
 */
import { requireAccessSession, getBearer } from "../../_lib/auth.js";
import { isAdminUser } from "../../_lib/adminAuth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { piFetch } from "../../_lib/piProxy.js";
import { UserRepository } from "../../_lib/userRepository.js";

export async function onRequestGet(context) {
  const session = requireAccessSession(context);
  if (session instanceof Response) return session;

  let beta = {};
  try {
    beta = await getBetaConfig(context);
  } catch {
    beta = {};
  }

  await resolveAuthorization(context, beta);

  const profile = await UserRepository.get(context, session.id).catch(function () {
    return null;
  });
  if (!isAdminUser(beta, session, profile)) {
    return jsonError("FORBIDDEN", "ops v71 metrics requires admin", 403);
  }

  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("AI_UNAVAILABLE", "AI_BASE_URL not configured", 502);
  }

  const url = new URL(context.request.url);
  const date = url.searchParams.get("date") || url.searchParams.get("race_date") || "";
  const path = date
    ? `/v1/admin/ops/v71-metrics?date=${encodeURIComponent(date)}`
    : "/v1/admin/ops/v71-metrics";

  const [proxied, piCacheRaw] = await Promise.all([
    aiFetch(context, path),
    piFetch(context, "/v1/ops/cache-metrics").catch(function () {
      return null;
    }),
  ]);

  if (proxied && proxied instanceof Response) return proxied;
  if (!proxied || !proxied.ok) {
    const msg =
      (proxied && proxied.error && proxied.error.message) || "v71 metrics unavailable";
    return jsonError("V71_METRICS_UNAVAILABLE", msg, 502);
  }

  const data = { ...(proxied.payload.data || {}) };
  const piCache =
    piCacheRaw && !(piCacheRaw instanceof Response) && piCacheRaw.ok
      ? piCacheRaw
      : null;
  if (piCache && piCache.payload) {
    data.pi_cache = piCache.payload;
  }

  return jsonOk(data, {
    ...(proxied.payload.meta || {}),
    service: "OpsV73Metrics",
  });
}
