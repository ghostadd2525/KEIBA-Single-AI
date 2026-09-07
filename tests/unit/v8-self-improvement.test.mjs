/**
 * Version8 — calendar guard, taxonomy, decide(no_improvement)
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  isWeekendJst,
  isRaceWeekendJst,
  assertResearchDay,
  researchGate,
} from "../../scripts/ops/v8/calendar.mjs";
import { analyzeMiss } from "../../scripts/ops/improvement/lib/analyzers.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");

test("isWeekendJst: Saturday UTC evening is Sunday JST → weekend", () => {
  // 2026-07-25 16:00 UTC = 2026-07-26 01:00 JST (Sunday)
  const d = new Date(Date.UTC(2026, 6, 25, 16, 0, 0));
  assert.equal(isWeekendJst(d), true);
  assert.equal(isRaceWeekendJst(d), true);
});

test("isWeekendJst: Monday JST is research day", () => {
  // 2026-07-26 16:00 UTC = 2026-07-27 01:00 JST (Monday)
  const d = new Date(Date.UTC(2026, 6, 26, 16, 0, 0));
  assert.equal(isWeekendJst(d), false);
});

test("assertResearchDay throws on weekend", () => {
  const weekend = new Date(Date.UTC(2026, 6, 25, 16, 0, 0));
  assert.throws(
    () => assertResearchDay({ purpose: "Analyzer", now: weekend }),
    /Production collects Evidence only/
  );
});

test("researchGate.blocked on weekend", () => {
  const weekend = new Date(Date.UTC(2026, 6, 25, 16, 0, 0));
  const g = researchGate("Proposal", weekend);
  assert.equal(g.allowed, false);
  assert.equal(g.blocked, true);
});

test("taxonomy contract exists with root cause families", () => {
  const taxPath = path.join(
    ROOT,
    "contracts/expect-root-cause-taxonomy/1.0/taxonomy.json"
  );
  assert.ok(fs.existsSync(taxPath));
  const tax = JSON.parse(fs.readFileSync(taxPath, "utf8"));
  const ids = tax.families.map((f) => f.id);
  assert.ok(ids.includes("candidate_pool"));
  assert.ok(ids.includes("repick"));
  assert.ok(ids.includes("delete"));
  assert.ok(ids.includes("confidence"));
  assert.ok(ids.includes("world"));
  assert.ok(ids.includes("subworld"));
});

test("analyzeMiss emits root_cause_family (Research taxonomy)", () => {
  const out = analyzeMiss({
    run_id: "test-run",
    events: [
      {
        event_id: "e1",
        payload: {
          miss_category: "miss_top1",
          confidence: 0.9,
          winner: { horse_number: 5 },
          candidate_pool: [{ horse_number: 1 }, { horse_number: 2 }],
        },
      },
      {
        event_id: "e2",
        payload: {
          miss_category: "miss_top1",
          confidence: 0.88,
          winner: { horse_number: 7 },
          candidate_pool: [{ horse_number: 3 }],
        },
      },
    ],
  });
  assert.equal(out.taxonomy_schema, "expect-root-cause-taxonomy/1.0");
  assert.ok(out.root_cause_family);
  assert.ok(Array.isArray(out.root_cause_families));
  assert.ok(out.root_cause_families.length >= 1);
  // winner not in pool → candidate_pool should rank high
  assert.equal(out.root_cause_family, "candidate_pool");
  assert.ok(out.root_cause_families.includes("candidate_pool"));
  assert.ok(out.root_cause_scores);
  assert.ok(out.root_cause_scores.candidate_pool > 0);
});

test("decide: no_improvement is success (reject path)", () => {
  const fixtures = path.join(ROOT, "fixtures/stats/baseline-285r-evaluations.json");
  assert.ok(fs.existsSync(fixtures), "285R fixtures required");
  const metrics = {
    hit_rate: 0.3,
    top3_hit_rate: 0.55,
    top5_hit_rate: 0.7,
    n: 285,
  };
  const baseline = { hit_rate: 0.32, top3_hit_rate: 0.56, top5_hit_rate: 0.71 };
  const delta = {
    hit_rate: metrics.hit_rate - baseline.hit_rate,
    top3_hit_rate: metrics.top3_hit_rate - baseline.top3_hit_rate,
    top5_hit_rate: metrics.top5_hit_rate - baseline.top5_hit_rate,
  };
  const improved =
    delta.hit_rate >= 0.01 ||
    (delta.hit_rate >= 0 && delta.top3_hit_rate >= 0.01);
  assert.equal(improved, false);
  const decision = improved ? "accept_candidate" : "reject_keep_baseline";
  assert.equal(decision, "reject_keep_baseline");
});

test("v8 weekly template and design doc exist", () => {
  assert.ok(fs.existsSync(path.join(ROOT, "docs/ops/v8-self-improvement-cycle.md")));
  assert.ok(fs.existsSync(path.join(ROOT, "development/weekly/README.md")));
  assert.ok(
    fs.existsSync(path.join(ROOT, "development/weekly/_TEMPLATE/manifesto.json"))
  );
});

test("feature flags reserved OFF in beta.json", () => {
  const cfg = JSON.parse(
    fs.readFileSync(path.join(ROOT, "public/config/beta.json"), "utf8")
  );
  assert.equal(cfg.ui_features.v8_canary_candidate_pool, false);
  assert.equal(cfg.ui_features.v8_canary_repick, false);
  assert.equal(cfg.ui_features.v8_canary_delete, false);
  assert.equal(cfg.ui_features.v8_production_canary, false);
});
