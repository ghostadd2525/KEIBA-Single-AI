import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  extractDateFromPiRaceId,
  findPiRaceInCatalog,
  isPiRaceId,
} from "../../functions/_lib/raceIdResolve.js";
import {
  mapPiPredictionToBundle,
  piProvenanceItem,
} from "../../functions/_lib/piPredictionMapper.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const piFixture = JSON.parse(
  readFileSync(join(__dirname, "../../fixtures/pi-prediction/niigata-6r.json"), "utf8")
);

describe("raceIdResolve (PI race_id)", () => {
  it("isPiRaceId: Win5 形式を認識", () => {
    assert.equal(isPiRaceId("2026-07-25-01-06"), true);
    assert.equal(isPiRaceId("20260719_hanshin_11"), false);
  });

  it("extractDateFromPiRaceId", () => {
    assert.equal(extractDateFromPiRaceId("2026-07-25-01-06"), "2026-07-25");
  });

  it("findPiRaceInCatalog", () => {
    const row = findPiRaceInCatalog(
      { races: [{ race_id: "2026-07-25-01-06", course: "新潟" }] },
      "2026-07-25-01-06"
    );
    assert.equal(row.course, "新潟");
  });
});

describe("piPredictionMapper", () => {
  it("mapPiPredictionToBundle: PI race_id をキーに PredictionBundle 化", () => {
    const bundle = mapPiPredictionToBundle(piFixture);
    assert.ok(bundle);
    assert.equal(bundle.race_id, "2026-07-25-01-06");
    assert.equal(bundle.race_info.venue, "新潟");
    assert.equal(bundle.race_info.race_no, 6);
    assert.equal(bundle.race_info.race_label, "新潟6R");
    assert.equal(bundle.race_info.class_label, "豊栄特別");
    assert.equal(bundle.evaluation.runners.length, 4);
    assert.equal(bundle.evaluation.runners[0].mark, "honmei");
    assert.equal(bundle.evaluation.runners[0].horse_name, "コルドンブルー");
    assert.ok(bundle.ai_confidence.score != null);
  });

  it("prediction_available=false なら null", () => {
    assert.equal(
      mapPiPredictionToBundle({ ...piFixture, prediction_available: false }),
      null
    );
  });

  it("piProvenanceItem: engine_source=pi", () => {
    const bundle = mapPiPredictionToBundle(piFixture);
    const item = piProvenanceItem("2026-07-25-01-06", bundle);
    assert.equal(item.engine_source, "pi");
    assert.equal(item.race_id, "2026-07-25-01-06");
  });
});
