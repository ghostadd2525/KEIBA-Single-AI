/**
 * オッズ変動AI — 単勝オッズ折れ線チャート
 */
(function (global) {
  "use strict";

  var COLORS = [
    "#c1a26d",
    "#7eb8a8",
    "#d4a574",
    "#8fa4d4",
    "#c98989",
    "#b8c97a",
    "#d49cc8",
    "#7ab8d4",
    "#e0b06e",
    "#9a8fd4",
    "#d48f8f",
    "#8fd4b8",
  ];
  var REFRESH_MS = 5 * 60 * 1000;
  var TOP_N = 6;
  /** 直前スナップショット（オッズ変動アラート用） umaban -> latest_odds */
  var lastOddsByRace = {};

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function shortRaceName(raw) {
    var s = String(raw == null ? "" : raw).trim();
    if (!s) return "";
    var m = s.match(
      /^(.+?)\s+\d{1,2}:\d{2}(?:芝|ダート|ダ|障)?\d*m?\d*頭?\s*$/u
    );
    if (m && m[1]) return String(m[1]).trim();
    s = s
      .replace(/\s+\d{1,2}:\d{2}(?:芝|ダート|ダ|障)\d+m\d+頭\s*$/u, "")
      .replace(/\s+\d{1,2}:\d{2}\S*\s*$/u, "")
      .trim();
    return s || String(raw).trim();
  }

  function formatPostLabel(post) {
    var p = String(post == null ? "" : post).trim();
    var m = p.match(/^(\d{1,2}):(\d{2})/);
    if (m) {
      return (
        String(Number(m[1])).padStart(2, "0") + ":" + m[2] + "出走"
      );
    }
    if (!p) return "";
    return p.indexOf("出走") >= 0 ? p : p + "出走";
  }

  function raceMetaLabel(data) {
    data = data || {};
    var bits = [];
    if (data.race_label) bits.push(String(data.race_label));
    var name = shortRaceName(data.race_name || "");
    if (name) bits.push(name);
    var postLabel = formatPostLabel(data.post_time);
    if (postLabel) bits.push(postLabel);
    return bits.join(" · ");
  }

  function jstToday() {
    var fmt = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Tokyo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    return fmt.format(new Date());
  }

  /** 開催日（土日でなければ次の土日）。例: 7/25 土を返す */
  function resolveRaceDates() {
    if (global.ExpectWeekendCalendar && ExpectWeekendCalendar.weekendRaceDates) {
      return ExpectWeekendCalendar.weekendRaceDates(new Date()).filter(Boolean);
    }
    if (global.ExpectApi && ExpectApi.Race && ExpectApi.Race.resolveListDate) {
      var d = ExpectApi.Race.resolveListDate({});
      return d ? [d] : [];
    }
    if (global.ExpectRaceListUrl && ExpectRaceListUrl.calendarFallbackDate) {
      var fb = ExpectRaceListUrl.calendarFallbackDate(new Date());
      return fb ? [fb] : [];
    }
    var today = jstToday();
    return today ? [today] : [];
  }

  function dateLabel(iso) {
    var p = String(iso || "").split("-");
    if (p.length !== 3) return iso || "";
    return Number(p[1]) + "/" + Number(p[2]);
  }

  function fmtOdds(v) {
    if (v == null || !Number.isFinite(Number(v))) return "—";
    var n = Number(v);
    return n >= 100 ? String(Math.round(n)) : n.toFixed(1);
  }

  function fmtTime(at) {
    if (!at) return "";
    var m = String(at).match(/T(\d{2}:\d{2})/);
    return m ? m[1] : String(at).slice(11, 16);
  }

  function buildPolyline(points, x0, y0, w, h, yMin, yMax) {
    var usable = points.filter(function (p) {
      return p.odds != null && Number.isFinite(Number(p.odds));
    });
    if (!usable.length) return "";
    var n = Math.max(points.length - 1, 1);
    var span = Math.max(yMax - yMin, 0.1);
    return usable
      .map(function (p) {
        var idx = points.indexOf(p);
        var x = x0 + (idx / n) * w;
        var y = y0 + h - ((Number(p.odds) - yMin) / span) * h;
        return x.toFixed(1) + "," + y.toFixed(1);
      })
      .join(" ");
  }

  function renderChart(svg, seriesList, timestamps) {
    if (!svg) return;
    var W = 640;
    var H = 280;
    var pad = { t: 18, r: 16, b: 36, l: 44 };
    var x0 = pad.l;
    var y0 = pad.t;
    var w = W - pad.l - pad.r;
    var h = H - pad.t - pad.b;

    var allOdds = [];
    seriesList.forEach(function (s) {
      (s.points || []).forEach(function (p) {
        if (p.odds != null && Number.isFinite(Number(p.odds))) allOdds.push(Number(p.odds));
      });
    });
    if (!allOdds.length) {
      svg.innerHTML =
        '<text x="50%" y="50%" text-anchor="middle" fill="#9aa3b2" font-size="14">オッズデータがありません</text>';
      return;
    }

    var yMin = Math.min.apply(null, allOdds);
    var yMax = Math.max.apply(null, allOdds);
    var padY = Math.max((yMax - yMin) * 0.12, 0.3);
    yMin = Math.max(1, yMin - padY);
    yMax = yMax + padY;

    var parts = [];
    parts.push(
      '<rect x="0" y="0" width="' +
        W +
        '" height="' +
        H +
        '" fill="transparent"></rect>'
    );

    // grid
    for (var g = 0; g <= 4; g++) {
      var gy = y0 + (h * g) / 4;
      var gv = yMax - ((yMax - yMin) * g) / 4;
      parts.push(
        '<line x1="' +
          x0 +
          '" y1="' +
          gy.toFixed(1) +
          '" x2="' +
          (x0 + w) +
          '" y2="' +
          gy.toFixed(1) +
          '" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>'
      );
      parts.push(
        '<text x="' +
          (x0 - 8) +
          '" y="' +
          (gy + 4).toFixed(1) +
          '" text-anchor="end" fill="#9aa3b2" font-size="11">' +
          escapeHtml(fmtOdds(gv)) +
          "</text>"
      );
    }

    seriesList.forEach(function (s, i) {
      var color = COLORS[i % COLORS.length];
      var pts = s.points || [];
      var poly = buildPolyline(pts, x0, y0, w, h, yMin, yMax);
      if (!poly) return;
      var n = Math.max(pts.length - 1, 1);
      if (pts.length === 1) {
        var ox = x0;
        var oy =
          y0 +
          h -
          ((Number(pts[0].odds) - yMin) / Math.max(yMax - yMin, 0.1)) * h;
        parts.push(
          '<circle cx="' +
            ox.toFixed(1) +
            '" cy="' +
            oy.toFixed(1) +
            '" r="4.5" fill="' +
            color +
            '"/>'
        );
      } else {
        parts.push(
          '<polyline fill="none" stroke="' +
            color +
            '" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" points="' +
            poly +
            '"/>'
        );
        pts.forEach(function (p, idx) {
          if (p.odds == null) return;
          var x = x0 + (idx / n) * w;
          var y =
            y0 +
            h -
            ((Number(p.odds) - yMin) / Math.max(yMax - yMin, 0.1)) * h;
          parts.push(
            '<circle cx="' +
              x.toFixed(1) +
              '" cy="' +
              y.toFixed(1) +
              '" r="3.2" fill="' +
              color +
              '"/>'
          );
        });
      }
    });

    // x labels
    var labels = timestamps || [];
    if (labels.length) {
      var showIdx = [0];
      if (labels.length > 2) showIdx.push(Math.floor((labels.length - 1) / 2));
      if (labels.length > 1) showIdx.push(labels.length - 1);
      var seen = {};
      showIdx.forEach(function (idx) {
        if (seen[idx]) return;
        seen[idx] = true;
        var x = x0 + (idx / Math.max(labels.length - 1, 1)) * w;
        parts.push(
          '<text x="' +
            x.toFixed(1) +
            '" y="' +
            (H - 12) +
            '" text-anchor="middle" fill="#9aa3b2" font-size="11">' +
            escapeHtml(fmtTime(labels[idx])) +
            "</text>"
        );
      });
    }

    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.innerHTML = parts.join("");
  }

  function legendHtml(seriesList) {
    return (
      '<ul class="odds-legend">' +
      seriesList
        .map(function (s, i) {
          return (
            "<li>" +
            '<i style="background:' +
            COLORS[i % COLORS.length] +
            '"></i>' +
            "<span>" +
            escapeHtml(s.horse_number) +
            " " +
            escapeHtml(s.horse_name || "") +
            "</span>" +
            "<b>" +
            escapeHtml(fmtOdds(s.latest_odds)) +
            "</b>" +
            "</li>"
          );
        })
        .join("") +
      "</ul>"
    );
  }

  function bind() {
    var raceListEl =
      document.getElementById("oddsRaceAccordion") ||
      document.getElementById("oddsRaceSelect") ||
      document.getElementById("oddsRaceList");
    var dateTabs = document.getElementById("oddsDateTabs");
    var venueChips = document.getElementById("oddsVenueChips");
    var filterNote = document.getElementById("oddsFilterNote");
    var chartCard = document.getElementById("oddsChartCard");
    var chartSvg = document.getElementById("oddsLineChart");
    var legendEl = document.getElementById("oddsLegend");
    var metaEl = document.getElementById("oddsChartMeta");
    var noteEl = document.getElementById("oddsChartNote");
    if (!raceListEl || !chartSvg) return;

    var state = {
      raceId: "",
      timer: null,
      loading: false,
      allItems: [],
      date: "all",
      venue: "all",
      openVenue: null,
      accordionClosed: false,
    };

    function ensureSvg() {
      var mount = document.getElementById("oddsChartMount");
      var svg = document.getElementById("oddsLineChart");
      if (svg && mount && mount.contains(svg)) return svg;
      if (!mount) return null;
      mount.innerHTML =
        '<svg class="odds-line-chart" id="oddsLineChart" viewBox="0 0 640 280" role="img" aria-label="単勝オッズの折れ線グラフ"></svg>';
      chartSvg = document.getElementById("oddsLineChart");
      return chartSvg;
    }

    function setBusy(on) {
      if (chartCard) chartCard.classList.toggle("is-loading", !!on);
      var mount = document.getElementById("oddsChartMount");
      if (!mount || !global.ExpectUx) return;
      if (on) {
        ExpectUx.showLoading(mount, {
          replace: false,
          compact: true,
          title: "オッズを取得中...",
          message: "単勝オッズの時系列を準備しています。",
        });
      } else {
        ExpectUx.hideLoading(mount);
      }
    }

    function detectOddsAlert(data) {
      var raceId = data && data.race_id;
      if (!raceId) return;
      var prev = lastOddsByRace[raceId] || null;
      var next = {};
      var series = Array.isArray(data.series) ? data.series : [];
      var movers = [];
      series.forEach(function (s) {
        var key = String(s.umaban != null ? s.umaban : s.horse_name || "");
        if (!key) return;
        var odds = s.latest_odds != null ? Number(s.latest_odds) : NaN;
        if (!Number.isFinite(odds) || odds <= 0) return;
        next[key] = odds;
        if (!prev || prev[key] == null) return;
        var before = Number(prev[key]);
        if (!Number.isFinite(before) || before <= 0) return;
        var ratio = Math.abs(odds - before) / before;
        // 相対10%以上、かつ絶対差0.5以上を「変動」とみなす
        if (ratio >= 0.1 && Math.abs(odds - before) >= 0.5) {
          movers.push({
            name: s.horse_name || key + "番",
            before: before,
            after: odds,
            down: odds < before,
          });
        }
      });
      lastOddsByRace[raceId] = next;
      if (!prev || !movers.length) return;
      movers.sort(function (a, b) {
        return Math.abs(b.after - b.before) / b.before - Math.abs(a.after - a.before) / a.before;
      });
      var top = movers[0];
      var label = data.race_label || data.race_name || "選択中レース";
      var msg =
        label +
        "<br><strong>" +
        top.name +
        "</strong> " +
        fmtOdds(top.before) +
        " → " +
        fmtOdds(top.after) +
        (top.down ? "（短縮）" : "（延長）");
      if (global.ExpectUserPrefs && ExpectUserPrefs.alertOdds) {
        ExpectUserPrefs.alertOdds(msg);
      }
    }

    function paint(data) {
      setBusy(false);
      var svg = ensureSvg();
      if (!svg) return;
      var all = Array.isArray(data.series) ? data.series.slice() : [];
      var top = all
        .filter(function (s) {
          return s.latest_odds != null;
        })
        .slice(0, TOP_N);
      if (!top.length) top = all.slice(0, TOP_N);

      detectOddsAlert(data);
      renderChart(svg, top, data.timestamps || []);
      if (legendEl) legendEl.innerHTML = legendHtml(top);

      var pc = data.point_count || 0;
      if (metaEl) {
        var base = raceMetaLabel(data);
        metaEl.textContent =
          (base ? base + " · " : "") + "記録 " + pc + "点";
      }
      if (noteEl) {
        if (pc < 2) {
          noteEl.textContent =
            "まだ記録点が少ないため点表示です。約5分ごとに自動取得し、折れ線が伸びていきます。";
        } else {
          noteEl.textContent =
            "単勝オッズの推移（人気上位" + TOP_N + "頭）。約5分間隔で更新します。";
        }
      }
    }

    function load(refresh) {
      var id = state.raceId;
      if (!id || state.loading) return Promise.resolve();
      state.loading = true;
      setBusy(true);
      return ExpectApi.OddsSeries.getSeries(id, {
        refresh: !!refresh,
        fresh: true,
      })
        .then(function (data) {
          state.loading = false;
          paint(data);
        })
        .catch(function () {
          state.loading = false;
          setBusy(false);
          var svg = ensureSvg();
          if (noteEl) noteEl.textContent = "オッズ時系列の取得に失敗しました。";
          if (legendEl) legendEl.innerHTML = "";
          if (svg) {
            svg.innerHTML =
              '<text x="50%" y="50%" text-anchor="middle" fill="#9aa3b2" font-size="14">取得に失敗しました</text>';
          }
        });
    }

    function startTimer() {
      if (state.timer) clearInterval(state.timer);
      state.timer = setInterval(function () {
        // 発走済みを候補から落とす
        renderFilters();
        applyFilterChange();
        load(true);
      }, REFRESH_MS);
    }

    function itemDate(r) {
      return (
        (r.race_info && r.race_info.date) ||
        (String(r.race_id || "").match(/^(\d{4}-\d{2}-\d{2})/) || [])[1] ||
        ""
      );
    }

    function itemVenue(r) {
      return (r.race_info && r.race_info.venue) || r.course || "";
    }

    function itemPostTime(r) {
      return (
        (r.race_info && r.race_info.post_time) ||
        r.post_time ||
        ""
      );
    }

    /** 発走時刻を過ぎたレースは候補から除外（レースカードと同様） */
    function itemPostAt(r) {
      var date = itemDate(r);
      var time = String(itemPostTime(r) || "").trim();
      if (!date || !time) return null;
      var m = time.match(/^(\d{1,2}):(\d{2})/);
      if (!m) return null;
      var h = parseInt(m[1], 10);
      var min = parseInt(m[2], 10);
      if (!Number.isFinite(h) || !Number.isFinite(min)) return null;
      // JST として解釈（ブラウザローカルが JST 想定。ISO オフセット付きで安定化）
      var iso =
        date +
        "T" +
        String(h).padStart(2, "0") +
        ":" +
        String(min).padStart(2, "0") +
        ":00+09:00";
      var d = new Date(iso);
      if (isNaN(d.getTime())) return null;
      return d;
    }

    function isRaceStarted(r) {
      var at = itemPostAt(r);
      if (!at) return false;
      return Date.now() >= at.getTime();
    }

    function filteredItems() {
      return state.allItems.filter(function (r) {
        if (isRaceStarted(r)) return false;
        if (state.date !== "all" && itemDate(r) !== state.date) return false;
        if (state.venue !== "all" && itemVenue(r) !== state.venue) return false;
        return true;
      });
    }

    function setActive(root, attr, value) {
      if (!root) return;
      root.querySelectorAll("[" + attr + "]").forEach(function (btn) {
        btn.classList.toggle("is-active", btn.getAttribute(attr) === value);
      });
    }

    function renderFilters() {
      var dates = [];
      var venues = [];
      var seenD = {};
      var seenV = {};
      var openItems = state.allItems.filter(function (r) {
        return !isRaceStarted(r);
      });
      openItems.forEach(function (r) {
        var d = itemDate(r);
        var v = itemVenue(r);
        if (d && !seenD[d]) {
          seenD[d] = true;
          dates.push({ iso: d, label: dateLabel(d) });
        }
        if (v && !seenV[v]) {
          seenV[v] = true;
          venues.push(v);
        }
      });
      dates.sort(function (a, b) {
        return String(a.iso).localeCompare(String(b.iso));
      });
      venues.sort(function (a, b) {
        return String(a).localeCompare(String(b), "ja");
      });

      if (dateTabs) {
        var dHtml =
          '<button type="button" class="tab-pill' +
          (state.date === "all" ? " is-active" : "") +
          '" data-filter-date="all">すべて</button>';
        dates.forEach(function (d) {
          dHtml +=
            '<button type="button" class="tab-pill' +
            (state.date === d.iso ? " is-active" : "") +
            '" data-filter-date="' +
            escapeHtml(d.iso) +
            '">' +
            escapeHtml(d.label) +
            "</button>";
        });
        dateTabs.innerHTML = dHtml;
      }
      if (venueChips) {
        var vHtml =
          '<button type="button" class="chip' +
          (state.venue === "all" ? " is-active" : "") +
          '" data-venue="all">すべて</button>';
        venues.forEach(function (v) {
          vHtml +=
            '<button type="button" class="chip' +
            (state.venue === v ? " is-active" : "") +
            '" data-venue="' +
            escapeHtml(v) +
            '">' +
            escapeHtml(v) +
            "</button>";
        });
        venueChips.innerHTML = vHtml;
      }
      if (filterNote) {
        filterNote.textContent =
          "対象 " +
          openItems.length +
          "レース · 会場 " +
          venues.length +
          "場（発走済みは非表示）";
      }
    }

    function raceRowLabel(r) {
      return raceMetaLabel({
        race_label:
          r.race_label ||
          (r.course || "") + (r.race_number != null ? r.race_number + "R" : ""),
        race_name:
          r.race_name ||
          (r.race_info && (r.race_info.race_name || r.race_info.class_label)) ||
          "",
        post_time:
          (r.race_info && r.race_info.post_time) || r.post_time || "",
      });
    }

    function raceShortLabel(r) {
      if (r.race_label) return String(r.race_label);
      var v = itemVenue(r) || "";
      var n = r.race_number != null ? r.race_number : r.race_no;
      return v + (n != null ? n + "R" : "");
    }

    function paintRaceList() {
      var items = filteredItems();
      if (!items.length) {
        raceListEl.innerHTML =
          '<p class="race-list-empty">この条件に合うレースがありません。</p>';
        return;
      }

      var groups = Object.create(null);
      var order = [];
      items.forEach(function (r) {
        var v = itemVenue(r) || "その他";
        if (!groups[v]) {
          groups[v] = [];
          order.push(v);
        }
        groups[v].push(r);
      });

      var openVenue = null;
      if (!state.accordionClosed) {
        openVenue = state.openVenue;
        if (!openVenue && state.raceId) {
          for (var i = 0; i < items.length; i++) {
            if (items[i].race_id === state.raceId) {
              openVenue = itemVenue(items[i]) || "その他";
              break;
            }
          }
        }
        if (!openVenue) openVenue = order[0] || null;
      }

      raceListEl.innerHTML = order
        .map(function (venue) {
          var races = groups[venue] || [];
          var open = openVenue === venue;
          return (
            '<div class="odds-venue-acc-item' +
            (open ? " is-open" : "") +
            '" data-venue-group="' +
            escapeHtml(venue) +
            '" role="listitem">' +
            '<button type="button" class="odds-venue-acc-trigger" aria-expanded="' +
            (open ? "true" : "false") +
            '">' +
            '<span class="odds-venue-acc-chevron" aria-hidden="true"></span>' +
            '<span class="odds-venue-acc-name">' +
            escapeHtml(venue) +
            "</span>" +
            '<span class="odds-venue-acc-count">' +
            races.length +
            "</span></button>" +
            '<div class="odds-venue-acc-panel"' +
            (open ? "" : " hidden") +
            ' aria-hidden="' +
            (open ? "false" : "true") +
            '">' +
            races
              .map(function (r) {
                var on = r.race_id === state.raceId;
                return (
                  '<button type="button" class="odds-venue-race' +
                  (on ? " is-active" : "") +
                  '" data-race-id="' +
                  escapeHtml(r.race_id) +
                  '">' +
                  escapeHtml(raceShortLabel(r)) +
                  "</button>"
                );
              })
              .join("") +
            "</div></div>"
          );
        })
        .join("");
    }

    function selectRace(raceId) {
      if (!raceId) return;
      state.raceId = raceId;
      state.accordionClosed = true;
      state.openVenue = null;
      paintRaceList();
      load(false);
      startTimer();
      try {
        var url = new URL(global.location.href);
        url.searchParams.set("race_id", raceId);
        global.history.replaceState({}, "", url.pathname + url.search);
      } catch (e) {}
    }

    function applyFilterChange() {
      state.accordionClosed = false;
      state.openVenue = null;
      paintRaceList();
      var items = filteredItems();
      var stillVisible = items.some(function (r) {
        return r.race_id === state.raceId;
      });
      if (!stillVisible) {
        if (items[0]) selectRace(items[0].race_id);
        else {
          state.raceId = "";
          if (state.timer) clearInterval(state.timer);
          setBusy(false);
          if (metaEl) metaEl.textContent = "条件に合うレースがありません";
          if (legendEl) legendEl.innerHTML = "";
          var svg = ensureSvg();
          if (svg) svg.innerHTML = "";
        }
      }
    }

    if (dateTabs) {
      dateTabs.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-filter-date]");
        if (!btn) return;
        state.date = btn.getAttribute("data-filter-date") || "all";
        state.venue = "all";
        renderFilters();
        applyFilterChange();
      });
    }
    if (venueChips) {
      venueChips.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-venue]");
        if (!btn) return;
        state.venue = btn.getAttribute("data-venue") || "all";
        setActive(venueChips, "data-venue", state.venue);
        applyFilterChange();
      });
    }
    raceListEl.addEventListener("click", function (e) {
      var trigger = e.target.closest(".odds-venue-acc-trigger");
      if (trigger && raceListEl.contains(trigger)) {
        e.preventDefault();
        var item = trigger.closest(".odds-venue-acc-item");
        if (!item) return;
        var venue = item.getAttribute("data-venue-group") || "";
        var willOpen = !item.classList.contains("is-open");
        state.accordionClosed = !willOpen;
        state.openVenue = willOpen ? venue : null;
        paintRaceList();
        return;
      }
      var raceBtn = e.target.closest("[data-race-id]");
      if (!raceBtn || !raceListEl.contains(raceBtn)) return;
      selectRace(raceBtn.getAttribute("data-race-id") || "");
    });
    global.addEventListener("pagehide", function () {
      if (state.timer) clearInterval(state.timer);
    });

    var dates = resolveRaceDates();
    var params = new URLSearchParams(global.location.search || "");
    var preset = params.get("race_id") || "";
    if (preset) {
      var fromId = String(preset).match(/^(\d{4}-\d{2}-\d{2})/);
      if (fromId && dates.indexOf(fromId[1]) < 0) dates = [fromId[1]].concat(dates);
    }

    if (metaEl) {
      metaEl.textContent =
        dates.length
          ? "開催日 " + dates.map(dateLabel).join("・") + " のレースを読み込み中…"
          : "レースを読み込み中…";
    }
    if (global.ExpectUx) {
      ExpectUx.showLoading(raceListEl, {
        replace: true,
        compact: true,
        title: "レース一覧を準備中...",
        message: "開催レースを読み込んでいます。",
      });
    }

    function listForDate(date) {
      if (global.ExpectApi && ExpectApi.Race && ExpectApi.Race.list) {
        return ExpectApi.Race.list({ date: date }).catch(function () {
          return { items: [] };
        });
      }
      return fetch("/api/races?date=" + encodeURIComponent(date), {
        headers: { accept: "application/json" },
        credentials: "same-origin",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (body) {
          var data = (body && body.data) || body || {};
          return { items: data.items || data.races || [] };
        })
        .catch(function () {
          return { items: [] };
        });
    }

    Promise.all((dates.length ? dates : [jstToday()]).map(listForDate))
      .then(function (results) {
        if (global.ExpectUx) ExpectUx.hideLoading(raceListEl);
        var seen = {};
        var list = [];
        (results || []).forEach(function (result) {
          var chunk = [];
          if (Array.isArray(result)) chunk = result;
          else if (result && Array.isArray(result.items)) chunk = result.items;
          else if (result && Array.isArray(result.races)) {
            chunk = result.races
              .map(function (r) {
                return ExpectApi.Race.mapPiRaceToWebItem
                  ? ExpectApi.Race.mapPiRaceToWebItem(r)
                  : r;
              })
              .filter(Boolean);
          }
          chunk.forEach(function (r) {
            if (!r || !r.race_id || seen[r.race_id]) return;
            seen[r.race_id] = true;
            list.push(r);
          });
        });
        state.allItems = list;
        if (preset) {
          var hitItem = null;
          for (var i = 0; i < list.length; i++) {
            if (list[i].race_id === preset) {
              hitItem = list[i];
              break;
            }
          }
          if (hitItem) {
            state.raceId = preset;
            state.date = itemDate(hitItem) || "all";
          }
        }
        renderFilters();
        if (!state.raceId) {
          var filtered = filteredItems();
          if (filtered[0]) state.raceId = filtered[0].race_id;
          else if (list[0]) state.raceId = list[0].race_id;
        }
        paintRaceList();
        if (!state.raceId) {
          setBusy(false);
          if (metaEl) metaEl.textContent = "レースなし";
          if (noteEl) noteEl.textContent = "表示できるレースがありません。";
          return;
        }
        load(false);
        startTimer();
      })
      .catch(function () {
        if (global.ExpectUx) ExpectUx.hideLoading(raceListEl);
        setBusy(false);
        raceListEl.innerHTML =
          '<p class="race-list-empty">レース一覧の取得に失敗しました。</p>';
        if (noteEl) noteEl.textContent = "レース一覧の取得に失敗しました。";
      });
  }

  global.ExpectOddsChart = { bind: bind };
})(typeof window !== "undefined" ? window : globalThis);
