/** 下部ナビ HTML を挿入（data-expect-nav 要素へ） */
(function () {
  var active = document.body.getAttribute("data-nav") || "home";
  var mount = document.querySelector("[data-expect-nav]");
  if (!mount) return;
  mount.outerHTML =
    '<nav class="bottom-nav" aria-label="メインメニュー">' +
    '<a href="index.html" data-nav="home"><svg class="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>ホーム</a>' +
    '<a href="races.html" data-nav="race"><svg class="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 16c2-4 4.5-6 7-6s5 2 7 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M8 10c.5-2 2-3.5 4-3.5S15.5 8 16 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="9" cy="17.5" r="1.5" stroke="currentColor" stroke-width="1.6" fill="none"/><circle cx="15" cy="17.5" r="1.5" stroke="currentColor" stroke-width="1.6" fill="none"/></svg>レース</a>' +
    '<a href="analysis.html" data-nav="analysis"><svg class="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 19h16M7 16V9M12 16V5M17 16v-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>分析</a>' +
    '<a href="saved.html" data-nav="challenge"><svg class="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 19h16M7 16V9M12 16v-7M17 16V6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M6 6.5h3.5M14.5 4h3.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>チャレンジ</a>' +
    '<a href="mypage.html" data-nav="mypage"><svg class="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6" fill="none"/><path d="M5 19.5c1.5-3.5 4-5 7-5s5.5 1.5 7 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>マイページ</a>' +
    "</nav>";
  if (window.ExpectShell) {
    ExpectShell.initNav(active);
    ExpectShell.mountGlobalTools();
  }
})();
