/**
 * ExpectApi.Supply — Coverage / Diagnostics クライアント
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
            (payload && payload.error && payload.error.message) || "Supply API error " + res.status
          );
        }
        return {
          data: payload && payload.data != null ? payload.data : payload,
          meta: (payload && payload.meta) || {},
        };
      });
    });
  }

  function coverage(opts) {
    opts = opts || {};
    return apiGet("/api/data/coverage", { date: opts.date || "" }).then(function (r) {
      return r.data;
    });
  }

  function diagnosticsMissing() {
    return apiGet("/api/diagnostics/missing").then(function (r) {
      return r.data;
    });
  }

  function fallbackReasons() {
    return apiGet("/api/diagnostics/fallback-reasons").then(function (r) {
      return r.data;
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Supply = {
    coverage: coverage,
    diagnosticsMissing: diagnosticsMissing,
    fallbackReasons: fallbackReasons,
  };
})(window);
