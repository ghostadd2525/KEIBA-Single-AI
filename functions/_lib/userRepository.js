/**
 * UserRepository — 正式アカウント
 *
 * Seed: ASSETS `/data/users.json`
 * 新規作成（setup）は KV `EXPECT_AUTH_STORE` に永続（未バインド時は Isolate メモリ）。
 */
import { loadAssetJson } from "./aiProxy.js";
import { authStoreGet, authStorePut } from "./authStore.js";
import { hashPassword, verifyPassword } from "./password.js";

/** @type {Map<string, object>} */
const runtimeUsers = new Map();

let seedLoaded = false;

function userKvKey(id) {
  return `user:${normalizeUserId(id)}`;
}

async function persistUser(context, user) {
  runtimeUsers.set(user.user_id, user);
  await authStorePut(context, userKvKey(user.user_id), user);
}

function normalizeUserId(id) {
  return String(id || "").trim();
}

function coerceUser(raw) {
  if (!raw || typeof raw !== "object") return null;
  const user_id = normalizeUserId(raw.user_id || raw.id);
  if (!user_id) return null;
  const roleRaw = raw.role != null ? String(raw.role) : "USER";
  let preferences = {};
  if (raw.preferences && typeof raw.preferences === "object") {
    preferences = { ...raw.preferences };
  } else if (raw.preferences_json) {
    try {
      preferences = JSON.parse(String(raw.preferences_json)) || {};
    } catch {
      preferences = {};
    }
  }
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
    // profiles テーブル相当（role / user_id / password は別管理）
    avatar_url: raw.avatar_url != null ? String(raw.avatar_url) : "",
    locale: raw.locale != null ? String(raw.locale) : "ja",
    preferences,
    updated_at: raw.updated_at || null,
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
  if (!id) return null;
  const seeded = runtimeUsers.get(id) || null;
  const fromKv = coerceUser(await authStoreGet(context, userKvKey(id)));
  if (seeded) {
    // users.json の role / password を正本にする（KV の古い USER で ADMIN を潰さない）
    if (fromKv) {
      const merged = {
        ...fromKv,
        ...seeded,
        avatar_url: fromKv.avatar_url || seeded.avatar_url || "",
        locale: fromKv.locale || seeded.locale || "ja",
        preferences: fromKv.preferences || seeded.preferences || {},
        display_name: fromKv.display_name || seeded.display_name,
        updated_at: fromKv.updated_at || seeded.updated_at,
      };
      runtimeUsers.set(id, merged);
      return merged;
    }
    return seeded;
  }
  if (fromKv) {
    runtimeUsers.set(id, fromKv);
    return fromKv;
  }
  return null;
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
  const existing = await getUser(context, user_id);
  if (existing) {
    return { ok: false, code: "LOGIN_ID_TAKEN", message: "このログインIDは既に使われています" };
  }

  const password_hash = await hashPassword(String(input.password || ""));
  const user = {
    user_id,
    password_hash,
    display_name: input.display_name != null ? String(input.display_name) : user_id,
    invite_id: input.invite_id ? String(input.invite_id).toUpperCase() : null,
    status: "active",
    // 一時ID経由の正式アカウントは常に USER（管理者昇格は別経路）
    role: "USER",
    created_at: new Date().toISOString(),
    terms_version: input.terms_version || null,
    terms_accepted_at: input.terms_accepted_at || new Date().toISOString(),
    avatar_url: "",
    locale: "ja",
    preferences: {},
    updated_at: new Date().toISOString(),
  };
  await persistUser(context, user);
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
  const user = await getUser(context, id);
  if (!user) {
    return { ok: false, code: "USER_NOT_FOUND", message: "ユーザーが見つかりません" };
  }
  const nextStatus = String(status || "").toLowerCase();
  if (nextStatus !== "active" && nextStatus !== "disabled") {
    return { ok: false, code: "INVALID_STATUS", message: "status は active または disabled" };
  }
  const next = { ...user, status: nextStatus };
  await persistUser(context, next);
  return { ok: true, user: next };
}

/**
 * @returns {{ ok: true, user } | { ok: false, code: string, message: string }}
 */
export async function setPassword(context, userId, password) {
  await ensureSeed(context);
  const id = normalizeUserId(userId);
  const user = await getUser(context, id);
  if (!user) {
    return { ok: false, code: "USER_NOT_FOUND", message: "ユーザーが見つかりません" };
  }
  if (String(password || "").length < 8) {
    return { ok: false, code: "WEAK_PASSWORD", message: "パスワードは8文字以上にしてください" };
  }
  const password_hash = await hashPassword(String(password));
  const next = { ...user, password_hash };
  await persistUser(context, next);
  return { ok: true, user: next };
}

/**
 * プロフィール更新（profiles 相当）。
 * 変更不可: role / user_id / password_hash
 * @returns {{ ok: true, user } | { ok: false, code: string, message: string }}
 */
export async function updateProfile(context, userId, fields = {}) {
  await ensureSeed(context);
  const id = normalizeUserId(userId);
  const user = await getUser(context, id);
  if (!user) {
    return { ok: false, code: "USER_NOT_FOUND", message: "ユーザーが見つかりません" };
  }

  const next = { ...user };
  if (Object.prototype.hasOwnProperty.call(fields, "display_name")) {
    const name = String(fields.display_name ?? "").trim();
    if (!name) {
      return { ok: false, code: "INVALID_DISPLAY_NAME", message: "表示名を入力してください" };
    }
    if (name.length > 40) {
      return { ok: false, code: "INVALID_DISPLAY_NAME", message: "表示名は40文字以内にしてください" };
    }
    next.display_name = name;
  }
  if (Object.prototype.hasOwnProperty.call(fields, "avatar_url")) {
    const url = String(fields.avatar_url ?? "").trim();
    if (url && !/^https?:\/\//i.test(url) && !url.startsWith("/") && !url.startsWith("assets/")) {
      return { ok: false, code: "INVALID_AVATAR_URL", message: "アバターURLの形式が不正です" };
    }
    next.avatar_url = url;
  }
  if (Object.prototype.hasOwnProperty.call(fields, "locale")) {
    const locale = String(fields.locale ?? "ja").trim() || "ja";
    if (!/^[a-z]{2}(-[A-Z]{2})?$/.test(locale)) {
      return { ok: false, code: "INVALID_LOCALE", message: "locale は ja / en 形式で指定してください" };
    }
    next.locale = locale;
  }
  if (Object.prototype.hasOwnProperty.call(fields, "preferences")) {
    const prefs = fields.preferences;
    if (prefs == null || typeof prefs !== "object" || Array.isArray(prefs)) {
      return { ok: false, code: "INVALID_PREFERENCES", message: "preferences はオブジェクトで指定してください" };
    }
    next.preferences = { ...prefs };
  }
  next.updated_at = new Date().toISOString();
  await persistUser(context, next);
  return { ok: true, user: next };
}

export function toPublicUser(user) {
  if (!user) return null;
  return {
    schema_version: "expect-user/1.0",
    user_id: user.user_id,
    login_id: user.user_id,
    status: user.status,
    role: user.role,
    invite_id: user.invite_id,
    created_at: user.created_at,
    terms_version: user.terms_version,
    terms_accepted_at: user.terms_accepted_at,
    profile: {
      display_name: user.display_name,
      avatar_url: user.avatar_url || "",
      locale: user.locale || "ja",
      preferences: user.preferences || {},
      updated_at: user.updated_at || null,
    },
    subscription: null,
  };
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
  updateProfile,
  toPublicUser,
  list: listUsers,
};
