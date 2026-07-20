/**
 * User Service BFF — GET/PATCH /api/users/me
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { getBearer, verifyStubToken } from "../../_lib/auth.js";

function unauthorized() {
  return jsonError("UNAUTHORIZED", "Bearer token required", 401);
}

export async function onRequestGet(context) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return unauthorized();

  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, proxied.payload.meta || {});
    }
  }

  return jsonError("USER_SERVICE_UNAVAILABLE", "user service unavailable", 502);
}

export async function onRequestPatch(context) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return unauthorized();

  let body = {};
  try {
    body = await context.request.json();
  } catch {
    body = {};
  }

  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/users/me", {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body || {}),
    });
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, proxied.payload.meta || {});
    }
  }

  return jsonError("USER_SERVICE_UNAVAILABLE", "user service unavailable", 502);
}
