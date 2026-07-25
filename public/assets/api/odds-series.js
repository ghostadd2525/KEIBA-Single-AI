/**
 * ExpectApi.OddsSeries — 単勝オッズ時系列
 * GET /api/races/:id/odds-series[?refresh=1]
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

  function api(path, opts) {
    opts = opts || {};
    var headers = { accept: "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;
    var fetchOpts = { headers: headers, credentials: "same-origin" };
    if (opts.fresh) fetchOpts.cache = "no-store";
    return fetch(path, fetchOpts).then(function (res) {
      return res.json().then(function (body) {
        if (!res.ok || (body && body.ok === false)) {
          var err = new Error(
            (body && body.error && body.error.message) || "odds series fetch failed"
          );
          err.code = body && body.error && body.error.code;
          err.status = res.status;
          throw err;
        }
        return (body && body.data) || body;
      });
    });
  }

  function getSeries(raceId, opts) {
    opts = opts || {};
    var qs = [];
    if (opts.refresh) qs.push("refresh=1");
    if (opts.fresh) qs.push("_=" + Date.now());
    var q = qs.length ? "?" + qs.join("&") : "";
    return api("/api/races/" + encodeURIComponent(raceId) + "/odds-series" + q, {
      fresh: !!opts.fresh,
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.OddsSeries = { getSeries: getSeries };
})(typeof window !== "undefined" ? window : globalThis);
