#!/usr/bin/env node
/**
 * Version8 Friday — Accept / Reject / No Improvement.
 *
 * Reject and no_improvement are successful process outcomes (ok: true).
 * Only accept + promote_to_production unlocks sat-deploy.
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { assertResearchDay, repoRoot, weekIdJst } from "./calendar.mjs";
import { upsertWeeklyHistory } from "./weekly-history.mjs";
import { validationKnowledgePayload } from "./proposal-validate.mjs";
import { maybeEnqueueFromDecision } from "./approval-queue.mjs";

const REPO = repoRoot();

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function listProposalIds() {
  const dir = join(REPO, "development", "proposals");
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json") && !f.startsWith("_"))
    .map((f) => f.replace(/\.json$/, ""));
}

function readJson(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function main() {
  if (!process.argv.includes("--allow-weekend")) {
    assertResearchDay({ purpose: "v8:fri-decide" });
  }
  const weekId = arg("--week-id", weekIdJst());
  const weekRoot =
    arg("--week-root", "") || join(REPO, "development", "weekly", weekId);
  const outDir = join(weekRoot, "fri-decision");
  mkdirSync(outDir, { recursive: true });

  const force = arg("--decision", ""); // accept|reject|no_improvement optional override
  const baseline = readJson(join(weekRoot, "thu-baseline", "report.json"));
  const exec = readJson(join(REPO, "development", "runs", "latest-execution-summary.json"));
  const proposalIds = listProposalIds();

  let decision = "no_improvement";
  let reason = "Default hold: no PE-measured baseline delta in Version8 scaffold.";
  let canaryPass = null;
  let promote = false;

  if (exec && String(exec.status || "").toLowerCase().includes("no improvement")) {
    decision = "no_improvement";
    reason = "Improvement cycle reported No Improvement Required (0 evidence or empty gate).";
  }

  if (baseline && baseline.comparison && baseline.comparison.verdict === "no_measured_delta") {
    decision = "no_improvement";
    reason =
      "285R baseline report has no measured PE delta. Holding current Version is success.";
  }

  // If RC count > 0 from improve cycle, still require explicit human accept override.
  const rcCount = Number(exec && exec.release_candidates != null ? exec.release_candidates : 0);
  if (rcCount > 0) {
    decision = "reject";
    reason =
      `Release candidates=${rcCount} but Friday auto-gate requires human Accept override ` +
      `(--decision accept). Default reject keeps Production safe.`;
    canaryPass = true;
  }

  if (force === "accept" || force === "reject" || force === "no_improvement") {
    decision = force;
    reason = `Operator override --decision ${force}`;
    promote = force === "accept";
  }

  const doc = {
    schema_version: "expect-v8-week-decision/1.0",
    week_id: weekId,
    decided_at: new Date().toISOString(),
    decision,
    ok: true,
    reason,
    baseline_id:
      (baseline && baseline.baseline && baseline.baseline.baseline_id) ||
      "formal-285r-offline-corpus",
    proposal_ids: proposalIds,
    canary_pass: canaryPass,
    baseline_delta:
      (baseline && baseline.comparison && baseline.comparison.measured_delta_hit_at_1) ?? null,
    promote_to_production: promote,
    rules: {
      no_improvement_is_success: true,
      reject_is_success: true,
      accept_requires_human_override_or_review: true,
      pe_ce_untouched: true,
    },
  };

  writeFileSync(join(outDir, "decision.json"), JSON.stringify(doc, null, 2) + "\n", "utf8");

  // Version8.8 — Approval Queue（全ゲート PASS の accept+promote のみ）
  const enqueueResult = maybeEnqueueFromDecision({
    week_id: weekId,
    weekRoot,
    decision: doc,
  });
  doc.approval_enqueue = {
    enqueued: !!enqueueResult.enqueued,
    approval_id: enqueueResult.approval_id || null,
    reason: enqueueResult.reason || null,
    gates: enqueueResult.gates || null,
  };
  writeFileSync(join(outDir, "decision.json"), JSON.stringify(doc, null, 2) + "\n", "utf8");

  // Version8.1/8.2 — Weekly Knowledge
  const hitDelta =
    baseline &&
    baseline.comparison &&
    typeof baseline.comparison.measured_delta_hit_at_1 === "number"
      ? Math.round(baseline.comparison.measured_delta_hit_at_1 * 100)
      : doc.baseline_delta != null && typeof doc.baseline_delta === "number"
        ? Math.round(doc.baseline_delta * 100)
        : null;
  const validationDoc =
    readJson(join(weekRoot, "tue-proposal", "proposal-validation.json")) ||
    readJson(join(REPO, "development", "analysis", "proposal-validation.json"));
  const knowledge = validationKnowledgePayload(validationDoc, decision);
  const miss = readJson(join(REPO, "development", "analysis", "miss", "latest.json"));
  upsertWeeklyHistory({
    week: weekId,
    decision,
    hit_delta: hitDelta,
    rank710_delta: null,
    primary_family: knowledge.root_cause || miss?.root_cause_family || null,
    root_cause: knowledge.root_cause || miss?.root_cause_family || null,
    validation_score: knowledge.validation_score,
    impact: knowledge.impact,
    proposals: knowledge.proposals,
    validation_pass_count: knowledge.validation_pass_count,
    validation_fail_count: knowledge.validation_fail_count,
    proposal_ids: proposalIds,
  });

  const manifestoPath = join(weekRoot, "manifesto.json");
  if (existsSync(manifestoPath)) {
    const m = JSON.parse(readFileSync(manifestoPath, "utf8"));
    m.decision = decision;
    m.updated_at = new Date().toISOString();
    if (m.stages && m.stages.fri_decision) {
      m.stages.fri_decision.status = "completed";
      m.stages.fri_decision.at = doc.decided_at;
    }
    writeFileSync(manifestoPath, JSON.stringify(m, null, 2) + "\n", "utf8");
  }

  console.log(JSON.stringify({ event: "v8_decide_done", ...doc }, null, 2));
}

try {
  main();
} catch (e) {
  console.error(e && e.message ? e.message : e);
  process.exit(e && e.code === "V8_RESEARCH_WEEKEND_BLOCKED" ? 3 : 1);
}
