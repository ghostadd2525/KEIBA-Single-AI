/**
 * ExpectRoles — クライアント側ロール正規化（functions/_lib/roles.js と同等）
 * UI / ops portal / mypage / auto-maintenance で判定元を統一する。
 */
(function (global) {
  "use strict";

  var Role = {
    USER: "USER",
    ADMIN: "ADMIN",
    OPS: "OPS",
    DEVELOPER: "DEVELOPER",
  };

  function normalizeRole(raw) {
    var r = String(raw == null ? "" : raw)
      .trim()
      .toUpperCase();
    if (!r) return Role.USER;
    if (r === "ADMINISTRATOR" || r === "ROOT" || r === "ADMIN") return Role.ADMIN;
    if (r === Role.OPS || r === Role.DEVELOPER || r === Role.USER) return r;
    // roles[] 先頭など
    if (r.indexOf("ADMIN") >= 0) return Role.ADMIN;
    return Role.USER;
  }

  function firstRoleFromList(list) {
    if (!list) return "";
    if (typeof list === "string") return list;
    if (Array.isArray(list) && list.length) return list[0];
    return "";
  }

  /**
   * Auth.me / users/me / JWT / ネスト user を単一プロファイルへ正規化
   * @returns {{ id: string, role: string, display_name?: string, roles?: any } | null}
   */
  function normalizeMe(raw) {
    if (!raw || typeof raw !== "object") return null;
    var root = raw.data && typeof raw.data === "object" ? raw.data : raw;
    var user =
      root.user && typeof root.user === "object"
        ? root.user
        : root.profile && root.profile.role != null
          ? Object.assign({}, root, { role: root.profile.role })
          : root;

    var roleRaw =
      user.role ||
      firstRoleFromList(user.roles) ||
      firstRoleFromList(root.roles) ||
      root.role ||
      "";

    var id =
      user.id ||
      user.user_id ||
      user.login_id ||
      root.user_id ||
      root.login_id ||
      root.id ||
      "";

    return {
      id: id ? String(id) : "",
      role: normalizeRole(roleRaw),
      display_name: user.display_name || (user.profile && user.profile.display_name) || "",
      roles: user.roles || root.roles || null,
      raw: root,
    };
  }

  function parseStubToken(token) {
    if (!token || String(token).indexOf("stub.") !== 0) return null;
    try {
      var parts = String(token).split(".");
      if (parts.length < 3) return null;
      var b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      var json = decodeURIComponent(escape(atob(b64)));
      return JSON.parse(json);
    } catch (e) {
      return null;
    }
  }

  function roleFromAccessToken() {
    var token = "";
    try {
      if (global.ExpectAuth && ExpectAuth.getAccessToken) {
        token = ExpectAuth.getAccessToken() || "";
      } else {
        token = localStorage.getItem("expect_access_token_v1") || "";
      }
    } catch (e) {
      token = "";
    }
    var payload = parseStubToken(token);
    if (!payload) return Role.USER;
    return normalizeRole(payload.role || "");
  }

  function localUserId() {
    try {
      var raw = localStorage.getItem("expect_auth_v1");
      var auth = raw ? JSON.parse(raw) : null;
      return (auth && auth.id) || "";
    } catch (e) {
      return "";
    }
  }

  /**
   * Version8.7 Operations Portal — 実効 ADMIN 判定
   * - normalizeRole 後の ADMIN
   * - JWT role
   * - beta.admin_user_ids allowlist
   */
  function isOpsPortalAdminSync(meLike, beta) {
    var me = normalizeMe(meLike) || { id: "", role: Role.USER };
    if (me.role === Role.ADMIN) return true;
    if (roleFromAccessToken() === Role.ADMIN) return true;

    var ids = (beta && Array.isArray(beta.admin_user_ids) && beta.admin_user_ids) || [];
    var uid = me.id || localUserId();
    if (uid && ids.map(String).indexOf(String(uid)) >= 0) return true;
    return false;
  }

  function isOpsPortalAdmin(meLike, beta) {
    if (isOpsPortalAdminSync(meLike, beta)) {
      return Promise.resolve(true);
    }
    var me = normalizeMe(meLike) || { id: localUserId(), role: Role.USER };
    return fetch("/config/beta.json", { cache: "no-store" })
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .then(function (doc) {
        return isOpsPortalAdminSync(me, doc || beta || {});
      })
      .catch(function () {
        return false;
      });
  }

  global.ExpectRoles = {
    Role: Role,
    normalizeRole: normalizeRole,
    normalizeMe: normalizeMe,
    roleFromAccessToken: roleFromAccessToken,
    isOpsPortalAdminSync: isOpsPortalAdminSync,
    isOpsPortalAdmin: isOpsPortalAdmin,
  };
})(window);
