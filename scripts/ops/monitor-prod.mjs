#!/usr/bin/env node
/**
 * Phase OPS-Monitor — 本番 EC2 監視（wrangler 非依存）
 *
 * Version 2 Operations Phase 1:
 *   PI probe (PI-H01/H02/H03) · MET-J04 · ALT-E02/E05 · SLK-N01
 *
 * Usage:
 *   node scripts/ops/monitor-prod.mjs
 *
 * Env:
 *   PYTHON_HEALTH_URL     default http://127.0.0.1:8000/health
 *   PI_HEALTH_URL         default http://127.0.0.1:8081/health
 *   PI_SYSTEMD_UNIT       default expect-pi-keibanet-api
 *   PI_TUNNEL_PROBE_URL   optional Tunnel 経由 PI 到達
 *   BFF_MONITOR_URL       optional
 *   OPS_MONITOR_KEY       BFF monitor key
 *   AI_TUNNEL_HEALTH_URL  optional
 *   OPS_SLACK_WEBHOOK_URL optional Critical Slack (SLK-N01)
 *   EXPECT_OPS_ROOT       state/incidents/metrics 出力ルート
 */
import { appendFileSync, mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { appendMetric, metricsFromPiChecks } from "./opsMetrics.mjs";
import { notifySlackCritical, notifySlackWarning, notifySlackRecovery } from "./opsSlack.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");

const OPS_ROOT = process.env.EXPECT_OPS_ROOT || join(REPO_ROOT, "var", "ops");
const INCIDENTS_FILE = join(OPS_ROOT, "incidents.jsonl");
const STATE_FILE = join(OPS_ROOT, "monitor-state.json");
const REPORT_FILE = join(OPS_ROOT, "monitor-latest.json");
const PI_METRICS_FILE = join(OPS_ROOT, "pi-metrics.jsonl");

const PYTHON_HEALTH = process.env.PYTHON_HEALTH_URL || "http://127.0.0.1:8000/health";
const PI_HEALTH = process.env.PI_HEALTH_URL || "http://127.0.0.1:8081/health";
const PI_UNIT = process.env.PI_SYSTEMD_UNIT || "expect-pi-keibanet-api";
const PI_TUNNEL_PROBE = process.env.PI_TUNNEL_PROBE_URL || "";
const BFF_MONITOR = process.env.BFF_MONITOR_URL || "";
const MONITOR_KEY = process.env.OPS_MONITOR_KEY || "";
const TUNNEL_HEALTH = process.env.AI_TUNNEL_HEALTH_URL || "";
const TIMEOUT_MS = Number(process.env.OPS_PROBE_TIMEOUT_MS || "8000");

function nowIso() {
  return new Date().toISOString();
}

function ensureDirs() {
  mkdirSync(OPS_ROOT, { recursive: true });
}

function readState() {
  if (!existsSync(STATE_FILE)) return { restart_counts: {}, last_status: {} };
  try {
    return JSON.parse(readFileSync(STATE_FILE, "utf8"));
  } catch {
    return { restart_counts: {}, last_status: {} };
  }
}

function writeState(state) {
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
}

function writeIncident(incident) {
  const line = {
    incident: true,
    schema_version: "expect-ops-incident/1.0",
    occurred_at: nowIso(),
    service: incident.service,
    error: incident.error,
    restart_count: incident.restart_count || 0,
    status: incident.status || "down",
    detail: incident.detail || {},
    source: "ec2-monitor",
    ...(incident.alert_id ? { alert_id: incident.alert_id } : {}),
  };
  appendFileSync(INCIDENTS_FILE, JSON.stringify(line) + "\n", "utf8");
  return line;
}

async function fetchJson(url, init) {
  init = init || {};
  const ctrl = new AbortController();
  const timer = setTimeout(function () {
    ctrl.abort();
  }, TIMEOUT_MS);
  const start = Date.now();
  try {
    const res = await fetch(url, { ...init, signal: ctrl.signal });
    const text = await res.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      body = null;
    }
    return {
      ok: res.ok,
      status: res.status,
      body,
      latency_ms: Date.now() - start,
      error: res.ok ? null : (body && body.error && body.error.message) || "HTTP " + res.status,
    };
  } catch (e) {
    return {
      ok: false,
      status: 0,
      body: null,
      latency_ms: Date.now() - start,
      error: String(e && e.message ? e.message : e),
    };
  } finally {
    clearTimeout(timer);
  }
}

function systemdRestartCount(unit) {
  if (process.platform === "win32") {
    return { active: "skipped", restarts: 0, skipped: true };
  }
  const active = spawnSync("systemctl", ["is-active", unit], { encoding: "utf8" });
  const show = spawnSync("systemctl", ["show", unit, "-p", "NRestarts", "--value"], {
    encoding: "utf8",
  });
  return {
    active: (active.stdout || "").trim(),
    restarts: parseInt((show.stdout || "0").trim(), 10) || 0,
    skipped: false,
  };
}

