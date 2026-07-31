/**
 * I-3 Proposal Generator — design docs only (no code artifacts).
 *
 * Rules enforced:
 *  - evidence_refs required (min 1)
 *  - analysis_refs structured (Analyzer output refs)
 *  - Analyzer confidence is advisory only — never sole accept/reject gate
 *  - Lifecycle starts at DRAFT; Human Review required for APPROVED+
 *  - metadata / additional fields allowed (forward compatible)
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import {
  ProposalStatus,
  withDraftLifecycle,
  transitionProposal,
  assertKnownStatus,
} from "./lifecycle.mjs";

const CORE_ELIGIBLE = new Set(["miss"]);

/** Confidence never gates creation or acceptance by itself. */
export const CONFIDENCE_POLICY = Object.freeze({
  role: "advisory_only",
  acceptance_requires: Object.freeze([
    "evidence_refs",
    "human_review",
    "lifecycle_transition",
  ]),
  note: "Analyzer confidence may inform review priority; it must not alone decide accept or reject.",
});

/**
 * Normalize analysis_refs entry (object preferred; legacy string path → object shell).
 * @param {unknown} ref
 * @param {{ event_type?: string, analysis_id?: string }} [fallback]
 */
export function normalizeAnalysisRef(ref, fallback = {}) {
  if (typeof ref === "string" && ref.trim()) {
    return {
      analysis_id: fallback.analysis_id || "legacy",
      event_type: fallback.event_type || "unknown",
      path: ref.trim(),
      root_cause: null,
      confidence: null,
      reason: null,
      schema_version: "expect-root-cause/1.0",
      legacy_string_path: true,
    };
  }
  if (!ref || typeof ref !== "object") {
    throw new Error("analysis_refs entry must be object or non-empty string path");
  }
  const o = /** @type {Record<string, unknown>} */ (ref);
  const analysis_id = String(o.analysis_id || fallback.analysis_id || "").trim();
  const event_type = String(o.event_type || fallback.event_type || "").trim();
  const path = String(o.path || "").trim();
  if (!analysis_id || !event_type || !path) {
    throw new Error("analysis_refs require analysis_id, event_type, and path");
  }
  const confidence =
    typeof o.confidence === "number" && o.confidence >= 0 && o.confidence <= 1
      ? o.confidence
      : null;
  return {
    analysis_id,
    event_type,
    path,
    root_cause: o.root_cause != null ? String(o.root_cause) : null,
    confidence,
    reason: o.reason != null ? String(o.reason) : null,
    schema_version: o.schema_version != null ? String(o.schema_version) : "expect-root-cause/1.0",
  };
}

/**
 * Build structured analysis_refs from Analyzer result.
 * @param {object} analysis
 * @param {string} eventType
 * @param {string} runId
 */
export function buildAnalysisRefs(analysis, eventType, runId) {
  const path = `development/analysis/${eventType}/${runId}.json`;
  return [
    normalizeAnalysisRef({
      analysis_id: analysis.analysis_id || `${eventType}-${runId}`,
      event_type: eventType,
      path,
      root_cause: analysis.root_cause ?? null,
      confidence: typeof analysis.confidence === "number" ? analysis.confidence : null,
      reason: analysis.reason ?? null,
      schema_version: analysis.schema_version || "expect-root-cause/1.0",
    }),
  ];
}

/**
 * Map index / analysis events → evidence_refs (required shape).
 * @param {object[]} events
 * @param {number} [limit]
 */
export function buildEvidenceRefs(events, limit = 50) {
  return (events || []).slice(0, limit).map((e) => ({
    event_id: e.event_id,
    event_type: e.event_type,
    path: e.path,
    race_date: e.race_date ?? null,
    race_id: e.race_id ?? null,
    fingerprint: e.fingerprint ?? null,
    cluster_id: e.cluster_id ?? null,
  }));
}

/**
 * Validate Proposal for I-3 enforcement.
 * Does NOT use analyzer confidence as accept/reject criterion.
 * @param {object} proposal
 * @returns {{ ok: boolean, errors: string[] }}
 */
