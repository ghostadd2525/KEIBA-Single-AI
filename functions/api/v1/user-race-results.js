/**
 * User race results BFF — GET/POST /api/v1/user-race-results
 * Monthly ledger (GET ?month=YYYY-MM) / strategy snapshot upsert (POST)
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { getBearer, verifyStubToken } from "../../_lib/auth.js";

function unauthorized() {
  return jsonError("UNAUTHORIZED", "Bearer token required", 401);
}

async function proxy(context, method, body, pathSuffix) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return unauthorized();

  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("USER_SERVICE_UNAVAILABLE", "user service unavailable", 502);
  }

  const url = new URL(context.request.url);
  const qs = url.search || "";
  const path = "/v1/user-race-results" + (pathSuffix || "") + qs;

  const proxied = await aiFetch(context, path, {
    method,
    headers: { Authorization: `Bearer ${token}` },
    body: body != null ? JSON.stringify(body) : undefined,
  });
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data, proxied.payload.meta || {});
  }
  return jsonError("USER_RACE_RESULTS_UNAVAILABLE", "user race results unavailable", 502);
}

export async function onRequestGet(context) {
  return proxy(context, "GET");
}

export async function onRequestPost(context) {
  let body = {};
  try {
    body = await context.request.json();
  } catch {
    body = {};
  }
  return proxy(context, "POST", body);
}
