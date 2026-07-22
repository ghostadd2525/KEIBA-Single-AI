/**
 * expect-ops-metrics/1.0 — JSON Metrics writer (MET-J*)
 * 設計: docs/releases/v2-operations-monitoring-inventory.md §2.7
 */
import { appendFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";

export const OPS_METRICS_SCHEMA = "expect-ops-metrics/1.0";

/**
 * @param {object} row
 * @returns {object}
 */
export function buildMetricRow(row) {
  return {
    schema_version: OPS_METRICS_SCHEMA,
    ts: row.ts || new Date().toISOString(),
    source: String(row.source || "unknown"),
    metric: String(row.metric || ""),
    value: row.value != null ? Number(row.value) : null,
    unit: row.unit != null ? String(row.unit) : null,
    labels: row.labels && typeof row.labels === "object" ? row.labels : {},
    status: row.status || "ok",
  };
}

/**
 * Append one metrics line to jsonl file.
 * @param {string} filePath
 * @param {object} row
 */
export function appendMetric(filePath, row) {
  const line = buildMetricRow(row);
  const dir = dirname(filePath);
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  appendFileSync(filePath, JSON.stringify(line) + "\n", "utf8");
  return line;
}

/**
 * Build PI health metric rows from probe checks.
 * @param {Array<object>} checks
 * @param {string} [source]
 */
export function metricsFromPiChecks(checks, source) {
  source = source || "pi-probe";
  const rows = [];
  (checks || []).forEach(function (c) {
    if (!c || c.skipped) return;
    if (c.name === "pi_api" || c.name === "pi_health") {
      if (c.latency_ms != null) {
        rows.push(
          buildMetricRow({
            source,
            metric: "pi.health.latency_ms",
            value: c.latency_ms,
            unit: "ms",
            labels: { probe: c.name },
            status: c.ok ? "ok" : "error",
          })
        );
      }
      rows.push(
        buildMetricRow({
          source,
          metric: "pi.health.ok",
          value: c.ok ? 1 : 0,
          unit: "bool",
          labels: { probe: c.name },
          status: c.ok ? "ok" : "error",
        })
      );
    }
    if (c.name === "pi_systemd") {
      rows.push(
        buildMetricRow({
          source,
          metric: "pi.systemd.active",
          value: c.ok ? 1 : 0,
          unit: "bool",
          labels: { unit: (c.detail && c.detail.unit) || "expect-pi-keibanet-api" },
          status: c.ok ? "ok" : "error",
        })
      );
    }
    if (c.name === "pi_tunnel") {
      if (c.latency_ms != null) {
        rows.push(
          buildMetricRow({
            source,
            metric: "pi.tunnel.health.latency_ms",
            value: c.latency_ms,
            unit: "ms",
            labels: {},
            status: c.ok ? "ok" : "error",
          })
        );
      }
      rows.push(
        buildMetricRow({
          source,
          metric: "tunnel.reachability.pi",
          value: c.ok ? 1 : 0,
          unit: "bool",
          status: c.ok ? "ok" : "error",
        })
      );
    }
  });
  return rows;
}
