/**
 * Conversation Layer BFF — POST /api/conversation/chat
 * Python ConversationService へプロキシ。
 * 404 / 未設定時は Kaoba → 薄いスタブへフォールバック（UI が壊れないように）。
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { KaobaAdapter } from "../../_lib/adapters/kaobaAdapter.js";
import { getBearer } from "../../_lib/auth.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

function stubReply(body) {
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
    });
    if (proxied && proxied.ok && !(proxied instanceof Response)) {
      return jsonOk(proxied.payload.data, {
        ...(proxied.payload.meta || {}),
        provider: "python",
        service: "ConversationService",
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

  const kaoba = await viaKaoba(context, body);
  if (kaoba) return kaoba;

  return jsonOk(stubReply(body), {
    provider: "bff_stub",
    service: "ConversationService",
    fallback: "stub",
  });
}
