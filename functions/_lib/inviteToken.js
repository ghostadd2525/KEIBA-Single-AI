/**
 * 自己検証可能な一時ID（跨 isolate でも INVITE_NOT_FOUND にならない）
 *
 * 形式: TMP-{expHex}-{nonceHex}-{sigHex}  （すべて大文字 hex）
 * 署名: HMAC-SHA256(secret, "TMP|{exp}|{nonce}") の先頭 12 hex
 */
import { getEnv } from "./env.js";

const PREFIX = "TMP-";

function signingSecret(context) {
  const env = (context && context.env) || {};
  const fromEnv =
    String(env.INVITE_SIGNING_SECRET || "").trim() ||
    String(getEnv(context).AI_API_KEY || "").trim();
  // 全 isolate で同一であること。本番では INVITE_SIGNING_SECRET / AI_API_KEY を設定。
  return fromEnv || "expect-invite-hmac-v1";
}

function toHex(buf) {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}

function randomNonceHex(bytes = 4) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return toHex(a);
}

/**
 * @param {string} secret
 * @param {string} expHex
 * @param {string} nonceHex
 */
async function signPart(secret, expHex, nonceHex) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const msg = `TMP|${expHex}|${nonceHex}`;
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  return toHex(sig).slice(0, 12);
}

/**
 * @param {string} inviteId
 * @returns {{ expHex: string, nonceHex: string, sigHex: string } | null}
 */
export function parseSignedInviteId(inviteId) {
  const id = String(inviteId || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");
  if (!id.startsWith(PREFIX)) return null;
  const parts = id.slice(PREFIX.length).split("-");
  if (parts.length !== 3) return null;
  const [expHex, nonceHex, sigHex] = parts;
  if (!/^[0-9A-F]{1,16}$/.test(expHex)) return null;
  if (!/^[0-9A-F]{8}$/.test(nonceHex)) return null;
  if (!/^[0-9A-F]{12}$/.test(sigHex)) return null;
  return { expHex, nonceHex, sigHex };
}

export function isSignedInviteId(inviteId) {
  return Boolean(parseSignedInviteId(inviteId));
}

/**
 * @param {any} context
 * @param {{ expiresAtMs: number, issuedAtIso?: string }} opts
 * @returns {Promise<{ invite_id: string, expires_at: string, issued_at: string }>}
 */
export async function mintSignedInvite(context, opts) {
  const expiresAtMs = Number(opts.expiresAtMs);
  const expSec = Math.floor(expiresAtMs / 1000);
  const expHex = expSec.toString(16).toUpperCase();
  const nonceHex = randomNonceHex(4);
  const sigHex = await signPart(signingSecret(context), expHex, nonceHex);
  const invite_id = `${PREFIX}${expHex}-${nonceHex}-${sigHex}`;
  const issued_at = opts.issuedAtIso || new Date().toISOString();
  return {
    invite_id,
    expires_at: new Date(expiresAtMs).toISOString(),
    issued_at,
  };
}

/**
 * 署名検証に成功したら invite レコード相当を返す（status は issued。期限切れは呼び出し側で判定）
 * @returns {Promise<object|null>}
 */
export async function resolveSignedInvite(context, inviteId) {
  const parsed = parseSignedInviteId(inviteId);
  if (!parsed) return null;
  const expectSig = await signPart(signingSecret(context), parsed.expHex, parsed.nonceHex);
  if (expectSig !== parsed.sigHex) return null;
  const expSec = parseInt(parsed.expHex, 16);
  if (!Number.isFinite(expSec) || expSec <= 0) return null;
  const expires_at = new Date(expSec * 1000).toISOString();
  const id = String(inviteId)
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");
  return {
    invite_id: id,
    status: "issued",
    issued_at: null,
    expires_at,
    activated_at: null,
    activated_user_id: null,
    note: "signed-invite",
  };
}
