/**
 * race_id 表示メタ（ブラウザ側・Prediction Core 非依存）
 */
(function (global) {
  "use strict";

  var VENUE_SLUG_JA = {
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
  };

  function parseRaceIdMeta(raceId) {
    var id = String(raceId || "").trim();
    if (!id) return null;
    var m = id.match(/^(\d{8})_([a-z]+)_(\d{1,2})$/i);
    if (m) {
      var ymd = m[1];
      var slug = m[2].toLowerCase();
      return {
        race_id: id,
        date: ymd.slice(0, 4) + "-" + ymd.slice(4, 6) + "-" + ymd.slice(6, 8),
        venue: VENUE_SLUG_JA[slug] || slug,
        venue_slug: slug,
        race_no: Number(m[3]),
        meeting_id: ymd + "_" + slug,
        place:
          (VENUE_SLUG_JA[slug] || slug) +
          (m[3] != null ? " " + Number(m[3]) + "R" : ""),
      };
    }
    return null;
  }

  function displayPlace(raceId, fallback) {
    var p = parseRaceIdMeta(raceId);
    if (p && p.place) return p.place;
    return fallback || "レース";
  }

  /** サンプル／プレースホルダ馬名を本番表示から除去 */
  function displayHorseName(name, horseNumber) {
    var n = String(name || "").trim();
    if (!n || /サンプル|sample|dummy|placeholder|test\s*horse/i.test(n)) {
      return horseNumber != null ? String(horseNumber) + "番" : "出走馬";
    }
    return n;
  }

  /**
   * 誤年 race_id を今週末（または今日）の年に補正。
   * 例: 2024-07-25-01-07 → 2026-07-25-01-07（MD が今週末に含まれるとき）
   * @returns {string|null} 補正後 ID。補正不要なら null
   */
  function correctRaceIdYear(raceId, instant) {
    var id = String(raceId || "").trim();
    var m = id.match(/^(\d{4})-(\d{2}-\d{2})-(.+)$/);
    if (!m) return null;
    var candidates = [];
    var seen = {};
    function pushDate(iso) {
      if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso) || seen[iso]) return;
      seen[iso] = true;
      candidates.push(iso);
    }
    if (global.ExpectWeekendCalendar) {
      if (typeof ExpectWeekendCalendar.jstParts === "function") {
        var parts = ExpectWeekendCalendar.jstParts(instant || new Date());
        if (parts && parts.date_jst) pushDate(parts.date_jst);
      }
      if (typeof ExpectWeekendCalendar.weekendRaceDates === "function") {
        (ExpectWeekendCalendar.weekendRaceDates(instant || new Date()) || []).forEach(pushDate);
      }
      if (typeof ExpectWeekendCalendar.decide === "function") {
        var cal = ExpectWeekendCalendar.decide(instant || new Date());
        if (cal) {
          if (cal.date_jst) pushDate(cal.date_jst);
          if (cal.next_open_date_jst) pushDate(cal.next_open_date_jst);
        }
      }
    }
    for (var i = 0; i < candidates.length; i++) {
      var d = candidates[i];
      if (m[2] === d.slice(5) && m[1] !== d.slice(0, 4)) {
        return d.slice(0, 4) + "-" + m[2] + "-" + m[3];
      }
    }
    return null;
  }

  /** 補正が必要なら補正後 ID、不要なら元の ID */
  function normalizeRaceIdYear(raceId, instant) {
    return correctRaceIdYear(raceId, instant) || String(raceId || "").trim();
  }

  /** 内部診断タグを一般 UI から除外 */
  function publicConfidenceFactors(factors) {
    if (!Array.isArray(factors)) return [];
    return factors.filter(function (f) {
      var s = String(f || "");
      if (!s) return false;
      if (/^[a-z0-9_]+:/i.test(s)) return false;
      if (/kpi\d+/i.test(s)) return false;
      if (/clarity|top_gap|venue_strong/i.test(s)) return false;
      return true;
    });
  }

  global.ExpectRaceIdMeta = {
    parseRaceIdMeta: parseRaceIdMeta,
    displayPlace: displayPlace,
    displayHorseName: displayHorseName,
    correctRaceIdYear: correctRaceIdYear,
    normalizeRaceIdYear: normalizeRaceIdYear,
    publicConfidenceFactors: publicConfidenceFactors,
    VENUE_SLUG_JA: VENUE_SLUG_JA,
  };
})(window);
