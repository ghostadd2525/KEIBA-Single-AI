import { getBearer, verifyStubToken } from "../../_lib/auth.js";
import { toFavoritesResponse } from "../../_lib/authDomain.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import {
  applyFavoriteOp,
  applyFavoriteOps,
  getUserState,
} from "../../_lib/userStore.js";

/**
 * AuthService — お気に入りサーバー同期
 * GET  /api/auth/favorites  … 取得
 * PUT  /api/auth/favorites  … intent op 適用（add / remove）
 *
 * PUT body（いずれか）:
 *   { "op": "add"|"remove", "race_id": "...", "item"?: {...} }
 *   { "ops": [ { "op": "...", "race_id": "..." }, ... ] }
 *
 * フルリスト置換（favorites: { items }）は拒否する。
 * stale client が未知の server favorite を消さないため。
 * ログイン/setup の結合は login.js / setup.js の mergeFavorites を維持。
 * UserService POST /v1/favorites の add/remove 意味論に揃える。
 */
export async function onRequestGet(context) {
  const user = requireUser(context);
  if (user instanceof Response) return user;
  return jsonOk(toFavoritesResponse(getUserState(user.id).favorites), meta(), {
    cacheControl: "no-store",
  });
}

export async function onRequestPut(context) {
  const user = requireUser(context);
  if (user instanceof Response) return user;

  let body;
  try {
    body = await context.request.json();
  } catch {
    return jsonError("BAD_REQUEST", "JSON body required", 400);
  }

  if (!body || typeof body !== "object") {
    return jsonError("BAD_REQUEST", "JSON object required", 400);
  }

  // 旧フルリスト置換はデータロスト源のため拒否
  if (looksLikeFullReplace(body)) {
    return jsonError(
      "BAD_REQUEST",
      "full favorites replace is not allowed; use op/ops add|remove",
      400
    );
  }

  try {
    let next;
    if (Array.isArray(body.ops)) {
      if (!body.ops.length) {
        return jsonError("BAD_REQUEST", "ops must be non-empty", 400);
      }
      next = applyFavoriteOps(user.id, body.ops);
    } else if (body.op || body.action) {
      next = applyFavoriteOp(user.id, body);
    } else {
      return jsonError(
        "BAD_REQUEST",
        'favorites write requires { op: "add"|"remove", race_id } or { ops: [...] }',
        400
      );
    }
    return jsonOk(toFavoritesResponse(next), meta(), { cacheControl: "no-store" });
  } catch (err) {
    return jsonError("BAD_REQUEST", err && err.message ? err.message : "invalid op", 400);
  }
}

function looksLikeFullReplace(body) {
  if (body.favorites && typeof body.favorites === "object" && !body.op && !body.ops) {
    return true;
  }
  if (Array.isArray(body.items) || Array.isArray(body.race_ids)) {
    return true;
  }
  if (body.schema_version && (body.items || body.race_ids) && !body.op && !body.ops) {
    return true;
  }
  return false;
}

function requireUser(context) {
  const token = getBearer(context.request);
  const user = verifyStubToken(token, { purpose: "access" });
  if (!user) return jsonError("UNAUTHORIZED", "login required", 401);
  return user;
}

function meta() {
  return {
    source: "stub-auth",
    service: "AuthService",
    contract: "AuthFavoritesResponse",
    cache: "bypass",
  };
}
