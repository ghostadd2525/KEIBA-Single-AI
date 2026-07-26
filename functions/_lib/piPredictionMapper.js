/**
 * PI GET /v1/predictions/{race_id} → PredictionBundle (single-prediction-bundle/2.0)
 */
import { normalizePredictionBundle } from "./domain.js";
import { buildExplainV21, isExplainV2Enabled } from "./explainBuilder.js";
import { applySegmentConfidenceBlend } from "./segmentConfidence.js";

const MARK_BY_RANK = {
  1: ["honmei", 1],
  2: ["taikou", 1],
  3: ["ana", 1],
  4: ["chuuken", 1],
};

function asInt(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

function asFloat(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function confidenceBand(score) {
  if (score == null) return "unknown";
  const s = score <= 1 ? score : score / 100;
  if (s >= 0.85) return "high";
  if (s >= 0.55) return "medium";
  return "low";
}

function candidateId(horseNumber, horseName) {
  if (horseNumber != null) return `c${String(horseNumber).padStart(2, "0")}`;
  return String(horseName || "unknown");
}

/** @param {Record<string, unknown>} candidate */
function mapCandidateToRunner(candidate) {
  const rank = asInt(candidate.Rank ?? candidate.rank ?? candidate.model_rank);
  const horseNumber = asInt(candidate.HorseNumber ?? candidate.horse_number);
  const horseName = String(
    candidate.CandidateID ?? candidate.horse_name ?? candidate.HorseName ?? ""
  );
  const winProb = asFloat(candidate.Confidence ?? candidate.confidence ?? candidate.win_prob);
  const markPair = rank != null ? MARK_BY_RANK[rank] : null;
  const runner = {
    candidate_id: candidateId(horseNumber, horseName),
    horse_number: horseNumber != null ? horseNumber : 0,
    horse_name: horseName || null,
    model_rank: rank,
    win_prob: winProb,
    mark: markPair ? markPair[0] : "none",
  };
  if (markPair) runner.mark_rank = markPair[1];

  const rawAbility =
    (candidate.AbilityScores && typeof candidate.AbilityScores === "object"
      ? candidate.AbilityScores
      : null) ||
    (candidate.ability_scores && typeof candidate.ability_scores === "object"
      ? candidate.ability_scores
      : null);
  if (rawAbility) {
    const ability = {};
    Object.keys(rawAbility).forEach(function (key) {
      const n = asFloat(rawAbility[key]);
      if (n != null) ability[key] = n;
    });
    if (Object.keys(ability).length) runner.ability_scores = ability;
  }
  return runner;
}

/**
 * @param {Record<string, unknown>} piPayload PI /v1/predictions レスポンス
 * @param {Record<string, unknown> | null} [catalogRace] PI races 行（任意）
 * @param {{ context?: object, explainV2Enabled?: boolean }} [options]
 */
export function mapPiPredictionToBundle(piPayload, catalogRace = null, options = {}) {
  if (!piPayload || piPayload.prediction_available !== true) {
    return null;
  }

  const pred = piPayload.prediction && typeof piPayload.prediction === "object"
    ? piPayload.prediction
    : {};
  const raceRow = catalogRace && typeof catalogRace === "object" ? catalogRace : piPayload;
  const raceId = String(raceRow.race_id || pred.race_id || "");
  const raceDate = String(raceRow.race_date || raceRow.date || "");
  const course = String(raceRow.course || raceRow.venue || "");
  const raceNo = asInt(raceRow.race_number ?? raceRow.race_no);
  const raceName = String(raceRow.race_name || "");
  const raceLabel = String(raceRow.race_label || (course && raceNo ? `${course}${raceNo}R` : ""));
  const surface = String(
    raceRow.surface || raceRow.target_surface || pred.surface || ""
  ).trim();
  const distance = asInt(raceRow.distance ?? raceRow.target_distance ?? pred.distance);

  const candidates = Array.isArray(pred.candidates) ? pred.candidates : [];
  const runners = candidates
    .map(mapCandidateToRunner)
    .sort((a, b) => (a.model_rank ?? 999) - (b.model_rank ?? 999));

  const overall = asFloat(pred.overall_confidence ?? piPayload.overall_confidence);
  const predMeta = pred.meta && typeof pred.meta === "object" ? pred.meta : {};
  const generatedAt =
    String(predMeta.generated_at || pred.generated_at || new Date().toISOString());

  const aiConfidence = {
    schema_version: "single-ai-confidence/1.0",
    status: overall != null ? "ok" : "unknown",
    score: overall,
    score_unit: "normalized",
    band: confidenceBand(overall),
    factors: [],
    component_scores: overall != null ? { model_score: overall } : {},
    notes: "pi-keibanet-api",
    computed_at: generatedAt,
  };

  if (overall != null) {
    const blended = applySegmentConfidenceBlend(overall, raceRow);
    if (blended) {
      aiConfidence.score = blended.score;
      aiConfidence.band = blended.band;
      aiConfidence.component_scores = {
        model_score: blended.model_score,
        segment_hit_rate: blended.segment_hit_rate,
        segment_scope: blended.segment_scope,
        segment_key: blended.segment_key,
        segment_samples: blended.segment_samples,
        blend_weights: { model: 0.6, segment: 0.4 },
      };
      aiConfidence.factors = [
        `segment_scope=${blended.segment_scope}`,
        `segment_hit_rate=${Number(blended.segment_hit_rate).toFixed(4)}`,
      ];
    }
  }

  const baseExplainMeta = {
    source: "pi-keibanet-api",
    numeric_race_id: raceRow.numeric_race_id || piPayload.numeric_race_id || null,
    collector_race_id: raceRow.collector_race_id || piPayload.collector_race_id || null,
    ...predMeta,
  };

  const explainEnabled =
    options.explainV2Enabled != null
      ? Boolean(options.explainV2Enabled)
      : isExplainV2Enabled(options.context);
  const honmei = runners.find((r) => r.mark === "honmei") || runners[0] || null;
  const explain = buildExplainV21({
    piPred: pred,
    honmeiRunner: honmei,
    aiConfidence,
    baseMeta: baseExplainMeta,
    enabled: explainEnabled,
  });

  const raw = {
    schema_version: "single-prediction-bundle/2.0",
    race_id: raceId,
    generated_at: generatedAt,
    model_version: String(predMeta.model_version || pred.core_version || "pi-core"),
    core_version: String(pred.core_version || "pi-core"),
    product_version: "expect-pi/1.1",
    status: "ok",
    warnings: [],
    race_info: {
      race_id: raceId,
      date: raceDate,
      venue: course,
      meeting_id: raceDate ? `${raceDate.replace(/-/g, "")}_${course}` : undefined,
      race_no: raceNo,
      class_label: raceName,
      race_label: raceLabel,
      race_name: raceName,
      race_status: String(raceRow.status || "published"),
      field_size: asInt(raceRow.field_size) ?? runners.length,
      surface: surface || null,
      distance: distance,
      post_time:
        raceRow.post_time != null && String(raceRow.post_time).trim() !== ""
          ? String(raceRow.post_time).trim()
          : piPayload.post_time != null && String(piPayload.post_time).trim() !== ""
            ? String(piPayload.post_time).trim()
            : null,
    },
    evaluation: {
      status: runners.length ? "ok" : "empty",
      world: pred.world != null ? String(pred.world) : null,
      sub_world: pred.sub_world != null ? String(pred.sub_world) : null,
      runners,
    },
    ai_confidence: aiConfidence,
    explain,
    betting_recommendations: {
      schema_version: "single-betting-recommendations/1.0",
      race_id: raceId,
      status: "pi",
      items: [],
      by_bet_type: {},
    },
  };

  return normalizePredictionBundle(raw, raceId);
}

/** PI provenance item（list meta.items 用） */
export function piProvenanceItem(raceId, bundle, extra = {}) {
  return {
    race_id: raceId,
    engine_source: "pi",
    model_version: bundle?.model_version ?? null,
    inference_generated_at: bundle?.generated_at ?? null,
    ...extra,
  };
}
