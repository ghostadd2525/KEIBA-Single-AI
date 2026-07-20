/**
 * ExpectApi.User — User Domain client (Phase U-1)
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

  function request(path, opts) {
    opts = opts || {};
    var headers = { Accept: "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;
    if (opts.headers) {
      Object.keys(opts.headers).forEach(function (k) {
        headers[k] = opts.headers[k];
      });
    }
    var init = { method: opts.method || "GET", headers: headers };
    if (opts.body != null) {
      init.body = JSON.stringify(opts.body);
      headers["Content-Type"] = "application/json; charset=utf-8";
    }
    return fetch(path, init).then(function (res) {
      return res.text().then(function (text) {
        var payload = null;
        try {
          payload = text ? JSON.parse(text) : null;
        } catch (e) {
          payload = null;
        }
        if (!res.ok || (payload && payload.ok === false)) {
          throw new Error(
            (payload && payload.error && payload.error.message) || "User API error"
          );
        }
        return payload && payload.data != null ? payload.data : payload;
      });
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.User = {
    me: function () {
      return request("/api/users/me");
    },
    patchMe: function (body) {
      return request("/api/users/me", { method: "PATCH", body: body || {} });
    },
    favorites: function () {
      return request("/api/v1/favorites");
    },
    addFavorite: function (item) {
      return request("/api/v1/favorites", { method: "POST", body: item || {} });
    },
    history: function () {
      return request("/api/v1/history");
    },
    chat: function (sessionId) {
      var q = sessionId ? "?session_id=" + encodeURIComponent(sessionId) : "";
      return request("/api/v1/chat" + q);
    },
  };
})(window);
