#!/usr/bin/env node
/**
 * Version8.2 — Canary in Validation-Pass × Priority order.
 *
 * Flow: Ranking → Validation Gate → Canary (eligible only)
 * Failures are recorded as gate_blocked (not Canary-evaluated).
 */
import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { assertResearchDay, repoRoot, weekIdJst } from "./calendar.mjs";
import { rankProposals } from "./rank-proposals.mjs";
import {
  validateProposals,
  loadCanaryEligible,
} from "./proposal-validate.mjs";

const REPO = repoRoot();

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function main() {
  if (!process.argv.includes("--allow-weekend")) {
    assertResearchDay({ purpose: "v8.2:canary-ranked" });
  }
  const weekId = arg("--week-id", weekIdJst());
  const devRoot = arg("--dev-root", join(REPO, "development"));

  // Ensure ranking + fresh validation
  rankProposals({ week_id: weekId, devRoot });
  const validation = validateProposals({ week_id: weekId, devRoot });
  const eligible =
    loadCanaryEligible(devRoot) || validation.canary_eligible || [];
  const blocked = (validation.validations || []).filter((v) => v.gate === "fail");

  const results = [];

  for (const v of blocked) {
    results.push({
      priority: v.priority,
      proposal: v.proposal,
      status: "gate_blocked",
      validation_score: v.validation_score,
      gate: "fail",
      warnings: v.warnings || [],
      note: "Validation Score below gate — not sent to Canary.",
    });
  }

  for (const row of eligible) {
    const ids = row.proposal_ids || [];
    if (!ids.length) {
      results.push({
        priority: row.priority,
        proposal: row.proposal,
        status: "deferred_no_imp_id",
        validation_score: row.validation_score,
        gate: "pass",
        note: "Passed Validation; create/link IMP-* before Canary eval.",
      });
      continue;
    }
    for (const proposalId of ids) {
      const r = spawnSync(
        process.execPath,
        [
          join(REPO, "scripts/ops/improvement/canary-evidence.mjs"),
          "--proposal",
          proposalId,
          "--skip-lifecycle",
        ],
        { cwd: REPO, encoding: "utf8" }
      );
      let verdict = null;
      try {
        const j = JSON.parse(r.stdout || "{}");
        verdict = j.verdict || null;
      } catch {
        /* ignore */
      }
      results.push({
        priority: row.priority,
        proposal: row.proposal,
        proposal_id: proposalId,
        status: r.status === 0 ? "evaluated" : "failed",
        exit_code: r.status,
        verdict,
        validation_score: row.validation_score,
        gate: "pass",
      });
    }
  }

  // Sort results: gate_blocked first by priority then evaluated
  results.sort((a, b) => (a.priority || 99) - (b.priority || 99));

  const doc = {
    schema_version: "expect-v82-canary-ranked/1.0",
    week_id: weekId,
    evaluated_at: new Date().toISOString(),
    gate_threshold: validation.gate_threshold,
    order: eligible.map((r) => r.proposal),
    blocked: blocked.map((v) => v.proposal),
    results,
    validation_summary: validation.summary,
    pe_ce_untouched: true,
  };

  const wed = join(devRoot, "weekly", weekId, "wed-canary");
  mkdirSync(wed, { recursive: true });
  writeFileSync(join(wed, "ranked-run.json"), JSON.stringify(doc, null, 2) + "\n", "utf8");
  mkdirSync(join(devRoot, "runs"), { recursive: true });
  writeFileSync(
    join(devRoot, "runs", "latest-canary-ranked.json"),
    JSON.stringify(doc, null, 2) + "\n",
    "utf8"
  );
  console.log(JSON.stringify(doc, null, 2));
}

try {
  main();
} catch (e) {
  console.error(e && e.message ? e.message : e);
  process.exit(e && e.code === "V8_RESEARCH_WEEKEND_BLOCKED" ? 3 : 1);
}
