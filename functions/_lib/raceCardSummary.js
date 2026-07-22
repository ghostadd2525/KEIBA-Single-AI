/**
 * RaceCardSummary — 一覧専用 DTO（PredictionBundle ではない）
 *
 * 契約: docs/releases/v2-ui-enhancement-mock.md §2.2
 * schema_version: expect-race-card-summary/1.0
 */
import { mapPiPredictionToBundle } from "./piPredictionMapper.js";

export const RACE_CARD_SUMMARY_SCHEMA = "expect-race-card-summary/1.0";
export const RACE_CARDS_LIST_SCHEMA = "expect-race-cards/1.0";

/** RaceCardSummary band 閾値（BFF 責務 — Web 禁止） */
export const CONFIDENCE_BAND_HIGH = 0.6;
export const CONFIDENCE_BAND_MEDIUM = 0.35;

/**
 * @param {number | null | undefined} score 0–1（>1 なら /100 正規化）
 * @returns {"high"|"medium"|"low"}
 */
export function confidenceBandFromScore(score) {
  if (score == null || !Number.isFinite(Number(score))) return "low";
  let s = Number(score);
  if (s > 1) s = s / 100;
  if (s >= CONFIDENCE_BAND_HIGH) return "high";
  if (s >= CONFIDENCE_BAND_MEDIUM) return "medium";
  return "low";
}

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
  return {
    venue,
    race_number: Number.isFinite(raceNumber) ? raceNumber : null,
    race_name: String(race.race_name || ""),
    post_time: postTime,
  };
}

/**
 * PredictionBundle → summary 名前空間（一覧用最小集合）
 * Phase 1: short_reason は常に null
 * @param {Record<string, unknown>} bundle
 */
export function buildSummaryFromBundle(bundle) {
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

  const rawScore = bundle?.ai_confidence?.score;
  const score =
    rawScore == null || !Number.isFinite(Number(rawScore))
      ? null
      : Number(rawScore) > 1
        ? Number(rawScore) / 100
        : Number(rawScore);

  const confidence =
    score == null
      ? null
      : {
          score,
          band: confidenceBandFromScore(score),
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
    card.summary = buildSummaryFromBundle(bundle);
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

export const RACE_CARDS_FETCH_CONCURRENCY = 9;
