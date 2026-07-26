/**
 * Phase OPS-1A — 認可コンテキスト組み立て
 *
 * 順序: 認証 → ロール解決 →（その後）公開制御
 * OPS-Monitor / Result Automation には影響しない。
 *
 * Version8.5.1: token.role による昇格は禁止。正本は user profile + allowlist のみ。
 */
import { getUser } from "./userRepository.js";
import { canBypassOpsMode, normalizeRole, Role } from "./roles.js";
import { isListedAdmin } from "./opsMode.js";

/**
 * @param {object} context
 * @param {object | null} [beta]
 * @returns {Promise<{ role: string, bypass_ops_mode: boolean, source: string }>}
 */
export async function resolveAuthorization(context, beta) {
  context.data = context.data || {};
  const session = context.data.user;

  if (!session || !session.id) {
    const authz = {
      role: Role.USER,
      bypass_ops_mode: false,
      source: "anonymous",
    };
    context.data.authz = authz;
    return authz;
  }

  let role = Role.USER;
  let source = "default";

  const profile = await getUser(context, session.id);
  if (profile && profile.role) {
    role = normalizeRole(profile.role);
    source = "user_profile";
  }
  // Version8.5.1: session.role / stub token role claim は採用しない

  if (role === Role.USER && (await isListedAdmin(context, session.id, beta))) {
    role = Role.ADMIN;
    source = "admin_allowlist";
  }

  const authz = {
    role,
    bypass_ops_mode: canBypassOpsMode(role),
    source,
  };
  context.data.user = { ...session, role };
  context.data.authz = authz;
  return authz;
}
