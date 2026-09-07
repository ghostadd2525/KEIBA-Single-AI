/**
 * ExpectStrategyComposer — 買い目戦略専用の説明文生成
 *
 * AI解説（narrative）の流用はしない。
 * Race Context + AI評価シグナルから、立ち回り / リスク / 配分理由を生成する。
 * Prediction・印・順位・資金配分の数値ロジックは変更しない（説明のみ）。
 */
(function (global) {
  "use strict";

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

  function horseLabel(h) {
    if (!h) return "中心馬";
    var name = String(h.horse_name || "").trim();
    var num = h.horse_number != null && h.horse_number !== "" ? h.horse_number : null;
    if (name) return num != null ? num + "番" + name : name;
    if (num != null) return num + "番";
    return "中心馬";
  }

  function honmeiOf(bundle) {
    var runners = ((bundle && bundle.evaluation && bundle.evaluation.runners) || []);
    for (var i = 0; i < runners.length; i++) {
      if (runners[i] && runners[i].mark === "honmei") return runners[i];
    }
    return runners[0] || null;
  }

  function sortedRunners(bundle) {
    return ((bundle && bundle.evaluation && bundle.evaluation.runners) || [])
      .slice()
      .sort(function (a, b) {
        return (Number(a.model_rank) || 999) - (Number(b.model_rank) || 999);
      });
  }

  function abilityMetrics(ability) {
    var a = ability && typeof ability === "object" ? ability : {};
    return {
      history: toPct(a.history_score),
      distance: toPct(a.distance_score),
      styleFit:
        a.style_distance_fit_weight != null
          ? toPct(a.style_distance_fit_weight)
          : toPct(a.style_confidence),
      front: toPct(a.front_rate),
      paceCollapse: toPct(a.pace_collapse_risk_v2),
      paceResilience:
        a.pace_collapse_risk_v2 != null
          ? toPct(1 - Number(a.pace_collapse_risk_v2))
          : null,
    };
  }

  /**
   * Bundle → Race Context / AI 評価シグナル
   */
  function extractSignals(bundle) {
    var info = (bundle && bundle.race_info) || {};
    var ac = (bundle && bundle.ai_confidence) || {};
    var meta = (bundle && bundle.explain && bundle.explain.meta) || {};
    var honmei = honmeiOf(bundle);
    var runners = sortedRunners(bundle);
    var metrics = abilityMetrics(honmei && honmei.ability_scores);
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
    var band = ac.band || bandFromScore(score);
    return {
      race_id: (bundle && bundle.race_id) || "",
      venue: info.venue || "",
      race_no: info.race_no != null ? info.race_no : info.race_number,
      race_name: info.race_name || info.class_label || "",
      field_size:
        asNum(info.field_size) != null ? asNum(info.field_size) : runners.length || null,
      surface: info.surface || info.track_type || "",
      distance: asNum(info.distance),
      going: info.going || info.track_condition || "",
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
      top1_prob:
        asNum(meta.top1_prob) != null ? asNum(meta.top1_prob) : asNum(honmei && honmei.win_prob),
      confidence_score: score,
      confidence_band: band,
    };
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

  function rivalCount(s) {
    if (isChaotic(s)) return 4;
    if (isSoloLead(s)) return 2;
    return 3;
  }

  function paceTone(s) {
    var m = s.metrics || {};
    if (m.paceCollapse != null) {
      if (m.paceCollapse >= 40) return "fast";
      if (m.paceCollapse < 20) return "slow";
      return "normal";
    }
    if (m.front != null) {
      if (m.front >= 70) return "front";
      if (m.front < 40) return "closer";
    }
    return "normal";
  }

  function placeLabel(s) {
    if (s.venue && s.race_no != null) return s.venue + s.race_no + "R";
    if (s.venue) return String(s.venue);
    return "今回のレース";
  }

  function courseBits(s) {
    var bits = [];
    if (s.surface) bits.push(String(s.surface));
    if (s.distance != null) bits.push(String(Math.round(s.distance)) + "m");
    if (s.going) bits.push(String(s.going));
    if (s.field_size != null) bits.push("出走" + s.field_size + "頭");
    return bits;
  }

  /**
   * 展開シナリオ — 「どう買うか」を先に書く（状況説明は最小限）
   */
  function buildScenarios(s, opts) {
    opts = opts || {};
    var axis = horseLabel(s.honmei) || horseLabel(opts.axis) || "中心の馬";
    var nRival = rivalCount(s);
    var rivalRange =
      nRival <= 2 ? "2頭まで" : nRival >= 4 ? "3〜4頭" : "2〜3頭";
    var pace = paceTone(s);

    var basic;
    if (isSoloLead(s)) {
      basic = axis + "を中心に、相手は" + rivalRange + "で買うのがおすすめです。";
    } else if (isChaotic(s)) {
      basic = axis + "を中心に、相手は" + rivalRange + "まで広めに残して買いましょう。";
    } else {
      basic = axis + "を中心に、相手は" + rivalRange + "まで選ぶのがバランスよいです。";
    }

    var collapse;
    if (pace === "fast") {
      collapse = "展開が崩れたら、" + axis + "中心のまま相手を1〜2頭増やして買いましょう。";
    } else if (pace === "slow" || pace === "front") {
      collapse = "想定より速くなったら、対抗寄りの相手を1頭追加して買いましょう。";
    } else if (pace === "closer") {
      collapse = "前が止まらない流れなら、先行寄りの相手を1頭入れて買いましょう。";
    } else {
      collapse = "展開が違ったら、" + axis + "中心は維持しつつ相手を1頭増やしましょう。";
    }

    var upset =
      "波乱を見るときも穴は相手に1頭まで。総額は増やさないのがおすすめです。";

    return [
      { title: "基本の買い方", body: basic },
      { title: "展開が崩れたとき", body: collapse },
      { title: "波乱を意識するとき", body: upset },
    ];
  }

  /**
   * リスク管理 — スマホ向け短いポイント（3〜4個）
   * @returns {string[]}
   */
  function buildRiskPoints(s) {
    var points = [];
    var band = s.confidence_band;
    var m = s.metrics || {};

    if (isChaotic(s)) {
      points.push("上位の力は近いレースです");
      points.push("展開次第で順位が変わる可能性があります");
    } else if (isSoloLead(s)) {
      points.push("中心馬は比較的はっきりしています");
      points.push("それでも展開や枠で着順が動くことがあります");
    } else {
      points.push("上位の差はそこまで大きくありません");
      points.push("展開次第で順位が変わる可能性があります");
    }

    if (s.field_size != null && s.field_size >= 15) {
      points.push("出走" + s.field_size + "頭と多く、紛れやすい条件です");
    } else if (m.paceCollapse != null && m.paceCollapse >= 40) {
      points.push("ペースが速くなりやすく、流れが崩れやすいです");
    } else if (s.surface) {
      points.push(s.surface + "の状態で向き不向きが変わりやすいです");
    }

    if (band === "low") {
      points.push("大きく勝負するより、少し控えめの金額がおすすめです");
    } else {
      points.push("大きく勝負するより、普段どおりの金額がおすすめです");
    }

    return points.slice(0, 4);
  }

  /** @deprecated 互換用（箇条書きを一文に連結） */
  function buildRisk(s) {
    return buildRiskPoints(s).join("。") + "。";
  }

  /**
   * 資金配分理由 — 各％ごとに短い説明（1文）
   * @returns {{ label: string, pct: number, reason: string }[]}
   */
  function buildAllocationItems(s, bank) {
    bank = bank || {};
    var mainPct = bank.mainPct;
    var coverPct = bank.coverPct;
    var lotteryPct = bank.lotteryPct;
    var items = [];

    if (mainPct != null) {
      var mainReason;
      if (isSoloLead(s) || (s.confidence_band === "high" && !isChaotic(s))) {
        mainReason = "中心に考えられそうなので、一番多く配分しています。";
      } else if (isChaotic(s) || s.confidence_band === "low") {
        mainReason = "結果が分かれやすいので、寄せすぎない割合にしています。";
      } else {
        mainReason = "中心の買い目として、いちばん大きな割合にしています。";
      }
      items.push({ label: "中心", pct: mainPct, reason: mainReason });
    }

    if (coverPct != null) {
      var coverReason;
      if (isChaotic(s) || (s.metrics && s.metrics.paceCollapse >= 40) || s.confidence_band === "low") {
        coverReason = "上位の力が近いので、展開が変わった時にも備えています。";
      } else if (isSoloLead(s)) {
        coverReason = "万一の入れ替わりに備えて残しています。";
      } else {
        coverReason = "展開のブレに備えるための割合です。";
      }
      items.push({ label: "保険", pct: coverPct, reason: coverReason });
    }

    if (lotteryPct != null) {
      items.push({
        label: "一発",
        pct: lotteryPct,
        reason:
          lotteryPct >= 20
            ? "高配当狙いの枠ですが、総額の中で抑えています。"
            : "高配当狙いなので少額にしています。",
      });
    }

    return items;
  }

  /** 互換用の連結文 */
  function buildAllocationNote(s, bank) {
    return buildAllocationItems(s, bank)
      .map(function (it) {
        return it.label + "（" + it.pct + "%）\n" + it.reason;
      })
      .join("\n");
  }

  /**
   * @param {{ bundle?: object, bank?: object, axis?: object, confidence?: number }} input
   */
  function compose(input) {
    input = input || {};
    var bundle = input.bundle || null;
    var bank = input.bank || null;
    var s = bundle ? extractSignals(bundle) : {};

    if (!bundle) {
      var conf = asNum(input.confidence);
      if (conf != null) {
        s.confidence_score = conf > 1 ? conf / 100 : conf;
        s.confidence_band = bandFromScore(s.confidence_score);
      }
      if (input.axis) {
        s.honmei = {
          horse_number: input.axis.num,
          horse_name: input.axis.name,
        };
      }
    }

    var scenarios = buildScenarios(s, { axis: input.axis });
    var riskPoints = buildRiskPoints(s);
    var allocationItems = buildAllocationItems(s, bank);

    return {
      scenarios: scenarios,
      riskPoints: riskPoints,
      risk: riskPoints.join("。") + "。",
      allocationItems: allocationItems,
      allocationNote: buildAllocationNote(s, bank),
      signals: s,
    };
  }

  global.ExpectStrategyComposer = {
    compose: compose,
    extractSignals: extractSignals,
    buildScenarios: buildScenarios,
    buildRisk: buildRisk,
    buildRiskPoints: buildRiskPoints,
    buildAllocationNote: buildAllocationNote,
    buildAllocationItems: buildAllocationItems,
  };
})(window);
