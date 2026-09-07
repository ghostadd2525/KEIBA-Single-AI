/**
 * POST /api/v1/notifications/:id/read
 */
import { aiFetch } from "../../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../../_lib/errors.js";
import { getBearer, verifyStubToken } from "../../../../_lib/auth.js";

export async function onRequestPost(context) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return jsonError("UNAUTHORIZED", "Bearer token required", 401);

  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("NOTIFICATIONS_UNAVAILABLE", "notifications unavailable", 502);
  }

  const id = context.params && context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "id required", 400);

  const proxied = await aiFetch(
    context,
    `/v1/notifications/${encodeURIComponent(id)}/read`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: "{}",
      timeoutMs: 15000,
    }
  );
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data || {}, proxied.payload.meta || {});
  }
  const status = (proxied && proxied.status) || 502;
  return jsonError(
    "NOTIFICATIONS_UNAVAILABLE",
    "notifications unavailable",
    status
  );
}
