#!/usr/bin/env node
/**
 * Version8.8 — Approval Queue (Human gate before Deploy Note).
 *
 * Enqueue ONLY when:
 *   decision == "accept"
 *   AND promote_to_production == true
 *   AND Validation == PASS
 *   AND Canary == PASS
 *   AND 285R == PASS
 *
 * Approve → deploy-note only (production_auto_apply: false). Human Deploy next.
 * Timeout (expires_at): status=rejected, reason=approval_timeout, auto=true → Knowledge.
 *
 * PE / CE / AI / ResultAutomation untouched.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { repoRoot, weekIdJst } from "./calendar.mjs";
import { BASELINE_LOCK } from "./ops-baseline.mjs";
import { appendApprovalRejectedPattern } from "./knowledge-base.mjs";

const REPO = repoRoot();
const TTL_MS = 7 * 24 * 60 * 60 * 1000;
const SCHEMA = "expect-v88-approval/1.0";

function arg(name, fallback = "") {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function readJson(path, fallback = null) {
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function writeJson(path, obj) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(obj, null, 2) + "\n", "utf8");
}

export function approvalsDirs(repo = REPO) {
  const root = join(repo, "development", "approvals");
  return {
    root,
    queue: join(root, "queue"),
    index: join(root, "index.json"),
    publicSnapshot: join(repo, "public", "ops-data", "approvals.json"),
  };
}

function ensureDirs(dirs = approvalsDirs()) {
  mkdirSync(dirs.queue, { recursive: true });
  mkdirSync(join(REPO, "public", "ops-data"), { recursive: true });
  return dirs;
}

/** Validation PASS: at least one gate=pass and zero gate=fail (or summary.pass>0 && fail==0). */
export function isValidationPass(weekRoot, repo = REPO) {
  const doc =
    readJson(join(weekRoot, "tue-proposal", "proposal-validation.json")) ||
    readJson(join(repo, "development", "analysis", "proposal-validation.json"));
  if (!doc) return false;
  const validations = Array.isArray(doc.validations) ? doc.validations : [];
  if (doc.summary) {
    const pass = Number(doc.summary.pass || 0);
    const fail = Number(doc.summary.fail || 0);
    if (pass > 0 && fail === 0) return true;
  }
  if (!validations.length) return false;
  const passN = validations.filter((v) => v.gate === "pass").length;
  const failN = validations.filter((v) => v.gate === "fail").length;
  return passN > 0 && failN === 0;
}

/** Canary PASS: evaluated results include PASS/PASS_WITH_WARNING and no FAIL. */
export function isCanaryPass(weekRoot, repo = REPO) {
  const doc =
    readJson(join(weekRoot, "wed-canary", "ranked-run.json")) ||
    readJson(join(repo, "development", "runs", "latest-canary-ranked.json"));
  if (!doc) return false;
  const results = Array.isArray(doc.results) ? doc.results : [];
  const evaluated = results.filter(
    (r) =>
      r &&
      (r.status === "evaluated" ||
        r.verdict === "PASS" ||
        r.verdict === "PASS_WITH_WARNING" ||
        r.verdict === "FAIL")
  );
  if (!evaluated.length) return false;
  const anyPass = evaluated.some(
    (r) => r.verdict === "PASS" || r.verdict === "PASS_WITH_WARNING"
  );
  const anyFail = evaluated.some((r) => r.verdict === "FAIL");
  return anyPass && !anyFail;
}

/**
 * 285R PASS: positive/improvement verdict, or measured_delta_hit_at_1 > 0.
 * Explicit PASS/pass/improvement accepted. regression / no_measured_delta = not PASS.
 */
export function is285RPass(weekRoot) {
  const doc = readJson(join(weekRoot, "thu-baseline", "report.json"));
  if (!doc || !doc.comparison) return false;
  const v = String(doc.comparison.verdict || "").toLowerCase();
  if (v === "pass" || v === "improvement" || v === "improved") return true;
  if (v === "regression" || v === "no_measured_delta" || v === "fail") return false;
  const delta = doc.comparison.measured_delta_hit_at_1;
  if (typeof delta === "number" && delta > 0) return true;
  if (doc.comparison.pass === true || doc.comparison.ok === true && v === "ok") return true;
  return false;
}

export function evaluateEnqueueGates(decision, weekRoot, repo = REPO) {
  const decisionOk = decision && decision.decision === "accept";
  const promoteOk = decision && decision.promote_to_production === true;
  const validation = isValidationPass(weekRoot, repo);
  const canary = isCanaryPass(weekRoot, repo);
  const r285 = is285RPass(weekRoot);
  return {
    decision_accept: !!decisionOk,
    promote_to_production: !!promoteOk,
    validation_pass: validation,
    canary_pass: canary,
    r285_pass: r285,
    all_pass: !!(decisionOk && promoteOk && validation && canary && r285),
  };
}

function queuePath(dirs, approvalId) {
  return join(dirs.queue, `${approvalId}.json`);
}

