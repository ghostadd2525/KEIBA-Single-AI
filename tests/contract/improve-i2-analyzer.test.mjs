import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ROOT } from "../helpers/load.mjs";
import { scanEvidence } from "../../scripts/ops/improvement/lib/scan.mjs";
import { buildIndex } from "../../scripts/ops/improvement/lib/index.mjs";
import {
  analyzeMiss,
  analyzeFeatureMissing,
  analyzePredictionFailed,
  analyzeResultSyncFailed,
  runAnalyzers,
  REGISTERED_EVENT_TYPES,
  getAnalyzer,
} from "../../scripts/ops/improvement/lib/analyzers.mjs";

const ANALYZE_CLI = join(ROOT, "scripts/ops/improvement/analyze-evidence.mjs");

function writeEvent(root, eventType, date, raceId, payload = {}, version = {}) {
  const dir = join(root, eventType, date);
  mkdirSync(dir, { recursive: true });
  const doc = {
    schema_version: "expect-improvement-evidence/1.0",
    event_type: eventType,
    event_id: `${eventType}:${raceId}:t1`,
    timestamp: "2026-07-19T12:00:00.000Z",
    race_id: raceId,
    race_date: date,
    fingerprint: `sha256:${eventType}${raceId}fp`,
    payload,
    version: { pipeline_version: "ops-result-automation/1.0", ...version },
  };
  writeFileSync(join(dir, `${raceId}.json`), JSON.stringify(doc, null, 2));
  return doc;
}

function assertContract(result) {
  assert.equal(result.schema_version, "expect-root-cause/1.0");
  assert.equal(typeof result.root_cause, "string");
  assert.ok(result.root_cause.length > 0);
  assert.equal(typeof result.confidence, "number");
  assert.ok(result.confidence >= 0 && result.confidence <= 1);
  assert.equal(typeof result.reason, "string");
  assert.ok(result.reason.length > 0);
}

describe("I-2 Analyzer Registry", () => {
  it("registers exactly four analyzers", () => {
    assert.deepEqual(
      [...REGISTERED_EVENT_TYPES].sort(),
      ["feature_missing", "miss", "prediction_failed", "result_sync_failed"]
    );
    assert.equal(getAnalyzer("unknown_future"), null);
  });

  it("miss analyzer returns root_cause/confidence/reason", () => {
    const r = analyzeMiss({
      event_type: "miss",
      run_id: "t",
      output_dir: ".",
      events: [
        {
          event_id: "m1",
          event_type: "miss",
          path: "evidence/improvement/miss/2026-07-19/a.json",
          fingerprint: "sha256:abc",
          race_date: "2026-07-19",
          payload: { miss_category: "miss_top1", confidence: 90, engine_source: "real_ai" },
        },
      ],
    });
    assertContract(r);
    assert.ok(r.root_cause.includes("miss") || r.root_cause.includes("calibration"));
    assert.equal(r.evidence_refs[0].fingerprint, "sha256:abc");
  });

  it("feature_missing analyzer returns contract fields", () => {
    const r = analyzeFeatureMissing({
      event_type: "feature_missing",
      run_id: "t",
      output_dir: ".",
      events: [
        {
          event_id: "f1",
          event_type: "feature_missing",
          path: "evidence/improvement/feature_missing/2026-07-19/a.json",
          fingerprint: "sha256:feat",
          race_date: "2026-07-19",
          payload: {
            fallback_reason: "market_feature_missing",
            feature_source: "missing",
          },
        },
      ],
    });
    assertContract(r);
    assert.equal(r.root_cause, "market_feature_absent");
  });

  it("prediction_failed and result_sync_failed return contract fields", () => {
    const p = analyzePredictionFailed({
      event_type: "prediction_failed",
      run_id: "t",
      output_dir: ".",
      events: [
        {
          event_id: "p1",
          event_type: "prediction_failed",
          path: "x",
          fingerprint: null,
          race_date: "2026-07-19",
          payload: { reason: "prediction_missing" },
        },
      ],
    });
    assertContract(p);
    assert.equal(p.root_cause, "prediction_absent");

    const s = analyzeResultSyncFailed({
      event_type: "result_sync_failed",
      run_id: "t",
      output_dir: ".",
      events: [
        {
          event_id: "s1",
          event_type: "result_sync_failed",
          path: "y",
          fingerprint: "sha256:rs",
          race_date: "2026-07-19",
          payload: { provider: "CsvResultProvider", error: "csv not found" },
        },
      ],
    });
    assertContract(s);
    assert.equal(s.root_cause, "result_csv_or_source_missing");
  });

  it("runAnalyzers writes latest.json per type", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i2-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i2-dev-"));
    writeEvent(evidence, "miss", "2026-07-19", "r1", {
      miss_category: "miss_top1",
      confidence: 88,
    });
    writeEvent(evidence, "feature_missing", "2026-07-19", "r2", {
      fallback_reason: "feature_missing",
      feature_source: "none",
    });
    const scan = scanEvidence(evidence);
    const results = runAnalyzers(scan, dev, "run-test");
    assert.ok(results.miss);
    assert.ok(results.feature_missing);
    assertContract(results.miss);
    assert.ok(existsSync(join(dev, "analysis", "miss", "latest.json")));
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("CLI improve:analyze exits 0", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i2-cli-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i2-cli-dev-"));
    writeEvent(
      evidence,
      "miss",
      "2026-07-19",
      "r1",
      { miss_category: "miss_top1" },
      { model_version: "core-1.0" }
    );
    const r = spawnSync(
      process.execPath,
      [
        ANALYZE_CLI,
        "--evidence-root",
        evidence,
        "--dev-root",
        dev,
        "--date",
        "2026-07-19",
      ],
      { encoding: "utf8" }
    );
    assert.equal(r.status, 0, r.stderr || r.stdout);
    const out = JSON.parse(r.stdout);
    assert.equal(out.phase, "I-2");
    assert.equal(out.evidence_count, 1);
    assert.ok(out.analyses.miss.root_cause);
    assert.ok(out.analyses.miss.confidence >= 0);
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});

describe("I-2 Index by-model-version extension", () => {
  it("writes by-model-version slice and preserves fingerprint", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i2-mv-"));
    const dev = mkdtempSync(join(tmpdir(), "i2-mv-dev-"));
    writeEvent(
      evidence,
      "miss",
      "2026-07-19",
      "r1",
      { miss_category: "miss_top1" },
      { model_version: "core-1.0" }
    );
    const scan = scanEvidence(evidence);
    const index = buildIndex(scan, dev, "2026-07-19");
    assert.equal(index.dimensions.by_model_version, true);
    assert.ok(index.counts_by_model_version["core-1.0"] >= 1);
    assert.ok(existsSync(join(dev, "index", "by-model-version", "core-1.0.json")));
    assert.equal(index.events[0].fingerprint, "sha256:missr1fp");
    assert.equal(index.events[0].model_version, "core-1.0");
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});
