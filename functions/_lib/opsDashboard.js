/**
 * Version 2 Operations Phase 2 — Metrics 集約 / Alert / Incident 派生
 * 設計: docs/releases/v2-operations-monitoring-inventory.md §8 Phase 2
 *
 * 正本スキーマ行: expect-ops-metrics/1.0 · expect-ops-incident/1.0
 */
import { buildMetricRow } from "./opsMetrics.js";

export const OPS_DASHBOARD_SCHEMA = "expect-ops-dashboard/1.0";

/** check.name → Alert ID（設計 §2.5） */
export const ALERT_BY_CHECK = {
  pi_health: "ALT-E02",
  pi_systemd: "ALT-E05",
  pi_tunnel: "ALT-E02",
  cloudflare_tunnel: "ALT-E03",
  prediction_api: "ALT-E04",
  result_automation: "ALT-E08",
  etl: "ALT-E09",
  bff: "ALT-E01",
  python_api: "ALT-E01",
};

export const ALERT_SEVERITY = {
  "ALT-E01": "critical",
  "ALT-E02": "critical",
  "ALT-E03": "critical",
  "ALT-E04": "critical",
  "ALT-E05": "critical",
  "ALT-E08": "warning",
  "ALT-E09": "warning",
};

/** Alert → Runbook アンカー（docs/ops/v2-operations-runbook.md） */
export const ALERT_RUNBOOK = {
  "ALT-E01": "docs/ops/v2-operations-runbook.md#alt-e01",
  "ALT-E02": "docs/ops/v2-operations-runbook.md#alt-e02",
  "ALT-E03": "docs/ops/v2-operations-runbook.md#alt-e03",
  "ALT-E04": "docs/ops/v2-operations-runbook.md#alt-e04",
  "ALT-E05": "docs/ops/v2-operations-runbook.md#alt-e05",
  "ALT-E08": "docs/ops/v2-operations-runbook.md#alt-e08",
  "ALT-E09": "docs/ops/v2-operations-runbook.md#alt-e09",
};

export const MONITOR_INVENTORY = [
  { id: "PI-H01", layer: "PI", status: "wired", via: "ec2-monitor systemd" },
  { id: "PI-H02", layer: "PI", status: "wired", via: "ec2-monitor + bff pi_health" },
  { id: "PI-H03", layer: "PI", status: "wired", via: "PI_TUNNEL_PROBE_URL optional" },
  { id: "TUN-H01", layer: "Tunnel", status: "wired", via: "ec2-monitor cloudflared" },
  { id: "TUN-H02", layer: "Tunnel", status: "wired", via: "bff cloudflare_tunnel" },
  { id: "CF-H02", layer: "Cloudflare", status: "wired", via: "GET /api/health" },
  { id: "MET-J02", layer: "Metrics", status: "wired", via: "bff dashboard/monitor" },
  { id: "MET-J04", layer: "Metrics", status: "wired", via: "pi-metrics.jsonl" },
  { id: "MET-J07", layer: "Metrics", status: "wired", via: "incidents.jsonl" },
  { id: "ALT-E02", layer: "Alert", status: "wired", via: "pi_health → Slack SLK-N01" },
  { id: "ALT-E05", layer: "Alert", status: "wired", via: "pi_systemd → Slack SLK-N01" },
  { id: "SLK-N01", layer: "Notification", status: "wired", via: "OPS_SLACK_WEBHOOK_URL" },
  { id: "SLK-N02", layer: "Notification", status: "wired", via: "warning webhook / shared" },
  { id: "GRF-D01", layer: "Observability", status: "prepared", via: "promtail example → Loki" },
];

/**
 * @param {object} check
 * @returns {string|null}
 */
export function alertIdForCheck(check) {
  if (!check || check.skipped) return null;
  if (check.alert_id) return String(check.alert_id);
  if (check.ok) return null;
  return ALERT_BY_CHECK[check.name] || null;
}

/**
 * @param {Array<object>} checks
 * @param {string} [source]
 * @returns {object[]}
 */
export function aggregateMetricsFromChecks(checks, source) {
  source = source || "bff-probe";
  const rows = [];
  (checks || []).forEach(function (c) {
    if (!c || c.skipped) return;
    const labels = { probe: c.name };
    rows.push(
      buildMetricRow({
        source,
        metric: "probe." + c.name + ".ok",
        value: c.ok ? 1 : 0,
        unit: "bool",
        labels,
        status: c.ok ? "ok" : "error",
      })
    );
    if (c.latency_ms != null) {
      rows.push(
        buildMetricRow({
          source,
          metric: "probe." + c.name + ".latency_ms",
          value: c.latency_ms,
          unit: "ms",
          labels,
          status: c.ok ? "ok" : "error",
        })
      );
    }
    if (c.name === "pi_health" || c.name === "pi_api") {
      rows.push(
        buildMetricRow({
          source,
          metric: "pi.health.ok",
          value: c.ok ? 1 : 0,
          unit: "bool",
          labels,
          status: c.ok ? "ok" : "error",
        })
      );
      if (c.latency_ms != null) {
        rows.push(
          buildMetricRow({
            source,
            metric: "pi.health.latency_ms",
            value: c.latency_ms,
            unit: "ms",
            labels,
            status: c.ok ? "ok" : "error",
          })
        );
      }
    }
  });
  return rows;
}

/**
 * @param {object[]} rows
 */
export function summarizeMetrics(rows) {
  const list = rows || [];
  let ok = 0;
  let error = 0;
  list.forEach(function (r) {
    if (r.status === "error") error += 1;
    else ok += 1;
  });
  return { total: list.length, ok, error };
}

