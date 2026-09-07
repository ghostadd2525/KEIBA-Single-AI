import { writeAudit, AuditEvent } from "./_lib/auditLog.js";
import { requireAuth } from "./_lib/auth.js";
import { resolveAuthorization } from "./_lib/authorization.js";
import { getBetaConfig } from "./_lib/betaConfig.js";
import { getEnv } from "./_lib/env.js";
import { jsonError } from "./_lib/errors.js";
import { evaluateOpsAccess, resolveOpsModeDetailed } from "./_lib/opsMode.js";
import {
  evaluateProductionAuthConfig,
  PRODUCTION_AUTH_FATAL_EXEMPT,
} from "./_lib/productionAuthGuard.js";

/**
 * Phase OPS-1A — 認可フロー
 *
 * 0. Production Auth FATAL guard（stub 矛盾）
 * 1. requireAuth（認証）
 * 2. resolveAuthorization（ロール / bypass 権限）← 公開制御より先
 * 3. evaluateOpsAccess（OPS Mode PUBLIC/CLOSED）
 * 4. USER のみ CLOSED で 503。ADMIN（将来 OPS/DEVELOPER）は常時許可
 *
 * /api/health / /api/ops/monitor は exempt（OPS-Monitor 非影響）
 * Result Automation は Python 側のため本 Middleware 対象外
 */
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (!url.pathname.startsWith("/api/")) {
    return context.next();
  }

  const env = getEnv(context);
  const authCfg = evaluateProductionAuthConfig(env);
  if (authCfg.fatal && !PRODUCTION_AUTH_FATAL_EXEMPT.has(url.pathname)) {
    return jsonError(authCfg.code, authCfg.message, 503, {
      expect_env: authCfg.expect_env,
      auth_mode: authCfg.auth_mode,
      allow_stub_auth: authCfg.allow_stub_auth,
      remediation: "Set ALLOW_STUB_AUTH=1 for stub break-glass, or switch AUTH_MODE off stub with a signed verifier",
    });
  }

  const authError = await requireAuth(context);
  if (authError) return authError;

  let beta = { maintenance_mode: false, audit: { enabled: true } };
  try {
    beta = await getBetaConfig(context);
  } catch {
    /* fail open on config */
  }

  // 権限判定は公開制御より先
  const authz = await resolveAuthorization(context, beta);
  const resolved = await resolveOpsModeDetailed(beta);
  const opsMode = resolved.ops_mode;
  const access = evaluateOpsAccess({
    pathname: url.pathname,
    opsMode,
    role: authz.role,
    bypassOpsMode: authz.bypass_ops_mode,
  });

  if (!access.allow) {
    writeAudit(context, {
      type: "ops_mode_block",
      ok: false,
      actor: context.data && context.data.user && context.data.user.id,
      detail: {
        path: url.pathname,
        ops_mode: access.ops_mode,
        role: access.role,
        reason: access.reason,
        resolve_reason: resolved.reason,
      },
    });
    return jsonError(
      "OPS_CLOSED",
      beta.maintenance_message ||
        "ただいまメンテナンス中です（Research Week）。土曜 0:00（JST）以降に再度ログインしてください。",
      503
    );
  }

  if (access.reason === "role_bypass" && opsMode !== "PUBLIC") {
    writeAudit(context, {
      type: "ops_admin_bypass",
      ok: true,
      actor: context.data && context.data.user && context.data.user.id,
      detail: {
        path: url.pathname,
        ops_mode: opsMode,
        role: access.role,
        resolve_reason: resolved.reason,
      },
    });
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
