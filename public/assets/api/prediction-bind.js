/**
 * Phase1: PredictionBundle → UI バインド（ui-api-mapping.md 準拠）
 * Analysis / Ticket / Kaoba は使わない。
 * I3: Bundle 供給元は Prediction または SingleDetail（Flag）。レイアウト/描画は非変更。
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

  /** "15:10" / "9:50" / "15:10:00" → "15:10" */
  function normalizePostTime(raw) {
    var m = String(raw == null ? "" : raw).trim().match(/^(\d{1,2}):(\d{2})/);
    if (!m) return "";
    return String(Number(m[1])).padStart(2, "0") + ":" + m[2];
  }

  /** "2歳新馬 10:20芝1600m9頭" → "2歳新馬" */
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
  var BAND_LABEL = {
    high: "高い",
    rather_high: "やや高い",
    medium: "ふつう",
    low: "低い",
    unknown: "不明",
  };

  /** UI8: 内部ラベル + score → 4段階 band（ラベル名は UI 非表示） */
  var CONFIDENCE_BAND_HIGH = 0.75;
  var CONFIDENCE_BAND_RATHER_HIGH = 0.6;
  var CONFIDENCE_BAND_MEDIUM = 0.35;
  var BAND_RANK = { high: 3, rather_high: 2, medium: 1, low: 0 };
  var RANK_TO_BAND = ["low", "medium", "rather_high", "high"];
  var LABEL_CEILING_BAND = {
    normal: "high",
    near_miss: "rather_high",
    affinity_residual: "medium",
    pure_residual: "low",
  };
  var CONFIDENCE_NOTE = "過去の同条件実績も含めた評価です";
  var FEATURE_LABEL = { db: "DB", daily_csv: "日次CSV", global_csv: "全体CSV" };

  function normalizeConfidenceScore(score) {
    if (score == null || !Number.isFinite(Number(score))) return null;
    var s = Number(score);
    if (s > 1) s = s / 100;
    return s;
  }

  function starsFromBand(band) {
    if (band === "high") return "★★★★★";
    if (band === "rather_high") return "★★★★☆";
    if (band === "medium") return "★★★☆☆";
    if (band === "low") return "★★☆☆☆";
    return "☆☆☆☆☆";
  }

  function bandFromNormalizedScore(score) {
    if (score == null || !Number.isFinite(Number(score))) return "unknown";
    var s = normalizeConfidenceScore(score);
    if (s == null) return "unknown";
    if (s >= CONFIDENCE_BAND_HIGH) return "high";
    if (s >= CONFIDENCE_BAND_RATHER_HIGH) return "rather_high";
    if (s >= CONFIDENCE_BAND_MEDIUM) return "medium";
    return "low";
  }

  function internalLabelFromScore(score) {
    var band = bandFromNormalizedScore(score);
    if (band === "high") return "normal";
    if (band === "rather_high") return "near_miss";
    if (band === "medium") return "affinity_residual";
    return "pure_residual";
  }

  function internalLabelFromWorld(world, extras) {
    extras = extras || {};
    if (extras.near_miss != null && extras.near_miss !== false) return "near_miss";
    if (extras.affinity != null && extras.affinity !== false) return "affinity_residual";
    var w = String(world || "")
      .trim()
      .toLowerCase();
    if (!w) return null;
    if (w === "core_world" || w === "core") return "normal";
    if (w === "midupper_world" || w === "midupper") return "near_miss";
    if (w === "midhole_world" || w === "midhole") return "affinity_residual";
    if (w === "rank7_world" || w === "rank7") return "pure_residual";
    if (w === "mixed_world" || w === "mixed") return "affinity_residual";
    if (w === "unsatisfied" || w === "bug_world" || w === "bug") return "pure_residual";
    return null;
  }

  function resolveInternalLabel(input) {
    input = input || {};
    var fromWorld = internalLabelFromWorld(input.world, {
      near_miss: input.near_miss,
      affinity: input.affinity,
    });
    if (fromWorld) return fromWorld;
    return internalLabelFromScore(input.score);
  }

  function confidenceBandFromLabelAndScore(label, score) {
    var resolved =
      label && LABEL_CEILING_BAND[label] ? label : resolveInternalLabel({ score: score });
    var labelBand = LABEL_CEILING_BAND[resolved] || "low";
    var scoreBand = bandFromNormalizedScore(score);
    if (scoreBand === "unknown") scoreBand = "low";
    var rank = Math.min(BAND_RANK[labelBand] || 0, BAND_RANK[scoreBand] || 0);
    return RANK_TO_BAND[rank];
  }

  function displayBandFromBundle(bundle) {
    var ac = (bundle && bundle.ai_confidence) || {};
    var score = ac.score;
    var world =
      bundle && bundle.evaluation && bundle.evaluation.world != null
        ? bundle.evaluation.world
        : null;
    var label = resolveInternalLabel({ world: world, score: score });
    return confidenceBandFromLabelAndScore(label, score);
  }

  function displayBandFromSummary(summary) {
    if (!summary || !summary.confidence) return "unknown";
    var confidence = summary.confidence;
    // BFF が UI8 band を既に計算済みならそれを優先（内部ラベルは summary に載せない）
    if (confidence.band && BAND_LABEL[confidence.band]) return confidence.band;
    return bandFromNormalizedScore(confidence.score);
  }

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
    var band = displayBandFromBundle(bundle);
    if (!BAND_LABEL[band]) {
      band = ac.band && BAND_LABEL[ac.band] ? ac.band : bandFromNormalizedScore(ac.score);
    }
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
    var name = shortRaceName(info.race_name || info.class_label || "レース");
    var grade = info.grade || "";
    var post = info.post_time != null ? String(info.post_time) : "";
    var listDate =
      info.date ||
      dateFromRaceId(rid) ||
      opts.listDate ||
      "";
    // data-race-date は常に ISO（フィルタ state.date と一致させる）
    var dateAttr =
      (/^\d{4}-\d{2}-\d{2}$/.test(String(info.date || ""))
        ? String(info.date)
        : "") ||
      dateFromRaceId(rid) ||
      (/^\d{4}-\d{2}-\d{2}$/.test(String(opts.listDate || ""))
        ? String(opts.listDate)
        : "") ||
      listDate;
    var dLabel =
      info.date_label ||
      (global.ExpectRaceListUrl && ExpectRaceListUrl.dateLabelFromIso
        ? ExpectRaceListUrl.dateLabelFromIso(listDate)
        : dateLabel({ date: listDate }));
    var dFull = info.date_full || dateFull({ date: listDate, date_label: dLabel });
    var bg = bgClass(info, raceNo);
    var nameDisp = name;
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
      // UI8: BFF の label+score band を優先（score のみ再計算しない）
      band = displayBandFromSummary(summary);
      if (band === "unknown") band = null;
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
      // 自信度ボックス内に状態を出す（左カラム下だと見落とされやすい）
      confSide =
        '<span class="race-conf-status">予想準備中</span><small>自信度</small>';
      confAriaLabel = "このレースの自信度 予想準備中";
      statusNote = "";
    } else if (status === "failed") {
      confSide =
        '<span class="race-conf-status">取得失敗</span><small>自信度</small>';
      confAriaLabel = "このレースの自信度 予想取得失敗";
      statusNote = "";
    } else {
      // missing（および未知 status）
      status = status === "missing" ? "missing" : status;
      confSide =
        '<span class="race-conf-status">未公開</span><small>自信度</small>';
      confAriaLabel = "このレースの自信度 予想未公開";
      statusNote = "";
    }

    // short_reason は Phase 1 未表示（フィールドがあっても出さない）

    return (
      '<a class="race-item race-item--bg' +
      bg +
      '" href="race.html?race_id=' +
      encodeURIComponent(rid) +
      '" data-race-date="' +
      escapeHtml(dateAttr) +
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
      // 発走時間は prediction status に関係なく常時・同位置（基本情報レイヤ）
      (post
        ? '<span class="race-item-time">' +
          escapeHtml(normalizePostTime(post)) +
          "出走</span>"
        : '<span class="race-item-time race-item-time--empty" hidden></span>') +
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
    var name = shortRaceName(info.race_name || info.class_label || "レース");
    var grade = info.grade || "";
    var conf = scorePercent(bundle) || 0;
    var band = displayBandFromBundle(bundle);
    var stars = starsFromBand(band);
    var dLabel = dateLabel(info);
    var dFull = dateFull(info);
    var post = info.post_time || "";
    var bg = bgClass(info, info.race_no);
    var nameDisp = name;
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
      (post
        ? "<span>" + escapeHtml(normalizePostTime(post)) + "出走</span>"
        : "") +
      "</div></div>" +
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
  var HOME_HONMEI_CACHE_KEY = "expect_home_honmei_v2";

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
      if (!o) return null;
      if (dateKey && o.date && o.date !== dateKey) return null;
      if (!o.race_id && !o.empty) return null;
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
    if (!snapshot) return false;
    var card = document.querySelector(".ai-card--predict");
    if (!card) return false;
    if (snapshot.empty || !snapshot.race_id) {
      applyHomeHonmeiEmpty(card);
      return true;
    }
    card.setAttribute("href", "race.html?race_id=" + encodeURIComponent(snapshot.race_id));
    var band = snapshot.band && BAND_LABEL[snapshot.band] ? snapshot.band : null;
    var stars = snapshot.stars || (band ? starsFromBand(band) : "☆☆☆☆☆");
    var bandLabel = band ? BAND_LABEL[band] : "—";
    var gauge = card.querySelector(".ai-gauge");
    var num = card.querySelector(".ai-gauge-num");
    var gLabel = card.querySelector(".ai-gauge-label");
    if (gauge) {
      gauge.classList.add("ai-gauge--stars");
      var score = snapshot.score != null ? Number(snapshot.score) : 0;
      gauge.style.setProperty("--p", String(score));
      gauge.setAttribute(
        "aria-label",
        "自信度 " + bandLabel + " " + stars
      );
    }
    if (num) num.textContent = stars;
    if (gLabel) gLabel.textContent = bandLabel;
    var desc = card.querySelector(".ai-desc");
    if (desc && snapshot.desc) desc.textContent = snapshot.desc;
    card.classList.add("is-ready");
    card.classList.remove("is-updating");
    card.classList.remove("is-empty-honmei");
    card.setAttribute("data-honmei-cached", "1");
    return true;
  }

  function homeHonmeiDesc(bundle) {
    var info = (bundle && bundle.race_info) || {};
    var venue = info.venue || "";
    var raceNo = info.race_no != null ? info.race_no : info.race_number;
    var raceName = shortRaceName(info.race_name || info.class_label || "");
    var parts = [];
    if (venue && raceNo != null) parts.push(venue + " " + raceNo + "R");
    else if (venue) parts.push(String(venue));
    else if (raceNo != null) parts.push(raceNo + "R");
    if (raceName) parts.push(raceName);
    return parts.join(" · ");
  }

  function applyHomeHonmeiCard(bundle) {
    var card = document.querySelector(".ai-card--predict");
    if (!card) return;
    if (!bundle || !bundle.race_id) {
      applyHomeHonmeiEmpty(card);
      return;
    }
    var band = displayBandFromBundle(bundle);
    var stars = starsFromBand(band);
    var bandLabel = BAND_LABEL[band] || BAND_LABEL.unknown;
    var score = scorePercent(bundle) || 0;
    card.setAttribute("href", "race.html?race_id=" + encodeURIComponent(bundle.race_id));
    var gauge = card.querySelector(".ai-gauge");
    var num = card.querySelector(".ai-gauge-num");
    var gLabel = card.querySelector(".ai-gauge-label");
    if (gauge) {
      gauge.classList.add("ai-gauge--stars");
      gauge.style.setProperty("--p", String(score));
      gauge.setAttribute("aria-label", "自信度 " + bandLabel + " " + stars);
    }
    if (num) num.textContent = stars;
    if (gLabel) gLabel.textContent = bandLabel;
    var info = bundle.race_info || {};
    var desc = card.querySelector(".ai-desc");
    var descText = homeHonmeiDesc(bundle);
    if (desc && descText) desc.textContent = descText;
    card.classList.add("is-ready");
    card.classList.remove("is-updating");
    card.classList.remove("is-empty-honmei");
    writeHomeHonmeiCache({
      date: homeHonmeiCacheDate(),
      race_id: bundle.race_id,
      score: score,
      band: band,
      stars: stars,
      desc: descText || (desc && desc.textContent) || "",
      venues: info.venue ? [String(info.venue)] : [],
      empty: false,
      at: Date.now(),
    });
  }

  function applyHomeHonmeiEmpty(card) {
    card = card || document.querySelector(".ai-card--predict");
    if (!card) return;
    card.setAttribute("href", "races.html");
    var gauge = card.querySelector(".ai-gauge");
    var num = card.querySelector(".ai-gauge-num");
    var gLabel = card.querySelector(".ai-gauge-label");
    if (gauge) {
      gauge.classList.add("ai-gauge--stars");
      gauge.style.setProperty("--p", "0");
      gauge.setAttribute("aria-label", "本日の本命候補なし");
    }
    if (num) num.textContent = "☆☆☆☆☆";
    if (gLabel) gLabel.textContent = "—";
    var desc = card.querySelector(".ai-desc");
    var descText = "本日 ★★★★☆ 以上の候補がありません";
    if (desc) desc.textContent = descText;
    card.classList.add("is-ready");
    card.classList.add("is-empty-honmei");
    card.classList.remove("is-updating");
    writeHomeHonmeiCache({
      date: homeHonmeiCacheDate(),
      race_id: "",
      score: 0,
      band: null,
      stars: "☆☆☆☆☆",
      desc: descText,
      venues: [],
      empty: true,
      at: Date.now(),
    });
  }

  function confidenceBandLabel(bundle) {
    var band = displayBandFromBundle(bundle);
    return BAND_LABEL[band] || BAND_LABEL.unknown;
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
        escapeHtml(
          String(
            r.number != null
              ? r.number
              : r.horse_number != null
                ? r.horse_number
                : "—"
          )
        ) +
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
        escapeHtml(
          String(
            r.number != null
              ? r.number
              : r.horse_number != null
                ? r.horse_number
                : "—"
          )
        ) +
        " " +
        escapeHtml(horseLabel(r.horse_name, r.horse_number)) +
        "</h4>" +
        '<p class="pick-card-meta">モデル評価順位 #' +
        escapeHtml(String(r.model_rank != null ? r.model_rank : "—")) +
        (typeof r.win_prob === "number"
          ? " · 1着確率　" + Math.round(r.win_prob * 1000) / 10 + "%"
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
      return explainV2SectionHtml(explain, bundle);
    }

    var reasons = explain.reasons || [];
    if (!reasons.length) {
      return (
        '<p class="muted">理由データなし</p>' +
        explainKaobaCtaHtml({ explain: explain, race_id: (bundle && bundle.race_id) || "", bundle: bundle })
      );
    }
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
    html += explainKaobaCtaHtml({
      explain: explain,
      race_id: (bundle && bundle.race_id) || "",
      bundle: bundle,
    });
    return html;
  }

  /** v2_explain Flag ON — ユーザー向け本命理由 */
  function explainV2SectionHtml(explain, bundleOrRaceId) {
    var bundle =
      bundleOrRaceId && typeof bundleOrRaceId === "object" ? bundleOrRaceId : null;
    var raceId = bundle
      ? bundle.race_id || ""
      : bundleOrRaceId || "";
    var reason = explain.reason || {};
    var dk = reason.decision_key || {};
    var conf = explain.confidence_reason || {};
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

    html += explainKaobaCtaHtml({
      explain: explain,
      race_id: raceId || "",
      bundle: bundle,
    });
    html += "</div>";
    return html;
  }

  /**
   * V5: Explain パネルから Conversation（mode=explain）へ。
   * prompt を自動送信し、吹き出し用 display も付与する。
   */
  function explainKaobaCtaHtml(opts) {
    opts = opts || {};
    var explain = opts.explain || {};
    if (!(explain && explain.reason) && !(opts.bundle && opts.bundle.runners)) {
      // 理由が無くても導線は出す（prompt のみ）
    }
    var rid = opts.race_id || (opts.bundle && opts.bundle.race_id) || "";
    var honmei =
      opts.bundle && typeof honmeiRunner === "function" ? honmeiRunner(opts.bundle) : null;
    var num = honmei && honmei.horse_number != null ? String(honmei.horse_number) : "";
    var name =
      honmei && honmei.horse_name
        ? horseLabel(honmei.horse_name, honmei.horse_number)
        : "";
    var display = "◎の理由を教えて";
    var prompt = "なぜ本命（◎）なの？理由を教えて。印や順位は変えなくていいよ。";
    if (num) {
      display = "◎ " + num + "番" + (name ? " " + name : "") + " の理由を教えて";
      prompt =
        "なぜ " +
        num +
        "番" +
        (name ? "（" + name + "）" : "") +
        " が本命（◎）なの？理由を短く教えて。印や順位は変えなくていいよ。";
    }
    var href =
      "chat.html?mode=explain&race_id=" +
      encodeURIComponent(rid) +
      "&prompt=" +
      encodeURIComponent(prompt) +
      "&display=" +
      encodeURIComponent(display);
    return (
      '<p class="explain-kaoba-cta"><a class="explain-kaoba-link" href="' +
      href +
      '">KAOBAに◎の理由を聞く</a></p>'
    );
  }

  function applyPaceDots(bundle) {
    var track = document.getElementById("paceTrack") || document.querySelector(".pace-track");
    if (!track) return;
    // 最終ゴールの予想着順：左から 1着・2着・3着… の馬番のみ
    var ordered = sortedRunnersByRank(bundle).filter(function (r) {
      return r && r.horse_number != null;
    });
    track.innerHTML = "";
    if (!ordered.length) {
      track.setAttribute("aria-label", "予想着順なし");
      return;
    }

    var maxDots = Math.min(ordered.length, 18);
    for (var i = 0; i < maxDots; i++) {
      var runner = ordered[i];
      var dot = document.createElement("span");
      dot.className = "pace-dot" + (i >= 3 ? " is-dim" : "");
      dot.textContent = String(runner.horse_number);
      dot.setAttribute("aria-label", i + 1 + "着予想 " + runner.horse_number + "番");
      track.appendChild(dot);
    }

    track.setAttribute("aria-label", "最終着順予想（左が1着・全" + maxDots + "頭）");
  }

  function applyMarksAndPicks(bundle) {
    var marksEl = document.getElementById("marksSectionBody");
    if (marksEl) marksEl.innerHTML = marksSectionHtml(bundle);
    var picksEl = document.getElementById("pickCardsBody");
    if (picksEl) picksEl.innerHTML = pickCardsHtml(bundle);
    applyPaceDots(bundle);
    if (global.ExpectExplainUx && ExpectExplainUx.applyToDom) {
      ExpectExplainUx.applyToDom(bundle, {
        ctaHtml: explainKaobaCtaHtml({
          explain: (bundle && bundle.explain) || {},
          race_id: (bundle && bundle.race_id) || "",
          bundle: bundle,
        }),
      });
    } else {
      var reasonsEl = document.getElementById("reasonsSectionBody");
      if (reasonsEl) reasonsEl.innerHTML = reasonsSectionHtml(bundle);
      var uxBody = document.getElementById("explainUxBody");
      if (uxBody) uxBody.innerHTML = reasonsSectionHtml(bundle);
    }
  }

  /**
   * prediction_available=false / pending / race_id 切替時:
   * 印・対抗穴・着順・explain・自信度・本命カードなど予測由来 DOM を全消去。
   * 過去 Bundle / mock / 別レース残留を残さない。
   */
  /** "15:10" → "15:10出走" */
  function formatPostTimeLabel(raw) {
    var t = normalizePostTime(raw);
    return t ? t + "出走" : "";
  }

  function extractPostTime(info) {
    info = info || {};
    if (info.post_time) return info.post_time;
    var raw = String(info.race_name || info.class_label || "");
    var m = raw.match(/(\d{1,2}):(\d{2})/);
    return m ? m[1] + ":" + m[2] : "";
  }

  function venueOnly(info) {
    if (global.ExpectCatalogIdentity && ExpectCatalogIdentity.venueOnly) {
      return ExpectCatalogIdentity.venueOnly(info) || "レース";
    }
    info = info || {};
    var v = String(info.venue || info.course || "")
      .replace(/\s*\d{1,2}\s*R\s*$/u, "")
      .trim();
    if (v) return v;
    var label = String(info.race_label || "");
    var m = label.match(/^(.+?)\s*\d{1,2}\s*R\s*$/u);
    if (m) return m[1].trim();
    return label.replace(/\s*\d{1,2}\s*R\s*$/u, "").trim() || "レース";
  }

  /** Catalog race_id → seed race_info (same race only). */
  var _catalogRaceInfoById = Object.create(null);

  function setCatalogRaceInfo(raceId, info) {
    var id = String(raceId || "").trim();
    if (!id || !info || typeof info !== "object") return false;
    if (info.race_id && String(info.race_id) !== id) return false;
    _catalogRaceInfoById[id] = Object.assign({}, info, { race_id: id });
    return true;
  }

  function getCatalogRaceInfo(raceId) {
    var id = String(raceId || "").trim();
    return id ? _catalogRaceInfoById[id] || null : null;
  }

  function clearCatalogRaceInfo(raceId) {
    var id = String(raceId || "").trim();
    if (id) delete _catalogRaceInfoById[id];
  }

  function formalNameFromInfo(info) {
    if (global.ExpectCatalogIdentity && ExpectCatalogIdentity.formalRaceName) {
      return shortRaceName(ExpectCatalogIdentity.formalRaceName(info));
    }
    return shortRaceName((info && info.race_name) || "");
  }

  function venueRaceHeading(info, raceId) {
    if (global.ExpectCatalogIdentity && ExpectCatalogIdentity.venueRaceHeading) {
      return ExpectCatalogIdentity.venueRaceHeading(info, raceId) || venueOnly(info);
    }
    var venue = venueOnly(info);
    var rno =
      info && (info.race_no != null ? info.race_no : info.race_number);
    if (venue && rno != null && rno !== "") return venue + " " + Number(rno) + "R";
    return venue;
  }

  function mergeDetailRaceInfo(bundleInfo, expectedRaceId) {
    var seed = getCatalogRaceInfo(expectedRaceId);
    if (global.ExpectCatalogIdentity && ExpectCatalogIdentity.mergeForRaceId) {
      return ExpectCatalogIdentity.mergeForRaceId(seed, bundleInfo, expectedRaceId);
    }
    if (
      seed &&
      String(seed.race_id || "") === String(expectedRaceId || "")
    ) {
      var merged = Object.assign({}, seed, bundleInfo || {});
      if (!merged.race_name) merged.race_name = seed.race_name || "";
      if (merged.venue == null || merged.venue === "") {
        merged.venue = seed.venue || seed.course || "";
      }
      if (merged.race_no == null) merged.race_no = seed.race_no;
      return merged;
    }
    return Object.assign({}, bundleInfo || {});
  }

  function paintRaceMeta(info, expectedRaceId) {
    info = info || {};
    var name = formalNameFromInfo(info);
    var postLabel = formatPostTimeLabel(extractPostTime(info));
    var dateBit = "";
    if (info.date_label) dateBit = String(info.date_label);
    else if (info.date && /^\d{4}-\d{2}-\d{2}$/.test(String(info.date))) {
      var d = String(info.date);
      dateBit = String(Number(d.slice(5, 7))) + "/" + String(Number(d.slice(8, 10)));
    }

    var heading = venueRaceHeading(info, expectedRaceId || info.race_id);
    var titleEl = document.getElementById("raceTitle");
    if (titleEl && heading) titleEl.textContent = heading;

    var subEl = document.getElementById("raceSub") || document.querySelector(".brand-sub");
    if (subEl) {
      // brand-sub: formal race name only (post time lives in race-meta-line)
      subEl.textContent = name || "読み込み中…";
    }

    var nameEl = document.getElementById("raceMetaName");
    var lineEl = document.getElementById("raceMetaLine");
    if (nameEl) nameEl.textContent = name || "—";
    if (lineEl) {
      var lineBits = [];
      if (dateBit) lineBits.push(dateBit);
      if (postLabel) lineBits.push(postLabel);
      lineEl.textContent = lineBits.join("・") || "レース情報を取得中…";
    }
  }

  /** Catalog-only early header paint (before Prediction). Same race_id only. */
  function paintRaceDetailHeader(info, expectedRaceId) {
    if (!info) return;
    var id = String(expectedRaceId || info.race_id || "").trim();
    if (info.race_id && id && String(info.race_id) !== id) return;
    paintRaceMeta(info, id);
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
    var expectId = String(expectedRaceId || bundle.race_id || "").trim();
    var info = mergeDetailRaceInfo(bundle.race_info || {}, expectId);
    var conf = scorePercent(bundle);
    var honmei = honmeiRunner(bundle);
    var band = displayBandFromBundle(bundle);
    var bandLabel = BAND_LABEL[band] || BAND_LABEL.unknown;

    paintRaceMeta(info, expectId);

    var card = document.querySelector(".honmei-card");
    if (card && honmei) {
      var num = card.querySelector(".honmei-num");
      var h2 = card.querySelector("h2");
      var p = card.querySelector("p");
      var stars = card.querySelector(".race-stars");
      if (num) {
        num.textContent = String(
          honmei.number != null
            ? honmei.number
            : honmei.horse_number != null
              ? honmei.horse_number
              : "—"
        );
      }
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
    } else if (card) {
      var isProjection =
        (meta && meta.engine_source === "pi_catalog_projection") ||
        (meta &&
          meta.fallback_reason === "pi_prediction_unavailable_catalog_projection");
      var num2 = card.querySelector(".honmei-num");
      var h22 = card.querySelector("h2");
      var p2 = card.querySelector("p");
      var stars2 = card.querySelector(".race-stars");
      if (num2) num2.textContent = "—";
      if (h22) h22.textContent = isProjection ? "予想データ準備中" : "本命未確定";
      if (p2) {
        p2.textContent = isProjection
          ? "レース情報のみ取得済み · 予想本体を再取得中です"
          : "AI本命 · 自信度：—";
      }
      if (stars2) stars2.textContent = "☆☆☆☆☆";
      var dkEmpty = card.querySelector(".explain-honmei-decision");
      if (dkEmpty) dkEmpty.remove();
    }

    var confEl = document.getElementById("raceConfidenceDetail");
    if (confEl && bundle.ai_confidence) {
      confEl.innerHTML = raceConfidenceDetailHtml(bundle);
    }

    // UI10: 旧 narrative を pace-card に流し込まない（着順ドット専用）
    var paceHint = document.querySelector(".pace-card > p.pace-card-hint");
    if (paceHint) {
      paceHint.textContent =
        (global.ExpectExplainUx && ExpectExplainUx.PACE_ORDER_HINT) ||
        "左端が1着予想、右へ行くほど着順が下がります。並んだ馬番は、AIが考えるゴールまでの着順です。";
    }

    var place = venueRaceHeading(info, expectId) || venueOnly(info);
    return {
      raceId: bundle.race_id,
      place: place,
      name: formalNameFromInfo(info),
      badge: info.grade || "",
      postTime: extractPostTime(info) || "",
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

  /**
   * UI8 ホーム本命: 表示自信度 ★★★★☆（rather_high）以上のうち score 最大の1件
   * @param {object[]} bundles
   * @returns {object | null}
   */
  function pickHomeTodaysHonmei(bundles) {
    if (!bundles || !bundles.length) return null;
    var eligible = bundles.filter(function (b) {
      var band = displayBandFromBundle(b);
      return (BAND_RANK[band] || 0) >= BAND_RANK.rather_high;
    });
    if (!eligible.length) return null;
    return eligible.slice().sort(function (a, b) {
      return (scorePercent(b) || 0) - (scorePercent(a) || 0);
    })[0];
  }

  /**
   * PredictionBundle → RaceCardSummary（一覧の段階表示用）
   * @param {object} bundle
   * @param {object} [seedCard]
   */
  function bundleToRaceCardSummary(bundle, seedCard) {
    seedCard = seedCard || {};
    if (!bundle || typeof bundle !== "object") {
      return {
        schema_version: "expect-race-card-summary/1.0",
        race_id: seedCard.race_id || "",
        race_info: seedCard.race_info || {},
        prediction: { status: "failed", engine_source: null },
        summary: null,
      };
    }
    var runners =
      (bundle.evaluation && Array.isArray(bundle.evaluation.runners)
        ? bundle.evaluation.runners
        : []) || [];
    var honmeiRunner =
      runners.find(function (r) {
        return r && r.mark === "honmei";
      }) ||
      runners[0] ||
      null;
    var conf = bundle.ai_confidence || {};
    var score =
      typeof conf.score === "number"
        ? conf.score > 1
          ? conf.score / 100
          : conf.score
        : null;
    var band = displayBandFromBundle(bundle);
    if (!BAND_LABEL[band]) {
      band =
        conf.band && conf.band !== "unknown"
          ? conf.band
          : score != null
            ? bandFromNormalizedScore(score)
            : null;
    }
    var seedInfo = seedCard.race_info || {};
    var bundleInfo = bundle.race_info || {};
    var ridForCatalog = bundle.race_id || seedCard.race_id || "";
    var catalogInfo = getCatalogRaceInfo(ridForCatalog) || {};
    var mergedInfo = Object.assign({}, seedInfo, bundleInfo);
    // Prediction 側の空文字で Catalog の venue/date/name/post_time を消さない
    if (!String(mergedInfo.venue || "").trim()) {
      mergedInfo.venue =
        seedInfo.venue || catalogInfo.venue || bundleInfo.venue || "";
    }
    if (!mergedInfo.date) {
      mergedInfo.date =
        seedInfo.date ||
        catalogInfo.date ||
        bundleInfo.date ||
        (String(bundle.race_id || seedCard.race_id || "").match(/^(\d{4}-\d{2}-\d{2})/) ||
          [])[1] ||
        "";
    }
    if (!String(mergedInfo.race_name || "").trim()) {
      mergedInfo.race_name =
        seedInfo.race_name || catalogInfo.race_name || bundleInfo.race_name || "";
    }
    // 一覧カード発走時間: Catalog 非空を authority。Prediction null/"" と空 seed でもレジストリから復元
    if (!String(mergedInfo.post_time || "").trim()) {
      if (String(seedInfo.post_time || "").trim()) {
        mergedInfo.post_time = seedInfo.post_time;
      } else if (String(catalogInfo.post_time || "").trim()) {
        mergedInfo.post_time = catalogInfo.post_time;
      } else if (String(bundleInfo.post_time || "").trim()) {
        mergedInfo.post_time = bundleInfo.post_time;
      }
    }
    var out = {
      schema_version: "expect-race-card-summary/1.0",
      race_id: bundle.race_id || seedCard.race_id || "",
      race_info: mergedInfo,
      prediction: {
        status: "ready",
        engine_source:
          (bundle.meta && bundle.meta.engine_source) ||
          (bundle.__meta && bundle.__meta.engine_source) ||
          "prediction",
      },
      summary: {
        honmei: honmeiRunner
          ? {
              horse_number: Number(honmeiRunner.horse_number) || 0,
              horse_name:
                honmeiRunner.horse_name != null ? String(honmeiRunner.horse_name) : null,
              mark: "honmei",
            }
          : null,
        confidence:
          score != null || band
            ? { score: score, band: band || "low" }
            : null,
        short_reason: null,
      },
    };
    if (!out.race_info.date) {
      var dm = String(out.race_id || "").match(/^(\d{4}-\d{2}-\d{2})/);
      if (dm) out.race_info.date = dm[1];
    }
    return out;
  }

  global.ExpectPredictionBind = {
    scorePercent: scorePercent,
    starsFromScore: starsFromScore,
    starsFromBand: starsFromBand,
    bandFromNormalizedScore: bandFromNormalizedScore,
    confidenceBandFromLabelAndScore: confidenceBandFromLabelAndScore,
    resolveInternalLabel: resolveInternalLabel,
    displayBandFromBundle: displayBandFromBundle,
    dateLabel: dateLabel,
    raceCardHtml: raceCardHtml,
    raceCardSummaryHtml: raceCardSummaryHtml,
    bundleToRaceCardSummary: bundleToRaceCardSummary,
    applyHomeHonmeiCard: applyHomeHonmeiCard,
    applyHomeHonmeiSnapshot: applyHomeHonmeiSnapshot,
    applyHomeHonmeiEmpty: applyHomeHonmeiEmpty,
    readHomeHonmeiCache: readHomeHonmeiCache,
    homeHonmeiCacheDate: homeHonmeiCacheDate,
    applyRaceDetail: applyRaceDetail,
    setCatalogRaceInfo: setCatalogRaceInfo,
    getCatalogRaceInfo: getCatalogRaceInfo,
    clearCatalogRaceInfo: clearCatalogRaceInfo,
    paintRaceDetailHeader: paintRaceDetailHeader,
    pickTopByConfidence: pickTopByConfidence,
    pickHomeTodaysHonmei: pickHomeTodaysHonmei,
    honmeiRunner: honmeiRunner,
    runnerByMark: runnerByMark,
    sortedRunnersByRank: sortedRunnersByRank,
    provenanceHtml: provenanceHtml,
    marksSectionHtml: marksSectionHtml,
    pickCardsHtml: pickCardsHtml,
    explainKaobaCtaHtml: explainKaobaCtaHtml,
    reasonsSectionHtml: reasonsSectionHtml,
  };
})(window);
