/**
 * ExpectApi.Supply — Coverage / Diagnostics クライアント
 */
(function (global) {
  "use strict";

  var DEFAULT_TIMEOUT_MS = 5000;

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function apiGet(path, query, opts) {
    opts = opts || {};
    var timeoutMs =
      typeof opts.timeoutMs === "number" && opts.timeoutMs > 0
        ? opts.timeoutMs
        : DEFAULT_TIMEOUT_MS;
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

    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;
    if (controller) {
      timer = setTimeout(function () {
        try {
          controller.abort();
        } catch (e) { /* ignore */ }
      }, timeoutMs);
    }

    return fetch(url, {
      method: "GET",
      headers: headers,
      signal: controller ? controller.signal : undefined,
    })
      .then(function (res) {
        return res.text().then(function (text) {
          var payload = null;
          try {
            payload = text ? JSON.parse(text) : null;
          } catch (e) {
            payload = null;
          }
          if (!res.ok || (payload && payload.ok === false)) {
            throw new Error(
              (payload && payload.error && payload.error.message) ||
                "Supply API error " + res.status
            );
          }
          return {
            data: payload && payload.data != null ? payload.data : payload,
            meta: (payload && payload.meta) || {},
          };
        });
      })
      .finally(function () {
        if (timer) clearTimeout(timer);
      });
  }

  function coverage(opts) {
    opts = opts || {};
    return apiGet("/api/data/coverage", { date: opts.date || "" }, opts).then(function (r) {
      return r.data;
    });
  }

  function diagnosticsMissing(opts) {
    return apiGet("/api/diagnostics/missing", null, opts || {}).then(function (r) {
      return r.data;
    });
  }

  function fallbackReasons(opts) {
    return apiGet("/api/diagnostics/fallback-reasons", null, opts || {}).then(function (r) {
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
