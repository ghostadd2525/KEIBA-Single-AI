/**
 * Version8.6 — Research Scheduler (shared planning / state).
 * PE / CE / AI / Production untouched. No auto Production deploy.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync, appendFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { isResearchWeekMaintenance } from "../../../functions/_lib/maintenanceSchedule.js";
import { jstParts, weekIdJst, repoRoot } from "./calendar.mjs";
import { BASELINE_LOCK } from "./ops-baseline.mjs";

/** Ordered Research phases (Recovery resumes from first incomplete). */
export const PHASE_ORDER = [
  "analyzer",
  "proposal",
  "validation",
  "canary",
  "baseline",
  "decision",
  "knowledge",
  "governance",
  "report",
];

/** Calendar weekday (0=Sun) → phases allowed to *start* that day (recovery may run earlier incomplete). */
export const WEEKDAY_PHASES = {
  1: ["analyzer"],
  2: ["proposal", "validation"],
  3: ["canary"],
  4: ["baseline"],
  5: ["decision", "knowledge", "governance", "report"],
  0: [],
  6: [],
};

export const PHASE_META = {
  analyzer: { day: "mon", manifesto: "mon_analyzer", label: "Analyzer" },
  proposal: { day: "tue", manifesto: "tue_proposal", label: "Proposal", sub: "proposal" },
  validation: { day: "tue", manifesto: "tue_validation", label: "Validation", sub: "validation" },
  canary: { day: "wed", manifesto: "wed_canary", label: "Canary" },
  baseline: { day: "thu", manifesto: "thu_baseline", label: "285R Baseline" },
  decision: { day: "fri", manifesto: "fri_decision", label: "Decision", sub: "decision" },
  knowledge: { day: "fri", manifesto: "fri_knowledge", label: "Knowledge", sub: "knowledge" },
  governance: { day: "fri", manifesto: "fri_governance", label: "Governance", sub: "governance" },
  report: { day: "fri", manifesto: "fri_report", label: "Weekly Report", sub: "report" },
};

export function schedulerDirs(repo = repoRoot()) {
  const sched = join(repo, "development", "scheduler");
  const pub = join(repo, "public", "ops-data");
  return {
    sched,
    pub,
    weeklyRunner: join(sched, "weekly-runner.json"),
    phaseHistory: join(sched, "phase-history.json"),
    runnerLog: join(sched, "runner.log"),
    publicSnapshot: join(pub, "research-scheduler.json"),
  };
}

export function ensureSchedulerDirs(repo = repoRoot()) {
  const d = schedulerDirs(repo);
  mkdirSync(d.sched, { recursive: true });
  mkdirSync(d.pub, { recursive: true });
  return d;
}

export function readJson(path, fallback = null) {
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

export function writeJson(path, doc) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(doc, null, 2) + "\n", "utf8");
}

export function appendLog(path, line) {
  mkdirSync(dirname(path), { recursive: true });
  const ts = new Date().toISOString();
  appendFileSync(path, `[${ts}] ${line}\n`, "utf8");
}

/**
 * Skip conditions (Research Scheduler).
 * @returns {{ skip: boolean, reason: string|null, maintenance: boolean, weekday: number }}
 */
export function evaluateSkip(now = new Date(), opts = {}) {
  const parts = jstParts(now);
  const maintenance = isResearchWeekMaintenance(now);

  if (opts.forceRun) {
    return { skip: false, reason: null, maintenance, ...parts };
  }

  // Public window → always skip Research
  if (!maintenance) {
    return {
      skip: true,
      reason: "public_window",
      detail: "Public期間は Research Skip（Maintenance期間のみ実行）",
      maintenance: false,
      ...parts,
    };
  }

  // Sat/Sun calendar (redundant with public for Sat+Sun morning, but explicit)
  if (parts.weekday === 0 || parts.weekday === 6) {
    return {
      skip: true,
      reason: "weekend",
      detail: `土日は Research skip（JST ${parts.weekday_name}）`,
      maintenance,
      ...parts,
    };
  }

  return { skip: false, reason: null, maintenance: true, ...parts };
}

export function loadManifesto(weekRoot) {
  return readJson(join(weekRoot, "manifesto.json"), null);
}

export function phaseStatusFromManifesto(manifesto, phaseId) {
  if (!manifesto || !manifesto.stages) return "pending";
  const key = PHASE_META[phaseId]?.manifesto;
  if (!key) return "pending";
  const st = manifesto.stages[key];
  if (!st) return "pending";
  return String(st.status || "pending");
}

export function isPhaseComplete(manifesto, phaseId, runnerState) {
  const fromRunner = runnerState?.phases?.[phaseId]?.status;
  if (fromRunner === "completed") return true;
  if (fromRunner === "failed") return false;
  const m = phaseStatusFromManifesto(manifesto, phaseId);
  return m === "completed";
}

/**
 * First incomplete phase in order, respecting recovery.
 * Also enforces: cannot start phase if previous failed/incomplete.
 */