async function checkPythonHealth() {
  const r = await fetchJson(PYTHON_HEALTH);
  return {
    name: "python_api",
    ok: r.ok && r.body && r.body.status === "ok",
    error: r.ok ? (r.body && r.body.status === "ok" ? null : "health status not ok") : r.error,
    latency_ms: r.latency_ms,
    detail: r.body,
  };
}

function checkPiSystemd() {
  const sd = systemdRestartCount(PI_UNIT);
  if (sd.skipped) {
    return {
      name: "pi_systemd",
      ok: true,
      skipped: true,
      error: null,
      restart_count: 0,
      detail: { unit: PI_UNIT, platform: process.platform },
    };
  }
  return {
    name: "pi_systemd",
    ok: sd.active === "active",
    error: sd.active === "active" ? null : "systemd unit not active: " + sd.active,
    restart_count: sd.restarts,
    detail: { unit: PI_UNIT, active: sd.active },
    alert_id: sd.active === "active" ? null : "ALT-E05",
  };
}

async function checkPiHealth() {
  const r = await fetchJson(PI_HEALTH);
  const body = r.body && r.body.data != null ? r.body.data : r.body;
  const statusOk =
    r.ok &&
    body &&
    (body.status === "ok" || body.status === "healthy" || body.ok === true);
  const serviceOk =
    !body ||
    !body.service ||
    String(body.service).includes("pi") ||
    String(body.service).includes("keibanet");
  const ok = !!(statusOk && serviceOk);
  return {
    name: "pi_health",
    ok,
    error: r.ok ? (ok ? null : "PI health status not ok") : r.error,
    latency_ms: r.latency_ms,
    detail: { url: PI_HEALTH, body },
    alert_id: ok ? null : "ALT-E02",
  };
}

async function checkPiTunnel() {
  if (!PI_TUNNEL_PROBE) {
    return {
      name: "pi_tunnel",
      ok: true,
      skipped: true,
      error: null,
      detail: { reason: "PI_TUNNEL_PROBE_URL unset" },
    };
  }
  const r = await fetchJson(PI_TUNNEL_PROBE);
  return {
    name: "pi_tunnel",
    ok: r.ok,
    error: r.error,
    latency_ms: r.latency_ms,
    detail: { url: PI_TUNNEL_PROBE },
    alert_id: r.ok ? null : "ALT-E02",
  };
}

async function checkTunnelHealth() {
  if (!TUNNEL_HEALTH) {
    const sd = systemdRestartCount("cloudflared-expect-ai");
    if (sd.skipped) {
      return {
        name: "cloudflare_tunnel",
        ok: true,
        skipped: true,
        error: null,
        restart_count: 0,
      };
    }
    return {
      name: "cloudflare_tunnel",
      ok: sd.active === "active",
      error: sd.active === "active" ? null : "systemd unit not active: " + sd.active,
      restart_count: sd.restarts,
      detail: { unit: "cloudflared-expect-ai", active: sd.active },
    };
  }
  const r = await fetchJson(TUNNEL_HEALTH);
  return {
    name: "cloudflare_tunnel",
    ok: r.ok,
    error: r.error,
    latency_ms: r.latency_ms,
    detail: { url: TUNNEL_HEALTH },
  };
}

async function checkPrediction() {
  const base = PYTHON_HEALTH.replace(/\/health\/?$/, "");
  const r = await fetchJson(base + "/v1/predictions");
  return {
    name: "prediction_api",
    ok: r.ok,
    error: r.error,
    latency_ms: r.latency_ms,
  };
}

async function checkConversation() {
  const base = PYTHON_HEALTH.replace(/\/health\/?$/, "");
  const r = await fetchJson(base + "/v1/conversation/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message: "health ping", session_id: "ops-monitor" }),
  });
  return {
    name: "conversation_api",
    ok: r.ok,
    error: r.error,
    latency_ms: r.latency_ms,
  };
}

async function checkEtl() {
  const base = PYTHON_HEALTH.replace(/\/health\/?$/, "");
  const r = await fetchJson(base + "/v1/admin/etl/status");
  const data = r.body && r.body.data != null ? r.body.data : r.body;
  const failed = data && data.status === "failed";
  return {
    name: "etl",
    ok: r.ok && !failed,
    error: !r.ok ? r.error : failed ? data.error_reason || "ETL failed" : null,
    latency_ms: r.latency_ms,
    detail: data,
  };
}

