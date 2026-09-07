/**
 * GET /api/ops/monitor-live — Live Monitor for Operations Console
 * Distinguishes Healthy / Pending / Failed / No Data (no fixed marketing labels).
 */
import { jsonOk } from "../../_lib/errors.js";
import {
  requireOpsAdmin,
  fetchOpsAsset,
  fetchJsonApi,
} from "../../_lib/opsConsole.js";

function classify(probe) {
  if (probe == null) return { status: "No Data", health: null, latency_ms: null };
  if (probe.skipped) return { status: "Pending", health: "skipped", latency_ms: probe.latency_ms ?? null };
  if (probe.ok === true || probe.status === "ok" || probe.status === "healthy") {
    return {
      status: "Healthy",
      health: probe.status || "ok",
      latency_ms: probe.latency_ms ?? null,
    };
  }
  if (probe.ok === false || probe.status === "unhealthy" || probe.status === "unreachable" || probe.status === "degraded") {
    return {
      status: probe.status === "degraded" ? "Failed" : "Failed",
      health: probe.status || "failed",
      latency_ms: probe.latency_ms ?? null,
    };
  }
  if (probe.status === "pending" || probe.status === "Pending") {
    return { status: "Pending", health: "pending", latency_ms: probe.latency_ms ?? null };
  }
  return {
    status: probe.status ? String(probe.status) : "No Data",
    health: probe.status || null,
    latency_ms: probe.latency_ms ?? null,
  };
}

export async function onRequestGet(context) {
  const gate = await requireOpsAdmin(context);
  if (gate.error) return gate.error;

  const [healthRes, scheduler, portalSnap, raRes] = await Promise.all([
    fetchJsonApi(context, "/api/health"),
    fetchOpsAsset(context, "/ops-data/research-scheduler.json"),
    fetchOpsAsset(context, "/ops-data/portal-snapshot.json"),
    fetchJsonApi(context, "/api/ops/result-automation"),
  ]);

  const health = healthRes.ok ? healthRes.data : null;
  const checkedAt = new Date().toISOString();

  const pages = health
    ? {
        status: health.status === "ok" ? "Healthy" : health.status === "degraded" ? "Failed" : String(health.status || "No Data"),
        health: health.status || null,
        latency_ms: null,
        last_update: checkedAt,
        detail: {
          runtime: health.runtime || null,
          expect_env: health.expect_env || null,
        },
      }
    : { status: "No Data", health: null, latency_ms: null, last_update: null, detail: null };

  const piRaw = health && health.pi;
  const piC = classify(piRaw);
  const pi = {
    ...piC,
    last_update: checkedAt,
    detail: piRaw
      ? {
          configured: piRaw.configured,
          status: piRaw.status,
          latency_ms: piRaw.latency_ms,
        }
      : null,
  };

  const aiRaw =
    health && typeof health.ai_proxy_configured === "boolean"
      ? {
          ok: health.ai_proxy_configured === true,
          status: health.ai_proxy_configured ? "ok" : "unconfigured",
          configured: health.ai_proxy_configured,
        }
      : null;
  const aiC = classify(aiRaw);
  const ai = {
    ...aiC,
    last_update: checkedAt,
    detail: aiRaw,
  };

  const ec2 = {
    status: "No Data",
    health: null,
    latency_ms: null,
    last_update: null,
    detail: null,
  };

  let ra = { status: "No Data", health: null, latency_ms: null, last_update: null, detail: null };
  if (raRes.ok && raRes.data) {
    const run = raRes.data.run || {};
    const st = run.status || raRes.data.status || null;
    if (!st) {
      ra.status = "No Data";
    } else if (String(st).toUpperCase() === "FAILED" || raRes.data.ok === false) {
      ra.status = "Failed";
      ra.health = String(st);
    } else if (/pending/i.test(String(st))) {
      ra.status = "Pending";
      ra.health = String(st);
    } else {
      ra.status = "Healthy";
      ra.health = String(st);
    }
    ra.last_update = raRes.data.checked_at || run.finished_at || run.started_at || checkedAt;
    ra.detail = {
      run_id: run.run_id || null,
      race_date: raRes.data.race_date || null,
      status: st,
    };
  } else if (health && health.result_automation) {
    const c = classify(health.result_automation);
    ra = {
      ...c,
      last_update: checkedAt,
      detail: health.result_automation,
    };
  }

  let sched = {
    status: "No Data",
    health: null,
    latency_ms: null,
    last_update: null,
    detail: null,
  };
  if (scheduler && scheduler.available !== false && (scheduler.week_id || scheduler.published_at)) {
    const phase = scheduler.current_phase;
    sched = {
      status: phase ? "Healthy" : scheduler.last_run_at ? "Healthy" : "Pending",
      health: phase || scheduler.recovery || "idle",
      latency_ms: null,
      last_update: scheduler.published_at || scheduler.last_run_at || null,
      detail: {
        week_id: scheduler.week_id || null,
        current_phase: phase || null,
        next_run: scheduler.next_run || null,
        last_run: scheduler.last_run_at || null,
      },
    };
  }

  const data = {
    schema_version: "expect-v89-monitor-live/1.0",
    checked_at: checkedAt,
    production_auto_apply: false,
    targets: {
      Pages: pages,
      PI: pi,
      AI: ai,
      EC2: ec2,
      ResultAutomation: ra,
      ResearchScheduler: sched,
    },
    portal_published_at: (portalSnap && portalSnap.published_at) || null,
  };

  return jsonOk(data, { service: "OpsMonitorLive", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
