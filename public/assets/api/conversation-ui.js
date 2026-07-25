/**
 * ExpectConversationUi — V5 Phase 3 Conversation UI Integration
 *
 * 既存画面から Review / Explain / Personal Chat へ導線を張る。
 * Conversation Platform / Tool Manager / Prediction API は変更しない。
 */
(function (global) {
  "use strict";

  function chatUrl(opts) {
    opts = opts || {};
    var q = new URLSearchParams();
    var mode = "";
    if (global.ExpectApi && ExpectApi.Conversation && ExpectApi.Conversation.normalizeMode) {
      mode = ExpectApi.Conversation.normalizeMode(opts.mode);
    } else {
      mode = String(opts.mode || "").trim().toLowerCase();
    }
    if (mode) q.set("mode", mode);
    if (opts.race_id || opts.raceId) q.set("race_id", opts.race_id || opts.raceId);
    if (opts.prompt) q.set("prompt", opts.prompt);
    if (opts.display) q.set("display", opts.display);
    if (opts.from) q.set("from", opts.from);
    var qs = q.toString();
    return "chat.html" + (qs ? "?" + qs : "");
  }

  function explainUrl(raceId, opts) {
    opts = opts || {};
    var display = opts.display || "◎の理由を教えて";
    var prompt =
      opts.prompt ||
      "なぜ本命（◎）なの？理由を教えて。印や順位は変えなくていいよ。";
    return chatUrl({
      mode: "explain",
      race_id: raceId,
      prompt: prompt,
      display: display,
    });
  }

  function reviewUrl(raceId) {
    return chatUrl({
      mode: "review",
      race_id: raceId,
      prompt: "この予想について相談したい",
      display: "この予想について相談したい",
    });
  }

  function personalChatUrl() {
    return chatUrl({ mode: "chat" });
  }

  /**
   * レース詳細では prediction-bind の「KAOBAに◎の理由を聞く」リンクのみ残す。
   * 旧 CTA カード（相談ボタン / Prediction Read Only）はマウントしない。
   */
  function mountRaceCtas(raceId) {
    if (!raceId) return;
    var legacy = document.getElementById("v5ConversationCtas");
    if (legacy && legacy.parentNode) legacy.parentNode.removeChild(legacy);
  }

  function ensureMenuLink(nav, id, href, label) {
    var link = document.getElementById(id);
    if (link) {
      link.setAttribute("href", href);
      // テキストノードをラベルに揃える（末尾 › は維持）
      var span = link.querySelector("span");
      link.textContent = "";
      link.appendChild(document.createTextNode(label + " "));
      if (span) link.appendChild(span);
      else {
        var chevron = document.createElement("span");
        chevron.textContent = "›";
        link.appendChild(chevron);
      }
      return link;
    }
    link = document.createElement("a");
    link.id = id;
    link.href = href;
    link.innerHTML = label + " <span>›</span>";
    nav.appendChild(link);
    return link;
  }

  /**
   * マイページメニューを保証する。
   * 本番で menu-list 欠落 / プロフィール・通知・チャット未表示の場合に再生成する。
   */
  function ensureMypageMenu() {
    var screen = document.querySelector(".page-mypage .screen, body.page-tab[data-nav='mypage'] .screen");
    if (!screen) screen = document.querySelector(".screen");
    var section = document.querySelector(".mypage-menu-section");
    var nav = document.getElementById("mypageMenu") || document.querySelector(".menu-list");

    if (!section && screen) {
      section = document.createElement("section");
      section.className = "mypage-menu-section";
      section.setAttribute("aria-labelledby", "mypageMenuHeading");
      section.innerHTML = '<h3 id="mypageMenuHeading" class="mypage-menu-heading">メニュー</h3>';
      var stats = screen.querySelector(".stats-grid");
      var admin = document.getElementById("adminInvitePanel");
      if (stats && stats.parentNode) {
        stats.parentNode.insertBefore(section, stats.nextSibling);
      } else if (admin && admin.parentNode) {
        admin.parentNode.insertBefore(section, admin);
      } else {
        screen.appendChild(section);
      }
    }

    if (!nav && section) {
      nav = document.createElement("nav");
      nav.className = "menu-list";
      nav.id = "mypageMenu";
      nav.setAttribute("aria-label", "マイページメニュー");
      section.appendChild(nav);
    } else if (nav && section && nav.parentNode !== section) {
      section.appendChild(nav);
    }

    if (!nav) return null;

    nav.id = nav.id || "mypageMenu";

    var chat = ensureMenuLink(nav, "mypagePersonalChatLink", personalChatUrl(), "チャットルーム");
    if (chat) chat.classList.add("menu-list-chat");
    var profile = ensureMenuLink(nav, "mypageProfileLink", "profile.html", "プロフィール設定");
    var notify = ensureMenuLink(nav, "mypageNotifyLink", "profile.html#notify", "通知設定");
    ensureMenuLink(nav, "mypageSavedLink", "saved.html", "今月の成績");
    ensureMenuLink(nav, "logoutLink", "#", "ログアウト");

    var ordered = [chat, profile, notify];
    for (var i = ordered.length - 1; i >= 0; i--) {
      if (ordered[i] && ordered[i].parentNode === nav) {
        nav.insertBefore(ordered[i], nav.firstChild);
      }
    }
    return nav;
  }

  function bindMypagePersonalChat() {
    ensureMypageMenu();
    var link = document.getElementById("mypagePersonalChatLink");
    if (link) link.setAttribute("href", personalChatUrl());
  }

  global.ExpectConversationUi = {
    chatUrl: chatUrl,
    explainUrl: explainUrl,
    reviewUrl: reviewUrl,
    personalChatUrl: personalChatUrl,
    mountRaceCtas: mountRaceCtas,
    ensureMypageMenu: ensureMypageMenu,
    bindMypagePersonalChat: bindMypagePersonalChat,
  };
})(window);

 -->
