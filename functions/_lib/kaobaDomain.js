/**
 * KaobaService ドメイン（ルールベース Concierge）
 *
 * Phase6: ルートからの差し替え入口は adapters/kaobaAdapter.js。
 * generateKaobaReply は rule プロバイダ実装として残す。
 *
 * Explain UX: 質問意図ごとに異なる観点で返答（explainConversationComposer）。
 * 内部用語（ステージ等）はユーザー向け reply に出さない。
 */

import { normalizePredictionBundle, scorePercent, toAnalysisDomain } from "./domain.js";
import { loadAssetJson } from "./aiProxy.js";
import {
  canExplainPick,
  formatExplainPickReply,
  isExplainPickIntent,
  projectExplainForPick,
} from "./explainPick.js";
import {
  classifyExplainChatIntent,
  composeExplainConversationReply,
  EXPLAIN_HELP_REPLY,
  CONSULT_ROOM_CHAT_REDIRECT,
} from "./explainConversationComposer.js";

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
  const mode = String(ctx.mode || input.mode || "").toLowerCase();
  const isExplain =
    mode === "explain" ||
    mode === "explain_pick" ||
    ctx.type === "honmei_reason" ||
    ctx.type === "explain_pick";

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
  const isConsult = hasStrategy || mode === "review";
  let suggestions = isConsult
    ? ["この買い方どう？", "見送るべき？", "初心者なら？"]
    : ["なぜ本命？", "不安材料は？", "穴馬は？"];
  let explainPick = null;
  let explainIntent = null;

  // Explain / 相談: 意図別にレース固有の解釈文を返す
  const chatIntent = classifyExplainChatIntent(message, {
    isExplainMode: isExplain || isConsult,
  });
  const wantsExplainChat =
    isExplain ||
    isConsult ||
    (chatIntent !== "general" && chatIntent !== "unknown" && chatIntent !== "casual") ||
    isExplainPickIntent(message) ||
    /本命|◎|対抗|穴|買い方|不安|理由|なぜ|少額|雨|オッズ|見送|初心/.test(message);

  if ((isExplain || isConsult) && (chatIntent === "unknown" || chatIntent === "casual")) {
    const composed = composeExplainConversationReply({
      message,
      bundle,
      isExplainMode: isExplain,
      isConsultMode: isConsult && !isExplain,
    });
    reply = (composed && composed.reply) || (isConsult ? CONSULT_ROOM_CHAT_REDIRECT : EXPLAIN_HELP_REPLY);
    suggestions = (composed && composed.suggestions) || suggestions;
    emotion = "fun";
    explainIntent = chatIntent;
  } else if ((bundle || isExplain || isConsult) && wantsExplainChat) {
    const composed = composeExplainConversationReply({
      message,
      bundle,
      isExplainMode: isExplain,
      isConsultMode: isConsult && !isExplain,
    });
    if (composed && composed.reply) {
      reply = composed.reply;
      suggestions = composed.suggestions || suggestions;
      emotion =
        composed.intent === "risks" ||
        composed.intent === "unknown" ||
        composed.intent === "casual"
          ? "fun"
          : "joy";
      explainIntent = composed.intent;
      if (
        !isConsult &&
        composed.intent === "why_honmei" &&
        bundle &&
        canExplainPick({ ...input, message: "なぜ本命？" })
      ) {
        explainPick = projectExplainForPick(bundle.explain);
      }
    }
  }

  if (!reply && isConsult) {
    reply = CONSULT_ROOM_CHAT_REDIRECT;
    emotion = "joy";
    suggestions = ["この買い方どう？", "見送るべき？", "初心者なら？"];
  } else if (!reply && /展開|ペース/.test(message)) {
    if (narrative) {
      reply = narrative;
    } else if (bundle) {
      const composed = composeExplainConversationReply({
        message: "なぜ本命？",
        bundle,
        isExplainMode: true,
      });
      reply =
        (composed && composed.reply) ||
        "展開はレース画面のAI解説もあわせて見てね。ペース想定が外れると位置取りが変わりやすいよ。";
    } else {
      reply = "展開はデータが揃ってから具体的に話すね。ペース想定が外れると位置取りが変わりやすいよ。";
    }
    emotion = "fun";
    if (charts) reply += `\n評価の目安: ${charts}`;
    suggestions = ["なぜ本命？", "不安材料は？", "穴馬は？"];
  } else if (!reply && /血統/.test(message)) {
    const ped = ((analysis && analysis.charts) || []).find((c) => c.key === "pedigree");
    if (ped) {
      reply = `血統適性は ${ped.value} 点くらいのイメージだよ。コース適性が効いてる産駒に注目してみて。`;
    } else {
      reply = "血統面ではコース適性が高い産駒が目立ってるよ。";
    }
    emotion = "fun";
    suggestions = ["なぜ本命？", "穴馬は？", "不安材料は？"];
  } else if (!reply && /本命|信頼度|おすすめ/.test(message) && h) {
    reply = `本命は ${h.horse_number}番 ${h.horse_name || ""}`.trim();
    if (conf != null) reply += "（自信の目安あり）";
    reply += "。くわしい理由は「なぜ本命？」で聞いてね。";
    if (place) reply = `${place} についてね。` + reply;
    emotion = "joy";
    suggestions = ["なぜ本命？", "2番との差は？", "不安材料は？"];
  } else if (!reply && (bundle || analysis)) {
    if (isConsult) {
      reply = CONSULT_ROOM_CHAT_REDIRECT;
      suggestions = ["この買い方どう？", "見送るべき？", "初心者なら？"];
    } else if (h) {
      reply = `本命目線は ${h.horse_number}番${h.horse_name ? " " + h.horse_name : ""}`;
      reply += "。理由・差・不安・穴のどれを深掘りする？";
      suggestions = ["なぜ本命？", "不安材料は？", "穴馬は？"];
    } else {
      reply =
        "気になるところを教えてね。「なぜ本命？」「不安材料は？」「穴馬は？」だと答えやすいよ。";
      suggestions = ["なぜ本命？", "不安材料は？", "穴馬は？"];
    }
    emotion = "joy";
  } else if (!reply) {
    reply = isConsult
      ? CONSULT_ROOM_CHAT_REDIRECT
      : "レースを指定してもらえると、予想データに沿ってもっと具体的に答えられるよ。";
    emotion = "joy";
    suggestions = isConsult
      ? ["この買い方どう？", "見送るべき？", "初心者なら？"]
      : ["なぜ本命？", "不安材料は？", "穴馬は？"];
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
  if (explainPick) {
    out.explain_pick = explainPick;
    out.intent = "explain_pick";
  } else if (explainIntent) {
    out.intent = explainIntent;
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
  classifyExplainChatIntent,
  composeExplainConversationReply,
};
