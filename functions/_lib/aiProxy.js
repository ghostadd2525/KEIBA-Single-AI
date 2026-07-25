import { getEnv, useAiProxy } from "./env.js";
import { jsonError } from "./errors.js";

const AI_FETCH_TIMEOUT_MS = 12000;

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

  const timeoutMs =
    typeof init.timeoutMs === "number" && init.timeoutMs > 0
      ? init.timeoutMs
      : AI_FETCH_TIMEOUT_MS;
  const { timeoutMs: _omit, signal: userSignal, ...fetchInit } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  if (userSignal) {
    if (userSignal.aborted) controller.abort();
    else
      userSignal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
  }

  let res;
  let text;
  try {
    res = await fetch(url, { ...fetchInit, headers, signal: controller.signal });
    // ヘッダ到着後の body 停滞も同一 AbortSignal で打ち切る
    text = await res.text();
  } catch (e) {
    const aborted = e && (e.name === "AbortError" || controller.signal.aborted);
    return jsonError(
      aborted ? "AI_TIMEOUT" : "AI_UNAVAILABLE",
      aborted ? "WIN5 AI service timeout" : "WIN5 AI service unreachable",
      502,
      {
        message: String(e && e.message ? e.message : e),
        timeout_ms: timeoutMs,
      }
    );
  } finally {
    clearTimeout(timer);
  }

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
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  // Pages may SPA-fallback missing assets to index.html (200) — treat as miss
  if (ct.includes("text/html")) return null;
  try {
    return await res.json();
  } catch {
    return null;
  }
}
