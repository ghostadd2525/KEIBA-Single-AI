/**
 * GET /api/health — BFF Liveness（認証不要）
 *
 * 軽量応答。詳細プローブは GET /api/ops/monitor
 * Phase OPS-Hardening: result_automation 要約を Python /health 経由で添付（失敗時は null）
 */
import { aiFetch } from "../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../_lib/env.js";
import { jsonOk } from "../_lib/errors.js";

export async function onRequestGet(context) {
  const env = getEnv(context);
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

  const raOk = !resultAutomation || resultAutomation.ok !== false;
  return jsonOk(
    {
      status: raOk ? "ok" : "degraded",
      service: "bff",
      runtime: "cloudflare-pages-functions",
      expect_env: env.EXPECT_ENV || "unknown",
      ai_proxy_configured: Boolean(env.AI_BASE_URL),
      result_automation: resultAutomation,
    },
    {
      service: "BffHealth",
      cache: "no-store",
    },
    { cacheControl: "no-store" }
  );
}
