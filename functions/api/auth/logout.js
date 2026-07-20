import { getBearer, verifyStubToken } from "../../_lib/auth.js";
import { toLogoutResponse } from "../../_lib/authDomain.js";
import { jsonOk } from "../../_lib/errors.js";
import { clearSessionSideEffects, mergeFavorites, setFavorites } from "../../_lib/userStore.js";

/**
 * AuthService — POST /api/auth/logout
 * 任意: body.favorites を最終同期してからログアウト応答
 */
export async function onRequestPost(context) {
  const token = getBearer(context.request);
  const user = token ? verifyStubToken(token) : null;

  let body = null;
  try {
    body = await context.request.json();
  } catch {
    body = null;
  }

  if (user && body && body.favorites) {
    setFavorites(user.id, mergeFavorites(null, body.favorites));
  }
  if (user) clearSessionSideEffects(user.id);

  return jsonOk(toLogoutResponse(), {
    source: "stub-auth",
    service: "AuthService",
    contract: "AuthLogoutResponse",
    cache: "bypass",
  }, { cacheControl: "no-store" });
}
