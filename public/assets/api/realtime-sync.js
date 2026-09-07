/**
 * ExpectRealtimeSync — Version7.3 適応リアルタイム同期
 *
 * Prediction Engine / Candidate Evaluation / AI ロジックは触らない。
 * - Ready は soft/durable 即表示
 * - pending 監視中は短周期（既定 8s）、監視なしは長周期（30s）or 停止
 * - pending → Ready を 30s 以内に反映（計測付き）
 */
(function (global) {
  "use strict";

  var TICK_ACTIVE_MS = 8000;
  var TICK_IDLE_MS = 30000;
  var RESULTS_EVERY_ACTIVE = 2; // ≈16s
  var RESULTS_EVERY_IDLE = 1; // idle でも 30s に 1 回
  var METRICS_KEY = "expect_v73_sync_metrics_v1";
  var listeners = Object.create(null);
  var watched = Object.create(null);
  var watchStarted = Object.create(null);
  var readyKnown = Object.create(null);
  var timer = null;
  var page = "";
  var tickCount = 0;
  var inflight = false;
  var currentTickMs = TICK_IDLE_MS;
  var metrics = {
    predictionFetches: 0,
    predictionHitsSoft: 0,
    predictionHitsDurable: 0,
    predictionMisses: 0,
    predictionNetworkMs: [],
    predictionReadyTransitions: 0,
    pendingToReadyMs: [],
    retries: 0,
    retrySuccess: 0,
    resultsPolls: 0,
    archivePurges: 0,
    startedAt: Date.now(),
    prefetchHits: 0,
  };

  function loadMetrics() {
    try {
      var raw = global.sessionStorage.getItem(METRICS_KEY);
      if (!raw) {
        // migrate from v71 key if present
        raw = global.sessionStorage.getItem("expect_v71_sync_metrics_v1");
      }
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") {
          Object.keys(metrics).forEach(function (k) {
            if (parsed[k] != null) metrics[k] = parsed[k];
          });
        }
      }
    } catch (e) { /* ignore */ }
  }

  function saveMetrics() {
    try {
      global.sessionStorage.setItem(METRICS_KEY, JSON.stringify(metrics));
    } catch (e) { /* ignore */ }
  }

  function emit(event, payload) {
    var list = listeners[event] || [];
    for (var i = 0; i < list.length; i++) {
      try {
        list[i](payload);
      } catch (e) { /* ignore */ }
    }
  }

  function avg(arr) {
    if (!arr || !arr.length) return null;
    var s = 0;
    for (var i = 0; i < arr.length; i++) s += arr[i];
    return Math.round(s / arr.length);
  }

  function recordNetworkMs(ms) {
    metrics.predictionFetches += 1;
    metrics.predictionNetworkMs.push(ms);
    if (metrics.predictionNetworkMs.length > 40) {
      metrics.predictionNetworkMs = metrics.predictionNetworkMs.slice(-40);
    }
    saveMetrics();
  }

  function isReady(bundle, meta) {
    if (
      global.ExpectApi &&
      ExpectApi.Prediction &&
      typeof ExpectApi.Prediction.isReady === "function"
    ) {
      return ExpectApi.Prediction.isReady(bundle, meta);
    }
    return !!(
      bundle &&
      bundle.evaluation &&
      Array.isArray(bundle.evaluation.runners) &&
      bundle.evaluation.runners.length
    );
  }

  function watchedCount() {
    return Object.keys(watched).length;
  }

  function desiredTickMs() {
    return watchedCount() > 0 ? TICK_ACTIVE_MS : TICK_IDLE_MS;
  }

  function rescheduleIfNeeded() {
    var next = desiredTickMs();
    if (next === currentTickMs && timer) return;
    currentTickMs = next;
    if (timer) {
      global.clearInterval(timer);
      timer = global.setInterval(tick, currentTickMs);
    }
  }

  function watch(raceId, meta) {
    if (!raceId) return;
    if (!watched[raceId] && !readyKnown[raceId]) {
      watchStarted[raceId] = Date.now();
    }
    watched[raceId] = {
      status: (meta && meta.status) || "processing",
      at: Date.now(),
    };
    rescheduleIfNeeded();
  }

  function unwatch(raceId) {
    if (raceId) {
      delete watched[raceId];
      delete watchStarted[raceId];
    }
    rescheduleIfNeeded();
  }

  function watchMany(raceIds, status) {
    (raceIds || []).forEach(function (id) {
      watch(id, { status: status || "processing" });
    });
  }

  function on(event, fn) {
    if (!event || typeof fn !== "function") return function () {};
    if (!listeners[event]) listeners[event] = [];
    listeners[event].push(fn);
    return function () {
      listeners[event] = (listeners[event] || []).filter(function (f) {
        return f !== fn;
      });
    };
  }

  function fetchOne(raceId) {
    if (
      !global.ExpectApi ||
      !ExpectApi.Prediction ||
      typeof ExpectApi.Prediction.getWithMeta !== "function"
    ) {
      return Promise.resolve(null);
    }
    var soft =
      global.ExpectRacePrefetch && ExpectRacePrefetch.getBundle
        ? ExpectRacePrefetch.getBundle(raceId)
        : null;
    if (soft && soft.bundle && isReady(soft.bundle, soft.meta || {})) {
      metrics.predictionHitsSoft += 1;
      metrics.prefetchHits += 1;
      saveMetrics();
      return Promise.resolve({
        raceId: raceId,
        bundle: soft.bundle,
        meta: soft.meta || {},
        source: "soft",
      });
    }
    var t0 = Date.now();
    return ExpectApi.Prediction.getWithMeta(raceId)
      .then(function (result) {
        recordNetworkMs(Date.now() - t0);
        if (!result || result.pending || !result.bundle) {
          metrics.predictionMisses += 1;
          saveMetrics();
          return { raceId: raceId, pending: true, meta: (result && result.meta) || {} };
        }
        if (!isReady(result.bundle, result.meta || {})) {
          metrics.predictionMisses += 1;
          saveMetrics();
          return { raceId: raceId, pending: true, meta: result.meta || {} };
        }
        if (global.ExpectRacePrefetch && ExpectRacePrefetch.putBundle) {
          ExpectRacePrefetch.putBundle(raceId, result.bundle, result.meta || {});
        }
        return {
          raceId: raceId,
          bundle: result.bundle,
          meta: result.meta || {},
          source: "network",
        };
      })
      .catch(function () {
        recordNetworkMs(Date.now() - t0);
        metrics.retries += 1;
        metrics.predictionMisses += 1;
        saveMetrics();
        return null;
      });
  }

  function pollPredictions() {
    var ids = Object.keys(watched).filter(function (id) {
      return !readyKnown[id];
    });
    if (!ids.length) return Promise.resolve([]);

    var concurrency = 2;
    var next = 0;
    var out = [];

    function worker() {
      return new Promise(function (resolve) {
        function step() {
          var i = next++;
          if (i >= ids.length) {
            resolve();
            return;
          }
          fetchOne(ids[i]).then(function (row) {
            if (row) out.push(row);
            step();
          });
        }
        step();
      });
    }

    var workers = [];
    for (var w = 0; w < concurrency; w++) workers.push(worker());
    return Promise.all(workers).then(function () {
      out.forEach(function (row) {
        if (!row || row.pending || !row.bundle) return;
        var wasReady = !!readyKnown[row.raceId];
        readyKnown[row.raceId] = true;
        delete watched[row.raceId];
        if (!wasReady) {
          metrics.predictionReadyTransitions += 1;
          metrics.retrySuccess += 1;
          var started = watchStarted[row.raceId];
          if (started) {
            var waited = Date.now() - started;
            metrics.pendingToReadyMs.push(waited);
            if (metrics.pendingToReadyMs.length > 40) {
              metrics.pendingToReadyMs = metrics.pendingToReadyMs.slice(-40);
            }
            delete watchStarted[row.raceId];
          }
          saveMetrics();
          emit("prediction-ready", row);
          emit("status-changed", {
            raceId: row.raceId,
            status: "ready",
            bundle: row.bundle,
            meta: row.meta,
            source: row.source,
          });
        }
      });
      rescheduleIfNeeded();
      return out;
    });
  }

  function pollResults() {
    metrics.resultsPolls += 1;
    saveMetrics();
    var date = "";
    try {
      if (global.ExpectCalendarWeekend && ExpectCalendarWeekend.todayJst) {
        date = ExpectCalendarWeekend.todayJst();
      }
    } catch (e) { /* ignore */ }
    if (!date) {
      var d = new Date();
      date =
        d.getFullYear() +
        "-" +
        String(d.getMonth() + 1).padStart(2, "0") +
        "-" +
        String(d.getDate()).padStart(2, "0");
    }

    var tasks = [];
    if (
      global.ExpectRaceDetailCache &&
      ExpectRaceDetailCache.applyDayArchiveFromApi
    ) {
      tasks.push(
        ExpectRaceDetailCache.applyDayArchiveFromApi(date)
          .then(function (res) {
            if (res && (res.purged || (res.race_ids && res.race_ids.length))) {
              metrics.archivePurges += 1;
              saveMetrics();
              emit("archive", res);
            }
            return res;
          })
          .catch(function () {
            return null;
          })
      );
    }
    if (
      global.ExpectApi &&
      ExpectApi.User &&
      typeof ExpectApi.User.settlePendingRaceResults === "function"
    ) {
      tasks.push(
        ExpectApi.User.settlePendingRaceResults()
          .then(function (res) {
            emit("results-updated", { source: "settlePending", data: res, date: date });
            return res;
          })
          .catch(function () {
            return null;
          })
      );
    } else {
      emit("results-updated", { source: "tick", date: date });
    }
    return Promise.all(tasks);
  }

  function tick() {
    if (inflight) return;
    if (global.document && global.document.visibilityState === "hidden") return;
    inflight = true;
    tickCount += 1;
    emit("tick", { at: Date.now(), tickCount: tickCount });
    var active = watchedCount() > 0;
    var every = active ? RESULTS_EVERY_ACTIVE : RESULTS_EVERY_IDLE;
    var jobs = [pollPredictions()];
    if (tickCount % every === 0) jobs.push(pollResults());
    Promise.all(jobs)
      .catch(function () {
        return null;
      })
      .then(function () {
        inflight = false;
        rescheduleIfNeeded();
      });
  }

  function start(opts) {
    opts = opts || {};
    page = opts.page || page || "unknown";
    loadMetrics();
    if (timer) return;
    currentTickMs = desiredTickMs();
    timer = global.setInterval(tick, currentTickMs);
    // 初回は少し遅らせて一覧描画・prefetch と競合しない（即時指定時は 0）
    global.setTimeout(tick, opts.immediate ? 0 : 1200);
  }

  function stop() {
    if (timer) {
      global.clearInterval(timer);
      timer = null;
    }
  }

  function noteSoftHit() {
    metrics.predictionHitsSoft += 1;
    saveMetrics();
  }

  function noteDurableHit() {
    metrics.predictionHitsDurable += 1;
    saveMetrics();
  }

  function noteFetchMs(ms) {
    recordNetworkMs(ms);
  }

  function getSnapshot() {
    var net = metrics.predictionNetworkMs || [];
    var soft = metrics.predictionHitsSoft || 0;
    var durable = metrics.predictionHitsDurable || 0;
    var prefetch = metrics.prefetchHits || 0;
    var hits = soft + durable;
    var fetches = metrics.predictionFetches || 0;
    var misses = metrics.predictionMisses || 0;
    var total = hits + fetches;
    var cacheHitRate = total ? Math.round((hits / total) * 1000) / 10 : null;
    var softTotal = soft + misses + fetches;
    var durableTotal = durable + misses + fetches;
    var retries = metrics.retries || 0;
    var retryOk = metrics.retrySuccess || 0;
    return {
      schema_version: "expect-v73-sync-metrics/1.0",
      page: page,
      tick_ms: currentTickMs,
      tick_active_ms: TICK_ACTIVE_MS,
      tick_idle_ms: TICK_IDLE_MS,
      watched: watchedCount(),
      ready_known: Object.keys(readyKnown).length,
      avg_prediction_fetch_ms: avg(net),
      avg_pending_to_ready_ms: avg(metrics.pendingToReadyMs || []),
      prediction_ready_transitions: metrics.predictionReadyTransitions || 0,
      cache_hit_rate_pct: cacheHitRate,
      soft_cache_hit_rate_pct: softTotal
        ? Math.round((soft / softTotal) * 1000) / 10
        : null,
      durable_cache_hit_rate_pct: durableTotal
        ? Math.round((durable / durableTotal) * 1000) / 10
        : null,
      prefetch_hit_rate_pct: softTotal
        ? Math.round((prefetch / softTotal) * 1000) / 10
        : null,
      miss_rate_pct: total
        ? Math.round((misses / Math.max(total + misses, 1)) * 1000) / 10
        : null,
      retry_success_rate_pct:
        retries > 0 ? Math.round((retryOk / Math.max(retries, 1)) * 1000) / 10 : null,
      results_polls: metrics.resultsPolls || 0,
      archive_purges: metrics.archivePurges || 0,
      raw: metrics,
    };
  }

  loadMetrics();

  global.ExpectRealtimeSync = {
    TICK_MS: TICK_ACTIVE_MS,
    TICK_ACTIVE_MS: TICK_ACTIVE_MS,
    TICK_IDLE_MS: TICK_IDLE_MS,
    start: start,
    stop: stop,
    on: on,
    watch: watch,
    unwatch: unwatch,
    watchMany: watchMany,
    noteSoftHit: noteSoftHit,
    noteDurableHit: noteDurableHit,
    noteFetchMs: noteFetchMs,
    getSnapshot: getSnapshot,
    pollNow: tick,
  };
})(typeof window !== "undefined" ? window : globalThis);
