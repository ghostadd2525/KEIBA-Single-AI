/**
 * Version8.3 — Analyzer Feedback Loop (Research only).
 *
 * Learns from Canary / 285R / Friday decision — never mutates Production Evidence.
 * Gradually calibrates Analyzer confidence biases + Validation error memory.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { repoRoot, weekIdJst, assertResearchDay } from "./calendar.mjs";

/** Learning rate for confidence bias (gentle). */
export const CONF_LR = 0.04;
/** Max absolute confidence bias per family. */
export const CONF_BIAS_MAX = 0.15;
/** Map expected_impact (0..1) → predicted Hit delta units. */
export const HIT_SCALE = 3;

function readJson(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function writeJson(path, doc) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(doc, null, 2) + "\n", "utf8");
}

function clamp(x, lo, hi) {
  return Math.max(lo, Math.min(hi, x));
}

function round3(x) {
  return Math.round(x * 1000) / 1000;
}

function historyDir(devRoot) {
  return join(devRoot, "history");
}

export function calibrationPath(devRoot) {
  return join(historyDir(devRoot), "analyzer_calibration.json");
}

export function precisionPath(devRoot) {
  return join(historyDir(devRoot), "root_cause_precision.json");
}

export function analyzerReportPath(devRoot) {
  return join(historyDir(devRoot), "analyzer_report.json");
}

export function validationCalPath(devRoot) {
  return join(historyDir(devRoot), "validation_calibration.json");
}

export function loadCalibration(devRoot) {
  return (
    readJson(calibrationPath(devRoot)) || {
      schema_version: "expect-v83-analyzer-calibration/1.0",
      confidence_bias: {},
      updated_at: null,
      note: "Research-only. Applied to Analyzer confidence gradually.",
    }
  );
}

export function loadPrecision(devRoot) {
  const raw = readJson(precisionPath(devRoot));
  if (raw?.by_root_cause) return raw;
  return {
    schema_version: "expect-v83-root-cause-precision/1.0",
    by_root_cause: {},
    updated_at: null,
  };
}

export function loadAnalyzerReports(devRoot) {
  const raw = readJson(analyzerReportPath(devRoot));
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.weeks)) return raw.weeks;
  return [];
}

export function loadValidationCalibration(devRoot) {
  return (
    readJson(validationCalPath(devRoot)) || {
      schema_version: "expect-v83-validation-calibration/1.0",
      samples: [],
      avg_error: null,
      n: 0,
      updated_at: null,
    }
  );
}

/**
 * Predicted Hit delta from Analyzer/Validation impact.
 * @param {number} expectedImpact 0..1
 */
export function predictHitDelta(expectedImpact) {
  if (!Number.isFinite(expectedImpact)) return 0;
  return Math.round(expectedImpact * HIT_SCALE * 10) / 10;
}

/**
 * Infer actual Hit delta from baseline / canary / decision (Research proxies OK).
 */
export function inferActualHitDelta({ baseline, canaryRow, decision, hitDelta }) {
  if (typeof hitDelta === "number" && Number.isFinite(hitDelta)) {
    return hitDelta;
  }
  const measured =
    baseline?.comparison?.measured_delta_hit_at_1 ??
    baseline?.comparison?.measured_delta_hit ??
    null;
  if (typeof measured === "number" && Number.isFinite(measured)) {
    // rate delta → approx hit-count units on 285R scale
    return Math.round(measured * 1000) / 10;
  }
  if (canaryRow) {
    if (canaryRow.status === "gate_blocked") return 0;
    if (canaryRow.verdict === "PASS" || canaryRow.verdict === "PASS_WITH_WARNING") {
      return 1;
    }
    if (canaryRow.verdict === "FAIL" || canaryRow.status === "failed") {
      return 0;
    }
    if (canaryRow.status === "evaluated") return 0.5;
    if (canaryRow.status === "deferred_no_imp_id" && canaryRow.gate === "pass") {
      return 0; // no canary run yet
    }
  }
  if (decision === "accept") return 1;
  if (decision === "reject" || decision === "no_improvement") return 0;
  return 0;
}

/**
 * Apply stored confidence biases (gentle) to a confidence map.
 * @param {Record<string, number>} confidence
 * @param {object} [calibration]
 */
