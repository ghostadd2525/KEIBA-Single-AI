/**
 * Version8.9 — Operations Console client
 * Approval Center first. Real data / No Data / Pending only.
 * Boundary: Research → Approval → Deploy Note → Human Deploy.
 */
(function () {
  "use strict";

  var SECTIONS = [
    "approval",
    "monitor",
    "timeline",
    "research",
    "knowledge",
    "deploy",
    "reports",
    "history",
    "evidence",
    "download",
    "audit",
    "system",
  ];
  var NO_DATA = "No Data";
  var PENDING = "Pending";
  var STUB_RE =
    /^(—|-|live|read-only|proxy|empty|pending publish|pipeline status|毎日\s*03:00\s*JST|03:00 JST daily|Cloudflare Pages|AI \/ PI|AI\/PI host|deploy_note_only)$/i;

  var state = {
    console: null,
    approvals: null,
    monitor: null,
    history: null,
    benchmarkStrategy: null,
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function displayValue(raw) {
    if (raw == null || raw === "") return NO_DATA;
    if (typeof raw === "object") return NO_DATA;
    var s = String(raw).trim();
    if (!s || STUB_RE.test(s)) return NO_DATA;
    return s;
  }

  function authHeaders() {
    var h = { Accept: "application/json" };
    try {
      if (window.ExpectAuth && ExpectAuth.getAccessToken) {
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

  function toneClass(tone) {
    if (tone === "ok" || tone === "bad" || tone === "warn" || tone === "muted") {
      return " ops-card--" + tone;
    }
    return " ops-card--muted";
  }

  function monitorTone(status) {
    if (status === "Healthy") return "ok";
    if (status === "Failed") return "bad";
    if (status === "Pending") return "warn";
    return "muted";
  }

  function renderCard(opts) {
    var value = displayValue(opts.value);
    var evidence = opts.evidence || [];
    var links = evidence
      .map(function (e) {
        return (
          '<a class="ops-evidence-link" href="' +
          esc(e.href) +
          '" target="_blank" rel="noopener">' +
          esc(e.label || "Evidence") +
          "</a>"
        );
      })
      .join(" ");
    var actions = "";
    if (opts.jsonPath || opts.apiPath) {
      actions +=
        '<button type="button" class="ops-mini-btn" data-json-view="' +
        esc(opts.jsonPath || "") +
        '" data-api-view="' +
        esc(opts.apiPath || "") +
        '" data-json-title="' +
        esc(opts.label || "JSON") +
        '">View JSON</button>';
    }
    return (
      '<article class="ops-card' +
      toneClass(opts.tone) +
      '"><h3>' +
      esc(opts.label) +
      '</h3><p class="ops-value">' +
      esc(value) +
      "</p>" +
      (opts.note ? '<p class="ops-card-note">' + esc(opts.note) + "</p>" : "") +
      (links ? '<p class="ops-card-note">' + links + "</p>" : "") +
      (actions ? '<p class="ops-card-actions">' + actions + "</p>" : "") +
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
      var body = denied.querySelector(".expect-state__msg");
      if (body && msg) body.textContent = msg;
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

  function remainingDays(item) {
    if (item.remaining_days != null) return Number(item.remaining_days);
    if (!item.expires_at) return null;
    var ms = new Date(item.expires_at).getTime() - Date.now();
    if (isNaN(ms)) return null;
    return Math.ceil(ms / 86400000);
  }

  function statusLabel(item) {
    if (!item) return NO_DATA;
    if (item.status === "rejected" && (item.auto === true || item.reason === "approval_timeout")) {
      return "Timeout";
    }
    var s = String(item.status || "").toLowerCase();
    if (s === "pending") return "Pending";
    if (s === "approved") return "Approved";
    if (s === "rejected") return "Rejected";
    if (s === "timeout") return "Timeout";
    return item.status ? String(item.status) : NO_DATA;
  }

  function openDialog(title, body, actionsHtml) {
    var dlg = document.getElementById("opsDialog");
    var t = document.getElementById("opsDialogTitle");
    var b = document.getElementById("opsDialogBody");
    var a = document.getElementById("opsDialogActions");
    if (!dlg) return;
    if (t) t.textContent = title || "Detail";
    if (b) {
      b.textContent =
        typeof body === "string" ? body : JSON.stringify(body, null, 2);
    }
    if (a) a.innerHTML = actionsHtml || "";
    if (typeof dlg.showModal === "function") dlg.showModal();
  }

  function evidenceForWeek(weekId, kinds) {
    var idx = state.console && state.console.publish && state.console.publish.evidence;
    var items = (idx && idx.items) || [];
    return items
      .filter(function (e) {
        if (weekId && e.week_id !== weekId) return false;
        if (!kinds || !kinds.length) return true;
        return kinds.some(function (k) {
          return e.kind === k || (e.label && e.label.indexOf(k) >= 0);
        });
      })
      .map(function (e) {
        return { label: e.label || e.kind, href: e.public_path };
      });
  }

  function paintApprovalCenter() {
    var grid = document.getElementById("opsGrid-approval");
    var tbody = document.getElementById("opsApprovalTbody");
    var note = document.getElementById("opsNote-approval");
    var data = state.approvals || { items: [] };
    var items = data.items || [];
    var counts = {
      pending: 0,
      approved: 0,
      rejected: 0,
      timeout: 0,
    };
    items.forEach(function (it) {
      var lab = statusLabel(it);
      if (lab === "Pending") counts.pending += 1;
      else if (lab === "Approved") counts.approved += 1;
      else if (lab === "Timeout") counts.timeout += 1;
      else if (lab === "Rejected") counts.rejected += 1;
    });
    if (data.pending_count != null) counts.pending = data.pending_count;
    if (data.approved_count != null) counts.approved = data.approved_count;
    if (data.rejected_count != null) counts.rejected = data.rejected_count;
    if (data.timeout_count != null) counts.timeout = data.timeout_count;

    if (grid) {
      grid.innerHTML = [
        { label: "Pending", value: String(counts.pending), tone: "warn" },
        { label: "Approved", value: String(counts.approved), tone: "ok" },
        { label: "Rejected", value: String(counts.rejected), tone: "muted" },
        { label: "Timeout", value: String(counts.timeout), tone: "bad" },
      ]
        .map(function (c) {
          return renderCard({
            label: c.label,
            value: c.value,
            tone: c.tone,
            jsonPath: "/ops-data/approval-queue.json",
            apiPath: "/api/ops/approvals",
          });
        })
        .join("");
    }
    if (note) {
      note.textContent =
        "Queue items=" +
        items.length +
        " · Timeout → status=Rejected reason=approval_timeout auto=true";
    }
    if (!tbody) return;
    if (!items.length) {
      tbody.innerHTML =
        '<tr><td colspan="9">' + esc(NO_DATA) + "</td></tr>";
      return;
    }
    tbody.innerHTML = items
      .map(function (item) {
        var proposals = (item.proposal_ids || []).join(", ") || item.approval_id || NO_DATA;
        var rem = remainingDays(item);
        var remText = rem == null ? NO_DATA : rem + " 日";
        var st = statusLabel(item);
        var timeoutNote =
          st === "Timeout"
            ? " reason=approval_timeout auto=true"
            : "";
        var actions =
          st === "Pending"
            ? '<button type="button" class="ops-mini-btn" data-approval-action="approve" data-approval-id="' +
              esc(item.approval_id) +
              '">Approve</button> ' +
              '<button type="button" class="ops-mini-btn" data-approval-action="reject" data-approval-id="' +
              esc(item.approval_id) +
              '">Reject</button> '
            : "";
        actions +=
          '<button type="button" class="ops-mini-btn" data-approval-detail="' +
          esc(item.approval_id) +
          '">Decision</button>';
        return (
          "<tr>" +
          "<td>" +
          esc(proposals) +
          "</td><td>" +
          esc(item.baseline_lock || NO_DATA) +
          "</td><td>" +
          esc(item.week_id || NO_DATA) +
          "</td><td>" +
          esc(item.decision || NO_DATA) +
          "</td><td>" +
          esc(item.created_at || NO_DATA) +
          "</td><td>" +
          esc(item.expires_at || NO_DATA) +
          "</td><td>" +
          esc(remText) +
          "</td><td>" +
          esc(st) +
          esc(timeoutNote) +
          "</td><td>" +
          actions +
          "</td></tr>"
        );
      })
      .join("");
  }

  function paintMonitor() {
    var grid = document.getElementById("opsGrid-monitor");
    if (!grid) return;
    var targets = (state.monitor && state.monitor.targets) || {};
    var order = ["Pages", "PI", "AI", "EC2", "ResultAutomation", "ResearchScheduler", "EvidenceCollector"];
    grid.innerHTML = order
      .map(function (key) {
        var t = targets[key] || {};
        var noteParts = [];
        if (t.health != null) noteParts.push("health=" + t.health);
        if (t.latency_ms != null) noteParts.push("latency=" + t.latency_ms + "ms");
        if (t.last_update) noteParts.push("updated=" + t.last_update);
        if (key === "EvidenceCollector") {
          if (t.success_rate != null) noteParts.push("success=" + t.success_rate);
          if (t.missing_rate != null) noteParts.push("missing=" + t.missing_rate);
          if (t.retry_count != null) noteParts.push("retries=" + t.retry_count);
        }
        return renderCard({
          label:
            key === "ResearchScheduler"
              ? "Research Scheduler"
              : key === "EvidenceCollector"
                ? "Evidence Collector"
                : key,
          value: t.status || NO_DATA,
          tone: monitorTone(t.status),
          note: noteParts.join(" · ") || null,
          apiPath:
            key === "EvidenceCollector"
              ? "/api/ops/evidence-collector"
              : "/api/ops/monitor-live",
          jsonPath:
            key === "ResearchScheduler" || key === "Research Scheduler"
              ? "/ops-data/research-scheduler.json"
              : key === "EvidenceCollector"
                ? "/ops-data/evidence-collector.json"
                : null,
        });
      })
      .join("");
  }

  function paintTimeline() {
    var host = document.getElementById("opsTimeline");
    var note = document.getElementById("opsNote-timeline");
    var tl =
      state.console && state.console.publish && state.console.publish.timeline;
    if (note) {
      note.hidden = false;
      note.textContent = tl
        ? "week=" +
          displayValue(tl.week_id) +
          " · next=" +
          displayValue(tl.next_run) +
          " · last=" +
          displayValue(tl.last_run)
        : NO_DATA;
    }
    if (!host) return;
    var steps = (tl && tl.steps) || [];
    if (!steps.length) {
      host.innerHTML = "<li>" + esc(NO_DATA) + "</li>";
      return;
    }
    host.innerHTML = steps
      .map(function (s) {
        return (
          '<li class="ops-timeline-step ops-timeline--' +
          esc(String(s.result || "Skip").toLowerCase()) +
          '"><strong>' +
          esc(s.label || s.key) +
          "</strong>" +
          '<span class="ops-timeline-meta">start=' +
          esc(s.started_at || NO_DATA) +
          " · end=" +
          esc(s.ended_at || NO_DATA) +
          " · duration=" +
          esc(s.duration_ms != null ? s.duration_ms + "ms" : NO_DATA) +
          " · " +
          esc(s.result || "Skip") +
          "</span></li>"
        );
      })
      .join("");
  }

  function snapCards(section) {
    var snap =
      (state.console && state.console.publish && state.console.publish.portal_snapshot) ||
      {};
    var week = (snap.research && snap.research.week_id) || null;
    if (section === "research") {
      var r = snap.research || {};
      return [
        {
          label: "Current Week",
          value: r.week_id,
          evidence: evidenceForWeek(week, ["decision", "weekly-ops-report"]),
          jsonPath: "/ops-data/portal-snapshot.json",
          apiPath: "/api/ops/portal",
        },
        {
          label: "Current Phase",
          value: r.current_phase,
          evidence: evidenceForWeek(week, ["proposal-validation", "ranked-run"]),
          jsonPath: "/ops-data/research-scheduler.json",
        },
        {
          label: "Next Run",
          value: r.next_run,
          jsonPath: "/ops-data/research-scheduler.json",
          apiPath: "/api/ops/research-scheduler",
        },
        {
          label: "Recovery",
          value: r.recovery,
          jsonPath: "/ops-data/research-scheduler.json",
        },
        {
          label: "Decision",
          value: r.decision,
          evidence: evidenceForWeek(week, ["decision"]),
          jsonPath: week ? "/ops-data/artifacts/" + week + "/decision.json" : null,
        },
        {
          label: "Validation",
          value: week ? "Open Evidence" : null,
          evidence: evidenceForWeek(week, ["proposal-validation"]),
          jsonPath: week
            ? "/ops-data/artifacts/" + week + "/proposal-validation.json"
            : null,
        },
        {
          label: "Canary",
          value: week ? "Open Evidence" : null,
          evidence: evidenceForWeek(week, ["ranked-run"]),
        },
        {
          label: "285R",
          value: week ? "Open Evidence" : null,
          evidence: evidenceForWeek(week, ["baseline-285r"]),
        },
      ];
    }
    if (section === "knowledge") {
      var k = snap.knowledge || {};
      return [
        {
          label: "Knowledge Score",
          value: k.knowledge_score,
          evidence: [{ label: "knowledge.json", href: "/ops-data/knowledge.json" }],
          jsonPath: "/ops-data/knowledge.json",
        },
        {
          label: "Accepted Patterns",
          value: k.accepted_patterns,
          evidence: [
            {
              label: "accepted_patterns.json",
              href: "/ops-data/artifacts/knowledge/accepted_patterns.json",
            },
          ],
        },
        {
          label: "Rejected Patterns",
          value: k.rejected_patterns,
          evidence: [
            {
              label: "rejected_patterns.json",
              href: "/ops-data/artifacts/knowledge/rejected_patterns.json",
            },
          ],
        },
        {
          label: "Governance",
          value: k.governance,
          jsonPath: "/ops-data/knowledge.json",
        },
      ];
    }
    if (section === "deploy") {
      var d = snap.deploy || {};
      return [
        {
          label: "Deploy Queue",
          value: d.deploy_queue,
          jsonPath: "/ops-data/deploy.json",
        },
        {
          label: "Accept済み候補",
          value: d.accepted_candidates,
          jsonPath: "/ops-data/deploy.json",
        },
        {
          label: "deploy-note",
          value: d.deploy_note,
          evidence: evidenceForWeek(week, ["deploy-note"]),
          jsonPath: "/ops-data/deploy.json",
          note: "Human Deploy required · production_auto_apply=false",
        },
      ];
    }
    if (section === "reports") {
      var rp = snap.reports || {};
      return [
        {
          label: "Weekly Report",
          value: rp.weekly_report,
          evidence: evidenceForWeek(week || rp.weekly_report, ["weekly-ops-report"]),
          jsonPath: "/ops-data/reports.json",
        },
        {
          label: "Baseline Health Check",
          value: rp.baseline_health_check,
          evidence: evidenceForWeek(week || rp.weekly_report, ["baseline-285r"]),
        },
        {
          label: "Boundary Audit",
          value: rp.boundary_audit,
          evidence: evidenceForWeek(week || rp.weekly_report, ["boundary-audit", "weekly-ops-report"]),
        },
        {
          label: "Incident Report",
          value: rp.incident_report,
          evidence: evidenceForWeek(week || rp.weekly_report, ["incident-report"]),
        },
      ];
    }
    return [];
  }

  function paintSectionGrid(id) {
    var grid = document.getElementById("opsGrid-" + id);
    if (!grid) return;
    var cards = snapCards(id);
    if (!cards.length) {
      grid.innerHTML = renderCard({ label: id, value: NO_DATA, tone: "muted" });
      return;
    }
    grid.innerHTML = cards
      .map(function (c) {
        var tone = "ok";
        var v = c.value;
        if (v == null || v === "") {
          if (c.label === "Baseline Health Check" || c.label === "Boundary Audit") {
            // Pending only when weekly report exists but field pending
            var snap =
              (state.console &&
                state.console.publish &&
                state.console.publish.portal_snapshot) ||
              {};
            v =
              snap.reports && snap.reports.weekly_report
                ? c.label.indexOf("Boundary") >= 0 || c.label.indexOf("Baseline") >= 0
                  ? PENDING
                  : NO_DATA
                : NO_DATA;
            if (String(c.value || "").toLowerCase() === "pending") v = PENDING;
          } else {
            v = NO_DATA;
          }
          tone = "muted";
        } else if (String(v).toLowerCase() === "pending") {
          tone = "muted";
        }
        return renderCard({
          label: c.label,
          value: v,
          tone: tone,
          note: c.note,
          evidence: c.evidence,
          jsonPath: c.jsonPath,
          apiPath: c.apiPath,
        });
      })
      .join("");
  }

  function paintSystem() {
    var grid = document.getElementById("opsGrid-system");
    if (!grid) return;
    var mon = (state.monitor && state.monitor.targets) || {};
    var cards = ["Pages", "PI", "AI", "EC2", "ResultAutomation", "ResearchScheduler"]
      .map(function (k) {
        var t = mon[k] || {};
        return renderCard({
          label: k === "ResearchScheduler" ? "Research Scheduler" : k,
          value: t.status || NO_DATA,
          tone: monitorTone(t.status),
          note: t.last_update ? "updated=" + t.last_update : null,
          apiPath: "/api/ops/monitor-live",
        });
      });
    var bm = state.benchmarkStrategy || {};
    cards.push(
      renderCard({
        label: "Benchmark Strategy",
        value: bm.current_strategy || "◎単勝1点",
        tone: bm.enabled !== false ? "ok" : "muted",
        note:
          "Status: " +
          (bm.status || "Production Standard") +
          " · Current Strategy: " +
          (bm.current_strategy || "◎単勝1点") +
          " · Version: " +
          (bm.version || "9.0") +
          " · Since: " +
          (bm.since || "2026-07") +
          " · Last Updated: " +
          (bm.last_updated || "2026-07-27") +
          (bm.enabled === false ? " · flag=OFF" : " · flag=ON"),
        jsonPath: "/ops-data/benchmark-strategy.json",
      })
    );
    grid.innerHTML = cards.join("");
  }

  function paintEvidence() {
    var host = document.getElementById("opsEvidenceList");
    if (!host) return;
    var items =
      (state.console &&
        state.console.publish &&
        state.console.publish.evidence &&
        state.console.publish.evidence.items) ||
      [];
    if (!items.length) {
      host.innerHTML = "<p class='ops-note'>" + esc(NO_DATA) + "</p>";
      return;
    }
    host.innerHTML = items
      .map(function (e) {
        return (
          '<article class="ops-evidence-item"><h3>' +
          esc(e.label) +
          "</h3><p class='ops-card-note'>" +
          esc(e.week_id || "knowledge") +
          " · " +
          esc(e.kind) +
          '</p><p><a class="ops-evidence-link" href="' +
          esc(e.public_path) +
          '" target="_blank" rel="noopener">Open</a> ' +
          '<button type="button" class="ops-mini-btn" data-json-view="' +
          esc(e.public_path) +
          '" data-json-title="' +
          esc(e.label) +
          '">View JSON</button></p></article>'
        );
      })
      .join("");
  }

  function paintDownload() {
    var host = document.getElementById("opsDownloadList");
    if (!host) return;
    var week =
      (state.console &&
        state.console.publish &&
        state.console.publish.portal_snapshot &&
        state.console.publish.portal_snapshot.research &&
        state.console.publish.portal_snapshot.research.week_id) ||
      (state.console &&
        state.console.publish &&
        state.console.publish.reports &&
        state.console.publish.reports.latest_week_id) ||
      null;
    var links = [
      { label: "Approval Queue JSON", href: "/ops-data/approval-queue.json" },
      { label: "Knowledge JSON", href: "/ops-data/knowledge.json" },
      { label: "Reports JSON", href: "/ops-data/reports.json" },
      { label: "Portal Snapshot JSON", href: "/ops-data/portal-snapshot.json" },
      { label: "History JSON", href: "/ops-data/history.json" },
      { label: "Timeline JSON", href: "/ops-data/timeline.json" },
    ];
    if (week) {
      links.push(
        {
          label: "Weekly Report JSON (" + week + ")",
          href: "/ops-data/artifacts/" + week + "/weekly-ops-report.json",
        },
        {
          label: "Weekly Report MD (" + week + ")",
          href: "/ops-data/artifacts/" + week + "/weekly-ops-report.md",
        },
        {
          label: "Boundary Audit (" + week + ")",
          href: "/ops-data/artifacts/" + week + "/boundary-audit.json",
        },
        {
          label: "Deploy Note JSON (" + week + ")",
          href: "/ops-data/artifacts/" + week + "/deploy-note.json",
        },
        {
          label: "Deploy Note MD (" + week + ")",
          href: "/ops-data/artifacts/" + week + "/deploy-note.md",
        }
      );
    }
    host.innerHTML = links
      .map(function (l) {
        return (
          "<li><a class='ops-evidence-link' href='" +
          esc(l.href) +
          "' download target='_blank' rel='noopener'>" +
          esc(l.label) +
          "</a></li>"
        );
      })
      .join("");
  }

  function paintAudit() {
    var tbody = document.getElementById("opsAuditTbody");
    if (!tbody) return;
    var cards =
      (state.console &&
        state.console.publish &&
        state.console.publish.audit &&
        state.console.publish.audit.cards) ||
      [];
    if (!cards.length) {
      tbody.innerHTML = '<tr><td colspan="6">' + esc(NO_DATA) + "</td></tr>";
      return;
    }
    tbody.innerHTML = cards
      .map(function (c) {
        return (
          "<tr><td>" +
          esc(c.card) +
          "</td><td>" +
          esc(c.display || NO_DATA) +
          "</td><td>" +
          esc(c.api || NO_DATA) +
          "</td><td>" +
          esc(c.publish || NO_DATA) +
          "</td><td>" +
          esc(c.runner || NO_DATA) +
          "</td><td>" +
          esc(c.source || NO_DATA) +
          "</td></tr>"
        );
      })
      .join("");
  }

  function paintHistory() {
    var kind = (document.getElementById("opsHistoryKind") || {}).value || "approval";
    var week = ((document.getElementById("opsHistoryWeek") || {}).value || "").trim();
    var version = ((document.getElementById("opsHistoryVersion") || {}).value || "").trim();
    var status = ((document.getElementById("opsHistoryStatus") || {}).value || "").trim();
    var q =
      "/api/ops/history?kind=" +
      encodeURIComponent(kind) +
      (week ? "&week=" + encodeURIComponent(week) : "") +
      (version ? "&version=" + encodeURIComponent(version) : "") +
      (status ? "&status=" + encodeURIComponent(status) : "");
    return fetchJson(q).then(function (res) {
      var data = unwrap(res) || { items: [] };
      var items = data.items || [];
      var thead = document.getElementById("opsHistoryThead");
      var tbody = document.getElementById("opsHistoryTbody");
      if (thead) {
        thead.innerHTML =
          "<tr><th>Week</th><th>Version</th><th>Status</th><th>Decision</th><th>Updated</th><th>Path</th></tr>";
      }
      if (!tbody) return;
      if (!items.length) {
        tbody.innerHTML = '<tr><td colspan="6">' + esc(NO_DATA) + "</td></tr>";
        return;
      }
      tbody.innerHTML = items
        .map(function (row) {
          var path = row.path || row.md_path || "";
          return (
            "<tr><td>" +
            esc(row.week_id || NO_DATA) +
            "</td><td>" +
            esc(row.version || NO_DATA) +
            "</td><td>" +
            esc(row.status || NO_DATA) +
            "</td><td>" +
            esc(row.decision || NO_DATA) +
            "</td><td>" +
            esc(row.updated_at || NO_DATA) +
            "</td><td>" +
            (path
              ? '<a class="ops-evidence-link" href="' +
                esc(path) +
                '" target="_blank" rel="noopener">Open</a>'
              : esc(NO_DATA)) +
            "</td></tr>"
          );
        })
        .join("");
    });
  }

  function findApproval(id) {
    var items = (state.approvals && state.approvals.items) || [];
    for (var i = 0; i < items.length; i++) {
      if (items[i].approval_id === id) return items[i];
    }
    return null;
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

  function loadApprovals() {
    return fetchJson("/api/ops/approvals").then(function (res) {
      state.approvals = unwrap(res) || { items: [] };
      paintApprovalCenter();
    });
  }

  function bindUi() {
    var nav = document.getElementById("opsPortalNav");
    if (nav) {
      nav.addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-ops-section]");
        if (!btn) return;
        ev.preventDefault();
        setActiveSection(btn.getAttribute("data-ops-section"));
      });
    }
    var refresh = document.getElementById("opsPortalRefreshBtn");
    if (refresh) refresh.onclick = function () {
      loadAll();
    };
    var histBtn = document.getElementById("opsHistoryApply");
    if (histBtn) histBtn.onclick = function () {
      paintHistory();
    };
    var searchForm = document.getElementById("opsSearchForm");
    if (searchForm) {
      searchForm.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var params = new URLSearchParams();
        ["q", "version", "week", "proposal", "pattern", "decision", "status"].forEach(
          function (k) {
            var el = document.getElementById(
              "opsSearch" + k.charAt(0).toUpperCase() + k.slice(1)
            );
            if (k === "q") el = document.getElementById("opsSearchQ");
            if (k === "version") el = document.getElementById("opsSearchVersion");
            if (k === "week") el = document.getElementById("opsSearchWeek");
            if (k === "proposal") el = document.getElementById("opsSearchProposal");
            if (k === "pattern") el = document.getElementById("opsSearchPattern");
            if (k === "decision") el = document.getElementById("opsSearchDecision");
            if (k === "status") el = document.getElementById("opsSearchStatus");
            if (el && el.value) params.set(k, el.value.trim());
          }
        );
        fetchJson("/api/ops/search?" + params.toString()).then(function (res) {
          var data = unwrap(res) || { docs: [] };
          var host = document.getElementById("opsSearchResults");
          if (!host) return;
          host.hidden = false;
          if (!data.docs || !data.docs.length) {
            host.innerHTML = "<p class='ops-note'>" + esc(NO_DATA) + "</p>";
            return;
          }
          host.innerHTML =
            "<ul>" +
            data.docs
              .map(function (d) {
                return (
                  "<li>" +
                  esc(d.type) +
                  " · " +
                  esc(d.id) +
                  " · week=" +
                  esc(d.week_id || NO_DATA) +
                  " · " +
                  esc(d.decision || d.status || NO_DATA) +
                  (d.path
                    ? ' · <a class="ops-evidence-link" href="' +
                      esc(d.path) +
                      '" target="_blank" rel="noopener">Open</a>'
                    : "") +
                  "</li>"
                );
              })
              .join("") +
            "</ul>";
        });
      });
    }

    document.body.addEventListener("click", function (ev) {
      var jsonBtn = ev.target.closest("[data-json-view]");
      if (jsonBtn) {
        var path = jsonBtn.getAttribute("data-json-view");
        var api = jsonBtn.getAttribute("data-api-view");
        var title = jsonBtn.getAttribute("data-json-title") || "JSON";
        var tasks = [];
        if (path) {
          tasks.push(
            fetch(path, { cache: "no-store" }).then(function (r) {
              return r.text().then(function (t) {
                return { label: "Publish JSON (" + path + ")", body: t };
              });
            })
          );
        }
        if (api) {
          tasks.push(
            fetchJson(api).then(function (res) {
              return {
                label: "API JSON (" + api + ")",
                body: JSON.stringify(res.body, null, 2),
              };
            })
          );
        }
        Promise.all(tasks).then(function (parts) {
          openDialog(
            title,
            parts
              .map(function (p) {
                return "===== " + p.label + " =====\n" + p.body;
              })
              .join("\n\n")
          );
        });
        return;
      }

      var detailBtn = ev.target.closest("[data-approval-detail]");
      if (detailBtn) {
        var id = detailBtn.getAttribute("data-approval-detail");
        var item = findApproval(id);
        var week = item && item.week_id;
        var paths = [];
        if (week) {
          paths.push("/ops-data/artifacts/" + week + "/decision.json");
        }
        Promise.all(
          paths.map(function (p) {
            return fetch(p, { cache: "no-store" })
              .then(function (r) {
                return r.ok ? r.json() : null;
              })
              .catch(function () {
                return null;
              });
          })
        ).then(function (bodies) {
          openDialog("Decision · " + id, {
            approval: item || { approval_id: id },
            decision_json: bodies[0] || NO_DATA,
          });
        });
        return;
      }

      var act = ev.target.closest("[data-approval-action]");
      if (act) {
        var aid = act.getAttribute("data-approval-id");
        var action = act.getAttribute("data-approval-action");
        if (action === "approve") {
          if (
            !window.confirm(
              "Approve しますか？ Deploy Note のみ作成し、Production には反映しません。"
            )
          ) {
            return;
          }
          postApproval(aid, "approve", {}).then(function () {
            return loadApprovals();
          });
        } else if (action === "reject") {
          var reason = window.prompt("却下理由（Knowledge に記録）");
          if (!reason || !String(reason).trim()) return;
          postApproval(aid, "reject", { reason: String(reason).trim() }).then(function () {
            return loadApprovals();
          });
        }
      }
    });
  }

  function paintAll() {
    paintApprovalCenter();
    paintMonitor();
    paintTimeline();
    paintSectionGrid("research");
    paintSectionGrid("knowledge");
    paintSectionGrid("deploy");
    paintSectionGrid("reports");
    paintEvidence();
    paintDownload();
    paintAudit();
    paintSystem();
    paintHistory();
  }

  function loadAll() {
    var statusEl = document.getElementById("opsLoadStatus");
    if (statusEl) statusEl.textContent = "読み込み中…";
    return Promise.all([
      fetchJson("/api/ops/console"),
      fetchJson("/api/ops/approvals"),
      fetchJson("/api/ops/monitor-live"),
      fetchJson("/ops-data/benchmark-strategy.json"),
    ]).then(function (parts) {
      var cons = parts[0];
      if (!cons || cons.status === 401) {
        showDenied("ログインが必要です。");
        return;
      }
      if (cons.status === 403 || (cons.body && cons.body.ok === false)) {
        showDenied(
          (cons.body && cons.body.error && cons.body.error.message) ||
            "role=ADMIN のみ利用できます。"
        );
        return;
      }
      state.console = unwrap(cons);
      if (!state.console) {
        showDenied("コンソールデータの取得に失敗しました。");
        return;
      }
      state.approvals = unwrap(parts[1]) || { items: [] };
      state.monitor = unwrap(parts[2]);
      var bmRes = parts[3];
      if (bmRes && bmRes.ok && bmRes.body && typeof bmRes.body === "object") {
        state.benchmarkStrategy =
          bmRes.body.data && typeof bmRes.body.data === "object"
            ? bmRes.body.data
            : bmRes.body;
      } else {
        state.benchmarkStrategy = null;
      }
      showMain();
      var meta = document.getElementById("opsPortalMeta");
      if (meta) {
        meta.textContent =
          "Version8.9 · Operations Console · baseline " +
          displayValue(
            (state.console.publish &&
              state.console.publish.portal_snapshot &&
              state.console.publish.portal_snapshot.baseline_lock) ||
              null
          ) +
          " · Production 自動適用禁止";
      }
      paintAll();
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
      if (!me && !authRaw && !userRaw) return { allow: false, reason: "login" };
      if (roles) {
        return roles.isOpsPortalAdmin(me || authRaw || userRaw).then(function (ok) {
          return { allow: !!ok, reason: ok ? "admin" : "forbidden" };
        });
      }
      var role = String(
        (me && me.role) ||
          (authRaw && authRaw.user && authRaw.user.role) ||
          (userRaw && userRaw.role) ||
          ""
      ).toUpperCase();
      if (role === "ADMIN" || role === "ADMINISTRATOR" || role === "ROOT") {
        return { allow: true, reason: "admin" };
      }
      return { allow: false, reason: "forbidden" };
    });
  }

  function boot() {
    bindUi();
    setActiveSection("approval");
    resolveAdminAccess().then(function (gate) {
      if (!gate || gate.reason === "login") {
        showDenied("ログインが必要です。");
        return;
      }
      if (!gate.allow) {
        showDenied("Operations Console は role=ADMIN のみ利用できます。");
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
