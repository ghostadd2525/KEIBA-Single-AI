/**
 * GET /api/ops/dashboard — Version 2 Ops Phase 3 ダッシュボード集約（最終）
 *
 * - 要 Bearer 認証
 * - beta.ui_features.v2_ops_dashboard === true のときのみ有効（Flag OFF → 404）
 * - admin_user_ids 設定時は管理者のみ
 * - overview / inventory / notifications / runbook 付き alerts
 */
import { getBearer, verifyStubToken } from "../../_lib/auth.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { buildDashboardPayload, alertIdForCheck } from "../../_lib/opsDashboard.js";
import { logFailedChecks } from "../../_lib/incidentLog.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { runAllProbes } from "../../_lib/opsMonitor.js";
import { dispatchAlerts, slackConfigured } from "../../_lib/opsSlack.js";
import { UserRepository } from "../../_lib/userRepository.js";

function isAdminUser(beta, session, profile) {
  const ids = (beta && beta.admin_user_ids) || [];
  if (!ids.length) return true;
  const uid = (session && session.id) || "";
  if (uid && ids.indexOf(uid) >= 0) return true;
  const role = (profile && profile.role) || (session && session.role) || "";
  return String(role).toUpperCase() === "ADMIN" || String(role).toUpperCase() === "OPS";
}

export async function onRequestGet(context) {
  const token = getBearer(context.request);
  const session = verifyStubToken(token, { purpose: "access" });
  if (!session) {
    return jsonError("UNAUTHORIZED", "login required", 401);
  }

  let beta = {};
  try {
    beta = await getBetaConfig(context);
  } catch {
    beta = {};
  }

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
