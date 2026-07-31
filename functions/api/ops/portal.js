/**
 * GET /api/ops/portal — Version8.8.1 Operations Dashboard（閲覧専用）
 *
 * - 実効 role=ADMIN のみ
 * - 表示値は実データ / "No Data" / "Pending" のみ（固定マーケ文言禁止）
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

/** Reject known stub / marketing labels — never surface as “real”. */
const STUB_RE =
  /^(—|-|live|read-only|proxy|empty|pending publish|pipeline status|毎日\s*03:00\s*JST|03:00 JST daily|Cloudflare Pages|AI\s*\/\s*PI|AI\/PI host|deploy_note_only)$/i;

async function fetchAssetJson(context, path) {
  try {
    if (context.env && context.env.ASSETS && typeof context.env.ASSETS.fetch === "function") {
      const u = new URL(path, context.request.url);
      const res = await context.env.ASSETS.fetch(u);
      if (res && res.ok) {
        const ct = (res.headers.get("content-type") || "").toLowerCase();
        if (ct.indexOf("json") < 0 && ct.indexOf("text/html") >= 0) return null;
        return await res.json();
      }
    }
  } catch {
    /* fall through */
  }
  try {
    const u = new URL(path, context.request.url);
    const res = await fetch(u.toString(), { cf: { cacheTtl: 0 } });
    if (!res.ok) return null;
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    if (ct.indexOf("json") < 0) return null;
    return await res.json();
  } catch {
    return null;
  }
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
  if (typeof v === "string") {
    const s = v.trim();
    if (!s || STUB_RE.test(s)) return false;
    return true;
  }
  if (typeof v === "object") return false;
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

function cardPending(label, note, source) {
  return {
    label,
    value: PENDING,
    tone: "muted",
    note: note || null,
    source: source || null,
  };
}

function pickScalar(obj, keys) {
  if (!obj || typeof obj !== "object") return null;
  for (let i = 0; i < keys.length; i++) {
    const v = obj[keys[i]];
    if (v == null || v === "") continue;
    if (typeof v === "object") continue;
    if (typeof v === "string" && STUB_RE.test(v.trim())) continue;
    return v;
  }
  return null;
}

/**
 * Format probe objects (e.g. health.pi) without String(object).
 * Uses status / latency_ms / configured / ok only.
 */
function formatProbe(obj) {
  if (obj == null) return null;
  if (typeof obj !== "object" || Array.isArray(obj)) {
    if (typeof obj === "boolean") return obj ? "true" : "false";
    if (typeof obj === "number" || typeof obj === "string") {
      const s = String(obj).trim();
      return s && !STUB_RE.test(s) ? s : null;
    }
    return null;
  }
  const parts = [];
  if (obj.status != null && String(obj.status).trim()) {
    parts.push("status=" + String(obj.status).trim());
  }
  if (obj.latency_ms != null && obj.latency_ms !== "") {
    parts.push("latency=" + String(obj.latency_ms) + "ms");
  }
  if (typeof obj.configured === "boolean") {
    parts.push("configured=" + String(obj.configured));
  }
  if (typeof obj.ok === "boolean" && obj.status == null) {
    parts.push("ok=" + String(obj.ok));
  }
  if (obj.service != null && String(obj.service).trim()) {
    parts.push("service=" + String(obj.service).trim());
  }
  return parts.length ? parts.join(" · ") : null;
}

function formatHealthPages(health) {
  if (!health || typeof health !== "object") return null;
  const parts = [];
  if (health.status != null && String(health.status).trim()) {
    parts.push("status=" + String(health.status).trim());
  }
  if (health.runtime != null && String(health.runtime).trim()) {
    parts.push("runtime=" + String(health.runtime).trim());
  }
  if (health.expect_env != null && String(health.expect_env).trim()) {
    parts.push("env=" + String(health.expect_env).trim());
  }
  return parts.length ? parts.join(" · ") : null;
}

function formatAiProbe(health) {
  if (!health || typeof health !== "object") return null;
  // Prefer nested ai object if present; else ai_proxy_configured + result_automation summary
  if (health.ai && typeof health.ai === "object") {
    return formatProbe(health.ai);
  }
  const parts = [];
  if (typeof health.ai_proxy_configured === "boolean") {
    parts.push("proxy=" + String(health.ai_proxy_configured));
  }
  const ra = health.result_automation;
  if (ra && typeof ra === "object") {
    if (ra.status != null) parts.push("ra_status=" + String(ra.status));
    else if (typeof ra.ok === "boolean") parts.push("ra_ok=" + String(ra.ok));
  }
  return parts.length ? parts.join(" · ") : null;
}

function recoveryDisplay(research, scheduler, display) {
  if (research && research.recovery != null && research.recovery !== "") {
    const r = research.recovery;
    if (typeof r === "boolean") return r ? "active" : "idle";
    if (typeof r === "string" && !STUB_RE.test(r.trim())) return r.trim();
  }
  if (scheduler && typeof scheduler.recovery_active === "boolean") {
    return scheduler.recovery_active ? "active" : "idle";
  }
  if (scheduler && typeof scheduler.recovery === "string" && scheduler.recovery.trim()) {
    return scheduler.recovery.trim();
  }
  if (scheduler && typeof scheduler.recovery === "boolean") {
    return scheduler.recovery ? "active" : "idle";
  }
  if (display && typeof display.recovery === "boolean") {
    return display.recovery ? "active" : "idle";
  }
  return null;
}

function reportCard(label, value, emptyMode) {
  if (value == null || value === "") {
    return emptyMode === "pending"
      ? cardPending(label, null, "publish")
      : card(label, null, "muted", null, "publish");
  }
  if (typeof value === "string" && /^pending$/i.test(value.trim())) {
    return cardPending(label, null, "publish");
  }
  return card(label, String(value), "ok", null, "publish");
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

  const [scheduler, portalSnap, approvalSnap, healthBody, publicStatusBody] =
    await Promise.all([
      fetchAssetJson(context, "/ops-data/research-scheduler.json"),
      fetchAssetJson(context, "/ops-data/portal-snapshot.json"),
      fetchAssetJson(context, "/ops-data/approval-queue.json").then(function (a) {
        return a || fetchAssetJson(context, "/ops-data/approvals.json");
      }),
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

  const research = snap.research || {};
  const knowledge = snap.knowledge || {};
  const deploySnap = snap.deploy || {};
  const reportsSnap = snap.reports || {};
  const approval =
    snap.approval ||
    (approvalSnap
      ? {
          pending: approvalSnap.pending_count ?? approvalSnap.pending ?? null,
          approved: approvalSnap.approved_count ?? approvalSnap.approved ?? null,
          rejected: approvalSnap.rejected_count ?? approvalSnap.rejected ?? null,
          timeout: approvalSnap.timeout_count ?? approvalSnap.timeout ?? null,
        }
      : {});

  const weekId =
    research.week_id || (scheduler && scheduler.week_id) || display.week_id || null;
  const phase =
    research.current_phase ||
    (scheduler && scheduler.current_phase) ||
    display.current_phase ||
    null;
  const nextRun =
    research.next_run ||
    (scheduler && scheduler.next_run) ||
    display.next_run ||
    null;
  const lastRun =
    research.last_run ||
    (scheduler && scheduler.last_run_at) ||
    display.last_run ||
    null;
  const recoveryVal = recoveryDisplay(research, scheduler, display);

  const pagesVal = formatHealthPages(health);
  const ec2Val =
    pickScalar(health, ["ec2", "host", "instance"]) ||
    pickScalar(snap.system || {}, ["ec2"]);
  const piVal = formatProbe(health && health.pi) || pickScalar(health, ["pi_status", "pi_ok"]);
  const aiVal = formatAiProbe(health) || pickScalar(health, ["ai_status", "ai_ok"]);

  const maintenanceVal =
    resolved.ops_mode === "CLOSED" || resolved.ops_mode === "PUBLIC"
      ? resolved.ops_mode
      : null;

  const data = {
    schema_version: "expect-v881-ops-portal/1.0",
    read_only: true,
    production_write: false,
    production_auto_apply: false,
    baseline_lock:
      snap.baseline_lock || (scheduler && scheduler.baseline_lock) || null,
    portal_version: "8.8.1",
    generated_at: new Date().toISOString(),
    authz_role: authz.role,
    authz_source: authz.source,
    empty_policy: { no_data: NO_DATA, pending: PENDING },
    sections: {
      system: {
        title: "System",
        cards: [
          card("Pages", pagesVal, pagesVal ? "ok" : "muted", null, "health"),
          card("EC2", ec2Val == null ? null : String(ec2Val), ec2Val == null ? "muted" : "ok", null, "health|snapshot"),
          card("PI", piVal, piVal ? "ok" : "muted", null, "health"),
          card("AI", aiVal, aiVal ? "ok" : "muted", null, "health"),
          card(
            "ResultAutomation",
            null,
            "muted",
            "client: GET /api/ops/result-automation",
            "client-live"
          ),
          card(
            "Research Scheduler",
            phase,
            phase ? "ok" : "muted",
            "portal-snapshot / research-scheduler.json",
            "publish"
          ),
        ],
      },
      production: {
        title: "Production",
        cards: [
          card("Prediction", null, "muted", "client: /api/ops/v71-metrics", "client-live"),
          card("Board", null, "muted", "client: /api/ops/v71-metrics", "client-live"),
          card("History", null, "muted", "client: /api/ops/v71-metrics", "client-live"),
          card("Challenge", null, "muted", "client: /api/ops/v71-metrics", "client-live"),
          card("Archive", null, "muted", "client: /api/ops/v71-metrics", "client-live"),
          card("Realtime", null, "muted", "client: /api/ops/v71-metrics", "client-live"),
          card(
            "Maintenance",
            maintenanceVal,
            maintenance ? "warn" : maintenanceVal ? "ok" : "muted",
            resolved.schedule_reason || (pub && pub.reason) || null,
            "ops-mode"
          ),
        ],
        note: "閲覧専用 — Production 書き換えなし",
      },
      research: {
        title: "Research",
        cards: [
          card("Current Week", weekId, weekId ? "ok" : "muted", null, "publish"),
          card("Current Phase", phase, phase ? "ok" : "muted", null, "publish"),
          card(
            "Next Run",
            nextRun,
            nextRun ? "ok" : "muted",
            lastRun ? "last=" + lastRun : null,
            "publish"
          ),
          card("Recovery", recoveryVal, recoveryVal ? "ok" : "muted", null, "publish"),
          card(
            "Decision",
            pickScalar(research, ["decision"]),
            pickScalar(research, ["decision"]) ? "ok" : "muted",
            null,
            "publish"
          ),
        ],
      },
      knowledge: {
        title: "Knowledge",
        cards: [
          card(
            "Knowledge Score",
            knowledge.knowledge_score != null ? String(knowledge.knowledge_score) : null,
            knowledge.knowledge_score != null ? "ok" : "muted",
            null,
            "publish"
          ),
          card(
            "Accepted Patterns",
            knowledge.accepted_patterns != null ? String(knowledge.accepted_patterns) : null,
            knowledge.accepted_patterns != null ? "ok" : "muted",
            null,
            "publish"
          ),
          card(
            "Rejected Patterns",
            knowledge.rejected_patterns != null ? String(knowledge.rejected_patterns) : null,
            knowledge.rejected_patterns != null ? "ok" : "muted",
            null,
            "publish"
          ),
          card(
            "Governance",
            knowledge.governance || null,
            knowledge.governance ? "ok" : "muted",
            null,
            "publish"
          ),
        ],
      },
      deploy: {
        title: "Deploy",
        cards: [
          card(
            "Deploy Queue",
            deploySnap.deploy_queue || null,
            deploySnap.deploy_queue ? "ok" : "muted",
            null,
            "publish"
          ),
          card(
            "Accept済み候補",
            deploySnap.accepted_candidates || null,
            deploySnap.accepted_candidates ? "ok" : "muted",
            null,
            "publish"
          ),
          card(
            "deploy-note",
            deploySnap.deploy_note || null,
            deploySnap.deploy_note ? "ok" : "muted",
            "Production 自動適用は禁止",
            "publish"
          ),
        ],
        note: "Accept 済みでも Production へ自動適用しない",
      },
      approval: {
        title: "Approval",
        cards: [
          card(
            "Pending",
            approval.pending != null ? String(approval.pending) : null,
            approval.pending != null ? "ok" : "muted",
            null,
            "publish|queue"
          ),
          card(
            "Approved",
            approval.approved != null ? String(approval.approved) : null,
            approval.approved != null ? "ok" : "muted",
            null,
            "publish|queue"
          ),
          card(
            "Rejected",
            approval.rejected != null ? String(approval.rejected) : null,
            approval.rejected != null ? "ok" : "muted",
            null,
            "publish|queue"
          ),
          card(
            "Timeout",
            approval.timeout != null ? String(approval.timeout) : null,
            approval.timeout != null ? "ok" : "muted",
            null,
            "publish|queue"
          ),
        ],
        note: "Accept → RC → Deploy Note → Human Deploy",
      },
      reports: {
        title: "Reports",
        cards: [
          reportCard("Weekly Report", reportsSnap.weekly_report, "no_data"),
          reportCard(
            "Baseline Health Check",
            reportsSnap.baseline_health_check,
            reportsSnap.weekly_report ? "pending" : "no_data"
          ),
          reportCard(
            "Boundary Audit",
            reportsSnap.boundary_audit,
            reportsSnap.weekly_report ? "pending" : "no_data"
          ),
          reportCard("Incident Report", reportsSnap.incident_report, "no_data"),
        ],
      },
    },
  };

  return jsonOk(data, { service: "OpsPortal", cache: "no-store" }, {
    status: 200,
    cacheControl: "no-store",
  });
}
