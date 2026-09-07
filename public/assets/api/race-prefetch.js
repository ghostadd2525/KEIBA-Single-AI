/**
 * ExpectRacePrefetch — Visible Prediction Prefetch (Version7.2)
 *
 * 一覧描画後、Viewport 内 + 前後 PAD 件だけ
 * Prediction Bundle / Board（history なし）をバックグラウンド取得する。
 * History は詳細データタブでのみ取得。Ready Bundle のみキャッシュ。
 */
(function (global) {
  "use strict";

  var SS_PB = "expect_pb_prefetch_v1";
  var SS_META = "expect_race_meta_v1";
  var SS_BOARD = "expect_board_prefetch_v1";
  var MAX_PB = 20;
  var MAX_BOARD = 20;
  /** Viewport 外に前後何件まで先読みするか */
  var PAD = 3;
  /** 同時取得上限（一覧 36 件を一気に叩かない） */
  var MAX_CONCURRENT = 2;

  var memPb = Object.create(null);
  var memMeta = Object.create(null);
  var memBoard = Object.create(null);
  var inflightPred = Object.create(null);
  var inflightBoard = Object.create(null);
  /** race_id → { prediction?: true, board?: true } */
  var done = Object.create(null);
  var queue = [];
  var active = 0;
  var observedRoot = null;
  var scrollTimer = null;
  var io = null;

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
      return (store[a] && store[a].at ? store[a].at : 0) -
        (store[b] && store[b].at ? store[b].at : 0);
    });
    var out = {};
    keys.slice(keys.length - max).forEach(function (k) {
      out[k] = store[k];
    });
    return out;
  }

  function raceIdFromHref(href) {
    var m = String(href || "").match(/race_id=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function markDone(raceId, kind) {
    if (!raceId) return;
    if (!done[raceId]) done[raceId] = {};
    done[raceId][kind] = true;
  }

  function isDone(raceId, kind) {
    return !!(done[raceId] && done[raceId][kind]);
  }

  function putMeta(raceId, meta) {
    if (!raceId || !meta) return;
    var row = {
      place: meta.place || "",
      name: meta.name || "",
      badge: meta.badge || "",
      dateLabel: meta.dateLabel || "",
      postTime: meta.postTime || "",
      date: meta.date || "",
      venue: meta.venue || meta.place || "",
      confidence: meta.confidence != null ? meta.confidence : null,
      predictionStatus: meta.predictionStatus || "",
      favorite: !!meta.favorite,
      thumbnail: meta.thumbnail || "",
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
    meta = meta || {};
    if (
      global.ExpectApi &&
      ExpectApi.Prediction &&
      typeof ExpectApi.Prediction.isReady === "function"
    ) {
      if (!ExpectApi.Prediction.isReady(bundle, meta)) return;
    } else {
      if (meta.prediction_status === "pending") return;
      if (meta.engine_source === "pi_catalog_projection") return;
      var runners =
        (bundle.evaluation && bundle.evaluation.runners) || bundle.runners || [];
      if (!Array.isArray(runners) || !runners.length) return;
    }
    var row = { bundle: bundle, meta: meta, at: Date.now() };
    memPb[raceId] = row;
    var store = readSs(SS_PB);
    store[raceId] = row;
    writeSs(SS_PB, prune(store, MAX_PB));
    markDone(raceId, "prediction");
    if (global.ExpectFavorites && ExpectFavorites.cacheBundle) {
      try {
        ExpectFavorites.cacheBundle(bundle);
      } catch (e) { /* ignore */ }
    }
    tryWarmDurable(raceId);
  }

  function getBundle(raceId) {
    if (!raceId) return null;
    if (memPb[raceId]) return memPb[raceId];
    var store = readSs(SS_PB);
    if (store[raceId] && store[raceId].bundle) {
      memPb[raceId] = store[raceId];
      markDone(raceId, "prediction");
      return store[raceId];
    }
    return null;
  }

  function putBoard(raceId, board, history) {
    if (!raceId || !board) return;
    var hist =
      history != null
        ? history
        : Array.isArray(board.history)
          ? board.history
          : null;
    var row = { board: board, history: hist, at: Date.now() };
    memBoard[raceId] = row;
    var store = readSs(SS_BOARD);
    store[raceId] = row;
    writeSs(SS_BOARD, prune(store, MAX_BOARD));
    markDone(raceId, "board");
    tryWarmDurable(raceId);
  }

  function getBoard(raceId) {
    if (!raceId) return null;
    if (memBoard[raceId]) return memBoard[raceId];
    var store = readSs(SS_BOARD);
    if (store[raceId] && store[raceId].board) {
      memBoard[raceId] = store[raceId];
      markDone(raceId, "board");
      return store[raceId];
    }
    return null;
  }

  /** Prediction + Board が揃えば durable cache へ（putIfReady がゲート） */
  function tryWarmDurable(raceId) {
    if (!global.ExpectRaceDetailCache || !ExpectRaceDetailCache.putIfReady) return;
    var pb = getBundle(raceId);
    var bh = getBoard(raceId);
    if (!pb || !pb.bundle || !bh || !bh.board) return;
    var info = (pb.bundle.race_info) || {};
    ExpectRaceDetailCache.putIfReady(raceId, {
      prediction: { bundle: pb.bundle, meta: pb.meta || {} },
      board: bh.board,
      history: bh.history,
      post_time: info.post_time || bh.board.post_time || "",
      date: info.date || bh.board.date || "",
    }).catch(function () { /* ignore */ });
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
      dateLabel =
        String(Number(date.slice(5, 7))) + "/" + String(Number(date.slice(8, 10)));
    }
    var conf =
      card.summary &&
      card.summary.confidence &&
      typeof card.summary.confidence.score === "number"
        ? card.summary.confidence.score
        : null;
    var fav = !!card.favorite;
    try {
      if (global.ExpectFavorites && typeof ExpectFavorites.has === "function") {
        fav = !!ExpectFavorites.has(card.race_id) || fav;
      }
    } catch (e) { /* ignore */ }
    var thumb =
      card.thumbnail ||
      (info.bg != null ? "bg" + info.bg : "") ||
      "";
    putMeta(card.race_id, {
      place: place,
      name: name,
      badge: post ? post + "出走" : "",
      dateLabel: dateLabel,
      postTime: post,
      date: date,
      venue: info.venue || place,
      confidence: conf,
      predictionStatus: (card.prediction && card.prediction.status) || "",
      favorite: fav,
      thumbnail: thumb,
    });
  }

  function prefetchPrediction(raceId) {
    if (!raceId) return Promise.resolve(null);
    if (isDone(raceId, "prediction") || getBundle(raceId)) {
      markDone(raceId, "prediction");
      return Promise.resolve(getBundle(raceId));
    }
    if (inflightPred[raceId]) return inflightPred[raceId];
    if (!global.ExpectApi || !ExpectApi.Prediction) return Promise.resolve(null);

    var getter =
      typeof ExpectApi.Prediction.getWithMeta === "function"
        ? ExpectApi.Prediction.getWithMeta(raceId)
        : ExpectApi.Prediction.get(raceId).then(function (b) {
            return { bundle: b, meta: {} };
          });

    inflightPred[raceId] = Promise.resolve(getter)
      .then(function (result) {
        if (result && result.pending) return null;
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
            date: info.date || "",
            venue: info.venue || info.place || "",
          });
          return { bundle: bundle, meta: meta, at: Date.now() };
        }
        return null;
      })
      .catch(function () {
        return null;
      })
      .then(function (row) {
        delete inflightPred[raceId];
        return row;
      });

    return inflightPred[raceId];
  }

  function prefetchBoard(raceId) {
    if (!raceId) return Promise.resolve(null);
    if (isDone(raceId, "board") || getBoard(raceId)) {
      markDone(raceId, "board");
      return Promise.resolve(getBoard(raceId));
    }
    if (inflightBoard[raceId]) return inflightBoard[raceId];

    var fetcher = null;
    if (global.ExpectApi && ExpectApi.RaceBoard && ExpectApi.RaceBoard.getBoard) {
      // Version7.2: board-only（history は詳細データタブで取得）
      fetcher = ExpectApi.RaceBoard.getBoard(raceId, {
        fresh: false,
        timeoutMs: 20000,
      });
    } else {
      var headers = { Accept: "application/json" };
      try {
        var t = global.localStorage.getItem("expect_access_token_v1");
        if (t) headers.Authorization = "Bearer " + t;
      } catch (e) { /* ignore */ }
      var controller =
        typeof AbortController !== "undefined" ? new AbortController() : null;
      var timer = null;
      if (controller) {
        timer = setTimeout(function () {
          try {
            controller.abort();
          } catch (e) { /* ignore */ }
        }, 20000);
      }
      fetcher = fetch(
        "/api/races/" + encodeURIComponent(raceId) + "/board",
        {
          headers: headers,
          credentials: "same-origin",
          signal: controller ? controller.signal : undefined,
        }
      )
        .then(function (res) {
          return res.json().then(function (body) {
            if (!res.ok || (body && body.ok === false)) throw new Error("board");
            return (body && body.data) || body;
          });
        })
        .finally(function () {
          if (timer) clearTimeout(timer);
        });
    }

    inflightBoard[raceId] = Promise.resolve(fetcher)
      .then(function (data) {
        if (!data) return null;
        putBoard(raceId, data, null);
        return getBoard(raceId);
      })
      .catch(function () {
        return null;
      })
      .then(function (row) {
        delete inflightBoard[raceId];
        return row;
      });

    return inflightBoard[raceId];
  }

  /** Prediction + Board（history なし）を先行取得 */
  function prefetch(raceId) {
    if (!raceId) return Promise.resolve(null);
    return prefetchPrediction(raceId).then(function (prediction) {
      return prefetchBoard(raceId).then(function (board) {
        return { prediction: prediction, board: board };
      });
    });
  }

  function pumpQueue() {
    while (active < MAX_CONCURRENT && queue.length) {
      var rid = queue.shift();
      if (!rid) continue;
      if (isDone(rid, "prediction") && isDone(rid, "board")) continue;
      active += 1;
      prefetch(rid)
        .catch(function () {
          return null;
        })
        .then(function () {
          active -= 1;
          pumpQueue();
        });
    }
  }

  function enqueue(raceId) {
    if (!raceId) return;
    if (isDone(raceId, "prediction") && isDone(raceId, "board")) return;
    if (inflightPred[raceId] || inflightBoard[raceId]) return;
    if (queue.indexOf(raceId) >= 0) return;
    queue.push(raceId);
    pumpQueue();
  }

  function listRaceLinks(root) {
    return Array.prototype.slice.call(
      root.querySelectorAll("a.race-item[href*='race_id=']")
    );
  }

  /** Viewport 内 index + 前後 PAD 件だけ enqueue */
  function prefetchVisibleWindow(root) {
    if (!root) return;
    var items = listRaceLinks(root);
    if (!items.length) return;

    var vh =
      global.innerHeight ||
      (global.document &&
        global.document.documentElement &&
        global.document.documentElement.clientHeight) ||
      800;
    var visible = [];
    items.forEach(function (a, i) {
      var rect = a.getBoundingClientRect();
      if (rect.bottom > -40 && rect.top < vh + 40) visible.push(i);
    });

    var min;
    var max;
    if (!visible.length) {
      // 初回レイアウト前など: 先頭 PAD*2+1 件だけ
      min = 0;
      max = Math.min(items.length - 1, PAD * 2);
    } else {
      min = Math.max(0, Math.min.apply(null, visible) - PAD);
      max = Math.min(items.length - 1, Math.max.apply(null, visible) + PAD);
    }

    for (var i = min; i <= max; i++) {
      var rid = raceIdFromHref(items[i].getAttribute("href"));
      if (rid) enqueue(rid);
    }
  }

  function onScrollOrResize() {
    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(function () {
      if (observedRoot) prefetchVisibleWindow(observedRoot);
    }, 120);
  }

  function observeList(root) {
    if (!root) return;
    observedRoot = root;

    // 初回 + 再描画後
    prefetchVisibleWindow(root);

    if (typeof IntersectionObserver !== "undefined") {
      if (!io) {
        io = new IntersectionObserver(
          function () {
            prefetchVisibleWindow(observedRoot);
          },
          {
            root: null,
            // 前後余白（おおよそ数カード分）
            rootMargin: "280px 0px",
            threshold: 0.01,
          }
        );
      }
      listRaceLinks(root).forEach(function (a) {
        if (a.dataset.pbObserve === "1") return;
        a.dataset.pbObserve = "1";
        io.observe(a);
      });
    } else {
      // フォールバック: 先頭数件のみ
      var links = listRaceLinks(root);
      var n = Math.min(PAD * 2 + 1, links.length);
      for (var i = 0; i < n; i++) {
        enqueue(raceIdFromHref(links[i].getAttribute("href")));
      }
    }

    if (!root.dataset.pbScrollBound) {
      root.dataset.pbScrollBound = "1";
      global.addEventListener("scroll", onScrollOrResize, { passive: true });
      global.addEventListener("resize", onScrollOrResize, { passive: true });
    }

    if (typeof MutationObserver !== "undefined" && !root.dataset.pbMoBound) {
      root.dataset.pbMoBound = "1";
      var mo = new MutationObserver(function () {
        if (typeof IntersectionObserver !== "undefined" && io) {
          listRaceLinks(root).forEach(function (a) {
            if (a.dataset.pbObserve === "1") return;
            a.dataset.pbObserve = "1";
            io.observe(a);
          });
        }
        prefetchVisibleWindow(root);
      });
      mo.observe(root, { childList: true, subtree: true });
    }
  }

  // 起動時に session 済み分を done に反映
  (function hydrateDoneFromSession() {
    try {
      var pb = readSs(SS_PB);
      Object.keys(pb).forEach(function (k) {
        if (pb[k] && pb[k].bundle) {
          memPb[k] = pb[k];
          markDone(k, "prediction");
        }
      });
      var bd = readSs(SS_BOARD);
      Object.keys(bd).forEach(function (k) {
        if (bd[k] && bd[k].board) {
          memBoard[k] = bd[k];
          markDone(k, "board");
        }
      });
    } catch (e) { /* ignore */ }
  })();

  global.ExpectRacePrefetch = {
    putBundle: putBundle,
    getBundle: getBundle,
    putBoard: putBoard,
    getBoard: getBoard,
    putMeta: putMeta,
    getMeta: getMeta,
    putMetaFromCard: putMetaFromCard,
    prefetch: prefetch,
    prefetchPrediction: prefetchPrediction,
    prefetchBoard: prefetchBoard,
    /** @deprecated Version7.2: board-only。prefetchBoard を使用 */
    prefetchBoardHistory: prefetchBoard,
    prefetchVisibleWindow: prefetchVisibleWindow,
    observeList: observeList,
  };
})(typeof window !== "undefined" ? window : globalThis);
