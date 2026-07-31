/**
 * Shared helpers for Version8.9 Operations Console APIs.
 * Read-only against public/ops-data Publish Layer.
 */
import { requireAccessSession } from "./auth.js";
import { resolveAuthorization } from "./authorization.js";
import { getBetaConfig } from "./betaConfig.js";
import { jsonError } from "./errors.js";
import { isOpsPortalAdmin } from "./opsPortalAccess.js";
import { Role } from "./roles.js";
import { UserRepository } from "./userRepository.js";

export async function requireOpsAdmin(context) {
  const session = requireAccessSession(context);
  if (session instanceof Response) return { error: session };

  let beta = {};
  try {
    beta = await getBetaConfig(context);
  } catch {
    beta = {};
  }

  const authz = await resolveAuthorization(context, beta);
  const profile = await UserRepository.get(context, session.id).catch(function () {
    return null;
  });
  const effectiveProfile = {
    ...(profile || {}),
    role: (profile && profile.role) || authz.role,
  };
  const allow =
    authz.role === Role.ADMIN || isOpsPortalAdmin(beta, session, effectiveProfile);
  if (!allow) {
    return { error: jsonError("FORBIDDEN", "ops console requires role=ADMIN", 403) };
  }
  return { session, beta, authz, profile: effectiveProfile };
}

export async function fetchOpsAsset(context, path) {
  try {
    if (context.env && context.env.ASSETS && typeof context.env.ASSETS.fetch === "function") {
      const u = new URL(path, context.request.url);
      const res = await context.env.ASSETS.fetch(u);
      if (res && res.ok) {
        const ct = (res.headers.get("content-type") || "").toLowerCase();
        if (ct.indexOf("text/html") >= 0) return null;
        if (ct.indexOf("json") >= 0 || path.endsWith(".json")) {
          return await res.json();
        }
        return await res.text();
      }
    }
  } catch {
    /* fall through */
  }
  try {
    const u = new URL(path, context.request.url);
    const res = await fetch(u.toString(), { cf: { cacheTtl: 0 } });
    if (!res.ok) return null;
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (ct.indexOf("text/html") >= 0) return null;
    if (ct.indexOf("json") >= 0 || path.endsWith(".json")) return await res.json();
    return await res.text();
  } catch {
    return null;
  }
}

export async function fetchJsonApi(context, path) {
  try {
    const u = new URL(path, context.request.url);
    const headers = { Accept: "application/json" };
    const auth = context.request.headers.get("authorization");
    if (auth) headers.Authorization = auth;
    const res = await fetch(u.toString(), { headers, cf: { cacheTtl: 0 } });
    if (!res.ok) return { ok: false, status: res.status, data: null };
    const body = await res.json();
    return {
      ok: body && body.ok !== false,
      status: res.status,
      data: body && body.data != null ? body.data : body,
      raw: body,
    };
  } catch (e) {
    return { ok: false, status: 0, data: null, error: String(e && e.message ? e.message : e) };
  }
}
