import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { readFileSync, existsSync } from "node:fs";
import { ROOT } from "../helpers/load.mjs";

describe("v2 Ops Phase3 dashboard final", () => {
  it("overview / inventory / notifications / runbook を含む", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsDashboard.js")).href
    );
    const dash = m.buildDashboardPayload(
      {
        status: "degraded",
        generated_at: "2026-07-22T06:00:00.000Z",
        checks: [
          { name: "bff", ok: true, latency_ms: 1 },
          { name: "pi_health", ok: false, latency_ms: 40, error: "down" },
          { name: "etl", ok: false, error: "failed" },
        ],
      },
      {
        notifications: {
          slackCriticalConfigured: true,
          slackWarningConfigured: false,
        },
      }
    );
    assert.equal(dash.phase, "v2-ops-phase3");
    assert.ok(dash.overview);
    assert.equal(dash.overview.probes_down, 2);
    assert.ok(dash.inventory.length >= 10);
    assert.ok(dash.inventory_summary.wired >= 1);
    assert.equal(dash.notifications.slack_critical.configured, true);
    assert.equal(dash.notifications.slack_warning.configured, false);
    const alt = dash.alerts.find((a) => a.alert_id === "ALT-E02");
    assert.ok(alt);
    assert.ok(String(alt.runbook).includes("v2-operations-runbook"));
  });
});

describe("v2 Ops Phase3 Slack SLK-N02", () => {
  it("warning / recovery を severity 別に送れる", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "scripts/ops/opsSlack.mjs")).href
    );
    m._resetSlackSuppress();
    const calls = [];
    const fakeFetch = async function (url, init) {
      calls.push(JSON.parse(init.body));
      return { ok: true };
    };
    const w = await m.notifySlackWarning(
      { alert_id: "ALT-E09", summary: "etl" },
      { webhookUrl: "https://hooks.example/w", now: 5000, fetch: fakeFetch }
    );
    const r = await m.notifySlackRecovery(
      { alert_id: "ALT-E02", summary: "recovered" },
      { webhookUrl: "https://hooks.example/w", now: 6000, fetch: fakeFetch }
    );
    assert.equal(w.sent, true);
    assert.equal(r.sent, true);
    assert.ok(calls[0].text.includes("warning"));
    assert.ok(calls[1].text.includes("recovery"));
    m._resetSlackSuppress();
  });

  it("dispatchAlerts が critical/warning を振り分ける", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "scripts/ops/opsSlack.mjs")).href
    );
    m._resetSlackSuppress();
    const calls = [];
    const fakeFetch = async function (_u, init) {
      calls.push(JSON.parse(init.body).text);
      return { ok: true };
    };
    await m.dispatchAlerts(
      [
        { alert_id: "ALT-E02", severity: "critical", active: true, summary: "pi" },
        { alert_id: "ALT-E08", severity: "warning", active: true, summary: "ra" },
      ],
      { webhookUrl: "https://hooks.example/x", now: 9000, fetch: fakeFetch }
    );
    assert.equal(calls.length, 2);
    assert.ok(calls[0].includes("critical"));
    assert.ok(calls[1].includes("warning"));
    m._resetSlackSuppress();
  });
});

describe("v2 Ops Phase3 Flag 既定値", () => {
  it("コード既定値: v2_ops_dashboard は OFF", () => {
    // Flag の契約は 2 層に分かれる（実値を検証するものではない）:
    //  - コード既定値: betaConfig.js の DEFAULTS では OFF
    //  - 本番設定値: config/beta.json は Release Version 2
    //    （commit 03e7a4f5）で意図的に ON
    const src = readFileSync(join(ROOT, "functions/_lib/betaConfig.js"), "utf8");
    const m = src.match(/v2_ops_dashboard:\s*(true|false)/);
    assert.ok(m, "betaConfig.js に v2_ops_dashboard 既定値が存在する");
    assert.equal(m[1], "false");
  });
});

describe("v2 Ops dashboard API Flag / 権限（振る舞い）", () => {
  // 旧 Ops V2 ダッシュボードの画面前提（opsV2Root 等）は現行
  // Version8.9 Operations Console に存在しないため、画面ではなく
  // API ハンドラの実際の振る舞い（ステータスコード）を検証する。
  async function loadDashboard() {
    const dash = await import(
      pathToFileURL(join(ROOT, "functions/api/ops/dashboard.js")).href
    );
    const auth = await import(
      pathToFileURL(join(ROOT, "functions/_lib/auth.js")).href
    );
    const beta = await import(
      pathToFileURL(join(ROOT, "functions/_lib/betaConfig.js")).href
    );
    return { dash, auth, beta };
  }
  function ctxWithToken(token) {
    return {
      env: {},
      request: new Request("https://example.com/api/ops/dashboard", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
      data: {},
    };
  }

  it("Flag OFF では 404 FEATURE_DISABLED を返す", async () => {
    const { dash, auth, beta } = await loadDashboard();
    beta._setBetaConfigForTests({
      ui_features: { v2_ops_dashboard: false },
      admin_user_ids: [],
    });
    try {
      const res = await dash.onRequestGet(
        ctxWithToken(auth.makeStubToken("ops-user"))
      );
      assert.equal(res.status, 404);
      const body = await res.json();
      assert.equal(body.error.code, "FEATURE_DISABLED");
    } finally {
      beta._resetBetaConfigCacheForTests();
    }
  });

  it("Flag ON でも非 ADMIN は 403 FORBIDDEN を返す", async () => {
    const { dash, auth, beta } = await loadDashboard();
    beta._setBetaConfigForTests({
      ui_features: { v2_ops_dashboard: true },
      admin_user_ids: [],
    });
    try {
      const res = await dash.onRequestGet(
        ctxWithToken(auth.makeStubToken("ops-user"))
      );
      assert.equal(res.status, 403);
      const body = await res.json();
      assert.equal(body.error.code, "FORBIDDEN");
    } finally {
      beta._resetBetaConfigCacheForTests();
    }
  });
});

describe("v2 Ops Phase3 docs / assets", () => {
  it("最終ドキュメントと Promtail 例が存在する", () => {
    assert.ok(existsSync(join(ROOT, "docs/ops/v2-operations-runbook.md")));
    assert.ok(existsSync(join(ROOT, "docs/ops/v2-operations-architecture-final.md")));
    assert.ok(
      existsSync(join(ROOT, "infra/observability/promtail-ops-metrics.example.yml"))
    );
    assert.ok(existsSync(join(ROOT, "functions/_lib/opsSlack.js")));
  });
});
