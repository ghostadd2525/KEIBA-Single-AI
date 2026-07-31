/**
 * auto-maintenance.js v12.4 — Version7 Maintenance Mode gate
 *
 * 初期化順序（必須）:
 *   requireAuth → isOpsBypassUser() → ADMIN 判定 → status 取得 → USER のみ Maintenance 判定
 *
 * Server 正本: GET /api/system/status（fallback: /api/ops/public-status）
 * Schedule: 日曜 21:00 JST 〜 土曜 00:00 JST → maintenance
 *
 * - メンテ中 + USER 認証済み → forceClearAuthState → /login.html
 * - メンテ中 + ADMIN/OPS/DEVELOPER → JWT 維持・forceClear 禁止・メンテ処理スキップ
 * - メンテ中 + 未認証 + 保護ページ → maintenance.html
 * - /login / maintenance / setup / terms / ops は認証・メンテ強制の対象外（リダイレクトループ禁止）
 * - /api/system/status が HTML（SPA fallback）のときは JSON とみなさない
 *
 * PE / CE / AI 非接触。
 */
(function (global) {
  "use strict";

  var SKIP_RE = /(^|\/)(maintenance|login|setup|ops|terms)(\.html)?\/?$/i;
  var BYPASS_ROLES = { ADMIN: 1, OPS: 1, DEVELOPER: 1 };
  var POLL_MS = 60 * 1000;
  /** pretty URL 優先。login.html 指定は CF 308 を1回挟むため /login を使う */
  var LOGIN_HREF = "/login";
  var MAINT_HREF = "/maintenance";
  var _pollTimer = null;
  var _lastMaintenance = null;
  var _forceLogoutInFlight = false;
  var _bypassCache = null; // null | Promise<boolean>

  function parseStubToken(token) {
    if (!token || token.indexOf("stub.") !== 0) return null;
    try {
      var parts = token.split(".");
      if (parts.length < 3) return null;
      var b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      var json = decodeURIComponent(escape(atob(b64)));
      return JSON.parse(json);
    } catch (e) {
      return null;
    }
  }

  function roleFromAccessToken() {
    var payload = parseStubToken(getAccessToken());
    if (!payload) return "";
    return String(payload.role || "").toUpperCase();
  }

  function pagePath() {
    try {
      return String(location.pathname || "");
    } catch (e) {
      return "";
    }
  }

  function isLoginPage() {
    return /(^|\/)login(\.html)?\/?$/i.test(pagePath());
  }

  function isMaintenancePage() {
    return /(^|\/)maintenance(\.html)?\/?$/i.test(pagePath());
  }

  function shouldSkip() {
    if (global.__EXPECT_SKIP_AUTO_MAINTENANCE) return true;
    var path = pagePath();
    if (SKIP_RE.test(path)) return true;
    var root = document.documentElement;
    if (root && root.getAttribute("data-skip-auto-maintenance") != null) return true;
    return false;
  }

  function unwrapStatus(json) {
    if (!json) return null;
    if (json.data && typeof json.data === "object") return json.data;
    return json;
  }

  function getAccessToken() {
    try {
      if (global.ExpectAuth && typeof ExpectAuth.getAccessToken === "function") {
        return ExpectAuth.getAccessToken() || "";
      }
      return localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function isAuthenticated() {
    if (global.ExpectAuth && typeof ExpectAuth.isLoggedIn === "function") {
      return !!ExpectAuth.isLoggedIn();
    }
    return !!getAccessToken();
  }

  function getLocalUserId() {
    try {
      var raw = localStorage.getItem("expect_auth_v1");
      var auth = raw ? JSON.parse(raw) : null;
      return (auth && auth.id) || "";
    } catch (e) {
      return "";
    }
  }

  /**
   * ADMIN / OPS / DEVELOPER / admin_user_ids → true
   * キャッシュし、メンテ処理より先に解決する。
   */
  function isOpsBypassUser() {
    if (_bypassCache) return _bypassCache;

    var tokenRole = roleFromAccessToken();
    if (BYPASS_ROLES[tokenRole]) {
      _bypassCache = Promise.resolve(true);
      return _bypassCache;
    }

    var uid = getLocalUserId();
    _bypassCache = fetch("/config/beta.json", { cache: "no-store" })
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .then(function (beta) {
        var list = (beta && Array.isArray(beta.admin_user_ids) && beta.admin_user_ids) || [];
        if (uid && list.map(String).indexOf(String(uid)) >= 0) return true;

        var token = getAccessToken();
        if (!token) return false;
        var headers = { Accept: "application/json", Authorization: "Bearer " + token };
        return fetch("/api/auth/me", { cache: "no-store", headers: headers })
          .then(function (res) {
            var ct = (res.headers.get("content-type") || "").toLowerCase();
            if (!res.ok || ct.indexOf("application/json") < 0) return false;
            return res.json();
          })
          .then(function (body) {
            if (!body) return false;
            var data = body && (body.data || body);
            var user = (data && data.user) || data || {};
            var role = String((user && user.role) || (data && data.role) || "").toUpperCase();
            if (BYPASS_ROLES[role]) return true;
            var meId = String(
              (user && (user.id || user.user_id)) ||
                (data && (data.id || data.user_id)) ||
                ""
            );
            return !!meId && list.map(String).indexOf(meId) >= 0;
          })
          .catch(function () {
            return false;
          });
      })
      .catch(function () {
        return false;
      });

    return _bypassCache;
  }

  function normalizeStatus(raw) {
    if (!raw || typeof raw !== "object") return null;
    var maintenance =
      raw.maintenance === true ||
      String(raw.ops_mode || "").toUpperCase() === "CLOSED";
    return {
      maintenance: maintenance,
      ops_mode: maintenance ? "CLOSED" : "PUBLIC",
      maintenance_start: raw.maintenance_start || null,
      maintenance_end: raw.maintenance_end || null,
      reason: raw.reason || (maintenance ? "Research Week" : "Production Open"),
      resolve_reason: raw.resolve_reason || raw.reason || null,
      message:
        raw.message ||
        "ただいまメンテナンス中です（Research Week）。土曜 0:00（JST）以降に再度ログインしてください。",
      next_open_date_jst:
        raw.next_open_date_jst ||
        (raw.maintenance_end ? String(raw.maintenance_end).slice(0, 10) : null),
      auto_maintenance_enabled: raw.auto_maintenance_enabled !== false,
    };
  }

  /** HTML SPA fallback を JSON と誤認しない */
  function parseJsonResponse(res, label) {
    var ct = (res.headers.get("content-type") || "").toLowerCase();
    if (!res.ok) throw new Error(label + " " + res.status);
    if (ct.indexOf("application/json") < 0) {
      throw new Error(label + " non-json content-type=" + ct);
    }
    return res.json();
  }

  function fetchSystemStatus() {
    return fetch("/api/system/status", { cache: "no-store", credentials: "same-origin" })
      .then(function (res) {
        return parseJsonResponse(res, "system-status");
      })
      .then(unwrapStatus)
      .then(normalizeStatus);
  }

  function fetchPublicStatus() {
    return fetch("/api/ops/public-status", { cache: "no-store", credentials: "same-origin" })
      .then(function (res) {
        return parseJsonResponse(res, "public-status");
      })
      .then(unwrapStatus)
      .then(normalizeStatus);
  }

  function fetchStatus() {
    return fetchSystemStatus().catch(function () {
      return fetchPublicStatus();
    });
  }

  function loadAutoFlag() {
    if (global.ExpectUiFeatures && ExpectUiFeatures.load) {
      return ExpectUiFeatures.load().then(function (f) {
        return !!(f && f.v11_auto_maintenance);
      });
    }
    return fetch("/config/beta.json", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("beta " + res.status);
        return res.json();
      })
      .then(function (doc) {
        return !!(doc && doc.ui_features && doc.ui_features.v11_auto_maintenance);
      })
      .catch(function () {
        return false;
      });
  }

  function redirectTo(href) {
    try {
      location.replace(href);
    } catch (e) {
      location.href = href;
    }
  }

  /** 同期の最終ガード — ADMIN 系ロールでは forceClear を絶対に実行しない */
  function isSyncBypassRole() {
    if (global.__EXPECT_MAINT_BYPASS) return true;
    var role = roleFromAccessToken();
    return !!BYPASS_ROLES[role];
  }

  /**
   * USER 専用。ADMIN bypass 時は絶対に呼ばない（forceClearAuthState 禁止）。
   */
  function forceLogoutToLogin() {
    if (isSyncBypassRole()) return Promise.resolve();
    if (_forceLogoutInFlight) return Promise.resolve();
    _forceLogoutInFlight = true;
    var clear = function () {
      if (isSyncBypassRole()) return;
      if (global.ExpectAuth && typeof ExpectAuth.forceClearAuthState === "function") {
        ExpectAuth.forceClearAuthState({ keepTerms: true });
      } else {
        try {
          localStorage.removeItem("expect_access_token_v1");
          localStorage.removeItem("expect_auth_v1");
          localStorage.removeItem("expect_account_ready_v1");
          sessionStorage.clear();
        } catch (e) { /* ignore */ }
      }
    };

    var p = Promise.resolve();
    if (global.ExpectAuth && typeof ExpectAuth.logout === "function" && getAccessToken()) {
      if (isSyncBypassRole()) {
        _forceLogoutInFlight = false;
        return Promise.resolve();
      }
      p = ExpectAuth.logout().catch(function () { /* ignore */ });
    }
    return p.then(function () {
      clear();
      // 既に login にいる場合は再遷移しない（ループ防止）
      if (!isLoginPage()) redirectTo(LOGIN_HREF);
      _forceLogoutInFlight = false;
    });
  }

  function applyGate(status) {
    if (!status) return Promise.resolve(status);
    global.ExpectPublicStatus = status;
    global.ExpectSystemStatus = status;

    var was = _lastMaintenance;
    _lastMaintenance = status.maintenance;

    if (!status.maintenance) {
      if (isMaintenancePage()) {
        redirectTo("index.html");
      }
      return Promise.resolve(status);
    }

    // maintenance === true — ADMIN 判定を先に完了してから USER 処理
    return isOpsBypassUser().then(function (bypass) {
      if (bypass) {
        global.__EXPECT_MAINT_BYPASS = true;
        // ADMIN: メンテ処理を完全スキップ（ログアウト・redirect なし）
        return status;
      }
      global.__EXPECT_MAINT_BYPASS = false;

      if (getAccessToken() || isAuthenticated()) {
        return forceLogoutToLogin().then(function () {
          return status;
        });
      }

      if (!isLoginPage() && !isMaintenancePage() && !shouldSkip()) {
        redirectTo(MAINT_HREF);
      } else if (isLoginPage() && was === false && status.maintenance === true) {
        /* stay on login */
      }
      return status;
    });
  }

  function runOnce() {
    return loadAutoFlag().then(function (on) {
      if (!on) return null;

      // USER ゲート: status 取得 → Maintenance 判定 → 必要なら forceClear → /login
      var userGate = function () {
        return fetchStatus()
          .catch(function () {
            return null;
          })
          .then(function (status) {
            if (!status) return null;
            return applyGate(status);
          });
      };

      // requireAuth 後: 認証済みなら isOpsBypassUser → ADMIN 判定を status より先に完了
      if (getAccessToken() || isAuthenticated()) {
        return isOpsBypassUser().then(function (bypass) {
          if (bypass) {
            global.__EXPECT_MAINT_BYPASS = true;
            // ADMIN: status は観測用に取得するが、forceClear / logout / redirect はしない
            return fetchStatus()
              .catch(function () {
                return null;
              })
              .then(function (status) {
                global.ExpectPublicStatus = status;
                global.ExpectSystemStatus = status;
                return status;
              });
          }
          return userGate();
        });
      }
      return userGate();
    });
  }

  function run() {
    if (shouldSkip() && !isLoginPage()) {
      if (!isLoginPage() && !isMaintenancePage()) return Promise.resolve(null);
    }
    return runOnce().then(function (status) {
      startPolling();
      return status;
    });
  }

  function startPolling() {
    if (_pollTimer) return;
    _pollTimer = setInterval(function () {
      runOnce().catch(function () { /* ignore */ });
    }, POLL_MS);

    try {
      if (global.ExpectRealtimeSync && typeof ExpectRealtimeSync.on === "function") {
        ExpectRealtimeSync.on("tick", function () {
          runOnce().catch(function () { /* ignore */ });
        });
      }
    } catch (e) { /* ignore */ }
  }

  function stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer);
      _pollTimer = null;
    }
  }

  function resolvePostAuthLanding() {
    if (!getAccessToken()) {
      return Promise.resolve("index.html");
    }
    _bypassCache = null; // ログイン直後は再判定
    return loadAutoFlag().then(function (on) {
      if (!on) return "index.html";
      return isOpsBypassUser().then(function (bypass) {
        if (bypass) {
          global.__EXPECT_MAINT_BYPASS = true;
          return "index.html";
        }
        return fetchStatus()
          .catch(function () {
            return null;
          })
          .then(function (status) {
            if (!status || !status.maintenance) return "index.html";
            return MAINT_HREF;
          });
      });
    });
  }

  function goPostAuthLanding() {
    return resolvePostAuthLanding().then(function (dest) {
      redirectTo(dest);
      return dest;
    });
  }

  function bindMaintenancePage() {
    return loadAutoFlag().then(function (on) {
      if (!on) {
        redirectTo("index.html");
        return null;
      }
      return isOpsBypassUser().then(function (bypass) {
        if (bypass) {
          global.__EXPECT_MAINT_BYPASS = true;
          redirectTo("index.html");
          return null;
        }
        return fetchStatus()
          .catch(function () {
            return null;
          })
          .then(function (status) {
            global.ExpectPublicStatus = status;
            if (!status || !status.maintenance) {
              redirectTo("index.html");
              return status;
            }
            if ((getAccessToken() || isAuthenticated()) && !isSyncBypassRole()) {
              if (global.ExpectAuth && typeof ExpectAuth.forceClearAuthState === "function") {
                ExpectAuth.forceClearAuthState({ keepTerms: true });
              }
            }
            fillMaintenanceDom(status);
            startPolling();
            return status;
          });
      });
    });
  }

  function weekdayJa(dateJst) {
    if (!dateJst) return "";
    try {
      var p = String(dateJst).split("-");
      var dt = new Date(Date.UTC(Number(p[0]), Number(p[1]) - 1, Number(p[2]), 3, 0, 0));
      return new Intl.DateTimeFormat("ja-JP", {
        timeZone: "Asia/Tokyo",
        weekday: "short",
      }).format(dt);
    } catch (e) {
      return "";
    }
  }

  function fillMaintenanceDom(status) {
    if (!status) return;
    var nextEl = document.getElementById("maintNextOpen");
    var msgEl = document.getElementById("maintMessage");
    var chatNote = document.getElementById("maintChatNote");
    if (msgEl && status.message) msgEl.textContent = status.message;
    if (nextEl) {
      var end = status.maintenance_end || status.next_open_date_jst;
      var d = end ? String(end).slice(0, 10) : null;
      var w = weekdayJa(d);
      nextEl.textContent = d
        ? d + (w ? "（" + w + "）" : "") + " 0:00（JST）公開予定"
        : "土曜 0:00（JST）以降に公開予定";
    }
    if (chatNote) {
      chatNote.hidden = !(status && status.maintenance);
    }
  }

  function bindLoginPage() {
    return runOnce().then(function (status) {
      startPolling();
      var banner = document.getElementById("maintLoginBanner");
      if (banner && status && status.maintenance && !global.__EXPECT_MAINT_BYPASS) {
        banner.hidden = false;
        banner.textContent =
          status.message ||
          "ただいま Research Week メンテナンス中です。土曜 0:00（JST）以降にログインできます。";
      } else if (banner) {
        banner.hidden = true;
      }
      return status;
    });
  }

  global.ExpectAutoMaintenance = {
    run: run,
    runOnce: runOnce,
    startPolling: startPolling,
    stopPolling: stopPolling,
    forceLogoutToLogin: forceLogoutToLogin,
    resolvePostAuthLanding: resolvePostAuthLanding,
    goPostAuthLanding: goPostAuthLanding,
    bindMaintenancePage: bindMaintenancePage,
    bindLoginPage: bindLoginPage,
    fillMaintenanceDom: fillMaintenanceDom,
    isOpsBypassUser: isOpsBypassUser,
    POLL_MS: POLL_MS,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      if (isLoginPage()) {
        bindLoginPage();
      } else if (isMaintenancePage()) {
        /* bindMaintenancePage from page */
      } else if (!shouldSkip()) {
        run();
      }
    });
  } else {
    if (isLoginPage()) bindLoginPage();
    else if (!shouldSkip() && !isMaintenancePage()) run();
  }
})(window);
