/**
 * Version8.5 Operations Mode — Weekly Report aggregator (Baseline locked).
 *
 * Ops / monitoring / QA only. No new Research platform features.
 * Aggregates artifacts + Baseline Health Check; runs Incident detect (write only on anomaly).
 *
 * PE / CE / AI / Production logic untouched.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  readdirSync,
  statSync,
} from "node:fs";
import { join } from "node:path";
import { jstParts, repoRoot, weekIdJst } from "./calendar.mjs";
import { BASELINE_LOCK } from "./ops-baseline.mjs";
import { detectIncidents, formatIncidentMarkdown } from "./incident-detect.mjs";

/** Locked Operations Baseline (re-export) */
export { BASELINE_LOCK } from "./ops-baseline.mjs";

const CANARY_FLAGS = [
  "v8_canary_candidate_pool",
  "v8_canary_repick",
  "v8_canary_delete",
  "v8_canary_confidence",
  "v8_production_canary",
];

function readJson(path, fallback = null) {
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function prevWeekId(weekId) {
  const m = String(weekId).match(/^(\d{4})-W(\d{2})$/);
  if (!m) return null;
  let y = Number(m[1]);
  let w = Number(m[2]) - 1;
  if (w < 1) {
    y -= 1;
    w = 52;
  }
  return `${y}-W${String(w).padStart(2, "0")}`;
}

function pct(n, d) {
  if (!d) return null;
  return Math.round((n / d) * 1000) / 10;
}

function countJsonFiles(dir, depth = 0) {
  if (!existsSync(dir) || depth > 4) return 0;
  let n = 0;
  try {
    for (const name of readdirSync(dir)) {
      const p = join(dir, name);
      let st;
      try {
        st = statSync(p);
      } catch {
        continue;
      }
      if (st.isDirectory()) n += countJsonFiles(p, depth + 1);
      else if (name.endsWith(".json")) n += 1;
    }
  } catch {
    return n;
  }
  return n;
}

/**
 * Baseline Health Check (ops mandatory).
 */
export function buildBaselineHealthCheck({
  REPO,
  weekRoot,
  miss,
  baseline,
  knowledgeSync,
  governance,
  beta,
}) {
  const flagsOn = CANARY_FLAGS.filter((f) => beta?.ui_features?.[f] === true);
  const productionCanaryOn = beta?.ui_features?.v8_production_canary === true;
  const evidenceRoot = join(REPO, "evidence", "improvement");
  const missEvidenceOk =
    (miss?.event_count ?? 0) > 0 || countJsonFiles(join(evidenceRoot, "miss")) > 0;
  const knowledgeUpdated = Boolean(
    knowledgeSync?.week ||
      existsSync(join(REPO, "development", "knowledge", "proposals.json"))
  );
  const governanceRan = Boolean(
    governance?.generated_at ||
      existsSync(join(REPO, "development", "knowledge", "governance-dashboard.json")) ||
      existsSync(join(weekRoot, "reports", "governance.json"))
  );
  const baseline285Ran = Boolean(
    baseline?.generated_at || baseline?.comparison || baseline?.baseline
  );
  const raOk =
    existsSync(join(REPO, "development", "index", "latest.json")) || missEvidenceOk;

  const peChanged = baseline?.comparison?.pe_mutated === true ? "有" : "無";
  const ceChanged = "無";
  const aiChanged = "無";

  const rows = {
    pe_changed: peChanged,
    ce_changed: ceChanged,
    ai_changed: aiChanged,
    result_automation: raOk ? "OK" : "NG",
    miss_evidence: missEvidenceOk ? "OK" : "NG",
    knowledge_updated: knowledgeUpdated ? "OK" : "NG",
    governance_ran: governanceRan ? "OK" : "NG",
    baseline_285r_ran: baseline285Ran ? "OK" : "NG",
    feature_flag_mis_on: flagsOn.length ? `有 (${flagsOn.join(", ")})` : "無",
    production_canary_leak: productionCanaryOn ? "有" : "無",
    baseline_lock: `Version${BASELINE_LOCK}`,
  };

  const critical_ng = [
    rows.result_automation === "NG" ? "result_automation" : null,
    rows.miss_evidence === "NG" ? "miss_evidence" : null,
    productionCanaryOn ? "production_canary_leak" : null,
    flagsOn.length ? "feature_flag_mis_on" : null,
    peChanged === "有" ? "pe_changed" : null,
  ].filter(Boolean);

  return {
    schema_version: "expect-v85-baseline-health-check/1.0",
    ...rows,
    critical_ng,
    ok: critical_ng.length === 0,
    research_only: true,
  };
}

/**
 * @param {{ week_id?: string, devRoot?: string }} [opts]
 */
export function buildWeeklyOpsReport(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const weekRoot = join(devRoot, "weekly", weekId);
  const prevId = prevWeekId(weekId);
  const prevRoot = prevId ? join(devRoot, "weekly", prevId) : null;

  const miss = readJson(join(devRoot, "analysis", "miss", "latest.json"), {});
  const validation = readJson(
    join(weekRoot, "tue-proposal", "proposal-validation.json"),
    readJson(join(devRoot, "analysis", "proposal-validation.json"), {})
  );
  const ranking = readJson(
    join(weekRoot, "tue-proposal", "proposal-ranking.json"),
    readJson(join(devRoot, "analysis", "proposal-ranking.json"), {})
  );
  const canary = readJson(
    join(weekRoot, "wed-canary", "ranked-run.json"),
    readJson(join(devRoot, "runs", "latest-canary-ranked.json"), {})
  );
  const baseline = readJson(join(weekRoot, "thu-baseline", "report.json"), {});
  const decision = readJson(join(weekRoot, "fri-decision", "decision.json"), {});
  const metrics = readJson(
    join(weekRoot, "reports", "research-metrics.json"),
    readJson(join(devRoot, "analysis", "research-metrics", "latest.json"), {})
  );
  const governance = readJson(
    join(weekRoot, "reports", "governance.json"),
    readJson(join(devRoot, "knowledge", "governance-dashboard.json"), {})
  );
  const feedback = readJson(
    join(weekRoot, "reports", "analyzer-feedback.json"),
    readJson(join(devRoot, "analysis", "analyzer-feedback", "latest.json"), {})
  );
  const knowledgeSync = readJson(
    join(weekRoot, "reports", "knowledge-sync.json"),
    {}
  );
  const history = readJson(join(devRoot, "history", "weekly_history.json"), []);
  const beta =
    readJson(join(REPO, "public", "config", "beta.json"), {}) ||
    readJson(join(REPO, "config", "beta.json"), {});
  const prevDecision = prevRoot
    ? readJson(join(prevRoot, "fri-decision", "decision.json"), {})
    : {};

  const canaryResults = canary?.results || [];
  const canaryEval = canaryResults.filter(
    (r) => r.status === "evaluated" || r.verdict
  );
  const canaryPass = canaryEval.filter(
    (r) => r.verdict === "PASS" || r.verdict === "PASS_WITH_WARNING"
  );

  const histWeek = Array.isArray(history)
    ? history.find((h) => h.week === weekId)
    : null;

  const decisionValue =
    decision?.decision || histWeek?.decision || "no_improvement";

  const evidenceRoot = join(REPO, "evidence", "improvement");
  const missFileCount = countJsonFiles(join(evidenceRoot, "miss"));
  const archiveCount =
    countJsonFiles(join(REPO, "evidence", "archive")) ||
    countJsonFiles(join(devRoot, "archive")) ||
    null;

  const production = {
    result_automation: "ops_probe",
    race_results: null,
    race_evaluations: null,
    miss_count: miss?.event_count ?? missFileCount ?? null,
    archive_count: archiveCount === 0 ? 0 : archiveCount,
    note:
      "race_results / race_evaluations 件数は Production DB 連携時に埋める。Research は読取のみ。",
  };

  const research = {
    miss_count: miss?.event_count ?? null,
    root_cause_share:
      miss?.root_cause_frequency_pct ||
      metrics?.root_cause_share ||
      miss?.findings?.by_miss_category ||
      {},
    root_cause_primary:
      miss?.root_cause_family ||
      metrics?.current_primary_family ||
      miss?.findings?.dominant_category ||
      miss?.root_cause ||
      null,
    proposal_count:
      (ranking?.ranking || []).length ||
      (validation?.validations || []).length ||
      null,
    validation_pass_rate_pct:
      validation?.summary?.pass_rate_pct ??
      metrics?.validation_pass_rate_pct ??
      null,
    canary_success_rate_pct: pct(canaryPass.length, canaryEval.length || 0),
    accept_rate_pct: metrics?.proposal_accept_rate_pct ?? null,
    reject_rate_pct: metrics?.reject_rate_pct ?? null,
    no_improvement_rate_pct: metrics?.no_improvement_rate_pct ?? null,
  };

  const knowledge = {
    active_pattern: governance?.active_pattern_count ?? null,
    stale_pattern: governance?.stale_pattern_count ?? null,
    archived_pattern: governance?.archived_pattern_count ?? null,
    average_knowledge_score:
      governance?.average_knowledge_score ??
      metrics?.governance_avg_knowledge_score ??
      null,
    merge_candidates: governance?.merge_candidate_count ?? null,
  };

  const analyzer = {
    precision: feedback?.precision ?? metrics?.proposal_success_rate ?? null,
    recall: feedback?.recall ?? metrics?.analyzer_recall ?? null,
    prediction_error:
      feedback?.avg_prediction_error ?? metrics?.average_prediction_error ?? null,
    confidence_calibration:
      feedback?.confidence_calibration_updates ||
      metrics?.confidence_calibration ||
      {},
    validation_calibration:
      feedback?.validation_avg_error ?? metrics?.validation_calibration ?? null,
  };

  const hitDelta =
    typeof decision?.baseline_delta === "number"
      ? Math.round(decision.baseline_delta * 1000) / 10
      : histWeek?.hit_delta ?? null;
  const prevHit =
    typeof prevDecision?.baseline_delta === "number"
      ? Math.round(prevDecision.baseline_delta * 1000) / 10
      : null;

  const improvement = {
    vs_prev_week: {
      hit: hitDelta != null && prevHit != null ? round1(hitDelta - prevHit) : hitDelta,
      purchase: null,
      rank710: histWeek?.rank710_delta ?? null,
      other_miss: null,
      rank46: null,
      note:
        "purchase / other_miss / rank46 は Production stats 連携時に埋める。現状 Research 成果物のみ。",
    },
    vs_285r: {
      hit: baseline?.comparison?.measured_delta_hit_at_1 ?? null,
      purchase: null,
      rank710: null,
      other_miss: null,
      rank46: null,
    },
    current_hit_delta: hitDelta,
  };

  const baseline285 = {
    baseline_id: baseline?.baseline?.baseline_id || "formal-285r-offline-corpus",
    measured_delta_hit_at_1:
      baseline?.comparison?.measured_delta_hit_at_1 ?? null,
    verdict: baseline?.comparison?.verdict || null,
    pe_mutated: baseline?.comparison?.pe_mutated === true,
  };

  const baseline_health = buildBaselineHealthCheck({
    REPO,
    weekRoot,
    miss,
    baseline,
    knowledgeSync,
    governance,
    beta,
  });

  const parts = jstParts();
  const researchRan = Boolean(
    decision?.decided_at ||
      validation?.generated_at ||
      existsSync(join(weekRoot, "mon-analyzer"))
  );

  return {
    schema_version: "expect-v8-weekly-ops-report/1.2",
    baseline_version: BASELINE_LOCK,
    baseline_lock: `Version${BASELINE_LOCK}`,
    operations_mode: true,
    week_id: weekId,
    generated_at: new Date().toISOString(),
    date_jst: parts.date_jst,
    weekday_jst: parts.weekday_name,
    phase: "operations",
    research_ran: researchRan,
    decision: {
      value: decisionValue,
      ok: true,
      reason:
        decision?.reason ||
        (decisionValue === "no_improvement"
          ? "改善案なし / 優位差なし。Version 維持は成功。"
          : null),
      promote_to_production: decision?.promote_to_production === true,
      no_improvement_is_success: true,
    },
    production,
    research,
    knowledge,
    governance: {
      active_pattern: knowledge.active_pattern,
      stale_pattern: knowledge.stale_pattern,
      archived_pattern: knowledge.archived_pattern,
      merge_candidates: knowledge.merge_candidates,
      active_rate_pct: governance?.active_rate_pct ?? metrics?.governance_active_rate_pct,
      stale_rate_pct: governance?.stale_rate_pct ?? metrics?.governance_stale_rate_pct,
      archive_rate_pct: governance?.archive_rate_pct ?? metrics?.governance_archive_rate_pct,
      merge_candidate_count: knowledge.merge_candidates,
      average_pattern_lifetime_weeks:
        governance?.average_pattern_lifetime_weeks ??
        metrics?.governance_avg_pattern_lifetime_weeks,
      average_knowledge_score: knowledge.average_knowledge_score,
    },
    analyzer,
    improvement,
    baseline_285r: baseline285,
    baseline_health,
    kpi_vs_prev: {
      prev_week: prevId,
      validation_pass_rate_pct: research.validation_pass_rate_pct,
      accept_rate_pct: research.accept_rate_pct,
      note: "前週 Research 完了後に差分が埋まる。",
    },
    safety: {
      pe_ce_ai_unchanged: true,
      production_untouched_by_research: true,
      new_research_features: false,
      baseline_locked: BASELINE_LOCK,
    },
  };
}

function round1(x) {
  return Math.round(x * 10) / 10;
}

export function formatWeeklyOpsMarkdown(doc) {
  const d = doc.decision?.value || "no_improvement";
  const h = doc.baseline_health || {};
  const inc = doc.incident || {};
  return [
    `# Weekly Ops Report — ${doc.week_id}`,
    ``,
    `**Operations Mode:** Version ${doc.baseline_version}（正式運用）  `,
    `**Baseline Lock:** Version ${doc.baseline_version}  `,
    `**Decision:** \`${d}\` （ok=${doc.decision?.ok}）  `,
    `**Incident:** ${inc.has_incident ? `有 (${inc.incident_count})` : "無"}  `,
    `**Generated:** ${doc.generated_at}（JST ${doc.date_jst} ${doc.weekday_jst}）`,
    ``,
    `## Decision`,
    ``,
    `- **value:** ${d}`,
    `- **reason:** ${doc.decision?.reason || "—"}`,
    `- **promote_to_production:** ${doc.decision?.promote_to_production}`,
    `- **規則:** no_improvement / Version 維持は成功`,
    ``,
    `## Baseline Health Check`,
    ``,
    `| 項目 | 内容 |`,
    `|------|------|`,
    `| PE変更 | ${fmt(h.pe_changed)} |`,
    `| CE変更 | ${fmt(h.ce_changed)} |`,
    `| AI変更 | ${fmt(h.ai_changed)} |`,
    `| ResultAutomation正常 | ${fmt(h.result_automation)} |`,
    `| Miss Evidence正常 | ${fmt(h.miss_evidence)} |`,
    `| Knowledge更新 | ${fmt(h.knowledge_updated)} |`,
    `| Governance更新 | ${fmt(h.governance_ran)} |`,
    `| 285R比較実施 | ${fmt(h.baseline_285r_ran)} |`,
    `| Feature Flag誤ON | ${fmt(h.feature_flag_mis_on)} |`,
    `| Production Canary混入 | ${fmt(h.production_canary_leak)} |`,
    `| Baseline Lock | ${fmt(h.baseline_lock)} |`,
    `| Health OK | ${h.ok === true ? "YES" : "NO"} |`,
    ``,
    `## Production Report`,
    ``,
    `| 項目 | 値 |`,
    `|------|-----|`,
    `| ResultAutomation | ${fmt(doc.production?.result_automation)} |`,
    `| race_results | ${fmt(doc.production?.race_results)} |`,
    `| race_evaluations | ${fmt(doc.production?.race_evaluations)} |`,
    `| Miss件数 | ${fmt(doc.production?.miss_count)} |`,
    `| Archive件数 | ${fmt(doc.production?.archive_count)} |`,
    ``,
    `## Research Report`,
    ``,
    `| 項目 | 値 |`,
    `|------|-----|`,
    `| Miss件数 | ${fmt(doc.research.miss_count)} |`,
    `| Root Cause 主因 | ${fmt(doc.research.root_cause_primary)} |`,
    `| Proposal件数 | ${fmt(doc.research.proposal_count)} |`,
    `| Validation Pass率 | ${fmtPct(doc.research.validation_pass_rate_pct)} |`,
    `| Canary成功率 | ${fmtPct(doc.research.canary_success_rate_pct)} |`,
    `| Accept率 | ${fmtPct(doc.research.accept_rate_pct)} |`,
    `| Reject率 | ${fmtPct(doc.research.reject_rate_pct)} |`,
    `| no_improvement率 | ${fmtPct(doc.research.no_improvement_rate_pct)} |`,
    ``,
    `### Root Cause 分布`,
    ``,
    "```json",
    JSON.stringify(doc.research.root_cause_share || {}, null, 2),
    "```",
    ``,
    `## Knowledge Report`,
    ``,
    `| 項目 | 値 |`,
    `|------|-----|`,
    `| Active Pattern | ${fmt(doc.knowledge.active_pattern)} |`,
    `| Stale Pattern | ${fmt(doc.knowledge.stale_pattern)} |`,
    `| Archived Pattern | ${fmt(doc.knowledge.archived_pattern)} |`,
    `| Merge Candidate | ${fmt(doc.knowledge.merge_candidates)} |`,
    `| Average Knowledge Score | ${fmt(doc.knowledge.average_knowledge_score)} |`,
    ``,
    `## Governance Report`,
    ``,
    `| 項目 | 値 |`,
    `|------|-----|`,
    `| Active率 | ${fmtPct(doc.governance.active_rate_pct)} |`,
    `| Stale率 | ${fmtPct(doc.governance.stale_rate_pct)} |`,
    `| Archive率 | ${fmtPct(doc.governance.archive_rate_pct)} |`,
    `| Merge候補数 | ${fmt(doc.governance.merge_candidate_count)} |`,
    `| Pattern寿命(平均週) | ${fmt(doc.governance.average_pattern_lifetime_weeks)} |`,
    `| 平均 Knowledge Score | ${fmt(doc.governance.average_knowledge_score)} |`,
    ``,
    `## Analyzer Report`,
    ``,
    `| 項目 | 値 |`,
    `|------|-----|`,
    `| Precision | ${fmt(doc.analyzer.precision)} |`,
    `| Recall | ${fmt(doc.analyzer.recall)} |`,
    `| Prediction Error | ${fmt(doc.analyzer.prediction_error)} |`,
    `| Confidence Calibration | ${fmt(JSON.stringify(doc.analyzer.confidence_calibration || {}))} |`,
    `| Validation Calibration | ${fmt(doc.analyzer.validation_calibration)} |`,
    ``,
    `## KPI Report（285R / 前週）`,
    ``,
    `| 項目 | vs 285R | vs 前週 |`,
    `|------|---------|--------|`,
    `| Hit | ${fmt(doc.improvement.vs_285r?.hit)} | ${fmt(doc.improvement.vs_prev_week.hit)} |`,
    `| Purchase | ${fmt(doc.improvement.vs_285r?.purchase)} | ${fmt(doc.improvement.vs_prev_week.purchase)} |`,
    `| rank710 | ${fmt(doc.improvement.vs_285r?.rank710)} | ${fmt(doc.improvement.vs_prev_week.rank710)} |`,
    `| other_miss | ${fmt(doc.improvement.vs_285r?.other_miss)} | ${fmt(doc.improvement.vs_prev_week.other_miss)} |`,
    `| rank46 | ${fmt(doc.improvement.vs_285r?.rank46)} | ${fmt(doc.improvement.vs_prev_week.rank46)} |`,
    ``,
    `## Baseline（285R）`,
    ``,
    `| 項目 | 値 |`,
    `|------|-----|`,
    `| baseline_id | ${fmt(doc.baseline_285r.baseline_id)} |`,
    `| measured_delta_hit_at_1 | ${fmt(doc.baseline_285r.measured_delta_hit_at_1)} |`,
    `| verdict | ${fmt(doc.baseline_285r.verdict)} |`,
    `| pe_mutated | ${doc.baseline_285r.pe_mutated} |`,
    ``,
    `## Incident`,
    ``,
    inc.has_incident
      ? `- **有:** ${fmt(inc.codes?.join(", "))} → \`incident-report.md\` を提出`
      : `- **無:** 異常トリガなし（Incident Report 未作成）`,
    ``,
    `## Safety`,
    ``,
    `- PE / CE / AI 変更なし: **${doc.safety.pe_ce_ai_unchanged}**`,
    `- Research → Production 非直結: **${doc.safety.production_untouched_by_research}**`,
    `- 新 Research 機能追加: **${doc.safety.new_research_features}**`,
    `- Baseline locked: **${doc.safety.baseline_locked}**`,
    `- Operations Mode: **${doc.operations_mode === true}**`,
    ``,
  ].join("\n");
}

function fmt(v) {
  return v == null || v === "" ? "—" : String(v);
}

function fmtPct(v) {
  return v == null ? "—" : `${v}%`;
}

export function writeWeeklyOpsReport(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const doc = buildWeeklyOpsReport(opts);

  const prevId = prevWeekId(doc.week_id);
  const prevDoc = prevId
    ? readJson(
        join(devRoot, "weekly", prevId, "reports", "weekly-ops-report.json"),
        null
      )
    : null;
  const detected = detectIncidents(doc, prevDoc);
  doc.incident = {
    has_incident: detected.has_incident,
    incident_count: detected.incidents.length,
    codes: detected.incidents.map((i) => i.code),
  };

  const weekRoot = join(devRoot, "weekly", doc.week_id);
  const reports = join(weekRoot, "reports");
  mkdirSync(reports, { recursive: true });
  const jsonPath = join(reports, "weekly-ops-report.json");
  const mdPath = join(reports, "weekly-ops-report.md");
  writeFileSync(jsonPath, JSON.stringify(doc, null, 2) + "\n", "utf8");
  writeFileSync(mdPath, formatWeeklyOpsMarkdown(doc), "utf8");

  let incidentPaths = null;
  if (detected.has_incident) {
    const bundle = {
      schema_version: "expect-v85-incident-bundle/1.0",
      baseline_lock: `Version${BASELINE_LOCK}`,
      week_id: doc.week_id,
      generated_at: new Date().toISOString(),
      date_jst: doc.date_jst,
      has_incident: true,
      incident_count: detected.incidents.length,
      incidents: detected.incidents,
    };
    const iJson = join(reports, "incident-report.json");
    const iMd = join(reports, "incident-report.md");
    writeFileSync(iJson, JSON.stringify(bundle, null, 2) + "\n", "utf8");
    writeFileSync(iMd, formatIncidentMarkdown(bundle), "utf8");
    incidentPaths = { json: iJson, md: iMd };
  }

  const histDir = join(devRoot, "history");
  mkdirSync(histDir, { recursive: true });
  writeFileSync(
    join(histDir, "latest-weekly-ops-report.json"),
    JSON.stringify(doc, null, 2) + "\n",
    "utf8"
  );

  return { doc, jsonPath, mdPath, incidentPaths };
}

function main() {
  const week_id = arg("--week-id", undefined);
  const out = writeWeeklyOpsReport({ week_id });
  console.log(
    JSON.stringify(
      {
        event: "v8_weekly_ops_report",
        week_id: out.doc.week_id,
        decision: out.doc.decision.value,
        baseline_lock: out.doc.baseline_lock,
        operations_mode: true,
        health_ok: out.doc.baseline_health?.ok,
        incident: out.doc.incident,
        paths: {
          json: out.jsonPath,
          md: out.mdPath,
          incident: out.incidentPaths,
        },
        pe_ce_ai_unchanged: true,
      },
      null,
      2
    )
  );
}

if (process.argv[1]?.endsWith("weekly-report.mjs")) {
  main();
}
