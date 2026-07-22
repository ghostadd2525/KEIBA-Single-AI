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

describe("v2 Ops Phase3 Flag OFF 恒等性", () => {
  it("v2_ops_dashboard 既定 false · opsV2Root hidden", () => {
    const beta = JSON.parse(readFileSync(join(ROOT, "config/beta.json"), "utf8"));
    assert.equal(beta.ui_features.v2_ops_dashboard, false);
    const html = readFileSync(join(ROOT, "public/ops.html"), "utf8");
    assert.match(html, /id="opsV2Root"[^>]*hidden/);
    assert.ok(
      html.includes(
        "Latency / Errors はクライアント計測。サーバ新規メトリクス API は追加していません。"
      )
    );
    assert.ok(html.includes("Overview"));
    assert.ok(html.includes("監視項目 Inventory"));
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
