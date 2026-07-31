/**
 * ExpectHttpCache — Phase1: メモリ + sessionStorage TTL キャッシュ + in-flight Promise 共有
 * API レスポンス形状は変更しない（fetcher の戻り値をそのまま返す）
 */
(function (global) {
  "use strict";

  var PREFIX = "expect_http_cache_v1:";
  var mem = Object.create(null);
  var inflight = Object.create(null);

  /** 既存仕様に寄せた TTL（ms） */
  var TTL = {
    coverage: 60 * 1000,
    predictions_list: 60 * 1000,
    predictions_get: 120 * 1000,
    heatmap: 60 * 1000,
    summary: 60 * 1000,
    races: 5 * 60 * 1000,
    race_cards: 5 * 60 * 1000,
    default: 60 * 1000,
  };

  function now() {
    return Date.now();
  }

  function buildKey(path, query) {
    var url = String(path || "");
    if (query && typeof query === "object") {
      var keys = Object.keys(query).sort();
      var parts = [];
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        if (query[k] != null && query[k] !== "") {
          parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(query[k])));
        }
      }
      if (parts.length) url += "?" + parts.join("&");
    } else if (typeof query === "string" && query) {
      url += (url.indexOf("?") >= 0 ? "&" : "?") + query;
    }
    return url;
  }

  function readSession(key) {
    try {
      var raw = global.sessionStorage.getItem(PREFIX + key);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || parsed.expiresAt == null) return null;
      if (parsed.expiresAt <= now()) {
        global.sessionStorage.removeItem(PREFIX + key);
        return null;
      }
      return parsed.value;
    } catch (e) {
      return null;
    }
  }

  function writeSession(key, value, expiresAt) {
    try {
      global.sessionStorage.setItem(
        PREFIX + key,
        JSON.stringify({ expiresAt: expiresAt, value: value })
      );
    } catch (e) {
      /* quota / private mode — memory only */
    }
  }

  function readMem(key) {
    var hit = mem[key];
    if (!hit) return null;
    if (hit.expiresAt <= now()) {
      delete mem[key];
      return null;
    }
    return hit.value;
  }

  function writeMem(key, value, expiresAt) {
    mem[key] = { value: value, expiresAt: expiresAt };
  }

  /**
   * @param {string} key
   * @param {number} ttlMs
   * @param {function(): Promise<any>} fetcher
   * @param {{ skipCache?: boolean, persist?: boolean }} opts
   */
  function cachedGet(key, ttlMs, fetcher, opts) {
    opts = opts || {};
    var k = String(key || "");
    if (!k || typeof fetcher !== "function") {
      return fetcher ? fetcher() : Promise.reject(new Error("cachedGet: invalid args"));
    }
    var ttl = typeof ttlMs === "number" && ttlMs > 0 ? ttlMs : TTL.default;

    if (!opts.skipCache) {
      var fromMem = readMem(k);
      if (fromMem !== null && fromMem !== undefined) {
        return Promise.resolve(fromMem);
      }
      if (opts.persist !== false) {
        var fromSession = readSession(k);
        if (fromSession !== null && fromSession !== undefined) {
          writeMem(k, fromSession, now() + ttl);
          return Promise.resolve(fromSession);
        }
      }
    }

    if (inflight[k]) return inflight[k];

    inflight[k] = Promise.resolve()
      .then(function () {
        return fetcher();
      })
      .then(function (value) {
        // pending / 空は短命または非キャッシュ（呼び出し側で skip も可）
        if (value && value.pending === true) {
          return value;
        }
        var expiresAt = now() + ttl;
        writeMem(k, value, expiresAt);
        if (opts.persist !== false) writeSession(k, value, expiresAt);
        return value;
      })
      .finally(function () {
        delete inflight[k];
      });

    return inflight[k];
  }

  function clear(prefix) {
    var p = prefix != null ? String(prefix) : "";
    Object.keys(mem).forEach(function (k) {
      if (!p || k.indexOf(p) === 0) delete mem[k];
    });
    Object.keys(inflight).forEach(function (k) {
      if (!p || k.indexOf(p) === 0) delete inflight[k];
    });
    try {
      var store = global.sessionStorage;
      var remove = [];
      for (var i = 0; i < store.length; i++) {
        var sk = store.key(i);
        if (sk && sk.indexOf(PREFIX) === 0) {
          var bare = sk.slice(PREFIX.length);
          if (!p || bare.indexOf(p) === 0) remove.push(sk);
        }
      }
      remove.forEach(function (sk) {
        store.removeItem(sk);
      });
    } catch (e) {
      /* ignore */
    }
  }

  global.ExpectHttpCache = {
    TTL: TTL,
    buildKey: buildKey,
    cachedGet: cachedGet,
    clear: clear,
  };
})(window);
