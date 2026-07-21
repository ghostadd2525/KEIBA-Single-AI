/**
 * Version 1.1 — auto maintenance gate
 * Flag OFF = no-op. Flag ON + CLOSED → maintenance.html
 */
(function (global) {
  "use strict";

  var SKIP_RE = /(^|\/)(maintenance|login|setup|ops)\.html$/i;

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
      if (!/maintenance\.html$/i.test(pagePath())) {
        location.replace(dest);
      }
    } catch (e) {
      /* ignore */
    }
  }

  function applyGate(status) {
    if (!status) return;
    global.ExpectPublicStatus = status;
    if (String(status.ops_mode).toUpperCase() === "CLOSED") {
      redirectToMaintenance();
    }
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

  function run() {
    if (shouldSkip()) return Promise.resolve(null);

    return loadAutoFlag().then(function (on) {
      if (!on) return null;
      return fetchStatus()
        .catch(function () {
          return fallbackStatus();
        })
        .then(function (status) {
          applyGate(status);
          return status;
        });
    });
  }

  /**
   * maintenance.html 用: Flag OFF ならホームへ戻す / status を埋める
   */
  function bindMaintenancePage() {
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
          fillMaintenanceDom(status);
          return status;
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
    bindMaintenancePage: bindMaintenancePage,
    fillMaintenanceDom: fillMaintenanceDom,
  };

  // Auto-run gate on normal pages
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
