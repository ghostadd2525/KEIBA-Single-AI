/**
 * explainPick.js — Explainability Phase 3
 *
 * Kaoba / Conversation の explain_pick intent に explain 2.1 を注入。
 * 設計: docs/releases/v2-explainability-design-review.md §10 Phase 3
 *
 * Gate: context.v2_explain === true（Web Flag）。OFF 時は呼び出し側が使わないこと。
 * データ前提: bundle.explain.reason（EXPLAIN_V2 で組み立て済み）が存在すること。
 */

const EXPLAIN_PICK_RE = /理由|なぜ|根拠|why|どうして|選定|本命.*(説明|教えて)|explain/i;

/**
 * @param {string} message
 * @returns {boolean}
 */
export function isExplainPickIntent(message) {
  return EXPLAIN_PICK_RE.test(String(message || ""));
}

/**
 * Web Flag v2_explain が context で ON か
 * @param {Record<string, unknown>|null|undefined} context
 */
export function isV2ExplainContext(context) {
  const ctx = context || {};
  if (ctx.v2_explain === true) return true;
  if (ctx.ui_features && ctx.ui_features.v2_explain === true) return true;
  return false;
}

/**
 * explain 2.1 → Kaoba / Conversation 用の投影（破壊的変換なし）
 * @param {Record<string, unknown>|null|undefined} explain
 */
export function projectExplainForPick(explain) {
  if (!explain || typeof explain !== "object") return null;
  const reason = explain.reason;
  if (!reason || typeof reason !== "object") return null;

  const dk = reason.decision_key || {};
  const factors = Array.isArray(reason.factors) ? reason.factors : [];
  const conf = explain.confidence_reason || {};
  const trace = explain.decision_trace || {};
  const stages = Array.isArray(trace.stages) ? trace.stages : [];

  const factorLines = factors.slice(0, 6).map((f) => {
    const label = f.label || f.kind || "";
    const text = f.text || "";
    return label && text ? `${label}: ${text}` : String(text || label);
  });

  const productStages = stages.filter(
    (s) =>
      (s.stage === "candidate_pool" || s.stage === "entry" || s.stage === "repick") &&
      (s.status === "applied" || s.status === "skipped")
  );
  const traceLines = productStages.length
    ? productStages.map((s) => {
        const delta = s.delta || {};
        return `${s.stage}[${s.status}] ${delta.summary || ""}`.trim();
      })
    : stages
        .filter((s) => s.status === "applied")
        .slice(0, 4)
        .map((s) => {
          const delta = s.delta || {};
          return `${s.stage}: ${delta.summary || ""}`.trim();
        });

  return {
    schema_version: "single-explain-pick/1.0",
    explain_phase: 3,
    decision_key: {
      key: dk.key || null,
      label: dk.label || null,
      text: dk.text || null,
    },
    summary: typeof reason.summary === "string" ? reason.summary : "",
    factor_lines: factorLines,
    confidence_summary:
      typeof conf.summary === "string" ? conf.summary : "",
    trace_lines: traceLines,
    pipeline_version: trace.pipeline_version || null,
    horse_number: reason.horse_number != null ? reason.horse_number : null,
    horse_name: reason.horse_name || null,
  };
}

/**
 * Kaoba 向け reply 文字列を組み立て
 * @param {ReturnType<typeof projectExplainForPick>} projection
 * @param {{ place?: string }} [opts]
 */
export function formatExplainPickReply(projection, opts = {}) {
  if (!projection) return null;
  const place = opts.place ? `${opts.place} についてね。` : "";
  const horse =
    projection.horse_number != null
      ? `${projection.horse_number}番${projection.horse_name || ""}`.trim()
      : "本命";
  const dk = projection.decision_key || {};
  const lines = [];
  lines.push(`${place}${horse}を◎にした理由を説明するね。`);
  if (dk.label) {
    lines.push(`決定打は「${dk.label}」${dk.text ? `（${dk.text}）` : ""}だよ。`);
  }
  if (projection.summary) {
    lines.push(projection.summary);
  }
  if (projection.factor_lines && projection.factor_lines.length) {
    lines.push("要点:");
    projection.factor_lines.forEach((f) => lines.push(`・${f}`));
  }
  if (projection.confidence_summary) {
    lines.push(`信頼度: ${projection.confidence_summary}`);
  }
  if (projection.trace_lines && projection.trace_lines.length) {
    lines.push("判断トレース:");
    projection.trace_lines.forEach((t) => lines.push(`・${t}`));
  }
  return lines.filter(Boolean).join("\n");
}

/**
 * explain_pick が発火できるか（Flag + payload）
 */
export function canExplainPick(input) {
  if (!isV2ExplainContext(input && input.context)) return false;
  if (!isExplainPickIntent(input && input.message)) return false;
  const bundle = input && input.refs && input.refs.bundle;
  const explain = bundle && bundle.explain;
  return !!(explain && explain.reason);
}
