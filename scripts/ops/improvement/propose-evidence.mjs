#!/usr/bin/env node
/**
 * I-3 Proposal Generator CLI
 *
 * Evidence → (Index) → Analyzer → Proposal (DRAFT) + Lifecycle
 * Does not mutate Production / Prediction Core.
 *
 * Usage:
 *   npm run improve:propose
 *   npm run improve:propose -- --date 2026-07-19
 *   npm run improve:propose -- --event-type miss
 *   npm run improve:propose -- --cluster sha256:...
 *   npm run improve:propose -- --reuse-analysis
 */
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { scanEvidence } from "./lib/scan.mjs";
import { buildIndex } from "./lib/index.mjs";
import { runAnalyzers, REGISTERED_EVENT_TYPES } from "./lib/analyzers.mjs";
import {
  createProposals,
  validateProposal,
  CONFIDENCE_POLICY,
} from "./lib/proposals.mjs";

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

/**
 * @param {string} devRoot
 * @param {string[]} eventTypes
 */
function loadLatestAnalyses(devRoot, eventTypes) {
  /** @type {Record<string, object>} */
  const out = {};
  for (const et of eventTypes) {
    const path = join(devRoot, "analysis", et, "latest.json");
    if (!existsSync(path)) continue;
    try {
      out[et] = JSON.parse(readFileSync(path, "utf8"));
    } catch {
      /* skip broken */
    }
  }
  return out;
}

function main() {
  const dateFilter = arg("--date", null);
  const evidenceRoot = arg("--evidence-root", join(REPO, "evidence", "improvement"));
  const devRoot = arg("--dev-root", join(REPO, "development"));
  const eventTypeArg = arg("--event-type", null);
  const cluster = arg("--cluster", null);
  const reuseAnalysis = process.argv.includes("--reuse-analysis");
  const skipIndex = process.argv.includes("--skip-index");
  const runId = runIdNow();

  const eventTypes = eventTypeArg
    ? [eventTypeArg]
    : [...REGISTERED_EVENT_TYPES];

  const scan = scanEvidence(evidenceRoot, dateFilter);

  /** @type {object | null} */
  let index = null;
  if (!skipIndex) {
    index = buildIndex(scan, devRoot, dateFilter);
  } else if (existsSync(join(devRoot, "index", "latest.json"))) {
    index = JSON.parse(readFileSync(join(devRoot, "index", "latest.json"), "utf8"));
  } else {
    index = {
      filter_date: dateFilter,
      dates: [],
      events: scan.events,
      counts_by_event_type: scan.countsByType,
    };
  }

  if (scan.total === 0) {
    const summary = {
      schema_version: "expect-proposal-run/1.0",
      phase: "I-3",
      run_id: runId,
      generated_at: new Date().toISOString(),
      corpus_status: "empty",
      evidence_count: 0,
      proposal_count: 0,
      proposal_ids: [],
      confidence_policy: CONFIDENCE_POLICY,
      notes: [
        "No evidence — no Proposal created.",
        "Prediction Core unchanged.",
      ],
    };
    writeRunSummary(devRoot, runId, summary);
    console.log(JSON.stringify(summary, null, 2));
    return 0;
  }

  /** @type {Record<string, object>} */
  let analyses;
  if (reuseAnalysis) {
    analyses = loadLatestAnalyses(devRoot, eventTypes);
    if (!Object.keys(analyses).length) {
      analyses = runAnalyzers(scan, devRoot, runId);
    }
  } else {
    analyses = runAnalyzers(scan, devRoot, runId);
  }

  const proposals = createProposals(analyses, index, devRoot, runId, {
    eventTypes: eventTypeArg ? [eventTypeArg] : undefined,
    fingerprint: cluster,
    author: "improve:propose",
  });

  const validations = proposals.map((p) => ({
    proposal_id: p.proposal_id,
    ...validateProposal(p),
  }));

  const summary = {
    schema_version: "expect-proposal-run/1.0",
    phase: "I-3",
    run_id: runId,
    generated_at: new Date().toISOString(),
    corpus_status: "populated",
    evidence_count: scan.total,
    counts_by_event_type: scan.countsByType,
    proposal_count: proposals.length,
    proposal_ids: proposals.map((p) => p.proposal_id),
    proposals: proposals.map((p) => ({
      proposal_id: p.proposal_id,
      status: p.status,
      event_types: p.event_types,
      evidence_ref_count: p.evidence_refs.length,
      analysis_ref_count: (p.analysis_refs || []).length,
      analyzer_confidence: p.metadata?.analyzer_confidence ?? null,
      review_priority_hint: p.metadata?.review_priority_hint ?? null,
    })),
    validations,
    confidence_policy: CONFIDENCE_POLICY,
    outputs: proposals.map((p) => `development/proposals/${p.proposal_id}.json`),
    notes: [
      "Proposals created as DRAFT with embedded Lifecycle.",
      "evidence_refs enforced (min 1).",
      "analysis_refs point at Analyzer outputs; confidence is advisory only.",
      "Human Review required before APPROVED / Canary.",
      "Next: I-4 Canary (after Lifecycle review of I-3).",
    ],
  };

  writeRunSummary(devRoot, runId, summary);
  console.log(JSON.stringify(summary, null, 2));
  return 0;
}

function writeRunSummary(devRoot, runId, summary) {
  const runDir = join(devRoot, "runs", runId);
  mkdirSync(runDir, { recursive: true });
  writeFileSync(
    join(runDir, "propose-summary.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );
  writeFileSync(
    join(devRoot, "runs", "latest-propose-summary.json"),
    JSON.stringify(summary, null, 2) + "\n",
    "utf8"
  );
}

process.exit(main());
