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
    publicConfidenceFactors: publicConfidenceFactors,
    VENUE_SLUG_JA: VENUE_SLUG_JA,
  };
})(window);
