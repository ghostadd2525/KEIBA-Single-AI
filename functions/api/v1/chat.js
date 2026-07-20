/**
 * User chat BFF — GET /api/v1/chat
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { getBearer, verifyStubToken } from "../../_lib/auth.js";

export async function onRequestGet(context) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return jsonError("UNAUTHORIZED", "Bearer token required", 401);

  const url = new URL(context.request.url);
  const qs = url.search || "";
  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/chat" + qs, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, proxied.payload.meta || {});
    }
  }
  return jsonError("CHAT_UNAVAILABLE", "chat unavailable", 502);
}
