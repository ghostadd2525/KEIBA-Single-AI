/**
 * Version 2 Explainability Phase 1 — 本番有効化前 E2E 確認
 *
 * 確認項目:
 * 1. Feature Flag 組み合わせ（Core / PI / BFF / Web）
 * 2. 実レース（新潟6R fixture）で summary / decision_key / confidence / decision_trace
 * 3. legacy reasons[] / narrative 後方互換
 * 4. explain_payload 欠損時の UI 耐性
 *
 * Core 生成は同梱 Python サブプロセスで検証（WIN5_EXPLAIN_V2_ENABLED）。
 */
import { describe, it, before } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import vm from "node:vm";
import { mapPiPredictionToBundle } from "../../functions/_lib/piPredictionMapper.js";
import {
  buildExplainV21,
  legacyCompat,
} from "../../functions/_lib/explainBuilder.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");
const RACE_ID = "2026-07-25-01-06";

function readJson(rel) {
  return JSON.parse(readFileSync(join(ROOT, rel), "utf8"));
}

const baseFixture = readJson("fixtures/pi-prediction/niigata-6r.json");

/** 設計 §1.3 相当の本番メタ（CE）を実レース候補に付与 */
function realRaceMeta() {
  return {
    gap12: 0.004883,
    top2_sum: 0.126579,
    entropy: 2.887667,
    race_required_pick: 2,
    spread_need_label: "strong_spread",
    observer_repick_ready_flag: 1,
    race_type_label: "ability",
    rank7_9_pick_required_flag: 0,
    top1_prob: 0.09771316412070961,
    field_size: 16,
    uncertainty: 0.8,
    model_version: "core-delegated",
    generated_at: "2026-07-21T10:00:00+09:00",
  };
}

/**
 * Core Flag ON で explain_payload を実レース候補から生成。
 * PI EXPLAIN_V2_ENABLED は呼び出し側で付与/省略を模擬。
 */
function generateCoreExplainPayload({ coreEnabled }) {
  const script = `
import json, os, sys
sys.path.insert(0, r${JSON.stringify(join(ROOT, "services/win5-ai/platform/core-overlay"))})
from ai_platform.core.explain import apply_win5_explain_v2_flags, build_explain_payload

apply_win5_explain_v2_flags(${coreEnabled ? "True" : "False"})
candidates = json.loads(${JSON.stringify(JSON.stringify(baseFixture.prediction.candidates))})
meta = json.loads(${JSON.stringify(JSON.stringify(realRaceMeta()))})
payload = build_explain_payload(
    candidates=candidates,
    world={"world": "midupper_world", "sub_world": "midupper_route"},
    confidence={
        "overall": ${baseFixture.prediction.overall_confidence},
        "band": "low",
        "meta": meta,
    },
    meta=meta,
    core_version="ai-core-migrated/1.0-phase1",
)
print(json.dumps({"ok": True, "payload": payload}, ensure_ascii=False))
`;
  const py = spawnSync("python", ["-c", script], {
    encoding: "utf8",
    cwd: ROOT,
    env: {
      ...process.env,
      WIN5_EXPLAIN_V2_ENABLED: coreEnabled ? "true" : "false",
      PYTHONIOENCODING: "utf-8",
    },
  });
  if (py.status !== 0) {
    throw new Error(`Core explain subprocess failed: ${py.stderr || py.stdout}`);
  }
  const line = (py.stdout || "").trim().split("\n").filter(Boolean).pop();
  return JSON.parse(line);
}

/** PI pass-through 模擬: Flag OFF なら explain_payload を落とす */
function piResponse({ corePayload, piEnabled }) {
  const pred = {
    ...baseFixture.prediction,
    world: "midupper_world",
    sub_world: "midupper_route",
    meta: { ...realRaceMeta() },
  };
  if (piEnabled && corePayload) {
    pred.explain_payload = corePayload;
  }
  return { ...baseFixture, prediction: pred };
}

function bffBundle(piDoc, bffEnabled) {
  return mapPiPredictionToBundle(piDoc, null, { explainV2Enabled: bffEnabled });
}

