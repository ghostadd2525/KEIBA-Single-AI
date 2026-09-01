/**
 * ExpectApi.Auth — AuthService クライアント（Phase9 招待制β）
 *
 * POST /api/auth/invite/start
 * POST /api/auth/setup
 * POST /api/auth/login
 * POST /api/auth/logout
 * GET  /api/auth/me
 * GET|PUT /api/auth/favorites  (PUT = add|remove intent ops)
 */
(function (global) {
  "use strict";

  var SCHEMA = "expect-auth/1.0";
  var TOKEN_KEY = "expect_access_token_v1";
  var SETUP_TOKEN_KEY = "expect_setup_token_v1";

  function getToken() {
    try {
      return global.localStorage.getItem(TOKEN_KEY) || "";
    } catch (e) {
      return "";
    }
  }

  function setToken(token) {
    try {
      if (!token) global.localStorage.removeItem(TOKEN_KEY);
      else global.localStorage.setItem(TOKEN_KEY, String(token));
    } catch (e) { /* ignore */ }
  }

  function getSetupToken() {
    try {
      return global.sessionStorage.getItem(SETUP_TOKEN_KEY) || "";
    } catch (e) {
      return "";
    }
  }

  function setSetupToken(token) {
    try {
      if (!token) global.sessionStorage.removeItem(SETUP_TOKEN_KEY);
      else global.sessionStorage.setItem(SETUP_TOKEN_KEY, String(token));
    } catch (e) { /* ignore */ }
  }

  function api(path, options) {
    options = options || {};
    var headers = { Accept: "application/json" };
    if (!options.anonymous) {
      var token = options.useSetupToken ? getSetupToken() : getToken();
      if (options.bearer) token = options.bearer;
      if (token) headers.Authorization = "Bearer " + token;
    }
    if (options.body != null) headers["Content-Type"] = "application/json; charset=utf-8";

    return fetch(path, {
      method: options.method || "GET",
      headers: headers,
      body: options.body != null ? JSON.stringify(options.body) : undefined,
    }).then(function (res) {
      return res.text().then(function (text) {
        var payload = null;
        try {
          payload = text ? JSON.parse(text) : null;
        } catch (e) {
          payload = null;
        }
        if (!res.ok || (payload && payload.ok === false)) {
          var err = new Error(
            (payload && payload.error && payload.error.message) || "API error " + res.status
          );
          err.status = res.status;
          err.code = (payload && payload.error && payload.error.code) || "HTTP_" + res.status;
          throw err;
        }
        return payload && payload.data != null ? payload.data : payload;
      });
    });
  }

  function normalizeLogin(data) {
    if (!data || typeof data !== "object") return null;
    return {
      schema_version: data.schema_version || SCHEMA,
      access_token: data.access_token || "",
      token_type: data.token_type || "bearer",
      expires_in: data.expires_in != null ? Number(data.expires_in) : 86400,
      user: data.user || { id: "" },
      favorites: data.favorites || null,
    };
  }

  var Auth = {
    SCHEMA: SCHEMA,
    getToken: getToken,
    setToken: setToken,
    getSetupToken: getSetupToken,
    setSetupToken: setSetupToken,

    /** 一時ID → setup_token */
    inviteStart: function (inviteId) {
      return api("/api/auth/invite/start", {
        method: "POST",
        anonymous: true,
        body: { invite_id: String(inviteId || "").trim() },
      }).then(function (data) {
        if (data && data.setup_token) setSetupToken(data.setup_token);
        return data;
      });
    },

    /** 初回設定 → 正式ログイン相当 */
    setup: function (payload) {
      payload = payload || {};
      var body = {
        setup_token: payload.setup_token || getSetupToken(),
        login_id: payload.login_id || payload.id,
        password: payload.password,
        terms_accepted: !!payload.terms_accepted,
        favorites: payload.favorites,
      };
      return api("/api/auth/setup", { method: "POST", body: body }).then(function (data) {
        var normalized = normalizeLogin(data);
        if (normalized && normalized.access_token) {
          setToken(normalized.access_token);
          setSetupToken("");
        }
        return normalized;
      });
    },

    login: function (creds) {
      return api("/api/auth/login", {
        method: "POST",
        anonymous: true,
        body: creds || {},
      }).then(function (data) {
        var normalized = normalizeLogin(data);
        if (normalized && normalized.access_token) setToken(normalized.access_token);
        return normalized;
      });
    },

    logout: function (opts) {
      opts = opts || {};
      var body = {};
      if (opts.favorites) body.favorites = opts.favorites;
      return api("/api/auth/logout", { method: "POST", body: body })
        .catch(function () {
          return { schema_version: SCHEMA, logged_out: true };
        })
        .then(function (data) {
          setToken("");
          setSetupToken("");
          return data || { schema_version: SCHEMA, logged_out: true };
        });
    },

    me: function () {
      return api("/api/auth/me", { method: "GET" });
    },

    getFavorites: function () {
      return api("/api/auth/favorites", { method: "GET" }).then(function (data) {
        return (data && data.favorites) || data;
      });
    },

    /**
     * Intent 同期: { op, race_id } | { ops: [...] }
     * フルリスト置換はサーバーが拒否する（stale overwrite 防止）。
     */
    putFavorites: function (payload) {
      var body = payload && typeof payload === "object" ? payload : {};
      return api("/api/auth/favorites", {
        method: "PUT",
        body: body,
      }).then(function (data) {
        return (data && data.favorites) || data;
      });
    },
  };

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Auth = Auth;
  global.ExpectApi.getToken = getToken;
  global.ExpectApi.setToken = setToken;
  global.ExpectApi.logout = function () {
    setToken("");
    setSetupToken("");
  };
})(window);
