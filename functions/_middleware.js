import { writeAudit, AuditEvent } from "./_lib/auditLog.js";
import { requireAuth } from "./_lib/auth.js";
import { getBetaConfig } from "./_lib/betaConfig.js";
import { jsonError } from "./_lib/errors.js";

const MAINTENANCE_ALLOW = new Set([
  "/api/auth/login",
  "/api/auth/logout",
  "/api/auth/me",
  "/api/auth/invite/start",
  "/api/auth/setup",
]);

export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (!url.pathname.startsWith("/api/")) {
    return context.next();
  }

  const authError = await requireAuth(context);
  if (authError) return authError;

  let beta = { maintenance_mode: false, audit: { enabled: true } };
  try {
    beta = await getBetaConfig(context);
  } catch {
    /* fail open */
  }

  if (beta.maintenance_mode && !MAINTENANCE_ALLOW.has(url.pathname)) {
    writeAudit(context, {
      type: "maintenance_block",
      ok: false,
      detail: { path: url.pathname },
    });
    return jsonError("MAINTENANCE", beta.maintenance_message || "maintenance", 503);
  }

  // 利用監査（レスポンス契約は変更しない）
  const path = url.pathname;
  const auditOn = !(beta.audit && beta.audit.enabled === false);
  if (auditOn) {
    if (path === "/api/predictions" || path.startsWith("/api/predictions/")) {
      context.data = context.data || {};
      context.data._auditPrediction = true;
    } else if (path.startsWith("/api/analysis/")) {
      context.data = context.data || {};
      context.data._auditAnalysis = true;
    } else if (path === "/api/kaoba/chat") {
      context.data = context.data || {};
      context.data._auditKaoba = true;
    }
  }

  const res = await context.next();

  try {
    if (context.data && context.data._auditPrediction && res && res.ok) {
      writeAudit(context, {
        type: AuditEvent.PREDICTION_USED,
        actor: context.data.user && context.data.user.id,
        detail: { path },
      });
    }
    if (context.data && context.data._auditAnalysis && res && res.ok) {
      writeAudit(context, {
        type: AuditEvent.ANALYSIS_USED,
        actor: context.data.user && context.data.user.id,
        detail: { path },
      });
    }
    if (context.data && context.data._auditKaoba && res && res.ok) {
      writeAudit(context, {
        type: AuditEvent.KAOBA_USED,
        actor: context.data.user && context.data.user.id,
        detail: { path },
      });
    }
  } catch {
    /* audit must not break responses */
  }

  return res;
}
