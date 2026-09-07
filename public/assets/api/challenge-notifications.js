/**
 * ExpectChallengeNotifications — shared global-bell Challenge result authority
 *
 * Real notifications: V6 durable GET /api/v1/notifications (CHALLENGE_RESULT_READY)
 * ui-test fixtures: sessionStorage only (never written to backend)
 *
 * Loaded on all screens that mount the global bell so unread/read state is shared.
 */
(function (global) {
  "use strict";

  var NOTIF_TYPE = "CHALLENGE_RESULT_READY";
  var NOTIF_KEY = "expect_challenge_result_notifications_v1";

  var _realNotifs = [];

  function isUiTestRaceId(raceId) {
    if (
      global.ExpectUiTestRace &&
      typeof ExpectUiTestRace.isUiTestRaceId === "function"
    ) {
      return !!ExpectUiTestRace.isUiTestRaceId(raceId);
    }
    return String(raceId || "").indexOf("ui-test-race-") === 0;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function notifStorage() {
    try {
      return global.sessionStorage;
    } catch (e) {
      return null;
    }
  }

  function readFixtureNotifications() {
    var store = notifStorage();
    if (!store) return [];
    try {
      var list = JSON.parse(store.getItem(NOTIF_KEY) || "[]");
      return Array.isArray(list) ? list : [];
    } catch (e) {
      return [];
    }
  }

  function writeFixtureNotifications(list) {
    var store = notifStorage();
    if (!store) return false;
    try {
      store.setItem(NOTIF_KEY, JSON.stringify(list || []));
      return true;
    } catch (e) {
      return false;
    }
  }

  function refreshBell() {
    if (
      global.ExpectReminders &&
      typeof ExpectReminders.refreshBell === "function"
    ) {
      ExpectReminders.refreshBell();
    }
  }

  function mergedList() {
    var fixture = readFixtureNotifications();
    var real = _realNotifs || [];
    var seen = {};
    var list = [];
    real.forEach(function (n) {
      if (!n || !n.race_id || seen[n.race_id]) return;
      seen[n.race_id] = 1;
      list.push(n);
    });
    fixture.forEach(function (n) {
      if (!n || !n.race_id || seen[n.race_id]) return;
      if (!isUiTestRaceId(n.race_id) && n.ui_test === false) return;
      seen[n.race_id] = 1;
      list.push(n);
    });
    return list;
  }

  function unreadCount() {
    return mergedList().filter(function (n) {
      return !n.read;
    }).length;
  }

  function markFixtureRead(raceId) {
    var id = NOTIF_TYPE + ":" + String(raceId);
    var list = readFixtureNotifications();
    var changed = false;
    list.forEach(function (n) {
      if ((n.id === id || n.race_id === raceId) && !n.read) {
        n.read = true;
        changed = true;
      }
    });
    if (changed) writeFixtureNotifications(list);
    return changed;
  }

  function markRead(raceId) {
    if (!raceId) return false;
    var changed = markFixtureRead(raceId);
    if (isUiTestRaceId(raceId)) {
      refreshBell();
      return changed;
    }
    var real = null;
    for (var i = 0; i < _realNotifs.length; i++) {
      if (_realNotifs[i].race_id === raceId) {
        real = _realNotifs[i];
        break;
      }
    }
    if (
      real &&
      real.notification_id != null &&
      global.ExpectChallengeLifecycle &&
      typeof ExpectChallengeLifecycle.markNotificationRead === "function"
    ) {
      ExpectChallengeLifecycle.markNotificationRead(real.notification_id).then(
        function () {
          real.read = true;
          refreshBell();
        }
      );
    } else if (real) {
      real.read = true;
      changed = true;
      refreshBell();
    }
    return changed;
  }

  function challengeHref(raceId) {
    return (
      "saved.html?race_id=" +
      encodeURIComponent(raceId) +
      "&from=challenge-result"
    );
  }

  function navigateToChallengeResult(raceId) {
    markRead(raceId);
    refreshBell();
    if (
      global.ExpectUiTestChallengeEntry &&
      typeof ExpectUiTestChallengeEntry.navigateToChallengeResult === "function"
    ) {
      // Prefer page host when Challenge scripts are present (scroll / refresh).
      // markRead already applied; host may mark again (idempotent).
      ExpectUiTestChallengeEntry.navigateToChallengeResult(raceId);
      return;
    }
    location.href = challengeHref(raceId);
  }

  function renderListHtml() {
    var list = mergedList();
    if (!list.length) return "";
    return list
      .map(function (n) {
        var venue = n.venue_line || "";
        var rname = n.race_name || "";
        if (
          global.ExpectUiTestChallengeEntry &&
          typeof ExpectUiTestChallengeEntry.findEntry === "function"
        ) {
          var entry = ExpectUiTestChallengeEntry.findEntry(n.race_id);
          if (entry) {
            venue =
              (entry.venue || "") +
                (entry.race_number ? " " + entry.race_number : "") || venue;
            rname = entry.race_name || rname;
          }
        }
        return (
          '<button type="button" class="global-bell-item global-bell-item--challenge' +
          (n.read ? " is-done" : "") +
          '" data-challenge-notif="' +
          escapeHtml(n.race_id) +
          '"' +
          (n.notification_id != null
            ? ' data-challenge-notif-id="' +
              escapeHtml(n.notification_id) +
              '"'
            : "") +
          ">" +
          '<span class="global-bell-type global-bell-type--challenge">Challenge</span>' +
          '<span class="global-bell-main">' +
          '<span class="global-bell-race">' +
          escapeHtml(n.title) +
          "</span>" +
          '<span class="global-bell-meta">' +
          escapeHtml(venue) +
          (rname ? "　" + escapeHtml(rname) : "") +
          "</span>" +
          '<span class="global-bell-remain">' +
          escapeHtml(n.body || "Game Masterとの結果を確認できます") +
          "</span>" +
          "</span></button>"
        );
      })
      .join("");
  }

  function bindList(listEl) {
    if (!listEl || listEl.dataset.ucNotifBound === "1") return;
    listEl.dataset.ucNotifBound = "1";
    listEl.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-challenge-notif]");
      if (!btn || !listEl.contains(btn)) return;
      e.preventDefault();
      var raceId = btn.getAttribute("data-challenge-notif");
      var panel = document.querySelector("[data-bell-panel]");
      var wrap = document.querySelector(".global-bell");
      if (wrap) wrap.classList.remove("is-open");
      if (panel) panel.hidden = true;
      navigateToChallengeResult(raceId);
    });
  }

  function hydrate() {
    if (
      !(
        global.ExpectChallengeLifecycle &&
        ExpectChallengeLifecycle.fetchChallengeNotifications
      )
    ) {
      refreshBell();
      return Promise.resolve([]);
    }
    return ExpectChallengeLifecycle.fetchChallengeNotifications()
      .then(function (list) {
        _realNotifs = list || [];
        refreshBell();
        return _realNotifs;
      })
      .catch(function () {
        return _realNotifs || [];
      });
  }

  function setRealNotifs(list) {
    _realNotifs = list || [];
    refreshBell();
  }

  function getRealNotifs() {
    return _realNotifs || [];
  }

  global.ExpectChallengeNotifications = {
    NOTIF_TYPE: NOTIF_TYPE,
    NOTIF_KEY: NOTIF_KEY,
    list: mergedList,
    unreadCount: unreadCount,
    renderListHtml: renderListHtml,
    bindList: bindList,
    markRead: markRead,
    hydrate: hydrate,
    setRealNotifs: setRealNotifs,
    getRealNotifs: getRealNotifs,
    readFixtureNotifications: readFixtureNotifications,
    writeFixtureNotifications: writeFixtureNotifications,
    refreshBell: refreshBell,
    navigateToChallengeResult: navigateToChallengeResult,
  };
})(window);
