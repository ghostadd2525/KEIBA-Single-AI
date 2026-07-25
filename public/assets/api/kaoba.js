/**
 * ExpectApi.Kaoba — KaobaService（AI Concierge）クライアント
 *
 * POST /api/kaoba/chat
 * fetch はここ以外に書かない（画面は ExpectApi.Kaoba のみ）
 *
 * 契約: contracts/expect-kaoba/1.0/
 */
(function (global) {
  "use strict";

  var SCHEMA = "expect-kaoba/1.0";

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function normalizeResponse(raw, raceId) {
    if (!raw || typeof raw !== "object") {
      return {
        schema_version: SCHEMA,
        reply: "うまく答えられなかったみたい。もう一度聞いてね。",
        suggestions: [],
        emotion: "neutral",
        referenced_race_id: raceId || null,
        provider: "fallback",
      };
    }
    return {
      schema_version: raw.schema_version || SCHEMA,
      reply: typeof raw.reply === "string" && raw.reply ? raw.reply : "うまく答えられなかったみたい。",
      suggestions: Array.isArray(raw.suggestions) ? raw.suggestions : [],
      emotion: raw.emotion || "neutral",
      referenced_race_id:
        raw.referenced_race_id != null
          ? raw.referenced_race_id
          : raw.race_id != null
            ? raw.race_id
            : raceId || null,
      provider: raw.provider || "mock",
      live2d: raw.live2d,
    };
  }

  function mockChat(payload) {
    var message = String((payload && payload.message) || "");
    var raceId = (payload && payload.race_id) || null;
    var reply = "（オフライン）いい質問！通信が戻ったらもっと詳しく答えるね。";
    if (/展開|ペース/.test(message)) {
      reply = "（オフライン）展開は差し有利のイメージで見てみよう。";
    } else     if (/買い目|戦略/.test(message)) {
      reply = "（オフライン）買い目は軸1頭流しで点数を抑えるのがおすすめだよ。";
    }
    return Promise.resolve(
      normalizeResponse(
        {
          schema_version: SCHEMA,
          reply: reply,
          suggestions: ["展開予想を教えて", "血統について教えて", "買い目を提案して"],
          emotion: "fun",
          referenced_race_id: raceId,
          provider: "offline-mock",
        },
        raceId
      )
    );
  }

  function apiPost(path, body) {
    var headers = { Accept: "application/json", "Content-Type": "application/json; charset=utf-8" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;

    return fetch(path, {
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
            (payload && payload.error && payload.error.message) || "API error " + res.status
          );
          err.status = res.status;
          throw err;
        }
        return payload && payload.data != null ? payload.data : payload;
      });
    });
  }

  var Kaoba = {
    SCHEMA: SCHEMA,

    /**
     * @param {{ message: string, history?: Array, race_id?: string, context?: object }} payload
     * @returns {Promise<object>} KaobaChatResponse
     */
    chat: function (payload) {
      payload = payload || {};
      var message = String(payload.message || "").trim();
      if (!message) return Promise.reject(new Error("message required"));

      var body = {
        message: message,
        history: Array.isArray(payload.history) ? payload.history : [],
        race_id: payload.race_id || null,
        context: payload.context || undefined,
      };

      return apiPost("/api/kaoba/chat", body)
        .then(function (data) {
          return normalizeResponse(data, body.race_id);
        })
        .catch(function () {
          if (global.ExpectMockGate && ExpectMockGate.allowMockFallback()) {
            return mockChat(body);
          }
          return Promise.reject(new Error("Kaoba API unavailable"));
        });
    },
  };

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Kaoba = Kaoba;
})(window);
