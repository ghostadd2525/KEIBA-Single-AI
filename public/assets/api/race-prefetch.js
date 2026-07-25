/**
 * ExpectRacePrefetch — レース詳細向け PredictionBundle / メタの先行取得
 * （ページ遷移後も sessionStorage でキャッシュ優先）
 */
(function (global) {
  "use strict";

  var SS_PB = "expect_pb_prefetch_v1";
  var SS_META = "expect_race_meta_v1";
  var MAX_PB = 12;
  var memPb = Object.create(null);
  var memMeta = Object.create(null);
  var inflight = Object.create(null);
  var observed = false;

  function readSs(key) {
    try {
      return JSON.parse(global.sessionStorage.getItem(key) || "{}") || {};
    } catch (e) {
      return {};
    }
  }

  function writeSs(key, obj) {
    try {
      global.sessionStorage.setItem(key, JSON.stringify(obj));
    } catch (e) {
      /* quota / private mode */
    }
  }

  function prune(store, max) {
    var keys = Object.keys(store);
    if (keys.length <= max) return store;
    keys.sort(function (a, b) {
      return (store[a] && store[a].at ? store[a].at : 0) - (store[b] && store[b].at ? store[b].at : 0);
    });
    var out = {};
    keys.slice(keys.length - max).forEach(function (k) {
      out[k] = store[k];
    });
    return out;
  }

  function putMeta(raceId, meta) {
    if (!raceId || !meta) return;
    var row = {
      place: meta.place || "",
      name: meta.name || "",
      badge: meta.badge || "",
      dateLabel: meta.dateLabel || "",
      postTime: meta.postTime || "",
      at: Date.now(),
    };
    memMeta[raceId] = row;
    var store = readSs(SS_META);
    store[raceId] = row;
    writeSs(SS_META, prune(store, 40));
  }

  function getMeta(raceId) {
    if (!raceId) return null;
    if (memMeta[raceId]) return memMeta[raceId];
    var store = readSs(SS_META);
    if (store[raceId]) {
      memMeta[raceId] = store[raceId];
      return store[raceId];
    }
    return null;
  }

  function putBundle(raceId, bundle, meta) {
    if (!raceId || !bundle) return;
    var row = { bundle: bundle, meta: meta || {}, at: Date.now() };
    memPb[raceId] = row;
    var store = readSs(SS_PB);
    store[raceId] = row;
    writeSs(SS_PB, prune(store, MAX_PB));
    if (global.ExpectFavorites && ExpectFavorites.cacheBundle) {
      try {
        ExpectFavorites.cacheBundle(bundle);
      } catch (e) { /* ignore */ }
    }
  }

  function getBundle(raceId) {
    if (!raceId) return null;
    if (memPb[raceId]) return memPb[raceId];
    var store = readSs(SS_PB);
    if (store[raceId] && store[raceId].bundle) {
      memPb[raceId] = store[raceId];
      return store[raceId];
    }
    return null;
  }

  function putMetaFromCard(card) {
    if (!card || !card.race_id) return;
    var info = card.race_info || {};
    var place =
      info.place ||
      info.venue ||
      (info.course ? String(info.course) : "") ||
      "";
    if (!place && global.ExpectRaceIdMeta && ExpectRaceIdMeta.displayPlace) {
      place = ExpectRaceIdMeta.displayPlace(card.race_id, "");
    }
    var name = info.race_name || info.class_label || "";
    var post = info.post_time || "";
    var dateLabel = "";
    var date = info.date || "";
    if (date && /^\d{4}-\d{2}-\d{2}/.test(date)) {
      dateLabel = String(Number(date.slice(5, 7))) + "/" + String(Number(date.slice(8, 10)));
    }
    putMeta(card.race_id, {
      place: place,
      name: name,
      badge: post ? post + "出走" : "",
      dateLabel: dateLabel,
      postTime: post,
    });
  }

  function prefetch(raceId) {
    if (!raceId) return Promise.resolve(null);
    var hit = getBundle(raceId);
    if (hit) return Promise.resolve(hit);
    if (inflight[raceId]) return inflight[raceId];
    if (!global.ExpectApi || !ExpectApi.Prediction) return Promise.resolve(null);

    var getter =
      typeof ExpectApi.Prediction.getWithMeta === "function"
        ? ExpectApi.Prediction.getWithMeta(raceId)
        : ExpectApi.Prediction.get(raceId).then(function (b) {
            return { bundle: b, meta: {} };
          });

    inflight[raceId] = Promise.resolve(getter)
      .then(function (result) {
        var bundle = result && result.bundle ? result.bundle : result;
        var meta = (result && result.meta) || {};
        if (bundle && bundle.race_id) {
          putBundle(raceId, bundle, meta);
          var info = bundle.race_info || {};
          putMeta(raceId, {
            place: info.place || info.venue || info.course || "",
            name: info.race_name || info.class_label || "",
            badge: info.post_time ? String(info.post_time) + "出走" : "",
            dateLabel: "",
            postTime: info.post_time || "",
          });
          return { bundle: bundle, meta: meta, at: Date.now() };
        }
        return null;
      })
      .catch(function () {
        return null;
      })
      .then(function (row) {
        delete inflight[raceId];
        return row;
      });

    return inflight[raceId];
  }

  function observeList(root) {
    if (!root || observed) return;
    if (typeof IntersectionObserver === "undefined") {
      // fallback: prefetch first few links
      var links = root.querySelectorAll("a.race-item[href*='race']");
      var n = Math.min(6, links.length);
      for (var i = 0; i < n; i++) {
        var href = links[i].getAttribute("href") || "";
        var m = href.match(/race_id=([^&]+)/);
        if (m) prefetch(decodeURIComponent(m[1]));
      }
      return;
    }
    observed = true;
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var a = entry.target;
          var href = a.getAttribute("href") || "";
          var m = href.match(/race_id=([^&]+)/);
          if (!m) return;
          var rid = decodeURIComponent(m[1]);
          prefetch(rid);
          io.unobserve(a);
        });
      },
      { root: null, rootMargin: "120px 0px", threshold: 0.15 }
    );

    function scan() {
      root.querySelectorAll("a.race-item[href*='race_id=']").forEach(function (a) {
        if (a.dataset.pbPrefetch === "1") return;
        a.dataset.pbPrefetch = "1";
        io.observe(a);
      });
    }

    scan();
    // list re-renders often — MutationObserver keeps coverage
    if (typeof MutationObserver !== "undefined") {
      var mo = new MutationObserver(function () {
        scan();
      });
      mo.observe(root, { childList: true, subtree: true });
    }
  }

  global.ExpectRacePrefetch = {
    putBundle: putBundle,
    getBundle: getBundle,
    putMeta: putMeta,
    getMeta: getMeta,
    putMetaFromCard: putMetaFromCard,
    prefetch: prefetch,
    observeList: observeList,
  };
})(typeof window !== "undefined" ? window : globalThis);
