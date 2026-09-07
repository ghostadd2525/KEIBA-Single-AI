#!/usr/bin/env node
/**
 * Version8.9 — Operations Console Publish (additive on Publish Layer)
 *
 * Builds history / timeline / evidence / search / audit indexes and
 * copies evidence artifacts under public/ops-data/ for Pages delivery.
 * No PE / CE / AI / RA / Research Logic mutation.
 */
import {
  existsSync,
  mkdirSync,
  readdirSync,
  copyFileSync,
  statSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { repoRoot, weekIdJst } from "./calendar.mjs";
import { BASELINE_LOCK } from "./ops-baseline.mjs";
import { readJson, writeJson, schedulerDirs } from "./runner-lib.mjs";
import { listApprovals } from "./approval-queue.mjs";

const REPO = repoRoot();

function listWeekIds(repo = REPO) {
  const weekly = join(repo, "development", "weekly");
  if (!existsSync(weekly)) return [];
  return readdirSync(weekly)
    .filter((n) => /^20\d{2}-W\d{2}$/.test(n))
    .filter((n) => {
      try {
        return statSync(join(weekly, n)).isDirectory();
      } catch {
        return false;
      }
    })
    .sort();
}

function safeCopy(src, dest) {
  if (!existsSync(src)) return false;
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(src, dest);
  return true;
}

function phaseStatus(ph) {
  if (!ph || typeof ph !== "object") return "Skip";
  const s = String(ph.status || "").toLowerCase();
  if (s === "completed" || s === "success") return "PASS";
  if (s === "failed" || s === "fail") return "FAIL";
  if (s === "running") return "Pending";
  if (s === "pending" || !s) return "Skip";
  return s;
}

/**
 * Publish console indexes + artifact copies. Called from publishOpsSnapshot.
 */
export function publishConsoleLayer(opts = {}) {
  const repo = opts.repo || REPO;
  const now = opts.now || new Date();
  const ops = join(repo, "public", "ops-data");
  const artRoot = join(ops, "artifacts");
  mkdirSync(artRoot, { recursive: true });

  const weekIds = listWeekIds(repo);
  const dirs = schedulerDirs(repo);
  const state = readJson(dirs.weeklyRunner, null);
  const phaseHistory = readJson(dirs.phaseHistory, []);
  let approvals = { items: [] };
  try {
    approvals = listApprovals({ repo }) || { items: [] };
  } catch {
    approvals = readJson(join(repo, "development", "approvals", "index.json"), {
      items: [],
    }) || { items: [] };
  }

  const history = {
    schema_version: "expect-v89-history/1.0",
    published_at: now.toISOString(),
    baseline_lock: `Version${BASELINE_LOCK}`,
    approval: [],
    deploy: [],
    research: [],
    weekly_report: [],
    boundary_audit: [],
    incident: [],
  };

  const evidence = {
    schema_version: "expect-v89-evidence-index/1.0",
    published_at: now.toISOString(),
    items: [],
  };

  const searchDocs = [];

  // Knowledge artifacts
  const kbFiles = [
    "accepted_patterns.json",
    "rejected_patterns.json",
    "proposals.json",
    "root_causes.json",
    "canary_results.json",
  ];
  for (const f of kbFiles) {
    const src = join(repo, "development", "knowledge", f);
    const pubRel = `ops-data/artifacts/knowledge/${f}`;
    if (safeCopy(src, join(repo, "public", pubRel))) {
      evidence.items.push({
        id: `knowledge:${f}`,
        kind: "knowledge",
        label: f,
        week_id: null,
        version: `Version${BASELINE_LOCK}`,
        public_path: `/${pubRel}`,
        source_path: `development/knowledge/${f}`,
      });
      searchDocs.push({
        type: "pattern",
        id: f,
        week_id: null,
        version: `Version${BASELINE_LOCK}`,
        status: null,
        decision: null,
        proposal: null,
        pattern: f.replace(/\.json$/, ""),
        path: `/${pubRel}`,
      });
    }
  }

  for (const weekId of weekIds) {
    const weekRoot = join(repo, "development", "weekly", weekId);
    const destWeek = join(artRoot, weekId);
    mkdirSync(destWeek, { recursive: true });

    const copies = [
      ["fri-decision/decision.json", "decision.json"],
      ["tue-proposal/proposal-validation.json", "proposal-validation.json"],
      ["wed-canary/ranked-run.json", "ranked-run.json"],
      ["thu-baseline/report.json", "baseline-285r.json"],
      ["sat-deploy/deploy-note.json", "deploy-note.json"],
      ["sat-deploy/deploy-note.md", "deploy-note.md"],
      ["reports/weekly-ops-report.json", "weekly-ops-report.json"],
      ["reports/weekly-ops-report.md", "weekly-ops-report.md"],
      ["reports/boundary-audit.json", "boundary-audit.json"],
      ["reports/boundary-audit.md", "boundary-audit.md"],
      ["reports/incident-report.json", "incident-report.json"],
      ["reports/incident-report.md", "incident-report.md"],
    ];

    const decision = readJson(join(weekRoot, "fri-decision", "decision.json"), null);
    const report = readJson(join(weekRoot, "reports", "weekly-ops-report.json"), null);
    const deployNote = readJson(join(weekRoot, "sat-deploy", "deploy-note.json"), null);
    const boundary =
      readJson(join(weekRoot, "reports", "boundary-audit.json"), null) ||
      (report && (report.boundary_audit || report.boundary)) ||
      null;
    const incident = readJson(join(weekRoot, "reports", "incident-report.json"), null);

    for (const [rel, name] of copies) {
      const src = join(weekRoot, rel);
      if (!existsSync(src)) continue;
      const pubRel = `ops-data/artifacts/${weekId}/${name}`;
      safeCopy(src, join(repo, "public", pubRel));
      const kind = name.replace(/\.(json|md)$/, "");
      evidence.items.push({
        id: `${weekId}:${name}`,
        kind,
        label: name,
        week_id: weekId,
        version: (decision && decision.baseline_lock) || `Version${BASELINE_LOCK}`,
        public_path: `/${pubRel}`,
        source_path: `development/weekly/${weekId}/${rel}`,
      });
    }

    const decisionVal =
      (decision && (decision.decision || decision.value)) ||
      (report && report.decision && (report.decision.value || report.decision)) ||
      null;

    history.research.push({
      week_id: weekId,
      version: `Version${BASELINE_LOCK}`,
      decision: decisionVal,
      status: decisionVal ? "recorded" : null,
      path: decision
        ? `/ops-data/artifacts/${weekId}/decision.json`
        : null,
      updated_at: decision?.updated_at || report?.generated_at || null,
    });

    if (report) {
      history.weekly_report.push({
        week_id: weekId,
        version: report.baseline_lock || `Version${BASELINE_LOCK}`,
        status: "available",
        decision: decisionVal,
        path: `/ops-data/artifacts/${weekId}/weekly-ops-report.json`,
        md_path: existsSync(join(destWeek, "weekly-ops-report.md"))
          ? `/ops-data/artifacts/${weekId}/weekly-ops-report.md`
          : null,
        updated_at: report.generated_at || null,
      });
    }

    if (boundary || (report && report.boundary_audit === "Pending")) {
      history.boundary_audit.push({
        week_id: weekId,
        version: `Version${BASELINE_LOCK}`,
        status:
          typeof boundary === "string"
            ? boundary
            : boundary
              ? boundary.status || "recorded"
              : "Pending",
        path: existsSync(join(destWeek, "boundary-audit.json"))
          ? `/ops-data/artifacts/${weekId}/boundary-audit.json`
          : report
            ? `/ops-data/artifacts/${weekId}/weekly-ops-report.json`
            : null,
        updated_at: report?.generated_at || null,
      });
    }

    if (incident) {
      history.incident.push({
        week_id: weekId,
        version: `Version${BASELINE_LOCK}`,
        status: incident.severity || incident.status || "recorded",
        path: `/ops-data/artifacts/${weekId}/incident-report.json`,
        updated_at: incident.generated_at || null,
      });
    }

    if (deployNote) {
      history.deploy.push({
        week_id: weekId,
        version: `Version${BASELINE_LOCK}`,
        status: deployNote.action || "deploy_note",
        decision: deployNote.decision || decisionVal,
        approval_id: deployNote.approval_id || null,
        production_auto_apply: deployNote.production_auto_apply === true,
        path: `/ops-data/artifacts/${weekId}/deploy-note.json`,
        md_path: existsSync(join(destWeek, "deploy-note.md"))
          ? `/ops-data/artifacts/${weekId}/deploy-note.md`
          : null,
        updated_at: deployNote.created_at || deployNote.updated_at || null,
      });
    }

    searchDocs.push({
      type: "week",
      id: weekId,
      week_id: weekId,
      version: `Version${BASELINE_LOCK}`,
      status: decisionVal || null,
      decision: decisionVal,
      proposal: null,
      pattern: null,
      path: `/ops-data/artifacts/${weekId}/`,
    });
    if (decisionVal) {
      searchDocs.push({
        type: "decision",
        id: `${weekId}:decision`,
        week_id: weekId,
        version: `Version${BASELINE_LOCK}`,
        status: decisionVal,
        decision: decisionVal,
        proposal: null,
        pattern: null,
        path: `/ops-data/artifacts/${weekId}/decision.json`,
      });
    }
  }

  // Approval history
  const items = Array.isArray(approvals.items) ? approvals.items : [];
  for (const a of items) {
    const status = a.status || null;
    const isTimeout =
      status === "rejected" &&
      (a.auto === true || a.reason === "approval_timeout");
    history.approval.push({
      approval_id: a.approval_id,
      week_id: a.week_id || null,
      version: a.baseline_lock || `Version${BASELINE_LOCK}`,
      proposal_ids: a.proposal_ids || [],
      decision: a.decision || null,
      status: isTimeout ? "timeout" : status,
      reason: a.reason || null,
      auto: a.auto === true,
      created_at: a.created_at || null,
      expires_at: a.expires_at || null,
      updated_at: a.updated_at || a.resolved_at || null,
    });
    searchDocs.push({
      type: "proposal",
      id: a.approval_id,
      week_id: a.week_id || null,
      version: a.baseline_lock || `Version${BASELINE_LOCK}`,
      status: isTimeout ? "timeout" : status,
      decision: a.decision || null,
      proposal: (a.proposal_ids || []).join(","),
      pattern: null,
      path: null,
    });
  }

  // Research phase history
  if (Array.isArray(phaseHistory)) {
    for (const h of phaseHistory.slice(-100)) {
      history.research.push({
        week_id: h.week_id || null,
        version: `Version${BASELINE_LOCK}`,
        phase: h.phase || null,
        decision: null,
        status: h.ok === false ? "FAIL" : h.ok === true ? "PASS" : null,
        started_at: h.started_at || null,
        ended_at: h.ended_at || null,
        duration_ms: h.duration_ms ?? null,
        path: null,
        updated_at: h.ended_at || h.started_at || null,
      });
    }
  }

  // Timeline
  const phases = (state && state.phases) || {};
  const phaseOrder = [
    ["analyzer", "Proposal"],
    ["proposal", "Proposal"],
    ["validation", "Validation"],
    ["canary", "Canary"],
    ["baseline", "285R"],
    ["decision", "Decision"],
    ["knowledge", "Knowledge"],
    ["governance", "Governance"],
    ["report", "Report"],
  ];
  const steps = [];
  const lastRun = state?.last_run_at || null;
  steps.push({
    key: "runner_start",
    label: "Runner Start",
    started_at: lastRun,
    ended_at: lastRun,
    duration_ms: 0,
    result: lastRun ? "PASS" : "Skip",
  });
  for (const [id, label] of phaseOrder) {
    const ph = phases[id] || {};
    steps.push({
      key: id,
      label,
      started_at: ph.started_at || null,
      ended_at: ph.ended_at || null,
      duration_ms: ph.duration_ms ?? null,
      result: phaseStatus(ph),
      exit_reason: ph.exit_reason || null,
    });
  }
  const pubAt = now.toISOString();
  steps.push({
    key: "publish",
    label: "Publish",
    started_at: pubAt,
    ended_at: pubAt,
    duration_ms: 0,
    result: "PASS",
  });
  steps.push({
    key: "approval_queue",
    label: "Approval Queue",
    started_at: null,
    ended_at: null,
    duration_ms: null,
    result: items.length ? "PASS" : "Skip",
  });
  steps.push({
    key: "deploy_note",
    label: "Deploy Note",
    started_at: null,
    ended_at: null,
    duration_ms: null,
    result: history.deploy.length ? "PASS" : "Skip",
  });
  steps.push({
    key: "completed",
    label: "Completed",
    started_at: pubAt,
    ended_at: pubAt,
    duration_ms: 0,
    result: "PASS",
  });

  const timeline = {
    schema_version: "expect-v89-timeline/1.0",
    published_at: pubAt,
    week_id: state?.week_id || weekIdJst(now),
    baseline_lock: state?.baseline_lock || `Version${BASELINE_LOCK}`,
    next_run: state?.next_run_jst || null,
    last_run: lastRun,
    steps,
  };

  const audit = {
    schema_version: "expect-v89-console-audit/1.0",
    published_at: pubAt,
    cards: [
      {
        card: "Current Week",
        display: "portal.research.week_id",
        api: "/api/ops/portal",
        publish: "/ops-data/portal-snapshot.json",
        runner: "v8:runner → publishOpsSnapshot",
        source: "development/scheduler/weekly-runner.json",
      },
      {
        card: "Next Run",
        display: "portal.research.next_run",
        api: "/api/ops/portal|/api/ops/research-scheduler",
        publish: "/ops-data/research-scheduler.json",
        runner: "nextRunHintJst / publishScheduler",
        source: "development/scheduler/weekly-runner.json",
      },
      {
        card: "Approval Queue",
        display: "approval-queue items",
        api: "/api/ops/approvals",
        publish: "/ops-data/approval-queue.json",
        runner: "approval-queue + publishApprovals",
        source: "development/approvals/",
      },
      {
        card: "Deploy Note",
        display: "portal.deploy.deploy_note",
        api: "/api/ops/portal",
        publish: "/ops-data/deploy.json",
        runner: "approve → deploy-note → publishDeploy",
        source: "development/weekly/*/sat-deploy/",
      },
      {
        card: "Knowledge",
        display: "portal.knowledge.*",
        api: "/api/ops/portal",
        publish: "/ops-data/knowledge.json",
        runner: "publishKnowledge",
        source: "development/knowledge/",
      },
      {
        card: "Weekly Report",
        display: "portal.reports.weekly_report",
        api: "/api/ops/portal",
        publish: "/ops-data/reports.json",
        runner: "publishReports",
        source: "development/weekly/*/reports/",
      },
      {
        card: "PI / AI / Pages",
        display: "Live Monitor",
        api: "/api/health|/api/ops/monitor-live",
        publish: null,
        runner: null,
        source: "live health probes",
      },
      {
        card: "ResultAutomation",
        display: "run.status",
        api: "/api/ops/result-automation",
        publish: null,
        runner: null,
        source: "AI /v1/admin/results/status (read-only)",
      },
      {
        card: "Runner Timeline",
        display: "timeline.steps",
        api: "/api/ops/timeline",
        publish: "/ops-data/timeline.json",
        runner: "weekly-runner phases + publish",
        source: "development/scheduler/",
      },
    ],
  };

  const searchIndex = {
    schema_version: "expect-v89-search-index/1.0",
    published_at: pubAt,
    docs: searchDocs,
  };

  writeJson(join(ops, "history.json"), history);
  writeJson(join(ops, "timeline.json"), timeline);
  writeJson(join(ops, "evidence-index.json"), evidence);
  writeJson(join(ops, "console-audit.json"), audit);
  writeJson(join(ops, "search-index.json"), searchIndex);

  return {
    ok: true,
    files: [
      "public/ops-data/history.json",
      "public/ops-data/timeline.json",
      "public/ops-data/evidence-index.json",
      "public/ops-data/console-audit.json",
      "public/ops-data/search-index.json",
    ],
    counts: {
      weeks: weekIds.length,
      evidence: evidence.items.length,
      approvals: history.approval.length,
      search_docs: searchDocs.length,
    },
  };
}
