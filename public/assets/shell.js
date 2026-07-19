/**
 * Expect 共通シェル: 下部ナビ活性・KA0BAトーク
 */
(function (global) {
  "use strict";

  var DEFAULT_LINES = [
    "今日のAI信頼度だよ！<br><strong>東京芝2000m</strong> は<br>とっても期待できそう！",
    "一緒に、<br><strong>勝ちにいこう！</strong>",
    "気になるレースは<br>保存しておくと便利だよ！",
    "タップありがとう！<br>何か聞きたいことが<br>あったらチャットへ！"
  ];

  function initNav(active) {
    document.querySelectorAll(".bottom-nav a[data-nav]").forEach(function (a) {
      a.classList.toggle("is-active", a.getAttribute("data-nav") === active);
    });
  }

  function initMascotTalk(lines) {
    var root = document.getElementById("mascotKa0ba");
    var btn = document.getElementById("mascotTalkBtn");
    var bubble = document.getElementById("mascotBubble");
    if (!root || !btn || !bubble) return;

    var talk = lines && lines.length ? lines : DEFAULT_LINES;
    var idx = 0;
    var hideTimer = null;
    var typeTimer = null;

    function clearTimers() {
      if (hideTimer) clearTimeout(hideTimer);
      if (typeTimer) clearInterval(typeTimer);
      hideTimer = typeTimer = null;
    }

    function hideBubble() {
      clearTimers();
      root.classList.remove("is-speaking");
    }

    function speak(html) {
      clearTimers();
      root.classList.remove("is-speaking");
      void root.offsetWidth;
      root.classList.add("is-speaking");

      var plain = html.replace(/<br\s*\/?>/gi, "\n").replace(/<\/?strong>/gi, "");
      var cursor = 0;
      bubble.innerHTML = "";
      typeTimer = setInterval(function () {
        cursor += 1;
        bubble.innerHTML = plain
          .slice(0, cursor)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/\n/g, "<br>");
        if (cursor >= plain.length) {
          clearInterval(typeTimer);
          typeTimer = null;
          bubble.innerHTML = html;
          hideTimer = setTimeout(hideBubble, 4200);
        }
      }, 28);
    }

    btn.addEventListener("click", function () {
      speak(talk[idx % talk.length]);
      idx += 1;
    });
  }

  function initChips(rootSel) {
    var root = document.querySelector(rootSel || ".chip-row");
    if (!root) return;
    root.addEventListener("click", function (e) {
      var chip = e.target.closest(".chip, .tab-pill");
      if (!chip || !root.contains(chip)) return;
      root.querySelectorAll(".chip, .tab-pill").forEach(function (c) {
        c.classList.remove("is-active");
      });
      chip.classList.add("is-active");
    });
  }

  global.ExpectShell = {
    initNav: initNav,
    initMascotTalk: initMascotTalk,
    initChips: initChips
  };
})(window);
