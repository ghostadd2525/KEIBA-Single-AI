import { jsonError } from "./errors.js";
import { getEnv } from "./env.js";

const PUBLIC_PATHS = new Set([
  "/api/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/invite/start",
  "/api/auth/setup",
  "/api/health",
  "/api/ops/monitor",
  "/api/ops/public-status",
  "/api/system/status",
]);

export function getBearer(request) {
  const h = request.headers.get("authorization") || "";
  const m = /^Bearer\s+(.+)$/i.exec(h);
  return m ? m[1].trim() : "";
}

/**
 * Version8.5.1: stub は開発／緊急ブレークグラスのみ。
 * EXPECT_ENV=production|prod では ALLOW_STUB_AUTH=1 が無い限り拒否。
 */
export function isProductionExpectEnv(env) {
  const e = String((env && env.EXPECT_ENV) || "")
    .trim()
    .toLowerCase();
  return e === "production" || e === "prod";
}

export function stubAuthAllowed(env) {
  if (!isProductionExpectEnv(env)) return true;
  return String((env && env.ALLOW_STUB_AUTH) || "") === "1";
}

/**
 * stub token: stub.<base64url({sub,exp,purpose})>.<exp>
 * Version8.5.1: role claim は発行・検証とも扱わない（昇格禁止）。
 */
export function makeStubToken(userId, expiresIn = 86400, opts = {}) {
  const exp = Math.floor(Date.now() / 1000) + expiresIn;
  const purpose = opts.purpose || "access";
  const payloadObj = { sub: userId, exp, purpose };
  // role は意図的に埋め込まない（opts.role 無視）
  const payload = btoa(unescape(encodeURIComponent(JSON.stringify(payloadObj))))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `stub.${payload}.${exp}`;
}

/**
 * @param {string} token
 * @param {{ purpose?: "access"|"setup" }} [opts]
 * @returns {{ id: string, purpose: string } | null}
 */
export function verifyStubToken(token, opts = {}) {
  if (!token || !token.startsWith("stub.")) return null;
  const parts = token.split(".");
  if (parts.length < 3) return null;
  try {
    const json = decodeURIComponent(escape(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"))));
    const payload = JSON.parse(json);
    if (!payload.sub) return null;
    if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) return null;
    const purpose = payload.purpose || "access";
    const want = opts.purpose || "access";
    if (purpose !== want) return null;
    // role claim があっても破棄（昇格経路を閉じる）
    return { id: String(payload.sub), purpose };
  } catch {
    return null;
  }
}

export async function requireAuth(context) {
  const url = new URL(context.request.url);
  if (PUBLIC_PATHS.has(url.pathname)) return null;

  const env = getEnv(context);
  const token = getBearer(context.request);

  // Phase9 β: Prediction 等の閲覧 API は従来どおり Bearer 任意。
  // me / favorites は各ハンドラで access トークンを必須化する。
  if (!token) return null;

  const isStubToken = token.startsWith("stub.");
  const mode = String(env.AUTH_MODE || "stub").toLowerCase();

  if (isProductionExpectEnv(env) && !stubAuthAllowed(env)) {
    if (isStubToken || mode === "stub" || !env.AUTH_MODE) {
      return jsonError(
        "STUB_AUTH_FORBIDDEN",
        "stub authentication is not allowed in production (Version8.5.1)",
        401
      );
    }
  }

  if (mode === "stub" || !env.AUTH_MODE) {
    if (!stubAuthAllowed(env) && isProductionExpectEnv(env)) {
      return jsonError(
        "STUB_AUTH_FORBIDDEN",
        "stub authentication is not allowed in production (Version8.5.1)",
        401
      );
    }
    const user = verifyStubToken(token, { purpose: "access" });
    if (!user) return jsonError("UNAUTHORIZED", "invalid token", 401);
    context.data = context.data || {};
    context.data.user = user;
    return null;
  }

  // 非 stub モード: stub トークンは拒否（本番・開発とも）
  if (isStubToken) {
    return jsonError("STUB_AUTH_FORBIDDEN", "stub token rejected for AUTH_MODE=" + mode, 401);
  }

  // 現行に署名 JWT 検証パスが無い場合は未対応
  return jsonError("AUTH_MODE_UNSUPPORTED", "AUTH_MODE requires non-stub verifier (not configured)", 401);
}

/**
 * ハンドラ用: access セッション必須 + Version8.5.1 stub 本番ポリシー。
 * @returns {{ id: string, purpose: string } | Response}
 */
export function requireAccessSession(context) {
  const env = getEnv(context);
  const token = getBearer(context.request);
  if (!token) {
    return jsonError("UNAUTHORIZED", "login required", 401);
  }

  const isStubToken = token.startsWith("stub.");
  if (isProductionExpectEnv(env) && !stubAuthAllowed(env) && isStubToken) {
    return jsonError(
      "STUB_AUTH_FORBIDDEN",
      "stub authentication is not allowed in production (Version8.5.1)",
      401
    );
  }

  if (isStubToken) {
    if (isProductionExpectEnv(env) && !stubAuthAllowed(env)) {
      return jsonError(
        "STUB_AUTH_FORBIDDEN",
        "stub authentication is not allowed in production (Version8.5.1)",
        401
      );
    }
    const user = verifyStubToken(token, { purpose: "access" });
    if (!user) return jsonError("UNAUTHORIZED", "invalid token", 401);
    context.data = context.data || {};
    context.data.user = user;
    return user;
  }

  const mode = String(env.AUTH_MODE || "stub").toLowerCase();
  if (mode === "stub" || !env.AUTH_MODE) {
    return jsonError("UNAUTHORIZED", "invalid token", 401);
  }
  return jsonError("AUTH_MODE_UNSUPPORTED", "AUTH_MODE requires non-stub verifier (not configured)", 401);
}
