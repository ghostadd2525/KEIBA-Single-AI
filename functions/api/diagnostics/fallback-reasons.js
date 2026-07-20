/**
 * Diagnostics BFF — GET /api/diagnostics/fallback-reasons
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestGet(context) {
  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/diagnostics/fallback-reasons");
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, {
        ...(proxied.payload.meta || {}),
        provider: "python",
        service: "Diagnostics",
      });
    }
  }

  return jsonError("DIAGNOSTICS_UNAVAILABLE", "fallback reasons unavailable", 502);
}
