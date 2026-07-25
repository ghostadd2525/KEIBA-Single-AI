/**
 * ExpectI18n — 簡易 日英切替（locale: ja | en）
 */
(function (global) {
  "use strict";

  var DICT = {
    ja: {
      "profile.title": "プロフィール編集",
      "profile.lead": "表示名・画像・言語・通知を変更できます。ユーザーID・role・パスワードは変更できません。",
      "profile.display_name": "表示名",
      "profile.avatar_url": "プロフィール画像URL",
      "profile.avatar_hint": "画像のURLを入れるとマイページのアイコンが変わります（空欄でデフォルト画像）。",
      "profile.locale": "言語",
      "profile.notify": "通知設定",
      "profile.notify_receive": "通知を受け取る",
      "profile.odds_alert": "オッズ変動アラート",
      "profile.user_id": "ユーザーID",
      "profile.role": "role",
      "profile.password_note": "パスワード変更はこの画面ではできません。",
      "profile.save": "保存する",
      "profile.saved": "保存しました。",
      "profile.saving": "保存中…",
      "profile.fail": "保存に失敗しました。",
      "profile.back": "マイページへ戻る",
      "mypage.edit_profile": "プロフィール編集",
    },
    en: {
      "profile.title": "Edit profile",
      "profile.lead": "You can change display name, avatar, language, and notifications. User ID, role, and password cannot be changed here.",
      "profile.display_name": "Display name",
      "profile.avatar_url": "Avatar image URL",
      "profile.avatar_hint": "Paste an image URL to change your My Page icon (leave blank for the default).",
      "profile.locale": "Language",
      "profile.notify": "Notifications",
      "profile.notify_receive": "Enable notifications",
      "profile.odds_alert": "Odds change alerts",
      "profile.user_id": "User ID",
      "profile.role": "role",
      "profile.password_note": "Password cannot be changed on this screen.",
      "profile.save": "Save",
      "profile.saved": "Saved.",
      "profile.saving": "Saving…",
      "profile.fail": "Failed to save.",
      "profile.back": "Back to My Page",
      "mypage.edit_profile": "Edit profile",
    },
  };

  function locale() {
    if (global.ExpectUserPrefs && ExpectUserPrefs.get) {
      return ExpectUserPrefs.get().locale === "en" ? "en" : "ja";
    }
    try {
      var raw = global.localStorage.getItem("expect_user_prefs_v1");
      var p = raw ? JSON.parse(raw) : {};
      return p.locale === "en" ? "en" : "ja";
    } catch (e) {
      return "ja";
    }
  }

  function t(key) {
    var loc = locale();
    return (DICT[loc] && DICT[loc][key]) || (DICT.ja && DICT.ja[key]) || key;
  }

  function apply(root) {
    var scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (!key) return;
      el.textContent = t(key);
    });
    if (document.documentElement) {
      document.documentElement.lang = locale();
    }
  }

  global.ExpectI18n = { t: t, apply: apply, locale: locale, DICT: DICT };
})(typeof window !== "undefined" ? window : globalThis);