async function checkBffMonitor() {
  if (!BFF_MONITOR) {
    return { name: "bff", ok: true, skipped: true, error: null };
  }
  const headers = { accept: "application/json" };
  if (MONITOR_KEY) headers["x-ops-monitor-key"] = MONITOR_KEY;
  const r = await fetchJson(BFF_MONITOR, { headers });
  const data = r.body && r.body.data != null ? r.body.data : r.body;
  return {
    name: "bff",
    ok: r.ok && data && data.status === "ok",
    error: r.ok ? (data && data.status !== "ok" ? "bff monitor degraded" : null) : r.error,
    latency_ms: r.latency_ms,
    detail: data,
  };
}

function attachSystemdRestarts(check, unit) {
  const sd = systemdRestartCount(unit);
  if (!sd.skipped) {
    check.restart_count = sd.restarts;
    check.detail = { ...(check.detail || {}), systemd_active: sd.active, unit };
  }
  return check;
}

async function emitAlertSlack(incident) {
  if (!incident.alert_id) return;
  if (incident.status === "recovered") {
    await notifySlackRecovery({
      alert_id: incident.alert_id,
      service: incident.service,
      summary: "recovered: " + (incident.error || ""),
      error: incident.error,
      runbook: "docs/ops/v2-operations-runbook.md",
    });
    return;
  }
  if (incident.status !== "down") return;
  const payload = {
    alert_id: incident.alert_id,
    service: incident.service,
    summary: incident.error,
    error: incident.error,
    runbook: "docs/ops/v2-operations-runbook.md",
  };
  const warningIds = { "ALT-E08": true, "ALT-E09": true };
  if (warningIds[incident.alert_id]) {
    await notifySlackWarning(payload);
  } else {
    await notifySlackCritical(payload);
  }
}

async function main() {
  ensureDirs();
  const state = readState();
  const prevStatus = state.last_status || {};

  let python = await checkPythonHealth();
  python = attachSystemdRestarts(python, "expect-ai");

  const piSystemd = checkPiSystemd();
  const piHealth = await checkPiHealth();
  const piTunnel = await checkPiTunnel();

  const checks = [
    python,
    await checkTunnelHealth(),
    piSystemd,
    piHealth,
    piTunnel,
    await checkPrediction(),
    await checkConversation(),
    await checkEtl(),
    await checkBffMonitor(),
  ];

  const active = checks.filter(function (c) {
    return !c.skipped;
  });
  const allOk = active.every(function (c) {
    return c.ok;
  });

  const piChecks = [piSystemd, piHealth, piTunnel];
  const piActive = piChecks.filter((c) => !c.skipped);
  const piOk = piActive.length === 0 ? true : piActive.every((c) => c.ok);

  const report = {
    schema_version: "expect-ops-monitor-report/1.0",
    generated_at: nowIso(),
    runtime: "ec2-monitor",
    status: allOk ? "ok" : "degraded",
    phase: "v2-ops-phase3",
    pi: {
      overall: piOk ? "ok" : "degraded",
      checks: piChecks,
    },
    checks,
  };

  writeFileSync(REPORT_FILE, JSON.stringify(report, null, 2), "utf8");

  metricsFromPiChecks(piChecks, "ec2-monitor").forEach(function (row) {
    appendMetric(PI_METRICS_FILE, row);
  });

  const newStatus = {};
  for (const c of checks) {
    newStatus[c.name] = c.ok ? "ok" : "down";
    const prev = prevStatus[c.name];
    const restarts = c.restart_count || 0;
    const prevRestarts = (state.restart_counts && state.restart_counts[c.name]) || 0;

    if (!c.ok && !c.skipped) {
      const incident = writeIncident({
        service: c.name,
        error: c.error || "unhealthy",
        restart_count: restarts,
        status: "down",
        detail: c.detail || {},
        alert_id: c.alert_id || null,
      });
      await emitAlertSlack(incident);
    } else if (prev === "down" && c.ok) {
      const recovered = writeIncident({
        service: c.name,
        error: "recovered",
        restart_count: restarts,
        status: "recovered",
        detail: c.detail || {},
        alert_id: c.alert_id || null,
      });
      await emitAlertSlack(recovered);
    }

    if (restarts > prevRestarts) {
      writeIncident({
        service: c.name,
        error: "service restarted (NRestarts increased)",
        restart_count: restarts,
        status: "degraded",
        detail: { previous: prevRestarts, current: restarts },
      });
    }

    state.restart_counts = state.restart_counts || {};
    state.restart_counts[c.name] = restarts;
  }

  state.last_status = newStatus;
  state.last_run = nowIso();
  writeState(state);

  console.log(JSON.stringify(report));
  process.exit(allOk ? 0 : 1);
}

main().catch(function (e) {
  writeIncident({
    service: "ec2_monitor",
    error: String(e && e.message ? e.message : e),
    restart_count: 0,
    status: "down",
  });
  console.error(e);
  process.exit(2);
});
