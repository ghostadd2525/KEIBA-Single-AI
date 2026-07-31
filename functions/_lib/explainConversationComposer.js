/**
 * KAOBA Explain Conversation Composer
 *
 * 回答は必ず 結論 → 理由 → 補足 の3段。
 * 実名: Bundle に horse_name があるときは必ず明示（例: 3番シェーンリヒト）。
 * 「この馬」「このレース」は取得できないときの最終フォールバックのみ。
 * 「本命馬」「Prediction」「対象馬」など内部語は使わない。
 * Prediction / 印 / 順位 / スコアは変更しない（会話文のみ）。
 */

import { extractExplainSignals } from "./explainUxComposer.js";

/** @typedef {'why_honmei'|'gap_vs_rival'|'risks'|'betting'|'upset'|'casual'|'unknown'|'general'|'weather'|'odds'|'budget'|'skip'|'beginner'} ExplainChatIntent */

export const EXPLAIN_HELP_REPLY =
  "ごめんね、ちょっと質問の内容が分からなかったよ😅\nレースについてなら何でも聞いてね。";

export const EXPLAIN_CASUAL_GUIDE =
  "雑談したいときは通常のKAOBAチャットでも話せるよ😊";

export const EXPLAIN_SUGGESTIONS = [
  "なぜ本命？",
  "2番との差は？",
  "不安材料は？",
  "穴馬は？",
];

/**
 * @param {string} message
 * @returns {boolean}
 */
export function isExplainCasualMessage(message) {
  const m = String(message || "").trim();
  if (!m) return false;
  if (
    /こんにちは|こんばんは|おはよう|おはようございます|やあ|はじめまして|hello|hi\b|ハロー/i.test(
      m
    )
  ) {
    return true;
  }
  if (/疲れた|つかれた|お疲れ|おつかれ|眠い|ねむい|元気|調子|気分/.test(m)) return true;
  if (/暑い|寒い|天気|雨|晴れ|雪/.test(m)) return true;
  if (/ありがとう|どうも|サンキュ|すき|好き|かわいい|可愛い/.test(m)) return true;
  if (/暇|つまらない|どうしてる|何してる|しゃべ|雑談|おしゃべり/.test(m)) return true;
  return false;
}

/**
 * @param {string} message
 * @param {{ isExplainMode?: boolean }} [opts]
 * @returns {ExplainChatIntent}
 */
export function classifyExplainChatIntent(message, opts = {}) {
  const m = String(message || "").trim();
  if (!m) return "unknown";
  // レース相談の天候・オッズ・少額は雑談より優先
  if (/雨なら|雨だと|雨の|重馬場|不良馬場|馬場.*悪|天候/.test(m)) return "weather";
  if (/オッズ/.test(m)) return "odds";
  if (/少額|予算/.test(m)) return "budget";
  if (/見送|パスする|買わない|休むべき/.test(m)) return "skip";
  if (/初心者|初めて|入門|わかりやすく/.test(m)) return "beginner";
  if (/この買い|買い方どう|戦略どう|どう思う/.test(m)) return "betting";
  if (opts.isExplainMode && isExplainCasualMessage(m)) return "casual";
  if (/差|対抗|2番|二番|比較|違い|どれくらい|どのくらい離れ/.test(m)) return "gap_vs_rival";
  if (/不安|リスク|危険|弱点|心配|崩れ|取れない|厳しい/.test(m)) return "risks";
  if (/買い方|買い目|どう買う|券種|点数|流し|ワイド|馬連|三連/.test(m)) return "betting";
  if (/穴馬|穴候補|大穴|波乱馬|穴は|一発/.test(m)) return "upset";
  if (/なぜ|理由|根拠|どうして|なぜ本命|本命.*教|◎|選定/.test(m)) return "why_honmei";
  if (opts.isExplainMode) return "unknown";
  return "general";
}

/**
 * 実馬名を優先。番号のみ・不明は null（呼び出し側で「この馬」最終 FB）。
 * 途中から読んでも分かるよう、名前があるときは毎回名前を含める。
 */