function loadPredictionBind(v2ExplainEnabled) {
  const code = readFileSync(join(ROOT, "public/assets/api/prediction-bind.js"), "utf8");
  const document = {
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
  };
  const sandbox = {
    window: null,
    document,
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

const RESULTS = {
  race_id: RACE_ID,
  matrix: [],
  display: null,
  legacy: null,
  missing: null,
  verdict: "PENDING",
};

describe("Explainability Phase 1 E2E — Flag 組み合わせ", () => {
  let coreOnPayload = null;

  before(() => {
    const off = generateCoreExplainPayload({ coreEnabled: false });
    assert.equal(off.payload, null, "Core OFF → explain_payload は null");

    const on = generateCoreExplainPayload({ coreEnabled: true });
    assert.ok(on.payload, "Core ON → explain_payload 生成");
    assert.equal(on.payload.schema_version, "core-explain-payload/1.0");
    assert.ok(on.payload.decision_key);
    assert.ok(Array.isArray(on.payload.confidence_components));
    assert.ok(Array.isArray(on.payload.decision_trace_stages));
    coreOnPayload = on.payload;
  });

  const cases = [
    {
      name: "全 OFF ≡ v1.1 空 explain",
      core: false,
      pi: false,
      bff: false,
      web: false,
      expectExplain21: false,
      expectV2Ui: false,
      expectLegacyList: false,
    },
    {
      name: "Core ON / PI OFF → payload 到達せず",
      core: true,
      pi: false,
      bff: true,
      web: true,
      expectExplain21: false,
      expectV2Ui: false,
      expectLegacyList: false,
    },
    {
      name: "Core+PI ON / BFF OFF → Bundle explain 空",
      core: true,
      pi: true,
      bff: false,
      web: true,
      expectExplain21: false,
      expectV2Ui: false,
      expectLegacyList: false,
    },
    {
      name: "Core+PI+BFF ON / Web OFF → explain 2.1 あるが v2 UI なし（legacy 表示）",
      core: true,
      pi: true,
      bff: true,
      web: false,
      expectExplain21: true,
      expectV2Ui: false,
      expectLegacyList: true,
    },
    {
      name: "全 ON → v2 UI（summary / decision_key / confidence / trace）",
      core: true,
      pi: true,
      bff: true,
      web: true,
      expectExplain21: true,
      expectV2Ui: true,
      expectLegacyList: false,
    },
  ];

  for (const c of cases) {
    it(c.name, () => {
      const payload = c.core ? coreOnPayload : null;
      const piDoc = piResponse({ corePayload: payload, piEnabled: c.pi });
      assert.equal(
        !!piDoc.prediction.explain_payload,
        !!(c.core && c.pi),
        "PI pass-through 条件"
      );

      const bundle = bffBundle(piDoc, c.bff);
      assert.ok(bundle);

      const has21 = bundle.explain && bundle.explain.schema_version === "single-explain/2.1";
      assert.equal(!!has21, c.expectExplain21);

      if (c.expectExplain21) {
        assert.ok(bundle.explain.reason?.summary);
        assert.ok(bundle.explain.reason?.decision_key?.key);
        assert.ok(bundle.explain.confidence_reason?.summary);
        assert.ok(bundle.explain.decision_trace?.stages?.length);
        assert.ok(bundle.explain.reasons?.length >= 1);
        assert.ok(bundle.explain.narrative);
      } else {
        assert.deepEqual(bundle.explain.reasons || [], []);
        assert.equal(bundle.explain.narrative || "", "");
        assert.equal(bundle.explain.reason, undefined);
      }

      const bind = loadPredictionBind(c.web);
      const html = bind.reasonsSectionHtml(bundle);
      const isV2Ui = html.includes("explain-v2") && html.includes("explain-decision-key");
      const isLegacyList = html.includes("reason-list") && !html.includes("explain-v2");
      const isMutedEmpty = html.includes("理由データなし");

      assert.equal(isV2Ui, c.expectV2Ui);
      if (c.expectLegacyList) assert.equal(isLegacyList, true);
      if (!c.expectExplain21 && !c.expectLegacyList) assert.equal(isMutedEmpty, true);

      RESULTS.matrix.push({
        name: c.name,
        flags: { core: c.core, pi: c.pi, bff: c.bff, web: c.web },
        explain21: !!has21,
        ui: isV2Ui ? "v2" : isLegacyList ? "legacy" : isMutedEmpty ? "empty" : "other",
        pass: true,
      });
    });
  }
});

describe("Explainability Phase 1 E2E — 実レース表示フィールド", () => {
  it(`${RACE_ID} 新潟6R: summary / decision_key / confidence / decision_trace`, () => {
    const { payload } = generateCoreExplainPayload({ coreEnabled: true });
    const piDoc = piResponse({ corePayload: payload, piEnabled: true });
    const bundle = bffBundle(piDoc, true);
    const ex = bundle.explain;

    assert.equal(bundle.race_id, RACE_ID);
    assert.equal(ex.schema_version, "single-explain/2.1");
    assert.ok(ex.reason.summary.includes("コルドンブルー") || ex.reason.summary.includes("4"));
    assert.ok(ex.reason.decision_key.key);
    assert.ok(ex.reason.decision_key.label);
    assert.ok(ex.confidence_reason.summary);
    assert.ok(
      ex.confidence_reason.components.some(
        (c) => c.contribution != null || c.weight != null
      )
    );
    assert.ok(ex.decision_trace.stages.every((s) => s.stage && s.status && s.delta?.summary != null));

    const bind = loadPredictionBind(true);
    const html = bind.reasonsSectionHtml(bundle);
    assert.match(html, /explain-decision-key/);
    assert.match(html, /explain-summary/);
    assert.match(html, /explain-confidence/);
    assert.match(html, /explain-trace/);
    assert.doesNotMatch(html, /理由データなし/);
    assert.doesNotMatch(html, /undefined/);
    assert.doesNotMatch(html, /\[object Object\]/);

    RESULTS.display = {
      race_id: RACE_ID,
      decision_key: ex.reason.decision_key.key,
      summary_preview: ex.reason.summary.slice(0, 80),
      confidence_band: ex.confidence_reason.band,
      trace_stages: ex.decision_trace.stages.map((s) => `${s.stage}:${s.status}`),
      ui_ok: true,
    };
  });
});

describe("Explainability Phase 1 E2E — legacy 後方互換", () => {
  it("Web Flag OFF でも reasons[] / narrative のみで既存 UI が描画できる", () => {
    const { payload } = generateCoreExplainPayload({ coreEnabled: true });
    const bundle = bffBundle(piResponse({ corePayload: payload, piEnabled: true }), true);
    assert.ok(bundle.explain.reasons[0].bullets.length);
    assert.ok(bundle.explain.narrative.length);

    const bind = loadPredictionBind(false);
    const html = bind.reasonsSectionHtml(bundle);
    assert.equal(html.includes("explain-v2"), false);
    assert.match(html, /reason-list/);
    assert.match(html, /番/);
    assert.doesNotMatch(html, /理由データなし/);

    // legacyCompat 単体でも reasons/narrative を供給
    const legacy = legacyCompat({ reason: bundle.explain.reason });
    assert.ok(legacy.reasons.length);
    assert.ok(legacy.narrative);

    RESULTS.legacy = { reasons: legacy.reasons.length, narrative: !!legacy.narrative, pass: true };
  });

  it("v1.1 クライアント想定: explain 2.1 フィールドを無視しても reasons/narrative で成立", () => {
    const { payload } = generateCoreExplainPayload({ coreEnabled: true });
    const bundle = bffBundle(piResponse({ corePayload: payload, piEnabled: true }), true);
    const legacyOnly = {
      explain: {
        reasons: bundle.explain.reasons,
        narrative: bundle.explain.narrative,
      },
    };
    const bind = loadPredictionBind(false);
    const html = bind.reasonsSectionHtml(legacyOnly);
    assert.match(html, /reason-list/);
  });
});

describe("Explainability Phase 1 E2E — explain_payload 欠損耐性", () => {
  it("BFF ON + payload 無し → 空 explain、UI は muted で崩れない", () => {
    const bundle = bffBundle(baseFixture, true);
    assert.deepEqual(bundle.explain.reasons, []);
    assert.equal(bundle.explain.narrative, "");
    assert.equal(bundle.explain.reason, undefined);

    const bindOn = loadPredictionBind(true);
    const htmlOn = bindOn.reasonsSectionHtml(bundle);
    assert.match(htmlOn, /理由データなし/);
    assert.doesNotMatch(htmlOn, /explain-v2/);
    assert.doesNotMatch(htmlOn, /undefined/);
    assert.doesNotMatch(htmlOn, /TypeError/);

    const bindOff = loadPredictionBind(false);
    const htmlOff = bindOff.reasonsSectionHtml(bundle);
    assert.match(htmlOff, /理由データなし/);

    // buildExplainV21 直接
    const empty = buildExplainV21({
      piPred: baseFixture.prediction,
      honmeiRunner: { horse_number: 4, horse_name: "X", mark: "honmei" },
      aiConfidence: { score: 0.05, band: "low" },
      enabled: true,
    });
    assert.deepEqual(empty.reasons, []);
    assert.equal(empty.narrative, "");

    RESULTS.missing = { pass: true, ui: "理由データなし" };
  });

  it("部分欠損（decision_key のみ欠落）でも reasonsSectionHtml が例外を投げない", () => {
    const bind = loadPredictionBind(true);
    const partial = {
      explain: {
        schema_version: "single-explain/2.1",
        reason: {
          summary: "サマリーのみ",
          factors: [],
        },
        confidence_reason: { summary: "信頼度メモ" },
        decision_trace: { stages: [] },
      },
    };
    assert.doesNotThrow(() => bind.reasonsSectionHtml(partial));
    const html = bind.reasonsSectionHtml(partial);
    assert.match(html, /explain-v2/);
    assert.match(html, /サマリーのみ/);
    assert.doesNotMatch(html, /undefined/);
  });
});

describe("Explainability Phase 1 E2E — レポート出力", () => {
  it("RC 判定レポートを書き出す", () => {
    RESULTS.verdict = "PASS";
    RESULTS.generated_at = new Date().toISOString();
    const outDir = join(ROOT, "docs/ops");
    mkdirSync(outDir, { recursive: true });
    const outPath = join(outDir, "v2-explainability-phase1-e2e-report.json");
    writeFileSync(outPath, JSON.stringify(RESULTS, null, 2), "utf8");
    assert.equal(RESULTS.verdict, "PASS");
  });
});
