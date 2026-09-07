/**
 * GET /api/ops/public-status — 公開モード / Maintenance ステータス（exempt・認証不要）
 *
 * メンテ UI・フロント Gate の単一ソース（後方互換）。契約加算のみ。
 * 正本スケジュールは Research Week（日曜21:00〜土曜00:00 JST）。
 */
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { jsonOk } from "../../_lib/errors.js";
import {
  resolveOpsModeDetailed,
  maintenanceUserMessage,
} from "../../_lib/opsMode.js";

export async function onRequestGet(context) {
  let beta = {};
  try {
    beta = await getBetaConfig(context);
  } catch {
    beta = {};
  }

  const resolved = await resolveOpsModeDetailed(beta, { now: new Date() });
  const maintenance =
    resolved.ops_mode === "CLOSED" || resolved.maintenance === true;

  const data = {
    ops_mode: resolved.ops_mode,
    reason: resolved.reason,
    manual_override: resolved.manual_override,
    auto_maintenance_enabled: resolved.auto_maintenance_enabled,
    maintenance,
    maintenance_start: resolved.maintenance_start || null,
    maintenance_end: resolved.maintenance_end || null,
    schedule_reason: resolved.schedule_reason || null,
    is_race_day: !maintenance,
    date_jst: null,
    next_open_date_jst: maintenance
      ? String(resolved.maintenance_end || "").slice(0, 10) || null
      : null,
    calendar_source: "research_week_jst",
    message: maintenanceUserMessage(beta),
  };

  return jsonOk(data, { service: "OpsPublicStatus", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
