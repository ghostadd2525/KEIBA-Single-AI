/** RaceCardSummary / 信頼度表示の band 閾値（BFF 責務） */
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
