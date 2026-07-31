import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  evaluateEnqueueGates,
  maybeEnqueueFromDecision,
  expireOverdueApprovals,
  approveApproval,
  rejectApproval,
  approvalsDirs,
} from "../../scripts/ops/v8/approval-queue.mjs";

function writeWeekFixtures(repo, weekId, opts = {}) {
  const weekRoot = join(repo, "development", "weekly", weekId);
  mkdirSync(join(weekRoot, "fri-decision"), { recursive: true });
  mkdirSync(join(weekRoot, "tue-proposal"), { recursive: true });
  mkdirSync(join(weekRoot, "wed-canary"), { recursive: true });
  mkdirSync(join(weekRoot, "thu-baseline"), { recursive: true });
  mkdirSync(join(repo, "development", "knowledge"), { recursive: true });

  writeFileSync(
    join(weekRoot, "tue-proposal", "proposal-validation.json"),
    JSON.stringify(
      {
        validations: [{ gate: "pass", family: "test", proposal: "test" }],
        summary: { pass: 1, fail: 0 },
      },
      null,
      2
    )
  );
  writeFileSync(
    join(weekRoot, "wed-canary", "ranked-run.json"),
    JSON.stringify(
      {
        results: [{ status: "evaluated", verdict: "PASS", proposal: "test" }],
      },
      null,
      2
    )
  );
  writeFileSync(
    join(weekRoot, "thu-baseline", "report.json"),
    JSON.stringify(
      {
        comparison: {
          verdict: opts.r285Verdict || "improvement",
          measured_delta_hit_at_1: opts.delta ?? 0.02,
        },
      },
      null,
      2
    )
  );
  return weekRoot;
}

test("enqueue only when accept+promote+all gates PASS", () => {
  const repo = mkdtempSync(join(tmpdir(), "v88-"));
  try {
    const weekId = "2026-W31";
    const weekRoot = writeWeekFixtures(repo, weekId);

    const noPromote = evaluateEnqueueGates(
      { decision: "accept", promote_to_production: false },
      weekRoot,
      repo
    );
    assert.equal(noPromote.all_pass, false);

    const rejectDec = evaluateEnqueueGates(
      { decision: "reject", promote_to_production: true },
      weekRoot,
      repo
    );
    assert.equal(rejectDec.all_pass, false);

    // fail 285R
    writeFileSync(
      join(weekRoot, "thu-baseline", "report.json"),
      JSON.stringify({ comparison: { verdict: "no_measured_delta" } })
    );
    const fail285 = evaluateEnqueueGates(
      { decision: "accept", promote_to_production: true, proposal_ids: ["IMP-1"] },
      weekRoot,
      repo
    );
    assert.equal(fail285.all_pass, false);
    assert.equal(fail285.r285_pass, false);

    writeWeekFixtures(repo, weekId, { r285Verdict: "improvement", delta: 0.01 });
    const ok = evaluateEnqueueGates(
      { decision: "accept", promote_to_production: true, proposal_ids: ["IMP-1"] },
      weekRoot,
      repo
    );
    assert.equal(ok.all_pass, true);

    const enq = maybeEnqueueFromDecision({
      repo,
      week_id: weekId,
      weekRoot,
      decision: {
        decision: "accept",
        promote_to_production: true,
        proposal_ids: ["IMP-1"],
      },
      now: new Date("2026-07-20T00:00:00.000Z"),
    });
    assert.equal(enq.enqueued, true);
    assert.ok(enq.item.created_at);
    assert.equal(enq.item.expires_at, "2026-07-27T00:00:00.000Z");
    assert.equal(enq.item.status, "pending");
  } finally {
    rmSync(repo, { recursive: true, force: true });
  }
});

