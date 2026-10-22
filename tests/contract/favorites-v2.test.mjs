/**
 * Phase 5 — お気に入り × RaceCardSummary
 * Flag OFF（v1.1）恒等も検証。
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

const ready = {
  schema_version: "expect-race-card-summary/1.0",
  race_id: "2026-07-25-01-06",
  race_info: {
    venue: "新潟",
    race_number: 6,
    race_name: "豊栄特別",
    post_time: "10:35",
    grade: "—",
  },
  prediction: { status: "ready", engine_source: "pi" },
  summary: {
    honmei: { horse_number: 4, horse_name: "コルドンブルー", mark: "honmei" },
    confidence: { score: 0.42, band: "medium" },
    short_reason: null,
  },
};

function loadFavorites(flagOn) {
  const store = {};
  const sandbox = {
    console,
    localStorage: {
      getItem(k) {
        return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null;
      },
      setItem(k, v) {
        store[k] = String(v);
      },
      removeItem(k) {
        delete store[k];
      },
    },
    CustomEvent: class CustomEvent {
      constructor(type, init) {
        this.type = type;
        this.detail = init && init.detail;
      }
    },
    ExpectUiFeatures: {
      enabled: (n) => flagOn && n === "v2_race_list_ui",
    },
    ExpectMockGate: { allowMockFallback: () => false },
    document: {
      addEventListener() {},
      querySelectorAll() {
        return [];
      },
    },
    addEventListener() {},
    dispatchEvent() {
      return true;
    },
  };
  sandbox.window = sandbox;
  const code = readFileSync(join(ROOT, "public/assets/favorites.js"), "utf8");
  vm.runInNewContext(code, sandbox);
  return { Fav: sandbox.ExpectFavorites, store };
}

function loadBind() {
  const sandbox = { window: null, console };
  sandbox.window = sandbox;
  const code = readFileSync(
    join(ROOT, "public/assets/api/prediction-bind.js"),
    "utf8"
  );
  vm.runInNewContext(code, sandbox);
  return sandbox.ExpectPredictionBind;
}

describe("RaceCardSummary → ExpectFavorites", () => {
  it("isRaceCardSummary / summaryFieldsFromBundle", () => {
    const { Fav } = loadFavorites(true);
    assert.equal(Fav.isRaceCardSummary(ready), true);
    assert.equal(Fav.isRaceCardSummary({ race_id: "x", ai_confidence: {} }), false);
    const fields = Fav.summaryFieldsFromBundle(ready);
    assert.equal(fields.honmei, "コルドンブルー");
    assert.equal(fields.honmeiNum, 4);
    assert.equal(fields.confPct, 42);
    assert.equal(fields.confBand, "medium");
  });

  it("cacheBundles 後 add で localStorage に ◎/信頼度を保存", () => {
    const { Fav, store } = loadFavorites(true);
    Fav.cacheBundles([ready]);
    const result = Fav.add(ready.race_id);
    assert.equal(result.ok, true);
    const item = Fav.list()[0];
    assert.equal(item.honmei, "コルドンブルー");
    assert.equal(item.honmeiNum, 4);
    assert.equal(item.confPct, 42);
    assert.equal(item.place, "新潟 6R");
    assert.equal(item.name, "豊栄特別");
    // 保存先キーは実装のキー解決（ユーザー未ログイン時は :guest）に従う。
    // 旧キー名を固定参照せず、実装が書いた先を検証する。
    const savedKeys = Object.keys(store).filter((k) =>
      k.startsWith("expect_favorites_v1")
    );
    assert.equal(savedKeys.length, 1, "favorites 保存キーが 1 件だけある");
    const raw = JSON.parse(store[savedKeys[0]]);
    assert.equal(raw[0].honmei, "コルドンブルー");
    assert.equal(raw[0].confPct, 42);
  });

  it("cacheBundles は既存 fav を summary で enrich", () => {
    const { Fav } = loadFavorites(true);
    Fav.add(ready.race_id, { place: "旧", name: "旧名" });
    Fav.cacheBundles([ready]);
    const item = Fav.list()[0];
    assert.equal(item.honmei, "コルドンブルー");
    assert.equal(item.confPct, 42);
    assert.equal(item.place, "新潟 6R");
  });
});

describe("cardHtml / ホーム表示契約", () => {
  // 現行仕様: ホームのお気に入りカードはレース情報のみを表示し、
  // 本命・信頼度は出さない（public/assets/styles.css の
  // 「ホームお気に入りはレース情報のみ（予想・信頼度は出さない）」）。
  // 本命・信頼度のデータ保持は表示とは分けて検証する。
  it("Flag ON でもホームカードに本命・信頼度を表示しない（データは保持）", () => {
    const { Fav } = loadFavorites(true);
    Fav.cacheBundles([ready]);
    Fav.add(ready.race_id);
    const item = Fav.list()[0];
    // データ保持: 本命・信頼度は item に保持される
    assert.equal(item.honmei, "コルドンブルー");
    assert.equal(item.honmeiNum, 4);
    assert.equal(item.confPct, 42);
    // 表示: fav-summary / 本命 / 信頼度% は出力されない
    const html = Fav.cardHtml(item, false);
    assert.doesNotMatch(html, /fav-summary/);
    assert.doesNotMatch(html, /◎/);
    assert.doesNotMatch(html, /コルドンブルー/);
    assert.doesNotMatch(html, /42%/);
    // レース識別情報は表示される
    assert.match(html, /fav-name/);
    assert.match(html, /豊栄特別/);
    assert.match(html, /新潟 6R/);
  });

  it("Flag OFF でも表示は同じで、データは保持される", () => {
    const { Fav } = loadFavorites(false);
    Fav.cacheBundles([ready]);
    Fav.add(ready.race_id);
    const item = Fav.list()[0];
    assert.equal(item.honmei, "コルドンブルー");
    const html = Fav.cardHtml(item, false);
    assert.doesNotMatch(html, /fav-summary/);
    assert.doesNotMatch(html, /コルドンブルー/);
    assert.doesNotMatch(html, /42%/);
    assert.match(html, /fav-name/);
    assert.match(html, /豊栄特別/);
  });
});

describe("raceCardSummaryHtml / data-fav-*", () => {
  it("ready カードの ★ に honmei / conf 属性", () => {
    const bind = loadBind();
    const html = bind.raceCardSummaryHtml(ready, { listDate: "2026-07-25" });
    assert.match(html, /data-fav-honmei="コルドンブルー"/);
    assert.match(html, /data-fav-honmei-num="4"/);
    assert.match(html, /data-fav-conf="42"/);
    assert.match(html, /data-fav-band="medium"/);
  });

  it("v1 raceCardHtml に data-fav-honmei なし（Flag OFF 経路）", () => {
    const bind = loadBind();
    const html = bind.raceCardHtml({
      race_id: "20260719_tokyo_11",
      race_info: {
        date: "2026-07-19",
        venue: "東京",
        race_no: 11,
        class_label: "函館記念",
        grade: "GIII",
        post_time: "15:45",
      },
      ai_confidence: { score: 0.88 },
    });
    assert.doesNotMatch(html, /data-fav-honmei/);
    assert.doesNotMatch(html, /data-fav-conf/);
    assert.match(html, /data-fav-toggle=/);
  });
});

describe("beta.json Flag 既定", () => {
  // Flag の契約は 2 層（コード既定値と本番設定値）に分かれる。
  // config/beta.json は Release Version 2（commit 03e7a4f5）で意図的に ON のため、
  // 実値を false と断言せず、コード既定値が OFF であることを固定する。
  it("コード既定値: betaConfig.js の v2_race_list_ui は OFF", () => {
    const src = readFileSync(
      join(ROOT, "functions/_lib/betaConfig.js"),
      "utf8"
    );
    const m = src.match(/v2_race_list_ui:\s*(true|false)/);
    assert.ok(m, "betaConfig.js に v2_race_list_ui 既定値が存在する");
    assert.equal(m[1], "false");
  });

  it("本番設定: config/beta.json の v2_race_list_ui は存在し boolean（実値は検証しない）", () => {
    const beta = JSON.parse(
      readFileSync(join(ROOT, "config/beta.json"), "utf8")
    );
    assert.equal(typeof beta.ui_features.v2_race_list_ui, "boolean");
  });
});
