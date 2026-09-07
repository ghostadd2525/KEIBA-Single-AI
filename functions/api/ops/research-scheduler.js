/**
 * GET /api/ops/research-scheduler — V8.6 / V8.8.1
 *
 * Reads public/ops-data/research-scheduler.json (Publish Layer / v8:runner).
 * Fixed schedule labels are forbidden — missing values stay null (UI → No Data).
 * PE / CE / AI untouched.
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

function present(v) {
  if (v == null) return null;
  if (typeof v === "string" && !String(v).trim()) return null;
  const s = String(v).trim();
  if (/^(—|-|毎日\s*03:00\s*JST|03:00 JST daily)$/i.test(s)) return null;
  return v;
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
  const empty = !snap || Object.keys(snap).length === 0;

  const data = {
    schema_version: "expect-v881-research-scheduler-api/1.0",
    available: !empty && snap.available !== false,
    current_phase: present(display.current_phase) || present(snap && snap.current_phase),
    next_run: present(display.next_run) || present(snap && snap.next_run) || present(snap && snap.next_run_jst),
    last_run: present(display.last_run) || present(snap && snap.last_run_at),
    duration_ms: display.duration_ms ?? snap?.duration_ms ?? null,
    success: display.success ?? snap?.success_count ?? null,
    failure: display.failure ?? snap?.failure_count ?? null,
    skip_reason: present(display.skip_reason) || present(snap && snap.last_skip_reason),
    recovery:
      typeof display.recovery === "boolean"
        ? display.recovery
        : typeof (snap && snap.recovery_active) === "boolean"
          ? snap.recovery_active
          : null,
    week_id: present(snap && snap.week_id),
    baseline_lock: present(snap && snap.baseline_lock),
    production_auto_apply: false,
    deploy_policy: null,
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
