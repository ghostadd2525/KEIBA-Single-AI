/**
 * Race detail tabs — AI予想 / 出馬表 / オッズ / データ
 * Version7.2: Board / Odds / History を完全分離
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

  function resolveHorseNumber(e) {
    if (!e || typeof e !== "object") return null;
    var raw =
      e.horse_number != null
        ? e.horse_number
        : e.number != null
          ? e.number
          : e.umaban != null
            ? e.umaban
            : null;
    var n = Number(raw);
    if (!Number.isFinite(n) || n < 1) return null;
    return n;
  }

  function resolvePopularity(e) {
    if (!e || typeof e !== "object") return null;
    var raw = e.popularity != null ? e.popularity : e.ninki != null ? e.ninki : null;
    var n = Number(raw);
    if (!Number.isFinite(n) || n < 1) return null;
    return n;
  }

  function shutubaHtml(entries) {
    if (!entries || !entries.length) {
      return '<p class="muted">出馬表データを取得できませんでした。</p>';
    }
    var rows = entries
      .map(function (e) {
        var hn = resolveHorseNumber(e);
        return (
          "<tr>" +
          '<td class="col-frame"><span class="' +
          frameClass(e.frame_number) +
          '">' +
          escapeHtml(displayFrame(e.frame_number)) +
          "</span></td>" +
          '<td class="col-num">' +
          escapeHtml(hn != null ? hn : "—") +
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
      var ha = resolveHorseNumber(a) || 0;
      var hb = resolveHorseNumber(b) || 0;
      return ha - hb;
    });
    var rows = sorted
      .map(function (e, i) {
        var hn = resolveHorseNumber(e);
        var pop = resolvePopularity(e);
        if (pop == null && published) pop = i + 1;
        return (
          "<tr>" +
          '<td class="col-pop">' +
          escapeHtml(pop != null ? pop : "—") +
          "</td>" +
          '<td class="col-num">' +
          escapeHtml(hn != null ? hn : "—") +
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
    var dist =
      r && r.distance != null && r.distance !== "" ? Number(r.distance) : NaN;
    var distLabel = Number.isFinite(dist) ? String(dist) + "m" : "";
    if (!surface && !distLabel) return "";
    if (surface === "芝" || surface === "ダ" || surface === "障") {
      return distLabel ? surface + distLabel : surface;
    }
    if (surface && distLabel) {
      if (/m$/i.test(surface) || surface.indexOf(String(dist)) >= 0) {
        return surface;
      }
      return surface + distLabel;
    }
    return surface || distLabel || "";
  }

  /** PI history `place` → venue label (domestic: 1札幌6 → 札幌; overseas: as-is). */
  function venueFromPlace(place) {
    var s = String(place == null ? "" : place).trim();
    if (!s) return "";
    var domestic = s.match(/^\d+(.+?)\d+$/);
    if (domestic && domestic[1]) return domestic[1].trim();
    return s;
  }

  /** Parenthetical suffix in PI race_name is grade/class (e.g. 函館スプリントS(GIII)). */
  function splitRaceNameGrade(raceName) {
    var raw = String(raceName == null ? "" : raceName).trim();
    if (!raw) return { title: "", grade: "" };
    var m = raw.match(/^(.+?)\(([^)]+)\)\s*$/);
    if (!m) return { title: raw, grade: "" };
    return { title: m[1].trim(), grade: m[2].trim() };
  }

  function recentRaceHtml(r) {
    var date = formatHistoryDate(r && r.date);
    var compactDate = date
      ? date.replace(/^(\d{4})\/0?(\d+)\/0?(\d+)$/, function (_, y, m, d) {
          return y + "/" + Number(m) + "/" + Number(d);
        })
      : "";
    var venue = venueFromPlace(r && r.place);
    var nameParts = splitRaceNameGrade(r && r.race_name);
    var surfaceDistance = formatSurfaceDistance(r);
    var finish = formatFinish(r && r.finish);
    var title = nameParts.title || "—";

    var subBits = [];
    if (compactDate) {
      subBits.push(
        '<span class="board-acc-race-date">' + escapeHtml(compactDate) + "</span>"
      );
    }
    if (venue) {
      subBits.push(
        '<span class="board-acc-race-venue">' + escapeHtml(venue) + "</span>"
      );
    }
    if (surfaceDistance) {
      subBits.push(
        '<span class="board-acc-race-sd">' +
          escapeHtml(surfaceDistance) +
          "</span>"
      );
    }

    return (
      '<li class="board-acc-race">' +
      '<div class="board-acc-race-main">' +
      '<div class="board-acc-race-head">' +
      '<span class="board-acc-race-title">' +
      escapeHtml(title) +
      "</span>" +
      (nameParts.grade
        ? '<span class="board-acc-race-grade">' +
          escapeHtml(nameParts.grade) +
          "</span>"
        : "") +
      "</div>" +
      '<span class="board-acc-race-finish">' +
      escapeHtml(finish) +
      "</span>" +
      "</div>" +
      (subBits.length
        ? '<div class="board-acc-race-sub">' +
          subBits.join(
            '<span class="board-acc-race-sep" aria-hidden="true">·</span>'
          ) +
          "</div>"
        : "") +
      "</li>"
    );
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
          var hn = h.horse_number != null ? h.horse_number : "—";
          return (
            '<div class="board-acc-item" role="listitem">' +
            '<button type="button" class="board-acc-trigger" aria-expanded="false" aria-controls="' +
            id +
            '" id="' +
            id +
            '-btn">' +
            '<span class="board-acc-num">' +
            escapeHtml(String(hn)) +
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
            '-btn" aria-hidden="true">' +
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
      var willOpen = !item.classList.contains("is-open");
      root.querySelectorAll(".board-acc-item.is-open").forEach(function (other) {
        if (other === item) return;
        other.classList.remove("is-open");
        var ob = other.querySelector(".board-acc-trigger");
        var op = other.querySelector(".board-acc-panel");
        if (ob) ob.setAttribute("aria-expanded", "false");
        if (op) op.setAttribute("aria-hidden", "true");
      });
      var panel = item.querySelector(".board-acc-panel");
      item.classList.toggle("is-open", willOpen);
      btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      if (panel) panel.setAttribute("aria-hidden", willOpen ? "false" : "true");
    });
  }

  function skeletonHtml(rows) {
    rows = rows || 6;
    var html = '<div class="skel-stack" aria-busy="true" aria-label="読み込み中">';
    for (var i = 0; i < rows; i++) {
      html +=
        '<div class="skel-row">' +
        '<span class="skel-block skel-block--sm"></span>' +
        '<span class="skel-block skel-block--lg"></span>' +
        "</div>";
    }
    return html + "</div>";
  }

  function bindTabs(raceId) {
    var tabs = document.getElementById("detailTabs");
    if (!tabs || tabs.dataset.boardBound === "1") return;
    tabs.dataset.boardBound = "1";

    var cache = {
      board: null,
      history: null,
      oddsView: null,
      loadingBoard: null,
      loadingHistory: null,
      activeTab: "ai",
      oddsTimer: null,
      paintedShutuba: false,
      paintedOdds: false,
      paintedData: false,
      warmed: false,
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

    function persistBoardHistory(board, history) {
      if (!global.ExpectRaceDetailCache || !ExpectRaceDetailCache.putIfReady) return;
      try {
        // READY + 馬番確定 + Prediction 整合が揃うまで永続化しない
        ExpectRaceDetailCache.putIfReady(raceId, {
          board: board || null,
          history: history != null ? history : (board && board.history) || null,
          post_time: board && board.post_time,
          date: board && board.date,
        }).catch(function () { /* ignore */ });
      } catch (e) { /* ignore */ }
    }

    function hydrateFromDurableCache() {
      if (!global.ExpectRaceDetailCache || !ExpectRaceDetailCache.get) {
        return Promise.resolve(null);
      }
      return ExpectRaceDetailCache.get(raceId).then(function (row) {
        if (!row) return null;
        if (row.board) cache.board = row.board;
        if (row.history) cache.history = row.history;
        else if (row.board && Array.isArray(row.board.history)) {
          cache.history = row.board.history;
        }
        return row;
      });
    }

    /** 一覧 Visible Prefetch の session キャッシュ */
    function hydrateFromSoftPrefetch() {
      if (!global.ExpectRacePrefetch || !ExpectRacePrefetch.getBoard) return null;
      var soft = ExpectRacePrefetch.getBoard(raceId);
      if (!soft || !soft.board) return null;
      cache.board = soft.board;
      cache.history =
        soft.history != null
          ? soft.history
          : Array.isArray(soft.board.history)
            ? soft.board.history
            : cache.history || [];
      return soft;
    }

    function ensureBoard(force) {
      // force=true でも Board 再取得はしない（メモリキャッシュ優先）
      if (!force && cache.board) return Promise.resolve(cache.board);
      if (force && cache.board) return Promise.resolve(cache.board);
      if (cache.loadingBoard) return cache.loadingBoard;

      if (hydrateFromSoftPrefetch() && cache.board) {
        return Promise.resolve(cache.board);
      }

      cache.loadingBoard = hydrateFromDurableCache()
        .then(function (row) {
          if (row && row.board) {
            cache.loadingBoard = null;
            return cache.board;
          }
          if (hydrateFromSoftPrefetch() && cache.board) {
            cache.loadingBoard = null;
            return cache.board;
          }
          // Version7.2: board は history なし
          return ExpectApi.RaceBoard.getBoard(raceId, {
            fresh: false,
            timeoutMs: 20000,
          }).then(function (data) {
            cache.board = data;
            if (global.ExpectRacePrefetch && ExpectRacePrefetch.putBoard) {
              ExpectRacePrefetch.putBoard(
                raceId,
                cache.board,
                cache.history || null
              );
            }
            persistBoardHistory(cache.board, cache.history || null);
            cache.loadingBoard = null;
            return data;
          });
        })
        .catch(function (err) {
          cache.loadingBoard = null;
          throw err;
        });
      return cache.loadingBoard;
    }

    function ensureHistory() {
      if (cache.history && cache.historyLoaded) {
        return Promise.resolve(cache.history);
      }
      if (cache.loadingHistory) return cache.loadingHistory;

      cache.loadingHistory = hydrateFromDurableCache()
        .then(function (row) {
          if (row && Array.isArray(row.history) && row.history.length) {
            cache.history = row.history;
            cache.historyLoaded = true;
            cache.loadingHistory = null;
            return cache.history;
          }
          var getter =
            global.ExpectApi &&
            ExpectApi.RaceHistory &&
            typeof ExpectApi.RaceHistory.getHistory === "function"
              ? ExpectApi.RaceHistory.getHistory(raceId, { timeoutMs: 60000 })
              : Promise.reject(new Error("RaceHistory unavailable"));
          return getter.then(function (data) {
            var hist =
              (data && Array.isArray(data.history) && data.history) ||
              (Array.isArray(data) ? data : []) ||
              [];
            cache.history = hist;
            cache.historyLoaded = true;
            if (global.ExpectRacePrefetch && ExpectRacePrefetch.putBoard && cache.board) {
              ExpectRacePrefetch.putBoard(raceId, cache.board, cache.history);
            }
            persistBoardHistory(cache.board, cache.history);
            cache.loadingHistory = null;
            return cache.history;
          });
        })
        .catch(function (err) {
          cache.loadingHistory = null;
          throw err;
        });
      return cache.loadingHistory;
    }

    function mergeOddsSeriesIntoBoard(board, seriesData) {
      if (!board || !Array.isArray(board.entries)) return board;
      var map = Object.create(null);
      var pop = Object.create(null);
      (seriesData && seriesData.series ? seriesData.series : []).forEach(function (s, idx) {
        var n = s.umaban != null ? s.umaban : s.horse_number;
        if (n == null) return;
        if (s.latest_odds != null && Number.isFinite(Number(s.latest_odds))) {
          map[String(n)] = Number(s.latest_odds);
        }
        if (s.popularity != null) pop[String(n)] = s.popularity;
        else if (map[String(n)] != null) pop[String(n)] = idx + 1;
      });
      if (!Object.keys(map).length) return board;
      var merged = {
        schema_version: board.schema_version,
        race_id: board.race_id,
        race_label: board.race_label,
        race_name: board.race_name,
        date: board.date,
        venue: board.venue,
        race_no: board.race_no,
        post_time: board.post_time,
        numeric_race_id: board.numeric_race_id,
        odds_status: (seriesData && seriesData.odds_status) || board.odds_status,
        odds_cache_ttl_sec: board.odds_cache_ttl_sec,
        count: board.count,
        entries: board.entries.map(function (e) {
          var copy = {};
          for (var k in e) {
            if (Object.prototype.hasOwnProperty.call(e, k)) copy[k] = e[k];
          }
          var key = String(e.horse_number != null ? e.horse_number : "");
          if (key && map[key] != null) copy.odds = map[key];
          if (key && pop[key] != null) copy.popularity = pop[key];
          return copy;
        }),
      };
      return merged;
    }

    /** Odds / Odds Series のみ最新取得。Board 本体は再取得しない */
    function refreshOddsOnly(opts) {
      opts = opts || {};
      var silent = !!opts.silent;
      var el = document.getElementById("tabOddsBody");
      if (!cache.board) {
        return ensureBoard().then(function () {
          return refreshOddsOnly(opts);
        });
      }
      if (!global.ExpectApi || !ExpectApi.OddsSeries || !ExpectApi.OddsSeries.getSeries) {
        if (el && cache.board) paintOddsFromBoard(cache.board, { silent: silent });
        return Promise.resolve(cache.board);
      }
      return ExpectApi.OddsSeries.getSeries(raceId, { fresh: true })
        .then(function (seriesData) {
          var merged = mergeOddsSeriesIntoBoard(cache.board, seriesData);
          cache.oddsView = merged;
          paintOddsFromBoard(merged, { silent: silent || !!cache.paintedOdds });
          return merged;
        })
        .catch(function () {
          if (el && cache.board && !cache.paintedOdds) {
            paintOddsFromBoard(cache.board, { silent: silent });
          }
          return cache.board;
        });
    }

    function paintShutubaFromBoard(data) {
      var el = document.getElementById("tabShutubaBody");
      if (!el || !data) return;
      hideTabLoading(el);
      el.innerHTML = shutubaHtml(data.entries);
      cache.paintedShutuba = true;
    }

    function paintOddsFromBoard(data, opts) {
      opts = opts || {};
      var el = document.getElementById("tabOddsBody");
      if (!el || !data) return;
      if (!opts.silent) hideTabLoading(el);
      el.innerHTML = oddsHtml(data.entries, data);
      cache.paintedOdds = true;
    }

    function paintDataFromHistory(history, entries) {
      var el = document.getElementById("tabDataBody");
      if (!el) return;
      hideTabLoading(el);
      el.dataset.accBound = "";
      el.innerHTML = historyHtml(history || [], entries || []);
      bindHistoryAccordion(el);
      cache.paintedData = true;
    }

    function paintShutuba() {
      var el = document.getElementById("tabShutubaBody");
      if (!el) return;
      if (cache.paintedShutuba && cache.board) {
        paintShutubaFromBoard(cache.board);
        return;
      }
      if (!el.querySelector(".skel-stack")) {
        showTabLoading(el, {
          title: "出馬表を準備中...",
          message: "出走馬データを読み込んでいます。",
        });
      }
      ensureBoard()
        .then(function (data) {
          paintShutubaFromBoard(data);
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
      var silent = !!opts.silent && !!(cache.board || cache.oddsView);
      if (cache.paintedOdds && (cache.oddsView || cache.board) && !opts.force) {
        paintOddsFromBoard(cache.oddsView || cache.board, { silent: true });
        if (opts.refresh !== false) refreshOddsOnly({ silent: true });
        return;
      }
      if (!silent && !el.querySelector(".skel-stack")) {
        showTabLoading(el, {
          title: "オッズを準備中...",
          message: "単勝オッズを取得しています。",
        });
      }
      // Version7.2: Board で即描画 → odds-series を非同期反映
      ensureBoard()
        .then(function (data) {
          paintOddsFromBoard(data, { silent: silent });
          return refreshOddsOnly({ silent: true });
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
      if (cache.paintedData && cache.historyLoaded) return;
      if (!el.querySelector(".skel-stack")) {
        showTabLoading(el, {
          title: "近走データを準備中...",
          message: "各馬の近走を取得しています。少し時間がかかることがあります。",
        });
      }

      // Board はブロックしない（名前表示用に裏で取得）
      ensureBoard().catch(function () { return null; });

      ensureHistory()
        .then(function (history) {
          var entries = (cache.board && cache.board.entries) || [];
          paintDataFromHistory(history || [], entries);
        })
        .catch(function () {
          hideTabLoading(el);
          el.innerHTML =
            '<p class="muted">近走データの取得に失敗しました。出馬表・オッズは利用できます。</p>';
        });
    }

    /** Version7.2: Board-only warm。History はデータタブ表示時のみ */
    function warm() {
      if (cache.warmed) return;
      cache.warmed = true;
      var shutuba = document.getElementById("tabShutubaBody");
      var odds = document.getElementById("tabOddsBody");
      var data = document.getElementById("tabDataBody");
      if (shutuba) shutuba.innerHTML = skeletonHtml(8);
      if (odds) odds.innerHTML = skeletonHtml(8);
      if (data) {
        data.innerHTML =
          '<p class="muted">近走は「データ」タブを開くと読み込みます。</p>';
      }

      hydrateFromDurableCache()
        .then(function (row) {
          if (row && row.board) {
            paintShutubaFromBoard(cache.board);
            paintOddsFromBoard(cache.board);
            refreshOddsOnly({ silent: true });
            return;
          }
          if (hydrateFromSoftPrefetch() && cache.board) {
            paintShutubaFromBoard(cache.board);
            paintOddsFromBoard(cache.board);
            refreshOddsOnly({ silent: true });
            return;
          }

          return ExpectApi.RaceBoard.getBoard(raceId, { timeoutMs: 20000 }).then(
            function (board) {
              cache.board = board;
              if (global.ExpectRacePrefetch && ExpectRacePrefetch.putBoard) {
                ExpectRacePrefetch.putBoard(raceId, cache.board, null);
              }
              persistBoardHistory(cache.board, null);
              paintShutubaFromBoard(board);
              paintOddsFromBoard(board);
              refreshOddsOnly({ silent: true });
            }
          );
        })
        .catch(function () {
          if (shutuba && !cache.paintedShutuba) {
            shutuba.innerHTML = '<p class="muted">出馬表の取得に失敗しました。</p>';
          }
          if (odds && !cache.paintedOdds) {
            odds.innerHTML = '<p class="muted">オッズの取得に失敗しました。</p>';
          }
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
      // Odds Series のみ定期更新（Board は再取得しない）
      cache.oddsTimer = setInterval(function () {
        if (cache.activeTab !== "odds") return;
        refreshOddsOnly({ silent: true });
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
      else if (tab === "result") paintResult();
    });

    function paintResult() {
      var body = document.getElementById("tabResultBody");
      if (!body) return;
      if (global.ExpectUserRaceResults && ExpectUserRaceResults.loadAndPaintResult) {
        ExpectUserRaceResults.loadAndPaintResult(raceId, body);
      } else {
        body.innerHTML = '<p class="muted">結果モジュールを読み込めませんでした。</p>';
      }
    }

    // Deep-link: ?tab=result
    try {
      var initTab = new URLSearchParams(location.search).get("tab");
      if (initTab && ["ai", "shutuba", "odds", "data", "result"].indexOf(initTab) >= 0) {
        setActive(initTab);
        if (initTab === "shutuba") paintShutuba();
        else if (initTab === "odds") paintOdds();
        else if (initTab === "data") paintData();
        else if (initTab === "result") paintResult();
      }
    } catch (e) { /* ignore */ }

    global.addEventListener("pagehide", stopOddsRefresh);

    // 詳細ページ入場時に即 warm（タブを開かなくても並列取得）
    warm();
  }

  global.ExpectRaceDetailTabs = {
    bind: bindTabs,
    shutubaHtml: shutubaHtml,
    oddsHtml: oddsHtml,
    historyHtml: historyHtml,
    skeletonHtml: skeletonHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
