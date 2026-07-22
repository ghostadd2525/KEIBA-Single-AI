/**
 * Phase OPS-1 / OPS-1A / V1.1 auto-maintenance — 公開モード（Ops Mode）
 *
 * PUBLIC: 一般ユーザー（USER）が Prediction / Conversation / User API を利用可
 * CLOSED: USER はブロック。ADMIN（および将来 OPS / DEVELOPER）は bypass
 *
 * 優先順位:
 * 1. beta.ops_mode（明示 override）
 * 2. beta.maintenance_mode === true → CLOSED
 * 3. ui_features.v11_auto_maintenance + CalendarProvider（非開催日 → CLOSED）
 * 4. それ以外 → PUBLIC
 */
import { createCalendarProvider } from "./calendar/createCalendarProvider.js";
import { canBypassOpsMode, normalizeRole, Role } from "./roles.js";

export const OpsMode = Object.freeze({
  PUBLIC: "PUBLIC",
  CLOSED: "CLOSED",
});

/** 公開制御の対象外（認証・監視・ヘルス・公開ステータス）。OPS-Monitor を壊さない。 */
export const OPS_MODE_EXEMPT_PATHS = new Set([
  "/api/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/me",
  "/api/auth/invite/start",
  "/api/auth/setup",
  "/api/health",
  "/api/ops/monitor",
  "/api/ops/public-status",
  "/api/v1/stats/heatmap",
]);

/**
 * @param {object | null | undefined} beta
 * @returns {boolean}
 */
export function isAutoMaintenanceEnabled(beta) {
  const f = beta && beta.ui_features;
  return !!(f && f.v11_auto_maintenance === true);
}

/**
 * @param {object | null | undefined} beta
 * @param {{
 *   now?: Date,
 *   provider?: import("./calendar/CalendarProvider.js").CalendarProvider,
 *   decision?: import("./calendar/CalendarProvider.js").CalendarDecision,
 * }} [options]
 * @returns {Promise<{
 *   ops_mode: "PUBLIC"|"CLOSED",
 *   reason: string,
 *   manual_override: boolean,
 *   auto_maintenance_enabled: boolean,
 *   calendar: import("./calendar/CalendarProvider.js").CalendarDecision | null,
 * }>}
 */
export async function resolveOpsModeDetailed(beta, options) {
  const opts = options || {};
  const autoOn = isAutoMaintenanceEnabled(beta);

  if (beta && beta.ops_mode != null && String(beta.ops_mode).trim()) {
    const m = String(beta.ops_mode).trim().toUpperCase();
    if (m === OpsMode.CLOSED || m === "MAINTENANCE" || m === "OFF") {
      return {
        ops_mode: OpsMode.CLOSED,
        reason: "manual_ops_mode",
        manual_override: true,
        auto_maintenance_enabled: autoOn,
        calendar: null,
      };
    }
    if (m === OpsMode.PUBLIC || m === "ON" || m === "OPEN") {
      return {
        ops_mode: OpsMode.PUBLIC,
        reason: "manual_ops_mode",
        manual_override: true,
        auto_maintenance_enabled: autoOn,
        calendar: null,
      };
    }
  }

  if (beta && beta.maintenance_mode === true) {
    return {
      ops_mode: OpsMode.CLOSED,
      reason: "manual_maintenance_mode",
      manual_override: true,
      auto_maintenance_enabled: autoOn,
      calendar: null,
    };
  }

  let calendar = opts.decision || null;
  if (autoOn) {
    if (!calendar) {
      const provider = opts.provider || createCalendarProvider(beta);
      calendar = await Promise.resolve(provider.decide(opts.now || new Date()));
    }
    if (calendar && calendar.is_race_day === false) {
      return {
        ops_mode: OpsMode.CLOSED,
        reason: "auto_calendar",
        manual_override: false,
        auto_maintenance_enabled: true,
        calendar: calendar,
      };
    }
    return {
      ops_mode: OpsMode.PUBLIC,
      reason: "auto_calendar_race_day",
      manual_override: false,
      auto_maintenance_enabled: true,
      calendar: calendar,
    };
  }

  return {
    ops_mode: OpsMode.PUBLIC,
    reason: "default_public",
    manual_override: false,
    auto_maintenance_enabled: false,
    calendar: calendar,
  };
}

