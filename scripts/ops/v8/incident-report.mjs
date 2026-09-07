/**
 * Version8.5 Operations — Incident Report writer (anomaly only).
 *
 * Usage:
 *   node scripts/ops/v8/incident-report.mjs
 *   node scripts/ops/v8/incident-report.mjs --week-id 2026-W30
 *   node scripts/ops/v8/incident-report.mjs --from-report path/to/weekly-ops-report.json
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { jstParts, repoRoot, weekIdJst } from "./calendar.mjs";
import { BASELINE_LOCK } from "./ops-baseline.mjs";
import {
  detectIncidents,
  formatIncidentMarkdown,
} from "./incident-detect.mjs";
import { buildWeeklyOpsReport } from "./weekly-report.mjs";

export {
  detectIncidents,
  formatIncidentMarkdown,
  PRECISION_DROP_THRESHOLD,
  KNOWLEDGE_SCORE_DROP_THRESHOLD,
  HIT_COLLAPSE_THRESHOLD,
} from "./incident-detect.mjs";

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function loadJson(path, fallback = null) {
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function prevWeekId(weekId) {
  const m = String(weekId).match(/^(\d{4})-W(\d{2})$/);
  if (!m) return null;
  let y = Number(m[1]);
  let w = Number(m[2]) - 1;
  if (w < 1) {
    y -= 1;
    w = 52;
  }
  return `${y}-W${String(w).padStart(2, "0")}`;
}

/**
 * Build + optionally write. Returns paths only when incidents exist.
 */
export function writeIncidentReport(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const doc =
    opts.doc ||
    (opts.from_report
      ? loadJson(opts.from_report)
      : buildWeeklyOpsReport({ week_id: weekId, devRoot }));
  if (!doc) {
    return { has_incident: false, incidents: [], paths: null, bundle: null };
  }

  const prevId = prevWeekId(doc.week_id);
  const prevDoc = prevId
    ? loadJson(
        join(devRoot, "weekly", prevId, "reports", "weekly-ops-report.json"),
        null
      )
    : null;

  const { incidents, has_incident } = detectIncidents(doc, prevDoc);
  const parts = jstParts();
  const bundle = {
    schema_version: "expect-v85-incident-bundle/1.0",
    baseline_lock: `Version${BASELINE_LOCK}`,
    week_id: doc.week_id,
    generated_at: new Date().toISOString(),
    date_jst: parts.date_jst,
    has_incident,
    incident_count: incidents.length,
    incidents,
  };

  if (!has_incident) {
    return { has_incident: false, incidents: [], bundle, paths: null };
  }

  const reports = join(devRoot, "weekly", doc.week_id, "reports");
  mkdirSync(reports, { recursive: true });
  const jsonPath = join(reports, "incident-report.json");
  const mdPath = join(reports, "incident-report.md");
  writeFileSync(jsonPath, JSON.stringify(bundle, null, 2) + "\n", "utf8");
  writeFileSync(mdPath, formatIncidentMarkdown(bundle), "utf8");
  return {
    has_incident: true,
    incidents,
    bundle,
    paths: { json: jsonPath, md: mdPath },
  };
}

function main() {
  const week_id = arg("--week-id", undefined);
  const from_report = arg("--from-report", undefined);
  const out = writeIncidentReport({ week_id, from_report });
  console.log(
    JSON.stringify(
      {
        event: "v8_incident_report",
        week_id: out.bundle?.week_id || week_id,
        has_incident: out.has_incident,
        incident_count: out.incidents.length,
        codes: out.incidents.map((i) => i.code),
        paths: out.paths,
        note: out.has_incident
          ? "Incident Report を提出してください"
          : "異常なし — Incident Report 未作成（正常）",
      },
      null,
      2
    )
  );
}

if (process.argv[1]?.endsWith("incident-report.mjs")) {
  main();
}
