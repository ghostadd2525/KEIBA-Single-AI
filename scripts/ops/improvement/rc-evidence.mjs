#!/usr/bin/env node
/**
 * I-5 RC Gate CLI — Canary Result 正本で RC + Manifest 生成。
 *
 * Usage:
 *   npm run improve:rc -- --proposal IMP-20260719-miss-001
 *   npm run improve:rc -- --proposal IMP-... --date 2026-07-19
 *   npm run improve:rc -- --proposal IMP-... --skip-lifecycle
 */
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import { scanEvidence } from "./lib/scan.mjs";
import { tryEmitReleaseCandidate, validateRcManifest } from "./lib/rc.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..", "..");
const DEV_ROOT = join(REPO, "development");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function runIdNow() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "Z";
}

function repoRootFromEvidence(evidenceRoot) {
  const norm = evidenceRoot.replace(/\\/g, "/").replace(/\/$/, "");
  if (norm.endsWith("evidence/improvement")) {
    return join(evidenceRoot, "..", "..");
  }
  return REPO;
}

function main() {
  const proposalId = arg("--proposal", null);
  if (!proposalId) {
    console.error("Usage: npm run improve:rc -- --proposal IMP-YYYYMMDD-type-001");
    return 1;
  }

  const dateFilter = arg("--date", null);
  const evidenceRoot = arg("--evidence-root", join(REPO, "evidence", "improvement"));
  const repoRoot = arg("--repo-root", repoRootFromEvidence(evidenceRoot));
  const devRoot = arg("--dev-root", DEV_ROOT);
  const skipLifecycle = process.argv.includes("--skip-lifecycle");
  const kpiRegression = process.argv.includes("--kpi-regression");
  const runId = runIdNow();

  const scan = scanEvidence(evidenceRoot, dateFilter);

  const outcome = tryEmitReleaseCandidate({
    devRoot,
    repoRoot,
    proposalId,
    runId,
    scan,
    applyLifecycle: !skipLifecycle,
    by: "improve:rc",
    kpiRegressionEnabled: kpiRegression,
  });

  const summary = {
    schema_version: "expect-rc-run/1.0",
    phase: "I-5",
    run_id: runId,
    generated_at: new Date().toISOString(),
    proposal_id: proposalId,
    status: outcome.status,
    rc_eligible: outcome.rc_eligible ?? false,
    result_id: outcome.result_id || null,
    manifest_id: outcome.manifest_id || null,
    canary_result_path: outcome.canary_result_path || null,
    manifest_path: outcome.manifest_path || null,
    rejection_reasons: outcome.rejection_reasons || [],
    notes: [
      "RC verdict sourced from Canary Result on disk — not inferred from Proposal.",
      "Structural gates: canary_verdict_eligible, human_review_approved, evidence_refs_valid, lifecycle_canary_pass.",
      skipLifecycle ? "Lifecycle transition skipped (--skip-lifecycle)." : null,
    ].filter(Boolean),
  };

  if (outcome.manifest) {
    const v = validateRcManifest(outcome.manifest);
    summary.manifest_valid = v.ok;
    if (!v.ok) summary.manifest_validation_errors = v.errors;
  }

  const runDir = join(devRoot, "runs", runId);
  mkdirSync(runDir, { recursive: true });
  writeFileSync(join(runDir, "rc-summary.json"), JSON.stringify(summary, null, 2) + "\n", "utf8");
  writeFileSync(
    join(devRoot, "runs", "latest-rc-summary.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );

  console.log(JSON.stringify(summary, null, 2));
  return outcome.status === "rejected" || outcome.status === "error" ? 1 : 0;
}

process.exit(main());
