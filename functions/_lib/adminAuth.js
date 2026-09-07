/**
 * Version8.5.1 — Ops / Admin 認可（fail-closed）
 *
 * - admin_user_ids 空 → admin ではない（fail-open 禁止）
 * - 特権 role の正本は user profile または allowlist のみ
 * - stub token の role claim は信用しない
 * PE / CE / AI / RA / Research 非変更
 */
import { normalizeRole, Role } from "./roles.js";

/**
 * @param {unknown} beta
 * @param {{ id?: string } | null} session
 * @param {{ role?: string } | null} profile
 * @returns {boolean}
 */
export function isAdminUser(beta, session, profile) {
  if (!session || !session.id) return false;

  const ids = (beta && Array.isArray(beta.admin_user_ids) ? beta.admin_user_ids : []) || [];
  const uid = String(session.id || "");

  if (uid && ids.length > 0 && ids.indexOf(uid) >= 0) {
    return true;
  }

  // 判定不能（profile 無し・role 無し・allowlist 空）→ USER 扱い = false
  if (!profile || profile.role == null || profile.role === "") {
    return false;
  }

  const role = normalizeRole(profile.role);
  return role === Role.ADMIN || role === Role.OPS || role === Role.DEVELOPER;
}

/**
 * @param {object} context
 * @param {object | null} beta
 * @param {{ id?: string } | null} session
 * @param {{ role?: string } | null} profile
 * @returns {boolean}
 */
export function isAdminAuthorized(context, beta, session, profile) {
  const authz = context && context.data && context.data.authz;
  if (authz && authz.role) {
    const r = normalizeRole(authz.role);
    if (r === Role.ADMIN || r === Role.OPS || r === Role.DEVELOPER) return true;
  }
  return isAdminUser(beta, session, profile);
}
