/**
 * Version 1.1 — auto maintenance gate（認証完了後のみ）
 * Flag OFF = no-op. Flag ON + CLOSED + 認証済み非 bypass → maintenance.html
 * 未ログインでは maintenance へ飛ばさない（login は ExpectAuth.requireAuth に任せる）
 */
(function (global) {
  "use strict";

  // Pages pretty URL（/login）と *.html の両方を除外
  var SKIP_RE = /(^|\/)(maintenance|login|setup|ops|terms)(\.html)?\/?$/i;
  var BYPASS_ROLES = { ADMIN: 1, OPS: 1, DEVELOPER: 1 };

  function pagePath() {
    try {
      return String(location.pathname || "");
    } catch (e) {
      return "";
    }
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

  /** ADMIN / OPS / DEVELOPER は UI でも通常利用（API bypass と揃える） */
  function isOpsBypassUser() {
    var token = getAccessToken();
    if (!token) return Promise.resolve(false);

    var headers = { Accept: "application/json", Authorization: "Bearer " + token };
    return fetch("/api/auth/me", { cache: "no-store", headers: headers })
      .then(function (res) {
        if (!res.ok) return false;
        return res.json();
      })
      .then(function (body) {
        var data = body && (body.data || body);
        var user = (data && data.user) || data || {};
        var role = String((user && user.role) || (data && data.role) || "").toUpperCase();
        if (BYPASS_ROLES[role]) return true;
        var uid = String(
          (user && (user.id || user.user_id)) ||
            (data && (data.id || data.user_id)) ||
            getLocalUserId() ||
            ""
        );
        return fetch("/config/beta.json", { cache: "no-store" })
          .then(function (r) {
            return r.ok ? r.json() : null;
          })
          .then(function (beta) {
            var list = (beta && Array.isArray(beta.admin_user_ids) && beta.admin_user_ids) || [];
            return !!uid && list.map(String).indexOf(uid) >= 0;
          })
          .catch(function () {
            return false;
          });
      })
      .catch(function () {
        return false;
      });
  }

  function fallbackStatus() {
    var cal =
      global.ExpectWeekendCalendar && ExpectWeekendCalendar.decide
        ? ExpectWeekendCalendar.decide(new Date())
        : { is_race_day: true, date_jst: null, next_open_date_jst: null, source: "weekend" };
    var closed = !cal.is_race_day;
    return {
      ops_mode: closed ? "CLOSED" : "PUBLIC",
      reason: closed ? "auto_calendar" : "auto_calendar_race_day",
      manual_override: false,
      auto_maintenance_enabled: true,
      is_race_day: !!cal.is_race_day,
      date_jst: cal.date_jst,
      next_open_date_jst: cal.next_open_date_jst,
      calendar_source: cal.source || "weekend",
      message: "ただいま公開時間外です。開催日のみご利用いただけます。",
      _fallback: true,
    };
  }

  function fetchStatus() {
    return fetch("/api/ops/public-status", { cache: "no-store", credentials: "same-origin" })
      .then(function (res) {
        if (!res.ok) throw new Error("status " + res.status);
        return res.json();
      })
      .then(unwrapStatus);
  }

  function redirectToMaintenance() {
    var dest = "maintenance.html";
    try {
      if (!/\/maintenance(\.html)?\/?$/i.test(pagePath())) {
        location.replace(dest);
      }
    } catch (e) {
      /* ignore */
    }
  }

  function applyGate(status) {
    if (!status) return Promise.resolve(status);
    global.ExpectPublicStatus = status;
    if (String(status.ops_mode).toUpperCase() !== "CLOSED") {
      return Promise.resolve(status);
    }
    // 未認証では maintenance へ飛ばさない
    if (!getAccessToken()) {
      return Promise.resolve(status);
    }
    return isOpsBypassUser().then(function (bypass) {
      if (!bypass) redirectToMaintenance();
      return status;
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

  /**
   * 保護ページ用ゲート。認証済みのときのみ CLOSED → maintenance。
   */
  function run() {
    if (shouldSkip()) return Promise.resolve(null);
    if (!getAccessToken()) return Promise.resolve(null);

    return loadAutoFlag().then(function (on) {
      if (!on) return null;
      return fetchStatus()
        .catch(function () {
          return fallbackStatus();
        })
        .then(function (status) {
          return applyGate(status);
        });
    });
  }

  /**
   * ログイン / setup / 規約同意直後の遷移先を決定する。
   * @returns {Promise<"maintenance.html"|"index.html">}
   */
  function resolvePostAuthLanding() {
    if (!getAccessToken()) {
      return Promise.resolve("index.html");
    }
    return loadAutoFlag().then(function (on) {
      if (!on) return "index.html";
      return fetchStatus()
        .catch(function () {
          return fallbackStatus();
        })
        .then(function (status) {
          global.ExpectPublicStatus = status;
          if (!status || String(status.ops_mode).toUpperCase() !== "CLOSED") {
            return "index.html";
          }
          return isOpsBypassUser().then(function (bypass) {
            return bypass ? "index.html" : "maintenance.html";
          });
        });
    });
  }

  function goPostAuthLanding() {
    return resolvePostAuthLanding().then(function (dest) {
      try {
        location.replace(dest);
      } catch (e) {
        location.href = dest;
      }
      return dest;
    });
  }

  /**
   * maintenance.html 用: 未ログインは login。Flag OFF / PUBLIC / ADMIN はホームへ。
   */
  function bindMaintenancePage() {
    if (!isAuthenticated() || !getAccessToken()) {
      location.replace("login.html");
      return Promise.resolve(null);
    }

    return loadAutoFlag().then(function (on) {
      if (!on) {
        location.replace("index.html");
        return null;
      }
      return fetchStatus()
        .catch(function () {
          return fallbackStatus();
        })
        .then(function (status) {
          global.ExpectPublicStatus = status;
          if (status && String(status.ops_mode).toUpperCase() === "PUBLIC") {
            location.replace("index.html");
            return status;
          }
          return isOpsBypassUser().then(function (bypass) {
            if (bypass) {
              location.replace("index.html");
              return status;
            }
            fillMaintenanceDom(status);
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
      var w = new Intl.DateTimeFormat("ja-JP", { timeZone: "Asia/Tokyo", weekday: "short" }).format(dt);
      return w;
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
      var d = status.next_open_date_jst;
      var w = weekdayJa(d);
      nextEl.textContent = d
        ? d + (w ? "（" + w + "）" : "") + " 公開予定"
        : "次回開催日に公開予定";
    }
    if (chatNote) {
      var closed = String(status.ops_mode).toUpperCase() === "CLOSED";
      chatNote.hidden = !closed;
    }
  }

  global.ExpectAutoMaintenance = {
    run: run,
    resolvePostAuthLanding: resolvePostAuthLanding,
    goPostAuthLanding: goPostAuthLanding,
    bindMaintenancePage: bindMaintenancePage,
    fillMaintenanceDom: fillMaintenanceDom,
    isOpsBypassUser: isOpsBypassUser,
  };

  // 自動実行は残すが、無トークン時は no-op（login への競合を消す）
  if (!shouldSkip()) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        run();
      });
    } else {
      run();
    }
  }
})(window);
