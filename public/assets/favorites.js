/**
 * お気に入りレース（最大3件・超過時は古いものから削除）
 */
(function (global) {
  "use strict";

  var KEY = "expect_favorites_v1";
  var MAX = 3;

  var CATALOG = {
    "20260719_tokyo_11": {
      id: "20260719_tokyo_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "東京 11R",
      name: "函館記念",
      badge: "GIII",
      image: "assets/images/race-bg-1.png",
      bg: 1
    },
    "20260719_hanshin_11": {
      id: "20260719_hanshin_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "阪神 11R",
      name: "メインレース",
      badge: "GIII",
      image: "assets/images/race-bg-2.png",
      bg: 2
    },
    "20260719_fukushima_11": {
      id: "20260719_fukushima_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "福島 11R",
      name: "ラジオNIKKEI賞",
      badge: "GIII",
      image: "assets/images/race-bg-3.png",
      bg: 3
    },
    "20260719_hakodate_11": {
      id: "20260719_hakodate_11",
      date: "2026-07-19",
      dateLabel: "7/19（土）",
      place: "函館 11R",
      name: "函館2歳S",
      badge: "GIII",
      image: "assets/images/race-bg-4.png",
      bg: 4
    },
    "20260720_nakayama_11": {
      id: "20260720_nakayama_11",
      date: "2026-07-20",
      dateLabel: "7/20（日）",
      place: "中山 11R",
      name: "中山ダート戦",
      badge: "L",
      image: "assets/images/race-bg-1.png",
      bg: 1
    }
  };

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
      return true;
    } catch (e) {
      return false;
    }
  }

  function normalize(entry) {
    var base = CATALOG[entry.id] || {};
    var image = entry.image || base.image || "assets/images/race-bg-1.png";
    var bg = entry.bg || base.bg || 1;
    // 古い保存データに旧画像が残っていても race-bg に寄せる
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
      image: image,
      bg: bg,
      addedAt: entry.addedAt || Date.now()
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
    var base = CATALOG[id] ? Object.assign({}, CATALOG[id]) : { id: id };
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

  function cardHtml(item) {
    var badge = item.badge
      ? '<span class="fav-badge">' + escapeHtml(item.badge) + "</span>"
      : "";
    var bgClass = "fav-card--bg" + (item.bg || 1);
    return (
      '<a class="fav-card ' +
      bgClass +
      '" href="race.html?race_id=' +
      encodeURIComponent(item.id) +
      '" style="background-image:url(\'' +
      escapeAttr(item.image) +
      "')\">" +
      '<div class="fav-card-shade" aria-hidden="true"></div>' +
      '<div class="fav-card-text">' +
      '<p class="fav-meta">' +
      escapeHtml(item.dateLabel) +
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

  function renderHome(railEl, emptyEl) {
    if (!railEl) return;
    var items = list();
    if (!items.length) {
      railEl.innerHTML =
        '<div class="fav-empty">レース詳細の ★ からお気に入りに追加できます（最大3件）</div>';
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    railEl.innerHTML = items.map(cardHtml).join("");
    if (emptyEl) emptyEl.hidden = true;
  }

  function bindButtons(root) {
    var scope = root || document;
    scope.querySelectorAll("[data-fav-toggle]").forEach(function (btn) {
      if (btn.dataset.favBound === "1") return;
      btn.dataset.favBound = "1";

      function sync() {
        var id = btn.getAttribute("data-fav-toggle");
        var on = has(id);
        btn.classList.toggle("is-active", on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
        var label = on ? "お気に入り解除" : "お気に入りに追加";
        btn.setAttribute("aria-label", label);
        var text = btn.querySelector("[data-fav-label]");
        if (text) text.textContent = on ? "お気に入り済" : "お気に入り";
      }

      function syncAll(id) {
        document.querySelectorAll('[data-fav-toggle="' + id + '"]').forEach(function (el) {
          var on = has(id);
          el.classList.toggle("is-active", on);
          el.setAttribute("aria-pressed", on ? "true" : "false");
          el.setAttribute("aria-label", on ? "お気に入り解除" : "お気に入りに追加");
          var t = el.querySelector("[data-fav-label]");
          if (t) t.textContent = on ? "お気に入り済" : "お気に入り";
        });
      }

      function applyToggle(id, meta) {
        toggle(id, meta);
        syncAll(id);
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
          dateLabel: btn.getAttribute("data-fav-date") || undefined
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

      sync();
    });
  }

  global.ExpectFavorites = {
    MAX: MAX,
    CATALOG: CATALOG,
    list: list,
    has: has,
    add: add,
    remove: remove,
    toggle: toggle,
    getMeta: getMeta,
    willEvictOnAdd: willEvictOnAdd,
    confirmReplace: confirmReplace,
    renderHome: renderHome,
    bindButtons: bindButtons
  };
})(window);
