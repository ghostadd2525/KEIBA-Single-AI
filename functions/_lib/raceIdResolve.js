/**
 * PI race_id（Win5 形式）解決ヘルパ
 *
 * 正式キー: YYYY-MM-DD-LL-RR（例: 2026-07-25-01-06）
 */

/** @type {RegExp} */
export const PI_RACE_ID_RE = /^(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{2})$/;

/** @param {string} raceId */
export function isPiRaceId(raceId) {
  return PI_RACE_ID_RE.test(String(raceId || "").trim());
}

/** @param {string} raceId */
export function extractDateFromPiRaceId(raceId) {
  const m = String(raceId || "").trim().match(PI_RACE_ID_RE);
  return m ? m[1] : "";
}

/**
 * PI /v1/races catalog から race_id 行を検索
 * @param {object} catalog
 * @param {string} raceId
 */
export function findPiRaceInCatalog(catalog, raceId) {
  const id = String(raceId || "").trim();
  const races = Array.isArray(catalog && catalog.races) ? catalog.races : [];
  return races.find((r) => String(r.race_id || "") === id) || null;
}
