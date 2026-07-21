/**
 * Phase1: PredictionBundle → UI バインド（ui-api-mapping.md 準拠）
 * Analysis / Ticket / Kaoba は使わない。
 */
(function (global) {
  "use strict";

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function horseLabel(name, num) {
    if (global.ExpectRaceIdMeta && ExpectRaceIdMeta.displayHorseName) {
      return ExpectRaceIdMeta.displayHorseName(name, num);
    }
    return name || (num != null ? String(num) + "番" : "出走馬");
  }

  function publicFactors(factors) {
    if (global.ExpectRaceIdMeta && ExpectRaceIdMeta.publicConfidenceFactors) {
      return ExpectRaceIdMeta.publicConfidenceFactors(factors);
    }
    return Array.isArray(factors) ? factors : [];
  }

  function scorePercent(bundle) {
    if (global.ExpectApi && ExpectApi.Prediction && ExpectApi.Prediction.scorePercent) {
      return ExpectApi.Prediction.scorePercent(bundle);
    }
    var c = (bundle && bundle.ai_confidence) || {};
    if (typeof c.score === "number") {
      return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
    }
    return null;
  }

  function starsFromScore(pct) {
    var n = Math.max(1, Math.min(5, Math.round((Number(pct) || 0) / 20)));
    var s = "";
    for (var i = 0; i < 5; i++) s += i < n ? "★" : "☆";
    return s;
  }

  function dateLabel(info) {
    if (!info) return "";
    if (info.date_label) return info.date_label;
    var d = info.date || "";
    var p = String(d).split("-");
    if (p.length === 3) return Number(p[1]) + "/" + Number(p[2]);
    return d;
  }

  function dateFull(info) {
    if (info && info.date_full) return info.date_full;
    return dateLabel(info);
  }

  var MARK_ORDER = ["honmei", "taikou", "ana", "chuuken"];
  var MARK_SYMBOL = { honmei: "◎", taikou: "○", ana: "▲", chuuken: "△", none: "—" };
  var MARK_LABEL = { honmei: "本命", taikou: "対抗", ana: "穴", chuuken: "中穴", none: "—" };
  var BAND_LABEL = { high: "高い", medium: "ふつう", low: "低い", unknown: "不明" };
  var FEATURE_LABEL = { db: "DB", daily_csv: "日次CSV", global_csv: "全体CSV" };

  function runnerByMark(bundle, mark) {
    var runners = (((bundle || {}).evaluation || {}).runners) || [];
    for (var i = 0; i < runners.length; i++) {
      if (runners[i].mark === mark) return runners[i];
    }
    return null;
  }

  function sortedRunnersByRank(bundle) {
    var runners = (((bundle || {}).evaluation || {}).runners) || [];
    return runners.slice().sort(function (a, b) {
      return (Number(a.model_rank) || 999) - (Number(b.model_rank) || 999);
    });
  }

  function honmeiRunner(bundle) {
    var byMark = runnerByMark(bundle, "honmei");
    if (byMark) return byMark;
    var sorted = sortedRunnersByRank(bundle);
    return sorted[0] || null;
  }

  function bgClass(info, raceNo) {
    var bg = info && info.bg != null ? Number(info.bg) : ((Number(raceNo) || 1) % 4) + 1;
    if (bg < 1 || bg > 4) bg = 1;
    return bg;
  }

  /** レース一覧カード HTML（既存 .race-item 構造を維持） */
  function raceCardHtml(bundle) {
    var info = (bundle && bundle.race_info) || {};
    var rid = (bundle && bundle.race_id) || info.race_id || "";
    var place = (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : "");
    var name = info.class_label || "レース";
    var grade = info.grade || "";
    var conf = scorePercent(bundle) || 0;
    var dLabel = dateLabel(info);
    var dFull = dateFull(info);
    var post = info.post_time || "";
    var bg = bgClass(info, info.race_no);
    var nameDisp = name + (grade && grade !== "—" ? "（" + grade + "）" : "");
    var eng =
      (bundle && bundle.__meta && bundle.__meta.engine_source) ||
      "";

    return (
      '<a class="race-item race-item--bg' +
      bg +
      '" href="race.html?race_id=' +
      encodeURIComponent(rid) +
      '" data-race-date="' +
      escapeHtml(dLabel) +
      '" data-race-venue="' +
      escapeHtml(info.venue || "") +
      '" data-race-name="' +
      escapeHtml(name) +
      '" data-race-conf="' +
      conf +
      '" data-race-time="' +
      escapeHtml(post) +
      '" data-race-place="' +
      escapeHtml(place) +
      '"' +
      (eng ? ' data-engine-source="' + escapeHtml(eng) + '"' : "") +
      ">" +
      '<button type="button" class="fav-btn fav-btn--icon" data-fav-toggle="' +
      escapeHtml(rid) +
      '" data-fav-place="' +
      escapeHtml(place) +
      '" data-fav-name="' +
      escapeHtml(name) +
      '" data-fav-badge="' +
      escapeHtml(grade) +
      '" data-fav-time="' +
      escapeHtml(post) +
      '" data-fav-date="' +
      escapeHtml(dFull) +
      '" aria-label="お気に入りに追加">' +
      '<span class="fav-star" aria-hidden="true">★</span></button>' +
      "<div>" +
      '<p class="race-item-place">' +
      escapeHtml(place) +
      "</p>" +
      '<p class="race-item-name">' +
      escapeHtml(nameDisp) +
      "</p>" +
      '<div class="race-item-meta">' +
      "<span>" +
      escapeHtml(post || "—") +
      "発走</span>" +
      '<span class="race-stars">' +
      starsFromScore(conf) +
      "</span></div></div>" +
      '<div class="race-item-side">' +
      '<div class="race-conf">' +
      conf +
      "%<small>AI信頼度</small></div>" +
      '<span class="btn-detail">詳細を見る ›</span></div></a>'
    );
  }

  /** ホーム「今日の本命」カード */
  function applyHomeHonmeiCard(bundle) {
    if (!bundle || !bundle.race_id) return;
    var card = document.querySelector(".ai-card--predict");
    if (!card) return;
    card.setAttribute("href", "race.html?race_id=" + encodeURIComponent(bundle.race_id));
    var score = scorePercent(bundle) || 0;
    var gauge = card.querySelector(".ai-gauge");
    var num = card.querySelector(".ai-gauge-num");
    if (gauge) {
      gauge.style.setProperty("--p", String(score));
      gauge.setAttribute("aria-label", "AI信頼度 " + score + "%");
    }
    if (num) num.textContent = score + "%";
    var info = bundle.race_info || {};
    var h = honmeiRunner(bundle);
    var desc = card.querySelector(".ai-desc");
    if (desc) {
      var place =
        (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : "");
      var horse =
        h && h.horse_number != null
          ? h.horse_number + "番 " + horseLabel(h.horse_name, h.horse_number)
          : "";
      if (place && horse) desc.textContent = place + " · " + horse;
      else if (horse) desc.textContent = "本命 " + horse;
      else if (place) desc.textContent = place + " が本日の注目";
    }
    card.classList.add("is-ready");
    card.classList.remove("is-updating");
  }

  function confidenceBandLabel(bundle) {
    var ac = (bundle && bundle.ai_confidence) || {};
    return BAND_LABEL[ac.band || "unknown"] || BAND_LABEL.unknown;
  }

  function provenanceHtml(meta, bundle) {
    meta = meta || (bundle && bundle.__meta) || {};
    var engine = meta.engine_source || "unknown";
    // 本番 UI: Mock / Fallback バッジは出さない（Real AI のみ控えめ表示）
    if (engine !== "real_ai") {
      return "";
    }
    return (
      '<div class="race-provenance is-real">' +
      '<span class="race-provenance-pill">AI予想</span>' +
      "</div>"
    );
  }

  function applyProvenanceBar(meta, bundle) {
    var el = document.getElementById("raceProvenance");
    if (!el) return;
    var html = provenanceHtml(meta, bundle);
    if (!html) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;
    el.innerHTML = html;
  }

  function marksSectionHtml(bundle) {
    var runners = (((bundle || {}).evaluation || {}).runners) || [];
    var marked = runners
      .filter(function (r) {
        return r.mark && r.mark !== "none";
      })
      .sort(function (a, b) {
        return MARK_ORDER.indexOf(a.mark) - MARK_ORDER.indexOf(b.mark);
      });
    if (!marked.length) {
      return '<p class="muted">印データなし</p>';
    }
    var html = '<div class="marks-grid">';
    marked.forEach(function (r) {
      html +=
        '<div class="mark-chip mark-chip--' +
        escapeHtml(r.mark) +
        '">' +
        '<span class="mark-chip-symbol">' +
        escapeHtml(MARK_SYMBOL[r.mark] || "—") +
        "</span>" +
        '<span class="mark-chip-num">' +
        escapeHtml(String(r.horse_number)) +
        "</span>" +
        '<span class="mark-chip-name">' +
        escapeHtml(horseLabel(r.horse_name, r.horse_number)) +
        "</span>" +
        '<span class="mark-chip-rank">#' +
        escapeHtml(String(r.model_rank != null ? r.model_rank : "—")) +
        "</span></div>";
    });
    html += "</div>";
    return html;
  }

  function pickCardsHtml(bundle) {
    var picks = ["taikou", "ana", "chuuken"];
    var html = "";
    picks.forEach(function (mark) {
      var r = runnerByMark(bundle, mark);
      if (!r) return;
      html +=
        '<article class="pick-card pick-card--' +
        mark +
        '">' +
        '<p class="pick-card-label">' +
        escapeHtml(MARK_LABEL[mark] || mark) +
        " " +
        escapeHtml(MARK_SYMBOL[mark] || "") +
        "</p>" +
        "<h4>" +
        escapeHtml(String(r.horse_number)) +
        " " +
        escapeHtml(horseLabel(r.horse_name, r.horse_number)) +
        "</h4>" +
        '<p class="pick-card-meta">評価順位 #' +
        escapeHtml(String(r.model_rank != null ? r.model_rank : "—")) +
        (typeof r.win_prob === "number"
          ? " · 勝率 " + Math.round(r.win_prob * 1000) / 10 + "%"
          : "") +
        "</p></article>";
    });
    return html || '<p class="muted">対抗・穴印なし</p>';
  }

  function reasonsSectionHtml(bundle) {
    var reasons = ((bundle.explain || {}).reasons) || [];
    if (!reasons.length) return '<p class="muted">理由データなし</p>';
    var html = '<ul class="reason-list">';
    reasons.forEach(function (r) {
      html += "<li><strong>" + escapeHtml(String(r.horse_number)) + "番</strong>";
      if (r.bullets && r.bullets.length) {
        html += "<ul>";
        r.bullets.forEach(function (b) {
          html += "<li>" + escapeHtml(b) + "</li>";
        });
        html += "</ul>";
      }
      html += "</li>";
    });
    html += "</ul>";
    return html;
  }

  function applyPaceDots(bundle) {
    var track = document.querySelector(".pace-track");
    if (!track) return;
    var top = sortedRunnersByRank(bundle).slice(0, 5);
    if (!top.length) return;
    var dots = track.querySelectorAll(".pace-dot");
    for (var i = 0; i < dots.length && i < top.length; i++) {
      dots[i].textContent = String(top[i].horse_number);
      dots[i].classList.toggle("is-dim", i >= 3);
    }
  }

  function applyMarksAndPicks(bundle) {
    var marksEl = document.getElementById("marksSectionBody");
    if (marksEl) marksEl.innerHTML = marksSectionHtml(bundle);
    var picksEl = document.getElementById("pickCardsBody");
    if (picksEl) picksEl.innerHTML = pickCardsHtml(bundle);
    var reasonsEl = document.getElementById("reasonsSectionBody");
    if (reasonsEl) reasonsEl.innerHTML = reasonsSectionHtml(bundle);
    applyPaceDots(bundle);
  }

  /**
   * レース詳細（Prediction で描画できる部分のみ）
   * Analysis 依存: .radar-box / .score-list は触らない
   */
  function applyRaceDetail(bundle, meta, expectedRaceId) {
    if (!bundle) return null;
    if (expectedRaceId && bundle.race_id && bundle.race_id !== expectedRaceId) {
      return { mismatch: true, raceId: bundle.race_id, expectedRaceId: expectedRaceId };
    }
    meta = meta || bundle.__meta || {};
    applyProvenanceBar(meta, bundle);
    applyMarksAndPicks(bundle);
    var info = bundle.race_info || {};
    var conf = scorePercent(bundle);
    var honmei = honmeiRunner(bundle);
    var bandLabel = confidenceBandLabel(bundle);

    var titleEl = document.getElementById("raceTitle");
    var subEl = document.querySelector(".brand-sub");
    if (titleEl) {
      titleEl.textContent =
        (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : "");
    }
    if (subEl) {
      var bits = [];
      if (info.class_label) bits.push(info.class_label);
      if (info.grade) bits.push(String(info.grade));
      var left = bits.join(" · ");
      subEl.textContent = left + (info.post_time ? (left ? " · " : "") + info.post_time : "");
    }

    var card = document.querySelector(".honmei-card");
    if (card && honmei) {
      var num = card.querySelector(".honmei-num");
      var h2 = card.querySelector("h2");
      var p = card.querySelector("p");
      var stars = card.querySelector(".race-stars");
      if (num) num.textContent = String(honmei.horse_number);
      if (h2) h2.textContent = horseLabel(honmei.horse_name, honmei.horse_number);
      if (p) {
        p.textContent =
          "AI本命 · 信頼度 " +
          (conf != null ? conf : "—") +
          (conf != null ? "%" : "") +
          "（" +
          bandLabel +
          "）";
      }
      if (stars && conf != null) stars.textContent = starsFromScore(conf);
    }

    var confEl = document.getElementById("raceConfidenceDetail");
    if (confEl && bundle.ai_confidence) {
      var ac = bundle.ai_confidence;
      var factors = publicFactors(ac.factors || []);
      confEl.innerHTML =
        "<p>信頼度 <strong>" +
        (conf != null ? conf + "%" : "—") +
        "</strong>（" +
        escapeHtml(bandLabel) +
        "）</p>" +
        (factors.length
          ? "<ul>" +
            factors
              .slice(0, 5)
              .map(function (f) {
                return "<li>" + escapeHtml(f) + "</li>";
              })
              .join("") +
            "</ul>"
          : "");
    }

    var narrativeEl = document.querySelector(".pace-card p");
    if (narrativeEl && bundle.explain && bundle.explain.narrative) {
      narrativeEl.textContent = bundle.explain.narrative;
    }

    var place =
      (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : "");
    return {
      raceId: bundle.race_id,
      place: place,
      name: info.class_label || "",
      badge: info.grade || "",
      postTime: info.post_time || "",
      dateLabel: dateFull(info),
      conf: conf,
      meta: meta,
      coreRaceId: meta.core_race_id || null,
    };
  }

  function pickTopByConfidence(bundles) {
    if (!bundles || !bundles.length) return null;
    return bundles.slice().sort(function (a, b) {
      return (scorePercent(b) || 0) - (scorePercent(a) || 0);
    })[0];
  }

  global.ExpectPredictionBind = {
    scorePercent: scorePercent,
    starsFromScore: starsFromScore,
    dateLabel: dateLabel,
    raceCardHtml: raceCardHtml,
    applyHomeHonmeiCard: applyHomeHonmeiCard,
    applyRaceDetail: applyRaceDetail,
    pickTopByConfidence: pickTopByConfidence,
    honmeiRunner: honmeiRunner,
    runnerByMark: runnerByMark,
    sortedRunnersByRank: sortedRunnersByRank,
    provenanceHtml: provenanceHtml,
    marksSectionHtml: marksSectionHtml,
    pickCardsHtml: pickCardsHtml,
    reasonsSectionHtml: reasonsSectionHtml,
  };
})(window);
