/**
 * AI信頼度 × 会場×芝ダ×距離の過去◎的中率ブレンド（60% / 40%）
 */
import { SEGMENT_HIT_RATES } from "./segmentHitRates.js";
import { confidenceBandFromScore } from "./confidenceBands.js";

export const MODEL_WEIGHT = 0.6;
export const SEGMENT_WEIGHT = 0.4;
export const MIN_SEGMENT_SAMPLES = 3;

const DISTANCE_BUCKETS = [1200, 1600, 2000, 2400];

/** @param {unknown} surface */
export function surfaceJa(surface) {
  const s = String(surface || "").toLowerCase();
  if (s.includes("turf") || s === "芝") return "芝";
  if (s.includes("dirt") || s === "ダ" || s === "ダート") return "ダ";
  return "芝";
}

/** @param {unknown} distance */
export function distanceBucket(distance) {
  const d = Number(distance) || 0;
  if (!d) return 1600;
  let best = DISTANCE_BUCKETS[0];
  let diff = Math.abs(d - best);
  for (let i = 1; i < DISTANCE_BUCKETS.length; i++) {
    const nd = Math.abs(d - DISTANCE_BUCKETS[i]);
    if (nd < diff) {
      diff = nd;
      best = DISTANCE_BUCKETS[i];
    }
  }
  return best;
}

/** @param {string} venue @param {string} surf @param {number} bucket */
export function segmentKey(venue, surf, bucket) {
  return `${String(venue || "").trim()}|${surf}|${bucket}`;
}

/** @param {number | null | undefined} score */
export function normalizeScore(score) {
  if (score == null || !Number.isFinite(Number(score))) return null;
  const s = Number(score);
  return s > 1 ? s / 100 : s;
}

/**
 * @param {Record<string, unknown> | null | undefined} race
 * @returns {{ venue: string, surface: string, distance: number | null }}
 */
export function raceSegmentContext(race) {
  const row = race || {};
  const info = row.race_info && typeof row.race_info === "object" ? row.race_info : row;
  const venue = String(info.venue || info.course || row.course || row.venue || "").trim();
  const surface = surfaceJa(
    info.surface || info.target_surface || row.surface || row.target_surface
  );
  const rawDist = info.distance ?? info.target_distance ?? row.distance ?? row.target_distance;
  const distNum = rawDist != null && rawDist !== "" ? Number(rawDist) : null;
  return {
    venue,
    surface,
    distance: Number.isFinite(distNum) ? distNum : null,
  };
}

/**
 * @param {typeof SEGMENT_HIT_RATES} [table]
 * @param {{ venue?: string, surface?: string, distance?: number | null }} ctx
 */
export function lookupSegmentHitRate(ctx, table = SEGMENT_HIT_RATES) {
  const overall = Number(table?.overall_hit_rate);
  const fallback = Number.isFinite(overall) ? overall : 0;
  const minN = Number(table?.min_samples) || MIN_SEGMENT_SAMPLES;
  const segments = table?.segments || {};
  const venue = String(ctx?.venue || "").trim();
  const surf = surfaceJa(ctx?.surface);
  const bucket = distanceBucket(ctx?.distance);

  if (!venue) return { hit_rate: fallback, key: null, n: 0, scope: "overall" };

  const fullKey = segmentKey(venue, surf, bucket);
  const full = segments[fullKey];
  if (full && Number(full.n) >= minN) {
    return {
      hit_rate: Number(full.hit_rate),
      key: fullKey,
      n: Number(full.n),
      scope: "venue_surface_distance",
    };
  }

  const venueSurfPrefix = `${venue}|${surf}|`;
  let venueSurfSum = 0;
  let venueSurfN = 0;
  for (const [key, row] of Object.entries(segments)) {
    if (!key.startsWith(venueSurfPrefix)) continue;
    const n = Number(row.n) || 0;
    if (n <= 0) continue;
    venueSurfSum += Number(row.hit_rate) * n;
    venueSurfN += n;
  }
  if (venueSurfN >= minN) {
    return {
      hit_rate: venueSurfSum / venueSurfN,
      key: `${venue}|${surf}|*`,
      n: venueSurfN,
      scope: "venue_surface",
    };
  }

  let venueSum = 0;
  let venueCount = 0;
  for (const [key, row] of Object.entries(segments)) {
    if (!key.startsWith(`${venue}|`)) continue;
    const n = Number(row.n) || 0;
    if (n <= 0) continue;
    venueSum += Number(row.hit_rate) * n;
    venueCount += n;
  }
  if (venueCount >= minN) {
    return {
      hit_rate: venueSum / venueCount,
      key: `${venue}|*`,
      n: venueCount,
      scope: "venue",
    };
  }

  return { hit_rate: fallback, key: null, n: 0, scope: "overall" };
}

/**
 * @param {number | null | undefined} modelScore 0–1
 * @param {number} segmentHitRate 0–1
 */
export function blendConfidenceScore(modelScore, segmentHitRate) {
  const model = normalizeScore(modelScore);
  if (model == null) return null;
  const segment = Number(segmentHitRate);
  const seg = Number.isFinite(segment) ? segment : 0;
  const blended = MODEL_WEIGHT * model + SEGMENT_WEIGHT * seg;
  return Math.min(Math.max(blended, 0), 1);
}

/**
 * @param {number | null | undefined} modelScore
 * @param {Record<string, unknown> | null | undefined} raceContext
 * @param {typeof SEGMENT_HIT_RATES} [table]
 */
export function applySegmentConfidenceBlend(modelScore, raceContext, table = SEGMENT_HIT_RATES) {
  const ctx = raceSegmentContext(raceContext);
  const lookup = lookupSegmentHitRate(ctx, table);
  const blended = blendConfidenceScore(modelScore, lookup.hit_rate);
  if (blended == null) return null;
  return {
    score: blended,
    band: confidenceBandFromScore(blended),
    model_score: normalizeScore(modelScore),
    segment_hit_rate: lookup.hit_rate,
    segment_key: lookup.key,
    segment_scope: lookup.scope,
    segment_samples: lookup.n,
  };
}
