/**
 * Conversation Layer BFF — POST /api/conversation/chat
 * Python ConversationService / V4 Orchestrator へプロキシ。
 * 404 / 未設定時は Kaoba → 薄いスタブへフォールバック（UI が壊れないように）。
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { KaobaAdapter } from "../../_lib/adapters/kaobaAdapter.js";
import { getBearer } from "../../_lib/auth.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

function isPersonalChatBody(body) {
  const mode = String((body && body.mode) || "").toLowerCase();
  const ctxType = body && body.context && body.context.type;
  return (
    mode === "chat" ||
    mode === "personal_chat" ||
    ctxType === "personal_chat" ||
    ctxType === "mypage_chat"
  );
}

function personalChatStub(body) {
  const message = String((body && body.message) || "").trim();
  let reply =
    "こんにちは。マイページの日常会話だよ。いま会話エンジン（Personal Chat）の準備中で、簡易応答になっているよ。競馬の予想変更はしないから、気軽に話しかけてね。";
  if (/こんにちは|はじめまして|やあ|hello/i.test(message)) {
    reply =
      "こんにちは！マイページのチャットルームだよ。いまは簡易モードだけど、雑談や使い方の質問なら大丈夫。予想の印はここでは変えないよ。";
  } else if (/気分|元気|調子|天気/.test(message)) {
    reply =
      "聞いてくれてありがとう。私はいつもレースの話も雑談も大歓迎だよ。今日はどんな一日？";
  } else if (/使い方|ヘルプ|help/i.test(message)) {
    reply =
      "このチャットルームは日常会話用だよ。レースの◎理由や相談は、レース詳細の「KAOBAに◎の理由を聞く」「KAOBAに相談」からどうぞ。";
  } else if (message) {
    reply =
      "「" +
      message.slice(0, 40) +
      "」ね。いまは簡易モードだから深い雑談はまだ弱いけど、もう少し具体的に話してくれると嬉しいな。";
  }
  return {
    session_id: (body && body.session_id) || "personal-chat-stub",
    agent: "chat",
    mode: "chat",
    intent: { name: "chat", confidence: 0.5, race_id: null, slots: { domain: "personal_chat" } },
    reply,
    citations: [],
    actions: [{ type: "mypage_chat" }],
    prediction_meta: null,
    kaoba_independent: true,
    involves_prediction: false,
    llm: { used: false, ollama_called: false, role: "bff_personal_chat_guard" },
    fallback: "bff_personal_chat_pending_v4",
  };
}

function looksLikeLegacyRaceRequired(data) {
  const reply = String((data && data.reply) || "");
  return /対象レースの予想データが見つかりません|レースを指定してください/.test(reply);
}

function stubReply(body) {
  if (isPersonalChatBody(body)) return personalChatStub(body);

  const message = String((body && body.message) || "");
  const raceId = (body && body.race_id) || null;
  const ctxType = body && body.context && body.context.type;
  let reply =
    "いまは簡易モードでお答えするね。レースや買い目のことは、もう少し具体的に聞いてみて！";
  if (ctxType === "strategy_review") {
    reply =
      "戦略の内容は受け取ったよ。軸と相手のバランスを見つつ、点数は抑えめが安心だと思う。詳しい評価は戦略画面の数値とあわせて確認してね。";
  } else if (raceId) {
    reply =
      "レース（" +
      String(raceId) +
      "）について聞かれたね。「展開」「血統」「買い目」のどれが気になる？";
  } else if (message) {
    reply = "「" + message.slice(0, 40) + "」についてだね。レースを指定してもらえると、もっと具体的に話せるよ。";
  }
  return {
    session_id: (body && body.session_id) || "stub",
    intent: { name: ctxType === "strategy_review" ? "strategy_review" : "unknown", confidence: 0.2, race_id: raceId },
    reply,
    citations: [],
    actions: [],
  };
}

async function viaKaoba(context, body) {
  try {
    const result = await KaobaAdapter.chat(context, body || {});
    if (result && result.errorResponse) return null;
    const resp = result && result.response;
    if (!resp) return null;
    const reply = resp.reply || resp.message || resp.text;
    if (!reply) return null;
    return jsonOk(
      {
        session_id: (body && body.session_id) || "kaoba",
        intent: { name: "kaoba_fallback", confidence: 0.4, race_id: body && body.race_id },
        reply: String(reply),
        citations: resp.citations || [],
        actions: resp.actions || [],
        prediction_meta: resp.prediction_meta || null,
      },
      {
        provider: result.provider || "kaoba",
        service: "ConversationService",
        fallback: "kaoba",
      }
    );
  } catch {
    return null;
  }
}

export async function onRequestPost(context) {
  let body = {};
  try {
    body = await context.request.json();
  } catch {
    body = {};
  }

  const token = getBearer(context.request);
  const proxyHeaders = {};
  if (token) proxyHeaders.Authorization = `Bearer ${token}`;

  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/conversation/chat", {
      method: "POST",
      headers: proxyHeaders,
      body: JSON.stringify(body || {}),
      // Explain/Review + Ollama は 25s 超えることがある → Kaoba 定型への誤フォールバック防止
      timeoutMs: 60000,
    });
    if (proxied && proxied.ok && !(proxied instanceof Response)) {
      const data = proxied.payload.data;
      const pyMeta = proxied.payload.meta || {};

      // EC2 で V4 Flag OFF / 旧コードのとき Legacy がレース必須エラーを返す。
      // Personal Chat ではレース不要なので BFF でガードする。
      if (isPersonalChatBody(body) && looksLikeLegacyRaceRequired(data) && !data?.orchestrator) {
        return jsonOk(personalChatStub(body), {
          provider: "python_legacy_guarded",
          service: "ConversationBff",
          platform: "pending_v4",
          ollama: false,
          fallback: "personal_chat_legacy_guard",
        });
      }

      return jsonOk(data, {
        ...pyMeta,
        provider: pyMeta.provider || "python",
        // Python が Orchestrator を返したときは上書きしない
        service: pyMeta.service || "ConversationService",
      });
    }
    // 404 / 不通: Conversation 未配備プロセスでも UI を止めない
    const status =
      proxied instanceof Response
        ? proxied.status
        : proxied && proxied.status
          ? proxied.status
          : 0;
    if (status && status !== 404 && status < 500 && proxied instanceof Response) {
      return proxied;
    }
  }

  if (isPersonalChatBody(body)) {
    return jsonOk(personalChatStub(body), {
      provider: "bff_stub",
      service: "ConversationBff",
      platform: "pending_v4",
      ollama: false,
      fallback: "personal_chat_stub",
    });
  }

  const kaoba = await viaKaoba(context, body);
  if (kaoba) return kaoba;

  return jsonOk(stubReply(body), {
    provider: "bff_stub",
    service: "ConversationService",
    fallback: "stub",
  });
}
