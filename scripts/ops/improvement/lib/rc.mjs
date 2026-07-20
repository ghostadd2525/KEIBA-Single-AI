/**
 * I-5 RC Gate — Canary Result を正本とし、Proposal から判定を推測しない。
 *
 * 必須 structural gates:
 * - canary_verdict_eligible (PASS | PASS_WITH_WARNING from Canary Result)
 * - human_review_approved
 * - evidence_refs_valid
 * - lifecycle_canary_pass
 *
 * 将来 KPI Regression gates は registry で拡張（デフォルト disabled）。
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { isCanaryRcEligible, loadProposal as loadCanaryProposal } from "./canary.mjs";
import {
  validateProposal,
  loadHumanReview,
} from "./proposals.mjs";
import {
  ProposalStatus,
  transitionProposal,
  canTransition,
} from "./lifecycle.mjs";

export const RcGatePhase = Object.freeze({
  STRUCTURAL: "structural",
  KPI_REGRESSION: "kpi_regression",
});

/** @type {ReadonlyArray<{ id: string, phase: string, severity: string, enabled: boolean, description: string }>} */
export const KPI_REGRESSION_GATE_REGISTRY = Object.freeze([
  {
    id: "kpi_hit_rate_non_regression",
    phase: RcGatePhase.KPI_REGRESSION,
    severity: "critical",
    enabled: false,
    description: "Future: hit_at_1 / hit rate vs baseline",
  },
  {
    id: "kpi_recovery_rate_non_regression",
    phase: RcGatePhase.KPI_REGRESSION,
    severity: "critical",
    enabled: false,
    description: "Future: recovery / ROI vs baseline",
  },
  {
    id: "kpi_calibration_non_regression",
    phase: RcGatePhase.KPI_REGRESSION,
    severity: "critical",
    enabled: false,
    description: "Future: calibration drift vs baseline",
  },
]);

export const STRUCTURAL_GATE_IDS = Object.freeze([
  "canary_verdict_eligible",
  "human_review_approved",
  "evidence_refs_valid",
  "lifecycle_canary_pass",
]);

