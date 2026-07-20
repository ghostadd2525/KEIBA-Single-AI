#!/usr/bin/env node
/**
 * Phase AI-Core Operational Cycle
 *
 * evidence/improvement にイベントが存在する場合のみパイプライン実行。
 * 0 件 → "No Improvement Required" で終了（Proposal/Canary/RC なし）。
 *
 * Usage:
 *   node scripts/ops/improvement/run-cycle.mjs
 *   node scripts/ops/improvement/run-cycle.mjs --date 2026-07-19
 *   node scripts/ops/improvement/run-cycle.mjs --evidence-root path/to/improvement
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { scanEvidence } from "./lib/scan.mjs";
import { buildIndex } from "./lib/index.mjs";
import { runAnalyzers } from "./lib/analyzers.mjs";
import { createProposals, isHumanReviewApproved } from "./lib/proposals.mjs";
import { runCanary } from "./lib/canary.mjs";
import { emitReleaseCandidates, countReleaseCandidates } from "./lib/rc.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..", "..");
const DEV_ROOT = join(REPO, "development");
const DEFAULT_EVIDENCE = join(REPO, "evidence", "improvement");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function runIdNow() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "Z";
}

function buildSummary(payload) {
  return {
    schema_version: "expect-ai-core-execution/1.0",
    phase: "AI-Core Operational Cycle",
    run_id: payload.run_id,
    generated_at: new Date().toISOString(),
    verdict: payload.verdict,
    evidence_count: payload.evidence_count,
    evidence_by_type: payload.evidence_by_type,
    proposal_count: payload.proposal_count,
    proposal_ids: payload.proposal_ids || [],
    canary: payload.canary || [],
    release_candidate_count: payload.release_candidate_count,
    release_candidate_new: payload.release_candidate_new || [],
    steps_executed: payload.steps_executed || [],
    notes: payload.notes || [],
  };
}

function writeSummary(summary) {
  const runDir = join(DEV_ROOT, "runs", summary.run_id);
  mkdirSync(runDir, { recursive: true });
  const path = join(runDir, "execution-summary.json");
  writeFileSync(path, JSON.stringify(summary, null, 2) + "\n", "utf8");
  mkdirSync(join(DEV_ROOT, "runs"), { recursive: true });
  writeFileSync(
    join(DEV_ROOT, "runs", "latest-execution-summary.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );
  return path;
}

function main() {
  const dateFilter = arg("--date", null);
  const evidenceRoot = arg("--evidence-root", DEFAULT_EVIDENCE);
  const runId = runIdNow();

  const scan = scanEvidence(evidenceRoot, dateFilter);

  if (scan.total === 0) {
    const summary = buildSummary({
      run_id: runId,
      verdict: "No Improvement Required",
      evidence_count: 0,
      evidence_by_type: scan.countsByType,
      proposal_count: 0,
      proposal_ids: [],
      canary: [],
      release_candidate_count: countReleaseCandidates(DEV_ROOT),
      release_candidate_new: [],
      steps_executed: ["evidence_scan"],
      notes: [
        "evidence/improvement has 0 events — skipped Index, Analyzer, Proposal, Canary, RC.",
        "Prediction Core unchanged.",
      ],
    });
    const path = writeSummary(summary);
    console.log(JSON.stringify({ ...summary, execution_summary_path: path }, null, 2));
    return 0;
  }

  const steps = ["evidence_scan"];

  const index = buildIndex(scan, DEV_ROOT, dateFilter);
  steps.push("evidence_index");

  const analyses = runAnalyzers(scan, DEV_ROOT, runId);
  steps.push("analyzer");

  const proposals = createProposals(analyses, index, DEV_ROOT, runId);
  steps.push("proposal_create");

  const canaryResults = runCanary(
    proposals,
    index,
    scan,
    DEV_ROOT,
    (id) => isHumanReviewApproved(DEV_ROOT, id),
    runId
  );
  steps.push("canary");

  const rcBefore = countReleaseCandidates(DEV_ROOT);
  const rcNew = emitReleaseCandidates(canaryResults, DEV_ROOT, REPO, runId, scan);
  steps.push("release_candidate");

  const rcAfter = countReleaseCandidates(DEV_ROOT);
  const rcCreated = rcNew.filter((r) => r.status === "created");

  const verdict =
    rcCreated.length > 0
      ? "Improvement Pipeline Complete — RC Pending Deploy Review"
      : canaryResults.some((c) => c.status === "pending_human_review")
        ? "Improvement Pipeline — Pending Human Review"
        : canaryResults.some((c) => c.pass)
          ? "Improvement Pipeline Complete — RC Gates Not Passed"
          : "Improvement Pipeline Complete — No RC (Canary not pass)";

  const summary = buildSummary({
    run_id: runId,
    verdict,
    evidence_count: scan.total,
    evidence_by_type: scan.countsByType,
    proposal_count: proposals.length,
    proposal_ids: proposals.map((p) => p.proposal_id),
    canary: canaryResults.map((c) => ({
      proposal_id: c.proposal_id,
      verdict: c.verdict,
      status: c.status,
      pass: c.pass,
      result_id: c.result_id,
      result_path: c.result_path,
    })),
    release_candidate_count: rcAfter,
    release_candidate_new: rcCreated,
    steps_executed: steps,
    notes: [
      "Human Review: development/reviews/{proposal_id}.json status=approved required before Canary evaluates.",
      "RC Gate: Canary Result on disk + CANARY_PASS lifecycle + valid evidence_refs.",
      "Prediction Core unchanged by this cycle.",
      rcCreated.length === 0 && canaryResults.every((c) => !c.pass)
        ? "No RC emitted — approve proposals and re-run, or fix Canary failures."
        : rcCreated.length === 0 && canaryResults.some((c) => c.pass)
          ? "No RC emitted — RC gates not passed (check lifecycle CANARY_PASS, Human Review, evidence_refs)."
          : null,
    ].filter(Boolean),
  });

  const path = writeSummary(summary);
  console.log(JSON.stringify({ ...summary, execution_summary_path: path }, null, 2));
  return 0;
}

process.exit(main());
