/**
 * UI1 — SingleResponse / core prediction → PredictionBundle 2.0 (View Mapper)
 *
 * Existing UI (ExpectPredictionBind) stays unchanged.
 * Does not expose World / Near Miss / Affinity / Explanation Confidence.
 * UI3: output always satisfies ExpectContractGuard.validatePredictionBundle.
 */
import { ensurePredictionBundleContract } from "./domain.js";

const MARK_BY_RANK = {
  1: ["honmei", 1],
  2: ["taikou", 1],
  3: ["ana", 1],
  4: ["chuuken", 1],
};

function asInt(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

function asFloat(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function extractPrediction(source) {
  if (!source || typeof source !== "object") return {};
  let src = source;
  if (src.single && typeof src.single === "object") src = src.single;
  if (src.core_payload && typeof src.core_payload.prediction === "object") {
    return { ...src.core_payload.prediction };
  }
  if (src.prediction && typeof src.prediction === "object") {
    return { ...src.prediction };
  }
  return {};
}

function extractRaceId(source, fallback) {
  if (!source || typeof source !== "object") return String(fallback || "");
  if (source.race_id) return String(source.race_id);
  if (source.single && source.single.race_id) return String(source.single.race_id);
  if (source.core_payload && source.core_payload.race_id) {
    return String(source.core_payload.race_id);
  }
  return String(fallback || "");
}

function candidateId(horseNumber, horseName) {
  if (horseNumber != null) return `c${String(horseNumber).padStart(2, "0")}`;
  return String(horseName || "unknown");
}

function runnersFromPrediction(prediction, baseRunners) {
  const ranks = Array.isArray(prediction.ranks) ? prediction.ranks : [];
  const scores = Array.isArray(prediction.scores) ? prediction.scores : [];
  const byNum = {};
  const byName = {};
  (baseRunners || []).forEach((br) => {
    const n = asInt(br.horse_number);
    if (n != null) byNum[n] = br;
    if (br.horse_name) byName[String(br.horse_name)] = br;
  });

  const runners = ranks.map((raw, i) => {
    const rank = i + 1;
    const markPair = MARK_BY_RANK[rank] || null;
    let horseNumber = asInt(raw);
    let horseName = null;
    let base = null;
    if (horseNumber != null) {
      base = byNum[horseNumber];
      if (base && base.horse_name) horseName = String(base.horse_name);
    } else {
      horseName = raw != null ? String(raw) : null;
      horseNumber = 0;
      base = horseName ? byName[horseName] : null;
      if (base && asInt(base.horse_number) != null) horseNumber = asInt(base.horse_number);
    }
    let winProb = i < scores.length ? asFloat(scores[i]) : null;
    if (winProb != null && winProb > 1) winProb = winProb / 100;

    const runner = {
      candidate_id: candidateId(horseNumber || null, horseName),
      horse_number: horseNumber,
      horse_name: horseName,
      model_rank: rank,
      win_prob: winProb,
      mark: markPair ? markPair[0] : "none",
    };
    if (markPair) runner.mark_rank = markPair[1];
    if (base && base.ability_scores && typeof base.ability_scores === "object") {
      runner.ability_scores = { ...base.ability_scores };
    }
    return runner;
  });

  runners.sort((a, b) => (a.model_rank || 999) - (b.model_rank || 999));
  return runners;
}

function sanitizeBundle(bundle) {
  const out = { ...bundle };
  const ev = { ...(out.evaluation || {}) };
  ev.world = null;
  ev.sub_world = null;
  out.evaluation = ev;
  const ex = { ...(out.explain || {}) };
  const meta = { ...(ex.meta || {}) };
  meta.world = null;
  meta.sub_world = null;
  ex.meta = meta;
  out.explain = ex;
  [
    "presentation",
    "registry",
    "near_miss",
    "affinity",
    "explanation_confidence",
    "ticket",
    "core_payload",
    "natural_explanation",
    "decision_reason",
  ].forEach((k) => {
    delete out[k];
  });
  return out;
}

/**
 * @param {object} singleOrCore
 * @param {{ race_id?: string, race_info?: object, base_bundle?: object }} [opts]
 */
export function mapSingleToPredictionBundle(singleOrCore, opts = {}) {
  const raceId = opts.race_id || extractRaceId(singleOrCore);
  const prediction = extractPrediction(singleOrCore);
  const base = opts.base_bundle && typeof opts.base_bundle === "object" ? opts.base_bundle : {};
  const baseRunners =
    base.evaluation && Array.isArray(base.evaluation.runners) ? base.evaluation.runners : [];

  let runners = runnersFromPrediction(prediction, baseRunners);
  if (!runners.length && baseRunners.length) runners = baseRunners.map((r) => ({ ...r }));

  const infoOverlay =
    opts.race_info || (base.race_info && typeof base.race_info === "object" ? base.race_info : null);
  const raceInfo = {
    race_id: raceId || "unknown",
    date: "unknown",
    venue: "unknown",
    race_no: 1,
    post_time: null,
    distance: null,
    surface: null,
    course: null,
    class_label: null,
    grade: null,
    field_size: runners.length || null,
    race_status: null,
    race_name: null,
    ...(infoOverlay || {}),
  };
  raceInfo.race_id = raceId || raceInfo.race_id;
  raceInfo.world = undefined;
  delete raceInfo.world;
  delete raceInfo.near_miss;
  delete raceInfo.affinity;

  let aiConfidence = base.ai_confidence && typeof base.ai_confidence === "object"
    ? { ...base.ai_confidence }
    : {
        schema_version: "ai-confidence/1.0",
        status: "unknown",
        score: null,
        score_unit: "normalized",
        band: "unknown",
        inputs_ref: null,
        factors: [],
        component_scores: {},
        notes: null,
        computed_at: null,
      };
  delete aiConfidence.explanation_confidence;
  delete aiConfidence.near_miss_confidence;

  let explain =
    base.explain && typeof base.explain === "object"
      ? { ...base.explain, meta: { ...(base.explain.meta || {}), world: null, sub_world: null } }
      : {
          meta: { world: null, sub_world: null, strategy_id: null, confidence_band: null },
          reasons: [],
          narrative: "",
        };
  if (typeof explain.narrative !== "string") {
    explain = { ...explain, narrative: "" };
  }

  const bets =
    base.betting_recommendations && typeof base.betting_recommendations === "object"
      ? base.betting_recommendations
      : { schema_version: "betting-recommendations/1.0", items: [] };

  return ensurePredictionBundleContract(
    sanitizeBundle({
      schema_version: "single-prediction-bundle/2.0",
      race_id: raceId,
      race_info: raceInfo,
      evaluation: {
        status: runners.length ? "ok" : "partial",
        world: null,
        sub_world: null,
        runners,
      },
      ai_confidence: aiConfidence,
      explain,
      betting_recommendations: bets,
      warnings: Array.isArray(base.warnings) ? [...base.warnings] : [],
      model_version: base.model_version ?? null,
      generated_at: base.generated_at ?? null,
    }),
    raceId
  );
}

export const SingleToBundleMapper = {
  map: mapSingleToPredictionBundle,
};
