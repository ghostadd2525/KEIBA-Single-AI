import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ROOT } from "../helpers/load.mjs";
import { scanEvidence } from "../../scripts/ops/improvement/lib/scan.mjs";
import { buildIndex } from "../../scripts/ops/improvement/lib/index.mjs";
import { runAnalyzers } from "../../scripts/ops/improvement/lib/analyzers.mjs";
import {
  createProposals,
  transitionStoredProposal,
  isHumanReviewApproved,
} from "../../scripts/ops/improvement/lib/proposals.mjs";
import { ProposalStatus } from "../../scripts/ops/improvement/lib/lifecycle.mjs";
import {
  CanaryVerdict,
  evaluateCanaryGates,
  runCanaryForProposal,
  validateCanaryResult,
  isCanaryRcEligible,
  writeCanaryArtifacts,
} from "../../scripts/ops/improvement/lib/canary.mjs";
import { tryEmitReleaseCandidate } from "../../scripts/ops/improvement/lib/rc.mjs";

const CANARY_CLI = join(ROOT, "scripts/ops/improvement/canary-evidence.mjs");

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
    fingerprint: `sha256:${eventType}${raceId}`,
    payload,
    version: { pipeline_version: "ops-result-automation/1.0" },
  };
  const rel = `evidence/improvement/${eventType}/${date}/${raceId}.json`;
  writeFileSync(join(dir, `${raceId}.json`), JSON.stringify(doc, null, 2));
  return { doc, rel };
}

function approveReview(devRoot, proposalId) {
  const reviewsDir = join(devRoot, "reviews");
  mkdirSync(reviewsDir, { recursive: true });
  writeFileSync(
    join(reviewsDir, `${proposalId}.json`),
    JSON.stringify(
      {
        schema_version: "expect-human-review/1.0",
        proposal_id: proposalId,
        status: "approved",
        reviewed_at: new Date().toISOString(),
        reviewed_by: "test-reviewer",
      },
      null,
      2
    ) + "\n",
    "utf8"
  );
}

function seedProposal(evidence, dev, opts = {}) {
  writeEvent(evidence, "miss", "2026-07-19", "r1", {
    miss_category: "miss_top1",
    confidence: 90,
  });
  const scan = scanEvidence(evidence, "2026-07-19");
  const index = buildIndex(scan, dev, "2026-07-19");
  const analyses = runAnalyzers(scan, dev, "run-i4");
  const [proposal] = createProposals(analyses, index, dev, "run-i4", { eventTypes: ["miss"] });
  if (opts.stripAnalysisRefs) {
    proposal.analysis_refs = [];
    writeFileSync(
      join(dev, "proposals", `${proposal.proposal_id}.json`),
      JSON.stringify(proposal, null, 2) + "\n",
      "utf8"
    );
  }
  if (opts.badEvidenceRefs) {
    proposal.evidence_refs = [
      {
        event_id: "miss:ghost:t1",
        event_type: "miss",
        path: "evidence/improvement/miss/2026-07-19/ghost.json",
      },
    ];
    writeFileSync(
      join(dev, "proposals", `${proposal.proposal_id}.json`),
      JSON.stringify(proposal, null, 2) + "\n",
      "utf8"
    );
  }
  return { proposal, scan, index };
}

