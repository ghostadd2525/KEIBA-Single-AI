/**
 * β用パスワードハッシュ（Web Crypto SHA-256）。
 * 将来 Argon2 / bcrypt 等へ差し替え可能な形式: sha256$<salt>$<hex>
 */

const DEFAULT_SALT = "expect-beta-v1";

function toHex(buffer) {
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function hashPassword(password, salt = DEFAULT_SALT) {
  const raw = String(salt) + ":" + String(password);
  const data = new TextEncoder().encode(raw);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return `sha256$${salt}$${toHex(digest)}`;
}

export async function verifyPassword(password, stored) {
  if (!stored || typeof stored !== "string") return false;
  const parts = stored.split("$");
  if (parts.length !== 3 || parts[0] !== "sha256") return false;
  const salt = parts[1];
  const expected = await hashPassword(password, salt);
  return expected === stored;
}

export function isStrongEnoughPassword(password) {
  const p = String(password || "");
  return p.length >= 8;
}

export function isValidLoginId(loginId) {
  const id = String(loginId || "").trim();
  // 4–32: 英数・_・-
  return /^[A-Za-z0-9_-]{4,32}$/.test(id);
}
