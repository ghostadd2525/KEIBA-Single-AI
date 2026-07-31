/**
 * ExpectApi.RaceCards — RaceCardSummary 一覧クライアント
 *
 * GET /api/race-cards?date=YYYY-MM-DD
 * Feature Flag（BFF）: v2_race_cards
 * Web 表示 Flag: v2_race_list_ui（呼び出し側）
 */
(function (global) {
  "use strict";

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function buildUrl(path, query) {
    var url = path;
    if (query && typeof query === "object") {
      var qs = new URLSearchParams();
      Object.keys(query).forEach(function (k) {
        if (query[k] != null && query[k] !== "") qs.set(k, query[k]);
      });
      var q = qs.toString();
      if (q) url += "?" + q;
    }
    return url;
  }

  function resolveDate(opts) {
    opts = opts || {};
    if (opts.date) return String(opts.date);
    if (global.ExpectApi && ExpectApi.Race && ExpectApi.Race.resolveListDate) {
      return ExpectApi.Race.resolveListDate(opts) || "";
    }
    if (global.ExpectRaceListUrl && ExpectRaceListUrl.resolveFromLocation) {
      var r = ExpectRaceListUrl.resolveFromLocation();
      if (r && r.date) return r.date;
    }
    if (global.ExpectRaceListUrl && ExpectRaceListUrl.calendarFallbackDate) {
      return ExpectRaceListUrl.calendarFallbackDate(new Date()) || "";
    }
    return "";
  }

  function apiGet(path, query) {
    function doFetch() {
      var headers = { Accept: "application/json" };
      var token = getToken();
      if (token) headers.Authorization = "Bearer " + token;

      return fetch(buildUrl(path, query), { method: "GET", headers: headers }).then(function (res) {
        return res.text().then(function (text) {
          var payload = null;
          try {
            payload = text ? JSON.parse(text) : null;
          } catch (e) {
            payload = null;
          }
          if (!res.ok || (payload && payload.ok === false)) {
            var err = new Error(
              (payload && payload.error && payload.error.message) || "API error " + res.status
            );
            err.status = res.status;
            err.code = payload && payload.error && payload.error.code;
            err.payload = payload;
            throw err;
          }
          return payload && payload.data != null ? payload.data : payload;
        });
      });
    }

    if (global.ExpectHttpCache) {
      var key = ExpectHttpCache.buildKey(path, query);
      return ExpectHttpCache.cachedGet(key, ExpectHttpCache.TTL.race_cards, doFetch);
    }
    return doFetch();
  }

  var RaceCards = {
    resolveDate: resolveDate,

    /**
     * @param {{ date?: string }} opts
     * @returns {Promise<{ date: string, count: number, race_cards: object[] }>}
     */
    list: function (opts) {
      opts = opts || {};
      var date = resolveDate(opts);
      if (!date) {
        return Promise.reject(new Error("date is required for race-cards"));
      }
      return apiGet("/api/race-cards", { date: date }).then(function (data) {
        var cards = (data && data.race_cards) || [];
        return {
          schema_version: (data && data.schema_version) || "expect-race-cards/1.0",
          date: (data && data.date) || date,
          count: data && data.count != null ? data.count : cards.length,
          race_cards: cards,
        };
      });
    },
  };

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.RaceCards = RaceCards;
})(window);
