/**
 * Conversation Layer BFF — POST /api/conversation/chat
 * Python ConversationService へプロキシ。未設定時は意図スタブ。
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestPost(context) {
  let body = {};
  try {
    body = await context.request.json();
  } catch {
    body = {};
  }

  const env = getEnv(context);
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/conversation/chat", {
      method: "POST",
      body: JSON.stringify(body || {}),
    });
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok) {
      return jsonOk(proxied.payload.data, {
        ...(proxied.payload.meta || {}),
        provider: "python",
        service: "ConversationService",
      });
    }
  }

  // AI_BASE_URL 未設定時の薄いスタブ（チャット UI 追加前の契約確認用）
  const message = String((body && body.message) || "");
  return jsonOk(
    {
      session_id: (body && body.session_id) || "stub",
      intent: { name: "unknown", confidence: 0.1, race_id: body && body.race_id },
      reply: "Conversation Layer スタブです。AI_BASE_URL を設定すると Intent→Prediction 経路が有効になります。 message=" + message.slice(0, 80),
      citations: [],
      actions: [{ type: "configure_ai_base_url" }],
    },
    { provider: "bff_stub", service: "ConversationService" }
  );
}
