/**
 * ExpectApi.Stats — 過去実績ヒートマップ等
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

  function apiGet(path, query) {
    var url = path;
    if (query && typeof query === "object") {
      var qs = new URLSearchParams();
      Object.keys(query).forEach(function (k) {
        if (query[k] != null && query[k] !== "") qs.set(k, query[k]);
      });
      var q = qs.toString();
      if (q) url += "?" + q;
    }
    var headers = { Accept: "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;

    return fetch(url, { method: "GET", headers: headers }).then(function (res) {
      return res.text().then(function (text) {
        var payload = null;
        try {
          payload = text ? JSON.parse(text) : null;
        } catch (e) {
          payload = null;
        }
        if (!res.ok || (payload && payload.ok === false)) {
          throw new Error(
            (payload && payload.error && payload.error.message) || "Stats API error " + res.status
          );
        }
        return {
          data: payload && payload.data != null ? payload.data : payload,
          meta: (payload && payload.meta) || {},
        };
      });
    });
  }

  function heatmap(opts) {
    opts = opts || {};
    var query = {};
    if (opts.venues) query.venues = opts.venues;
    return apiGet("/api/v1/stats/heatmap", query).then(function (r) {
      return r.data;
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Stats = {
    heatmap: heatmap,
  };
})(window);
