/**
 * Version 1.1 progressive enhancements (Flag-gated).
 * Does not modify Prediction Core. Uses existing APIs only.
 */
(function (global) {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function ensureStatusRow(parent) {
    if (!parent) return null;
    var row = qs(".v11-status-row", parent);
    if (row) return row;
    row = document.createElement("div");
    row.className = "v11-status-row";
    row.setAttribute("aria-label", "システム状態");
    parent.insertBefore(row, parent.firstChild);
    return row;
  }

  function chip(label, ok) {
    var el = document.createElement("span");
    el.className = "v11-chip";
    el.dataset.ok = ok === true ? "1" : ok === false ? "0" : "";
    el.innerHTML = '<span class="v11-chip-dot" aria-hidden="true"></span>';
    var text = document.createElement("span");
    text.textContent = label;
    el.appendChild(text);
    return el;
  }

  function mountSystemHealth(row) {
    if (!row || !ExpectUiFeatures.enabled("v11_system_health")) return;
    var el = chip("Health …", null);
    row.appendChild(el);
    var t0 = performance.now();
    fetch("/api/health", { cache: "no-store" })
      .then(function (res) {
        return res.json().then(function (body) {
          return { res: res, body: body, ms: Math.round(performance.now() - t0) };
        });
      })
      .then(function (pack) {
        var ok = !!(
          pack.res.ok &&
          pack.body &&
          (pack.body.ok || (pack.body.data && pack.body.data.status === "ok"))
        );
        el.dataset.ok = ok ? "1" : "0";
        el.lastChild.textContent = ok ? "BFF OK · " + pack.ms + "ms" : "BFF 異常";
      })
      .catch(function () {
        el.dataset.ok = "0";
        el.lastChild.textContent = "BFF 到達不可";
      });
  }

  function mountCollectorHold(row) {
    if (!row || !ExpectUiFeatures.enabled("v11_collector_status")) return;
    row.appendChild(chip("Collector: HOLD（Real 未接続）", true));
  }

  function enhanceHomeLoading() {
    if (!ExpectUiFeatures.enabled("v11_loading_errors")) return;
    var mount = document.getElementById("aiCards");
    if (mount && mount.classList.contains("is-loading") && window.ExpectUx) {
      if (ExpectUx.showLoading && !mount.querySelector("[data-expect-loading='1']")) {
        ExpectUx.showLoading(mount, {
          replace: false,
          compact: true,
          title: "ロード中...",
          message: "しばらくお待ちください。",
        });
      } else if (!mount.querySelector(".expect-skeleton") && !mount.querySelector("[data-expect-loading='1']")) {
        var sk = document.createElement("div");
        sk.className = "v11-home-skel";
        sk.innerHTML = ExpectUx.skeletonCards(3, "ai");
        mount.appendChild(sk);
      }
    }
  }

  function enhanceRaceListBadges() {
    if (!ExpectUiFeatures.enabled("v11_races")) return;
    document.querySelectorAll(".race-item[data-engine-source]").forEach(function (card) {
      if (card.querySelector(".v11-engine-badge")) return;
      var eng = card.getAttribute("data-engine-source") || "";
      var badge = document.createElement("span");
      badge.className =
        "v11-engine-badge " + (eng === "real_ai" ? "is-real" : "is-fallback");
      badge.textContent =
        eng === "real_ai" ? "real_ai" : eng === "mock_fallback" ? "fallback" : eng || "—";
      var side = card.querySelector(".race-item-side") || card;
      side.insertBefore(badge, side.firstChild);
    });
  }

  function enhanceRaceDetailExplain(bundle, meta) {
    if (!ExpectUiFeatures.enabled("v11_explain")) return;
    var body = document.getElementById("reasonsSectionBody");
    var section = document.getElementById("reasonsSection");
    if (!body || !section) return;
    section.hidden = false;
    var narrative = bundle && bundle.explain && bundle.explain.narrative;
    var reasons = (bundle && bundle.explain && bundle.explain.reasons) || [];
    var html = "";
    if (narrative) html += '<p class="v11-explain-narrative"></p>';
    if (window.ExpectPredictionBind && ExpectPredictionBind.reasonsSectionHtml) {
      html += ExpectPredictionBind.reasonsSectionHtml(bundle || {});
    } else if (!reasons.length) {
      var fr = (meta && meta.fallback_reason) || "";
      html +=
        '<p class="muted">理由データなし' + (fr ? "（" + fr + "）" : "") + "</p>";
    }
    body.innerHTML = html;
    var nEl = body.querySelector(".v11-explain-narrative");
    if (nEl && narrative) nEl.textContent = narrative;
  }

  function enhanceRaceDetailConfidence(bundle) {
    if (!ExpectUiFeatures.enabled("v11_confidence")) return;
    var confEl = document.getElementById("raceConfidenceDetail");
    var section = document.getElementById("confidenceSection");
    if (!confEl || !section) return;
    section.hidden = false;
    var ac = (bundle && bundle.ai_confidence) || {};
    var pct = null;
    if (typeof ac.score === "number") {
      pct = ac.score <= 1 ? Math.round(ac.score * 100) : Math.round(ac.score);
    }
    if (pct == null) {
      var m = (confEl.textContent || "").match(/(\d+)\s*%/);
      if (m) pct = Number(m[1]);
    }
    if (pct != null && !confEl.querySelector(".v11-conf-meter")) {
      var meter = document.createElement("div");
      meter.className = "v11-conf-meter";
      meter.setAttribute("aria-hidden", "true");
      meter.innerHTML =
        '<i style="width:' + Math.max(0, Math.min(100, pct)) + '%"></i>';
      confEl.insertBefore(meter, confEl.firstChild);
    }
  }

  function enhanceProvenance(meta, bundle) {
    if (!ExpectUiFeatures.enabled("v11_race_detail")) return;
    var el = document.getElementById("raceProvenance");
    if (!el) return;
    meta = meta || (bundle && bundle.__meta) || {};
    var engine = meta.engine_source || "unknown";
    var fr = meta.fallback_reason || "";
    var cls = engine === "real_ai" ? "is-real" : "is-fallback";
    var label =
      engine === "real_ai"
        ? "AI予想 · real_ai"
        : "供給制約 · " + (engine || "fallback") + (fr ? " · " + fr : "");
    el.hidden = false;
    el.innerHTML =
      '<div class="race-provenance ' +
      cls +
      '"><span class="race-provenance-pill"></span></div>';
    var pill = el.querySelector(".race-provenance-pill");
    if (pill) pill.textContent = label;
  }

  function hookRaceDetail() {
    if (!window.ExpectPredictionBind || !ExpectPredictionBind.applyRaceDetail) return;
    var orig = ExpectPredictionBind.applyRaceDetail;
    if (orig.__v11Wrapped) return;
    function wrapped(bundle, meta, expectedRaceId) {
      var applied = orig(bundle, meta, expectedRaceId);
      if (applied && applied.mismatch) return applied;
      try {
        enhanceProvenance(meta, bundle);
        enhanceRaceDetailExplain(bundle, meta);
        enhanceRaceDetailConfidence(bundle);
      } catch (e) {
        /* additive only */
      }
      return applied;
    }
    wrapped.__v11Wrapped = true;
    ExpectPredictionBind.applyRaceDetail = wrapped;
  }

  function observeRaceList() {
    if (!ExpectUiFeatures.enabled("v11_races")) return;
    var list = document.getElementById("raceList");
    if (!list || typeof MutationObserver === "undefined") {
      enhanceRaceListBadges();
      return;
    }
    var mo = new MutationObserver(function () {
      enhanceRaceListBadges();
    });
    mo.observe(list, { childList: true, subtree: true });
    enhanceRaceListBadges();
  }

  function boot() {
    if (!window.ExpectUiFeatures) return;
    ExpectUiFeatures.ready(function () {
      var homeChrome = document.getElementById("homeChrome");
      var statusParent = homeChrome || qs(".screen") || qs(".app");
      if (
        ExpectUiFeatures.enabled("v11_system_health") ||
        ExpectUiFeatures.enabled("v11_collector_status")
      ) {
        var row = ensureStatusRow(statusParent);
        mountSystemHealth(row);
        mountCollectorHold(row);
      }
      if (document.body.classList.contains("page-home")) {
        enhanceHomeLoading();
      }
      hookRaceDetail();
      observeRaceList();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.ExpectV11 = {
    boot: boot,
    enhanceRaceListBadges: enhanceRaceListBadges,
  };
})(window);
