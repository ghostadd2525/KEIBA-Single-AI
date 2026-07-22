/**
 * GET /api/ops/monitor — 統合ヘルス（本番監視用）
 *
 * BFF / Python / Tunnel / PI / Prediction / Conversation / ETL / Result Automation をプローブ。
 * Version 2 Phase 2: metrics / alerts / incidents を additive 添付（JSON 統一）。
 *
 * OPS_MONITOR_KEY 設定時は X-Ops-Monitor-Key または ?key= 必須。
 */
import { alertIdForCheck } from "../../_lib/opsDashboard.js";
import { logFailedChecks } from "../../_lib/incidentLog.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { runAllProbes, verifyMonitorKey } from "../../_lib/opsMonitor.js";
import { dispatchAlerts } from "../../_lib/opsSlack.js";

export async function onRequestGet(context) {
  if (!verifyMonitorKey(context)) {
    return jsonError("UNAUTHORIZED", "Invalid or missing ops monitor key", 401);
  }

  const report = await runAllProbes(context);

  const failed = report.checks.filter(function (c) {
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

  if (report.alerts && report.alerts.length) {
    await dispatchAlerts(context, report.alerts);
  }

  const httpStatus = report.status === "ok" ? 200 : 503;
  return jsonOk(report, { service: "OpsMonitor", cache: "no-store" }, { status: httpStatus, cacheControl: "no-store" });
}
