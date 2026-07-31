/**
 * GET /api/health — BFF Liveness（認証不要）
 *
 * 軽量応答。詳細プローブは GET /api/ops/monitor
 * Phase OPS-Hardening: result_automation 要約を Python /health 経由で添付（失敗時は null）
 * Version 2 Ops Phase 1: PI 状態を additive 添付（契約フィールド追加・既存キー非破壊）
 */
import { aiFetch } from "../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../_lib/env.js";
import { jsonError, jsonOk } from "../_lib/errors.js";
import { piFetchStatus, usePiProxy } from "../_lib/piProxy.js";
import { evaluateProductionAuthConfig } from "../_lib/productionAuthGuard.js";

async function probePiSummary(context, env) {
  if (!usePiProxy(env)) {
    return {
      configured: false,
      ok: null,
      status: "skipped",
      latency_ms: 0,
    };
  }
  const start = Date.now();
  try {
    const result = await Promise.race([
      piFetchStatus(context, "/health"),
      new Promise(function (_, reject) {
        setTimeout(function () {
          reject(new Error("pi health probe timeout"));
        }, 3000);
      }),
    ]);
    const latency = Date.now() - start;
    const payload =
      result && result.payload && result.payload.data != null
        ? result.payload.data
        : result && result.payload;
    const statusOk =
      result &&
      result.ok &&
      payload &&
      (payload.status === "ok" || payload.status === "healthy" || payload.ok === true);
    return {
      configured: true,
      ok: !!statusOk,
      status: statusOk ? "ok" : "degraded",
      latency_ms: latency,
      service: (payload && payload.service) || null,
    };
  } catch {
    return {
      configured: true,
      ok: false,
      status: "unreachable",
      latency_ms: Date.now() - start,
      issues: ["PI /health unreachable"],
    };
  }
}

export async function onRequestGet(context) {
  const env = getEnv(context);
  const authCfg = evaluateProductionAuthConfig(env);
  if (authCfg.fatal) {
    return jsonError(authCfg.code, authCfg.message, 503, {
      expect_env: authCfg.expect_env,
      auth_mode: authCfg.auth_mode,
      allow_stub_auth: authCfg.allow_stub_auth,
      remediation:
        "Set ALLOW_STUB_AUTH=1 (break-glass) or migrate AUTH_MODE off stub with a signed verifier",
    });
  }

  let resultAutomation = null;
  if (useAiProxy(env)) {
    try {
      const proxied = await Promise.race([
        aiFetch(context, "/health"),
        new Promise(function (_, reject) {
          setTimeout(function () {
            reject(new Error("health probe timeout"));
          }, 3000);
        }),
      ]);
      if (proxied && !(proxied instanceof Response) && proxied.ok) {
        const payload =
          proxied.payload && proxied.payload.data != null
            ? proxied.payload.data
            : proxied.payload;
        if (payload && payload.result_automation) {
          resultAutomation = payload.result_automation;
        }
      }
    } catch {
      resultAutomation = { ok: false, status: "unreachable", issues: ["python /health unreachable"] };
    }
  }

  const pi = await probePiSummary(context, env);

  const raOk = !resultAutomation || resultAutomation.ok !== false;
  const piOk = !pi.configured || pi.ok !== false;
  return jsonOk(
    {
      status: raOk && piOk ? "ok" : "degraded",
      service: "bff",
      runtime: "cloudflare-pages-functions",
      expect_env: env.EXPECT_ENV || "unknown",
      auth_mode: env.AUTH_MODE || "stub",
      allow_stub_auth: String(env.ALLOW_STUB_AUTH || "") === "1",
      ai_proxy_configured: Boolean(env.AI_BASE_URL),
      pi_proxy_configured: Boolean(env.PI_BASE_URL),
      result_automation: resultAutomation,
      pi: pi,
    },
    {
      service: "BffHealth",
      cache: "no-store",
    },
    { cacheControl: "no-store" }
  );
}
