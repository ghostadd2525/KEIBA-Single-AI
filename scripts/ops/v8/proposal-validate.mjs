/**
 * Version8.2 — Proposal Validation (Research only).
 *
 * Dimensions (0..1):
 *   expected_impact, risk, confidence, coverage, cost
 *
 * Validation Score (proposed):
 *   score = (Impact × Confidence × Coverage) / (Risk × (1 + Cost))
 *   ε floor on Risk to avoid divide-by-zero
 *
 * Canary Entry Gate: score >= GATE_THRESHOLD and not hard-blocked by similarity.
 * PE / CE / AI Core untouched.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { IMPACT_WEIGHT } from "./root-cause-score.mjs";
import {
  loadKnowledgeBase,
  similaritySearch,
  computeKnowledgeScore,
} from "./knowledge-base.mjs";
import { repoRoot, weekIdJst } from "./calendar.mjs";

/** Minimum Validation Score to enter Canary (Research heuristic). */
export const GATE_THRESHOLD = 0.12;

/** Risk floor so denominator never collapses. */
export const RISK_EPSILON = 0.08;

/** Cost by family — implementation blast radius (0=tiny .. 1=large). */
export const COST_BY_FAMILY = Object.freeze({
  candidate_pool: 0.55,
  repick: 0.45,
  delete: 0.5,
  purchase: 0.4,
  confidence: 0.35,
  world: 0.5,
  subworld: 0.45,
  ranking: 0.65,
  features: 0.7,
  ops_data: 0.25,
  unknown: 0.5,
});

/** Intrinsic regression risk by family (before similarity bump). */
export const BASE_RISK_BY_FAMILY = Object.freeze({
  candidate_pool: 0.35,
  repick: 0.4,
  delete: 0.45,
  purchase: 0.3,
  confidence: 0.35,
  world: 0.4,
  subworld: 0.4,
  ranking: 0.5,
  features: 0.35,
  ops_data: 0.2,
  unknown: 0.55,
});

function readJson(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function clamp01(x) {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, Math.round(x * 1000) / 1000));
}

function round4(x) {
  return Math.round(x * 10000) / 10000;
}

/**
 * Validation Score formula (V8.4: Knowledge Score multiplies numerator).
 * score = (Impact × Confidence × Coverage × K) / (Risk × (1 + Cost))
 * where K = 0.5 + 0.5 × knowledge_score  (knowledge_score default 0.5 → K=0.75)
 * @param {{ expected_impact: number, confidence: number, coverage: number, risk: number, cost: number, knowledge_score?: number }} d
 */
export function computeValidationScore(d) {
  const impact = clamp01(d.expected_impact);
  const confidence = clamp01(d.confidence);
  const coverage = clamp01(d.coverage);
  const risk = Math.max(RISK_EPSILON, clamp01(d.risk));
  const cost = clamp01(d.cost);
  const ks =
    typeof d.knowledge_score === "number" ? clamp01(d.knowledge_score) : 0.5;
  const knowledgeFactor = 0.5 + 0.5 * ks;
  const numerator = impact * confidence * coverage * knowledgeFactor;
  const denominator = risk * (1 + cost);
  return round4(numerator / denominator);
}

/**
 * @deprecated Prefer similaritySearch from knowledge-base (V8.4).
 * Kept for backward-compatible tests that pass weekly history arrays.
 */
export function findSimilarRejected(family, history, currentWeek) {
  const hits = [];
  for (const w of history || []) {
    if (currentWeek && w.week === currentWeek) continue;
    if (String(w.decision) !== "reject") continue;
    const fam = w.root_cause || w.primary_family || null;
    if (fam !== family && w.primary_family !== family) continue;
    hits.push({
      week: w.week,
      decision: "reject",
      root_cause: fam || family,
      label: familyLabel(family),
      similarity: fam === family ? 0.95 : 0.85,
      message: `Similar to ${w.week} Reject ${familyLabel(family)}`,
    });
  }
  const seen = new Set();
  return hits.filter((h) => {
    if (seen.has(h.week)) return false;
    seen.add(h.week);
    return true;
  });
}

function familyLabel(family) {
  const map = {
    candidate_pool: "CandidatePool Threshold",
    repick: "Repick",
    delete: "Delete",
    purchase: "Purchase",
    confidence: "Confidence",
    world: "World",
    subworld: "Subworld",
    ranking: "Ranking",
    features: "Features",
    ops_data: "Ops Data",
    unknown: "Unknown",
  };
  return map[family] || family;
}

