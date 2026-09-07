/**
 * GET /api/ops/result-automation?date=YYYY-MM-DD
 * ResultAutomation Version7 pipeline dashboard (admin).
 * Version8.5.1: fail-closed admin（RA 本体ロジック非変更）。
 */
import { requireAccessSession, getBearer } from "../../_lib/auth.js";
import { isAdminUser } from "../../_lib/adminAuth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { UserRepository } from "../../_lib/userRepository.js";

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
    return jsonError("FORBIDDEN", "ops result-automation requires admin", 403);
  }

  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("AI_UNAVAILABLE", "AI_BASE_URL not configured", 502);
  }

  const url = new URL(context.request.url);
  const date = url.searchParams.get("date") || url.searchParams.get("race_date") || "";
  const path = date
    ? `/v1/admin/results/status?date=${encodeURIComponent(date)}`
    : "/v1/admin/results/status";
  const proxied = await aiFetch(context, path);
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data, {
      ...(proxied.payload.meta || {}),
      service: "ResultAutomationDashboard",
    });
  }
  const msg =
    (proxied && proxied.error && proxied.error.message) ||
    "result automation status unavailable";
  return jsonError("RESULT_AUTOMATION_UNAVAILABLE", msg, 502);
}
