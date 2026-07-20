#!/usr/bin/env node
/**
 * I-1 Evidence Index CLI
 *
 * Reads evidence/improvement (Production output, read-only).
 * Writes development/index only (Development).
 *
 *   development/index/by-model-version/{model_version|unknown}.json
 *   development/index/clusters/{cluster_id}.json
 *
 * Usage:
 *   npm run improve:index
 *   npm run improve:index -- --date 2026-07-19
 *   node scripts/ops/improvement/index-evidence.mjs --evidence-root <path> --dev-root <path>
 */
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { scanEvidence } from "./lib/scan.mjs";
import { buildIndex } from "./lib/index.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..", "..");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function main() {
  const dateFilter = arg("--date", null);
  const evidenceRoot = arg("--evidence-root", join(REPO, "evidence", "improvement"));
  const devRoot = arg("--dev-root", join(REPO, "development"));

  const scan = scanEvidence(evidenceRoot, dateFilter);
  const index = buildIndex(scan, devRoot, dateFilter);

  const summary = {
    schema_version: "expect-evidence-index-run/1.0",
    phase: "I-1",
    generated_at: index.generated_at,
    source_root: evidenceRoot,
    output_root: join(devRoot, "index"),
    filter_date: dateFilter,
    corpus_status: index.corpus_status,
    evidence_count: index.event_total,
    counts_by_event_type: index.counts_by_event_type,
    cluster_count: index.clusters.length,
    dates: index.dates,
    outputs: [
      "development/index/latest.json",
      "development/index/by-event-type/summary.json",
      ...index.dates.map((d) => `development/index/by-date/${d}.json`),
      ...Object.keys(index.counts_by_event_type || {})
        .filter((t) => (index.counts_by_event_type[t] || 0) > 0)
        .map((t) => `development/index/by-event-type/${t}.json`),
      ...index.clusters.map((c) => `development/index/clusters/${c.cluster_id}.json`),
    ],
    notes:
      index.event_total === 0
        ? ["No evidence found — empty index written. Proposal/Canary not run (I-1 scope)."]
        : ["Evidence Index updated. Next: I-2 Analyzer Registry."],
  };

  console.log(JSON.stringify(summary, null, 2));
  return index.event_total === 0 ? 0 : 0;
}

process.exit(main());
