#!/usr/bin/env node
/**
 * Version8.6 — Research Scheduler Runner (single weekly orchestrator).
 *
 * Daily 03:00 JST (systemd) → decide weekday → run one phase (or skip).
 * Maintenance window only. No Production auto-apply. Baseline 8.5 lock.
 *
 * Usage:
 *   npm run v8:runner
 *   node scripts/ops/v8/runner.mjs
 *   node scripts/ops/v8/runner.mjs --force   # ops override (tests)
 *   node scripts/ops/v8/runner.mjs --dry-run
 */
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import {
  PHASE_META,
  PHASE_ORDER,
  appendLog,
  emptyRunnerState,
  ensureSchedulerDirs,
  evaluateSkip,
  nextRunHintJst,
  planTick,
  readJson,
  repoRoot,
  schedulerDirs,
  weekIdJst,
  writeJson,
  BASELINE_LOCK,
} from "./runner-lib.mjs";
import { expireOverdueApprovals } from "./approval-queue.mjs";
import { publishOpsSnapshot } from "./publish-ops-snapshot.mjs";

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function loadOrInitState(weekId, paths) {
  const existing = readJson(paths.weeklyRunner, null);
  if (existing && existing.week_id === weekId) return existing;
  // New week — reset phase board
  return emptyRunnerState(weekId);
}

function pushHistory(paths, entry) {
  const hist = readJson(paths.phaseHistory, []);
  const arr = Array.isArray(hist) ? hist : [];
  arr.push(entry);
  while (arr.length > 200) arr.shift();
  writeJson(paths.phaseHistory, arr);
  return arr;
}

function publishSnapshot(paths, state, extras = {}) {
  const snap = {
    ...state,
    ...extras,
    schema_version: "expect-v86-research-scheduler-card/1.0",
    published_at: new Date().toISOString(),
  };
  writeJson(paths.publicSnapshot, snap);
  writeJson(paths.weeklyRunner, state);
  return snap;
}

