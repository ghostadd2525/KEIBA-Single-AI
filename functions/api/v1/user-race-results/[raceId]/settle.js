/**
 * POST /api/v1/user-race-results/:raceId/settle
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
    return jsonError("USER_SERVICE_UNAVAILABLE", "user service unavailable", 502);
  }

  let body = {};
  try {
    body = await context.request.json();
  } catch {
    body = {};
  }

  const raceId = context.params.raceId;
  const proxied = await aiFetch(
    context,
    `/v1/user-race-results/${encodeURIComponent(raceId)}/settle`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body || {}),
    }
  );
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data, proxied.payload.meta || {});
  }
  return jsonError("SETTLE_UNAVAILABLE", "settle unavailable", 502);
}