export function validateProposal(proposal) {
  const errors = [];
  if (!proposal || typeof proposal !== "object") {
    return { ok: false, errors: ["proposal must be an object"] };
  }
  if (proposal.schema_version !== "expect-improvement-proposal/1.0") {
    errors.push("schema_version must be expect-improvement-proposal/1.0");
  }
  if (!proposal.proposal_id || !/^IMP-[0-9]{8}-[a-z0-9_]+-[0-9]{3}$/.test(proposal.proposal_id)) {
    errors.push("proposal_id must match IMP-YYYYMMDD-type-seq");
  }
  try {
    assertKnownStatus(proposal.status);
  } catch (e) {
    errors.push(String(e.message || e));
  }
  if (!Array.isArray(proposal.event_types) || proposal.event_types.length < 1) {
    errors.push("event_types required (min 1)");
  }
  if (!Array.isArray(proposal.evidence_refs) || proposal.evidence_refs.length < 1) {
    errors.push("evidence_refs required (min 1) — Proposal without Evidence is rejected");
  } else {
    proposal.evidence_refs.forEach((r, i) => {
      if (!r || !r.event_id || !r.event_type || !r.path) {
        errors.push(`evidence_refs[${i}] requires event_id, event_type, path`);
      }
    });
  }
  for (const key of ["purpose", "target", "expected_effect", "evaluation_method"]) {
    if (!proposal[key] || !String(proposal[key]).trim()) {
      errors.push(`${key} required`);
    }
  }
  if (!Array.isArray(proposal.side_effects) || proposal.side_effects.length < 1) {
    errors.push("side_effects required (min 1)");
  }
  if (Array.isArray(proposal.code_artifacts) && proposal.code_artifacts.length > 0) {
    errors.push("code_artifacts must be empty (no code generation)");
  }
  if (Array.isArray(proposal.analysis_refs)) {
    proposal.analysis_refs.forEach((r, i) => {
      try {
        normalizeAnalysisRef(r, {
          event_type: proposal.event_types?.[0],
          analysis_id: proposal.proposal_id,
        });
      } catch (e) {
        errors.push(`analysis_refs[${i}]: ${e.message || e}`);
      }
    });
  }
  if (proposal.lifecycle) {
    if (proposal.lifecycle.status && proposal.lifecycle.status !== proposal.status) {
      errors.push("lifecycle.status must match proposal.status");
    }
  }
  // Explicit non-rule: do not error on low/high confidence
  return { ok: errors.length === 0, errors };
}

/**
 * Assert validateProposal; throw on failure.
 * @param {object} proposal
 */
export function assertValidProposal(proposal) {
  const v = validateProposal(proposal);
  if (!v.ok) {
    throw new Error(`invalid proposal: ${v.errors.join("; ")}`);
  }
}

/**
 * @param {Record<string, object>} analyses
 * @param {object} index
 * @param {string} devRoot
 * @param {string} runId
 * @param {{
 *   eventTypes?: string[],
 *   fingerprint?: string | null,
 *   author?: string,
 * }} [options]
 */
