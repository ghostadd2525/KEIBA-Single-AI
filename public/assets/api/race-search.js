/**
 * ExpectRaceSearch — Race Catalog 検索マッチ（Phase 4）
 *
 * 設計: docs/releases/v2-ui-enhancement-mock.md §3.5
 * - Catalog: レース名 / 会場 / R（place）/ 日付
 * - v2 拡張（v2_race_list_ui または data-prediction-status あり）:
 *   本命馬名（data-race-honmei）/ 信頼度% / band
 * - Flag OFF（v1 カード）: Catalog フィールドのみ → v1.1 と同一
 */
(function (global) {
  "use strict";

  var BAND_SEARCH_LABEL = {
    high: "高い high",
    medium: "中程度 ふつう medium",
    low: "低い low",
  };

  /**
   * @param {{
   *   date?: string,
   *   venue?: string,
   *   name?: string,
   *   place?: string,
   *   honmei?: string,
   *   conf?: string|number,
   *   band?: string,
   *   v2Enhanced?: boolean
   * }} fields
   */
  function buildSearchHaystack(fields) {
    fields = fields || {};
    var parts = [
      fields.date || "",
      fields.venue || "",
      fields.name || "",
      fields.place || "",
    ];
    if (fields.v2Enhanced) {
      parts.push(fields.honmei || "");
      if (fields.conf != null && fields.conf !== "") {
        parts.push(String(fields.conf));
        parts.push(String(fields.conf) + "%");
      }
      var band = fields.band || "";
      if (band) {
        parts.push(band);
        parts.push(BAND_SEARCH_LABEL[band] || "");
      }
    }
    return parts.join(" ").toLowerCase().replace(/\s+/g, " ").trim();
  }

  function fieldsFromElement(el) {
    if (!el || !el.getAttribute) {
      return {
        date: "",
        venue: "",
        name: "",
        place: "",
        honmei: "",
        conf: "",
        band: "",
        v2Enhanced: false,
      };
    }
    var hasStatus = el.hasAttribute("data-prediction-status");
    var flagOn =
      global.ExpectUiFeatures &&
      typeof ExpectUiFeatures.enabled === "function" &&
      ExpectUiFeatures.enabled("v2_race_list_ui");
    return {
      date: el.getAttribute("data-race-date") || "",
      venue: el.getAttribute("data-race-venue") || "",
      name: el.getAttribute("data-race-name") || "",
      place: el.getAttribute("data-race-place") || "",
      honmei: el.getAttribute("data-race-honmei") || "",
      conf: el.getAttribute("data-race-conf") || "",
      band: el.getAttribute("data-confidence-band") || "",
      v2Enhanced: !!(flagOn || hasStatus),
    };
  }

  function datesMatch(cardDate, wantDate) {
    var date = String(cardDate || "").trim();
    var want = String(wantDate || "").trim();
    if (!want || want === "all") return true;
    if (!date) return false;
    if (date === want) return true;
    // "7/26" ↔ "2026-07-26"
    if (/^\d{4}-\d{2}-\d{2}$/.test(want)) {
      var label =
        String(Number(want.slice(5, 7))) + "/" + String(Number(want.slice(8, 10)));
      var labelPad = want.slice(5, 7) + "/" + want.slice(8, 10);
      if (date === label || date === labelPad) return true;
    }
    if (/^\d{1,2}\/\d{1,2}$/.test(date) && /^\d{4}-\d{2}-\d{2}$/.test(want)) {
      var p = date.split("/");
      var m = Number(p[0]);
      var d = Number(p[1]);
      return Number(want.slice(5, 7)) === m && Number(want.slice(8, 10)) === d;
    }
    // race_id prefix
    if (date.indexOf(want) === 0) return true;
    return false;
  }

  /**
   * @param {object} fields fieldsFromElement または同等
   * @param {{ q?: string, date?: string, venue?: string }} state
   */
  /**
   * 発走時刻を過ぎたレースか（JST）。時刻不明なら false（一覧に残す）。
   * @param {string} dateIso YYYY-MM-DD
   * @param {string} postTime HH:MM
   */
  function isPostTimePassed(dateIso, postTime) {
    var date = String(dateIso || "").trim();
    var m = String(postTime || "").trim().match(/^(\d{1,2}):(\d{2})/);
    if (!m || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
    var hh = String(Number(m[1])).padStart(2, "0");
    var at = Date.parse(date + "T" + hh + ":" + m[2] + ":00+09:00");
    if (!Number.isFinite(at)) return false;
    return Date.now() >= at;
  }

  function matchRaceSearch(fields, state) {
    state = state || {};
    var date = String(fields.date || "").trim();
    var venue = String(fields.venue || "").trim();
    var place = String(fields.place || "").trim();
    var time = String(fields.time || "").trim();
    var wantVenue = String(state.venue || "").trim();
    if (state.date && state.date !== "all" && !datesMatch(date, state.date)) return false;
    if (wantVenue && wantVenue !== "all") {
      if (venue !== wantVenue && place.indexOf(wantVenue) < 0) return false;
    }
    // 出走後は一覧から除外（hideStarted !== false のとき）
    if (state.hideStarted !== false && isPostTimePassed(date, time)) return false;
    var q = (state.q || "").trim();
    if (!q) return true;
    var hay = buildSearchHaystack(fields);
    var tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
    for (var i = 0; i < tokens.length; i++) {
      if (hay.indexOf(tokens[i]) < 0) return false;
    }
    return true;
  }

  function matchElement(el, state) {
    var fields = fieldsFromElement(el);
    fields.time = el.getAttribute("data-race-time") || "";
    return matchRaceSearch(fields, state);
  }

  global.ExpectRaceSearch = {
    buildSearchHaystack: buildSearchHaystack,
    fieldsFromElement: fieldsFromElement,
    matchRaceSearch: matchRaceSearch,
    matchElement: matchElement,
    isPostTimePassed: isPostTimePassed,
    BAND_SEARCH_LABEL: BAND_SEARCH_LABEL,
  };
})(typeof window !== "undefined" ? window : globalThis);
