/**
 * Version8.1 — multi Root Cause, scores, priority, history, ranking
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  scoreMissEvent,
  aggregateScores,
  computeImprovementPriority,
} from "../../scripts/ops/v8/root-cause-score.mjs";
import { analyzeMiss } from "../../scripts/ops/improvement/lib/analyzers.mjs";
import {
  upsertWeeklyHistory,
  loadWeeklyHistory,
  summarizeHistory,
} from "../../scripts/ops/v8/weekly-history.mjs";
import { rankProposals } from "../../scripts/ops/v8/rank-proposals.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");

test("scoreMissEvent: multi families + scores when winner not in pool", () => {
  const r = scoreMissEvent({
    miss_category: "miss_top1",
    confidence: 90,
    winner: { horse_number: 5 },
    candidate_pool: [{ horse_number: 1 }, { horse_number: 2 }],
  });
  assert.ok(r.root_cause_families.includes("candidate_pool"));
  assert.ok(r.root_cause_families.length >= 2);
  assert.ok(r.scores.candidate_pool > r.scores.delete);
  assert.equal(typeof r.confidence.candidate_pool, "number");
  assert.ok(r.confidence.candidate_pool > 0);
});

test("scoreMissEvent: winner in pool → repick high", () => {
  const r = scoreMissEvent({
    miss_category: "miss_top1",
    winner: { horse_number: 3 },
    candidate_pool: [{ horse_number: 1 }, { horse_number: 3 }],
  });
  assert.ok(r.root_cause_families.includes("repick"));
  assert.ok(r.scores.repick >= 0.4);
});

test("scoreMissEvent: deleted winner → delete score", () => {
  const r = scoreMissEvent({
    miss_category: "miss_top5",
    winner: { horse_number: 7 },
    candidate_pool: [{ horse_number: 1 }],
    deleted: [7],
  });
  assert.ok(r.root_cause_families.includes("delete"));
  assert.ok(r.scores.delete >= 0.5);
});

test("aggregate + priority bands", () => {
  const per = [
    scoreMissEvent({
      miss_category: "miss_top5",
      winner: { horse_number: 9 },
      candidate_pool: [{ horse_number: 1 }],
    }),
    scoreMissEvent({
      miss_category: "miss_top5",
      winner: { horse_number: 8 },
      candidate_pool: [],
    }),
    scoreMissEvent({
      miss_category: "miss_top1",
      winner: { horse_number: 2 },
      candidate_pool: [{ horse_number: 2 }, { horse_number: 3 }],
    }),
  ];
  const agg = aggregateScores(per);
  assert.ok(agg.frequency_pct.candidate_pool > 0);
  const pri = computeImprovementPriority(agg);
  assert.ok(pri.length >= 1);
  assert.equal(pri[0].priority, 1);
  assert.ok(["A", "B", "C"].includes(pri[0].priority_band));
});

test("analyzeMiss V8.1 fields", () => {
  const out = analyzeMiss({
    run_id: "v81",
    events: [
      {
        event_id: "e1",
        race_id: "r1",
        payload: {
          miss_category: "miss_top1",
          confidence: 0.9,
          winner: { horse_number: 5 },
          candidate_pool: [{ horse_number: 1 }],
        },
      },
      {
        event_id: "e2",
        race_id: "r2",
        payload: {
          miss_category: "miss_top3",
          winner: { horse_number: 4 },
          candidate_pool: [{ horse_number: 4 }, { horse_number: 6 }],
        },
      },
    ],
  });
  assert.ok(out.analyzer_version === "v8.3" || out.analyzer_version === "v8.1");
  assert.ok(Array.isArray(out.root_cause_families));
  assert.equal(typeof out.root_cause_families[0], "string");
  assert.ok(out.root_cause_scores.candidate_pool >= 0);
  assert.ok(Array.isArray(out.per_race));
  assert.equal(out.per_race.length, 2);
  assert.ok(out.per_race[0].root_cause_families.length >= 1);
  assert.ok(Array.isArray(out.improvement_priority));
  assert.ok(out.root_cause_families.includes("candidate_pool"));
  assert.ok(out.root_cause_families.includes("repick"));
  assert.ok(
    out.root_cause_scores.candidate_pool > 0 || out.root_cause_scores.repick > 0
  );
});

test("weekly history upsert + rates", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v81-hist-"));
  upsertWeeklyHistory(
    { week: "2026-W31", decision: "accept", hit_delta: 2, rank710_delta: -1 },
    { devRoot: tmp }
  );
  upsertWeeklyHistory({ week: "2026-W32", decision: "reject" }, { devRoot: tmp });
  upsertWeeklyHistory({ week: "2026-W33", decision: "no_improvement" }, { devRoot: tmp });
  const weeks = loadWeeklyHistory(tmp);
  assert.equal(weeks.length, 3);
  const s = summarizeHistory(weeks);
  assert.equal(s.accept_rate, 33.3);
  assert.equal(s.reject_rate, 33.3);
  assert.equal(s.no_improvement_rate, 33.3);
  assert.equal(s.avg_hit_delta, 2);
});

test("rankProposals writes proposal-ranking.json", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v81-rank-"));
  const analysisDir = path.join(tmp, "analysis", "miss");
  fs.mkdirSync(analysisDir, { recursive: true });
  fs.mkdirSync(path.join(tmp, "weekly", "2026-W30"), { recursive: true });
  const analysis = analyzeMiss({
    run_id: "rank",
    events: [
      {
        event_id: "a",
        race_id: "r",
        payload: {
          miss_category: "miss_top5",
          winner: { horse_number: 9 },
          candidate_pool: [{ horse_number: 1 }],
        },
      },
    ],
  });
  fs.writeFileSync(
    path.join(analysisDir, "latest.json"),
    JSON.stringify(analysis, null, 2)
  );
  const doc = rankProposals({ week_id: "2026-W30", devRoot: tmp });
  assert.equal(doc.schema_version, "expect-v81-proposal-ranking/1.0");
  assert.ok(doc.ranking[0].priority === 1);
  assert.ok(
    fs.existsSync(path.join(tmp, "analysis", "proposal-ranking.json"))
  );
});

test("design doc and history path exist", () => {
  assert.ok(
    fs.existsSync(path.join(ROOT, "docs/ops/v8.1-analyzer-root-cause.md"))
  );
  assert.ok(
    fs.existsSync(path.join(ROOT, "development/history/weekly_history.json"))
  );
});
