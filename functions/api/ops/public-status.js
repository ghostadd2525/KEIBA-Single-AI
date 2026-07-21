/**
 * GET /api/ops/public-status — 公開モード / 開催日ステータス（exempt・認証不要）
 *
 * メンテ UI・フロント Gate・Canary の単一ソース。契約加算のみ。
 */
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { createCalendarProvider } from "../../_lib/calendar/createCalendarProvider.js";
import { jsonOk } from "../../_lib/errors.js";
import { resolveOpsModeDetailed } from "../../_lib/opsMode.js";

export async function onRequestGet(context) {
  let beta = {};
  try {
    beta = await getBetaConfig(context);
  } catch {
    beta = {};
  }

  const provider = createCalendarProvider(beta);
  const calendar = await Promise.resolve(provider.decide(new Date()));
  const resolved = await resolveOpsModeDetailed(beta, {
    provider: provider,
    decision: calendar,
  });

  const data = {
    ops_mode: resolved.ops_mode,
    reason: resolved.reason,
    manual_override: resolved.manual_override,
    auto_maintenance_enabled: resolved.auto_maintenance_enabled,
    is_race_day: !!(calendar && calendar.is_race_day),
    date_jst: (calendar && calendar.date_jst) || null,
    next_open_date_jst: (calendar && calendar.next_open_date_jst) || null,
    calendar_source: (calendar && calendar.source) || "weekend",
    message:
      beta.maintenance_message ||
      "ただいま公開時間外です。開催日のみご利用いただけます。",
  };

  return jsonOk(data, { service: "OpsPublicStatus", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
