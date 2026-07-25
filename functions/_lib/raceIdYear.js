/**
 * race_id の誤年補正（サーバー）
 * 例: 2024-07-25-01-07 → 2026-07-25-01-07（MD が今週末に含まれるとき）
 */

function jstParts(instant = new Date()) {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  });
  const map = {};
  fmt.formatToParts(instant).forEach((p) => {
    if (p.type !== "literal") map[p.type] = p.value;
  });
  const y = Number(map.year);
  const m = Number(map.month);
  const d = Number(map.day);
  const wdMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  const weekday = wdMap[map.weekday] != null ? wdMap[map.weekday] : 0;
  const date_jst =
    String(y).padStart(4, "0") +
    "-" +
    String(m).padStart(2, "0") +
    "-" +
    String(d).padStart(2, "0");
  return { y, m, d, date_jst, weekday };
}

function addDaysJst(y, m, d, addDays) {
  const utc = Date.UTC(y, m - 1, d + addDays, 3, 0, 0);
  return jstParts(new Date(utc)).date_jst;
}

function weekendRaceDates(instant = new Date()) {
  const parts = jstParts(instant);
  let sat;
  let sun;
  if (parts.weekday === 6) {
    sat = parts.date_jst;
    sun = addDaysJst(parts.y, parts.m, parts.d, 1);
  } else if (parts.weekday === 0) {
    sun = parts.date_jst;
    sat = addDaysJst(parts.y, parts.m, parts.d, -1);
  } else {
    const daysUntilSat = (6 - parts.weekday + 7) % 7 || 7;
    sat = addDaysJst(parts.y, parts.m, parts.d, daysUntilSat);
    const sp = jstParts(
      new Date(
        Date.UTC(
          Number(sat.slice(0, 4)),
          Number(sat.slice(5, 7)) - 1,
          Number(sat.slice(8, 10)),
          3,
          0,
          0
        )
      )
    );
    sun = addDaysJst(sp.y, sp.m, sp.d, 1);
  }
  return [sat, sun];
}

/**
 * @param {string} raceId
 * @returns {string|null} 補正後 ID。不要なら null
 */
export function correctRaceIdYear(raceId, instant = new Date()) {
  const id = String(raceId || "").trim();
  const m = id.match(/^(\d{4})-(\d{2}-\d{2})-(.+)$/);
  if (!m) return null;
  const candidates = weekendRaceDates(instant);
  const today = jstParts(instant).date_jst;
  if (today && !candidates.includes(today)) candidates.unshift(today);
  for (const d of candidates) {
    if (m[2] === d.slice(5) && m[1] !== d.slice(0, 4)) {
      return d.slice(0, 4) + "-" + m[2] + "-" + m[3];
    }
  }
  return null;
}

export function normalizeRaceIdYear(raceId, instant = new Date()) {
  return correctRaceIdYear(raceId, instant) || String(raceId || "").trim();
}