function horseLabel(h) {
  if (!h) return null;
  const name = String(h.horse_name || "").trim();
  const num = h.horse_number != null && h.horse_number !== "" ? h.horse_number : null;
  if (name) {
    return num != null ? `${num}番${name}` : name;
  }
  if (num != null) return `${num}番`;
  return null;
}

/** 会場+R を優先。「このレース」は最終フォールバックのみ。 */
function racePlace(s) {
  if (!s) return "このレース";
  if (s.venue && s.race_no != null) return `${s.venue}${s.race_no}R`;
  if (s.venue) return String(s.venue);
  if (s.race_id) return String(s.race_id);
  return "このレース";
}

function rivalOf(signals) {
  return (signals.opponents || [])[0] || null;
}

function anaCandidates(bundle) {
  const runners = Array.isArray(bundle?.evaluation?.runners)
    ? bundle.evaluation.runners.slice()
    : [];
  const marked = runners.filter((r) => r && (r.mark === "ana" || r.mark === "upset"));
  if (marked.length) return marked.slice(0, 2);
  const sorted = runners
    .slice()
    .sort((a, b) => (Number(a.model_rank) || 999) - (Number(b.model_rank) || 999));
  return sorted.slice(2, 4).filter(Boolean);
}

function joinReply(parts) {
  return parts
    .filter(Boolean)
    .map((p) => String(p).trim())
    .filter(Boolean)
    .join("\n");
}

/** Bundle 馬名があれば実名（例: 3番シェーンリヒト）。無いときだけ「この馬」 */
function focusHorse(s) {
  return horseLabel(s && s.honmei) || "この馬";
}

/** 補足用の馬名（番号なし）。無ければ focusHorse */
function focusHorseBare(s) {
  const bare = String((s && s.honmei && s.honmei.horse_name) || "").trim();
  return bare || focusHorse(s);
}

/** 理由文を1段落にまとめる */
function mergeReason(lines, fallback) {
  const xs = (lines || []).filter(Boolean).map((x) => String(x).trim()).filter(Boolean);
  if (!xs.length) return fallback;
  if (xs.length === 1) return xs[0];
  const head = stripYoEnding(xs[0]);
  return `${head}し、${xs[1]}`;
}

function stripYoEnding(s) {
  return String(s || "")
    .trim()
    .replace(/[。．]\s*$/, "")
    .replace(/だよ$/, "")
    .replace(/よ$/, "");
}

/** 結論 → 理由 → 補足（この3段だけ） */
function composeExplain(conclusion, reason, supplement) {
  return joinReply([conclusion, reason, supplement]);
}

/**
 * Bundle 信号 → 情景ベースの根拠カード
 * @returns {{ kind: string, strength: number, why: string|null, gap: string|null, risk: string|null }[]}
 */
