import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { mkdtempSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { ROOT } from "../helpers/load.mjs";

describe("v2 Ops Phase1 opsMetrics", () => {
  it("buildMetricRow が expect-ops-metrics/1.0 を満たす", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "scripts/ops/opsMetrics.mjs")).href
    );
    const row = m.buildMetricRow({
      source: "ec2-monitor",
      metric: "pi.health.latency_ms",
      value: 42,
      unit: "ms",
      labels: { probe: "pi_health" },
      status: "ok",
    });
    assert.equal(row.schema_version, "expect-ops-metrics/1.0");
    assert.equal(row.source, "ec2-monitor");
    assert.equal(row.metric, "pi.health.latency_ms");
    assert.equal(row.value, 42);
    assert.equal(row.unit, "ms");
    assert.equal(row.status, "ok");
    assert.ok(row.ts);
  });

  it("metricsFromPiChecks が MET-J04 行を生成する", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "scripts/ops/opsMetrics.mjs")).href
    );
    const rows = m.metricsFromPiChecks(
      [
        { name: "pi_systemd", ok: true, detail: { unit: "expect-pi-keibanet-api" } },
        { name: "pi_health", ok: true, latency_ms: 12 },
        { name: "pi_tunnel", ok: false, latency_ms: 900, skipped: false },
      ],
      "ec2-monitor"
    );
    const names = rows.map((r) => r.metric);
    assert.ok(names.includes("pi.systemd.active"));
    assert.ok(names.includes("pi.health.latency_ms"));
    assert.ok(names.includes("pi.health.ok"));
    assert.ok(names.includes("pi.tunnel.health.latency_ms"));
    assert.ok(names.includes("tunnel.reachability.pi"));
  });

  it("appendMetric が jsonl に追記する", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "scripts/ops/opsMetrics.mjs")).href
    );
    const dir = mkdtempSync(join(tmpdir(), "ops-metrics-"));
    const file = join(dir, "pi-metrics.jsonl");
    m.appendMetric(file, {
      source: "pi-probe",
      metric: "pi.health.ok",
      value: 1,
      unit: "bool",
      status: "ok",
    });
    assert.ok(existsSync(file));
    const line = JSON.parse(readFileSync(file, "utf8").trim());
    assert.equal(line.schema_version, "expect-ops-metrics/1.0");
    assert.equal(line.metric, "pi.health.ok");
  });
});

describe("v2 Ops Phase1 opsSlack SLK-N01", () => {
  it("webhook 未設定時は no-op", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "scripts/ops/opsSlack.mjs")).href
    );
    m._resetSlackSuppress();
    const prev = process.env.OPS_SLACK_WEBHOOK_URL;
    delete process.env.OPS_SLACK_WEBHOOK_URL;
    delete process.env.OPS_SLACK_WEBHOOK_CRITICAL;
    const r = await m.notifySlackCritical({
      alert_id: "ALT-E02",
      service: "pi_health",
      error: "down",
    });
    assert.equal(r.sent, false);
    assert.equal(r.reason, "webhook_unset");
    if (prev) process.env.OPS_SLACK_WEBHOOK_URL = prev;
  });

  it("同一 Alert ID は 15 分抑制", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "scripts/ops/opsSlack.mjs")).href
    );
    m._resetSlackSuppress();
    const calls = [];
    const fakeFetch = async function (url, init) {
      calls.push({ url, init });
      return { ok: true };
    };
    const r1 = await m.notifySlackCritical(
      { alert_id: "ALT-E05", error: "inactive" },
      { webhookUrl: "https://hooks.example/x", now: 1000, fetch: fakeFetch }
    );
    const r2 = await m.notifySlackCritical(
      { alert_id: "ALT-E05", error: "inactive" },
      { webhookUrl: "https://hooks.example/x", now: 1000 + 60_000, fetch: fakeFetch }
    );
    assert.equal(r1.sent, true);
    assert.equal(r2.sent, false);
    assert.equal(r2.reason, "suppressed");
    assert.equal(calls.length, 1);
    m._resetSlackSuppress();
  });
});

describe("v2 Ops Phase1 BFF opsMonitor PI", () => {
  it("probePiHealth / runAllProbes が export されている", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsMonitor.js")).href
    );
    assert.equal(typeof m.probePiHealth, "function");
    assert.equal(typeof m.runAllProbes, "function");
  });

  it("PI_BASE_URL 未設定時 probePiHealth は skipped", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsMonitor.js")).href
    );
    const r = await m.probePiHealth({
      env: {},
      request: new Request("https://example.com/api/ops/monitor"),
    });
    assert.equal(r.name, "pi_health");
    assert.equal(r.skipped, true);
    assert.equal(r.ok, true);
  });
});

describe("v2 Ops Phase1 BFF opsMetrics", () => {
  it("logMetric が expect-ops-metrics/1.0 行を返す", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsMetrics.js")).href
    );
    const row = m.logMetric(null, {
      metric: "pi.health.ok",
      value: 1,
      unit: "bool",
      status: "ok",
    });
    assert.equal(row.schema_version, "expect-ops-metrics/1.0");
    assert.equal(row.source, "bff-probe");
  });
});

describe("v2 Ops Phase1 assets", () => {
  it("契約・スクリプト・Flag が存在する", async () => {
    assert.ok(existsSync(join(ROOT, "contracts/expect-ops-metrics/1.0/schema.json")));
    assert.ok(existsSync(join(ROOT, "scripts/ops/monitor-prod.mjs")));
    assert.ok(existsSync(join(ROOT, "scripts/ops/opsMetrics.mjs")));
    assert.ok(existsSync(join(ROOT, "scripts/ops/opsSlack.mjs")));
    const beta = JSON.parse(readFileSync(join(ROOT, "config/beta.json"), "utf8"));
    assert.equal(beta.ui_features.v2_ops_dashboard, false);
  });
});
