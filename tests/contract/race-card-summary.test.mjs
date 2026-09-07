import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildRaceCardSummary,
  buildSummaryFromBundle,
  classifyPiPredictionPayload,
  confidenceBandFromScore,
  confidenceBandFromLabelAndScore,
  resolveConfidenceDisplay,
  CONFIDENCE_BAND_HIGH,
  CONFIDENCE_BAND_RATHER_HIGH,
  CONFIDENCE_BAND_MEDIUM,
  predictionStatusFromHttp,
} from "../../functions/_lib/raceCardSummary.js";
import { mapPiPredictionToBundle } from "../../functions/_lib/piPredictionMapper.js";
import { isV2RaceCardsEnabled } from "../../functions/_lib/featureFlags.js";
import {
  _resetBetaConfigCacheForTests,
  _setBetaConfigForTests,
} from "../../functions/_lib/betaConfig.js";
import { validateWithSchema } from "../../contracts/lib/schema-validate.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function readJson(rel) {
  return JSON.parse(readFileSync(join(ROOT, rel), "utf8"));
}

const schema = readJson("contracts/expect-race-card-summary/1.0/schema.json");
const piFixture = readJson("fixtures/pi-prediction/niigata-6r.json");
const readyFixture = readJson("fixtures/race-card-summary/ready.json");
const missingFixture = readJson("fixtures/race-card-summary/missing.json");
const apiSample = readJson("fixtures/race-card-summary/api-race-cards-sample.json");

describe("RaceCardSummary band（BFF 閾値 UI7/UI8）", () => {
  it("high ≥ 0.75 / rather_high ≥ 0.60 / medium ≥ 0.35 / low < 0.35", () => {
    assert.equal(CONFIDENCE_BAND_HIGH, 0.75);
    assert.equal(CONFIDENCE_BAND_RATHER_HIGH, 0.6);
    assert.equal(CONFIDENCE_BAND_MEDIUM, 0.35);
    assert.equal(confidenceBandFromScore(0.75), "high");
    assert.equal(confidenceBandFromScore(0.74), "rather_high");
    assert.equal(confidenceBandFromScore(0.6), "rather_high");
    assert.equal(confidenceBandFromScore(0.59), "medium");
    assert.equal(confidenceBandFromScore(0.35), "medium");
    assert.equal(confidenceBandFromScore(0.34), "low");
    assert.equal(confidenceBandFromScore(42), "medium"); // percent → /100
  });
});

describe("UI8 label + score band", () => {
  it("Near Miss 天井で high score でも rather_high 止まり", () => {
    assert.equal(
      confidenceBandFromLabelAndScore("near_miss", 0.9),
      "rather_high"
    );
  });
  it("Pure Residual は高 score でも low", () => {
    assert.equal(
      confidenceBandFromLabelAndScore("pure_residual", 0.95),
      "low"
    );
  });
  it("Normal + medium score → medium", () => {
    assert.equal(confidenceBandFromLabelAndScore("normal", 0.5), "medium");
  });
  it("midupper_world + 0.8 → rather_high（Near Miss 天井）", () => {
    const { label, band } = resolveConfidenceDisplay({
      world: "midupper_world",
      score: 0.8,
    });
    assert.equal(label, "near_miss");
    assert.equal(band, "rather_high");
  });
  it("core_world + 0.8 → high", () => {
    const { label, band } = resolveConfidenceDisplay({
      world: "core_world",
      score: 0.8,
    });
    assert.equal(label, "normal");
    assert.equal(band, "high");
  });
});

