/**
 * Race detail tabs — AI予想 / 出馬表 / オッズ / データ
 */
(function (global) {
  "use strict";

  var ODDS_REFRESH_MS = 5 * 60 * 1000;

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function frameClass(frame) {
    var n = Number(frame);
    if (!Number.isFinite(n) || n < 1) return "frame-badge frame-badge--0";
    return "frame-badge frame-badge--" + Math.min(8, Math.max(1, n));
  }

  function formatOdds(v) {
    if (v == null || v === "" || !Number.isFinite(Number(v))) return "—";
    var n = Number(v);
    // 旧フォールバック値は未発表扱い
    if (Math.abs(n - 99.9) < 0.05) return "—";
    return n >= 100 ? String(Math.round(n)) : n.toFixed(1);
  }

  function formatFinish(v) {
    if (v == null || v === "") return "—";
    var n = Number(v);
    if (Number.isFinite(n)) return n + "着";
    return String(v);
  }

  function showTabLoading(el, opts) {
    opts = opts || {};
    if (!el) return;
    if (global.ExpectUx && typeof ExpectUx.showLoading === "function") {
      ExpectUx.showLoading(el, {
        replace: true,
        compact: true,
        title: opts.title || "ロード中...",
        message: opts.message || "データを準備しています。",
        progress: opts.progress !== false,
      });
      return;
    }
    el.innerHTML = '<p class="muted">' + escapeHtml(opts.message || "読み込み中…") + "</p>";
  }

  function hideTabLoading(el) {
    if (!el) return;
    if (global.ExpectUx && typeof ExpectUx.hideLoading === "function") {
      ExpectUx.hideLoading(el);
    }
  }

  function shutubaHtml(entries) {
    if (!entries || !entries.length) {
      return '<p class="muted">出馬表データを取得できませんでした。</p>';
    }
    var rows = entries
      .map(function (e) {
        return (
          "<tr>" +
          '<td class="col-frame"><span class="' +
          frameClass(e.frame_number) +
          '">' +
          escapeHtml(e.frame_number != null ? e.frame_number : "—") +
          "</span></td>" +
          '<td class="col-num">' +
          escapeHtml(e.horse_number != null ? e.horse_number : "—") +
          "</td>" +
          '<td class="col-name">' +
          escapeHtml(e.horse_name || "—") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    return (
      '<div class="board-table-wrap">' +
      '<table class="board-table board-table--shutuba">' +
      "<thead><tr><th>枠</th><th>馬番</th><th>馬名</th></tr></thead>" +
      "<tbody>" +
      rows +
      "</tbody></table></div>"
    );
  }

  function oddsHtml(entries, meta) {
    meta = meta || {};
    if (!entries || !entries.length) {
      return '<p class="muted">オッズデータを取得できませんでした。</p>';
    }
    var published = entries.some(function (e) {
      return e.odds != null && Number.isFinite(Number(e.odds)) && Math.abs(Number(e.odds) - 99.9) >= 0.05;
    });
    var note = "";
    if (!published || meta.odds_status === "unpublished") {
      note =
        '<p class="board-odds-note muted">単勝オッズはまだ発表されていないか、取得待機中です。5分ごとに自動更新します。</p>';
    } else {
      note =
        '<p class="board-odds-note muted">単勝オッズ（約5分ごとに更新・サーバー側でキャッシュ）</p>';
    }
    var sorted = entries.slice().sort(function (a, b) {
      var oa = a.odds != null && Math.abs(Number(a.odds) - 99.9) >= 0.05 ? Number(a.odds) : 9999;
      var ob = b.odds != null && Math.abs(Number(b.odds) - 99.9) >= 0.05 ? Number(b.odds) : 9999;
      if (oa !== ob) return oa - ob;
      return (a.horse_number || 0) - (b.horse_number || 0);
    });
    var rows = sorted
      .map(function (e, i) {
        var pop =
          e.popularity != null
            ? e.popularity
            : published
              ? i + 1
              : "—";
        return (
          "<tr>" +
          '<td class="col-pop">' +
          escapeHtml(pop) +
          "</td>" +
          '<td class="col-num">' +
          escapeHtml(e.horse_number != null ? e.horse_number : "—") +
          "</td>" +
          '<td class="col-name">' +
          escapeHtml(e.horse_name || "—") +
          "</td>" +
          '<td class="col-odds">' +
          escapeHtml(formatOdds(e.odds)) +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    return (
      note +
      '<div class="board-table-wrap">' +
      '<table class="board-table board-table--odds">' +
      "<thead><tr><th>人気</th><th>馬番</th><th>馬名</th><th>単勝</th></tr></thead>" +
      "<tbody>" +
      rows +
      "</tbody></table></div>"
    );
  }

  function historyHtml(history) {
    if (!history || !history.length) {
      return '<p class="muted">近走データを取得できませんでした。</p>';
    }
    return history
      .map(function (h) {
        var recent = h.recent || [];
        var body;
        if (!recent.length) {
          body = '<p class="board-history-empty muted">近走なし</p>';
        } else {
          body =
            '<ul class="board-history-list">' +
            recent
              .map(function (r) {
                var bits = [];
                if (r.date) bits.push(escapeHtml(r.date));
                if (r.place) bits.push(escapeHtml(r.place));
                if (r.surface || r.distance) {
                  bits.push(
                    escapeHtml(
                      String(r.surface || "") +
                        (r.distance != null ? String(r.distance) + "m" : "")
                    )
                  );
                }
                if (r.race_name) bits.push(escapeHtml(r.race_name));
                return (
                  "<li>" +
                  '<span class="board-history-finish">' +
                  escapeHtml(formatFinish(r.finish)) +
                  "</span>" +
                  '<span class="board-history-meta">' +
                  bits.join(" · ") +
                  "</span>" +
                  (r.odds != null
                    ? '<span class="board-history-odds">' +
                      escapeHtml(formatOdds(r.odds)) +
                      "倍</span>"
                    : "") +
                  "</li>"
                );
              })
              .join("") +
            "</ul>";
        }
        return (
          '<article class="board-history-card">' +
          '<header class="board-history-head">' +
          '<span class="board-history-num">' +
          escapeHtml(h.horse_number != null ? h.horse_number : "—") +
          "</span>" +
          '<span class="board-history-name">' +
          escapeHtml(h.horse_name || "—") +
          "</span></header>" +
          body +
          "</article>"
        );
      })
      .join("");
  }

  function bindTabs(raceId) {
    var tabs = document.getElementById("detailTabs");
    if (!tabs || tabs.dataset.boardBound === "1") return;
    tabs.dataset.boardBound = "1";

    var cache = {
      board: null,
      history: null,
      loadingBoard: null,
      loadingHistory: null,
      activeTab: "ai",
      oddsTimer: null,
    };

    function setActive(tabName) {
      cache.activeTab = tabName;
      tabs.querySelectorAll(".chip[data-tab]").forEach(function (btn) {
        var on = btn.getAttribute("data-tab") === tabName;
        btn.classList.toggle("is-active", on);
        btn.setAttribute("aria-selected", on ? "true" : "false");
      });
      document.querySelectorAll("[data-tab-panel]").forEach(function (el) {
        var on = el.getAttribute("data-tab-panel") === tabName;
        el.hidden = !on;
      });
      if (tabName === "odds") startOddsRefresh();
      else stopOddsRefresh();
    }

    function ensureBoard(force) {
      if (!force && cache.board) return Promise.resolve(cache.board);
      if (!force && cache.loadingBoard) return cache.loadingBoard;
      cache.loadingBoard = ExpectApi.RaceBoard.getBoard(raceId, {
        includeHistory: false,
        fresh: !!force,
      })
        .then(function (data) {
          cache.board = data;
          cache.loadingBoard = null;
          return data;
        })
        .catch(function (err) {
          cache.loadingBoard = null;
          throw err;
        });
      return cache.loadingBoard;
    }

    function ensureHistory() {
      if (cache.history) return Promise.resolve(cache.history);
      if (cache.loadingHistory) return cache.loadingHistory;
      cache.loadingHistory = ExpectApi.RaceBoard.getBoard(raceId, { includeHistory: true })
        .then(function (data) {
          cache.board = data;
          cache.history = data.history || [];
          cache.loadingHistory = null;
          return cache.history;
        })
        .catch(function (err) {
          cache.loadingHistory = null;
          throw err;
        });
      return cache.loadingHistory;
    }

    function paintShutuba() {
      var el = document.getElementById("tabShutubaBody");
      if (!el) return;
      showTabLoading(el, {
        title: "出馬表を準備中...",
        message: "出走馬データを読み込んでいます。",
      });
      ensureBoard()
        .then(function (data) {
          hideTabLoading(el);
          el.innerHTML = shutubaHtml(data.entries);
        })
        .catch(function () {
          hideTabLoading(el);
          el.innerHTML = '<p class="muted">出馬表の取得に失敗しました。</p>';
        });
    }

    function paintOdds(opts) {
      opts = opts || {};
      var el = document.getElementById("tabOddsBody");
      if (!el) return;
      var silent = !!opts.silent && !!cache.board;
      if (!silent) {
        showTabLoading(el, {
          title: "オッズを準備中...",
          message: "単勝オッズを取得しています。",
        });
      }
      ensureBoard(!!opts.force)
        .then(function (data) {
          hideTabLoading(el);
          el.innerHTML = oddsHtml(data.entries, data);
        })
        .catch(function () {
          if (!silent) {
            hideTabLoading(el);
            el.innerHTML = '<p class="muted">オッズの取得に失敗しました。</p>';
          }
        });
    }

    function paintData() {
      var el = document.getElementById("tabDataBody");
      if (!el) return;
      showTabLoading(el, {
        title: "近走データを準備中...",
        message: "各馬の近走を取得しています。少し時間がかかることがあります。",
      });
      ensureHistory()
        .then(function (history) {
          hideTabLoading(el);
          el.innerHTML = historyHtml(history);
        })
        .catch(function () {
          hideTabLoading(el);
          el.innerHTML = '<p class="muted">近走データの取得に失敗しました。</p>';
        });
    }

    function stopOddsRefresh() {
      if (cache.oddsTimer) {
        clearInterval(cache.oddsTimer);
        cache.oddsTimer = null;
      }
    }

    function startOddsRefresh() {
      stopOddsRefresh();
      // サーバー側 TTL と揃えて 5 分。クライアント連打でも PI キャッシュで netkeiba を叩かない
      cache.oddsTimer = setInterval(function () {
        if (cache.activeTab !== "odds") return;
        cache.board = null;
        paintOdds({ force: true, silent: true });
      }, ODDS_REFRESH_MS);
    }

    tabs.addEventListener("click", function (e) {
      var btn = e.target.closest(".chip[data-tab]");
      if (!btn || btn.disabled) return;
      e.preventDefault();
      var tab = btn.getAttribute("data-tab");
      if (!tab) return;
      setActive(tab);
      if (tab === "shutuba") paintShutuba();
      else if (tab === "odds") paintOdds();
      else if (tab === "data") paintData();
    });

    global.addEventListener("pagehide", stopOddsRefresh);
  }

  global.ExpectRaceDetailTabs = {
    bind: bindTabs,
    shutubaHtml: shutubaHtml,
    oddsHtml: oddsHtml,
    historyHtml: historyHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