function relDevPath(devRoot, absPath) {
  const norm = absPath.replace(/\\/g, "/");
  if (norm.includes("/development/")) {
    return norm.replace(/^.*?development\//, "development/");
  }
  const devNorm = String(devRoot).replace(/\\/g, "/").replace(/\/$/, "");
  if (norm.startsWith(`${devNorm}/`)) {
    return `development/${norm.slice(devNorm.length + 1)}`;
  }
  return norm;
}

function manifestIdFor(proposalId, runId) {
  return `RCM-${proposalId}-${runId}`;
}

/**
 * Load Canary Result from disk (authoritative). Never infer verdict from Proposal.
 * @param {string} devRoot
 * @param {string} proposalId
 * @param {string | null} [explicitRelPath]
 */
export function loadCanaryResult(devRoot, proposalId, explicitRelPath = null) {
  let absPath;
  if (explicitRelPath) {
    const norm = explicitRelPath.replace(/\\/g, "/");
    if (norm.startsWith("development/")) {
      absPath = join(devRoot, norm.slice("development/".length));
    } else {
      absPath = join(devRoot, "canary", "results", proposalId, "latest.json");
    }
  } else {
    absPath = join(devRoot, "canary", "results", proposalId, "latest.json");
  }

  if (!existsSync(absPath)) {
    throw new Error(`canary result not found for ${proposalId}`);
  }
  const result = JSON.parse(readFileSync(absPath, "utf8"));
  if (result.proposal_id !== proposalId) {
    throw new Error(
      `canary result proposal_id mismatch: expected ${proposalId}, got ${result.proposal_id}`
    );
  }
  return { result, path: absPath, rel: relDevPath(devRoot, absPath) };
}

/**
 * Validate evidence_refs structural + filesystem presence (+ optional corpus link).
 * @param {object} proposal
 * @param {object | null} scan
 * @param {string} repoRoot
 */
export function validateEvidenceRefsForRc(proposal, scan, repoRoot) {
  const structural = validateProposal(proposal);
  if (!structural.ok) {
    return {
      pass: false,
      message: structural.errors.join("; "),
      linked_count: 0,
    };
  }

  for (const ref of proposal.evidence_refs) {
    const abs = join(repoRoot, ref.path.replace(/^\//, ""));
    if (!existsSync(abs)) {
      return {
        pass: false,
        message: `missing evidence file: ${ref.path}`,
        linked_count: 0,
      };
    }
  }

  let linkedCount = proposal.evidence_refs.length;
  if (scan?.events?.length) {
    const paths = new Set(scan.events.map((e) => e.path));
    linkedCount = proposal.evidence_refs.filter((r) => paths.has(r.path)).length;
    if (linkedCount === 0) {
      return {
        pass: false,
        message: "evidence_refs do not link to scanned corpus",
        linked_count: 0,
      };
    }
  }

  return {
    pass: true,
    message: `refs=${proposal.evidence_refs.length} linked=${linkedCount}`,
    linked_count: linkedCount,
  };
}

/**
 * Evaluate RC gates. Canary Result is authoritative for canary verdict.
 * @param {{
 *   canaryResult: object,
 *   proposal: object,
 *   reviewDoc: object | null,
 *   scan?: object | null,
 *   repoRoot: string,
 *   kpiRegressionEnabled?: boolean,
 * }} ctx
 */
export function evaluateRcGates(ctx) {
  const { canaryResult, proposal, reviewDoc, scan, repoRoot } = ctx;
  const kpiEnabled = ctx.kpiRegressionEnabled === true;

  /** @type {Record<string, object>} */
  const gates = {};

  gates.canary_verdict_eligible = {
    pass:
      canaryResult.evaluation_status === "completed" &&
      isCanaryRcEligible(canaryResult.verdict),
    phase: RcGatePhase.STRUCTURAL,
    severity: "critical",
    enabled: true,
    message: `canary_result verdict=${canaryResult.verdict ?? "null"} status=${canaryResult.evaluation_status}`,
  };

  gates.human_review_approved = {
    pass: reviewDoc?.status === "approved",
    phase: RcGatePhase.STRUCTURAL,
    severity: "critical",
    enabled: true,
    message: `human_review=${reviewDoc?.status ?? "missing"}`,
  };

  const evidenceCheck = validateEvidenceRefsForRc(proposal, scan || null, repoRoot);
  gates.evidence_refs_valid = {
    pass: evidenceCheck.pass,
    phase: RcGatePhase.STRUCTURAL,
    severity: "critical",
    enabled: true,
    message: evidenceCheck.message,
  };

  gates.lifecycle_canary_pass = {
    pass: proposal.status === ProposalStatus.CANARY_PASS,
    phase: RcGatePhase.STRUCTURAL,
    severity: "critical",
    enabled: true,
    message: `proposal.status=${proposal.status}`,
  };

  for (const kpi of KPI_REGRESSION_GATE_REGISTRY) {
    const enabled = kpiEnabled && kpi.enabled;
    gates[kpi.id] = {
      pass: true,
      phase: RcGatePhase.KPI_REGRESSION,
      severity: kpi.severity,
      enabled,
      skipped: !enabled,
      message: enabled ? "not_implemented" : "kpi_regression_disabled",
    };
  }

  const rejectionReasons = [];
  for (const [id, g] of Object.entries(gates)) {
    if (g.skipped) continue;
    if (!g.enabled && g.phase === RcGatePhase.KPI_REGRESSION) continue;
    if (g.severity === "critical" && !g.pass) {
      rejectionReasons.push(`${id}: ${g.message}`);
    }
  }

  const rcEligible = rejectionReasons.length === 0;

  return {
    gates,
    rcEligible,
    rejectionReasons,
    gate_policy: {
      structural_required: [...STRUCTURAL_GATE_IDS],
      kpi_regression_enabled: kpiEnabled,
      kpi_gates: KPI_REGRESSION_GATE_REGISTRY.map((g) => g.id),
    },
  };
}

/**
 * @param {object} manifest
 */
export function validateRcManifest(manifest) {
  /** @type {string[]} */
  const errors = [];
  if (manifest?.schema_version !== "expect-rc-manifest/1.0") {
    errors.push("schema_version must be expect-rc-manifest/1.0");
  }
  if (!manifest?.manifest_id) errors.push("manifest_id required");
  if (!manifest?.proposal_id) errors.push("proposal_id required");
  if (!manifest?.result_id) errors.push("result_id required");
  if (!manifest?.refs?.canary_result_path) errors.push("refs.canary_result_path required");
  if (
    manifest?.manifest_id &&
    manifest?.proposal_id &&
    !String(manifest.manifest_id).includes(manifest.proposal_id)
  ) {
    errors.push("manifest_id must embed proposal_id");
  }
  if (
    manifest?.result_id &&
    manifest?.proposal_id &&
    !String(manifest.result_id).includes(manifest.proposal_id)
  ) {
    errors.push("result_id must match proposal_id trace");
  }
  return { ok: errors.length === 0, errors };
}

function buildRcManifest({
  proposalId,
  runId,
  canaryResult,
  canaryResultRel,
  proposalRel,
  reviewRel,
  gateEval,
  rcEligible,
  candidateRel,
  manifestRel,
}) {
  return {
    schema_version: "expect-rc-manifest/1.0",
    manifest_id: manifestIdFor(proposalId, runId),
    proposal_id: proposalId,
    result_id: canaryResult.result_id,
    run_id: runId,
    rc_eligible: rcEligible,
    canary_verdict: canaryResult.verdict,
    gates: gateEval.gates,
    gate_policy: gateEval.gate_policy,
    refs: {
      proposal_path: proposalRel,
      canary_result_path: canaryResultRel,
      human_review_path: reviewRel,
      candidate_path: candidateRel,
      manifest_path: manifestRel,
      links_path: candidateRel ? candidateRel.replace("candidate.json", "links.json") : null,
    },
    rejection_reasons: gateEval.rejectionReasons,
    created_at: new Date().toISOString(),
    metadata: {
      verdict_source: "canary_result_only",
      canary_result_schema: canaryResult.schema_version,
    },
  };
}

/**
 * Apply CANARY_PASS → RC_CREATED from successful RC emission.
 * @param {string} devRoot
 * @param {string} proposalId
 * @param {object} manifest
 */
export function applyLifecycleFromRc(devRoot, proposalId, manifest, opts = {}) {
  const { proposal, path: proposalPath } = loadCanaryProposal(devRoot, proposalId);
  if (!manifest.rc_eligible) {
    return { proposal, applied: false, reason: "rc_not_eligible" };
  }
  if (proposal.status !== ProposalStatus.CANARY_PASS) {
    return {
      proposal,
      applied: false,
      reason: `expected CANARY_PASS, got ${proposal.status}`,
    };
  }
  if (!canTransition(proposal.status, ProposalStatus.RC_CREATED)) {
    return { proposal, applied: false, reason: "illegal_transition" };
  }

  const by = opts.by || "improve:rc";
  const final = transitionProposal(proposal, ProposalStatus.RC_CREATED, {
    by,
    note: `RC created — manifest ${manifest.manifest_id} basis: canary_result ${manifest.result_id}`,
  });
  final.metadata = {
    ...(proposal.metadata || {}),
    latest_rc_manifest_id: manifest.manifest_id,
    latest_rc_manifest_path: manifest.refs?.manifest_path || null,
    latest_rc_candidate_path: manifest.refs?.candidate_path || null,
    latest_rc_created_at: manifest.created_at,
  };
  writeFileSync(proposalPath, JSON.stringify(final, null, 2) + "\n", "utf8");
  return { proposal: final, applied: true };
}

/**
 * Try emit RC for one proposal. Loads Canary Result from disk.
 * @param {{
 *   devRoot: string,
 *   repoRoot: string,
 *   proposalId: string,
 *   runId: string,
 *   canaryResultPath?: string | null,
 *   scan?: object | null,
 *   applyLifecycle?: boolean,
 *   by?: string,
 *   kpiRegressionEnabled?: boolean,
 * }} opts
 */
export function tryEmitReleaseCandidate(opts) {
  const {
    devRoot,
    repoRoot,
    proposalId,
    runId,
    canaryResultPath = null,
    scan = null,
    applyLifecycle = true,
    by = "improve:rc",
    kpiRegressionEnabled = false,
  } = opts;

  const { proposal, path: proposalPath } = loadCanaryProposal(devRoot, proposalId);
  const proposalRel = relDevPath(devRoot, proposalPath);

  let reviewDoc = null;
  let reviewRel = null;
  try {
    const loaded = loadHumanReview(devRoot, proposalId);
    reviewDoc = loaded.review;
    reviewRel = loaded.rel;
  } catch {
    reviewDoc = null;
  }

  const { result: canaryResult, rel: canaryResultRel } = loadCanaryResult(
    devRoot,
    proposalId,
    canaryResultPath
  );

  const gateEval = evaluateRcGates({
    canaryResult,
    proposal,
    reviewDoc,
    scan,
    repoRoot,
    kpiRegressionEnabled,
  });

  const rcRoot = join(devRoot, "release-candidates");
  mkdirSync(rcRoot, { recursive: true });
  const outDir = join(rcRoot, proposalId);

  if (!gateEval.rcEligible) {
    const manifest = buildRcManifest({
      proposalId,
      runId,
      canaryResult,
      canaryResultRel,
      proposalRel,
      reviewRel,
      gateEval,
      rcEligible: false,
      candidateRel: null,
      manifestRel: null,
    });
    const rejectDir = join(devRoot, "runs", runId, "rc-rejected");
    mkdirSync(rejectDir, { recursive: true });
    writeFileSync(
      join(rejectDir, `${proposalId}.json`),
      JSON.stringify(manifest, null, 2) + "\n",
      "utf8"
    );
    return {
      proposal_id: proposalId,
      status: "rejected",
      rc_eligible: false,
      rejection_reasons: gateEval.rejectionReasons,
      manifest,
      result_id: canaryResult.result_id,
      canary_result_path: canaryResultRel,
    };
  }

  if (existsSync(outDir)) {
    return {
      proposal_id: proposalId,
      status: "already_exists",
      rc_eligible: true,
      result_id: canaryResult.result_id,
      canary_result_path: canaryResultRel,
    };
  }

  mkdirSync(outDir, { recursive: true });

  const candidateRel = relDevPath(devRoot, join(outDir, "candidate.json"));
  const manifestRel = relDevPath(devRoot, join(outDir, "manifest.json"));

  const manifest = buildRcManifest({
    proposalId,
    runId,
    canaryResult,
    canaryResultRel,
    proposalRel,
    reviewRel,
    gateEval,
    rcEligible: true,
    candidateRel,
    manifestRel,
  });
  manifest.refs.manifest_path = manifestRel;
  manifest.refs.links_path = relDevPath(devRoot, join(outDir, "links.json"));

  const verdict = canaryResult.verdict;
  const candidate = {
    schema_version: "expect-release-candidate/1.0",
    proposal_id: proposalId,
    result_id: canaryResult.result_id,
    manifest_id: manifest.manifest_id,
    status: "pending_review",
    canary_verdict: verdict,
    canary_status: verdict === "PASS_WITH_WARNING" ? "pass_with_warning" : "pass",
    links: {
      proposal: proposalRel,
      canary_config: `development/canary/configs/${proposalId}.json`,
      canary_report: `development/canary/reports/${proposalId}.json`,
      canary_result: canaryResultRel,
      canary_criteria: `development/canary/criteria/${proposalId}.json`,
      manifest: manifestRel,
      human_review: reviewRel,
      analysis: (proposal.analysis_refs || []).map((r) =>
        typeof r === "string" ? r : r.path
      ),
    },
    gate_summary: {
      rc_eligible: true,
      structural_gates: STRUCTURAL_GATE_IDS.map((id) => ({
        id,
        pass: gateEval.gates[id]?.pass ?? false,
      })),
      kpi_regression_enabled: kpiRegressionEnabled,
    },
    risk_summary: "Residual risk until Human RC review and controlled deploy.",
    deploy_notes:
      verdict === "PASS_WITH_WARNING"
        ? "Canary PASS_WITH_WARNING — review warnings before deploy."
        : proposal.event_types?.includes("miss")
          ? "Prediction Core change allowed only after RC approval — not during canary."
          : "No Prediction Core change — supply/metadata/ops only.",
    created_at: new Date().toISOString(),
    reviewed_at: null,
    reviewed_by: null,
  };

  writeFileSync(join(outDir, "candidate.json"), JSON.stringify(candidate, null, 2) + "\n", "utf8");
  writeFileSync(join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n", "utf8");
  writeFileSync(
    join(outDir, "links.json"),
    JSON.stringify(
      {
        ...candidate.links,
        result_id: canaryResult.result_id,
        proposal_id: proposalId,
      },
      null,
      2
    ) + "\n",
    "utf8"
  );
  writeFileSync(
    join(outDir, "checklist.md"),
    `# Release Candidate — ${proposalId}

- [ ] Proposal reviewed (Human Review approved)
- [ ] Canary Result \`${canaryResult.result_id}\` — verdict **${verdict}**
- [ ] RC Manifest \`${manifest.manifest_id}\`
- [ ] Prediction Core unchanged until explicit deploy approval
- [ ] OPS-Monitor plan documented

**Decision:** pending_review
`,
    "utf8"
  );

  if (applyLifecycle) {
    applyLifecycleFromRc(devRoot, proposalId, manifest, { by });
  }

  return {
    proposal_id: proposalId,
    status: "created",
    rc_eligible: true,
    manifest_id: manifest.manifest_id,
    result_id: canaryResult.result_id,
    canary_result_path: canaryResultRel,
    manifest_path: manifestRel,
    manifest,
  };
}

/**
 * Batch RC emission (cycle). Each entry reloads Canary Result from disk.
 * @param {object[]} canaryOutcomes — runCanary output (uses result_path hint only)
 * @param {string} devRoot
 * @param {string} repoRoot
 * @param {string} runId
 * @param {object | null} [scan]
 */
export function emitReleaseCandidates(canaryOutcomes, devRoot, repoRoot, runId, scan = null) {
  /** @type {object[]} */
  const emitted = [];
  for (const cr of canaryOutcomes) {
    try {
      const outcome = tryEmitReleaseCandidate({
        devRoot,
        repoRoot,
        proposalId: cr.proposal_id,
        runId,
        canaryResultPath: cr.result_path || null,
        scan,
        applyLifecycle: true,
        by: "improve:cycle",
      });
      emitted.push(outcome);
    } catch (e) {
      emitted.push({
        proposal_id: cr.proposal_id,
        status: "error",
        error: String(e.message || e),
      });
    }
  }
  return emitted;
}

/**
 * Count RC directories (excluding _TEMPLATE).
 */
export function countReleaseCandidates(devRoot) {
  const rcRoot = join(devRoot, "release-candidates");
  if (!existsSync(rcRoot)) return 0;
  return readdirSync(rcRoot).filter((name) => {
    if (name.startsWith("_")) return false;
    return statSync(join(rcRoot, name)).isDirectory();
  }).length;
}
