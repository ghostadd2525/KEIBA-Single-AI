/**
 * WeekendCalendarProvider — 既定の開催日判定（土日 = 開催日）
 */
import { addDaysJst, jstParts } from "./CalendarProvider.js";

/**
 * @param {Date} [instant]
 * @returns {import("./CalendarProvider.js").CalendarDecision}
 */
export function decideWeekend(instant) {
  const parts = jstParts(instant || new Date());
  const isRace = parts.weekday === 0 || parts.weekday === 6;
  let nextOpen = parts.date_jst;
  if (!isRace) {
    // days until next Saturday
    const daysUntilSat = (6 - parts.weekday + 7) % 7 || 7;
    nextOpen = addDaysJst(parts.y, parts.m, parts.d, daysUntilSat);
  }
  return {
    is_race_day: isRace,
    date_jst: parts.date_jst,
    next_open_date_jst: nextOpen,
    source: "weekend",
    note: "JST Sat/Sun = race day; Mon-Fri = maintenance",
  };
}

/** @type {import("./CalendarProvider.js").CalendarProvider} */
export const WeekendCalendarProvider = {
  id: "weekend",
  decide: function (instant) {
    return decideWeekend(instant);
  },
};

export default WeekendCalendarProvider;
