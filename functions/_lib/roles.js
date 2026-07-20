/**
 * Phase OPS-1A — ロール / 権限（公開制御より先に評価）
 *
 * 現行: USER / ADMIN
 * 予約: OPS / DEVELOPER（将来追加。特権マトリクスのみ先に定義）
 *
 * OPS-Monitor / Result Automation とは独立（BFF ユーザー到達のみ）。
 */
export const Role = Object.freeze({
  USER: "USER",
  ADMIN: "ADMIN",
  OPS: "OPS",
  DEVELOPER: "DEVELOPER",
});

export const Privilege = Object.freeze({
  /** OPS Mode（PUBLIC/CLOSED）および maintenance_mode を迂回 */
  BYPASS_OPS_MODE: "bypass_ops_mode",
});

/** @type {Readonly<Record<string, ReadonlyArray<string>>>} */
const ROLE_PRIVILEGES = Object.freeze({
  [Role.USER]: Object.freeze([]),
  [Role.ADMIN]: Object.freeze([Privilege.BYPASS_OPS_MODE]),
  [Role.OPS]: Object.freeze([Privilege.BYPASS_OPS_MODE]),
  [Role.DEVELOPER]: Object.freeze([Privilege.BYPASS_OPS_MODE]),
});

/**
 * @param {unknown} raw
 * @returns {string}
 */
export function normalizeRole(raw) {
  const r = String(raw || Role.USER)
    .trim()
    .toUpperCase();
  if (r === "ADMINISTRATOR" || r === "ROOT") return Role.ADMIN;
  if (r === Role.ADMIN || r === Role.USER || r === Role.OPS || r === Role.DEVELOPER) {
    return r;
  }
  return Role.USER;
}

/**
 * @param {string} role
 * @returns {ReadonlyArray<string>}
 */
export function privilegesFor(role) {
  const key = normalizeRole(role);
  return ROLE_PRIVILEGES[key] || ROLE_PRIVILEGES[Role.USER];
}

/**
 * @param {string} role
 * @param {string} privilege
 */
export function hasPrivilege(role, privilege) {
  return privilegesFor(role).includes(privilege);
}

/**
 * @param {string} role
 */
export function canBypassOpsMode(role) {
  return hasPrivilege(role, Privilege.BYPASS_OPS_MODE);
}

/**
 * @param {string} role
 */
export function isPrivilegedOpsRole(role) {
  const r = normalizeRole(role);
  return r === Role.ADMIN || r === Role.OPS || r === Role.DEVELOPER;
}
