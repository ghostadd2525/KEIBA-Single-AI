/**
 * ExpectChallengeLifecycle — V7 real-user Challenge lifecycle client
 *
 * Backend authority (V6): ACTIVE → READY → CONSUMED
 * ui-test-race-* must never call lifecycle / notification / settlement APIs.
 */
(function (global) {
  "use strict";

  var NOTIF_KIND = "CHALLENGE_RESULT_READY";
  var STATUS_ACTIVE = "ACTIVE";
  var STATUS_READY = "READY";
  var STATUS_CONSUMED = "CONSUMED";

  function isUiTestRaceId(raceId) {
    if (
      global.ExpectUiTestRace &&
      typeof ExpectUiTestRace.isUiTestRaceId === "function"
    ) {
      return !!ExpectUiTestRace.isUiTestRaceId(raceId);
    }
    return String(raceId || "").indexOf("ui-test-race-") === 0;
  }

  function isAuthenticated() {
    try {
      if (global.ExpectAuth && typeof ExpectAuth.isLoggedIn === "function") {
        return !!ExpectAuth.isLoggedIn();
      }
    } catch (e) {
      /* ignore */
    }
    try {
      return !!(
        global.localStorage &&
        localStorage.getItem("expect_access_token_v1")
      );
    } catch (e2) {
      return false;
    }
  }

  function parsePayload(raw) {
    if (!raw) return {};
    if (typeof raw === "object") return raw;
    try {
      return JSON.parse(String(raw)) || {};
    } catch (e) {
      return {};
    }
  }

  function legsDisplay(tickets, ordered) {
    if (!Array.isArray(tickets) || !tickets.length) return "";
    return tickets
      .map(function (t) {
        var legs = t.legs || [];
        return legs.join(ordered ? " → " : " - ");
      })
      .filter(Boolean)
      .join(" / ");
  }

  function betsFromSnapshot(item) {
    item = item || {};
    var snap = item.strategy_snapshot || {};
    var betsObj = snap.bets || {};
    var axis = snap.axis || {};
    var rivals = Array.isArray(snap.rivals) ? snap.rivals : [];
    var orderedTypes = { 馬単: 1, 三連単: 1 };
    var out = [];
    Object.keys(betsObj).forEach(function (betType) {
      var spec = betsObj[betType] || {};
      var amount = Number(spec.amount) || 0;
      var ordered = !!orderedTypes[betType];
      var selections = [];
      if (axis && (axis.num != null || axis.horse_number != null)) {
        selections.push({
          horse_number: Number(axis.num != null ? axis.num : axis.horse_number),
          horse_name: String(axis.name || ""),
        });
      }
      rivals.forEach(function (r) {
        if (!r || typeof r !== "object") return;
        var n = r.num != null ? r.num : r.horse_number;
        if (n == null) return;
        selections.push({
          horse_number: Number(n),
          horse_name: String(r.name || r.horse_name || ""),
        });
      });
      out.push({
        bet_type: String(betType),
        ordered: ordered,
        legs_display: legsDisplay(spec.tickets, ordered) || "",
        selections: selections,
        amount: amount,
      });
    });
    if (!out.length && Array.isArray(item.selected_bet_types)) {
      item.selected_bet_types.forEach(function (bt) {
        out.push({
          bet_type: String(bt),
          ordered: false,
          legs_display: "",
          selections: [],
          amount: Number(item.unit_stake) || 0,
        });
      });
    }
    return out;
  }

  function parseRaceLabel(label) {
    var s = String(label || "");
    var m = s.match(/^(.+?)\s*(\d+)\s*R(?:\s+(.+))?$/i);
    if (m) {
      return {
        venue: m[1].trim(),
        race_number: m[2] + "R",
        race_name: (m[3] || "").trim(),
      };
    }
    return { venue: s, race_number: "", race_name: "" };
  }

  function entryFromLifecycleAndResult(life, resultPayload) {
    if (!life || !life.race_id) return null;
    if (isUiTestRaceId(life.race_id)) return null;
    var item =
      (resultPayload && (resultPayload.user_result || resultPayload.item)) ||
      null;
    if (!item || !item.purchase_registered) return null;
    var parsed = parseRaceLabel(item.race_label);
    var status =
      String(life.status || STATUS_ACTIVE).toUpperCase() === STATUS_READY
        ? STATUS_READY
        : STATUS_ACTIVE;
    var bets = betsFromSnapshot(item);
    var total =
      Number(item.purchase_amount) ||
      bets.reduce(function (s, b) {
        return s + (Number(b.amount) || 0);
      }, 0);
    return {
      race_id: String(life.race_id),
      ui_test: false,
      real_lifecycle: true,
      race_date: item.race_date != null ? String(item.race_date) : null,
      venue: parsed.venue || "",
      race_number: parsed.race_number || "",
      race_name: parsed.race_name || item.race_label || "",
      post_time: item.post_time || item.postTime || "",
      registered_at: item.registered_at || null,
      total_registered_amount: total,
      status: status,
      bets: bets,
      lifecycle: {
        status: status,
        result_ready_at: life.result_ready_at || null,
        result_viewed_at: life.result_viewed_at || null,
        consumed_at: life.consumed_at || null,
      },
      // No battle / financial spoilers on READY accordion cards.
    };
  }

  function battleBetRowsFromUser(item) {
    item = item || {};
    var snap = item.strategy_snapshot || {};
    var betsObj = snap.bets || {};
    var results = item.bet_results || {};
    var orderedTypes = { 馬単: 1, 三連単: 1 };
    var rows = [];
    Object.keys(betsObj).forEach(function (betType) {
      var spec = betsObj[betType] || {};
      var res = results[betType] || {};
      var amount = Number(
        res.purchase_amount != null ? res.purchase_amount : spec.amount
      ) || 0;
      var payout = Number(res.payout_amount != null ? res.payout_amount : 0) || 0;
      var profit =
        res.profit != null ? Number(res.profit) : payout - amount;
      var hit = !!(res.hit || (res.hit_tickets && res.hit_tickets.length));
      rows.push({
        bet_type: String(betType),
        legs_display: legsDisplay(spec.tickets, !!orderedTypes[betType]),
        amount: amount,
        payout: payout,
        profit: profit,
        result_label: hit ? "的中" : "はずれ",
      });
    });
    return rows;
  }

  /**
   * Build modal battle from authoritative getRaceResult payload.
   * Returns { ok, battle } or { ok:false, reason }.
   */
  function buildBattleFromRaceResult(payload) {
    if (!payload || typeof payload !== "object") {
      return { ok: false, reason: "missing_result_payload" };
    }
    var item = payload.user_result || payload.item;
    if (!item || !item.purchase_registered) {
      return { ok: false, reason: "purchase_not_registered" };
    }
    if (!item.settled) {
      return { ok: false, reason: "not_settled" };
    }
    var ai = payload.ai_theory;
    if (!ai || ai.purchase_amount == null || ai.payout_amount == null) {
      return { ok: false, reason: "gamemaster_comparator_missing" };
    }
    var userReg = Number(item.purchase_amount) || 0;
    var userPay = Number(item.payout_amount) || 0;
    var userProfit =
      item.profit != null ? Number(item.profit) : userPay - userReg;
    var aiReg = Number(ai.purchase_amount) || 0;
    var aiPay = Number(ai.payout_amount) || 0;
    var aiProfit = ai.profit != null ? Number(ai.profit) : aiPay - aiReg;
    var winner =
      userProfit > aiProfit ? "USER" : userProfit < aiProfit ? "AI" : "DRAW";
    return {
      ok: true,
      battle: {
        user: {
          registered: userReg,
          payout: userPay,
          profit: userProfit,
          bets: battleBetRowsFromUser(item),
        },
        ai: {
          registered: aiReg,
          payout: aiPay,
          profit: aiProfit,
          source: String(ai.source || "AI_THEORY_FROZEN"),
        },
        winner: winner,
      },
      user_result: item,
      ai_theory: ai,
    };
  }

  function mapNotification(row) {
    if (!row) return null;
    var kind = String(row.kind || row.notification_type || "");
    if (kind !== NOTIF_KIND) return null;
    var payload = parsePayload(row.payload_json || row.payload);
    var raceId = String(payload.race_id || "");
    if (!raceId || isUiTestRaceId(raceId)) return null;
    return {
      id: String(row.id),
      notification_id: row.id,
      notification_type: NOTIF_KIND,
      race_id: raceId,
      title: row.title || "Challenge結果が確定しました",
      venue_line: payload.venue_line || raceId,
      race_name: payload.race_name || "",
      body: "Game Masterとの結果を確認できます",
      read: !!(row.read_at || row.read),
      created_at: row.created_at || null,
      href: payload.href || null,
    };
  }

  function fetchActiveEntries() {
    if (!isAuthenticated()) return Promise.resolve([]);
    if (
      !(
        global.ExpectApi &&
        ExpectApi.User &&
        ExpectApi.User.challengeActive &&
        ExpectApi.User.getRaceResult
      )
    ) {
      return Promise.resolve([]);
    }
    return ExpectApi.User.challengeActive()
      .then(function (data) {
        var items = (data && data.items) || [];
        var jobs = items
          .filter(function (life) {
            return life && life.race_id && !isUiTestRaceId(life.race_id);
          })
          .map(function (life) {
            return ExpectApi.User.getRaceResult(life.race_id)
              .then(function (payload) {
                return entryFromLifecycleAndResult(life, payload);
              })
              .catch(function () {
                return null;
              });
          });
        return Promise.all(jobs);
      })
      .then(function (entries) {
        return (entries || []).filter(Boolean);
      })
      .catch(function () {
        return [];
      });
  }

  function fetchChallengeNotifications() {
    if (!isAuthenticated()) return Promise.resolve([]);
    if (!(global.ExpectApi && ExpectApi.User && ExpectApi.User.notifications)) {
      return Promise.resolve([]);
    }
    return ExpectApi.User.notifications(40)
      .then(function (data) {
        var items = (data && data.items) || [];
        return items.map(mapNotification).filter(Boolean);
      })
      .catch(function () {
        return [];
      });
  }

  function markNotificationRead(notificationId) {
    if (notificationId == null || notificationId === "") {
      return Promise.resolve(false);
    }
    if (isUiTestRaceId(String(notificationId))) {
      return Promise.resolve(false);
    }
    if (
      !(
        global.ExpectApi &&
        ExpectApi.User &&
        ExpectApi.User.notificationMarkRead
      )
    ) {
      return Promise.resolve(false);
    }
    return ExpectApi.User.notificationMarkRead(notificationId)
      .then(function () {
        return true;
      })
      .catch(function () {
        return false;
      });
  }

  function markViewedAfterReveal(raceId) {
    if (!raceId || isUiTestRaceId(raceId)) {
      return Promise.resolve({ skipped: true, reason: "ui_test_isolated" });
    }
    if (
      !(
        global.ExpectApi &&
        ExpectApi.User &&
        ExpectApi.User.challengeLifecycleViewed
      )
    ) {
      return Promise.reject(new Error("lifecycle API unavailable"));
    }
    return ExpectApi.User.challengeLifecycleViewed(raceId, {
      reveal_completed: true,
    });
  }

  function refreshAggregates() {
    if (
      global.ExpectChallengeDashboard &&
      typeof ExpectChallengeDashboard.refresh === "function"
    ) {
      ExpectChallengeDashboard.refresh();
    }
  }

  global.ExpectChallengeLifecycle = {
    NOTIF_KIND: NOTIF_KIND,
    STATUS_ACTIVE: STATUS_ACTIVE,
    STATUS_READY: STATUS_READY,
    STATUS_CONSUMED: STATUS_CONSUMED,
    isUiTestRaceId: isUiTestRaceId,
    isAuthenticated: isAuthenticated,
    entryFromLifecycleAndResult: entryFromLifecycleAndResult,
    buildBattleFromRaceResult: buildBattleFromRaceResult,
    mapNotification: mapNotification,
    fetchActiveEntries: fetchActiveEntries,
    fetchChallengeNotifications: fetchChallengeNotifications,
    markNotificationRead: markNotificationRead,
    markViewedAfterReveal: markViewedAfterReveal,
    refreshAggregates: refreshAggregates,
    betsFromSnapshot: betsFromSnapshot,
  };
})(typeof window !== "undefined" ? window : globalThis);
