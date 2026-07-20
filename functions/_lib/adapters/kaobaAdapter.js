/**
 * KaobaReplyAdapter — 応答生成のみ差し替え
 *
 * 契約（expect-kaoba/1.0）・POST /api/kaoba/chat は変更しない。
 *
 * プロバイダ優先順位:
 *   1. python … AI_BASE_URL → POST /v1/kaoba/chat（将来 LLM 実装）
 *   2. rule  … generateKaobaReply（現行デフォルト）
 *
 * env.KAOBA_PROVIDER = "python" | "rule" | "auto"（default: auto）
 *   auto = python 成功時は python、失敗時 rule
 */
import { aiFetch } from "../aiProxy.js";
import { getEnv } from "../env.js";
import {
  generateKaobaReply as ruleGenerateKaobaReply,
  loadKaobaRefs,
  normalizeKaobaResponse,
} from "../kaobaDomain.js";
import { adaptAnalysisGet } from "./analysisAdapter.js";
import { adaptPredictionGet } from "./predictionAdapter.js";

function providerMode(context) {
  const raw = String((getEnv(context).KAOBA_PROVIDER || "auto")).toLowerCase();
  if (raw === "python" || raw === "llm" || raw === "rule") return raw === "llm" ? "python" : raw;
  return "auto";
}

/**
 * race_id 参照を Adapter 経由で解決（Mock 直読みをやめる）
 * Prediction / Analysis が実AIになっても Kaoba は同じ経路で追従する。
 */
export async function loadKaobaRefsViaAdapters(context, raceId) {
  if (!raceId) {
    return { race_id: null, bundle: null, analysis: null };
  }

  const [pred, anal] = await Promise.all([
    adaptPredictionGet(context, raceId),
    adaptAnalysisGet(context, raceId),
  ]);

  const bundle = pred && pred.ok ? pred.bundle : null;
  const analysis = anal && anal.ok ? anal.analysis : null;

  return {
    race_id: raceId,
    bundle,
    analysis,
    ref_sources: {
      prediction: pred && pred.ok ? pred.provider : "none",
      analysis: anal && anal.ok ? anal.provider : "none",
    },
  };
}

async function generateViaPython(context, input) {
  const proxied = await aiFetch(context, "/v1/kaoba/chat", {
    method: "POST",
    body: JSON.stringify({
      message: input.message,
      history: input.history || [],
      race_id: input.race_id || null,
      context: input.context || {},
    }),
  });
  if (proxied && proxied instanceof Response) {
    return { ok: false, errorResponse: proxied };
  }
  if (!proxied || !proxied.ok) return null;
  const data = proxied.payload.data != null ? proxied.payload.data : proxied.payload;
  return {
    ok: true,
    response: normalizeKaobaResponse(data, input.race_id || null),
    source: "single-ai",
    provider: "python",
  };
}

/** ルールエンジン（現行）。差し替え時はこの関数参照だけを変える。 */
export function generateViaRule(input) {
  const response = ruleGenerateKaobaReply(input);
  return {
    ok: true,
    response,
    source: "mock",
    provider: "rule",
  };
}

/**
 * 唯一の公開生成入口 — ルートはこれを呼ぶ
 * @returns {Promise<{ ok: true, response, source, provider }>}
 *
 * auto / python: Python 成功時のみ python。失敗（不通・502 等）は rule へフォールバック。
 * （errorResponse をそのまま返さない — 契約レスポンスを維持）
 */
export async function adaptKaobaChat(context, body) {
  const message = String((body && body.message) || "").trim();
  const raceId = String(
    (body && (body.race_id || (body.context && body.context.bundle_ref))) || ""
  ).trim() || null;
  const history = Array.isArray(body.history) ? body.history : [];
  const contextUi = (body && body.context) || {};

  const refs = await loadKaobaRefsViaAdapters(context, raceId);
  const input = {
    message,
    history,
    race_id: raceId,
    context: contextUi,
    refs,
  };

  const mode = providerMode(context);

  if (mode === "rule") {
    return generateViaRule(input);
  }

  if (mode === "python" || mode === "auto") {
    const fromPy = await generateViaPython(context, input);
    if (fromPy && fromPy.ok) return fromPy;
    // python 不通 / Network error / 非OK → rule（auto・python 強制とも契約応答を維持）
    const fallback = generateViaRule(input);
    fallback.provider = mode === "python" ? "rule-fallback" : "rule";
    return fallback;
  }

  return generateViaRule(input);
}

export const KaobaAdapter = {
  chat: adaptKaobaChat,
  generateViaRule,
  loadRefs: loadKaobaRefsViaAdapters,
  /** 互換: 旧 generateKaobaReply 名 */
  generateKaobaReply: ruleGenerateKaobaReply,
  /** 旧 loadKaobaRefs は adapters 経由へ誘導 */
  loadKaobaRefs,
};
