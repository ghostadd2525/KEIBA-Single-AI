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
    assert.ok(p.factor_lines.some((l) => /Pool|Entry|RePick|CE/.test(l)));
    assert.ok(p.trace_lines.length >= 1);
    const reply = formatExplainPickReply(p, { place: "新潟 6R" });
    assert.match(reply, /決定打/);
    assert.match(reply, /判断トレース/);
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
    assert.equal(res.intent, undefined);
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
    assert.match(res.reply, /決定打/);
    assert.match(res.reply, /Pool|RePick|CE/);
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
  it("v2_explain は false", () => {
    const beta = readJson("config/beta.json");
    assert.equal(beta.ui_features.v2_explain, false);
  });
});
