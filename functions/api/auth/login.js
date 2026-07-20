/**
 * AuthService — POST /api/auth/login
 * Phase9: 正式ログイン（ログインID + パスワード）のみ。
 * 一時IDでの初回利用は POST /api/auth/invite/start → /api/auth/setup。
 */
import { writeAudit, AuditEvent } from "../../_lib/auditLog.js";
import { makeStubToken } from "../../_lib/auth.js";
import { toLoginResponse } from "../../_lib/authDomain.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { UserRepository } from "../../_lib/userRepository.js";
import { getUserState, mergeFavorites, setFavorites } from "../../_lib/userStore.js";

const ACCESS_TTL = 86400;

export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return jsonError("BAD_REQUEST", "JSON body required", 400);
  }

  const loginId = String((body && (body.id || body.login_id)) || "").trim();
  const password = String((body && body.password) || "");

  if (loginId.length < 4) {
    writeAudit(context, {
      type: AuditEvent.LOGIN_FAILURE,
      ok: false,
      actor: loginId || null,
      detail: { reason: "INVALID_ID" },
    });
    return jsonError("INVALID_ID", "ログインIDを正しく入力してください", 400);
  }
  if (!password) {
    writeAudit(context, {
      type: AuditEvent.LOGIN_FAILURE,
      ok: false,
      actor: loginId,
      detail: { reason: "PASSWORD_REQUIRED" },
    });
    return jsonError(
      "PASSWORD_REQUIRED",
      "パスワードを入力してください。初回の方は一時IDから設定を開始してください",
      400
    );
  }

  const auth = await UserRepository.authenticate(context, loginId, password);
  if (!auth.ok) {
    writeAudit(context, {
      type: AuditEvent.LOGIN_FAILURE,
      ok: false,
      actor: loginId,
      detail: { reason: auth.code },
    });
    const status = auth.code === "USER_DISABLED" ? 403 : 401;
    return jsonError(auth.code, auth.message, status);
  }

  const user = auth.user;
  let favorites = getUserState(user.user_id).favorites;
  if (body && body.favorites) {
    favorites = setFavorites(user.user_id, mergeFavorites(favorites, body.favorites));
  }

  const token = makeStubToken(user.user_id, ACCESS_TTL, { purpose: "access" });

  writeAudit(context, {
    type: AuditEvent.LOGIN_SUCCESS,
    actor: user.user_id,
  });

  return jsonOk(
    toLoginResponse(
      token,
      ACCESS_TTL,
      { id: user.user_id, display_name: user.display_name },
      favorites
    ),
    {
      source: "stub-auth",
      service: "AuthService",
      contract: "AuthLoginResponse",
      cache: "bypass",
      flow: "login",
    },
    { cacheControl: "no-store" }
  );
}
