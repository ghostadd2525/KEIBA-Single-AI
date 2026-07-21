/**
 * CalendarProvider factory
 *
 * beta.calendar_provider:
 *   - "weekend" | unset → WeekendCalendarProvider（既定）
 *   - "ops-calendar" → 将来 OpsCalendarProvider（未実装時は weekend にフォールバック）
 */
import { WeekendCalendarProvider } from "./WeekendCalendarProvider.js";

/**
 * @param {object | null | undefined} beta
 * @returns {import("./CalendarProvider.js").CalendarProvider}
 */
export function createCalendarProvider(beta) {
  const id =
    beta && beta.calendar_provider != null
      ? String(beta.calendar_provider).trim().toLowerCase()
      : "weekend";

  if (id === "ops-calendar") {
    // 差し替え口のみ。ops-calendar.json 実装までは weekend へフォールバック。
    return WeekendCalendarProvider;
  }

  return WeekendCalendarProvider;
}

export default createCalendarProvider;
