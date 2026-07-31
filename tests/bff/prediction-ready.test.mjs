import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  bundleRunners,
  isCatalogProjectionMeta,
  isReadyPredictionBundle,
} from "../../functions/_lib/predictionReady.js";

describe("predictionReady (Version7)", () => {
  it("rejects empty runners", () => {
    const bundle = {
      race_id: "2026-07-26-02-04",
      evaluation: { runners: [] },
    };
    assert.equal(isReadyPredictionBundle(bundle, { engine_source: "pi" }), false);
    assert.equal(bundleRunners(bundle).length, 0);
  });

  it("rejects pi_catalog_projection even with runners", () => {
    const bundle = {
      race_id: "2026-07-26-02-04",
      evaluation: { runners: [{ horse_number: 1 }] },
    };
    assert.equal(
      isReadyPredictionBundle(bundle, { engine_source: "pi_catalog_projection" }),
      false
    );
    assert.equal(isCatalogProjectionMeta({ engine_source: "pi_catalog_projection" }), true);
  });

  it("accepts real PI bundle with runners", () => {
    const bundle = {
      race_id: "2026-07-26-02-04",
      evaluation: { runners: [{ horse_number: 4, mark: "honmei" }] },
    };
    assert.equal(isReadyPredictionBundle(bundle, { engine_source: "pi" }), true);
  });

  it("rejects pending meta", () => {
    const bundle = {
      race_id: "x",
      evaluation: { runners: [{ horse_number: 1 }] },
    };
    assert.equal(
      isReadyPredictionBundle(bundle, { prediction_status: "pending" }),
      false
    );
  });
});
