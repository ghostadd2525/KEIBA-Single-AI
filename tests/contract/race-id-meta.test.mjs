import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  parseRaceIdMeta,
  alignRaceInfoToRaceId,
  alignBundleToRaceId,
} from "../../functions/_lib/raceIdMeta.js";
import { normalizePredictionBundle } from "../../functions/_lib/domain.js";

describe("race_id / venue alignment (UI P0)", () => {
  it("parses 20260719_tokyo_11", () => {
    const p = parseRaceIdMeta("20260719_tokyo_11");
    assert.equal(p.venue, "東京");
    assert.equal(p.race_no, 11);
    assert.equal(p.date, "2026-07-19");
    assert.equal(p.meeting_id, "20260719_tokyo");
  });

  it("aligns hanshin template race_info to tokyo race_id", () => {
    const info = alignRaceInfoToRaceId(
      {
        venue: "阪神",
        race_no: 11,
        meeting_id: "20260719_hanshin",
        class_label: "3歳以上1勝クラス",
      },
      "20260719_tokyo_11"
    );
    assert.equal(info.venue, "東京");
    assert.equal(info.meeting_id, "20260719_tokyo");
    assert.equal(info.race_no, 11);
  });

  it("normalizePredictionBundle overlays venue from race_id", () => {
    const bundle = normalizePredictionBundle(
      {
        schema_version: "single-prediction-bundle/2.0",
        race_id: "20260719_hanshin_11",
        race_info: {
          venue: "阪神",
          race_no: 11,
          date: "2026-07-19",
        },
        evaluation: { runners: [] },
        ai_confidence: { score: 0.5 },
      },
      "20260719_tokyo_11"
    );
    assert.equal(bundle.race_id, "20260719_tokyo_11");
    assert.equal(bundle.race_info.venue, "東京");
  });

  it("alignBundleToRaceId is idempotent for matching ids", () => {
    const b = alignBundleToRaceId(
      {
        race_id: "20260720_nakayama_11",
        race_info: { venue: "中山", race_no: 11 },
      },
      "20260720_nakayama_11"
    );
    assert.equal(b.race_info.venue, "中山");
  });
});
