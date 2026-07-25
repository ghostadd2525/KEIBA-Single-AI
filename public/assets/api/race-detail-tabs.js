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

  /** PI 出馬表の混入（性齢・DBリンク・騎手・斤量）を馬名から除去 */
  function cleanHorseName(name) {
    var n = String(name == null ? "" : name).trim();
    if (!n || n === "—") return "—";
    var sexCut = n.match(/^(.+?)\s+[牡牝セ]\s*\d/);
    if (sexCut && sexCut[1]) return sexCut[1].trim();
    var dbIdx = n.indexOf("のデータベース");
    if (dbIdx > 0) return n.slice(0, dbIdx).replace(/\s+[牡牝セ]\s*\d.*$/, "").trim() || n;
    return n;
  }

  function displayFrame(frame) {
    var n = Number(frame);
    if (!Number.isFinite(n) || n < 1) return "—";
    return String(n);
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
          escapeHtml(displayFrame(e.frame_number)) +
          "</span></td>" +
          '<td class="col-num">' +
          escapeHtml(e.horse_number != null ? e.horse_number : "—") +
          "</td>" +
          '<td class="col-name">' +
          escapeHtml(cleanHorseName(e.horse_name)) +
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
          escapeHtml(cleanHorseName(e.horse_name)) +
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
      "<thead><tr><th>人気</th><th>馬番</th><th>馬名</th><th>単勝オッズ</th></tr></thead>" +
      "<tbody>" +
      rows +
      "</tbody></table></div>"
    );
  }

  function circleHorseNum(n) {
    var num = Number(n);
    if (Number.isFinite(num) && num >= 1 && num <= 20) {
      return String.fromCharCode(0x245f + num);
    }
    return num != null && Number.isFinite(num) ? String(num) : "—";
  }

  function formatHistoryDate(v) {
    var s = String(v == null ? "" : v).trim();
    if (!s) return "";
    var m = s.match(/(\d{4})[\/\-]?(\d{1,2})[\/\-]?(\d{1,2})/);
    if (!m) return s;
    return (
      m[1] +
      "/" +
      String(Number(m[2])).padStart(2, "0") +
      "/" +
      String(Number(m[3])).padStart(2, "0")
    );
  }

  function formatSurfaceDistance(r) {
    var surface = String((r && r.surface) || "").trim();
    var dist = r && r.distance != null && r.distance !== "" ? Number(r.distance) : NaN;
    var distLabel = Number.isFinite(dist) ? String(dist) + "m" : "";
    if (surface && distLabel) {
      if (/m$/i.test(surface) || surface.indexOf(String(dist)) >= 0) return surface;
      return surface + distLabel;
    }
    return surface || distLabel || "";
  }

  function mergeHistoryRows(entries, history) {
    var byNum = Object.create(null);
    (history || []).forEach(function (h) {
      if (h && h.horse_number != null) {
        byNum[String(h.horse_number)] = h;
      }
    });
    if (entries && entries.length) {
      return entries.map(function (e) {
        var hit = byNum[String(e.horse_number)];
        return {
          horse_number: e.horse_number,
          horse_name: e.horse_name,
          recent: hit && Array.isArray(hit.recent) ? hit.recent : [],
        };
      });
    }
    return (history || []).map(function (h) {
      return {
        horse_number: h.horse_number,
        horse_name: h.horse_name,
        recent: Array.isArray(h.recent) ? h.recent : [],
      };
    });
  }

  function recentRaceHtml(r) {
    var lines = [];
    var date = formatHistoryDate(r && r.date);
    if (date) lines.push('<div class="board-acc-line board-acc-line--date">' + escapeHtml(date) + "</div>");
    lines.push(
      '<div class="board-acc-line board-acc-line--finish">' +
        escapeHtml(formatFinish(r && r.finish)) +
        "</div>"
    );
    if (r && r.race_name) {
      lines.push(
        '<div class="board-acc-line board-acc-line--race">' +
          escapeHtml(r.race_name) +
          "</div>"
      );
    }
    var sd = formatSurfaceDistance(r);
    if (sd) {
      lines.push(
        '<div class="board-acc-line board-acc-line--track">' + escapeHtml(sd) + "</div>"
      );
    }
    return '<li class="board-acc-race">' + lines.join("") + "</li>";
  }

  function historyHtml(history, entries) {
    var rows = mergeHistoryRows(entries || [], history || []);
    if (!rows.length) {
      return '<p class="muted">近走データはありません</p>';
    }
    return (
      '<div class="board-acc" role="list">' +
      rows
        .map(function (h, idx) {
          var id = "board-acc-" + idx;
          var recent = (h.recent || []).slice(0, 3);
          var panelBody;
          if (!recent.length) {
            panelBody =
              '<p class="board-history-empty muted">近走データはありません</p>';
          } else {
            panelBody =
              '<ul class="board-acc-races">' +
              recent.map(recentRaceHtml).join("") +
              "</ul>";
          }
          return (
            '<div class="board-acc-item" role="listitem">' +
            '<button type="button" class="board-acc-trigger" aria-expanded="false" aria-controls="' +
            id +
            '" id="' +
            id +
            '-btn">' +
            '<span class="board-acc-num">' +
            escapeHtml(circleHorseNum(h.horse_number)) +
            "</span>" +
            '<span class="board-acc-name">' +
            escapeHtml(cleanHorseName(h.horse_name)) +
            "</span>" +
            '<span class="board-acc-chevron" aria-hidden="true"></span>' +
            "</button>" +
            '<div class="board-acc-panel" id="' +
            id +
            '" role="region" aria-labelledby="' +
            id +
            '-btn">' +
            '<div class="board-acc-panel-inner">' +
            panelBody +
            "</div></div></div>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  function bindHistoryAccordion(root) {
    if (!root || root.dataset.accBound === "1") return;
    root.dataset.accBound = "1";
    root.addEventListener("click", function (e) {
      var btn = e.target.closest(".board-acc-trigger");
      if (!btn || !root.contains(btn)) return;
      e.preventDefault();
      var item = btn.closest(".board-acc-item");
      if (!item) return;
      var panel = item.querySelector(".board-acc-panel");
      var open = !item.classList.contains("is-open");
      item.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      if (panel) panel.setAttribute("aria-hidden", open ? "false" : "true");
    });
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

      function renderRows(rows) {
        hideTabLoading(el);
        el.dataset.accBound = "";
        el.innerHTML = historyHtml(rows.history, rows.entries);
        bindHistoryAccordion(el);
      }

      ensureHistory()
        .then(function (history) {
          var entries =
            (cache.board && cache.board.entries) ||
            [];
          renderRows({ history: history || [], entries: entries });
        })
        .catch(function () {
          return ensureBoard()
            .then(function (data) {
              renderRows({
                history: [],
                entries: (data && data.entries) || [],
              });
            })
            .catch(function () {
              hideTabLoading(el);
              el.innerHTML =
                '<p class="muted">近走データの取得に失敗しました。</p>';
            });
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
