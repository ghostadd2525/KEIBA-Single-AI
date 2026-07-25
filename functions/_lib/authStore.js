/**
 * Auth 永続ストア（招待・ユーザー）
 * Cloudflare KV `EXPECT_AUTH_STORE` があれば跨 isolate で共有。
 * 未バインド時は Isolate メモリのみ（開発フォールバック）。
 */

/** @type {Map<string, string>} */
const memory = new Map();

function kv(context) {
  return (context && context.env && context.env.EXPECT_AUTH_STORE) || null;
}

/**
 * @param {any} context
 * @param {string} key
 * @returns {Promise<any|null>}
 */
export async function authStoreGet(context, key) {
  const k = String(key || "");
  if (!k) return null;
  const store = kv(context);
  if (store) {
    try {
      const raw = await store.get(k);
      if (raw == null || raw === "") return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
  const raw = memory.get(k);
  if (raw == null) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * @param {any} context
 * @param {string} key
 * @param {any} value
 * @param {{ expirationTtl?: number }} [opts]
 */
export async function authStorePut(context, key, value, opts = {}) {
  const k = String(key || "");
  if (!k) return;
  const raw = JSON.stringify(value);
  const store = kv(context);
  if (store) {
    const putOpts = {};
    if (opts.expirationTtl && Number.isFinite(opts.expirationTtl)) {
      putOpts.expirationTtl = Math.max(60, Math.floor(opts.expirationTtl));
    }
    await store.put(k, raw, putOpts);
    return;
  }
  memory.set(k, raw);
}

/**
 * @param {any} context
 * @param {string} prefix
 * @param {number} [limit]
 * @returns {Promise<string[]>}
 */
export async function authStoreListKeys(context, prefix, limit = 200) {
  const p = String(prefix || "");
  const store = kv(context);
  if (store && typeof store.list === "function") {
    try {
      const out = [];
      let cursor;
      do {
        const page = await store.list({ prefix: p, limit: Math.min(100, limit - out.length), cursor });
        for (const key of page.keys || []) {
          if (key && key.name) out.push(key.name);
        }
        cursor = page.list_complete ? undefined : page.cursor;
      } while (cursor && out.length < limit);
      return out;
    } catch {
      return [];
    }
  }
  const keys = [];
  for (const k of memory.keys()) {
    if (k.startsWith(p)) keys.push(k);
    if (keys.length >= limit) break;
  }
  return keys;
}

/** テスト用 */
export function _resetAuthStoreMemoryForTests() {
  memory.clear();
}
