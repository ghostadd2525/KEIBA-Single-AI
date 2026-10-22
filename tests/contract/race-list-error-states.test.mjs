/**
 * レース一覧のエラー状態分離（Phase 4-D）
 *
 * - API クライアント（race.js）: 上流エラーで reject し、正常時は items を返す。
 * - races.html（静的契約）: 失敗した日付を空結果と区別し、全件失敗では
 *   通信エラーを表示し、部分失敗では注記を1つだけ出す構造になっていること。
 *
 * DOM の最終状態はこの基盤では実測できないため、静的契約と API 層の
 * 挙動で担保する（ブラウザ確認は別工程）。
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function loadRaceApi(fetchImpl) {
  const code = readFileSync(join(ROOT, "public/assets/api/race.js"), "utf8");
  const sandbox = {
    window: null,
    console,
    fetch: fetchImpl,
    localStorage: { getItem: () => "" },
    location: { search: "" },
    URLSearchParams,
  };
  sandbox.window = sandbox;
  vm.runInNewContext(code, sandbox);
  return sandbox.ExpectApi.Race;
}

function jsonResp(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

describe("ExpectApi.Race.list のエラー挙動", () => {
  it("上流 502（PI_BAD_RESPONSE）では reject し、空結果に化けない", async () => {
    const Race = loadRaceApi(async () =>
      jsonResp(502, {
        ok: false,
        error: { code: "PI_BAD_RESPONSE", message: "PI KeibaNet API returned non-JSON" },
      })
    );
    await assert.rejects(() => Race.list({ date: "2026-10-24" }), /non-JSON/);
  });

  it("正常な空結果は items: [] で解決する", async () => {
    const Race = loadRaceApi(async () =>
      jsonResp(200, { ok: true, data: { date: "2026-10-24", races: [] } })
    );
    const r = await Race.list({ date: "2026-10-24" });
    assert.ok(Array.isArray(r.items));
    assert.equal(r.items.length, 0);
  });

  it("正常時は races を items に整形して返す", async () => {
    const Race = loadRaceApi(async () =>
      jsonResp(200, {
        ok: true,
        data: {
          date: "2026-10-24",
          races: [{ race_id: "2026-10-24-01-01", course: "東京", race_number: 1 }],
        },
      })
    );
    const r = await Race.list({ date: "2026-10-24" });
    assert.equal(r.items.length, 1);
    assert.equal(r.items[0].race_id, "2026-10-24-01-01");
  });
});

describe("races.html のエラー状態分離（静的契約）", () => {
  const html = readFileSync(join(ROOT, "public/races.html"), "utf8");

  it("取得失敗した日付を failedDates として空結果と区別する", () => {
    assert.match(html, /failedDates/);
    assert.match(html, /failed: true/);
    assert.match(html, /failed: false/);
  });

  it("全日付失敗では通信エラーを表示し、空状態にしない分岐がある", () => {
    assert.match(html, /cat\.failedDates\.length >= dates\.length/);
    assert.match(html, /renderError\("通信エラーのため一覧を更新できませんでした。"\)/);
  });

  it("正常な空結果の表示（レースがありません）は維持される", () => {
    assert.match(html, /レースがありません。/);
  });

  it("部分失敗の注記は1箇所だけに定義され、再描画で重複しない構造である", () => {
    const occurrences = html.split("race-list-partial-note").length - 1;
    assert.equal(occurrences, 1);
    assert.match(html, /一部の日付のレース情報を取得できませんでした。/);
  });

  it("エラー表示でローディングが解除される", () => {
    assert.match(html, /function renderError\(message\) \{\s*\n\s*if \(window\.ExpectUx && ExpectUx\.hideLoading\)/);
    assert.match(html, /aria-busy", "false"/);
  });

  it("再試行は全体再読み込みで、状態が重複しない", () => {
    assert.match(html, /onRetry: function \(\) \{\s*\n\s*location\.reload\(\);/);
  });
});
