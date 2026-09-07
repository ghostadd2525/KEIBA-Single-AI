/**
 * Production UI — race data readiness banners (board / odds / detail).
 * Consumes GET /api/races/:id/data-status (Ops integrity mapped server-side).
 */
(function (global) {
  "use strict";

  var POLL_MS = 60 * 1000;
  var _timers = {};
  var _last = {};

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function authHeaders() {
    var h = { Accept: "application/json" };
    try {
      var t =
        (global.ExpectAuth && ExpectAuth.getAccessToken && ExpectAuth.getAccessToken()) ||
        localStorage.getItem("expect_access_token_v1") ||
        "";
      if (t) h.Authorization = "Bearer " + t;
    } catch (e) {
      /* ignore */
    }
    return h;
  }

  function ensureBanner(host, id) {
    if (!host) return null;
    var el = host.querySelector("[data-race-data-status='" + id + "']");
    if (el) return el;
    el = document.createElement("div");
    el.className = "race-data-status";
    el.setAttribute("data-race-data-status", id);
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    el.hidden = true;
    if (host.firstChild) host.insertBefore(el, host.firstChild);
    else host.appendChild(el);
    return el;
  }

  function renderBanner(el, surface) {
    if (!el) return;
    if (!surface || !surface.visible || surface.state === "ready" || !surface.message) {
      el.hidden = true;
      el.innerHTML = "";
      el.className = "race-data-status";
      return;
    }
    var tone =
      surface.state === "error"
        ? "is-error"
        : surface.state === "loading"
          ? "is-loading"
          : "is-pending";
    el.className = "race-data-status " + tone;
    el.hidden = false;
    el.innerHTML =
      '<p class="race-data-status__msg">' + escapeHtml(surface.message) + "</p>";
  }

  function applyToMounts(raceId, data) {
    var surfaces = (data && data.surfaces) || {};
    var map = [
      { key: "detail", sel: "[data-data-status-mount='detail']" },
      { key: "board", sel: "[data-data-status-mount='board']" },
      { key: "odds", sel: "[data-data-status-mount='odds']" },
    ];
    map.forEach(function (m) {
      var hosts = document.querySelectorAll(m.sel);
      for (var i = 0; i < hosts.length; i++) {
        var banner = ensureBanner(hosts[i], m.key);
        renderBanner(banner, surfaces[m.key]);
      }
    });
  }

  function fetchStatus(raceId) {
    var url =
      "/api/races/" + encodeURIComponent(raceId) + "/data-status?_=" + Date.now();
    return fetch(url, { credentials: "include", cache: "no-store", headers: authHeaders() }).then(
      function (res) {
        return res.json().then(function (body) {
          if (!res.ok) {
            return {
              race_id: raceId,
              state: "error",
              visible: true,
              message: "データの取得に失敗しました。しばらくしてから再度お試しください。",
              surfaces: {
                detail: {
                  visible: true,
                  state: "error",
                  message: "データの取得に失敗しました。しばらくしてから再度お試しください。",
                },
                board: {
                  visible: true,
                  state: "error",
                  message: "データの取得に失敗しました。しばらくしてから再度お試しください。",
                },
                odds: {
                  visible: true,
                  state: "error",
                  message: "データの取得に失敗しました。しばらくしてから再度お試しください。",
                },
              },
            };
          }
          return (body && body.data) || body;
        });
      }
    );
  }

  function stopPolling(raceId) {
    var t = _timers[raceId];
    if (t) {
      clearInterval(t);
      delete _timers[raceId];
    }
  }

  function startPolling(raceId) {
    stopPolling(raceId);
    _timers[raceId] = setInterval(function () {
      refresh(raceId);
    }, POLL_MS);
  }

  function refresh(raceId) {
    if (!raceId) return Promise.resolve(null);
    return fetchStatus(raceId)
      .then(function (data) {
        _last[raceId] = data;
        applyToMounts(raceId, data);
        if (data && data.state === "ready") stopPolling(raceId);
        else startPolling(raceId);
        return data;
      })
      .catch(function () {
        var err = {
          race_id: raceId,
          state: "error",
          visible: true,
          surfaces: {
            detail: {
              visible: true,
              state: "error",
              message: "データの取得に失敗しました。しばらくしてから再度お試しください。",
            },
            board: {
              visible: true,
              state: "error",
              message: "データの取得に失敗しました。しばらくしてから再度お試しください。",
            },
            odds: {
              visible: true,
              state: "error",
              message: "データの取得に失敗しました。しばらくしてから再度お試しください。",
            },
          },
        };
        applyToMounts(raceId, err);
        startPolling(raceId);
        return err;
      });
  }

  function bind(raceId, opts) {
    opts = opts || {};
    // Show loading immediately on mounts
    applyToMounts(raceId, {
      state: "loading",
      surfaces: {
        detail: {
          visible: true,
          state: "loading",
          message: "レースデータを確認しています…",
        },
        board: {
          visible: true,
          state: "loading",
          message: "レースデータを確認しています…",
        },
        odds: {
          visible: true,
          state: "loading",
          message: "レースデータを確認しています…",
        },
      },
    });
    return refresh(raceId);
  }

  function getLast(raceId) {
    return _last[raceId] || null;
  }

  function remember(raceId, data) {
    if (!raceId || !data) return;
    _last[raceId] = data;
  }

  function isReady(raceId) {
    var last = getLast(raceId);
    return !!(last && last.state === "ready");
  }

  global.ExpectDataStatus = {
    bind: bind,
    refresh: refresh,
    stopPolling: stopPolling,
    getLast: getLast,
    remember: remember,
    isReady: isReady,
  };
})(typeof window !== "undefined" ? window : globalThis);
