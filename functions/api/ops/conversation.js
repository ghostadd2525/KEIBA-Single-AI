/**
 * Conversation Observability BFF — GET /api/ops/conversation
 * Proxies AI /v1/ops/conversation/dashboard (+ health fallback).
 *
 * Version8.5.1: ADMIN 必須（JWT/session → resolveAuthorization → profile/allowlist）。
 * Maintenance / OPS CLOSED は middleware 経由。PE / CE / AI 非変更。
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getBearer, requireAccessSession } from "../../_lib/auth.js";
import { isAdminUser } from "../../_lib/adminAuth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
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
    return jsonError("FORBIDDEN", "ops conversation requires admin", 403);
  }

  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return jsonError("AI_UNAVAILABLE", "AI_BASE_URL not configured", 503);
  }

  const token = getBearer(context.request);
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const dash = await aiFetch(context, "/v1/ops/conversation/dashboard", {
    method: "GET",
    headers,
    timeoutMs: 20000,
  });
  if (dash && dash.ok && !(dash instanceof Response)) {
    return jsonOk(dash.payload.data, {
      ...(dash.payload.meta || {}),
      service: "ConversationObservabilityBff",
    });
  }

  const [health, metrics, alerts] = await Promise.all([
    aiFetch(context, "/v1/conversation/health", { method: "GET", headers, timeoutMs: 15000 }),
    aiFetch(context, "/v1/ops/conversation/metrics", { method: "GET", headers, timeoutMs: 10000 }),
    aiFetch(context, "/v1/ops/conversation/alerts", { method: "GET", headers, timeoutMs: 10000 }),
  ]);

  const healthData =
    health && health.ok && !(health instanceof Response) ? health.payload.data : null;
  const metricsData =
    metrics && metrics.ok && !(metrics instanceof Response) ? metrics.payload.data : null;
  const alertsData =
    alerts && alerts.ok && !(alerts instanceof Response) ? alerts.payload.data : null;

  if (!healthData && !metricsData) {
    if (dash instanceof Response) return dash;
    return jsonError("CONVERSATION_OBS_UNAVAILABLE", "conversation observability unavailable", 502);
  }

  return jsonOk(
    {
      schema: "expect-conversation-observability/1.0",
      categories: {
        conversation: (metricsData && metricsData.conversation) || {},
        ollama: (metricsData && metricsData.ollama) || {},
        knowledge: (metricsData && metricsData.knowledge) || {},
        security: (metricsData && metricsData.security) || {},
      },
      health: healthData || {},
      alerts: (alertsData && alertsData.alerts) || [],
      generated_at: new Date().toISOString(),
      fallback: "composed",
    },
    { service: "ConversationObservabilityBff", fallback: "composed" }
  );
}