export function createProposals(analyses, index, devRoot, runId, options = {}) {
  const proposalsDir = join(devRoot, "proposals");
  mkdirSync(proposalsDir, { recursive: true });

  /** @type {object[]} */
  const created = [];
  let seq = 1;

  const typeFilter = options.eventTypes
    ? new Set(options.eventTypes.map((t) => String(t)))
    : null;
  const fingerprint = options.fingerprint ? String(options.fingerprint) : null;
  const author = options.author || "improve:propose";

  for (const [eventType, analysis] of Object.entries(analyses)) {
    if (typeFilter && !typeFilter.has(eventType)) continue;
    if (!analysis || analysis.status === "unsupported") continue;
    if ((analysis.event_count || 0) === 0) continue;

    // Confidence is advisory — never skip creation based on confidence alone
    void analysis.confidence;

    let typeEvents = (index.events || []).filter((e) => e.event_type === eventType);
    if (fingerprint) {
      typeEvents = typeEvents.filter((e) => e.fingerprint === fingerprint);
    }

    // Prefer Analyzer evidence_refs when present (keeps fingerprint linkage)
    let evidence_refs = [];
    if (Array.isArray(analysis.evidence_refs) && analysis.evidence_refs.length) {
      evidence_refs = buildEvidenceRefs(
        fingerprint
          ? analysis.evidence_refs.filter((e) => e.fingerprint === fingerprint)
          : analysis.evidence_refs
      );
    }
    if (!evidence_refs.length) {
      evidence_refs = buildEvidenceRefs(typeEvents);
    }
    if (!evidence_refs.length) continue;

    const datePart = (index.filter_date || index.dates?.[0] || runId.slice(0, 10)).replace(
      /-/g,
      ""
    );
    const typeSlug = eventType.replace(/[^a-z0-9_]/gi, "").toLowerCase() || "evt";
    const proposalId = `IMP-${datePart}-${typeSlug}-${String(seq).padStart(3, "0")}`;
    seq += 1;

    const isCore = CORE_ELIGIBLE.has(eventType);
    const rec = analysis.recommendation || "";
    const analysis_refs = buildAnalysisRefs(analysis, eventType, runId);
    const fingerprints = [
      ...new Set(
        evidence_refs.map((e) => e.fingerprint).filter((f) => typeof f === "string" && f)
      ),
    ];

    /** @type {object} */
    let proposal = {
      schema_version: "expect-improvement-proposal/1.0",
      proposal_id: proposalId,
      status: ProposalStatus.DRAFT,
      event_types: [eventType],
      fingerprints,
      evidence_refs,
      purpose: buildPurpose(eventType, analysis),
      target: buildTarget(eventType, isCore),
      expected_effect: buildExpectedEffect(eventType, analysis),
      side_effects: buildSideEffects(eventType, isCore),
      evaluation_method: `Human review then Canary per development/canary/criteria/${proposalId}.json`,
      non_goals: [
        "Code generation in proposal",
        "Production Prediction Core change before Canary pass",
        "Accept or reject solely by Analyzer confidence",
      ],
      analysis_refs,
      metadata: {
        confidence_policy: CONFIDENCE_POLICY,
        analyzer_confidence:
          typeof analysis.confidence === "number" ? analysis.confidence : null,
        analyzer_root_cause: analysis.root_cause ?? null,
        analyzer_root_cause_family: analysis.root_cause_family ?? null,
        analyzer_root_cause_families: analysis.root_cause_families ?? null,
        analyzer_root_cause_scores: analysis.root_cause_scores ?? null,
        target_root_cause_family: analysis.root_cause_family ?? null,
        improvement_priority: analysis.improvement_priority ?? null,
        research_priority:
          Array.isArray(analysis.improvement_priority) &&
          analysis.improvement_priority[0]
            ? analysis.improvement_priority[0].priority
            : null,
        analyzer_status: analysis.status ?? null,
        review_priority_hint: priorityHint(analysis.confidence),
        analyzer_version: analysis.analyzer_version || null,
      },
      code_artifacts: [],
      run_id: runId,
      created_at: new Date().toISOString(),
      updated_at: null,
      author,
    };

    proposal = withDraftLifecycle(proposal, { by: author });
    assertValidProposal(proposal);

    const md = buildProposalMarkdown(proposal, analysis, rec);
    writeFileSync(join(proposalsDir, `${proposalId}.json`), JSON.stringify(proposal, null, 2) + "\n", "utf8");
    writeFileSync(join(proposalsDir, `${proposalId}.md`), md, "utf8");
    created.push(proposal);
  }

  return created;
}

/**
 * Advisory ranking hint only — never an acceptance decision.
 * @param {unknown} confidence
 */
function priorityHint(confidence) {
  if (typeof confidence !== "number") return "unspecified";
  if (confidence >= 0.8) return "high_review_attention";
  if (confidence >= 0.5) return "normal_review";
  return "low_confidence_needs_more_evidence";
}

function buildPurpose(eventType, analysis) {
  if (eventType === "miss") {
    return `Reduce ${analysis.findings?.dominant_category || "miss"} events (${analysis.event_count} in corpus) via ranking calibration design.`;
  }
  if (eventType === "feature_missing") {
    return `Reduce feature_missing events (${analysis.event_count}) via data supply and metadata design — not Core.`;
  }
  return `Address ${eventType} events (${analysis.event_count}) per operational analysis ${analysis.analysis_id}.`;
}

function buildTarget(eventType, isCore) {
  if (eventType === "feature_missing") {
    return "ETL/feature supply gates and fallback_reason/feature_source normalization — Prediction Core out of scope.";
  }
  if (isCore) {
    return "Top1 selection / calibration design — applicable only after Canary pass on non-feature-co-occurring races.";
  }
  return `${eventType} operational remediation — not Prediction Core.`;
}

function buildExpectedEffect(eventType, analysis) {
  if (eventType === "miss") {
    return "miss_top1 rate non-increasing; hit_at_1 non-decreasing vs baseline on canary set.";
  }
  if (eventType === "feature_missing") {
    return "feature_missing count decreasing vs baseline; mock_fallback feature rate non-increasing.";
  }
  return `Measurable reduction or stabilization of ${eventType} vs baseline.`;
}

function buildSideEffects(eventType, isCore) {
  const base = [
    "Proposal contains no executable code",
    "Analyzer confidence is advisory; Human Review decides acceptance",
  ];
  if (isCore) {
    base.push("Core calibration may shift explain/confidence tone");
    base.push("Must not apply on feature_missing co-occurring races");
  }
  if (eventType === "feature_missing") {
    base.push("Stricter gates may delay public open");
  }
  return base;
}

