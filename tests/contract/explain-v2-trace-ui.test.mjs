/**
 * Explainability — decision_trace 折りたたみ UI（設計書 §2 / §5.3）
 *
 * 検証範囲は表示契約のみ。decision_trace のデータ生成・保持契約は
 * explain-v2.test.mjs / explain-v2-e2e.test.mjs 側で検証する。
 * - Flag ON + 有効な trace → <details class="explain-trace"> で段階表示
 * - 内部 stage ID / reason code / 生データをユーザー向けに出さない
 * - summary が空・内部コードのみの段階は出さず、有効な段階が無ければ
 *   折りたたみ自体を生成しない
 * - Flag OFF / trace 欠損では従来表示のまま
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function loadBind(v2ExplainEnabled) {
  const code = readFileSync(
    join(ROOT, "public/assets/api/prediction-bind.js"),
    "utf8"
  );
  const sandbox = {
    window: null,
    document: {
      body: { classList: { add() {}, remove() {} } },
      getElementById() {
        return null;
      },
      querySelector() {
        return null;
      },
      createElement() {
        return { className: "", textContent: "", parentNode: null };
      },
    },
    console,
    ExpectUiFeatures: {
      enabled(name) {
        if (name === "v2_explain") return !!v2ExplainEnabled;
        return false;
      },
    },
  };
  sandbox.window = sandbox;
  sandbox.global = sandbox;
  vm.runInNewContext(code, sandbox);
  return sandbox.ExpectPredictionBind;
}

function bundleWithTrace(stages) {
  return {
    race_id: "2026-07-25-01-06",
    explain: {
      schema_version: "single-explain/2.1",
      reason: {
        horse_number: 4,
        horse_name: "コルドンブルー",
        summary: "4番コルドンブルーを◎にしたのは、AI予測では1番手のため。",
        decision_key: { key: "ce_rank1_gap_lead", label: "AI予測1位", text: "" },
        factors: [],
      },
      confidence_reason: { summary: "信頼度は低めです。", components: [] },
      decision_trace: {
        schema_version: "single-decision-trace/1.0",
        pipeline_version: "ai-core-migrated/1.0-phase1",
        stages,
      },
      reasons: [],
      narrative: "",
    },
  };
}

const validStages = [
  {
    stage: "candidate_evaluation",
    status: "applied",
    delta: { summary: "CE 1 位: 4 番コルドンブルー（勝率 6.6%）" },
  },
  {
    stage: "world_classification",
    status: "applied",
    delta: { summary: "midupper_world / midupper_route" },
  },
  {
    stage: "mark_assignment",
    status: "applied",
    delta: { summary: "1 位の馬に ◎ を付けた" },
  },
];

describe("decision_trace 折りたたみ UI", () => {
  it("Flag ON: 有効な trace を <details class=explain-trace> で段階表示する", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(bundleWithTrace(validStages));
    assert.match(html, /<details class="explain-trace">/);
    assert.match(html, /<summary>詳しく見る（◎を選んだ流れ）<\/summary>/);
    assert.match(html, /explain-trace-list/);
    assert.match(html, /AI予測/);
    assert.match(html, /レース傾向の判定/);
    assert.match(html, /印の付与/);
    // 既存要素（要約・信頼度・Kaoba 導線）も維持される
    assert.match(html, /explain-summary/);
    assert.match(html, /explain-confidence/);
    assert.match(html, /explain-kaoba-cta/);
  });

  it("内部 stage ID・世界コード・reason code を露出しない", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        ...validStages,
        {
          stage: "candidate_pool",
          status: "applied",
          delta: { summary: "candidate_pool で rv2_near を適用した" },
          timestamp: "2026-07-21T04:00:01.123Z",
        },
      ])
    );
    assert.doesNotMatch(html, /candidate_pool/);
    assert.doesNotMatch(html, /candidate_evaluation/);
    assert.doesNotMatch(html, /world_classification/);
    assert.doesNotMatch(html, /mark_assignment/);
    assert.doesNotMatch(html, /midupper_world/);
    assert.doesNotMatch(html, /rv2_near/);
    assert.doesNotMatch(html, /2026-07-21T04:00:01/);
  });

  it("未知の stage / status は内部値を出さず、汎用ラベルまたは無表示にする", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        { stage: "mystery_stage", status: "weird_status", delta: { summary: "何らかの判定を行った" } },
      ])
    );
    assert.match(html, /explain-trace/);
    assert.match(html, /判断ステップ/);
    assert.doesNotMatch(html, /mystery_stage/);
    assert.doesNotMatch(html, /weird_status/);
  });

  it("summary が空でも、有効な stage と status があればラベル＋状態を残す", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        { stage: "candidate_evaluation", status: "applied", delta: { summary: "" } },
        { stage: "entry", status: "not_applied", delta: {} },
      ])
    );
    assert.match(html, /<details class="explain-trace">/);
    assert.match(html, /AI予測/);
    assert.match(html, /\[適用\]/);
    assert.match(html, /候補への追加/);
    assert.match(html, /\[未適用\]/);
  });

  it("内部語を含む summary は本文を出さないが、段階ラベル＋状態は残る", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        {
          stage: "candidate_pool",
          status: "applied",
          delta: { summary: "candidate_pool で rv2_near を適用した" },
        },
        {
          stage: "mark_assignment",
          status: "applied",
          delta: { summary: "Rank1 → ◎（honmei）" },
        },
      ])
    );
    assert.match(html, /候補の絞り込み/);
    assert.match(html, /印の付与/);
    assert.doesNotMatch(html, /rv2_near/);
    assert.doesNotMatch(html, /honmei/);
  });

  it("欠損・不正な stage からは段階を作らず、有効な段階が無ければ折りたたみを作らない", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        { status: "applied", delta: { summary: "段階名なし" } },
        { stage: 42, status: "applied", delta: { summary: "数値の段階" } },
        null,
        "candidate_evaluation",
      ])
    );
    assert.doesNotMatch(html, /explain-trace/);
    assert.doesNotMatch(html, /段階名なし/);
  });

  it("元データの段階順序をそのまま維持する", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        { stage: "mark_assignment", status: "applied", delta: { summary: "1 位の馬に ◎ を付けた" } },
        { stage: "candidate_evaluation", status: "applied", delta: { summary: "AI予測で 1 位だった" } },
      ])
    );
    const traceHtml = html.slice(html.indexOf("explain-trace"));
    const markIdx = traceHtml.indexOf("印の付与");
    const ceIdx = traceHtml.indexOf("AI予測");
    assert.ok(markIdx !== -1 && ceIdx !== -1);
    assert.ok(markIdx < ceIdx);
  });

  it("purchase など根拠未確認のラベルは汎用ラベルにし、内部 ID を出さない", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        { stage: "purchase", status: "not_applied", delta: { summary: "Purchase 未配線" } },
      ])
    );
    assert.match(html, /判断ステップ/);
    assert.match(html, /\[未適用\]/);
    assert.doesNotMatch(html, /purchase/);
    assert.doesNotMatch(html, /購入判断/);
  });

  it("trace 欠損・空配列では折りたたみを作らない", () => {
    const bind = loadBind(true);
    const noTrace = bundleWithTrace([]);
    delete noTrace.explain.decision_trace;
    assert.doesNotMatch(bind.reasonsSectionHtml(noTrace), /explain-trace/);
    assert.doesNotMatch(
      bind.reasonsSectionHtml(bundleWithTrace([])),
      /explain-trace/
    );
  });

  it("XSS 文字列は HTML として挿入されない", () => {
    const bind = loadBind(true);
    const html = bind.reasonsSectionHtml(
      bundleWithTrace([
        {
          stage: "candidate_evaluation",
          status: "applied",
          delta: { summary: '<script>alert(1)</script> を含む説明' },
        },
      ])
    );
    assert.doesNotMatch(html, /<script>alert\(1\)<\/script>/);
    assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  });

  it("Flag OFF: trace があっても折りたたみは表示しない", () => {
    const bind = loadBind(false);
    const bundle = bundleWithTrace(validStages);
    bundle.explain.reasons = [{ horse_number: 4, bullets: ["従来の理由"] }];
    const html = bind.reasonsSectionHtml(bundle);
    assert.doesNotMatch(html, /explain-trace/);
    assert.match(html, /従来の理由/);
  });
});
