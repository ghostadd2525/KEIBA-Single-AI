import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { clone, loadSchemas, readJson, validateWithSchema } from "../helpers/load.mjs";

const { analysis: schema } = loadSchemas();
const valid = readJson("fixtures/analysis/valid-hanshin-11.json");

describe("Analysis contract", () => {
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

  it("必須フィールド欠落: charts", () => {
    const bad = clone(valid);
    delete bad.charts;
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("charts") && e.includes("required")));
  });

  it("型不一致: charts[].value が文字列", () => {
    const bad = clone(valid);
    bad.charts[0].value = "90";
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("value") && e.includes("type")));
  });

  it("型不一致: charts が配列でない", () => {
    const bad = clone(valid);
    bad.charts = { key: "pedigree" };
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("charts") && e.includes("type")));
  });

  it("schema_version 不一致", () => {
    const bad = clone(valid);
    bad.schema_version = "expect-analysis/0.9";
    const r = validateWithSchema(schema, bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("const")));
  });
});