function collectEvidence(s) {
  const m = s.metrics || {};
  const items = [];
  const name = focusHorse(s);

  if (s.venue || s.surface) {
    const course =
      s.venue && s.surface
        ? `${s.venue}の${s.surface}`
        : s.venue
          ? `${s.venue}`
          : `${s.surface}`;
    items.push({
      kind: "course",
      strength: 55,
      why: `${course}らしい流れになりやすく、そこで運べる馬が残るイメージだよ`,
      gap: `${course}では、どの位置から直線に入れるかの差が出やすいよ`,
      risk: `${course}で想定と違う流れになると、直線まで脚が持たなくなりやすいよ`,
    });
    if (s.venue) {
      items.push({
        kind: "course_flow",
        strength: 52,
        why: `${s.venue}では序盤の位置取りが、その後の流れを決めやすいよ`,
        gap: `${s.venue}では、取りたい位置を取れたかどうかで差が開きやすいよ`,
        risk: `${s.venue}で想定外の先行争いになると、後半に息が上がりやすいよ`,
      });
    }
  }

  if (s.distance != null) {
    let distWhy = null;
    let distRisk = null;
    let distGap = null;
    if (s.distance <= 1400) {
      distWhy = `短い距離なので、出して好位に付けた馬が最後まで残りやすいよ`;
      distRisk = `出遅れると、追い上げる間もなく終わってしまいやすいよ`;
      distGap = `短い距離では、序盤に前へ行けた側が残りやすいよ`;
    } else if (s.distance <= 1800) {
      distWhy = `道中の運びと、最後の直線での伸びの両方が効きやすい距離だよ`;
      distRisk = `ペースを誤ると、最後の直線で勢いが落ちやすいよ`;
      distGap = `${s.distance}mでは、直線でどれだけ脚を使えるかの差が出やすいよ`;
    } else {
      distWhy = `長い距離なので、後半まで脚を使える馬が残りやすいよ`;
      distRisk = `後半につかれてしまうと、直線で差されやすくなるよ`;
      distGap = `長い距離では、後半に脚が残るかどうかで差が出やすいよ`;
    }
    items.push({
      kind: "distance",
      strength: 60,
      why: distWhy,
      gap: distGap,
      risk: distRisk,
    });
  }

  if (m.distance != null) {
    if (m.distance >= 70) {
      items.push({
        kind: "distance_fit",
        strength: 85,
        why:
          s.distance != null
            ? `今回の${s.distance}mでも、${name} は最後まで脚が残りやすいタイプだよ`
            : `${name} は今回の距離でも、最後まで脚が残りやすいタイプだよ`,
        gap: `距離の向きでは、${name} の方が直線まで楽に運べそうだよ`,
        risk: null,
      });
    } else if (m.distance < 45) {
      items.push({
        kind: "distance_fit",
        strength: 30,
        why: null,
        gap: "距離の向きでは、どちらも決め手になりにくいよ",
        risk:
          s.distance != null
            ? `今回の${s.distance}mは ${name} の得意と言えず、後半につかれると崩れやすいよ`
            : `${name} にとって今回の距離は得意と言えず、後半につかれると崩れやすいよ`,
      });
    }
  }

  if (m.front != null) {
    if (m.front >= 70) {
      items.push({
        kind: "style",
        strength: 80,
        why: `${name} は前めの位置から押していける形が合いやすいよ`,
        gap: `前で運べるかどうかで、${name} の方が楽に見えるよ`,
        risk: `${name} は前に行けないと、得意な形を作れず苦しくなりやすいよ`,
      });
    } else if (m.front >= 40) {
      items.push({
        kind: "style",
        strength: 65,
        why: `${name} は中団あたりで様子を見ながら運べるタイプだよ`,
        gap: "中団の取り合いになると、位置取りの差が出やすいよ",
        risk: `${name} は中団が詰まると、進路を失って直線で伸びきれないよ`,
      });
    } else {
      items.push({
        kind: "style",
        strength: 50,
        why: `${name} は後ろから差してくる形が合いやすいよ`,
        gap: `差せる展開かどうかで、${name} と対抗の見え方が変わるよ`,
        risk: `${name} は前が止まらない展開だと、差せないまま終わりやすいよ`,
      });
    }
  }

  if (m.paceCollapse != null) {
    if (m.paceCollapse >= 40) {
      items.push({
        kind: "pace",
        strength: 45,
        why: null,
        gap: "前半が速くなりやすく、粘れる馬と苦しくなる馬で差が出やすいよ",
        risk: `${name} は前半の流れが速くなると、直線で息が上がって差されやすいよ`,
      });
    } else if (m.paceCollapse < 20) {
      items.push({
        kind: "pace",
        strength: 75,
        why: "落ち着いた流れになりやすく、前で運んだ馬が粘りやすいよ",
        gap: "落ち着いた流れなら、前で運べる側が差を広げやすいよ",
        risk: `${name} は想定より速い流れになると、粘れず崩れやすいよ`,
      });
    } else {
      items.push({
        kind: "pace",
        strength: 55,
        why: "極端な流れにはなりにくく、標準的な運びになりやすいよ",
        gap: "標準的な流れでは、細かい位置取りの差が残りやすいよ",
        risk: `${name} はペース配分を誤ると、直線で勢いが落ちやすいよ`,
      });
    }
  }

  if (m.history != null) {
    if (m.history >= 70) {
      items.push({
        kind: "ability",
        strength: 82,
        why: `${name} は近走もしっかり走れていて、今回も同じ水準を出せそうだよ`,
        gap: `近走の内容では、${name} の方が安定して見えやすいよ`,
        risk: null,
      });
    } else if (m.history < 45) {
      items.push({
        kind: "ability",
        strength: 35,
        why: null,
        gap: "近走だけだと、差がはっきりしないよ",
        risk: `${name} は近走が波打っているので、同じ走りが出ないと崩れやすいよ`,
      });
    } else {
      items.push({
        kind: "ability",
        strength: 58,
        why: `${name} の近走はまずまずで、大きなマイナスは目立たないよ`,
        gap: "近走だけでは、差が小さいよ",
        risk: null,
      });
    }
  }

  if (m.paceResilience != null) {
    if (m.paceResilience >= 70) {
      items.push({
        kind: "stability",
        strength: 78,
        why: `${name} は流れが多少乱れても、最後まで形を崩しにくいよ`,
        gap: `流れが少し荒れても、${name} の方が粘りやすいよ`,
        risk: null,
      });
    } else if (m.paceResilience < 45) {
      items.push({
        kind: "stability",
        strength: 32,
        why: null,
        gap: "流れが乱れたときの粘りでは、差が開きにくいよ",
        risk: `${name} は流れが乱れると、最後の直線で勢いが落ちやすいよ`,
      });
    }
  }

  if (m.styleFit != null) {
    if (m.styleFit >= 70) {
      items.push({
        kind: "style_fit",
        strength: 76,
        why: `${name} は想定している流れとの相性が良いよ`,
        gap: `流れとの相性では、${name} の方が有利に見えやすいよ`,
        risk: null,
      });
    } else if (m.styleFit < 45) {
      items.push({
        kind: "style_fit",
        strength: 34,
        why: null,
        gap: null,
        risk: `${name} は想定と違う流れになると、一気に苦しくなりやすいよ`,
      });
    }
  }

  if (s.field_size != null) {
    if (s.field_size >= 15) {
      items.push({
        kind: "field",
        strength: 50,
        why: null,
        gap: `出走${s.field_size}頭と多く、馬群の中で差が埋もれやすいよ`,
        risk: `出走${s.field_size}頭だと馬群に包まれ、進路が取れないと崩れやすいよ`,
      });
    } else if (s.field_size <= 10) {
      items.push({
        kind: "field",
        strength: 62,
        why: `出走${s.field_size}頭と少なめで、実力差が出やすい並びだよ`,
        gap: "少頭数なので、2頭の差が着順に出やすいよ",
        risk: null,
      });
    }
  }

  return items;
}

