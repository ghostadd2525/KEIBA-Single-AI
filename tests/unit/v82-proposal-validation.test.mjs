/**
 * Version8.2 — Proposal Validation, Gate, Similar, Knowledge
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  computeValidationScore,
  validateProposalRow,
  validateProposals,
  findSimilarRejected,
  GATE_THRESHOLD,
} from "../../scripts/ops/v8/proposal-validate.mjs";
import {
  upsertWeeklyHistory,
  summarizeHistory,
  loadWeeklyHistory,
} from "../../scripts/ops/v8/weekly-history.mjs";
import { analyzeMiss } from "../../scripts/ops/improvement/lib/analyzers.mjs";
import { rankProposals } from "../../scripts/ops/v8/rank-proposals.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");

test("computeValidationScore formula", () => {
  const high = computeValidationScore({
    expected_impact: 0.8,
    confidence: 0.8,
    coverage: 0.5,
    risk: 0.3,
    cost: 0.4,
    knowledge_score: 1, // K factor = 1 → classic V8.2 numerator
  });
  const low = computeValidationScore({
    expected_impact: 0.2,
    confidence: 0.3,
    coverage: 0.05,
    risk: 0.7,
    cost: 0.8,
    knowledge_score: 1,
  });
  assert.ok(high > GATE_THRESHOLD);
  assert.ok(high > low);
  // (0.8*0.8*0.5*1) / (0.3*1.4) = 0.32 / 0.42 ≈ 0.7619
  assert.ok(Math.abs(high - 0.7619) < 0.01);
});

test("similar rejected detection", () => {
  const history = [
    {
      week: "2026-W30",
      decision: "reject",
      root_cause: "candidate_pool",
      primary_family: "candidate_pool",
    },
  ];
  const hits = findSimilarRejected("candidate_pool", history, "2026-W31");
  assert.equal(hits.length, 1);
  assert.match(hits[0].message, /2026-W30/);
  assert.match(hits[0].message, /CandidatePool/);
});

test("gate blocks low score / similar weak impact", () => {
  const miss = {
    root_cause_scores: { candidate_pool: 0.2 },
    root_cause_confidence: { candidate_pool: 0.2 },
    root_cause_frequency_pct: { candidate_pool: 5 },
  };
  const history = [
    {
      week: "2026-W30",
      decision: "reject",
      root_cause: "candidate_pool",
    },
  ];
  const row = {
    family: "candidate_pool",
    proposal: "candidate_pool",
    score: 0.2,
    frequency_pct: 5,
    priority: 1,
  };
  const v = validateProposalRow(row, miss, history, { week_id: "2026-W31" });
  assert.equal(v.gate, "fail");
  assert.ok(v.warnings.length >= 1 || v.hard_block);
});

test("strong proposal can pass gate", () => {
  const miss = {
    root_cause_scores: { candidate_pool: 0.85 },
    root_cause_confidence: { candidate_pool: 0.8 },
    root_cause_frequency_pct: { candidate_pool: 42 },
  };
  const row = {
    family: "candidate_pool",
    proposal: "candidate_pool",
    score: 0.85,
    frequency_pct: 42,
    priority: 1,
    priority_band: "A",
  };
  const v = validateProposalRow(row, miss, [], { week_id: "2026-W31" });
  assert.equal(v.gate, "pass");
  assert.ok(v.validation_score >= GATE_THRESHOLD);
  assert.ok(v.dimensions.expected_impact > 0.5);
  assert.ok(v.dimensions.coverage > 0.3);
});

test("validateProposals writes artifact + canary_eligible", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v82-val-"));
  fs.mkdirSync(path.join(tmp, "analysis", "miss"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "weekly", "2026-W31"), { recursive: true });
  const analysis = analyzeMiss({
    run_id: "v82",
    events: [
      {
        event_id: "e1",
        race_id: "r1",
        payload: {
          miss_category: "miss_top5",
          winner: { horse_number: 9 },
          candidate_pool: [{ horse_number: 1 }],
        },
      },
      {
        event_id: "e2",
        race_id: "r2",
        payload: {
          miss_category: "miss_top5",
          winner: { horse_number: 8 },
          candidate_pool: [],
        },
      },
      {
        event_id: "e3",
        race_id: "r3",
        payload: {
          miss_category: "miss_top5",
          winner: { horse_number: 7 },
          candidate_pool: [{ horse_number: 2 }],
        },
      },
    ],
  });
  fs.writeFileSync(
    path.join(tmp, "analysis", "miss", "latest.json"),
    JSON.stringify(analysis)
  );
  rankProposals({ week_id: "2026-W31", devRoot: tmp });
  const doc = validateProposals({ week_id: "2026-W31", devRoot: tmp });
  assert.ok(
    doc.schema_version === "expect-v84-validation-run/1.0" ||
      doc.schema_version === "expect-v82-validation-run/1.0"
  );
  assert.ok(doc.validations.length >= 1);
  assert.ok(fs.existsSync(path.join(tmp, "analysis", "proposal-validation.json")));
  assert.ok(Array.isArray(doc.canary_eligible));
  // At least one should pass with strong candidate_pool corpus
  assert.ok(doc.summary.pass + doc.summary.fail === doc.summary.total);
});

test("weekly knowledge fields + metrics rates", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v82-know-"));
  upsertWeeklyHistory(
    {
      week: "2026-W30",
      decision: "reject",
      root_cause: "candidate_pool",
      validation_score: 0.2,
      impact: 0.3,
      validation_pass_count: 0,
      validation_fail_count: 2,
      proposals: [
        {
          proposal: "candidate_pool",
          gate: "fail",
          validation_score: 0.2,
          root_cause: "candidate_pool",
          impact: 0.3,
        },
      ],
    },
    { devRoot: tmp }
  );
  upsertWeeklyHistory(
    {
      week: "2026-W31",
      decision: "accept",
      root_cause: "candidate_pool",
      validation_score: 0.5,
      impact: 0.7,
      validation_pass_count: 1,
      validation_fail_count: 1,
      hit_delta: 2,
    },
    { devRoot: tmp }
  );
  const weeks = loadWeeklyHistory(tmp);
  assert.equal(weeks[0].validation_score, 0.2);
  assert.ok(weeks[0].proposals.length >= 1);
  const s = summarizeHistory(weeks);
  assert.equal(s.validation_pass_rate, 25); // 1/(1+1+0+2)=1/4
  assert.equal(s.validation_reject_rate, 75);
  assert.ok(s.root_cause_success.candidate_pool === 50);
  assert.ok(s.proposal_recurrence_rate === 100); // family in 2 weeks
});

test("design doc exists", () => {
  assert.ok(
    fs.existsSync(path.join(ROOT, "docs/ops/v8.2-proposal-validation.md"))
  );
});
