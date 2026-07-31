/**
 * GET /api/ops/evidence-collector — Research Evidence Collector monitoring
 */
import { jsonOk } from "../../_lib/errors.js";
import { requireOpsAdmin, fetchJsonApi } from "../../_lib/opsConsole.js";

export async function onRequestGet(context) {
  const gate = await requireOpsAdmin(context);
  if (gate.error) return gate.error;

  const res = await fetchJsonApi(context, "/v1/admin/research/evidence/monitoring");
  const checkedAt = new Date().toISOString();
  const data = res.ok ? res.data : null;

  let status = "No Data";
  if (data) {
    if (data.collector_status === "disabled") status = "Pending";
    else if (data.anti_leak_violations_total > 0) status = "Failed";
    else if ((data.snapshots_by_status?.failed || 0) > 0) status = "Failed";
    else if (data.evidence_coverage?.snapshot_rate >= 0.5) status = "Healthy";
    else if (data.evidence_coverage?.snapshots_total > 0) status = "Pending";
    else status = "Pending";
  }

  return jsonOk({
    schema_version: "expect-v10-evidence-collector/1.0",
    checked_at: checkedAt,
    status,
    success_rate: data?.success_rate ?? null,
    missing_rate: data?.missing_rate ?? null,
    retry_count: data?.retry_count ?? null,
    source_latency_ms_avg: data?.source_latency_ms_avg ?? null,
    source_availability: data?.source_availability ?? null,
    evidence_coverage: data?.evidence_coverage ?? null,
    jobs_by_status: data?.jobs_by_status ?? {},
    snapshots_by_status: data?.snapshots_by_status ?? {},
    anti_leak_violations_total: data?.anti_leak_violations_total ?? 0,
    collector_status: data?.collector_status ?? "unknown",
    pi_base_url_configured: data?.pi_base_url_configured ?? false,
  });
}
