import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { scanEvidence } from "../../scripts/ops/improvement/lib/scan.mjs";
import { ROOT } from "../helpers/load.mjs";

const RUNNER = join(ROOT, "scripts/ops/improvement/run-cycle.mjs");

function writeMissEvidence(root, date, raceId) {
  const dir = join(root, "miss", date);
  mkdirSync(dir, { recursive: true });
  const doc = {
    schema_version: "expect-improvement-evidence/1.0",
    event_type: "miss",
    event_id: `miss:${raceId}:t1`,
    timestamp: "2026-07-19T12:00:00.000Z",
    race_id: raceId,
    race_date: date,
    fingerprint: "sha256:testmiss",
    payload: {
      miss_category: "miss_top1",
      confidence: 85,
      engine_source: "real_ai",
      winner: { horse_number: 2 },
    },
    version: { pipeline_version: "ops-result-automation/1.0" },
  };
  writeFileSync(join(dir, `${raceId}.json`), JSON.stringify(doc, null, 2));
}

describe("AI-Core Operational Cycle", () => {
  it("scanEvidence returns 0 for empty tree", () => {
    const tmp = mkdtempSync(join(tmpdir(), "imp-empty-"));
    const r = scanEvidence(tmp);
    assert.equal(r.total, 0);
    rmSync(tmp, { recursive: true, force: true });
  });

  it("0 evidence → No Improvement Required, no proposals created in run dir", () => {
    const evidence = mkdtempSync(join(tmpdir(), "imp-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "imp-dev-"));
    mkdirSync(join(dev, "proposals"), { recursive: true });

    const r = spawnSync(process.execPath, [RUNNER, "--evidence-root", evidence], {
      cwd: ROOT,
      encoding: "utf8",
      env: { ...process.env },
    });
    assert.equal(r.status, 0, r.stderr || r.stdout);
    const out = JSON.parse(r.stdout);
    assert.equal(out.verdict, "No Improvement Required");
    assert.equal(out.evidence_count, 0);
    assert.equal(out.proposal_count, 0);
    assert.deepEqual(out.canary, []);
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("with evidence → proposals and canary pending review", () => {
    const evidence = mkdtempSync(join(tmpdir(), "imp-ev2-"));
    writeMissEvidence(evidence, "2026-07-19", "2026-07-19-04-11");

    const r = spawnSync(
      process.execPath,
      [RUNNER, "--evidence-root", evidence, "--date", "2026-07-19"],
      { cwd: ROOT, encoding: "utf8" }
    );
    assert.equal(r.status, 0, r.stderr || r.stdout);
    const out = JSON.parse(r.stdout);
    assert.equal(out.evidence_count, 1);
    assert.ok(out.proposal_count >= 1);
    assert.ok(out.proposal_ids[0].startsWith("IMP-"));
    assert.equal(out.canary[0].status, "pending_human_review");
    assert.equal(out.release_candidate_new.length, 0);
    rmSync(evidence, { recursive: true, force: true });
  });
});