/**
 * @param {Array<object>} checks
 * @returns {object[]}
 */
export function deriveAlertsFromChecks(checks) {
  const alerts = [];
  const seen = new Set();
  (checks || []).forEach(function (c) {
    if (!c || c.skipped || c.ok) return;
    const alertId = alertIdForCheck(c);
    if (!alertId || seen.has(alertId)) return;
    seen.add(alertId);
    alerts.push({
      alert_id: alertId,
      severity: ALERT_SEVERITY[alertId] || "warning",
      active: true,
      service: c.name,
      summary: c.error || "unhealthy",
      latency_ms: c.latency_ms != null ? c.latency_ms : null,
      runbook: ALERT_RUNBOOK[alertId] || "docs/ops/v2-operations-runbook.md",
    });
  });
  return alerts;
}

/**
 * Snapshot incidents from current failed probes（BFF は永続 jsonl を持たない）
 * @param {Array<object>} checks
 * @returns {object[]}
 */
export function deriveIncidentsFromChecks(checks) {
  const now = new Date().toISOString();
  return (checks || [])
    .filter(function (c) {
      return c && !c.skipped && !c.ok;
    })
    .map(function (c) {
      return {
        incident: true,
        schema_version: "expect-ops-incident/1.0",
        occurred_at: now,
        service: c.name,
        error: c.error || "unhealthy",
        restart_count: c.restart_count || 0,
        status: "down",
        detail: c.detail || {},
        source: "bff-dashboard",
        alert_id: alertIdForCheck(c),
      };
    });
}

/**
 * PI 表示用に checks を正規化
 * @param {object} piBlock
 * @param {Array<object>} checks
 */
export function enrichPiDisplay(piBlock, checks) {
  const piChecks = (checks || []).filter(function (c) {
    return c && String(c.name || "").indexOf("pi_") === 0;
  });
  const fromBlock = (piBlock && piBlock.checks) || [];
  const merged = piChecks.length ? piChecks : fromBlock;
  const active = merged.filter(function (c) {
    return !c.skipped;
  });
  const overall =
    active.length === 0
      ? "skipped"
      : active.every(function (c) {
          return c.ok;
        })
        ? "ok"
        : "degraded";
  return {
    overall: (piBlock && piBlock.overall) || overall,
    checks: merged.map(function (c) {
      return {
        name: c.name,
        ok: !!c.ok,
        skipped: !!c.skipped,
        error: c.error || null,
        latency_ms: c.latency_ms != null ? c.latency_ms : null,
        alert_id: alertIdForCheck(c),
        detail: c.detail || null,
      };
    }),
  };
}

/**
 * @param {Array<object>} checks
 */
export function buildOverview(checks) {
  const list = checks || [];
  const active = list.filter(function (c) {
    return !c.skipped;
  });
  const ok = active.filter(function (c) {
    return c.ok;
  }).length;
  const down = active.filter(function (c) {
    return !c.ok;
  }).length;
  const skipped = list.filter(function (c) {
    return c.skipped;
  }).length;
  return {
    probes_total: list.length,
    probes_active: active.length,
    probes_ok: ok,
    probes_down: down,
    probes_skipped: skipped,
    health_ratio: active.length ? Math.round((ok / active.length) * 1000) / 10 : null,
  };
}

/**
 * @param {{ slackCriticalConfigured?: boolean, slackWarningConfigured?: boolean }} [notif]
 */
export function buildNotificationsStatus(notif) {
  notif = notif || {};
  return {
    slack_critical: {
      id: "SLK-N01",
      configured: !!notif.slackCriticalConfigured,
      suppress_minutes: 15,
    },
    slack_warning: {
      id: "SLK-N02",
      configured: !!notif.slackWarningConfigured,
      suppress_minutes: 15,
    },
    note: "Webhook URL は Secrets のみ。未設定時は no-op。",
  };
}

/**
 * @param {object} report  runAllProbes 結果
 * @param {{ source?: string, notifications?: object }} [opts]
 */
export function buildDashboardPayload(report, opts) {
  opts = opts || {};
  const checks = (report && report.checks) || [];
  const metricsRows = aggregateMetricsFromChecks(checks, opts.source || "bff-probe");
  const alerts = deriveAlertsFromChecks(checks);
  const incidents = deriveIncidentsFromChecks(checks);
  const pi = enrichPiDisplay(report && report.pi, checks);
  const overview = buildOverview(checks);
  const inventory = MONITOR_INVENTORY.map(function (row) {
    return { ...row };
  });

  return {
    schema_version: OPS_DASHBOARD_SCHEMA,
    phase: "v2-ops-phase3",
    status: (report && report.status) || "ok",
    generated_at: (report && report.generated_at) || new Date().toISOString(),
    overview: overview,
    inventory: inventory,
    inventory_summary: {
      wired: inventory.filter(function (i) {
        return i.status === "wired";
      }).length,
      prepared: inventory.filter(function (i) {
        return i.status === "prepared";
      }).length,
      total: inventory.length,
    },
    notifications: buildNotificationsStatus(opts.notifications),
    pi: pi,
    metrics: {
      schema_version: "expect-ops-metrics/1.0",
      rows: metricsRows,
      summary: summarizeMetrics(metricsRows),
    },
    alerts: alerts,
    alert_summary: {
      critical: alerts.filter(function (a) {
        return a.severity === "critical";
      }).length,
      warning: alerts.filter(function (a) {
        return a.severity === "warning";
      }).length,
      active: alerts.length,
    },
    incidents: incidents,
    incident_summary: {
      count: incidents.length,
    },
    checks: checks,
  };
}
