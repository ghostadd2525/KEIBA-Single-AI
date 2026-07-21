/**
 * Weekend calendar mirror (client) — status API 失敗時のフォールバックのみ。
 * 正本は BFF /api/ops/public-status。
 */
(function (global) {
  "use strict";

  function jstParts(instant) {
    var d = instant instanceof Date ? instant : new Date();
    var fmt = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Tokyo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      weekday: "short",
    });
    var map = {};
    fmt.formatToParts(d).forEach(function (p) {
      if (p.type !== "literal") map[p.type] = p.value;
    });
    var y = Number(map.year);
    var m = Number(map.month);
    var day = Number(map.day);
    var wdMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
    var weekday = wdMap[map.weekday] != null ? wdMap[map.weekday] : 0;
    var date_jst =
      String(y).padStart(4, "0") +
      "-" +
      String(m).padStart(2, "0") +
      "-" +
      String(day).padStart(2, "0");
    return { y: y, m: m, d: day, date_jst: date_jst, weekday: weekday };
  }

  function addDaysJst(y, m, d, addDays) {
    var utc = Date.UTC(y, m - 1, d + addDays, 3, 0, 0);
    return jstParts(new Date(utc)).date_jst;
  }

  function decide(instant) {
    var parts = jstParts(instant || new Date());
    var isRace = parts.weekday === 0 || parts.weekday === 6;
    var nextOpen = parts.date_jst;
    if (!isRace) {
      var daysUntilSat = (6 - parts.weekday + 7) % 7 || 7;
      nextOpen = addDaysJst(parts.y, parts.m, parts.d, daysUntilSat);
    }
    return {
      is_race_day: isRace,
      date_jst: parts.date_jst,
      next_open_date_jst: nextOpen,
      source: "weekend",
    };
  }

  global.ExpectWeekendCalendar = {
    decide: decide,
    jstParts: jstParts,
  };
})(window);
