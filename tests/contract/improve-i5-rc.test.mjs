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
  loadHumanReview,
} from "../../scripts/ops/improvement/lib/proposals.mjs";
import { ProposalStatus } from "../../scripts/ops/improvement/lib/lifecycle.mjs";
import {
  runCanaryForProposal,
  CanaryVerdict,
} from "../../scripts/ops/improvement/lib/canary.mjs";
import {
  evaluateRcGates,
  tryEmitReleaseCandidate,
  validateRcManifest,
  loadCanaryResult,
  STRUCTURAL_GATE_IDS,
  KPI_REGRESSION_GATE_REGISTRY,
  validateEvidenceRefsForRc,
} from "../../scripts/ops/improvement/lib/rc.mjs";

const RC_CLI = join(ROOT, "scripts/ops/improvement/rc-evidence.mjs");

function writeEvent(evidenceRoot, eventType, date, raceId, payload = {}) {
  const dir = join(evidenceRoot, eventType, date);
  mkdirSync(dir, { recursive: true });
  writeFileSync(
    join(dir, `${raceId}.json`),
    JSON.stringify(
      {
        schema_version: "expect-improvement-evidence/1.0",
        event_type: eventType,
        event_id: `${eventType}:${raceId}:t1`,
        timestamp: "2026-07-19T12:00:00.000Z",
        race_id: raceId,
        race_date: date,
        fingerprint: `sha256:${eventType}${raceId}`,
        payload,
        version: { pipeline_version: "ops-result-automation/1.0" },
      },
      null,
      2
    )
  );
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

function seedRcReady(opts = {}) {
  const repo = mkdtempSync(join(tmpdir(), "i5-repo-"));
  const evidence = join(repo, "evidence", "improvement");
  mkdirSync(evidence, { recursive: true });
  const dev = mkdtempSync(join(tmpdir(), "i5-dev-"));
  writeEvent(evidence, "miss", "2026-07-19", "r1", { miss_category: "miss_top1" });
  const scan = scanEvidence(evidence, "2026-07-19");
  const index = buildIndex(scan, dev, "2026-07-19");
  const analyses = runAnalyzers(scan, dev, "run-i5");
  const [proposal] = createProposals(analyses, index, dev, "run-i5", { eventTypes: ["miss"] });
  const id = proposal.proposal_id;

  if (!opts.skipApproval) {
    transitionStoredProposal(dev, id, ProposalStatus.UNDER_REVIEW, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.APPROVED, { by: "test" });
    approveReview(dev, id);
  }

  let canaryOutcome = null;
  if (!opts.skipCanary) {
    const stored = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    canaryOutcome = runCanaryForProposal(stored, index, scan, dev, "run-i5-canary", {
      isApproved: () => !opts.skipApproval,
      applyLifecycle: !opts.skipCanaryLifecycle,
    });
  }

  return { repo, dev, evidence, scan, index, proposal, id, canaryOutcome };
}

describe("I-5 RC Gate structural requirements", () => {
  it("defines four mandatory structural gates", () => {
    assert.deepEqual(STRUCTURAL_GATE_IDS, [
      "canary_verdict_eligible",
      "human_review_approved",
      "evidence_refs_valid",
      "lifecycle_canary_pass",
    ]);
  });

  it("evaluateRcGates passes when all structural gates satisfied", () => {
    const { repo, dev, scan, id, canaryOutcome } = seedRcReady();
    const { result } = loadCanaryResult(dev, id);
    const proposal = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    const { review } = loadHumanReview(dev, id);

    const evalOut = evaluateRcGates({
      canaryResult: result,
      proposal,
      reviewDoc: review,
      scan,
      repoRoot: repo,
    });
    assert.equal(evalOut.rcEligible, true);
    assert.equal(evalOut.rejectionReasons.length, 0);
    for (const gateId of STRUCTURAL_GATE_IDS) {
      assert.equal(evalOut.gates[gateId].pass, true, gateId);
    }

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
    void canaryOutcome;
  });

  it("rejects when Human Review not approved", () => {
    const { repo, dev, scan, id } = seedRcReady({ skipApproval: true, skipCanary: true });
    transitionStoredProposal(dev, id, ProposalStatus.UNDER_REVIEW, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.APPROVED, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.CANARY_RUNNING, { by: "test" });
    transitionStoredProposal(dev, id, ProposalStatus.CANARY_PASS, { by: "test" });

    const resultsDir = join(dev, "canary", "results", id);
    mkdirSync(resultsDir, { recursive: true });
    const canaryDoc = {
      schema_version: "expect-canary-result/1.0",
      result_id: `CAN-${id}-test`,
      proposal_id: id,
      run_id: "test",
      verdict: CanaryVerdict.PASS,
      evaluation_status: "completed",
      gates: {},
      refs: { proposal_path: `development/proposals/${id}.json` },
      evaluated_at: new Date().toISOString(),
    };
    writeFileSync(join(resultsDir, "latest.json"), JSON.stringify(canaryDoc, null, 2) + "\n");

    const proposal = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    const { result } = loadCanaryResult(dev, id);

    const evalOut = evaluateRcGates({
      canaryResult: result,
      proposal,
      reviewDoc: null,
      scan,
      repoRoot: repo,
    });
    assert.equal(evalOut.rcEligible, false);
    assert.equal(evalOut.gates.human_review_approved.pass, false);

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("rejects when lifecycle is not CANARY_PASS", () => {
    const { repo, dev, scan, id } = seedRcReady({ skipCanary: true });
    approveReview(dev, id);
    const proposal = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    assert.equal(proposal.status, ProposalStatus.APPROVED);

    const fakeResult = {
      schema_version: "expect-canary-result/1.0",
      result_id: `CAN-${id}-fake`,
      proposal_id: id,
      run_id: "fake",
      verdict: CanaryVerdict.PASS,
      evaluation_status: "completed",
    };

    const evalOut = evaluateRcGates({
      canaryResult: fakeResult,
      proposal,
      reviewDoc: { status: "approved" },
      scan,
      repoRoot: repo,
    });
    assert.equal(evalOut.gates.lifecycle_canary_pass.pass, false);
    assert.equal(evalOut.rcEligible, false);

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("uses Canary Result verdict — not Proposal metadata", () => {
    const { repo, dev, scan, id } = seedRcReady();
    const proposal = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    proposal.metadata.latest_canary_verdict = CanaryVerdict.PASS;
    const { result } = loadCanaryResult(dev, id);
    result.verdict = CanaryVerdict.FAIL;
    result.evaluation_status = "completed";

    const evalOut = evaluateRcGates({
      canaryResult: result,
      proposal,
      reviewDoc: { status: "approved" },
      scan,
      repoRoot: repo,
    });
    assert.equal(evalOut.gates.canary_verdict_eligible.pass, false);

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});

describe("I-5 KPI regression extensibility", () => {
  it("KPI gates are registered but disabled by default", () => {
    assert.ok(KPI_REGRESSION_GATE_REGISTRY.length >= 3);
    assert.ok(KPI_REGRESSION_GATE_REGISTRY.every((g) => g.enabled === false));
  });

  it("disabled KPI gates do not block RC eligibility", () => {
    const { repo, dev, scan, id } = seedRcReady();
    const { result } = loadCanaryResult(dev, id);
    const proposal = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    const evalOut = evaluateRcGates({
      canaryResult: result,
      proposal,
      reviewDoc: { status: "approved" },
      scan,
      repoRoot: repo,
      kpiRegressionEnabled: false,
    });
    assert.equal(evalOut.rcEligible, true);
    assert.equal(evalOut.gate_policy.kpi_regression_enabled, false);
    for (const kpi of KPI_REGRESSION_GATE_REGISTRY) {
      assert.equal(evalOut.gates[kpi.id].skipped, true);
    }

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});

describe("I-5 RC Manifest & emission", () => {
  it("creates RC package with manifest cross-refs", () => {
    const { repo, dev, scan, id, canaryOutcome } = seedRcReady();
    const outcome = tryEmitReleaseCandidate({
      devRoot: dev,
      repoRoot: repo,
      proposalId: id,
      runId: "run-i5-rc",
      canaryResultPath: canaryOutcome.result_path,
      scan,
    });

    assert.equal(outcome.status, "created");
    assert.ok(outcome.manifest_id.includes(id));
    assert.equal(outcome.result_id, canaryOutcome.result_id);

    const manifest = JSON.parse(
      readFileSync(join(dev, "release-candidates", id, "manifest.json"), "utf8")
    );
    const v = validateRcManifest(manifest);
    assert.equal(v.ok, true, v.errors.join("; "));
    assert.equal(manifest.proposal_id, id);
    assert.equal(manifest.result_id, canaryOutcome.result_id);
    assert.equal(manifest.refs.canary_result_path, outcome.canary_result_path);
    assert.equal(manifest.metadata.verdict_source, "canary_result_only");

    const candidate = JSON.parse(
      readFileSync(join(dev, "release-candidates", id, "candidate.json"), "utf8")
    );
    assert.equal(candidate.result_id, canaryOutcome.result_id);
    assert.equal(candidate.manifest_id, manifest.manifest_id);
    assert.equal(candidate.links.manifest, manifest.refs.manifest_path);

    const after = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    assert.equal(after.status, ProposalStatus.RC_CREATED);
    assert.equal(after.metadata.latest_rc_manifest_id, manifest.manifest_id);

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("rejects RC when evidence_refs invalid on disk", () => {
    const { repo, dev, scan, id, canaryOutcome } = seedRcReady();
    const proposal = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    proposal.evidence_refs = [
      {
        event_id: "miss:ghost:t1",
        event_type: "miss",
        path: "evidence/improvement/miss/2026-07-19/ghost.json",
      },
    ];
    writeFileSync(join(dev, "proposals", `${id}.json`), JSON.stringify(proposal, null, 2) + "\n");

    const evidenceCheck = validateEvidenceRefsForRc(proposal, scan, repo);
    assert.equal(evidenceCheck.pass, false);

    const outcome = tryEmitReleaseCandidate({
      devRoot: dev,
      repoRoot: repo,
      proposalId: id,
      runId: "run-i5-reject",
      canaryResultPath: canaryOutcome.result_path,
      scan,
    });
    assert.equal(outcome.status, "rejected");
    assert.ok(outcome.rejection_reasons.some((r) => r.includes("evidence_refs_valid")));

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("loadCanaryResultRc reads from disk path", () => {
    const { repo, dev, id, canaryOutcome } = seedRcReady();
    const loaded = loadCanaryResult(dev, id, canaryOutcome.result_path);
    assert.equal(loaded.result.proposal_id, id);
    assert.ok(loaded.result.result_id);

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});

describe("I-5 RC CLI", () => {
  it("improve:rc exits 0 when gates pass", () => {
    const { repo, dev, id } = seedRcReady();
    const r = spawnSync(
      process.execPath,
      [
        RC_CLI,
        "--proposal",
        id,
        "--evidence-root",
        join(repo, "evidence", "improvement"),
        "--dev-root",
        dev,
        "--date",
        "2026-07-19",
      ],
      { encoding: "utf8" }
    );
    assert.equal(r.status, 0, r.stderr || r.stdout);
    const out = JSON.parse(r.stdout);
    assert.equal(out.phase, "I-5");
    assert.equal(out.status, "created");
    assert.equal(out.rc_eligible, true);

    rmSync(repo, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("requires --proposal", () => {
    const r = spawnSync(process.execPath, [RC_CLI], { encoding: "utf8" });
    assert.notEqual(r.status, 0);
  });
});
