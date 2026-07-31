/**
 * Version8.8 — Approval Queue BFF (list)
 * GET /api/ops/approvals
 */
import { requireAccessSession, getBearer } from "../../_lib/auth.js";
import { isAdminUser } from "../../_lib/adminAuth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { UserRepository } from "../../_lib/userRepository.js";

async function loadAssetJson(context, path) {
  try {
    if (context.env && context.env.ASSETS && typeof context.env.ASSETS.fetch === "function") {
      const u = new URL(path, context.request.url);
      const res = await context.env.ASSETS.fetch(u);
      if (res && res.ok) {
        const ct = (res.headers.get("content-type") || "").toLowerCase();
        if (ct.indexOf("text/html") >= 0) return null;
        return await res.json();
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
    if (ct.indexOf("json") < 0) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function loadPublicSnapshot(context) {
  // Prefer approval-queue.json (v8.8.1 Publish Layer); approvals.json is alias
  return (
    (await loadAssetJson(context, "/ops-data/approval-queue.json")) ||
    (await loadAssetJson(context, "/ops-data/approvals.json"))
  );
}

export async function onRequestGet(context) {
  const session = requireAccessSession(context);
  if (session instanceof Response) return session;

  let beta = {};
  try {
    beta = await getBetaConfig(context);
  } catch {
    beta = {};
  }
  await resolveAuthorization(context, beta);
  const profile = await UserRepository.get(context, session.id).catch(function () {
    return null;
  });
  if (!isAdminUser(beta, session, profile)) {
    return jsonError("FORBIDDEN", "approvals require admin", 403);
  }

  const env = getEnv(context);
  const url = new URL(context.request.url);
  const status = url.searchParams.get("status") || "";
  const q = status ? `?status=${encodeURIComponent(status)}` : "";

  if (useAiProxy(env)) {
    const token = getBearer(context.request);
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const proxied = await aiFetch(context, `/v1/admin/approvals${q}`, {
      method: "GET",
      headers,
      timeoutMs: 20000,
    });
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, {
        ...(proxied.payload.meta || {}),
        service: "ApprovalQueueBff",
      });
    }
  }

  const snap = await loadPublicSnapshot(context);
  if (snap) {
    let items = snap.items || [];
    if (status) {
      items = items.filter(function (x) {
        return x && x.status === status;
      });
    }
    return jsonOk({ ...snap, items }, { service: "ApprovalQueueBff", source: "ops-data" });
  }
  return jsonError("APPROVALS_UNAVAILABLE", "approval queue unavailable", 502);
}
