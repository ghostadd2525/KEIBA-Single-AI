#!/usr/bin/env node
/**
 * I-2 Analyzer Registry CLI
 *
 * Reads evidence/improvement (or reuses Index scan).
 * Writes development/analysis/{event_type}/ only.
 *
 * Usage:
 *   npm run improve:analyze
 *   npm run improve:analyze -- --date 2026-07-19
 *   node scripts/ops/improvement/analyze-evidence.mjs --evidence-root <path> --dev-root <path>
 */
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import { scanEvidence } from "./lib/scan.mjs";
import { buildIndex } from "./lib/index.mjs";
import { runAnalyzers, REGISTERED_EVENT_TYPES } from "./lib/analyzers.mjs";

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
  const dateFilter = arg("--date", null);
  const evidenceRoot = arg("--evidence-root", join(REPO, "evidence", "improvement"));
  const devRoot = arg("--dev-root", join(REPO, "development"));
  const skipIndex = process.argv.includes("--skip-index");
  const runId = runIdNow();

  const scan = scanEvidence(evidenceRoot, dateFilter);

  if (!skipIndex) {
    buildIndex(scan, devRoot, dateFilter);
  }

  if (scan.total === 0) {
    const summary = {
      schema_version: "expect-analyzer-run/1.0",
      phase: "I-2",
      run_id: runId,
      generated_at: new Date().toISOString(),
      corpus_status: "empty",
      evidence_count: 0,
      analyzers_registered: REGISTERED_EVENT_TYPES,
      analyses: {},
      notes: [
        "No evidence — Analyzer not executed. No Proposal created (I-2 scope).",
      ],
    };
    const runDir = join(devRoot, "runs", runId);
    mkdirSync(runDir, { recursive: true });
    writeFileSync(
      join(runDir, "analyze-summary.json"),
      JSON.stringify(summary, null, 2) + "\n",
      "utf8"
    );
    console.log(JSON.stringify(summary, null, 2));
    return 0;
  }

  const analyses = runAnalyzers(scan, devRoot, runId);

  const summary = {
    schema_version: "expect-analyzer-run/1.0",
    phase: "I-2",
    run_id: runId,
    generated_at: new Date().toISOString(),
    corpus_status: "populated",
    evidence_count: scan.total,
    counts_by_event_type: scan.countsByType,
    analyzers_registered: REGISTERED_EVENT_TYPES,
    analyses: Object.fromEntries(
      Object.entries(analyses).map(([et, a]) => [
        et,
        {
          analysis_id: a.analysis_id,
          status: a.status,
          root_cause: a.root_cause,
          confidence: a.confidence,
          reason: a.reason,
          event_count: a.event_count,
          evidence_ref_count: (a.evidence_refs || []).length,
        },
      ])
    ),
    outputs: Object.keys(analyses).map(
      (et) => `development/analysis/${et}/latest.json`
    ),
    notes: ["Analyzer Registry complete. Next: I-3 Proposal (done) / I-4 Canary."],
  };

  const runDir = join(devRoot, "runs", runId);
  mkdirSync(runDir, { recursive: true });
  writeFileSync(
    join(runDir, "analyze-summary.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );
  writeFileSync(
    join(devRoot, "runs", "latest-analyze-summary.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );

  console.log(JSON.stringify(summary, null, 2));
  return 0;
}

process.exit(main());
