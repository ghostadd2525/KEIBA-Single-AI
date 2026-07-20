/**
 * SINGLE-09 Prototype v2 — P0 improvements only
 * 画面順: 印 → AI本命カード（三連単#1） → 残りTOP5（タブ） → 信頼度1行 → 短い解説
 * AI / API / DB なし。PredictionBundle 表示のみ。
 */
(function (global) {
  "use strict";

  var MARK_ORDER = ["honmei", "taikou", "ana", "chuuken"];
  var MARK_SYMBOL = {
    honmei: "◎",
    taikou: "○",
    ana: "▲",
    chuuken: "△",
    none: "—"
  };
  var BAND_LABEL = {
    high: "高い",
    medium: "ふつう",
    low: "低い",
    unknown: "不明"
  };

  var CATALOG = {
    meetings: [
      { meeting_id: "20260719_hanshin", date: "2026-07-19", venue: "阪神" },
      { meeting_id: "20260719_fukushima", date: "2026-07-19", venue: "福島" },
      { meeting_id: "20260720_nakayama", date: "2026-07-20", venue: "中山" }
    ],
    races: [
      {
        race_id: "20260719_hanshin_10",
        meeting_id: "20260719_hanshin",
        race_no: 10,
        surface: "turf",
        distance: 1600,
        field_size: 16,
        has_bundle: false
      },
      {
        race_id: "20260719_hanshin_11",
        meeting_id: "20260719_hanshin",
        race_no: 11,
        surface: "dirt",
        distance: 1800,
        field_size: 15,
        has_bundle: true
      },
      {
        race_id: "20260719_hanshin_12",
        meeting_id: "20260719_hanshin",
        race_no: 12,
        surface: "turf",
        distance: 1200,
        field_size: 18,
        has_bundle: false
      },
      {
        race_id: "20260719_fukushima_11",
        meeting_id: "20260719_fukushima",
        race_no: 11,
        surface: "turf",
        distance: 2000,
        field_size: 14,
        has_bundle: false
      },
      {
        race_id: "20260720_nakayama_11",
        meeting_id: "20260720_nakayama",
        race_no: 11,
        surface: "dirt",
        distance: 1200,
        field_size: 16,
        has_bundle: false
      }
    ]
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function surfaceLabel(surface) {
    if (surface === "turf") return "芝";
    if (surface === "dirt") return "ダート";
    return surface || "—";
  }

  function distanceLine(surface, distance) {
    if (!distance && !surface) return "—";
    return surfaceLabel(surface) + " " + (distance || "—") + "m";
  }

  function formatScore(s) {
    if (typeof s !== "number") return "—";
    return s.toFixed(2);
  }

  function loadPredictionBundle(raceId) {
    var id = raceId || "20260719_hanshin_11";
    if (global.ExpectApi && global.ExpectApi.Prediction && global.ExpectApi.Prediction.get) {
      return global.ExpectApi.Prediction.get(id).catch(function () {
        return loadPredictionBundleFallback();
      });
    }
    return loadPredictionBundleFallback();
  }

  function loadPredictionBundleFallback() {
    return fetch("data/sample_prediction_bundle.json")
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .catch(function () {
        if (global.SAMPLE_PREDICTION_BUNDLE) {
          return global.SAMPLE_PREDICTION_BUNDLE;
        }
        throw new Error(
          "PredictionBundle を読めませんでした。sample_data.js を確認してください。"
        );
      });
  }

  function getMeeting(meetingId) {
    for (var i = 0; i < CATALOG.meetings.length; i++) {
      if (CATALOG.meetings[i].meeting_id === meetingId) return CATALOG.meetings[i];
    }
    return null;
  }

  function racesForMeeting(meetingId) {
    return CATALOG.races.filter(function (r) {
      return r.meeting_id === meetingId;
    });
  }

  function parseHash() {
    var raw = (location.hash || "").replace(/^#/, "");
    if (!raw || raw === "/") return { view: "meetings" };
    var parts = raw.split("/").filter(Boolean);
    if (parts[0] === "meeting" && parts[1]) {
      return { view: "races", meetingId: decodeURIComponent(parts[1]) };
    }
    return { view: "meetings" };
  }

  /* ---------- 一覧（v1 と同等 · P1 改善は対象外） ---------- */

  function renderMeetingList(root) {
    var byDate = {};
    CATALOG.meetings.forEach(function (m) {
      (byDate[m.date] = byDate[m.date] || []).push(m);
    });
    var html = "";
    Object.keys(byDate).sort().forEach(function (date) {
      html += '<section class="date-group">';
      html += '<p class="date-label">' + escapeHtml(date) + "</p>";
      html += '<ul class="list">';
      byDate[date].forEach(function (m) {
        html +=
          '<li><a class="list-link" href="#/meeting/' +
          encodeURIComponent(m.meeting_id) +
          '"><span class="list-main"><span class="list-title">' +
          escapeHtml(m.venue) +
          '</span></span><span class="chevron">›</span></a></li>';
      });
      html += "</ul></section>";
    });
    root.innerHTML = html;
  }

  function renderRaceList(root, meetingId) {
    var meeting = getMeeting(meetingId);
    if (!meeting) {
      root.innerHTML =
        '<div class="empty-state"><p>開催が見つかりません。</p>' +
        '<p><a href="#/">開催一覧へ</a></p></div>';
      return;
    }
    var races = racesForMeeting(meetingId).slice().sort(function (a, b) {
      return a.race_no - b.race_no;
    });
    var html = '<ul class="list">';
    races.forEach(function (r) {
      var meta = distanceLine(r.surface, r.distance) + " · " + r.field_size + "頭";
      var badge = r.has_bundle
        ? '<span class="badge badge-yes">予想あり</span>'
        : '<span class="badge badge-no">予想なし</span>';
      var href = r.has_bundle
        ? "race.html?race_id=" + encodeURIComponent(r.race_id)
        : "#";
      var cls = r.has_bundle ? "list-link" : "list-link is-disabled";
      html +=
        '<li><a class="' + cls + '" href="' + href + '">' +
        '<span class="list-main"><span class="list-title">' +
        escapeHtml(String(r.race_no)) +
        'R</span><span class="list-meta">' +
        escapeHtml(meta) +
        "</span></span>" +
        '<span style="display:flex;align-items:center;gap:0.5rem">' +
        badge +
        (r.has_bundle ? '<span class="chevron">›</span>' : "") +
        "</span></a></li>";
    });
    html += "</ul>";
    root.innerHTML = html;
  }

  /* ---------- レース詳細（v2 · P0 反映） ---------- */

  function raceTitle(info) {
    var parts = [];
    if (info.venue) parts.push(info.venue);
    if (info.race_no != null) parts.push(info.race_no + "R");
    return parts.join(" ") || info.race_id || "レース";
  }

  function betsOf(recs, betType) {
    if (!recs || !recs.items) return [];
    return recs.items
      .filter(function (it) { return it.bet_type === betType; })
      .slice()
      .sort(function (a, b) { return a.recommendation_rank - b.recommendation_rank; })
      .slice(0, 5);
  }

  /* P0-1: 印を最上部に主役表示 */
  function renderMarksSection(evaluation) {
    var html = '<section class="section"><h3 class="section-title">印</h3>';
    if (!evaluation || evaluation.status !== "ok" || !evaluation.runners) {
      return html + '<div class="empty-state"><p>評価なし</p></div></section>';
    }
    var marked = evaluation.runners
      .filter(function (r) { return r.mark && r.mark !== "none"; })
      .sort(function (a, b) {
        return MARK_ORDER.indexOf(a.mark) - MARK_ORDER.indexOf(b.mark);
      });
    if (!marked.length) {
      return html + '<div class="empty-state"><p>印なし</p></div></section>';
    }
    html += '<div class="marks">';
    marked.forEach(function (r) {
      var cls = r.mark === "honmei" ? "mark-row is-honmei" : "mark-row";
      html +=
        '<div class="' + cls + '">' +
        '<span class="mark-symbol">' + escapeHtml(MARK_SYMBOL[r.mark] || "—") + "</span>" +
        '<span class="mark-num">' + escapeHtml(String(r.horse_number)) + "</span>" +
        '<span class="mark-name">' + escapeHtml(r.horse_name || "") + "</span></div>";
    });
    html += "</div></section>";
    return html;
  }

  /* P0-3: AI本命（三連単 #1）カード */
  function renderHeroSection(recs) {
    var trifecta = betsOf(recs, "trifecta");
    var top = trifecta.length ? trifecta[0] : null;
    var html = '<section class="section">';
    if (!top) {
      return (
        html +
        '<div class="empty-state"><p>おすすめ買い目はありません</p></div></section>'
      );
    }
    html += '<div class="hero-card">';
    html += '<p class="hero-label">AI本命 · 三連単 #1</p>';
    html += '<p class="hero-legs">' + escapeHtml(top.legs_display || "—") + "</p>";
    html +=
      '<p class="hero-sub">1着→2着→3着の順 · score ' +
      escapeHtml(formatScore(top.recommendation_score)) +
      "</p>";
    if (top.comment) {
      html += '<p class="hero-comment">' + escapeHtml(top.comment) + "</p>";
    }
    html += "</div></section>";
    return html;
  }

  /* P0-4: 残り買い目（三連単 #2-5 / 三連複 TOP5 タブ切替） */
  function renderRestBetsSection(recs) {
    var trifectaRest = betsOf(recs, "trifecta").slice(1);
    var trio = betsOf(recs, "trio");
    var html =
      '<section class="section"><h3 class="section-title">残りのおすすめ</h3>';
    if (!trifectaRest.length && !trio.length) {
      return html + '<div class="empty-state"><p>他のおすすめはありません</p></div></section>';
    }
    html += '<div class="bet-tabs" role="tablist">';
    html +=
      '<button type="button" class="bet-tab is-active" data-tab="trifecta">三連単 #2-5</button>';
    html +=
      '<button type="button" class="bet-tab" data-tab="trio">三連複 TOP5</button>';
    html += "</div>";
    html += '<div data-panel="trifecta">' + renderBetList(trifectaRest) + "</div>";
    html += '<div data-panel="trio" hidden>' + renderBetList(trio) + "</div>";
    html += "</section>";
    return html;
  }

  function renderBetList(items) {
    if (!items.length) {
      return '<div class="empty-state"><p>おすすめ買い目はありません</p></div>';
    }
    var html = '<ul class="bet-list">';
    items.forEach(function (it) {
      html += '<li class="bet-item"><div class="bet-top">';
      html +=
        '<div><span class="bet-rank">#' +
        escapeHtml(String(it.recommendation_rank)) +
        '</span><span class="bet-legs">' +
        escapeHtml(it.legs_display || "—") +
        "</span></div>";
      html +=
        '<span class="bet-score">score ' +
        escapeHtml(formatScore(it.recommendation_score)) +
        "</span></div>";
      if (it.comment) {
        html += '<p class="bet-comment">' + escapeHtml(it.comment) + "</p>";
      }
      html += "</li>";
    });
    html += "</ul>";
    return html;
  }

  /* P0-2: 信頼度は1行 + 折りたたみプレースホルダー */
  function renderConfidenceSection(ac) {
    var html = '<section class="section"><h3 class="section-title">AI信頼度</h3>';
    if (!ac || ac.status === "unavailable") {
      return html + '<div class="empty-state"><p>信頼度情報なし</p></div></section>';
    }
    var band = ac.band || "unknown";
    var label = BAND_LABEL[band] || BAND_LABEL.unknown;
    if (ac.status === "deferred") {
      label = "算出準備中";
      band = "unknown";
    }
    html +=
      '<div class="confidence-line">' +
      '<span class="confidence-dot band-' + escapeHtml(band) + '"></span>' +
      "<span>この予想の信頼度は <strong>" + escapeHtml(label) + "</strong> です</span>" +
      "</div>";
    html +=
      '<details class="fold"><summary>詳しい根拠を見る</summary>' +
      '<div class="fold-body">' +
      "<p>（プレースホルダー）根拠の内訳は今後ここに表示します。</p>" +
      "<ul><li>過去の的中傾向（KPI-08）</li><li>AI評価の明確さ</li></ul>" +
      "</div></details>";
    html += '<p class="disclaimer">※ 的中を保証するものではありません</p>';
    html += "</section>";
    return html;
  }

  /* P0-5: 解説は短文 + 「詳細を見る」 */
  function renderExplainSection(explain) {
    var html = '<section class="section"><h3 class="section-title">解説</h3>';
    if (!explain || (!explain.narrative && !(explain.reasons || []).length)) {
      return html + '<div class="empty-state"><p>解説なし</p></div></section>';
    }
    if (explain.narrative) {
      html += '<p class="narrative">' + escapeHtml(explain.narrative) + "</p>";
    }
    var reasons = explain.reasons || [];
    if (reasons.length) {
      html += '<details class="fold"><summary>詳細を見る</summary><div class="fold-body">';
      reasons.forEach(function (r) {
        html +=
          '<p class="reason-title">' + escapeHtml(String(r.horse_number)) + "番</p>";
        if (r.bullets && r.bullets.length) {
          html += "<ul>";
          r.bullets.forEach(function (b) {
            html += "<li>" + escapeHtml(b) + "</li>";
          });
          html += "</ul>";
        }
      });
      html += "</div></details>";
    }
    html += "</section>";
    return html;
  }

  function renderRaceDetail(root, bundle, expectedRaceId) {
    if (!bundle || (expectedRaceId && bundle.race_id !== expectedRaceId)) {
      root.innerHTML =
        '<div class="empty-state"><p>このレースの予想データはありません</p></div>';
      return;
    }
    var info = bundle.race_info || {};
    var meta =
      distanceLine(info.surface, info.distance) +
      " · " +
      (info.field_size != null ? info.field_size + "頭" : "頭数—") +
      (info.post_time ? " · 発走 " + info.post_time : "");

    var html = "";
    html += '<section class="section race-header">';
    html += "<h2>" + escapeHtml(raceTitle(info)) +
      (info.class_label ? " <small>" + escapeHtml(info.class_label) + "</small>" : "") +
      "</h2>";
    html += '<p class="meta-line">' + escapeHtml(meta) + "</p>";
    html += "</section>";

    html += renderMarksSection(bundle.evaluation);            // P0-1
    html += renderHeroSection(bundle.betting_recommendations); // P0-3
    html += renderRestBetsSection(bundle.betting_recommendations); // P0-4
    html += renderConfidenceSection(bundle.ai_confidence);    // P0-2
    html += renderExplainSection(bundle.explain);             // P0-5

    root.innerHTML = html;
    bindBetTabs(root);
  }

  function bindBetTabs(root) {
    var tabs = root.querySelectorAll(".bet-tab");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var target = tab.getAttribute("data-tab");
        tabs.forEach(function (t) {
          t.classList.toggle("is-active", t === tab);
        });
        root.querySelectorAll("[data-panel]").forEach(function (panel) {
          panel.hidden = panel.getAttribute("data-panel") !== target;
        });
      });
    });
  }

  /* ---------- init ---------- */

  function initIndex() {
    var main = document.getElementById("main");
    var title = document.getElementById("pageTitle");
    var backBtn = document.getElementById("backBtn");
    if (!main) return;

    function paint() {
      var route = parseHash();
      if (route.view === "races") {
        var meeting = getMeeting(route.meetingId);
        title.textContent = meeting ? meeting.venue + " " + meeting.date : "レース一覧";
        backBtn.hidden = false;
        backBtn.onclick = function () { location.hash = "/"; };
        renderRaceList(main, route.meetingId);
        document.title = "SingleAI v2 — レース一覧";
      } else {
        title.textContent = "開催一覧";
        backBtn.hidden = true;
        backBtn.onclick = null;
        renderMeetingList(main);
        document.title = "SingleAI v2 — 開催一覧";
      }
    }

    window.addEventListener("hashchange", paint);
    paint();
  }

  function initRacePage() {
    var main = document.getElementById("main");
    var backLink = document.getElementById("backLink");
    if (!main) return;

    var raceId = new URLSearchParams(location.search).get("race_id") || "20260719_hanshin_11";
    var catalogRace = CATALOG.races.filter(function (r) {
      return r.race_id === raceId;
    })[0];
    if (backLink && catalogRace) {
      backLink.href = "index.html#/meeting/" + encodeURIComponent(catalogRace.meeting_id);
    }

    loadPredictionBundle()
      .then(function (bundle) {
        if (!catalogRace || !catalogRace.has_bundle) {
          main.innerHTML =
            '<div class="empty-state"><p>このレースの予想データはありません</p>' +
            '<p><a href="index.html">開催一覧へ</a></p></div>';
          return;
        }
        renderRaceDetail(main, bundle, raceId);
        document.title = "SingleAI v2 — " + raceTitle(bundle.race_info || {});
      })
      .catch(function (err) {
        main.innerHTML =
          '<div class="empty-state"><p>読み込みエラー</p><p class="muted">' +
          escapeHtml(err.message || String(err)) +
          "</p></div>";
      });
  }

  global.SingleDemo = {
    initIndex: initIndex,
    initRacePage: initRacePage
  };
})(window);
