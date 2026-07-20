/**
 * お気に入りレース（最大3件・超過時は古いものから削除）
 */
(function (global) {
  "use strict";

  var KEY = "expect_favorites_v1";
  var MAX = 3;

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
      image: "assets/images/race-bg-1.png",
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
      image: "assets/images/race-bg-2.png",
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
      image: "assets/images/race-bg-3.png",
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
      image: "assets/images/race-bg-4.png",
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
      image: "assets/images/race-bg-1.png",
      bg: 1,
      ai: { overall: 79, pedigree: 76, pace: 82, jockey: 75, form: 80, odds: 78 }
    }
  };

  var _bundleCache = {};

  function scoreFromBundle(b) {
    if (!b) return null;
    var c = b.ai_confidence || {};
    if (typeof c.score === "number") {
      return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
    }
    return null;
  }

  function metaFromBundle(b) {
    if (!b || !b.race_id) return null;
    var info = b.race_info || {};
    var d = info.date || "";
    var p = String(d).split("-");
    var dateLabel =
      info.date_label ||
      (p.length === 3 ? Number(p[1]) + "/" + Number(p[2]) : d);
    return {
      id: b.race_id,
      date: d,
      dateLabel: dateLabel,
      place:
        (info.venue || "") + (info.race_no != null ? " " + info.race_no + "R" : ""),
      name: info.class_label || "",
      badge: info.grade || "",
      postTime: info.post_time || "",
      image: "assets/images/race-bg-1.png",
      bg: ((Number(info.race_no) || 1) % 4) + 1,
    };
  }

  function aiFromBundle(b) {
    var overall = scoreFromBundle(b) || 70;
    return {
      overall: overall,
      pedigree: overall,
      pace: overall,
      jockey: overall,
      form: overall,
      odds: overall,
    };
  }

  function cacheBundles(bundles) {
    (bundles || []).forEach(function (b) {
      if (b && b.race_id) _bundleCache[b.race_id] = b;
    });
  }

  function cacheBundle(bundle) {
    if (bundle && bundle.race_id) _bundleCache[bundle.race_id] = bundle;
  }

  var AI_PARAM_LABELS = {
    pedigree: "血統適性",
    pace: "展開予測",
    jockey: "騎手相性",
    form: "近走内容",
    odds: "オッズ妙味"
  };

  function defaultAi() {
    return { overall: 70, pedigree: 70, pace: 70, jockey: 70, form: 70, odds: 70 };
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
    var base = allowCatalog() && CATALOG[id] && CATALOG[id].ai;
    return Object.assign(defaultAi(), base || {});
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
      var list = JSON.parse(store.getItem(KEY) || "[]");
      return Array.isArray(list) ? list : [];
    } catch (e) {
      return [];
    }
  }

  function write(list) {
    var store = storage();
    if (!store) return false;
    try {
      store.setItem(KEY, JSON.stringify(list));
      scheduleServerSync();
      return true;
    } catch (e) {
      return false;
    }
  }

  var _syncTimer = null;
  var _syncing = false;

  /** サーバー同期用 DTO（expect-favorites/1.0） */
  function exportForSync() {
    var items = list().map(function (item) {
      return {
        race_id: item.id,
        place: item.place || null,
        name: item.name || null,
        badge: item.badge || null,
        post_time: item.postTime || null,
        date_label: item.dateLabel || null,
        added_at: item.addedAt || Date.now(),
      };
    });
    return {
      schema_version: "expect-favorites/1.0",
      race_ids: items.map(function (x) {
        return x.race_id;
      }),
      items: items,
      synced_at: null,
    };
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

    var store = storage();
    if (store) {
      try {
        store.setItem(KEY, JSON.stringify(next));
      } catch (e) { /* ignore */ }
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
    if (_syncTimer) clearTimeout(_syncTimer);
    _syncTimer = setTimeout(function () {
      syncNow({ reason: "local-change" }).catch(function () { /* ignore */ });
    }, 600);
  }

  /** ログイン後・変更後の push / pull */
  function syncNow(opts) {
    opts = opts || {};
    if (!canSync()) return Promise.resolve({ ok: false, reason: "guest" });
    if (_syncing) return Promise.resolve({ ok: false, reason: "busy" });
    _syncing = true;

    var push = ExpectApi.Auth.putFavorites(exportForSync())
      .then(function (fav) {
        if (fav) importFromServer(fav, { merge: false });
        return { ok: true, favorites: fav, reason: opts.reason || "sync" };
      })
      .catch(function (err) {
        return { ok: false, error: err };
      })
      .then(function (result) {
        _syncing = false;
        return result;
      });

    return push;
  }

  function pullFromServer() {
    if (!canSync() || !ExpectApi.Auth.getFavorites) {
      return Promise.resolve({ ok: false, reason: "guest" });
    }
    return ExpectApi.Auth.getFavorites()
      .then(function (fav) {
        importFromServer(fav, { merge: true });
        return { ok: true, favorites: fav };
      })
      .catch(function (err) {
        return { ok: false, error: err };
      });
  }

  function normalize(entry) {
    var base = getMeta(entry.id, entry);
    var image = entry.image || base.image || "assets/images/race-bg-1.png";
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
    write(items);
    return { ok: true, added: true, list: list(), evicted: evicted };
  }

  function remove(id) {
    var next = read().filter(function (item) {
      return item.id !== id;
    });
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
    var badge = item.badge
      ? '<span class="fav-badge">' + escapeHtml(item.badge) + "</span>"
      : "";
    var bgClass = "fav-card--bg" + (item.bg || 1);
    var time = item.postTime ? String(item.postTime).trim() : "";
    var metaLine = escapeHtml(item.dateLabel || "");
    if (time) {
      metaLine +=
        (metaLine ? '<span class="fav-meta-sep"> · </span>' : "") +
        '<span class="fav-time">' +
        escapeHtml(time) +
        "発走</span>";
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
      '" style="background-image:url(\'' +
      escapeAttr(item.image) +
      "')\">" +
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
      badge +
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

  function syncEditButton() {
    var btn = document.getElementById("favEditBtn");
    if (!btn) return;
    var items = list();
    btn.disabled = !items.length && !homeEditMode;
    btn.textContent = homeEditMode ? "完了" : "編集";
    btn.setAttribute("aria-pressed", homeEditMode ? "true" : "false");
    btn.classList.toggle("is-active", homeEditMode);
  }

  function renderHome(railEl, emptyEl) {
    if (!railEl) return;
    var items = list();
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

  function bindHomeEdit() {
    var btn = document.getElementById("favEditBtn");
    var rail = document.getElementById("favoritesRail");
    if (!btn || !rail || btn.dataset.favEditBound === "1") return;
    btn.dataset.favEditBound = "1";

    btn.addEventListener("click", function () {
      if (!list().length && !homeEditMode) return;
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
          postTime: btn.getAttribute("data-fav-time") || undefined
        };

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
    if (e.key === KEY) syncStarButtons(document);
  });
  global.addEventListener("pageshow", function () {
    syncStarButtons(document);
  });

  global.ExpectFavorites = {
    MAX: MAX,
    CATALOG: CATALOG,
    AI_PARAM_LABELS: AI_PARAM_LABELS,
    list: list,
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
    cacheBundles: cacheBundles,
    cacheBundle: cacheBundle,
  };
})(window);
