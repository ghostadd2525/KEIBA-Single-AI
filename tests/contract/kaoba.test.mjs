import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { clone, readJson, validateDef } from "../helpers/load.mjs";

const schema = readJson("contracts/expect-kaoba/1.0/schema.json");
const request = readJson("fixtures/kaoba/chat-request.json");
const response = readJson("fixtures/kaoba/chat-response.json");
const responseNoRace = readJson("fixtures/kaoba/chat-response-no-race.json");

describe("KaobaService contract", () => {
  it("正常系: KaobaChatRequest", () => {
    const r = validateDef(schema, "KaobaChatRequest", request);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("正常系: KaobaChatResponse（race 参照あり）", () => {
    const r = validateDef(schema, "KaobaChatResponse", response);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("正常系: KaobaChatResponse（race なし）", () => {
    const r = validateDef(schema, "KaobaChatResponse", responseNoRace);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("必須フィールド欠落: request.message", () => {
    const bad = clone(request);
    delete bad.message;
    const r = validateDef(schema, "KaobaChatRequest", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("message") && e.includes("required")));
  });

  it("必須フィールド欠落: response.reply", () => {
    const bad = clone(response);
    delete bad.reply;
    const r = validateDef(schema, "KaobaChatResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("reply") && e.includes("required")));
  });

  it("必須フィールド欠落: referenced_race_id キー自体", () => {
    const bad = clone(response);
    delete bad.referenced_race_id;
    const r = validateDef(schema, "KaobaChatResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("referenced_race_id")));
  });

  it("型不一致: suggestions が文字列", () => {
    const bad = clone(response);
    bad.suggestions = "展開を詳しく";
    const r = validateDef(schema, "KaobaChatResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("suggestions") && e.includes("type")));
  });

  it("schema_version 不一致", () => {
    const bad = clone(response);
    bad.schema_version = "expect-kaoba/0.9";
    const r = validateDef(schema, "KaobaChatResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("const")));
  });
});
