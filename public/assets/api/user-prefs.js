/**
 * ExpectUserPrefs — 通知設定（preferences）のローカル適用
 * notify: ブラウザ通知 + リマインダー
 * odds_alert: オッズ変動アラート（オッズ画面更新時）
 */
(function (global) {
  "use strict";

  var KEY = "expect_user_prefs_v1";

  function read() {
    try {
      var raw = global.localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  function write(prefs) {
    try {
      global.localStorage.setItem(KEY, JSON.stringify(prefs || {}));
    } catch (e) {}
  }

  function fromMe(me) {
    var p = (me && me.profile && me.profile.preferences) || {};
    var next = {
      notify: p.notify !== false,
      odds_alert: !!p.odds_alert,
      locale: (me && me.profile && me.profile.locale) || "ja",
    };
    write(next);
    return next;
  }

  function get() {
    var p = read();
    return {
      notify: p.notify !== false,
      odds_alert: !!p.odds_alert,
      locale: p.locale || "ja",
    };
  }

  function notificationsEnabled() {
    return !!get().notify;
  }

  function oddsAlertEnabled() {
    return !!get().odds_alert;
  }

  function ensurePermission() {
    if (!notificationsEnabled()) return Promise.resolve("denied-by-pref");
    if (!("Notification" in global)) return Promise.resolve("unsupported");
    if (Notification.permission === "granted") return Promise.resolve("granted");
    if (Notification.permission === "denied") return Promise.resolve("denied");
    return Notification.requestPermission();
  }

  function notify(title, body, tag) {
    if (!notificationsEnabled()) return false;
    if (!("Notification" in global)) return false;
    if (Notification.permission !== "granted") return false;
    try {
      new Notification(title, { body: body || "", tag: tag || "expect" });
      return true;
    } catch (e) {
      return false;
    }
  }

  function alertOdds(message) {
    if (!oddsAlertEnabled()) return false;
    if (global.ExpectShell && ExpectShell.speakMascot) {
      ExpectShell.speakMascot(message, 5200);
    }
    notify("オッズ変動アラート", message.replace(/<[^>]+>/g, " "), "odds-alert");
    return true;
  }

  global.ExpectUserPrefs = {
    fromMe: fromMe,
    get: get,
    write: write,
    notificationsEnabled: notificationsEnabled,
    oddsAlertEnabled: oddsAlertEnabled,
    ensurePermission: ensurePermission,
    notify: notify,
    alertOdds: alertOdds,
  };
})(typeof window !== "undefined" ? window : globalThis);
