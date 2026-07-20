/**
 * Phase OPS-Monitor — BFF からの依存サービスプローブ
 * 本番: AI_BASE_URL 経由（Tunnel + Access Token）
 * 開発: wrangler dev でも同一コードパス（binding のみ異なる）
 */
import { aiFetch } from "./aiProxy.js";
import { getEnv, useAiProxy } from "./env.js";

const PROBE_TIMEOUT_MS = 8000;

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise(function (_, reject) {
      setTimeout(function () {
        reject(new Error("probe timeout " + ms + "ms"));
      }, ms);
    }),
  ]);
}

/**
 * @param {object} context
 * @param {string} path
 * @param {RequestInit} [init]
 */
async function probeAi(context, path, init) {
  init = init || { method: "GET" };
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return {
      ok: false,
      skipped: true,
      error: "AI_BASE_URL not configured",
      latency_ms: 0,
    };
  }
  const start = Date.now();
  try {
    const result = await withTimeout(aiFetch(context, path, init), PROBE_TIMEOUT_MS);
    const latency = Date.now() - start;
    if (result instanceof Response) {
      return { ok: false, error: "AI proxy returned Response", latency_ms: latency };
    }
    if (result && result.ok) {
      return { ok: true, latency_ms: latency, source: result.source || "win5-ai" };
    }
    const errMsg =
      (result && result.error && result.error.message) ||
      (result && result.payload && result.payload.error && result.payload.error.message) ||
      "AI probe failed";
    return { ok: false, error: errMsg, latency_ms: latency, status: result && result.status };
  } catch (e) {
    return {
      ok: false,
      error: String(e && e.message ? e.message : e),
      latency_ms: Date.now() - start,
    };
  }
}

export async function probePythonHealth(context) {
  const r = await probeAi(context, "/health");
  return {
    name: "python_api",
    ...r,
  };
}

/** Tunnel 到達性は AI_BASE_URL /health の成否で間接判定 */
export async function probeCloudflareTunnel(context) {
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return {
      name: "cloudflare_tunnel",
      ok: false,
      skipped: true,
      error: "AI_BASE_URL not configured — tunnel probe skipped",
      latency_ms: 0,
    };
  }
  const r = await probeAi(context, "/health");
  return {
    name: "cloudflare_tunnel",
    ok: r.ok,
    error: r.ok ? null : r.error || "tunnel or origin unreachable via AI_BASE_URL",
    latency_ms: r.latency_ms,
    detail: { via: env.AI_BASE_URL },
  };
}

export async function probePredictionApi(context) {
  const r = await probeAi(context, "/v1/predictions");
  return {
    name: "prediction_api",
    ...r,
  };
}

export async function probeConversationApi(context) {
  const r = await probeAi(context, "/v1/conversation/chat", {
    method: "POST",
    body: JSON.stringify({ message: "health ping", session_id: "ops-monitor" }),
  });
  return {
    name: "conversation_api",
    ...r,
  };
}

export async function probeEtlStatus(context) {
  const start = Date.now();
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return {
      name: "etl",
      ok: false,
      skipped: true,
      error: "AI_BASE_URL not configured",
      latency_ms: 0,
    };
  }
  try {
    const proxied = await withTimeout(aiFetch(context, "/v1/admin/etl/status"), PROBE_TIMEOUT_MS);
    const latency = Date.now() - start;
    if (!proxied || !proxied.ok) {
      const errMsg =
        (proxied && proxied.error && proxied.error.message) || "ETL status probe failed";
      return { name: "etl", ok: false, error: errMsg, latency_ms: latency };
    }
    const data =
      proxied.payload && proxied.payload.data != null ? proxied.payload.data : proxied.payload;
    const failed = data && data.status === "failed";
    return {
      name: "etl",
      ok: !failed,
      error: failed ? data.error_reason || "ETL latest run failed" : null,
      latency_ms: latency,
      detail: data,
    };
  } catch (e) {
    return {
      name: "etl",
      ok: false,
      error: String(e && e.message ? e.message : e),
      latency_ms: Date.now() - start,
    };
  }
}

/**
 * Result Automation health:
 * stale ACTIVE / FAILED / DEGRADED / missing manifest|summary
 */
export async function probeResultAutomation(context) {
  const start = Date.now();
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return {
      name: "result_automation",
      ok: false,
      skipped: true,
      error: "AI_BASE_URL not configured",
      latency_ms: 0,
    };
  }
  try {
    const proxied = await withTimeout(
      aiFetch(context, "/v1/admin/results/status"),
      PROBE_TIMEOUT_MS
    );
    const latency = Date.now() - start;
    if (!proxied || !proxied.ok) {
      const errMsg =
        (proxied && proxied.error && proxied.error.message) ||
        "result_automation status probe failed";
      return { name: "result_automation", ok: false, error: errMsg, latency_ms: latency };
    }
    const data =
      proxied.payload && proxied.payload.data != null ? proxied.payload.data : proxied.payload;
    const ok = !(data && data.ok === false);
    const issues = (data && data.issues) || [];
    return {
      name: "result_automation",
      ok: ok,
      error: ok ? null : issues.join("; ") || data.status || "result_automation unhealthy",
      latency_ms: latency,
      detail: data,
    };
  } catch (e) {
    return {
      name: "result_automation",
      ok: false,
      error: String(e && e.message ? e.message : e),
      latency_ms: Date.now() - start,
    };
  }
}

export async function runAllProbes(context) {
  const env = getEnv(context);
  const bff = {
    name: "bff",
    ok: true,
    latency_ms: 0,
    detail: {
      expect_env: env.EXPECT_ENV || "unknown",
      runtime: "cloudflare-pages-functions",
    },
  };

  const [python, tunnel, prediction, conversation, etl, resultAutomation] = await Promise.all([
    probePythonHealth(context),
    probeCloudflareTunnel(context),
    probePredictionApi(context),
    probeConversationApi(context),
    probeEtlStatus(context),
    probeResultAutomation(context),
  ]);

  const checks = [bff, python, tunnel, prediction, conversation, etl, resultAutomation];
  const active = checks.filter(function (c) {
    return !c.skipped;
  });
  const allOk = active.every(function (c) {
    return c.ok;
  });
  const anyDown = active.some(function (c) {
    return !c.ok;
  });

  return {
    status: allOk ? "ok" : anyDown ? "degraded" : "ok",
    checks: checks,
    generated_at: new Date().toISOString(),
  };
}

export function verifyMonitorKey(context) {
  const env = getEnv(context);
  const expected = String((context.env && context.env.OPS_MONITOR_KEY) || "").trim();
  if (!expected) return true;
  const req = context.request;
  const header = (req.headers.get("x-ops-monitor-key") || "").trim();
  const url = new URL(req.url);
  const query = (url.searchParams.get("key") || "").trim();
  return header === expected || query === expected;
}
