/**
 * ExpectApi.SingleDetail — I3 Detail-only Feature Flag wiring
 *
 * Flag OFF (default): ExpectApi.Prediction.getWithMeta
 * Flag ON: /api/single/detail/:raceId → Bundle (Single when core available,
 *          else Prediction fallback). On transport error → Prediction.
 *
 * List pages must NOT load this module.
 * Race List Cache is never touched.
 */
(function (global) {
  "use strict";

  var FLAG = "single_ai_detail";
  var TIMEOUT_MS = 14000;

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function flagOn() {
    return !!(
      global.ExpectUiFeatures &&
      typeof ExpectUiFeatures.enabled === "function" &&
      ExpectUiFeatures.enabled(FLAG)
    );
  }

  function readOptionalCore(raceId) {
    // Staging/Shadow only: optional core inject (does not invent Core)
    try {
      var raw = global.sessionStorage.getItem("expect_single_core_" + raceId);
      if (!raw) return null;
      var o = JSON.parse(raw);
      return o && typeof o === "object" ? o : null;
    } catch (e) {
      return null;
    }
  }

  function predictionFallback(raceId) {
    if (!global.ExpectApi || !ExpectApi.Prediction || !ExpectApi.Prediction.getWithMeta) {
      return Promise.reject(new Error("Prediction API unavailable"));
    }
    return ExpectApi.Prediction.getWithMeta(raceId).then(function (result) {
      if (result && result.meta) {
        result.meta.detail_source = result.meta.detail_source || "prediction";
        result.meta.single_detail_flag = flagOn();
      }
      return result;
    });
  }

  function parseDetailResponse(res) {
    return res.text().then(function (text) {
      var body = null;
      try {
        body = text ? JSON.parse(text) : null;
      } catch (e) {
        var err = new Error("non-JSON response");
        err.status = res.status;
        err.code = "BAD_RESPONSE";
        throw err;
      }
      if (res.status === 202 || (body && body.error && body.error.code === "PREDICTION_PENDING")) {
        return {
          bundle: null,
          meta: (body && body.meta) || {},
          pending: true,
          error: (body && body.error) || { code: "PREDICTION_PENDING" },
        };
      }
      if (!res.ok || (body && body.ok === false)) {
        var e2 = new Error(
          (body && body.error && body.error.message) || "Single detail error"
        );
        e2.status = res.status;
        e2.code = body && body.error && body.error.code;
        e2.body = body;
        throw e2;
      }
      return {
        bundle: body.data,
        meta: body.meta || {},
      };
    });
  }

  function fetchSingleDetail(raceId, timeoutMs) {
    var headers = { Accept: "application/json", "Content-Type": "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;
    var core = readOptionalCore(raceId);
    var body = {
      timeout_ms: timeoutMs || TIMEOUT_MS,
      force: false,
    };
    try {
      if (global.sessionStorage.getItem("expect_single_force_v1") === "1") {
        body.force = true;
      }
    } catch (e) { /* ignore */ }
    if (core) body.core_payload = core;

    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;
    var p = fetch("/api/single/detail/" + encodeURIComponent(raceId), {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
      signal: controller ? controller.signal : undefined,
    }).then(parseDetailResponse);

    if (controller) {
      timer = setTimeout(function () {
        try {
          controller.abort();
        } catch (e) { /* ignore */ }
      }, timeoutMs || TIMEOUT_MS);
      p = p.finally(function () {
        if (timer) clearTimeout(timer);
      });
    }
    return p;
  }

  /**
   * @param {string} raceId
   * @returns {Promise<{bundle: object|null, meta: object, pending?: boolean}>}
   */
  function getWithMeta(raceId) {
    if (!raceId) return Promise.reject(new Error("race_id required"));

    var ready =
      global.ExpectUiFeatures && typeof ExpectUiFeatures.ready === "function"
        ? ExpectUiFeatures.ready()
        : Promise.resolve(null);

    return Promise.resolve(ready).then(function () {
      if (!flagOn()) {
        return predictionFallback(raceId);
      }

      return fetchSingleDetail(raceId, TIMEOUT_MS).catch(function (err) {
        // Timeout / network / 5xx → immediate Prediction rollback path
        return predictionFallback(raceId).then(function (result) {
          if (result && result.meta) {
            result.meta.detail_source = "prediction_fallback";
            result.meta.single_detail_flag = true;
            result.meta.fallback_reason =
              (err && err.code) ||
              (err && err.name === "AbortError" ? "TIMEOUT" : "SINGLE_DETAIL_ERROR");
          }
          return result;
        });
      });
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.SingleDetail = {
    flagName: FLAG,
    isEnabled: flagOn,
    getWithMeta: getWithMeta,
    /** test helper */
    _predictionFallback: predictionFallback,
    _fetchSingleDetail: fetchSingleDetail,
  };
})(typeof window !== "undefined" ? window : this);