function listQueueFiles(dirs) {
  if (!existsSync(dirs.queue)) return [];
  return readdirSync(dirs.queue)
    .filter((f) => f.endsWith(".json"))
    .map((f) => readJson(join(dirs.queue, f)))
    .filter(Boolean);
}

function remainingMs(item, now = new Date()) {
  if (!item || !item.expires_at) return null;
  return new Date(item.expires_at).getTime() - now.getTime();
}

function withRemaining(item, now = new Date()) {
  const rem = remainingMs(item, now);
  return {
    ...item,
    remaining_ms: rem,
    remaining_days:
      rem == null ? null : Math.max(0, Math.ceil(rem / (24 * 60 * 60 * 1000))),
  };
}

export function rebuildIndex(dirs = ensureDirs(), now = new Date()) {
  const items = listQueueFiles(dirs).map((x) => withRemaining(x, now));
  items.sort((a, b) => String(a.created_at || "").localeCompare(String(b.created_at || "")));
  const index = {
    schema_version: "expect-v88-approval-index/1.0",
    baseline_lock: `Version${BASELINE_LOCK}`,
    updated_at: now.toISOString(),
    pending_count: items.filter((x) => x.status === "pending").length,
    items,
  };
  writeJson(dirs.index, index);
  writeJson(dirs.publicSnapshot, {
    ...index,
    production_auto_apply: false,
    boundary: "Accept → RC → Deploy Note → Human Deploy",
  });
  return index;
}

/**
 * Attempt enqueue from Friday decision.json. No-op unless all gates pass.
 */
export function maybeEnqueueFromDecision(opts = {}) {
  const repo = opts.repo || REPO;
  const weekId = opts.week_id || weekIdJst();
  const weekRoot =
    opts.weekRoot || join(repo, "development", "weekly", weekId);
  const decision =
    opts.decision ||
    readJson(join(weekRoot, "fri-decision", "decision.json"));
  const dirs = ensureDirs(approvalsDirs(repo));
  const gates = evaluateEnqueueGates(decision, weekRoot, repo);

  if (!gates.all_pass) {
    return {
      enqueued: false,
      reason: "enqueue_gates_not_met",
      gates,
      week_id: weekId,
    };
  }

  const proposalIds = decision.proposal_ids || [];
  const approvalId = `APR-${weekId}-${(proposalIds[0] || "week").replace(/[^a-zA-Z0-9_-]/g, "_")}`;
  const existing = readJson(queuePath(dirs, approvalId));
  if (existing && existing.status === "pending") {
    return { enqueued: false, reason: "already_pending", approval_id: approvalId, gates };
  }

  const created = new Date(opts.now || Date.now());
  const expires = new Date(created.getTime() + TTL_MS);
  const item = {
    schema_version: SCHEMA,
    approval_id: approvalId,
    week_id: weekId,
    proposal_ids: proposalIds,
    status: "pending",
    created_at: created.toISOString(),
    expires_at: expires.toISOString(),
    decision_ref: join("development", "weekly", weekId, "fri-decision", "decision.json"),
    decision: "accept",
    promote_to_production_requested: true,
    production_auto_apply: false,
    gates: {
      validation: "PASS",
      canary: "PASS",
      r285: "PASS",
    },
    boundary: "Accept → RC → Deploy Note → Human Deploy",
    actor: null,
    reject_reason: null,
    auto: false,
    deploy_note_path: null,
  };
  writeJson(queuePath(dirs, approvalId), item);
  mkdirSync(join(weekRoot, "approval"), { recursive: true });
  writeJson(join(weekRoot, "approval", `${approvalId}.json`), item);
  rebuildIndex(dirs, created);
  return { enqueued: true, approval_id: approvalId, item, gates };
}

function recordKnowledgeReject(item, reason, auto, repo = REPO) {
  return appendApprovalRejectedPattern({
    repo,
    week_id: item.week_id,
    approval_id: item.approval_id,
    proposal: (item.proposal_ids && item.proposal_ids[0]) || item.approval_id,
    reason,
    auto: !!auto,
    source: "v88_approval_queue",
  });
}

function writeDeployNoteForApproval(item, repo = REPO) {
  const weekRoot = join(repo, "development", "weekly", item.week_id);
  const outDir = join(weekRoot, "sat-deploy");
  mkdirSync(outDir, { recursive: true });
  const out = join(outDir, "deploy-note.json");
  const note = {
    schema_version: "expect-v8-deploy-note/1.0",
    ok: true,
    action: "deploy_note_only_no_auto_apply",
    week_id: item.week_id,
    approval_id: item.approval_id,
    decision: "accept",
    promote_to_production: false,
    production_auto_apply: false,
    boundary: "Accept → RC → Deploy Note → Human Deploy",
    note:
      "Version8.8 Approval: Dashboard Approve 済み。Deploy Note のみ。Production 自動適用禁止。Human Deploy 必須。",
    proposal_ids: item.proposal_ids || [],
    human_deploy_required: true,
    approved_at: new Date().toISOString(),
  };
  writeJson(out, note);
  return out;
}