export function applyConfidenceCalibration(confidence, calibration) {
  const biases = calibration?.confidence_bias || {};
  /** @type {Record<string, number>} */
  const out = {};
  for (const [k, v] of Object.entries(confidence || {})) {
    const b = Number(biases[k]) || 0;
    out[k] = clamp(Number(v) + b, 0, 1);
  }
  return out;
}

/**
 * Update confidence bias from precision (EMA-like step).
 * success rate high → raise bias slightly; low → lower.
 */
export function updateConfidenceBias(calibration, precisionByFamily) {
  const biases = { ...(calibration.confidence_bias || {}) };
  const updates = {};
  for (const [family, stats] of Object.entries(precisionByFamily || {})) {
    const precision =
      typeof stats.precision === "number"
        ? stats.precision
        : stats.accepted > 0
          ? stats.successful / stats.accepted
          : null;
    if (precision == null || stats.accepted < 1) continue;
    const delta = CONF_LR * (precision - 0.5);
    const prev = Number(biases[family]) || 0;
    const next = clamp(prev + delta, -CONF_BIAS_MAX, CONF_BIAS_MAX);
    biases[family] = round3(next);
    updates[family] = { prev: round3(prev), next: round3(next), precision, delta: round3(delta) };
  }
  return {
    ...calibration,
    schema_version: "expect-v83-analyzer-calibration/1.0",
    confidence_bias: biases,
    last_updates: updates,
    updated_at: new Date().toISOString(),
  };
}

/**
 * Merge weekly precision deltas into cumulative ledger.
 */
export function mergePrecision(ledger, weekDeltas) {
  const by = { ...(ledger.by_root_cause || {}) };
  for (const [family, d] of Object.entries(weekDeltas || {})) {
    const cur = by[family] || {
      proposals: 0,
      accepted: 0,
      successful: 0,
      precision: 0,
    };
    const proposals = cur.proposals + (d.proposals || 0);
    const accepted = cur.accepted + (d.accepted || 0);
    const successful = cur.successful + (d.successful || 0);
    by[family] = {
      proposals,
      accepted,
      successful,
      precision: accepted > 0 ? round3(successful / accepted) : 0,
    };
  }
  return {
    schema_version: "expect-v83-root-cause-precision/1.0",
    by_root_cause: by,
    updated_at: new Date().toISOString(),
  };
}

/**
 * Build per-proposal feedback comparisons for one week.
 */
export function buildFeedbackComparisons({
  validation,
  canaryRun,
  baseline,
  decision,
  hitDelta,
}) {
  const validations = validation?.validations || [];
  const canaryByProposal = {};
  for (const r of canaryRun?.results || []) {
    const key = r.proposal || r.family;
    if (!key) continue;
    if (!canaryByProposal[key]) canaryByProposal[key] = r;
  }

  const comparisons = [];
  /** @type {Record<string, {proposals:number,accepted:number,successful:number}>} */
  const weekPrecision = {};

  for (const v of validations) {
    const family = v.family || v.proposal || v.root_cause;
    if (!family) continue;
    if (!weekPrecision[family]) {
      weekPrecision[family] = { proposals: 0, accepted: 0, successful: 0 };
    }
    weekPrecision[family].proposals += 1;

    const predicted_hit = predictHitDelta(v.impact ?? v.dimensions?.expected_impact ?? 0);
    const canaryRow = canaryByProposal[family] || null;
    const actual_hit = inferActualHitDelta({
      baseline,
      canaryRow,
      decision,
      hitDelta,
    });
    const prediction_error = round3(Math.abs(predicted_hit - actual_hit));

    const accepted =
      v.gate === "pass" &&
      (decision === "accept" ||
        canaryRow?.verdict === "PASS" ||
        canaryRow?.verdict === "PASS_WITH_WARNING" ||
        canaryRow?.status === "evaluated" ||
        canaryRow?.status === "deferred_no_imp_id");
    // "accepted into trial" — passed validation and entered canary path
    const enteredTrial = v.gate === "pass";
    if (enteredTrial) weekPrecision[family].accepted += 1;

    const successful = enteredTrial && actual_hit > 0;
    if (successful) weekPrecision[family].successful += 1;

    const validation_score = v.validation_score ?? null;
    // Normalize actual improvement to 0..1 for calibration vs validation score
    const actual_improvement_01 = clamp(actual_hit / HIT_SCALE, 0, 1);
    const calibration_error =
      validation_score != null
        ? round3(Math.abs(validation_score - actual_improvement_01))
        : null;

    comparisons.push({
      root_cause: family,
      proposal: family,
      proposal_label: `${family} entry`,
      gate: v.gate,
      analyzer_prediction_hit: predicted_hit,
      canary_result_hit: actual_hit,
      prediction_error,
      validation_score,
      actual_improvement_01: round3(actual_improvement_01),
      calibration_error,
      decision,
      canary_status: canaryRow?.status ?? null,
      canary_verdict: canaryRow?.verdict ?? null,
    });
  }

  // Attach precision for week
  for (const [family, s] of Object.entries(weekPrecision)) {
    s.precision = s.accepted > 0 ? round3(s.successful / s.accepted) : 0;
  }

  return { comparisons, weekPrecision };
}

