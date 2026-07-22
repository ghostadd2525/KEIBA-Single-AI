import { getEnv } from "./env.js";
import { jsonError } from "./errors.js";

export function usePiProxy(env) {
  return Boolean(env.PI_BASE_URL);
}

export async function piFetch(context, path, init = {}) {
  const env = getEnv(context);
  if (!usePiProxy(env)) {
    return jsonError("PI_BASE_URL_REQUIRED", "PI KeibaNet API is not configured", 503);
  }

  const url = env.PI_BASE_URL + path;
  const headers = {
    accept: "application/json",
    ...(init.headers || {}),
  };
  if (env.CF_ACCESS_CLIENT_ID && env.CF_ACCESS_CLIENT_SECRET) {
    headers["CF-Access-Client-Id"] = env.CF_ACCESS_CLIENT_ID;
    headers["CF-Access-Client-Secret"] = env.CF_ACCESS_CLIENT_SECRET;
  }

  let res;
  try {
    res = await fetch(url, { ...init, headers });
  } catch (e) {
    return jsonError("PI_UNAVAILABLE", "PI KeibaNet API unreachable", 502, {
      message: String(e && e.message ? e.message : e),
    });
  }

  const text = await res.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    return jsonError("PI_BAD_RESPONSE", "PI KeibaNet API returned non-JSON", 502);
  }

  if (!res.ok) {
    return jsonError(
      (payload && payload.error) || "PI_ERROR",
      (payload && payload.message) || "PI KeibaNet API error",
      res.status >= 400 && res.status < 600 ? res.status : 502,
      payload
    );
  }

  return { ok: true, payload, source: "pi-keibanet-api" };
}

/**
 * Soft PI fetch — 単レース失敗を一覧合成で status に落とす用。
 * 既存 piFetch の Response 返却契約は変更しない。
 *
 * @returns {Promise<{ ok: boolean, status: number, payload: unknown, source: string, error?: string }>}
 */
export async function piFetchStatus(context, path, init = {}) {
  const env = getEnv(context);
  if (!usePiProxy(env)) {
    return {
      ok: false,
      status: 503,
      payload: null,
      source: "pi-keibanet-api",
      error: "PI_BASE_URL_REQUIRED",
    };
  }

  const url = env.PI_BASE_URL + path;
  const headers = {
    accept: "application/json",
    ...(init.headers || {}),
  };
  if (env.CF_ACCESS_CLIENT_ID && env.CF_ACCESS_CLIENT_SECRET) {
    headers["CF-Access-Client-Id"] = env.CF_ACCESS_CLIENT_ID;
    headers["CF-Access-Client-Secret"] = env.CF_ACCESS_CLIENT_SECRET;
  }

  let res;
  try {
    res = await fetch(url, { ...init, headers });
  } catch (e) {
    return {
      ok: false,
      status: 502,
      payload: null,
      source: "pi-keibanet-api",
      error: String(e && e.message ? e.message : e),
    };
  }

  const text = await res.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    return {
      ok: false,
      status: 502,
      payload: null,
      source: "pi-keibanet-api",
      error: "PI_BAD_RESPONSE",
    };
  }

  return {
    ok: res.ok,
    status: res.status,
    payload,
    source: "pi-keibanet-api",
  };
}
