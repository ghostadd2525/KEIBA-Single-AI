/**
 * Race Catalog identity helpers (race-list UI).
 * Catalog owns date/venue/race_no/race_id/race_label for list cards & filters.
 * Prediction enrichment must not overwrite these fields.
 */
(function (global) {
  "use strict";

  function nonEmpty(v) {
    return v != null && String(v).trim() !== "";
  }

  /**
   * Prefer catalog seed identity over prediction/mock race_info.
   * @param {object} seedInfo
   * @param {object} bundleInfo
   * @returns {object}
   */
  function mergeRaceInfoPreferCatalog(seedInfo, bundleInfo) {
    seedInfo = seedInfo || {};
    bundleInfo = bundleInfo || {};
    var merged = Object.assign({}, seedInfo, bundleInfo);

    function pick() {
      var i;
      for (i = 0; i < arguments.length; i++) {
        if (nonEmpty(arguments[i])) return arguments[i];
      }
      return "";
    }

    merged.venue = pick(seedInfo.venue, seedInfo.course, bundleInfo.venue, bundleInfo.course);
    merged.course = pick(seedInfo.course, seedInfo.venue, bundleInfo.course, bundleInfo.venue);
    merged.race_label = pick(seedInfo.race_label, bundleInfo.race_label);
    merged.date = pick(
      seedInfo.date,
      (String(seedInfo.race_id || "").match(/^(\d{4}-\d{2}-\d{2})/) || [])[1],
      (String(bundleInfo.race_id || "").match(/^(\d{4}-\d{2}-\d{2})/) || [])[1]
      // Intentionally omit bundleInfo.date — mock may carry stale 2026-07-19
    );
    if (nonEmpty(seedInfo.date_label)) merged.date_label = seedInfo.date_label;
    if (nonEmpty(seedInfo.date_full)) merged.date_full = seedInfo.date_full;
    if (nonEmpty(seedInfo.race_name)) merged.race_name = seedInfo.race_name;
    else if (!nonEmpty(merged.race_name)) merged.race_name = pick(bundleInfo.race_name, "");
    if (nonEmpty(seedInfo.class_label)) merged.class_label = seedInfo.class_label;
    // Catalog non-empty post_time is authority; null/"" from Prediction must not win
    if (nonEmpty(seedInfo.post_time)) merged.post_time = seedInfo.post_time;
    else if (!nonEmpty(merged.post_time)) {
      merged.post_time = pick(bundleInfo.post_time, "");
    }

    if (seedInfo.race_no != null || seedInfo.race_number != null) {
      merged.race_no =
        seedInfo.race_no != null ? seedInfo.race_no : seedInfo.race_number;
      merged.race_number =
        seedInfo.race_number != null ? seedInfo.race_number : seedInfo.race_no;
    } else if (bundleInfo.race_no != null || bundleInfo.race_number != null) {
      merged.race_no =
        bundleInfo.race_no != null ? bundleInfo.race_no : bundleInfo.race_number;
      merged.race_number =
        bundleInfo.race_number != null ? bundleInfo.race_number : bundleInfo.race_no;
    }

    // Do not adopt prediction meeting_id when catalog did not provide one
    if (nonEmpty(seedInfo.meeting_id)) {
      merged.meeting_id = seedInfo.meeting_id;
    } else {
      delete merged.meeting_id;
    }

    if (nonEmpty(seedInfo.race_id)) {
      merged.race_id = String(seedInfo.race_id);
    }

    return merged;
  }

  /** Unique venues in first-seen catalog order (no alphabetical sort). */
  function uniqueVenuesInCatalogOrder(cardsOrBundles) {
    var out = [];
    (cardsOrBundles || []).forEach(function (c) {
      var info = (c && c.race_info) || c || {};
      var v = String(info.venue || info.course || "").trim();
      if (v && out.indexOf(v) < 0) out.push(v);
    });
    return out;
  }

  function isMockOrUnavailablePrediction(meta, engineSource) {
    meta = meta || {};
    var eng = String(
      engineSource || meta.engine_source || meta.engine || ""
    ).toLowerCase();
    var fb = String(meta.fallback_state || meta.fallback_reason || "").toLowerCase();
    if (eng === "mock_fallback" || eng === "bff_mock" || eng === "mock") return true;
    if (eng === "prediction_unavailable") return true;
    if (fb.indexOf("mock_fallback") >= 0) return true;
    if (fb.indexOf("prediction_unavailable") >= 0) return true;
    if (fb.indexOf("race_not_found") >= 0) return true;
    if (fb.indexOf("race_not_resolved") >= 0) return true;
    if (fb.indexOf("feature_not_ready") >= 0) return true;
    if (fb.indexOf("input_not_ready") >= 0) return true;
    if (meta.prediction_available === false) return true;
    if (String(meta.model_version || "").toLowerCase().indexOf("dummy-model") >= 0) {
      return true;
    }
    return false;
  }

  /** Venue only — never treat Catalog meeting ordinal (01/02/03) as JRA venue code. */
  function venueOnly(info) {
    info = info || {};
    var v = String(info.venue || info.course || "")
      .replace(/\s*\d{1,2}\s*R\s*$/u, "")
      .trim();
    if (v) return v;
    var label = String(info.race_label || "");
    var m = label.match(/^(.+?)\s*\d{1,2}\s*R\s*$/u);
    if (m) return m[1].trim();
    return label.replace(/\s*\d{1,2}\s*R\s*$/u, "").trim();
  }

  /**
   * race_no from race_info, else Catalog race_id suffix …-MM-RR (not JRA venue).
   * Only accepts suffix when raceId matches info.race_id (identity guard).
   */
  function resolveRaceNo(info, raceId) {
    info = info || {};
    if (info.race_no != null && info.race_no !== "") {
      var n1 = Number(info.race_no);
      if (!isNaN(n1) && n1 > 0) return n1;
    }
    if (info.race_number != null && info.race_number !== "") {
      var n2 = Number(info.race_number);
      if (!isNaN(n2) && n2 > 0) return n2;
    }
    var rid = String(raceId || info.race_id || "").trim();
    if (nonEmpty(info.race_id) && rid && String(info.race_id) !== rid) return null;
    var m = rid.match(/^\d{4}-\d{2}-\d{2}-\d{2}-(\d{2})$/);
    if (!m) return null;
    var n3 = Number(m[1]);
    return !isNaN(n3) && n3 > 0 ? n3 : null;
  }

  /** Header title: "新潟 1R" — venue from metadata, not meeting→JRA remap. */
  function venueRaceHeading(info, raceId) {
    var venue = venueOnly(info);
    var rno = resolveRaceNo(info, raceId);
    if (venue && rno != null) return venue + " " + rno + "R";
    return venue || "";
  }

  /**
   * Formal race name only (Catalog race_name).
   * Never invent from distance/surface/race_label ("新潟1R").
   */
  function formalRaceName(info) {
    info = info || {};
    var raw = String(info.race_name || "").trim();
    if (!raw) return "";
    // Reject pure course/distance fragments if they ever leak into race_name
    if (/^(芝|ダート|ダ|障)\s*\d+m$/u.test(raw)) return "";
    if (/^\d+m$/u.test(raw)) return "";
    return raw;
  }

  /**
   * Merge only when seed.race_id matches expectedRaceId (no cross-race name reuse).
   */
  function mergeForRaceId(seedInfo, bundleInfo, expectedRaceId) {
    seedInfo = seedInfo || {};
    bundleInfo = bundleInfo || {};
    var expectId = String(expectedRaceId || "").trim();
    var seedOk =
      expectId &&
      nonEmpty(seedInfo.race_id) &&
      String(seedInfo.race_id) === expectId;
    if (!seedOk) {
      return mergeRaceInfoPreferCatalog({}, bundleInfo);
    }
    return mergeRaceInfoPreferCatalog(seedInfo, bundleInfo);
  }

  /**
   * Production canonical race_id: YYYY-MM-DD-MM-RR
   * Rejects mock/legacy ids (e.g. 20260719_hanshin_11).
   */
  function isCanonicalRaceId(raceId) {
    return /^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$/.test(String(raceId || "").trim());
  }

  function isTestOrFixtureRaceId(raceId) {
    var id = String(raceId || "");
    if (!id) return true;
    if (/test|demo|fixture|mock|sample|placeholder|hanshin_|tokyo_|fukushima_|hakodate_|nakayama_/i.test(id)) {
      return true;
    }
    if (!isCanonicalRaceId(id)) return true;
    return false;
  }

  function raceDateFromCard(card) {
    var info = (card && card.race_info) || {};
    var d = String(info.date || "").trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(d)) return d;
    var m = String((card && card.race_id) || "").match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : "";
  }

  /**
   * Keep only Catalog/production races for list render.
   * Official Catalog races with prediction missing/processing are kept.
   *
   * @param {object[]} cards
   * @param {{ dates?: string[], allowIds?: Record<string, boolean>|null }} [opts]
   * @returns {object[]}
   */
  function filterRaceCardsForProduction(cards, opts) {
    opts = opts || {};
    var dateSet = null;
    if (opts.dates && opts.dates.length) {
      dateSet = Object.create(null);
      opts.dates.forEach(function (d) {
        if (d && d !== "all") dateSet[String(d)] = true;
      });
    }
    var allow = opts.allowIds || null;
    var seen = Object.create(null);
    var out = [];
    (cards || []).forEach(function (card) {
      if (!card) return;
      var id = String(card.race_id || "").trim();
      if (!id || isTestOrFixtureRaceId(id)) return;
      if (allow && !allow[id]) return;
      var d = raceDateFromCard(card);
      if (dateSet && (!d || !dateSet[d])) return;
      if (seen[id]) return;
      seen[id] = true;
      out.push(card);
    });
    return out;
  }

  function buildAllowIdsFromCards(cards) {
    var allow = Object.create(null);
    (cards || []).forEach(function (c) {
      var id = c && c.race_id != null ? String(c.race_id).trim() : "";
      if (id && isCanonicalRaceId(id)) allow[id] = true;
    });
    return allow;
  }

  /**
   * Catalog items / races → race_id → non-empty post_time map.
   * Accepts both PI top-level post_time and race_info.post_time.
   */
  function buildPostTimeByIdFromCatalogItems(items) {
    var map = Object.create(null);
    (items || []).forEach(function (item) {
      if (!item) return;
      var id = String(item.race_id || "").trim();
      if (!id) return;
      var info = item.race_info || {};
      var pt = nonEmpty(info.post_time)
        ? info.post_time
        : nonEmpty(item.post_time)
          ? item.post_time
          : "";
      if (nonEmpty(pt)) map[id] = String(pt).trim();
    });
    return map;
  }

  /**
   * Fill empty/null post_time from Catalog authority map. Never overwrite non-empty.
   * @param {object[]} cards
   * @param {Record<string, string>|null} postTimeById
   * @returns {object[]}
   */
  function applyCatalogPostTimeAuthority(cards, postTimeById) {
    if (!postTimeById) return cards || [];
    return (cards || []).map(function (card) {
      if (!card) return card;
      var id = String(card.race_id || "").trim();
      var auth = id ? postTimeById[id] : "";
      if (!nonEmpty(auth)) return card;
      var info = card.race_info || {};
      if (nonEmpty(info.post_time)) return card;
      return Object.assign({}, card, {
        race_info: Object.assign({}, info, { post_time: String(auth).trim() }),
      });
    });
  }

  var api = {
    nonEmpty: nonEmpty,
    mergeRaceInfoPreferCatalog: mergeRaceInfoPreferCatalog,
    mergeForRaceId: mergeForRaceId,
    uniqueVenuesInCatalogOrder: uniqueVenuesInCatalogOrder,
    isMockOrUnavailablePrediction: isMockOrUnavailablePrediction,
    venueOnly: venueOnly,
    resolveRaceNo: resolveRaceNo,
    venueRaceHeading: venueRaceHeading,
    formalRaceName: formalRaceName,
    isCanonicalRaceId: isCanonicalRaceId,
    isTestOrFixtureRaceId: isTestOrFixtureRaceId,
    raceDateFromCard: raceDateFromCard,
    filterRaceCardsForProduction: filterRaceCardsForProduction,
    buildAllowIdsFromCards: buildAllowIdsFromCards,
    buildPostTimeByIdFromCatalogItems: buildPostTimeByIdFromCatalogItems,
    applyCatalogPostTimeAuthority: applyCatalogPostTimeAuthority,
  };

  global.ExpectCatalogIdentity = api;

  // Node / unit-test bridge
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
