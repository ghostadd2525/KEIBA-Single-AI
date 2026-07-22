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
  var CONFIDENCE_NOTE = "過去の同条件実績も含めた評価です";
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

  function starsFromBand(band) {
    if (band === "high") return "★★★★★";
    if (band === "medium") return "★★★☆☆";
    if (band === "low") return "★★☆☆☆";
    return "☆☆☆☆☆";
  }

  function bandFromNormalizedScore(score) {
    if (score == null || !Number.isFinite(Number(score))) return "unknown";
    var s = Number(score);
    if (s > 1) s = s / 100;
    if (s >= 0.6) return "high";
    if (s >= 0.35) return "medium";
    return "low";
  }

  /** 一覧カード右側 — 星＋ラベル（% 非表示）の内側 HTML */
  function raceConfidenceSideInner(band, stars) {
    var label = BAND_LABEL[band] || BAND_LABEL.unknown;
    var starText = stars || starsFromBand(band);
    return (
      '<span class="race-conf-stars" aria-hidden="true">' +
      starText +
      "</span>" +
      '<span class="race-conf-label">' +
      escapeHtml(label) +
      "</span>" +
      "<small>自信度</small>"
    );
  }

  /** 詳細ページ — 内訳（モデル評価 / 条件別実績） */
  function raceConfidenceDetailHtml(bundle) {
    var ac = (bundle && bundle.ai_confidence) || {};
    var comp = ac.component_scores || {};
    var band = ac.band && BAND_LABEL[ac.band] ? ac.band : bandFromNormalizedScore(ac.score);
    var bandLabel = BAND_LABEL[band] || BAND_LABEL.unknown;
    var stars = starsFromBand(band);
    var modelScore = comp.model_score != null ? comp.model_score : ac.score;
    var modelBand = bandFromNormalizedScore(modelScore);
    var segmentRate = comp.segment_hit_rate;
    var segmentBand = segmentRate != null ? bandFromNormalizedScore(segmentRate) : null;

    var html = '<div class="confidence-detail-v2">';
    html +=
      '<p class="confidence-summary">このレースの自信度：<strong>' +
      escapeHtml(bandLabel) +
      '</strong> <span class="race-stars" aria-hidden="true">' +
      stars +
      "</span></p>";
    html +=
      '<p class="confidence-footnote muted">' +
      escapeHtml(CONFIDENCE_NOTE) +
      "（％は的中率ではありません）</p>";
    html += '<dl class="confidence-breakdown">';
    html +=
      '<div class="confidence-breakdown-row"><dt>レース評価</dt><dd>モデルが見た◎の強さ：<strong>' +
      escapeHtml(BAND_LABEL[modelBand] || "—") +
      "</strong></dd></div>";
    if (segmentRate != null) {
      var segLabel = BAND_LABEL[segmentBand] || BAND_LABEL.unknown;
      var scopeNote = "";
      if (comp.segment_scope === "venue_surface_distance" && comp.segment_key) {
        scopeNote = "（" + String(comp.segment_key).replace(/\|/g, "·") + "）";
      } else if (comp.segment_scope === "venue") {
        scopeNote = "（" + String(comp.segment_key || "会場") + "）";
      } else if (comp.segment_scope === "venue_surface") {
        scopeNote = "（" + String(comp.segment_key || "会場·馬場") + "）";
      } else if (comp.segment_scope === "overall") {
        scopeNote = "（全体実績）";
      }
      html +=
        '<div class="confidence-breakdown-row"><dt>条件別実績</dt><dd>同条件の過去◎実績：<strong>' +
        escapeHtml(segLabel) +
        "</strong>" +
        escapeHtml(scopeNote) +
        "</dd></div>";
    }
    html += "</dl></div>";
    return html;
  }

  function summaryScorePercent(confidence) {
    if (!confidence || typeof confidence.score !== "number") return null;
    var s = confidence.score;
    return s <= 1 ? Math.round(s * 100) : Math.round(s);
  }

  function dateFromRaceId(raceId) {
    var m = String(raceId || "").match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : "";
  }

  /**
   * RaceCardSummary → 一覧カード HTML（v2_race_list_ui）
   * short_reason は Phase 1 未表示。
   * @param {object} card RaceCardSummary
   * @param {{ listDate?: string }} [opts]
   */
  function raceCardSummaryHtml(card, opts) {
    opts = opts || {};
    var info = (card && card.race_info) || {};
    var pred = (card && card.prediction) || {};
    var status = String(pred.status || "missing");
    var summary = card && card.summary;
    var rid = (card && card.race_id) || "";
    var raceNo = info.race_number != null ? info.race_number : info.race_no;
    var place =
      info.race_label ||
      (info.venue || "") + (raceNo != null ? " " + raceNo + "R" : "");
    var name = info.race_name || info.class_label || "レース";
    var grade = info.grade || "";
    var post = info.post_time != null ? String(info.post_time) : "";
    var listDate =
      opts.listDate ||
      info.date ||
      dateFromRaceId(rid) ||
      "";
    var dLabel =
      info.date_label ||
      (global.ExpectRaceListUrl && ExpectRaceListUrl.dateLabelFromIso
        ? ExpectRaceListUrl.dateLabelFromIso(listDate)
        : dateLabel({ date: listDate }));
    var dFull = info.date_full || dateFull({ date: listDate, date_label: dLabel });
    var bg = bgClass(info, raceNo);
    var nameDisp = name + (grade && grade !== "—" ? "（" + grade + "）" : "");
    var eng = pred.engine_source || "";

    var confPct = null;
    var band = null;
    var statusNote = "";
    var stars = "☆☆☆☆☆";
    var confSide = "—<small>自信度</small>";
    var confAriaLabel = "";
    var honmeiNameAttr = "";

    if (status === "ready" && summary) {
      var honmei = summary.honmei;
      var confidence = summary.confidence;
      confPct = summaryScorePercent(confidence);
      band = confidence && confidence.band ? confidence.band : null;
      if (honmei && honmei.horse_name) {
        honmeiNameAttr = String(honmei.horse_name).trim();
      }
      if (band) stars = starsFromBand(band);
      else if (confPct != null) stars = starsFromScore(confPct);
      if (band) {
        confSide = raceConfidenceSideInner(band, stars);
        confAriaLabel = "このレースの自信度 " + (BAND_LABEL[band] || BAND_LABEL.unknown);
      } else if (confPct != null) {
        var fbBand = bandFromNormalizedScore(confPct / 100);
        confSide = raceConfidenceSideInner(fbBand, stars);
        confAriaLabel = "このレースの自信度 " + (BAND_LABEL[fbBand] || BAND_LABEL.unknown);
      }
    } else if (status === "processing") {
      confSide = "—<small>自信度</small>";
      statusNote = '<p class="race-item-status-note muted">予想準備中</p>';
    } else if (status === "failed") {
      statusNote = '<p class="race-item-status-note muted">予想取得失敗</p>';
      confSide = "—<small>自信度</small>";
    } else {
      // missing（および未知 status）
      status = status === "missing" ? "missing" : status;
      statusNote = '<p class="race-item-status-note muted">予想未公開</p>';
      confSide = "—<small>自信度</small>";
    }

    // short_reason は Phase 1 未表示（フィールドがあっても出さない）

    return (
      '<a class="race-item race-item--bg' +
      bg +
      '" href="race.html?race_id=' +
      encodeURIComponent(rid) +
      '" data-race-date="' +
      escapeHtml(listDate || dLabel) +
      '" data-race-venue="' +
      escapeHtml(info.venue || "") +
      '" data-race-name="' +
      escapeHtml(name) +
      '" data-race-conf="' +
      (confPct != null ? confPct : 0) +
      '" data-race-time="' +
      escapeHtml(post) +
      '" data-race-place="' +
      escapeHtml(place) +
      '" data-race-honmei="' +
      escapeHtml(honmeiNameAttr) +
      '" data-prediction-status="' +
      escapeHtml(status) +
      '"' +
      (band ? ' data-confidence-band="' + escapeHtml(band) + '"' : "") +
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
      '"' +
      (honmeiNameAttr
        ? ' data-fav-honmei="' + escapeHtml(honmeiNameAttr) + '"'
        : "") +
      (status === "ready" && summary && summary.honmei && summary.honmei.horse_number != null
        ? ' data-fav-honmei-num="' + escapeHtml(String(summary.honmei.horse_number)) + '"'
        : "") +
      (confPct != null ? ' data-fav-conf="' + escapeHtml(String(confPct)) + '"' : "") +
      (band ? ' data-fav-band="' + escapeHtml(band) + '"' : "") +
      ' aria-label="お気に入りに追加">' +
      '<span class="fav-star" aria-hidden="true">★</span></button>' +
      "<div>" +
      '<p class="race-item-place">' +
      escapeHtml(place) +
      "</p>" +
      '<p class="race-item-name">' +
      escapeHtml(nameDisp) +
      "</p>" +
      statusNote +
      '<div class="race-item-meta">' +
      "<span>" +
      escapeHtml(post || "—") +
      "発走</span>" +
      (band || confPct != null
        ? ""
        : '<span class="race-stars">' + stars + "</span>") +
      "</div></div>" +
      '<div class="race-item-side">' +
      '<div class="race-conf"' +
      (confAriaLabel
        ? ' title="' +
          escapeHtml(CONFIDENCE_NOTE) +
          '" aria-label="' +
          escapeHtml(confAriaLabel) +
          '"'
        : "") +
      ">" +
      confSide +
      "</div>" +
      '<span class="btn-detail">詳細を見る ›</span></div></a>'
    );
  }

  /** レース一覧カード HTML（既存 .race-item 構造を維持）— Flag OFF / v1.1 */
  function raceCardHtml(bundle) {
    var info = (bundle && bundle.race_info) || {};
    var rid = (bundle && bundle.race_id) || info.race_id || "";
    var place =
      info.race_label ||
      (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : "");
    var name = info.race_name || info.class_label || "レース";
    var grade = info.grade || "";
    var conf = scorePercent(bundle) || 0;
    var band = bandFromNormalizedScore(
      (bundle && bundle.ai_confidence && bundle.ai_confidence.score) || conf / 100
    );
    var stars = starsFromBand(band);
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
      escapeHtml(info.date || dLabel) +
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
      "発走</span></div></div>" +
      '<div class="race-item-side">' +
      '<div class="race-conf" title="' +
      escapeHtml(CONFIDENCE_NOTE) +
      '" aria-label="このレースの自信度 ' +
      escapeHtml(BAND_LABEL[band] || BAND_LABEL.unknown) +
      '">' +
      raceConfidenceSideInner(band, stars) +
      "</div>" +
      '<span class="btn-detail">詳細を見る ›</span></div></a>'
    );
  }

  /** ホーム「今日の本命」カード（当日分は localStorage に固定） */
  var HOME_HONMEI_CACHE_KEY = "expect_home_honmei_v1";

  function homeHonmeiCacheDate() {
    if (global.ExpectRealDataBind && ExpectRealDataBind.resolveHomeDate) {
      return ExpectRealDataBind.resolveHomeDate() || "";
    }
    return "";
  }

  function readHomeHonmeiCache(dateKey) {
    try {
      var raw = global.localStorage.getItem(HOME_HONMEI_CACHE_KEY);
      if (!raw) return null;
      var o = JSON.parse(raw);
      if (!o || !o.race_id) return null;
      if (dateKey && o.date && o.date !== dateKey) return null;
      return o;
    } catch (e) {
      return null;
    }
  }

  function writeHomeHonmeiCache(snapshot) {
    try {
      global.localStorage.setItem(HOME_HONMEI_CACHE_KEY, JSON.stringify(snapshot));
    } catch (e) { /* ignore */ }
  }

  function applyHomeHonmeiSnapshot(snapshot) {
    if (!snapshot || !snapshot.race_id) return false;
    var card = document.querySelector(".ai-card--predict");
    if (!card) return false;
    card.setAttribute("href", "race.html?race_id=" + encodeURIComponent(snapshot.race_id));
    var score = snapshot.score != null ? Number(snapshot.score) : 0;
    var gauge = card.querySelector(".ai-gauge");
    var num = card.querySelector(".ai-gauge-num");
    if (gauge) {
      gauge.style.setProperty("--p", String(score));
      gauge.setAttribute("aria-label", "AI信頼度 " + score + "%");
    }
    if (num) num.textContent = score + "%";
    var desc = card.querySelector(".ai-desc");
    if (desc && snapshot.desc) desc.textContent = snapshot.desc;
    card.classList.add("is-ready");
    card.classList.remove("is-updating");
    card.setAttribute("data-honmei-cached", "1");
    return true;
  }

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
    var descText = "";
    if (desc) {
      var place =
        (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : "");
      var horse =
        h && h.horse_number != null
          ? h.horse_number + "番 " + horseLabel(h.horse_name, h.horse_number)
          : "";
      if (place && horse) descText = place + " · " + horse;
      else if (horse) descText = "本命 " + horse;
      else if (place) descText = place + " が本日の注目";
      if (descText) desc.textContent = descText;
    }
    card.classList.add("is-ready");
    card.classList.remove("is-updating");
    writeHomeHonmeiCache({
      date: homeHonmeiCacheDate(),
      race_id: bundle.race_id,
      score: score,
      desc: descText || (desc && desc.textContent) || "",
      venues: info.venue ? [String(info.venue)] : [],
      at: Date.now(),
    });
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
    var explain = (bundle && bundle.explain) || {};
    var v2On =
      global.ExpectUiFeatures &&
      typeof ExpectUiFeatures.enabled === "function" &&
      ExpectUiFeatures.enabled("v2_explain");

    if (v2On && explain.reason) {
      return explainV2SectionHtml(explain, bundle && bundle.race_id);
    }

    var reasons = explain.reasons || [];
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

  /** v2_explain Flag ON — ユーザー向け本命理由 */
  function explainV2SectionHtml(explain, raceId) {
    var reason = explain.reason || {};
    var dk = reason.decision_key || {};
    var conf = explain.confidence_reason || {};
    var trace = explain.decision_trace || {};
    var html = '<div class="explain-v2">';

    if (reason.summary) {
      html += '<p class="explain-summary">' + escapeHtml(String(reason.summary)) + "</p>";
    } else if (dk.label) {
      html +=
        '<p class="explain-summary">' +
        escapeHtml(String(dk.label)) +
        (dk.text ? " — " + escapeHtml(String(dk.text)) : "") +
        "</p>";
    }

    var factors = Array.isArray(reason.factors) ? reason.factors : [];
    var userFactors = factors.filter(function (f) {
      return f.kind !== "comparison" && f.kind !== "repick";
    });
    if (userFactors.length) {
      html += '<ul class="reason-list explain-factors">';
      userFactors.forEach(function (f) {
        html +=
          "<li><strong>" +
          escapeHtml(String(f.label || "")) +
          "</strong> " +
          escapeHtml(String(f.text || "")) +
          "</li>";
      });
      html += "</ul>";
    }

    if (conf.summary) {
      html += '<div class="explain-confidence">';
      html += "<h4>信頼度について</h4>";
      html += "<p>" + escapeHtml(String(conf.summary)) + "</p>";
      html += "</div>";
    }

    var stages = trace.stages && Array.isArray(trace.stages) ? trace.stages : [];
    if (stages.length) {
      html +=
        '<details class="explain-trace"><summary>詳細（開発者向け）</summary><ol class="explain-trace-list">';
      stages.forEach(function (s) {
        var delta = s.delta || {};
        var stageLabel = explainStageLabel(String(s.stage || ""));
        html +=
          "<li><span class=\"explain-trace-stage\">" +
          escapeHtml(stageLabel) +
          '</span> <span class="explain-trace-status">[' +
          escapeHtml(explainStatusLabel(String(s.status || ""))) +
          "]</span> " +
          escapeHtml(String(delta.summary || ""));
        html += "</li>";
      });
      html += "</ol></details>";
    }

    html += explainKaobaCtaHtml({
      explain: explain,
      race_id: raceId || "",
    });
    html += "</div>";
    return html;
  }

  function explainStageLabel(stage) {
    var map = {
      candidate_evaluation: "AI予測",
      world_classification: "レース傾向の判定",
      candidate_pool: "候補の絞り込み",
      entry: "候補への追加",
      repick: "候補の並べ替え",
      delete: "除外ルール",
      mark_assignment: "印の付与",
    };
    return map[stage] || stage;
  }

  function explainStatusLabel(status) {
    var map = {
      applied: "適用",
      skipped: "見送り",
      locked: "固定",
      not_applied: "未適用",
    };
    return map[status] || status;
  }

  /**
   * Phase 3: v2_explain ON 時のみ KAOBA explain_pick 導線
   */
  function explainKaobaCtaHtml(bundle) {
    var v2On =
      global.ExpectUiFeatures &&
      typeof ExpectUiFeatures.enabled === "function" &&
      ExpectUiFeatures.enabled("v2_explain");
    if (!v2On) return "";
    if (!(bundle && bundle.explain && bundle.explain.reason)) return "";
    var rid = (bundle && bundle.race_id) || "";
    var href =
      "chat.html?race_id=" +
      encodeURIComponent(rid) +
      "&prompt=" +
      encodeURIComponent("なぜ本命なの？理由を教えて");
    return (
      '<p class="explain-kaoba-cta"><a class="explain-kaoba-link" href="' +
      href +
      '">KAOBAに◎の理由を聞く</a></p>'
    );
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
    var ac = bundle.ai_confidence || {};
    var band =
      ac.band && BAND_LABEL[ac.band] ? ac.band : bandFromNormalizedScore(ac.score);
    var bandLabel = BAND_LABEL[band] || BAND_LABEL.unknown;

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
        p.textContent = "AI本命 · 自信度：" + bandLabel;
      }
      if (stars && conf != null) stars.textContent = starsFromBand(band);

      // v2_explain: 本命カード下に決定打 1 行（Flag OFF 時は要素を除去して v1.1 恒等）
      var dkHost = card.querySelector(".explain-honmei-decision");
      var v2Explain =
        global.ExpectUiFeatures &&
        ExpectUiFeatures.enabled("v2_explain") &&
        bundle.explain &&
        bundle.explain.reason &&
        bundle.explain.reason.decision_key;
      if (v2Explain) {
        var dk = bundle.explain.reason.decision_key;
        if (!dkHost) {
          dkHost = document.createElement("p");
          dkHost.className = "explain-honmei-decision muted";
          var insertAfter = stars || p;
          if (insertAfter && insertAfter.parentNode) {
            insertAfter.parentNode.insertBefore(dkHost, insertAfter.nextSibling);
          }
        }
        dkHost.textContent =
          "決定打: " +
          String(dk.label || "") +
          (dk.text ? " — " + String(dk.text) : "");
      } else if (dkHost) {
        dkHost.remove();
      }
    }

    var confEl = document.getElementById("raceConfidenceDetail");
    if (confEl && bundle.ai_confidence) {
      confEl.innerHTML = raceConfidenceDetailHtml(bundle);
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
    starsFromBand: starsFromBand,
    dateLabel: dateLabel,
    raceCardHtml: raceCardHtml,
    raceCardSummaryHtml: raceCardSummaryHtml,
    applyHomeHonmeiCard: applyHomeHonmeiCard,
    applyHomeHonmeiSnapshot: applyHomeHonmeiSnapshot,
    readHomeHonmeiCache: readHomeHonmeiCache,
    homeHonmeiCacheDate: homeHonmeiCacheDate,
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
