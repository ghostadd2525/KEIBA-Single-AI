/**
 * Admin — 一時ID（招待）発行
 * POST /api/admin/invitations  … 自動発行のみ（ID手入力なし）
 * GET  /api/admin/invitations  … 最近使用（activated）5件
 *
 * expires_days → expires_at を保存。assertIssuable 時に期限切れ判定される。
 */
import { getBearer, verifyStubToken } from "../../_lib/auth.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { InvitationRepository } from "../../_lib/invitationRepository.js";
import { UserRepository } from "../../_lib/userRepository.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { isPrivilegedOpsRole } from "../../_lib/roles.js";
import { writeAudit } from "../../_lib/auditLog.js";

function unauthorized() {
  return jsonError("UNAUTHORIZED", "login required", 401);
}

function forbidden() {
  return jsonError("FORBIDDEN", "管理者のみ一時IDを発行できます", 403);
}

async function requireAdmin(context) {
  const token = getBearer(context.request);
  const session = verifyStubToken(token, { purpose: "access" });
  if (!session) return { ok: false, response: unauthorized() };
  context.data = context.data || {};
  context.data.user = session;
  const beta = await getBetaConfig(context);
  const authz = await resolveAuthorization(context, beta);
  if (!isPrivilegedOpsRole(authz.role)) {
    return { ok: false, response: forbidden() };
  }
  const user = (await UserRepository.get(context, session.id)) || {
    user_id: session.id,
    role: authz.role,
  };
  return { ok: true, user, role: authz.role, session };
}

/** 最近使用（activated）5件。activated_at 降順 */
function recentUsed(items, limit = 5) {
  return (items || [])
    .filter((x) => x && x.status === "activated" && x.activated_at)
    .sort((a, b) => String(b.activated_at).localeCompare(String(a.activated_at)))
    .slice(0, limit);
}

export async function onRequestGet(context) {
  const gate = await requireAdmin(context);
  if (!gate.ok) return gate.response;
  const items = await InvitationRepository.list(context);
  const used = recentUsed(items, 5);
  return jsonOk(
    {
      invitations: used,
      recent_used: used,
      count: used.length,
    },
    { source: "invitation-repository", service: "AdminInvite" },
    { cacheControl: "no-store" }
  );
}

export async function onRequestPost(context) {
  const gate = await requireAdmin(context);
  if (!gate.ok) return gate.response;

  let body = {};
  try {
    body = await context.request.json();
  } catch {
    body = {};
  }

  // 手入力IDなし。署名付き一時IDを自動発行（跨 isolate で検証可能）
  let days = Number(body.expires_days);
  if (!Number.isFinite(days) || days < 1) days = 14;
  if (days > 90) days = 90;

  let issued = null;
  for (let i = 0; i < 5; i++) {
    issued = await InvitationRepository.issue(context, "", {
      note: `auto-issued by ${gate.user.user_id}`,
      expires_days: days,
    });
    if (issued.ok) break;
    if (issued.code !== "INVITE_EXISTS" && issued.code !== "INVITE_ALREADY_USED") break;
  }
  if (!issued || !issued.ok) {
    const status =
      issued && (issued.code === "INVITE_EXISTS" || issued.code === "INVITE_ALREADY_USED")
        ? 409
        : 400;
    return jsonError(
      (issued && issued.code) || "ISSUE_FAILED",
      (issued && issued.message) || "一時IDの発行に失敗しました",
      status
    );
  }

  writeAudit(context, {
    type: "invitation_issued",
    ok: true,
    actor: gate.user.user_id,
    detail: {
      invite_id: issued.invite.invite_id,
      expires_at: issued.invite.expires_at,
      expires_days: days,
    },
  });

  return jsonOk(
    {
      invite: issued.invite,
      expires_days: days,
      login_hint: "ログイン画面の「一時ID」欄に入力してください",
    },
    { source: "invitation-repository", service: "AdminInvite" },
    { cacheControl: "no-store" }
  );
}
