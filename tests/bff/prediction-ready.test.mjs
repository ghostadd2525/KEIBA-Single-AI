import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  bundleRunners,
  isCatalogProjectionMeta,
  isReadyPredictionBundle,
  isTerminalUnavailable,
  isTerminalUnavailableReason,
  isRetryableUnavailableReason,
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

  it("classifies race_not_resolved as terminal", () => {
    assert.equal(isTerminalUnavailableReason("race_not_resolved"), true);
    assert.equal(isRetryableUnavailableReason("race_not_resolved"), false);
    const bundle = {
      race_id: "2026-08-23-03-10",
      prediction_available: false,
      fallback_reason: "race_not_resolved",
      evaluation: { runners: [], status: "unavailable" },
    };
    const meta = {
      engine_source: "prediction_unavailable",
      fallback_reason: "race_not_resolved",
      fallback_state: "prediction_unavailable:race_not_resolved",
    };
    assert.equal(isTerminalUnavailable(bundle, meta), true);
    assert.equal(isReadyPredictionBundle(bundle, meta), false);
  });

  it("classifies feature_not_ready as retryable pending", () => {
    assert.equal(isRetryableUnavailableReason("feature_not_ready"), true);
    assert.equal(isTerminalUnavailableReason("feature_not_ready"), false);
    assert.equal(isRetryableUnavailableReason("empty_runners"), true);
    assert.equal(isRetryableUnavailableReason("pi_prediction_unavailable_pending"), true);
  });

  it("accepts ready real bundle (case A)", () => {
    const bundle = {
      race_id: "2026-08-23-03-10",
      evaluation: { runners: [{ horse_number: 9, mark: "honmei" }] },
    };
    assert.equal(isReadyPredictionBundle(bundle, { engine_source: "real" }), true);
  });
});
