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
  validateProposal,
  normalizeAnalysisRef,
  buildAnalysisRefs,
  CONFIDENCE_POLICY,
  transitionStoredProposal,
} from "../../scripts/ops/improvement/lib/proposals.mjs";
import {
  canTransition,
  assertTransition,
  transitionProposal,
  ProposalStatus,
} from "../../scripts/ops/improvement/lib/lifecycle.mjs";

const PROPOSE_CLI = join(ROOT, "scripts/ops/improvement/propose-evidence.mjs");

function writeEvent(root, eventType, date, raceId, payload = {}, version = {}) {
  const dir = join(root, eventType, date);
  mkdirSync(dir, { recursive: true });
  const doc = {
    schema_version: "expect-improvement-evidence/1.0",
    event_type: eventType,
    event_id: `${eventType}:${raceId}:t1`,
    timestamp: "2026-07-19T12:00:00.000Z",
    race_id: raceId,
    race_date: date,
    fingerprint: `sha256:${eventType}${raceId}fp`,
    payload,
    version: { pipeline_version: "ops-result-automation/1.0", ...version },
  };
  writeFileSync(join(dir, `${raceId}.json`), JSON.stringify(doc, null, 2));
  return doc;
}

describe("I-3 Proposal contract & confidence policy", () => {
  it("confidence policy is advisory_only", () => {
    assert.equal(CONFIDENCE_POLICY.role, "advisory_only");
    assert.ok(CONFIDENCE_POLICY.acceptance_requires.includes("human_review"));
    assert.ok(!CONFIDENCE_POLICY.acceptance_requires.includes("confidence_threshold"));
  });

  it("normalizeAnalysisRef accepts structured and legacy string", () => {
    const obj = normalizeAnalysisRef({
      analysis_id: "miss-r1",
      event_type: "miss",
      path: "development/analysis/miss/r1.json",
      confidence: 0.9,
      root_cause: "ranking_near_miss_top1",
    });
    assert.equal(obj.analysis_id, "miss-r1");
    assert.equal(obj.confidence, 0.9);

    const legacy = normalizeAnalysisRef("development/analysis/miss/old.json", {
      event_type: "miss",
      analysis_id: "legacy-id",
    });
    assert.equal(legacy.path, "development/analysis/miss/old.json");
    assert.equal(legacy.legacy_string_path, true);
  });

  it("validateProposal rejects empty evidence_refs", () => {
    const bad = {
      schema_version: "expect-improvement-proposal/1.0",
      proposal_id: "IMP-20260719-miss-001",
      status: "DRAFT",
      event_types: ["miss"],
      evidence_refs: [],
      purpose: "x",
      target: "y",
      expected_effect: "z",
      side_effects: ["s"],
      evaluation_method: "e",
      created_at: new Date().toISOString(),
    };
    const v = validateProposal(bad);
    assert.equal(v.ok, false);
    assert.ok(v.errors.some((e) => e.includes("evidence_refs")));
  });

  it("validateProposal does not fail on low analyzer confidence in metadata", () => {
    const ok = {
      schema_version: "expect-improvement-proposal/1.0",
      proposal_id: "IMP-20260719-miss-001",
      status: "DRAFT",
      event_types: ["miss"],
      evidence_refs: [
        {
          event_id: "miss:r1:t1",
          event_type: "miss",
          path: "evidence/improvement/miss/2026-07-19/r1.json",
        },
      ],
      purpose: "p",
      target: "t",
      expected_effect: "e",
      side_effects: ["s"],
      evaluation_method: "m",
      analysis_refs: buildAnalysisRefs(
        {
          analysis_id: "miss-x",
          root_cause: "unclear",
          confidence: 0.1,
          reason: "low",
        },
        "miss",
        "run-x"
      ),
      metadata: {
        analyzer_confidence: 0.1,
        confidence_policy: CONFIDENCE_POLICY,
      },
      created_at: new Date().toISOString(),
      code_artifacts: [],
    };
    const v = validateProposal(ok);
    assert.equal(v.ok, true, v.errors.join("; "));
  });
});

describe("I-3 Lifecycle enforcement", () => {
  it("allows DRAFT → UNDER_REVIEW → APPROVED", () => {
    assert.equal(canTransition("DRAFT", "UNDER_REVIEW"), true);
    assert.equal(canTransition("UNDER_REVIEW", "APPROVED"), true);
    assert.equal(canTransition("DRAFT", "APPROVED"), false);
    assert.throws(() => assertTransition("DRAFT", "DEPLOYED"));
  });

  it("transitionProposal updates status without consulting confidence", () => {
    const proposal = {
      schema_version: "expect-improvement-proposal/1.0",
      proposal_id: "IMP-20260719-miss-001",
      status: "DRAFT",
      event_types: ["miss"],
      evidence_refs: [
        { event_id: "a", event_type: "miss", path: "p.json" },
      ],
      purpose: "p",
      target: "t",
      expected_effect: "e",
      side_effects: ["s"],
      evaluation_method: "m",
      metadata: { analyzer_confidence: 0.99 },
      created_at: new Date().toISOString(),
      code_artifacts: [],
      lifecycle: {
        schema_version: "expect-proposal-lifecycle/1.0",
        proposal_id: "IMP-20260719-miss-001",
        status: "DRAFT",
        previous_status: null,
        updated_at: new Date().toISOString(),
        history: [{ status: "DRAFT", at: new Date().toISOString() }],
      },
    };
    const next = transitionProposal(proposal, ProposalStatus.UNDER_REVIEW, {
      by: "test",
      note: "manual",
    });
    assert.equal(next.status, "UNDER_REVIEW");
    assert.equal(next.lifecycle.status, "UNDER_REVIEW");
    assert.equal(next.metadata.analyzer_confidence, 0.99);
  });
});

