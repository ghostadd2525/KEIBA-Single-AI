/**
 * Phase7-08 — PredictionService envelope meta（provenance）契約
 * PredictionBundle Schema は対象外（変更禁止）。
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  mergeGetProvenanceMeta,
  mergeListProvenanceMeta,
} from "../../functions/_lib/adapters/predictionAdapter.js";
import {
  predictionGetEnvelope,
  predictionListEnvelope,
} from "../bff/build-envelope.mjs";
import { loadSchemas, readJson } from "../helpers/load.mjs";

const ENGINE_SOURCES = new Set(["real_ai", "real", "pi", "mock_fallback", "mock", "bff_mock"]);
const ENGINES = new Set(["real", "mock", "n/a"]);

function assertListItem(item) {
  assert.equal(typeof item.race_id, "string");
  assert.ok(ENGINE_SOURCES.has(item.engine_source), `bad engine_source: ${item.engine_source}`);
  assert.ok("model_version" in item);
  assert.ok("inference_generated_at" in item);
}

describe("Prediction envelope meta (provenance)", () => {
  const schemas = loadSchemas();
  const bundle = readJson("fixtures/prediction-bundle/valid-hanshin-11.json");

  it("BFF mock list: meta.items で bff_mock 識別", () => {
    const env = predictionListEnvelope([bundle], schemas);
    assert.equal(env.meta.provider, "mock");
    assert.equal(env.meta.adapter, "PredictionAdapter");
    assert.equal(env.meta.engine, "n/a");
    assert.ok(Array.isArray(env.meta.items));
    assert.equal(env.meta.items.length, 1);
    assertListItem(env.meta.items[0]);
    assert.equal(env.meta.items[0].engine_source, "bff_mock");
    assert.equal(env.meta.items[0].model_version, bundle.model_version);
    assert.equal(env.meta.items[0].inference_generated_at, bundle.generated_at);
    // PB 本体に運用フィールドを載せない
    assert.equal("provider" in env.data[0], false);
    assert.equal("engine_source" in env.data[0], false);
  });

  it("BFF mock get: meta にフラット provenance", () => {
    const env = predictionGetEnvelope(bundle, schemas);
    assert.equal(env.meta.provider, "mock");
    assert.equal(env.meta.adapter, "PredictionAdapter");
    assert.equal(env.meta.engine, "n/a");
    assert.equal(env.meta.engine_source, "bff_mock");
    assert.equal(env.meta.model_version, bundle.model_version);
    assert.equal(env.meta.inference_generated_at, bundle.generated_at);
    assert.equal(env.meta.race_id, bundle.race_id);
    assert.equal("engine_source" in env.data, false);
  });

  it("mergeListProvenanceMeta: real_ai / mock_fallback を保持", () => {
    const merged = mergeListProvenanceMeta(
      {
        source: "single-ai",
        service: "PredictionService",
        provider: "python",
        adapter: "PredictionAdapter",
      },
      {
        engine: "real",
        items: [
          {
            race_id: "20260719_fukushima_11",
            engine_source: "real_ai",
            model_version: "core-delegated",
            inference_generated_at: "2026-07-20T10:00:00",
            core_race_id: "2026-07-19-04-11",
          },
          {
            race_id: "20260719_hanshin_11",
            engine_source: "mock_fallback",
            model_version: "dummy-model-0.0.0",
            inference_generated_at: "2026-07-19T12:00:00+09:00",
          },
        ],
      }
    );
    assert.equal(merged.engine, "real");
    assert.equal(merged.provider, "python");
    assert.equal(merged.items[0].engine_source, "real_ai");
    assert.equal(merged.items[1].engine_source, "mock_fallback");
    merged.items.forEach(assertListItem);
  });

  it("mergeGetProvenanceMeta: real_ai フラット", () => {
    const merged = mergeGetProvenanceMeta(
      {
        source: "single-ai",
        service: "PredictionService",
        provider: "python",
        adapter: "PredictionAdapter",
      },
      {
        engine: "real",
        engine_source: "real_ai",
        model_version: "core-delegated",
        inference_generated_at: "2026-07-20T10:00:00",
        race_id: "2026-07-19-01-10",
        core_race_id: "2026-07-19-01-10",
      }
    );
    assert.equal(merged.engine, "real");
    assert.ok(ENGINES.has(merged.engine));
    assert.equal(merged.engine_source, "real_ai");
    assert.equal(merged.model_version, "core-delegated");
    assert.equal(merged.inference_generated_at, "2026-07-20T10:00:00");
    assert.equal(merged.core_race_id, "2026-07-19-01-10");
  });

  it("engine_source 列挙は運用3系統をカバー", () => {
    for (const s of ["real_ai", "mock_fallback", "bff_mock"]) {
      assert.ok(ENGINE_SOURCES.has(s));
    }
  });
});
