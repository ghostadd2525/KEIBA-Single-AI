/**
 * GET /api/v1/notifications
 */
import { aiFetch } from "../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import { getBearer, verifyStubToken } from "../../../_lib/auth.js";

export async function onRequestGet(context) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return jsonError("UNAUTHORIZED", "Bearer token required", 401);

  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("NOTIFICATIONS_UNAVAILABLE", "notifications unavailable", 502);
  }

  const url = new URL(context.request.url);
  const qs = url.search || "";
  const proxied = await aiFetch(context, "/v1/notifications" + qs, {
    headers: { Authorization: `Bearer ${token}` },
    timeoutMs: 15000,
  });
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data || {}, proxied.payload.meta || {});
  }
  return jsonError("NOTIFICATIONS_UNAVAILABLE", "notifications unavailable", 502);
}
