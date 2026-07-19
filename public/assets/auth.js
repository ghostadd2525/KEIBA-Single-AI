/**
 * Expect 簡易認証（プロトタイプ用）
 * 規約同意・操作説明は端末内で初回のみ（ログアウト後も再表示しない）
 */
(function (global) {
  "use strict";

  var AUTH_KEY = "expect_auth_v1";
  var TERMS_KEY = "expect_terms_v1";
  var ONBOARD_KEY = "expect_onboard_v1";
  var TERMS_VERSION = "2026-07-19";
  var ONBOARD_VERSION = "2026-07-19";

  function storage() {
    try {
      return global.localStorage;
    } catch (e) {
      return null;
    }
  }

  function readJson(key) {
    var store = storage();
    if (!store) return null;
    try {
      return JSON.parse(store.getItem(key) || "null");
    } catch (e) {
      return null;
    }
  }

  function writeJson(key, data) {
    var store = storage();
    if (!store) return false;
    try {
      store.setItem(key, JSON.stringify(data));
      return true;
    } catch (e) {
      return false;
    }
  }

  function removeKey(key) {
    var store = storage();
    if (!store) return;
    try {
      store.removeItem(key);
    } catch (e) { /* ignore */ }
  }

  function readAuth() {
    return readJson(AUTH_KEY);
  }

  function isLoggedIn() {
    var s = readAuth();
    return !!(s && s.id);
  }

  function hasAcceptedTerms() {
    var t = readJson(TERMS_KEY);
    return !!(t && t.version === TERMS_VERSION && t.accepted === true);
  }

  function needsOnboarding() {
    var o = readJson(ONBOARD_KEY);
    return !(o && o.version === ONBOARD_VERSION && o.done === true);
  }

  function login(id) {
    return writeJson(AUTH_KEY, {
      id: String(id),
      at: Date.now()
    });
  }

  function acceptTerms() {
    if (!isLoggedIn()) return false;
    return writeJson(TERMS_KEY, {
      accepted: true,
      version: TERMS_VERSION,
      at: Date.now()
    });
  }

  function completeOnboarding() {
    return writeJson(ONBOARD_KEY, {
      done: true,
      version: ONBOARD_VERSION,
      at: Date.now()
    });
  }

  function logout() {
    // ログイン状態のみクリア（規約・操作説明は初回フラグとして残す）
    removeKey(AUTH_KEY);
  }

  function pageName() {
    var parts = (location.pathname || "").split("/");
    return parts[parts.length - 1] || "index.html";
  }

  function requireAuth() {
    var here = pageName();
    if (here === "login.html" || here === "terms.html") return false;

    if (!isLoggedIn()) {
      location.replace("login.html");
      return false;
    }
    if (!hasAcceptedTerms()) {
      location.replace("terms.html");
      return false;
    }
    return true;
  }

  global.ExpectAuth = {
    TERMS_VERSION: TERMS_VERSION,
    ONBOARD_VERSION: ONBOARD_VERSION,
    isLoggedIn: isLoggedIn,
    hasAcceptedTerms: hasAcceptedTerms,
    needsOnboarding: needsOnboarding,
    login: login,
    acceptTerms: acceptTerms,
    completeOnboarding: completeOnboarding,
    logout: logout,
    requireAuth: requireAuth,
    current: readAuth
  };
})(window);
