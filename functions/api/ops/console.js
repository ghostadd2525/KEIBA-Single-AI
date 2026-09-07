/**
 * GET /api/ops/console — Version8.9 Operations Console bootstrap
 */
import { jsonOk } from "../../_lib/errors.js";
import { requireOpsAdmin, fetchOpsAsset, fetchJsonApi } from "../../_lib/opsConsole.js";

export async function onRequestGet(context) {
  const gate = await requireOpsAdmin(context);
  if (gate.error) return gate.error;

  const [
    portalSnap,
    history,
    timeline,
    evidence,
    audit,
    searchIndex,
    approvals,
    scheduler,
    knowledge,
    reports,
    deploy,
    health,
  ] = await Promise.all([
    fetchOpsAsset(context, "/ops-data/portal-snapshot.json"),
    fetchOpsAsset(context, "/ops-data/history.json"),
    fetchOpsAsset(context, "/ops-data/timeline.json"),
    fetchOpsAsset(context, "/ops-data/evidence-index.json"),
    fetchOpsAsset(context, "/ops-data/console-audit.json"),
    fetchOpsAsset(context, "/ops-data/search-index.json"),
    fetchOpsAsset(context, "/ops-data/approval-queue.json"),
    fetchOpsAsset(context, "/ops-data/research-scheduler.json"),
    fetchOpsAsset(context, "/ops-data/knowledge.json"),
    fetchOpsAsset(context, "/ops-data/reports.json"),
    fetchOpsAsset(context, "/ops-data/deploy.json"),
    fetchJsonApi(context, "/api/health"),
  ]);

  const data = {
    schema_version: "expect-v89-ops-console/1.0",
    portal_version: "8.9",
    production_auto_apply: false,
    boundary: "Research → Approval → Deploy Note → Human Deploy",
    generated_at: new Date().toISOString(),
    publish: {
      portal_snapshot: portalSnap,
      history,
      timeline,
      evidence,
      audit,
      search_index: searchIndex,
      approval_queue: approvals,
      research_scheduler: scheduler,
      knowledge,
      reports,
      deploy,
    },
    live: {
      health: health.ok ? health.data : null,
      health_ok: !!health.ok,
    },
    empty_policy: { no_data: "No Data", pending: "Pending" },
  };

  return jsonOk(data, { service: "OpsConsole", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
