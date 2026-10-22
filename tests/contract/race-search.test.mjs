/**
 * Phase 4 — Race Catalog 検索（data-race-honmei + summary 対象）
 * Flag OFF（v1 カード）恒等も検証。
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function loadScript(rel, extras) {
  const code = readFileSync(join(ROOT, rel), "utf8");
  const sandbox = {
    window: null,
    console,
    ExpectUiFeatures: { enabled: () => false },
    ...(extras || {}),
  };
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox);
  return sandbox;
}

function loadSearch(flagOn) {
  return loadScript("public/assets/api/race-search.js", {
    ExpectUiFeatures: { enabled: (n) => flagOn && n === "v2_race_list_ui" },
  }).ExpectRaceSearch;
}

function loadBind() {
  return loadScript("public/assets/api/prediction-bind.js").ExpectPredictionBind;
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
    short_reason: null,
  },
};

describe("raceCardSummaryHtml / data-race-honmei", () => {
  it("ready カードに data-race-honmei と data-confidence-band", () => {
    const bind = loadBind();
    const html = bind.raceCardSummaryHtml(ready, { listDate: "2026-07-25" });
    // データ連携用の属性（検索・お気に入りが使用）
    assert.match(html, /data-race-honmei="コルドンブルー"/);
    assert.match(html, /data-confidence-band="medium"/);
    assert.match(html, /data-prediction-status="ready"/);
    // 読み上げ契約（現行）: リンクの識別情報はテキストで提供され、
    // 自信度欄とお気に入りボタンに aria-label が付く。
    // 一覧で視覚表示していない本命情報を、読み上げ専用の
    // aria-label としては要求しない。
    assert.match(html, /新潟 6R/);
    assert.match(html, /豊栄特別/);
    assert.match(html, /aria-label="このレースの自信度 [^"]+"/);
    assert.match(html, /aria-label="お気に入りに追加"/);
    assert.doesNotMatch(html, /aria-label="本命/);
  });

  it("missing は data-race-honmei 空文字", () => {
    const bind = loadBind();
    const html = bind.raceCardSummaryHtml({
      ...ready,
      prediction: { status: "missing" },
      summary: null,
    });
    assert.match(html, /data-race-honmei=""/);
  });
});

describe("ExpectRaceSearch / v2 enhanced", () => {
  const search = loadSearch(true);

  it("本命馬名でマッチ", () => {
    const fields = {
      date: "2026-07-25",
      venue: "新潟",
      name: "豊栄特別",
      place: "新潟 6R",
      honmei: "コルドンブルー",
      conf: 42,
      band: "medium",
      v2Enhanced: true,
    };
    assert.equal(search.matchRaceSearch(fields, { q: "コルドン", date: "all", venue: "all" }), true);
    assert.equal(search.matchRaceSearch(fields, { q: "存在しない馬", date: "all", venue: "all" }), false);
  });

  it("信頼度% / band でマッチ", () => {
    const fields = {
      date: "2026-07-25",
      venue: "新潟",
      name: "豊栄特別",
      place: "新潟 6R",
      honmei: "コルドンブルー",
      conf: 42,
      band: "medium",
      v2Enhanced: true,
    };
    assert.equal(search.matchRaceSearch(fields, { q: "42", date: "all", venue: "all" }), true);
    assert.equal(search.matchRaceSearch(fields, { q: "medium", date: "all", venue: "all" }), true);
    assert.equal(search.matchRaceSearch(fields, { q: "ふつう", date: "all", venue: "all" }), true);
  });

  it("会場 + 本命の複合トークン", () => {
    const fields = {
      date: "2026-07-25",
      venue: "新潟",
      name: "豊栄特別",
      place: "新潟 6R",
      honmei: "コルドンブルー",
      conf: 42,
      band: "medium",
      v2Enhanced: true,
    };
    assert.equal(
      search.matchRaceSearch(fields, { q: "新潟 コルドン", date: "all", venue: "all" }),
      true
    );
  });
});

describe("Flag OFF 恒等 — 検索 haystack", () => {
  it("v2Enhanced=false では honmei/conf を検索に含めない", () => {
    const search = loadSearch(false);
    const hay = search.buildSearchHaystack({
      date: "2026-07-25",
      venue: "新潟",
      name: "豊栄特別",
      place: "新潟 6R",
      honmei: "コルドンブルー",
      conf: 42,
      band: "medium",
      v2Enhanced: false,
    });
    assert.doesNotMatch(hay, /コルドン/);
    assert.doesNotMatch(hay, /42/);
    assert.match(hay, /豊栄特別/);
  });

  it("v1 raceCardHtml に data-race-honmei / data-prediction-status なし", () => {
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
    assert.doesNotMatch(html, /data-race-honmei/);
    assert.doesNotMatch(html, /data-prediction-status/);
  });

  it("v1 カード相当 fields は Catalog クエリのみ（Flag OFF）", () => {
    const search = loadSearch(false);
    const el = {
      getAttribute(name) {
        const m = {
          "data-race-date": "2026-07-25",
          "data-race-venue": "新潟",
          "data-race-name": "豊栄特別",
          "data-race-place": "新潟 6R",
          "data-race-conf": "42",
        };
        return m[name] || null;
      },
      hasAttribute(name) {
        return name !== "data-prediction-status";
      },
    };
    // Flag OFF + no prediction-status → v2Enhanced false
    assert.equal(
      search.matchElement(el, { q: "コルドン", date: "all", venue: "all" }),
      false
    );
    assert.equal(
      search.matchElement(el, { q: "豊栄", date: "all", venue: "all" }),
      true
    );
    // conf は v1 でも属性にあるが、拡張 OFF では検索対象外
    assert.equal(
      search.matchElement(el, { q: "42", date: "all", venue: "all" }),
      false
    );
  });
});

describe("Feature Flag 既定（検索は v2_race_list_ui に連動）", () => {
  it("コード既定値: v2_race_list_ui は OFF（本番設定の実値は検証しない）", () => {
    // Flag の契約は 2 層に分かれる（実値を検証するものではない）:
    //  - コード既定値: betaConfig.js の DEFAULTS では OFF
    //  - 本番設定値: public/config/beta.json は Release Version 2
    //    （commit 03e7a4f5）で意図的に ON
    const src = readFileSync(join(ROOT, "functions/_lib/betaConfig.js"), "utf8");
    const m = src.match(/v2_race_list_ui:\s*(true|false)/);
    assert.ok(m, "betaConfig.js に v2_race_list_ui 既定値が存在する");
    assert.equal(m[1], "false");
    const beta = JSON.parse(readFileSync(join(ROOT, "public/config/beta.json"), "utf8"));
    assert.equal(typeof beta.ui_features.v2_race_list_ui, "boolean");
  });

  it("races.html が race-search.js を読み込む", () => {
    const html = readFileSync(join(ROOT, "public/races.html"), "utf8");
    assert.match(html, /race-search\.js/);
    assert.match(html, /本命馬名/);
  });
});
