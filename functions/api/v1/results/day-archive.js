/**
 * GET /api/v1/results/day-archive?date=YYYY-MM-DD
 * Client cache purge signal after ResultAutomation archive (no PII).
 */
import { aiFetch } from "../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const date = url.searchParams.get("date") || url.searchParams.get("race_date") || "";
  if (!date) {
    return jsonError("BAD_REQUEST", "date required", 400);
  }
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("AI_UNAVAILABLE", "AI_BASE_URL not configured", 502);
  }
  const proxied = await aiFetch(
    context,
    `/v1/results/day-archive?date=${encodeURIComponent(date)}`
  );
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data, proxied.payload.meta || {});
  }
  const msg =
    (proxied && proxied.error && proxied.error.message) || "day-archive unavailable";
  return jsonError("ARCHIVE_UNAVAILABLE", msg, 502);
}