/**
 * Validate one ranked proposal row.
 * @param {object} row ranking row
 * @param {object} miss analysis
 * @param {object|object[]} kbOrHistory Knowledge Base object or legacy history array
 * @param {{ week_id?: string, gate_threshold?: number, devRoot?: string }} [opts]
 */
export function validateProposalRow(row, miss, kbOrHistory, opts = {}) {
  const family = row.family || row.proposal;
  const gateThreshold = opts.gate_threshold ?? GATE_THRESHOLD;
  const scoreFromAnalyzer = Number(row.score) || miss?.root_cause_scores?.[family] || 0;
  const confFromAnalyzer =
    miss?.root_cause_confidence?.[family] ??
    (typeof miss?.confidence === "number" ? miss.confidence : 0.4);
  const freqPct =
    row.frequency_pct ?? miss?.root_cause_frequency_pct?.[family] ?? 0;
  const impactWeight = IMPACT_WEIGHT[family] ?? 0.3;

  const expected_impact = clamp01(
    0.55 * scoreFromAnalyzer + 0.45 * impactWeight * Math.max(scoreFromAnalyzer, 0.2)
  );
  const confidence = clamp01(confFromAnalyzer);
  const coverage = clamp01(freqPct / 100);
  let risk = BASE_RISK_BY_FAMILY[family] ?? 0.45;
  const cost = COST_BY_FAMILY[family] ?? 0.5;

  // V8.4 — Similarity Search against Knowledge Base (preferred)
  let similar = [];
  let knowledge_score = 0.5;
  let similarity = null;
  const isKb =
    kbOrHistory &&
    typeof kbOrHistory === "object" &&
    !Array.isArray(kbOrHistory) &&
    (kbOrHistory.accepted_patterns || kbOrHistory.proposals);

  if (isKb) {
    similarity = similaritySearch(family, kbOrHistory, { week_id: opts.week_id });
    knowledge_score = similarity.knowledge_score;
    similar = similarity.rejected_hits || [];
    if (similarity.past_accepted && expected_impact >= 0.3) {
      // Prior accept for same family slightly reduces perceived risk
      risk = clamp01(risk - 0.05);
    }
  } else {
    similar = findSimilarRejected(family, kbOrHistory, opts.week_id);
    knowledge_score = computeKnowledgeScore(0, similar.length > 0 ? 1 : 0);
  }

  const warnings = [];
  if (similar.length) {
    risk = clamp01(risk + 0.15 + Math.min(0.2, similar.length * 0.05));
    for (const s of similar.slice(0, 3)) {
      warnings.push({
        type: "similar_rejected_proposal",
        ...s,
      });
    }
  }
  if (similarity?.similar_proposal) {
    warnings.push({
      type: "similar_proposal_in_kb",
      message: "Similar proposal exists in Knowledge Base",
      count: similarity.similar_proposals?.length || 0,
    });
  }
  if (similarity?.past_accepted) {
    warnings.push({
      type: "past_accepted_pattern",
      message: "Past Accept pattern exists — consider reuse",
      hits: similarity.accepted_hits?.slice(0, 2),
    });
  }

  let hard_block = false;
  let hard_block_reason = null;
  if (coverage < 0.02 && scoreFromAnalyzer < 0.1) {
    hard_block = true;
    hard_block_reason = "insufficient_coverage_and_signal";
  }
  if (similar.some((s) => s.similarity >= 0.95) && expected_impact < 0.35) {
    hard_block = true;
    hard_block_reason = "similar_reject_without_strong_impact";
  }

  const dimensions = {
    expected_impact,
    risk,
    confidence,
    coverage,
    cost,
    knowledge_score,
  };
  const validation_score = computeValidationScore(dimensions);
  const pass =
    !hard_block && validation_score >= gateThreshold && coverage >= 0.02;

  return {
    schema_version: "expect-v84-proposal-validation/1.0",
    proposal: family,
    family,
    priority: row.priority ?? null,
    priority_band: row.priority_band ?? null,
    proposal_ids: row.proposal_ids || [],
    dimensions,
    knowledge_score,
    similarity: similarity
      ? {
          same_proposal: similarity.same_proposal,
          similar_proposal: similarity.similar_proposal,
          past_rejected: similarity.past_rejected,
          past_accepted: similarity.past_accepted,
        }
      : null,
    validation_score,
    gate: pass ? "pass" : "fail",
    gate_threshold: gateThreshold,
    hard_block,
    hard_block_reason,
    warnings,
    formula:
      "score = (Impact × Confidence × Coverage × (0.5+0.5·KnowledgeScore)) / (Risk × (1 + Cost))",
    root_cause: family,
    impact: expected_impact,
  };
}

