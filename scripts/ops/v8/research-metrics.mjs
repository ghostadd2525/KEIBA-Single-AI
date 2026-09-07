/**
 * Version8.1 — Research Metrics (not Ops dashboard).
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { detectPatterns } from "./pattern-detect.mjs";
import { loadWeeklyHistory, summarizeHistory } from "./weekly-history.mjs";
import { summarizeFeedbackMetrics } from "./analyzer-feedback.mjs";
import { summarizeKnowledgeMetrics, ensureKnowledgeBase } from "./knowledge-base.mjs";
import { summarizeGovernanceMetrics } from "./governance.mjs";
import { repoRoot, weekIdJst } from "./calendar.mjs";

function readJson(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

/**
 * @param {{ week_id?: string, weeks?: number, devRoot?: string }} [opts]
 */
export function buildResearchMetrics(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const pattern = detectPatterns({
    week_id: weekId,
    weeks: opts.weeks || 4,
    devRoot,
  });
  const history = loadWeeklyHistory(devRoot);
  const rates = summarizeHistory(history);
  const miss = readJson(join(devRoot, "analysis", "miss", "latest.json"));
  const ranking = readJson(join(devRoot, "analysis", "proposal-ranking.json"));
  const validation = readJson(join(devRoot, "analysis", "proposal-validation.json"));
  const feedback = summarizeFeedbackMetrics(devRoot);
  ensureKnowledgeBase(devRoot);
  const knowledge = summarizeKnowledgeMetrics(devRoot);
  const governance = summarizeGovernanceMetrics(devRoot);

  const doc = {
    schema_version: "expect-v85-research-metrics/1.0",
    scope: "research_only",
    week_id: weekId,
    generated_at: new Date().toISOString(),
    root_cause_share: pattern.distribution_pct,
    root_cause_ranked: pattern.ranked,
    proposal_accept_rate_pct: rates.accept_rate,
    reject_rate_pct: rates.reject_rate,
    no_improvement_rate_pct: rates.no_improvement_rate,
    improvement_success_rate_pct: rates.improvement_success_rate,
    avg_hit_delta: rates.avg_hit_delta,
    history_weeks: rates.weeks,
    // Version8.2
    validation_pass_rate_pct:
      validation?.summary?.pass_rate_pct ?? rates.validation_pass_rate,
    validation_reject_rate_pct:
      validation?.summary?.reject_rate_pct ?? rates.validation_reject_rate,
    proposal_recurrence_rate_pct: rates.proposal_recurrence_rate,
    root_cause_improvement_success_pct: rates.root_cause_success,
    // Version8.3 Feedback
    root_cause_precision: feedback.root_cause_precision,
    analyzer_recall: feedback.analyzer_recall,
    average_prediction_error: feedback.average_prediction_error,
    confidence_calibration: feedback.confidence_calibration,
    validation_calibration: feedback.validation_calibration_avg_error,
    proposal_success_rate: feedback.proposal_success_rate,
    latest_analyzer_report: feedback.latest_analyzer_report,
    // Version8.4 Knowledge Base
    pattern_reuse_rate_pct: knowledge.pattern_reuse_rate_pct,
    accepted_pattern_count: knowledge.accepted_pattern_count,
    rejected_pattern_count: knowledge.rejected_pattern_count,
    knowledge_hit_rate_pct: knowledge.knowledge_hit_rate_pct,
    similar_proposal_rate_pct: knowledge.similar_proposal_rate_pct,
    knowledge_scores: knowledge.knowledge_scores,
    // Version8.5 Governance
    governance_active_rate_pct: governance.active_rate_pct,
    governance_stale_rate_pct: governance.stale_rate_pct,
    governance_archive_rate_pct: governance.archive_rate_pct,
    governance_merge_candidate_count: governance.merge_candidate_count,
    governance_avg_pattern_lifetime_weeks: governance.average_pattern_lifetime_weeks,
    governance_avg_knowledge_score: governance.average_knowledge_score,
    current_primary_family: miss?.root_cause_family || null,
    current_scores: miss?.root_cause_scores || null,
    proposal_ranking_top:
      ranking?.ranking?.slice(0, 5).map((r) => ({
        proposal: r.proposal,
        priority: r.priority,
        priority_band: r.priority_band,
        knowledge_score: r.knowledge_score ?? null,
      })) || [],
    validation_top:
      validation?.validations?.slice(0, 5).map((v) => ({
        proposal: v.proposal,
        validation_score: v.validation_score,
        gate: v.gate,
        impact: v.impact,
        knowledge_score: v.knowledge_score ?? null,
      })) || [],
    pe_ce_untouched: true,
    production_evidence_untouched: true,
  };

  const outDir = join(devRoot, "analysis", "research-metrics");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "latest.json"), JSON.stringify(doc, null, 2) + "\n", "utf8");
  writeFileSync(join(outDir, `${weekId}.json`), JSON.stringify(doc, null, 2) + "\n", "utf8");

  const weekReports = join(devRoot, "weekly", weekId, "reports");
  if (existsSync(join(devRoot, "weekly", weekId))) {
    mkdirSync(weekReports, { recursive: true });
    writeFileSync(
      join(weekReports, "research-metrics.json"),
      JSON.stringify(doc, null, 2) + "\n",
      "utf8"
    );
  }

  return doc;
}

function main() {
  const wi = process.argv.indexOf("--week-id");
  const week_id = wi >= 0 ? process.argv[wi + 1] : undefined;
  console.log(JSON.stringify(buildResearchMetrics({ week_id }), null, 2));
}

if (process.argv[1]?.endsWith("research-metrics.mjs")) {
  main();
}
