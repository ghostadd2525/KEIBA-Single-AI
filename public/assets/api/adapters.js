/**
 * PredictionBundle → 画面 DOM
 */
(function (global) {
  "use strict";

  function starsFromConf(conf) {
    var n = Math.max(1, Math.min(5, Math.round((Number(conf) || 0) / 20)));
    var s = "";
    for (var i = 0; i < 5; i++) s += i < n ? "★" : "☆";
    return s;
  }

  /** PredictionBundle → 一覧カード HTML */
  function raceListItemHtml(bundle) {
    var info = (bundle && bundle.race_info) || {};
    var place = (info.venue || "") + " " + (info.race_no != null ? info.race_no + "R" : "");
    var name = info.class_label || "レース";
    var badge = info.grade || "";
    var conf = (global.ExpectBundle && global.ExpectBundle.scorePercent(bundle)) || 0;
    var bg = info.bg || ((info.race_no || 1) % 4) + 1;
    var dateLabel = info.date_label || "";
    if (!dateLabel && info.date) {
      var p = String(info.date).split("-");
      if (p.length === 3) dateLabel = Number(p[1]) + "/" + Number(p[2]);
    }
    var dateFull = info.date_full || dateLabel;
    var raceId = (global.ExpectBundle && global.ExpectBundle.raceId(bundle)) || bundle.race_id;
    var nameAttr = name.replace(/"/g, "&quot;");
    var postTime = info.post_time || "";

    return (
      '<a class="race-item race-item--bg' +
      bg +
      '" href="race.html?race_id=' +
      encodeURIComponent(raceId) +
      '" data-race-date="' +
      dateLabel +
      '" data-race-venue="' +
      (info.venue || "") +
      '" data-race-name="' +
      nameAttr +
      '" data-race-conf="' +
      conf +
      '" data-race-time="' +
      postTime +
      '" data-race-place="' +
      place +
      '">' +
      '<button type="button" class="fav-btn fav-btn--icon" data-fav-toggle="' +
      raceId +
      '" data-fav-place="' +
      place +
      '" data-fav-name="' +
      nameAttr +
      '" data-fav-badge="' +
      badge +
      '" data-fav-time="' +
      postTime +
      '" data-fav-date="' +
      dateFull +
      '" aria-label="お気に入りに追加">' +
      '<span class="fav-star" aria-hidden="true">★</span></button>' +
      "<div>" +
      '<p class="race-item-place">' +
      place +
      "</p>" +
      '<p class="race-item-name">' +
      name +
      (badge && badge !== "—" ? "（" + badge + "）" : "") +
      "</p>" +
      '<div class="race-item-meta">' +
      "<span>" +
      (postTime || "—") +
      "発走</span>" +
      '<span class="race-stars">' +
      starsFromConf(conf) +
      "</span></div></div>" +
      '<div class="race-item-side">' +
      '<div class="race-conf">' +
      conf +
      "%<small>AI信頼度</small></div>" +
      '<span class="btn-detail">詳細を見る ›</span></div></a>'
    );
  }

  function chartMap(analysis) {
    var map = { pedigree: 70, pace: 70, jockey: 70, form: 70, odds: 70 };
    var charts = (analysis && analysis.charts) || [];
    charts.forEach(function (c) {
      if (c && c.key) map[c.key] = Number(c.value) || 0;
    });
    map.overall =
      Number(analysis && analysis.overall) ||
      Math.round((map.pedigree + map.pace + map.jockey + map.form + map.odds) / 5);
    return map;
  }

  /** PredictionBundle (+ optional Analysis) で詳細画面を構築 */
  function applyFromBundle(bundle, analysis) {
    var info = (bundle && bundle.race_info) || {};
    var honmei = global.ExpectBundle.honmei(bundle);
    var scores = chartMap(analysis);
    var conf = global.ExpectBundle.scorePercent(bundle);
    if (conf == null) conf = scores.overall;

    var titleEl = document.getElementById("raceTitle");
    var subEl = document.querySelector(".brand-sub");
    if (titleEl) {
      titleEl.textContent =
        (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : "");
    }
    if (subEl) {
      var label = info.class_label || "";
      var pt = info.post_time || "";
      subEl.textContent = label + (pt ? " · " + pt : "");
    }

    var card = document.querySelector(".honmei-card");
    if (card && honmei) {
      var num = card.querySelector(".honmei-num");
      var h2 = card.querySelector("h2");
      var p = card.querySelector("p");
      var stars = card.querySelector(".race-stars");
      if (num) num.textContent = String(honmei.horse_number);
      if (h2) h2.textContent = honmei.horse_name || "本命馬";
      if (p) p.textContent = "AI本命 · 信頼度 " + conf + "%";
      if (stars) stars.textContent = starsFromConf(conf);
    }

    var narrativeEl = document.querySelector(".pace-card p");
    if (narrativeEl) {
      var text =
        (analysis && analysis.narrative) ||
        (bundle.explain && bundle.explain.narrative) ||
        "";
      if (text) narrativeEl.textContent = text;
    }

    var rows = document.querySelectorAll(".score-list .score-row");
    var keys = ["pedigree", "pace", "jockey", "form", "odds"];
    rows.forEach(function (row, i) {
      var key = keys[i];
      if (!key) return;
      var v = scores[key];
      var bar = row.querySelector(".score-bar i");
      var b = row.querySelector("b");
      if (bar) bar.style.width = v + "%";
      if (b) b.textContent = String(v);
    });

    return {
      honmei: honmei,
      scores: scores,
      conf: conf,
      place: titleEl ? titleEl.textContent : "",
      name: info.class_label || "",
      postTime: info.post_time || "",
      raceId: global.ExpectBundle.raceId(bundle),
    };
  }

  global.ExpectAdapters = {
    starsFromConf: starsFromConf,
    raceListItemHtml: raceListItemHtml,
    chartMap: chartMap,
    applyFromBundle: applyFromBundle,
    applyRaceDetailCompose: function (model) {
      return applyFromBundle(model.bundle || model.prediction, model.analysis);
    },
  };
})(window);