describe("RaceCardSummary builder", () => {
  it("PI ready → summary.honmei + confidence.band + short_reason=null", () => {
    const classified = classifyPiPredictionPayload(piFixture, piFixture);
    assert.equal(classified.status, "ready");
    const card = buildRaceCardSummary({
      raceId: piFixture.race_id,
      catalogRace: {
        ...piFixture,
        post_time: "10:35",
      },
      predictionStatus: "ready",
      bundle: classified.bundle,
      engineSource: "pi",
    });
    assert.equal(card.schema_version, "expect-race-card-summary/1.0");
    assert.equal(card.race_info.venue, "新潟");
    assert.equal(card.race_info.race_number, 6);
    assert.equal(card.race_info.race_name, "豊栄特別");
    assert.equal(card.race_info.post_time, "10:35");
    assert.equal(card.prediction.status, "ready");
    assert.equal(card.prediction.engine_source, "pi");
    assert.equal(card.summary.honmei.horse_number, 4);
    assert.equal(card.summary.honmei.horse_name, "コルドンブルー");
    assert.equal(card.summary.honmei.mark, "honmei");
    assert.ok(card.summary.confidence.score != null);
    assert.equal(card.summary.confidence.band, "low"); // fixture overall ≈ 0.055
    assert.equal(card.summary.short_reason, null);
    // PredictionBundle を返していない
    assert.equal(card.evaluation, undefined);
    assert.equal(card.ai_confidence, undefined);
    assert.equal(card.explain, undefined);

    const v = validateWithSchema(schema, card);
    assert.equal(v.ok, true, JSON.stringify(v.errors));
  });

  it("prediction_available=false → missing + summary=null", () => {
    const classified = classifyPiPredictionPayload(
      { ...piFixture, prediction_available: false },
      piFixture
    );
    assert.equal(classified.status, "missing");
    const card = buildRaceCardSummary({
      raceId: piFixture.race_id,
      catalogRace: piFixture,
      predictionStatus: "missing",
    });
    assert.equal(card.prediction.status, "missing");
    assert.equal(card.summary, null);
  });

  it("HTTP 404 → missing / 5xx → failed / 202 → processing", () => {
    assert.equal(predictionStatusFromHttp(404), "missing");
    assert.equal(predictionStatusFromHttp(500), "failed");
    assert.equal(predictionStatusFromHttp(502), "failed");
    assert.equal(predictionStatusFromHttp(202), "processing");
  });

  it("fixtures validate against schema", () => {
    assert.equal(validateWithSchema(schema, readyFixture).ok, true);
    assert.equal(validateWithSchema(schema, missingFixture).ok, true);
    for (const card of apiSample.data.race_cards) {
      assert.equal(validateWithSchema(schema, card).ok, true);
    }
  });

  it("buildSummaryFromBundle は PredictionBundle フィールドを summary にのみ投影", () => {
    const bundle = mapPiPredictionToBundle(piFixture);
    const summary = buildSummaryFromBundle(bundle);
    assert.equal(summary.short_reason, null);
    assert.ok(summary.honmei);
    assert.ok(summary.confidence);
    assert.equal(Object.keys(summary).sort().join(","), "confidence,honmei,short_reason");
  });
});

describe("Feature Flag v2_race_cards", () => {
  beforeEach(() => {
    _resetBetaConfigCacheForTests();
  });

  it("既定 false", async () => {
    _setBetaConfigForTests({ ui_features: {} });
    const enabled = await isV2RaceCardsEnabled({ env: {} });
    assert.equal(enabled, false);
  });

  it("beta ui_features.v2_race_cards=true で有効", async () => {
    _setBetaConfigForTests({ ui_features: { v2_race_cards: true } });
    const enabled = await isV2RaceCardsEnabled({ env: {} });
    assert.equal(enabled, true);
  });

  it("env V2_RACE_CARDS=true が beta より優先", async () => {
    _setBetaConfigForTests({ ui_features: { v2_race_cards: false } });
    const enabled = await isV2RaceCardsEnabled({ env: { V2_RACE_CARDS: "true" } });
    assert.equal(enabled, true);
  });

  it("env V2_RACE_CARDS=false で明示 OFF", async () => {
    _setBetaConfigForTests({ ui_features: { v2_race_cards: true } });
    const enabled = await isV2RaceCardsEnabled({ env: { V2_RACE_CARDS: "false" } });
    assert.equal(enabled, false);
  });
});

describe("Flag OFF 恒等（既存 /api/races 非破壊）", () => {
  it("race-cards モジュールは既存 races/index を import しない", async () => {
    const racesSrc = readFileSync(
      join(ROOT, "functions/api/races/index.js"),
      "utf8"
    );
    assert.equal(racesSrc.includes("race-cards"), false);
    assert.equal(racesSrc.includes("v2_race_cards"), false);
    assert.equal(racesSrc.includes("RaceCardSummary"), false);
  });

  it("piPredictionMapper / PredictionAdapter 契約ファイルは race-cards に依存しない", () => {
    const mapper = readFileSync(
      join(ROOT, "functions/_lib/piPredictionMapper.js"),
      "utf8"
    );
    const adapter = readFileSync(
      join(ROOT, "functions/_lib/adapters/predictionAdapter.js"),
      "utf8"
    );
    assert.equal(mapper.includes("raceCardSummary"), false);
    assert.equal(adapter.includes("raceCardSummary"), false);
  });
});