/**
 * 同期互換 API。Flag OFF / 手動のみの既存テスト向け。
 * auto maintenance 時は Weekend（または options.decision）を同期評価する。
 *
 * @param {object | null | undefined} beta
 * @param {{
 *   now?: Date,
 *   provider?: import("./calendar/CalendarProvider.js").CalendarProvider,
 *   decision?: import("./calendar/CalendarProvider.js").CalendarDecision,
 * }} [options]
 * @returns {"PUBLIC"|"CLOSED"}
 */
export function resolveOpsMode(beta, options) {
  const opts = options || {};
  const autoOn = isAutoMaintenanceEnabled(beta);

  if (beta && beta.ops_mode != null && String(beta.ops_mode).trim()) {
    const m = String(beta.ops_mode).trim().toUpperCase();
    if (m === OpsMode.CLOSED || m === "MAINTENANCE" || m === "OFF") {
      return OpsMode.CLOSED;
    }
    if (m === OpsMode.PUBLIC || m === "ON" || m === "OPEN") {
      return OpsMode.PUBLIC;
    }
  }
  if (beta && beta.maintenance_mode === true) {
    return OpsMode.CLOSED;
  }

  if (autoOn) {
    const provider = opts.provider || createCalendarProvider(beta);
    const decision =
      opts.decision || provider.decide(opts.now || new Date());
    // sync path: decide must not return a Promise here（Weekend は sync）
    if (decision && typeof decision.then === "function") {
      return OpsMode.PUBLIC;
    }
    if (decision && decision.is_race_day === false) {
      return OpsMode.CLOSED;
    }
  }

  return OpsMode.PUBLIC;
}

/**
 * 認可（ロール）評価のあとに呼ぶ公開制御判定。
 *
 * @param {{
 *   pathname: string,
 *   opsMode: string,
 *   role?: string,
 *   bypassOpsMode?: boolean,
 * }} input
 * @returns {{ allow: boolean, reason: string, role: string, ops_mode: string }}
 */
export function evaluateOpsAccess(input) {
  const pathname = String((input && input.pathname) || "");
  const opsMode =
    input && input.opsMode === OpsMode.CLOSED ? OpsMode.CLOSED : OpsMode.PUBLIC;
  const role = normalizeRole(input && input.role);
  const bypass =
    input && typeof input.bypassOpsMode === "boolean"
      ? input.bypassOpsMode
      : canBypassOpsMode(role);

  if (OPS_MODE_EXEMPT_PATHS.has(pathname)) {
    return { allow: true, reason: "exempt_path", role, ops_mode: opsMode };
  }
  if (bypass) {
    return { allow: true, reason: "role_bypass", role, ops_mode: opsMode };
  }
  if (opsMode === OpsMode.CLOSED) {
    return { allow: false, reason: "ops_closed", role, ops_mode: opsMode };
  }
  return { allow: true, reason: "ops_public", role, ops_mode: opsMode };
}

/**
 * @param {object} context
 * @param {string} userId
 * @param {object | null} beta
 * @returns {Promise<boolean>}
 */
export async function isListedAdmin(context, userId, beta) {
  const id = String(userId || "").trim();
  if (!id) return false;
  const fromBeta = (beta && Array.isArray(beta.admin_user_ids) ? beta.admin_user_ids : [])
    .map(function (x) {
      return String(x || "").trim();
    })
    .filter(Boolean);
  const env = (context && context.env) || {};
  const fromEnv = String(env.EXPECT_ADMIN_USER_IDS || "")
    .split(",")
    .map(function (x) {
      return x.trim();
    })
    .filter(Boolean);
  const set = new Set(fromBeta.concat(fromEnv));
  return set.has(id);
}

export { Role, canBypassOpsMode, normalizeRole };
