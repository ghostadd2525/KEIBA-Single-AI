/**
 * POST /api/auth/invite/start
 * 一時ID検証 → 初回設定用 setup_token 発行
 */
import { writeAudit, AuditEvent } from "../../../_lib/auditLog.js";
import { makeStubToken } from "../../../_lib/auth.js";
import { InvitationRepository } from "../../../_lib/invitationRepository.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";

const SETUP_TTL = 1800; // 30 min

export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return jsonError("BAD_REQUEST", "JSON body required", 400);
  }

  const inviteId = InvitationRepository.normalizeInviteId(
    (body && (body.invite_id || body.id || body.temp_id)) || ""
  );
  if (inviteId.length < 4) {
    return jsonError("INVALID_INVITE", "一時IDを正しく入力してください", 400);
  }

  const check = await InvitationRepository.assertIssuable(context, inviteId);
  if (!check.ok) {
    writeAudit(context, {
      type: AuditEvent.INVITATION_USED,
      ok: false,
      target: inviteId,
      detail: { reason: check.code },
    });
    const status =
      check.code === "INVITE_NOT_FOUND"
        ? 404
        : check.code === "INVITE_ALREADY_USED" || check.code === "INVITE_DISABLED"
          ? 409
          : 400;
    return jsonError(check.code, check.message, status);
  }

  const setup_token = makeStubToken(inviteId, SETUP_TTL, { purpose: "setup" });

  writeAudit(context, {
    type: AuditEvent.INVITATION_USED,
    target: inviteId,
    detail: { next: "setup" },
  });

  return jsonOk(
    {
      schema_version: "expect-auth/1.0",
      invite_id: inviteId,
      setup_token,
      token_type: "bearer",
      expires_in: SETUP_TTL,
      next: "setup",
    },
    {
      source: "stub-auth",
      service: "AuthService",
      contract: "AuthInviteStartResponse",
      cache: "bypass",
    },
    { cacheControl: "no-store" }
  );
}
