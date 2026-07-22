/**
 * KaobaService ドメイン（ルールベース Concierge）
 *
 * Phase6: ルートからの差し替え入口は adapters/kaobaAdapter.js。
 * generateKaobaReply は rule プロバイダ実装として残す。
 * LLM/Python へは KaobaAdapter.chat（または generateViaPython）を使う。
 *
 * Phase 3 Explainability: explain_pick → explain 2.1 注入（v2_explain）
 */

import { normalizePredictionBundle, scorePercent, toAnalysisDomain } from "./domain.js";
import { loadAssetJson } from "./aiProxy.js";
import {
  canExplainPick,
  formatExplainPickReply,
  isExplainPickIntent,
  projectExplainForPick,
} from "./explainPick.js";

export const KAOBA_SCHEMA = "expect-kaoba/1.0";

/**
 * race_id があるときだけ PredictionBundle + Analysis を読む（契約は変更しない）
 */
export async function loadKaobaRefs(context, raceId) {
  if (!raceId) {
    return { race_id: null, bundle: null, analysis: null };
  }

  let bundle = await loadAssetJson(context, `/data/mocks/bundle-${raceId}.json`);
  if (!bundle) {
    bundle = await loadAssetJson(context, "/data/mocks/bundle-20260719_hanshin_11.json");
  }
  const normalized = bundle ? normalizePredictionBundle(bundle, raceId) : null;

  const all = await loadAssetJson(context, "/data/mocks/analysis.json");
  const row = (all && all[raceId]) || null;
  const analysis = toAnalysisDomain(
    row || {
      race_id: raceId,
      charts: [],
      overall: null,
      narrative: "",
    },
    raceId
  );

  return {
    race_id: raceId,
    bundle: normalized,
    analysis,
  };
}

function honmei(bundle) {
  const runners = (bundle && bundle.evaluation && bundle.evaluation.runners) || [];
  return runners.find((r) => r.mark === "honmei") || runners[0] || null;
}

function chartSummary(analysis) {
  if (!analysis || !Array.isArray(analysis.charts) || !analysis.charts.length) return "";
  return analysis.charts
    .slice(0, 5)
    .map((c) => `${c.label || c.key}${c.value != null ? c.value : "—"}`)
    .join(" / ");
}

/**
 * ルールベース応答。LLM 差し替え時はこの関数を置き換えるか、先頭で provider 分岐する。
 * @returns {import('../../contracts/expect-kaoba/1.0/Kaoba').KaobaChatResponse}
 */
