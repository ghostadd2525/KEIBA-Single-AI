#!/usr/bin/env node
/**
 * Version8 Thursday — 285R Baseline comparison (offline, no PE change).
 *
 * Reads formal 285R fixture summary + latest canary/analysis signals,
 * writes thu-baseline/report.json. Does not mutate Production DB.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { assertResearchDay, repoRoot, weekIdJst } from "./calendar.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = repoRoot();

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function loadBaselineFixture() {
  const path = join(REPO, "fixtures", "stats", "baseline-285r-evaluations.json");
  if (!existsSync(path)) {
    return { ok: false, reason: "baseline fixture missing", path };
  }
  const doc = JSON.parse(readFileSync(path, "utf8"));
  const rows = Array.isArray(doc.evaluations)
    ? doc.evaluations
    : Array.isArray(doc.rows)
      ? doc.rows
      : [];
  let hits = 0;
  for (const r of rows) {
    if (r.hit_at_1 === 1 || r.hit_at_1 === true) hits += 1;
  }
  const n = rows.length || Number(doc.n) || 0;
  const hitRate = n ? Math.round((hits / n) * 10000) / 10000 : null;
  return {
    ok: true,
    path,
    baseline_id: doc.baseline_id || "formal-285r-offline-corpus",
    n: n || Number(doc.n) || 285,
    hits: hits || Number(doc.hits) || null,
    hit_rate: hitRate ?? doc.hit_rate ?? null,
    metric: doc.metric || "formal_v2_pe_baseline_hit",
  };
}

function loadCanarySummary() {
  const latestRun = join(REPO, "development", "runs", "latest-execution-summary.json");
  if (!existsSync(latestRun)) return null;
  try {
    return JSON.parse(readFileSync(latestRun, "utf8"));
  } catch {
    return null;
  }
}

function main() {
  if (!process.argv.includes("--allow-weekend")) {
    assertResearchDay({ purpose: "v8:thu-baseline" });
  }
  const weekRoot =
    arg("--week-root", "") ||
    join(REPO, "development", "weekly", arg("--week-id", weekIdJst()));
  const outDir = join(weekRoot, "thu-baseline");
  mkdirSync(outDir, { recursive: true });

  const baseline = loadBaselineFixture();
  const canary = loadCanarySummary();

  // Without a PE-mutating canary implementation, delta is informational.
  // Scaffold records "no_measured_delta" so Friday can choose no_improvement safely.
  const report = {
    schema_version: "expect-v8-baseline-report/1.0",
    week_id: arg("--week-id", weekIdJst()),
    generated_at: new Date().toISOString(),
    baseline,
    canary_execution_summary: canary
      ? {
          schema_version: canary.schema_version || null,
          status: canary.status || null,
          release_candidates: canary.release_candidates ?? null,
          note: "Offline canary summary only — PE not modified.",
        }
      : null,
    comparison: {
      method: "fixture_holdout_reference",
      pe_mutated: false,
      measured_delta_hit_at_1: null,
      verdict: "no_measured_delta",
      note:
        "Version8 scaffold compares against 285R fixture metadata. " +
        "A Proposal that changes Core must supply canary metrics in a follow-up PR; " +
        "until then Friday defaults to no_improvement / reject-safe hold.",
    },
    ok: true,
  };

  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2) + "\n", "utf8");
  console.log(JSON.stringify({ event: "v8_baseline_done", path: join(outDir, "report.json"), ok: true }, null, 2));
}

try {
  main();
} catch (e) {
  console.error(e && e.message ? e.message : e);
  process.exit(e && e.code === "V8_RESEARCH_WEEKEND_BLOCKED" ? 3 : 1);
}