describe("I-4 Canary verdicts & RC eligibility", () => {
  it("supports PASS, PASS_WITH_WARNING, FAIL and RC eligibility", () => {
    assert.equal(isCanaryRcEligible(CanaryVerdict.PASS), true);
    assert.equal(isCanaryRcEligible(CanaryVerdict.PASS_WITH_WARNING), true);
    assert.equal(isCanaryRcEligible(CanaryVerdict.FAIL), false);
    assert.equal(isCanaryRcEligible(null), false);
  });

  it("evaluateCanaryGates derives three verdict states", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i4-gates-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i4-gates-dev-"));
    const { proposal, scan } = seedProposal(evidence, dev);
    const typeEvents = scan.events.filter((e) => e.event_type === "miss");
    const artifacts = writeCanaryArtifacts(proposal, buildIndex(scan, dev), dev);

    const pass = evaluateCanaryGates(proposal, typeEvents, artifacts.criteria);
    assert.equal(pass.verdict, CanaryVerdict.PASS);

    const warnProposal = { ...proposal, analysis_refs: [] };
    const warn = evaluateCanaryGates(warnProposal, typeEvents, artifacts.criteria);
    assert.equal(warn.verdict, CanaryVerdict.PASS_WITH_WARNING);

    const failProposal = {
      ...proposal,
      evidence_refs: [{ event_id: "x", event_type: "miss", path: "evidence/improvement/miss/2026-07-19/none.json" }],
    };
    const fail = evaluateCanaryGates(failProposal, typeEvents, artifacts.criteria);
    assert.equal(fail.verdict, CanaryVerdict.FAIL);
    assert.equal(fail.rollback_triggered, true);

    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});

describe("I-4 Canary Result artifact", () => {
  it("writes independent result with proposal_id mutual trace", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i4-res-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i4-res-dev-"));
    const { proposal, scan, index } = seedProposal(evidence, dev);
    const id = proposal.proposal_id;

    transitionStoredProposal(dev, id, ProposalStatus.UNDER_REVIEW, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.APPROVED, { by: "test" });
    approveReview(dev, id);
    assert.equal(isHumanReviewApproved(dev, id), true);

    const before = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    const contentSnapshot = {
      purpose: before.purpose,
      target: before.target,
      evidence_refs: before.evidence_refs,
      expected_effect: before.expected_effect,
    };

    const outcome = runCanaryForProposal(proposal, index, scan, dev, "run-i4-test", {
      isApproved: () => true,
      applyLifecycle: true,
      by: "test",
    });

    assert.equal(outcome.verdict, CanaryVerdict.PASS);
    assert.equal(outcome.proposal_id, id);
    assert.ok(outcome.result_id.includes(id));
    assert.ok(existsSync(join(dev, "canary", "results", id, "latest.json")));
    assert.ok(existsSync(join(dev, "canary", "results", id, "run-i4-test.json")));

    const result = JSON.parse(readFileSync(join(dev, "canary", "results", id, "latest.json"), "utf8"));
    const v = validateCanaryResult(result);
    assert.equal(v.ok, true, v.errors.join("; "));
    assert.equal(result.proposal_id, id);
    assert.equal(result.refs.proposal_path, `development/proposals/${id}.json`);
    assert.equal(result.lifecycle_applied?.basis, "canary_result");
    assert.equal(result.lifecycle_applied?.to_status, ProposalStatus.CANARY_PASS);

    const after = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    assert.equal(after.status, ProposalStatus.CANARY_PASS);
    assert.equal(after.purpose, contentSnapshot.purpose);
    assert.equal(after.target, contentSnapshot.target);
    assert.deepEqual(after.evidence_refs, contentSnapshot.evidence_refs);
    assert.equal(after.expected_effect, contentSnapshot.expected_effect);
    assert.equal(after.metadata.latest_canary_result_id, outcome.result_id);
    assert.ok(after.metadata.latest_canary_verdict === CanaryVerdict.PASS);

    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("FAIL sets CANARY_FAIL without mutating proposal body", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i4-fail-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i4-fail-dev-"));
    const { proposal, scan, index } = seedProposal(evidence, dev, { badEvidenceRefs: true });
    const id = proposal.proposal_id;
    const stored = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    transitionStoredProposal(dev, id, ProposalStatus.UNDER_REVIEW, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.APPROVED, { by: "test" });
    approveReview(dev, id);

    const outcome = runCanaryForProposal(stored, index, scan, dev, "run-fail", {
      isApproved: () => true,
    });
    assert.equal(outcome.verdict, CanaryVerdict.FAIL);
    assert.equal(outcome.pass, false);

    const after = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    assert.equal(after.status, ProposalStatus.CANARY_FAIL);
    assert.equal(after.purpose, stored.purpose);

    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("pending_human_review when review not approved", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i4-pend-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i4-pend-dev-"));
    const { proposal, scan, index } = seedProposal(evidence, dev);
    const id = proposal.proposal_id;

    const outcome = runCanaryForProposal(proposal, index, scan, dev, "run-pend", {
      isApproved: () => false,
      applyLifecycle: true,
    });
    assert.equal(outcome.status, "pending_human_review");
    assert.equal(outcome.verdict, null);

    const after = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    assert.equal(after.status, ProposalStatus.DRAFT);

    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("PASS_WITH_WARNING passes RC structural gates (I-5)", () => {
    const repo = mkdtempSync(join(tmpdir(), "i4-warn-repo-"));
    const evidence = join(repo, "evidence", "improvement");
    mkdirSync(evidence, { recursive: true });
    const dev = mkdtempSync(join(tmpdir(), "i4-warn-dev-"));
    const { proposal, scan, index } = seedProposal(evidence, dev, { stripAnalysisRefs: true });
    const id = proposal.proposal_id;
    const stored = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    transitionStoredProposal(dev, id, ProposalStatus.UNDER_REVIEW, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.APPROVED, { by: "test" });
    approveReview(dev, id);

    const outcome = runCanaryForProposal(stored, index, scan, dev, "run-warn", {
      isApproved: () => true,
    });
    assert.equal(outcome.verdict, CanaryVerdict.PASS_WITH_WARNING);
    assert.equal(outcome.pass, true);

    const rc = tryEmitReleaseCandidate({
      devRoot: dev,
      repoRoot: repo,
      proposalId: id,
      runId: "run-warn-rc",
      canaryResultPath: outcome.result_path,
      scan,
    });
    assert.equal(rc.status, "created");
    const candidate = JSON.parse(
      readFileSync(join(dev, "release-candidates", id, "candidate.json"), "utf8")
    );
    assert.equal(candidate.canary_verdict, CanaryVerdict.PASS_WITH_WARNING);
    assert.equal(candidate.canary_status, "pass_with_warning");
    assert.equal(candidate.result_id, outcome.result_id);
    assert.ok(candidate.links.canary_result.includes("canary/results"));
    assert.ok(existsSync(join(dev, "release-candidates", id, "manifest.json")));

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});

describe("I-4 Canary CLI", () => {
  it("improve:canary exits 0 and writes canary summary", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i4-cli-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i4-cli-dev-"));
    const { proposal } = seedProposal(evidence, dev);
    const id = proposal.proposal_id;
    transitionStoredProposal(dev, id, ProposalStatus.UNDER_REVIEW, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.APPROVED, { by: "test" });
    approveReview(dev, id);

    const r = spawnSync(
      process.execPath,
      [
        CANARY_CLI,
        "--proposal",
        id,
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
    assert.equal(out.phase, "I-4");
    assert.equal(out.proposal_id, id);
    assert.equal(out.verdict, CanaryVerdict.PASS);
    assert.equal(out.rc_eligible, true);
    assert.ok(existsSync(join(dev, "canary", "results", id, "latest.json")));

    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("requires --proposal", () => {
    const r = spawnSync(process.execPath, [CANARY_CLI], { encoding: "utf8" });
    assert.notEqual(r.status, 0);
  });
});
