/**
 * Diagnostics BFF — GET /api/diagnostics/missing
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestGet(context) {
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("AI_BASE_URL_REQUIRED", "Set AI_BASE_URL to collect missing reports", 503);
  }
  const proxied = await aiFetch(context, "/v1/diagnostics/missing");
  if (proxied && proxied instanceof Response) return proxied;
  if (!proxied || !proxied.ok) {
    return jsonError("DIAGNOSTICS_UNAVAILABLE", "diagnostics failed", 502);
  }
  return jsonOk(proxied.payload.data, {
    ...(proxied.payload.meta || {}),
    provider: "python",
    service: "Diagnostics",
  });
}
