/**
 * ExpectUx — フロントのみの loading / error / empty ヘルパ
 * API・契約に依存しない。
 */
(function (global) {
  "use strict";

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
    var parts = ['<div class="expect-skeleton" role="status" aria-live="polite" aria-label="読み込み中">'];
    for (var i = 0; i < n; i++) parts.push('<div class="' + cls + '"></div>');
    parts.push("</div>");
    return parts.join("");
  }

  function stateCard(opts) {
    opts = opts || {};
    var kind = opts.kind || "empty";
    var title = opts.title || "";
    var message = opts.message || "";
    var retry = opts.retryLabel || "再読み込み";
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
      '<div class="msg msg-ai msg-typing" data-typing="1" aria-label="入力中">' +
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
    stateCard: stateCard,
    showIn: showIn,
    setLoadingClass: setLoadingClass,
    typingRow: typingRow,
    removeTyping: removeTyping,
    scrollLogToBottom: scrollLogToBottom,
  };
})(window);
