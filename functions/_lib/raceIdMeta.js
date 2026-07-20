/**
 * race_id → 開催メタ（BFF / UI 共通の軽量パーサ）
 * Prediction Core 非依存。表示整合・モック再バインド用。
 */

/** @type {Readonly<Record<string, string>>} */
export const VENUE_SLUG_JA = Object.freeze({
  sapporo: "札幌",
  hakodate: "函館",
  fukushima: "福島",
  niigata: "新潟",
  tokyo: "東京",
  nakayama: "中山",
  chukyo: "中京",
  kyoto: "京都",
  hanshin: "阪神",
  kokura: "小倉",
});

/**
 * @param {unknown} raceId
 * @returns {{
 *   race_id: string,
 *   date: string | null,
 *   venue: string | null,
 *   venue_slug: string | null,
 *   race_no: number | null,
 *   meeting_id: string | null,
 * } | null}
 */
export function parseRaceIdMeta(raceId) {
  const id = String(raceId || "").trim();
  if (!id) return null;

  // 20260719_tokyo_11
  let m = id.match(/^(\d{8})_([a-z]+)_(\d{1,2})$/i);
  if (m) {
    const ymd = m[1];
    const slug = m[2].toLowerCase();
    const race_no = Number(m[3]);
    const date = `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`;
    return {
      race_id: id,
      date,
      venue: VENUE_SLUG_JA[slug] || slug,
      venue_slug: slug,
      race_no,
      meeting_id: `${ymd}_${slug}`,
    };
  }

  // 2026-07-19-04-11（core 風）— venue は推定不可
  m = id.match(/^(\d{4}-\d{2}-\d{2})-(\d{1,2})-(\d{1,2})$/);
  if (m) {
    return {
      race_id: id,
      date: m[1],
      venue: null,
      venue_slug: null,
      race_no: Number(m[3]),
      meeting_id: null,
    };
  }

  return null;
}

/**
 * race_info を race_id と整合させる（venue / race_no / date / meeting_id）。
 * @param {object} raceInfo
 * @param {string} raceId
 */
export function alignRaceInfoToRaceId(raceInfo, raceId) {
  const parsed = parseRaceIdMeta(raceId);
  if (!parsed) return raceInfo || {};
  const info = { ...(raceInfo || {}) };
  info.race_id = raceId;

  if (parsed.date && (!info.date || info.date !== parsed.date)) {
    info.date = parsed.date;
  }
  if (parsed.race_no != null && (info.race_no == null || Number(info.race_no) !== parsed.race_no)) {
    info.race_no = parsed.race_no;
  }
  if (parsed.venue) {
    // race_id に会場スラッグがある場合はそれを正とする（モックテンプレ混入対策）
    info.venue = parsed.venue;
  }
  if (parsed.meeting_id) {
    info.meeting_id = parsed.meeting_id;
  }
  return info;
}

/**
 * @param {object} bundle
 * @param {string} raceId
 */
export function alignBundleToRaceId(bundle, raceId) {
  if (!bundle || typeof bundle !== "object") return bundle;
  const id = raceId || bundle.race_id;
  if (!id) return bundle;
  return {
    ...bundle,
    race_id: id,
    race_info: alignRaceInfoToRaceId(bundle.race_info || {}, id),
  };
}
