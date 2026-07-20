/**
 * I-4 Canary — Proposal 入力 → 独立 Canary Result 出力。
 *
 * - verdict: PASS | PASS_WITH_WARNING | FAIL
 * - Lifecycle は Result を根拠に Proposal status/lifecycle のみ更新（本文は不変）
 * - Config / Criteria / Report（要約）も生成
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import {
  ProposalStatus,
  transitionProposal,
  canTransition,
} from "./lifecycle.mjs";
import { isHumanReviewApproved } from "./proposals.mjs";

export const CanaryVerdict = Object.freeze({
  PASS: "PASS",
  PASS_WITH_WARNING: "PASS_WITH_WARNING",
  FAIL: "FAIL",
});

/** RC 出力可（I-5）— PASS と PASS_WITH_WARNING */
export function isCanaryRcEligible(verdict) {
  return verdict === CanaryVerdict.PASS || verdict === CanaryVerdict.PASS_WITH_WARNING;
}

/**
 * @param {string} devRoot
 * @param {string} proposalId
 */
export function loadProposal(devRoot, proposalId) {
  const path = join(devRoot, "proposals", `${proposalId}.json`);
  if (!existsSync(path)) {
    throw new Error(`proposal not found: ${proposalId}`);
  }
  return { proposal: JSON.parse(readFileSync(path, "utf8")), path };
}

function resultIdFor(proposalId, runId) {
  return `CAN-${proposalId}-${runId}`;
}

