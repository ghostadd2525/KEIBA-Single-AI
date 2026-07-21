/**
 * Phase7 — Real AI PredictionBundle 品質検証
 *
 * 前提: AI_ENGINE=real で生成済み JSON が docs/phase7/artifacts/ にあること。
 * または --generate で Python 側生成を呼び出す（別プロセス推奨）。
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { validateWithSchema } from "../contracts/lib/schema-validate.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const ART = path.join(ROOT, "docs", "phase7", "artifacts");
const SCHEMA = JSON.parse(
  fs.readFileSync(path.join(ROOT, "contracts/single-prediction-bundle/2.0/schema.json"), "utf8")
);
const MOCK = JSON.parse(
  fs.readFileSync(path.join(ROOT, "public/data/mocks/bundle-20260719_hanshin_11.json"), "utf8")
);
const ANALYSIS = JSON.parse(
  fs.readFileSync(path.join(ROOT, "public/data/mocks/analysis.json"), "utf8")
);

function scorePercent(bundle) {
  const c = (bundle && bundle.ai_confidence) || {};
  if (typeof c.score === "number") {
    return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
  }
  return null;
}

function honmei(bundle) {
  const runners = (((bundle || {}).evaluation || {}).runners) || [];
  return runners.find((r) => r.mark === "honmei") || runners[0] || null;
}

/** UI bind が参照する必須フィールド（ui-api-mapping / prediction-bind） */
function checkUiBind(bundle) {
  const issues = [];
  const info = bundle.race_info || {};
  if (!bundle.race_id) issues.push("race_id missing");
  if (!info.venue) issues.push("race_info.venue missing (title/card)");
  if (info.race_no == null) issues.push("race_info.race_no missing");
  if (!info.class_label) issues.push("race_info.class_label missing (card name)");
  if (!info.post_time) issues.push("race_info.post_time missing (card meta; UI shows —)");
  if (!info.date && !info.date_label) issues.push("race_info.date/date_label missing (date tabs)");
  if (typeof scorePercent(bundle) !== "number") issues.push("ai_confidence.score not numeric");
  const h = honmei(bundle);
  if (!h) issues.push("no runners for honmei card");
  else {
    if (h.horse_number == null) issues.push("honmei.horse_number missing");
    if (!h.horse_name) issues.push("honmei.horse_name missing");
  }
  if (!(bundle.explain && bundle.explain.narrative)) {
    issues.push("explain.narrative missing (pace-card text)");
  }
  const items = (bundle.betting_recommendations || {}).items || [];
  if (!items.length) issues.push("betting_recommendations.items empty (strategy CTA still works)");
  return { ok: issues.filter((i) => !i.includes("empty") && !i.includes("post_time")).length === 0, issues };
}

/** Kaoba generateKaobaReply が参照するフィールド */
function checkKaobaRefs(bundle, raceId) {
  const issues = [];
  const info = bundle.race_info || {};
  const h = honmei(bundle);
  const conf = scorePercent(bundle);
  if (!info.venue && info.race_no == null) issues.push("Kaoba place string weak");
  if (!h) issues.push("Kaoba honmei unavailable");
  if (conf == null) issues.push("Kaoba confidence unavailable");
  const analysisRow = ANALYSIS[raceId];
  const analysisConnected = Boolean(analysisRow && Array.isArray(analysisRow.charts) && analysisRow.charts.length);
  return {
    ok: issues.length === 0,
    issues,
    analysis_row_present: Boolean(analysisRow),
    analysis_charts_connected: analysisConnected,
    sample_reply_bits: {
      place: `${info.venue || ""} ${info.race_no != null ? info.race_no + "R" : ""}`.trim(),
      honmei: h ? `${h.horse_number} ${h.horse_name || ""}`.trim() : null,
      conf,
      narrative: (bundle.explain && bundle.explain.narrative) || "",
    },
  };
}

