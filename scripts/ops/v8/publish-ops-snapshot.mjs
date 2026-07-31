#!/usr/bin/env node
/**
 * Version8.8.1 — Ops Publish Layer
 *
 * Reads Research artifacts under development/ and writes public/ops-data/*
 * for Operations Dashboard. No PE / CE / AI / RA / Research Logic mutation.
 *
 * Usage:
 *   node scripts/ops/v8/publish-ops-snapshot.mjs
 *   npm run v8:publish
 */
import { existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { repoRoot, weekIdJst, jstParts } from "./calendar.mjs";
import { BASELINE_LOCK } from "./ops-baseline.mjs";
import { readJson, writeJson, schedulerDirs } from "./runner-lib.mjs";
import { listApprovals } from "./approval-queue.mjs";
import { publishConsoleLayer } from "./publish-console-v89.mjs";

const REPO = repoRoot();
const PENDING = "Pending";

/** Stub / marketing strings must never be published as real values. */
const STUB_RE =
  /^(—|-|live|read-only|proxy|empty|pending publish|pipeline status|毎日\s*03:00\s*JST|03:00 JST daily|Cloudflare Pages|AI\s*\/\s*PI|deploy_note_only)$/i;

function isStub(v) {
  if (v == null) return true;
  if (typeof v === "string" && (!v.trim() || STUB_RE.test(v.trim()))) return true;
  return false;
}

function realOrNull(v) {
  return isStub(v) ? null : v;
}

/**
 * Next calendar 03:00 JST as ISO(+09:00). Real computed schedule, not a fixed label.
 */
export function nextRunIsoJst(now = new Date()) {
  const parts = jstParts(now);
  // parts.date_jst = YYYY-MM-DD in JST
  const [y, m, d] = String(parts.date_jst).split("-").map(Number);
  // Candidate today 03:00 JST = UTC yesterday 18:00 (JST=UTC+9)
  let candidateUtc = Date.UTC(y, m - 1, d, 3 - 9, 0, 0);
  if (candidateUtc <= now.getTime()) {
    candidateUtc += 24 * 60 * 60 * 1000;
  }
  const next = new Date(candidateUtc);
  // Format +09:00 wall clock
  const j = jstParts(next);
  return `${j.date_jst}T03:00:00+09:00`;
}

function avgKnowledgeScore(proposalsDoc) {
  const props = (proposalsDoc && proposalsDoc.proposals) || {};
  const scores = Object.values(props)
    .map((p) => (p && typeof p.knowledge_score === "number" ? p.knowledge_score : null))
    .filter((n) => n != null);
  if (!scores.length) return null;
  return Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 1000) / 1000;
}

function publishKnowledge(repo = REPO) {
  const root = join(repo, "development", "knowledge");
  const accepted = readJson(join(root, "accepted_patterns.json"), null);
  const rejected = readJson(join(root, "rejected_patterns.json"), null);
  const proposals = readJson(join(root, "proposals.json"), null);
  const rootCauses = readJson(join(root, "root_causes.json"), null);
  const canary = readJson(join(root, "canary_results.json"), null);

  const acceptedN = Array.isArray(accepted?.patterns) ? accepted.patterns.length : null;
  const rejectedN = Array.isArray(rejected?.patterns) ? rejected.patterns.length : null;
  const score = avgKnowledgeScore(proposals);
  const families = rootCauses?.families ? Object.keys(rootCauses.families).length : null;

  const hasAnyFile = !!(accepted || rejected || proposals || rootCauses || canary);
  const out = {
    schema_version: "expect-v881-knowledge-publish/1.0",
    published_at: new Date().toISOString(),
    source: "development/knowledge",
    knowledge_score: score,
    accepted_patterns: acceptedN,
    rejected_patterns: rejectedN,
    governance:
      families == null
        ? null
        : families > 0
          ? `families:${families}`
          : null,
    available: hasAnyFile,
    raw_meta: {
      accepted_updated_at: accepted?.updated_at ?? null,
      rejected_updated_at: rejected?.updated_at ?? null,
      proposals_updated_at: proposals?.updated_at ?? null,
    },
  };
  writeJson(join(repo, "public", "ops-data", "knowledge.json"), out);
  return out;
}

