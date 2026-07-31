/**
 * ExpectApi.Single — Existing Site → Single AI (I1)
 *
 * POST /api/single
 * POST /api/single/:race_id
 * GET  /api/single/health
 * GET  /api/single/version
 *
 * Opt-in client. Does not replace ExpectApi.Prediction.
 * Race pages keep using Prediction unless Migration Guide says otherwise.
 */
(function (global) {
  "use strict";

  var SCHEMA = "site-integration/single/v1";

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function headers(json) {
    var h = { Accept: "application/json" };
    if (json) h["Content-Type"] = "application/json; charset=utf-8";
    var token = getToken();
    if (token) h.Authorization = "Bearer " + token;
    return h;
  }

  function parse(res) {
    return res.text().then(function (text) {
      var body = null;
      try {
        body = text ? JSON.parse(text) : null;
      } catch (e) {
        var err = new Error("non-JSON response");
        err.status = res.status;
        throw err;
      }
      if (!res.ok || (body && body.ok === false)) {
        var e2 = new Error(
          (body && body.error && body.error.message) || "Single API error"
        );
        e2.status = res.status;
        e2.code = body && body.error && body.error.code;
        e2.body = body;
        throw e2;
      }
      return body;
    });
  }

  var Single = {
    schema: SCHEMA,

    health: function () {
      return fetch("/api/single/health", { method: "GET", headers: headers(false) }).then(
        parse
      );
    },

    version: function () {
      return fetch("/api/single/version", { method: "GET", headers: headers(false) }).then(
        parse
      );
    },

    /**
     * @param {{ race_id: string, core_payload: object, options?: object, force?: boolean, timeout_ms?: number }} body
     */
    call: function (body) {
      return fetch("/api/single", {
        method: "POST",
        headers: headers(true),
        body: JSON.stringify(body || {}),
      }).then(parse);
    },

    /**
     * @param {string} raceId
     * @param {{ core_payload: object, options?: object, force?: boolean, timeout_ms?: number }} body
     */
    callByRaceId: function (raceId, body) {
      if (!raceId) return Promise.reject(new Error("race_id required"));
      return fetch("/api/single/" + encodeURIComponent(raceId), {
        method: "POST",
        headers: headers(true),
        body: JSON.stringify(body || {}),
      }).then(parse);
    },
  };

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Single = Single;
})(typeof window !== "undefined" ? window : this);