function runPhaseCommand(phaseId, weekId) {
  const meta = PHASE_META[phaseId];
  if (!meta) throw new Error(`Unknown phase: ${phaseId}`);
  const args = [
    join(repoRoot(), "scripts/ops/v8/run-day.mjs"),
    "--day",
    meta.day,
    "--week-id",
    weekId,
  ];
  if (meta.sub) {
    args.push("--phase", meta.sub);
  }
  // Runner already gated Maintenance; allow weekday scripts if Sat recovery override
  if (hasFlag("--force")) args.push("--allow-weekend");

  const r = spawnSync(process.execPath, args, {
    cwd: repoRoot(),
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (r.stdout) process.stdout.write(r.stdout);
  if (r.stderr) process.stderr.write(r.stderr);
  return {
    status: r.status ?? 1,
    ok: r.status === 0,
    stdout: r.stdout || "",
    stderr: r.stderr || "",
  };
}

function runHealthCheck(weekId) {
  try {
    const r = spawnSync(
      process.execPath,
      [
        join(repoRoot(), "scripts/ops/v8/incident-report.mjs"),
        "--week-id",
        weekId,
      ],
      { cwd: repoRoot(), encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    );
    if (r.stdout) {
      try {
        return JSON.parse(r.stdout);
      } catch {
        return { has_incident: false, raw: r.stdout };
      }
    }
    return { has_incident: false };
  } catch (e) {
    return { has_incident: false, error: String(e?.message || e) };
  }
}

function checkBaselineFlags() {
  const betaPath = join(repoRoot(), "config", "beta.json");
  const beta = readJson(betaPath, {});
  const f = beta.ui_features || {};
  const canaryOn = [
    "v8_canary_candidate_pool",
    "v8_canary_repick",
    "v8_canary_delete",
    "v8_canary_confidence",
    "v8_production_canary",
  ].filter((k) => f[k] === true);
  return {
    baseline_lock: `Version${BASELINE_LOCK}`,
    canary_flags_off: canaryOn.length === 0,
    canary_on: canaryOn,
    production_auto_apply: false,
  };
}

export function runScheduler(opts = {}) {
  const now = opts.now || new Date();
  const force = opts.force || hasFlag("--force");
  const dryRun = opts.dryRun || hasFlag("--dry-run");
  const paths = ensureSchedulerDirs();
  const weekId = opts.week_id || arg("--week-id", weekIdJst(now));

  appendLog(paths.runnerLog, `tick start week=${weekId} force=${force} dry=${dryRun}`);

  // Version8.8 — daily Approval Queue audit (expires_at → approval_timeout → Knowledge)
  let approvalExpire = { expired_count: 0 };
  try {
    if (!dryRun) {
      approvalExpire = expireOverdueApprovals({ now });
      appendLog(
        paths.runnerLog,
        `approval_expire count=${approvalExpire.expired_count || 0}`
      );
    }
  } catch (e) {
    appendLog(
      paths.runnerLog,
      `approval_expire_error ${String(e && e.message ? e.message : e)}`
    );
  }

  let state = loadOrInitState(weekId, paths);
  state.week_id = weekId;
  state.baseline_lock = `Version${BASELINE_LOCK}`;
  const nextHint = nextRunHintJst(now);
  state.next_run_jst = nextHint.iso || nextHint.schedule || null;
  state.updated_at = new Date().toISOString();

  const finalize = function (payload) {
    if (dryRun) return payload;
    try {
      const pub = publishOpsSnapshot({ now });
      appendLog(
        paths.runnerLog,
        `publish ok week=${(pub.summary && pub.summary.week_id) || ""} next=${(pub.summary && pub.summary.next_run) || ""}`
      );
      return Object.assign({}, payload, {
        publish: { ok: true, summary: pub.summary || null },
      });
    } catch (e) {
      appendLog(
        paths.runnerLog,
        `publish_error ${String(e && e.message ? e.message : e)}`
      );
      return Object.assign({}, payload, {
        publish: { ok: false, error: String(e && e.message ? e.message : e) },
      });
    }
  };

  const plan = planTick(now, {
    week_id: weekId,
    weekRoot: join(repoRoot(), "development", "weekly", weekId),
    runnerState: state,
    forceRun: force,
  });

  const flags = checkBaselineFlags();

  // dry-run: plan only — no state mutation, no ops-data publish
  if (dryRun) {
    appendLog(
      paths.runnerLog,
      `dry-run plan=${plan.plan || plan.phase || "?"} week=${weekId} next=${nextHint.iso || ""} skip_publish=1`
    );
    return {
      ok: true,
      action: "dry_run",
      plan,
      week_id: weekId,
      next_run: nextHint.iso || nextHint.schedule || null,
      approval_expire: approvalExpire,
      publish: { ok: false, skipped: true, reason: "dry_run" },
    };
  }

  if (plan.plan === "skip" || plan.skip) {
    state.skip_count = (state.skip_count || 0) + 1;
    state.last_skip_reason = plan.reason || plan.detail || "skip";
    state.last_run_at = new Date().toISOString();
    state.current_phase = null;
    state.recovery_active = false;
    const snap = publishSnapshot(paths, state, {
      display: {
        current_phase: null,
        next_run: nextHint.iso || nextHint.schedule || null,
        last_run: state.last_run_at,
        duration_ms: 0,
        success: state.success_count,
        failure: state.failure_count,
        skip_reason: state.last_skip_reason,
        recovery: false,
      },
      health: flags,
      last_tick: { action: "skip", reason: state.last_skip_reason, date_jst: plan.date_jst },
    });
    appendLog(paths.runnerLog, `skip reason=${state.last_skip_reason}`);
    return finalize({
      ok: true,
      action: "skip",
      reason: state.last_skip_reason,
      state: snap,
      approval_expire: approvalExpire,
    });
  }

  if (plan.plan === "all_done") {
    state.current_phase = null;
    state.recovery_active = false;
    state.last_run_at = new Date().toISOString();
    state.last_skip_reason = "week_phases_complete";
    const health = runHealthCheck(weekId);
    const snap = publishSnapshot(paths, state, {
      display: {
        current_phase: "complete",
        next_run: nextHint.schedule,
        last_run: state.last_run_at,
        duration_ms: 0,
        success: state.success_count,
        failure: state.failure_count,
        skip_reason: "week_complete",
        recovery: false,
      },
      health: { ...flags, incident: health },
      last_tick: { action: "all_done", week_id: weekId },
    });
    appendLog(paths.runnerLog, "all phases complete");
    return finalize({ ok: true, action: "all_done", state: snap, approval_expire: approvalExpire });
  }

  if (plan.plan === "blocked" || plan.plan === "wait") {
    state.last_run_at = new Date().toISOString();
    state.last_skip_reason = plan.reason;
    state.current_phase = plan.next_phase || plan.waiting_on || null;
    state.recovery_active = plan.plan === "blocked";
    const snap = publishSnapshot(paths, state, {
      display: {
        current_phase: state.current_phase || null,
        next_run: nextHint.iso || nextHint.schedule || null,
        last_run: state.last_run_at,
        duration_ms: 0,
        success: state.success_count,
        failure: state.failure_count,
        skip_reason: plan.reason,
        recovery: state.recovery_active,
      },
      health: flags,
      last_tick: { action: plan.plan, reason: plan.reason },
    });
    appendLog(paths.runnerLog, `${plan.plan} ${plan.reason}`);
    return finalize({
      ok: true,
      action: plan.plan,
      reason: plan.reason,
      state: snap,
      approval_expire: approvalExpire,
    });
  }

  const phaseId = plan.phase;
  if (!phaseId) {
    appendLog(paths.runnerLog, "no phase planned");
    return finalize({ ok: true, action: "noop", state, approval_expire: approvalExpire });
  }

  // Double-exec: already completed
  if (state.phases[phaseId]?.status === "completed") {
    appendLog(paths.runnerLog, `double-exec guard skip phase=${phaseId}`);
    state.last_skip_reason = `already_completed:${phaseId}`;
    state.skip_count += 1;
    const snap = publishSnapshot(paths, state, {
      display: {
        current_phase: phaseId,
        next_run: nextHint.iso || nextHint.schedule || null,
        last_run: new Date().toISOString(),
        skip_reason: state.last_skip_reason,
        recovery: false,
        success: state.success_count,
        failure: state.failure_count,
      },
      health: flags,
    });
    return finalize({
      ok: true,
      action: "skip_double",
      phase: phaseId,
      state: snap,
      approval_expire: approvalExpire,
    });
  }

  const started = Date.now();
  const startedIso = new Date().toISOString();
  state.current_phase = phaseId;
  state.recovery_active = !!plan.recovery;
  state.phases[phaseId] = {
    ...state.phases[phaseId],
    status: "running",
    started_at: startedIso,
    ended_at: null,
    duration_ms: null,
    exit_reason: null,
  };
  publishSnapshot(paths, state, { health: flags });
  appendLog(paths.runnerLog, `phase start ${phaseId} recovery=${!!plan.recovery}`);

  let result;
  try {
    result = runPhaseCommand(phaseId, weekId);
  } catch (e) {
    result = { ok: false, status: 1, stderr: String(e?.message || e), stdout: "" };
  }

  const endedIso = new Date().toISOString();
  const duration = Date.now() - started;
  const exitReason = result.ok ? "success" : `exit_${result.status}`;

  state.phases[phaseId] = {
    status: result.ok ? "completed" : "failed",
    started_at: startedIso,
    ended_at: endedIso,
    duration_ms: duration,
    exit_reason: exitReason,
  };
  state.last_run_at = endedIso;
  state.current_phase = result.ok ? null : phaseId;
  state.recovery_active = !result.ok;

  if (result.ok) {
    state.success_count += 1;
    state.last_success_at = endedIso;
    state.last_skip_reason = null;
  } else {
    state.failure_count += 1;
    state.last_failure_at = endedIso;
  }

  pushHistory(paths, {
    week_id: weekId,
    phase: phaseId,
    label: PHASE_META[phaseId]?.label,
    started_at: startedIso,
    ended_at: endedIso,
    duration_ms: duration,
    exit_reason: exitReason,
    recovery: !!plan.recovery,
    ok: result.ok,
  });

  // Friday report done → health + incident if needed
  let healthExtra = flags;
  if (result.ok && phaseId === "report") {
    healthExtra = { ...flags, incident: runHealthCheck(weekId) };
  }

  const snap = publishSnapshot(paths, state, {
    display: {
      current_phase: result.ok
        ? PHASE_ORDER[PHASE_ORDER.indexOf(phaseId) + 1] || "complete"
        : phaseId,
      next_run: nextHint.iso || nextHint.schedule || null,
      last_run: endedIso,
      duration_ms: duration,
      success: state.success_count,
      failure: state.failure_count,
      skip_reason: result.ok ? null : exitReason,
      recovery: state.recovery_active,
    },
    health: healthExtra,
    last_tick: {
      action: result.ok ? "success" : "failure",
      phase: phaseId,
      duration_ms: duration,
      exit_reason: exitReason,
    },
  });

  appendLog(
    paths.runnerLog,
    `phase end ${phaseId} ok=${result.ok} duration_ms=${duration} reason=${exitReason}`
  );

  return finalize({
    ok: result.ok,
    action: result.ok ? "ran" : "failed",
    phase: phaseId,
    duration_ms: duration,
    state: snap,
    approval_expire: approvalExpire,
  });
}

function main() {
  const out = runScheduler({
    force: hasFlag("--force"),
    dryRun: hasFlag("--dry-run"),
    week_id: arg("--week-id", undefined),
  });
  console.log(
    JSON.stringify(
      {
        event: "v8_research_scheduler",
        baseline_lock: `Version${BASELINE_LOCK}`,
        action: out.action,
        phase: out.phase || null,
        reason: out.reason || null,
        ok: out.ok,
        duration_ms: out.duration_ms || null,
        approval_expire: out.approval_expire || null,
        publish: out.publish || null,
        paths: schedulerDirs(),
      },
      null,
      2
    )
  );
  if (!out.ok && out.action === "failed") process.exit(1);
}

if (process.argv[1]?.endsWith("runner.mjs")) {
  try {
    main();
  } catch (e) {
    console.error(e && e.message ? e.message : e);
    process.exit(1);
  }
}
