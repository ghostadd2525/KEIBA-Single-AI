import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { readFileSync, existsSync } from "node:fs";
import { ROOT } from "../helpers/load.mjs";

describe("v2 Ops Phase2 opsDashboard aggregate", () => {
  it("metrics / alerts / incidents を統一スキーマで集約する", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsDashboard.js")).href
    );
    const report = {
      status: "degraded",
      generated_at: "2026-07-22T00:00:00.000Z",
      pi: {
        overall: "degraded",
        checks: [{ name: "pi_health", ok: false, latency_ms: 50, error: "down", alert_id: "ALT-E02" }],
      },
      checks: [
        { name: "bff", ok: true, latency_ms: 1 },
        { name: "pi_health", ok: false, latency_ms: 50, error: "down", alert_id: "ALT-E02" },
        { name: "cloudflare_tunnel", ok: false, latency_ms: 20, error: "unreachable" },
        { name: "etl", ok: true, skipped: true },
      ],
    };
    const dash = m.buildDashboardPayload(report);
    assert.equal(dash.schema_version, "expect-ops-dashboard/1.0");
    assert.equal(dash.phase, "v2-ops-phase3");
    assert.equal(dash.metrics.schema_version, "expect-ops-metrics/1.0");
    assert.ok(dash.metrics.rows.length >= 2);
    assert.ok(dash.metrics.summary.total > 0);
    assert.equal(dash.pi.overall, "degraded");
    assert.equal(dash.pi.checks.length, 1);
    assert.ok(dash.alerts.some((a) => a.alert_id === "ALT-E02"));
    assert.ok(dash.alerts.some((a) => a.alert_id === "ALT-E03"));
    assert.equal(dash.alert_summary.critical >= 2, true);
    assert.equal(dash.incidents.length, 2);
    assert.equal(dash.incidents[0].schema_version, "expect-ops-incident/1.0");
  });

  it("alertIdForCheck は成功時 null", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsDashboard.js")).href
    );
    assert.equal(m.alertIdForCheck({ name: "pi_health", ok: true }), null);
    assert.equal(m.alertIdForCheck({ name: "pi_health", ok: false }), "ALT-E02");
  });
});

describe("v2 Ops Phase2 Feature Flag", () => {
  it("コード既定値: v2_ops_dashboard は OFF（本番設定の実値は検証しない）", () => {
    // Flag の契約は 2 層に分かれる（実値を検証するものではない）:
    //  - コード既定値: betaConfig.js の DEFAULTS では OFF
    //  - 本番設定値: config/ と public/config/ の beta.json は Release
    //    Version 2（commit 03e7a4f5）で意図的に ON
    const src = readFileSync(join(ROOT, "functions/_lib/betaConfig.js"), "utf8");
    const m = src.match(/v2_ops_dashboard:\s*(true|false)/);
    assert.ok(m, "betaConfig.js に v2_ops_dashboard 既定値が存在する");
    assert.equal(m[1], "false");
    const beta = JSON.parse(readFileSync(join(ROOT, "config/beta.json"), "utf8"));
    const pub = JSON.parse(readFileSync(join(ROOT, "public/config/beta.json"), "utf8"));
    assert.equal(typeof beta.ui_features.v2_ops_dashboard, "boolean");
    assert.equal(typeof pub.ui_features.v2_ops_dashboard, "boolean");
  });

});

describe("現行 Ops Console 契約（ops.html / ops-console-v89）", () => {
  // 旧 Ops V2 ダッシュボード（opsV2Root 等）は Version8.9 Operations
  // Console へ置換済み。ここでは現行ページに実在する契約のみを検証する。
  // 静的検査は「要素と初期状態」の確認に限る（挙動は API 側で別途検証）。
  it("ゲート要素（opsGateNote / opsDenied / opsMain）が初期 hidden で存在する", () => {
    const html = readFileSync(join(ROOT, "public/ops.html"), "utf8");
    assert.ok(html.includes('id="opsGateNote"'));
    assert.match(html, /<div id="opsDenied"[^>]*hidden/);
    assert.match(html, /<div id="opsMain"[^>]*hidden/);
    assert.ok(html.includes("role=ADMIN のみ利用できます"));
  });

  it("タブ（data-ops-section）とペイン（opsPane-*）が対応する", () => {
    const html = readFileSync(join(ROOT, "public/ops.html"), "utf8");
    const tabs = [...html.matchAll(/data-ops-section="([^"]+)"/g)].map((m) => m[1]);
    const panes = [...html.matchAll(/id="opsPane-([^"]+)"/g)].map((m) => m[1]);
    assert.ok(tabs.length >= 10);
    assert.deepEqual([...tabs].sort(), [...panes].sort());
  });

  it("Production 自動適用禁止が明示され、権限ゲートがデータ取得より前に置かれる", () => {
    const html = readFileSync(join(ROOT, "public/ops.html"), "utf8");
    assert.ok(html.includes("Production 自動適用禁止"));
    assert.ok(html.includes("Human Deploy only"));
    const js = readFileSync(
      join(ROOT, "public/assets/ops-console-v89.js"),
      "utf8"
    );
    assert.ok(js.includes("/api/ops/monitor-live"));
    // boot: 権限確認（resolveAdminAccess）→ 不許可なら showDenied、
    // データ取得（loadAll）は許可後にのみ呼ばれる（静的な順序契約）
    const boot = js.slice(js.indexOf("function boot()"));
    assert.ok(boot.includes("resolveAdminAccess"));
    assert.ok(boot.indexOf("showDenied") < boot.indexOf("loadAll();"));
  });
});

