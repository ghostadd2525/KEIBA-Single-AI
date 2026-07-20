import { jsonError } from "./errors.js";
import { getEnv } from "./env.js";

const PUBLIC_PATHS = new Set([
  "/api/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/invite/start",
  "/api/auth/setup",
]);

export function getBearer(request) {
  const h = request.headers.get("authorization") || "";
  const m = /^Bearer\s+(.+)$/i.exec(h);
  return m ? m[1].trim() : "";
}

/**
 * stub token: stub.<base64url({sub,exp,purpose})>.<exp>
 * purpose: "access" | "setup"（未指定トークンは access 扱い）
 */
export function makeStubToken(userId, expiresIn = 86400, opts = {}) {
  const exp = Math.floor(Date.now() / 1000) + expiresIn;
  const purpose = opts.purpose || "access";
  const payload = btoa(
    unescape(encodeURIComponent(JSON.stringify({ sub: userId, exp, purpose })))
  )
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

  if (env.AUTH_MODE === "stub" || !env.AUTH_MODE) {
    const user = verifyStubToken(token, { purpose: "access" });
    if (!user) return jsonError("UNAUTHORIZED", "invalid token", 401);
    context.data = context.data || {};
    context.data.user = user;
    return null;
  }

  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return jsonError("UNAUTHORIZED", "invalid token", 401);
  context.data = context.data || {};
  context.data.user = user;
  return null;
}
