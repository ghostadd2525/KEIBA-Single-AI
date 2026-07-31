/**
 * POST /api/auth/setup
 * 初回設定: ログインID / パスワード / 規約同意 → 正式アカウント作成
 */
import { writeAudit, AuditEvent } from "../../_lib/auditLog.js";
import { getBearer, makeStubToken, verifyStubToken } from "../../_lib/auth.js";
import { toLoginResponse } from "../../_lib/authDomain.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { InvitationRepository } from "../../_lib/invitationRepository.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { isStrongEnoughPassword, isValidLoginId } from "../../_lib/password.js";
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

  const setupToken =
    String((body && body.setup_token) || "").trim() || getBearer(context.request);
  const setup = verifyStubToken(setupToken, { purpose: "setup" });
  if (!setup) {
    return jsonError("UNAUTHORIZED", "初回設定セッションが無効または期限切れです", 401);
  }

  const inviteId = InvitationRepository.normalizeInviteId(setup.id);
  const loginId = String((body && (body.login_id || body.id)) || "").trim();
  const password = String((body && body.password) || "");
  const termsAccepted = !!(body && (body.terms_accepted === true || body.terms_accepted === "true"));

  if (!isValidLoginId(loginId)) {
    return jsonError(
      "INVALID_LOGIN_ID",
      "ログインIDは半角英数・_・- の4〜32文字で入力してください",
      400
    );
  }
  if (!isStrongEnoughPassword(password)) {
    return jsonError("WEAK_PASSWORD", "パスワードは8文字以上にしてください", 400);
  }
  if (!termsAccepted) {
    return jsonError("TERMS_REQUIRED", "利用規約への同意が必要です", 400);
  }

  const beta = await getBetaConfig(context);
  const termsVersion = beta.terms_version || "2026-07-19";

  const issuable = await InvitationRepository.assertIssuable(context, inviteId);
  if (!issuable.ok) {
    return jsonError(issuable.code, issuable.message, 409);
  }

  const created = await UserRepository.create(context, {
    login_id: loginId,
    password,
    display_name: loginId,
    invite_id: inviteId,
    role: "USER",
    terms_version: termsVersion,
    terms_accepted_at: new Date().toISOString(),
  });
  if (!created.ok) {
    return jsonError(created.code, created.message, created.code === "LOGIN_ID_TAKEN" ? 409 : 400);
  }

  const activated = await InvitationRepository.activate(context, inviteId, loginId);
  if (!activated.ok) {
    return jsonError(activated.code, activated.message, 409);
  }

  let favorites = getUserState(loginId).favorites;
  if (body && body.favorites) {
    favorites = setFavorites(loginId, mergeFavorites(favorites, body.favorites));
  }

  const token = makeStubToken(loginId, ACCESS_TTL, {
    purpose: "access",
    role: "USER",
  });

  writeAudit(context, {
    type: AuditEvent.SETUP_COMPLETE,
    actor: loginId,
    target: inviteId,
    detail: { terms_version: termsVersion },
  });

  return jsonOk(
    toLoginResponse(
      token,
      ACCESS_TTL,
      { id: created.user.user_id, display_name: created.user.display_name },
      favorites
    ),
    {
      source: "stub-auth",
      service: "AuthService",
      contract: "AuthLoginResponse",
      cache: "bypass",
      invite_id: inviteId,
      flow: "setup",
    },
    { cacheControl: "no-store" }
  );
}
