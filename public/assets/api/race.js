/**
 * ExpectApi.Race — Race Catalog クライアント
 *
 * GET /api/races?date=YYYY-MM-DD → PI /v1/races プロキシ（BFF 経由）
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

  function dateLabelFromIso(date) {
    var p = String(date || "").split("-");
    if (p.length !== 3) return "";
    return Number(p[1]) + "/" + Number(p[2]);
  }

  function dateFullFromIso(date) {
    var p = String(date || "").split("-");
    if (p.length !== 3) return "";
    var wd = ["日", "月", "火", "水", "木", "金", "土"];
    var d = new Date(date + "T12:00:00+09:00");
    var w = isNaN(d.getTime()) ? "" : wd[d.getUTCDay()] || "";
    return Number(p[1]) + "/" + Number(p[2]) + (w ? "（" + w + "）" : "");
  }

  /** PI race row → Web Race Catalog item（race_info 互換付き） */
  function mapPiRaceToWebItem(race) {
    if (!race || typeof race !== "object") return null;
    var course = String(race.course || race.venue || "");
    var raceNumber =
      race.race_number != null
        ? Number(race.race_number)
        : race.race_no != null
          ? Number(race.race_no)
          : null;
    var date = String(race.date || race.race_date || "");
    var raceName = String(race.race_name || "");
    var raceLabel = String(race.race_label || "");
    var raceId = String(race.race_id || "");
    return {
      race_id: raceId,
      race_label: raceLabel,
      race_name: raceName,
      course: course,
      race_number: raceNumber,
      status: String(race.status || "published"),
      race_info: {
        race_id: raceId,
        date: date,
        venue: course,
        race_no: raceNumber,
        course: course,
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

  function mapCatalogItems(catalog) {
    var races = (catalog && catalog.races) || [];
    return races
      .map(mapPiRaceToWebItem)
      .filter(function (item) {
        return item && item.race_id;
      });
  }

  /** 一覧カード用の最小 bundle 形（PredictionBundle 契約検証対象外） */
  function toCardBundle(item) {
    if (!item) return null;
    return {
      race_id: item.race_id,
      race_info: Object.assign({}, item.race_info || {}),
      ai_confidence: { score: null, status: "catalog" },
    };
  }

  function resolveListDate(opts) {
    opts = opts || {};
    if (opts.date) return String(opts.date);
    try {
      var params = new URLSearchParams(global.location.search || "");
      var fromUrl = params.get("date");
      if (fromUrl) return fromUrl;
    } catch (e) {
      /* ignore */
    }
    if (global.ExpectWeekendCalendar && ExpectWeekendCalendar.decide) {
      var cal = ExpectWeekendCalendar.decide(new Date());
      if (cal && cal.is_race_day && cal.date_jst) return cal.date_jst;
      if (cal && cal.next_open_date_jst) return cal.next_open_date_jst;
    }
    return "";
  }

  function apiGet(path, query) {
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
          throw err;
        }
        return payload && payload.data != null ? payload.data : payload;
      });
    });
  }

  var Race = {
    mapPiRaceToWebItem: mapPiRaceToWebItem,
    mapCatalogItems: mapCatalogItems,
    toCardBundle: toCardBundle,
    resolveListDate: resolveListDate,

    /** @returns {Promise<{date:string,count:number,races:object[],items:object[]}>} */
    list: function (opts) {
      opts = opts || {};
      var date = resolveListDate(opts);
      if (!date) {
        return Promise.reject(new Error("date is required for race catalog"));
      }
      return apiGet("/api/races", { date: date }).then(function (catalog) {
        var items = mapCatalogItems(catalog || {});
        return Object.assign({}, catalog || {}, { items: items });
      });
    },
  };

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Race = Race;
})(window);