function pickEvidence(items, mode, n) {
  const scored = items
    .map((it) => {
      const text = it[mode];
      if (!text) return null;
      let score = it.strength;
      if (mode === "risk") score = 100 - it.strength;
      if (mode === "gap") score = Math.abs(it.strength - 50) + it.strength * 0.3;
      return { ...it, text, score };
    })
    .filter(Boolean);
  scored.sort((a, b) => b.score - a.score);
  const out = [];
  const kinds = new Set();
  for (const it of scored) {
    if (kinds.has(it.kind)) continue;
    kinds.add(it.kind);
    out.push(it.text);
    if (out.length >= n) break;
  }
  return out;
}

/**
 * なぜ◎？ — 結論 → 理由 → 補足
 */
function buildWhy(s) {
  const name = focusHorse(s);
  const bare = focusHorseBare(s);
  const evidence = collectEvidence(s);
  const reasons = pickEvidence(evidence, "why", 2);
  const reason = reasons.length
    ? `近走内容・距離・展開の相性をまとめて見ると、${bare}が一番安定して走れそうだったよ。`
    : "近走内容・距離・展開の相性をまとめて見ると、一番安定して走れそうだったよ。";
  return composeExplain(
    `${name}を◎にした一番の理由は、今回の条件なら一番力を発揮しやすいと判断したからだよ。`,
    reason,
    `だから今回は${bare}を中心に考えているよ。`
  );
}

/**
 * 2番との差 — 結論 → 理由 → 補足
 */
