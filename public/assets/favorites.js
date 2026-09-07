/**
 * お気に入りレース（最大3件・超過時は古いものから削除）
 */
(function (global) {
  "use strict";

  var KEY = "expect_favorites_v1";
  var MAX = 3;

  /** ログイン中ユーザー ID（未ログインは空） */
  function currentUserId() {
    try {
      if (global.ExpectAuth && typeof ExpectAuth.current === "function") {
        var cur = ExpectAuth.current();
        if (cur && cur.id) return String(cur.id);
      }
      var raw = global.localStorage.getItem("expect_auth_v1");
      var parsed = raw ? JSON.parse(raw) : null;
      return parsed && parsed.id ? String(parsed.id) : "";
    } catch (e) {
      return "";
    }
  }

  /**
   * お気に入りはユーザーごとに分離する。
   * 旧キー expect_favorites_v1 はログイン時にそのユーザー枠へ一度だけ移行。
   */
  function storageKey() {
    var uid = currentUserId();
    return uid ? KEY + ":" + uid : KEY + ":guest";
  }

  function migrateLegacyFavorites(store, key) {
    if (!store) return;
    try {
      var legacy = store.getItem(KEY);
      if (!legacy) return;
      if (!store.getItem(key)) {
        store.setItem(key, legacy);
      }
      // 共有キーを消して他ユーザーへ漏れないようにする
      store.removeItem(KEY);
    } catch (e) { /* ignore */ }
  }

  /** @deprecated dev fallback — Prefer cacheBundles() from Prediction API */
  var CATALOG = {
    "20260719_tokyo_11": {
      id: "20260719_tokyo_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "東京 11R",
      name: "函館記念",
      badge: "GIII",
      postTime: "15:45",
      image: "assets/images/race-bg-1.webp",
      bg: 1,
      ai: { overall: 88, pedigree: 90, pace: 86, jockey: 84, form: 91, odds: 79 }
    },
    "20260719_hanshin_11": {
      id: "20260719_hanshin_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "阪神 11R",
      name: "メインレース",
      badge: "GIII",
      postTime: "15:40",
      image: "assets/images/race-bg-2.webp",
      bg: 2,
      ai: { overall: 92, pedigree: 94, pace: 90, jockey: 88, form: 93, odds: 82 }
    },
    "20260719_fukushima_11": {
      id: "20260719_fukushima_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "福島 11R",
      name: "ラジオNIKKEI賞",
      badge: "GIII",
      postTime: "15:25",
      image: "assets/images/race-bg-3.webp",
      bg: 3,
      ai: { overall: 76, pedigree: 78, pace: 74, jockey: 80, form: 72, odds: 70 }
    },
    "20260719_hakodate_11": {
      id: "20260719_hakodate_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "函館 11R",
      name: "函館2歳S",
      badge: "GIII",
      postTime: "15:10",
      image: "assets/images/race-bg-4.webp",
      bg: 4,
      ai: { overall: 81, pedigree: 83, pace: 79, jockey: 77, form: 85, odds: 74 }
    },
    "20260720_nakayama_11": {
      id: "20260720_nakayama_11",
      date: "2026-07-20",
      dateLabel: "7/20（日）",
      place: "中山 11R",
      name: "中山ダート戦",
      badge: "L",
      postTime: "15:30",
      image: "assets/images/race-bg-1.webp",
      bg: 1,
      ai: { overall: 79, pedigree: 76, pace: 82, jockey: 75, form: 80, odds: 78 }
    }
  };

  var _bundleCache = {};

  function v2RaceListUiOn() {
    return !!(
      global.ExpectUiFeatures &&
      typeof ExpectUiFeatures.enabled === "function" &&
      ExpectUiFeatures.enabled("v2_race_list_ui")
    );
  }

  function isRaceCardSummary(b) {
    if (!b || typeof b !== "object") return false;
    if (b.schema_version && String(b.schema_version).indexOf("race-card-summary") >= 0) {
      return true;
    }
    return !!(b.prediction && typeof b.prediction === "object" && "summary" in b);
  }

  function scoreFromBundle(b) {
    if (!b) return null;
    if (isRaceCardSummary(b)) {
      var sc =
        b.summary &&
        b.summary.confidence &&
        typeof b.summary.confidence.score === "number"
          ? b.summary.confidence.score
          : null;
      if (typeof sc === "number") {
        return sc <= 1 ? Math.round(sc * 100) : Math.round(sc);
      }
      return null;
    }
    var c = b.ai_confidence || {};
    if (typeof c.score === "number") {
      return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
    }
    return null;
  }

  function summaryFieldsFromBundle(b) {
    if (!isRaceCardSummary(b)) return {};
    var summary = b.summary;
    if (!summary) return { honmei: "", honmeiNum: null, confPct: null, confBand: "" };
    var h = summary.honmei;
    var conf = summary.confidence;
    var confPct = null;
    if (conf && typeof conf.score === "number") {
      confPct = conf.score <= 1 ? Math.round(conf.score * 100) : Math.round(conf.score);
    }
    return {
      honmei: h && h.horse_name ? String(h.horse_name) : "",
      honmeiNum: h && h.horse_number != null ? h.horse_number : null,
      confPct: confPct,
      confBand: conf && conf.band ? String(conf.band) : "",
    };
  }

  function metaFromBundle(b) {
    if (!b || !b.race_id) return null;
    var info = b.race_info || {};
    var d = info.date || "";
    if (!d && b.race_id) {
      var m = String(b.race_id).match(/^(\d{4}-\d{2}-\d{2})/);
      if (m) d = m[1];
    }
    var p = String(d).split("-");
    var dateLabel =
      info.date_label ||
      (p.length === 3 ? Number(p[1]) + "/" + Number(p[2]) : d);
    var raceNo = info.race_number != null ? info.race_number : info.race_no;
    var summaryBits = summaryFieldsFromBundle(b);
    return Object.assign(
      {
        id: b.race_id,
        date: d,
        dateLabel: dateLabel,
        place:
          info.race_label ||
          (info.venue || "") + (raceNo != null ? " " + raceNo + "R" : ""),
        name: info.race_name || info.class_label || "",
        badge: info.grade || "",
        postTime: info.post_time || "",
        image: "assets/images/race-bg-1.webp",
        bg: ((Number(raceNo) || 1) % 4) + 1,
      },
      summaryBits
    );
  }

  function aiFromBundle(b) {
    if (global.ExpectAnalysisBind && typeof ExpectAnalysisBind.toAiParams === "function") {
      var mapped = ExpectAnalysisBind.toAiParams(b, null);
      if (mapped) return mapped;
      return {
        overall: null,
        history: null,
        distance: null,
        style_fit: null,
        front: null,
        pace_resilience: null,
      };
    }
    var overall = scoreFromBundle(b);
    if (overall == null) {
      return {
        overall: null,
        history: null,
        distance: null,
        style_fit: null,
        front: null,
        pace_resilience: null,
      };
    }
    return {
      overall: overall,
      history: overall,
      distance: overall,
      style_fit: overall,
      front: overall,
      pace_resilience: overall,
    };
  }

  /** RaceCardSummary から localStorage のお気に入りへ ◎/信頼度を投影（サーバー同期はしない） */
  function enrichStoredFromCache() {
    var store = storage();
    if (!store) return;
    var items = read();
    if (!items.length) return;
    var changed = false;
    var next = items.map(function (raw) {
      var b = _bundleCache[raw.id];
      if (!b || !isRaceCardSummary(b)) return raw;
      var fields = summaryFieldsFromBundle(b);
      var meta = metaFromBundle(b);
      var updated = Object.assign({}, raw);
      if (fields.honmei) {
        if (updated.honmei !== fields.honmei) changed = true;
        updated.honmei = fields.honmei;
      }
      if (fields.honmeiNum != null) {
        if (updated.honmeiNum !== fields.honmeiNum) changed = true;
        updated.honmeiNum = fields.honmeiNum;
      }
      if (fields.confPct != null) {
        if (updated.confPct !== fields.confPct) changed = true;
        updated.confPct = fields.confPct;
      }
      if (fields.confBand) {
        if (updated.confBand !== fields.confBand) changed = true;
        updated.confBand = fields.confBand;
      }
      if (meta.place && updated.place !== meta.place) {
        updated.place = meta.place;
        changed = true;
      }
      if (meta.name && updated.name !== meta.name) {
        updated.name = meta.name;
        changed = true;
      }
      if (meta.badge && updated.badge !== meta.badge) {
        updated.badge = meta.badge;
        changed = true;
      }
      if (meta.postTime && updated.postTime !== meta.postTime) {
        updated.postTime = meta.postTime;
        changed = true;
      }
      if (meta.date && updated.date !== meta.date) {
        updated.date = meta.date;
        changed = true;
      }
      if (meta.dateLabel && updated.dateLabel !== meta.dateLabel) {
        updated.dateLabel = meta.dateLabel;
        changed = true;
      }
      return updated;
    });
    if (!changed) return;
    try {
      var key = storageKey();
      migrateLegacyFavorites(store, key);
      store.setItem(key, JSON.stringify(next));
    } catch (e) {
      /* ignore */
    }
  }

  function cacheBundles(bundles) {
    (bundles || []).forEach(function (b) {
      if (b && b.race_id) _bundleCache[b.race_id] = b;
    });
    enrichStoredFromCache();
  }

  function cacheBundle(bundle) {
    if (bundle && bundle.race_id) {
      _bundleCache[bundle.race_id] = bundle;
      enrichStoredFromCache();
    }
  }

  var AI_PARAM_LABELS = {
    history: "近走成績",
    distance: "距離適性",
    style_fit: "脚質×距離",
    front: "先行傾向",
    pace_resilience: "展開耐性",
  };

  function defaultAi() {
    return {
      overall: null,
      history: null,
      distance: null,
      style_fit: null,
      front: null,
      pace_resilience: null,
    };
  }

  function allowCatalog() {
    return (
      global.ExpectMockGate &&
      typeof ExpectMockGate.allowMockFallback === "function" &&
      ExpectMockGate.allowMockFallback()
    );
  }

  function getAi(id) {
    if (_bundleCache[id]) return aiFromBundle(_bundleCache[id]);
    // Analysis ダッシュボードではモック70%を使わない。
    // カタログは開発モック許可時のみ。
    if (allowCatalog() && CATALOG[id] && CATALOG[id].ai) {
      var c = CATALOG[id].ai;
      return {
        overall: c.overall != null ? c.overall : null,
        history: c.form != null ? c.form : c.pedigree != null ? c.pedigree : null,
        distance: c.pace != null ? c.pace : null,
        style_fit: c.jockey != null ? c.jockey : null,
        front: c.form != null ? c.form : null,
        pace_resilience: c.odds != null ? c.odds : null,
      };
    }
    return defaultAi();
  }

  function storage() {
    try {
      return global.localStorage;
    } catch (e) {
      return null;
    }
  }

  function read() {
    var store = storage();
    if (!store) return [];
    try {
      var key = storageKey();
      migrateLegacyFavorites(store, key);
      var list = JSON.parse(store.getItem(key) || "[]");
      return Array.isArray(list) ? list : [];
    } catch (e) {
      return [];
    }
  }

  function write(list, opts) {
    opts = opts || {};
    var store = storage();
    if (!store) return false;
    try {
      var key = storageKey();
      migrateLegacyFavorites(store, key);
      store.setItem(key, JSON.stringify(list));
      // intent 同期は add/remove が enqueue。importFromServer 等は schedule しない。
      if (opts.scheduleSync !== false && !_suppressSyncSchedule) {
        scheduleServerSync();
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  /** ログイン切替後に UI を当該ユーザーの枠へ載せ替える */
  function bindToCurrentUser(opts) {
    opts = opts || {};
    // 別ユーザー枠へ載せる前に、未送信 intent を破棄（誤適用防止）
    _pendingOps = [];
    if (_syncTimer) {
      clearTimeout(_syncTimer);
      _syncTimer = null;
    }
    var store = storage();
    if (store) migrateLegacyFavorites(store, storageKey());
    if (opts.clearGuest) {
      try {
        if (store) store.removeItem(KEY + ":guest");
      } catch (e) { /* ignore */ }
    }
    global.dispatchEvent(
      new CustomEvent("expect:favorites-changed", {
        detail: { list: list(), source: "user-switch" },
      })
    );
    return list();
  }

  var _syncTimer = null;
  var _syncing = false;
  var _pendingOps = [];
  var _suppressSyncSchedule = false;

  function itemToSyncDto(item) {
    return {
      race_id: item.id,
      place: item.place || null,
      name: item.name || null,
      badge: item.badge || null,
      post_time: item.postTime || null,
      date_label: item.dateLabel || null,
      added_at: item.addedAt || Date.now(),
    };
  }

  /** サーバー同期用 DTO（expect-favorites/1.0）— 表示・login payload 用。PUT 本体には使わない */
  function exportForSync() {
    var items = list().map(itemToSyncDto);
    return {
      schema_version: "expect-favorites/1.0",
      race_ids: items.map(function (x) {
        return x.race_id;
      }),
      items: items,
      synced_at: null,
    };
  }

  function enqueueOp(op) {
    if (!op || !op.op || !op.race_id) return;
    _pendingOps.push(op);
  }

  /**
   * サーバー favorites を localStorage へ取り込む
   * @param {object} fav FavoritesState
   * @param {{ merge?: boolean }} opts merge=true でローカルと結合
   */
  function importFromServer(fav, opts) {
    opts = opts || {};
    if (!fav || typeof fav !== "object") return list();
    var remoteItems = Array.isArray(fav.items) ? fav.items : [];
    var mapped = remoteItems.map(function (it) {
      return normalize({
        id: it.race_id || it.id,
        place: it.place,
        name: it.name,
        badge: it.badge,
        postTime: it.post_time || it.postTime,
        dateLabel: it.date_label || it.dateLabel,
        addedAt: it.added_at || it.addedAt || Date.now(),
      });
    });

    var next = mapped;
    if (opts.merge) {
      var map = {};
      list().concat(mapped).forEach(function (item) {
        var prev = map[item.id];
        if (!prev || (item.addedAt || 0) >= (prev.addedAt || 0)) map[item.id] = item;
      });
      next = Object.keys(map)
        .map(function (k) {
          return map[k];
        })
        .sort(function (a, b) {
          return (b.addedAt || 0) - (a.addedAt || 0);
        })
        .slice(0, MAX);
    } else {
      next = mapped
        .sort(function (a, b) {
          return (b.addedAt || 0) - (a.addedAt || 0);
        })
        .slice(0, MAX);
    }

    _suppressSyncSchedule = true;
    try {
      var store = storage();
      if (store) {
        try {
          var key = storageKey();
          migrateLegacyFavorites(store, key);
          store.setItem(key, JSON.stringify(next));
        } catch (e) { /* ignore */ }
      }
    } finally {
      _suppressSyncSchedule = false;
    }
    global.dispatchEvent(
      new CustomEvent("expect:favorites-changed", { detail: { list: list(), source: "server" } })
    );
    return list();
  }

  function canSync() {
    var authed =
      global.ExpectAuth &&
      (typeof ExpectAuth.hasServerSession === "function"
        ? ExpectAuth.hasServerSession()
        : ExpectAuth.isLoggedIn() && ExpectAuth.getAccessToken && ExpectAuth.getAccessToken());
    return !!(
      authed &&
      global.ExpectApi &&
      ExpectApi.Auth &&
      typeof ExpectApi.Auth.putFavorites === "function"
    );
  }

  function scheduleServerSync() {
    if (!canSync()) return;
    if (!_pendingOps.length) return;
    if (_syncTimer) clearTimeout(_syncTimer);
    _syncTimer = setTimeout(function () {
      syncNow({ reason: "local-change" }).catch(function () { /* ignore */ });
    }, 600);
  }

  /**
   * intent ops をサーバー最新へ適用。pending がなければ pull（login）または noop。
   * フルリスト PUT は行わない（stale overwrite 防止）。
   */
  function syncNow(opts) {
    opts = opts || {};
    if (!canSync()) return Promise.resolve({ ok: false, reason: "guest" });
    if (_syncing) return Promise.resolve({ ok: false, reason: "busy" });

    if (!_pendingOps.length) {
      if (opts.reason === "login" || opts.pullIfEmpty) {
        return pullFromServer().then(function (r) {
          return Object.assign({ reason: opts.reason || "pull" }, r);
        });
      }
      return Promise.resolve({ ok: true, reason: "noop", favorites: exportForSync() });
    }

    _syncing = true;
    var batch = _pendingOps.slice();
    _pendingOps = [];

    var body = batch.length === 1 ? batch[0] : { ops: batch };

    return ExpectApi.Auth.putFavorites(body)
      .then(function (fav) {
        if (fav) importFromServer(fav, { merge: false });
        return { ok: true, favorites: fav, reason: opts.reason || "sync", ops: batch };
      })
      .catch(function (err) {
        // 失敗時は未送信 ops を先頭に戻す
        _pendingOps = batch.concat(_pendingOps);
        return { ok: false, error: err };
      })
      .then(function (result) {
        _syncing = false;
        return result;
      });
  }

  function pullFromServer() {
    if (!canSync() || !ExpectApi.Auth.getFavorites) {
      return Promise.resolve({ ok: false, reason: "guest" });
    }
    return ExpectApi.Auth.getFavorites()
      .then(function (fav) {
        importFromServer(fav, { merge: false });
        return { ok: true, favorites: fav };
      })
      .catch(function (err) {
        return { ok: false, error: err };
      });
  }

  function normalize(entry) {
    var base = getMeta(entry.id, entry);
    var image = entry.image || base.image || "assets/images/race-bg-1.webp";
    var bg = entry.bg || base.bg || 1;
    if (String(image).indexOf("race-bg-") < 0 && base.image) {
      image = base.image;
      bg = base.bg || bg;
    }
    return {
      id: entry.id,
      date: entry.date || base.date || "",
      dateLabel: entry.dateLabel || base.dateLabel || "",
      place: entry.place || base.place || "レース",
      name: entry.name || base.name || "",
      badge: entry.badge || base.badge || "",
      postTime: entry.postTime || base.postTime || "",
      image: image,
      bg: bg,
      ai: getAi(entry.id),
      addedAt: entry.addedAt || Date.now(),
      honmei: entry.honmei != null ? entry.honmei : base.honmei || "",
      honmeiNum:
        entry.honmeiNum != null
          ? entry.honmeiNum
          : base.honmeiNum != null
            ? base.honmeiNum
            : null,
      confPct:
        entry.confPct != null
          ? entry.confPct
          : base.confPct != null
            ? base.confPct
            : null,
      confBand: entry.confBand != null ? entry.confBand : base.confBand || "",
    };
  }

  function list() {
    return read()
      .map(normalize)
      .sort(function (a, b) {
        return (b.addedAt || 0) - (a.addedAt || 0);
      });
  }

  function has(id) {
    return read().some(function (item) {
      return item.id === id;
    });
  }

  function getMeta(id, override) {
    var base = _bundleCache[id]
      ? Object.assign({ ai: getAi(id) }, metaFromBundle(_bundleCache[id]))
      : allowCatalog() && CATALOG[id]
        ? Object.assign({}, CATALOG[id])
        : { id: id };
    if (override) {
      Object.keys(override).forEach(function (k) {
        if (override[k] != null && override[k] !== "") base[k] = override[k];
      });
    }
    return base;
  }

  function oldest() {
    var items = read().slice().sort(function (a, b) {
      return (a.addedAt || 0) - (b.addedAt || 0);
    });
    return items.length ? normalize(items[0]) : null;
  }

  function willEvictOnAdd(id) {
    if (!id || has(id)) return null;
    if (read().length < MAX) return null;
    return oldest();
  }

  function add(id, override) {
    if (!id) return { ok: false, list: list() };
    var before = read();
    var evicted = null;
    if (!has(id) && before.length >= MAX) {
      evicted = oldest();
    }
    var items = before.filter(function (item) {
      return item.id !== id;
    });
    var entry = normalize(
      Object.assign({}, getMeta(id, override), { id: id, addedAt: Date.now() })
    );
    items.push(entry);
    while (items.length > MAX) {
      items.sort(function (a, b) {
        return (a.addedAt || 0) - (b.addedAt || 0);
      });
      items.shift();
    }
    // 明示 ADD のみ送信。ローカル eviction を REMOVE として送ると stale が他端末の race を消す。
    enqueueOp({ op: "add", race_id: id, item: itemToSyncDto(entry) });
    write(items);
    return { ok: true, added: true, list: list(), evicted: evicted };
  }

  function remove(id) {
    var next = read().filter(function (item) {
      return item.id !== id;
    });
    enqueueOp({ op: "remove", race_id: id });
    write(next);
    return { ok: true, added: false, list: list() };
  }

  function toggle(id, override) {
    if (has(id)) return remove(id);
    return add(id, override);
  }

  function confirmReplace(evicted, onConfirm, onCancel) {
    var existing = document.querySelector(".fav-dialog-root");
    if (existing) existing.remove();

    var root = document.createElement("div");
    root.className = "fav-dialog-root";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-labelledby", "favDialogTitle");

    var victim = evicted
      ? escapeHtml(evicted.place) +
        (evicted.name ? "　" + escapeHtml(evicted.name) : "")
      : "いちばん古いレース";

    root.innerHTML =
      '<div class="fav-dialog-backdrop" data-fav-dialog-cancel></div>' +
      '<div class="fav-dialog">' +
      '  <p class="fav-dialog-kicker">お気に入り上限</p>' +
      '  <h2 id="favDialogTitle">4件目を登録しますか？</h2>' +
      '  <p class="fav-dialog-body">お気に入りは最大3件です。<br>登録すると、いちばん古いレースが外れます。</p>' +
      '  <p class="fav-dialog-victim">外れるレース：<strong>' +
      victim +
      "</strong></p>" +
      '  <div class="fav-dialog-actions">' +
      '    <button type="button" class="fav-dialog-cancel" data-fav-dialog-cancel>キャンセル</button>' +
      '    <button type="button" class="fav-dialog-ok" data-fav-dialog-ok>登録する</button>' +
      "  </div>" +
      "</div>";

    function close() {
      root.remove();
      document.body.classList.remove("is-fav-dialog");
    }

    root.addEventListener("click", function (e) {
      if (e.target.closest("[data-fav-dialog-cancel]")) {
        close();
        if (onCancel) onCancel();
      }
      if (e.target.closest("[data-fav-dialog-ok]")) {
        close();
        if (onConfirm) onConfirm();
      }
    });

    document.body.classList.add("is-fav-dialog");
    document.body.appendChild(root);
    var ok = root.querySelector("[data-fav-dialog-ok]");
    if (ok) ok.focus();
  }

  var homeEditMode = false;

  function cardHtml(item, editing) {
    var bgClass = "race-item--bg" + (item.bg || 1);
    var time = item.postTime ? String(item.postTime).trim() : "";
    var metaLine = escapeHtml(item.dateLabel || "");
    if (time) {
      metaLine +=
        (metaLine ? '<span class="fav-meta-sep"> · </span>' : "") +
        '<span class="fav-time">' +
        escapeHtml(time) +
        "出走</span>";
    }
    var removeBtn = editing
      ? '<button type="button" class="fav-card-remove" data-fav-remove="' +
        escapeAttr(item.id) +
        '" aria-label="お気に入りから削除">×</button>'
      : "";

    return (
      '<a class="fav-card ' +
      bgClass +
      (editing ? " is-editing" : "") +
      '" href="race.html?race_id=' +
      encodeURIComponent(item.id) +
      '">' +
      removeBtn +
      '<div class="fav-card-shade" aria-hidden="true"></div>' +
      '<div class="fav-card-text">' +
      '<p class="fav-meta">' +
      metaLine +
      "</p>" +
      '<p class="fav-place">' +
      escapeHtml(item.place) +
      "</p>" +
      '<p class="fav-name">' +
      escapeHtml(item.name) +
      "</p>" +
      "</div>" +
      "</a>"
    );
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  /** race_id / date から YYYY-MM-DD を取る */
  function raceDateIso(item) {
    var d = String((item && item.date) || "").trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(d)) return d;
    var id = String((item && item.id) || "");
    var m = id.match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : "";
  }

  /** 出走時刻を過ぎたお気に入りか（時刻不明なら false＝表示継続） */
  function isFavoriteStarted(item) {
    var date = raceDateIso(item);
    var time = item && item.postTime != null ? String(item.postTime) : "";
    if (
      global.ExpectRaceSearch &&
      typeof ExpectRaceSearch.isPostTimePassed === "function"
    ) {
      return ExpectRaceSearch.isPostTimePassed(date, time);
    }
    var m = time.trim().match(/^(\d{1,2}):(\d{2})/);
    if (!m || !date) return false;
    var hh = String(Number(m[1])).padStart(2, "0");
    var at = Date.parse(date + "T" + hh + ":" + m[2] + ":00+09:00");
    if (!Number.isFinite(at)) return false;
    return Date.now() >= at;
  }

  /** ホーム表示用：出走前のお気に入りのみ */
  function listUpcoming() {
    return list().filter(function (item) {
      return !isFavoriteStarted(item);
    });
  }

  function syncEditButton() {
    var btn = document.getElementById("favEditBtn");
    if (!btn) return;
    var items = listUpcoming();
    btn.disabled = !items.length && !homeEditMode;
    btn.textContent = homeEditMode ? "完了" : "編集";
    btn.setAttribute("aria-pressed", homeEditMode ? "true" : "false");
    btn.classList.toggle("is-active", homeEditMode);
  }

  function renderHome(railEl, emptyEl) {
    if (!railEl) return;
    var items = listUpcoming();
    if (!items.length) {
      homeEditMode = false;
      railEl.classList.remove("is-editing");
      railEl.innerHTML =
        '<div class="fav-empty">レース詳細の ★ からお気に入りに追加できます（最大3件）</div>';
      if (emptyEl) emptyEl.hidden = false;
      syncEditButton();
      return;
    }
    railEl.classList.toggle("is-editing", homeEditMode);
    railEl.innerHTML = items
      .map(function (item) {
        return cardHtml(item, homeEditMode);
      })
      .join("");
    if (emptyEl) emptyEl.hidden = true;
    syncEditButton();
  }

  function bindHomeCardNavigation(rail) {
    if (!rail || rail.dataset.favNavBound === "1") return;
    rail.dataset.favNavBound = "1";

    var gesture = null;
    var TAP_SLOP = 10;

    function clearGesture() {
      gesture = null;
    }

    rail.addEventListener("pointerdown", function (e) {
      if (homeEditMode) return;
      var card = e.target.closest(".fav-card");
      if (!card) return;
      gesture = {
        pointerId: e.pointerId,
        x: e.clientX,
        y: e.clientY,
        card: card,
        moved: false,
      };
    });

    rail.addEventListener("pointermove", function (e) {
      if (!gesture || gesture.pointerId !== e.pointerId) return;
      if (
        Math.abs(e.clientX - gesture.x) > TAP_SLOP ||
        Math.abs(e.clientY - gesture.y) > TAP_SLOP
      ) {
        gesture.moved = true;
      }
    });

    function finishPointer(e) {
      if (!gesture || gesture.pointerId !== e.pointerId) return;
      var card = gesture.card;
      var shouldNavigate = !homeEditMode && !gesture.moved && card;
      clearGesture();
      if (!shouldNavigate) return;
      var href = card.getAttribute("href");
      if (!href) return;
      e.preventDefault();
      global.location.assign(href);
    }

    rail.addEventListener("pointerup", finishPointer);
    rail.addEventListener("pointercancel", clearGesture);
  }

  function bindHomeEdit() {
    var btn = document.getElementById("favEditBtn");
    var rail = document.getElementById("favoritesRail");
    if (!btn || !rail || btn.dataset.favEditBound === "1") return;
    btn.dataset.favEditBound = "1";

    bindHomeCardNavigation(rail);

    btn.addEventListener("click", function () {
      if (!listUpcoming().length && !homeEditMode) return;
      homeEditMode = !homeEditMode;
      renderHome(rail);
      global.dispatchEvent(
        new CustomEvent("expect:favorites-edit-mode", {
          detail: { editing: homeEditMode }
        })
      );
    });

    rail.addEventListener("click", function (e) {
      var removeBtn = e.target.closest("[data-fav-remove]");
      if (removeBtn) {
        e.preventDefault();
        e.stopPropagation();
        var id = removeBtn.getAttribute("data-fav-remove");
        if (!id) return;
        remove(id);
        renderHome(rail);
        global.dispatchEvent(
          new CustomEvent("expect:favorites-changed", {
            detail: { id: id, list: list() }
          })
        );
        return;
      }
      if (homeEditMode) {
        var card = e.target.closest(".fav-card");
        if (card) {
          e.preventDefault();
          e.stopPropagation();
        }
      }
    });

    // 出走時刻経過後にホームのカードを落とす
    setInterval(function () {
      if (!document.getElementById("favoritesRail")) return;
      renderHome(rail);
    }, 60000);

    syncEditButton();
  }

  /** レース一覧・詳細などの ★ 表示を localStorage と同期 */
  function syncStarButtons(root) {
    var scope = root || document;
    scope.querySelectorAll("[data-fav-toggle]").forEach(function (el) {
      var id = el.getAttribute("data-fav-toggle");
      if (!id) return;
      var on = has(id);
      el.classList.toggle("is-active", on);
      el.setAttribute("aria-pressed", on ? "true" : "false");
      el.setAttribute("aria-label", on ? "お気に入り解除" : "お気に入りに追加");
      var t = el.querySelector("[data-fav-label]");
      if (t) t.textContent = on ? "お気に入り済" : "お気に入り";
    });
  }

  function bindButtons(root) {
    var scope = root || document;
    scope.querySelectorAll("[data-fav-toggle]").forEach(function (btn) {
      if (btn.dataset.favBound === "1") return;
      btn.dataset.favBound = "1";

      function applyToggle(id, meta) {
        toggle(id, meta);
        syncStarButtons(document);
        global.dispatchEvent(
          new CustomEvent("expect:favorites-changed", { detail: { id: id, list: list() } })
        );
      }

      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        var id = btn.getAttribute("data-fav-toggle");
        var meta = {
          place: btn.getAttribute("data-fav-place") || undefined,
          name: btn.getAttribute("data-fav-name") || undefined,
          badge: btn.getAttribute("data-fav-badge") || undefined,
          dateLabel: btn.getAttribute("data-fav-date") || undefined,
          postTime: btn.getAttribute("data-fav-time") || undefined,
          honmei: btn.getAttribute("data-fav-honmei") || undefined,
          honmeiNum: btn.getAttribute("data-fav-honmei-num") || undefined,
          confPct: btn.getAttribute("data-fav-conf") || undefined,
          confBand: btn.getAttribute("data-fav-band") || undefined,
        };
        if (meta.honmeiNum != null && meta.honmeiNum !== "") {
          meta.honmeiNum = Number(meta.honmeiNum);
        }
        if (meta.confPct != null && meta.confPct !== "") {
          meta.confPct = Number(meta.confPct);
        }

        // 解除はそのまま
        if (has(id)) {
          applyToggle(id, meta);
          return;
        }

        // 4件目以降は確認ポップアップ
        var evicted = willEvictOnAdd(id);
        if (evicted) {
          confirmReplace(evicted, function () {
            applyToggle(id, meta);
          });
          return;
        }

        applyToggle(id, meta);
      });
    });

    syncStarButtons(scope);
  }

  // ホーム編集削除 ↔ レース★ の双方向同期
  global.addEventListener("expect:favorites-changed", function () {
    syncStarButtons(document);
  });

  // 別タブ／bfcache 復帰時も同期
  global.addEventListener("storage", function (e) {
    if (!e.key) return;
    if (e.key === storageKey() || e.key === KEY || e.key.indexOf(KEY + ":") === 0) {
      syncStarButtons(document);
    }
  });
  global.addEventListener("pageshow", function () {
    syncStarButtons(document);
  });

  global.ExpectFavorites = {
    MAX: MAX,
    CATALOG: CATALOG,
    AI_PARAM_LABELS: AI_PARAM_LABELS,
    list: list,
    listUpcoming: listUpcoming,
    isFavoriteStarted: isFavoriteStarted,
    has: has,
    add: add,
    remove: remove,
    toggle: toggle,
    getMeta: getMeta,
    getAi: getAi,
    willEvictOnAdd: willEvictOnAdd,
    confirmReplace: confirmReplace,
    renderHome: renderHome,
    bindHomeEdit: bindHomeEdit,
    bindButtons: bindButtons,
    syncStarButtons: syncStarButtons,
    exportForSync: exportForSync,
    importFromServer: importFromServer,
    syncNow: syncNow,
    pullFromServer: pullFromServer,
    canSync: canSync,
    pendingOps: function () {
      return _pendingOps.slice();
    },
    bindToCurrentUser: bindToCurrentUser,
    storageKey: storageKey,
    cacheBundles: cacheBundles,
    cacheBundle: cacheBundle,
    isRaceCardSummary: isRaceCardSummary,
    summaryFieldsFromBundle: summaryFieldsFromBundle,
    cardHtml: cardHtml,
  };
})(window);