function listWeekIds(repo = REPO) {
  const weekly = join(repo, "development", "weekly");
  if (!existsSync(weekly)) return [];
  return readdirSync(weekly)
    .filter((n) => n.startsWith("20") && !n.startsWith("_"))
    .filter((n) => {
      try {
        return statSync(join(weekly, n)).isDirectory();
      } catch {
        return false;
      }
    })
    .sort();
}

function publishReports(repo = REPO) {
  const weekIds = listWeekIds(repo);
  const reports = [];
  for (const weekId of weekIds) {
    const dir = join(repo, "development", "weekly", weekId, "reports");
    if (!existsSync(dir)) continue;
    for (const f of readdirSync(dir).filter((x) => x.endsWith(".json") || x.endsWith(".md"))) {
      const p = join(dir, f);
      const st = statSync(p);
      reports.push({
        week_id: weekId,
        file: f,
        path: `development/weekly/${weekId}/reports/${f}`,
        mtime: st.mtime.toISOString(),
        bytes: st.size,
      });
    }
  }
  reports.sort((a, b) => String(b.mtime).localeCompare(String(a.mtime)));

  const latestOps = reports.find((r) => r.file === "weekly-ops-report.json");
  let latestDoc = null;
  if (latestOps) {
    latestDoc = readJson(join(repo, latestOps.path), null);
  }

  const baselineHealth =
    latestDoc?.baseline_health_check ||
    latestDoc?.baseline_health ||
    latestDoc?.health_check ||
    null;
  const boundary =
    latestDoc?.boundary_audit || latestDoc?.boundary || latestDoc?.safety || null;
  const incidentPath = latestDoc
    ? join(repo, "development", "weekly", latestDoc.week_id || "", "reports", "incident-report.json")
    : null;
  const incident = incidentPath && existsSync(incidentPath) ? readJson(incidentPath, null) : null;

  const out = {
    schema_version: "expect-v881-reports-publish/1.0",
    published_at: new Date().toISOString(),
    source: "development/weekly/*/reports",
    weekly_report: latestOps
      ? latestOps.week_id || latestDoc?.week_id || "available"
      : null,
    weekly_report_path: latestOps ? latestOps.path : null,
    baseline_health_check: baselineHealth
      ? typeof baselineHealth === "string"
        ? baselineHealth
        : baselineHealth.status || baselineHealth.ok === true
          ? "OK"
          : PENDING
      : latestOps
        ? PENDING
        : null,
    boundary_audit: boundary
      ? typeof boundary === "string"
        ? boundary
        : boundary.status || (boundary.production_auto_apply === false ? "hold" : PENDING)
      : latestOps
        ? PENDING
        : null,
    incident_report: incident ? incident.severity || "present" : null,
    latest_week_id: latestDoc?.week_id || latestOps?.week_id || null,
    decision: latestDoc?.decision?.value || latestDoc?.decision || null,
    items: reports.slice(0, 50),
  };
  writeJson(join(repo, "public", "ops-data", "reports.json"), out);
  return out;
}

