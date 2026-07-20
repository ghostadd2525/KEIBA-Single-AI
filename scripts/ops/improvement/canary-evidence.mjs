#!/usr/bin/env node
/**
 * I-4 Canary CLI — Proposal → independent Canary Result + Lifecycle (status only).
 *
 * Usage:
 *   npm run improve:canary -- --proposal IMP-20260719-miss-001
 *   npm run improve:canary -- --proposal IMP-... --date 2026-07-19
 *   npm run improve:canary -- --proposal IMP-... --skip-lifecycle
 */
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import { scanEvidence } from "./lib/scan.mjs";
import { buildIndex } from "./lib/index.mjs";
import {
  loadProposal,
  runCanaryForProposal,
  CanaryVerdict,
  isCanaryRcEligible,
} from "./lib/canary.mjs";
import { isHumanReviewApproved } from "./lib/proposals.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..", "..");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function runIdNow() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "Z";
}

function main() {
  const proposalId = arg("--proposal", null);
  if (!proposalId) {
    console.error("Usage: npm run improve:canary -- --proposal IMP-YYYYMMDD-type-001");
    return 1;
  }

  const dateFilter = arg("--date", null);
  const evidenceRoot = arg("--evidence-root", join(REPO, "evidence", "improvement"));
  const devRoot = arg("--dev-root", join(REPO, "development"));
  const skipLifecycle = process.argv.includes("--skip-lifecycle");
  const runId = runIdNow();

  const { proposal } = loadProposal(devRoot, proposalId);
  const scan = scanEvidence(evidenceRoot, dateFilter);
  const index = buildIndex(scan, devRoot, dateFilter);

  const outcome = runCanaryForProposal(proposal, index, scan, devRoot, runId, {
    isApproved: (id) => isHumanReviewApproved(devRoot, id),
    applyLifecycle: !skipLifecycle,
    by: "improve:canary",
  });

  const summary = {
    schema_version: "expect-canary-run/1.0",
    phase: "I-4",
    run_id: runId,
    generated_at: new Date().toISOString(),
    proposal_id: proposalId,
    result_id: outcome.result_id,
    verdict: outcome.verdict,
    evaluation_status: outcome.status,
    rc_eligible: isCanaryRcEligible(outcome.verdict),
    pass: outcome.pass,
    result_path: outcome.result_path,
    lifecycle_applied: outcome.lifecycle_applied || outcome.result?.lifecycle_applied || null,
    verdicts_supported: Object.values(CanaryVerdict),
    notes: [
      "Canary Result is independent artifact under development/canary/results/{proposal_id}/",
      "Proposal content unchanged — only status/lifecycle/metadata canary pointers updated when lifecycle applied.",
      skipLifecycle ? "Lifecycle transition skipped (--skip-lifecycle)." : null,
    ].filter(Boolean),
  };

  const runDir = join(devRoot, "runs", runId);
  mkdirSync(runDir, { recursive: true });
  writeFileSync(join(runDir, "canary-summary.json"), JSON.stringify(summary, null, 2) + "\n", "utf8");
  writeFileSync(
    join(devRoot, "runs", "latest-canary-summary.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );

  console.log(JSON.stringify(summary, null, 2));
  return 0;
}

process.exit(main());
