/**
 * Auth stub 用ユーザー状態（Isolate 内メモリ）
 * 本番では DB / KV に置換。favorites 同期の構造を先に固定する。
 */

const FAV_SCHEMA = "expect-favorites/1.0";

/** @type {Map<string, { favorites: object }>} */
const users = new Map();

export function emptyFavorites() {
  return {
    schema_version: FAV_SCHEMA,
    race_ids: [],
    items: [],
    synced_at: null,
  };
}

export function normalizeFavorites(raw) {
  if (!raw || typeof raw !== "object") return emptyFavorites();
  const items = Array.isArray(raw.items) ? raw.items : [];
  const normalized = [];
  const seen = new Set();
  for (const it of items) {
    if (!it || typeof it !== "object") continue;
    const raceId = String(it.race_id || it.id || "").trim();
    if (!raceId || seen.has(raceId)) continue;
    seen.add(raceId);
    normalized.push({
      race_id: raceId,
      place: it.place != null ? String(it.place) : null,
      name: it.name != null ? String(it.name) : null,
      badge: it.badge != null ? String(it.badge) : null,
      post_time: it.post_time != null ? String(it.post_time) : it.postTime != null ? String(it.postTime) : null,
      date_label:
        it.date_label != null
          ? String(it.date_label)
          : it.dateLabel != null
            ? String(it.dateLabel)
            : null,
      added_at: typeof it.added_at === "number" ? it.added_at : typeof it.addedAt === "number" ? it.addedAt : Date.now(),
    });
    if (normalized.length >= 3) break;
  }
  const raceIds = Array.isArray(raw.race_ids) && raw.race_ids.length
    ? raw.race_ids.map(String).filter((id) => seen.has(id) || normalized.some((x) => x.race_id === id)).slice(0, 3)
    : normalized.map((x) => x.race_id);
  return {
    schema_version: FAV_SCHEMA,
    race_ids: raceIds.length ? raceIds : normalized.map((x) => x.race_id),
    items: normalized,
    synced_at: raw.synced_at || new Date().toISOString(),
  };
}

/** サーバー既存とクライアント送信をマージ（新しい added_at 優先、最大3） */
export function mergeFavorites(serverFav, clientFav) {
  const a = normalizeFavorites(serverFav).items;
  const b = normalizeFavorites(clientFav).items;
  const map = new Map();
  [...a, ...b].forEach((it) => {
    const prev = map.get(it.race_id);
    if (!prev || (it.added_at || 0) >= (prev.added_at || 0)) {
      map.set(it.race_id, it);
    }
  });
  const merged = Array.from(map.values())
    .sort((x, y) => (y.added_at || 0) - (x.added_at || 0))
    .slice(0, 3);
  return normalizeFavorites({ items: merged, race_ids: merged.map((x) => x.race_id) });
}

/**
 * Intent op をサーバー最新状態へ適用（フルリスト上書き禁止の正本経路）。
 * op: "add" | "remove"
 */
export function applyFavoriteOp(userId, opInput) {
  const op = opInput && typeof opInput === "object" ? opInput : {};
  const kind = String(op.op || op.action || "")
    .trim()
    .toLowerCase();
  const raceId = String(op.race_id || op.id || (op.item && (op.item.race_id || op.item.id)) || "").trim();
  if (!raceId) {
    throw new Error("race_id required");
  }
  if (kind !== "add" && kind !== "remove") {
    throw new Error('op must be "add" or "remove"');
  }

  const current = normalizeFavorites(getUserState(userId).favorites);
  let items = current.items.slice();

  if (kind === "remove") {
    items = items.filter((it) => it.race_id !== raceId);
  } else {
    const src = op.item && typeof op.item === "object" ? op.item : op;
    const nextItem = {
      race_id: raceId,
      place: src.place != null ? String(src.place) : null,
      name: src.name != null ? String(src.name) : null,
      badge: src.badge != null ? String(src.badge) : null,
      post_time:
        src.post_time != null
          ? String(src.post_time)
          : src.postTime != null
            ? String(src.postTime)
            : null,
      date_label:
        src.date_label != null
          ? String(src.date_label)
          : src.dateLabel != null
            ? String(src.dateLabel)
            : null,
      added_at:
        typeof src.added_at === "number"
          ? src.added_at
          : typeof src.addedAt === "number"
            ? src.addedAt
            : Date.now(),
    };
    items = items.filter((it) => it.race_id !== raceId);
    items.push(nextItem);
    items = items
      .sort((x, y) => (y.added_at || 0) - (x.added_at || 0))
      .slice(0, 3);
  }

  return setFavorites(userId, {
    items,
    race_ids: items.map((x) => x.race_id),
  });
}

/** 複数 intent を順にサーバー最新へ適用 */
export function applyFavoriteOps(userId, ops) {
  const list = Array.isArray(ops) ? ops : [];
  let last = getUserState(userId).favorites;
  for (const op of list) {
    last = applyFavoriteOp(userId, op);
  }
  return normalizeFavorites(last);
}

export function getUserState(userId) {
  const id = String(userId || "");
  if (!id) return { favorites: emptyFavorites() };
  if (!users.has(id)) {
    users.set(id, { favorites: emptyFavorites() });
  }
  return users.get(id);
}

export function setFavorites(userId, favorites) {
  const state = getUserState(userId);
  state.favorites = normalizeFavorites(favorites);
  users.set(String(userId), state);
  return state.favorites;
}

/** テスト用: Isolate 内メモリを空にする */
export function __resetUserStoreForTests() {
  users.clear();
}

export function clearSessionSideEffects(/* userId */) {
  // stub: トークン無効化はクライアント側。サーバー状態は残す（再ログインで復元）
  return true;
}
