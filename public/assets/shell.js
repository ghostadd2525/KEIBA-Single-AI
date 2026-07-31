/**
 * Expect 共通シェル: 下部ナビ活性・KA0BAトーク
 */
(function (global) {
  "use strict";

  var BRIGHTNESS_KEY = "expect_brightness_v1";

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

  var mascotHideTimer = null;
  var mascotTypeTimer = null;
  var mascotQueue = [];
  var mascotBusy = false;

  function clearMascotTimers() {
    if (mascotHideTimer) clearTimeout(mascotHideTimer);
    if (mascotTypeTimer) clearInterval(mascotTypeTimer);
    mascotHideTimer = mascotTypeTimer = null;
  }

  function hideMascotBubble() {
    clearMascotTimers();
    var root = document.getElementById("mascotKa0ba");
    if (root) root.classList.remove("is-speaking");
    mascotBusy = false;
    if (mascotQueue.length) {
      var next = mascotQueue.shift();
      speakMascot(next.html, next.holdMs);
    }
  }

  /** KAOBA吹き出し（リマインダー等からも利用） */
  function speakMascot(html, holdMs) {
    var root = document.getElementById("mascotKa0ba");
    var bubble = document.getElementById("mascotBubble");
    if (!root || !bubble || !html) return false;

    if (mascotBusy) {
      mascotQueue.push({ html: html, holdMs: holdMs });
      return true;
    }

    mascotBusy = true;
    clearMascotTimers();
    root.classList.remove("is-speaking");
    void root.offsetWidth;
    root.classList.add("is-speaking");

    var hold = typeof holdMs === "number" ? holdMs : 5200;
    var plain = String(html)
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/?strong>/gi, "");
    var cursor = 0;
    bubble.innerHTML = "";
    mascotTypeTimer = setInterval(function () {
      cursor += 1;
      bubble.innerHTML = plain
        .slice(0, cursor)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>");
      if (cursor >= plain.length) {
        clearInterval(mascotTypeTimer);
        mascotTypeTimer = null;
        bubble.innerHTML = html;
        mascotHideTimer = setTimeout(hideMascotBubble, hold);
      }
    }, 28);
    return true;
  }

  function initMascotTalk(lines) {
    var btn = document.getElementById("mascotTalkBtn");
    if (!btn || btn.getAttribute("data-mascot-bound") === "1") return;
    btn.setAttribute("data-mascot-bound", "1");

    var talk = lines && lines.length ? lines : DEFAULT_LINES;
    var idx = 0;

    btn.addEventListener("click", function () {
      speakMascot(talk[idx % talk.length], 4200);
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

  var NAV_ITEMS = [
    { id: "home", href: "index.html", label: "ホーム" },
    { id: "race", href: "races.html", label: "レース" },
    { id: "analysis", href: "analysis.html", label: "分析" },
    { id: "challenge", href: "saved.html", label: "チャレンジ" },
    { id: "mypage", href: "mypage.html", label: "マイページ" }
  ];

  var TOOLS_HTML =
    '<div class="global-tools" aria-label="共通ツール">' +
    '<div class="global-bell">' +
    '<button type="button" class="icon-btn" aria-label="リマインダー" aria-haspopup="true" aria-expanded="false" data-global-bell title="お気に入りレースのリマインダー">' +
    '<svg class="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M12 3a5.5 5.5 0 0 0-5.5 5.5v2.2c0 .9-.3 1.8-.9 2.5L4.2 15.2c-.4.5-.1 1.3.6 1.3h14.4c.7 0 1-.8.6-1.3l-1.4-2c-.6-.7-.9-1.6-.9-2.5V8.5A5.5 5.5 0 0 0 12 3Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>' +
    '<path d="M10 18.5a2 2 0 0 0 4 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
    "</svg>" +
    '<span class="global-bell-badge" data-bell-badge hidden></span>' +
    "</button>" +
    '<div class="global-bell-panel" data-bell-panel hidden role="dialog" aria-label="リマインダー">' +
    '<p class="global-bell-head">リマインダー</p>' +
    '<p class="global-bell-sub">発走15分前：チケット購入 / 発走5分前：レース開始</p>' +
    '<div class="global-bell-list" data-bell-list></div>' +
    "</div></div>" +
    '<div class="global-menu">' +
    '<button type="button" class="icon-btn" aria-label="メニュー" aria-haspopup="true" aria-expanded="false" data-global-menu>' +
    '<svg class="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M5 7h14M5 12h14M5 17h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
    "</svg></button>" +
    '<div class="global-menu-panel" id="globalMenuPanel" hidden role="menu" aria-label="メニュー">' +
    NAV_ITEMS.map(function (item) {
      return (
        '<a class="global-menu-item" role="menuitem" href="' +
        item.href +
        '" data-nav="' +
        item.id +
        '">' +
        item.label +
        "</a>"
      );
    }).join("") +
    '<button type="button" class="global-menu-item global-menu-item--logout" role="menuitem" data-global-logout>ログアウト</button>' +
    "</div></div></div>";

  function bindGlobalMenu(root) {
    var wrap = root.querySelector(".global-menu");
    var menuBtn = root.querySelector("[data-global-menu]");
    var panel = root.querySelector("#globalMenuPanel");
    if (!wrap || !menuBtn || !panel) return;

    var active = document.body.getAttribute("data-nav") || "home";
    panel.querySelectorAll("[data-nav]").forEach(function (a) {
      a.classList.toggle("is-active", a.getAttribute("data-nav") === active);
    });

    function closeMenu() {
      wrap.classList.remove("is-open");
      panel.hidden = true;
      menuBtn.setAttribute("aria-expanded", "false");
    }

    function openMenu() {
      wrap.classList.add("is-open");
      panel.hidden = false;
      menuBtn.setAttribute("aria-expanded", "true");
    }

    function toggleMenu(e) {
      e.preventDefault();
      e.stopPropagation();
      if (wrap.classList.contains("is-open")) closeMenu();
      else openMenu();
    }

    menuBtn.addEventListener("click", toggleMenu);

    var logoutBtn = panel.querySelector("[data-global-logout]");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        closeMenu();
        var go = function () {
          window.location.href = "login.html";
        };
        if (global.ExpectAuth && typeof ExpectAuth.logout === "function") {
          Promise.resolve(ExpectAuth.logout()).finally(go);
        } else {
          go();
        }
      });
    }

    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) closeMenu();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMenu();
    });
  }

  function mountGlobalTools() {
    if (document.querySelector(".global-tools")) return;
    var app = document.querySelector(".app");
    if (!app) return;
    // ログイン・利用規約など認証前画面では出さない
    if (
      document.body.classList.contains("page-login") ||
      document.body.classList.contains("page-terms")
    ) {
      return;
    }

    var topbarInner = app.querySelector(".topbar-inner");
    if (!topbarInner) return;

    var slot = topbarInner.querySelector(".topbar-tools");
    if (!slot) {
      slot = document.createElement("div");
      slot.className = "topbar-tools";
      topbarInner.appendChild(slot);
    }

    // ページ固有ボタン（お気に入り等）は残し、共通のベル・メニューを右端へ
    slot.removeAttribute("aria-hidden");
    slot.insertAdjacentHTML("beforeend", TOOLS_HTML);
    bindGlobalMenu(slot);
    if (global.ExpectReminders && typeof ExpectReminders.bind === "function") {
      ExpectReminders.bind(slot);
    }
  }

  function getBrightness() {
    try {
      var v = global.localStorage.getItem(BRIGHTNESS_KEY);
      return v === "bright" ? "bright" : "dark";
    } catch (e) {
      return "dark";
    }
  }

  function applyBrightness(mode) {
    var next = mode === "bright" ? "bright" : "dark";
    document.documentElement.setAttribute("data-brightness", next);
    try {
      global.localStorage.setItem(BRIGHTNESS_KEY, next);
    } catch (e) {}
    return next;
  }

  function toggleBrightness() {
    return applyBrightness(getBrightness() === "bright" ? "dark" : "bright");
  }

  function syncBrightnessButton(btn) {
    if (!btn) return;
    var bright = getBrightness() === "bright";
    btn.setAttribute("aria-pressed", bright ? "true" : "false");
    btn.title = bright ? "明るさ: 明るめ（タップで暗く）" : "明るさ: 標準（タップで明るく）";
    btn.classList.toggle("is-bright", bright);
  }

  // 全画面で保存済みの明るさを反映
  applyBrightness(getBrightness());

  global.ExpectShell = {
    initNav: initNav,
    initMascotTalk: initMascotTalk,
    speakMascot: speakMascot,
    initChips: initChips,
    mountGlobalTools: mountGlobalTools,
    getBrightness: getBrightness,
    applyBrightness: applyBrightness,
    toggleBrightness: toggleBrightness,
    syncBrightnessButton: syncBrightnessButton
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountGlobalTools);
  } else {
    mountGlobalTools();
  }
})(window);
