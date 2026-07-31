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
import {
  evaluateSingleDetailAlerts,
  snapshotSingleDetailMetrics,
  DEFAULT_THRESHOLDS,
} from "./singleDetailObservability.js";

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

/**
 * Horse Number Integrity — formal umaban gate for Feature CSV
 * PI: GET /v1/ops/horse-number-integrity
 */
export async function probeHorseNumberIntegrity(context) {
  const env = getEnv(context);
  if (!usePiProxy(env)) {
    return {
      name: "pi_horse_number_integrity",
      ok: true,
      skipped: true,
      error: null,
      latency_ms: 0,
      detail: { reason: "PI_BASE_URL not configured" },
      label: "Horse Number Integrity",
    };
  }
  const start = Date.now();
  try {
    const result = await withTimeout(
      piFetchStatus(context, "/v1/ops/horse-number-integrity"),
      PROBE_TIMEOUT_MS
    );
    const latency = Date.now() - start;
    const payload =
      result && result.payload && result.payload.data != null
        ? result.payload.data
        : result && result.payload;
    const statusOk = !!(result && result.ok && payload && payload.ok === true);
    const blocked =
      (payload &&
        payload.live_runners &&
        payload.live_runners.blocked_race_ids) ||
      (payload && payload.latest_report && payload.latest_report.blocked_race_ids) ||
      [];
    return {
      name: "pi_horse_number_integrity",
      ok: statusOk,
      error: statusOk
        ? null
        : (payload && payload.check ? payload.check + " NG" : null) ||
          (result && result.error) ||
          "Horse Number Not Ready",
      latency_ms: latency,
      detail: {
        via: env.PI_BASE_URL,
        check: "Horse Number Integrity",
        date: payload && payload.date,
        blocked_race_ids: blocked,
        body: payload,
      },
      label: "Horse Number Integrity",
      alert_id: statusOk ? null : "ALT-E10",
    };
  } catch (e) {
    return {
      name: "pi_horse_number_integrity",
      ok: false,
      error: String(e && e.message ? e.message : e),
      latency_ms: Date.now() - start,
      label: "Horse Number Integrity",
      alert_id: "ALT-E10",
    };
  }
}

/**
 * I4 — in-process Single Detail metrics / alerts (Flag ON path only).
 * Also probes Python /v1/site/health when AI proxy is configured.
 */
