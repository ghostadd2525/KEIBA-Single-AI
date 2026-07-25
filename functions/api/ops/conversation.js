/**
 * Conversation Observability BFF — GET /api/ops/conversation
 * Proxies AI /v1/ops/conversation/dashboard (+ health fallback).
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getBearer } from "../../_lib/auth.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestGet(context) {
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

  // Fallback: compose from health + metrics
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
