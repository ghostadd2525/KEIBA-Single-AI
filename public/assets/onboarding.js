/**
 * 初回操作説明（スポットライトツアー）
 * ハイライト箇所のみ操作可能、周囲はグレーアウトでタッチ不可
 */
(function (global) {
  "use strict";

  var STEPS = [
    {
      selector: "#favorites",
      title: "お気に入りレース",
      body: "注目レースをここに並べられます。カードを横にスワイプして確認しましょう。",
      pad: 8
    },
    {
      selector: "#aiCards",
      title: "AIの着眼点",
      body: "今日の注目ポイントや信頼度がまとまっています。気になるカードをタップしてみてください。",
      pad: 8
    },
    {
      selector: "#heatmap",
      title: "ヒートマップ",
      body: "競馬場×距離の傾向を色で確認できます。横スワイプで他の条件も見られます。",
      pad: 8
    },
    {
      selector: "#mascotKa0ba",
      title: "KAOBA",
      body: "右下のKAOBAをタップすると、ひとことアドバイスが表示されます。",
      pad: 10
    },
    {
      selector: ".bottom-nav",
      title: "メニュー",
      body: "レース一覧・分析・今月成績・マイページへは下のメニューから移動できます。",
      pad: 6
    }
  ];

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function startOnboarding() {
    if (!global.ExpectAuth || !ExpectAuth.needsOnboarding()) return;
    if ($(".ob-root")) return;

    var step = 0;
    var root = document.createElement("div");
    root.className = "ob-root";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", "操作説明");
    root.innerHTML =
      '<div class="ob-block" data-ob="top"></div>' +
      '<div class="ob-block" data-ob="left"></div>' +
      '<div class="ob-block" data-ob="right"></div>' +
      '<div class="ob-block" data-ob="bottom"></div>' +
      '<div class="ob-ring" aria-hidden="true"></div>' +
      '<div class="ob-card">' +
      '  <p class="ob-step"></p>' +
      "  <h2></h2>" +
      '  <p class="ob-body"></p>' +
      '  <div class="ob-actions">' +
      '    <button type="button" class="ob-skip">スキップ</button>' +
      '    <button type="button" class="ob-next">次へ</button>' +
      "  </div>" +
      "</div>";

    document.body.appendChild(root);
    document.body.classList.add("is-onboarding");

    var blockTop = $('[data-ob="top"]', root);
    var blockLeft = $('[data-ob="left"]', root);
    var blockRight = $('[data-ob="right"]', root);
    var blockBottom = $('[data-ob="bottom"]', root);
    var ring = $(".ob-ring", root);
    var card = $(".ob-card", root);
    var stepEl = $(".ob-step", root);
    var titleEl = $("h2", root);
    var bodyEl = $(".ob-body", root);
    var nextBtn = $(".ob-next", root);
    var skipBtn = $(".ob-skip", root);

    function finish() {
      ExpectAuth.completeOnboarding();
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
      document.body.classList.remove("is-onboarding");
      root.remove();
    }

    function placeCard(hole) {
      var gap = 12;
      var cw = card.offsetWidth || 280;
      var ch = card.offsetHeight || 140;
      var vw = window.innerWidth;
      var vh = window.innerHeight;
      var left = clamp(hole.x + (hole.w - cw) / 2, 14, vw - cw - 14);
      var top = hole.y + hole.h + gap;

      if (top + ch > vh - 12) {
        top = hole.y - ch - gap;
      }
      if (top < 12) {
        top = clamp(vh - ch - 16, 12, vh - ch - 12);
      }

      card.style.left = left + "px";
      card.style.top = top + "px";
    }

    function layoutBlocks(hole) {
      var vw = window.innerWidth;
      var vh = window.innerHeight;
      var x = hole.x;
      var y = hole.y;
      var w = hole.w;
      var h = hole.h;

      blockTop.style.cssText = "left:0;top:0;width:" + vw + "px;height:" + y + "px;";
      blockLeft.style.cssText =
        "left:0;top:" + y + "px;width:" + x + "px;height:" + h + "px;";
      blockRight.style.cssText =
        "left:" + (x + w) + "px;top:" + y + "px;width:" + Math.max(0, vw - x - w) + "px;height:" + h + "px;";
      blockBottom.style.cssText =
        "left:0;top:" + (y + h) + "px;width:" + vw + "px;height:" + Math.max(0, vh - y - h) + "px;";

      ring.style.cssText =
        "left:" + x + "px;top:" + y + "px;width:" + w + "px;height:" + h + "px;";
    }

    function render() {
      if (step >= STEPS.length) {
        finish();
        return;
      }

      var conf = STEPS[step];
      var el = $(conf.selector);
      if (!el) {
        step += 1;
        render();
        return;
      }

      el.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });

      var pad = conf.pad || 8;
      var rect = el.getBoundingClientRect();
      var hole = {
        x: Math.max(6, rect.left - pad),
        y: Math.max(6, rect.top - pad),
        w: 0,
        h: 0
      };
      hole.w = Math.min(window.innerWidth - hole.x - 6, rect.width + pad * 2);
      hole.h = Math.min(window.innerHeight - hole.y - 6, rect.height + pad * 2);

      layoutBlocks(hole);

      stepEl.textContent = "操作説明 " + (step + 1) + " / " + STEPS.length;
      titleEl.textContent = conf.title;
      bodyEl.textContent = conf.body;
      nextBtn.textContent = step === STEPS.length - 1 ? "はじめる" : "次へ";

      requestAnimationFrame(function () {
        placeCard(hole);
      });
    }

    function onResize() {
      render();
    }

    nextBtn.addEventListener("click", function () {
      step += 1;
      render();
    });

    skipBtn.addEventListener("click", finish);

    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);

    setTimeout(render, 120);
  }

  global.ExpectOnboarding = {
    start: startOnboarding
  };
})(window);