function publishScheduler(repo = REPO, now = new Date()) {
  const dirs = schedulerDirs(repo);
  const state = readJson(dirs.weeklyRunner, null);
  const history = readJson(dirs.phaseHistory, []);

  const weekId = realOrNull(state?.week_id) || weekIdJst(now);
  const currentPhase = realOrNull(state?.current_phase);
  const lastRun = realOrNull(state?.last_run_at);
  // Prefer computed next ISO; never publish stub schedule labels
  const nextRaw = realOrNull(state?.next_run_jst);
  const nextRun =
    nextRaw && !STUB_RE.test(String(nextRaw)) ? nextRaw : state ? nextRunIsoJst(now) : null;
  const recovery =
    state && typeof state.recovery_active === "boolean"
      ? state.recovery_active
        ? "active"
        : "idle"
      : null;

  const out = {
    schema_version: "expect-v881-scheduler-publish/1.0",
    published_at: now.toISOString(),
    source: "development/scheduler",
    available: !!state,
    baseline_lock: state?.baseline_lock || `Version${BASELINE_LOCK}`,
    week_id: state ? weekId : null,
    current_phase: currentPhase,
    last_run_at: lastRun,
    next_run: state ? nextRun : null,
    next_run_jst: state ? nextRun : null,
    recovery_active: state ? !!state.recovery_active : null,
    recovery,
    success_count: state?.success_count ?? null,
    failure_count: state?.failure_count ?? null,
    skip_count: state?.skip_count ?? null,
    last_skip_reason: realOrNull(state?.last_skip_reason),
    production_auto_apply: false,
    deploy_policy: null, // do not publish stub; deploy.json owns deploy-note
    phases: state?.phases || null,
    display: state
      ? {
          current_phase: currentPhase,
          next_run: nextRun,
          last_run: lastRun,
          recovery: state.recovery_active === true,
          success: state.success_count ?? null,
          failure: state.failure_count ?? null,
          skip_reason: realOrNull(state?.last_skip_reason),
        }
      : {},
    history_tail: Array.isArray(history) ? history.slice(-10) : [],
    raw_updated_at: state?.updated_at || null,
  };
  writeJson(join(repo, "public", "ops-data", "research-scheduler.json"), out);
  return out;
}

function publishApprovals(repo = REPO) {
  // Prefer live queue index; fall back to empty publish schema
  let index = null;
  try {
    index = listApprovals({ repo });
  } catch {
    index = readJson(join(repo, "development", "approvals", "index.json"), null);
  }
  const items = Array.isArray(index?.items) ? index.items : [];
  const counts = {
    pending: items.filter((x) => x.status === "pending").length,
    approved: items.filter((x) => x.status === "approved").length,
    rejected: items.filter((x) => x.status === "rejected" && !x.auto).length,
    timeout: items.filter(
      (x) => x.status === "rejected" && (x.auto === true || x.reason === "approval_timeout")
    ).length,
  };
  const out = {
    schema_version: "expect-v881-approval-publish/1.0",
    published_at: new Date().toISOString(),
    source: "development/approvals",
    pending_count: counts.pending,
    approved_count: counts.approved,
    rejected_count: counts.rejected,
    timeout_count: counts.timeout,
    pending: counts.pending,
    approved: counts.approved,
    rejected: counts.rejected,
    timeout: counts.timeout,
    items,
    production_auto_apply: false,
    boundary: "Accept → RC → Deploy Note → Human Deploy",
  };
  writeJson(join(repo, "public", "ops-data", "approval-queue.json"), out);
  // compatibility alias for earlier V8.8 path
  writeJson(join(repo, "public", "ops-data", "approvals.json"), out);
  return out;
}

function publishDeploy(repo = REPO) {
  const weekIds = listWeekIds(repo);
  const notes = [];
  for (const weekId of weekIds) {
    const p = join(repo, "development", "weekly", weekId, "sat-deploy", "deploy-note.json");
    if (!existsSync(p)) continue;
    const doc = readJson(p, null);
    if (!doc) continue;
    notes.push({
      week_id: weekId,
      path: `development/weekly/${weekId}/sat-deploy/deploy-note.json`,
      action: doc.action || null,
      decision: doc.decision || null,
      production_auto_apply: doc.production_auto_apply === true,
      human_deploy_required: !!doc.human_deploy_required,
      approval_id: doc.approval_id || null,
      proposal_ids: doc.proposal_ids || [],
      note: realOrNull(doc.note),
    });
  }
  notes.sort((a, b) => String(b.week_id).localeCompare(String(a.week_id)));
  const latest = notes[0] || null;

  // Accepted candidates from approval queue
  let approved = [];
  try {
    const aq = listApprovals({ repo, status: "approved" });
    approved = (aq.items || []).map((x) => x.approval_id);
  } catch {
    approved = [];
  }

  const out = {
    schema_version: "expect-v881-deploy-publish/1.0",
    published_at: new Date().toISOString(),
    source: "development/weekly/*/sat-deploy",
    deploy_queue: notes.length ? `${notes.length} note(s)` : null,
    accepted_candidates: approved.length ? approved.join(", ") : null,
    deploy_note: latest
      ? latest.action || latest.path
      : null,
    production_auto_apply: false,
    human_deploy_required: latest ? !!latest.human_deploy_required : null,
    latest,
    notes: notes.slice(0, 20),
  };
  writeJson(join(repo, "public", "ops-data", "deploy.json"), out);
  return out;
}

