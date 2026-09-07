/**
 * GET /api/v1/challenge/monthly?month=YYYY-MM
 * AI benchmark vs user ledger (V7 / V9 Benchmark Layer)
 *
 * Feature flag V9_BENCHMARK_LAYER is enforced on AI service.
 * BFF mirrors the flag into meta for FE consumers.
 */
import { aiFetch } from "../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import { getBearer, verifyStubToken } from "../../../_lib/auth.js";

function flagOn(env) {
  // V9.0 Production Standard: default ON when unset (rollback: 0/false/no/off).
  const raw = env && env.V9_BENCHMARK_LAYER;
  if (raw === undefined || raw === null || String(raw).trim() === "") return true;
  const v = String(raw).trim().toLowerCase();
  if (v === "0" || v === "false" || v === "no" || v === "off") return false;
  return v === "1" || v === "true" || v === "yes" || v === "on";
}

export async function onRequestGet(context) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return jsonError("UNAUTHORIZED", "Bearer token required", 401);

  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("CHALLENGE_UNAVAILABLE", "challenge service unavailable", 502);
  }

  const url = new URL(context.request.url);
  const qs = url.search || "";
  const proxied = await aiFetch(context, "/v1/challenge/monthly" + qs, {
    headers: { Authorization: `Bearer ${token}` },
    timeoutMs: 25000,
  });
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    const data = proxied.payload.data || {};
    const meta = Object.assign({}, proxied.payload.meta || {}, {
      v9_benchmark_layer: !!(
        (data.feature_flags && data.feature_flags.v9_benchmark_layer) ||
        flagOn(env)
      ),
    });
    return jsonOk(data, meta);
  }
  return jsonError("CHALLENGE_UNAVAILABLE", "challenge service unavailable", 502);
}
