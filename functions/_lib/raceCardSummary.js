/**
 * RaceCardSummary — 一覧専用 DTO（PredictionBundle ではない）
 *
 * 契約: docs/releases/v2-ui-enhancement-mock.md §2.2
 * schema_version: expect-race-card-summary/1.0
 */
import { mapPiPredictionToBundle } from "./piPredictionMapper.js";
import { applySegmentConfidenceBlend } from "./segmentConfidence.js";
import {
  CONFIDENCE_BAND_HIGH,
  CONFIDENCE_BAND_RATHER_HIGH,
  CONFIDENCE_BAND_MEDIUM,
  confidenceBandFromScore,
  confidenceBandFromLabelAndScore,
  resolveInternalLabel,
  resolveConfidenceDisplay,
} from "./confidenceBands.js";

export {
  CONFIDENCE_BAND_HIGH,
  CONFIDENCE_BAND_RATHER_HIGH,
  CONFIDENCE_BAND_MEDIUM,
  confidenceBandFromScore,
  confidenceBandFromLabelAndScore,
  resolveInternalLabel,
  resolveConfidenceDisplay,
};

export const RACE_CARD_SUMMARY_SCHEMA = "expect-race-card-summary/1.0";
export const RACE_CARDS_LIST_SCHEMA = "expect-race-cards/1.0";

/**
 * Catalog 行 → race_info（Catalog 由来のみ）
 * @param {Record<string, unknown>} race
 */
export function buildRaceInfoFromCatalog(race) {
  const venue = String(race.course || race.venue || "");
  const raceNumber =
    race.race_number != null
      ? Number(race.race_number)
      : race.race_no != null
        ? Number(race.race_no)
        : null;
  const postTime =
    race.post_time != null && String(race.post_time).trim() !== ""
      ? String(race.post_time)
      : null;
  const surface =
    race.surface != null && String(race.surface).trim() !== ""
      ? String(race.surface)
      : race.target_surface != null && String(race.target_surface).trim() !== ""
        ? String(race.target_surface)
        : null;
  const rawDist = race.distance ?? race.target_distance;
  const distance =
    rawDist != null && rawDist !== "" && Number.isFinite(Number(rawDist))
      ? Number(rawDist)
      : null;
  return {
    venue,
    race_number: Number.isFinite(raceNumber) ? raceNumber : null,
    race_name: String(race.race_name || ""),
    post_time: postTime,
    surface,
    distance,
    date: String(race.date || race.race_date || "").trim() || null,
    date_label:
      race.date_label != null && String(race.date_label).trim() !== ""
        ? String(race.date_label)
        : null,
  };
}

/**
 * PredictionBundle → summary 名前空間（一覧用最小集合）
 * Phase 1: short_reason は常に null
 * @param {Record<string, unknown>} bundle
 * @param {Record<string, unknown> | null} [catalogRace]
 */
export function buildSummaryFromBundle(bundle, catalogRace = null) {
  const runners = Array.isArray(bundle?.evaluation?.runners)
    ? bundle.evaluation.runners
    : [];
  const honmeiRunner = runners.find((r) => r && r.mark === "honmei") || runners[0] || null;

  const honmei = honmeiRunner
    ? {
        horse_number: Number(honmeiRunner.horse_number) || 0,
        horse_name: honmeiRunner.horse_name != null ? String(honmeiRunner.horse_name) : null,
        mark: "honmei",
      }
    : null;

  const comp = bundle?.ai_confidence?.component_scores || {};
  const rawModel = comp.model_score != null ? comp.model_score : bundle?.ai_confidence?.score;
  const modelScore =
    rawModel == null || !Number.isFinite(Number(rawModel))
      ? null
      : Number(rawModel) > 1
        ? Number(rawModel) / 100
        : Number(rawModel);

  const raceCtx = catalogRace || bundle?.race_info || {};
  const blended = applySegmentConfidenceBlend(modelScore, raceCtx);
  // UI8: band = 内部ラベル（world 等）+ score。ラベル自体は summary に載せない
  const world = bundle?.evaluation?.world;
  const confidence =
    blended == null
      ? null
      : {
          score: blended.score,
          band: confidenceBandFromLabelAndScore(
            resolveInternalLabel({ world, score: blended.score }),
            blended.score
          ),
        };

  return {
    honmei,
    confidence,
    short_reason: null,
  };
}

/**
 * PI prediction 取得結果 → RaceCardSummary
 *
 * @param {{
 *   raceId: string,
 *   catalogRace: Record<string, unknown>,
 *   predictionStatus: "ready"|"processing"|"failed"|"missing",
 *   bundle?: Record<string, unknown> | null,
 *   engineSource?: string,
 * }} args
 */
export function buildRaceCardSummary(args) {
  const {
    raceId,
    catalogRace,
    predictionStatus,
    bundle = null,
    engineSource,
  } = args;

  const card = {
    schema_version: RACE_CARD_SUMMARY_SCHEMA,
    race_id: String(raceId || catalogRace?.race_id || ""),
    race_info: buildRaceInfoFromCatalog(catalogRace || {}),
    prediction: {
      status: predictionStatus,
    },
    summary: null,
  };

  if (engineSource) {
    card.prediction.engine_source = engineSource;
  }

  if (predictionStatus === "ready" && bundle) {
    card.summary = buildSummaryFromBundle(bundle, catalogRace);
    if (!card.prediction.engine_source) {
      card.prediction.engine_source = "pi";
    }
  }

  return card;
}

/**
 * PI /v1/predictions ペイロードから status + bundle を決定
 * @param {Record<string, unknown> | null} payload
 * @param {Record<string, unknown>} catalogRace
 * @returns {{ status: "ready"|"missing"|"failed", bundle: object|null }}
 */
export function classifyPiPredictionPayload(payload, catalogRace) {
  if (!payload || typeof payload !== "object") {
    return { status: "failed", bundle: null };
  }
  if (payload.prediction_available !== true) {
    return { status: "missing", bundle: null };
  }
  try {
    const bundle = mapPiPredictionToBundle(payload, catalogRace);
    if (!bundle) return { status: "failed", bundle: null };
    return { status: "ready", bundle };
  } catch {
    return { status: "failed", bundle: null };
  }
}

/**
 * HTTP ステータス → prediction.status（単レース取得失敗時）
 * @param {number} httpStatus
 */
export function predictionStatusFromHttp(httpStatus) {
  if (httpStatus === 404) return "missing";
  if (httpStatus === 202 || httpStatus === 409) return "processing";
  return "failed";
}

/**
 * 並列 map（設計: BFF 並列 9 件）
 * @template T, R
 * @param {T[]} items
 * @param {number} concurrency
 * @param {(item: T, index: number) => Promise<R>} fn
 * @returns {Promise<R[]>}
 */
export async function mapWithConcurrency(items, concurrency, fn) {
  const n = items.length;
  const results = new Array(n);
  let next = 0;
  const workers = Math.max(1, Math.min(concurrency, n || 1));

  async function worker() {
    while (true) {
      const i = next++;
      if (i >= n) return;
      results[i] = await fn(items[i], i);
    }
  }

  await Promise.all(Array.from({ length: workers }, () => worker()));
  return results;
}

/** 全日 36R: CF ~30s 制限内に収めるため高めに */
export const RACE_CARDS_FETCH_CONCURRENCY = 24;