function buildGap(s) {
  const name = focusHorse(s);
  const bare = focusHorseBare(s);
  const rival = rivalOf(s);
  const rName = horseLabel(rival) || "2番手";
  const evidence = collectEvidence(s);
  const dims = pickEvidence(evidence, "gap", 2);
  const top = dims[0] || "位置取りと、直線での伸び方の差が出やすいよ";
  const reason = mergeReason(dims.length ? dims.slice(0, 2) : [top], top);

  let conclusion;
  let supplement;
  if (s.gap12 != null && s.gap12 >= 0.04) {
    conclusion = `${name}と${rName}を比べると、${top}`;
    supplement = `だから今回は${bare}を一歩前に見ているよ。`;
  } else if (s.gap12 != null && s.gap12 < 0.02) {
    conclusion = `${rName}も強いけど、${name}との差は小さいよ。`;
    supplement = "入れ替わる余地は残るので、差は薄いと見ていいよ。";
  } else {
    conclusion = `2番の${rName}も強いけど、今回は${name}側の位置取りを評価したよ。`;
    supplement = `差はあるけど詰められる範囲で、中心は${bare}だよ。`;
  }

  return composeExplain(conclusion, reason, supplement);
}

/**
 * 不安材料 — 結論 → 理由 → 補足
 */
function buildRisks(s) {
  const name = focusHorse(s);
  const bare = focusHorseBare(s);
  const evidence = collectEvidence(s);
  const risks = pickEvidence(evidence, "risk", 2);
  const reasonLines = risks.length
    ? risks
    : [
        "想定と違うペースになると、位置を取れず苦しくなりやすいよ",
        "前が止まらない展開だと、狙った形を作れないよ",
      ];
  const top = reasonLines[0];
  const reason = mergeReason(
    reasonLines.slice(0, 2),
    "想定と違う流れになると、力を出しにくくなりやすいよ。"
  );
  return composeExplain(
    `${name}で一番心配なのは、${stripYoEnding(top)}ことだよ。`,
    reason,
    `もしその流れになると、${bare}も力を出しにくくなるよ。`
  );
}

/**
 * 穴馬 — 結論 → 理由 → 補足
 */
function buildUpset(s, bundle) {
  const ana = anaCandidates(bundle);
  const tips = ana.map((r) => horseLabel(r)).filter(Boolean);
  const tipBare = ana
    .map((r) => String((r && r.horse_name) || "").trim())
    .filter(Boolean);
  const evidence = collectEvidence(s);
  const m = s.metrics || {};

  const upsetBits = [];
  if (s.entropy != null && s.entropy >= 2.2) {
    upsetBits.push("上位が接戦なので、人気薄が一気に上がりやすい並びだよ");
  }
  if (m.paceCollapse != null && m.paceCollapse >= 40) {
    upsetBits.push("前半が速くなると、前の人気馬より後ろからの馬が残りやすいよ");
  }
  if (s.field_size != null && s.field_size >= 15) {
    upsetBits.push(`出走${s.field_size}頭と多く、伏兵が紛れやすいよ`);
  }
  if (s.distance != null) {
    upsetBits.push(
      s.distance <= 1400
        ? "短い距離では、序盤の位置取り次第で人気薄が残ることがあるよ"
        : `${s.distance}mが合う人気薄は、直線で伸びてくることがあるよ`
    );
  }
  if (!upsetBits.length) {
    pickEvidence(evidence, "gap", 2).forEach((g) => upsetBits.push(g));
  }

  let conclusion;
  if (tips.length >= 2) {
    conclusion = `穴候補として見たいのは${tips[0]}と${tips[1]}だよ。`;
  } else if (tips.length === 1) {
    conclusion = `穴候補として見たいのは${tips[0]}だよ。`;
  } else {
    conclusion = "穴を探すなら、上位以外で今回の距離・流れが合う馬だよ。";
  }

  const reason = mergeReason(
    upsetBits.slice(0, 2),
    "今回の流れに合いそうな人気薄を拾ったよ。"
  );
  const tipName = tipBare[0] || tips[0];
  const supplement = tipName
    ? `だから${tipName}は相手の端に残しておきたいよ。`
    : `${racePlace(s)}では、条件が合う人気薄を端に置いておく感じだよ。`;

  return composeExplain(conclusion, reason, supplement);
}

function buildSkipConsult() {
  return composeExplain(
    "迷うなら、無理に大きく買わず見送り寄りでいいよ。",
    "自信が薄いときは総額を抑えるか、主軸だけ少額にするのが無難。",
    "今日の調子に合わせて、無理しない立ち回りを優先しよう。"
  );
}