/**
 * Run full feedback loop for a week.
 * @param {{ week_id?: string, devRoot?: string, weekRoot?: string }} [opts]
 */
export function runAnalyzerFeedback(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const weekRoot =
    opts.weekRoot || join(devRoot, "weekly", weekId);

  const validation =
    readJson(join(weekRoot, "tue-proposal", "proposal-validation.json")) ||
    readJson(join(devRoot, "analysis", "proposal-validation.json"));
  const canaryRun =
    readJson(join(weekRoot, "wed-canary", "ranked-run.json")) ||
    readJson(join(devRoot, "runs", "latest-canary-ranked.json"));
  const baseline = readJson(join(weekRoot, "thu-baseline", "report.json"));
  const decisionDoc =
    readJson(join(weekRoot, "fri-decision", "decision.json")) || {};
  const decision = decisionDoc.decision || "no_improvement";
  const hitDelta =
    typeof decisionDoc.baseline_delta === "number"
      ? Math.round(decisionDoc.baseline_delta * 1000) / 10
      : null;

  const { comparisons, weekPrecision } = buildFeedbackComparisons({
    validation,
    canaryRun,
    baseline,
    decision,
    hitDelta,
  });

  const prevPrecision = loadPrecision(devRoot);
  const precision = mergePrecision(prevPrecision, weekPrecision);
  writeJson(precisionPath(devRoot), precision);

  const prevCal = loadCalibration(devRoot);
  const calibration = updateConfidenceBias(prevCal, precision.by_root_cause);
  writeJson(calibrationPath(devRoot), calibration);

  // Validation calibration samples
  const valCal = loadValidationCalibration(devRoot);
  const newSamples = comparisons
    .filter((c) => c.calibration_error != null)
    .map((c) => ({
      week: weekId,
      root_cause: c.root_cause,
      validation_score: c.validation_score,
      actual_improvement: c.actual_improvement_01,
      calibration_error: c.calibration_error,
    }));
  const samples = [...(valCal.samples || []), ...newSamples].slice(-200);
  const avg_error =
    samples.length > 0
      ? round3(
          samples.reduce((s, x) => s + (x.calibration_error || 0), 0) / samples.length
        )
      : null;
  const valCalOut = {
    schema_version: "expect-v83-validation-calibration/1.0",
    samples,
    avg_error,
    n: samples.length,
    updated_at: new Date().toISOString(),
  };
  writeJson(validationCalPath(devRoot), valCalOut);

  const errors = comparisons.map((c) => c.prediction_error);
  const avg_prediction_error =
    errors.length > 0
      ? round3(errors.reduce((a, b) => a + b, 0) / errors.length)
      : null;

  const precisionEntries = Object.entries(precision.by_root_cause).filter(
    ([, s]) => s.accepted > 0
  );
  precisionEntries.sort((a, b) => b[1].precision - a[1].precision);
  const best_root_cause = precisionEntries[0]?.[0] || null;
  const worst_root_cause =
    precisionEntries.length > 0
      ? precisionEntries[precisionEntries.length - 1][0]
      : null;

  const weekAccepted = Object.values(weekPrecision).reduce(
    (s, x) => s + x.accepted,
    0
  );
  const weekSuccessful = Object.values(weekPrecision).reduce(
    (s, x) => s + x.successful,
    0
  );
  const week_precision =
    weekAccepted > 0 ? round3(weekSuccessful / weekAccepted) : null;

  // Recall: successful / all proposals that had evidence signal (proposals count)
  const weekProposals = Object.values(weekPrecision).reduce(
    (s, x) => s + x.proposals,
    0
  );
  const week_recall =
    weekProposals > 0 ? round3(weekSuccessful / weekProposals) : null;

  const report = {
    week: weekId,
    precision: week_precision,
    avg_prediction_error,
    best_root_cause,
    worst_root_cause,
    recall: week_recall,
    proposal_success_rate: week_precision,
    validation_avg_error: avg_error,
    comparisons,
    week_precision_by_cause: weekPrecision,
    confidence_calibration_updates: calibration.last_updates || {},
    generated_at: new Date().toISOString(),
    research_only: true,
    production_evidence_untouched: true,
  };

  const reports = loadAnalyzerReports(devRoot).filter((r) => r.week !== weekId);
  reports.push(report);
  reports.sort((a, b) => String(a.week).localeCompare(String(b.week)));
  writeJson(analyzerReportPath(devRoot), reports);

  // Also write week-scoped artifacts
  const outAnalysis = join(devRoot, "analysis", "analyzer-feedback");
  mkdirSync(outAnalysis, { recursive: true });
  writeJson(join(outAnalysis, "latest.json"), report);
  writeJson(join(outAnalysis, `${weekId}.json`), report);

  if (existsSync(weekRoot)) {
    const reportsDir = join(weekRoot, "reports");
    mkdirSync(reportsDir, { recursive: true });
    writeJson(join(reportsDir, "analyzer-feedback.json"), report);
  }

  return {
    schema_version: "expect-v83-feedback-run/1.0",
    week_id: weekId,
    report,
    precision: precision.by_root_cause,
    calibration: {
      confidence_bias: calibration.confidence_bias,
      last_updates: calibration.last_updates,
    },
    validation_calibration: { avg_error, n: samples.length },
    pe_ce_untouched: true,
  };
}

