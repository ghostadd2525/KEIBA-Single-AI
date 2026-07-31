/**
 * GET /api/ops/timeline
 */
import { jsonOk } from "../../_lib/errors.js";
import { requireOpsAdmin, fetchOpsAsset } from "../../_lib/opsConsole.js";

export async function onRequestGet(context) {
  const gate = await requireOpsAdmin(context);
  if (gate.error) return gate.error;

  const timeline = await fetchOpsAsset(context, "/ops-data/timeline.json");
  const data = timeline || {
    schema_version: "expect-v89-timeline/1.0",
    week_id: null,
    steps: [],
    available: false,
  };
  if (!timeline) data.available = false;
  else data.available = true;

  return jsonOk(data, { service: "OpsTimeline", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
