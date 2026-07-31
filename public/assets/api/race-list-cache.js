/**
 * ExpectRaceListCache — レース一覧 Stale-While-Revalidate キャッシュ
 *
 * IndexedDB store: race_list_cache（優先）→ 失敗時 localStorage
 * キー: race_id
 *
 * 保持: race_id / race_date / venue / race_number / race_name / post_time /
 *       confidence / prediction_status / favorite / thumbnail / updated_at
 * 対象外: オッズ・人気・リアルタイム値
 *
 * 変更禁止: Prediction Engine / Candidate Evaluation / AI ロジック
 */
(function (global) {
  "use strict";

  var DB_NAME = "expect_race_list_v2";
  var DB_VERSION = 1;
  var STORE = "race_list_cache";
  var LS_KEY = "expect_race_list_cache_v6";
  var LEGACY_LS_KEYS = [
    "expect_race_list_cache_v5",
    "expect_race_list_cache_v4",
    "expect_race_list_cache_v2",
  ];
  var MAX_LS_ENTRIES = 240;
  var mem = Object.create(null);
  var dbPromise = null;
  var backend = "memory";
  var prefetchInflight = null;

  function now() {
    return Date.now();
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
          var store = db.createObjectStore(STORE, { keyPath: "race_id" });
          store.createIndex("race_date", "race_date", { unique: false });
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
        if (!req) {
          resolve(undefined);
          return;
        }
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
      if (!raw) return { entries: {} };
      var o = JSON.parse(raw);
      if (!o || typeof o !== "object") return { entries: {} };
      if (!o.entries || typeof o.entries !== "object") o.entries = {};
      return o;
    } catch (e) {
      return { entries: {} };
    }
  }

  function writeLsAll(store) {
    try {
      var keys = Object.keys(store.entries || {});
      if (keys.length > MAX_LS_ENTRIES) {
        keys.sort(function (a, b) {
          return (
            Number((store.entries[a] && store.entries[a].updated_at) || 0) -
            Number((store.entries[b] && store.entries[b].updated_at) || 0)
          );
        });
        keys.slice(0, keys.length - MAX_LS_ENTRIES).forEach(function (k) {
          delete store.entries[k];
        });
      }
      global.localStorage.setItem(LS_KEY, JSON.stringify(store));
      return true;
    } catch (e) {
      return false;
    }
  }

  function confScore(card) {
    if (card && typeof card.confidence === "number") return card.confidence;
    var c =
      card &&
      card.summary &&
      card.summary.confidence &&
      typeof card.summary.confidence.score === "number"
        ? card.summary.confidence.score
        : null;
    return c;
  }

  function confBand(card) {
    if (card && card.confidence_band) return card.confidence_band;
    var c = card && card.summary && card.summary.confidence;
    return (c && c.band) || null;
  }

  function statusOf(card) {
    if (card && card.prediction_status) return String(card.prediction_status);
    return (card && card.prediction && card.prediction.status) || "missing";
  }

  function favoriteOf(card) {
    if (card && typeof card.favorite === "boolean") return card.favorite;
    try {
      if (global.ExpectFavorites && typeof ExpectFavorites.has === "function") {
        return !!ExpectFavorites.has(card && card.race_id);
      }
    } catch (e) { /* ignore */ }
    return false;
  }

  function thumbnailOf(card) {
    if (card && card.thumbnail != null && card.thumbnail !== "") {
      return String(card.thumbnail);
    }
    var info = (card && card.race_info) || {};
    var raceNo = info.race_number != null ? info.race_number : info.race_no;
    if (card && card.race_number != null) raceNo = card.race_number;
    var bg = info.bg != null ? Number(info.bg) : ((Number(raceNo) || 1) % 4) + 1;
    if (!Number.isFinite(bg) || bg < 1 || bg > 4) bg = 1;
    return "bg" + bg;
  }

  function raceDateOf(card) {
    if (card && card.race_date) return String(card.race_date);
    var info = (card && card.race_info) || {};
    var d = info.date || "";
    if (d && /^\d{4}-\d{2}-\d{2}/.test(d)) return d.slice(0, 10);
    var m = String((card && card.race_id) || "").match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : "";
  }

  /**
   * 正規キャッシュ行（race_id キー）
   * honmei はカード描画補助のみ（オッズ等は含めない）
   */
  function normalizeRow(input) {
    if (!input || !input.race_id) return null;
    var info = input.race_info || {};
    var raceNo =
      input.race_number != null
        ? input.race_number
        : info.race_number != null
          ? info.race_number
          : info.race_no;
    var conf = confScore(input);
    var honmei = null;
    if (input.honmei) {
      honmei = {
        horse_number: input.honmei.horse_number,
        horse_name: input.honmei.horse_name || "",
      };
    } else if (input.summary && input.summary.honmei) {
      honmei = {
        horse_number: input.summary.honmei.horse_number,
        horse_name: input.summary.honmei.horse_name || "",
      };
    }
    return {
      race_id: String(input.race_id),
      race_date: raceDateOf(input),
      venue: String(input.venue || info.venue || info.place || ""),
      race_number: raceNo != null && raceNo !== "" ? Number(raceNo) : null,
      race_name: String(input.race_name || info.race_name || info.class_label || ""),
      post_time: input.post_time != null ? input.post_time : info.post_time || null,
      confidence: conf,
      confidence_band: confBand(input),
      prediction_status: statusOf(input),
      favorite: favoriteOf(input),
      thumbnail: thumbnailOf(input),
      honmei: honmei,
      updated_at: Number(input.updated_at) || now(),
    };
  }

  /** 一覧カード DTO へ復元（描画用） */
  function toRaceCard(row) {
    row = normalizeRow(row);
    if (!row) return null;
    var conf =
      row.confidence != null && Number.isFinite(Number(row.confidence))
        ? {
            score: Number(row.confidence),
            band: row.confidence_band || null,
          }
        : null;
    return {
      schema_version: "expect-race-card-summary/1.0",
      race_id: row.race_id,
      race_info: {
        date: row.race_date,
        venue: row.venue,
        place: row.venue,
        race_number: row.race_number,
        race_name: row.race_name,
        post_time: row.post_time,
        race_label:
          (row.venue || "") +
          (row.race_number != null ? " " + row.race_number + "R" : ""),
      },
      prediction: {
        status: row.prediction_status || "missing",
        engine_source: null,
      },
      summary: conf
        ? { confidence: conf, honmei: row.honmei || null }
        : row.honmei
          ? { confidence: null, honmei: row.honmei }
          : null,
      favorite: !!row.favorite,
      thumbnail: row.thumbnail || null,
      updated_at: row.updated_at,
    };
  }

  function fromRaceCard(card) {
    return normalizeRow(card);
  }

  function cardFingerprint(cardOrRow) {
    var row = normalizeRow(cardOrRow);
    if (!row) return "";
    return [
      row.race_id,
      row.race_date,
      row.venue,
      row.race_number != null ? String(row.race_number) : "",
      row.race_name,
      row.post_time || "",
      row.confidence != null ? String(row.confidence) : "",
      row.prediction_status || "",
      row.favorite ? "1" : "0",
      row.thumbnail || "",
    ].join("|");
  }

  function acceptRow(row) {
    row = normalizeRow(row);
    if (!row || !row.race_id) return null;
    return row;
  }

  function get(raceId) {
    if (!raceId) return Promise.resolve(null);
    var rid = String(raceId);
    if (mem[rid]) {
      var hit = acceptRow(mem[rid]);
      if (hit) return Promise.resolve(hit);
      delete mem[rid];
    }
    return idbReq("readonly", function (store) {
      return store.get(rid);
    })
      .then(function (row) {
        backend = "indexedDB";
        var ok = acceptRow(row);
        if (!ok) return null;
        mem[rid] = ok;
        return ok;
      })
      .catch(function () {
        backend = "localStorage";
        var map = readLsAll();
        var ok = acceptRow(map.entries[rid]);
        if (!ok) return null;
        mem[rid] = ok;
        return ok;
      });
  }

  function put(row) {
    row = normalizeRow(row);
    if (!row) return Promise.resolve(null);
    row.updated_at = now();
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
        map.entries[row.race_id] = row;
        writeLsAll(map);
        return row;
      });
  }

  function putMany(rows) {
    var list = (rows || []).map(normalizeRow).filter(Boolean);
    if (!list.length) return Promise.resolve([]);
    list.forEach(function (r) {
      r.updated_at = now();
      mem[r.race_id] = r;
    });
    return openDb()
      .then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(STORE, "readwrite");
          var store = tx.objectStore(STORE);
          list.forEach(function (r) {
            store.put(r);
          });
          tx.oncomplete = function () {
            backend = "indexedDB";
            resolve(list);
          };
          tx.onerror = function () {
            reject(tx.error || new Error("idb putMany failed"));
          };
        });
      })
      .catch(function () {
        backend = "localStorage";
        var map = readLsAll();
        list.forEach(function (r) {
          map.entries[r.race_id] = r;
        });
        writeLsAll(map);
        return list;
      });
  }

  function putCards(cards) {
    return putMany((cards || []).map(fromRaceCard));
  }

  function remove(raceId) {
    var rid = String(raceId || "");
    if (!rid) return Promise.resolve(false);
    delete mem[rid];
    return idbReq("readwrite", function (store) {
      return store.delete(rid);
    })
      .then(function () {
        return true;
      })
      .catch(function () {
        var map = readLsAll();
        if (map.entries[rid]) {
          delete map.entries[rid];
          writeLsAll(map);
          return true;
        }
        return false;
      });
  }

  function removeMany(raceIds) {
    var ids = (raceIds || []).map(String).filter(Boolean);
    if (!ids.length) return Promise.resolve(0);
    ids.forEach(function (id) {
      delete mem[id];
    });
    return openDb()
      .then(function (db) {
        return new Promise(function (resolve, reject) {
          var tx = db.transaction(STORE, "readwrite");
          var store = tx.objectStore(STORE);
          ids.forEach(function (id) {
            store.delete(id);
          });
          tx.oncomplete = function () {
            resolve(ids.length);
          };
          tx.onerror = function () {
            reject(tx.error || new Error("idb removeMany failed"));
          };
        });
      })
      .catch(function () {
        var map = readLsAll();
        var n = 0;
        ids.forEach(function (id) {
          if (map.entries[id]) {
            delete map.entries[id];
            n += 1;
          }
        });
        writeLsAll(map);
        return n;
      });
  }

  function listAll() {
    return idbReq("readonly", function (store) {
      return store.getAll();
    })
      .then(function (rows) {
        backend = "indexedDB";
        return (rows || []).map(acceptRow).filter(Boolean);
      })
      .catch(function () {
        backend = "localStorage";
        var map = readLsAll();
        return Object.keys(map.entries)
          .map(function (k) {
            return acceptRow(map.entries[k]);
          })
          .filter(Boolean);
      });
  }

  function getByDates(dates) {
    var want = Object.create(null);
    (dates || []).forEach(function (d) {
      if (d) want[String(d)] = 1;
    });
    return listAll().then(function (rows) {
      var filtered = rows.filter(function (r) {
        return r.race_date && want[r.race_date];
      });
      filtered.sort(function (a, b) {
        if (a.race_date !== b.race_date) {
          return String(a.race_date).localeCompare(String(b.race_date));
        }
        var va = a.venue || "";
        var vb = b.venue || "";
        if (va !== vb) return va.localeCompare(vb, "ja");
        return (Number(a.race_number) || 0) - (Number(b.race_number) || 0);
      });
      return filtered;
    });
  }

  /** 日付配列から一覧描画用 payload を組み立て */
  function getPayloadForDates(dates, opts) {
    opts = opts || {};
    return getByDates(dates).then(function (rows) {
      if (!rows.length) return null;
      var cards = rows.map(toRaceCard).filter(Boolean);
      return {
        schema_version: "expect-race-cards/1.0",
        date: dates.length === 1 ? dates[0] : dates[0],
        dates: dates.slice(),
        count: cards.length,
        race_cards: cards,
        enriched: cards.some(function (c) {
          return c.prediction && c.prediction.status === "ready";
        }),
        _cacheKey: opts.cacheKey || undefined,
        from_list_cache: true,
      };
    });
  }

  function retainOnly(raceIds) {
    var keep = Object.create(null);
    (raceIds || []).forEach(function (id) {
      if (id) keep[String(id)] = 1;
    });
    return listAll().then(function (rows) {
      var drop = rows
        .filter(function (r) {
          return !keep[r.race_id];
        })
        .map(function (r) {
          return r.race_id;
        });
      return removeMany(drop);
    });
  }

  function clearAll() {
    mem = Object.create(null);
    var removed = 0;
    try {
      [LS_KEY].concat(LEGACY_LS_KEYS).forEach(function (k) {
        if (global.localStorage && localStorage.getItem(k) != null) {
          localStorage.removeItem(k);
          removed += 1;
        }
      });
    } catch (e) { /* ignore */ }
    return idbReq("readwrite", function (store) {
      return store.clear();
    })
      .then(function () {
        backend = "indexedDB";
        return removed + 1;
      })
      .catch(function () {
        return removed;
      });
  }

  function patchFavorite(raceId, isFav) {
    return get(raceId).then(function (row) {
      if (!row) return null;
      row.favorite = !!isFav;
      row.updated_at = now();
      return put(row);
    });
  }

  function weekendDates() {
    if (global.ExpectWeekendCalendar && ExpectWeekendCalendar.weekendRaceDates) {
      return ExpectWeekendCalendar.weekendRaceDates(new Date()).filter(Boolean);
    }
    return [];
  }

  /**
   * ログイン後 / 起動時: 今週開催の一覧をまとめて race_list_cache へ
   * （自信度は取れれば付与。失敗してもカタログだけで即表示可能にする）
   */
  function prefetchWeekend(opts) {
    opts = opts || {};
    if (prefetchInflight) return prefetchInflight;
    var dates = opts.dates || weekendDates();
    if (!dates.length) return Promise.resolve({ ok: false, reason: "no_dates" });
    if (!global.ExpectApi || !ExpectApi.Race) {
      return Promise.resolve({ ok: false, reason: "no_api" });
    }

    prefetchInflight = Promise.all(
      dates.map(function (d) {
        return Promise.resolve(ExpectApi.Race.list({ date: d }))
          .then(function (catalog) {
            return { date: d, items: (catalog && catalog.items) || [] };
          })
          .catch(function () {
            return { date: d, items: [] };
          });
      })
    )
      .then(function (rows) {
        var cards = [];
        rows.forEach(function (row) {
          (row.items || []).forEach(function (item) {
            var info = (item && item.race_info) || {};
            var raceNo =
              info.race_no != null
                ? info.race_no
                : item.race_number != null
                  ? item.race_number
                  : null;
            cards.push({
              race_id: item.race_id,
              race_info: {
                venue: info.venue || item.course || "",
                race_number: raceNo,
                race_name: info.race_name || item.race_name || "",
                post_time: info.post_time || null,
                date: info.date || row.date || "",
              },
              prediction: { status: "processing" },
              summary: null,
            });
          });
        });
        if (!cards.length) return { ok: false, reason: "empty", count: 0 };

        var enrichPromise = Promise.resolve(cards);
        if (global.ExpectApi.RaceCards) {
          enrichPromise = Promise.all(
            dates.map(function (d) {
              return Promise.resolve(ExpectApi.RaceCards.list({ date: d })).catch(
                function () {
                  return null;
                }
              );
            })
          ).then(function (parts) {
            var byId = Object.create(null);
            cards.forEach(function (c) {
              byId[String(c.race_id)] = c;
            });
            parts.forEach(function (p) {
              ((p && p.race_cards) || []).forEach(function (rc) {
                if (!rc || !rc.race_id) return;
                byId[String(rc.race_id)] = rc;
              });
            });
            return Object.keys(byId).map(function (k) {
              return byId[k];
            });
          });
        }

        return enrichPromise.then(function (finalCards) {
          return putCards(finalCards).then(function (saved) {
            return { ok: true, count: (saved && saved.length) || 0, dates: dates };
          });
        });
      })
      .catch(function () {
        return { ok: false, reason: "error" };
      })
      .then(function (result) {
        prefetchInflight = null;
        try {
          global.dispatchEvent(
            new CustomEvent("expect:race-list-cache-prefetched", {
              detail: result || {},
            })
          );
        } catch (e) { /* ignore */ }
        return result;
      });

    return prefetchInflight;
  }

  /** 後方互換: スロット一括は日付で展開して race_id 行へ保存 */
  function putPayload(slot, mode, dateKey, payload) {
    var cards = (payload && payload.race_cards) || [];
    return putCards(cards).then(function (saved) {
      return {
        slot: slot,
        mode: mode,
        date: dateKey,
        payload: payload,
        saved: saved,
      };
    });
  }

  function slimCard(card) {
    return toRaceCard(fromRaceCard(card));
  }

  function slimPayload(payload) {
    if (!payload) return null;
    var cards = ((payload.race_cards || []).map(slimCard)).filter(Boolean);
    if (!cards.length) return null;
    return Object.assign({}, payload, {
      race_cards: cards,
      count: cards.length,
    });
  }

  function slotKey(mode, dateKey) {
    return String(mode || "v2") + ":" + String(dateKey || "");
  }

  function scheduleBootPrefetch() {
    function run() {
      try {
        if (!global.ExpectAuth || typeof ExpectAuth.isLoggedIn !== "function") return;
        if (!ExpectAuth.isLoggedIn()) return;
        if (!global.ExpectApi || !ExpectApi.Race) return;
        prefetchWeekend({ reason: "boot" }).catch(function () { /* ignore */ });
      } catch (e) { /* ignore */ }
    }
    if (typeof document === "undefined") return;
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        setTimeout(run, 50);
      });
    } else {
      setTimeout(run, 50);
    }
  }

  // お気に入り変更 → キャッシュの favorite を差分更新
  try {
    global.addEventListener("expect:favorites-changed", function (ev) {
      var id = ev && ev.detail && ev.detail.id;
      if (!id) return;
      var isFav =
        global.ExpectFavorites && ExpectFavorites.has
          ? !!ExpectFavorites.has(id)
          : false;
      patchFavorite(id, isFav).catch(function () { /* ignore */ });
    });
  } catch (e) { /* ignore */ }

  global.ExpectRaceListCache = {
    STORE: STORE,
    get: get,
    put: put,
    putMany: putMany,
    putCards: putCards,
    putPayload: putPayload,
    remove: remove,
    removeMany: removeMany,
    retainOnly: retainOnly,
    clearAll: clearAll,
    listAll: listAll,
    getByDates: getByDates,
    getPayloadForDates: getPayloadForDates,
    toRaceCard: toRaceCard,
    fromRaceCard: fromRaceCard,
    slimCard: slimCard,
    slimPayload: slimPayload,
    cardFingerprint: cardFingerprint,
    patchFavorite: patchFavorite,
    prefetchWeekend: prefetchWeekend,
    slotKey: slotKey,
    backend: function () {
      return backend;
    },
  };

  scheduleBootPrefetch();
})(typeof window !== "undefined" ? window : globalThis);
