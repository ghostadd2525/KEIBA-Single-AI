/**
 * Phase OPS-1 / OPS-1A — 公開モード（Ops Mode）
 *
 * PUBLIC: 一般ユーザー（USER）が Prediction / Conversation / User API を利用可
 * CLOSED: USER はブロック。ADMIN（および将来 OPS / DEVELOPER）は bypass
 *
 * 現状のソース:
 * 1. beta.ops_mode（明示 override）
 * 2. beta.maintenance_mode === true → CLOSED
 * 3. それ以外 → PUBLIC
 *
 * 将来: ops-calendar.json による開催日判定をここに追加（Monitor/RA 非依存）
 */
import { canBypassOpsMode, normalizeRole, Role } from "./roles.js";

export const OpsMode = Object.freeze({
  PUBLIC: "PUBLIC",
  CLOSED: "CLOSED",
});

/** 公開制御の対象外（認証・監視・ヘルス）。OPS-Monitor を壊さない。 */
export const OPS_MODE_EXEMPT_PATHS = new Set([
  "/api/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/me",
  "/api/auth/invite/start",
  "/api/auth/setup",
  "/api/health",
  "/api/ops/monitor",
]);

/**
 * @param {object | null | undefined} beta
 * @returns {"PUBLIC"|"CLOSED"}
 */
export function resolveOpsMode(beta) {
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
  // 権限判定は公開制御より先（呼び出し側で role 解決済み前提）
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