export async function probeSingleDetailOps(context) {
  const start = Date.now();
  const metrics = snapshotSingleDetailMetrics();
  const evaluated = evaluateSingleDetailAlerts(DEFAULT_THRESHOLDS, metrics);
  const sdAlerts = evaluated.alerts || [];
  const critical = sdAlerts.some(function (a) {
    return a.severity === "critical";
  });
  const warning = sdAlerts.some(function (a) {
    return a.severity === "warning";
  });

  let siteHealth = null;
  const site = await probeAi(context, "/v1/site/health");
  if (!site.skipped) {
    siteHealth = {
      ok: !!site.ok,
      latency_ms: site.latency_ms || 0,
      error: site.error || null,
    };
  }

  const deferred = !!evaluated.deferred;
  const ok = deferred ? true : !critical && (!siteHealth || siteHealth.ok);
  const firstCritical = sdAlerts.find(function (a) {
    return a.severity === "critical";
  });
  const firstAlert = firstCritical || sdAlerts[0] || null;

  return {
    name: "single_detail_ops",
    ok: ok,
    skipped: false,
    deferred: deferred,
    latency_ms: Date.now() - start,
    error: ok
      ? null
      : (firstAlert && firstAlert.message) ||
        (siteHealth && !siteHealth.ok && siteHealth.error) ||
        "single detail ops degraded",
    alert_id: !ok && firstAlert ? firstAlert.alert_id : null,
    label: "Single Detail Ops",
    detail: {
      metrics: metrics,
      alerts: sdAlerts,
      alert_eval: {
        deferred: deferred,
        reason: evaluated.reason || null,
        thresholds: DEFAULT_THRESHOLDS,
      },
      site_health: siteHealth,
      warning_only: !critical && warning,
    },
  };
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

  const [
    python,
    tunnel,
    piHealth,
    horseNumberIntegrity,
    prediction,
    conversation,
    conversationHealth,
    etl,
    resultAutomation,
    singleDetailOps,
  ] = await Promise.all([
    probePythonHealth(context),
    probeCloudflareTunnel(context),
    probePiHealth(context),
    probeHorseNumberIntegrity(context),
    probePredictionApi(context),
    probeConversationApi(context),
    probeConversationHealth(context),
    probeEtlStatus(context),
    probeResultAutomation(context),
    probeSingleDetailOps(context),
  ]);

  const checks = [
    bff,
    python,
    tunnel,
    piHealth,
    horseNumberIntegrity,
    prediction,
    conversation,
    conversationHealth,
    etl,
    resultAutomation,
    singleDetailOps,
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

  const sdMetrics = (singleDetailOps.detail && singleDetailOps.detail.metrics) || {};
  logMetrics(context, [
    {
      source: "bff-probe",
      metric: "single_detail.requests_total",
      value: sdMetrics.requests_total || 0,
      unit: "count",
      labels: { probe: "single_detail_ops" },
      status: singleDetailOps.ok ? "ok" : "error",
    },
    {
      source: "bff-probe",
      metric: "single_detail.latency_ms_p95",
      value: sdMetrics.latency_ms_p95 || 0,
      unit: "ms",
      labels: { probe: "single_detail_ops" },
      status: singleDetailOps.ok ? "ok" : "error",
    },
    {
      source: "bff-probe",
      metric: "single_detail.prediction_fallback",
      value: sdMetrics.prediction_fallback || 0,
      unit: "count",
      labels: { probe: "single_detail_ops" },
      status: "ok",
    },
    {
      source: "bff-probe",
      metric: "single_detail.error_fallback",
      value: sdMetrics.error_fallback || 0,
      unit: "count",
      labels: { probe: "single_detail_ops" },
      status: singleDetailOps.ok ? "ok" : "error",
    },
  ]);

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

  // Merge full SD alert set (deriveAlertsFromChecks keeps one id per failed check)
  const sdExtra = ((singleDetailOps.detail && singleDetailOps.detail.alerts) || []).map(
    function (a) {
      return {
        alert_id: a.alert_id,
        severity: a.severity || "warning",
        active: true,
        service: "single_detail_ops",
        summary: a.message || a.title || "single detail alert",
        latency_ms: sdMetrics.latency_ms_p95 != null ? sdMetrics.latency_ms_p95 : null,
        runbook: a.runbook || "docs/ops/single-detail-runbook.md",
      };
    }
  );
  const seenIds = new Set(
    (dash.alerts || []).map(function (a) {
      return a.alert_id;
    })
  );
  const mergedAlerts = (dash.alerts || []).slice();
  sdExtra.forEach(function (a) {
    if (!seenIds.has(a.alert_id)) {
      seenIds.add(a.alert_id);
      mergedAlerts.push(a);
    }
  });

  return {
    ...base,
    overview: dash.overview,
    inventory: dash.inventory,
    inventory_summary: dash.inventory_summary,
    notifications: dash.notifications,
    metrics: dash.metrics,
    alerts: mergedAlerts,
    alert_summary: {
      ...(dash.alert_summary || {}),
      total: mergedAlerts.length,
      critical: mergedAlerts.filter(function (a) {
        return a.severity === "critical";
      }).length,
      warning: mergedAlerts.filter(function (a) {
        return a.severity === "warning";
      }).length,
    },
    incidents: dash.incidents,
    incident_summary: dash.incident_summary,
    single_detail: {
      metrics: sdMetrics,
      alerts: (singleDetailOps.detail && singleDetailOps.detail.alerts) || [],
      deferred: !!singleDetailOps.deferred,
    },
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
