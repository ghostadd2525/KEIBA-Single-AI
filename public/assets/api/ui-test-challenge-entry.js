/**
 * ExpectUiTestChallengeEntry — Challenge active list + result modal host
 *
 * Schema authority: /data/ui-test-challenge-entry.schema.json
 * Runtime store (ui-test only): sessionStorage (static hosting cannot write public/*.json)
 *
 * Multi-race collection:
 *   { schema_version, ui_test, entries: [ raceEntry, ... ] }
 *
 * Lifecycle: ACTIVE | RESULT_READY (ui-test fixture) | READY (real V6 backend)
 * ui-test uses Frontend fixture only — no Result Automation / DB / Settlement.
 * Real users: ExpectChallengeLifecycle + V6 backend authority (no sessionStorage lifecycle).
 *
 * Does NOT send ui-test-race-* to lifecycle / notification / settlement APIs.
 * Does NOT mutate AI Benchmark or real user score aggregates from fixtures.
 */
(function (global) {
  "use strict";

  var SCHEMA_VERSION = "expect-ui-test-challenge-entry/1.2";
  var STORAGE_KEY = "expect_ui_test_challenge_entry_v1";
  var NOTIF_KEY = "expect_challenge_result_notifications_v1";
  var AGGREGATE_KEY = "expect_ui_test_challenge_aggregate_v1";
  var SCHEMA_URL = "data/ui-test-challenge-entry.schema.json";
  var ACTIVE_LABEL = "Challenge参加中";
  var RESULT_READY_LABEL = "結果確定";
  var NOTIF_TYPE = "CHALLENGE_RESULT_READY";
  var STATUS_ACTIVE = "ACTIVE";
  var STATUS_RESULT_READY = "RESULT_READY";
  var STATUS_READY = "READY";
  var UI_TEST_RACE_ID = "ui-test-race-001";

  var _savedRefresh = null;
  var _realEntries = [];
  var _pendingConsumeRaceIds = {};
  var _pendingConsumeBattles = {};
  var _modalOpenRaceId = null;
  /** UI-test delete-lock clock (ms). null = wall clock. */
  var _uiTestNowMs = null;
  var DELETE_LOCK_MINUTES = 5;

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtYen(n, signed) {
    var v = Math.round(Number(n) || 0);
    var abs = "¥" + Math.abs(v).toLocaleString("ja-JP");
    if (!signed) return abs;
    if (v > 0) return "+" + abs;
    if (v < 0) return "-" + abs;
    return abs;
  }

  function storage() {
    try {
      return global.sessionStorage;
    } catch (e) {
      return null;
    }
  }

  function notifStorage() {
    try {
      return global.sessionStorage;
    } catch (e) {
      return null;
    }
  }

  function currentMonth() {
    var d = new Date();
    var m = d.getMonth() + 1;
    return d.getFullYear() + "-" + (m < 10 ? "0" : "") + m;
  }

  function parseMonthLabel(text) {
    var m = String(text || "").match(/(\d{4})年\s*(\d{1,2})月/);
    if (!m) return currentMonth();
    var mm = Number(m[2]);
    return m[1] + "-" + (mm < 10 ? "0" : "") + mm;
  }

  function entryMonth(entry) {
    if (!entry) return "";
    var rd = String(entry.race_date || "");
    if (/^\d{4}-\d{2}/.test(rd)) return rd.slice(0, 7);
    var ra = String(entry.registered_at || "");
    if (/^\d{4}-\d{2}/.test(ra)) return ra.slice(0, 7);
    return "";
  }

  function fixtureRaceInfo(raceId) {
    if (
      global.ExpectUiTestRace &&
      ExpectUiTestRace.isUiTestRaceId &&
      ExpectUiTestRace.isUiTestRaceId(raceId) &&
      typeof ExpectUiTestRace.getBundle === "function"
    ) {
      var bundle = ExpectUiTestRace.getBundle();
      return (bundle && bundle.race_info) || null;
    }
    return null;
  }

  function enrichFromFixture(entry) {
    if (!entry || !entry.ui_test) return entry;
    var info = fixtureRaceInfo(entry.race_id);
    if (!info) return entry;
    if (!entry.venue && info.venue) entry.venue = String(info.venue);
    if (!entry.race_number && (info.race_no != null || info.race_number != null)) {
      var no = info.race_no != null ? info.race_no : info.race_number;
      entry.race_number = String(no) + "R";
    }
    if (!entry.race_name && (info.race_name || info.class_label)) {
      entry.race_name = String(info.race_name || info.class_label);
    }
    if (!entry.post_time && info.post_time) {
      entry.post_time = String(info.post_time);
    }
    if ((!entry.race_date || entry.race_date === "TEST") && info.date && /^\d{4}-\d{2}/.test(String(info.date))) {
      entry.race_date = String(info.date);
    }
    return entry;
  }

  function normalizeStatus(raw) {
    var s = String(raw || "").toUpperCase();
    if (s === STATUS_RESULT_READY || s === STATUS_READY) return s === STATUS_READY ? STATUS_READY : STATUS_RESULT_READY;
    return STATUS_ACTIVE;
  }

  function isReadyStatus(status) {
    var s = String(status || "").toUpperCase();
    return s === STATUS_RESULT_READY || s === STATUS_READY;
  }

  function isUiTestRaceId(raceId) {
    if (
      global.ExpectChallengeLifecycle &&
      typeof ExpectChallengeLifecycle.isUiTestRaceId === "function"
    ) {
      return !!ExpectChallengeLifecycle.isUiTestRaceId(raceId);
    }
    return String(raceId || "").indexOf("ui-test-race-") === 0;
  }

  function normalizeBattle(raw) {
    if (!raw || typeof raw !== "object") return null;
    var user = raw.user || {};
    var ai = raw.ai || {};
    var userReg = Number(user.registered != null ? user.registered : user.total_registered) || 0;
    var userPay = Number(user.payout != null ? user.payout : user.total_payout) || 0;
    var aiReg = Number(ai.registered != null ? ai.registered : ai.total_registered) || 0;
    var aiPay = Number(ai.payout != null ? ai.payout : ai.total_payout) || 0;
    var userProfit =
      user.profit != null ? Number(user.profit) : userPay - userReg;
    var aiProfit = ai.profit != null ? Number(ai.profit) : aiPay - aiReg;
    var winner = raw.winner;
    if (winner !== "USER" && winner !== "AI" && winner !== "DRAW") {
      if (userProfit > aiProfit) winner = "USER";
      else if (userProfit < aiProfit) winner = "AI";
      else winner = "DRAW";
    }
    return {
      user: {
        registered: userReg,
        payout: userPay,
        profit: userProfit,
        bets: Array.isArray(user.bets)
          ? user.bets.map(function (b) {
              var amount = Number(b.amount) || 0;
              var payout = Number(b.payout) || 0;
              var profit =
                b.profit != null ? Number(b.profit) : payout - amount;
              return {
                bet_type: String(b.bet_type || ""),
                legs_display: b.legs_display != null ? String(b.legs_display) : "",
                amount: amount,
                payout: payout,
                profit: profit,
                result_label: String(
                  b.result_label || (payout > 0 ? "的中" : "はずれ")
                ),
              };
            })
          : [],
      },
      ai: {
        registered: aiReg,
        payout: aiPay,
        profit: aiProfit,
        source: String(ai.source || "FROZEN_UI_TEST_AI_CHALLENGE"),
      },
      winner: winner,
    };
  }

  function normalizeRaceEntry(raw) {
    if (!raw || typeof raw !== "object") return null;
    if (!raw.race_id || !Array.isArray(raw.bets) || !raw.bets.length) return null;
    var total = 0;
    var bets = raw.bets.map(function (b) {
      var amount = Number(b.amount) || 0;
      total += amount;
      return {
        bet_type: String(b.bet_type || ""),
        ordered: !!b.ordered,
        legs_display: b.legs_display != null ? String(b.legs_display) : "",
        selections: Array.isArray(b.selections)
          ? b.selections.map(function (s) {
              return {
                horse_number: Number(s.horse_number),
                horse_name: String(s.horse_name || ""),
              };
            })
          : [],
        amount: amount,
      };
    });
    var entry = {
      race_id: String(raw.race_id),
      ui_test: raw.ui_test !== false,
      race_date: raw.race_date != null ? String(raw.race_date) : null,
      venue: raw.venue != null ? String(raw.venue) : "",
      race_number: raw.race_number != null ? String(raw.race_number) : "",
      race_name: raw.race_name != null ? String(raw.race_name) : "",
      post_time: raw.post_time != null ? String(raw.post_time) : "",
      registered_at: raw.registered_at || null,
      total_registered_amount: Number(raw.total_registered_amount) || total,
      status: normalizeStatus(raw.status),
      bets: bets,
    };
    if (!entry.total_registered_amount) entry.total_registered_amount = total;
    var battle = normalizeBattle(raw.battle);
    if (battle) entry.battle = battle;
    // Never fabricate financial battle for real races; ui-test may use fixture.
    if (isReadyStatus(entry.status) && !entry.battle && entry.ui_test) {
      entry.battle = defaultBattleFixture(entry);
    }
    if (raw.real_lifecycle) entry.real_lifecycle = true;
    if (raw.lifecycle) entry.lifecycle = raw.lifecycle;
    return enrichFromFixture(entry);
  }

  function normalizeCollection(raw) {
    if (!raw || typeof raw !== "object") return null;

    if (!Array.isArray(raw.entries) && raw.race_id && Array.isArray(raw.bets)) {
      var legacy = normalizeRaceEntry(raw);
      if (!legacy) return null;
      return {
        schema_version: SCHEMA_VERSION,
        ui_test: legacy.ui_test,
        entries: [legacy],
      };
    }

    if (!Array.isArray(raw.entries) || !raw.entries.length) return null;
    var entries = [];
    raw.entries.forEach(function (e) {
      var n = normalizeRaceEntry(e);
      if (n) entries.push(n);
    });
    if (!entries.length) return null;
    return {
      schema_version: raw.schema_version || SCHEMA_VERSION,
      ui_test: raw.ui_test !== false,
      entries: entries,
    };
  }

  function loadCollection() {
    var store = storage();
    if (!store) return null;
    try {
      return normalizeCollection(JSON.parse(store.getItem(STORAGE_KEY) || "null"));
    } catch (e) {
      return null;
    }
  }

  function saveCollection(collection) {
    var store = storage();
    if (!store) return false;
    if (!collection || !Array.isArray(collection.entries) || !collection.entries.length) {
      try {
        store.removeItem(STORAGE_KEY);
      } catch (e) {
        /* ignore */
      }
      return true;
    }
    var norm = normalizeCollection(collection);
    if (!norm) {
      try {
        store.removeItem(STORAGE_KEY);
      } catch (e2) {
        /* ignore */
      }
      return true;
    }
    try {
      store.setItem(STORAGE_KEY, JSON.stringify(norm));
      return true;
    } catch (e) {
      return false;
    }
  }

  function save(entry) {
    var race = normalizeRaceEntry(entry);
    if (!race) return false;
    var col = loadCollection() || {
      schema_version: SCHEMA_VERSION,
      ui_test: true,
      entries: [],
    };
    var next = [];
    var replaced = false;
    col.entries.forEach(function (e) {
      if (e.race_id === race.race_id) {
        next.push(race);
        replaced = true;
      } else {
        next.push(e);
      }
    });
    if (!replaced) next.push(race);
    return saveCollection({
      schema_version: SCHEMA_VERSION,
      ui_test: col.ui_test !== false,
      entries: next,
    });
  }

  function load() {
    var col = loadCollection();
    if (!col || !col.entries.length) return null;
    return col.entries[col.entries.length - 1];
  }

  function clear() {
    var store = storage();
    if (!store) return;
    try {
      store.removeItem(STORAGE_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  function weekOfMonthNow() {
    var d = new Date();
    return Math.min(5, Math.max(1, Math.ceil(d.getDate() / 7)));
  }

  function readAggregateOverlay() {
    var store = storage();
    if (!store) return null;
    try {
      var raw = JSON.parse(store.getItem(AGGREGATE_KEY) || "null");
      if (!raw || raw.ui_test !== true || !raw.applied) return null;
      return raw;
    } catch (e) {
      return null;
    }
  }

  function writeAggregateOverlay(overlay) {
    var store = storage();
    if (!store) return false;
    try {
      if (!overlay) {
        store.removeItem(AGGREGATE_KEY);
        return true;
      }
      store.setItem(AGGREGATE_KEY, JSON.stringify(overlay));
      return true;
    } catch (e) {
      return false;
    }
  }

  function clearAggregateOverlay() {
    return writeAggregateOverlay(null);
  }

  /** Frontend-only monthly/weekly reflection after ui-test CONSUMED. Never hits backend. */
  function applyUiTestConsumedFixture(raceId, battle) {
    if (!isUiTestRaceId(raceId)) return false;
    battle = normalizeBattle(battle) || visualDummyBattle001();
    var user = battle.user || {};
    var ai = battle.ai || {};
    var week = weekOfMonthNow();
    var overlay = {
      schema_version: "expect-ui-test-challenge-aggregate/1.0",
      ui_test: true,
      applied: true,
      race_id: String(raceId),
      applied_at: new Date().toISOString(),
      week: week,
      user: {
        purchase_amount: Number(user.registered) || 900,
        payout_amount: Number(user.payout) || 3300,
        profit: Number(user.profit) || 2400,
        race_count: 1,
        hit_count: 1,
      },
      // V7.5 visual: profit +¥2,400 → +100pt (not floor(profit/1000)=2)
      progress_award: Number(user.profit) >= 1000 ? 100 : 0,
      // Presentation coherence only — not real AI Benchmark mutation.
      gamemaster: {
        purchase_amount: Number(ai.registered) || 1000,
        payout_amount: Number(ai.payout) || 1600,
        profit: Number(ai.profit) || 600,
        race_count: 1,
        hit_count: 1,
      },
      note: "UIテスト反映（本番集計API未変更）",
    };
    writeAggregateOverlay(overlay);
    return true;
  }

  function standardActiveUiTestEntry() {
    var info = fixtureRaceInfo(UI_TEST_RACE_ID) || {};
    var today = new Date();
    var yyyy = today.getFullYear();
    var mm = today.getMonth() + 1;
    var dd = today.getDate();
    var raceDate =
      yyyy +
      "-" +
      (mm < 10 ? "0" : "") +
      mm +
      "-" +
      (dd < 10 ? "0" : "") +
      dd;
    return normalizeRaceEntry({
      ui_test: true,
      race_id: UI_TEST_RACE_ID,
      race_date: raceDate,
      venue: info.venue || "東京",
      race_number:
        info.race_no != null || info.race_number != null
          ? String(info.race_no != null ? info.race_no : info.race_number) + "R"
          : "11R",
      race_name: info.race_name || info.class_label || "Expect Challenge テストレース",
      post_time: info.post_time || "15:40",
      registered_at: new Date().toISOString(),
      total_registered_amount: 900,
      status: STATUS_ACTIVE,
      bets: [
        {
          bet_type: "単勝",
          ordered: false,
          legs_display: "2番 テスト馬ニバン",
          selections: [{ horse_number: 2, horse_name: "テスト馬ニバン" }],
          amount: 300,
        },
        {
          bet_type: "馬連",
          ordered: false,
          legs_display: "2番 - 8番",
          selections: [
            { horse_number: 2, horse_name: "テスト馬ニバン" },
            { horse_number: 8, horse_name: "テスト馬ハチバン" },
          ],
          amount: 500,
        },
        {
          bet_type: "三連単",
          ordered: true,
          legs_display: "2 → 8 → 13",
          selections: [
            { horse_number: 2, horse_name: "テスト馬ニバン" },
            { horse_number: 8, horse_name: "テスト馬ハチバン" },
            { horse_number: 13, horse_name: "テスト馬ジュウサン" },
          ],
          amount: 100,
        },
      ],
    });
  }

  /** Reset ui-test-race-001 to ACTIVE Challenge参加中 with ¥900 fixture. */
  function resetUiTestActiveFixture() {
    clearAggregateOverlay();
    var list = readNotifications().filter(function (n) {
      return n.race_id !== UI_TEST_RACE_ID;
    });
    writeNotifications(list);
    var entry = standardActiveUiTestEntry();
    var ok = save(entry);
    if (
      global.ExpectChallengeDashboard &&
      typeof ExpectChallengeDashboard.refresh === "function"
    ) {
      ExpectChallengeDashboard.refresh();
    }
    requestRefresh();
    return ok;
  }

  /** READY +5min auto-consume visual equivalent — no backend / no modal. */
  function simulateAutoConsumeUiTest(raceId) {
    raceId = raceId || UI_TEST_RACE_ID;
    if (!isUiTestRaceId(raceId)) return false;
    var entry = findEntry(raceId);
    if (!entry) {
      resetUiTestActiveFixture();
      markResultReady(raceId);
      entry = findEntry(raceId);
    }
    if (!entry || !isReadyStatus(entry.status)) {
      markResultReady(raceId);
      entry = findEntry(raceId);
    }
    var battle = entry && entry.battle
      ? entry.battle
      : visualDummyBattle001();
    applyUiTestConsumedFixture(raceId, battle);
    deleteRace(raceId);
    setTimeout(function () {
      if (
        global.ExpectChallengeDashboard &&
        typeof ExpectChallengeDashboard.refresh === "function"
      ) {
        ExpectChallengeDashboard.refresh();
      }
      requestRefresh();
    }, 0);
    return true;
  }

  function buildFromStock(raceId, stock, meta) {
    meta = meta || {};
    stock = Array.isArray(stock) ? stock : [];
    var total = 0;
    var bets = stock.map(function (item) {
      total += Number(item.amount) || 0;
      var selections = (item.selection || []).map(function (num, idx) {
        var line = (item.selection_lines && item.selection_lines[idx]) || "";
        var name = "";
        var m = String(line).match(/^\d+番\s*(.*)$/);
        if (m) name = m[1];
        return {
          horse_number: Number(num),
          horse_name: name,
        };
      });
      return {
        bet_type: item.bet_type,
        ordered: !!item.ordered,
        legs_display: item.legs_display || "",
        selections: selections,
        amount: Number(item.amount) || 0,
      };
    });
    var raceDate = meta.raceDate || null;
    if (!raceDate || raceDate === "TEST") {
      raceDate = currentMonth() + "-01";
    }
    return normalizeRaceEntry({
      ui_test: true,
      race_id: raceId,
      race_date: raceDate,
      venue: meta.venue || "",
      race_number: meta.raceNumber || "",
      race_name: meta.raceName || "",
      post_time: meta.postTime || meta.post_time || "",
      registered_at: new Date().toISOString(),
      total_registered_amount: total,
      status: STATUS_ACTIVE,
      bets: bets,
    });
  }

  function sortEntries(entries) {
    return entries.slice().sort(function (a, b) {
      var da = String(a.race_date || a.registered_at || "");
      var db = String(b.race_date || b.registered_at || "");
      if (da !== db) return db.localeCompare(da);
      var pa = String(a.post_time || "");
      var pb = String(b.post_time || "");
      if (pa !== pb) return pb.localeCompare(pa);
      return String(b.registered_at || "").localeCompare(String(a.registered_at || ""));
    });
  }

  function filterByMonth(entries, monthYm) {
    if (!monthYm) return entries;
    return entries.filter(function (e) {
      var em = entryMonth(e);
      if (!em) return true;
      return em === monthYm;
    });
  }

  function globalTotal(entries) {
    var sum = 0;
    (entries || []).forEach(function (e) {
      (e.bets || []).forEach(function (b) {
        sum += Number(b.amount) || 0;
      });
    });
    return sum;
  }

  function raceTotal(entry) {
    var sum = 0;
    (entry.bets || []).forEach(function (b) {
      sum += Number(b.amount) || 0;
    });
    return sum;
  }

  function selectionLinesHtml(bet) {
    if (bet.ordered && bet.legs_display) {
      return "<div>" + escapeHtml(bet.legs_display) + "</div>";
    }
    if (Array.isArray(bet.selections) && bet.selections.length) {
      return bet.selections
        .map(function (s) {
          var label =
            s.horse_number +
            "番" +
            (s.horse_name ? " " + s.horse_name : "");
          return "<div>" + escapeHtml(label) + "</div>";
        })
        .join("");
    }
    if (bet.legs_display) {
      return "<div>" + escapeHtml(bet.legs_display) + "</div>";
    }
    return "<div>—</div>";
  }

  function racePlace(entry) {
    return (
      (entry.venue || "") +
      (entry.race_number
        ? (entry.venue ? " " : "") + entry.race_number
        : "")
    );
  }

  function statusLabel(entry) {
    return entry && isReadyStatus(entry.status)
      ? RESULT_READY_LABEL
      : ACTIVE_LABEL;
  }

  /** Frontend-only visual dummy for ui-test-race-001 — no backend / settlement. */
  function visualDummyBattle001() {
    return normalizeBattle({
      user: {
        registered: 900,
        payout: 3300,
        profit: 2400,
        bets: [
          {
            bet_type: "単勝",
            legs_display: "2番 テスト馬ニバン",
            amount: 300,
            payout: 900,
            profit: 600,
            result_label: "的中",
          },
          {
            bet_type: "馬連",
            legs_display: "2番 - 8番",
            amount: 500,
            payout: 0,
            profit: -500,
            result_label: "はずれ",
          },
          {
            bet_type: "三連単",
            legs_display: "2 → 8 → 13",
            amount: 100,
            payout: 2400,
            profit: 2300,
            result_label: "的中",
          },
        ],
      },
      ai: {
        registered: 1000,
        payout: 1600,
        profit: 600,
        source: "FROZEN_UI_TEST_AI_CHALLENGE",
      },
      winner: "USER",
    });
  }

  function defaultBattleFixture(entry) {
    if (entry && entry.race_id === "ui-test-race-001") {
      return visualDummyBattle001();
    }
    var bets = (entry.bets || []).map(function (b, i) {
      var hit = i === 1;
      var payout = hit ? Math.max(Number(b.amount) || 0, 100) * 4 + 300 : 0;
      var amount = Number(b.amount) || 0;
      return {
        bet_type: b.bet_type,
        legs_display:
          b.legs_display ||
          (b.selections || [])
            .map(function (s) {
              return s.horse_number + "番" + (s.horse_name ? " " + s.horse_name : "");
            })
            .join(b.ordered ? " → " : " - "),
        amount: amount,
        payout: payout,
        profit: payout - amount,
        result_label: hit ? "的中" : "はずれ",
      };
    });
    var userReg = raceTotal(entry);
    var userPay = bets.reduce(function (s, b) {
      return s + (Number(b.payout) || 0);
    }, 0);
    var userProfit = userPay - userReg;
    var aiReg = 1000;
    var aiPay = 450;
    var aiProfit = aiPay - aiReg;
    var winner =
      userProfit > aiProfit ? "USER" : userProfit < aiProfit ? "AI" : "DRAW";
    return normalizeBattle({
      user: {
        registered: userReg,
        payout: userPay,
        profit: userProfit,
        bets: bets,
      },
      ai: {
        registered: aiReg,
        payout: aiPay,
        profit: aiProfit,
        source: "FROZEN_UI_TEST_AI_CHALLENGE",
      },
      winner: winner,
    });
  }

  function notifId(raceId) {
    return NOTIF_TYPE + ":" + String(raceId);
  }

  function readNotifications() {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.readFixtureNotifications === "function"
    ) {
      return ExpectChallengeNotifications.readFixtureNotifications();
    }
    var store = notifStorage();
    if (!store) return [];
    try {
      var list = JSON.parse(store.getItem(NOTIF_KEY) || "[]");
      return Array.isArray(list) ? list : [];
    } catch (e) {
      return [];
    }
  }

  function writeNotifications(list) {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.writeFixtureNotifications === "function"
    ) {
      return ExpectChallengeNotifications.writeFixtureNotifications(list);
    }
    var store = notifStorage();
    if (!store) return false;
    try {
      store.setItem(NOTIF_KEY, JSON.stringify(list || []));
      return true;
    } catch (e) {
      return false;
    }
  }

  function getRealNotifs() {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.getRealNotifs === "function"
    ) {
      return ExpectChallengeNotifications.getRealNotifs() || [];
    }
    return [];
  }

  function setRealNotifs(list) {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.setRealNotifs === "function"
    ) {
      ExpectChallengeNotifications.setRealNotifs(list || []);
    }
  }

  function deleteLockClockMs() {
    if (_uiTestNowMs != null && isFinite(_uiTestNowMs)) return _uiTestNowMs;
    return Date.now();
  }

  /**
   * Official lock: post_time - 5 minutes (発走5分前から削除禁止).
   * READY always locked. Missing post_time → locked (no unsafe delete).
   */
  function parseEntryPostAt(entry) {
    if (!entry) return null;
    var date = String(entry.race_date || "").slice(0, 10);
    var time = String(entry.post_time || "");
    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !time) return null;
    var parts = time.split(":");
    var h = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return null;
    var d = new Date(date + "T00:00:00");
    if (isNaN(d.getTime())) return null;
    d.setHours(h, m, 0, 0);
    return d;
  }

  function isDeleteLocked(entry) {
    if (!entry) return true;
    if (isReadyStatus(entry.status)) return true;
    var postAt = parseEntryPostAt(entry);
    if (!postAt) return true;
    var lockAt = postAt.getTime() - DELETE_LOCK_MINUTES * 60 * 1000;
    return deleteLockClockMs() >= lockAt;
  }

  function canShowDeleteControls(entry) {
    if (!(entry && (entry.ui_test || isUiTestRaceId(entry.race_id)))) {
      return false;
    }
    if (isReadyStatus(entry.status)) return false;
    if (isDeleteLocked(entry)) return false;
    return true;
  }

  function setUiTestClock(isoOrMs) {
    if (isoOrMs == null || isoOrMs === "") {
      _uiTestNowMs = null;
      return null;
    }
    if (typeof isoOrMs === "number") {
      _uiTestNowMs = isoOrMs;
      return _uiTestNowMs;
    }
    var t = Date.parse(String(isoOrMs));
    _uiTestNowMs = isNaN(t) ? null : t;
    return _uiTestNowMs;
  }

  function upsertResultNotification(entry) {
    if (!entry || entry.status !== STATUS_RESULT_READY) return false;
    var id = notifId(entry.race_id);
    var list = readNotifications();
    var exists = list.some(function (n) {
      return n.id === id;
    });
    if (exists) return false;
    list.unshift({
      id: id,
      notification_type: NOTIF_TYPE,
      race_id: entry.race_id,
      title: "Challenge結果が確定しました",
      venue_line: racePlace(entry) || entry.race_id,
      race_name: entry.race_name || "",
      body: "Game Masterとの結果を確認できます",
      read: false,
      created_at: new Date().toISOString(),
    });
    writeNotifications(list);
    return true;
  }

  function markNotificationRead(raceId) {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.markRead === "function"
    ) {
      return ExpectChallengeNotifications.markRead(raceId);
    }
    var id = notifId(raceId);
    var list = readNotifications();
    var changed = false;
    list.forEach(function (n) {
      if (n.id === id && !n.read) {
        n.read = true;
        changed = true;
      }
    });
    if (changed) writeNotifications(list);
    return changed;
  }

  function unreadNotificationCount() {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.unreadCount === "function"
    ) {
      return ExpectChallengeNotifications.unreadCount() || 0;
    }
    return readNotifications().filter(function (n) {
      return !n.read;
    }).length;
  }

  function refreshBell() {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.refreshBell === "function"
    ) {
      ExpectChallengeNotifications.refreshBell();
      return;
    }
    if (global.ExpectReminders && typeof ExpectReminders.refreshBell === "function") {
      ExpectReminders.refreshBell();
    }
  }

  function requestRefresh() {
    if (typeof _savedRefresh === "function") _savedRefresh();
    refreshBell();
  }

  function deleteBet(raceId, betIndex) {
    var entry = findEntry(raceId);
    if (!canShowDeleteControls(entry)) return false;
    var col = loadCollection();
    if (!col) return false;
    var next = [];
    col.entries.forEach(function (e) {
      if (e.race_id !== raceId) {
        next.push(e);
        return;
      }
      var bets = (e.bets || []).slice();
      if (betIndex < 0 || betIndex >= bets.length) {
        next.push(e);
        return;
      }
      bets.splice(betIndex, 1);
      if (!bets.length) return;
      e.bets = bets;
      e.total_registered_amount = raceTotal(e);
      if (e.battle && e.battle.user) {
        e.battle = defaultBattleFixture(e);
      }
      next.push(e);
    });
    return saveCollection({
      schema_version: SCHEMA_VERSION,
      ui_test: col.ui_test !== false,
      entries: next,
    });
  }

  function deleteRace(raceId) {
    var entry = findEntry(raceId);
    if (!canShowDeleteControls(entry)) return false;
    var col = loadCollection();
    if (!col) return false;
    var next = col.entries.filter(function (e) {
      return e.race_id !== raceId;
    });
    return saveCollection({
      schema_version: SCHEMA_VERSION,
      ui_test: col.ui_test !== false,
      entries: next,
    });
  }

  function markResultReady(raceId, battleOverride) {
    if (!isUiTestRaceId(raceId)) return false;
    var col = loadCollection();
    if (!col) return false;
    var found = null;
    col.entries = col.entries.map(function (e) {
      if (e.race_id !== raceId) return e;
      e.status = STATUS_RESULT_READY;
      if (battleOverride) {
        e.battle = normalizeBattle(battleOverride);
      } else if (e.race_id === "ui-test-race-001") {
        e.battle = visualDummyBattle001();
      } else {
        e.battle = e.battle || defaultBattleFixture(e);
      }
      found = e;
      return e;
    });
    if (!found) return false;
    var ok = saveCollection(col);
    if (ok) upsertResultNotification(found);
    requestRefresh();
    return ok;
  }

  function findEntry(raceId) {
    for (var r = 0; r < _realEntries.length; r++) {
      if (_realEntries[r].race_id === raceId) return _realEntries[r];
    }
    var col = loadCollection();
    if (!col) return null;
    for (var i = 0; i < col.entries.length; i++) {
      if (col.entries[i].race_id === raceId) return col.entries[i];
    }
    return null;
  }

  function uiTestEntriesOnly() {
    var col = loadCollection();
    if (!col || !col.entries) return [];
    return col.entries.filter(function (e) {
      return e.ui_test || isUiTestRaceId(e.race_id);
    });
  }

  function mergedActiveEntries() {
    var map = {};
    uiTestEntriesOnly().forEach(function (e) {
      map[e.race_id] = e;
    });
    _realEntries.forEach(function (e) {
      if (!e || !e.race_id || isUiTestRaceId(e.race_id)) return;
      // Backend wins for real races — never resurrect from sessionStorage.
      map[e.race_id] = e;
    });
    return Object.keys(map).map(function (k) {
      return map[k];
    });
  }

  function openConfirmDialog(opts) {
    opts = opts || {};
    var existing = document.querySelector(".fav-dialog-root");
    if (existing) existing.remove();

    var root = document.createElement("div");
    root.className = "fav-dialog-root";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-labelledby", "ucConfirmTitle");
    root.innerHTML =
      '<div class="fav-dialog-backdrop" data-uc-dialog-cancel></div>' +
      '<div class="fav-dialog">' +
      '<p class="fav-dialog-kicker">' +
      escapeHtml(opts.kicker || "User Challenge") +
      "</p>" +
      '<h2 id="ucConfirmTitle">' +
      escapeHtml(opts.title || "確認") +
      "</h2>" +
      '<p class="fav-dialog-body">' +
      (opts.bodyHtml || escapeHtml(opts.body || "")) +
      "</p>" +
      '<div class="fav-dialog-actions">' +
      '<button type="button" class="fav-dialog-cancel" data-uc-dialog-cancel>キャンセル</button>' +
      '<button type="button" class="fav-dialog-ok" data-uc-dialog-ok>' +
      escapeHtml(opts.okLabel || "削除する") +
      "</button>" +
      "</div></div>";

    function close() {
      root.remove();
      document.body.classList.remove("is-fav-dialog");
    }

    root.addEventListener("click", function (e) {
      if (e.target.closest("[data-uc-dialog-cancel]")) {
        close();
        if (opts.onCancel) opts.onCancel();
      }
      if (e.target.closest("[data-uc-dialog-ok]")) {
        close();
        if (opts.onConfirm) opts.onConfirm();
      }
    });

    document.body.classList.add("is-fav-dialog");
    document.body.appendChild(root);
    var ok = root.querySelector("[data-uc-dialog-ok]");
    if (ok) ok.focus();
  }

  function barWidth(value, maxAbs) {
    var v = Math.abs(Number(value) || 0);
    if (!maxAbs || maxAbs <= 0) return 8;
    return Math.max(8, Math.round((v / maxAbs) * 100));
  }

  function prefersReducedMotion() {
    try {
      return !!(
        global.matchMedia &&
        global.matchMedia("(prefers-reduced-motion: reduce)").matches
      );
    } catch (e) {
      return false;
    }
  }

  function resolveWinner(userProfit, aiProfit) {
    if (userProfit > aiProfit) return "USER";
    if (userProfit < aiProfit) return "AI";
    return "DRAW";
  }

  function winnerRevealCopy(winner) {
    if (winner === "USER") return "YOU WIN";
    if (winner === "AI") return "YOU LOSE";
    return "DRAW";
  }

  /** Presentation opponent label only — internal winner/AI ids unchanged. */
  var RESULT_OPPONENT_DISPLAY_NAME = "Game Master";

  /**
   * Modal kicker: ExpectAuth display_name authority.
   * Never invent a fixture username; fall back to auth id, then generic.
   */
  function resolveUserDisplayName() {
    try {
      if (global.ExpectAuth && typeof ExpectAuth.current === "function") {
        var u = ExpectAuth.current();
        if (u && u.display_name != null && String(u.display_name).trim()) {
          return String(u.display_name).trim();
        }
        if (u && u.id != null && String(u.id).trim()) {
          return String(u.id).trim();
        }
      }
    } catch (e) { /* ignore */ }
    return "User Challenge";
  }

  function signedToneClass(n) {
    var v = Number(n) || 0;
    if (v > 0) return "is-plus";
    if (v < 0) return "is-minus";
    return "is-zero";
  }

  /** Acceptance variants — profits drive winner (never hard-coded). */
  function visualDummyBattleVariant(kind) {
    kind = String(kind || "USER").toUpperCase();
    if (kind === "AI" || kind === "LOSE") {
      return normalizeBattle({
        user: {
          registered: 900,
          payout: 1500,
          profit: 600,
          bets: [
            {
              bet_type: "単勝",
              legs_display: "2番 テスト馬ニバン",
              amount: 300,
              payout: 900,
              profit: 600,
              result_label: "的中",
            },
            {
              bet_type: "馬連",
              legs_display: "2番 - 8番",
              amount: 500,
              payout: 0,
              profit: -500,
              result_label: "はずれ",
            },
            {
              bet_type: "三連単",
              legs_display: "2 → 8 → 13",
              amount: 100,
              payout: 600,
              profit: 500,
              result_label: "的中",
            },
          ],
        },
        ai: {
          registered: 1000,
          payout: 2300,
          profit: 1300,
          source: "FROZEN_UI_TEST_AI_CHALLENGE",
        },
        winner: resolveWinner(600, 1300),
      });
    }
    if (kind === "DRAW") {
      return normalizeBattle({
        user: {
          registered: 900,
          payout: 2150,
          profit: 1250,
          bets: [
            {
              bet_type: "単勝",
              legs_display: "2番 テスト馬ニバン",
              amount: 300,
              payout: 900,
              profit: 600,
              result_label: "的中",
            },
            {
              bet_type: "馬連",
              legs_display: "2番 - 8番",
              amount: 500,
              payout: 0,
              profit: -500,
              result_label: "はずれ",
            },
            {
              bet_type: "三連単",
              legs_display: "2 → 8 → 13",
              amount: 100,
              payout: 1150,
              profit: 1050,
              result_label: "的中",
            },
          ],
        },
        ai: {
          registered: 1000,
          payout: 2250,
          profit: 1250,
          source: "FROZEN_UI_TEST_AI_CHALLENGE",
        },
        winner: resolveWinner(1250, 1250),
      });
    }
    return visualDummyBattle001();
  }

  function openBattleModal(raceId, opts) {
    opts = opts || {};
    var entry = findEntry(raceId);
    if (!entry || !isReadyStatus(entry.status)) return false;

    // Real races: load authoritative settlement + GameMaster (ai_theory) first.
    if (!entry.ui_test && !isUiTestRaceId(entry.race_id) && !opts.battle) {
      if (
        !(
          global.ExpectApi &&
          ExpectApi.User &&
          ExpectApi.User.getRaceResult &&
          global.ExpectChallengeLifecycle
        )
      ) {
        openConfirmDialog({
          title: "結果を取得できません",
          body: "認証または API が利用できません。",
          okLabel: "閉じる",
        });
        return false;
      }
      ExpectApi.User.getRaceResult(raceId)
        .then(function (payload) {
          var built = ExpectChallengeLifecycle.buildBattleFromRaceResult(payload);
          if (!built.ok) {
            openConfirmDialog({
              title: "Challenge結果を表示できません",
              body:
                built.reason === "gamemaster_comparator_missing"
                  ? "Game Master比較データ（凍結AI理論）がありません。捏造はしません。"
                  : "確定結果データを取得できませんでした（" +
                    (built.reason || "unknown") +
                    "）。",
              okLabel: "閉じる",
            });
            return;
          }
          openBattleModal(raceId, { battle: built.battle, real: true });
        })
        .catch(function (err) {
          openConfirmDialog({
            title: "結果の取得に失敗しました",
            body: (err && err.message) || "再試行してください。",
            okLabel: "閉じる",
          });
        });
      return true;
    }

    var battle = opts.battle
      ? normalizeBattle(opts.battle)
      : entry.race_id === "ui-test-race-001"
        ? visualDummyBattle001()
        : entry.ui_test
          ? entry.battle || defaultBattleFixture(entry)
          : null;
    if (!battle) return false;
    var userProfit = Number(battle.user.profit) || 0;
    var aiProfit = Number(battle.ai.profit) || 0;
    battle.winner = resolveWinner(userProfit, aiProfit);
    // Notification read ≠ lifecycle viewed
    markNotificationRead(raceId);
    refreshBell();

    var existing = document.querySelector(
      ".fav-dialog-root.user-challenge-battle-root"
    );
    if (existing) existing.remove();

    var maxAbs = Math.max(Math.abs(userProfit), Math.abs(aiProfit), 1);
    var userW = barWidth(userProfit, maxAbs);
    var aiW = barWidth(aiProfit, maxAbs);
    var diff = userProfit - aiProfit;
    var reveal = winnerRevealCopy(battle.winner);
    var reduceMotion = prefersReducedMotion();
    var isReal = !!(opts.real || entry.real_lifecycle || (!entry.ui_test && !isUiTestRaceId(entry.race_id)));
    _modalOpenRaceId = raceId;

    var betRows = (battle.user.bets || [])
      .map(function (b) {
        var profit =
          b.profit != null
            ? Number(b.profit)
            : (Number(b.payout) || 0) - (Number(b.amount) || 0);
        var hit = String(b.result_label || "") === "的中";
        return (
          '<article class="uc-battle-bet">' +
          '<div class="uc-battle-bet-head">' +
          '<span class="uc-bet-badge ' +
          (hit ? "is-hit" : "is-miss") +
          '">' +
          escapeHtml(b.result_label || "—") +
          "</span>" +
          '<span class="uc-battle-bet-type">[' +
          escapeHtml(b.bet_type || "—") +
          "]</span></div>" +
          '<div class="uc-battle-bet-legs">' +
          escapeHtml(b.legs_display || "—") +
          "</div>" +
          '<dl class="uc-battle-bet-meta">' +
          "<div><dt>登録</dt><dd>" +
          escapeHtml(fmtYen(b.amount)) +
          "</dd></div>" +
          "<div><dt>払戻</dt><dd>" +
          escapeHtml(fmtYen(b.payout)) +
          "</dd></div>" +
          '<div><dt>収支</dt><dd class="' +
          signedToneClass(profit) +
          '">' +
          escapeHtml(fmtYen(profit, true)) +
          "</dd></div>" +
          "</dl></article>"
        );
      })
      .join("");

    var root = document.createElement("div");
    root.className =
      "fav-dialog-root user-challenge-battle-root" +
      (reduceMotion ? " is-reduced-motion" : "");
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-labelledby", "ucBattleTitle");
    root.setAttribute("data-race-id", raceId);
    root.innerHTML =
      '<div class="fav-dialog-backdrop" data-uc-battle-close></div>' +
      '<div class="fav-dialog user-challenge-battle-dialog" role="document">' +
      '<button type="button" class="user-challenge-battle-x" data-uc-battle-close aria-label="閉じる">×</button>' +
      '<p class="fav-dialog-kicker">' +
      escapeHtml(resolveUserDisplayName()) +
      "</p>" +
      '<h2 id="ucBattleTitle">Challenge結果</h2>' +
      '<div class="uc-battle-scroll">' +
      '<p class="uc-battle-race">' +
      escapeHtml(racePlace(entry) || entry.race_id) +
      "</p>" +
      '<p class="uc-battle-name">' +
      escapeHtml(entry.race_name || "—") +
      "</p>" +
      (entry.post_time
        ? '<p class="uc-battle-post">発走 ' +
          escapeHtml(entry.post_time) +
          "</p>"
        : "") +
      '<p class="uc-result-kicker">' +
      escapeHtml(RESULT_OPPONENT_DISPLAY_NAME) +
      "との収支バトル</p>" +
      '<div class="cmp-bars uc-result-bars" data-uc-result-bars>' +
      '<div class="cmp-bar-row">' +
      '<span class="cmp-bar-label">' +
      escapeHtml(resolveUserDisplayName()) +
      "</span>" +
      '<div class="cmp-bar-track"><i class="cmp-bar cmp-bar--you' +
      (userProfit < 0 ? " is-neg" : "") +
      '" data-uc-bar="user" style="width:0%"></i></div>' +
      '<b class="' +
      signedToneClass(userProfit) +
      '">' +
      escapeHtml(fmtYen(userProfit, true)) +
      "</b></div>" +
      '<div class="cmp-bar-row">' +
      '<span class="cmp-bar-label">' +
      escapeHtml(RESULT_OPPONENT_DISPLAY_NAME) +
      "</span>" +
      '<div class="cmp-bar-track"><i class="cmp-bar cmp-bar--ai' +
      (aiProfit < 0 ? " is-neg" : "") +
      '" data-uc-bar="ai" style="width:0%"></i></div>' +
      '<b class="' +
      signedToneClass(aiProfit) +
      '">' +
      escapeHtml(fmtYen(aiProfit, true)) +
      "</b></div></div>" +
      '<section class="uc-result-reveal uc-result-winner" data-uc-reveal="winner" data-winner="' +
      escapeHtml(battle.winner) +
      '" aria-live="polite">' +
      '<div class="uc-result-winner-frame" aria-hidden="true">' +
      '<span class="uc-result-winner-ornament uc-result-winner-ornament--l"></span>' +
      '<span class="uc-result-winner-ornament uc-result-winner-ornament--r"></span>' +
      "</div>" +
      '<p class="uc-result-winner-kicker">RESULT</p>' +
      '<p class="uc-result-winner-en">' +
      escapeHtml(reveal) +
      "</p>" +
      '<div class="uc-result-winner-rule" aria-hidden="true"></div>' +
      "</section>" +
      '<section class="uc-result-reveal uc-result-diff" data-uc-reveal="diff">' +
      '<p class="uc-result-diff-kicker">収支差</p>' +
      '<p class="uc-result-diff-value ' +
      signedToneClass(diff) +
      '">' +
      escapeHtml(fmtYen(diff, true)) +
      "</p></section>" +
      '<section class="uc-result-reveal uc-result-totals" data-uc-reveal="totals">' +
      '<div class="uc-result-total-row"><span>' +
      escapeHtml(resolveUserDisplayName()) +
      "</span>" +
      "<span>登録 " +
      escapeHtml(fmtYen(battle.user.registered)) +
      " · 払戻 " +
      escapeHtml(fmtYen(battle.user.payout)) +
      "</span></div>" +
      '<div class="uc-result-total-row"><span>' +
      escapeHtml(RESULT_OPPONENT_DISPLAY_NAME) +
      "</span>" +
      "<span>登録 " +
      escapeHtml(fmtYen(battle.ai.registered)) +
      " · 払戻 " +
      escapeHtml(fmtYen(battle.ai.payout)) +
      "</span></div></section>" +
      (betRows
        ? '<section class="uc-battle-bets">' +
          "<h3>買い目別結果</h3>" +
          '<button type="button" class="uc-bet-details-toggle" data-uc-bet-details aria-expanded="false">' +
          '詳細を見る <span aria-hidden="true">▽</span></button>' +
          '<div class="uc-bet-details-panel" hidden>' +
          betRows +
          "</div></section>"
        : "") +
      '<p class="uc-result-footnote">※ 払戻は確定した公式結果に基づくものです</p>' +
      '<div class="uc-result-viewed-status" data-uc-viewed-status hidden></div>' +
      '<button type="button" class="uc-result-close-btn" data-uc-battle-close>閉じる</button>' +
      "</div></div>";

    function setViewedStatus(html, isError) {
      var el = root.querySelector("[data-uc-viewed-status]");
      if (!el) return;
      el.hidden = !html;
      el.className =
        "uc-result-viewed-status" + (isError ? " is-error" : "");
      el.innerHTML = html || "";
    }

    function onRevealCompleted() {
      // ui-test: frontend-only pending consume — never call real viewed API
      if (!isReal || isUiTestRaceId(raceId)) {
        _pendingConsumeRaceIds[raceId] = true;
        _pendingConsumeBattles[raceId] = battle;
        setViewedStatus(
          "UIテスト: 閉じると Active から外れ、月次/週次フィクスチャに反映します（API未送信）",
          false
        );
        return;
      }
      if (
        !(
          global.ExpectChallengeLifecycle &&
          ExpectChallengeLifecycle.markViewedAfterReveal
        )
      ) {
        return;
      }
      setViewedStatus("結果反映を同期中…", false);
      ExpectChallengeLifecycle.markViewedAfterReveal(raceId)
        .then(function (res) {
          _pendingConsumeRaceIds[raceId] = true;
          setViewedStatus(
            res && res.already_consumed
              ? "結果は反映済みです"
              : "結果を User Challenge に反映しました",
            false
          );
          ExpectChallengeLifecycle.refreshAggregates();
        })
        .catch(function (err) {
          setViewedStatus(
            '<span>結果の同期に失敗しました。表示はそのままです。</span> ' +
              '<button type="button" class="uc-result-retry-viewed" data-uc-retry-viewed>' +
              "再試行</button>" +
              '<span class="muted"> ' +
              escapeHtml((err && err.message) || "") +
              "</span>",
            true
          );
        });
    }

    function close() {
      root.remove();
      document.body.classList.remove("is-fav-dialog");
      document.removeEventListener("keydown", onKey);
      var closedId = _modalOpenRaceId;
      _modalOpenRaceId = null;
      // Remove from active list only after modal close (avoid layout jump under modal).
      if (closedId && _pendingConsumeRaceIds[closedId]) {
        delete _pendingConsumeRaceIds[closedId];
        var pendingBattle = _pendingConsumeBattles[closedId];
        delete _pendingConsumeBattles[closedId];
        if (isUiTestRaceId(closedId)) {
          applyUiTestConsumedFixture(
            closedId,
            pendingBattle || visualDummyBattle001()
          );
          deleteRace(closedId);
        }
        setTimeout(function () {
          if (
            global.ExpectChallengeDashboard &&
            typeof ExpectChallengeDashboard.refresh === "function"
          ) {
            ExpectChallengeDashboard.refresh();
          }
          if (typeof _savedRefresh === "function") _savedRefresh();
          else requestRefresh();
        }, 0);
      }
    }

    function onKey(e) {
      if (e.key === "Escape") close();
    }

    function showReveal() {
      root.querySelectorAll("[data-uc-reveal]").forEach(function (el) {
        el.classList.add("is-shown");
      });
      onRevealCompleted();
    }

    function runReveal() {
      var userBar = root.querySelector('[data-uc-bar="user"]');
      var aiBar = root.querySelector('[data-uc-bar="ai"]');
      if (reduceMotion) {
        if (userBar) userBar.style.width = userW + "%";
        if (aiBar) aiBar.style.width = aiW + "%";
        showReveal();
        return;
      }
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          if (userBar) userBar.style.width = userW + "%";
          if (aiBar) aiBar.style.width = aiW + "%";
        });
      });
      setTimeout(showReveal, 780);
    }

    root.addEventListener("click", function (e) {
      if (e.target.closest("[data-uc-battle-close]")) {
        close();
        return;
      }
      if (e.target.closest("[data-uc-retry-viewed]")) {
        e.preventDefault();
        onRevealCompleted();
        return;
      }
      var toggle = e.target.closest("[data-uc-bet-details]");
      if (toggle && root.contains(toggle)) {
        e.preventDefault();
        var panel = root.querySelector(".uc-bet-details-panel");
        if (!panel) return;
        var open = panel.hasAttribute("hidden");
        if (open) {
          panel.removeAttribute("hidden");
          toggle.setAttribute("aria-expanded", "true");
          toggle.innerHTML =
            '詳細を見る <span aria-hidden="true">∧</span>';
        } else {
          panel.setAttribute("hidden", "");
          toggle.setAttribute("aria-expanded", "false");
          toggle.innerHTML =
            '詳細を見る <span aria-hidden="true">▽</span>';
        }
      }
    });
    document.addEventListener("keydown", onKey);

    document.body.classList.add("is-fav-dialog");
    document.body.appendChild(root);
    runReveal();
    return true;
  }

  function navigateToChallengeResult(raceId) {
    var target =
      "saved.html?race_id=" +
      encodeURIComponent(raceId) +
      "&from=challenge-result";
    try {
      var path = String(location.pathname || "");
      var onChallenge =
        /(^|\/)saved(\.html)?\/?$/i.test(path) ||
        path.indexOf("/saved") !== -1;
      if (onChallenge) {
        markNotificationRead(raceId);
        refreshBell();
        history.replaceState({}, "", target);
        if (typeof _savedRefresh === "function") {
          _savedRefresh();
        } else {
          var el = document.getElementById("userChallengeEntrySection");
          // Accordion stays CLOSED — CTA is outside the panel.
          if (el) mount(el, { openRaceId: "", focusRaceId: raceId });
        }
        return;
      }
    } catch (e) {
      /* fall through */
    }
    location.href = target;
  }

  function raceAccordionItemHtml(entry, openRaceId, idx) {
    var id = "uc-acc-" + idx;
    var isOpen = !!(openRaceId && entry.race_id === openRaceId);
    var ready = isReadyStatus(entry.status);
    var statusCls = ready
      ? "user-challenge-race-status is-ready"
      : "user-challenge-race-status is-active";
    var allowDelete = canShowDeleteControls(entry);
    var betsHtml = entry.bets
      .map(function (bet, bidx) {
        return (
          '<article class="user-challenge-bet" data-bet-index="' +
          bidx +
          '">' +
          '<div class="user-challenge-bet-top">' +
          "<strong>" +
          escapeHtml(bet.bet_type) +
          "</strong>" +
          (allowDelete
            ? '<button type="button" class="user-challenge-del-x" data-uc-del-bet="' +
              bidx +
              '" data-race-id="' +
              escapeHtml(entry.race_id) +
              '" aria-label="この買い目のChallenge登録を削除">×</button>'
            : "") +
          "</div>" +
          '<div class="user-challenge-bet-body">' +
          selectionLinesHtml(bet) +
          "</div>" +
          '<p class="user-challenge-bet-amount">' +
          escapeHtml(fmtYen(bet.amount)) +
          "</p></article>"
        );
      })
      .join("");
    var cta = ready
      ? '<div class="user-challenge-ready-cta-wrap">' +
        '<button type="button" class="user-challenge-battle-cta" data-uc-battle="' +
        escapeHtml(entry.race_id) +
        '">Challenge結果</button></div>'
      : "";
    return (
      '<div class="board-acc-item user-challenge-acc-item' +
      (isOpen ? " is-open" : "") +
      (ready ? " is-result-ready" : "") +
      '" data-race-id="' +
      escapeHtml(entry.race_id) +
      '" data-status="' +
      escapeHtml(entry.status || STATUS_ACTIVE) +
      '" role="listitem">' +
      '<div class="user-challenge-acc-head">' +
      '<button type="button" class="board-acc-trigger user-challenge-acc-trigger" aria-expanded="' +
      (isOpen ? "true" : "false") +
      '" aria-controls="' +
      id +
      '" id="' +
      id +
      '-btn">' +
      '<span class="user-challenge-acc-main">' +
      '<span class="user-challenge-acc-place-row">' +
      '<span class="user-challenge-acc-place">' +
      escapeHtml(racePlace(entry) || entry.race_id) +
      "</span>" +
      '<span class="' +
      statusCls +
      '">' +
      escapeHtml(statusLabel(entry)) +
      "</span>" +
      "</span>" +
      '<span class="user-challenge-acc-name">' +
      escapeHtml(entry.race_name || "—") +
      "</span>" +
      (entry.post_time
        ? '<span class="user-challenge-acc-post">発走 ' +
          escapeHtml(entry.post_time) +
          "</span>"
        : "") +
      "</span>" +
      '<span class="board-acc-chevron" aria-hidden="true"></span>' +
      "</button>" +
      (allowDelete
        ? '<button type="button" class="user-challenge-del-x user-challenge-del-race" data-uc-del-race="' +
          escapeHtml(entry.race_id) +
          '" aria-label="' +
          escapeHtml((racePlace(entry) || entry.race_id) + "のChallenge登録をすべて削除") +
          '">×</button>'
        : "") +
      "</div>" +
      cta +
      '<div class="board-acc-panel user-challenge-acc-panel" id="' +
      id +
      '" role="region" aria-labelledby="' +
      id +
      '-btn" aria-hidden="' +
      (isOpen ? "false" : "true") +
      '">' +
      '<div class="board-acc-panel-inner">' +
      '<p class="user-challenge-kicker">登録した買い目の詳細</p>' +
      '<div class="user-challenge-bets">' +
      betsHtml +
      "</div>" +
      '<p class="user-challenge-race-total">レース登録金額 <strong>' +
      escapeHtml(fmtYen(raceTotal(entry))) +
      "</strong></p>" +
      "</div></div></div>"
    );
  }

  function collectionHtml(entries, opts) {
    opts = opts || {};
    var openRaceId = opts.openRaceId || "";
    var anyUiTest = entries.some(function (e) {
      return e.ui_test;
    });
    var anyActive = entries.some(function (e) {
      return !isReadyStatus(e.status);
    });
    var anyReady = entries.some(function (e) {
      return isReadyStatus(e.status);
    });
    var badges = "";
    if (anyActive) {
      badges +=
        '<span class="user-challenge-status-badge" aria-label="' +
        escapeHtml(ACTIVE_LABEL) +
        '">' +
        escapeHtml(ACTIVE_LABEL) +
        "</span>";
    }
    if (anyReady) {
      badges +=
        '<span class="user-challenge-status-badge is-ready" aria-label="' +
        escapeHtml(RESULT_READY_LABEL) +
        '">' +
        escapeHtml(RESULT_READY_LABEL) +
        "</span>";
    }
    if (anyUiTest) {
      badges +=
        '<span class="race-item-test-badge" aria-label="UIテスト">UIテスト</span>';
    }
    var list =
      '<div class="board-acc user-challenge-acc" role="list">' +
      entries
        .map(function (e, i) {
          return raceAccordionItemHtml(e, openRaceId, i);
        })
        .join("") +
      "</div>";
    var simBtn = "";
    if (anyUiTest) {
      var parts = [];
      if (anyActive) {
        parts.push(
          '<button type="button" class="user-challenge-sim-ready" data-uc-sim-ready>' +
            "結果確定をシミュレート（UIテスト）</button>"
        );
      }
      if (anyReady) {
        parts.push(
          '<span class="user-challenge-skip-wrap">' +
            '<button type="button" class="user-challenge-sim-ready" data-uc-sim-auto-consume>' +
            "結果表示をスキップ</button>" +
            '<span class="race-item-test-badge user-challenge-skip-badge" aria-label="UIテスト">UIテスト</span>' +
            "</span>"
        );
      }
      parts.push(
        '<button type="button" class="user-challenge-sim-ready is-reset" data-uc-sim-reset-active>' +
          "UIテストをACTIVEに戻す</button>"
      );
      simBtn = '<div class="user-challenge-sim-row">' + parts.join("") + "</div>";
    }
    return (
      '<div class="user-challenge-entry-head">' +
      "<h3>" +
      escapeHtml(resolveUserDisplayName()) +
      "（User Challenge）</h3>" +
      '<div class="user-challenge-badges">' +
      badges +
      "</div></div>" +
      '<p class="user-challenge-total user-challenge-global-total">合計登録金額 <strong>' +
      escapeHtml(fmtYen(globalTotal(entries))) +
      "</strong></p>" +
      list +
      simBtn +
      (anyUiTest
        ? '<p class="muted user-challenge-note">Frontend UIテスト用の登録内容です。AI成績・実成績には加算されません（API未送信・DB未書込・Settlement未発火）。</p>'
        : "")
    );
  }

  function bindAccordion(root) {
    if (!root || root.dataset.ucAccBound === "1") return;
    root.dataset.ucAccBound = "1";
    root.addEventListener("click", function (e) {
      if (e.target.closest(".user-challenge-del-x, .user-challenge-battle-cta, .user-challenge-sim-ready, .user-challenge-ready-cta-wrap")) {
        return;
      }
      var btn = e.target.closest(".board-acc-trigger");
      if (!btn || !root.contains(btn)) return;
      e.preventDefault();
      var item = btn.closest(".board-acc-item");
      if (!item) return;
      var willOpen = !item.classList.contains("is-open");
      root.querySelectorAll(".board-acc-item.is-open").forEach(function (other) {
        if (other === item) return;
        other.classList.remove("is-open");
        var ob = other.querySelector(".board-acc-trigger");
        var op = other.querySelector(".board-acc-panel");
        if (ob) ob.setAttribute("aria-expanded", "false");
        if (op) op.setAttribute("aria-hidden", "true");
      });
      var panel = item.querySelector(".board-acc-panel");
      item.classList.toggle("is-open", willOpen);
      btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      if (panel) panel.setAttribute("aria-hidden", willOpen ? "false" : "true");
    });
  }

  function queryTargetRaceId() {
    try {
      var sp = new URLSearchParams(location.search);
      var from = sp.get("from") || "";
      var raceId = sp.get("race_id") || "";
      if (
        (from === "challenge-entry" || from === "challenge-result") &&
        raceId
      ) {
        return raceId;
      }
    } catch (e) {
      /* ignore */
    }
    return "";
  }

  /**
   * Accordion auto-open is only for challenge-entry deep links.
   * from=challenge-result must keep accordion CLOSED (CTA is outside).
   */
  function queryOpenRaceId() {
    try {
      var sp = new URLSearchParams(location.search);
      var from = sp.get("from") || "";
      var raceId = sp.get("race_id") || "";
      if (from === "challenge-entry" && raceId) {
        return raceId;
      }
    } catch (e) {
      /* ignore */
    }
    return "";
  }

  function prefersReducedMotionScroll() {
    try {
      return !!(
        global.matchMedia &&
        global.matchMedia("(prefers-reduced-motion: reduce)").matches
      );
    } catch (e) {
      return false;
    }
  }

  /** Scroll target race into view; optional brief highlight. Never opens accordion/modal. */
  function focusTargetRace(raceId, opts) {
    opts = opts || {};
    if (!raceId) return false;
    var item = null;
    var nodes = document.querySelectorAll(".user-challenge-acc-item");
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].getAttribute("data-race-id") === String(raceId)) {
        item = nodes[i];
        break;
      }
    }
    if (!item) return false;
    try {
      item.scrollIntoView({
        behavior: prefersReducedMotionScroll() ? "auto" : "smooth",
        block: "center",
      });
    } catch (e1) {
      try {
        item.scrollIntoView(true);
      } catch (e2) {
        /* ignore */
      }
    }
    if (opts.highlight !== false) {
      item.classList.add("is-bell-target");
      if (!prefersReducedMotionScroll()) {
        global.setTimeout(function () {
          try {
            item.classList.remove("is-bell-target");
          } catch (e3) {
            /* ignore */
          }
        }, 1800);
      } else {
        global.setTimeout(function () {
          try {
            item.classList.remove("is-bell-target");
          } catch (e4) {
            /* ignore */
          }
        }, 400);
      }
    }
    return true;
  }

  function scheduleFocusTargetRace(raceId) {
    if (!raceId) return;
    global.setTimeout(function () {
      focusTargetRace(raceId, { highlight: true });
    }, 80);
  }

  function maybeAutoSimResult() {
    try {
      var sp = new URLSearchParams(location.search);
      if (sp.get("ui_test_flow") === "1" || sp.get("ui_test_reset") === "1") {
        resetUiTestActiveFixture();
      }
      var lockMode = sp.get("ui_test_delete_lock");
      if (lockMode != null && lockMode !== "") {
        var probe = findEntry(UI_TEST_RACE_ID) || standardActiveUiTestEntry();
        var postAt = parseEntryPostAt(probe);
        if (postAt) {
          if (lockMode === "locked" || lockMode === "1" || lockMode === "after") {
            setUiTestClock(postAt.getTime() - 4 * 60 * 1000);
          } else if (
            lockMode === "before" ||
            lockMode === "0" ||
            lockMode === "open"
          ) {
            setUiTestClock(postAt.getTime() - 6 * 60 * 1000);
          }
        }
      }
      var nowIso = sp.get("ui_test_now");
      if (nowIso) setUiTestClock(nowIso);
      var sim = sp.get("challenge_result_sim");
      if (sim) markResultReady(sim);
      var auto = sp.get("ui_test_auto_consume");
      if (auto === "1" || auto === UI_TEST_RACE_ID) {
        simulateAutoConsumeUiTest(UI_TEST_RACE_ID);
      }
      // from=challenge-result: scroll target CLOSED; never auto-open modal/accordion
    } catch (e) {
      /* ignore */
    }
  }

  function mount(container, opts) {
    if (!container) return false;
    opts = opts || {};
    var entries = sortEntries(
      filterByMonth(opts.entries || mergedActiveEntries(), opts.month || null)
    );
    // Keep modal race visible while open even if backend already CONSUMED.
    if (_modalOpenRaceId) {
      var still = entries.some(function (e) {
        return e.race_id === _modalOpenRaceId;
      });
      if (!still) {
        var held = findEntry(_modalOpenRaceId);
        if (held) entries = entries.concat([held]);
      }
    }
    if (!entries.length) {
      container.hidden = true;
      container.innerHTML = "";
      return false;
    }
    var openRaceId =
      opts.openRaceId != null ? opts.openRaceId : queryOpenRaceId();
    container.hidden = false;
    container.innerHTML = collectionHtml(entries, { openRaceId: openRaceId });
    bindAccordion(container.querySelector(".user-challenge-acc"));
    var targetId = opts.focusRaceId != null ? opts.focusRaceId : queryTargetRaceId();
    if (targetId) scheduleFocusTargetRace(targetId);
    return true;
  }

  function bindActions(container) {
    if (!container || container.dataset.ucActionsBound === "1") return;
    container.dataset.ucActionsBound = "1";
    container.addEventListener("click", function (e) {
      var delBet = e.target.closest("[data-uc-del-bet]");
      if (delBet && container.contains(delBet)) {
        e.preventDefault();
        e.stopPropagation();
        var raceId = delBet.getAttribute("data-race-id");
        var bidx = Number(delBet.getAttribute("data-uc-del-bet"));
        openConfirmDialog({
          title: "この買い目のChallenge登録を削除しますか？",
          body: "Challenge登録からの削除です。他の買い目は残ります。",
          okLabel: "削除する",
          onConfirm: function () {
            deleteBet(raceId, bidx);
            requestRefresh();
          },
        });
        return;
      }

      var delRace = e.target.closest("[data-uc-del-race]");
      if (delRace && container.contains(delRace)) {
        e.preventDefault();
        e.stopPropagation();
        var rid = delRace.getAttribute("data-uc-del-race");
        var entry = findEntry(rid);
        var place = entry ? racePlace(entry) || rid : rid;
        openConfirmDialog({
          title: place + "のChallenge登録をすべて削除しますか？",
          body: "このレースに登録されている買い目をすべて削除します。",
          okLabel: "削除する",
          onConfirm: function () {
            deleteRace(rid);
            requestRefresh();
          },
        });
        return;
      }

      var battleBtn = e.target.closest("[data-uc-battle]");
      if (battleBtn && container.contains(battleBtn)) {
        e.preventDefault();
        e.stopPropagation();
        openBattleModal(battleBtn.getAttribute("data-uc-battle"));
        return;
      }

      var sim = e.target.closest("[data-uc-sim-ready]");
      if (sim && container.contains(sim)) {
        e.preventDefault();
        e.stopPropagation();
        var col = loadCollection();
        if (!col) {
          resetUiTestActiveFixture();
          col = loadCollection();
        }
        if (!col) return;
        var target = null;
        for (var i = 0; i < col.entries.length; i++) {
          if (col.entries[i].ui_test && !isReadyStatus(col.entries[i].status)) {
            target = col.entries[i];
            break;
          }
        }
        if (!target) {
          resetUiTestActiveFixture();
          target = findEntry(UI_TEST_RACE_ID);
        }
        if (!target) return;
        markResultReady(target.race_id);
        return;
      }

      var autoSim = e.target.closest("[data-uc-sim-auto-consume]");
      if (autoSim && container.contains(autoSim)) {
        e.preventDefault();
        e.stopPropagation();
        simulateAutoConsumeUiTest(UI_TEST_RACE_ID);
        return;
      }

      var resetSim = e.target.closest("[data-uc-sim-reset-active]");
      if (resetSim && container.contains(resetSim)) {
        e.preventDefault();
        e.stopPropagation();
        resetUiTestActiveFixture();
      }
    });
  }

  function bindSavedPage(container) {
    if (!container) return;
    var state = {
      month: currentMonth(),
    };
    function paintLocal() {
      var labelEl = document.querySelector(".ledger-month-nav-label");
      if (labelEl && labelEl.textContent && labelEl.textContent !== "—") {
        state.month = parseMonthLabel(labelEl.textContent);
      }
      mount(container, {
        month: state.month,
        openRaceId: queryOpenRaceId() || "",
        focusRaceId: queryTargetRaceId() || undefined,
      });
      refreshBell();
    }
    function refresh() {
      paintLocal();
      var jobs = [];
      if (
        global.ExpectChallengeLifecycle &&
        ExpectChallengeLifecycle.isAuthenticated &&
        ExpectChallengeLifecycle.isAuthenticated()
      ) {
        jobs.push(
          ExpectChallengeLifecycle.fetchActiveEntries().then(function (entries) {
            _realEntries = entries || [];
          })
        );
        jobs.push(
          ExpectChallengeLifecycle.fetchChallengeNotifications().then(
            function (list) {
              setRealNotifs(list || []);
            }
          )
        );
      } else {
        _realEntries = [];
        setRealNotifs([]);
      }
      if (!jobs.length) {
        paintLocal();
        return;
      }
      Promise.all(jobs).then(function () {
        paintLocal();
      });
    }
    _savedRefresh = refresh;
    bindActions(container);
    maybeAutoSimResult();
    refresh();
    var prev = document.querySelector("[data-ledger-prev]");
    var next = document.querySelector("[data-ledger-next]");
    function afterMonthNav() {
      setTimeout(refresh, 0);
    }
    if (prev) prev.addEventListener("click", afterMonthNav);
    if (next) next.addEventListener("click", afterMonthNav);
  }

  function mergeFixtureEntries(fixtureEntries) {
    var col = loadCollection() || {
      schema_version: SCHEMA_VERSION,
      ui_test: true,
      entries: [],
    };
    var map = {};
    col.entries.forEach(function (e) {
      map[e.race_id] = e;
    });
    (fixtureEntries || []).forEach(function (raw) {
      var n = normalizeRaceEntry(raw);
      if (!n) return;
      if (!map[n.race_id]) map[n.race_id] = n;
    });
    var entries = Object.keys(map).map(function (k) {
      return map[k];
    });
    return saveCollection({
      schema_version: SCHEMA_VERSION,
      ui_test: true,
      entries: entries,
    });
  }

  function aiChallengeHref(opts) {
    opts = opts || {};
    var q = [];
    if (opts.raceId) q.push("race_id=" + encodeURIComponent(opts.raceId));
    if (opts.from) q.push("from=" + encodeURIComponent(opts.from));
    return "saved.html" + (q.length ? "?" + q.join("&") : "");
  }

  function challengeNotifListHtml() {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.renderListHtml === "function"
    ) {
      return ExpectChallengeNotifications.renderListHtml() || "";
    }
    return "";
  }

  function bindChallengeNotifList(listEl) {
    if (
      global.ExpectChallengeNotifications &&
      typeof ExpectChallengeNotifications.bindList === "function"
    ) {
      ExpectChallengeNotifications.bindList(listEl);
    }
  }

  // ExpectChallengeNotifications is owned by challenge-notifications.js (global).

  global.ExpectUiTestChallengeEntry = {
    SCHEMA_VERSION: SCHEMA_VERSION,
    STORAGE_KEY: STORAGE_KEY,
    SCHEMA_URL: SCHEMA_URL,
    ACTIVE_LABEL: ACTIVE_LABEL,
    RESULT_READY_LABEL: RESULT_READY_LABEL,
    STATUS_ACTIVE: STATUS_ACTIVE,
    STATUS_RESULT_READY: STATUS_RESULT_READY,
    STATUS_READY: STATUS_READY,
    isReadyStatus: isReadyStatus,
    save: save,
    saveCollection: saveCollection,
    load: load,
    loadCollection: loadCollection,
    clear: clear,
    normalize: normalizeRaceEntry,
    normalizeCollection: normalizeCollection,
    buildFromStock: buildFromStock,
    mount: mount,
    bindSavedPage: bindSavedPage,
    mergeFixtureEntries: mergeFixtureEntries,
    globalTotal: globalTotal,
    raceTotal: raceTotal,
    deleteBet: deleteBet,
    deleteRace: deleteRace,
    canShowDeleteControls: canShowDeleteControls,
    isDeleteLocked: isDeleteLocked,
    setUiTestClock: setUiTestClock,
    DELETE_LOCK_MINUTES: DELETE_LOCK_MINUTES,
    markResultReady: markResultReady,
    openBattleModal: openBattleModal,
    navigateToChallengeResult: navigateToChallengeResult,
    visualDummyBattleVariant: visualDummyBattleVariant,
    resolveWinner: resolveWinner,
    defaultBattleFixture: defaultBattleFixture,
    aiChallengeHref: aiChallengeHref,
    findEntry: findEntry,
    mergedActiveEntries: mergedActiveEntries,
    getAggregateOverlay: readAggregateOverlay,
    clearAggregateOverlay: clearAggregateOverlay,
    applyUiTestConsumedFixture: applyUiTestConsumedFixture,
    resetUiTestActiveFixture: resetUiTestActiveFixture,
    simulateAutoConsumeUiTest: simulateAutoConsumeUiTest,
    standardActiveUiTestEntry: standardActiveUiTestEntry,
    resolveUserDisplayName: resolveUserDisplayName,
    UI_TEST_RACE_ID: UI_TEST_RACE_ID,
  };
})(window);
