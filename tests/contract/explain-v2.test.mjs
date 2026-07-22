import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mapPiPredictionToBundle } from "../../functions/_lib/piPredictionMapper.js";
import {
  buildExplainV21,
  buildHonmeiReason,
  legacyCompat,
} from "../../functions/_lib/explainBuilder.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function readJson(rel) {
  return JSON.parse(readFileSync(join(ROOT, rel), "utf8"));
}

const baseFixture = readJson("fixtures/pi-prediction/niigata-6r.json");

function withExplainPayload(fixture) {
  const pred = fixture.prediction;
  return {
    ...fixture,
    prediction: {
      ...pred,
      explain_payload: {
        schema_version: "core-explain-payload/1.0",
        honmei_candidate_id: "コルドンブルー",
        decision_key: {
          key: "ce_rank1_gap_lead",
          kind: "candidate_evaluation",
          label: "CE 1 位・2 位差最大",
          text: "2 位との勝率差が最も大きい",
          evidence: { model_rank: 1, win_prob: 0.0977, gap12: 0.0044 },
        },
        ranking_evidence: {
          rank: 1,
          win_prob: 0.0977,
          gap_to_next: 0.0044,
          horse_number: 4,
        },
        world: { world: "midupper_world", sub_world: "midupper_route" },
        confidence_meta: {
          gap12: 0.0044,
          entropy: 2.88,
          top1_prob: 0.0977,
          field_size: 16,
        },
        confidence_components: [
          { key: "top1_prob", value: 0.0977, weight: 0.55, contribution: 0.7 },
          { key: "gap12", value: 0.0044, weight: 0.25, contribution: 0.15 },
          { key: "entropy", value: 2.88, weight: 0.2, contribution: 0.15 },
        ],
        confidence_band: "low",
        overall_confidence: 0.055,
        decision_trace_stages: [
          {
            stage: "candidate_evaluation",
            status: "applied",
            delta: { summary: "CE 1 位: 4 番コルドンブルー" },
          },
          {
            stage: "delete",
            status: "locked",
            delta: { summary: "Delete Boundary — 変更禁止" },
          },
          {
            stage: "mark_assignment",
            status: "applied",
            delta: { summary: "Rank1 → ◎（honmei）" },
          },
        ],
        required_role: { race_required_pick: 2, spread_need_label: "strong_spread" },
        product_stages: null,
        pipeline_version: "ai-core-migrated/1.0-phase1",
      },
    },
  };
}

describe("explainBuilder / Flag OFF 恒等", () => {
  it("Flag OFF: explain は空 reasons/narrative（v1.1）", () => {
    const bundle = mapPiPredictionToBundle(withExplainPayload(baseFixture), null, {
      explainV2Enabled: false,
    });
    assert.ok(bundle);
    assert.deepEqual(bundle.explain.reasons, []);
    assert.equal(bundle.explain.narrative, "");
    assert.equal(bundle.explain.reason, undefined);
    assert.equal(bundle.explain.confidence_reason, undefined);
    assert.equal(bundle.explain.decision_trace, undefined);
  });

  it("ペイロード無し Flag ON: 空 explain", () => {
    const bundle = mapPiPredictionToBundle(baseFixture, null, {
      explainV2Enabled: true,
    });
    assert.ok(bundle);
    assert.deepEqual(bundle.explain.reasons, []);
    assert.equal(bundle.explain.narrative, "");
  });
});

describe("explainBuilder / Flag ON explain 2.1", () => {
  it("reason.decision_key + confidence contribution/weight + decision_trace", () => {
    const fixture = withExplainPayload(baseFixture);
    const bundle = mapPiPredictionToBundle(fixture, null, {
      explainV2Enabled: true,
    });
    assert.ok(bundle);
    assert.equal(bundle.explain.schema_version, "single-explain/2.1");
    assert.ok(bundle.explain.reason);
    assert.equal(bundle.explain.reason.decision_key.key, "ce_rank1_gap_lead");
    assert.ok(bundle.explain.reason.summary);
    assert.ok(bundle.explain.confidence_reason);
    const comps = bundle.explain.confidence_reason.components;
    assert.ok(comps.some((c) => c.key === "gap12" && c.contribution != null && c.weight != null));
    assert.ok(bundle.explain.decision_trace);
    assert.ok(
      bundle.explain.decision_trace.stages.every(
        (s) => s.stage && s.status && s.delta && typeof s.delta.summary === "string"
      )
    );
    // legacy compat
    assert.ok(bundle.explain.reasons.length >= 1);
    assert.ok(bundle.explain.narrative);
    // not a PredictionBundle dump of explain_payload
    assert.equal(bundle.explain_payload, undefined);
  });

  it("legacyCompat は reasons[] / narrative を生成", () => {
    const reason = buildHonmeiReason(withExplainPayload(baseFixture).prediction, {
      candidate_id: "c04",
      horse_number: 4,
      horse_name: "コルドンブルー",
      mark: "honmei",
      win_prob: 0.0977,
    });
    const legacy = legacyCompat({ reason });
    assert.equal(legacy.reasons[0].horse_number, 4);
    assert.ok(legacy.reasons[0].bullets.length);
    assert.ok(legacy.narrative);
  });

  it("buildExplainV21 enabled=false は空", () => {
    const ex = buildExplainV21({
      piPred: withExplainPayload(baseFixture).prediction,
      honmeiRunner: { horse_number: 4, horse_name: "A", mark: "honmei" },
      aiConfidence: { score: 0.05, band: "low" },
      enabled: false,
    });
    assert.deepEqual(ex.reasons, []);
    assert.equal(ex.narrative, "");
  });
});

