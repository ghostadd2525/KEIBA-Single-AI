/**
 * Phase2: Analysis → UI バインド（ui-api-mapping.md）
 * キーは PredictionBundle.race_id
 */
(function (global) {
  "use strict";

  var KEYS = ["pedigree", "pace", "jockey", "form", "odds"];
  var DEFAULT_LABELS = {
    pedigree: "血統適性",
    pace: "展開予測",
    jockey: "騎手相性",
    form: "近走内容",
    odds: "オッズ妙味",
  };

  function chartMap(analysis) {
    if (global.ExpectApi && ExpectApi.Analysis && ExpectApi.Analysis.chartMap) {
      return ExpectApi.Analysis.chartMap(analysis);
    }
    var map = { pedigree: 0, pace: 0, jockey: 0, form: 0, odds: 0, overall: 0 };
    if (!analysis) return map;
    if (analysis.overall != null) map.overall = Number(analysis.overall) || 0;
    (analysis.charts || []).forEach(function (c) {
      if (c && c.key) map[c.key] = Number(c.value) || 0;
    });
    return map;
  }

  /**
   * レース詳細: 評価内訳バー + レーダー文言
   * レイアウト / CSS は変更しない
   */
  function applyRaceDetailAnalysis(analysis) {
    if (!analysis) return null;
    var scores = chartMap(analysis);

    var rows = document.querySelectorAll(".score-list .score-row");
    rows.forEach(function (row, i) {
      var key = KEYS[i];
      if (!key) return;
      var v = scores[key];
      var bar = row.querySelector(".score-bar i");
      var b = row.querySelector("b");
      var label = row.querySelector("span");
      if (bar) bar.style.width = v + "%";
      if (b) b.textContent = String(v);
      if (label && analysis.charts && analysis.charts[i] && analysis.charts[i].label) {
        var pretty = DEFAULT_LABELS[key] || analysis.charts[i].label;
        label.textContent = pretty;
      }
    });

    var radar = document.querySelector(".radar-box span");
    if (radar) {
      radar.innerHTML = "血統<br>展開<br>騎手";
    }

    /* 展開文: PB 優先。空のときだけ Analysis.narrative で補完 */
    var narrativeEl = document.querySelector(".pace-card p");
    if (narrativeEl && analysis.narrative) {
      var current = (narrativeEl.textContent || "").trim();
      if (!current) narrativeEl.textContent = analysis.narrative;
    }

    return scores;
  }

  /**
   * Analysis + PB 信頼度 → 分析画面用 ai オブジェクト
   */
  function toAiParams(bundle, analysis) {
    var scores = chartMap(analysis);
    var conf = null;
    if (global.ExpectApi && ExpectApi.Prediction && ExpectApi.Prediction.scorePercent) {
      conf = ExpectApi.Prediction.scorePercent(bundle);
    }
    if (conf == null && scores.overall) conf = scores.overall;
    return {
      overall: conf != null ? conf : scores.overall || 0,
      pedigree: scores.pedigree,
      pace: scores.pace,
      jockey: scores.jockey,
      form: scores.form,
      odds: scores.odds,
    };
  }

  global.ExpectAnalysisBind = {
    KEYS: KEYS,
    chartMap: chartMap,
    applyRaceDetailAnalysis: applyRaceDetailAnalysis,
    toAiParams: toAiParams,
  };
})(window);
