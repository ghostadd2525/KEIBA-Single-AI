/**
 * expect-ops-metrics/1.0 — BFF side (Logpush / console)
 * 設計: docs/releases/v2-operations-monitoring-inventory.md §2.7
 */
export const OPS_METRICS_SCHEMA = "expect-ops-metrics/1.0";

export function buildMetricRow(row) {
  return {
    schema_version: OPS_METRICS_SCHEMA,
    ts: row.ts || new Date().toISOString(),
    source: String(row.source || "bff-probe"),
    metric: String(row.metric || ""),
    value: row.value != null ? Number(row.value) : null,
    unit: row.unit != null ? String(row.unit) : null,
    labels: row.labels && typeof row.labels === "object" ? row.labels : {},
    status: row.status || "ok",
  };
}

/** Workers Logpush 向けに 1 行 JSON を出力 */
export function logMetric(context, row) {
  const line = buildMetricRow(row);
  console.log(JSON.stringify({ ops_metric: true, ...line }));
  return line;
}

export function logMetrics(context, rows) {
  return (rows || []).map(function (r) {
    return logMetric(context, r);
  });
}