test("timeout sets rejected / approval_timeout / auto and Knowledge", () => {
  const repo = mkdtempSync(join(tmpdir(), "v88-"));
  try {
    const weekId = "2026-W31";
    const weekRoot = writeWeekFixtures(repo, weekId);
    // Patch module REPO is fixed — enqueue uses approvalsDirs(repo) via maybeEnqueueFromDecision opts.repo
    const enq = maybeEnqueueFromDecision({
      repo,
      week_id: weekId,
      weekRoot,
      decision: {
        decision: "accept",
        promote_to_production: true,
        proposal_ids: ["IMP-T"],
      },
      now: new Date("2026-07-01T00:00:00.000Z"),
    });
    assert.equal(enq.enqueued, true);

    const exp = expireOverdueApprovals({
      repo,
      now: new Date("2026-07-10T00:00:00.000Z"),
    });
    assert.equal(exp.expired_count, 1);
    assert.equal(exp.expired[0].status, "rejected");
    assert.equal(exp.expired[0].reason, "approval_timeout");
    assert.equal(exp.expired[0].auto, true);

    const kb = JSON.parse(
      readFileSync(join(repo, "development", "knowledge", "rejected_patterns.json"), "utf8")
    );
    assert.ok(kb.patterns.some((p) => p.reason === "approval_timeout" && p.auto === true));
  } finally {
    rmSync(repo, { recursive: true, force: true });
  }
});

test("approve writes deploy-note only with production_auto_apply false", () => {
  const repo = mkdtempSync(join(tmpdir(), "v88-"));
  try {
    const weekId = "2026-W31";
    const weekRoot = writeWeekFixtures(repo, weekId);
    const enq = maybeEnqueueFromDecision({
      repo,
      week_id: weekId,
      weekRoot,
      decision: {
        decision: "accept",
        promote_to_production: true,
        proposal_ids: ["IMP-A"],
      },
      now: new Date("2026-07-20T00:00:00.000Z"),
    });
    assert.equal(enq.enqueued, true);
    const r = approveApproval(enq.approval_id, {
      repo,
      actor: "admin-test",
      now: new Date("2026-07-21T00:00:00.000Z"),
    });
    assert.equal(r.ok, true);
    assert.equal(r.item.status, "approved");
    assert.equal(r.item.production_auto_apply, false);
    const note = JSON.parse(readFileSync(r.deploy_note, "utf8"));
    assert.equal(note.production_auto_apply, false);
    assert.equal(note.human_deploy_required, true);
    assert.equal(note.boundary, "Accept → RC → Deploy Note → Human Deploy");
    assert.ok(existsSync(r.deploy_note));
  } finally {
    rmSync(repo, { recursive: true, force: true });
  }
});

test("reject with reason writes Knowledge rejected_patterns", () => {
  const repo = mkdtempSync(join(tmpdir(), "v88-"));
  try {
    const weekId = "2026-W31";
    const weekRoot = writeWeekFixtures(repo, weekId);
    const enq = maybeEnqueueFromDecision({
      repo,
      week_id: weekId,
      weekRoot,
      decision: {
        decision: "accept",
        promote_to_production: true,
        proposal_ids: ["IMP-R"],
      },
      now: new Date("2026-07-20T00:00:00.000Z"),
    });
    assert.equal(enq.enqueued, true);
    const r = rejectApproval(enq.approval_id, {
      repo,
      actor: "admin-test",
      reason: "regression_risk_demo",
      now: new Date("2026-07-21T00:00:00.000Z"),
    });
    assert.equal(r.ok, true);
    assert.equal(r.item.status, "rejected");
    assert.equal(r.item.reject_reason, "regression_risk_demo");
    assert.equal(r.item.auto, false);
    const kb = JSON.parse(
      readFileSync(join(repo, "development", "knowledge", "rejected_patterns.json"), "utf8")
    );
    assert.ok(
      kb.patterns.some(
        (p) =>
          p.reason === "regression_risk_demo" &&
          p.approval_id === enq.approval_id &&
          p.auto === false
      )
    );
  } finally {
    rmSync(repo, { recursive: true, force: true });
  }
});
