/**
 * CalendarProvider — 開催日判定の差し替え口（Version 1.1 auto maintenance）
 *
 * 曜日や祝日ロジックを opsMode にハードコードしない。
 * 初期実装: WeekendCalendarProvider
 * 将来: OpsCalendarProvider（ops-calendar.json）
 */

/**
 * @typedef {object} CalendarDecision
 * @property {boolean} is_race_day
 * @property {string} date_jst          // YYYY-MM-DD (Asia/Tokyo)
 * @property {string|null} next_open_date_jst
 * @property {string} source            // "weekend" | "ops-calendar" | ...
 * @property {string} [note]
 */

/**
 * @typedef {object} CalendarProvider
 * @property {string} id
 * @property {(instant: Date) => CalendarDecision | Promise<CalendarDecision>} decide
 */

/**
 * Instant → JST calendar date parts.
 * @param {Date} instant
 * @returns {{ y: number, m: number, d: number, date_jst: string, weekday: number }}
 *   weekday: 0=Sun … 6=Sat（JST）
 */
export function jstParts(instant) {
  const d = instant instanceof Date ? instant : new Date();
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  });
  const map = {};
  fmt.formatToParts(d).forEach(function (p) {
    if (p.type !== "literal") map[p.type] = p.value;
  });
  const y = Number(map.year);
  const m = Number(map.month);
  const day = Number(map.day);
  const wdMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  const weekday = wdMap[map.weekday] != null ? wdMap[map.weekday] : 0;
  const date_jst =
    String(y).padStart(4, "0") +
    "-" +
    String(m).padStart(2, "0") +
    "-" +
    String(day).padStart(2, "0");
  return { y: y, m: m, d: day, date_jst: date_jst, weekday: weekday };
}

/**
 * @param {number} y
 * @param {number} m 1-12
 * @param {number} d
 * @param {number} addDays
 * @returns {string} YYYY-MM-DD
 */
export function addDaysJst(y, m, d, addDays) {
  // noon UTC-ish via Date.UTC then shift: use pure civil date math in JST by UTC noon trick
  const utc = Date.UTC(y, m - 1, d + addDays, 3, 0, 0); // 12:00 JST approx
  const parts = jstParts(new Date(utc));
  return parts.date_jst;
}

export default {};
