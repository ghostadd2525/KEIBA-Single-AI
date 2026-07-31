/**
 * GET /api/ops/history?kind=&week=&version=&status=
 */
import { jsonOk } from "../../_lib/errors.js";
import { requireOpsAdmin, fetchOpsAsset } from "../../_lib/opsConsole.js";

const KINDS = [
  "approval",
  "deploy",
  "research",
  "weekly_report",
  "boundary_audit",
  "incident",
];

export async function onRequestGet(context) {
  const gate = await requireOpsAdmin(context);
  if (gate.error) return gate.error;

  const url = new URL(context.request.url);
  const kind = (url.searchParams.get("kind") || "").trim();
  const week = (url.searchParams.get("week") || "").trim();
  const version = (url.searchParams.get("version") || "").trim();
  const status = (url.searchParams.get("status") || "").trim().toLowerCase();

  const history = (await fetchOpsAsset(context, "/ops-data/history.json")) || {
    approval: [],
    deploy: [],
    research: [],
    weekly_report: [],
    boundary_audit: [],
    incident: [],
  };

  function filterList(list) {
    return (list || []).filter(function (row) {
      if (week && String(row.week_id || "") !== week) return false;
      if (version && String(row.version || "").indexOf(version) < 0) return false;
      if (status) {
        const s = String(row.status || "").toLowerCase();
        if (s !== status && !(status === "timeout" && row.auto === true)) return false;
      }
      return true;
    });
  }

  const out = { schema_version: "expect-v89-history-api/1.0", filters: { kind, week, version, status } };
  if (kind && KINDS.indexOf(kind) >= 0) {
    out.items = filterList(history[kind]);
    out.kind = kind;
  } else {
    out.sections = {};
    KINDS.forEach(function (k) {
      out.sections[k] = filterList(history[k]);
    });
  }

  return jsonOk(out, { service: "OpsHistory", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
