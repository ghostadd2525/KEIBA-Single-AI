/**
 * Phase2: Analysis / PredictionBundle → UI バインド（評価内訳）
 * cache-bust: 2026-07-25-race-detail-fix
 * 評価内訳は ◎馬の能力特徴量（ability_scores）を優先。無い場合のみ自信度系へフォールバック。
 */
(function (global) {
  "use strict";

  var KEYS = ["history", "distance", "style_fit", "front", "pace_resilience"];
  var DEFAULT_LABELS = {
    history: "近走成績",
    distance: "距離適性",
    style_fit: "脚質×距離",
    front: "先行傾向",
    pace_resilience: "展開耐性",
  };

  function emptyScoreMap() {
    return {
      history: 0,
      distance: 0,
      style_fit: 0,
      front: 0,
      pace_resilience: 0,
      overall: 0,
    };
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** 評価内訳で高いちょうど2項目を返す { a, b }（ラベルは分割しない） */
  function topPairFromCharts(charts) {
    var list = (charts || [])
      .map(function (c) {
        var key = c && c.key;
        return {
          key: key,
          label: DEFAULT_LABELS[key] || (c && c.label) || "",
          value: Number(c && c.value) || 0,
        };
      })
      .filter(function (c) {
        return c.label;
      })
      .sort(function (a, b) {
        return b.value - a.value;
      });
    if (list.length >= 2) return { a: list[0].label, b: list[1].label };
    if (list.length === 1) return { a: list[0].label, b: "" };
    return null;
  }

  function topPairLabelFromCharts(charts) {
    var pair = topPairFromCharts(charts);
    if (!pair) return "—";
    if (pair.b) return pair.a + "×" + pair.b;
    return pair.a;
  }

  /** 0–1 または 0–100 → 0–100 整数 */
  function toPct(v) {
    if (v == null || v === "") return null;
    var n = Number(v);
    if (!isFinite(n)) return null;
    if (n >= 0 && n <= 1) n = n * 100;
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  function chartMap(analysis) {
    var map = emptyScoreMap();
    if (!analysis) return map;
    if (analysis.overall != null) {
      var o = toPct(analysis.overall);
      map.overall = o != null ? o : Number(analysis.overall) || 0;
    }
    (analysis.charts || []).forEach(function (c) {
      if (!c || !c.key) return;
      var pct = toPct(c.value);
      map[c.key] = pct != null ? pct : Number(c.value) || 0;
    });
    return map;
  }

  function pickHonmei(runners) {
    var list = runners || [];
    for (var i = 0; i < list.length; i++) {
      if (list[i] && list[i].mark === "honmei") return list[i];
    }
    var byProb = list.slice().sort(function (a, b) {
      return (Number(b.win_prob) || 0) - (Number(a.win_prob) || 0);
    });
    return byProb[0] || null;
  }

  /**
   * ◎馬 ability_scores → Analysis 互換 charts
   * @returns {{ charts: object[], overall: number } | null}
   */
  function chartsFromAbilityScores(ability, overallHint) {
    if (!ability || typeof ability !== "object") return null;

    // Canonical keys first; UI/fixture aliases (history, distance, …) second.
    var history = toPct(
      ability.history_score != null ? ability.history_score : ability.history
    );
    var distance = toPct(
      ability.distance_score != null ? ability.distance_score : ability.distance
    );
    // style_confidence は高止まりしやすいため、脚質×距離フィットを優先
    var styleFit = null;
    if (ability.style_distance_fit_weight != null) {
      styleFit = toPct(ability.style_distance_fit_weight);
    } else if (ability.style_fit != null) {
      styleFit = toPct(ability.style_fit);
    } else if (ability.gate_risk_score != null) {
      styleFit = toPct(1 - Number(ability.gate_risk_score));
    } else if (ability.style_disadvantage_score != null) {
      styleFit = toPct(1 - Number(ability.style_disadvantage_score));
    }
    var front = toPct(
      ability.front_rate != null ? ability.front_rate : ability.front
    );

    var paceResilience = null;
    if (ability.pace_resilience != null) {
      paceResilience = toPct(ability.pace_resilience);
    } else if (ability.pace_collapse_risk_v2 != null) {
      paceResilience = toPct(1 - Number(ability.pace_collapse_risk_v2));
    } else if (ability.inside_traffic_risk != null) {
      paceResilience = toPct(1 - Number(ability.inside_traffic_risk));
    } else if (ability.gate_risk_score != null) {
      paceResilience = toPct(1 - Number(ability.gate_risk_score));
    }

    function val(pct) {
      return pct != null ? pct : 0;
    }

    var charts = [
      { key: "history", label: DEFAULT_LABELS.history, value: val(history) },
      { key: "distance", label: DEFAULT_LABELS.distance, value: val(distance) },
      { key: "style_fit", label: DEFAULT_LABELS.style_fit, value: val(styleFit) },
      { key: "front", label: DEFAULT_LABELS.front, value: val(front) },
      {
        key: "pace_resilience",
        label: DEFAULT_LABELS.pace_resilience,
        value: val(paceResilience),
      },
    ];

    var known = [history, distance, styleFit, front, paceResilience].filter(function (v) {
      return v != null;
    });
    if (!known.length) return null;

    var overall =
      overallHint != null
        ? val(toPct(overallHint))
        : Math.round(known.reduce(function (a, b) { return a + b; }, 0) / known.length);

    return { charts: charts, overall: overall };
  }

  /**
   * PredictionBundle → 評価内訳 charts（◎馬の能力特徴量のみ）
   */
  function chartsFromPredictionBundle(bundle) {
    if (!bundle || typeof bundle !== "object") return null;
    var runners = ((bundle.evaluation || {}).runners) || [];
    var honmei = pickHonmei(runners);
    var ability = honmei && honmei.ability_scores ? honmei.ability_scores : null;
    var ac = bundle.ai_confidence || {};
    return chartsFromAbilityScores(ability, ac.score);
  }

  function applyRaceDetailAnalysis(analysis) {
    if (!analysis) return null;
    var scores = chartMap(analysis);
    var charts = analysis.charts || [];

    var rows = document.querySelectorAll(".score-list .score-row");
    rows.forEach(function (row, i) {
      var key = KEYS[i];
      if (!key) return;
      var chart = null;
      for (var j = 0; j < charts.length; j++) {
        if (charts[j] && charts[j].key === key) {
          chart = charts[j];
          break;
        }
      }
      if (!chart && charts[i] && charts[i].key === key) chart = charts[i];
      var v = chart && chart.value != null ? toPct(chart.value) : scores[key];
      if (v == null) v = scores[key] || 0;
      var bar = row.querySelector(".score-bar i");
      var b = row.querySelector("b");
      var label = row.querySelector("span");
      if (bar) bar.style.width = v + "%";
      if (b) b.textContent = String(v);
      if (label) {
        label.textContent = (chart && chart.label) || DEFAULT_LABELS[key] || key;
      }
    });

    var radar = document.querySelector(".radar-box span");
    if (radar) {
      var pair = topPairFromCharts(charts);
      if (pair && pair.a && pair.b) {
        // 例: 近走成績 / × / 脚質×距離（B内の×は分割しない）
        radar.innerHTML =
          '<span class="radar-line">' +
          escapeHtml(pair.a) +
          '</span><span class="radar-x">×</span><span class="radar-line">' +
          escapeHtml(pair.b) +
          "</span>";
      } else if (pair && pair.a) {
        radar.textContent = pair.a;
      } else {
        radar.textContent = "—";
      }
    }

    var narrativeEl = document.querySelector(".pace-card p");
    if (narrativeEl && analysis.narrative) {
      var current = (narrativeEl.textContent || "").trim();
      if (!current) narrativeEl.textContent = analysis.narrative;
    }

    return scores;
  }

  function applyFromPredictionBundle(bundle) {
    var derived = chartsFromPredictionBundle(bundle);
    if (!derived) return false;
    applyRaceDetailAnalysis(derived);
    return true;
  }

  function toAiParams(bundle, analysis) {
    var fromPb = chartsFromPredictionBundle(bundle);
    var fromAnalysis =
      !fromPb && analysis && typeof analysis === "object"
        ? {
            charts: analysis.charts || [],
            overall: analysis.overall,
          }
        : null;
    // Lookup failure must not become silent 0% success.
    if (!fromPb && !fromAnalysis) return null;
    if (!fromPb && fromAnalysis && !(fromAnalysis.charts && fromAnalysis.charts.length)) {
      return null;
    }
    var scores = fromPb ? chartMap(fromPb) : chartMap(fromAnalysis);
    var conf = null;
    if (fromPb && global.ExpectApi && ExpectApi.Prediction && ExpectApi.Prediction.scorePercent) {
      conf = ExpectApi.Prediction.scorePercent(bundle);
    }
    if (conf == null && scores.overall) conf = scores.overall;
    return {
      overall: conf != null ? conf : scores.overall != null ? scores.overall : null,
      history: scores.history != null ? scores.history : null,
      distance: scores.distance != null ? scores.distance : null,
      style_fit: scores.style_fit != null ? scores.style_fit : null,
      front: scores.front != null ? scores.front : null,
      pace_resilience: scores.pace_resilience != null ? scores.pace_resilience : null,
      // 旧キー互換
      style: scores.style_fit,
      pedigree: scores.history,
      pace: scores.distance,
      jockey: scores.style_fit,
      form: scores.front,
      odds: scores.pace_resilience,
      win_prob: scores.history,
      model_score: scores.distance,
      segment_hit: scores.style_fit,
      confidence: scores.front,
      concentration: scores.pace_resilience,
    };
  }

  global.ExpectAnalysisBind = {
    KEYS: KEYS,
    DEFAULT_LABELS: DEFAULT_LABELS,
    chartMap: chartMap,
    chartsFromPredictionBundle: chartsFromPredictionBundle,
    chartsFromAbilityScores: chartsFromAbilityScores,
    applyRaceDetailAnalysis: applyRaceDetailAnalysis,
    applyFromPredictionBundle: applyFromPredictionBundle,
    topPairFromCharts: topPairFromCharts,
    topPairLabelFromCharts: topPairLabelFromCharts,
    toAiParams: toAiParams,
  };
})(window);
