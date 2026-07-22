/**
 * Expect 認証 — Phase9 招待制β
 * ゲスト閲覧不可（strict 既定）。一時ID → 初回設定 → 正式ログイン。
 */
(function (global) {
  "use strict";

  var AUTH_KEY = "expect_auth_v1";
  var TOKEN_KEY = "expect_access_token_v1";
  var TERMS_KEY = "expect_terms_v1";
  var ONBOARD_KEY = "expect_onboard_v1";
  var ACCOUNT_READY_KEY = "expect_account_ready_v1";
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

  function getAccessToken() {
    var store = storage();
    if (!store) return "";
    return store.getItem(TOKEN_KEY) || "";
  }

  function setAccessToken(token) {
    var store = storage();
    if (!store) return false;
    if (!token) {
      store.removeItem(TOKEN_KEY);
      return true;
    }
    store.setItem(TOKEN_KEY, String(token));
    return true;
  }

  function isLoggedIn() {
    var s = readAuth();
    return !!(s && s.id && getAccessToken());
  }

  function hasServerSession() {
    return isLoggedIn() && !!getAccessToken();
  }

  function hasAcceptedTerms() {
    var t = readJson(TERMS_KEY);
    return !!(t && t.version === TERMS_VERSION && t.accepted === true);
  }

  function needsOnboarding() {
    var o = readJson(ONBOARD_KEY);
    return !(o && o.version === ONBOARD_VERSION && o.done === true);
  }

  function login(id, opts) {
    opts = opts || {};
    if (opts.access_token) setAccessToken(opts.access_token);
    return writeJson(AUTH_KEY, {
      id: String(id),
      display_name: opts.display_name || String(id),
      at: Date.now(),
    });
  }

  function localFavoritesPayload() {
    if (global.ExpectFavorites && typeof ExpectFavorites.exportForSync === "function") {
      return ExpectFavorites.exportForSync();
    }
    return { schema_version: "expect-favorites/1.0", race_ids: [], items: [] };
  }

  function hasAccountReady() {
    var s = readJson(ACCOUNT_READY_KEY);
    return !!(s && s.ready === true);
  }

  function markAccountReady(loginId) {
    return writeJson(ACCOUNT_READY_KEY, {
      ready: true,
      login_id: loginId ? String(loginId) : "",
      at: Date.now(),
    });
  }

  function finishLogin(data, fallbackId) {
    var user = (data && data.user) || { id: fallbackId };
    login(user.id || fallbackId, {
      access_token: data && data.access_token,
      display_name: user.display_name,
    });
    markAccountReady(user.id || fallbackId);
    if (data && data.access_token) {
      acceptTerms();
    }
    try {
      if (data && data.favorites && global.ExpectFavorites && ExpectFavorites.importFromServer) {
        ExpectFavorites.importFromServer(data.favorites, { merge: true });
      }
      if (global.ExpectFavorites && ExpectFavorites.syncNow) {
        ExpectFavorites.syncNow({ reason: "login" }).catch(function () { /* ignore */ });
      }
    } catch (e) { /* favorites must not block login */ }
    return { ok: true, data: data };
  }

  /** 正式ログイン（ログインID + パスワード） */
  function loginWithApi(id, password) {
    var creds = {
      id: String(id),
      password: password != null ? String(password) : "",
      favorites: localFavoritesPayload(),
    };

    if (global.ExpectApi && ExpectApi.Auth && typeof ExpectApi.Auth.login === "function") {
      return ExpectApi.Auth.login(creds).then(function (data) {
        return finishLogin(data, id);
      });
    }
    return Promise.reject(new Error("Auth API unavailable"));
  }

  /** 一時IDで初回設定を開始 */
  function startInvite(inviteId) {
    if (!global.ExpectApi || !ExpectApi.Auth || !ExpectApi.Auth.inviteStart) {
      return Promise.reject(new Error("Auth API unavailable"));
    }
    return ExpectApi.Auth.inviteStart(inviteId);
  }

  /** 初回設定完了 */
  function completeSetup(payload) {
    if (!global.ExpectApi || !ExpectApi.Auth || !ExpectApi.Auth.setup) {
      return Promise.reject(new Error("Auth API unavailable"));
    }
    var body = Object.assign({}, payload, { favorites: localFavoritesPayload() });
    return ExpectApi.Auth.setup(body).then(function (data) {
      return finishLogin(data, payload.login_id || payload.id);
    });
  }

  function acceptTerms() {
    return writeJson(TERMS_KEY, {
      accepted: true,
      version: TERMS_VERSION,
      at: Date.now(),
    });
  }

  function completeOnboarding() {
    return writeJson(ONBOARD_KEY, {
      done: true,
      version: ONBOARD_VERSION,
      at: Date.now(),
    });
  }

  function logout() {
    var fav = localFavoritesPayload();
    var clearLocal = function () {
      removeKey(AUTH_KEY);
      setAccessToken("");
      if (global.ExpectApi && ExpectApi.Auth && ExpectApi.Auth.setSetupToken) {
        ExpectApi.Auth.setSetupToken("");
      }
      if (global.ExpectApi && typeof ExpectApi.logout === "function") {
        ExpectApi.logout();
      }
    };

    if (global.ExpectApi && ExpectApi.Auth && typeof ExpectApi.Auth.logout === "function") {
      return ExpectApi.Auth.logout({ favorites: fav })
        .catch(function () { /* ignore network */ })
        .then(function () {
          clearLocal();
          return { ok: true };
        });
    }
    clearLocal();
    return Promise.resolve({ ok: true });
  }

  function refreshMe() {
    if (!isLoggedIn() || !global.ExpectApi || !ExpectApi.Auth || !ExpectApi.Auth.me) {
      return Promise.resolve(null);
    }
    return ExpectApi.Auth.me().then(function (data) {
      if (data && data.user) {
        writeJson(AUTH_KEY, {
          id: data.user.id,
          display_name: data.user.display_name || data.user.id,
          at: Date.now(),
        });
      }
      if (data && data.favorites && global.ExpectFavorites && ExpectFavorites.importFromServer) {
        ExpectFavorites.importFromServer(data.favorites, { merge: true });
      }
      return data;
    });
  }

  /**
   * Phase9 β: 既定でログイン必須（strict）。
   * opts.strict === false でゲスト許可（非推奨）。
   */
  function requireAuth(opts) {
    opts = opts || {};
    var here = pageName();
    if (
      here === "login.html" ||
      here === "terms.html" ||
      here === "setup.html" ||
      here === "login" ||
      here === "terms" ||
      here === "setup"
    ) {
      return true;
    }

    var strict = opts.strict !== false;
    if (!strict) return true;

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

  function pageName() {
    var parts = (location.pathname || "").split("/");
    var last = parts[parts.length - 1] || "index.html";
    return last;
  }

  global.ExpectAuth = {
    TERMS_VERSION: TERMS_VERSION,
    ONBOARD_VERSION: ONBOARD_VERSION,
    isLoggedIn: isLoggedIn,
    hasServerSession: hasServerSession,
    hasAcceptedTerms: hasAcceptedTerms,
    needsOnboarding: needsOnboarding,
    login: login,
    loginWithApi: loginWithApi,
    startInvite: startInvite,
    completeSetup: completeSetup,
    acceptTerms: acceptTerms,
    completeOnboarding: completeOnboarding,
    logout: logout,
    requireAuth: requireAuth,
    refreshMe: refreshMe,
    current: readAuth,
    getAccessToken: getAccessToken,
    setAccessToken: setAccessToken,
    hasAccountReady: hasAccountReady,
    markAccountReady: markAccountReady,
  };
})(window);
