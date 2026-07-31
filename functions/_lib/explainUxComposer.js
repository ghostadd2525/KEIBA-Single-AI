/**
 * UI10 — Explain UX Composer
 *
 * 固定の長文テンプレは使わない。
 * Bundle 上の数値・AbilityScores・展開系メタ・自信度から事実句を選び、
 * 内部数値は根拠に使い、画面には解釈文のみ出す（LLM なし・数値非表示）。
 *
 * @typedef {{ id: string, title: string, paragraphs: string[], bullets: string[] }} ExplainUxBlock
 */

import { confidenceBandFromScore } from "./confidenceBands.js";

const BAND_JA = {
  high: "高い",
  rather_high: "やや高い",
  medium: "ふつう",
  low: "低い",
  unknown: "不明",
};

function asNum(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function toPct(v) {
  const n = asNum(v);
  if (n == null) return null;
  if (n >= 0 && n <= 1) return Math.round(n * 1000) / 10;
  return Math.round(n * 10) / 10;
}

function pctLabel(v) {
  const p = toPct(v);
  return p == null ? null : `${p}%`;
}

function normalizeScore(v) {
  const n = asNum(v);
  if (n == null) return null;
  return n > 1 ? n / 100 : n;
}

function honmeiOf(bundle) {
  const runners = Array.isArray(bundle?.evaluation?.runners)
    ? bundle.evaluation.runners
    : [];
  return runners.find((r) => r && r.mark === "honmei") || runners[0] || null;
}

function sortedRunners(bundle) {
  const runners = Array.isArray(bundle?.evaluation?.runners)
    ? bundle.evaluation.runners.slice()
    : [];
  return runners.sort(
    (a, b) => (Number(a.model_rank) || 999) - (Number(b.model_rank) || 999)
  );
}

function abilityMetrics(ability) {
  const a = ability && typeof ability === "object" ? ability : {};
  const history = toPct(a.history_score);
  const distance = toPct(a.distance_score);
  let styleFit = null;
  if (a.style_distance_fit_weight != null) styleFit = toPct(a.style_distance_fit_weight);
  else if (a.style_confidence != null) styleFit = toPct(a.style_confidence);
  const front = toPct(a.front_rate);
  let paceResilience = null;
  if (a.pace_collapse_risk_v2 != null) {
    paceResilience = toPct(1 - Number(a.pace_collapse_risk_v2));
  } else if (a.inside_traffic_risk != null) {
    paceResilience = toPct(1 - Number(a.inside_traffic_risk));
  }
  const paceCollapse = toPct(a.pace_collapse_risk_v2);
  return { history, distance, styleFit, front, paceResilience, paceCollapse };
}

/**
 * Bundle → 信号抽出（文章生成の入力）
 */
export function extractExplainSignals(bundle) {
  const info = bundle?.race_info || {};
  const ev = bundle?.evaluation || {};
  const ac = bundle?.ai_confidence || {};
  const meta = (bundle?.explain && bundle.explain.meta) || {};
  const honmei = honmeiOf(bundle);
  const ability = honmei?.ability_scores || {};
  const metrics = abilityMetrics(ability);
  const runners = sortedRunners(bundle);
  const opponents = runners
    .filter((r) => r && r !== honmei)
    .slice(0, 3)
    .map((r) => ({
      horse_number: r.horse_number,
      horse_name: r.horse_name,
      win_prob: asNum(r.win_prob),
      model_rank: asNum(r.model_rank),
    }));

  const score = normalizeScore(ac.score);
  const band =
    ac.band && BAND_JA[ac.band]
      ? ac.band
      : score != null
        ? confidenceBandFromScore(score)
        : "unknown";

  return {
    race_id: bundle?.race_id || "",
    venue: info.venue || "",
    race_no: info.race_no ?? info.race_number ?? null,
    race_name: info.race_name || info.class_label || "",
    field_size: asNum(info.field_size) ?? runners.length,
    surface: info.surface || null,
    distance: asNum(info.distance),
    world: ev.world || null,
    sub_world: ev.sub_world || null,
    honmei: honmei
      ? {
          horse_number: honmei.horse_number,
          horse_name: honmei.horse_name,
          win_prob: asNum(honmei.win_prob),
          model_rank: asNum(honmei.model_rank) || 1,
        }
      : null,
    metrics,
    opponents,
    gap12: asNum(meta.gap12),
    entropy: asNum(meta.entropy),
    top1_prob: asNum(meta.top1_prob) ?? asNum(honmei?.win_prob),
    top2_sum: asNum(meta.top2_sum),
    race_required_pick: asNum(meta.race_required_pick),
    spread_need_score: asNum(meta.spread_need_score),
    spread_need_label: meta.spread_need_label || null,
    race_type_label: meta.race_type_label || meta.causal_race_type || null,
    confidence_score: score,
    confidence_band: band,
    confidence_band_ja: BAND_JA[band] || BAND_JA.unknown,
  };
}

function joinSentences(parts) {
  const seen = new Set();
  const out = [];
  for (const raw of parts) {
    const s = String(raw || "").trim();
    if (!s) continue;
    if (seen.has(s)) continue;
    seen.add(s);
    out.push(s.endsWith("。") ? s : `${s}。`);
  }
  return out;
}

function isChaotic(s) {
  if (s.entropy != null && s.entropy >= 2.35) return true;
  if (s.gap12 != null && s.gap12 < 0.02) return true;
  if (s.field_size != null && s.field_size >= 16 && (s.gap12 == null || s.gap12 < 0.03)) {
    return true;
  }
  return false;
}

function isSoloLead(s) {
  if (s.gap12 != null && s.gap12 >= 0.04 && s.top1_prob != null && s.top1_prob >= 0.18) {
    return true;
  }
  if (s.gap12 != null && s.gap12 >= 0.03 && s.top1_prob != null && s.top1_prob >= 0.14) {
    return true;
  }
  return false;
}

/** 内部指標 → ユーザー向け解釈（数値は出さない） */
function interpretCrowd(s) {
  if (s.entropy == null) return null;
  if (s.entropy >= 2.5) return "勝ち筋が分散しやすく、波乱も十分考えられるレースです";
  if (s.entropy >= 2.2) return "上位は接戦で順位が入れ替わる可能性があります";
  return "上位がまとまりやすく、本命寄りに流れやすい構図です";
}

function interpretGap(s) {
  if (s.gap12 == null) return null;
  if (s.gap12 >= 0.04) return "◎がやや抜けています";
  if (s.gap12 >= 0.02) return "◎と対抗の差はありますが、詰め寄れる範囲です";
  return "◎と対抗はほぼ同じくらいの力に見えます";
}

function interpretPace(s) {
  const m = s.metrics || {};
  if (m.paceCollapse != null) {
    if (m.paceCollapse >= 40) return "ペースが乱れると展開が荒れやすいタイプです";
    if (m.paceCollapse >= 20) return "ペースは標準的で、極端な荒れ方はしにくいです";
    return "ペースは落ち着きやすく、先行有利の流れも意識しやすいです";
  }
  if (m.front != null) {
    if (m.front >= 70) return "本命側は先行しやすい脚質寄りです";
    if (m.front >= 40) return "本命側の位置取りは中団〜先行のあいだです";
    return "本命側は後方から運ぶ可能性があります";
  }
  return null;
}

function interpretAbility(label, score) {
  if (score == null) return null;
  if (label === "能力（近走）") {
    if (score >= 70) return "近走の内容がしっかりしています";
    if (score >= 45) return "近走は平均的で、大きなマイナスはありません";
    return "近走だけを見るとやや物足りない面があります";
  }
  if (label === "距離適性") {
    if (score >= 70) return "この距離との相性が良いです";
    if (score >= 45) return "距離適性は平均的です";
    return "距離面ではやや不安が残ります";
  }
  if (label === "展開との相性") {
    if (score >= 70) return "想定される展開との相性が良いです";
    if (score >= 45) return "展開との相性はまずまずです";
    return "展開が噛み合わないと苦しくなりやすいです";
  }
  if (label === "安定性") {
    if (score >= 70) return "崩れにくく、安定して走れるタイプです";
    if (score >= 45) return "安定感は平均的です";
    return "展開次第でブレやすい面があります";
  }
  return null;
}

function interpretConfidence(s) {
  const band = s.confidence_band;
  if (band === "high")
    return "AIはこのレースの本命をかなり信頼しています。それでも無理な増額はせず、普段どおりの金額で組み立てましょう";
  if (band === "rather_high")
    return "AIはこのレースの本命を比較的信頼しています。普段どおりの金額で組み立てるのがおすすめです";
  if (band === "medium")
    return "AIの自信は中くらいなので、大きく勝負するより普段どおりの金額で楽しむのがおすすめです";
  if (band === "low")
    return "AIの自信は控えめで、普段より少し控えめの金額で楽しむのがおすすめです";
  return "AIの自信度はまだはっきりしていません。無理のない金額で組み立てましょう";
}

function horseLabel(h) {
  if (!h) return "本命候補";
  if (h.horse_number != null) return `${h.horse_number}番${h.horse_name || ""}`.trim();
  return h.horse_name || "本命候補";
}

/** 1. このレースの状況 */
function buildRaceSituation(s) {
  const bullets = [];
  const paras = [];

  const place =
    s.venue && s.race_no != null
      ? `${s.venue}${s.race_no}R`
      : s.venue || s.race_id || "このレース";
  const field =
    s.field_size != null ? `出走${s.field_size}頭の` : "";
  paras.push(
    `${place}${s.race_name ? `（${s.race_name}）` : ""}は、${field}AIがレース全体の流れを見ています`
  );

  const crowd = interpretCrowd(s);
  const gap = interpretGap(s);
  const pace = interpretPace(s);
  if (crowd) bullets.push(crowd);
  if (gap) bullets.push(gap);
  if (pace) bullets.push(pace);

  if (isChaotic(s)) {
    paras.push("全体として混戦寄りで、1頭に決め打ちしすぎると取りこぼしやすい構図です");
  } else if (isSoloLead(s)) {
    paras.push("全体として本命が浮きやすく、軸を作りやすい構図です");
  } else {
    paras.push("上位争いはあるものの、極端な荒レースとまでは言えない構図です");
  }

  return {
    id: "race_situation",
    title: "このレースの状況",
    paragraphs: joinSentences(paras),
    bullets,
  };
}

/** 2. ◎を選んだ理由 */
function buildHonmeiReason(s) {
  const bullets = [];
  const paras = [];
  const h = s.honmei;
  if (!h) {
    return {
      id: "honmei_reason",
      title: "◎を選んだ理由",
      paragraphs: ["本命候補のデータがまだ揃っていません。"],
      bullets: [],
    };
  }

  const name = horseLabel(h);
  if (isSoloLead(s)) {
    paras.push(`${name}を◎としたのは、AI評価で先頭に立ち、他馬より一歩抜けているためです`);
  } else if (s.gap12 != null && s.gap12 < 0.02) {
    paras.push(`${name}を◎としたのは、AI評価で1番手ですが、対抗との差は小さく接戦のためです`);
  } else {
    paras.push(`${name}を◎としたのは、AI評価で総合的に最もバランスが良いためです`);
  }

  const m = s.metrics;
  const abilitySpecs = [
    ["能力（近走）", m.history],
    ["距離適性", m.distance],
    ["展開との相性", m.styleFit],
    ["安定性", m.paceResilience != null ? m.paceResilience : m.front],
  ];
  const scored = abilitySpecs
    .map(([label, v]) => ({ label, v, text: interpretAbility(label, v) }))
    .filter((x) => x.text);
  scored.sort((a, b) => (b.v || 0) - (a.v || 0));
  scored.forEach((x) => bullets.push(`${x.label}: ${x.text}`));

  const gap = interpretGap(s);
  if (gap) paras.push(gap);

  const strong = scored.filter((x) => x.v != null && x.v >= 70);
  if (strong.length) {
    paras.push(`特に ${strong.map((x) => x.label).join("・")} が選んだ決め手になっています`);
  } else if (scored.length) {
    paras.push("突出した一点より、総合のバランスを優先して選んでいます");
  } else {
    paras.push("能力の細部より、AI順位の一貫性を優先して選んでいます");
  }

  return {
    id: "honmei_reason",
    title: "◎を選んだ理由",
    paragraphs: joinSentences(paras),
    bullets,
  };
}

/** 3. 買うときのポイント */
function buildBettingPoints(s) {
  const bullets = [];
  const paras = [];
  const axisName = s.honmei ? horseLabel(s.honmei) : "◎";
  const rivalCount = Math.min(3, Math.max(2, (s.opponents && s.opponents.length) || 2));

  if (isSoloLead(s)) {
    paras.push(
      `${axisName}がやや抜けて見えるので、今回は${axisName}を中心に考え、相手は${rivalCount}頭ほどに絞ると買いやすいです`
    );
    bullets.push(`中心: ${axisName} / 相手の目安: ${rivalCount}頭前後`);
  } else if (isChaotic(s)) {
    paras.push(
      `どの馬が勝ってもおかしくないほどの混戦寄りです。今回は${axisName}を中心に考えつつ、相手は広めに${Math.min(4, rivalCount + 1)}頭ほど残すと取りこぼしを減らせます`
    );
    bullets.push(`中心: ${axisName} / 相手は広めに残す`);
  } else {
    paras.push(
      "1頭だけが大きく抜けているレースではありません。ただ、どの馬が勝ってもおかしくないほどの大混戦でもありません"
    );
    paras.push(
      `今回は${axisName}を中心に考え、相手は${rivalCount}頭ほど選ぶとバランスよく買えます`
    );
    bullets.push(`中心: ${axisName} / 相手の目安: ${rivalCount}頭前後`);
  }

  if (s.opponents.length) {
    const names = s.opponents
      .map((o) =>
        `${o.horse_number != null ? o.horse_number + "番" : ""}${o.horse_name || ""}`.trim()
      )
      .filter(Boolean);
    if (names.length) {
      bullets.push(`相手候補の例: ${names.join("、")}`);
      paras.push(
        `相手には ${names.slice(0, 2).join("、")} あたりを入れておくと整理しやすいです`
      );
    }
  }

  if (s.race_required_pick != null && s.race_required_pick >= 2) {
    bullets.push("注意: 上位以外にも数頭は意識した方がよい条件です");
  }

  bullets.push(interpretConfidence(s));

  return {
    id: "betting_points",
    title: "買うときのポイント",
    paragraphs: joinSentences(paras),
    bullets,
  };
}

/** 4. レース全体の見立て */
function buildOverallView(s) {
  const bullets = [];
  const paras = [];

  paras.push(interpretConfidence(s));

  if (s.honmei) {
    const n = horseLabel(s.honmei);
    if (isChaotic(s)) {
      paras.push(
        `まとめ: まず ${n} を中心に考え、相手は広めに残して組み立てましょう`
      );
    } else if (isSoloLead(s)) {
      paras.push(
        `まとめ: まず ${n} を中心に考え、相手は2〜3頭ほどに絞ると買いやすいです`
      );
    } else {
      paras.push(
        `まとめ: まず ${n} を中心に考え、相手は2〜3頭ほど選ぶとバランスよく買えます`
      );
    }
  }

  const confPct =
    s.confidence_score != null ? Math.round(s.confidence_score * 100) : null;
  if (isChaotic(s) && (confPct == null || confPct < 60)) {
    paras.push("波乱も十分考えられるレースです。少点数より券種を分ける方が向きます");
  } else if (isSoloLead(s) && confPct != null && confPct >= 55) {
    paras.push("軸の信頼は取りやすい一方、オッズの妙味は別問題です");
  } else {
    paras.push("予想の参考にはなりますが、最終判断はオッズと枠順を見てからが安全です");
  }

  const crowd = interpretCrowd(s);
  const gap = interpretGap(s);
  if (gap) bullets.push(gap);
  if (crowd) bullets.push(crowd);
  if (s.field_size != null) {
    if (s.field_size >= 16) bullets.push("多頭数で波乱が広がりやすいレースです");
    else if (s.field_size <= 10) bullets.push("頭数が少なめで整理しやすいレースです");
    else bullets.push("頭数は標準的な規模です");
  }

  return {
    id: "overall_view",
    title: "レース全体の見立て",
    paragraphs: joinSentences(paras),
    bullets,
  };
}

function fingerprintBlocks(blocks) {
  const raw = blocks
    .map((b) => `${b.id}|${(b.paragraphs || []).join("")}|${(b.bullets || []).join("")}`)
    .join("||");
  let h = 0;
  for (let i = 0; i < raw.length; i++) h = (h * 31 + raw.charCodeAt(i)) >>> 0;
  return `ux10_${h.toString(16)}`;
}

/** ブロック間で同一文が連続しないよう削る */
function dedupeAcrossBlocks(blocks) {
  const seen = new Set();
  return blocks.map((b) => {
    const paragraphs = [];
    for (const p of b.paragraphs || []) {
      if (seen.has(p)) continue;
      seen.add(p);
      paragraphs.push(p);
    }
    const bullets = [];
    for (const x of b.bullets || []) {
      if (seen.has(x)) continue;
      seen.add(x);
      bullets.push(x);
    }
    return { ...b, paragraphs, bullets };
  });
}

/**
 * @param {Record<string, unknown>} bundle
 * @returns {{
 *   schema_version: string,
 *   blocks: ExplainUxBlock[],
 *   fingerprint: string,
 *   signals: object
 * }}
 */
export function composeExplainUx(bundle) {
  const signals = extractExplainSignals(bundle || {});
  let blocks = [
    buildRaceSituation(signals),
    buildHonmeiReason(signals),
    buildBettingPoints(signals),
    buildOverallView(signals),
  ];
  blocks = dedupeAcrossBlocks(blocks);
  return {
    schema_version: "explain-ux/1.1",
    blocks,
    fingerprint: fingerprintBlocks(blocks),
    signals: {
      race_id: signals.race_id,
      gap12: signals.gap12,
      entropy: signals.entropy,
      confidence_score: signals.confidence_score,
      confidence_band: signals.confidence_band,
      honmei: signals.honmei,
    },
  };
}

/** Bundle.explain.narrative 互換用（4ブロック要約・旧テンプレ禁止） */
export function narrativeFromExplainUx(ux) {
  if (!ux || !Array.isArray(ux.blocks)) return "";
  const lines = [];
  for (const b of ux.blocks) {
    if (b.paragraphs && b.paragraphs[0]) lines.push(b.paragraphs[0]);
  }
  return lines.join(" ");
}
