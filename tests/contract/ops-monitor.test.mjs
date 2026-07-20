import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { ROOT } from "../helpers/load.mjs";

describe("Phase OPS-Monitor incidentLog", () => {
  it("writeIncident が必須フィールドを含む", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/incidentLog.js")).href
    );
    const line = m.writeIncident(null, {
      service: "python_api",
      error: "connection refused",
      restart_count: 3,
    });
    assert.equal(line.incident, true);
    assert.equal(line.schema_version, "expect-ops-incident/1.0");
    assert.equal(line.service, "python_api");
    assert.equal(line.error, "connection refused");
    assert.equal(line.restart_count, 3);
    assert.ok(line.occurred_at);
  });

  it("logFailedChecks が失敗分のみ記録する", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/incidentLog.js")).href
    );
    const lines = m.logFailedChecks(null, [
      { name: "bff", ok: true },
      { name: "etl", ok: false, error: "failed run" },
    ]);
    assert.equal(lines.length, 1);
    assert.equal(lines[0].service, "etl");
  });
});

describe("Phase OPS-Monitor opsMonitor", () => {
  it("verifyMonitorKey は未設定時 true", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsMonitor.js")).href
    );
    const ok = m.verifyMonitorKey({
      env: {},
      request: new Request("https://example.com/api/ops/monitor"),
    });
    assert.equal(ok, true);
  });

  it("verifyMonitorKey はキー一致を要求", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsMonitor.js")).href
    );
    const ok = m.verifyMonitorKey({
      env: { OPS_MONITOR_KEY: "secret" },
      request: new Request("https://example.com/api/ops/monitor", {
        headers: { "x-ops-monitor-key": "secret" },
      }),
    });
    assert.equal(ok, true);
  });
});

describe("Phase OPS-Hardening result_automation probe", () => {
  it("probeResultAutomation が export されている", async () => {
    const m = await import(
      pathToFileURL(join(ROOT, "functions/_lib/opsMonitor.js")).href
    );
    assert.equal(typeof m.probeResultAutomation, "function");
    assert.equal(typeof m.runAllProbes, "function");
  });

  it("hardening docs / recovery module が存在する", async () => {
    const { existsSync } = await import("node:fs");
    assert.ok(existsSync(join(ROOT, "docs/ops/ops-hardening-runbook.md")));
    assert.ok(existsSync(join(ROOT, "docs/ops/gameday-live-e2e.md")));
    assert.ok(
      existsSync(
        join(ROOT, "services/win5-ai/app/ops/run_recovery.py")
      )
    );
  });
});
