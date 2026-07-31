/**
 * Version8.3 — Analyzer Feedback Loop tests
 */
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  predictHitDelta,
  inferActualHitDelta,
  buildFeedbackComparisons,
  updateConfidenceBias,
  mergePrecision,
  applyConfidenceCalibration,
  runAnalyzerFeedback,
  CONF_LR,
  HIT_SCALE,
} from "../../scripts/ops/v8/analyzer-feedback.mjs";
import { analyzeMiss } from "../../scripts/ops/improvement/lib/analyzers.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "../..");

test("predictHitDelta scales impact", () => {
  assert.equal(predictHitDelta(2 / HIT_SCALE), 2);
  assert.ok(predictHitDelta(0.8) > predictHitDelta(0.2));
});

test("prediction error example Hit+2 vs Hit+1", () => {
  const predicted = predictHitDelta(2 / 3);
  const actual = 1;
  const err = Math.abs(predicted - actual);
  assert.ok(Math.abs(err - 1) < 0.05 || Math.abs(predicted - 2) < 0.05);
});

test("inferActualHitDelta prefers explicit hit_delta", () => {
  assert.equal(inferActualHitDelta({ hitDelta: 2 }), 2);
  assert.equal(
    inferActualHitDelta({
      canaryRow: { verdict: "PASS", status: "evaluated" },
    }),
    1
  );
});

test("confidence calibration moves gently", () => {
  const cal = updateConfidenceBias(
    { confidence_bias: { candidate_pool: 0 } },
    { candidate_pool: { accepted: 6, successful: 5, precision: 0.83 } }
  );
  assert.ok(cal.confidence_bias.candidate_pool > 0);
  assert.ok(cal.confidence_bias.candidate_pool <= CONF_LR); // one step from 0.5
  const down = updateConfidenceBias(
    { confidence_bias: { delete: 0 } },
    { delete: { accepted: 4, successful: 1, precision: 0.25 } }
  );
  assert.ok(down.confidence_bias.delete < 0);
});

test("applyConfidenceCalibration clamps", () => {
  const out = applyConfidenceCalibration(
    { candidate_pool: 0.9 },
    { confidence_bias: { candidate_pool: 0.2 } }
  );
  assert.equal(out.candidate_pool, 1);
});

test("mergePrecision accumulates", () => {
  const led = mergePrecision(
    { by_root_cause: {} },
    { candidate_pool: { proposals: 10, accepted: 4, successful: 3 } }
  );
  const led2 = mergePrecision(led, {
    candidate_pool: { proposals: 8, accepted: 2, successful: 2 },
  });
  assert.equal(led2.by_root_cause.candidate_pool.proposals, 18);
  assert.equal(led2.by_root_cause.candidate_pool.accepted, 6);
  assert.equal(led2.by_root_cause.candidate_pool.successful, 5);
  assert.equal(led2.by_root_cause.candidate_pool.precision, 0.833);
});

test("buildFeedbackComparisons + runAnalyzerFeedback writes report", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "v83-fb-"));
  const weekId = "2026-W34";
  const weekRoot = path.join(tmp, "weekly", weekId);
  fs.mkdirSync(path.join(weekRoot, "tue-proposal"), { recursive: true });
  fs.mkdirSync(path.join(weekRoot, "wed-canary"), { recursive: true });
  fs.mkdirSync(path.join(weekRoot, "thu-baseline"), { recursive: true });
  fs.mkdirSync(path.join(weekRoot, "fri-decision"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "analysis"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "history"), { recursive: true });

  const validation = {
    validations: [
      {
        family: "candidate_pool",
        proposal: "candidate_pool",
        gate: "pass",
        impact: 0.67,
        validation_score: 0.81,
        dimensions: { expected_impact: 0.67 },
      },
      {
        family: "delete",
        proposal: "delete",
        gate: "fail",
        impact: 0.2,
        validation_score: 0.1,
        dimensions: { expected_impact: 0.2 },
      },
    ],
  };
  fs.writeFileSync(
    path.join(weekRoot, "tue-proposal", "proposal-validation.json"),
    JSON.stringify(validation)
  );
  fs.writeFileSync(
    path.join(weekRoot, "wed-canary", "ranked-run.json"),
    JSON.stringify({
      results: [
        {
          proposal: "candidate_pool",
          status: "evaluated",
          verdict: "PASS",
          gate: "pass",
        },
      ],
    })
  );
  fs.writeFileSync(
    path.join(weekRoot, "thu-baseline", "report.json"),
    JSON.stringify({
      comparison: { measured_delta_hit_at_1: null, verdict: "no_measured_delta" },
    })
  );
  fs.writeFileSync(
    path.join(weekRoot, "fri-decision", "decision.json"),
    JSON.stringify({ decision: "accept", baseline_delta: null })
  );

  const built = buildFeedbackComparisons({
    validation,
    canaryRun: {
      results: [
        {
          proposal: "candidate_pool",
          status: "evaluated",
          verdict: "PASS",
        },
      ],
    },
    baseline: null,
    decision: "accept",
    hitDelta: 1,
  });
  const cp = built.comparisons.find((c) => c.root_cause === "candidate_pool");
  assert.ok(cp);
  assert.ok(cp.prediction_error >= 0);
  assert.ok(cp.calibration_error != null);

  const out = runAnalyzerFeedback({
    week_id: weekId,
    devRoot: tmp,
    weekRoot,
  });
  assert.equal(out.report.week, weekId);
  assert.ok(fs.existsSync(path.join(tmp, "history", "analyzer_report.json")));
  assert.ok(fs.existsSync(path.join(tmp, "history", "root_cause_precision.json")));
  assert.ok(fs.existsSync(path.join(tmp, "history", "analyzer_calibration.json")));
  assert.ok(out.precision.candidate_pool);
  assert.ok(out.report.best_root_cause);
});

test("analyzeMiss exposes calibration fields", () => {
  const out = analyzeMiss({
    run_id: "v83",
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
    ],
  });
  assert.equal(out.analyzer_version, "v8.3");
  assert.ok(out.root_cause_confidence_raw);
  assert.ok(out.confidence_calibration_bias);
});

test("design doc exists", () => {
  assert.ok(
    fs.existsSync(path.join(ROOT, "docs/ops/v8.3-analyzer-feedback.md"))
  );
});