/**
 * Run validation for all ranked proposals.
 * @param {{ week_id?: string, devRoot?: string, gate_threshold?: number }} [opts]
 */
export function validateProposals(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const miss = readJson(join(devRoot, "analysis", "miss", "latest.json"));
  const ranking =
    readJson(join(devRoot, "analysis", "proposal-ranking.json")) ||
    { ranking: [] };
  // V8.4 — Analyzer reads Knowledge Base (not weekly history)
  const kb = loadKnowledgeBase(devRoot);

  const validations = (ranking.ranking || []).map((row) =>
    validateProposalRow(row, miss, kb, {
      week_id: weekId,
      gate_threshold: opts.gate_threshold,
      devRoot,
    })
  );

  const passed = validations.filter((v) => v.gate === "pass");
  const failed = validations.filter((v) => v.gate === "fail");

  const canary_eligible = passed.map((v) => ({
    priority: v.priority,
    proposal: v.proposal,
    proposal_ids: v.proposal_ids,
    validation_score: v.validation_score,
  }));

  const doc = {
    schema_version: "expect-v84-validation-run/1.0",
    week_id: weekId,
    generated_at: new Date().toISOString(),
    gate_threshold: opts.gate_threshold ?? GATE_THRESHOLD,
    formula:
      "ValidationScore = (Impact × Confidence × Coverage × (0.5+0.5·KnowledgeScore)) / (Risk × (1 + Cost))",
    knowledge_base: true,
    validations,
    summary: {
      total: validations.length,
      pass: passed.length,
      fail: failed.length,
      pass_rate_pct:
        validations.length > 0
          ? Math.round((passed.length / validations.length) * 1000) / 10
          : 0,
      reject_rate_pct:
        validations.length > 0
          ? Math.round((failed.length / validations.length) * 1000) / 10
          : 0,
    },
    canary_eligible,
    pe_ce_untouched: true,
  };

  mkdirSync(join(devRoot, "analysis"), { recursive: true });
  writeFileSync(
    join(devRoot, "analysis", "proposal-validation.json"),
    JSON.stringify(doc, null, 2) + "\n",
    "utf8"
  );

  const weekRoot = join(devRoot, "weekly", weekId);
  if (existsSync(weekRoot)) {
    const tue = join(weekRoot, "tue-proposal");
    mkdirSync(tue, { recursive: true });
    writeFileSync(
      join(tue, "proposal-validation.json"),
      JSON.stringify(doc, null, 2) + "\n",
      "utf8"
    );
  }

  return doc;
}

/**
 * Load canary-eligible list (after validation). Empty if validation missing.
 * @param {string} devRoot
 */
export function loadCanaryEligible(devRoot) {
  const doc = readJson(join(devRoot, "analysis", "proposal-validation.json"));
  if (!doc) return null;
  return doc.canary_eligible || [];
}

/**
 * Summarize validation knowledge for weekly history.
 * @param {object} validationDoc
 * @param {string} decision
 */
export function validationKnowledgePayload(validationDoc, decision) {
  const validations = validationDoc?.validations || [];
  const top = [...validations].sort(
    (a, b) => (b.validation_score || 0) - (a.validation_score || 0)
  )[0];
  return {
    proposals: validations.map((v) => ({
      proposal: v.proposal,
      root_cause: v.root_cause,
      validation_score: v.validation_score,
      gate: v.gate,
      impact: v.impact,
      decision: v.gate === "pass" ? decision : "validation_reject",
      warnings: (v.warnings || []).map((w) => w.message),
    })),
    validation_score: top?.validation_score ?? null,
    root_cause: top?.root_cause ?? null,
    impact: top?.impact ?? null,
    validation_pass_count: validations.filter((v) => v.gate === "pass").length,
    validation_fail_count: validations.filter((v) => v.gate === "fail").length,
  };
}

function main() {
  const wi = process.argv.indexOf("--week-id");
  const week_id = wi >= 0 ? process.argv[wi + 1] : undefined;
  const gi = process.argv.indexOf("--gate");
  const gate_threshold = gi >= 0 ? Number(process.argv[gi + 1]) : undefined;
  console.log(
    JSON.stringify(validateProposals({ week_id, gate_threshold }), null, 2)
  );
}

if (process.argv[1]?.endsWith("proposal-validate.mjs")) {
  main();
}
