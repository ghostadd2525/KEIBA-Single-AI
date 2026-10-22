/**
 * piProxy — 上流エラーの構造化（Phase 4-D）
 *
 * 正常系・既存エラーコードの挙動を維持したまま、本文読み取り失敗が
 * 未処理例外にならず PI_BODY_READ_FAILED になること、診断情報に
 * 本文・内部 URL・認証情報が含まれないことを検証する。
 * 実 fetch は行わず globalThis.fetch をスタブ化する。
 */
import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { piFetch, piFetchStatus } from "../../functions/_lib/piProxy.js";

const ctx = { env: { PI_BASE_URL: "http://pi-internal.example:8081" } };
const originalFetch = globalThis.fetch;

function stubFetch(impl) {
  globalThis.fetch = impl;
}
function resp(status, body, contentType = "application/json") {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (name) =>
        String(name).toLowerCase() === "content-type" ? contentType : null,
    },
    text: async () => body,
  };
}
function bodyReadFailResp() {
  return {
    ok: true,
    status: 200,
    headers: { get: () => "application/json" },
    text: async () => {
      throw new TypeError("body stream error");
    },
  };
}

describe("piFetch 上流エラー処理", () => {
  beforeEach(() => {});
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("有効な JSON は ok:true と payload を返す", async () => {
    stubFetch(async () => resp(200, JSON.stringify({ races: [{ race_id: "r1" }] })));
    const r = await piFetch(ctx, "/v1/races?date=2026-10-24");
    assert.equal(r.ok, true);
    assert.equal(r.payload.races.length, 1);
  });

  it("上流 HTTP エラーはステータスとコードを引き継ぐ", async () => {
    stubFetch(async () =>
      resp(500, JSON.stringify({ error: "UPSTREAM_X", message: "boom" }))
    );
    const r = await piFetch(ctx, "/v1/races?date=2026-10-24");
    assert.ok(r instanceof Response);
    assert.equal(r.status, 500);
    const j = await r.json();
    assert.equal(j.error.code, "UPSTREAM_X");
  });

  it("非 JSON 本文は PI_BAD_RESPONSE（利用者向け details に診断情報を含めない）", async () => {
    stubFetch(async () => resp(200, "<html>Bad Gateway</html>", "text/html; charset=utf-8"));
    const r = await piFetch(ctx, "/v1/races?date=2026-10-24");
    assert.equal(r.status, 502);
    const j = await r.json();
    assert.equal(j.error.code, "PI_BAD_RESPONSE");
    // details は既存契約どおり null 相当で、上流ステータス・Content-Type を含めない
    assert.equal(j.error.details, null);
    const raw = JSON.stringify(j);
    assert.doesNotMatch(raw, /upstream_status/);
    assert.doesNotMatch(raw, /upstream_content_type/);
    assert.doesNotMatch(raw, /text\/html/);
    assert.doesNotMatch(raw, /Bad Gateway/);
    assert.doesNotMatch(raw, /pi-internal/);
  });

  it("空本文は正常系として payload:null を返す", async () => {
    stubFetch(async () => resp(200, ""));
    const r = await piFetch(ctx, "/v1/races?date=2026-10-24");
    assert.equal(r.ok, true);
    assert.equal(r.payload, null);
  });

  it("fetch 接続エラーは PI_UNAVAILABLE", async () => {
    stubFetch(async () => {
      throw new TypeError("fetch failed");
    });
    const r = await piFetch(ctx, "/v1/races?date=2026-10-24");
    assert.equal(r.status, 502);
    const j = await r.json();
    assert.equal(j.error.code, "PI_UNAVAILABLE");
  });

  it("AbortController タイムアウトは PI_TIMEOUT", async () => {
    stubFetch(
      (url, init) =>
        new Promise((_, reject) => {
          init.signal.addEventListener("abort", () =>
            reject(Object.assign(new Error("aborted"), { name: "AbortError" }))
          );
        })
    );
    const r = await piFetch(ctx, "/v1/races?date=2026-10-24", { timeoutMs: 30 });
    assert.equal(r.status, 502);
    const j = await r.json();
    assert.equal(j.error.code, "PI_TIMEOUT");
  });

  it("本文読み取り失敗は例外を投げず PI_BODY_READ_FAILED を返す", async () => {
    stubFetch(async () => bodyReadFailResp());
    const r = await piFetch(ctx, "/v1/races?date=2026-10-24");
    assert.ok(r instanceof Response);
    assert.equal(r.status, 502);
    const j = await r.json();
    assert.equal(j.error.code, "PI_BODY_READ_FAILED");
    const raw = JSON.stringify(j);
    assert.doesNotMatch(raw, /body stream error/);
    assert.doesNotMatch(raw, /pi-internal/);
  });
});

describe("piFetchStatus 上流エラー処理", () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("本文読み取り失敗は例外を投げず PI_BODY_READ_FAILED を返す", async () => {
    stubFetch(async () => bodyReadFailResp());
    const r = await piFetchStatus(ctx, "/v1/predictions/r1");
    assert.equal(r.ok, false);
    assert.equal(r.status, 502);
    assert.equal(r.payload, null);
    assert.equal(r.error, "PI_BODY_READ_FAILED");
  });

  it("非 JSON 本文は PI_BAD_RESPONSE のまま（診断付き）", async () => {
    stubFetch(async () => resp(200, "<html>ng</html>", "text/html"));
    const r = await piFetchStatus(ctx, "/v1/predictions/r1");
    assert.equal(r.ok, false);
    assert.equal(r.error, "PI_BAD_RESPONSE");
    assert.equal(r.diagnostics.upstream_status, 200);
    assert.equal(r.diagnostics.upstream_content_type, "text/html");
  });
});