/**
 * Summarize feedback artifacts for Research Metrics.
 */
export function summarizeFeedbackMetrics(devRoot) {
  const precision = loadPrecision(devRoot);
  const cal = loadCalibration(devRoot);
  const valCal = loadValidationCalibration(devRoot);
  const reports = loadAnalyzerReports(devRoot);
  const latest = reports.length ? reports[reports.length - 1] : null;

  let totalAccepted = 0;
  let totalSuccessful = 0;
  let totalProposals = 0;
  for (const s of Object.values(precision.by_root_cause || {})) {
    totalAccepted += s.accepted || 0;
    totalSuccessful += s.successful || 0;
    totalProposals += s.proposals || 0;
  }

  return {
    root_cause_precision: precision.by_root_cause || {},
    analyzer_recall:
      totalProposals > 0 ? round3(totalSuccessful / totalProposals) : null,
    average_prediction_error: latest?.avg_prediction_error ?? null,
    confidence_calibration: cal.confidence_bias || {},
    validation_calibration_avg_error: valCal.avg_error,
    proposal_success_rate:
      totalAccepted > 0 ? round3(totalSuccessful / totalAccepted) : null,
    latest_analyzer_report: latest
      ? {
          week: latest.week,
          precision: latest.precision,
          best_root_cause: latest.best_root_cause,
          worst_root_cause: latest.worst_root_cause,
        }
      : null,
  };
}

function main() {
  if (!process.argv.includes("--allow-weekend")) {
    assertResearchDay({ purpose: "v8.3:analyzer-feedback" });
  }
  const wi = process.argv.indexOf("--week-id");
  const week_id = wi >= 0 ? process.argv[wi + 1] : undefined;
  console.log(JSON.stringify(runAnalyzerFeedback({ week_id }), null, 2));
}

if (process.argv[1]?.endsWith("analyzer-feedback.mjs")) {
  try {
    main();
  } catch (e) {
    console.error(e && e.message ? e.message : e);
    process.exit(e && e.code === "V8_RESEARCH_WEEKEND_BLOCKED" ? 3 : 1);
  }
}