function cardValue(v, emptyMode = "no_data") {
  if (v == null || v === "") return emptyMode === "pending" ? PENDING : null;
  if (isStub(v)) return emptyMode === "pending" ? PENDING : null;
  return v;
}

function buildPortalSnapshot({ knowledge, reports, scheduler, approvals, deploy }, repo = REPO) {
  const snap = {
    schema_version: "expect-v881-portal-snapshot/1.0",
    baseline_lock: scheduler?.baseline_lock || `Version${BASELINE_LOCK}`,
    read_only: true,
    production_auto_apply: false,
    published_at: new Date().toISOString(),
    publish_layer: "8.8.1",
    knowledge: {
      knowledge_score: knowledge.knowledge_score,
      accepted_patterns:
        knowledge.accepted_patterns == null ? null : String(knowledge.accepted_patterns),
      rejected_patterns:
        knowledge.rejected_patterns == null ? null : String(knowledge.rejected_patterns),
      governance: knowledge.governance,
    },
    research: {
      week_id: scheduler.week_id,
      current_phase: scheduler.current_phase,
      next_run: scheduler.next_run,
      last_run: scheduler.last_run_at,
      recovery: scheduler.recovery,
      decision: reports.decision
        ? typeof reports.decision === "string"
          ? reports.decision
          : reports.decision.value || null
        : null,
    },
    deploy: {
      deploy_queue: deploy.deploy_queue,
      accepted_candidates: deploy.accepted_candidates,
      deploy_note: deploy.deploy_note,
    },
    reports: {
      weekly_report: reports.weekly_report,
      baseline_health_check: reports.baseline_health_check,
      boundary_audit: reports.boundary_audit,
      incident_report: reports.incident_report,
    },
    approval: {
      pending: approvals.pending_count,
      approved: approvals.approved_count,
      rejected: approvals.rejected_count,
      timeout: approvals.timeout_count,
    },
    system: {},
    production: {},
  };
  writeJson(join(repo, "public", "ops-data", "portal-snapshot.json"), snap);
  return snap;
}

export function publishOpsSnapshot(opts = {}) {
  const repo = opts.repo || REPO;
  const now = opts.now || new Date();
  mkdirSync(join(repo, "public", "ops-data"), { recursive: true });

  const knowledge = publishKnowledge(repo);
  const reports = publishReports(repo);
  const scheduler = publishScheduler(repo, now);
  const approvals = publishApprovals(repo);
  const deploy = publishDeploy(repo);
  const portal = buildPortalSnapshot(
    { knowledge, reports, scheduler, approvals, deploy },
    repo
  );
  const consoleLayer = publishConsoleLayer({ repo, now });

  return {
    ok: true,
    schema_version: "expect-v881-publish-result/1.0",
    published_at: now.toISOString(),
    files: [
      "public/ops-data/knowledge.json",
      "public/ops-data/reports.json",
      "public/ops-data/research-scheduler.json",
      "public/ops-data/approval-queue.json",
      "public/ops-data/deploy.json",
      "public/ops-data/portal-snapshot.json",
      ...(consoleLayer.files || []),
    ],
    summary: {
      week_id: scheduler.week_id,
      current_phase: scheduler.current_phase,
      next_run: scheduler.next_run,
      knowledge_score: knowledge.knowledge_score,
      pending_approvals: approvals.pending_count,
      weekly_report: reports.weekly_report,
      console: consoleLayer.counts || null,
    },
    portal_schema: portal.schema_version,
  };
}

function main() {
  const out = publishOpsSnapshot();
  console.log(JSON.stringify(out, null, 2));
}

const isMain =
  process.argv[1] &&
  String(process.argv[1]).replace(/\\/g, "/").endsWith("publish-ops-snapshot.mjs");
if (isMain) {
  try {
    main();
  } catch (e) {
    console.error(e && e.message ? e.message : e);
    process.exit(1);
  }
}
