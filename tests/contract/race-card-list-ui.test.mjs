/**
 * Phase 3 — raceCardSummaryHtml（v2_race_list_ui）表示確認
 * Flag OFF 経路の raceCardHtml 恒等も検証。
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function loadBind() {
  const code = readFileSync(join(ROOT, "public/assets/api/prediction-bind.js"), "utf8");
  const sandbox = {
    window: null,
    document: {
      getElementById() {
        return null;
      },
      querySelector() {
        return null;
      },
      createElement() {
        return {};
      },
    },
    console,
    ExpectUiFeatures: { enabled: () => false },
  };
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox);
  return sandbox.ExpectPredictionBind;
}

const ready = {
  schema_version: "expect-race-card-summary/1.0",
  race_id: "2026-07-25-01-06",
  race_info: {
    venue: "新潟",
    race_number: 6,
    race_name: "豊栄特別",
    post_time: "10:35",
  },
  prediction: { status: "ready", engine_source: "pi" },
  summary: {
    honmei: { horse_number: 4, horse_name: "コルドンブルー", mark: "honmei" },
    confidence: { score: 0.42, band: "medium" },
    short_reason: "CE 1 位 · 表示禁止確認用",
  },
};

describe("raceCardSummaryHtml / prediction.status", () => {
  const bind = loadBind();

  it("ready: ◎ + confidence% + band + data-prediction-status", () => {
    const html = bind.raceCardSummaryHtml(ready, { listDate: "2026-07-25" });
    assert.match(html, /data-prediction-status="ready"/);
    assert.match(html, /race-item-honmei/);
    assert.match(html, /◎ 4/);
    assert.match(html, /コルドンブルー/);
    assert.match(html, />42%<small>ふつう<\/small>/);
    assert.match(html, /data-confidence-band="medium"/);
    assert.match(html, /data-race-date="2026-07-25"/);
    // short_reason は Phase 1 未表示
    assert.doesNotMatch(html, /表示禁止確認用/);
    assert.doesNotMatch(html, /short_reason/);
  });

  it("processing: ◎ — 予想準備中 / 信頼度 —", () => {
    const html = bind.raceCardSummaryHtml({
      ...ready,
      prediction: { status: "processing" },
      summary: null,
    });
    assert.match(html, /data-prediction-status="processing"/);
    assert.match(html, /予想準備中/);
    assert.match(html, /—<small>AI信頼度<\/small>/);
    assert.doesNotMatch(html, /コルドンブルー/);
  });

  it("failed: Catalog + 予想取得失敗", () => {
    const html = bind.raceCardSummaryHtml({
      ...ready,
      prediction: { status: "failed" },
      summary: null,
    });
    assert.match(html, /data-prediction-status="failed"/);
    assert.match(html, /予想取得失敗/);
    assert.match(html, /豊栄特別/);
    assert.doesNotMatch(html, /race-item-honmei/);
  });

  it("missing: Catalog + 予想未公開", () => {
    const html = bind.raceCardSummaryHtml({
      schema_version: "expect-race-card-summary/1.0",
      race_id: "2026-07-25-01-12",
      race_info: {
        venue: "新潟",
        race_number: 12,
        race_name: "未設定",
        post_time: null,
      },
      prediction: { status: "missing" },
      summary: null,
    });
    assert.match(html, /data-prediction-status="missing"/);
    assert.match(html, /予想未公開/);
    assert.match(html, /新潟 12R/);
  });
});

describe("Flag OFF 恒等 — raceCardHtml", () => {
  it("v1 raceCardHtml は PredictionBundle 形のまま（honmei / status 属性なし）", () => {
    const bind = loadBind();
    const html = bind.raceCardHtml({
      race_id: "2026-07-25-01-06",
      race_info: {
        venue: "新潟",
        race_no: 6,
        race_name: "豊栄特別",
        post_time: "10:35",
        date: "2026-07-25",
      },
      ai_confidence: { score: 0.42, band: "medium" },
    });
    assert.doesNotMatch(html, /data-prediction-status/);
    assert.doesNotMatch(html, /race-item-honmei/);
    assert.match(html, /race-item/);
    assert.match(html, /42%<small>AI信頼度<\/small>/);
  });
});

describe("Feature Flag 既定", () => {
  it("beta.json / ui-features で v2_race_list_ui は false", () => {
    const beta = JSON.parse(readFileSync(join(ROOT, "public/config/beta.json"), "utf8"));
    assert.equal(beta.ui_features.v2_race_list_ui, false);
    const ui = readFileSync(join(ROOT, "public/assets/api/ui-features.js"), "utf8");
    assert.match(ui, /v2_race_list_ui:\s*false/);
  });
});