describe("Explainability Phase 2 — Pool / Entry / RePick", () => {
  function withProductStages(fixture) {
    const base = withExplainPayload(fixture);
    const product_stages = [
      {
        stage: "candidate_pool",
        status: "applied",
        timestamp: "2026-07-21T04:00:01.123Z",
        delta: {
          summary: "Pool+Entry (PE-V2-A): rank11 サンプルホース を Pool に追加",
          reason_codes: ["pe_v2_a", "pe_insert"],
          before: { pool_size: 8 },
          after: { pool_size: 9 },
          inputs: { facet: "PE-V2-A", cand_name: "サンプルホース", cand_rank: 11 },
          outputs: { fired: true, inserted: true },
        },
      },
      {
        stage: "entry",
        status: "applied",
        timestamp: "2026-07-21T04:00:01.123Z",
        delta: {
          summary: "Entry (PE-V2-A): サンプルホース（rank11）を Entry 登録",
          reason_codes: ["pe_v2_a", "pe_insert"],
          before: { pool_size: 8 },
          after: { pool_size: 9, inserted: true },
          outputs: { inserted: true },
        },
      },
      {
        stage: "repick",
        status: "applied",
        timestamp: "2026-07-21T04:00:01.123Z",
        delta: {
          summary: "NEAR rescue: rank9 NEAR馬 → repick membership",
          reason_codes: ["rv2_near", "rp_v2_a", "rp_displaced"],
          before: { in_repick: 0, surv_pos: 10 },
          after: { in_repick: 1, displaced: true },
          inputs: { N: 8, victim_rank: 11 },
          outputs: { displaced: true },
        },
      },
    ];
    base.prediction.explain_payload.product_stages = product_stages;
    base.prediction.explain_payload.decision_trace_stages = [
      ...base.prediction.explain_payload.decision_trace_stages,
      {
        stage: "candidate_pool",
        status: "not_applied",
        delta: { summary: "Product Pool 未配線（PI CE 経路）" },
      },
      {
        stage: "entry",
        status: "not_applied",
        delta: { summary: "Product Entry 未配線（PI CE 経路）" },
      },
      {
        stage: "repick",
        status: "not_applied",
        delta: { summary: "RePick 未実行" },
      },
    ];
    base.prediction.explain_payload.pipeline_version = "ai-core-migrated/1.0-phase2";
    return base;
  }

  it("Flag OFF は product_stages があっても空 explain（v1.1 恒等）", () => {
    const bundle = mapPiPredictionToBundle(withProductStages(baseFixture), null, {
      explainV2Enabled: false,
    });
    assert.deepEqual(bundle.explain.reasons, []);
    assert.equal(bundle.explain.reason, undefined);
    assert.equal(bundle.explain.decision_trace, undefined);
  });

  it("Flag ON: decision_trace に Pool/Entry/RePick applied + timestamp", () => {
    const bundle = mapPiPredictionToBundle(withProductStages(baseFixture), null, {
      explainV2Enabled: true,
    });
    assert.equal(bundle.explain.meta.explain_phase, 2);
    const by = Object.fromEntries(
      bundle.explain.decision_trace.stages.map((s) => [s.stage, s])
    );
    assert.equal(by.candidate_pool.status, "applied");
    assert.equal(by.entry.status, "applied");
    assert.equal(by.repick.status, "applied");
    assert.equal(by.repick.timestamp, "2026-07-21T04:00:01.123Z");
    assert.ok(by.repick.delta.reason_codes.includes("rv2_near"));
  });

  it("Flag ON: reason.factors に Pool / Entry / RePick 理由", () => {
    const bundle = mapPiPredictionToBundle(withProductStages(baseFixture), null, {
      explainV2Enabled: true,
    });
    const labels = bundle.explain.reason.factors.map((f) => f.label);
    assert.ok(labels.includes("Pool 理由"));
    assert.ok(labels.includes("Entry 理由"));
    assert.ok(labels.includes("RePick 理由"));
    const repick = bundle.explain.reason.factors.find((f) => f.kind === "repick");
    assert.ok(repick);
    assert.match(repick.text, /NEAR rescue/);
  });

  it("product 無し Flag ON は Phase 1（product_stages null・explain_phase 1）", () => {
    const bundle = mapPiPredictionToBundle(withExplainPayload(baseFixture), null, {
      explainV2Enabled: true,
    });
    assert.equal(bundle.explain.meta.explain_phase, 1);
    assert.ok(bundle.explain.reason);
    assert.ok(!bundle.explain.reason.factors.some((f) => f.label === "Pool 理由"));
  });
});
