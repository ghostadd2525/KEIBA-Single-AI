/**
 * explainBuilder.js — PredictionBundle.explain 2.1
 *
 * 設計: docs/releases/v2-explainability-design-review.md §5.2 / Phase 2
 * Feature Flag: EXPLAIN_V2_ENABLED（BFF、既定 false）
 * Core explain_payload を投影。Phase 2 は product_stages を trace/factors へ。
 * Flag OFF → 空 explain（v1.1）。
 */

/** ユーザー向けラベル（内部コード → 画面表示） */
const LABELS_JA = {
  ce_rank1: "AI予測1位",
  ce_rank1_gap_lead: "AI予測1位・2位との差が大きい",
  midupper_world: "上位争いになりやすいレース",
  midupper_route: "好位・先行が活きやすい展開",
  core_world: "実力差が出やすいレース",
  ability: "能力差がはっきりしやすいレース",
  strong_spread: "展開が分かれやすいレース",
  gap12: "1番手と2番手の差",
  entropy: "混戦度",
  field_size: "出走頭数",
  top1_prob: "本命の推定勝率",
  top2_sum: "上位2頭の合計勝率",
  candidate_pool: "候補の絞り込み",
  entry: "候補への追加",
  repick: "候補の並べ替え",
};

/** レース傾向を1文で（世界コードの組み合わせ） */
const RACE_TENDENCY = {
  "midupper_world|midupper_route":
    "上位争いになりやすく、好位・先行が活きやすい展開です。",
  "midupper_world|":
    "上位争いになりやすいレースです。",
  "core_world|":
    "実力差が出やすいレースです。",
  "ability|":
    "能力差がはっきりしやすいレースです。",
  "|strong_spread": "展開が分かれやすいレースです。",
  "|midupper_route": "好位・先行が活きやすい展開です。",
};

const PRODUCT_STAGE_FACTOR = {
  candidate_pool: { kind: "comparison", label: "候補の絞り込み" },
  entry: { kind: "comparison", label: "候補への追加" },
  repick: { kind: "repick", label: "候補の並べ替え" },
};

function labelOf(code) {
  const c = String(code || "");
  return LABELS_JA[c] || c;
}

/** 世界・サブ世界をユーザー向け1文に */
function raceTendencyText(world, subWorld) {
  const w = String(world || "").trim();
  const s = String(subWorld || "").trim();
  const key = `${w}|${s}`;
  if (RACE_TENDENCY[key]) return RACE_TENDENCY[key];
  const parts = [];
  if (w && LABELS_JA[w] && !RACE_TENDENCY[`${w}|`]) parts.push(LABELS_JA[w]);
  if (s && LABELS_JA[s]) parts.push(LABELS_JA[s]);
  if (parts.length) return `${parts.join("。")}。`;
  if (w || s) return "レース条件に合わせて評価しています。";
  return "";
}

/** decision_key のユーザー向け短ラベル */
function decisionKeyUserLabel(key) {
  if (key === "ce_rank1_gap_lead") return "AI予測1位・2位との差が大きい";
  return "AI予測1位";
}

/** decision_key.text をユーザー向けに（CE 等を除去） */
function decisionKeyUserText(key, text, gap12) {
  const t = String(text || "").trim();
  if (t && !/\bCE\b/i.test(t)) return t;
  if (key === "ce_rank1_gap_lead") {
    return "2番手との推定勝率差が、このレースで最も大きい";
  }
  if (gap12 != null && gap12 < 0.02) {
    return "1番手ですが、2番手との差は小さめです";
  }
  return "モデル評価で1番手";
}

function envFlagOn(context) {
  const raw =
    (context && context.env && context.env.EXPLAIN_V2_ENABLED) ||
    (typeof process !== "undefined" && process.env && process.env.EXPLAIN_V2_ENABLED) ||
    "";
  return ["1", "true", "yes", "on"].includes(String(raw).trim().toLowerCase());
}

function pct(prob) {
  const n = Number(prob);
  if (!Number.isFinite(n)) return "—";
  return `${Math.round(n * 1000) / 10}%`;
}