describe("Live Monitor API 権限・状態（振る舞い）", () => {
  async function loadMonitorLive() {
    return import(
      pathToFileURL(join(ROOT, "functions/api/ops/monitor-live.js")).href
    );
  }
  async function loadAuthzHelpers() {
    const auth = await import(
      pathToFileURL(join(ROOT, "functions/_lib/auth.js")).href
    );
    const beta = await import(
      pathToFileURL(join(ROOT, "functions/_lib/betaConfig.js")).href
    );
    return { auth, beta };
  }
  function ctxWithToken(token) {
    return {
      env: {},
      request: new Request("https://example.com/api/ops/monitor-live", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
      data: {},
    };
  }

  it("未認証は 401、非 ADMIN は 403（requireOpsAdmin の振る舞い）", async () => {
    const { onRequestGet } = await loadMonitorLive();
    const { auth, beta } = await loadAuthzHelpers();
    beta._setBetaConfigForTests({
      ui_features: { v2_ops_dashboard: true },
      admin_user_ids: ["ops-admin"],
    });
    try {
      const anon = await onRequestGet(ctxWithToken(null));
      assert.equal(anon.status, 401);
      const user = await onRequestGet(
        ctxWithToken(auth.makeStubToken("ops-user"))
      );
      assert.equal(user.status, 403);
      const body = await user.json();
      assert.equal(body.error.code, "FORBIDDEN");
    } finally {
      beta._resetBetaConfigCacheForTests();
    }
  });

  it("ADMIN では Healthy / Failed / Pending / No Data を区別する", async () => {
    const { onRequestGet } = await loadMonitorLive();
    const { auth, beta } = await loadAuthzHelpers();
    beta._setBetaConfigForTests({
      ui_features: { v2_ops_dashboard: true },
      admin_user_ids: ["ops-admin"],
    });
    const json = (obj) =>
      new Response(JSON.stringify(obj), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    const prevFetch = globalThis.fetch;
    globalThis.fetch = async (url) => {
      const u = String(url);
      if (u.includes("/api/health")) {
        return json({
          status: "ok",
          pi: { ok: true, status: "ok", latency_ms: 5 },
          ai_proxy_configured: true,
        });
      }
      if (u.includes("/api/ops/result-automation")) {
        return json({
          data: {
            run: { status: "FAILED", run_id: "r1" },
            race_date: "2026-07-25",
            checked_at: "2026-07-25T00:00:00Z",
          },
        });
      }
      return new Response("not found", { status: 404 });
    };
    const ctx = {
      env: {
        ASSETS: {
          fetch: async (url) => {
            const p = new URL(url).pathname;
            if (p.endsWith("/ops-data/research-scheduler.json")) {
              // week_id のみ（phase / last_run なし）→ Pending
              return json({
                week_id: "2026-W30",
                published_at: "2026-07-25T00:00:00Z",
              });
            }
            if (p.endsWith("/ops-data/portal-snapshot.json")) return json({});
            return new Response("not found", { status: 404 });
          },
        },
      },
      request: new Request("https://example.com/api/ops/monitor-live", {
        headers: {
          Authorization: `Bearer ${auth.makeStubToken("ops-admin")}`,
        },
      }),
      data: {},
    };
    try {
      const res = await onRequestGet(ctx);
      assert.equal(res.status, 200);
      const body = await res.json();
      assert.equal(body.data.schema_version, "expect-v89-monitor-live/1.0");
      assert.equal(body.data.production_auto_apply, false);
      const t = body.data.targets;
      assert.equal(t.Pages.status, "Healthy");
      assert.equal(t.PI.status, "Healthy");
      assert.equal(t.PI.latency_ms, 5);
      assert.equal(t.AI.status, "Healthy");
      assert.equal(t.ResultAutomation.status, "Failed");
      assert.equal(t.ResearchScheduler.status, "Pending");
      assert.equal(t.EC2.status, "No Data");
    } finally {
      globalThis.fetch = prevFetch;
      beta._resetBetaConfigCacheForTests();
    }
  });
});

describe("v2 Ops Phase2 assets", () => {
  it("dashboard API / 集約モジュールが存在する", () => {
    assert.ok(existsSync(join(ROOT, "functions/api/ops/dashboard.js")));
    assert.ok(existsSync(join(ROOT, "functions/_lib/opsDashboard.js")));
  });

  it("incidentLog が alert_id を渡せる", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/incidentLog.js")).href
    );
    const line = m.writeIncident(null, {
      service: "pi_health",
      error: "down",
      alert_id: "ALT-E02",
    });
    assert.equal(line.alert_id, "ALT-E02");
  });
});