/** Analysis 未接続（mock map に無い / デフォルト）時の挙動 */
function checkAnalysisDisconnected(raceId) {
  const row = ANALYSIS[raceId];
  if (!row) {
    return {
      status: "disconnected_default",
      note: "analysis.json にキー無し → charts デフォルト or 空、narrative 空/準備中。レーダーは静的寄り",
    };
  }
  return {
    status: "mock_connected",
    note: "mock analysis.json に行あり（実AI Analysis ではない）",
    overall: row.overall,
    charts: (row.charts || []).length,
  };
}

function mockDiff(real) {
  const fields = [
    ["schema_version", MOCK.schema_version, real.schema_version],
    ["model_version", MOCK.model_version, real.model_version],
    ["product_version", MOCK.product_version, real.product_version],
    ["core_version", MOCK.core_version, real.core_version],
    ["evaluation.world", MOCK.evaluation?.world, real.evaluation?.world],
    ["evaluation.runners_count", MOCK.evaluation?.runners?.length, real.evaluation?.runners?.length],
    ["ai_confidence.score", MOCK.ai_confidence?.score, real.ai_confidence?.score],
    ["ai_confidence.band", MOCK.ai_confidence?.band, real.ai_confidence?.band],
    ["ai_confidence.inputs_ref", !!MOCK.ai_confidence?.inputs_ref, !!real.ai_confidence?.inputs_ref],
    ["explain.reasons_count", MOCK.explain?.reasons?.length, real.explain?.reasons?.length],
    ["betting.items_count", MOCK.betting_recommendations?.items?.length, real.betting_recommendations?.items?.length],
    ["race_info.post_time", MOCK.race_info?.post_time, real.race_info?.post_time],
    ["race_info.bg", MOCK.race_info?.bg, real.race_info?.bg],
    ["race_info.date_label", MOCK.race_info?.date_label, real.race_info?.date_label],
  ];
  return fields.map(([k, m, r]) => ({
    field: k,
    mock: m,
    real: r,
    same: JSON.stringify(m) === JSON.stringify(r),
  }));
}

function mockOnlyDisplayItems() {
  return [
    {
      item: "race_info.bg / date_label / date_full",
      reason: "UI 補助。Real は catalog 経由時のみ付与、Core 直 ID では欠落しやすい",
    },
    {
      item: "race_info.post_time",
      reason: "Race Data / Core に発走時刻が無いため Real では空→UI は「—発走」",
    },
    {
      item: "evaluation.world / sub_world",
      reason: "prediction_response に未含有。mapper は null",
    },
    {
      item: "ai_confidence.component_scores / rich inputs_ref",
      reason: "Mock はダミー詳細。Real は factors 中心",
    },
    {
      item: "explain.reasons[].bullets のリッチ文",
      reason: "Mock は手書き説明。Real は順位・スコア要約",
    },
    {
      item: "pace-dot / heatmap / ROI ダッシュ",
      reason: "PB 外の静的モック。Real 接続でも変わらない",
    },
    {
      item: "Analysis レーダー・評価バーのレース固有値",
      reason: "Analysis 実AI未接続。mock map キー一致時のみ mock 値",
    },
  ];
}

function schemaCheck(bundle) {
  return validateWithSchema(SCHEMA, bundle);
}

