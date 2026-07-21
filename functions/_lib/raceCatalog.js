/**
 * PI /v1/races 行 → Web Race Catalog 契約（一覧表示用）
 *
 * 既存 UI は race_info.venue / race_no / class_label を参照するため互換フィールドも付与。
 */

function dateLabelFromIso(date) {
  const p = String(date || "").split("-");
  if (p.length !== 3) return "";
  return `${Number(p[1])}/${Number(p[2])}`;
}

function dateFullFromIso(date) {
  const p = String(date || "").split("-");
  if (p.length !== 3) return "";
  const wd = ["日", "月", "火", "水", "木", "金", "土"];
  const d = new Date(`${date}T12:00:00+09:00`);
  const w = Number.isNaN(d.getTime()) ? "" : wd[d.getUTCDay()] || "";
  return `${Number(p[1])}/${Number(p[2])}${w ? "（" + w + "）" : ""}`;
}

/** @param {Record<string, unknown>} race PI API race row */
export function mapPiRaceToWebItem(race) {
  if (!race || typeof race !== "object") {
    throw new Error("invalid PI race row");
  }
  const course = String(race.course || race.venue || "");
  const raceNumber =
    race.race_number != null
      ? Number(race.race_number)
      : race.race_no != null
        ? Number(race.race_no)
        : null;
  const date = String(race.date || race.race_date || "");
  const raceName = String(race.race_name || "");
  const raceLabel = String(race.race_label || "");
  const raceId = String(race.race_id || "");

  return {
    race_id: raceId,
    race_label: raceLabel,
    race_name: raceName,
    course,
    race_number: raceNumber,
    status: String(race.status || "published"),
    race_info: {
      race_id: raceId,
      date,
      venue: course,
      race_no: raceNumber,
      course,
      class_label: raceName,
      race_label: raceLabel,
      race_name: raceName,
      race_status: String(race.status || "published"),
      date_label: dateLabelFromIso(date),
      date_full: dateFullFromIso(date),
      post_time: race.post_time != null ? String(race.post_time) : "",
    },
  };
}

/** @param {Record<string, unknown>} catalog PI /v1/races payload */
export function mapPiCatalogToWebItems(catalog) {
  const races = Array.isArray(catalog && catalog.races) ? catalog.races : [];
  return races.map((race) => mapPiRaceToWebItem(race));
}
