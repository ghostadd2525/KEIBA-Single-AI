/**
 * UI10 — client Explain UX（Bundle 構造化データ → 4ブロック）
 * 内部数値は根拠に使い、画面には解釈文のみ出す（数値非表示）。
 * BFF の explain.ux（schema explain-ux/1.1+）があればそれを優先。無ければ再構成。
 */
(function (global) {
  "use strict";

  var BAND_JA = {
    high: "高い",
    rather_high: "やや高い",
    medium: "ふつう",
    low: "低い",
    unknown: "不明",
  };

  var PACE_ORDER_HINT =
    "左端が1着予想、右へ行くほど着順が下がります。並んだ馬番は、AIが考えるゴールまでの着順です。";

  function asNum(v) {
    if (v == null || v === "") return null;
    var n = Number(v);
    return isFinite(n) ? n : null;
  }

  function toPct(v) {
    var n = asNum(v);
    if (n == null) return null;
    if (n >= 0 && n <= 1) return Math.round(n * 1000) / 10;
    return Math.round(n * 10) / 10;
  }

  function normalizeScore(v) {
    var n = asNum(v);
    if (n == null) return null;
    return n > 1 ? n / 100 : n;
  }

  function bandFromScore(score) {
    var s = normalizeScore(score);
    if (s == null) return "unknown";
    if (s >= 0.75) return "high";
    if (s >= 0.6) return "rather_high";
    if (s >= 0.35) return "medium";
    return "low";
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function honmeiOf(bundle) {
    var runners = ((bundle && bundle.evaluation && bundle.evaluation.runners) || []);
    for (var i = 0; i < runners.length; i++) {
      if (runners[i] && runners[i].mark === "honmei") return runners[i];
    }
    return runners[0] || null;
  }

  function sortedRunners(bundle) {
    var runners = ((bundle && bundle.evaluation && bundle.evaluation.runners) || []).slice();
    return runners.sort(function (a, b) {
      return (Number(a.model_rank) || 999) - (Number(b.model_rank) || 999);
    });
  }

  function abilityMetrics(ability) {
    var a = ability && typeof ability === "object" ? ability : {};
    var history = toPct(a.history_score);
    var distance = toPct(a.distance_score);
    var styleFit = null;
    if (a.style_distance_fit_weight != null) styleFit = toPct(a.style_distance_fit_weight);
    else if (a.style_confidence != null) styleFit = toPct(a.style_confidence);
    var front = toPct(a.front_rate);
    var paceResilience = null;
    if (a.pace_collapse_risk_v2 != null) paceResilience = toPct(1 - Number(a.pace_collapse_risk_v2));
    else if (a.inside_traffic_risk != null) paceResilience = toPct(1 - Number(a.inside_traffic_risk));
    return {
      history: history,
      distance: distance,
      styleFit: styleFit,
      front: front,
      paceResilience: paceResilience,
      paceCollapse: toPct(a.pace_collapse_risk_v2),
    };
  }

  function extractSignals(bundle) {
    var info = (bundle && bundle.race_info) || {};
    var ac = (bundle && bundle.ai_confidence) || {};
    var meta = (bundle && bundle.explain && bundle.explain.meta) || {};
    var honmei = honmeiOf(bundle);
    var metrics = abilityMetrics(honmei && honmei.ability_scores);
    var runners = sortedRunners(bundle);
    var opponents = runners
      .filter(function (r) {
        return r && r !== honmei;
      })
      .slice(0, 3)
      .map(function (r) {
        return {
          horse_number: r.horse_number,
          horse_name: r.horse_name,
          win_prob: asNum(r.win_prob),
        };
      });
    var score = normalizeScore(ac.score);
    var band = ac.band && BAND_JA[ac.band] ? ac.band : bandFromScore(score);
    return {
      race_id: (bundle && bundle.race_id) || "",
      venue: info.venue || "",
      race_no: info.race_no != null ? info.race_no : info.race_number,
      race_name: info.race_name || info.class_label || "",
      field_size: asNum(info.field_size) != null ? asNum(info.field_size) : runners.length,
      honmei: honmei
        ? {
            horse_number: honmei.horse_number,
            horse_name: honmei.horse_name,
            win_prob: asNum(honmei.win_prob),
            model_rank: asNum(honmei.model_rank) || 1,
          }
        : null,
      metrics: metrics,
      opponents: opponents,
      gap12: asNum(meta.gap12),
      entropy: asNum(meta.entropy),
      top1_prob: asNum(meta.top1_prob) != null ? asNum(meta.top1_prob) : asNum(honmei && honmei.win_prob),
      race_required_pick: asNum(meta.race_required_pick),
      confidence_score: score,
      confidence_band: band,
      confidence_band_ja: BAND_JA[band] || BAND_JA.unknown,
    };
  }

  function joinSentences(parts) {
    var seen = {};
    var out = [];
    for (var i = 0; i < parts.length; i++) {
      var s = String(parts[i] || "").trim();
      if (!s || seen[s]) continue;
      seen[s] = 1;
      out.push(/。$/.test(s) ? s : s + "。");
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
    if (s.gap12 != null && s.gap12 >= 0.04 && s.top1_prob != null && s.top1_prob >= 0.18) return true;
    if (s.gap12 != null && s.gap12 >= 0.03 && s.top1_prob != null && s.top1_prob >= 0.14) return true;
    return false;
  }

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
    var m = s.metrics || {};
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
    var band = s.confidence_band;
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
    if (h.horse_number != null) return String(h.horse_number) + "番" + (h.horse_name || "");
    return h.horse_name || "本命候補";
  }

  function buildRaceSituation(s) {
    var bullets = [];
    var paras = [];
    var place =
      s.venue && s.race_no != null ? s.venue + s.race_no + "R" : s.venue || s.race_id || "このレース";
    var field = s.field_size != null ? "出走" + s.field_size + "頭の" : "";
    paras.push(
      place +
        (s.race_name ? "（" + s.race_name + "）" : "") +
        "は、" +
        field +
        "AIがレース全体の流れを見ています"
    );
    var crowd = interpretCrowd(s);
    var gap = interpretGap(s);
    var pace = interpretPace(s);
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
    return { id: "race_situation", title: "このレースの状況", paragraphs: joinSentences(paras), bullets: bullets };
  }

  function buildHonmeiReason(s) {
    var bullets = [];
    var paras = [];
    var h = s.honmei;
    if (!h) {
      return {
        id: "honmei_reason",
        title: "◎を選んだ理由",
        paragraphs: ["本命候補のデータがまだ揃っていません。"],
        bullets: [],
      };
    }
    var name = horseLabel(h);
    if (isSoloLead(s)) {
      paras.push(name + "を◎としたのは、AI評価で先頭に立ち、他馬より一歩抜けているためです");
    } else if (s.gap12 != null && s.gap12 < 0.02) {
      paras.push(name + "を◎としたのは、AI評価で1番手ですが、対抗との差は小さく接戦のためです");
    } else {
      paras.push(name + "を◎としたのは、AI評価で総合的に最もバランスが良いためです");
    }
    var m = s.metrics;
    var abilitySpecs = [
      ["能力（近走）", m.history],
      ["距離適性", m.distance],
      ["展開との相性", m.styleFit],
      ["安定性", m.paceResilience != null ? m.paceResilience : m.front],
    ];
    var scored = abilitySpecs
      .map(function (pair) {
        return { label: pair[0], v: pair[1], text: interpretAbility(pair[0], pair[1]) };
      })
      .filter(function (x) {
        return x.text;
      });
    scored.sort(function (a, b) {
      return (b.v || 0) - (a.v || 0);
    });
    scored.forEach(function (x) {
      bullets.push(x.label + ": " + x.text);
    });
    var gap = interpretGap(s);
    if (gap) paras.push(gap);
    var strong = scored.filter(function (x) {
      return x.v != null && x.v >= 70;
    });
    if (strong.length) {
      paras.push(
        "特に " +
          strong
            .map(function (x) {
              return x.label;
            })
            .join("・") +
          " が選んだ決め手になっています"
      );
    } else if (scored.length) {
      paras.push("突出した一点より、総合のバランスを優先して選んでいます");
    } else {
      paras.push("能力の細部より、AI順位の一貫性を優先して選んでいます");
    }
    return { id: "honmei_reason", title: "◎を選んだ理由", paragraphs: joinSentences(paras), bullets: bullets };
  }

  function buildBettingPoints(s) {
    var bullets = [];
    var paras = [];
    var axisName = s.honmei ? horseLabel(s.honmei) : "◎";
    var rivalCount = Math.min(3, Math.max(2, (s.opponents && s.opponents.length) || 2));
    if (isSoloLead(s)) {
      paras.push(
        axisName +
          "がやや抜けて見えるので、今回は" +
          axisName +
          "を中心に考え、相手は" +
          rivalCount +
          "頭ほどに絞ると買いやすいです"
      );
      bullets.push("中心: " + axisName + " / 相手の目安: " + rivalCount + "頭前後");
    } else if (isChaotic(s)) {
      paras.push(
        "どの馬が勝ってもおかしくないほどの混戦寄りです。今回は" +
          axisName +
          "を中心に考えつつ、相手は広めに" +
          Math.min(4, rivalCount + 1) +
          "頭ほど残すと取りこぼしを減らせます"
      );
      bullets.push("中心: " + axisName + " / 相手は広めに残す");
    } else {
      paras.push(
        "1頭だけが大きく抜けているレースではありません。ただ、どの馬が勝ってもおかしくないほどの大混戦でもありません"
      );
      paras.push(
        "今回は" +
          axisName +
          "を中心に考え、相手は" +
          rivalCount +
          "頭ほど選ぶとバランスよく買えます"
      );
      bullets.push("中心: " + axisName + " / 相手の目安: " + rivalCount + "頭前後");
    }
    if (s.opponents.length) {
      var names = s.opponents
        .map(function (o) {
          return (
            (o.horse_number != null ? o.horse_number + "番" : "") + (o.horse_name || "")
          ).trim();
        })
        .filter(Boolean);
      if (names.length) {
        bullets.push("相手候補の例: " + names.join("、"));
        paras.push(
          "相手には " + names.slice(0, 2).join("、") + " あたりを入れておくと整理しやすいです"
        );
      }
    }
    if (s.race_required_pick != null && s.race_required_pick >= 2) {
      bullets.push("注意: 上位以外にも数頭は意識した方がよい条件です");
    }
    var conf = interpretConfidence(s);
    bullets.push(conf);
    return { id: "betting_points", title: "買うときのポイント", paragraphs: joinSentences(paras), bullets: bullets };
  }

  function buildOverallView(s) {
    var bullets = [];
    var paras = [];
    paras.push(interpretConfidence(s));
    if (s.honmei) {
      var n = horseLabel(s.honmei);
      if (isChaotic(s)) {
        paras.push("まとめ: まず " + n + " を中心に考え、相手は広めに残して組み立てましょう");
      } else if (isSoloLead(s)) {
        paras.push("まとめ: まず " + n + " を中心に考え、相手は2〜3頭ほどに絞ると買いやすいです");
      } else {
        paras.push("まとめ: まず " + n + " を中心に考え、相手は2〜3頭ほど選ぶとバランスよく買えます");
      }
    }
    var confPct = s.confidence_score != null ? Math.round(s.confidence_score * 100) : null;
    if (isChaotic(s) && (confPct == null || confPct < 60)) {
      paras.push("波乱も十分考えられるレースです。少点数より券種を分ける方が向きます");
    } else if (isSoloLead(s) && confPct != null && confPct >= 55) {
      paras.push("軸の信頼は取りやすい一方、オッズの妙味は別問題です");
    } else {
      paras.push("予想の参考にはなりますが、最終判断はオッズと枠順を見てからが安全です");
    }
    var crowd = interpretCrowd(s);
    var gap = interpretGap(s);
    if (gap) bullets.push(gap);
    if (crowd) bullets.push(crowd);
    if (s.field_size != null) {
      if (s.field_size >= 16) bullets.push("多頭数で波乱が広がりやすいレースです");
      else if (s.field_size <= 10) bullets.push("頭数が少なめで整理しやすいレースです");
      else bullets.push("頭数は標準的な規模です");
    }
    return { id: "overall_view", title: "レース全体の見立て", paragraphs: joinSentences(paras), bullets: bullets };
  }

  function fingerprintBlocks(blocks) {
    var raw = blocks
      .map(function (b) {
        return b.id + "|" + (b.paragraphs || []).join("") + "|" + (b.bullets || []).join("");
      })
      .join("||");
    var h = 0;
    for (var i = 0; i < raw.length; i++) h = (h * 31 + raw.charCodeAt(i)) >>> 0;
    return "ux10_" + h.toString(16);
  }

  function dedupeAcrossBlocks(blocks) {
    var seen = {};
    return blocks.map(function (b) {
      var paragraphs = [];
      (b.paragraphs || []).forEach(function (p) {
        if (seen[p]) return;
        seen[p] = 1;
        paragraphs.push(p);
      });
      var bullets = [];
      (b.bullets || []).forEach(function (x) {
        if (seen[x]) return;
        seen[x] = 1;
        bullets.push(x);
      });
      return { id: b.id, title: b.title, paragraphs: paragraphs, bullets: bullets };
    });
  }

  function compose(bundle) {
    var s = extractSignals(bundle || {});
    var blocks = dedupeAcrossBlocks([
      buildRaceSituation(s),
      buildHonmeiReason(s),
      buildBettingPoints(s),
      buildOverallView(s),
    ]);
    return {
      schema_version: "explain-ux/1.1",
      blocks: blocks,
      fingerprint: fingerprintBlocks(blocks),
    };
  }

  function isInterpretOnlySchema(ver) {
    var v = String(ver || "");
    // 1.1+ = 解釈文のみ（数値非表示）。旧 1.0 はクライアントで再構成する
    return /^explain-ux\/1\.(1|[2-9]|\d{2,})/.test(v) || /^explain-ux\/[2-9]/.test(v);
  }

  function resolveUx(bundle) {
    var ex = (bundle && bundle.explain) || {};
    if (
      ex.ux &&
      Array.isArray(ex.ux.blocks) &&
      ex.ux.blocks.length &&
      isInterpretOnlySchema(ex.ux.schema_version)
    ) {
      return {
        schema_version: ex.ux.schema_version || "explain-ux/1.1",
        blocks: ex.ux.blocks,
        fingerprint: ex.ux.fingerprint || fingerprintBlocks(ex.ux.blocks),
      };
    }
    return compose(bundle);
  }

  function blocksHtml(ux, ctaHtml) {
    if (!ux || !ux.blocks || !ux.blocks.length) {
      return '<p class="muted">解説データを生成できませんでした</p>';
    }
    var html = '<div class="explain-ux" data-fingerprint="' + escapeHtml(ux.fingerprint || "") + '">';
    ux.blocks.forEach(function (b) {
      html += '<article class="explain-ux-block" data-block="' + escapeHtml(b.id || "") + '">';
      html += "<h3>" + escapeHtml(b.title || "") + "</h3>";
      (b.paragraphs || []).forEach(function (p) {
        html += '<p class="explain-ux-p">' + escapeHtml(p) + "</p>";
      });
      if (b.bullets && b.bullets.length) {
        html += '<ul class="explain-ux-list">';
        b.bullets.forEach(function (x) {
          html += "<li>" + escapeHtml(x) + "</li>";
        });
        html += "</ul>";
      }
      html += "</article>";
    });
    if (ctaHtml) html += ctaHtml;
    html += "</div>";
    return html;
  }

  function applyPaceOrderHint() {
    var paceHint =
      document.querySelector(".pace-card > p.pace-card-hint") ||
      document.querySelector(".pace-card > p");
    if (!paceHint) return;
    paceHint.className = "pace-card-hint muted";
    paceHint.textContent = PACE_ORDER_HINT;
  }

  function applyToDom(bundle, opts) {
    opts = opts || {};
    var mount =
      document.getElementById("explainUxBody") ||
      document.getElementById("reasonsSectionBody");
    if (!mount) return null;
    var ux = resolveUx(bundle);
    var cta = "";
    if (opts.ctaHtml != null) {
      cta = opts.ctaHtml;
    } else if (
      global.ExpectPredictionBind &&
      ExpectPredictionBind.explainKaobaCtaHtml
    ) {
      cta = ExpectPredictionBind.explainKaobaCtaHtml({
        explain: (bundle && bundle.explain) || {},
        race_id: (bundle && bundle.race_id) || "",
        bundle: bundle,
      });
    }
    mount.innerHTML = blocksHtml(ux, cta);
    applyPaceOrderHint();
    return ux;
  }

  global.ExpectExplainUx = {
    compose: compose,
    resolve: resolveUx,
    blocksHtml: blocksHtml,
    applyToDom: applyToDom,
    PACE_ORDER_HINT: PACE_ORDER_HINT,
  };
})(window);
