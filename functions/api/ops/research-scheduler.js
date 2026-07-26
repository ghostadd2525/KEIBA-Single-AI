/**
 * GET /api/ops/research-scheduler — V8.6 Research Scheduler card (admin)
 *
 * Reads public/ops-data/research-scheduler.json (written by v8:runner).
 * PE / CE / AI untouched. Version8.5.1: fail-closed admin.
 */
import { requireAccessSession } from "../../_lib/auth.js";
import { isAdminUser } from "../../_lib/adminAuth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { UserRepository } from "../../_lib/userRepository.js";

async function loadSnapshot(context) {
  try {
    if (context.env && context.env.ASSETS && typeof context.env.ASSETS.fetch === "function") {
      const u = new URL("/ops-data/research-scheduler.json", context.request.url);
      const res = await context.env.ASSETS.fetch(u);
      if (res && res.ok) return await res.json();
    }
  } catch {
    /* fall through */
  }
  try {
    const u = new URL("/ops-data/research-scheduler.json", context.request.url);
    const res = await fetch(u.toString(), { cf: { cacheTtl: 0 } });
    if (res.ok) return await res.json();
  } catch {
    /* empty */
  }
  return null;
}

export async function onRequestGet(context) {
  const session = requireAccessSession(context);
  if (session instanceof Response) return session;

  let beta = {};
  try {
    beta = await getBetaConfig(context);
  } catch {
    beta = {};
  }

  await resolveAuthorization(context, beta);

  const profile = await UserRepository.get(context, session.id).catch(function () {
    return null;
  });
  if (!isAdminUser(beta, session, profile)) {
    return jsonError("FORBIDDEN", "research scheduler requires admin", 403);
  }

  const snap = await loadSnapshot(context);
  const display = (snap && snap.display) || {};
  const data = {
    schema_version: "expect-v86-research-scheduler-api/1.0",
    available: !!snap,
    current_phase: display.current_phase || (snap && snap.current_phase) || "—",
    next_run: display.next_run || (snap && snap.next_run_jst) || "毎日 03:00 JST",
    last_run: display.last_run || (snap && snap.last_run_at) || null,
    duration_ms: display.duration_ms ?? null,
    success: display.success ?? (snap && snap.success_count) ?? 0,
    failure: display.failure ?? (snap && snap.failure_count) ?? 0,
    skip_reason: display.skip_reason || (snap && snap.last_skip_reason) || null,
    recovery: display.recovery ?? (snap && snap.recovery_active) ?? false,
    week_id: (snap && snap.week_id) || null,
    baseline_lock: (snap && snap.baseline_lock) || "Version8.5",
    production_auto_apply: false,
    deploy_policy: (snap && snap.deploy_policy) || "deploy_note_only",
    health: (snap && snap.health) || null,
    phases: (snap && snap.phases) || null,
    last_tick: (snap && snap.last_tick) || null,
    raw: snap,
  };

  return jsonOk(data, { service: "ResearchScheduler", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
