/**
 * Phase 2 URL 同期 — ExpectRaceListUrl 契約テスト
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function loadRaceListUrl(sandboxExtras) {
  const code = readFileSync(join(ROOT, "public/assets/api/race-list-url.js"), "utf8");
  const calCode = readFileSync(
    join(ROOT, "public/assets/api/calendar-weekend.js"),
    "utf8"
  );
  const historyCalls = [];
  const location = {
    pathname: "/races.html",
    search: "",
    hash: "",
  };
  const history = {
    pushState(state, _title, url) {
      historyCalls.push({ type: "push", state, url });
      const u = new URL(url, "https://example.test");
      location.pathname = u.pathname;
      location.search = u.search;
      location.hash = u.hash;
    },
    replaceState(state, _title, url) {
      historyCalls.push({ type: "replace", state, url });
      const u = new URL(url, "https://example.test");
      location.pathname = u.pathname;
      location.search = u.search;
      location.hash = u.hash;
    },
  };
  const sandbox = {
    Date,
    URLSearchParams,
    console,
    location,
    history,
    window: null,
    ...sandboxExtras,
  };
  sandbox.window = sandbox;
  vm.runInNewContext(calCode + "\n" + code, sandbox);
  return {
    api: sandbox.ExpectRaceListUrl,
    location,
    historyCalls,
  };
}

describe("ExpectRaceListUrl.isValidIsoDate", () => {
  it("accepts real calendar YYYY-MM-DD", () => {
    const { api } = loadRaceListUrl();
    assert.equal(api.isValidIsoDate("2026-07-25"), true);
    assert.equal(api.isValidIsoDate("2026-02-28"), true);
  });

  it("rejects format / impossible dates", () => {
    const { api } = loadRaceListUrl();
    assert.equal(api.isValidIsoDate("2026-7-25"), false);
    assert.equal(api.isValidIsoDate("07/25"), false);
    assert.equal(api.isValidIsoDate("2026-02-30"), false);
    assert.equal(api.isValidIsoDate("not-a-date"), false);
    assert.equal(api.isValidIsoDate(""), false);
  });
});

describe("ExpectRaceListUrl.resolveFromLocation", () => {
  it("URL date を優先する", () => {
    const { api } = loadRaceListUrl();
    const r = api.resolveFromLocation({ search: "?date=2026-07-26" });
    assert.equal(r.date, "2026-07-26");
    assert.equal(r.source, "url");
    assert.equal(r.replaced, false);
  });

  it("date なし → none（すべて）", () => {
    const { api } = loadRaceListUrl();
    const r = api.resolveFromLocation({ search: "" });
    assert.equal(r.date, null);
    assert.equal(r.source, "none");
  });

  it("不正 date → 週末カレンダーへフォールバック", () => {
    // 2026-07-22 は水曜 → next Saturday 2026-07-25
    const now = new Date("2026-07-22T03:00:00+09:00");
    const { api } = loadRaceListUrl();
    const r = api.resolveFromLocation({ search: "?date=bogus", now });
    assert.equal(r.source, "fallback");
    assert.equal(r.replaced, true);
    assert.equal(r.date, "2026-07-25");
  });
});

describe("ExpectRaceListUrl.writeDate / normalizeLocation", () => {
  it("タブ操作相当: push で ?date= を更新", () => {
    const { api, location, historyCalls } = loadRaceListUrl();
    api.writeDate("2026-07-25", { mode: "push" });
    assert.equal(location.search, "?date=2026-07-25");
    assert.equal(historyCalls[0].type, "push");
  });

  it("すべて: date クエリを削除", () => {
    const { api, location } = loadRaceListUrl();
    location.search = "?date=2026-07-25&x=1";
    api.writeDate(null, { mode: "push", search: location.search });
    assert.equal(location.search, "?x=1");
  });

  it("不正パラメータは replaceState で正規化", () => {
    const now = new Date("2026-07-22T03:00:00+09:00");
    const { api, location, historyCalls } = loadRaceListUrl();
    location.search = "?date=invalid";
    const date = api.normalizeLocation({ search: location.search, now });
    assert.equal(date, "2026-07-25");
    assert.equal(location.search, "?date=2026-07-25");
    assert.ok(historyCalls.some((c) => c.type === "replace"));
  });
});

describe("Feature Flag 非干渉（URL モジュール単体）", () => {
  it("ui_features に依存しない（Flag OFF でもモジュールは動作）", () => {
    const { api } = loadRaceListUrl();
    assert.equal(typeof api.resolveFromLocation, "function");
    assert.equal(typeof api.writeDate, "function");
    // beta / ExpectUiFeatures 未注入でも resolve 可能
    const r = api.resolveFromLocation({ search: "?date=2026-07-25" });
    assert.equal(r.date, "2026-07-25");
  });
});
