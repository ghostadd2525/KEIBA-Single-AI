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

    var timeoutMs =
      typeof opts.timeoutMs === "number" && opts.timeoutMs > 0 ? opts.timeoutMs : 0;
    var controller = null;
    var timer = null;
    if (timeoutMs > 0 && typeof AbortController !== "undefined") {
      controller = new AbortController();
      init.signal = controller.signal;
      timer = setTimeout(function () {
        try {
          controller.abort();
        } catch (e) { /* ignore */ }
      }, timeoutMs);
    }

    return fetch(path, init)
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
              (payload && payload.error && payload.error.message) || "User API error"
            );
          }
          return payload && payload.data != null ? payload.data : payload;
        });
      })
      .catch(function (err) {
        if (err && err.name === "AbortError") {
          throw new Error("応答がタイムアウトしました。再試行してください。");
        }
        throw err;
      })
      .finally(function () {
        if (timer) clearTimeout(timer);
      });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.User = {
    me: function () {
      return request("/api/users/me", { timeoutMs: 8000 });
    },
    patchMe: function (body) {
      return request("/api/users/me", { method: "PATCH", body: body || {}, timeoutMs: 10000 });
    },
    issueInvite: function (body) {
      // 発行自体は通常1秒前後。接続詰まり対策で15秒打ち切り
      return request("/api/admin/invitations", {
        method: "POST",
        body: body || {},
        timeoutMs: 15000,
      });
    },
    listInvites: function () {
      return request("/api/admin/invitations", { timeoutMs: 10000 });
    },
    favorites: function () {
      return request("/api/v1/favorites", { timeoutMs: 8000 });
    },
    addFavorite: function (item) {
      return request("/api/v1/favorites", {
        method: "POST",
        body: item || {},
        timeoutMs: 8000,
      });
    },
    history: function () {
      return request("/api/v1/history", { timeoutMs: 8000 });
    },
    monthlyRaceResults: function (month) {
      var q = month ? "?month=" + encodeURIComponent(month) : "";
      return request("/api/v1/user-race-results" + q, { timeoutMs: 12000 });
    },
    purchaseHistory: function () {
      return request("/api/v1/user-race-results?view=history", { timeoutMs: 15000 });
    },
    getRaceResult: function (raceId) {
      return request(
        "/api/v1/user-race-results/" + encodeURIComponent(raceId),
        { timeoutMs: 10000 }
      );
    },
    saveRaceResult: function (body) {
      return request("/api/v1/user-race-results", {
        method: "POST",
        body: body || {},
        timeoutMs: 10000,
      });
    },
    settleRaceResult: function (raceId, body) {
      return request(
        "/api/v1/user-race-results/" + encodeURIComponent(raceId) + "/settle",
        {
          method: "POST",
          body: body || {},
          timeoutMs: 15000,
        }
      );
    },
    settlePendingRaceResults: function () {
      return request("/api/v1/user-race-results/settle-pending", {
        method: "POST",
        body: {},
        timeoutMs: 20000,
      });
    },
    registerPurchase: function (body) {
      var payload = Object.assign({ action: "purchase" }, body || {});
      return request("/api/v1/user-race-results", {
        method: "POST",
        body: payload,
        timeoutMs: 12000,
      });
    },
    progress: function () {
      return request("/api/v1/user/progress", { timeoutMs: 8000 });
    },
    challengeMonthly: function (month) {
      var q = month ? "?month=" + encodeURIComponent(month) : "";
      return request("/api/v1/challenge/monthly" + q, { timeoutMs: 25000 });
    },
    challengeActive: function () {
      return request("/api/v1/challenge/active", { timeoutMs: 15000 });
    },
    challengeLifecycleViewed: function (raceId, body) {
      return request(
        "/api/v1/challenge/lifecycle/" + encodeURIComponent(raceId) + "/viewed",
        {
          method: "POST",
          body: body || { reveal_completed: true },
          timeoutMs: 15000,
        }
      );
    },
    notifications: function (limit) {
      var q =
        limit != null ? "?limit=" + encodeURIComponent(String(limit)) : "";
      return request("/api/v1/notifications" + q, { timeoutMs: 12000 });
    },
    notificationMarkRead: function (id) {
      return request(
        "/api/v1/notifications/" + encodeURIComponent(id) + "/read",
        { method: "POST", body: {}, timeoutMs: 10000 }
      );
    },
    chat: function (sessionId) {
      var q = sessionId ? "?session_id=" + encodeURIComponent(sessionId) : "";
      return request("/api/v1/chat" + q, { timeoutMs: 8000 });
    },
  };
})(window);
