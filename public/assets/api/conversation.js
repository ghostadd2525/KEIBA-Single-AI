/**
 * ExpectApi.Conversation — Conversation Platform クライアント（V5 UI Integration）
 *
 * POST /api/conversation/chat → BFF → /v1/conversation/chat
 * Prediction は Read Only（UI から予測を変更しない）。
 *
 * Modes（ADR / V4 契約）:
 *   explain — KAOBAに◎の理由を聞く（予想の説明）
 *   review  — 相談AI（買い方・立ち回り）
 *   chat    — マイページ日常会話（Personal Chat）
 */
(function (global) {
  "use strict";

  var MODES = {
    explain: { label: "KAOBAに◎の理由を聞く", contextType: "honmei_reason" },
    review: { label: "相談AI", contextType: "consult" },
    chat: { label: "マイページ日常会話", contextType: "personal_chat" },
  };

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function normalizeMode(raw) {
    var s = String(raw || "")
      .trim()
      .toLowerCase();
    if (s === "explain" || s === "explain_pick" || s === "honmei_reason") return "explain";
    if (s === "review" || s === "consult" || s === "strategy_review") return "review";
    if (s === "chat" || s === "personal_chat" || s === "mypage_chat") return "chat";
    return "";
  }

  function chat(body) {
    body = body || {};
    var headers = {
      Accept: "application/json",
      "Content-Type": "application/json; charset=utf-8",
    };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;

    var mode = normalizeMode(body.mode);
    var ctx = body.context && typeof body.context === "object" ? Object.assign({}, body.context) : {};
    if (mode && !ctx.type && MODES[mode]) {
      ctx.type = MODES[mode].contextType;
      ctx.mode = mode;
    }
    if (mode) {
      body = Object.assign({}, body, { mode: mode, context: ctx });
    }

    // UI は Prediction を送って Official を上書きしない（ADR-003）
    if (body.prediction) {
      delete body.prediction;
    }
    if (body.prediction_bundle) {
      delete body.prediction_bundle;
    }

    return fetch("/api/conversation/chat", {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
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

  function explain(opts) {
    opts = opts || {};
    return chat({
      mode: "explain",
      message: opts.message || "なぜ本命なの？理由を教えて",
      race_id: opts.race_id || opts.raceId || null,
      session_id: opts.session_id || null,
      context: Object.assign({ ui: "race", type: "honmei_reason", mode: "explain" }, opts.context || {}),
    });
  }

  function review(opts) {
    opts = opts || {};
    return chat({
      mode: "review",
      message: opts.message || "この予想について相談したい",
      race_id: opts.race_id || opts.raceId || null,
      session_id: opts.session_id || null,
      context: Object.assign({ ui: "race", type: "consult", mode: "review" }, opts.context || {}),
    });
  }

  function personalChat(opts) {
    opts = opts || {};
    return chat({
      mode: "chat",
      message: opts.message || "こんにちは",
      session_id: opts.session_id || null,
      context: Object.assign(
        { ui: "mypage", type: "personal_chat", mode: "chat" },
        opts.context || {}
      ),
    });
  }

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Conversation = {
    MODES: MODES,
    normalizeMode: normalizeMode,
    chat: chat,
    explain: explain,
    review: review,
    personalChat: personalChat,
  };
})(window);
