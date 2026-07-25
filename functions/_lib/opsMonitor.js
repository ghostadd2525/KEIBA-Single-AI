/**
 * Phase OPS-Monitor — BFF からの依存サービスプローブ
 * 本番: AI_BASE_URL 経由（Tunnel + Access Token）
 * Version 2 Ops Phase 1: PI_BASE_URL 経由 PI Health（PI-H03 相当）
 * 開発: wrangler dev でも同一コードパス（binding のみ異なる）
 */
import { aiFetch } from "./aiProxy.js";
import { getEnv, useAiProxy } from "./env.js";
import { logMetrics } from "./opsMetrics.js";
import { piFetchStatus, usePiProxy } from "./piProxy.js";
import { buildDashboardPayload } from "./opsDashboard.js";

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

/**
 * PI KeibaNet API liveness（PI_BASE_URL/health）
 * systemd は BFF から不可 → EC2 monitor-prod 側（PI-H01）
 */
export async function probePiHealth(context) {
  const env = getEnv(context);
  if (!usePiProxy(env)) {
    return {
      name: "pi_health",
      ok: true,
      skipped: true,
      error: null,
      latency_ms: 0,
      detail: { reason: "PI_BASE_URL not configured" },
    };
  }
  const start = Date.now();
  try {
    const result = await withTimeout(piFetchStatus(context, "/health"), PROBE_TIMEOUT_MS);
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
      name: "pi_health",
      ok: !!statusOk,
      error: statusOk
        ? null
        : (result && result.error) || "PI health status not ok",
      latency_ms: latency,
      detail: { via: env.PI_BASE_URL, body: payload },
      alert_id: statusOk ? null : "ALT-E02",
    };
  } catch (e) {
    return {
      name: "pi_health",
      ok: false,
      error: String(e && e.message ? e.message : e),
      latency_ms: Date.now() - start,
      alert_id: "ALT-E02",
    };
  }
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

export async function probeConversationHealth(context) {
  const start = Date.now();
  const env = getEnv(context);
  if (!useAiProxy(env)) {
    return {
      name: "conversation_health",
      ok: false,
      skipped: true,
      error: "AI_BASE_URL not configured",
      latency_ms: 0,
    };
  }
  try {
    const proxied = await withTimeout(
      aiFetch(context, "/v1/conversation/health"),
      PROBE_TIMEOUT_MS
    );
    const latency = Date.now() - start;
    if (!proxied || !proxied.ok) {
      return {
        name: "conversation_health",
        ok: false,
        error:
          (proxied && proxied.error && proxied.error.message) ||
          "conversation health probe failed",
        latency_ms: latency,
      };
    }
    const data =
      proxied.payload && proxied.payload.data != null ? proxied.payload.data : proxied.payload;
    const overallOk = data && (data.overall_ok === true || data.status === "ok");
    return {
      name: "conversation_health",
      ok: !!overallOk,
      latency_ms: latency,
      detail: {
        status: data && data.status,
        components: data && data.components,
      },
      error: overallOk ? null : "conversation health degraded",
    };
  } catch (e) {
    return {
      name: "conversation_health",
      ok: false,
      error: String((e && e.message) || e),
      latency_ms: Date.now() - start,
    };
  }
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

  const [python, tunnel, piHealth, prediction, conversation, conversationHealth, etl, resultAutomation] =
    await Promise.all([
      probePythonHealth(context),
      probeCloudflareTunnel(context),
      probePiHealth(context),
      probePredictionApi(context),
      probeConversationApi(context),
      probeConversationHealth(context),
      probeEtlStatus(context),
      probeResultAutomation(context),
    ]);

  const checks = [
    bff,
    python,
    tunnel,
    piHealth,
    prediction,
    conversation,
    conversationHealth,
    etl,
    resultAutomation,
  ];
  const active = checks.filter(function (c) {
    return !c.skipped;
  });
  const allOk = active.every(function (c) {
    return c.ok;
  });
  const anyDown = active.some(function (c) {
    return !c.ok;
  });

  if (!piHealth.skipped) {
    logMetrics(context, [
      {
        source: "bff-probe",
        metric: "pi.health.ok",
        value: piHealth.ok ? 1 : 0,
        unit: "bool",
        labels: { probe: "pi_health" },
        status: piHealth.ok ? "ok" : "error",
      },
      {
        source: "bff-probe",
        metric: "pi.health.latency_ms",
        value: piHealth.latency_ms || 0,
        unit: "ms",
        labels: { probe: "pi_health" },
        status: piHealth.ok ? "ok" : "error",
      },
    ]);
  }

  const base = {
    status: allOk ? "ok" : anyDown ? "degraded" : "ok",
    phase: "v2-ops-phase3",
    pi: {
      overall: piHealth.skipped ? "skipped" : piHealth.ok ? "ok" : "degraded",
      checks: [piHealth],
    },
    checks: checks,
    generated_at: new Date().toISOString(),
  };

  const dash = buildDashboardPayload(base, { source: "bff-probe" });
  return {
    ...base,
    overview: dash.overview,
    inventory: dash.inventory,
    inventory_summary: dash.inventory_summary,
    notifications: dash.notifications,
    metrics: dash.metrics,
    alerts: dash.alerts,
    alert_summary: dash.alert_summary,
    incidents: dash.incidents,
    incident_summary: dash.incident_summary,
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
