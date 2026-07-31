/**
 * GET /api/system/status — Maintenance 正本（認証不要）
 *
 * {
 *   maintenance: boolean,
 *   maintenance_start: string,
 *   maintenance_end: string,
 *   reason: string
 * }
 *
 * Version7 Maintenance Mode — Research Week schedule (JST).
 * PE / CE / AI untouched.
 */
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { jsonOk } from "../../_lib/errors.js";
import { resolveOpsModeDetailed, maintenanceUserMessage } from "../../_lib/opsMode.js";

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
    maintenance,
    maintenance_start: resolved.maintenance_start || null,
    maintenance_end: resolved.maintenance_end || null,
    reason: maintenance
      ? resolved.schedule_reason || resolved.reason || "Research Week"
      : resolved.schedule_reason || "Production Open",
    ops_mode: resolved.ops_mode,
    resolve_reason: resolved.reason,
    message: maintenanceUserMessage(beta),
    server_time_iso: new Date().toISOString(),
  };

  return jsonOk(data, { service: "SystemStatus", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