function buildBeginnerConsult(s) {
  const name = s ? focusHorse(s) : "中心の馬";
  return composeExplain(
    "初心者なら、主軸（馬連・ワイド）を少点数で買うのがおすすめだよ。",
    "保険や一発は後回しにして、総額も普段どおりに抑えよう。",
    `軸の ${name} を中心に、相手は広げすぎないのが安心。`
  );
}

function buildBettingConsult(s) {
  const name = s ? focusHorse(s) : "中心の馬";
  return composeExplain(
    `この買い方なら、${name}を中心に進めて大丈夫だと思うよ。`,
    "大きく崩すより、点数と総額を守るほうが安心だよ。",
    "少額・見送り・雨・オッズの話も、気になるところから聞いてね。"
  );
}

function buildBudgetConsult(s) {
  const name = s ? focusHorse(s) : "中心の馬";
  return composeExplain(
    "少額なら、主軸（馬連・ワイド）に寄せるのがおすすめだよ。",
    "保険や一発は後回しにして、総額を普段どおりに抑えよう。",
    `軸の ${name} 中心はそのままで大丈夫。`
  );
}

function buildWeatherConsult() {
  return composeExplain(
    "雨なら、前が残るか崩れやすいかが変わりやすいよ。",
    "軸は変えず、相手を1頭増減して様子を見るのが無難。",
    "馬場発表を見てから最終判断しよう。"
  );
}

function buildOddsConsult() {
  return composeExplain(
    "オッズが動いても、軸をすぐ変えないのがおすすめだよ。",
    "人気が急に集まった相手は点数を少し抑えめに。",
    "総額の上限は守ったまま調整しよう。"
  );
}

function buildBettingRedirect() {
  return buildBettingConsult(null);
}

function buildCasual(message) {
  const m = String(message || "").trim();
  let soft = "うん、聞いてるよ。";
  if (/おはよう/.test(m)) soft = "おはよう！";
  else if (/こんばんは/.test(m)) soft = "こんばんは！";
  else if (/こんにちは|はじめまして|hello|hi\b|やあ|ハロー/i.test(m)) soft = "こんにちは！";
  else if (/疲れた|つかれた|お疲れ|おつかれ|眠い|ねむい/.test(m)) soft = "お疲れさま。少し休んでね。";
  else if (/暑い/.test(m)) soft = "だよね、暑いね。";
  else if (/寒い/.test(m)) soft = "だよね、寒いね。";
  else if (/ありがとう|サンキュ|どうも/.test(m)) soft = "どういたしまして。";
  else if (/元気|調子|気分/.test(m)) soft = "聞いてくれてありがとう。";
  return joinReply([
    soft,
    EXPLAIN_CASUAL_GUIDE,
    "レースについて気になることがあれば、何でも聞いてね。",
  ]);
}

function buildUnknown() {
  return EXPLAIN_HELP_REPLY;
}

function buildGeneral(s) {
  const name = focusHorse(s);
  const bare = focusHorseBare(s);
  const place = racePlace(s);
  return composeExplain(
    `${place}では◎の${name}を中心に見ているよ。`,
    `${bare}の走り方と、今回の距離・展開の相性が良さそうに見えるよ。`,
    "知りたい内容に合わせて、「なぜ本命？」「2番との差は？」「不安材料は？」「穴馬は？」のどれかで聞いてね。"
  );
}

export const CONSULT_CHIP_SUGGESTIONS = [
  "この買い方どう？",
  "見送るべき？",
  "初心者なら？",
];

export const CONSULT_EXPLAIN_REDIRECT =
  "その内容は「予想の説明」で確認できるよ。\n馬の理由や差・不安・穴の話はそちらが向いているよ。\nここでは買い方や立ち回りの相談を続けよう。";

export const CONSULT_ROOM_CHAT_REDIRECT =
  "その話ならルームチャットで話そう😊\nここではレースや買い方の相談を中心に案内しているよ。";

export const CONSULT_GREETING_TAIL =
  "レースや買い方について気になることがあれば、一緒に考えるよ。";

/**
 * @param {string} message
 * @returns {boolean}
 */
