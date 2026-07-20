/**
 * PredictionBundle = サービス間共通契約（API Contract）
 * schema: single-prediction-bundle/2.0
 *
 * Analysis / Confidence / Ticket / Kaoba は bundle.race_id をキーに参照する。
 */

export const BUNDLE_SCHEMA = "single-prediction-bundle/2.0";

export function scorePercent(aiConfidence) {
  const c = aiConfidence || {};
  if (typeof c.score_percent === "number") return Math.round(c.score_percent);
  if (typeof c.score === "number") {
    return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
  }
  return null;
}

/** カタログ行 → 一覧用 PredictionBundle（契約を満たす最小形） */
export function catalogToPredictionBundle(race, baseBundle = null) {
  const raceId = race.race_id;
  const hint = race.ai_confidence != null ? Number(race.ai_confidence) : null;
  const base = baseBundle ? normalizePredictionBundle(baseBundle, raceId) : null;

  const bundle = {
    schema_version: BUNDLE_SCHEMA,
    race_id: raceId,
    generated_at: (base && base.generated_at) || new Date().toISOString(),
    model_version: (base && base.model_version) || "list-projection",
    core_version: (base && base.core_version) || "list-projection",
    product_version: (base && base.product_version) || "expect-ui-0.1.0",
    status: base && base.status ? base.status : "ok",
    warnings: [],
    race_info: {
      race_id: raceId,
      date: race.date,
      venue: race.venue,
      meeting_id: `${String(race.date || "").replace(/-/g, "")}_${String(race.venue || "").toLowerCase()}`,
      race_no: race.race_no,
      post_time: race.post_time,
      distance: race.distance,
      surface: race.surface,
      course: (base && base.race_info && base.race_info.course) || null,
      class_label: race.class_label,
      grade: race.badge || null,
      field_size: race.field_size,
      race_status: race.status || "scheduled",
      // UI 補助（契約外ではない拡張。未知キーはクライアントが無視可）
      date_label: race.date_label || null,
      date_full: race.date_full || null,
      bg: race.bg != null ? race.bg : null,
    },
    evaluation:
      base && base.evaluation
        ? base.evaluation
        : { status: "list", world: null, sub_world: null, runners: [] },
    ai_confidence: {
      schema_version: "single-ai-confidence/1.0",
      status: "ok",
      score: hint != null ? hint / 100 : (base && base.ai_confidence && base.ai_confidence.score) || null,
      score_unit: "normalized",
      band:
        hint == null
          ? (base && base.ai_confidence && base.ai_confidence.band) || "unknown"
          : hint >= 85
            ? "high"
            : hint >= 70
              ? "medium"
              : "low",
      factors: (base && base.ai_confidence && base.ai_confidence.factors) || [],
      component_scores: (base && base.ai_confidence && base.ai_confidence.component_scores) || {},
      notes: "list projection",
      computed_at: new Date().toISOString(),
    },
    explain: (base && base.explain) || {
      meta: {},
      reasons: [],
      narrative: "",
    },
    betting_recommendations: (base && base.betting_recommendations) || {
      schema_version: "single-betting-recommendations/1.0",
      race_id: raceId,
      status: "list",
      items: [],
      by_bet_type: {},
    },
  };

  return normalizePredictionBundle(bundle, raceId);
}

/** 生 JSON → PredictionBundle（共通契約に正規化） */
export function normalizePredictionBundle(raw, raceId) {
  if (!raw || typeof raw !== "object") {
    throw new Error("invalid PredictionBundle");
  }
  const id = raceId || raw.race_id || (raw.race_info && raw.race_info.race_id);
  const info = { ...(raw.race_info || {}) };
  if (id) {
    info.race_id = id;
  }

  return {
    ...raw,
    schema_version: BUNDLE_SCHEMA,
    race_id: id,
    race_info: info,
    status: raw.status || "ok",
    warnings: Array.isArray(raw.warnings) ? raw.warnings : [],
    evaluation: (() => {
      const ev = raw.evaluation || {};
      return {
        status: ev.status || "unknown",
        world: ev.world != null ? ev.world : null,
        sub_world: ev.sub_world != null ? ev.sub_world : null,
        runners: Array.isArray(ev.runners) ? ev.runners : [],
      };
    })(),
    ai_confidence: (() => {
      const c = raw.ai_confidence || {};
      return {
        schema_version: c.schema_version || "single-ai-confidence/1.0",
        status: c.status || "unknown",
        score: Object.prototype.hasOwnProperty.call(c, "score") ? c.score : null,
        score_unit: c.score_unit || "normalized",
        band: c.band || "unknown",
        inputs_ref: c.inputs_ref != null ? c.inputs_ref : null,
        factors: Array.isArray(c.factors) ? c.factors : [],
        component_scores: c.component_scores || {},
        notes: c.notes != null ? c.notes : null,
        computed_at: c.computed_at != null ? c.computed_at : null,
      };
    })(),
    explain: (() => {
      const ex = raw.explain || {};
      return {
        meta: ex.meta || {},
        reasons: Array.isArray(ex.reasons) ? ex.reasons : [],
        narrative: typeof ex.narrative === "string" ? ex.narrative : "",
      };
    })(),
    betting_recommendations: raw.betting_recommendations || {
      schema_version: "single-betting-recommendations/1.0",
      race_id: id,
      status: "unknown",
      items: [],
    },
  };
}

/** ConfidenceService 投影（PredictionBundle.ai_confidence + race_id） */
export function projectConfidence(bundle) {
  const b = normalizePredictionBundle(bundle);
  const c = b.ai_confidence || {};
  return {
    schema_version: "expect-confidence/1.0",
    race_id: b.race_id,
    status: c.status || "ok",
    score: c.score != null ? c.score : null,
    score_percent: scorePercent(c),
    score_unit: c.score_unit || "normalized",
    band: c.band || "unknown",
    factors: c.factors || [],
    component_scores: c.component_scores || {},
    notes: c.notes || "",
    computed_at: c.computed_at || null,
  };
}

/** TicketService 投影（PredictionBundle.betting_recommendations + race_id） */
export function projectTickets(bundle) {
  const b = normalizePredictionBundle(bundle);
  const br = b.betting_recommendations || {};
  return {
    schema_version: "expect-tickets/1.0",
    race_id: b.race_id,
    status: br.status || "ok",
    strategy_id: br.strategy_id || null,
    generated_at: br.generated_at || null,
    items: br.items || [],
    by_bet_type: br.by_bet_type || {},
  };
}

export function toAnalysisDomain(row, raceId) {
  return {
    schema_version: "expect-analysis/1.0",
    race_id: raceId || (row && row.race_id),
    charts: (row && row.charts) || [],
    overall: row && row.overall != null ? Number(row.overall) : null,
    narrative: (row && row.narrative) || "",
  };
}

/** @deprecated use normalizePredictionBundle */
export function toPredictionDomain(bundle, raceId) {
  return normalizePredictionBundle(bundle, raceId);
}

export function toConfidenceDomain(bundle, raceId) {
  return projectConfidence(normalizePredictionBundle(bundle, raceId));
}

export function toTicketDomain(bundle, raceId) {
  return projectTickets(normalizePredictionBundle(bundle, raceId));
}

export function toPredictionSummary(race) {
  const b = catalogToPredictionBundle(race);
  return {
    race_id: b.race_id,
    confidence_hint: scorePercent(b.ai_confidence),
  };
}
