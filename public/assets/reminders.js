/**
 * お気に入りレースのリマインダー
 * - 発走15分前: チケット購入
 * - 発走5分前: レース開始
 *
 * 発走時刻は Prediction API / bundle キャッシュから取得（POST_FALLBACK 廃止）
 */
(function (global) {
  "use strict";

  var FAV_KEY = "expect_favorites_v1";
  var FIRED_KEY = "expect_reminders_fired_v1";
  var TICKET_OFFSET_MIN = 15;
  var START_OFFSET_MIN = 5;
  var POLL_MS = 20000;

  var pollTimer = null;
  var bound = false;
  var _metaHydrating = false;
  var _metaHydrated = false;

  function storage() {
    try {
      return global.localStorage;
    } catch (e) {
      return null;
    }
  }

  function readFavorites() {
    if (global.ExpectFavorites && typeof ExpectFavorites.list === "function") {
      return ExpectFavorites.list();
    }
    var store = storage();
    if (!store) return [];
    try {
      var list = JSON.parse(store.getItem(FAV_KEY) || "[]");
      if (!Array.isArray(list)) return [];
      return list.map(function (item) {
        return {
          id: item.id,
          date: item.date || "",
          postTime: item.postTime || "",
          place: item.place || "レース",
          name: item.name || "",
        };
      });
    } catch (e) {
      return [];
    }
  }

  function ensureRaceMeta() {
    if (_metaHydrated || _metaHydrating) return Promise.resolve();
    if (!global.ExpectApi || !ExpectApi.Prediction || !global.ExpectFavorites) {
      return Promise.resolve();
    }
    var favs = readFavorites().filter(function (f) {
      return f.id && (!f.date || !f.postTime);
    });
    if (!favs.length) {
      _metaHydrated = true;
      return Promise.resolve();
    }
    _metaHydrating = true;
    return Promise.all(
      favs.map(function (f) {
        return ExpectApi.Prediction.get(f.id)
          .then(function (b) {
            if (b && ExpectFavorites.cacheBundle) ExpectFavorites.cacheBundle(b);
          })
          .catch(function () {});
      })
    ).finally(function () {
      _metaHydrating = false;
      _metaHydrated = true;
    });
  }

  function readFired() {
    var store = storage();
    if (!store) return {};
    try {
      var obj = JSON.parse(store.getItem(FIRED_KEY) || "{}");
      return obj && typeof obj === "object" ? obj : {};
    } catch (e) {
      return {};
    }
  }

  function writeFired(map) {
    var store = storage();
    if (!store) return;
    try {
      store.setItem(FIRED_KEY, JSON.stringify(map));
    } catch (e) {}
  }

  function parsePostDate(fav) {
    var date = fav.date;
    var time = fav.postTime;
    if ((!date || !time) && global.ExpectFavorites && ExpectFavorites.getMeta) {
      var meta = ExpectFavorites.getMeta(fav.id);
      date = date || meta.date || "";
      time = time || meta.postTime || "";
    }
    if (!date || !time) return null;
    var parts = String(time).split(":");
    var h = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return null;
    var d = new Date(date + "T00:00:00");
    if (isNaN(d.getTime())) return null;
    d.setHours(h, m, 0, 0);
    return d;
  }

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function formatClock(date) {
    return pad(date.getHours()) + ":" + pad(date.getMinutes());
  }

  function formatRemain(ms) {
    if (ms <= 0) return "まもなく";
    var min = Math.floor(ms / 60000);
    if (min < 60) return "あと" + min + "分";
    var h = Math.floor(min / 60);
    var r = min % 60;
    return "あと" + h + "時間" + (r ? r + "分" : "");
  }

  function buildEvents(now) {
    now = now || new Date();
    var events = [];
    readFavorites().forEach(function (fav) {
      var post = parsePostDate(fav);
      if (!post) return;
      var place = fav.place || "レース";
      var name = fav.name || "";
      var label = place + (name ? "　" + name : "");

      events.push({
        key: fav.id + ":ticket",
        type: "ticket",
        typeLabel: "チケット購入",
        raceId: fav.id,
        label: label,
        postAt: post,
        at: new Date(post.getTime() - TICKET_OFFSET_MIN * 60000),
        href: "race.html?race_id=" + encodeURIComponent(fav.id),
        note: "発走" + TICKET_OFFSET_MIN + "分前",
      });
      events.push({
        key: fav.id + ":start",
        type: "start",
        typeLabel: "レース開始",
        raceId: fav.id,
        label: label,
        postAt: post,
        at: new Date(post.getTime() - START_OFFSET_MIN * 60000),
        href: "race.html?race_id=" + encodeURIComponent(fav.id),
        note: "発走" + START_OFFSET_MIN + "分前",
      });
    });
    events.sort(function (a, b) {
      return a.at - b.at;
    });
    return events;
  }

  function upcomingEvents(now) {
    now = now || new Date();
    return buildEvents(now).filter(function (ev) {
      return ev.postAt.getTime() + 5 * 60000 >= now.getTime();
    });
  }

  function dueEvents(now) {
    now = now || new Date();
    var fired = readFired();
    return buildEvents(now).filter(function (ev) {
      if (fired[ev.key]) return false;
      var t = ev.at.getTime();
      return t <= now.getTime() && now.getTime() - t < 2 * 60000;
    });
  }

  function ensureToastHost() {
    var host = document.getElementById("reminderToastHost");
    if (host) return host;
    host = document.createElement("div");
    host.id = "reminderToastHost";
    host.className = "reminder-toast-host";
    document.body.appendChild(host);
    return host;
  }

  function showToast(ev) {
    var host = ensureToastHost();
    var el = document.createElement("div");
    el.className = "reminder-toast reminder-toast--" + ev.type;
    el.innerHTML =
      '<p class="reminder-toast-kicker">' +
      ev.typeLabel +
      "リマインダー</p>" +
      '<p class="reminder-toast-title">' +
      ev.label +
      "</p>" +
      '<p class="reminder-toast-note">' +
      ev.note +
      "（発走 " +
      formatClock(ev.postAt) +
      "）</p>";
    host.appendChild(el);
    setTimeout(function () {
      el.classList.add("is-out");
      setTimeout(function () {
        el.remove();
      }, 320);
    }, 5200);
  }

  function notifySystem(ev) {
    if (!("Notification" in global)) return;
    if (Notification.permission !== "granted") return;
    try {
      new Notification(ev.typeLabel + "リマインダー", {
        body: ev.label + "（" + ev.note + " / 発走 " + formatClock(ev.postAt) + "）",
        tag: ev.key,
      });
    } catch (e) {}
  }

  function mascotLine(ev) {
    var race = ev.label;
    var post = formatClock(ev.postAt);
    if (ev.type === "ticket") {
      return (
        "リマインダーだよ！<br><strong>" +
        race +
        "</strong><br>発走まであと15分。<br>チケット購入、忘れずにね！"
      );
    }
    return (
      "まもなく発走！<br><strong>" +
      race +
      "</strong><br>発走 " +
      post +
      "（あと5分）<br>一緒に勝ちにいこう！"
    );
  }

  function speakMascotReminder(ev) {
    if (global.ExpectShell && typeof ExpectShell.speakMascot === "function") {
      ExpectShell.speakMascot(mascotLine(ev), 6200);
    }
  }

  function fireDue() {
    var now = new Date();
    var due = dueEvents(now);
    if (!due.length) {
      updateBadge();
      return;
    }
    var fired = readFired();
    due.forEach(function (ev) {
      fired[ev.key] = Date.now();
      showToast(ev);
      notifySystem(ev);
      speakMascotReminder(ev);
    });
    writeFired(fired);
    updateBadge();
    renderPanel();
  }

  function updateBadge() {
    var badge = document.querySelector("[data-bell-badge]");
    if (!badge) return;
    var now = new Date();
    var soon = upcomingEvents(now).filter(function (ev) {
      var ms = ev.at.getTime() - now.getTime();
      return ms >= 0 && ms <= 60 * 60000;
    }).length;
    if (soon > 0) {
      badge.hidden = false;
      badge.textContent = String(soon > 9 ? "9+" : soon);
    } else {
      badge.hidden = true;
      badge.textContent = "";
    }
  }

  function renderPanel() {
    var list = document.querySelector("[data-bell-list]");
    if (!list) return;
    var now = new Date();
    var favs = readFavorites();
    if (!favs.length) {
      list.innerHTML =
        '<p class="global-bell-empty">お気に入りレースを登録すると、<br>発走15分前（チケット購入）と<br>発走5分前（レース開始）にリマインドします。</p>';
      return;
    }

    var events = upcomingEvents(now);
    var fired = readFired();
    if (!events.length) {
      list.innerHTML =
        '<p class="global-bell-empty">発走時刻が取得できないお気に入りがあるか、予定中のリマインダーはありません。</p>';
      return;
    }

    list.innerHTML = events
      .map(function (ev) {
        var done = !!fired[ev.key] || ev.at.getTime() < now.getTime();
        var status = done ? "通知済み / 経過" : formatRemain(ev.at.getTime() - now.getTime());
        return (
          '<a class="global-bell-item' +
          (done ? " is-done" : "") +
          '" href="' +
          ev.href +
          '">' +
          '<span class="global-bell-type global-bell-type--' +
          ev.type +
          '">' +
          ev.typeLabel +
          "</span>" +
          '<span class="global-bell-main">' +
          '<span class="global-bell-race">' +
          ev.label +
          "</span>" +
          '<span class="global-bell-meta">' +
          ev.note +
          " · 発走 " +
          formatClock(ev.postAt) +
          " · 通知 " +
          formatClock(ev.at) +
          "</span>" +
          '<span class="global-bell-remain">' +
          status +
          "</span>" +
          "</span></a>"
        );
      })
      .join("");
  }

  function requestPermissionIfNeeded() {
    if (!("Notification" in global)) return;
    if (Notification.permission === "default") {
      try {
        Notification.requestPermission();
      } catch (e) {}
    }
  }

  function bind(root) {
    var wrap = (root && root.querySelector(".global-bell")) || document.querySelector(".global-bell");
    var btn = wrap && wrap.querySelector("[data-global-bell]");
    var panel = wrap && wrap.querySelector("[data-bell-panel]");
    if (!wrap || !btn || !panel || bound) {
      if (wrap && btn && panel) {
        ensureRaceMeta().finally(function () {
          renderPanel();
          updateBadge();
        });
      }
      return;
    }
    bound = true;

    function close() {
      wrap.classList.remove("is-open");
      panel.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    }

    function open() {
      wrap.classList.add("is-open");
      panel.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      renderPanel();
      requestPermissionIfNeeded();

      var now = new Date();
      var next = upcomingEvents(now).filter(function (ev) {
        return ev.at.getTime() >= now.getTime();
      })[0];
      if (next && global.ExpectShell && ExpectShell.speakMascot) {
        ExpectShell.speakMascot(
          "ベルのリマインダーだよ！<br>次は <strong>" +
            next.label +
            "</strong><br>" +
            next.typeLabel +
            "（" +
            next.note +
            "）<br>通知 " +
            formatClock(next.at) +
            " 予定♪",
          5600
        );
      } else if (global.ExpectShell && ExpectShell.speakMascot) {
        ExpectShell.speakMascot(
          "お気に入りレースを登録すると、<br>発走15分前と5分前に<br>わたしがリマインドするよ！",
          5200
        );
      }
    }

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (wrap.classList.contains("is-open")) close();
      else open();
    });

    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) close();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });

    ensureRaceMeta().finally(function () {
      renderPanel();
      updateBadge();
      fireDue();
      if (pollTimer) clearInterval(pollTimer);
      pollTimer = setInterval(function () {
        fireDue();
        if (wrap.classList.contains("is-open")) renderPanel();
        else updateBadge();
      }, POLL_MS);
    });
  }

  function tryBind() {
    var tools = document.querySelector(".global-tools");
    if (tools) bind(tools);
  }

  global.ExpectReminders = {
    bind: bind,
    buildEvents: buildEvents,
    fireDue: fireDue,
    ensureRaceMeta: ensureRaceMeta,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", tryBind);
  } else {
    tryBind();
  }
})(window);
