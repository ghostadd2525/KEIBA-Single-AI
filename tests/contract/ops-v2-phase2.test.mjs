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
  it("v2_ops_dashboard 既定は false", () => {
    const beta = JSON.parse(readFileSync(join(ROOT, "config/beta.json"), "utf8"));
    const pub = JSON.parse(readFileSync(join(ROOT, "public/config/beta.json"), "utf8"));
    assert.equal(beta.ui_features.v2_ops_dashboard, false);
    assert.equal(pub.ui_features.v2_ops_dashboard, false);
  });

  it("ops.html の v2 セクションは Flag ゲート付き", () => {
    const html = readFileSync(join(ROOT, "public/ops.html"), "utf8");
    assert.ok(html.includes('id="opsV2Root"'));
    assert.ok(html.includes("features.v2_ops_dashboard"));
    assert.ok(html.includes("/api/ops/dashboard"));
    assert.ok(html.includes('v2Root.hidden = true') || html.includes("v2Root.hidden = true"));
  });
});

describe("v2 Ops Phase2 Flag OFF 恒等性", () => {
  it("Flag OFF 時の latency note 文言が v1.1 パスを維持", () => {
    const html = readFileSync(join(ROOT, "public/ops.html"), "utf8");
    assert.ok(
      html.includes(
        "Latency / Errors はクライアント計測。サーバ新規メトリクス API は追加していません。"
      )
    );
    /* v2 root は hidden 初期 + Flag OFF で再 hidden */
    assert.match(html, /id="opsV2Root"[^>]*hidden/);
  });

  it("v1.1 基本カード 8 種が残存", () => {
    const html = readFileSync(join(ROOT, "public/ops.html"), "utf8");
    [
      "Health",
      "API応答 (health)",
      "API応答 (predictions)",
      "Prediction件数",
      "mock_fallback率",
      "AI成功率 (real_ai)",
      "Collector",
      "Predictions取得",
    ].forEach(function (label) {
      assert.ok(html.includes(label), "missing card " + label);
    });
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
