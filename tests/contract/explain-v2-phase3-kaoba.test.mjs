/**
 * Explainability Phase 3 — Kaoba explain_pick + Flag OFF 恒等
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  canExplainPick,
  formatExplainPickReply,
  isExplainPickIntent,
  isV2ExplainContext,
  projectExplainForPick,
} from "../../functions/_lib/explainPick.js";
import { generateKaobaReply } from "../../functions/_lib/kaobaDomain.js";
import { mapPiPredictionToBundle } from "../../functions/_lib/piPredictionMapper.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function readJson(rel) {
  return JSON.parse(readFileSync(join(ROOT, rel), "utf8"));
}

const phase2Sample = readJson("fixtures/explain/v2-explain-phase2-sample.json");
const baseFixture = readJson("fixtures/pi-prediction/niigata-6r.json");

function bundleWithExplain() {
  return {
    race_id: phase2Sample.race_id,
    race_info: { venue: "新潟", race_no: 6 },
    evaluation: phase2Sample.evaluation,
    ai_confidence: phase2Sample.ai_confidence,
    explain: phase2Sample.explain,
  };
}

describe("explainPick helpers", () => {
  it("isExplainPickIntent は なぜ/理由 を検出", () => {
    assert.equal(isExplainPickIntent("なぜ本命なの？"), true);
    assert.equal(isExplainPickIntent("選定理由を教えて"), true);
    assert.equal(isExplainPickIntent("買い目を提案して"), false);
  });

  it("v2_explain context のみ true", () => {
    assert.equal(isV2ExplainContext({ v2_explain: true }), true);
    assert.equal(isV2ExplainContext({ ui_features: { v2_explain: true } }), true);
    assert.equal(isV2ExplainContext({}), false);
    assert.equal(isV2ExplainContext({ v2_explain: false }), false);
  });

  it("projectExplainForPick は decision_key / factors / trace を投影", () => {
    const p = projectExplainForPick(phase2Sample.explain);
    assert.ok(p);
    assert.equal(p.explain_phase, 3);
    assert.equal(p.schema_version, "single-explain-pick/1.0");
    assert.ok(p.decision_key.label);
    // factor_lines は reason.factors の「ラベル: 本文」をそのまま投影する
    // （サンプル fixture のラベルがそのまま現れることを固定する）
    assert.ok(p.factor_lines.some((l) => l.startsWith("CE 評価:")));
    assert.ok(p.factor_lines.length >= 2);
    assert.ok(p.trace_lines.length >= 1);
    const reply = formatExplainPickReply(p, { place: "新潟 6R" });
    // 現行のユーザー向け文面（explainPick.js: 平易な理由文のみ）に合わせる
    assert.match(reply, /いちばん効いたのは/);
    assert.match(reply, /ポイント:/);
    assert.match(reply, /自信の目安:/);
    // 内部用語（決定打・判断トレース・ステージ名）は返信に出さない
    assert.doesNotMatch(reply, /決定打|判断トレース/);
    assert.doesNotMatch(reply, /candidate_pool|repick|ステージ/);
  });
});

describe("Kaoba explain_pick / Flag OFF 恒等", () => {
  it("Flag OFF（context なし）: explain があっても explain_pick 注入しない", () => {
    const res = generateKaobaReply({
      message: "なぜ本命なの？理由を教えて",
      race_id: "2026-07-25-01-06",
      context: { ui: "chat" },
      refs: { race_id: "2026-07-25-01-06", bundle: bundleWithExplain() },
    });
    // intent と explain_pick は別の意味を持つフィールド
    // （kaobaDomain.js:237-242）: intent は発話の意図分類であり、
    // explain_pick 注入時は "explain_pick" が入るが、未注入でも
    // 意図分類（例: why_honmei）が入り得る。したがって intent は
    // 未注入の根拠として扱わず、explain_pick 自体を直接検証する。
    // 未注入時の表現は「プロパティ自体が存在しない」形
    // （out への代入は注入時にのみ行われる）。
    assert.equal(
      Object.prototype.hasOwnProperty.call(res, "explain_pick"),
      false
    );
    assert.equal(res.explain_pick, undefined);
    assert.doesNotMatch(res.reply, /判断トレース/);
  });

  it("Flag ON: explain_pick に reason / decision_trace を注入", () => {
    assert.equal(
      canExplainPick({
        message: "なぜ◎なの？",
        context: { v2_explain: true },
        refs: { bundle: bundleWithExplain() },
      }),
      true
    );
    const res = generateKaobaReply({
      message: "なぜ本命なの？理由を教えて",
      race_id: "2026-07-25-01-06",
      context: { v2_explain: true, ui: "chat" },
      refs: { race_id: "2026-07-25-01-06", bundle: bundleWithExplain() },
    });
    assert.equal(res.intent, "explain_pick");
    assert.ok(res.explain_pick);
    assert.equal(res.explain_pick.explain_phase, 3);
    assert.ok(res.explain_pick.factor_lines.length >= 1);
    assert.ok(res.explain_pick.trace_lines.length >= 1);
    // 返信文は現行の平易なユーザー向け表現（結論→理由→補足）に従う
    assert.match(res.reply, /を◎にした一番の理由は/);
    // 内部用語（決定打・判断トレース・ステージ名）は返信に出さない
    assert.doesNotMatch(res.reply, /決定打|判断トレース/);
    assert.doesNotMatch(res.reply, /candidate_pool|repick|ステージ/);
    assert.equal(res.schema_version, "expect-kaoba/1.0");
  });

  it("Flag ON でも reason 無しなら v1.1 経路（注入なし）", () => {
    const res = generateKaobaReply({
      message: "なぜ本命なの？",
      context: { v2_explain: true },
      refs: {
        race_id: "x",
        bundle: {
          race_id: "x",
          race_info: { venue: "新潟", race_no: 6 },
          explain: { reasons: [], narrative: "" },
          evaluation: { runners: [{ horse_number: 4, mark: "honmei", horse_name: "A" }] },
          ai_confidence: { score: 0.1 },
        },
      },
    });
    assert.equal(res.explain_pick, undefined);
  });

  it("BFF Flag OFF: mapper は空 explain（kaoba_ready なし）", () => {
    const bundle = mapPiPredictionToBundle(baseFixture, null, {
      explainV2Enabled: false,
    });
    assert.equal(bundle.explain.reason, undefined);
    assert.equal(bundle.explain.meta && bundle.explain.meta.kaoba_ready, undefined);
  });
});

describe("beta.json Flag", () => {
  // Flag の契約は 2 層に分かれる（実値を検証するものではない）:
  //  - コード既定値: betaConfig.js の DEFAULTS では OFF（未設定時は安全側）
  //  - 本番設定値: config/beta.json は Release Version 2（commit 03e7a4f5）で
  //    Pages 自動反映により v1.1 へ巻き戻らないよう意図的に ON
  // したがって config の実値を false と断言せず、両層の前提を別々に固定する。
  it("コード既定値: betaConfig.js の v2_explain は OFF", () => {
    const src = readFileSync(
      join(ROOT, "functions/_lib/betaConfig.js"),
      "utf8"
    );
    const m = src.match(/v2_explain:\s*(true|false)/);
    assert.ok(m, "betaConfig.js に v2_explain 既定値が存在する");
    assert.equal(m[1], "false");
  });

  it("本番設定: config/beta.json の v2_explain は存在し boolean（実値は検証しない）", () => {
    const beta = readJson("config/beta.json");
    assert.equal(typeof beta.ui_features.v2_explain, "boolean");
  });
});
