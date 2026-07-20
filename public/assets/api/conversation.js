/**
 * ExpectApi.Conversation — Conversation Layer クライアント
 * POST /api/conversation/chat
 */
(function (global) {
  "use strict";

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function chat(body) {
    var headers = {
      Accept: "application/json",
      "Content-Type": "application/json; charset=utf-8",
    };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;

    return fetch("/api/conversation/chat", {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body || {}),
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
            (payload && payload.error && payload.error.message) || "Conversation API error"
          );
          err.status = res.status;
          throw err;
        }
        var data = payload && payload.data != null ? payload.data : payload;
        data.__meta = payload && payload.meta ? payload.meta : {};
        return data;
      });
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Conversation = { chat: chat };
})(window);
