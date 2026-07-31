/**
 * I4 — GET /api/ops/single-detail
 * Metrics + alerts for Single AI Detail Feature Flag path.
 * Admin / ops auth same pattern as other ops routes where possible;
 * allows OPS_MONITOR_KEY for probe automation.
 */
import { requireAccessSession } from "../../_lib/auth.js";
import { isAdminUser } from "../../_lib/adminAuth.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { UserRepository } from "../../_lib/userRepository.js";
import {
  evaluateSingleDetailAlerts,
  snapshotSingleDetailMetrics,
  DEFAULT_THRESHOLDS,
} from "../../_lib/singleDetailObservability.js";
import { getEnv } from "../../_lib/env.js";

function allowMonitorKey(context) {
  const env = getEnv(context);
  const key = env.OPS_MONITOR_KEY || "";
  if (!key) return false;
  const hdr = context.request.headers.get("X-Ops-Monitor-Key") || "";
  return hdr === key;
}

export async function onRequestGet(context) {
  if (!allowMonitorKey(context)) {
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
      return jsonError("FORBIDDEN", "ops single-detail requires admin", 403);
    }
  }

  const metrics = snapshotSingleDetailMetrics();
  const evaluated = evaluateSingleDetailAlerts(DEFAULT_THRESHOLDS, metrics);
  const payload = {
    schema_version: "expect-single-detail-ops/1.0",
    phase: "I4",
    metrics,
    alerts: evaluated.alerts || [],
    alert_eval: {
      deferred: !!evaluated.deferred,
      reason: evaluated.reason || null,
      thresholds: DEFAULT_THRESHOLDS,
    },
    endpoints: {
      detail: "/api/single/detail/:raceId",
      site_health: "/v1/site/health",
      single_metrics: "/v1/single/metrics",
    },
    notes: [
      "Flag ON path only hits /api/single/detail (list LOCK).",
      "Flag ON rate here = detail endpoint hit rate among recorded resolves.",
      "Prediction fallback is expected when core_payload is absent.",
    ],
  };

  const critical = (evaluated.alerts || []).some(function (a) {
    return a.severity === "critical";
  });
  return jsonOk(payload, { service: "SingleDetailOps", cache: "no-store" }, {
    status: critical ? 503 : 200,
    cacheControl: "no-store",
  });
}
