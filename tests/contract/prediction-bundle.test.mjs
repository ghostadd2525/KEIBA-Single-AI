import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { clone, loadSchemas, readJson, validateWithSchema } from "../helpers/load.mjs";

const { predictionBundle: schema } = loadSchemas();
const valid = readJson("fixtures/prediction-bundle/valid-hanshin-11.json");

describe("PredictionBundle contract", () => {
  it("正常系: fixture が schema を満たす", () => {
    const r = validateWithSchema(schema, valid);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("必須フィールド欠落: race_id", () => {
    const bad = clone(valid);
    delete bad.race_id;
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("race_id") && e.includes("required")));
  });

  it("必須フィールド欠落: evaluation.runners", () => {
    const bad = clone(valid);
    delete bad.evaluation.runners;
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("runners") && e.includes("required")));
  });

  it("必須フィールド欠落: ai_confidence.score", () => {
    const bad = clone(valid);
    delete bad.ai_confidence.score;
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("score") && e.includes("required")));
  });

  it("型不一致: race_info.race_no が文字列", () => {
    const bad = clone(valid);
    bad.race_info.race_no = "11";
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("race_no") && e.includes("type")));
  });

  it("型不一致: ai_confidence.score が文字列", () => {
    const bad = clone(valid);
    bad.ai_confidence.score = "0.62";
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("score") && e.includes("type")));
  });

  it("schema_version 不一致", () => {
    const bad = clone(valid);
    bad.schema_version = "single-prediction-bundle/1.0";
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("const")));
  });
});