describe("I-3 Proposal Generator", () => {
  it("createProposals writes DRAFT with evidence_refs and analysis_refs", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i3-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i3-dev-"));
    writeEvent(evidence, "miss", "2026-07-19", "r1", {
      miss_category: "miss_top1",
      confidence: 90,
    });
    writeEvent(evidence, "feature_missing", "2026-07-19", "r2", {
      fallback_reason: "feature_missing",
    });

    const scan = scanEvidence(evidence);
    const index = buildIndex(scan, dev, "2026-07-19");
    const analyses = runAnalyzers(scan, dev, "run-i3");
    const proposals = createProposals(analyses, index, dev, "run-i3");

    assert.ok(proposals.length >= 2);
    for (const p of proposals) {
      assert.equal(p.status, "DRAFT");
      assert.ok(p.evidence_refs.length >= 1);
      assert.ok(Array.isArray(p.analysis_refs) && p.analysis_refs.length >= 1);
      assert.equal(typeof p.analysis_refs[0].analysis_id, "string");
      assert.equal(typeof p.analysis_refs[0].path, "string");
      assert.equal(p.metadata.confidence_policy.role, "advisory_only");
      assert.equal(p.lifecycle.status, "DRAFT");
      assert.equal(validateProposal(p).ok, true);
      assert.ok(existsSync(join(dev, "proposals", `${p.proposal_id}.json`)));
      assert.ok(existsSync(join(dev, "proposals", `${p.proposal_id}.md`)));
    }

    // Low confidence still produces a proposal (not gated)
    const lowDev = mkdtempSync(join(tmpdir(), "i3-low-"));
    const lowAnalyses = {
      miss: {
        ...analyses.miss,
        confidence: 0.05,
        root_cause: "miss_distribution_unclear",
        reason: "sparse",
        evidence_refs: analyses.miss.evidence_refs,
        event_count: analyses.miss.event_count,
        status: "ok",
        analysis_id: "miss-low",
      },
    };
    const low = createProposals(lowAnalyses, index, lowDev, "run-low", {
      eventTypes: ["miss"],
    });
    assert.equal(low.length, 1);
    assert.equal(low[0].metadata.analyzer_confidence, 0.05);

    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
    rmSync(lowDev, { recursive: true, force: true });
  });

  it("transitionStoredProposal enforces legal transitions", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i3-tr-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i3-tr-dev-"));
    writeEvent(evidence, "miss", "2026-07-19", "r1", { miss_category: "miss_top1" });
    const scan = scanEvidence(evidence);
    const index = buildIndex(scan, dev, "2026-07-19");
    const analyses = runAnalyzers(scan, dev, "run-tr");
    const [p] = createProposals(analyses, index, dev, "run-tr", { eventTypes: ["miss"] });
    const under = transitionStoredProposal(dev, p.proposal_id, "UNDER_REVIEW", {
      by: "reviewer",
    });
    assert.equal(under.status, "UNDER_REVIEW");
    assert.throws(() =>
      transitionStoredProposal(dev, p.proposal_id, "DEPLOYED", { by: "x" })
    );
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("CLI improve:propose exits 0 and enforces evidence_refs", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i3-cli-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i3-cli-dev-"));
    writeEvent(evidence, "miss", "2026-07-19", "r1", { miss_category: "miss_top1" });

    const r = spawnSync(
      process.execPath,
      [
        PROPOSE_CLI,
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
    assert.equal(out.phase, "I-3");
    assert.ok(out.proposal_count >= 1);
    assert.equal(out.confidence_policy.role, "advisory_only");
    assert.ok(out.validations.every((v) => v.ok));

    const id = out.proposal_ids[0];
    const doc = JSON.parse(readFileSync(join(dev, "proposals", `${id}.json`), "utf8"));
    assert.ok(doc.evidence_refs.length >= 1);
    assert.ok(doc.analysis_refs[0].analysis_id);
    assert.equal(doc.status, "DRAFT");

    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });

  it("CLI empty corpus creates zero proposals", () => {
    const evidence = mkdtempSync(join(tmpdir(), "i3-empty-ev-"));
    const dev = mkdtempSync(join(tmpdir(), "i3-empty-dev-"));
    const r = spawnSync(
      process.execPath,
      [PROPOSE_CLI, "--evidence-root", evidence, "--dev-root", dev],
      { encoding: "utf8" }
    );
    assert.equal(r.status, 0, r.stderr || r.stdout);
    const out = JSON.parse(r.stdout);
    assert.equal(out.proposal_count, 0);
    assert.equal(out.corpus_status, "empty");
    rmSync(evidence, { recursive: true, force: true });
    rmSync(dev, { recursive: true, force: true });
  });
});
