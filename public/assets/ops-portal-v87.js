/**
 * Version8.7 — Operations Dashboard client（閲覧専用）
 * 実効 ADMIN 判定は ExpectRoles（JWT / me.user.role / admin_user_ids / normalizeRole）。
 * Production 書き込み UI なし。
 */
(function () {
  "use strict";

  var SECTIONS = [
    "system",
    "production",
    "research",
    "knowledge",
    "deploy",
    "approval",
    "reports",
  ];
  var NO_DATA = "No Data";
  var PENDING = "Pending";
  var STUB_RE =
    /^(—|-|live|read-only|proxy|empty|pending publish|pipeline status|毎日\s*03:00\s*JST|03:00 JST daily|Cloudflare Pages|AI \/ PI|AI\/PI host|deploy_note_only)$/i;

  function displayValue(raw, fallback) {
    if (raw == null || raw === "") return fallback || NO_DATA;
    if (typeof raw === "object") return fallback || NO_DATA;
    var s = String(raw).trim();
    if (!s || STUB_RE.test(s)) return fallback || NO_DATA;
    return s;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function authHeaders() {
    var h = { Accept: "application/json" };
    try {
      if (window.ExpectAuth && typeof ExpectAuth.getAccessToken === "function") {
        var t = ExpectAuth.getAccessToken();
        if (t) h.Authorization = "Bearer " + t;
      } else if (window.ExpectApi && ExpectApi.Auth && ExpectApi.Auth.getToken) {
        var t2 = ExpectApi.Auth.getToken();
        if (t2) h.Authorization = "Bearer " + t2;
      }
    } catch (e) {
      /* ignore */
    }
    return h;
  }

  function toneClass(tone) {
    if (tone === "ok" || tone === "bad" || tone === "warn" || tone === "muted") {
      return " ops-card--" + tone;
    }
    return " ops-card--muted";
  }

  function renderCard(c) {
    var value = displayValue(c && c.value, NO_DATA);
    return (
      '<article class="ops-card' +
      toneClass(c.tone) +
      '"><h3>' +
      esc(c.label) +
      '</h3><p class="ops-value">' +
      esc(value) +
      "</p>" +
      (c.note ? '<p class="ops-card-note">' + esc(c.note) + "</p>" : "") +
      "</article>"
    );
  }

  function showDenied(msg) {
    var note = document.getElementById("opsGateNote");
    var denied = document.getElementById("opsDenied");
    var main = document.getElementById("opsMain");
    if (note) note.hidden = true;
    if (main) main.hidden = true;
    if (denied) {
      denied.hidden = false;
      var title = denied.querySelector(".expect-state__title");
      var body = denied.querySelector(".expect-state__msg");
      if (title) title.textContent = "アクセス不可";
      if (body) {
        body.textContent =
          msg ||
          "Operations Dashboard は role=ADMIN のみ閲覧できます。一般ユーザーはアクセスできません。";
      }
    }
  }

  function showMain() {
    var note = document.getElementById("opsGateNote");
    var denied = document.getElementById("opsDenied");
    var main = document.getElementById("opsMain");
    if (note) note.hidden = true;
    if (denied) denied.hidden = true;
    if (main) main.hidden = false;
  }

  function setActiveSection(id) {
    SECTIONS.forEach(function (key) {
      var pane = document.getElementById("opsPane-" + key);
      var tab = document.querySelector('[data-ops-section="' + key + '"]');
      var on = key === id;
      if (pane) pane.hidden = !on;
      if (tab) {
        tab.classList.toggle("is-active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
      }
    });
  }

  function bindNav() {
    var nav = document.getElementById("opsPortalNav");
    if (!nav) return;
    nav.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-ops-section]");
      if (!btn) return;
      ev.preventDefault();
      setActiveSection(btn.getAttribute("data-ops-section"));
    });
  }

  function paintPortal(data) {
    var sections = (data && data.sections) || {};
    var meta = document.getElementById("opsPortalMeta");
    if (meta) {
      meta.textContent =
        "Version8.8 · Approval 書き込み可 · baseline " +
        ((data && data.baseline_lock) || "Version8.5.1") +
        " · Production 自動適用禁止（Deploy Note → Human Deploy）";
    }
    SECTIONS.forEach(function (key) {
      var sec = sections[key];
      var grid = document.getElementById("opsGrid-" + key);
      var note = document.getElementById("opsNote-" + key);
      if (!grid) return;
      if (!sec || !sec.cards || !sec.cards.length) {
        grid.innerHTML = renderCard({
          label: key,
          value: NO_DATA,
          tone: "muted",
        });
        return;
      }
      grid.innerHTML = sec.cards.map(renderCard).join("");
      if (note) {
        note.textContent = sec.note || "";
        note.hidden = !sec.note;
      }
    });
  }

  function mergeLiveHints(portal, extras) {
    if (!portal || !portal.sections) return portal;
    var sys = portal.sections.system;
    var prod = portal.sections.production;
    var research = portal.sections.research;

    if (extras.ra && sys && sys.cards) {
      sys.cards = sys.cards.map(function (c) {
        if (c.label !== "ResultAutomation") return c;
        var run = extras.ra.run || {};
        var val = run.status || extras.ra.status;
        if (val == null || val === "") {
          return Object.assign({}, c, { value: NO_DATA, tone: "muted" });
        }
        if (typeof val === "object") {
          return Object.assign({}, c, { value: NO_DATA, tone: "muted" });
        }
        return Object.assign({}, c, {
          value: String(val),
          tone: extras.ra.ok === false || String(val) === "FAILED" ? "bad" : "ok",
        });
      });
    } else if (sys && sys.cards) {
      sys.cards = sys.cards.map(function (c) {
        if (c.label !== "ResultAutomation") return c;
        return Object.assign({}, c, { value: NO_DATA, tone: "muted" });
      });
    }

    if (extras.sched && research && research.cards) {
      var d = extras.sched;
      research.cards = research.cards.map(function (c) {
        if (c.label === "Current Week" && d.week_id) {
          return Object.assign({}, c, { value: d.week_id, tone: "ok" });
        }
        if (c.label === "Current Phase" && d.current_phase) {
          return Object.assign({}, c, { value: d.current_phase, tone: "ok" });
        }
        if (c.label === "Next Run" && d.next_run) {
          return Object.assign({}, c, { value: d.next_run, tone: "ok" });
        }
        if (c.label === "Recovery" && d.recovery != null) {
          var recVal =
            typeof d.recovery === "boolean"
              ? d.recovery
                ? "active"
                : "idle"
              : String(d.recovery);
          return Object.assign({}, c, {
            value: recVal,
            tone: recVal === "active" || d.recovery === true ? "warn" : "ok",
          });
        }
        return c;
      });
      if (sys && sys.cards) {
        sys.cards = sys.cards.map(function (c) {
          if (c.label !== "Research Scheduler") return c;
          if (!d.current_phase) {
            return Object.assign({}, c, {
              value: c.value && c.value !== NO_DATA ? c.value : NO_DATA,
              tone: "muted",
            });
          }
          return Object.assign({}, c, {
            value: d.current_phase,
            tone: "ok",
          });
        });
      }
    }

    if (extras.v71 && prod && prod.cards) {
      var v = extras.v71;
      prod.cards = prod.cards.map(function (c) {
        if (c.label === "Maintenance") return c;
        var key = String(c.label || "").toLowerCase();
        var src =
          v[key] ||
          v[c.label] ||
          (v.services && (v.services[key] || v.services[c.label]));
        if (src == null) {
          return Object.assign({}, c, { value: NO_DATA, tone: "muted" });
        }
        var val =
          typeof src === "object"
            ? src.status != null
              ? src.status
              : src.state != null
                ? src.state
                : typeof src.ok === "boolean"
                  ? String(src.ok)
                  : null
            : src;
        if (val == null || val === "" || typeof val === "object") {
          return Object.assign({}, c, { value: NO_DATA, tone: "muted" });
        }
        return Object.assign({}, c, {
          value: String(val),
          tone: val === false || val === "bad" ? "bad" : "ok",
        });
      });
    } else if (prod && prod.cards) {
      prod.cards = prod.cards.map(function (c) {
        if (c.label === "Maintenance") return c;
        return Object.assign({}, c, { value: NO_DATA, tone: "muted" });
      });
    }

    return portal;
  }

  function formatRemaining(item) {
    if (item.remaining_days != null) return "残り " + item.remaining_days + " 日";
    if (item.remaining_ms == null) return NO_DATA;
    var d = Math.max(0, Math.ceil(Number(item.remaining_ms) / 86400000));
    return "残り " + d + " 日";
  }

  function paintApprovals(data) {
    var host = document.getElementById("opsApprovalList");
    var note = document.getElementById("opsNote-approval");
    var grid = document.getElementById("opsGrid-approval");
    if (!host && !grid) return;
    var items = (data && data.items) || [];
    var pending = items.filter(function (x) {
      return x && x.status === "pending";
    });
    var counts = {
      pending:
        data && data.pending_count != null
          ? data.pending_count
          : data && data.pending != null
            ? data.pending
            : pending.length,
      approved:
        data && data.approved_count != null
          ? data.approved_count
          : data && data.approved != null
            ? data.approved
            : items.filter(function (x) {
                return x && x.status === "approved";
              }).length,
      rejected:
        data && data.rejected_count != null
          ? data.rejected_count
          : data && data.rejected != null
            ? data.rejected
            : items.filter(function (x) {
                return x && x.status === "rejected" && !x.auto;
              }).length,
      timeout:
        data && data.timeout_count != null
          ? data.timeout_count
          : data && data.timeout != null
            ? data.timeout
            : items.filter(function (x) {
                return (
                  x &&
                  x.status === "rejected" &&
                  (x.auto === true || x.reason === "approval_timeout")
                );
              }).length,
    };
    if (grid) {
      grid.innerHTML = [
        { label: "Pending", value: String(counts.pending), tone: "ok" },
        { label: "Approved", value: String(counts.approved), tone: "ok" },
        { label: "Rejected", value: String(counts.rejected), tone: "ok" },
        { label: "Timeout", value: String(counts.timeout), tone: "ok" },
      ]
        .map(renderCard)
        .join("");
    }
    if (note) {
      note.textContent =
        "Queue pending=" +
        counts.pending +
        " · Boundary: Accept → RC → Deploy Note → Human Deploy";
      note.hidden = false;
    }
    if (!host) return;
    if (!pending.length) {
      host.innerHTML =
        '<article class="ops-card ops-card--muted"><h3>承認待ち</h3><p class="ops-value">' +
        esc(NO_DATA) +
        "</p></article>";
      return;
    }
    host.innerHTML = pending
      .map(function (item) {
        return (
          '<article class="ops-card ops-card--warn ops-approval-card" data-approval-id="' +
          esc(item.approval_id) +
          '">' +
          "<h3>" +
          esc(item.approval_id) +
          "</h3>" +
          '<p class="ops-value">' +
          esc(item.week_id || NO_DATA) +
          "</p>" +
          '<p class="ops-card-note">expires_at: ' +
          esc(item.expires_at || NO_DATA) +
          " · " +
          esc(formatRemaining(item)) +
          "</p>" +
          '<p class="ops-card-note">proposals: ' +
          esc((item.proposal_ids || []).join(", ") || NO_DATA) +
          "</p>" +
          '<div class="ops-approval-actions">' +
          '<button type="button" class="ops-refresh-btn" data-approval-action="approve">Approve</button> ' +
          '<button type="button" class="ops-refresh-btn" data-approval-action="reject">Reject</button>' +
          "</div></article>"
        );
      })
      .join("");
  }

  function postApproval(id, action, body) {
    return fetch("/api/ops/approvals/" + encodeURIComponent(id) + "/" + action, {
      method: "POST",
      cache: "no-store",
      credentials: "same-origin",
      headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json().then(function (body) {
        return { ok: r.ok, status: r.status, body: body };
      });
    });
  }

  function bindApprovalActions() {
    var host =
      document.getElementById("opsApprovalList") ||
      document.getElementById("opsGrid-approval");
    if (!host || host._approvalBound) return;
    host._approvalBound = true;
    host.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-approval-action]");
      if (!btn) return;
      var card = btn.closest("[data-approval-id]");
      if (!card) return;
      var id = card.getAttribute("data-approval-id");
      var action = btn.getAttribute("data-approval-action");
      if (action === "approve") {
        if (!window.confirm("承認しますか？ Production には反映せず Deploy Note のみ作成します。")) {
          return;
        }
        postApproval(id, "approve", {}).then(function () {
          return loadApprovals();
        });
        return;
      }
      if (action === "reject") {
        var reason = window.prompt("却下理由（Knowledge Base に記録）");
        if (!reason || !String(reason).trim()) return;
        postApproval(id, "reject", { reason: String(reason).trim() }).then(function () {
          return loadApprovals();
        });
      }
    });
  }

  function loadApprovals() {
    return fetchJson("/api/ops/approvals")
      .then(function (res) {
        var data = unwrap(res);
        paintApprovals(data || { items: [] });
        bindApprovalActions();
      })
      .catch(function () {
        paintApprovals({ items: [] });
      });
  }

  function fetchJson(url) {
    return fetch(url, {
      cache: "no-store",
      credentials: "same-origin",
      headers: authHeaders(),
    }).then(function (r) {
      return r.json().then(function (body) {
        return { ok: r.ok, status: r.status, body: body };
      });
    });
  }

  function unwrap(res) {
    if (!res || !res.ok || !res.body) return null;
    if (res.body.ok === false) return null;
    return res.body.data != null ? res.body.data : res.body;
  }

  function loadAll() {
    var statusEl = document.getElementById("opsLoadStatus");
    if (statusEl) statusEl.textContent = "読み込み中…";

    return Promise.all([
      fetchJson("/api/ops/portal"),
      fetchJson("/api/ops/research-scheduler").catch(function () {
        return null;
      }),
      fetchJson("/api/ops/result-automation").catch(function () {
        return null;
      }),
      fetchJson("/api/ops/v71-metrics").catch(function () {
        return null;
      }),
    ]).then(function (parts) {
      var portalRes = parts[0];
      if (!portalRes || portalRes.status === 401) {
        showDenied("ログインが必要です。");
        return;
      }
      if (portalRes.status === 403 || (portalRes.body && portalRes.body.ok === false)) {
        showDenied(
          (portalRes.body &&
            portalRes.body.error &&
            portalRes.body.error.message) ||
            "role=ADMIN のみ閲覧できます。"
        );
        return;
      }
      var portal = unwrap(portalRes);
      if (!portal) {
        showDenied("ポータルデータの取得に失敗しました。");
        return;
      }
      portal = mergeLiveHints(portal, {
        sched: unwrap(parts[1]),
        ra: unwrap(parts[2]),
        v71: unwrap(parts[3]),
      });
      showMain();
      paintPortal(portal);
      loadApprovals();
      if (statusEl) {
        statusEl.textContent =
          "更新: " +
          new Date().toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" }) +
          " JST";
      }
    });
  }

  function resolveAdminAccess() {
    var roles = window.ExpectRoles;
    var authMe =
      window.ExpectApi && ExpectApi.Auth && ExpectApi.Auth.me
        ? ExpectApi.Auth.me().catch(function () {
            return null;
          })
        : Promise.resolve(null);
    var userMe =
      window.ExpectApi && ExpectApi.User && ExpectApi.User.me
        ? ExpectApi.User.me().catch(function () {
            return null;
          })
        : Promise.resolve(null);

    return Promise.all([authMe, userMe]).then(function (parts) {
      var authRaw = parts[0];
      var userRaw = parts[1];
      var me =
        (roles && roles.normalizeMe(userRaw)) ||
        (roles && roles.normalizeMe(authRaw)) ||
        null;

      if (!me && !authRaw && !userRaw) {
        return { allow: false, reason: "login" };
      }

      if (roles) {
        return roles.isOpsPortalAdmin(me || authRaw || userRaw).then(function (ok) {
          return { allow: !!ok, me: me, reason: ok ? "admin" : "forbidden" };
        });
      }

      // fallback（ExpectRoles 未読込）
      var role = String(
        (me && me.role) ||
          (authRaw && authRaw.user && authRaw.user.role) ||
          (userRaw && userRaw.role) ||
          ""
      ).toUpperCase();
      if (role === "ADMIN" || role === "ADMINISTRATOR" || role === "ROOT") {
        return { allow: true, me: me, reason: "admin" };
      }
      return { allow: false, me: me, reason: "forbidden" };
    });
  }

  function boot() {
    bindNav();
    setActiveSection("system");

    var refresh = document.getElementById("opsPortalRefreshBtn");
    if (refresh) {
      refresh.onclick = function () {
        loadAll();
      };
    }

    resolveAdminAccess().then(function (gate) {
      if (!gate || gate.reason === "login") {
        showDenied("ログインが必要です。");
        return;
      }
      if (!gate.allow) {
        showDenied(
          "Operations Dashboard は role=ADMIN のみ閲覧できます。一般ユーザーはアクセスできません。"
        );
        return;
      }
      loadAll();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
