/**
 * UserRepository — 正式アカウント
 *
 * Seed: ASSETS `/data/users.json`
 * 新規作成（setup）は Isolate メモリに保持。
 * 将来: KV / D1 差し替え。
 */
import { loadAssetJson } from "./aiProxy.js";
import { hashPassword, verifyPassword } from "./password.js";

/** @type {Map<string, object>} */
const runtimeUsers = new Map();

let seedLoaded = false;

function normalizeUserId(id) {
  return String(id || "").trim();
}

function coerceUser(raw) {
  if (!raw || typeof raw !== "object") return null;
  const user_id = normalizeUserId(raw.user_id || raw.id);
  if (!user_id) return null;
  const roleRaw = raw.role != null ? String(raw.role) : "USER";
  return {
    user_id,
    password_hash: raw.password_hash || "",
    display_name: raw.display_name != null ? String(raw.display_name) : user_id,
    invite_id: raw.invite_id ? String(raw.invite_id).toUpperCase() : null,
    status: String(raw.status || "active").toLowerCase(),
    role: String(roleRaw).trim().toUpperCase() || "USER",
    created_at: raw.created_at || null,
    terms_version: raw.terms_version || null,
    terms_accepted_at: raw.terms_accepted_at || null,
  };
}

async function ensureSeed(context) {
  if (seedLoaded) return;
  try {
    const doc = await loadAssetJson(context, "/data/users.json");
    const list = (doc && Array.isArray(doc.users) ? doc.users : []).map(coerceUser).filter(Boolean);
    for (const u of list) {
      if (!runtimeUsers.has(u.user_id)) runtimeUsers.set(u.user_id, u);
    }
  } catch {
    /* ASSETS 未設定・テスト環境では空 seed で続行 */
  }
  seedLoaded = true;
}

export async function getUser(context, userId) {
  await ensureSeed(context);
  const id = normalizeUserId(userId);
  return runtimeUsers.get(id) || null;
}

export async function findUserByLoginId(context, loginId) {
  return getUser(context, loginId);
}

/**
 * @returns {{ ok: true, user } | { ok: false, code: string, message: string }}
 */
export async function createUser(context, input) {
  await ensureSeed(context);
  const user_id = normalizeUserId(input.login_id || input.user_id);
  if (!user_id) {
    return { ok: false, code: "INVALID_LOGIN_ID", message: "ログインIDが不正です" };
  }
  if (runtimeUsers.has(user_id)) {
    return { ok: false, code: "LOGIN_ID_TAKEN", message: "このログインIDは既に使われています" };
  }

  const password_hash = await hashPassword(String(input.password || ""));
  const user = {
    user_id,
    password_hash,
    display_name: input.display_name != null ? String(input.display_name) : user_id,
    invite_id: input.invite_id ? String(input.invite_id).toUpperCase() : null,
    status: "active",
    role: String(input.role || "USER").trim().toUpperCase() || "USER",
    created_at: new Date().toISOString(),
    terms_version: input.terms_version || null,
    terms_accepted_at: input.terms_accepted_at || new Date().toISOString(),
  };
  runtimeUsers.set(user_id, user);
  return { ok: true, user };
}

/**
 * @returns {{ ok: true, user } | { ok: false, code: string, message: string }}
 */
export async function authenticate(context, loginId, password) {
  const user = await findUserByLoginId(context, loginId);
  if (!user) {
    return { ok: false, code: "INVALID_CREDENTIALS", message: "ログインIDまたはパスワードが違います" };
  }
  if (user.status !== "active") {
    return { ok: false, code: "USER_DISABLED", message: "このアカウントは利用停止中です" };
  }
  const ok = await verifyPassword(password, user.password_hash);
  if (!ok) {
    return { ok: false, code: "INVALID_CREDENTIALS", message: "ログインIDまたはパスワードが違います" };
  }
  return { ok: true, user };
}

/**
 * @returns {{ ok: true, user } | { ok: false, code: string, message: string }}
 */
export async function setUserStatus(context, userId, status) {
  await ensureSeed(context);
  const id = normalizeUserId(userId);
  const user = runtimeUsers.get(id);
  if (!user) {
    return { ok: false, code: "USER_NOT_FOUND", message: "ユーザーが見つかりません" };
  }
  const nextStatus = String(status || "").toLowerCase();
  if (nextStatus !== "active" && nextStatus !== "disabled") {
    return { ok: false, code: "INVALID_STATUS", message: "status は active または disabled" };
  }
  const next = { ...user, status: nextStatus };
  runtimeUsers.set(id, next);
  return { ok: true, user: next };
}

/**
 * @returns {{ ok: true, user } | { ok: false, code: string, message: string }}
 */
export async function setPassword(context, userId, password) {
  await ensureSeed(context);
  const id = normalizeUserId(userId);
  const user = runtimeUsers.get(id);
  if (!user) {
    return { ok: false, code: "USER_NOT_FOUND", message: "ユーザーが見つかりません" };
  }
  if (String(password || "").length < 8) {
    return { ok: false, code: "WEAK_PASSWORD", message: "パスワードは8文字以上にしてください" };
  }
  const password_hash = await hashPassword(String(password));
  const next = { ...user, password_hash };
  runtimeUsers.set(id, next);
  return { ok: true, user: next };
}

export async function listUsers(context) {
  await ensureSeed(context);
  return [...runtimeUsers.values()].sort((a, b) => a.user_id.localeCompare(b.user_id));
}

/** CLI / テスト: seed 読込後にメモリユーザーを丸ごと置換書き出し用に取得 */
export function _dumpUsersForPersist() {
  return [...runtimeUsers.values()];
}

export function _upsertUserForPersist(user) {
  const u = coerceUser(user);
  if (u) runtimeUsers.set(u.user_id, u);
  seedLoaded = true;
}

export function _resetUserRuntimeForTests() {
  runtimeUsers.clear();
  seedLoaded = false;
}

export const UserRepository = {
  get: getUser,
  findByLoginId: findUserByLoginId,
  create: createUser,
  authenticate,
  setStatus: setUserStatus,
  setPassword,
  list: listUsers,
};
