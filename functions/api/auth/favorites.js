import { getBearer, verifyStubToken } from "../../_lib/auth.js";
import { toFavoritesResponse } from "../../_lib/authDomain.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { getUserState, mergeFavorites, setFavorites } from "../../_lib/userStore.js";

/**
 * AuthService — お気に入りサーバー同期
 * GET  /api/auth/favorites  … 取得
 * PUT  /api/auth/favorites  … localStorage から push（マージ）
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

  const incoming = body && body.favorites ? body.favorites : body;
  if (!incoming || typeof incoming !== "object") {
    return jsonError("BAD_REQUEST", "favorites object required", 400);
  }

  const merged = setFavorites(user.id, mergeFavorites(getUserState(user.id).favorites, incoming));
  return jsonOk(toFavoritesResponse(merged), meta(), { cacheControl: "no-store" });
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
