/**
 * Version8.4 — Research Knowledge Base tests
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  computeKnowledgeScore,
  ensureKnowledgeBase,
  loadKnowledgeBase,
  similaritySearch,
  syncKnowledgeFromWeek,
  summarizeKnowledgeMetrics,
  proposalLabel,
} from "../../scripts/ops/v8/knowledge-base.mjs";
import {
  computeValidationScore,
  validateProposalRow,
} from "../../scripts/ops/v8/proposal-validate.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");

test("Knowledge Score: 4 accept / 1 reject → 0.82", () => {
  assert.equal(computeKnowledgeScore(4, 1), 0.82);
  assert.equal(computeKnowledgeScore(0, 0), 0.5);
});

test("ensureKnowledgeBase creates files", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v84-kb-"));
  const p = ensureKnowledgeBase(tmp);
  assert.ok(fs.existsSync(p.accepted_patterns));
  assert.ok(fs.existsSync(p.rejected_patterns));
  assert.ok(fs.existsSync(p.root_causes));
  assert.ok(fs.existsSync(p.proposals));
  assert.ok(fs.existsSync(p.canary_results));
  assert.ok(fs.existsSync(p.timeline));
});

test("similaritySearch detects past reject/accept", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v84-sim-"));
  ensureKnowledgeBase(tmp);
  const kb = loadKnowledgeBase(tmp);
  kb.accepted_patterns.patterns.push({
    pattern_id: "PAT-001",
    root_cause: "candidate_pool",
    proposal: "Entry Threshold Safe",
    accepted_week: "2026-W34",
    hit_delta: 2,
  });
  kb.rejected_patterns.patterns.push({
    pattern_id: "REJ-001",
    root_cause: "delete",
    proposal: "Delete Expansion",
    rejected_week: "2026-W30",
    reason: "285R Regression",
  });
  kb.proposals.proposals.candidate_pool = {
    family: "candidate_pool",
    accepted_count: 4,
    rejected_count: 1,
    knowledge_score: 0.82,
  };
  fs.writeFileSync(
    kb.paths.accepted_patterns,
    JSON.stringify(kb.accepted_patterns, null, 2)
  );
  fs.writeFileSync(
    kb.paths.rejected_patterns,
    JSON.stringify(kb.rejected_patterns, null, 2)
  );
  fs.writeFileSync(kb.paths.proposals, JSON.stringify(kb.proposals, null, 2));

  const kb2 = loadKnowledgeBase(tmp);
  const hit = similaritySearch("candidate_pool", kb2);
  assert.equal(hit.past_accepted, true);
  assert.equal(hit.knowledge_score, 0.82);
  assert.equal(hit.same_proposal, true);

  const del = similaritySearch("delete", kb2);
  assert.equal(del.past_rejected, true);
  assert.match(del.rejected_hits[0].message, /285R|Delete|Reject/);
});

test("Validation uses Knowledge Score", () => {
  const withHigh = computeValidationScore({
    expected_impact: 0.7,
    confidence: 0.7,
    coverage: 0.4,
    risk: 0.3,
    cost: 0.4,
    knowledge_score: 0.82,
  });
  const withLow = computeValidationScore({
    expected_impact: 0.7,
    confidence: 0.7,
    coverage: 0.4,
    risk: 0.3,
    cost: 0.4,
    knowledge_score: 0.2,
  });
  assert.ok(withHigh > withLow);
});

test("validateProposalRow reads KB not history", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v84-val-"));
  ensureKnowledgeBase(tmp);
  const kb = loadKnowledgeBase(tmp);
  kb.rejected_patterns.patterns.push({
    pattern_id: "REJ-014",
    root_cause: "candidate_pool",
    proposal: proposalLabel("candidate_pool"),
    rejected_week: "2026-W30",
    reason: "285R Regression",
  });
  fs.writeFileSync(
    kb.paths.rejected_patterns,
    JSON.stringify(kb.rejected_patterns, null, 2)
  );
  const kb2 = loadKnowledgeBase(tmp);
  const v = validateProposalRow(
    {
      family: "candidate_pool",
      proposal: "candidate_pool",
      score: 0.2,
      frequency_pct: 5,
      priority: 1,
    },
    {
      root_cause_scores: { candidate_pool: 0.2 },
      root_cause_confidence: { candidate_pool: 0.2 },
      root_cause_frequency_pct: { candidate_pool: 5 },
    },
    kb2,
    { week_id: "2026-W31" }
  );
  assert.ok(v.knowledge_score != null);
  assert.ok(v.similarity);
  assert.equal(v.similarity.past_rejected, true);
  assert.ok(v.warnings.some((w) => w.type === "similar_rejected_proposal"));
});

test("syncKnowledgeFromWeek writes patterns + timeline", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v84-sync-"));
  const weekId = "2026-W34";
  const weekRoot = path.join(tmp, "weekly", weekId);
  fs.mkdirSync(path.join(weekRoot, "fri-decision"), { recursive: true });
  fs.mkdirSync(path.join(weekRoot, "tue-proposal"), { recursive: true });
  fs.mkdirSync(path.join(weekRoot, "wed-canary"), { recursive: true });
  fs.mkdirSync(path.join(weekRoot, "thu-baseline"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "analysis", "miss"), { recursive: true });
  ensureKnowledgeBase(tmp);

  fs.writeFileSync(
    path.join(weekRoot, "fri-decision", "decision.json"),
    JSON.stringify({
      decision: "accept",
      baseline_delta: 0.02,
      reason: "human accept",
    })
  );
  fs.writeFileSync(
    path.join(weekRoot, "tue-proposal", "proposal-validation.json"),
    JSON.stringify({
      validations: [
        { family: "candidate_pool", gate: "pass", validation_score: 0.5 },
      ],
    })
  );
  fs.writeFileSync(
    path.join(weekRoot, "wed-canary", "ranked-run.json"),
    JSON.stringify({
      results: [
        { proposal: "candidate_pool", status: "evaluated", verdict: "PASS" },
      ],
    })
  );
  fs.writeFileSync(
    path.join(tmp, "analysis", "miss", "latest.json"),
    JSON.stringify({
      root_cause_family: "candidate_pool",
      root_cause_scores: { candidate_pool: 0.8 },
    })
  );

  const out = syncKnowledgeFromWeek({
    week_id: weekId,
    devRoot: tmp,
    weekRoot,
  });
  assert.ok(out.accepted[0].startsWith("PAT-"));
  const kb = loadKnowledgeBase(tmp);
  assert.equal(kb.accepted_patterns.patterns[0].proposal, "Entry Threshold Safe");
  assert.equal(kb.timeline[0].week, weekId);
  assert.deepEqual(kb.timeline[0].accepted, out.accepted);

  const w35 = path.join(tmp, "weekly", "2026-W35");
  fs.mkdirSync(path.join(w35, "fri-decision"), { recursive: true });
  fs.mkdirSync(path.join(w35, "tue-proposal"), { recursive: true });
  fs.mkdirSync(path.join(w35, "wed-canary"), { recursive: true });
  fs.mkdirSync(path.join(w35, "thu-baseline"), { recursive: true });
  fs.writeFileSync(
    path.join(w35, "fri-decision", "decision.json"),
    JSON.stringify({ decision: "reject", reason: "hold" })
  );
  fs.writeFileSync(
    path.join(w35, "thu-baseline", "report.json"),
    JSON.stringify({
      comparison: { measured_delta_hit_at_1: -0.01, verdict: "regression" },
    })
  );
  fs.writeFileSync(
    path.join(w35, "tue-proposal", "proposal-validation.json"),
    JSON.stringify({
      validations: [{ family: "delete", gate: "pass", validation_score: 0.4 }],
    })
  );
  const rej = syncKnowledgeFromWeek({
    week_id: "2026-W35",
    devRoot: tmp,
    weekRoot: w35,
  });
  assert.ok(rej.rejected[0].startsWith("REJ-"));
  const kb2 = loadKnowledgeBase(tmp);
  assert.equal(kb2.rejected_patterns.patterns[0].reason, "285R Regression");

  const metrics = summarizeKnowledgeMetrics(tmp);
  assert.ok(metrics.accepted_pattern_count >= 1);
  assert.ok(metrics.rejected_pattern_count >= 1);
});

test("repo knowledge dir and design doc exist", () => {
  assert.ok(fs.existsSync(path.join(ROOT, "development/knowledge")));
  assert.ok(
    fs.existsSync(path.join(ROOT, "docs/ops/v8.4-research-knowledge-base.md"))
  );
  assert.ok(
    fs.existsSync(path.join(ROOT, "development/history/research_timeline.json"))
  );
});
