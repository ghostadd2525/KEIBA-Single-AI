/**
 * GET /api/ops/search?q=&version=&week=&proposal=&pattern=&decision=&status=
 */
import { jsonOk } from "../../_lib/errors.js";
import { requireOpsAdmin, fetchOpsAsset } from "../../_lib/opsConsole.js";

export async function onRequestGet(context) {
  const gate = await requireOpsAdmin(context);
  if (gate.error) return gate.error;

  const url = new URL(context.request.url);
  const q = (url.searchParams.get("q") || "").trim().toLowerCase();
  const version = (url.searchParams.get("version") || "").trim().toLowerCase();
  const week = (url.searchParams.get("week") || "").trim();
  const proposal = (url.searchParams.get("proposal") || "").trim().toLowerCase();
  const pattern = (url.searchParams.get("pattern") || "").trim().toLowerCase();
  const decision = (url.searchParams.get("decision") || "").trim().toLowerCase();
  const status = (url.searchParams.get("status") || "").trim().toLowerCase();

  const index = (await fetchOpsAsset(context, "/ops-data/search-index.json")) || {
    docs: [],
  };
  const docs = (index.docs || []).filter(function (d) {
    if (week && String(d.week_id || "") !== week) return false;
    if (version && String(d.version || "").toLowerCase().indexOf(version) < 0) return false;
    if (proposal && String(d.proposal || d.id || "").toLowerCase().indexOf(proposal) < 0)
      return false;
    if (pattern && String(d.pattern || "").toLowerCase().indexOf(pattern) < 0) return false;
    if (decision && String(d.decision || "").toLowerCase().indexOf(decision) < 0) return false;
    if (status && String(d.status || "").toLowerCase() !== status) return false;
    if (q) {
      const hay = [d.type, d.id, d.week_id, d.version, d.status, d.decision, d.proposal, d.pattern]
        .map(function (x) {
          return String(x || "").toLowerCase();
        })
        .join(" ");
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  });

  return jsonOk(
    {
      schema_version: "expect-v89-search-api/1.0",
      count: docs.length,
      docs,
    },
    { service: "OpsSearch", cache: "no-store" },
    { status: 200, cacheControl: "no-store" }
  );
}
