import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  publishOpsSnapshot,
  nextRunIsoJst,
} from "../../scripts/ops/v8/publish-ops-snapshot.mjs";

function setupRepo() {
  const repo = mkdtempSync(join(tmpdir(), "v881-pub-"));
  mkdirSync(join(repo, "development", "knowledge"), { recursive: true });
  mkdirSync(join(repo, "development", "scheduler"), { recursive: true });
  mkdirSync(join(repo, "development", "approvals", "pending"), { recursive: true });
  mkdirSync(join(repo, "development", "weekly", "2026-W30", "reports"), { recursive: true });
  mkdirSync(join(repo, "public", "ops-data"), { recursive: true });

  writeFileSync(
    join(repo, "development", "knowledge", "accepted_patterns.json"),
    JSON.stringify({ patterns: [{ id: "a1" }], updated_at: "2026-07-20T00:00:00.000Z" }, null, 2)
  );
  writeFileSync(
    join(repo, "development", "knowledge", "rejected_patterns.json"),
    JSON.stringify({ patterns: [], updated_at: "2026-07-20T00:00:00.000Z" }, null, 2)
  );
  writeFileSync(
    join(repo, "development", "scheduler", "weekly-runner.json"),
    JSON.stringify(
      {
        week_id: "2026-W30",
        baseline_lock: "Version8.5",
        current_phase: null,
        last_run_at: "2026-07-26T13:34:13.966Z",
        next_run_jst: null,
        recovery_active: false,
        success_count: 1,
        failure_count: 0,
        skip_count: 0,
        updated_at: "2026-07-26T13:34:13.966Z",
      },
      null,
      2
    )
  );
  writeFileSync(
    join(repo, "development", "weekly", "2026-W30", "reports", "weekly-ops-report.json"),
    JSON.stringify(
      {
        week_id: "2026-W30",
        decision: "no_improvement",
        baseline_health_check: "OK",
      },
      null,
      2
    )
  );
  return repo;
}

test("nextRunIsoJst returns concrete +09:00 ISO, not fixed label", () => {
  const iso = nextRunIsoJst(new Date("2026-07-26T12:00:00+09:00"));
  assert.match(iso, /^\d{4}-\d{2}-\d{2}T03:00:00\+09:00$/);
  assert.doesNotMatch(iso, /毎日/);
});

test("publishOpsSnapshot writes all ops-data files from development artifacts", () => {
  const repo = setupRepo();
  try {
    const now = new Date("2026-07-26T12:00:00+09:00");
    const result = publishOpsSnapshot({ repo, now });
    assert.equal(result.ok, true);

    const files = [
      "knowledge.json",
      "reports.json",
      "research-scheduler.json",
      "approval-queue.json",
      "deploy.json",
      "portal-snapshot.json",
    ];
    for (const f of files) {
      assert.equal(existsSync(join(repo, "public", "ops-data", f)), true, f);
    }

    const portal = JSON.parse(
      readFileSync(join(repo, "public", "ops-data", "portal-snapshot.json"), "utf8")
    );
    assert.equal(portal.publish_layer, "8.8.1");
    assert.equal(portal.production_auto_apply, false);
    assert.equal(portal.research.week_id, "2026-W30");
    assert.equal(portal.research.next_run, "2026-07-27T03:00:00+09:00");
    assert.equal(portal.research.recovery, "idle");
    assert.equal(portal.knowledge.accepted_patterns, "1");
    assert.equal(portal.reports.weekly_report, "2026-W30");
    assert.equal(portal.approval.pending, 0);

    const sched = JSON.parse(
      readFileSync(join(repo, "public", "ops-data", "research-scheduler.json"), "utf8")
    );
    assert.equal(sched.next_run, "2026-07-27T03:00:00+09:00");
    assert.notEqual(sched.next_run, "毎日 03:00 JST");
  } finally {
    rmSync(repo, { recursive: true, force: true });
  }
});

test("empty development yields null fields (UI No Data), not fixed stubs", () => {
  const repo = mkdtempSync(join(tmpdir(), "v881-empty-"));
  try {
    mkdirSync(join(repo, "public", "ops-data"), { recursive: true });
    mkdirSync(join(repo, "development"), { recursive: true });
    const result = publishOpsSnapshot({
      repo,
      now: new Date("2026-07-26T12:00:00+09:00"),
    });
    assert.equal(result.ok, true);
    const portal = JSON.parse(
      readFileSync(join(repo, "public", "ops-data", "portal-snapshot.json"), "utf8")
    );
    assert.equal(portal.research.week_id, null);
    assert.equal(portal.research.next_run, null);
    assert.equal(portal.research.recovery, null);
    assert.equal(portal.knowledge.knowledge_score, null);
    assert.equal(portal.reports.weekly_report, null);
    assert.equal(portal.deploy.deploy_note, null);
  } finally {
    rmSync(repo, { recursive: true, force: true });
  }
});
