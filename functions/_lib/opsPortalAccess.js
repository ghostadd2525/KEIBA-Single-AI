/**
 * Version8.7 — Operations Portal アクセス判定
 *
 * /ops および GET /api/ops/portal は role=ADMIN のみ。
 * Version8.5.1: session.role（token claim）は信用しない。profile + allowlist のみ。
 * PE / CE / AI / ResultAutomation / Research ロジック非変更。
 */
import { normalizeRole, Role } from "./roles.js";

/**
 * @param {unknown} beta
 * @param {{ id?: string, role?: string } | null} session
 * @param {{ role?: string } | null} profile
 * @returns {boolean}
 */
export function isOpsPortalAdmin(beta, session, profile) {
  if (profile && profile.role != null && profile.role !== "") {
    const role = normalizeRole(profile.role);
    if (role === Role.ADMIN || role === Role.OPS || role === Role.DEVELOPER) {
      return true;
    }
  }

  const ids = (beta && beta.admin_user_ids) || [];
  const uid = (session && session.id) || "";
  if (uid && ids.length && ids.indexOf(uid) >= 0) return true;

  return false;
}
