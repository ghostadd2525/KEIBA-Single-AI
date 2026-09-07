/**
 * Version8.5 — Research Governance tests
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "path";
import { fileURLToPath } from "node:url";
import {
  weekDistance,
  applyKnowledgeDecay,
  agePattern,
  revalidatePattern,
  findMergeCandidates,
  runGovernance,
  STALE_AFTER_WEEKS,
  ARCHIVE_AFTER_WEEKS,
} from "../../scripts/ops/v8/governance.mjs";
import { ensureKnowledgeBase, loadKnowledgeBase } from "../../scripts/ops/v8/knowledge-base.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");

test("weekDistance and decay 0.92→~0.74 over 26w", () => {
  assert.equal(weekDistance("2026-W31", "2026-W37"), 6);
  const d = applyKnowledgeDecay(0.92, 26);
  assert.ok(Math.abs(d - 0.74) < 0.02);
});

test("aging active → stale → archived", () => {
  const base = {
    pattern_id: "PAT-001",
    created_week: "2026-W20",
    last_used: "2026-W20",
    usage_count: 1,
    status: "active",
  };
  const stale = agePattern(base, "2026-W28"); // 8 weeks
  assert.equal(stale.status, "stale");
  assert.ok(stale.weeks_unused >= STALE_AFTER_WEEKS);

  const archived = agePattern(base, "2026-W36"); // 16 weeks
  assert.equal(archived.status, "archived");
  assert.ok(archived.weeks_unused >= ARCHIVE_AFTER_WEEKS);
});

test("revalidation no_improvement → stale", () => {
  const pat = {
    pattern_id: "PAT-001",
    created_week: "2026-W20",
    last_used: "2026-W34",
    status: "active",
    last_revalidated: null,
  };
  const out = revalidatePattern(
    pat,
    { comparison: { verdict: "no_measured_delta", measured_delta_hit_at_1: null } },
    "2026-W34"
  );
  assert.equal(out.status, "stale");
  assert.equal(out.revalidation_result, "no_improvement");
});

test("merge candidates for duplicate root_cause+proposal", () => {
  const c = findMergeCandidates([
    {
      pattern_id: "PAT-001",
      root_cause: "candidate_pool",
      proposal: "Entry Threshold Safe",
      status: "active",
    },
    {
      pattern_id: "PAT-014",
      root_cause: "candidate_pool",
      proposal: "Entry Threshold Safe",
      status: "active",
    },
  ]);
  assert.equal(c.length, 1);
  assert.deepEqual(c[0].pattern_ids.sort(), ["PAT-001", "PAT-014"]);
  assert.equal(c[0].status, "merge_candidate");
});

test("runGovernance writes dashboard", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v85-gov-"));
  ensureKnowledgeBase(tmp);
  const weekId = "2026-W40";
  const weekRoot = path.join(tmp, "weekly", weekId);
  fs.mkdirSync(path.join(weekRoot, "thu-baseline"), { recursive: true });
  fs.writeFileSync(
    path.join(weekRoot, "thu-baseline", "report.json"),
    JSON.stringify({
      comparison: { verdict: "no_measured_delta", measured_delta_hit_at_1: null },
    })
  );

  const kb = loadKnowledgeBase(tmp);
  kb.accepted_patterns.patterns = [
    {
      pattern_id: "PAT-001",
      root_cause: "candidate_pool",
      proposal: "Entry Threshold Safe",
      accepted_week: "2026-W20",
      created_week: "2026-W20",
      last_used: "2026-W38",
      usage_count: 2,
      status: "active",
    },
    {
      pattern_id: "PAT-014",
      root_cause: "candidate_pool",
      proposal: "Entry Threshold Safe",
      accepted_week: "2026-W22",
      created_week: "2026-W22",
      last_used: "2026-W39",
      usage_count: 1,
      status: "active",
    },
  ];
  kb.proposals.proposals = {
    candidate_pool: {
      family: "candidate_pool",
      accepted_count: 4,
      rejected_count: 1,
      knowledge_score: 0.92,
      last_week: "2026-W38",
    },
  };
  fs.writeFileSync(
    kb.paths.accepted_patterns,
    JSON.stringify(kb.accepted_patterns, null, 2)
  );
  fs.writeFileSync(kb.paths.proposals, JSON.stringify(kb.proposals, null, 2));

  const out = runGovernance({ week_id: weekId, devRoot: tmp, weekRoot });
  assert.equal(out.dashboard.schema_version, "expect-v85-governance-dashboard/1.0");
  assert.ok(out.dashboard.merge_candidate_count >= 1);
  assert.ok(fs.existsSync(path.join(tmp, "knowledge", "governance-dashboard.json")));
  assert.ok(fs.existsSync(path.join(tmp, "knowledge", "merge_candidates.json")));
  assert.equal(out.dashboard.safety.production_decision_influence, false);

  const dash = JSON.parse(
    fs.readFileSync(path.join(tmp, "knowledge", "governance-dashboard.json"), "utf8")
  );
  // Revalidation with no_measured_delta marks patterns stale
  assert.ok(dash.stale_pattern_count >= 1);
  assert.ok(typeof dash.average_knowledge_score === "number");
});

test("design doc and research-governance agent exist", () => {
  assert.ok(
    fs.existsSync(path.join(ROOT, "docs/ops/v8.5-research-governance.md"))
  );
  assert.ok(
    fs.existsSync(path.join(ROOT, ".cursor/agents/research-governance.md"))
  );
});