export function approveApproval(approvalId, opts = {}) {
  const repo = opts.repo || REPO;
  const dirs = ensureDirs(approvalsDirs(repo));
  const path = queuePath(dirs, approvalId);
  const item = readJson(path);
  if (!item) return { ok: false, error: "not_found" };
  if (item.status !== "pending") {
    return { ok: false, error: "not_pending", status: item.status };
  }
  const now = new Date(opts.now || Date.now());
  if (new Date(item.expires_at).getTime() < now.getTime()) {
    return expireOne(item, dirs, now, repo);
  }
  const deployNotePath = writeDeployNoteForApproval(item, repo);
  const updated = {
    ...item,
    status: "approved",
    actor: opts.actor || null,
    approved_at: now.toISOString(),
    auto: false,
    production_auto_apply: false,
    deploy_note_path: deployNotePath.replace(/\\/g, "/"),
  };
  writeJson(path, updated);
  rebuildIndex(dirs, now);
  return { ok: true, item: withRemaining(updated, now), deploy_note: deployNotePath };
}

export function rejectApproval(approvalId, opts = {}) {
  const repo = opts.repo || REPO;
  const dirs = ensureDirs(approvalsDirs(repo));
  const path = queuePath(dirs, approvalId);
  const item = readJson(path);
  if (!item) return { ok: false, error: "not_found" };
  if (item.status !== "pending") {
    return { ok: false, error: "not_pending", status: item.status };
  }
  const reason = String(opts.reason || "").trim() || "rejected";
  const now = new Date(opts.now || Date.now());
  const auto = !!opts.auto;
  const kbId = recordKnowledgeReject(item, reason, auto, repo);
  const updated = {
    ...item,
    status: "rejected",
    reject_reason: reason,
    reason,
    auto,
    actor: opts.actor || (auto ? "system" : null),
    rejected_at: now.toISOString(),
    knowledge_pattern_id: kbId,
  };
  writeJson(path, updated);
  rebuildIndex(dirs, now);
  return { ok: true, item: withRemaining(updated, now), knowledge_pattern_id: kbId };
}

function expireOne(item, dirs, now, repo = REPO) {
  return rejectApproval(item.approval_id, {
    reason: "approval_timeout",
    auto: true,
    actor: "system",
    now,
    repo,
  });
}

/** Daily 03:00 Runner: pending past expires_at → rejected / approval_timeout / auto. */
export function expireOverdueApprovals(opts = {}) {
  const repo = opts.repo || REPO;
  const dirs = ensureDirs(approvalsDirs(repo));
  const now = new Date(opts.now || Date.now());
  const expired = [];
  for (const item of listQueueFiles(dirs)) {
    if (item.status !== "pending") continue;
    if (new Date(item.expires_at).getTime() > now.getTime()) continue;
    const r = expireOne(item, dirs, now, repo);
    if (r.ok) expired.push(r.item);
  }
  rebuildIndex(dirs, now);
  return {
    ok: true,
    expired_count: expired.length,
    expired,
    at: now.toISOString(),
  };
}

export function listApprovals(opts = {}) {
  const dirs = ensureDirs(approvalsDirs(opts.repo || REPO));
  const now = new Date(opts.now || Date.now());
  const index = rebuildIndex(dirs, now);
  const status = opts.status || "";
  let items = index.items || [];
  if (status) items = items.filter((x) => x.status === status);
  return { ...index, items };
}

function main() {
  if (hasFlag("--expire") || hasFlag("--audit")) {
    console.log(JSON.stringify(expireOverdueApprovals(), null, 2));
    return;
  }
  if (hasFlag("--enqueue")) {
    const weekId = arg("--week-id", weekIdJst());
    console.log(
      JSON.stringify(
        maybeEnqueueFromDecision({
          week_id: weekId,
          weekRoot: arg("--week-root", "") || undefined,
        }),
        null,
        2
      )
    );
    return;
  }
  if (hasFlag("--approve")) {
    const id = arg("--approve") || arg("--id");
    console.log(
      JSON.stringify(
        approveApproval(id, { actor: arg("--actor", "admin") }),
        null,
        2
      )
    );
    return;
  }
  if (hasFlag("--reject")) {
    const id = arg("--reject") || arg("--id");
    console.log(
      JSON.stringify(
        rejectApproval(id, {
          actor: arg("--actor", "admin"),
          reason: arg("--reason", "rejected"),
          auto: hasFlag("--auto"),
        }),
        null,
        2
      )
    );
    return;
  }
  if (hasFlag("--list")) {
    console.log(
      JSON.stringify(listApprovals({ status: arg("--status", "") }), null, 2)
    );
    return;
  }
  console.log(
    JSON.stringify(
      {
        usage:
          "approval-queue.mjs --enqueue|--expire|--list|--approve ID|--reject ID [--reason ...] [--actor ...]",
      },
      null,
      2
    )
  );
}

const isMain =
  process.argv[1] &&
  String(process.argv[1]).replace(/\\/g, "/").endsWith("approval-queue.mjs");
if (isMain) {
  try {
    main();
  } catch (e) {
    console.error(e && e.message ? e.message : e);
    process.exit(1);
  }
}
