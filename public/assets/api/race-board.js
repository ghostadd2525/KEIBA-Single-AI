/**
 * ExpectApi.RaceBoard — 出馬表 / オッズ / 近走
 * GET /api/races/:id/board[?include=history]
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
    var timeoutMs =
      typeof opts.timeoutMs === "number" && opts.timeoutMs > 0 ? opts.timeoutMs : 15000;
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;
    if (controller) {
      timer = setTimeout(function () {
        try {
          controller.abort();
        } catch (e) { /* ignore */ }
      }, timeoutMs);
    }
    var fetchOpts = {
      headers: headers,
      credentials: "same-origin",
      signal: controller ? controller.signal : undefined,
    };
    if (opts.fresh) fetchOpts.cache = "no-store";
    return fetch(path, fetchOpts)
      .then(function (res) {
        return res.json().then(function (body) {
          if (!res.ok || (body && body.ok === false)) {
            var err = new Error(
              (body && body.error && body.error.message) || "board fetch failed"
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
          var te = new Error("board timeout");
          te.code = "TIMEOUT";
          throw te;
        }
        throw err;
      })
      .finally(function () {
        if (timer) clearTimeout(timer);
      });
  }

  function getBoard(raceId, opts) {
    opts = opts || {};
    var qs = [];
    if (opts.includeHistory) qs.push("include=history");
    // 強制更新時はブラウザ/中間キャッシュを避ける（PI 側は 5 分 TTL）
    if (opts.fresh) qs.push("_=" + Date.now());
    var q = qs.length ? "?" + qs.join("&") : "";
    return api("/api/races/" + encodeURIComponent(raceId) + "/board" + q, {
      fresh: !!opts.fresh,
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.RaceBoard = {
    getBoard: getBoard,
  };
})(typeof window !== "undefined" ? window : globalThis);
