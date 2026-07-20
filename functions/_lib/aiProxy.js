import { getEnv, useAiProxy } from "./env.js";
import { jsonError } from "./errors.js";

export async function aiFetch(context, path, init = {}) {
  const env = getEnv(context);
  if (!useAiProxy(env)) return null;

  const url = env.AI_BASE_URL + path;
  const headers = {
    accept: "application/json",
    ...(init.headers || {}),
  };
  if (env.AI_API_KEY) headers["X-AI-Key"] = env.AI_API_KEY;
  // Phase9-A: Cloudflare Access Service Token（未設定時は送らない＝ローカル互換）
  if (env.CF_ACCESS_CLIENT_ID && env.CF_ACCESS_CLIENT_SECRET) {
    headers["CF-Access-Client-Id"] = env.CF_ACCESS_CLIENT_ID;
    headers["CF-Access-Client-Secret"] = env.CF_ACCESS_CLIENT_SECRET;
  }
  if (init.body && !headers["content-type"]) {
    headers["content-type"] = "application/json; charset=utf-8";
  }

  let res;
  try {
    res = await fetch(url, { ...init, headers });
  } catch (e) {
    return jsonError("AI_UNAVAILABLE", "WIN5 AI service unreachable", 502, {
      message: String(e && e.message ? e.message : e),
    });
  }

  const text = await res.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    return jsonError("AI_BAD_RESPONSE", "WIN5 AI returned non-JSON", 502);
  }

  if (!res.ok) {
    return jsonError(
      (payload && payload.error && payload.error.code) || "AI_ERROR",
      (payload && payload.error && payload.error.message) || "WIN5 AI error",
      res.status >= 400 && res.status < 600 ? res.status : 502,
      payload
    );
  }

  return { ok: true, payload, source: "win5-ai" };
}

export async function loadAssetJson(context, assetPath) {
  const url = new URL(assetPath, context.request.url);
  const res = await context.env.ASSETS.fetch(url);
  if (!res.ok) return null;
  return res.json();
}
