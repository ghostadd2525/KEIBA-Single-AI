/**
 * GET /api/ops/dashboard — Version 2 Ops Phase 3 ダッシュボード集約（最終）
 *
 * - 要 Bearer 認証
 * - beta.ui_features.v2_ops_dashboard === true のときのみ有効（Flag OFF → 404）
 * - Version8.5.1: ADMIN = profile role または admin_user_ids（fail-closed）
 * - overview / inventory / notifications / runbook 付き alerts
 */
import { requireAccessSession } from "../../_lib/auth.js";
import { isAdminUser } from "../../_lib/adminAuth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { buildDashboardPayload, alertIdForCheck } from "../../_lib/opsDashboard.js";
import { logFailedChecks } from "../../_lib/incidentLog.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { runAllProbes } from "../../_lib/opsMonitor.js";
import { dispatchAlerts, slackConfigured } from "../../_lib/opsSlack.js";
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

  const features = (beta && beta.ui_features) || {};
  if (!features.v2_ops_dashboard) {
    return jsonError("FEATURE_DISABLED", "v2_ops_dashboard is off", 404);
  }

  const profile = await UserRepository.get(context, session.id).catch(function () {
    return null;
  });
  if (!isAdminUser(beta, session, profile)) {
    return jsonError("FORBIDDEN", "ops dashboard requires admin", 403);
  }

  const report = await runAllProbes(context);
  const slack = slackConfigured(context.env || {});
  const payload = buildDashboardPayload(report, {
    source: "bff-dashboard",
    notifications: {
      slackCriticalConfigured: slack.critical,
      slackWarningConfigured: slack.warning,
    },
  });

  const failed = (report.checks || []).filter(function (c) {
    return !c.skipped && !c.ok;
  });
  if (failed.length) {
    logFailedChecks(
      context,
      failed.map(function (c) {
        return {
          name: c.name,
          ok: false,
          error: c.error || "unhealthy",
          restart_count: 0,
          detail: c.detail || { latency_ms: c.latency_ms },
          alert_id: alertIdForCheck(c),
        };
      })
    );
  }

  if (payload.alerts && payload.alerts.length) {
    await dispatchAlerts(context, payload.alerts);
  }

  const httpStatus = payload.status === "ok" ? 200 : 503;
  return jsonOk(payload, { service: "OpsDashboard", cache: "no-store" }, {
    status: httpStatus,
    cacheControl: "no-store",
  });
}
