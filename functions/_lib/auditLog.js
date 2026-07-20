/**
 * Phase10 — 監査ログ（JSONL 1行1イベント）
 *
 * Workers: console に JSON 1行（Logpush / wrangler tail で収集）
 * CLI / Node: logs/audit/beta-audit.jsonl へ追記可能な形（writeAuditLineLocal）
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

  // JSONL: 1行の JSON
  console.log(JSON.stringify({ audit: true, ...line }));
  return line;
}

/** Node CLI 用ファイル追記（Workers では使わない） */
export async function appendAuditJsonl(filePath, evt) {
  const { appendFileSync, mkdirSync } = await import("node:fs");
  const { dirname } = await import("node:path");
  const line = {
    ts: new Date().toISOString(),
    type: String(evt.type || "unknown"),
    ok: evt.ok !== false,
    actor: evt.actor != null ? String(evt.actor) : "cli",
    target: evt.target != null ? String(evt.target) : null,
    detail: evt.detail && typeof evt.detail === "object" ? evt.detail : {},
    source: "cli",
  };
  mkdirSync(dirname(filePath), { recursive: true });
  appendFileSync(filePath, JSON.stringify(line) + "\n", "utf8");
  return line;
}
