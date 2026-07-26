/**
 * GET /api/ops/portal — Version8.7 Operations Dashboard（閲覧専用）
 *
 * - 実効 role=ADMIN（resolveAuthorization / admin_user_ids）のみ
 * - 値は実データ優先。未生成は "No Data" / "Pending"（固定マーケ文言禁止）
 * - PE / CE / AI / ResultAutomation / Research ロジック非変更
 */
import { requireAccessSession } from "../../_lib/auth.js";
import { resolveAuthorization } from "../../_lib/authorization.js";
import { getBetaConfig } from "../../_lib/betaConfig.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { resolveOpsModeDetailed } from "../../_lib/opsMode.js";
import { isOpsPortalAdmin } from "../../_lib/opsPortalAccess.js";
import { Role } from "../../_lib/roles.js";
import { UserRepository } from "../../_lib/userRepository.js";

const NO_DATA = "No Data";
const PENDING = "Pending";

async function fetchAssetJson(context, path) {
  try {
    if (context.env && context.env.ASSETS && typeof context.env.ASSETS.fetch === "function") {
      const u = new URL(path, context.request.url);
      const res = await context.env.ASSETS.fetch(u);
      if (res && res.ok) return await res.json();
    }
  } catch {
    /* fall through */
  }
  try {
    const u = new URL(path, context.request.url);
    const res = await fetch(u.toString(), { cf: { cacheTtl: 0 } });
    if (res.ok) return await res.json();
  } catch {
    /* empty */
  }
  return null;
}

