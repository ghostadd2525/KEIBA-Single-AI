/**
 * ExpectRaceDetailCache — Prediction / Board / History のレース単位クライアントキャッシュ
 *
 * 優先: IndexedDB → 失敗時 localStorage
 * Odds / Odds Series は対象外（都度取得）
 *
 * 変更禁止: Prediction Engine / API 仕様 / AI ロジック
 */
(function (global) {
  "use strict";

  var DB_NAME = "expect_keiba_v1";
  var DB_VERSION = 1;
  var STORE = "race_detail";
  var LS_KEY = "expect_race_detail_cache_v1";
  var MAX_LS_ENTRIES = 24;
  var mem = Object.create(null);
  var dbPromise = null;
  var startupDone = false;
  var backend = "memory";
  var writeChains = Object.create(null);
  /** READY 待ちの不完全スナップショット（永続化しない） */
  var pendingMerge = Object.create(null);

  function enqueueWrite(raceId, fn) {
    var rid = String(raceId || "");
    var prev = writeChains[rid] || Promise.resolve();
    var next = prev
      .catch(function () { /* ignore prior */ })
      .then(fn);
    writeChains[rid] = next.then(
      function () {
        return undefined;
      },
      function () {
        return undefined;
      }
    );
    return next;
  }

  function formalHorseNumber(v) {
    if (v == null || v === "") return null;
    var n = Number(v);
    if (!Number.isFinite(n) || n < 1 || n !== Math.floor(n)) return null;
    return n;
  }

  function formalHorseId(v) {
    var s = String(v == null ? "" : v).trim();
    if (!s || /^tr_/i.test(s) || s === "0") return null;
    return s;
  }

  /** Board 全頭に正式 horse_number + horse_id があるか */
  function boardHorseNumbersReady(board) {
    var entries = (board && board.entries) || [];
    if (!entries.length) return false;
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (!formalHorseNumber(e && e.horse_number)) return false;
      if (!formalHorseId(e && e.horse_id)) return false;
    }
    return true;
  }

  function predictionBundleOf(prediction) {
    if (!prediction) return null;
    return prediction.bundle || prediction;
  }

  /** Prediction runners と Board entries の馬番・horse_id 整合 */
  function predictionBoardAligned(prediction, board) {
    var bundle = predictionBundleOf(prediction);
    if (!bundle || !board) return false;
    var runners =
      (bundle.evaluation && bundle.evaluation.runners) ||
      bundle.runners ||
      [];
    if (!runners.length) return false;
    var byNum = Object.create(null);
    (board.entries || []).forEach(function (e) {
      var n = formalHorseNumber(e && e.horse_number);
      if (n != null) byNum[String(n)] = e;
    });
    for (var i = 0; i < runners.length; i++) {
      var r = runners[i];
      var n = formalHorseNumber(
        r && (r.horse_number != null ? r.horse_number : r.umaban)
      );
      if (n == null) return false;
      var be = byNum[String(n)];
      if (!be) return false;
      var rid = formalHorseId(r && r.horse_id);
      var bid = formalHorseId(be.horse_id);
      if (rid && bid && rid !== bid) return false;
    }
    return true;
  }

  /**
   * キャッシュ保存可能な完全スナップショットか。
   * 馬番未確定・不整合のデータを絶対に保存しない。
   */
  function isSnapshotCacheable(row) {
    row = normalizeRow(row);
    if (!row || !row.prediction || !row.board) return false;
    var predMeta = (row.prediction && row.prediction.meta) || {};
    if (predMeta.prediction_status === "pending") return false;
    if (predMeta.engine_source === "pi_catalog_projection") return false;
    if (
      predMeta.fallback_reason === "pi_prediction_unavailable_catalog_projection" ||
      predMeta.fallback_reason === "pi_prediction_unavailable_pending"
    ) {
      return false;
    }
    var bundle = predictionBundleOf(row.prediction);
    var runners =
      (bundle && bundle.evaluation && bundle.evaluation.runners) ||
      (bundle && bundle.runners) ||
      [];
    if (!runners.length) return false;
    if (!boardHorseNumbersReady(row.board)) return false;
    if (!predictionBoardAligned(row.prediction, row.board)) return false;
    return true;
  }

  function authHeaders() {
    var h = { Accept: "application/json" };
    try {
      var t =
        (global.ExpectAuth &&
          ExpectAuth.getAccessToken &&
          ExpectAuth.getAccessToken()) ||
        global.localStorage.getItem("expect_access_token_v1") ||
        "";
      if (t) h.Authorization = "Bearer " + t;
    } catch (e) { /* ignore */ }
    return h;
  }

  /** data-status === ready のみ true。loading/pending/error は false */
  function fetchDataStatusReady(raceId) {
    if (
      global.ExpectDataStatus &&
      typeof ExpectDataStatus.getLast === "function"
    ) {
      var last = ExpectDataStatus.getLast(raceId);
      if (last && last.state === "ready") return Promise.resolve(true);
      if (last && last.state && last.state !== "ready") {
        return Promise.resolve(false);
      }
    }
    var url =
      "/api/races/" +
      encodeURIComponent(raceId) +
      "/data-status?_=" +
      Date.now();
    return fetch(url, {
      credentials: "include",
      cache: "no-store",
      headers: authHeaders(),
    })
      .then(function (res) {
        return res.json().then(function (body) {
          var data = (body && body.data) || body || {};
          if (
            global.ExpectDataStatus &&
            typeof ExpectDataStatus.remember === "function"
          ) {
            ExpectDataStatus.remember(raceId, data);
          }
          return data.state === "ready";
        });
      })
      .catch(function () {
        return false;
      });
  }

  function now() {
    return Date.now();
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  /** 発走時刻（JST）を expires_at（ms）に。無い場合は開催日 23:59:59 JST */
  function computeExpiresAt(raceId, postTime, dateIso) {
    var date =
      dateIso ||
      (String(raceId || "").match(/^(\d{4}-\d{2}-\d{2})/) || [])[1] ||
      "";
    var time = String(postTime || "").trim();
    var m = time.match(/^(\d{1,2}):(\d{2})/);
    if (date && m) {
      var iso =
        date +
        "T" +
        pad2(Number(m[1])) +
        ":" +
        m[2] +
        ":00+09:00";
      var t = new Date(iso).getTime();
      if (Number.isFinite(t)) return t;
    }
    if (date) {
      var end = new Date(date + "T23:59:59+09:00").getTime();
      if (Number.isFinite(end)) return end;
    }
    return now() + 24 * 60 * 60 * 1000;
  }

  function isExpired(row) {
    if (!row) return true;
    var exp = Number(row.expires_at);
    if (!Number.isFinite(exp)) return true;
    return exp <= now();
  }

  function normalizeRow(row) {
    if (!row || !row.race_id) return null;
    return {
      race_id: String(row.race_id),
      created_at: Number(row.created_at) || now(),
      expires_at: Number(row.expires_at) || 0,
      prediction: row.prediction != null ? row.prediction : null,
      board: row.board != null ? row.board : null,
      history: Array.isArray(row.history) ? row.history : row.history || null,
    };
  }

  function openDb() {
    if (dbPromise) return dbPromise;
    if (!global.indexedDB) {
      dbPromise = Promise.reject(new Error("no indexedDB"));
      return dbPromise;
    }
    dbPromise = new Promise(function (resolve, reject) {
      var req = global.indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = function () {
        reject(req.error || new Error("idb open failed"));
      };
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "race_id" });
        }
      };
      req.onsuccess = function () {
        resolve(req.result);
      };
    });
    return dbPromise;
  }

  function idbReq(mode, fn) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, mode);
        var store = tx.objectStore(STORE);
        var req = fn(store);
        req.onsuccess = function () {
          resolve(req.result);
        };
        req.onerror = function () {
          reject(req.error || new Error("idb request failed"));
        };
      });
    });
  }

  function readLsAll() {
    try {
      var raw = global.localStorage.getItem(LS_KEY);
      if (!raw) return {};
      var o = JSON.parse(raw);
      return o && typeof o === "object" ? o : {};
    } catch (e) {
      return {};
    }
  }

  function writeLsAll(map) {
    try {
      var keys = Object.keys(map);
      if (keys.length > MAX_LS_ENTRIES) {
        keys.sort(function (a, b) {
          return (map[a].created_at || 0) - (map[b].created_at || 0);
        });
        keys.slice(0, keys.length - MAX_LS_ENTRIES).forEach(function (k) {
          delete map[k];
        });
      }
      global.localStorage.setItem(LS_KEY, JSON.stringify(map));
      return true;
    } catch (e) {
      return false;
    }
  }

  function get(raceId) {
    if (!raceId) return Promise.resolve(null);
    var rid = String(raceId);

    function accept(row) {
      row = normalizeRow(row);
      if (!row || isExpired(row)) return null;
      // 馬番未確定・不整合キャッシュは破棄（誤馬番固定の再発防止）
      if (!isSnapshotCacheable(row)) return null;
      return row;
    }

    if (mem[rid]) {
      var hit = accept(mem[rid]);
      if (hit) return Promise.resolve(hit);
      delete mem[rid];
    }

    return idbReq("readonly", function (store) {
      return store.get(rid);
    })
      .then(function (row) {
        backend = "indexedDB";
        var ok = accept(row);
        if (!ok) {
          if (row) remove(rid);
          return null;
        }
        mem[rid] = ok;
        return ok;
      })
      .catch(function () {
        backend = "localStorage";
        var map = readLsAll();
        var ok = accept(map[rid]);
        if (!ok) {
          if (map[rid]) {
            delete map[rid];
            writeLsAll(map);
          }
          return null;
        }
        mem[rid] = ok;
        return ok;
      });
  }

  function put(row) {
    row = normalizeRow(row);
    if (!row) return Promise.resolve(null);
    if (!isSnapshotCacheable(row)) {
      return Promise.resolve(null);
    }
    if (!row.expires_at) {
      row.expires_at = computeExpiresAt(row.race_id, null, null);
    }
    if (isExpired(row)) {
      return remove(row.race_id).then(function () {
        return null;
      });
    }
    mem[row.race_id] = row;

    return idbReq("readwrite", function (store) {
      return store.put(row);
    })
      .then(function () {
        backend = "indexedDB";
        return row;
      })
      .catch(function () {
        backend = "localStorage";
        var map = readLsAll();
        map[row.race_id] = row;
        writeLsAll(map);
        return row;
      });
  }

  /**
   * data-status=ready かつ馬番確定・整合が取れたときだけ保存。
   * Prediction / Board が別タイミングで届いても、揃うまで pending に留め永続化しない。
   */
  function putIfReady(raceId, patch) {
    patch = patch || {};
    var rid = String(raceId);
    return enqueueWrite(rid, function () {
      return Promise.all([
        idbReq("readonly", function (store) {
          return store.get(rid);
        }).catch(function () {
          var map = readLsAll();
          return map[rid] || null;
        }),
        fetchDataStatusReady(rid),
      ]).then(function (parts) {
        var statusReady = !!parts[1];
        if (!statusReady) {
          delete pendingMerge[rid];
          return null;
        }

        var existing =
          normalizeRow(parts[0]) ||
          normalizeRow(pendingMerge[rid]) ||
          {
            race_id: rid,
            created_at: now(),
            expires_at: 0,
            prediction: null,
            board: null,
            history: null,
          };

        var next = {
          race_id: rid,
          created_at: existing.created_at || now(),
          expires_at: existing.expires_at || 0,
          prediction: existing.prediction,
          board: existing.board,
          history: existing.history,
        };
        if (patch.prediction != null) next.prediction = patch.prediction;
        if (patch.board != null) next.board = patch.board;
        if (patch.history != null) next.history = patch.history;
        if (
          next.history == null &&
          next.board &&
          Array.isArray(next.board.history)
        ) {
          next.history = next.board.history;
        }

        var info =
          patch.post_time ||
          (next.board && next.board.post_time) ||
          (predictionBundleOf(next.prediction) &&
            predictionBundleOf(next.prediction).race_info &&
            predictionBundleOf(next.prediction).race_info.post_time) ||
          "";
        var date =
          patch.date ||
          (next.board && next.board.date) ||
          (String(rid).match(/^(\d{4}-\d{2}-\d{2})/) || [])[1] ||
          "";
        next.expires_at = computeExpiresAt(rid, info, date);

        if (!isSnapshotCacheable(next)) {
          pendingMerge[rid] = next;
          return null;
        }
        delete pendingMerge[rid];
        return put(next);
      });
    });
  }

  /** @deprecated use putIfReady */
  function putPartial(raceId, patch) {
    return putIfReady(raceId, patch);
  }

  function remove(raceId) {
    if (!raceId) return Promise.resolve();
    var rid = String(raceId);
    delete mem[rid];
    return idbReq("readwrite", function (store) {
      return store.delete(rid);
    })
      .catch(function () {
        var map = readLsAll();
        if (map[rid]) {
          delete map[rid];
          writeLsAll(map);
        }
      })
      .then(function () {
        return undefined;
      });
  }

  function listAll() {
    return idbReq("readonly", function (store) {
      return store.getAll();
    })
      .then(function (rows) {
        backend = "indexedDB";
        return (rows || []).map(normalizeRow).filter(Boolean);
      })
      .catch(function () {
        backend = "localStorage";
        var map = readLsAll();
        return Object.keys(map)
          .map(function (k) {
            return normalizeRow(map[k]);
          })
          .filter(Boolean);
      });
  }

  function purgeExpired() {
    return listAll().then(function (rows) {
      var ops = [];
      rows.forEach(function (row) {
        if (isExpired(row) || !isSnapshotCacheable(row)) {
          ops.push(remove(row.race_id));
        }
      });
      return Promise.all(ops).then(function () {
        return ops.length;
      });
    });
  }

  /** 一覧に無い race_id を削除 */
  function retainOnly(raceIds) {
    var keep = Object.create(null);
    (raceIds || []).forEach(function (id) {
      if (id) keep[String(id)] = 1;
    });
    return listAll().then(function (rows) {
      var ops = [];
      rows.forEach(function (row) {
        if (!keep[row.race_id]) ops.push(remove(row.race_id));
      });
      return Promise.all(ops).then(function () {
        return ops.length;
      });
    });
  }

  function purgeOnStartup() {
    if (startupDone) return Promise.resolve(0);
    startupDone = true;
    return purgeExpired();
  }

  var LIST_CACHE_KEYS = [
    "expect_race_list_cache_v6",
    "expect_race_list_cache_v5",
    "expect_race_list_cache_v4",
    "expect_race_list_cache_v2",
  ];
  var PREFETCH_SS_KEYS = ["expect_pb_prefetch_v1", "expect_race_meta_v1"];

  /** レース一覧カード用 localStorage / sessionStorage のみ全削除（緊急用） */
  function clearListCaches() {
    var removed = 0;
    try {
      LIST_CACHE_KEYS.forEach(function (k) {
        if (global.localStorage && localStorage.getItem(k) != null) {
          localStorage.removeItem(k);
          removed += 1;
        }
      });
    } catch (e) { /* ignore */ }
    try {
      PREFETCH_SS_KEYS.forEach(function (k) {
        if (global.sessionStorage && sessionStorage.getItem(k) != null) {
          sessionStorage.removeItem(k);
          removed += 1;
        }
      });
    } catch (e2) { /* ignore */ }
    try {
      if (global.ExpectRaceListCache && ExpectRaceListCache.clearAll) {
        ExpectRaceListCache.clearAll().catch(function () { /* ignore */ });
        removed += 1;
      }
    } catch (e3) { /* ignore */ }
    return removed;
  }

  /**
   * ResultAutomation アーカイブ後のクライアント掃除。
   * サーバ DB / Archive は保持。クライアントの race_list_cache・詳細キャッシュのみ対象 race_id を削除。
   * （購入履歴・結果・研究用は Archive 側を参照）
   */
  function applyArchivePurge(raceIds) {
    var ids = (raceIds || []).map(String).filter(Boolean);
    var listOp =
      ids.length &&
      global.ExpectRaceListCache &&
      ExpectRaceListCache.removeMany
        ? ExpectRaceListCache.removeMany(ids)
        : Promise.resolve(0);

    if (!ids.length) {
      return listOp.then(function () {
        return purgeExpired().then(function (n) {
          return { list_removed: 0, detail_removed: n || 0, archived: true };
        });
      });
    }

    var detailOps = ids.map(function (id) {
      return remove(String(id));
    });
    return Promise.all([listOp, Promise.all(detailOps)]).then(function (parts) {
      return {
        list_removed: parts[0] || ids.length,
        detail_removed: ids.length,
        archived: true,
      };
    });
  }

  function applyDayArchiveFromApi(date) {
    if (!date) return Promise.resolve(null);
    var url = "/api/v1/results/day-archive?date=" + encodeURIComponent(date);
    return fetch(url, { cache: "no-store", credentials: "same-origin" })
      .then(function (res) {
        return res.json().then(function (body) {
          if (!res.ok || !body || !body.ok) return null;
          return body.data || null;
        });
      })
      .then(function (data) {
        if (!data || !data.archived) return null;
        var ids =
          (data.client_purge && data.client_purge.race_ids) ||
          (data.archive && data.archive.race_ids) ||
          [];
        return applyArchivePurge(ids).then(function (r) {
          return { archive: data, purge: r };
        });
      })
      .catch(function () {
        return null;
      });
  }

  // モジュール読込時に一度だけ期限切れ掃除（非同期・失敗無視）
  try {
    purgeOnStartup().catch(function () { /* ignore */ });
  } catch (e) { /* ignore */ }

  global.ExpectRaceDetailCache = {
    get: get,
    put: put,
    putPartial: putPartial,
    putIfReady: putIfReady,
    remove: remove,
    purgeExpired: purgeExpired,
    retainOnly: retainOnly,
    purgeOnStartup: purgeOnStartup,
    clearListCaches: clearListCaches,
    applyArchivePurge: applyArchivePurge,
    applyDayArchiveFromApi: applyDayArchiveFromApi,
    computeExpiresAt: computeExpiresAt,
    isSnapshotCacheable: isSnapshotCacheable,
    boardHorseNumbersReady: boardHorseNumbersReady,
    fetchDataStatusReady: fetchDataStatusReady,
    storageBackend: function () {
      return backend;
    },
  };
})(typeof window !== "undefined" ? window : globalThis);
