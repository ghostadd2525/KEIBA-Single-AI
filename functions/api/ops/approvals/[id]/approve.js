/**
 * POST /api/ops/approvals/:id/approve — Version8.8
 * Deploy Note only. Production auto-apply forbidden.
 */
import { requireAccessSession, getBearer } from "../../../../_lib/auth.js";
import { isAdminUser } from "../../../../_lib/adminAuth.js";
import { resolveAuthorization } from "../../../../_lib/authorization.js";
import { getBetaConfig } from "../../../../_lib/betaConfig.js";
import { aiFetch } from "../../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../../_lib/errors.js";
import { UserRepository } from "../../../../_lib/userRepository.js";

export async function onRequestPost(context) {
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
  if (!useAiProxy(env)) {
    return jsonError("AI_UNAVAILABLE", "AI_BASE_URL required for approval actions", 503);
  }

  const id = context.params && context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "approval id required", 400);

  const token = getBearer(context.request);
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const proxied = await aiFetch(
    context,
    `/v1/admin/approvals/${encodeURIComponent(id)}/approve`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({ actor: session.id || "admin" }),
      timeoutMs: 30000,
    }
  );
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    return jsonOk(proxied.payload.data, {
      ...(proxied.payload.meta || {}),
      service: "ApprovalQueueBff",
    });
  }
  return jsonError(
    "APPROVAL_ACTION_FAILED",
    (proxied && proxied.error && proxied.error.message) || "approve failed",
    502
  );
}
