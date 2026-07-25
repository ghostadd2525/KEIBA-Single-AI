/**
 * InvitationRepository — 管理者発行の一時ID
 *
 * 正本:
 *  1) ASSETS `/data/invitations.json`（シード）
 *  2) 署名付き一時ID（跨 isolate 自己検証）
 *  3) KV `EXPECT_AUTH_STORE`（発行・activated 状態の永続）
 *  4) Isolate メモリ（開発フォールバック）
 */
import { loadAssetJson } from "./aiProxy.js";
import { authStoreGet, authStoreListKeys, authStorePut } from "./authStore.js";
import { isSignedInviteId, mintSignedInvite, resolveSignedInvite } from "./inviteToken.js";

/** @typedef {"issued"|"activated"|"disabled"|"expired"} InviteStatus */

const STATUSES = new Set(["issued", "activated", "disabled", "expired"]);

/** @type {Map<string, object>} */
const runtimeOverlay = new Map();

let seedCache = null;

function normalizeInviteId(id) {
  return String(id || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");
}

function nowIso() {
  return new Date().toISOString();
}

function inviteKvKey(id) {
  return `invite:${normalizeInviteId(id)}`;
}

function coerceInvite(raw) {
  if (!raw || typeof raw !== "object") return null;
  const invite_id = normalizeInviteId(raw.invite_id || raw.id);
  if (!invite_id) return null;
  let status = String(raw.status || "issued").toLowerCase();
  if (!STATUSES.has(status)) status = "issued";
  return {
    invite_id,
    status,
    issued_at: raw.issued_at || null,
    expires_at: raw.expires_at || null,
    activated_at: raw.activated_at || null,
    activated_user_id: raw.activated_user_id || null,
    note: raw.note || null,
  };
}

function applyExpiry(invite) {
  if (!invite) return null;
  if (invite.status === "issued" && invite.expires_at) {
    const exp = Date.parse(invite.expires_at);
    if (!Number.isNaN(exp) && exp < Date.now()) {
      return { ...invite, status: "expired" };
    }
  }
  return invite;
}

async function loadSeed(context) {
  if (seedCache) return seedCache;
  const doc = await loadAssetJson(context, "/data/invitations.json");
  const list = (doc && Array.isArray(doc.invitations) ? doc.invitations : [])
    .map(coerceInvite)
    .filter(Boolean);
  const map = new Map();
  for (const inv of list) map.set(inv.invite_id, inv);
  seedCache = map;
  return map;
}

function mergeInvite(...parts) {
  let out = null;
  for (const p of parts) {
    if (!p) continue;
    out = { ...(out || {}), ...p };
  }
  return applyExpiry(out);
}

async function persistInvite(context, invite) {
  const id = normalizeInviteId(invite.invite_id);
  runtimeOverlay.set(id, invite);
  let ttl;
  if (invite.expires_at) {
    const exp = Date.parse(invite.expires_at);
    if (!Number.isNaN(exp)) {
      // 期限後も activated 履歴を残すため +30日
      ttl = Math.max(86400, Math.ceil((exp - Date.now()) / 1000) + 30 * 86400);
    }
  }
  await authStorePut(context, inviteKvKey(id), invite, ttl ? { expirationTtl: ttl } : {});
}

/** 管理者登録済み一時IDを取得 */
export async function getInvitation(context, inviteId) {
  const id = normalizeInviteId(inviteId);
  if (!id) return null;
  const seed = await loadSeed(context);
  const fromKv = coerceInvite(await authStoreGet(context, inviteKvKey(id)));
  const fromMem = runtimeOverlay.get(id) || null;
  let signed = null;
  if (isSignedInviteId(id)) {
    signed = await resolveSignedInvite(context, id);
  }
  return mergeInvite(seed.get(id) || null, signed, fromKv, fromMem);
}

/**
 * issued のみ初回利用可。それ以外は理由コード付き。
 * @returns {{ ok: true, invite } | { ok: false, code: string, message: string }}
 */
export async function assertIssuable(context, inviteId) {
  const invite = await getInvitation(context, inviteId);
  if (!invite) {
    return { ok: false, code: "INVITE_NOT_FOUND", message: "一時IDが見つかりません" };
  }
  if (invite.status === "activated") {
    return { ok: false, code: "INVITE_ALREADY_USED", message: "この一時IDは利用済みです" };
  }
  if (invite.status === "disabled") {
    return { ok: false, code: "INVITE_DISABLED", message: "この一時IDは停止されています" };
  }
  if (invite.status === "expired") {
    return { ok: false, code: "INVITE_EXPIRED", message: "この一時IDは期限切れです" };
  }
  if (invite.status !== "issued") {
    return { ok: false, code: "INVITE_INVALID", message: "この一時IDは利用できません" };
  }
  return { ok: true, invite };
}

/** issued → activated */
export async function activateInvitation(context, inviteId, userId) {
  const check = await assertIssuable(context, inviteId);
  if (!check.ok) return check;
  const next = {
    ...check.invite,
    status: "activated",
    activated_at: nowIso(),
    activated_user_id: String(userId),
  };
  await persistInvite(context, next);
  return { ok: true, invite: next };
}

/**
 * 管理者: 一時IDを issued として登録。
 * inviteId 省略時は署名付きIDを自動発行（跨 isolate で検証可能）。
 */
export async function issueInvitation(context, inviteId, opts = {}) {
  await loadSeed(context);

  let id = normalizeInviteId(inviteId);
  let expires_at = opts.expires_at || null;
  let issued_at = nowIso();

  if (!id) {
    const days = Number(opts.expires_days);
    const safeDays = Number.isFinite(days) && days >= 1 ? Math.min(90, days) : 14;
    const minted = await mintSignedInvite(context, {
      expiresAtMs: Date.now() + safeDays * 86400000,
      issuedAtIso: issued_at,
    });
    id = minted.invite_id;
    expires_at = minted.expires_at;
    issued_at = minted.issued_at;
    // 新規 nonce のため既存チェック不要（署名だけだと issued に見える）
    const next = {
      invite_id: id,
      status: "issued",
      issued_at,
      expires_at,
      activated_at: null,
      activated_user_id: null,
      note: opts.note || null,
    };
    await persistInvite(context, next);
    return { ok: true, invite: next };
  } else if (id.length < 4) {
    return { ok: false, code: "INVALID_INVITE", message: "一時IDが不正です" };
  }

  // seed / KV / メモリ上の実体のみ衝突とみなす（署名の自己解決は除外）
  const seed = await loadSeed(context);
  const fromKv = coerceInvite(await authStoreGet(context, inviteKvKey(id)));
  const fromMem = runtimeOverlay.get(id) || null;
  const stored = mergeInvite(seed.get(id) || null, fromKv, fromMem);
  if (stored && stored.status === "issued") {
    if (opts.allow_existing) return { ok: true, invite: stored };
    return { ok: false, code: "INVITE_EXISTS", message: "この一時IDは既に発行済みです" };
  }
  if (stored && stored.status === "activated") {
    return { ok: false, code: "INVITE_ALREADY_USED", message: "利用済みの一時IDは再発行できません" };
  }

  if (!expires_at && isSignedInviteId(id)) {
    const signed = await resolveSignedInvite(context, id);
    if (signed) expires_at = signed.expires_at;
  }

  const next = {
    invite_id: id,
    status: "issued",
    issued_at,
    expires_at,
    activated_at: null,
    activated_user_id: null,
    note: opts.note || null,
  };
  await persistInvite(context, next);
  return { ok: true, invite: next };
}

/** 管理者: issued | activated → disabled */
export async function disableInvitation(context, inviteId) {
  const invite = await getInvitation(context, inviteId);
  if (!invite) {
    return { ok: false, code: "INVITE_NOT_FOUND", message: "一時IDが見つかりません" };
  }
  if (invite.status === "disabled") {
    return { ok: true, invite };
  }
  if (invite.status === "expired") {
    return { ok: false, code: "INVITE_EXPIRED", message: "期限切れの一時IDは停止不要です" };
  }
  const next = { ...invite, status: "disabled" };
  await persistInvite(context, next);
  return { ok: true, invite: next };
}

/**
 * 管理者: disabled → issued（未アクティベート）または activated（利用済み）
 */
export async function enableInvitation(context, inviteId) {
  const invite = await getInvitation(context, inviteId);
  if (!invite) {
    return { ok: false, code: "INVITE_NOT_FOUND", message: "一時IDが見つかりません" };
  }
  if (invite.status === "expired") {
    return { ok: false, code: "INVITE_EXPIRED", message: "期限切れの一時IDは有効化できません" };
  }
  if (invite.status !== "disabled") {
    return { ok: true, invite };
  }
  const next = {
    ...invite,
    status: invite.activated_user_id ? "activated" : "issued",
  };
  await persistInvite(context, next);
  return { ok: true, invite: next };
}

/** 一覧（seed ∪ overlay ∪ KV） */
export async function listInvitations(context) {
  const seed = await loadSeed(context);
  const ids = new Set([...seed.keys(), ...runtimeOverlay.keys()]);
  try {
    const keys = await authStoreListKeys(context, "invite:", 500);
    for (const k of keys) {
      const id = k.replace(/^invite:/, "");
      if (id) ids.add(normalizeInviteId(id));
    }
  } catch {
    /* ignore */
  }
  const items = [];
  for (const id of ids) {
    const inv = await getInvitation(context, id);
    if (inv) items.push(inv);
  }
  items.sort((a, b) => String(a.invite_id).localeCompare(String(b.invite_id)));
  return items;
}

/** テスト用: オーバーレイと seed キャッシュをクリア */
export function _resetInvitationRuntimeForTests() {
  runtimeOverlay.clear();
  seedCache = null;
}

/** テスト用: ASSETS なしで seed を注入 */
export function _seedInvitationsForTests(invitations) {
  const map = new Map();
  for (const raw of invitations || []) {
    const inv = coerceInvite(raw);
    if (inv) map.set(inv.invite_id, inv);
  }
  seedCache = map;
  runtimeOverlay.clear();
}

export const InvitationRepository = {
  get: getInvitation,
  list: listInvitations,
  assertIssuable,
  issue: issueInvitation,
  activate: activateInvitation,
  disable: disableInvitation,
  enable: enableInvitation,
  normalizeInviteId,
  STATUSES: [...STATUSES],
};