async function fetchJsonPath(context, path) {
  try {
    const u = new URL(path, context.request.url);
    const headers = {};
    const auth = context.request.headers.get("authorization");
    if (auth) headers.Authorization = auth;
    const res = await fetch(u.toString(), {
      headers,
      cf: { cacheTtl: 0 },
    });
    if (!res.ok) return null;
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (ct.indexOf("application/json") < 0) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function present(v) {
  if (v == null) return false;
  if (typeof v === "string" && !String(v).trim()) return false;
  return true;
}

function card(label, value, tone, note, source) {
  let display = value;
  let t = tone || "muted";
  if (!present(display)) {
    display = NO_DATA;
    t = "muted";
  }
  return {
    label,
    value: display,
    tone: t,
    note: note || null,
    source: source || null,
  };
}

function pick(obj, keys) {
  if (!obj || typeof obj !== "object") return null;
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    if (obj[k] != null && obj[k] !== "") return obj[k];
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

  const authz = await resolveAuthorization(context, beta);
  const profile = await UserRepository.get(context, session.id).catch(function () {
    return null;
  });
  const effectiveProfile = {
    ...(profile || {}),
    role: (profile && profile.role) || authz.role,
  };

  const allow =
    authz.role === Role.ADMIN || isOpsPortalAdmin(beta, session, effectiveProfile);
  if (!allow) {
    return jsonError("FORBIDDEN", "ops portal requires role=ADMIN", 403);
  }

  const resolved = await resolveOpsModeDetailed(beta, { now: new Date() });
  const maintenance =
    resolved.ops_mode === "CLOSED" || resolved.maintenance === true;

  const [scheduler, portalSnap, healthBody, publicStatusBody] = await Promise.all([
    fetchAssetJson(context, "/ops-data/research-scheduler.json"),
    fetchAssetJson(context, "/ops-data/portal-snapshot.json"),
    fetchJsonPath(context, "/api/health"),
    fetchJsonPath(context, "/api/ops/public-status"),
  ]);

  const display = (scheduler && scheduler.display) || {};
  const snap =
    portalSnap && typeof portalSnap === "object" && !Array.isArray(portalSnap)
      ? portalSnap
      : {};
  const health = (healthBody && (healthBody.data || healthBody)) || null;
  const pub =
    (publicStatusBody && (publicStatusBody.data || publicStatusBody)) || null;

  const hasScheduler =
    !!(scheduler && Object.keys(scheduler).length > 0) ||
    !!(display && Object.keys(display).length > 0);

  const pagesVal = "OK"; // portal 自身が応答している＝Pages 到達可
  const ec2Val = pick(health, ["ec2", "host", "instance"]) || pick(snap.system || {}, ["ec2"]);
  const piVal = pick(health, ["pi", "pi_status", "pi_ok"]);
  const aiVal = pick(health, ["ai", "ai_status", "ai_ok"]);

  const data = {
    schema_version: "expect-v87-ops-portal/1.1",
    read_only: true,
    production_write: false,
    production_auto_apply: false,
    baseline_lock: (scheduler && scheduler.baseline_lock) || snap.baseline_lock || null,
    portal_version: "8.7",
    generated_at: new Date().toISOString(),
    authz_role: authz.role,
    authz_source: authz.source,
    empty_policy: { no_data: NO_DATA, pending: PENDING },
    sections: {
      system: {
        title: "System",
        cards: [
          card("Pages", pagesVal, "ok", null, "portal"),
          card("EC2", ec2Val == null ? NO_DATA : String(ec2Val), ec2Val == null ? "muted" : "ok", null, "health|snapshot"),
          card(
            "PI",
            piVal == null ? NO_DATA : piVal === true ? "OK" : String(piVal),
            piVal == null ? "muted" : "ok",
            null,
            "health"
          ),
          card(
            "AI",
            aiVal == null ? NO_DATA : aiVal === true ? "OK" : String(aiVal),
            aiVal == null ? "muted" : "ok",
            null,
            "health"
          ),
          card(
            "ResultAutomation",
            PENDING,
            "muted",
            "クライアントが GET /api/ops/result-automation で上書き",
            "client-live"
          ),
          card(
            "Research Scheduler",
            hasScheduler
              ? display.current_phase ||
                  scheduler.current_phase ||
                  PENDING
              : NO_DATA,
            hasScheduler ? "ok" : "muted",
            "GET /api/ops/research-scheduler",
            "scheduler"
          ),
        ],
      },
      production: {
        title: "Production",
        cards: [
          card("Prediction", PENDING, "muted", "v71-metrics で上書き可", "client-live"),
          card("Board", PENDING, "muted", "v71-metrics で上書き可", "client-live"),
          card("History", PENDING, "muted", "v71-metrics で上書き可", "client-live"),
          card("Challenge", PENDING, "muted", "v71-metrics で上書き可", "client-live"),
          card("Archive", PENDING, "muted", "v71-metrics で上書き可", "client-live"),
          card("Realtime", PENDING, "muted", "v71-metrics で上書き可", "client-live"),
          card(
            "Maintenance",
            maintenance ? "CLOSED" : "PUBLIC",
            maintenance ? "warn" : "ok",
            resolved.schedule_reason || (pub && pub.reason) || null,
            "ops-mode"
          ),
        ],
        note: "閲覧専用 — Production 書き換えなし",
      },
      research: {
        title: "Research",
        cards: [
          card(
            "Current Week",
            hasScheduler ? scheduler.week_id || display.week_id || NO_DATA : NO_DATA,
            hasScheduler && (scheduler.week_id || display.week_id) ? "ok" : "muted",
            null,
            "scheduler"
          ),
          card(
            "Current Phase",
            hasScheduler
              ? display.current_phase || scheduler.current_phase || NO_DATA
              : NO_DATA,
            hasScheduler && (display.current_phase || scheduler.current_phase)
              ? "ok"
              : "muted",
            null,
            "scheduler"
          ),
          card(
            "Next Run",
            hasScheduler
              ? display.next_run || scheduler.next_run_jst || PENDING
              : NO_DATA,
            hasScheduler ? "ok" : "muted",
            null,
            "scheduler"
          ),
          card(
            "Recovery",
            hasScheduler
              ? display.recovery || scheduler.recovery_active
                ? "active"
                : "idle"
              : NO_DATA,
            hasScheduler ? "ok" : "muted",
            null,
            "scheduler"
          ),
          card(
            "Decision",
            pick(snap.research || {}, ["decision"]) || NO_DATA,
            "muted",
            null,
            "snapshot"
          ),
        ],
      },
      knowledge: {
        title: "Knowledge",
        cards: [
          card("Knowledge Score", pick(snap.knowledge || {}, ["knowledge_score"]) || NO_DATA, "muted", null, "snapshot"),
          card("Accepted Patterns", pick(snap.knowledge || {}, ["accepted_patterns"]) || NO_DATA, "muted", null, "snapshot"),
          card("Rejected Patterns", pick(snap.knowledge || {}, ["rejected_patterns"]) || NO_DATA, "muted", null, "snapshot"),
          card("Governance", pick(snap.knowledge || {}, ["governance"]) || NO_DATA, "muted", null, "snapshot"),
        ],
      },
      deploy: {
        title: "Deploy",
        cards: [
          card("Deploy Queue", pick(snap.deploy || {}, ["deploy_queue"]) || NO_DATA, "muted", null, "snapshot"),
          card("Accept済み候補", pick(snap.deploy || {}, ["accepted_candidates"]) || NO_DATA, "muted", null, "snapshot"),
          card(
            "deploy-note",
            (scheduler && scheduler.deploy_policy) ||
              pick(snap.deploy || {}, ["deploy_note"]) ||
              NO_DATA,
            scheduler && scheduler.deploy_policy ? "ok" : "muted",
            "Production 自動適用は禁止",
            "scheduler|snapshot"
          ),
        ],
        note: "Accept 済みでも Production へ自動適用しない",
      },
      reports: {
        title: "Reports",
        cards: [
          card("Weekly Report", pick(snap.reports || {}, ["weekly_report"]) || PENDING, "muted", null, "snapshot"),
          card(
            "Baseline Health Check",
            pick(snap.reports || {}, ["baseline_health_check"]) || PENDING,
            "muted",
            null,
            "snapshot"
          ),
          card("Boundary Audit", pick(snap.reports || {}, ["boundary_audit"]) || PENDING, "muted", null, "snapshot"),
          card("Incident Report", pick(snap.reports || {}, ["incident_report"]) || NO_DATA, "muted", null, "snapshot"),
        ],
      },
    },
  };

  return jsonOk(data, { service: "OpsPortal", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