function asNum(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * Pass-through merge: product_stages replace matching stage keys.
 * Design: append/replace without rewriting delta fields.
 */
export function mergeProductStages(baseStages, productStages) {
  const base = Array.isArray(baseStages) ? baseStages : [];
  const product = Array.isArray(productStages) ? productStages : [];
  if (!product.length) {
    return base.map((s) => ({
      stage: s.stage,
      status: s.status,
      delta: s.delta || { summary: "" },
      ...(s.timestamp ? { timestamp: s.timestamp } : {}),
    }));
  }
  const byStage = new Map();
  base.forEach((s) => {
    if (s && s.stage) byStage.set(s.stage, s);
  });
  product.forEach((p) => {
    if (p && p.stage) byStage.set(p.stage, p);
  });
  const ordered = [];
  const seen = new Set();
  base.forEach((s) => {
    const key = s && s.stage;
    const src = key && byStage.has(key) ? byStage.get(key) : s;
    ordered.push({
      stage: src.stage,
      status: src.status,
      delta: src.delta || { summary: "" },
      ...(src.timestamp ? { timestamp: src.timestamp } : {}),
    });
    if (key) seen.add(key);
  });
  product.forEach((p) => {
    if (p && p.stage && !seen.has(p.stage)) {
      ordered.push({
        stage: p.stage,
        status: p.status,
        delta: p.delta || { summary: "" },
        ...(p.timestamp ? { timestamp: p.timestamp } : {}),
      });
      seen.add(p.stage);
    }
  });
  return ordered;
}

/**
 * Pool / Entry / RePick → reason.factors（applied|skipped のみ）
 */
export function productFactorsFromStages(stages) {
  const list = Array.isArray(stages) ? stages : [];
  const factors = [];
  list.forEach((s) => {
    const map = PRODUCT_STAGE_FACTOR[s.stage];
    if (!map) return;
    if (s.status !== "applied" && s.status !== "skipped") return;
    const delta = s.delta || {};
    factors.push({
      kind: map.kind,
      label: map.label,
      text: String(delta.summary || ""),
      weight: "secondary",
      evidence: {
        stage: s.stage,
        status: s.status,
        reason_codes: delta.reason_codes || [],
        ...(delta.inputs || {}),
        ...(delta.outputs || {}),
      },
    });
  });
  return factors;
}

/**
 * @param {Record<string, unknown>} piPred prediction object from PI
 * @param {Record<string, unknown>|null} honmeiRunner mapped runner
 */
export function buildHonmeiReason(piPred, honmeiRunner) {
  const payload = (piPred && piPred.explain_payload) || {};
  const meta = (piPred && piPred.meta) || {};
  const world = String((payload.world && payload.world.world) || piPred.world || "");
  const subWorld = String(
    (payload.world && payload.world.sub_world) || piPred.sub_world || ""
  );
  const ranking = payload.ranking_evidence || {};
  const required = payload.required_role || {};
  const decisionKey = payload.decision_key || {
    key: "ce_rank1",
    kind: "candidate_evaluation",
    label: labelOf("ce_rank1"),
  };

  const horseNumber =
    asNum(honmeiRunner && honmeiRunner.horse_number) ??
    asNum(ranking.horse_number) ??
    0;
  const horseName =
    (honmeiRunner && honmeiRunner.horse_name) ||
    payload.honmei_candidate_id ||
    null;
  const winProb =
    asNum(honmeiRunner && honmeiRunner.win_prob) ?? asNum(ranking.win_prob) ?? 0;
  const gap12 = asNum(ranking.gap_to_next) ?? asNum(meta.gap12) ?? 0;
  const tendency = raceTendencyText(world, subWorld);
  const dkKey = decisionKey.key || "ce_rank1";

  const factors = [
    {
      kind: "candidate_evaluation",
      label: "AI予測",
      text: `モデル評価の1番手（推定勝率 ${pct(winProb)}）`,
      weight: "primary",
      evidence: {
        model_rank: 1,
        win_prob: winProb,
        gap12,
      },
    },
  ];
  if (tendency) {
    factors.push({
      kind: "race_context",
      label: "レースの傾向",
      text: tendency.replace(/。$/, ""),
      evidence: { world, sub_world: subWorld },
    });
  }
  const pick = required.race_required_pick;
  const spread = required.spread_need_label || meta.spread_need_label;
  if (pick != null || spread) {
    factors.push({
      kind: "required_role",
      label: "買い目の幅",
      text:
        pick != null
          ? `上位以外も${pick}頭程度は押さえた方がよい展開${spread ? "（展開が分かれやすい）" : ""}`
          : spread
            ? "展開が分かれやすいレース"
            : "",
      weight: "secondary",
      evidence: {
        race_required_pick: pick,
        spread_need_label: spread,
        race_type_label: required.race_type_label || meta.race_type_label,
      },
    });
  }

  // Pool / Entry / RePick は decision_trace のみ（画面の主リストには出さない）
  const productStages = Array.isArray(payload.product_stages)
    ? payload.product_stages
    : [];
  const traceForFactors = productStages.length
    ? productStages
    : Array.isArray(payload.decision_trace_stages)
      ? payload.decision_trace_stages
      : [];
  const productFactors = productFactorsFromStages(traceForFactors);

  const namePart = horseName
    ? `${horseNumber}番${horseName}`
    : `${horseNumber}番`;
  const rankHint =
    dkKey === "ce_rank1_gap_lead"
      ? `AI予測では1番手で、2番手との差も相対的に大きい`
      : `AI予測では1番手`;
  const summary = `${namePart}を◎にしたのは、${rankHint}ため。${
    tendency ? ` ${tendency}` : ""
  }`.trim();

  const productCodes = productFactors
    .flatMap((f) => (f.evidence && f.evidence.reason_codes) || [])
    .filter(Boolean);

  return {
    schema_version: "single-honmei-reason/1.0",
    candidate_id:
      (honmeiRunner && honmeiRunner.candidate_id) ||
      (horseNumber != null ? `c${String(horseNumber).padStart(2, "0")}` : "c00"),
    horse_number: horseNumber,
    horse_name: horseName,
    mark: "honmei",
    decision_key: {
      key: dkKey,
      kind: decisionKey.kind || "candidate_evaluation",
      label: decisionKeyUserLabel(dkKey),
      text: decisionKeyUserText(dkKey, decisionKey.text, gap12),
      evidence: decisionKey.evidence || {},
    },
    summary,
    factors,
    reason_codes: [
      dkKey,
      world ? `world_${world}` : null,
      subWorld ? `route_${subWorld}` : null,
      ...productCodes,
    ].filter(Boolean),
  };
}

/**
 * @param {Record<string, unknown>} meta
 * @param {Record<string, unknown>} aiConfidence
 * @param {Record<string, unknown>} [payload]
 */
export function buildConfidenceReason(meta, aiConfidence, payload = {}) {
  const score =
    aiConfidence && Object.prototype.hasOwnProperty.call(aiConfidence, "score")
      ? aiConfidence.score
      : payload.overall_confidence ?? null;
  const band =
    (aiConfidence && aiConfidence.band) ||
    payload.confidence_band ||
    "unknown";
  const confMeta = { ...(meta || {}), ...(payload.confidence_meta || {}) };
  const rawComponents = Array.isArray(payload.confidence_components)
    ? payload.confidence_components
    : [];

  const interpret = {
    gap12: (v) => (Number(v) < 0.02 ? "差が小さく上位が拮抗" : "1 位が相対的に明確"),
    entropy: (v) => (Number(v) > 2.5 ? "勝率分布が分散" : "勝率が比較的集中"),
    field_size: (v) => (Number(v) >= 14 ? "多頭数で不確実性増" : "頭数は標準的"),
    top1_prob: () => "本命候補の勝率ベース",
    top2_sum: () => "上位集中度の参考指標",
  };

  const components = rawComponents.map((c) => {
    const key = String(c.key || "");
    const value = c.value;
    const fn = interpret[key];
    return {
      key,
      label: labelOf(key),
      value,
      interpretation: fn ? fn(value) : "",
      contribution: c.contribution != null ? Number(c.contribution) : undefined,
      weight: c.weight != null ? Number(c.weight) : undefined,
    };
  });

  // Fallback if Core omitted components
  if (!components.length) {
    const gap12 = asNum(confMeta.gap12);
    const entropy = asNum(confMeta.entropy);
    const fieldSize = asNum(confMeta.field_size);
    if (gap12 != null) {
      components.push({
        key: "gap12",
        label: labelOf("gap12"),
        value: gap12,
        interpretation: interpret.gap12(gap12),
        weight: 0.25,
      });
    }
    if (entropy != null) {
      components.push({
        key: "entropy",
        label: labelOf("entropy"),
        value: entropy,
        interpretation: interpret.entropy(entropy),
        weight: 0.2,
      });
    }
    if (fieldSize != null) {
      components.push({
        key: "field_size",
        label: labelOf("field_size"),
        value: fieldSize,
        interpretation: interpret.field_size(fieldSize),
      });
    }
  }

  const gap12 = asNum(confMeta.gap12);
  const summary =
    band === "low" || (gap12 != null && gap12 < 0.02)
      ? "このレースは混戦になりやすく、◎ の優位は限定的です。"
      : band === "high"
        ? "1番手の評価と2番手との差から、◎ に一定の説得力があります。"
        : "1番手は評価されていますが、混戦の余地もあります。";

  return {
    schema_version: "single-confidence-reason/1.0",
    score,
    band,
    score_unit: "normalized",
    summary,
    components,
    formula_ref: "top1*(0.55+0.25*gap_factor+0.20*spread_factor)",
  };
}

/**
 * @param {Record<string, unknown>} piPred
 */
export function buildDecisionTrace(piPred) {
  const payload = (piPred && piPred.explain_payload) || {};
  const base = Array.isArray(payload.decision_trace_stages)
    ? payload.decision_trace_stages
    : [];
  const product = Array.isArray(payload.product_stages) ? payload.product_stages : [];
  // Core が既に merge 済みでも、product_stages を再投影して idempotent に保つ
  const stages = mergeProductStages(base, product);

  return {
    schema_version: "single-decision-trace/1.0",
    pipeline_version:
      payload.pipeline_version ||
      piPred.core_version ||
      (product.length ? "ai-core-migrated/1.0-phase2" : "ai-core-migrated/1.0-phase1"),
    stages,
  };
}

/**
 * Legacy 2.0 fields from reason
 * @param {Record<string, unknown>} explain
 */
export function legacyCompat(explain) {
  const reason = explain && explain.reason;
  if (!reason) {
    return {
      reasons: Array.isArray(explain?.reasons) ? explain.reasons : [],
      narrative: typeof explain?.narrative === "string" ? explain.narrative : "",
    };
  }
  const bullets = (reason.factors || []).map((f) => f.label || f.text).filter(Boolean);
  const decisionLabel =
    reason.decision_key && reason.decision_key.label
      ? reason.decision_key.label
      : null;
  const legacyBullets = decisionLabel
    ? [decisionLabel, ...bullets.filter((b) => b !== decisionLabel)]
    : bullets;
  return {
    reasons: [
      {
        horse_number: reason.horse_number,
        bullets: legacyBullets.slice(0, 6),
      },
    ],
    narrative:
      typeof reason.summary === "string"
        ? reason.summary.length > 80
          ? `${reason.horse_number}番${reason.horse_name || ""}を◎。${decisionLabel || "AI予測1位"}。`.replace(
              /を◎。$/,
              "を◎。"
            )
          : reason.summary
        : "",
  };
}

/**
 * Build full explain 2.1 from PI prediction + honmei runner + ai_confidence
 */
export function buildExplainV21({
  piPred,
  honmeiRunner,
  aiConfidence,
  baseMeta = {},
  enabled = false,
}) {
  if (!enabled || !piPred || !piPred.explain_payload) {
    return {
      meta: baseMeta,
      reasons: [],
      narrative: "",
    };
  }

  const payload = piPred.explain_payload;
  const reason = buildHonmeiReason(piPred, honmeiRunner);
  const confidence_reason = buildConfidenceReason(
    piPred.meta || {},
    aiConfidence || {},
    payload
  );
  const decision_trace = buildDecisionTrace(piPred);
  const hasProduct = Array.isArray(payload.product_stages) && payload.product_stages.length > 0;
  const explain = {
    schema_version: "single-explain/2.1",
    meta: {
      ...baseMeta,
      explain_source: "core-explain-payload/1.0",
      explain_phase: hasProduct ? 2 : 1,
      // Phase 3: Kaoba explain_pick が消費可能（Web Flag v2_explain で注入）
      kaoba_ready: true,
      kaoba_intent: "explain_pick",
    },
    reason,
    confidence_reason,
    decision_trace,
  };
  const legacy = legacyCompat(explain);
  explain.reasons = legacy.reasons;
  explain.narrative =
    legacy.narrative ||
    `${reason.horse_number}番${reason.horse_name || ""}を◎。${reason.decision_key.label}。`;
  return explain;
}

export function isExplainV2Enabled(context) {
  return envFlagOn(context);
}

export { LABELS_JA };
