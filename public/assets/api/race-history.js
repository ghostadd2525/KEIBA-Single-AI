/**
 * ExpectApi.RaceHistory — 近走データ（Version7.2）
 * GET /api/races/:id/history
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

  function getHistory(raceId, opts) {
    opts = opts || {};
    if (!raceId) return Promise.reject(new Error("race_id required"));
    var headers = { accept: "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;
    var timeoutMs =
      typeof opts.timeoutMs === "number" && opts.timeoutMs > 0 ? opts.timeoutMs : 60000;
    var qs = opts.fresh ? "?_=" + Date.now() : "";
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;
    if (controller) {
      timer = setTimeout(function () {
        try {
          controller.abort();
        } catch (e) { /* ignore */ }
      }, timeoutMs);
    }
    return fetch(
      "/api/races/" + encodeURIComponent(raceId) + "/history" + qs,
      {
        headers: headers,
        credentials: "same-origin",
        signal: controller ? controller.signal : undefined,
        cache: opts.fresh ? "no-store" : "default",
      }
    )
      .then(function (res) {
        return res.json().then(function (body) {
          if (!res.ok || (body && body.ok === false)) {
            var err = new Error(
              (body && body.error && body.error.message) || "history fetch failed"
            );
            err.code = body && body.error && body.error.code;
            err.status = res.status;
            throw err;
          }
          return (body && body.data) || body;
        });
      })
      .catch(function (err) {
        if (err && err.name === "AbortError") {
          var te = new Error("history timeout");
          te.code = "TIMEOUT";
          throw te;
        }
        throw err;
      })
      .finally(function () {
        if (timer) clearTimeout(timer);
      });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.RaceHistory = {
    getHistory: getHistory,
  };
})(typeof window !== "undefined" ? window : this);
