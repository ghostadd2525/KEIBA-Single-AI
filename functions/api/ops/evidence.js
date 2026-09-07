/**
 * GET /api/ops/evidence?id=&week=&kind=
 */
import { jsonOk } from "../../_lib/errors.js";
import { requireOpsAdmin, fetchOpsAsset } from "../../_lib/opsConsole.js";

export async function onRequestGet(context) {
  const gate = await requireOpsAdmin(context);
  if (gate.error) return gate.error;

  const url = new URL(context.request.url);
  const id = (url.searchParams.get("id") || "").trim();
  const week = (url.searchParams.get("week") || "").trim();
  const kind = (url.searchParams.get("kind") || "").trim();

  const index = (await fetchOpsAsset(context, "/ops-data/evidence-index.json")) || {
    items: [],
  };
  let items = index.items || [];
  if (week) items = items.filter((x) => x.week_id === week);
  if (kind) items = items.filter((x) => x.kind === kind || x.label === kind);
  if (id) items = items.filter((x) => x.id === id);

  let body = null;
  if (items.length === 1 && items[0].public_path) {
    body = await fetchOpsAsset(context, items[0].public_path);
  }

  return jsonOk(
    {
      schema_version: "expect-v89-evidence-api/1.0",
      items,
      body,
    },
    { service: "OpsEvidence", cache: "no-store" },
    { status: 200, cacheControl: "no-store" }
  );
}
