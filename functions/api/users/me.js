/**
 * User Service BFF — GET/PATCH /api/users/me
 *
 * 1) Pages UserRepository（β本番の正本）
 * 2) AI User Domain があれば同期的に反映（任意）
 *
 * PATCH で変更可: display_name / avatar_url / locale / preferences
 * 変更不可: role / user_id / login_id / password
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { getBearer, verifyStubToken } from "../../_lib/auth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { UserRepository } from "../../_lib/userRepository.js";

function unauthorized() {
  return jsonError("UNAUTHORIZED", "Bearer token required", 401);
}

function pickProfilePatch(body) {
  const out = {};
  if (!body || typeof body !== "object") return out;
  if (Object.prototype.hasOwnProperty.call(body, "display_name")) {
    out.display_name = body.display_name;
  }
  if (Object.prototype.hasOwnProperty.call(body, "avatar_url")) {
    out.avatar_url = body.avatar_url;
  }
  if (Object.prototype.hasOwnProperty.call(body, "locale")) {
    out.locale = body.locale;
  }
  if (Object.prototype.hasOwnProperty.call(body, "preferences")) {
    out.preferences = body.preferences;
  }
  // nested profile payload support
  if (body.profile && typeof body.profile === "object") {
    Object.assign(out, pickProfilePatch(body.profile));
  }
  return out;
}

export async function onRequestGet(context) {
  const token = getBearer(context.request);
  const session = verifyStubToken(token, { purpose: "access" });
  if (!session) return unauthorized();

  context.data = context.data || {};
  context.data.user = session;

  const beta = await getBetaConfig(context);
  const authz = await resolveAuthorization(context, beta);

  const local = await UserRepository.get(context, session.id);
  if (local) {
    const pub = UserRepository.toPublicUser(local);
    // allowlist / token を含む実効ロールを返す（mypage 管理者UIの正本）
    pub.role = authz.role;
    return jsonOk(pub, {
      source: "user-repository",
      service: "UserService",
      contract: "expect-user/1.0",
      authz_source: authz.source,
    });
  }

  // seed/KV に無くても allowlist 管理者なら最小プロフィールを返す
  if (authz.role === "ADMIN" || authz.role === "OPS" || authz.role === "DEVELOPER") {
    return jsonOk(
      {
        schema_version: "expect-user/1.0",
        user_id: session.id,
        login_id: session.id,
        status: "active",
        role: authz.role,
        invite_id: null,
        created_at: null,
        terms_version: null,
        terms_accepted_at: null,
        profile: {
          display_name: session.id,
          avatar_url: "",
          locale: "ja",
          preferences: {},
          updated_at: null,
        },
        subscription: null,
      },
      {
        source: "authz-fallback",
        service: "UserService",
        contract: "expect-user/1.0",
        authz_source: authz.source,
      }
    );
  }

  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, proxied.payload.meta || {});
    }
  }

  return jsonError("USER_NOT_FOUND", "ユーザーが見つかりません", 404);
}

export async function onRequestPatch(context) {
  const token = getBearer(context.request);
  const session = verifyStubToken(token, { purpose: "access" });
  if (!session) return unauthorized();

  let body = {};
  try {
    body = await context.request.json();
  } catch {
    body = {};
  }

  // 明示拒否
  if (
    body &&
    (Object.prototype.hasOwnProperty.call(body, "role") ||
      Object.prototype.hasOwnProperty.call(body, "user_id") ||
      Object.prototype.hasOwnProperty.call(body, "login_id") ||
      Object.prototype.hasOwnProperty.call(body, "password") ||
      Object.prototype.hasOwnProperty.call(body, "password_hash"))
  ) {
    return jsonError(
      "FIELD_FORBIDDEN",
      "role / ユーザーID / パスワードはこの画面から変更できません",
      400
    );
  }

  const patch = pickProfilePatch(body);
  if (!Object.keys(patch).length) {
    return jsonError("BAD_REQUEST", "更新するプロフィール項目がありません", 400);
  }

  const updated = await UserRepository.updateProfile(context, session.id, patch);
  if (!updated.ok) {
    return jsonError(updated.code, updated.message, 400);
  }

  // AI User Domain があればベストエフォート同期
  const env = getEnv(context);
  if (useAiProxy(env)) {
    try {
      await aiFetch(context, "/v1/users/me", {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify(patch),
      });
    } catch {
      /* local save は成功扱い */
    }
  }

  return jsonOk(UserRepository.toPublicUser(updated.user), {
    source: "user-repository",
    service: "UserService",
    contract: "expect-user/1.0",
  });
}
