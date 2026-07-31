/**
 * Version8.6 Research Scheduler — unit tests
 */
import test from "node:test";
import assert from "node:assert/strict";
import {
  evaluateSkip,
  nextPhaseToRun,
  PHASE_ORDER,
  emptyRunnerState,
  planTick,
} from "../../scripts/ops/v8/runner-lib.mjs";
import { isResearchWeekMaintenance } from "../../functions/_lib/maintenanceSchedule.js";

function jstWall(y, m, d, hh, mm) {
  return new Date(Date.UTC(y, m - 1, d, hh - 9, mm, 0));
}

test("Public window (Sat) → skip", () => {
  const sat = jstWall(2026, 7, 25, 3, 0); // Sat 03:00
  assert.equal(isResearchWeekMaintenance(sat), false);
  const s = evaluateSkip(sat);
  assert.equal(s.skip, true);
  assert.equal(s.reason, "public_window");
});

test("Maintenance Mon 03:00 → not skip", () => {
  const mon = jstWall(2026, 7, 20, 3, 0);
  assert.equal(isResearchWeekMaintenance(mon), true);
  const s = evaluateSkip(mon);
  assert.equal(s.skip, false);
});

test("Sun 03:00 Public → skip", () => {
  const sun = jstWall(2026, 7, 19, 3, 0);
  const s = evaluateSkip(sun);
  assert.equal(s.skip, true);
});

test("Recovery resumes failed validation", () => {
  const state = emptyRunnerState("2026-W30");
  state.phases.analyzer.status = "completed";
  state.phases.proposal.status = "completed";
  state.phases.validation.status = "failed";
  const manifesto = {
    stages: {
      mon_analyzer: { status: "completed" },
      tue_proposal: { status: "completed" },
      tue_validation: { status: "pending" },
    },
  };
  // Wednesday — still recover validation before canary
  const next = nextPhaseToRun(manifesto, state, 3);
  assert.equal(next.action, "run");
  assert.equal(next.phase, "validation");
  assert.equal(next.recovery, true);
});

test("Order block: canary waits if validation incomplete", () => {
  const state = emptyRunnerState("2026-W30");
  state.phases.analyzer.status = "completed";
  state.phases.proposal.status = "completed";
  const manifesto = {
    stages: {
      mon_analyzer: { status: "completed" },
      tue_proposal: { status: "completed" },
    },
  };
  const next = nextPhaseToRun(manifesto, state, 3); // Wed
  assert.equal(next.phase, "validation");
  assert.equal(next.action, "run");
});

test("Double-complete: all done", () => {
  const state = emptyRunnerState("2026-W30");
  for (const id of PHASE_ORDER) state.phases[id].status = "completed";
  const manifesto = { stages: {} };
  const next = nextPhaseToRun(manifesto, state, 5);
  assert.equal(next.action, "all_done");
});

test("planTick dry path public", () => {
  const plan = planTick(jstWall(2026, 7, 25, 3, 0), {
    week_id: "2026-W30",
    runnerState: emptyRunnerState("2026-W30"),
  });
  assert.equal(plan.plan, "skip");
  assert.equal(plan.reason, "public_window");
});

test("Deploy policy constant: no production auto apply", () => {
  const s = emptyRunnerState("2026-W30");
  assert.equal(s.production_auto_apply, false);
  assert.equal(s.deploy_policy, "deploy_note_only");
  assert.equal(s.baseline_lock, "Version8.5");
});
