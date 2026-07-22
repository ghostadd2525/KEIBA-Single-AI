import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  MODEL_WEIGHT,
  SEGMENT_WEIGHT,
  blendConfidenceScore,
  lookupSegmentHitRate,
  applySegmentConfidenceBlend,
  segmentKey,
  distanceBucket,
  surfaceJa,
} from "../../functions/_lib/segmentConfidence.js";
import { buildSummaryFromBundle } from "../../functions/_lib/raceCardSummary.js";
import { mapPiPredictionToBundle } from "../../functions/_lib/piPredictionMapper.js";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");
const piFixture = JSON.parse(
  readFileSync(join(ROOT, "fixtures/pi-prediction/niigata-6r.json"), "utf8")
);

const TABLE = {
  overall_hit_rate: 218 / 285,
  min_samples: 3,
  segments: {
    "新潟|芝|1600": { hit_rate: 0.8, n: 10 },
  },
};

describe("segmentConfidence blend 60/40", () => {
  it("weights are 0.6 / 0.4", () => {
    assert.equal(MODEL_WEIGHT, 0.6);
    assert.equal(SEGMENT_WEIGHT, 0.4);
  });

  it("blendConfidenceScore: 0.1 model + 0.8 segment → 0.38", () => {
    const blended = blendConfidenceScore(0.1, 0.8);
    assert.ok(blended != null);
    assert.equal(Math.round(blended * 1000), 380);
  });

  it("lookup: exact segment when n≥3", () => {
    const row = lookupSegmentHitRate(
      { venue: "新潟", surface: "芝", distance: 1600 },
      TABLE
    );
    assert.equal(row.scope, "venue_surface_distance");
    assert.equal(row.hit_rate, 0.8);
    assert.equal(row.key, segmentKey("新潟", "芝", 1600));
  });

  it("lookup: falls back to overall when segment missing", () => {
    const row = lookupSegmentHitRate(
      { venue: "札幌", surface: "芝", distance: 2000 },
      TABLE
    );
    assert.equal(row.scope, "overall");
    assert.equal(row.hit_rate, TABLE.overall_hit_rate);
  });

  it("applySegmentConfidenceBlend uses catalog context", () => {
    const out = applySegmentConfidenceBlend(
      0.055,
      { venue: "新潟", surface: "芝", distance: 1600 },
      TABLE
    );
    assert.ok(out);
    assert.ok(Math.abs(out.score - (0.6 * 0.055 + 0.4 * 0.8)) < 0.001);
    assert.equal(out.segment_scope, "venue_surface_distance");
  });

  it("distanceBucket snaps to nearest UI bucket", () => {
    assert.equal(distanceBucket(1800), 1600);
    assert.equal(distanceBucket(2100), 2000);
    assert.equal(surfaceJa("turf"), "芝");
    assert.equal(surfaceJa("dirt"), "ダ");
  });
});

describe("buildSummaryFromBundle + PI mapper", () => {
  it("mapper と summary が同一のブレンド score を返す", () => {
    const catalog = {
      ...piFixture,
      surface: "芝",
      distance: 1600,
      post_time: "10:35",
    };
    const bundle = mapPiPredictionToBundle(piFixture, catalog);
    const model = bundle.ai_confidence.component_scores.model_score;
    const summary = buildSummaryFromBundle(bundle, catalog);
    assert.ok(model != null);
    assert.ok(summary.confidence.score > model);
    assert.equal(
      Math.round(summary.confidence.score * 1000),
      Math.round(bundle.ai_confidence.score * 1000)
    );
  });
});
