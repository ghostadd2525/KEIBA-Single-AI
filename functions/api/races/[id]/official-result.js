/**
 * GET /api/races/:id/official-result
 * Finish order + payouts from race_results (AI SQLite). No Prediction Engine.
 */
import { aiFetch } from "../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";

export async function onRequestGet(context) {
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("OFFICIAL_RESULT_UNAVAILABLE", "official result unavailable", 502);
  }
  const id = context.params.id;
  const proxied = await aiFetch(
    context,
    `/v1/races/${encodeURIComponent(id)}/official-result`
  );
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data, proxied.payload.meta || {});
  }
  if (proxied && proxied.status === 404) {
    return jsonError("NOT_FOUND", "official result not found", 404);
  }
  return jsonError("OFFICIAL_RESULT_UNAVAILABLE", "official result unavailable", 502);
}
