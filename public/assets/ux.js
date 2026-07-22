/**
 * ExpectUx 窶・繝輔Ο繝ｳ繝医・縺ｿ縺ｮ loading / error / empty 繝倥Ν繝・
 * API繝ｻ螂醍ｴ・↓萓晏ｭ倥＠縺ｪ縺・・
 */
(function (global) {
  "use strict";

  var DEFAULT_LOADING_TITLE = "繝ｭ繝ｼ繝我ｸｭ...";
  var DEFAULT_LOADING_MSG = "縺励・繧峨￥縺雁ｾ・■縺上□縺輔＞縲・;
  var LOAD_AVG_KEY = "expect_ux_load_avg_ms";
  var DEFAULT_EXPECTED_MS = 2800;
  var LOADING_RUNNER_SRC = "assets/images/mascot-loading-run.png?v=2";
  var _loadTimers = [];

  function el(html) {
    var t = document.createElement("template");
    t.innerHTML = String(html).trim();
    return t.content.firstElementChild;
  }

  function clearChildren(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function skeletonCards(count, variant) {
    var n = Math.max(1, count || 3);
    var cls = variant === "ai" ? "expect-skel expect-skel--ai" : "expect-skel expect-skel--card";
    var parts = ['<div class="expect-skeleton" role="status" aria-live="polite" aria-label="隱ｭ縺ｿ霎ｼ縺ｿ荳ｭ">'];
    for (var i = 0; i < n; i++) parts.push('<div class="' + cls + '"></div>');
    parts.push("</div>");
    return parts.join("");
  }

  function readExpectedMs() {
    try {
      var v = parseFloat(sessionStorage.getItem(LOAD_AVG_KEY) || "");
      if (isFinite(v) && v >= 600 && v <= 30000) return v;
    } catch (e) {}
    return DEFAULT_EXPECTED_MS;
  }

  function rememberLoadMs(ms) {
    if (!isFinite(ms) || ms < 80) return;
    ms = Math.min(30000, Math.max(200, ms));
    try {
      var prev = parseFloat(sessionStorage.getItem(LOAD_AVG_KEY) || "");
      var next = isFinite(prev) && prev > 0 ? prev * 0.65 + ms * 0.35 : ms;
      sessionStorage.setItem(LOAD_AVG_KEY, String(Math.round(next)));
    } catch (e) {}
  }

  function formatSec(ms) {
    var s = Math.max(0, ms) / 1000;
    if (s < 10) return s.toFixed(1) + "遘・;
    return Math.round(s) + "遘・;
  }

  function stopProgress(panel) {
    if (!panel) return;
    var tid = panel._expectLoadTimer;
    if (tid) {
      clearInterval(tid);
      panel._expectLoadTimer = null;
    }
    _loadTimers = _loadTimers.filter(function (p) {
      return p !== panel;
    });
  }

  /**
   * 邨碁℃譎る俣・区ｨｪ繝舌・・・PI縺ｯ螳滄ｲ謐励↑縺・竊・逶ｮ螳画凾髢薙↓貍ｸ霑代☆繧区耳螳壹ヰ繝ｼ・・
   */
  function startProgress(panel, opts) {
    opts = opts || {};
    if (!panel || panel._expectLoadTimer) return;
    var expected = opts.expectedMs > 0 ? opts.expectedMs : readExpectedMs();
    var started = Date.now();
    panel._expectLoadStarted = started;
    panel._expectLoadExpected = expected;

    var fill = panel.querySelector("[data-expect-load-fill]");
    var meta = panel.querySelector("[data-expect-load-meta]");
    var track = panel.querySelector("[data-expect-load-track]");
    var runner = panel.querySelector("[data-expect-load-runner]");
    if (!fill || !meta) return;

    if (track) {
      track.setAttribute("aria-valuemin", "0");
      track.setAttribute("aria-valuemax", "100");
    }

    function tick(forcePct) {
      var elapsed = Date.now() - started;
      var pct;
      if (forcePct != null) {
        pct = forcePct;
      } else {
        // 逶ｮ螳画凾髢薙〒 ~90% 莉倩ｿ代∪縺ｧ貍ｸ霑托ｼ亥ｮ御ｺ・∪縺ｧ 100% 縺ｫ縺励↑縺・ｼ・
        pct = (1 - Math.exp(-elapsed / Math.max(400, expected))) * 92;
        if (pct > 92) pct = 92;
      }
      fill.style.width = pct.toFixed(1) + "%";
      if (runner) {
        // 繝舌・蜈育ｫｯ縺ｫ蜷医ｏ縺帙※繧ｭ繝｣繝ｩ繧貞ｷｦ蜿ｳ遘ｻ蜍包ｼ医ｏ縺壹°縺ｫ荳贋ｸ九ヰ繧ｦ繝ｳ繝会ｼ・
        var bounce = Math.sin(elapsed / 120) * 3;
        runner.style.transform =
          "translateX(-50%) translateY(" + bounce.toFixed(1) + "px)";
        runner.style.left = pct.toFixed(1) + "%";
        runner.classList.toggle("is-running", forcePct == null);
      }
      if (track) {
        track.setAttribute("aria-valuenow", String(Math.round(pct)));
        track.setAttribute(
          "aria-label",
          "隱ｭ縺ｿ霎ｼ縺ｿ騾ｲ謐・邏・ + Math.round(pct) + "%縲∫ｵ碁℃ " + formatSec(elapsed)
        );
      }
      meta.textContent =
        "邨碁℃ " +
        formatSec(elapsed) +
        " ・・逶ｮ螳・" +
        formatSec(expected);
    }

    tick();
    panel._expectLoadTimer = setInterval(tick, 80);
    _loadTimers.push(panel);
    panel._expectLoadComplete = function () {
      var elapsed = Date.now() - started;
      rememberLoadMs(elapsed);
      tick(100);
      stopProgress(panel);
    };
  }

  /**
   * @param {{
   *   title?: string,
   *   message?: string,
   *   compact?: boolean,
   *   overlay?: boolean,
   *   expectedMs?: number,
   *   progress?: boolean
   * }} [opts]
   */
  function loadingPanel(opts) {
    opts = opts || {};
    var title = opts.title != null ? opts.title : DEFAULT_LOADING_TITLE;
    var message = opts.message != null ? opts.message : DEFAULT_LOADING_MSG;
    var showProgress = opts.progress !== false;
    var cls = "expect-loading";
    if (opts.compact) cls += " expect-loading--compact";
    if (opts.overlay) cls += " expect-loading--overlay";
    var root = el(
      '<div class="' +
        cls +
        '" role="status" aria-live="polite" aria-busy="true" data-expect-loading="1">' +
        '<div class="expect-loading__spinner" aria-hidden="true"></div>' +
        '<p class="expect-loading__title"></p>' +
        '<p class="expect-loading__msg"></p>' +
        (showProgress
          ? '<div class="expect-loading__progress" data-expect-load-track role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">' +
            '<div class="expect-loading__track">' +
            '<img class="expect-loading__runner" data-expect-load-runner src="' +
            LOADING_RUNNER_SRC +
            '" alt="" width="72" height="72" draggable="false" />' +
            '<div class="expect-loading__bar"><span class="expect-loading__fill" data-expect-load-fill></span></div>' +
            "</div>" +
            '<p class="expect-loading__meta" data-expect-load-meta>邨碁℃ 0.0遘・/p>' +
            "</div>"
          : "") +
        "</div>"
    );
    root.querySelector(".expect-loading__title").textContent = title;
    root.querySelector(".expect-loading__msg").textContent = message;
    if (showProgress) startProgress(root, opts);
    return root;
  }

  function loadingHtml(opts) {
    return loadingPanel(opts).outerHTML;
  }

  /**
   * mount 蜀・↓繝ｭ繝ｼ繝・ぅ繝ｳ繧ｰ逕ｻ髱｢繧貞ｷｮ縺苓ｾｼ繧縲・
   * replace=true・域里螳夲ｼ峨〒荳ｭ霄ｫ繧堤ｽｮ謠帙’alse 縺ｧ繧ｪ繝ｼ繝舌・繝ｬ繧､霑ｽ蜉縲・
   */
  function showLoading(mount, opts) {
    opts = opts || {};
    if (!mount) return null;
    var replace = opts.replace !== false;
    mount.setAttribute("aria-busy", "true");
    mount.classList.add("is-api-loading");
    if (replace) {
      clearChildren(mount);
      var panel = loadingPanel(opts);
      mount.appendChild(panel);
      return panel;
    }
    hideLoading(mount, { keepBusy: true });
    var overlay = loadingPanel(Object.assign({}, opts, { overlay: true }));
    if (getComputedStyle(mount).position === "static") {
      mount.style.position = "relative";
    }
    mount.appendChild(overlay);
    return overlay;
  }

  function hideLoading(mount, opts) {
    opts = opts || {};
    if (!mount) return;
    mount.querySelectorAll("[data-expect-loading='1']").forEach(function (n) {
      if (!opts.keepBusy && typeof n._expectLoadComplete === "function") {
        try {
          n._expectLoadComplete();
        } catch (e) {}
      } else {
        stopProgress(n);
      }
      n.remove();
    });
    if (!opts.keepBusy) {
      mount.setAttribute("aria-busy", "false");
      mount.classList.remove("is-api-loading");
    }
  }

  /** 髱咏噪HTML縺ｮ繝ｭ繝ｼ繝・ぅ繝ｳ繧ｰ譫縺ｫ繧るｲ謐励ヰ繝ｼ繧剃ｻ倥￠繧・*/
  function bootStaticLoading() {
    document.querySelectorAll("[data-expect-loading='1']").forEach(function (panel) {
      if (panel._expectLoadTimer) return;
      if (!panel.querySelector("[data-expect-load-fill]")) {
        var wrap = el(
          '<div class="expect-loading__progress" data-expect-load-track role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">' +
            '<div class="expect-loading__track">' +
            '<img class="expect-loading__runner" data-expect-load-runner src="' +
            LOADING_RUNNER_SRC +
            '" alt="" width="72" height="72" draggable="false" />' +
            '<div class="expect-loading__bar"><span class="expect-loading__fill" data-expect-load-fill></span></div>' +
            "</div>" +
            '<p class="expect-loading__meta" data-expect-load-meta>邨碁℃ 0.0遘・/p>' +
            "</div>"
        );
        panel.appendChild(wrap);
      } else if (!panel.querySelector("[data-expect-load-runner]")) {
        var barHost = panel.querySelector(".expect-loading__bar");
        var trackHost = barHost && barHost.parentElement;
        if (barHost && trackHost && !trackHost.classList.contains("expect-loading__track")) {
          var trackWrap = document.createElement("div");
          trackWrap.className = "expect-loading__track";
          trackHost.insertBefore(trackWrap, barHost);
          trackWrap.appendChild(barHost);
          trackHost = trackWrap;
        }
        if (trackHost) {
          var img = document.createElement("img");
          img.className = "expect-loading__runner";
          img.setAttribute("data-expect-load-runner", "");
          img.src = LOADING_RUNNER_SRC;
          img.alt = "";
          img.width = 72;
          img.height = 72;
          img.draggable = false;
          trackHost.insertBefore(img, trackHost.firstChild);
        }
      }
      startProgress(panel);
    });
  }

  function stateCard(opts) {
    opts = opts || {};
    var kind = opts.kind || "empty";
    var title = opts.title || "";
    var message = opts.message || "";
    var retry = opts.retryLabel || "蜀崎ｪｭ縺ｿ霎ｼ縺ｿ";
    var showRetry = !!opts.onRetry;
    var kindClass =
      kind === "error" ? "error" : kind === "warn" ? "empty" : "empty";
    var root = el(
      '<div class="expect-state expect-state--' +
        kindClass +
        (kind === "warn" ? " expect-state--warn" : "") +
        '" role="' +
        (kind === "error" ? "alert" : "status") +
        '">' +
        (title ? '<p class="expect-state__title"></p>' : "") +
        (message ? '<p class="expect-state__msg"></p>' : "") +
        (showRetry ? '<div class="expect-state__actions"><button type="button" class="expect-btn"></button></div>' : "") +
        "</div>"
    );
    var tEl = root.querySelector(".expect-state__title");
    var mEl = root.querySelector(".expect-state__msg");
    var bEl = root.querySelector(".expect-btn");
    if (tEl) tEl.textContent = title;
    if (mEl) mEl.textContent = message;
    if (bEl && showRetry) {
      bEl.textContent = retry;
      bEl.addEventListener("click", function () {
        opts.onRetry();
      });
    }
    return root;
  }

  function showIn(mount, nodeOrHtml) {
    if (!mount) return;
    clearChildren(mount);
    if (typeof nodeOrHtml === "string") mount.innerHTML = nodeOrHtml;
    else if (nodeOrHtml) mount.appendChild(nodeOrHtml);
  }

  function setLoadingClass(node, on) {
    if (!node) return;
    node.classList.toggle("is-loading", !!on);
  }

  function typingRow() {
    return el(
      '<div class="msg msg-ai msg-typing" data-typing="1" aria-label="蜈･蜉帑ｸｭ">' +
        '<img src="assets/images/mascot-ka0ba.png?v=10" alt="" />' +
        '<div class="msg-bubble">' +
        '<span class="msg-typing__dot"></span>' +
        '<span class="msg-typing__dot"></span>' +
        '<span class="msg-typing__dot"></span>' +
        "</div></div>"
    );
  }

  function removeTyping(log) {
    if (!log) return;
    log.querySelectorAll("[data-typing='1']").forEach(function (n) {
      n.remove();
    });
  }

  function scrollLogToBottom(log) {
    if (!log) return;
    requestAnimationFrame(function () {
      log.scrollTo({ top: log.scrollHeight, behavior: "smooth" });
    });
  }

  global.ExpectUx = {
    skeletonCards: skeletonCards,
    loadingPanel: loadingPanel,
    loadingHtml: loadingHtml,
    showLoading: showLoading,
    hideLoading: hideLoading,
    bootStaticLoading: bootStaticLoading,
    stateCard: stateCard,
    showIn: showIn,
    setLoadingClass: setLoadingClass,
    typingRow: typingRow,
    removeTyping: removeTyping,
    scrollLogToBottom: scrollLogToBottom,
    DEFAULT_LOADING_TITLE: DEFAULT_LOADING_TITLE,
    DEFAULT_LOADING_MSG: DEFAULT_LOADING_MSG,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootStaticLoading);
  } else {
    bootStaticLoading();
  }
})(window);