export function isConsultGreeting(message) {
  const text = String(message || "").trim();
  if (!text) return false;
  if (/買い|資金|少額|予算|見送|雨|馬場|オッズ|初心|戦略|立ち回|点数|◎|本命|穴馬|不安/.test(text)) {
    return false;
  }
  if (/こんにちは|こんばんは|おはよう|おはようございます|やあ|はじめまして|hello|hi\b|ハロー/i.test(text)) {
    return true;
  }
  if (/お疲れ|おつかれ|ありがとう|どうも|サンキュ/.test(text)) return true;
  return false;
}

/**
 * @param {string} message
 * @returns {string}
 */
export function buildConsultGreetingReply(message) {
  const text = String(message || "").trim();
  let soft = "こんにちは😊";
  if (/ありがとう|どうも|サンキュ/.test(text)) soft = "どういたしまして😊";
  else if (/お疲れ|おつかれ/.test(text)) soft = "お疲れさま😊";
  else if (/おはよう/.test(text)) soft = "おはよう😊";
  else if (/こんばんは/.test(text)) soft = "こんばんは😊";
  else if (/hello|hi\b|ハロー/i.test(text)) soft = "Hello😊";
  return soft + "\n" + CONSULT_GREETING_TAIL;
}

/**
 * 相談AIルーティング（実装で強制）
 * ① greeting → ② explain_redirect → ③ strategy:* → ④ room_chat_redirect
 * @param {string} message
 * @returns {string}
 */
export function classifyConsultRoute(message) {
  const text = String(message || "").trim();
  if (!text) return "room_chat_redirect";

  // 意味を持たない短い英数字・記号のみ
  if (/^[a-zA-Z0-9]{1,12}$/.test(text)) return "room_chat_redirect";
  if (/^[.．。…・\-_=+*]{1,12}$/.test(text)) return "room_chat_redirect";

  // ① Greeting（ルーム誘導しない）
  if (isConsultGreeting(text)) return "greeting";

  // ② Explain質問
  if (/なぜ|◎|本命.*理由|2番との差|対抗との差|不安材料|穴馬|穴候補|穴は[？?]/.test(text)) {
    return "explain_redirect";
  }

  const intent = classifyExplainChatIntent(text, { isExplainMode: true });
  if (intent === "why_honmei" || intent === "gap_vs_rival" || intent === "upset") {
    return "explain_redirect";
  }
  if (intent === "risks" && /不安材料|弱点|心配な点/.test(text)) {
    return "explain_redirect";
  }

  // ③ Strategy相談
  if (
    intent === "weather" ||
    intent === "odds" ||
    intent === "budget" ||
    intent === "skip" ||
    intent === "beginner" ||
    intent === "betting"
  ) {
    return "strategy:" + intent;
  }
  if (intent === "risks") return "strategy:risks";
  if (/買い|資金|少額|予算|見送|雨|馬場|オッズ|初心|戦略|立ち回|点数|券種|ワイド|馬連|三連|どう思う/.test(text)) {
    return "strategy:betting";
  }

  // ④ 雑談・意味不明・競馬無関係
  return "room_chat_redirect";
}
/**
 * @param {{ message?: string, bundle?: object, isExplainMode?: boolean, isConsultMode?: boolean }} input
 * @returns {{ intent: ExplainChatIntent|string, reply: string, suggestions: string[], route?: string } | null}
 */