export function generateKaobaReply(input) {
  const message = String((input && input.message) || "").trim();
  const ctx = (input && input.context) || {};
  const refs = (input && input.refs) || {};
  const bundle = refs.bundle || null;
  const analysis = refs.analysis || null;
  const raceId = refs.race_id || input.race_id || null;
  const hasStrategy = ctx.ui === "strategy" || ctx.type === "strategy_review";

  const info = (bundle && bundle.race_info) || {};
  const h = honmei(bundle);
  const conf = bundle ? scorePercent(bundle.ai_confidence) : null;
  const place =
    (info.venue || "") + (info.race_no != null ? ` ${info.race_no}R` : "");
  const charts = chartSummary(analysis);
  const narrative =
    (bundle && bundle.explain && bundle.explain.narrative) ||
    (analysis && analysis.narrative) ||
    "";

  let reply;
  let emotion = "fun";
  let suggestions = ["展開を詳しく", "本命を教えて", "買い目を整理"];
  let explainPick = null;

  // Phase 3: v2_explain ON + explain_pick + explain.reason → 構造化理由を注入
  if (canExplainPick(input)) {
    const projection = projectExplainForPick(bundle.explain);
    const formatted = formatExplainPickReply(projection, { place });
    if (formatted) {
      reply = formatted;
      emotion = "joy";
      suggestions = ["信頼度の根拠は？", "買い目を提案して", "展開を詳しく"];
      explainPick = projection;
    }
  }

  if (!reply && hasStrategy) {
    reply =
      "戦略データ受け取ったよ！軸は明確にして、点数を抑えめがおすすめ。主軸→保険→一発の順で入れてね。";
    emotion = "joy";
    suggestions = ["点数を抑える案", "軸を見直す", "リスクを教えて"];
    if (h) {
      reply += `\n軸候補の目安は ${h.horse_number}番 ${h.horse_name || ""}`.trim() + "。";
    }
  } else if (!reply && /買い目|戦略/.test(message)) {
    reply = "買い目は軸1頭流しで点数を抑えるのがおすすめ！相手は最大3頭までにしてみよう。";
    emotion = "joy";
    if (h && conf != null) {
      reply += `\nいまの本命目線は ${h.horse_number}番（AI信頼度 ${conf}%）だよ。`;
    }
    suggestions = ["展開予想を教えて", "リスクを教えて", "血統について教えて"];
  } else if (!reply && /展開|ペース/.test(message)) {
    if (narrative) {
      reply = narrative;
    } else {
      reply = "データ上は差し馬の評価が伸びてるよ。中盤でペースが上がる想定だね。";
    }
    emotion = "fun";
    if (charts) reply += `\n評価の目安: ${charts}`;
    suggestions = ["本命を教えて", "買い目を提案して", "血統について教えて"];
  } else if (!reply && /血統/.test(message)) {
    const ped = ((analysis && analysis.charts) || []).find((c) => c.key === "pedigree");
    if (ped) {
      reply = `血統適性は ${ped.value} 点くらいのイメージだよ。コース適性が効いてる産駒に注目してみて。`;
    } else {
      reply = "血統面ではコース適性が高い産駒が目立ってるよ。";
    }
    emotion = "fun";
    suggestions = ["展開予想を教えて", "本命を教えて", "買い目を提案して"];
  } else if (!reply && /本命|信頼度|おすすめ/.test(message) && h) {
    reply = `本命は ${h.horse_number}番 ${h.horse_name || ""}`.trim();
    if (conf != null) reply += `（AI信頼度 ${conf}%）`;
    reply += "。根拠は上位確率の分離と総合評価だよ。";
    if (place) reply = `${place} についてね。` + reply;
    emotion = "joy";
    suggestions = ["なぜ◎なの？", "展開を詳しく", "買い目を提案して"];
  } else if (!reply && (bundle || analysis)) {
    reply = "いい質問！";
    if (place) reply += `${place} を見ているよ。`;
    if (h) {
      reply += `本命目線は ${h.horse_number}番${h.horse_name ? " " + h.horse_name : ""}`;
      if (conf != null) reply += `（信頼度 ${conf}%）`;
      reply += "。";
    } else {
      reply += "いまのところ本命評価に大きな変動はないよ。";
    }
    if (narrative) reply += `\n${narrative}`;
    emotion = "joy";
    if (isExplainPickIntent(message) && !(bundle && bundle.explain && bundle.explain.reason)) {
      suggestions = ["本命を教えて", "買い目を提案して", "展開を詳しく"];
    }
  } else if (!reply) {
    reply =
      "いい質問！レースを指定してもらえると、予想データに沿ってもっと具体的に答えられるよ。";
    emotion = "joy";
    suggestions = ["展開予想を教えて", "血統について教えて", "買い目を提案して"];
  }

  const out = {
    schema_version: KAOBA_SCHEMA,
    reply,
    suggestions,
    emotion,
    referenced_race_id: raceId || null,
    provider: "rule",
    live2d: {
      motion: emotion === "joy" ? "talk_happy" : "talk_idle",
      expression: emotion === "joy" ? "smile" : "neutral",
    },
  };
  // additive（契約 additionalProperties: true）— Flag OFF 経路では付与しない
  if (explainPick) {
    out.explain_pick = explainPick;
    out.intent = "explain_pick";
  }
  return out;
}

export function normalizeKaobaResponse(raw, raceId) {
  const data = raw && typeof raw === "object" ? raw : {};
  const out = {
    schema_version: KAOBA_SCHEMA,
    reply:
      typeof data.reply === "string" && data.reply
        ? data.reply
        : "うまく答えられなかったみたい。",
    suggestions: Array.isArray(data.suggestions) ? data.suggestions : [],
    emotion: data.emotion || "neutral",
    referenced_race_id:
      data.referenced_race_id != null
        ? data.referenced_race_id
        : data.race_id != null
          ? data.race_id
          : raceId || null,
    provider: data.provider || "mock",
    live2d: data.live2d || undefined,
  };
  if (data.explain_pick && typeof data.explain_pick === "object") {
    out.explain_pick = data.explain_pick;
  }
  if (typeof data.intent === "string") {
    out.intent = data.intent;
  }
  return out;
}

export {
  canExplainPick,
  isExplainPickIntent,
  projectExplainForPick,
  formatExplainPickReply,
};