function main() {
  if (!fs.existsSync(ART)) {
    console.error("artifacts missing:", ART);
    process.exit(1);
  }
  const files = fs
    .readdirSync(ART)
    .filter((f) => f.startsWith("bundle-") && f.endsWith(".json"))
    .sort();
  if (!files.length) {
    console.error("no bundle-*.json in artifacts");
    process.exit(1);
  }

  const races = [];
  for (const f of files) {
    const bundle = JSON.parse(fs.readFileSync(path.join(ART, f), "utf8"));
    const schema = schemaCheck(bundle);
    const ui = checkUiBind(bundle);
    const kaoba = checkKaobaRefs(bundle, bundle.race_id);
    const analysis = checkAnalysisDisconnected(bundle.race_id);
    const diff = mockDiff(bundle);
    const source =
      String(bundle.product_version || "").includes("single-ai") ||
      String(bundle.model_version || "").includes("core")
        ? "real_ai"
        : String(bundle.model_version || "").includes("dummy") ||
            String(bundle.product_version || "").includes("prototype")
          ? "mock_fallback"
          : "unknown";

    races.push({
      file: f,
      race_id: bundle.race_id,
      source,
      schema,
      contract: {
        ok: schema.ok && bundle.schema_version === "single-prediction-bundle/2.0",
        schema_version: bundle.schema_version,
        required_top_level: [
          "schema_version",
          "race_id",
          "race_info",
          "evaluation",
          "ai_confidence",
          "explain",
          "betting_recommendations",
        ].every((k) => k in bundle),
      },
      ui,
      kaoba,
      analysis,
      metrics: {
        runners: (bundle.evaluation?.runners || []).length,
        bet_items: (bundle.betting_recommendations?.items || []).length,
        conf_score: bundle.ai_confidence?.score ?? null,
        conf_pct: scorePercent(bundle),
        honmei: (() => {
          const h = honmei(bundle);
          return h
            ? { horse_number: h.horse_number, horse_name: h.horse_name, mark: h.mark }
            : null;
        })(),
        warnings: bundle.warnings || [],
      },
      mock_diff: diff,
    });
  }

  const report = {
    phase: "Phase7 Validation",
    generated_at: new Date().toISOString(),
    artifact_dir: "docs/phase7/artifacts",
    summary: {
      bundles: races.length,
      schema_pass: races.filter((r) => r.schema.ok).length,
      contract_pass: races.filter((r) => r.contract.ok).length,
      real_ai: races.filter((r) => r.source === "real_ai").length,
      mock_fallback: races.filter((r) => r.source === "mock_fallback").length,
      ui_hard_fail: races.filter((r) => r.ui.issues.some((i) => i.includes("missing") && !i.includes("post_time") && !i.includes("empty"))).length,
    },
    races,
    mock_only_display_items: mockOnlyDisplayItems(),
    wishlist_for_pb_not_changing_contract: [
      "evaluation.world / sub_world（Core CE から投影）",
      "race_info.post_time（Race Data 拡張）",
      "per-horse explain の要因上位（XAI）",
      "confidence component_scores の実値",
      "betting item への推定配当帯（市場データ依存）",
    ],
    gaps_beyond_pb: [
      "Analysis charts / overall / narrative（別契約）",
      "オッズ時系列・変動AI",
      "UserStats（ROI / ランキング）",
      "結果確定・払戻",
      "展開位置取り（pace-dot）モデル出力",
      "Kaoba LLM 文脈（現状 rule + mock bundle 読取経路あり）",
    ],
    analysis_real_ai_challenges: [
      "RealAiAnalysisSource 未実装（常に mock/default）",
      "PB.race_id と analysis.json キー不一致時はデフォルト charts",
      "Core 特徴量 → charts 5軸への射影仕様が未定義",
      "Kaoba loadKaobaRefs が BFF mock 直読のままなら実PBを見ない（Adapter 経路要確認）",
    ],
    tech_debt: [
      "AI_ENGINE はプロセス起動時固定（モジュール import 時）",
      "list_bundles で未解決レースは Mock 混在（source ラベル無し）",
      "resolve_core_race_id が predict_ranking を複数回呼びレイテンシ大",
      "Kaoba BFF refs が ASSETS mock 依存の可能性",
      "Confidence/Ticket BFF が Adapter 未統一",
      "pandas/Core CSV 依存で Docker 単体では実推論不可",
    ],
  };

  const outJson = path.join(ROOT, "docs/phase7/validation-report.json");
  fs.mkdirSync(path.dirname(outJson), { recursive: true });
  fs.writeFileSync(outJson, JSON.stringify(report, null, 2), "utf8");
  console.log(JSON.stringify(report.summary, null, 2));
  console.log("wrote", outJson);
}

main();
