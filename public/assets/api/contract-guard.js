/**
 * フロント契約ガード — 契約違反でも UI を壊さずエラーカードへフォールバック
 *
 * Schema 全量は載せない（必須・型・schema_version の軽量チェック）
 */
(function (global) {
  "use strict";

  var PB_VERSION = "single-prediction-bundle/2.0";
  var ANALYSIS_VERSION = "expect-analysis/1.0";

  function isObj(v) {
    return v != null && typeof v === "object" && !Array.isArray(v);
  }

  function validatePredictionBundle(bundle) {
    var errors = [];
    if (!isObj(bundle)) return { ok: false, errors: ["$: not an object"], contract: "PredictionBundle" };
    if (bundle.schema_version !== PB_VERSION) {
      errors.push("schema_version: expected " + PB_VERSION);
    }
    if (typeof bundle.race_id !== "string" || !bundle.race_id) {
      errors.push("race_id: required string");
    }
    if (!isObj(bundle.race_info)) {
      errors.push("race_info: required object");
    } else {
      if (typeof bundle.race_info.venue !== "string") errors.push("race_info.venue: string");
      if (typeof bundle.race_info.date !== "string") errors.push("race_info.date: string");
      if (typeof bundle.race_info.race_no !== "number") errors.push("race_info.race_no: number");
    }
    if (!isObj(bundle.evaluation) || !Array.isArray(bundle.evaluation.runners)) {
      errors.push("evaluation.runners: required array");
    }
    if (!isObj(bundle.ai_confidence) || !("score" in bundle.ai_confidence)) {
      errors.push("ai_confidence.score: required");
    } else if (
      bundle.ai_confidence.score != null &&
      typeof bundle.ai_confidence.score !== "number"
    ) {
      errors.push("ai_confidence.score: number|null");
    }
    if (!isObj(bundle.explain) || typeof bundle.explain.narrative !== "string") {
      errors.push("explain.narrative: required string");
    }
    if (!isObj(bundle.betting_recommendations) || !Array.isArray(bundle.betting_recommendations.items)) {
      errors.push("betting_recommendations.items: required array");
    }
    return { ok: errors.length === 0, errors: errors, contract: "PredictionBundle" };
  }

  function validateAnalysis(analysis) {
    var errors = [];
    if (!isObj(analysis)) return { ok: false, errors: ["$: not an object"], contract: "Analysis" };
    if (analysis.schema_version !== ANALYSIS_VERSION) {
      errors.push("schema_version: expected " + ANALYSIS_VERSION);
    }
    if (typeof analysis.race_id !== "string" || !analysis.race_id) {
      errors.push("race_id: required string");
    }
    if (!Array.isArray(analysis.charts)) {
      errors.push("charts: required array");
    } else {
      analysis.charts.forEach(function (c, i) {
        if (!isObj(c)) {
          errors.push("charts[" + i + "]: object");
          return;
        }
        if (typeof c.key !== "string") errors.push("charts[" + i + "].key: string");
        if (typeof c.label !== "string") errors.push("charts[" + i + "].label: string");
        if (typeof c.value !== "number") errors.push("charts[" + i + "].value: number");
      });
    }
    return { ok: errors.length === 0, errors: errors, contract: "Analysis" };
  }

  function filterValidBundles(list) {
    var ok = [];
    var rejected = [];
    (list || []).forEach(function (b, i) {
      var r = validatePredictionBundle(b);
      if (r.ok) ok.push(b);
      else rejected.push({ index: i, race_id: b && b.race_id, errors: r.errors });
    });
    return { ok: ok, rejected: rejected };
  }

  /**
   * 既存レイアウト内にエラーカードを出す（破壊的な全置換はしない）
   * @param {Element|string|null} mount
   * @param {{ title?: string, message?: string, errors?: string[] }} opts
   */
  function showErrorCard(mount, opts) {
    opts = opts || {};
    var el =
      typeof mount === "string" ? document.querySelector(mount) : mount;
    if (!el) return null;

    var existing = el.querySelector(":scope > .contract-error-card");
    if (existing) existing.remove();

    var card = document.createElement("div");
    card.className = "contract-error-card";
    card.setAttribute("role", "alert");
    card.setAttribute("data-contract-error", "1");

    var title = document.createElement("p");
    title.className = "contract-error-card__title";
    title.textContent = opts.title || "データを表示できません";

    var msg = document.createElement("p");
    msg.className = "contract-error-card__msg";
    msg.textContent =
      opts.message ||
      "API契約と一致しない応答を受け取りました。画面レイアウトは維持しています。";

    card.appendChild(title);
    card.appendChild(msg);

    if (opts.errors && opts.errors.length) {
      var detail = document.createElement("p");
      detail.className = "contract-error-card__detail";
      detail.textContent = opts.errors.slice(0, 3).join(" / ");
      card.appendChild(detail);
    }

    if (el.firstChild) el.insertBefore(card, el.firstChild);
    else el.appendChild(card);
    return card;
  }

  function clearErrorCard(mount) {
    var el = typeof mount === "string" ? document.querySelector(mount) : mount;
    if (!el) return;
    el.querySelectorAll(":scope > .contract-error-card").forEach(function (c) {
      c.remove();
    });
  }

  /**
   * バインド実行を安全化。契約違反時は bind せずエラーカード。
   * @returns {boolean} バインドしたか
   */
  function safeApply(mount, result, applyFn, opts) {
    opts = opts || {};
    if (result && result.ok !== false && applyFn) {
      clearErrorCard(mount);
      try {
        applyFn();
        return true;
      } catch (e) {
        showErrorCard(mount, {
          title: opts.title || "表示に失敗しました",
          message: "データの反映中に問題が発生しました。",
          errors: [String(e && e.message ? e.message : e)],
        });
        return false;
      }
    }
    showErrorCard(mount, {
      title: opts.title || "データを表示できません",
      message: opts.message,
      errors: (result && result.errors) || [],
    });
    return false;
  }

  global.ExpectContractGuard = {
    PB_VERSION: PB_VERSION,
    ANALYSIS_VERSION: ANALYSIS_VERSION,
    validatePredictionBundle: validatePredictionBundle,
    validateAnalysis: validateAnalysis,
    filterValidBundles: filterValidBundles,
    showErrorCard: showErrorCard,
    clearErrorCard: clearErrorCard,
    safeApply: safeApply,
  };
})(window);
