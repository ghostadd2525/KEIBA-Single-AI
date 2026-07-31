/**
 * Version8.5 — Incident detection (pure; no weekly-report import).
 */
import { BASELINE_LOCK } from "./ops-baseline.mjs";

export const PRECISION_DROP_THRESHOLD = 15;
export const KNOWLEDGE_SCORE_DROP_THRESHOLD = 0.15;
export const HIT_COLLAPSE_THRESHOLD = -5;

/**
 * @returns {{ incidents: object[], has_incident: boolean }}
 */
export function detectIncidents(doc, prevDoc = null) {
  const incidents = [];
  const h = doc.baseline_health || {};
  const researchRan = doc.research_ran === true;
  const now = doc.generated_at || new Date().toISOString();

  function push(partial) {
    incidents.push({
      schema_version: "expect-v85-incident/1.0",
      occurred_at: now,
      baseline_lock: `Version${BASELINE_LOCK}`,
      week_id: doc.week_id,
      production_impact: partial.production_impact ?? false,
      ...partial,
    });
  }

  if (h.result_automation === "NG") {
    push({
      category: "Production",
      code: "RA_FAIL",
      title: "ResultAutomation失敗",
      scope: "Production pipeline / ResultAutomation",
      cause_candidates: [
        "Collector / ResultAutomation ジョブ失敗",
        "最新 index / Miss Evidence 未到達",
      ],
      recommended_action:
        "土日 Production ジョブログを確認し ResultAutomation を再実行。Research は触らない。",
      production_impact: true,
    });
  }
  if (h.miss_evidence === "NG") {
    push({
      category: "Production",
      code: "MISS_EVIDENCE_MISSING",
      title: "Miss Evidence未生成",
      scope: "evidence/improvement/miss · analysis/miss",
      cause_candidates: [
        "race_evaluations 未完了",
        "Miss 抽出スクリプト未実行",
      ],
      recommended_action:
        "race_results → race_evaluations → Miss Evidence を順に再実行。",
      production_impact: true,
    });
  }
  if (doc.production?.archive_status === "failed") {
    push({
      category: "Production",
      code: "ARCHIVE_FAIL",
      title: "Archive失敗",
      scope: "evidence/archive",
      cause_candidates: ["Archive ジョブ失敗", "出力パス不一致"],
      recommended_action: "Archive ジョブを再実行し件数を確認。",
      production_impact: true,
    });
  }
  if (doc.production?.race_results_status === "failed") {
    push({
      category: "Production",
      code: "RACE_RESULTS_FAIL",
      title: "race_results取得失敗",
      scope: "Production DB / race_results",
      cause_candidates: ["API/DB 接続失敗", "日付キー不一致"],
      recommended_action:
        "Production 側の results 取得を再実行。Research は触らない。",
      production_impact: true,
    });
  }

  if (
    h.production_canary_leak === "有" ||
    String(h.production_canary_leak || "").startsWith("有")
  ) {
    push({
      category: "Production",
      code: "PRODUCTION_CANARY_LEAK",
      title: "Production Canary混入",
      scope: "beta / feature flags",
      cause_candidates: ["v8_production_canary 誤ON"],
      recommended_action:
        "直ちに Production Canary flag を OFF。PE/CE は変更しない。",
      production_impact: true,
    });
  }
  if (h.feature_flag_mis_on && h.feature_flag_mis_on !== "無") {
    push({
      category: "Production",
      code: "FEATURE_FLAG_MIS_ON",
      title: "Feature Flag誤ON",
      scope: "beta.ui_features",
      cause_candidates: [String(h.feature_flag_mis_on)],
      recommended_action: "該当 Canary flag を OFF に戻す。",
      production_impact: true,
    });
  }
  if (h.pe_changed === "有") {
    push({
      category: "Production",
      code: "PE_CHANGED",
      title: "PE変更検出（禁止違反）",
      scope: "Prediction Engine",
      cause_candidates: ["Baseline 比較で pe_mutated=true"],
      recommended_action: "PE 差分を特定し Version8.5 へ戻す。Hot Patch 禁止。",
      production_impact: true,
    });
  }

  if (researchRan) {
    const prevPrecision = prevDoc?.analyzer?.precision;
    const curPrecision = doc.analyzer?.precision;
    if (
      typeof prevPrecision === "number" &&
      typeof curPrecision === "number" &&
      prevPrecision - curPrecision >= PRECISION_DROP_THRESHOLD
    ) {
      push({
        category: "Research",
        code: "PRECISION_DROP",
        title: "Root Cause Precision大幅低下",
        scope: "Analyzer Feedback",
        cause_candidates: [
          `precision ${prevPrecision} → ${curPrecision} (threshold ${PRECISION_DROP_THRESHOLD})`,
        ],
        recommended_action:
          "Miss Evidence と Root Cause ラベルを再確認。PE/CE は変更しない。",
        production_impact: false,
      });
    }

    const prevKs = prevDoc?.knowledge?.average_knowledge_score;
    const curKs = doc.knowledge?.average_knowledge_score;
    if (
      typeof prevKs === "number" &&
      typeof curKs === "number" &&
      prevKs - curKs >= KNOWLEDGE_SCORE_DROP_THRESHOLD
    ) {
      push({
        category: "Research",
        code: "KNOWLEDGE_SCORE_DROP",
        title: "Knowledge Score急落",
        scope: "Knowledge / Governance",
        cause_candidates: [
          `avg score ${prevKs} → ${curKs} (threshold ${KNOWLEDGE_SCORE_DROP_THRESHOLD})`,
        ],
        recommended_action:
          "Governance aging / stale 移行を確認。Merge 候補を点検。",
        production_impact: false,
      });
    }

    const hit285 = doc.improvement?.vs_285r?.hit;
    if (typeof hit285 === "number" && hit285 <= HIT_COLLAPSE_THRESHOLD) {
      push({
        category: "Research",
        code: "CANARY_285R_WORSE",
        title: "Canaryで285R悪化",
        scope: "Canary / 285R Baseline",
        cause_candidates: [`measured_delta_hit_at_1=${hit285}`],
        recommended_action:
          "decision=no_improvement を維持。Proposal を Reject / Archive。Production へは出さない。",
        production_impact: false,
      });
    }

    const valPass = doc.research?.validation_pass_rate_pct;
    const accept = doc.research?.accept_rate_pct;
    if (
      typeof valPass === "number" &&
      valPass >= 70 &&
      typeof accept === "number" &&
      accept === 0 &&
      typeof hit285 === "number" &&
      hit285 <= 0
    ) {
      push({
        category: "Research",
        code: "VALIDATION_REAL_DIVERGENCE",
        title: "Validation Scoreと実改善量が継続して乖離",
        scope: "Proposal Validation vs 285R",
        cause_candidates: [
          `validation_pass_rate=${valPass}% but accept=${accept}% hitΔ=${hit285}`,
        ],
        recommended_action:
          "Validation Calibration を Analyzer Feedback で見直し。機能追加はしない。",
        production_impact: false,
      });
    }
  }

  const vsPrev = doc.improvement?.vs_prev_week || {};
  if (typeof vsPrev.hit === "number" && vsPrev.hit <= HIT_COLLAPSE_THRESHOLD) {
    push({
      category: "KPI",
      code: "HIT_COLLAPSE",
      title: "Hit率急落",
      scope: "KPI vs 前週",
      cause_candidates: [`hit delta vs prev = ${vsPrev.hit}`],
      recommended_action:
        "Production Miss を確認。Research 提案は Evidence 必須。",
      production_impact: true,
    });
  }
  for (const key of ["rank710", "other_miss", "rank46"]) {
    const v = vsPrev[key];
    if (typeof v === "number" && v > 0) {
      push({
        category: "KPI",
        code: `${key.toUpperCase()}_UP`,
        title: `${key}増加`,
        scope: "KPI vs 前週",
        cause_candidates: [`${key} delta = ${v}`],
        recommended_action:
          "Miss Evidence の該当カテゴリを確認。PE/CE 変更禁止。",
        production_impact: true,
      });
    }
  }
  if (typeof vsPrev.purchase === "number" && vsPrev.purchase < 0) {
    push({
      category: "KPI",
      code: "PURCHASE_WORSE",
      title: "Purchase成績悪化",
      scope: "KPI vs 前週",
      cause_candidates: [`purchase delta = ${vsPrev.purchase}`],
      recommended_action: "購入ロジックは触らず Evidence を蓄積。",
      production_impact: true,
    });
  }

  return { incidents, has_incident: incidents.length > 0 };
}

export function formatIncidentMarkdown(bundle) {
  const lines = [
    `# Incident Report — ${bundle.week_id}`,
    ``,
    `**Baseline Lock:** Version${BASELINE_LOCK}  `,
    `**Generated:** ${bundle.generated_at}  `,
    `**Incident count:** ${bundle.incidents.length}`,
    ``,
  ];
  for (const inc of bundle.incidents) {
    lines.push(
      `## [${inc.code}] ${inc.title}`,
      ``,
      `| 項目 | 内容 |`,
      `|------|------|`,
      `| 発生日時 | ${inc.occurred_at} |`,
      `| カテゴリ | ${inc.category} |`,
      `| 影響範囲 | ${inc.scope} |`,
      `| Productionへの影響 | ${inc.production_impact ? "有" : "無"} |`,
      ``,
      `### 原因候補`,
      ``,
      ...(inc.cause_candidates || []).map((c) => `- ${c}`),
      ``,
      `### 推奨対応`,
      ``,
      `${inc.recommended_action}`,
      ``
    );
  }
  return lines.join("\n");
}
