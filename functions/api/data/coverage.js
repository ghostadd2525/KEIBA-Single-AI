/**
 * Coverage BFF — GET /api/data/coverage
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const date = url.searchParams.get("date") || url.searchParams.get("race_date") || "";
  const qs = date ? `?date=${encodeURIComponent(date)}` : "";
  const env = getEnv(context);

  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/data/coverage" + qs);
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, {
        ...(proxied.payload.meta || {}),
        provider: "python",
        service: "Coverage",
      });
    }
  }

  return jsonError("COVERAGE_UNAVAILABLE", "coverage unavailable", 502);
}
