/**
 * PredictionBundle — フロントの唯一の入口契約ヘルパ
 * schema: single-prediction-bundle/2.0
 */
(function (global) {
  "use strict";

  var SCHEMA = "single-prediction-bundle/2.0";

  function raceId(bundle) {
    if (!bundle) return "";
    return bundle.race_id || (bundle.race_info && bundle.race_info.race_id) || "";
  }

  function scorePercent(bundle) {
    var c = (bundle && bundle.ai_confidence) || {};
    if (typeof c.score_percent === "number") return Math.round(c.score_percent);
    if (typeof c.score === "number") {
      return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
    }
    return null;
  }

  function honmei(bundle) {
    var runners = (((bundle || {}).evaluation || {}).runners) || [];
    return (
      runners.find(function (r) {
        return r.mark === "honmei";
      }) || runners[0] || null
    );
  }

  function confidenceView(bundle) {
    var c = (bundle && bundle.ai_confidence) || {};
    return {
      race_id: raceId(bundle),
      status: c.status || "ok",
      score: c.score,
      score_percent: scorePercent(bundle),
      band: c.band || "unknown",
      factors: c.factors || [],
    };
  }

  function ticketsView(bundle) {
    var br = (bundle && bundle.betting_recommendations) || {};
    return {
      race_id: raceId(bundle),
      status: br.status || "ok",
      items: br.items || [],
      by_bet_type: br.by_bet_type || {},
      strategy_id: br.strategy_id || null,
    };
  }

  function isBundle(obj) {
    return !!(obj && obj.race_id && (obj.schema_version || obj.evaluation || obj.race_info));
  }

  global.ExpectBundle = {
    SCHEMA: SCHEMA,
    raceId: raceId,
    scorePercent: scorePercent,
    honmei: honmei,
    confidence: confidenceView,
    tickets: ticketsView,
    isBundle: isBundle,
  };
})(window);
