/**
 * Phase UI-RealData — Prediction / Coverage / User から UI をバインド
 */
(function (global) {
  "use strict";

  function scorePercent(bundle) {
    if (global.ExpectPredictionBind && ExpectPredictionBind.scorePercent) {
      return ExpectPredictionBind.scorePercent(bundle);
    }
    var c = (bundle && bundle.ai_confidence) || {};
    if (typeof c.score === "number") {
      return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
    }
    return null;
  }

  function dateLabel(info) {
    if (!info) return "";
    if (info.date_label) return info.date_label;
    var d = info.date || "";
    var p = String(d).split("-");
    if (p.length === 3) return Number(p[1]) + "/" + Number(p[2]);
    return d;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function surfaceJa(surface) {
    var s = String(surface || "").toLowerCase();
    if (s.indexOf("turf") >= 0 || s === "芝") return "芝";
    if (s.indexOf("dirt") >= 0 || s === "ダ" || s === "ダート") return "ダ";
    return "芝";
  }

  function distanceBucket(dist) {
    var d = Number(dist) || 0;
    var buckets = [1200, 1600, 2000, 2400];
    var best = buckets[0];
    var diff = Math.abs(d - best);
    for (var i = 1; i < buckets.length; i++) {
      var nd = Math.abs(d - buckets[i]);
      if (nd < diff) {
        diff = nd;
        best = buckets[i];
      }
    }
    return best;
  }

  function aggregateByVenueSurfaceDistance(bundles) {
    var map = {};
    (bundles || []).forEach(function (b) {
      var info = b.race_info || {};
      var venue = info.venue || "—";
      var surf = surfaceJa(info.surface);
      var bucket = distanceBucket(info.distance);
      var key = venue + "|" + surf + "|" + bucket;
      var pct = scorePercent(b);
      if (pct == null) return;
      if (!map[key]) map[key] = { sum: 0, n: 0 };
      map[key].sum += pct;
      map[key].n += 1;
    });
    return map;
  }

  function avgFromMap(map, venue, surf, bucket) {
    var key = venue + "|" + surf + "|" + bucket;
    var row = map[key];
    if (!row || !row.n) return null;
    return Math.round(row.sum / row.n);
  }

  function venuesFromBundles(bundles) {
    var set = {};
    (bundles || []).forEach(function (b) {
      var v = b.race_info && b.race_info.venue;
      if (v) set[v] = true;
    });
    return Object.keys(set).sort();
  }

  /** @returns {{ iso: string, label: string }[]} ISO 昇順（URL ?date= と整合） */
  function datesFromBundles(bundles) {
    var map = {};
    (bundles || []).forEach(function (b) {
      var info = b.race_info || {};
      var iso = String(info.date || "").trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return;
      if (!map[iso]) map[iso] = dateLabel(info) || iso;
    });
    return Object.keys(map)
      .sort()
      .map(function (iso) {
        return { iso: iso, label: map[iso] };
      });
  }

  function cellHtml(pct) {
    if (pct == null) {
      return '<td><span class="hv hv--empty" style="--v:0"><b>—</b><i></i></span></td>';
    }
    return (
      '<td><span class="hv" style="--v:' +
      pct +
      '"><b>' +
      pct +
      '%</b><i></i></span></td>'
    );
  }

  function heatmapCellHtml(cell) {
    if (!cell || cell.pct == null) {
      return '<td><span class="hv hv--empty" style="--v:0"><b>—</b><i></i></span></td>';
    }
    var band = cell.band && cell.band !== "unknown" ? " hv--" + cell.band : "";
    return (
      '<td><span class="hv' +
      band +
      '" style="--v:' +
      cell.pct +
      '"><b>' +
      cell.pct +
      '%</b><i></i></span></td>'
    );
  }

  function conditionCellHtml(cell) {
    if (!cell || cell.pct == null) {
      return '<td style="--v:0">—</td>';
    }
    return '<td style="--v:' + cell.pct + '">' + cell.pct + "%</td>";
  }

  function formatHeatNote(data, venueCount) {
    var when = "";
    if (data && data.updated_at) {
      try {
        var d = new Date(data.updated_at);
        if (!isNaN(d.getTime())) {
          when =
            d.getFullYear() +
            "/" +
            (d.getMonth() + 1) +
            "/" +
            d.getDate() +
            " " +
            String(d.getHours()).padStart(2, "0") +
            ":" +
            String(d.getMinutes()).padStart(2, "0");
        }
      } catch (e) {
        when = String(data.updated_at);
      }
    }
    var parts = ["◎的中率（過去実績）"];
    if (venueCount) parts.push("対象会場 " + venueCount + "場");
    if (data && data.races_evaluated) parts.push(data.races_evaluated + "R評価");
    if (when) parts.push("※" + when + " 更新");
    return parts.join(" · ");
  }

  function paintHeatmapFromStats(data, venueFilter) {
    var dist = (data && data.distance) || {};
    var cond = (data && data.condition) || {};
    var venues = dist.venues || [];
    var appliedFilter = venueFilter && venueFilter.length ? venueFilter : null;
    if (appliedFilter) {
      var allow = {};
      appliedFilter.forEach(function (v) {
        allow[v] = true;
      });
      var filtered = venues.filter(function (v) {
        return allow[v];
      });
      // 当日会場名とセグメントキーが一致しない場合は全会場表示へフォールバック
      if (filtered.length) venues = filtered;
      else appliedFilter = null;
    }

    var distBody = document.querySelector("#heatmapBody");
    if (distBody) {
      if (!venues.length) {
        distBody.innerHTML =
          '<tr><td colspan="9" class="muted">過去実績データがありません</td></tr>';
      } else {
        var distRows = (dist.rows || []).filter(function (row) {
          return venues.indexOf(row.venue) >= 0;
        });
        distBody.innerHTML = distRows
          .map(function (row) {
            var cells = (row.cells || []).map(heatmapCellHtml).join("");
            return (
              '<tr><th class="row-head">' +
              escapeHtml(row.venue) +
              "</th>" +
              cells +
              "</tr>"
            );
          })
          .join("");
      }
    }

    var condBody = document.querySelector("#conditionHeatmapBody");
    if (condBody) {
      var condRows = cond.rows || [];
      if (appliedFilter) {
        var allowVenues = {};
        appliedFilter.forEach(function (v) {
          allowVenues[v] = true;
        });
        condRows = condRows.filter(function (row) {
          return allowVenues[row.venue];
        });
      }
      if (!condRows.length) {
        condBody.innerHTML =
          '<tr><td colspan="5" class="muted">過去実績データがありません</td></tr>';
      } else {
        condBody.innerHTML = condRows
          .map(function (row) {
            var cells = (row.cells || []).map(conditionCellHtml).join("");
            return "<tr><th>" + escapeHtml(row.label || "") + "</th>" + cells + "</tr>";
          })
          .join("");
      }
    }

    var noteText = formatHeatNote(data, venues.length);
    document.querySelectorAll("[data-heat-asof]").forEach(function (note) {
      note.textContent = noteText;
    });
  }

  var heatmapPollTimer = null;
  var heatmapPollOpts = null;

  function fetchAndPaintHeatmap(opts) {
    opts = opts || {};
    var venues = opts.venues || null;
    if (venues && venues.length) {
      heatmapPollOpts = Object.assign({}, heatmapPollOpts || {}, { venues: venues });
    } else if (opts.venues === null) {
      heatmapPollOpts = Object.assign({}, heatmapPollOpts || {}, { venues: null });
    }
    var query = {};
    if (venues && venues.length) query.venues = venues.join(",");
    var req =
      global.ExpectApi && ExpectApi.Stats && ExpectApi.Stats.heatmap
        ? ExpectApi.Stats.heatmap(query)
        : fetch(
            "/api/v1/stats/heatmap" +
              (query.venues ? "?venues=" + encodeURIComponent(query.venues) : "")
          )
            .then(function (res) {
              return res.json();
            })
            .then(function (payload) {
              return payload && payload.data != null ? payload.data : payload;
            });
    return req
      .then(function (data) {
        paintHeatmapFromStats(data, venues);
        return data;
      });
  }

  function startHeatmapPolling(opts) {
    opts = opts || {};
    heatmapPollOpts = opts;
    var intervalMs = opts.intervalMs || 60000;
    if (heatmapPollTimer) clearInterval(heatmapPollTimer);
    function tick() {
      fetchAndPaintHeatmap(heatmapPollOpts || {}).catch(function () {
        /* 前回表示を維持 */
      });
    }
    tick();
    heatmapPollTimer = setInterval(tick, intervalMs);
    return function stopHeatmapPolling() {
      if (heatmapPollTimer) clearInterval(heatmapPollTimer);
      heatmapPollTimer = null;
    };
  }

  function resolveHomeDate() {
    if (global.ExpectRaceListUrl && ExpectRaceListUrl.calendarFallbackDate) {
      var fb = ExpectRaceListUrl.calendarFallbackDate(new Date());
      if (fb) return fb;
    }
    if (global.ExpectWeekendCalendar && ExpectWeekendCalendar.decide) {
      var cal = ExpectWeekendCalendar.decide(new Date());
      if (cal && cal.is_race_day && cal.date_jst) return cal.date_jst;
      if (cal && cal.next_open_date_jst) return cal.next_open_date_jst;
    }
    return "";
  }

  function paintDistanceHeatmap(bundles) {
    var tbody = document.querySelector("#heatmapBody");
    if (!tbody) return;
    var venues = venuesFromBundles(bundles);
    if (!venues.length) {
      tbody.innerHTML =
        '<tr><td colspan="9" class="muted">Prediction API からレースを取得できませんでした</td></tr>';
      return;
    }
    var agg = aggregateByVenueSurfaceDistance(bundles);
    var cols = [
      { surf: "芝", bucket: 1200 },
      { surf: "芝", bucket: 1600 },
      { surf: "芝", bucket: 2000 },
      { surf: "芝", bucket: 2400 },
      { surf: "ダ", bucket: 1200 },
      { surf: "ダ", bucket: 1600 },
      { surf: "ダ", bucket: 2000 },
      { surf: "ダ", bucket: 2400 },
    ];
    tbody.innerHTML = venues
      .map(function (venue) {
        var cells = cols
          .map(function (c) {
            return cellHtml(avgFromMap(agg, venue, c.surf, c.bucket));
          })
          .join("");
        return (
          "<tr><th class=\"row-head\">" + escapeHtml(venue) + "</th>" + cells + "</tr>"
        );
      })
      .join("");
    var note = document.querySelector("#heatmap [data-heat-asof]");
    if (note) {
      note.textContent =
        "対象会場 " + venues.length + "場 · Prediction API 集計（会場×距離×芝ダ）";
    }
  }

  function paintConditionHeatmap(bundles) {
    var tbody = document.querySelector("#conditionHeatmapBody");
    if (!tbody) return;
    var agg = {};
    (bundles || []).forEach(function (b) {
      var info = b.race_info || {};
      var venue = info.venue || "—";
      var surf = surfaceJa(info.surface);
      var key = venue + " " + surf;
      var pct = scorePercent(b);
      if (pct == null) return;
      if (!agg[key]) agg[key] = { sum: 0, n: 0 };
      agg[key].sum += pct;
      agg[key].n += 1;
    });
    var keys = Object.keys(agg).sort();
    if (!keys.length) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="muted">データなし</td></tr>';
      return;
    }
    tbody.innerHTML = keys
      .map(function (key) {
        var avg = Math.round(agg[key].sum / agg[key].n);
        var cells = [avg, avg, avg, avg]
          .map(function (v) {
            return '<td style="--v:' + v + '">' + v + "%</td>";
          })
          .join("");
        return "<tr><th>" + escapeHtml(key) + "</th>" + cells + "</tr>";
      })
      .join("");
  }

  function paintDashMetrics(coverage, history) {
    var roiEl = document.getElementById("dashCoverage") || document.querySelector(".dash-roi");
    var rankEl = document.getElementById("dashHistory") || document.querySelector(".dash-rank");
    var metricWrap = roiEl && roiEl.closest ? roiEl.closest(".dash-metric") : null;
    if (roiEl) {
      if (coverage && (Number(coverage.race_total) || 0) > 0) {
        var total = Number(coverage.race_total) || 0;
        var real = Number(coverage.real_ai) || 0;
        var pct = total ? Math.round((real / total) * 100) : 0;
        roiEl.textContent = pct + "%";
        var label = roiEl.parentElement && roiEl.parentElement.querySelector(".dash-label");
        if (label) {
          label.innerHTML =
            'AIカバレッジ <img class="info-ico" src="assets/icons/icon-info.svg" alt="" />';
        }
        if (metricWrap) metricWrap.hidden = false;
      } else {
        roiEl.textContent = "";
        if (metricWrap) metricWrap.hidden = true;
      }
    }
    if (rankEl && history) {
      var n = Number(history.count) || (history.items && history.items.length) || 0;
      rankEl.innerHTML = "閲覧履歴 " + n + "件 <span>›</span>";
    }
  }

  function buildFilterChips(bundles) {
    return {
      dates: datesFromBundles(bundles),
      venues: venuesFromBundles(bundles),
    };
  }

  function renderChipRow(container, attr, values, allLabel) {
    if (!container) return;
    var html =
      '<button type="button" class="chip is-active" data-' +
      attr +
      '="all">' +
      escapeHtml(allLabel || "すべて") +
      "</button>";
    values.forEach(function (v, i) {
      var cls = "chip";
      html +=
        '<button type="button" class="' +
        cls +
        '" data-' +
        attr +
        '="' +
        escapeHtml(v) +
        '">' +
        escapeHtml(v) +
        "</button>";
    });
    container.innerHTML = html;
  }

  function renderDateTabs(container, dates) {
    if (!container) return;
    var html =
      '<button type="button" class="tab-pill is-active" data-filter-date="all">すべて</button>';
    (dates || []).forEach(function (d) {
      var iso = typeof d === "object" && d ? d.iso : d;
      var label = typeof d === "object" && d ? d.label : d;
      if (!iso) return;
      html +=
        '<button type="button" class="tab-pill" data-filter-date="' +
        escapeHtml(iso) +
        '">' +
        escapeHtml(label || iso) +
        "</button>";
    });
    container.innerHTML = html;
  }

  function renderDateSearchChips(container, dates) {
    if (!container) return;
    var html =
      '<button type="button" class="chip is-active" data-search-date="all">すべて</button>';
    (dates || []).forEach(function (d) {
      var iso = typeof d === "object" && d ? d.iso : d;
      var label = typeof d === "object" && d ? d.label : d;
      if (!iso) return;
      html +=
        '<button type="button" class="chip" data-search-date="' +
        escapeHtml(iso) +
        '">' +
        escapeHtml(label || iso) +
        "</button>";
    });
    container.innerHTML = html;
  }

  function applyRacesFilters(bundles) {
    var chips = buildFilterChips(bundles);
    // 今週末の土日タブを常に含める（データ未取得日も選択可能に）
    if (global.ExpectWeekendCalendar && ExpectWeekendCalendar.weekendRaceDates) {
      var week = ExpectWeekendCalendar.weekendRaceDates(new Date()) || [];
      var have = {};
      (chips.dates || []).forEach(function (d) {
        have[d.iso] = d;
      });
      week.forEach(function (iso) {
        if (!have[iso]) {
          var label =
            global.ExpectRaceListUrl && ExpectRaceListUrl.dateLabelFromIso
              ? ExpectRaceListUrl.dateLabelFromIso(iso)
              : iso;
          chips.dates.push({ iso: iso, label: label });
        }
      });
      chips.dates.sort(function (a, b) {
        return String(a.iso).localeCompare(String(b.iso));
      });
    }
    renderDateTabs(document.getElementById("dateTabs"), chips.dates);
    renderChipRow(document.getElementById("venueChips"), "venue", chips.venues);
    renderDateSearchChips(document.getElementById("raceSearchDates"), chips.dates);
    renderChipRow(document.getElementById("raceSearchVenues"), "search-venue", chips.venues);
    var note = document.getElementById("raceFilterNote");
    if (note) {
      note.textContent =
        "対象 " +
        (bundles ? bundles.length : 0) +
        "レース · 会場 " +
        chips.venues.length +
        " · お気に入りは最大3件";
    }
    // チップ再描画後に現在の絞り込みを再適用（会場選択を維持）
    try {
      global.dispatchEvent(new CustomEvent("expect:race-filters-ready"));
    } catch (e) { /* ignore */ }
  }

  function bindMypageProfile(me, history, chat) {
    var card = document.querySelector(".profile-card");
    if (!card || !me) return;
    var p = me.profile || {};
    var h2 = card.querySelector("h2");
    var metas = card.querySelectorAll(".meta");
    var badge = card.querySelector(".badge-premium");
    if (h2) h2.textContent = p.display_name || me.login_id || "ユーザー";
    if (metas[0]) metas[0].textContent = "login_id · " + (me.login_id || "—");
    if (badge) {
      var role = me.role || (me.user && me.user.role) || "";
      badge.textContent = role ? String(role) : me.status || "USER";
    }
    if (metas[1]) {
      var histN = (history && history.count) || 0;
      var chatN = (chat && chat.count) || 0;
      metas[1].textContent = "Lv. — · 閲覧 " + histN + " · チャット " + chatN;
    }
    var stats = document.querySelector(".stats-grid");
    if (stats && history) {
      var cells = stats.querySelectorAll(".stat-cell b");
      var n = Number(history.count) || 0;
      if (cells[0]) cells[0].textContent = n + "件";
      if (cells[1]) cells[1].textContent = "—";
      if (cells[2]) cells[2].textContent = "—";
      if (cells[3]) cells[3].textContent = n + "R";
      stats.querySelector("h3").textContent = "アクティビティ（User API）";
    }
  }

  function bindSavedPage(history, coverage) {
    var heroLabel = document.querySelector(".balance-hero-label");
    var heroValue = document.querySelector(".balance-hero-value");
    var heroSub = document.querySelector(".balance-hero-sub");
    var now = new Date();
    var ym = now.getFullYear() + "年" + (now.getMonth() + 1) + "月";
    if (heroLabel) heroLabel.textContent = ym + " · 閲覧アクティビティ";
    var n = (history && history.count) || 0;
    if (heroValue) {
      heroValue.textContent = n + " レース閲覧";
      heroValue.classList.remove("is-plus", "is-minus");
    }
    if (heroSub && coverage) {
      var total = Number(coverage.race_total) || 0;
      var real = Number(coverage.real_ai) || 0;
      var pct = total ? Math.round((real / total) * 100) : 0;
      heroSub.innerHTML =
        'AIカバレッジ <strong>' + pct + "%</strong> (" + real + "/" + total + ")";
    }
    var stats = document.querySelector(".stats-grid");
    if (stats) {
      stats.querySelector("h3").textContent = "今月のアクティビティ";
      var cells = stats.querySelectorAll(".stat-cell b");
      if (cells[0]) cells[0].textContent = n + "件";
      if (cells[1]) cells[1].textContent = coverage ? coverage.coverage + "%" : "—";
      if (cells[2]) cells[2].textContent = "—";
      if (cells[3]) cells[3].textContent = n + "R";
    }
    var weekList = document.querySelector(".balance-week-list");
    if (weekList && history && history.items) {
      var items = history.items.slice(0, 8);
      if (!items.length) {
        weekList.innerHTML = "<li><span>履歴なし</span><b>—</b></li>";
      } else {
        weekList.innerHTML = items
          .map(function (it) {
            return (
              "<li><span>" +
              escapeHtml(it.race_id || "—") +
              "</span><b>" +
              escapeHtml(it.engine_source || it.viewed_at || "—") +
              "</b></li>"
            );
          })
          .join("");
      }
    }
    var notes = document.querySelector(".balance-notes p");
    if (notes) {
      notes.textContent =
        "的中・収支データは未提供のため、User API の予測閲覧履歴と Coverage を表示しています。";
    }
  }

  function mascotLinesFromData(bundles, coverage) {
    var top = null;
    if (bundles && bundles.length && global.ExpectPredictionBind) {
      top = ExpectPredictionBind.pickTopByConfidence(bundles);
    }
    var lines = ["お疲れさま！<br>今日も一緒に<br>レースを見ていこう！"];
    if (top) {
      var info = top.race_info || {};
      var conf = scorePercent(top);
      lines.push(
        "今日は<br><strong>" +
          escapeHtml(info.venue || "") +
          (info.race_no != null ? " " + info.race_no + "R" : "") +
          "</strong> の<br>信頼度が高いよ！" +
          (conf != null ? "（" + conf + "%）" : "")
      );
    }
    if (coverage && coverage.coverage != null) {
      lines.push(
        "AIカバレッジは<br><strong>" +
          coverage.coverage +
          "%</strong> だよ！"
      );
    }
    lines.push("お気に入りレース、<br>忘れずにチェックしてね！");
    return lines;
  }

  function cacheBundles(bundles) {
    if (global.ExpectFavorites && typeof ExpectFavorites.cacheBundles === "function") {
      ExpectFavorites.cacheBundles(bundles);
    }
  }

  global.ExpectRealDataBind = {
    scorePercent: scorePercent,
    paintDistanceHeatmap: paintDistanceHeatmap,
    paintConditionHeatmap: paintConditionHeatmap,
    paintHeatmapFromStats: paintHeatmapFromStats,
    fetchAndPaintHeatmap: fetchAndPaintHeatmap,
    startHeatmapPolling: startHeatmapPolling,
    resolveHomeDate: resolveHomeDate,
    paintDashMetrics: paintDashMetrics,
    applyRacesFilters: applyRacesFilters,
    bindMypageProfile: bindMypageProfile,
    bindSavedPage: bindSavedPage,
    mascotLinesFromData: mascotLinesFromData,
    cacheBundles: cacheBundles,
    buildFilterChips: buildFilterChips,
  };
})(window);