function relPath(devRoot, absPath) {
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

/**
 * @param {object} proposal
 * @param {object} index
 * @param {string} devRoot
 */
export function writeCanaryArtifacts(proposal, index, devRoot) {
  const id = proposal.proposal_id;
  const eventType = proposal.event_types[0];
  const configsDir = join(devRoot, "canary", "configs");
  const criteriaDir = join(devRoot, "canary", "criteria");
  mkdirSync(configsDir, { recursive: true });
  mkdirSync(criteriaDir, { recursive: true });

  const config = buildConfig(id, eventType, index, proposal);
  const criteria = buildCriteria(id, eventType, proposal);

  const configPath = join(configsDir, `${id}.json`);
  const criteriaPath = join(criteriaDir, `${id}.json`);
  writeFileSync(configPath, JSON.stringify(config, null, 2) + "\n", "utf8");
  writeFileSync(criteriaPath, JSON.stringify(criteria, null, 2) + "\n", "utf8");

  return {
    config,
    criteria,
    configPath,
    criteriaPath,
    configRel: relPath(devRoot, configPath),
    criteriaRel: relPath(devRoot, criteriaPath),
  };
}

function buildConfig(proposalId, eventType, index, proposal) {
  return {
    schema_version: "expect-canary-config/1.0",
    proposal_id: proposalId,
    baseline: {
      description: "Evidence corpus baseline from Proposal evidence_refs / index",
      evidence_dates: index.dates || [],
      metrics_snapshot: index.counts_by_event_type || {},
      evidence_ref_count: (proposal.evidence_refs || []).length,
    },
    scope: {
      event_types: proposal.event_types || [eventType],
      race_dates: index.dates || [],
      fingerprints: proposal.fingerprints || [],
    },
    forbidden: [
      "production_core_mutation",
      "live_db_write",
      "disable_ops_monitor",
      "skip_human_review",
    ],
    created_at: new Date().toISOString(),
  };
}

function buildCriteria(proposalId, eventType, proposal) {
  const successGates = [
    { id: "corpus_documented", rule: "Baseline events captured from evidence", severity: "critical" },
    { id: "no_core_change_in_canary", rule: "No Core mutation during canary phase", severity: "critical" },
    {
      id: "proposal_evidence_linked",
      rule: "Proposal evidence_refs align with evaluated corpus",
      severity: "critical",
    },
    {
      id: "analysis_refs_present",
      rule: "Proposal cites Analyzer output via analysis_refs",
      severity: "warning",
    },
  ];

  if (eventType === "miss") {
    successGates.push({
      id: "miss_categories_enumerated",
      rule: "Miss categories present in evidence payload",
      severity: "critical",
    });
  }
  if (eventType === "feature_missing") {
    successGates.push({
      id: "feature_signals_present",
      rule: "feature_missing payloads include fallback_reason or feature_source",
      severity: "warning",
    });
  }

  return {
    schema_version: "expect-canary-criteria/1.0",
    proposal_id: proposalId,
    success: {
      description: "Offline structural canary on evidence baseline (Development only)",
      gates: successGates,
    },
    rollback: {
      description: "Critical gate failure → FAIL; warning-only → PASS_WITH_WARNING",
      triggers: [
        { id: "critical_gate_fail", rule: "Any critical gate false", action: "fail_canary" },
        { id: "warning_gate_fail", rule: "Warning gate false with critical pass", action: "pass_with_warning" },
      ],
    },
  };
}

/**
 * Evaluate gates and derive verdict.
 * @param {object} proposal
 * @param {object[]} typeEvents
 * @param {object} criteria
 */
export function evaluateCanaryGates(proposal, typeEvents, criteria) {
  const eventType = proposal.event_types[0];
  /** @type {Record<string, { pass: boolean, severity: string, message: string }>} */
  const gates = {};

  gates.corpus_documented = {
    pass: typeEvents.length > 0,
    severity: "critical",
    message: `events=${typeEvents.length}`,
  };
  gates.no_core_change_in_canary = {
    pass: true,
    severity: "critical",
    message: "offline evaluation — Core unchanged",
  };

  const evidencePaths = new Set(typeEvents.map((e) => e.path));
  const linked = (proposal.evidence_refs || []).filter((r) => evidencePaths.has(r.path));
  gates.proposal_evidence_linked = {
    pass: linked.length > 0 || typeEvents.length === 0,
    severity: "critical",
    message: `linked_refs=${linked.length}/${(proposal.evidence_refs || []).length}`,
  };

  gates.analysis_refs_present = {
    pass: Array.isArray(proposal.analysis_refs) && proposal.analysis_refs.length > 0,
    severity: "warning",
    message: `analysis_refs=${(proposal.analysis_refs || []).length}`,
  };

  if (eventType === "miss") {
    const cats = {};
    for (const ev of typeEvents) {
      const c = ev.payload?.miss_category || "unknown";
      cats[c] = (cats[c] || 0) + 1;
    }
    gates.miss_categories_enumerated = {
      pass: Object.keys(cats).length > 0,
      severity: "critical",
      message: `categories=${Object.keys(cats).join(",") || "none"}`,
    };
  }

  if (eventType === "feature_missing") {
    gates.feature_signals_present = {
      pass: typeEvents.some((e) => e.payload?.fallback_reason || e.payload?.feature_source),
      severity: "warning",
      message: "fallback_reason or feature_source in payload",
    };
  }

  const criticalFail = Object.values(gates).some((g) => g.severity === "critical" && !g.pass);
  const warningFail = Object.values(gates).some((g) => g.severity === "warning" && !g.pass);

  let verdict;
  const warnings = [];
  if (criticalFail) {
    verdict = CanaryVerdict.FAIL;
    warnings.push("One or more critical gates failed");
  } else if (warningFail) {
    verdict = CanaryVerdict.PASS_WITH_WARNING;
    for (const [id, g] of Object.entries(gates)) {
      if (g.severity === "warning" && !g.pass) warnings.push(`warning gate failed: ${id}`);
    }
  } else {
    verdict = CanaryVerdict.PASS;
  }

  return {
    verdict,
    gates,
    warnings,
    rollback_triggered: verdict === CanaryVerdict.FAIL,
    metrics: {
      baseline_event_count: typeEvents.length,
      linked_evidence_refs: linked.length,
    },
    criteria,
  };
}

/**
 * Build Canary Result document.
 */
export function buildCanaryResult({
  proposal,
  proposalPath,
  runId,
  verdict,
  gates,
  warnings,
  metrics,
  rollback_triggered,
  refs,
  evaluation_status,
  lifecycle_applied,
  notes,
}) {
  const proposalId = proposal.proposal_id;
  return {
    schema_version: "expect-canary-result/1.0",
    result_id: resultIdFor(proposalId, runId),
    proposal_id: proposalId,
    run_id: runId,
    verdict,
    evaluation_status: evaluation_status || "completed",
    gates,
    warnings: warnings || [],
    metrics: metrics || {},
    rollback_triggered: !!rollback_triggered,
    refs,
    lifecycle_applied: lifecycle_applied || null,
    evaluated_at: evaluation_status === "completed" ? new Date().toISOString() : null,
    notes: notes || [],
    metadata: {
      event_types: proposal.event_types,
      confidence_policy: "canary_verdict_from_gates_not_analyzer_confidence",
    },
  };
}

export function validateCanaryResult(result) {
  /** @type {string[]} */
  const errors = [];
  if (result?.schema_version !== "expect-canary-result/1.0") {
    errors.push("schema_version must be expect-canary-result/1.0");
  }
  if (!result?.result_id) errors.push("result_id required");
  if (!result?.proposal_id) errors.push("proposal_id required");
  if (!result?.run_id) errors.push("run_id required");
  if (!result?.refs?.proposal_path) errors.push("refs.proposal_path required");
  const verdictOk =
    result?.verdict === null ||
    Object.values(CanaryVerdict).includes(result?.verdict);
  if (!verdictOk) errors.push("verdict must be PASS | PASS_WITH_WARNING | FAIL | null");
  if (result?.evaluation_status === "completed" && !result?.verdict) {
    errors.push("completed evaluation requires verdict");
  }
  if (
    result?.result_id &&
    result?.proposal_id &&
    !String(result.result_id).includes(result.proposal_id)
  ) {
    errors.push("result_id must embed proposal_id for mutual trace");
  }
  return { ok: errors.length === 0, errors };
}

/**
 * Persist Canary Result + legacy report summary.
 * @param {object} result
 * @param {string} devRoot
 */
export function writeCanaryResult(result, devRoot) {
  const proposalId = result.proposal_id;
  const resultsDir = join(devRoot, "canary", "results", proposalId);
  mkdirSync(resultsDir, { recursive: true });

  const resultPath = join(resultsDir, `${result.run_id}.json`);
  const latestPath = join(resultsDir, "latest.json");
  writeFileSync(resultPath, JSON.stringify(result, null, 2) + "\n", "utf8");
  writeFileSync(latestPath, JSON.stringify(result, null, 2) + "\n", "utf8");

  const reportPath = join(devRoot, "canary", "reports", `${proposalId}.json`);
  mkdirSync(join(devRoot, "canary", "reports"), { recursive: true });
  const legacyStatus =
    result.verdict === CanaryVerdict.PASS
      ? "pass"
      : result.verdict === CanaryVerdict.PASS_WITH_WARNING
        ? "pass_with_warning"
        : result.verdict === CanaryVerdict.FAIL
          ? "fail"
          : "pending";

  writeFileSync(
    reportPath,
    JSON.stringify(
      {
        schema_version: "expect-canary-report/1.0",
        proposal_id: proposalId,
        status: legacyStatus,
        verdict: result.verdict,
        result_id: result.result_id,
        canary_result_path: relPath(devRoot, latestPath),
        metrics_delta: result.metrics,
        side_effects: [],
        gates: Object.fromEntries(Object.entries(result.gates).map(([k, v]) => [k, v.pass])),
        evidence_sample: result.refs?.evidence_sample || [],
        rollback_triggered: result.rollback_triggered,
        evaluated_at: result.evaluated_at,
        notes: (result.notes || []).join(" "),
        warnings: result.warnings,
      },
      null,
      2
    ) + "\n",
    "utf8"
  );

  return {
    resultPath,
    latestPath,
    reportPath,
    resultRel: relPath(devRoot, latestPath),
  };
}

/**
 * Apply Lifecycle transitions from Canary Result. Mutates only status/lifecycle/metadata canary pointers.
 * @param {string} devRoot
 * @param {object} result
 * @param {{ by?: string, skipIfPending?: boolean }} [opts]
 */
export function applyLifecycleFromCanaryResult(devRoot, result, opts = {}) {
  const { proposal, path: proposalPath } = loadProposal(devRoot, result.proposal_id);
  if (result.evaluation_status !== "completed" || !result.verdict) {
    return { proposal, applied: false, reason: "no_completed_verdict" };
  }

  const by = opts.by || "improve:canary";
  /** @type {{ from: string, to: string, at: string, note: string }[]} */
  const transitions = [];
  let next = { ...proposal };

  const targetStatus =
    result.verdict === CanaryVerdict.FAIL
      ? ProposalStatus.CANARY_FAIL
      : ProposalStatus.CANARY_PASS;

  if (next.status === ProposalStatus.APPROVED && canTransition(next.status, ProposalStatus.CANARY_RUNNING)) {
    const mid = transitionProposal(next, ProposalStatus.CANARY_RUNNING, {
      by,
      note: `Canary started — result ${result.result_id}`,
    });
    transitions.push({
      from: ProposalStatus.APPROVED,
      to: ProposalStatus.CANARY_RUNNING,
      at: mid.lifecycle.updated_at,
      note: mid.lifecycle.note,
    });
    next = mid;
  }

  if (!canTransition(next.status, targetStatus)) {
    return {
      proposal: next,
      applied: false,
      reason: `illegal transition ${next.status} -> ${targetStatus}`,
    };
  }

  const final = transitionProposal(next, targetStatus, {
    by,
    note: `Canary ${result.verdict} — basis: ${result.result_id}`,
  });
  transitions.push({
    from: next.status,
    to: targetStatus,
    at: final.lifecycle.updated_at,
    note: final.lifecycle.note,
  });

  final.metadata = {
    ...(proposal.metadata || {}),
    latest_canary_result_id: result.result_id,
    latest_canary_result_path: result.refs?.canary_result_path || null,
    latest_canary_verdict: result.verdict,
    latest_canary_evaluated_at: result.evaluated_at,
  };

  writeFileSync(proposalPath, JSON.stringify(final, null, 2) + "\n", "utf8");

  result.lifecycle_applied = {
    from_status: proposal.status,
    to_status: final.status,
    transitions,
    basis: "canary_result",
  };

  return { proposal: final, applied: true, transitions };
}

/**
 * Run canary for one Proposal.
 * @param {object} proposal
 * @param {object} index
 * @param {object} scanResult
 * @param {string} devRoot
 * @param {string} runId
 * @param {{ isApproved?: (id: string) => boolean, applyLifecycle?: boolean, by?: string }} [opts]
 */
export function runCanaryForProposal(proposal, index, scanResult, devRoot, runId, opts = {}) {
  const isApproved = opts.isApproved || ((id) => isHumanReviewApproved(devRoot, id));
  const applyLifecycle = opts.applyLifecycle !== false;
  const id = proposal.proposal_id;
  const proposalPath = join(devRoot, "proposals", `${id}.json`);
  const eventType = proposal.event_types[0];
  const typeEvents = scanResult.events.filter((e) => e.event_type === eventType);

  const artifacts = writeCanaryArtifacts(proposal, index, devRoot);

  if (!isApproved(id)) {
    const result = buildCanaryResult({
      proposal,
      proposalPath,
      runId,
      verdict: null,
      gates: {},
      warnings: [],
      metrics: {},
      rollback_triggered: false,
      refs: {
        proposal_path: relPath(devRoot, proposalPath),
        config_path: artifacts.configRel,
        criteria_path: artifacts.criteriaRel,
        evidence_sample: [],
      },
      evaluation_status: "pending_human_review",
      notes: [`Canary skipped until development/reviews/${id}.json status=approved`],
    });
    const paths = writeCanaryResult(result, devRoot);
    result.refs.canary_result_path = paths.resultRel;
    writeFileSync(paths.latestPath, JSON.stringify(result, null, 2) + "\n", "utf8");
    return {
      proposal_id: id,
      result_id: result.result_id,
      verdict: null,
      status: "pending_human_review",
      pass: false,
      result_path: paths.resultRel,
      result,
    };
  }

  const evalOut = evaluateCanaryGates(proposal, typeEvents, artifacts.criteria);
  let result = buildCanaryResult({
    proposal,
    proposalPath,
    runId,
    verdict: evalOut.verdict,
    gates: evalOut.gates,
    warnings: evalOut.warnings,
    metrics: evalOut.metrics,
    rollback_triggered: evalOut.rollback_triggered,
    refs: {
      proposal_path: relPath(devRoot, proposalPath),
      config_path: artifacts.configRel,
      criteria_path: artifacts.criteriaRel,
      evidence_sample: typeEvents.slice(0, 5).map((e) => e.path),
    },
    evaluation_status: "completed",
    notes: [
      evalOut.verdict === CanaryVerdict.PASS
        ? "Offline canary PASS on evidence baseline."
        : evalOut.verdict === CanaryVerdict.PASS_WITH_WARNING
          ? "Offline canary PASS_WITH_WARNING — review warnings before RC."
          : "Canary FAIL — revise proposal.",
    ],
  });

  const paths = writeCanaryResult(result, devRoot);
  result.refs.canary_result_path = paths.resultRel;
  writeFileSync(paths.latestPath, JSON.stringify(result, null, 2) + "\n", "utf8");

  if (applyLifecycle) {
    const lc = applyLifecycleFromCanaryResult(devRoot, result, { by: opts.by || "improve:canary" });
    if (lc.applied) {
      writeFileSync(paths.latestPath, JSON.stringify(result, null, 2) + "\n", "utf8");
      writeFileSync(paths.resultPath, JSON.stringify(result, null, 2) + "\n", "utf8");
    }
  }

  return {
    proposal_id: id,
    result_id: result.result_id,
    verdict: result.verdict,
    status: result.evaluation_status,
    pass: isCanaryRcEligible(result.verdict),
    result_path: paths.resultRel,
    lifecycle_applied: result.lifecycle_applied,
    result,
  };
}

/**
 * Batch canary (cycle).
 * @param {object[]} proposals
 * @param {object} index
 * @param {object} scanResult
 * @param {string} devRoot
 * @param {(id: string) => boolean} isApproved
 */
export function runCanary(proposals, index, scanResult, devRoot, isApproved, runId) {
  const rid = runId || new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "Z";
  return proposals.map((p) =>
    runCanaryForProposal(p, index, scanResult, devRoot, rid, { isApproved, applyLifecycle: true })
  );
}