export function composeExplainConversationReply(input) {
  const message = String((input && input.message) || "").trim();
  const bundle = (input && input.bundle) || null;
  const isExplainMode = !!(input && input.isExplainMode);
  const isConsultMode = !!(input && input.isConsultMode);
  const consultChips = CONSULT_CHIP_SUGGESTIONS.slice();

  if (isConsultMode) {
    const route = classifyConsultRoute(message);
    if (route === "greeting") {
      return {
        intent: "greeting",
        reply: buildConsultGreetingReply(message),
        suggestions: consultChips,
        route,
      };
    }
    if (route === "explain_redirect") {
      return {
        intent: "explain_redirect",
        reply: CONSULT_EXPLAIN_REDIRECT,
        suggestions: consultChips,
        route,
      };
    }
    if (route === "room_chat_redirect") {
      return {
        intent: "room_chat_redirect",
        reply: CONSULT_ROOM_CHAT_REDIRECT,
        suggestions: consultChips,
        route,
      };
    }

    const signals = bundle ? extractExplainSignals(bundle) : null;
    const sub = route.startsWith("strategy:") ? route.slice("strategy:".length) : "betting";
    if (sub === "weather") {
      return { intent: sub, reply: buildWeatherConsult(), suggestions: consultChips, route };
    }
    if (sub === "odds") {
      return { intent: sub, reply: buildOddsConsult(), suggestions: consultChips, route };
    }
    if (sub === "skip") {
      return { intent: sub, reply: buildSkipConsult(), suggestions: consultChips, route };
    }
    if (sub === "beginner") {
      return { intent: sub, reply: buildBeginnerConsult(signals), suggestions: consultChips, route };
    }
    if (sub === "budget") {
      return { intent: sub, reply: buildBudgetConsult(signals), suggestions: consultChips, route };
    }
    if (sub === "risks") {
      return {
        intent: sub,
        reply: composeExplain(
          "展開が想定と違うと、着順は動きやすいよ。",
          "だから大きく勝負するより、普段どおりの金額が安心。",
          "迷うなら点数を減らすか、見送り寄りでもいいよ。"
        ),
        suggestions: consultChips,
        route,
      };
    }
    return {
      intent: "betting",
      reply: buildBettingConsult(signals),
      suggestions: consultChips,
      route,
    };
  }

  const intent = classifyExplainChatIntent(message, { isExplainMode });

  if (intent === "casual") {
    return {
      intent: "casual",
      reply: buildCasual(message),
      suggestions: EXPLAIN_SUGGESTIONS.slice(),
    };
  }
  if (intent === "unknown") {
    return {
      intent: "unknown",
      reply: buildUnknown(),
      suggestions: EXPLAIN_SUGGESTIONS.slice(),
    };
  }
  if (intent === "weather") {
    return {
      intent: "weather",
      reply: buildWeatherConsult(),
      suggestions: consultChips,
    };
  }
  if (intent === "odds") {
    return {
      intent: "odds",
      reply: buildOddsConsult(),
      suggestions: consultChips,
    };
  }
  if (intent === "skip") {
    return {
      intent: "skip",
      reply: buildSkipConsult(),
      suggestions: consultChips,
    };
  }

  const signals = bundle ? extractExplainSignals(bundle) : null;

  if (intent === "beginner") {
    return {
      intent: "beginner",
      reply: buildBeginnerConsult(signals),
      suggestions: consultChips,
    };
  }
  if (intent === "betting") {
    return {
      intent: "betting",
      reply: buildBettingConsult(signals),
      suggestions: consultChips,
    };
  }
  if (intent === "budget") {
    return {
      intent: "budget",
      reply: buildBudgetConsult(signals),
      suggestions: consultChips,
    };
  }
  if (!bundle) return null;

  if (!signals.honmei && intent !== "upset" && intent !== "general") {
    const placeHint = racePlace(signals);
    return {
      intent,
      reply:
        placeHint !== "このレース"
          ? `${placeHint}の予想データがまだ揃っていないみたい。レース画面の予想が表示されてから、もう一度聞いてね。`
          : "予想データがまだ揃っていないみたい。レース画面の予想が表示されてから、もう一度聞いてね。",
      suggestions: EXPLAIN_SUGGESTIONS.slice(),
    };
  }

  let reply;
  let suggestions = EXPLAIN_SUGGESTIONS.slice();
  switch (intent) {
    case "gap_vs_rival":
      reply = buildGap(signals);
      suggestions = ["なぜ本命？", "不安材料は？", "穴馬は？"];
      break;
    case "risks":
      reply = buildRisks(signals);
      suggestions = ["なぜ本命？", "2番との差は？", "穴馬は？"];
      break;
    case "upset":
      reply = buildUpset(signals, bundle);
      suggestions = ["なぜ本命？", "不安材料は？", "2番との差は？"];
      break;
    case "why_honmei":
      reply = buildWhy(signals);
      suggestions = ["2番との差は？", "不安材料は？", "穴馬は？"];
      break;
    default:
      reply = buildGeneral(signals);
  }

  return { intent, reply, suggestions };
}