export function nextPhaseToRun(manifesto, runnerState, weekday) {
  const allowedToday = new Set(WEEKDAY_PHASES[weekday] || []);
  let firstIncomplete = null;

  for (const id of PHASE_ORDER) {
    if (isPhaseComplete(manifesto, id, runnerState)) continue;
    const st = runnerState?.phases?.[id]?.status;
    if (st === "failed") {
      // Resume this failed phase (recovery)
      firstIncomplete = id;
      break;
    }
    firstIncomplete = id;
    break;
  }

  if (!firstIncomplete) {
    return { phase: null, action: "all_done", reason: "week_phases_complete" };
  }

  // Double-exec guard: today's planned phases that are already complete → skip those
  // Recovery: if incomplete phase is *before* today's window, still run it (resume)
  const idx = PHASE_ORDER.indexOf(firstIncomplete);
  const todayIds = WEEKDAY_PHASES[weekday] || [];
  const todayMinIdx =
    todayIds.length === 0
      ? Infinity
      : Math.min(...todayIds.map((p) => PHASE_ORDER.indexOf(p)));

  // If we're behind schedule (incomplete before today), recover
  if (idx < todayMinIdx || allowedToday.has(firstIncomplete)) {
    // Order guarantee: previous must be complete
    if (idx > 0) {
      const prev = PHASE_ORDER[idx - 1];
      if (!isPhaseComplete(manifesto, prev, runnerState)) {
        return {
          phase: null,
          action: "blocked",
          reason: `prerequisite_incomplete:${prev}`,
          waiting_on: prev,
        };
      }
      const prevFail = runnerState?.phases?.[prev]?.status === "failed";
      if (prevFail) {
        return {
          phase: null,
          action: "blocked",
          reason: `prerequisite_failed:${prev}`,
          waiting_on: prev,
        };
      }
    }
    return {
      phase: firstIncomplete,
      action: "run",
      reason: idx < todayMinIdx ? "recovery" : "scheduled",
      recovery: idx < todayMinIdx || runnerState?.phases?.[firstIncomplete]?.status === "failed",
    };
  }

  // Incomplete phase is in the future relative to today — wait
  return {
    phase: null,
    action: "wait",
    reason: `waiting_for_calendar:${firstIncomplete}`,
    next_phase: firstIncomplete,
  };
}

/** Phases to attempt this tick (one phase per runner invocation for safety). */
export function planTick(now = new Date(), ctx = {}) {
  const skip = evaluateSkip(now, ctx);
  if (skip.skip) {
    return { ...skip, plan: "skip", phase: null };
  }
  const weekId = ctx.week_id || weekIdJst(now);
  const weekRoot =
    ctx.weekRoot || join(repoRoot(), "development", "weekly", weekId);
  const manifesto = loadManifesto(weekRoot);
  const runnerState = ctx.runnerState || null;
  const next = nextPhaseToRun(manifesto, runnerState, skip.weekday);
  return {
    skip: false,
    plan: next.action,
    phase: next.phase,
    reason: next.reason,
    recovery: !!next.recovery,
    week_id: weekId,
    week_root: weekRoot,
    maintenance: true,
    weekday: skip.weekday,
    weekday_name: skip.weekday_name,
    date_jst: skip.date_jst,
    waiting_on: next.waiting_on || null,
    next_phase: next.next_phase || next.phase,
  };
}

export function emptyRunnerState(weekId) {
  const phases = {};
  for (const id of PHASE_ORDER) {
    phases[id] = { status: "pending", started_at: null, ended_at: null, duration_ms: null, exit_reason: null };
  }
  return {
    schema_version: "expect-v86-weekly-runner/1.0",
    baseline_lock: `Version${BASELINE_LOCK}`,
    week_id: weekId,
    current_phase: null,
    last_run_at: null,
    last_success_at: null,
    last_failure_at: null,
    last_skip_reason: null,
    recovery_active: false,
    success_count: 0,
    failure_count: 0,
    skip_count: 0,
    next_run_jst: null,
    phases,
    deploy_policy: "deploy_note_only",
    production_auto_apply: false,
    updated_at: new Date().toISOString(),
  };
}

export function nextRunHintJst(now = new Date()) {
  // Next 03:00 JST as concrete timestamp (no fixed marketing label).
  const p = jstParts(now);
  const [y, m, d] = String(p.date_jst).split("-").map(Number);
  let candidateUtc = Date.UTC(y, m - 1, d, 3 - 9, 0, 0);
  if (candidateUtc <= now.getTime()) candidateUtc += 24 * 60 * 60 * 1000;
  const next = new Date(candidateUtc);
  const j = jstParts(next);
  const iso = `${j.date_jst}T03:00:00+09:00`;
  return {
    schedule: iso,
    iso,
    date_jst: j.date_jst,
    note: "systemd timer expect-v8-research-scheduler.timer",
  };
}

export { BASELINE_LOCK, weekIdJst, jstParts, repoRoot, isResearchWeekMaintenance };
