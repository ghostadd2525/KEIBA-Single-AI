/**
 * InvitationRepository — 管理者発行の一時ID
 *
 * 正本: ASSETS `/data/invitations.json`（管理者が登録）
 * 実行時の状態更新（activated 等）は Isolate メモリにオーバーレイ。
 * 将来: KV / D1 に差し替え可能なインタフェース。
 */
import { loadAssetJson } from "./aiProxy.js";

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

function mergeInvite(seed, overlay) {
  if (!seed && !overlay) return null;
  return applyExpiry({ ...(seed || {}), ...(overlay || {}) });
}

/** 管理者登録済み一時IDを取得 */
export async function getInvitation(context, inviteId) {
  const id = normalizeInviteId(inviteId);
  if (!id) return null;
  const seed = await loadSeed(context);
  return mergeInvite(seed.get(id) || null, runtimeOverlay.get(id) || null);
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
  const id = normalizeInviteId(inviteId);
  const next = {
    ...check.invite,
    status: "activated",
    activated_at: nowIso(),
    activated_user_id: String(userId),
  };
  runtimeOverlay.set(id, next);
  return { ok: true, invite: next };
}

/**
 * 管理者: 一時IDを issued として登録（ランタイム）。
 * 永続化は ASSETS JSON への追記（scripts/issue-invite.mjs）と併用。
 */
export async function issueInvitation(context, inviteId, opts = {}) {
  await loadSeed(context);
  const id = normalizeInviteId(inviteId);
  if (id.length < 4) {
    return { ok: false, code: "INVALID_INVITE", message: "一時IDが不正です" };
  }
  const existing = await getInvitation(context, id);
  if (existing && existing.status === "issued") {
    return { ok: false, code: "INVITE_EXISTS", message: "この一時IDは既に発行済みです" };
  }
  if (existing && existing.status === "activated") {
    return { ok: false, code: "INVITE_ALREADY_USED", message: "利用済みの一時IDは再発行できません" };
  }
  const next = {
    invite_id: id,
    status: "issued",
    issued_at: nowIso(),
    expires_at: opts.expires_at || null,
    activated_at: null,
    activated_user_id: null,
    note: opts.note || null,
  };
  runtimeOverlay.set(id, next);
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
  const id = normalizeInviteId(inviteId);
  const next = { ...invite, status: "disabled" };
  runtimeOverlay.set(id, next);
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
  const id = normalizeInviteId(inviteId);
  const next = {
    ...invite,
    status: invite.activated_user_id ? "activated" : "issued",
  };
  runtimeOverlay.set(id, next);
  return { ok: true, invite: next };
}

/** 一覧（seed ∪ overlay） */
export async function listInvitations(context) {
  const seed = await loadSeed(context);
  const ids = new Set([...seed.keys(), ...runtimeOverlay.keys()]);
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
