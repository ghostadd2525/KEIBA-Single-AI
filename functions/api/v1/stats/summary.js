/**
 * STATS-1 — GET /api/v1/stats/summary
 */
import { aiFetch } from "../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const period = url.searchParams.get("period") || "overall";
  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, `/v1/stats/summary?period=${encodeURIComponent(period)}`);
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, proxied.payload.meta || {});
    }
  }
  return jsonError("STATS_UNAVAILABLE", "stats service unavailable", 502);
}
