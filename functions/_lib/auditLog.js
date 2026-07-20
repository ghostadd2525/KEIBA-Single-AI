/**
 * Phase10 — 監査ログ（JSONL 1行1イベント）
 *
 * Workers: console に JSON 1行（Logpush / wrangler tail で収集）
 * CLI ファイル追記は scripts/beta-admin.mjs 側で実施（node:fs を Functions にバンドルしない）
 */

export const AuditEvent = {
  LOGIN_SUCCESS: "login_success",
  LOGIN_FAILURE: "login_failure",
  INVITATION_USED: "invitation_used",
  SETUP_COMPLETE: "setup_complete",
  ACCOUNT_DISABLED: "account_disabled",
  ACCOUNT_ENABLED: "account_enabled",
  INVITATION_ISSUED: "invitation_issued",
  INVITATION_DISABLED: "invitation_disabled",
  INVITATION_ENABLED: "invitation_enabled",
  PREDICTION_USED: "prediction_used",
  ANALYSIS_USED: "analysis_used",
  KAOBA_USED: "kaoba_used",
  PASSWORD_RESET: "password_reset",
};

/**
 * @param {object} [context]
 * @param {{ type: string, actor?: string|null, target?: string|null, ok?: boolean, detail?: object }} evt
 */
export function writeAudit(context, evt) {
  const line = {
    ts: new Date().toISOString(),
    type: String(evt.type || "unknown"),
    ok: evt.ok !== false,
    actor: evt.actor != null ? String(evt.actor) : null,
    target: evt.target != null ? String(evt.target) : null,
    detail: evt.detail && typeof evt.detail === "object" ? evt.detail : {},
    request_id:
      (context &&
        context.request &&
        context.request.headers &&
        (context.request.headers.get("cf-ray") || context.request.headers.get("x-request-id"))) ||
      null,
  };

  console.log(JSON.stringify({ audit: true, ...line }));
  return line;
}

/**
 * CLI 向けプレースホルダ（Workers では呼ばない）。
 * ファイル追記が必要な場合は scripts/beta-admin.mjs の audit() を使う。
 */
export async function appendAuditJsonl(_filePath, evt) {
  return writeAudit(null, { ...evt, actor: evt.actor != null ? evt.actor : "cli" });
}
