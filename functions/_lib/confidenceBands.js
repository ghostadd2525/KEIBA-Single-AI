/** RaceCardSummary / 信頼度表示の band 閾値（BFF 責務）
 * UI8: 内部ラベル（Normal / Near Miss / Affinity Residual / Pure Residual）+ score
 * → 表示 band。内部名は UI に出さない。
 */

export const CONFIDENCE_BAND_HIGH = 0.75;
export const CONFIDENCE_BAND_RATHER_HIGH = 0.6;
export const CONFIDENCE_BAND_MEDIUM = 0.35;

/** @typedef {"normal"|"near_miss"|"affinity_residual"|"pure_residual"} InternalConfidenceLabel */
/** @typedef {"high"|"rather_high"|"medium"|"low"} ConfidenceBand */

export const INTERNAL_LABEL_NORMAL = "normal";
export const INTERNAL_LABEL_NEAR_MISS = "near_miss";
export const INTERNAL_LABEL_AFFINITY_RESIDUAL = "affinity_residual";
export const INTERNAL_LABEL_PURE_RESIDUAL = "pure_residual";

/** 表示 band の強さ（大きいほど自信度が高い） */
export const BAND_RANK = {
  high: 3,
  rather_high: 2,
  medium: 1,
  low: 0,
};

const RANK_TO_BAND = /** @type {const} */ (["low", "medium", "rather_high", "high"]);

/** 内部ラベルの天井 band（これより上には上げない） */
export const LABEL_CEILING_BAND = {
  normal: "high",
  near_miss: "rather_high",
  affinity_residual: "medium",
  pure_residual: "low",
};

/**
 * @param {number | null | undefined} score 0–1（>1 なら /100 正規化）
 * @returns {number | null}
 */
export function normalizeConfidenceScore(score) {
  if (score == null || !Number.isFinite(Number(score))) return null;
  let s = Number(score);
  if (s > 1) s = s / 100;
  return s;
}

/**
 * @param {number | null | undefined} score 0–1（>1 なら /100 正規化）
 * @returns {ConfidenceBand}
 */
export function confidenceBandFromScore(score) {
  const s = normalizeConfidenceScore(score);
  if (s == null) return "low";
  if (s >= CONFIDENCE_BAND_HIGH) return "high";
  if (s >= CONFIDENCE_BAND_RATHER_HIGH) return "rather_high";
  if (s >= CONFIDENCE_BAND_MEDIUM) return "medium";
  return "low";
}

/**
 * score 帯を内部ラベルのフォールバックに使う（world が無い / 非 CEW のとき）
 * @param {number | null | undefined} score
 * @returns {InternalConfidenceLabel}
 */
export function internalLabelFromScore(score) {
  const band = confidenceBandFromScore(score);
  if (band === "high") return INTERNAL_LABEL_NORMAL;
  if (band === "rather_high") return INTERNAL_LABEL_NEAR_MISS;
  if (band === "medium") return INTERNAL_LABEL_AFFINITY_RESIDUAL;
  return INTERNAL_LABEL_PURE_RESIDUAL;
}

/**
 * PI / CEW world → 内部ラベル。未対応 world は null（score フォールバックへ）
 * @param {unknown} world
 * @param {{ near_miss?: unknown, affinity?: unknown }} [extras]
 * @returns {InternalConfidenceLabel | null}
 */
export function internalLabelFromWorld(world, extras = {}) {
  if (extras.near_miss != null && extras.near_miss !== false) {
    return INTERNAL_LABEL_NEAR_MISS;
  }
  if (extras.affinity != null && extras.affinity !== false) {
    return INTERNAL_LABEL_AFFINITY_RESIDUAL;
  }
  const w = String(world || "")
    .trim()
    .toLowerCase();
  if (!w) return null;
  if (w === "core_world" || w === "core") return INTERNAL_LABEL_NORMAL;
  if (w === "midupper_world" || w === "midupper") return INTERNAL_LABEL_NEAR_MISS;
  if (w === "midhole_world" || w === "midhole") return INTERNAL_LABEL_AFFINITY_RESIDUAL;
  if (w === "rank7_world" || w === "rank7") return INTERNAL_LABEL_PURE_RESIDUAL;
  if (w === "mixed_world" || w === "mixed") return INTERNAL_LABEL_AFFINITY_RESIDUAL;
  if (w === "unsatisfied" || w === "bug_world" || w === "bug") {
    return INTERNAL_LABEL_PURE_RESIDUAL;
  }
  return null;
}

/**
 * @param {{
 *   world?: unknown,
 *   near_miss?: unknown,
 *   affinity?: unknown,
 *   score?: number | null,
 * }} input
 * @returns {InternalConfidenceLabel}
 */
export function resolveInternalLabel(input = {}) {
  const fromWorld = internalLabelFromWorld(input.world, {
    near_miss: input.near_miss,
    affinity: input.affinity,
  });
  if (fromWorld) return fromWorld;
  return internalLabelFromScore(input.score);
}

/**
 * UI8: 内部ラベル天井 ∩ score 帯 → 最終表示 band
 * @param {InternalConfidenceLabel | string | null | undefined} label
 * @param {number | null | undefined} score
 * @returns {ConfidenceBand}
 */
export function confidenceBandFromLabelAndScore(label, score) {
  const resolved =
    label && LABEL_CEILING_BAND[/** @type {string} */ (label)]
      ? /** @type {InternalConfidenceLabel} */ (label)
      : resolveInternalLabel({ score });
  const labelBand = LABEL_CEILING_BAND[resolved] || "low";
  const scoreBand = confidenceBandFromScore(score);
  const rank = Math.min(
    BAND_RANK[labelBand] ?? 0,
    BAND_RANK[scoreBand] ?? 0
  );
  return RANK_TO_BAND[rank];
}

/**
 * Bundle / PI 由来の入力から表示 band を一発解決
 * @param {{
 *   world?: unknown,
 *   near_miss?: unknown,
 *   affinity?: unknown,
 *   score?: number | null,
 * }} input
 * @returns {{ label: InternalConfidenceLabel, band: ConfidenceBand }}
 */
export function resolveConfidenceDisplay(input = {}) {
  const label = resolveInternalLabel(input);
  const band = confidenceBandFromLabelAndScore(label, input.score);
  return { label, band };
}