function buildProposalMarkdown(proposal, analysis, recommendation) {
  const conf =
    typeof analysis.confidence === "number" ? analysis.confidence.toFixed(3) : "—";
  const refs = (proposal.analysis_refs || [])
    .map((r) => {
      const n = normalizeAnalysisRef(r, { event_type: proposal.event_types[0] });
      return `- \`${n.analysis_id}\` (${n.event_type}) → \`${n.path}\` · root_cause=\`${n.root_cause || "—"}\` · confidence=${n.confidence ?? "—"} (advisory)`;
    })
    .join("\n");

  return `# Improvement Proposal — ${proposal.proposal_id}

> **コード生成禁止。** Human Review → Canary → RC → Deploy  
> Schema: \`expect-improvement-proposal/1.0\` · Lifecycle: \`${proposal.status}\`  
> **Confidence policy:** advisory only — never sole accept/reject criterion

| 項目 | 値 |
|------|-----|
| proposal_id | \`${proposal.proposal_id}\` |
| status | \`${proposal.status}\` |
| event_types | ${proposal.event_types.join(", ")} |
| evidence_refs | ${proposal.evidence_refs.length} |
| analysis_refs | ${(proposal.analysis_refs || []).length} |
| analyzer_confidence | ${conf} (advisory) |
| run_id | \`${proposal.run_id}\` |
| created_at | ${proposal.created_at} |

## 1. 目的（purpose）

${proposal.purpose}

## 2. 対象（target）

${proposal.target}

## 3. 期待効果（expected_effect）

${proposal.expected_effect}

## 4. 副作用（side_effects）

${proposal.side_effects.map((s) => `- ${s}`).join("\n")}

## 5. 評価方法（evaluation_method）

${proposal.evaluation_method}

## Evidence refs

${proposal.evidence_refs
  .slice(0, 20)
  .map((e) => `- \`${e.event_id}\` (${e.event_type}) → \`${e.path}\``)
  .join("\n")}
${proposal.evidence_refs.length > 20 ? `\n… and ${proposal.evidence_refs.length - 20} more` : ""}

## Analysis refs

${refs || "_none_"}

## Analyzer findings

\`\`\`json
${JSON.stringify(analysis.findings || {}, null, 2)}
\`\`\`

| field | value |
|-------|-------|
| root_cause | \`${analysis.root_cause}\` |
| confidence | ${conf} |
| reason | ${analysis.reason || "—"} |

## Recommendation

${recommendation}

## Human Review

Record approval in \`development/reviews/${proposal.proposal_id}.json\` (\`status=approved\`) before Canary runs.  
Do **not** approve or reject based solely on Analyzer confidence.

`;
}

/**
 * @param {string} devRoot
 * @param {string} proposalId
 */
export function isHumanReviewApproved(devRoot, proposalId) {
  const path = join(devRoot, "reviews", `${proposalId}.json`);
  if (!existsSync(path)) return false;
  try {
    const doc = JSON.parse(readFileSync(path, "utf8"));
    return doc.status === "approved";
  } catch {
    return false;
  }
}

/**
 * @param {string} devRoot
 * @param {string} proposalId
 */
export function loadHumanReview(devRoot, proposalId) {
  const path = join(devRoot, "reviews", `${proposalId}.json`);
  if (!existsSync(path)) {
    throw new Error(`human review not found: ${proposalId}`);
  }
  const review = JSON.parse(readFileSync(path, "utf8"));
  const rel = path.replace(/\\/g, "/").includes("/development/")
    ? path.replace(/\\/g, "/").replace(/^.*?development\//, "development/")
    : `development/reviews/${proposalId}.json`;
  return { review, path, rel };
}

/**
 * Load proposal JSON, apply lifecycle transition, persist.
 * Confidence is ignored for the transition decision.
 * @param {string} devRoot
 * @param {string} proposalId
 * @param {string} nextStatus
 * @param {{ by?: string, note?: string }} [meta]
 */
export function transitionStoredProposal(devRoot, proposalId, nextStatus, meta = {}) {
  const path = join(devRoot, "proposals", `${proposalId}.json`);
  if (!existsSync(path)) {
    throw new Error(`proposal not found: ${proposalId}`);
  }
  const proposal = JSON.parse(readFileSync(path, "utf8"));
  assertValidProposal(proposal);
  const next = transitionProposal(proposal, nextStatus, meta);
  assertValidProposal(next);
  writeFileSync(path, JSON.stringify(next, null, 2) + "\n", "utf8");
  return next;
}

export { transitionProposal, ProposalStatus };
