import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ROOT } from "../helpers/load.mjs";
import { scanEvidence } from "../../scripts/ops/improvement/lib/scan.mjs";
import { buildIndex } from "../../scripts/ops/improvement/lib/index.mjs";
import {
  canTransition,
  createLifecycle,
  transitionLifecycle,
  ProposalStatus,
} from "../../scripts/ops/improvement/lib/lifecycle.mjs";

const INDEX_CLI = join(ROOT, "scripts/ops/improvement/index-evidence.mjs");

function writeEvent(root, eventType, date, raceId, payload = {}) {
  const dir = join(root, eventType, date);
  mkdirSync(dir, { recursive: true });
  const doc = {
    schema_version: "expect-improvement-evidence/1.0",
    event_type: eventType,
    event_id: `${eventType}:${raceId}:t1`,
    timestamp: "2026-07-19T12:00:00.000Z",
    race_id: raceId,
    race_date: date,
    fingerprint: `sha256:${eventType}fp01abcdef`,
    payload,
    version: { pipeline_version: "ops-result-automation/1.0" },
  };
  writeFileSync(join(dir, `${raceId}.json`), JSON.stringify(doc, null, 2));
  return doc;
}

describe("I-1 Evidence Index", () => {
  it("empty corpus writes empty index", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i1-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i1-dev-"));
    const scan = scanEvidence(evidence);
    const index = buildIndex(scan, dev, null);
    assert.equal(index.corpus_status, "empty");
    assert.equal(index.event_total, 0);
    assert.ok(existsSync(join(dev, "index", "latest.json")));
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("populated corpus writes by-date / by-event-type / clusters", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i1-ev2-"));
    const dev = mkdtempSync(join(tmpdir(), "i1-dev2-"));
    writeEvent(evidence, "miss", "2026-07-19", "r1", { miss_category: "miss_top1" });
    writeEvent(evidence, "feature_missing", "2026-07-19", "r2", {
      fallback_reason: "feature_missing",
    });

    const scan = scanEvidence(evidence, "2026-07-19");
    assert.equal(scan.total, 2);
    const index = buildIndex(scan, dev, "2026-07-19");
    assert.equal(index.event_total, 2);
    assert.equal(index.corpus_status, "populated");
    assert.ok(existsSync(join(dev, "index", "by-date", "2026-07-19.json")));
    assert.ok(existsSync(join(dev, "index", "by-event-type", "miss.json")));
    assert.ok(existsSync(join(dev, "index", "by-event-type", "feature_missing.json")));
    assert.ok(index.clusters.length >= 1);
    const clusterFile = join(dev, "index", "clusters", `${index.clusters[0].cluster_id}.json`);
    assert.ok(existsSync(clusterFile));

    // Event refs are Proposal-traceable
    for (const ev of index.events) {
      assert.ok(ev.event_id);
      assert.ok(ev.path.startsWith("evidence/improvement/"));
    }
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("CLI improve:index exits 0 and prints summary", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i1-cli-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i1-cli-dev-"));
    writeEvent(evidence, "miss", "2026-07-19", "r1", { miss_category: "miss_top1" });

    const r = spawnSync(
      process.execPath,
      [
        INDEX_CLI,
        "--evidence-root",
        evidence,
        "--dev-root",
        dev,
        "--date",
        "2026-07-19",
      ],
      { encoding: "utf8" }
    );
    assert.equal(r.status, 0, r.stderr || r.stdout);
    const out = JSON.parse(r.stdout);
    assert.equal(out.phase, "I-1");
    assert.equal(out.evidence_count, 1);
    assert.equal(out.corpus_status, "populated");
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});

describe("I-1 Proposal Lifecycle scaffold", () => {
  it("allows DRAFT → UNDER_REVIEW → APPROVED → CANARY_RUNNING", () => {
    assert.equal(canTransition(ProposalStatus.DRAFT, ProposalStatus.UNDER_REVIEW), true);
    assert.equal(canTransition(ProposalStatus.UNDER_REVIEW, ProposalStatus.APPROVED), true);
    assert.equal(canTransition(ProposalStatus.APPROVED, ProposalStatus.CANARY_RUNNING), true);
    assert.equal(canTransition(ProposalStatus.DRAFT, ProposalStatus.DEPLOYED), false);
  });

  it("transitionLifecycle records history", () => {
    let lc = createLifecycle(ProposalStatus.DRAFT, { by: "system" });
    lc = transitionLifecycle(lc, ProposalStatus.UNDER_REVIEW, { by: "reviewer" });
    assert.equal(lc.status, ProposalStatus.UNDER_REVIEW);
    assert.equal(lc.previous_status, ProposalStatus.DRAFT);
    assert.equal(lc.history.length, 2);
  });
});
