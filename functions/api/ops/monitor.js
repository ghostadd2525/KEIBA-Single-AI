/**
 * GET /api/ops/monitor — 統合ヘルス（本番監視用）
 *
 * BFF / Python / Tunnel / Prediction / Conversation / ETL / Result Automation をプローブ。
 * 障害時は incident ログへ記録。
 *
 * OPS_MONITOR_KEY 設定時は X-Ops-Monitor-Key または ?key= 必須。
 */
import { logFailedChecks } from "../../_lib/incidentLog.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { runAllProbes, verifyMonitorKey } from "../../_lib/opsMonitor.js";

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
        };
      })
    );
  }

  const httpStatus = report.status === "ok" ? 200 : 503;
  return jsonOk(report, { service: "OpsMonitor", cache: "no-store" }, { status: httpStatus, cacheControl: "no-store" });
}
