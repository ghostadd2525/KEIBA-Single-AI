/**
 * Phase OPS-1 / OPS-1A / V1.1 / V7 Maintenance Mode — 公開モード（Ops Mode）
 *
 * PUBLIC: 一般ユーザー（USER）が Prediction / Conversation / User API を利用可
 * CLOSED: USER はブロック。ADMIN（および将来 OPS / DEVELOPER）は bypass
 *
 * 優先順位:
 * 1. beta.ops_mode（明示 override）
 * 2. beta.maintenance_mode === true → CLOSED
 * 3. ui_features.v11_auto_maintenance + Research Week schedule
 *    （日曜 21:00 JST 〜 土曜 00:00 JST → CLOSED）
 * 4. それ以外 → PUBLIC
 *
 * ADMIN / OPS / DEVELOPER は CLOSED でも bypass（JWT 維持・強制ログアウト対象外）。
 * PE / CE / AI / ResultAutomation / Research ロジックは変更しない。
 */
import {
  isResearchWeekMaintenance,
  resolveMaintenanceWindow,
  maintenanceUserMessage,
} from "./maintenanceSchedule.js";
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
  "/api/users/me",
  "/api/admin/invitations",
  "/api/health",
  "/api/ops/monitor",
  "/api/ops/public-status",
  "/api/system/status",
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
 * @param {{ now?: Date }} [options]
 * @returns {Promise<{
 *   ops_mode: "PUBLIC"|"CLOSED",
 *   reason: string,
 *   manual_override: boolean,
 *   auto_maintenance_enabled: boolean,
 *   maintenance: boolean,
 *   maintenance_start: string | null,
 *   maintenance_end: string | null,
 *   schedule_reason: string | null,
 *   calendar: null,
 * }>}
 */
export async function resolveOpsModeDetailed(beta, options) {
  const opts = options || {};
  const now = opts.now || new Date();
  const autoOn = isAutoMaintenanceEnabled(beta);
  const window = resolveMaintenanceWindow(now);

  if (beta && beta.ops_mode != null && String(beta.ops_mode).trim()) {
    const m = String(beta.ops_mode).trim().toUpperCase();
    if (m === OpsMode.CLOSED || m === "MAINTENANCE" || m === "OFF") {
      return {
        ops_mode: OpsMode.CLOSED,
        reason: "manual_ops_mode",
        manual_override: true,
        auto_maintenance_enabled: autoOn,
        maintenance: true,
        maintenance_start: window.maintenance_start,
        maintenance_end: window.maintenance_end,
        schedule_reason: window.reason,
        calendar: null,
      };
    }
    if (m === OpsMode.PUBLIC || m === "ON" || m === "OPEN") {
      return {
        ops_mode: OpsMode.PUBLIC,
        reason: "manual_ops_mode",
        manual_override: true,
        auto_maintenance_enabled: autoOn,
        maintenance: false,
        maintenance_start: window.maintenance_start,
        maintenance_end: window.maintenance_end,
        schedule_reason: window.reason,
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
      maintenance: true,
      maintenance_start: window.maintenance_start,
      maintenance_end: window.maintenance_end,
      schedule_reason: "manual_maintenance_mode",
      calendar: null,
    };
  }

  if (autoOn) {
    const closed = isResearchWeekMaintenance(now);
    return {
      ops_mode: closed ? OpsMode.CLOSED : OpsMode.PUBLIC,
      reason: closed ? "research_week_maintenance" : "research_week_open",
      manual_override: false,
      auto_maintenance_enabled: true,
      maintenance: closed,
      maintenance_start: window.maintenance_start,
      maintenance_end: window.maintenance_end,
      schedule_reason: window.reason,
      calendar: null,
    };
  }

  return {
    ops_mode: OpsMode.PUBLIC,
    reason: "default_public",
    manual_override: false,
    auto_maintenance_enabled: false,
    maintenance: false,
    maintenance_start: window.maintenance_start,
    maintenance_end: window.maintenance_end,
    schedule_reason: window.reason,
    calendar: null,
  };
}

/**
 * 同期互換 API。
 *
 * @param {object | null | undefined} beta
 * @param {{ now?: Date }} [options]
 * @returns {"PUBLIC"|"CLOSED"}
 */
export function resolveOpsMode(beta, options) {
  const opts = options || {};
  const now = opts.now || new Date();
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
    return isResearchWeekMaintenance(now) ? OpsMode.CLOSED : OpsMode.PUBLIC;
  }

  return OpsMode.PUBLIC;
}

/**
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

export { Role, canBypassOpsMode, normalizeRole, maintenanceUserMessage };
