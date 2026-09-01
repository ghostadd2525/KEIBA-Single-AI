/**
 * ExpectUserRaceResults — purchase register, monthly ledger, result tab
 * User P&L only (AI stats are separate).
 */
(function (global) {
  "use strict";

  var BET_TYPES = ["単勝", "複勝", "馬連", "馬単", "ワイド", "三連複", "三連単"];
  var PRESETS = [100, 300, 500, 1000];
  /** Official max from app_settings max_purchase_amount_per_race (migration 010). */
  var OFFICIAL_MAX_PURCHASE_AMOUNT_PER_RACE = 50000;
  var MIN_UNIT_STAKE = 100;
  var UNIT_STAKE_STEP = 100;

  /**
   * Shared Challenge / purchase unit amount validator (FE + contract tests).
   * @param {*} raw
   * @param {number} [maxAmount]
   * @returns {{ok:boolean, amount?:number, code?:string, message?:string}}
   */
  function validateChallengeUnitAmount(raw, maxAmount) {
    var maxN = Number(maxAmount);
    if (!Number.isFinite(maxN) || maxN < MIN_UNIT_STAKE) {
      maxN = OFFICIAL_MAX_PURCHASE_AMOUNT_PER_RACE;
    }
    if (raw == null) {
      return {
        ok: false,
        code: "empty",
        message: "購入金額を入力してください",
      };
    }
    if (typeof raw === "number") {
      if (!Number.isFinite(raw)) {
        return {
          ok: false,
          code: "non_numeric",
          message: "購入金額は数字で入力してください",
        };
      }
      if (!Number.isInteger(raw)) {
        return {
          ok: false,
          code: "decimal",
          message: "購入金額は整数で入力してください",
        };
      }
      if (raw < 0) {
        return {
          ok: false,
          code: "negative",
          message: "購入金額は100円以上で入力してください",
        };
      }
      if (raw === 0 || raw < MIN_UNIT_STAKE) {
        return {
          ok: false,
          code: "below_min",
          message: "購入金額は100円以上で入力してください",
        };
      }
      if (raw % UNIT_STAKE_STEP !== 0) {
        return {
          ok: false,
          code: "non_step",
          message: "購入金額は100円単位で入力してください",
        };
      }
      if (raw > maxN) {
        return {
          ok: false,
          code: "over_max",
          message:
            "購入金額は" +
            maxN.toLocaleString("ja-JP") +
            "円以下で入力してください",
        };
      }
      return { ok: true, amount: raw };
    }
    var s = String(raw).trim();
    if (!s) {
      return {
        ok: false,
        code: "empty",
        message: "購入金額を入力してください",
      };
    }
    if (/[.]/.test(s) || /[eE]/.test(s)) {
      return {
        ok: false,
        code: "decimal",
        message: "購入金額は整数で入力してください",
      };
    }
    if (/^[-+]/.test(s) || /[^\d]/.test(s)) {
      if (/[-]/.test(s)) {
        return {
          ok: false,
          code: "negative",
          message: "購入金額は100円以上で入力してください",
        };
      }
      return {
        ok: false,
        code: "non_numeric",
        message: "購入金額は数字で入力してください",
      };
    }
    var n = Number(s);
    if (!Number.isFinite(n) || !Number.isInteger(n)) {
      return {
        ok: false,
        code: "non_numeric",
        message: "購入金額は数字で入力してください",
      };
    }
    return validateChallengeUnitAmount(n, maxN);
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtYen(n, withSign) {
    var v = Math.round(Number(n) || 0);
    var abs = "¥" + Math.abs(v).toLocaleString("ja-JP");
    if (!withSign) return abs;
    if (v > 0) return "+" + abs;
    if (v < 0) return "-" + abs;
    return abs;
  }

  function pct(n) {
    return n == null || !Number.isFinite(Number(n)) ? "—" : Math.round(Number(n) * (Number(n) <= 1 ? 100 : 1)) + "%";
  }

  function monthLabel(ym) {
    var parts = String(ym || "").split("-");
    if (parts.length !== 2) return ym || "";
    return parts[0] + "年" + Number(parts[1]) + "月";
  }

  function shiftMonth(ym, delta) {
    var parts = String(ym).split("-").map(Number);
    var d = new Date(parts[0], parts[1] - 1 + delta, 1);
    var m = d.getMonth() + 1;
    return d.getFullYear() + "-" + (m < 10 ? "0" : "") + m;
  }

  function currentMonth() {
    var d = new Date();
    var m = d.getMonth() + 1;
    return d.getFullYear() + "-" + (m < 10 ? "0" : "") + m;
  }

  function raceDateFromId(raceId) {
    var s = String(raceId || "");
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return m[1] + "-" + m[2] + "-" + m[3];
    m = s.match(/^(\d{4})(\d{2})(\d{2})/);
    if (m) return m[1] + "-" + m[2] + "-" + m[3];
    return null;
  }

  function estimatePoints(strategyData, betTypes) {
    var stakes = global.ExpectStrategyStakes;
    if (!stakes || !stakes.expandBetTickets) return 0;
    var axis = Number(strategyData && strategyData.axis && strategyData.axis.num);
    var rivals = ((strategyData && strategyData.rivals) || [])
      .map(function (r) {
        return Number(r.num);
      })
      .filter(function (n) {
        return Number.isFinite(n) && n >= 1;
      });
    var n = 0;
    (betTypes || []).forEach(function (bt) {
      var tickets = stakes.expandBetTickets(bt, 100, axis, rivals);
      n += (tickets && tickets.length) || 0;
    });
    return n;
  }

  function mountPurchaseForm(container, raceId, strategyData, meta) {
    if (!container) return;
    meta = meta || {};
    var defaultTypes = ((strategyData && strategyData.tickets) || []).map(function (t) {
      return t.type;
    });
    if (!defaultTypes.length) defaultTypes = ["馬連", "ワイド", "三連複"];

    container.innerHTML =
      '<section class="chart-card purchase-card" id="purchaseCard">' +
      "<h3>購入を登録（ユーザー成績）</h3>" +
      '<p class="muted">AI提案の買い目を選んで、実際の購入金額を記録します。後からAIが変わっても保存内容は変わりません。</p>' +
      '<div class="purchase-presets" role="group" aria-label="購入金額">' +
      PRESETS.map(function (n) {
        return (
          '<button type="button" class="purchase-preset' +
          (n === 100 ? " is-active" : "") +
          '" data-unit="' +
          n +
          '">' +
          n +
          "円</button>"
        );
      }).join("") +
      '<button type="button" class="purchase-preset" data-unit="other">その他</button>' +
      "</div>" +
      '<label class="purchase-other" hidden><span>任意金額（円）</span>' +
      '<input type="text" inputmode="numeric" pattern="[0-9]*" id="purchaseOtherInput" maxlength="6" /></label>' +
      '<div class="purchase-types" role="group" aria-label="購入券種">' +
      BET_TYPES.map(function (bt) {
        var on = defaultTypes.indexOf(bt) >= 0;
        return (
          '<label class="purchase-type"><input type="checkbox" value="' +
          escapeHtml(bt) +
          '"' +
          (on ? " checked" : "") +
          " /> " +
          escapeHtml(bt) +
          "</label>"
        );
      }).join("") +
      "</div>" +
      '<p class="purchase-summary" id="purchaseSummary">—</p>' +
      '<p class="purchase-msg muted" id="purchaseMsg" role="status"></p>' +
      '<button type="button" class="strategy-btn" id="purchaseSubmitBtn">購入を登録する</button>' +
      "</section>";

    var unit = 100;
    var other = false;

    function selectedTypes() {
      return Array.prototype.slice
        .call(container.querySelectorAll(".purchase-type input:checked"))
        .map(function (el) {
          return el.value;
        });
    }

    function currentUnit() {
      if (other) {
        var raw = String((document.getElementById("purchaseOtherInput") || {}).value || "").replace(/\D/g, "");
        var n = parseInt(raw, 10);
        return Number.isFinite(n) ? n : 0;
      }
      return unit;
    }

    function refreshSummary() {
      var u = currentUnit();
      var types = selectedTypes();
      var pts = estimatePoints(strategyData, types);
      var total = pts * Math.max(0, Math.floor(u / 100) * 100);
      var el = document.getElementById("purchaseSummary");
      if (el) {
        el.textContent =
          "点数 " + pts + "点 · 1点 " + fmtYen(Math.max(0, Math.floor(u / 100) * 100)) + " · 合計 " + fmtYen(total);
      }
    }

    container.querySelectorAll(".purchase-preset").forEach(function (btn) {
      btn.addEventListener("click", function () {
        container.querySelectorAll(".purchase-preset").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        var v = btn.getAttribute("data-unit");
        var otherLabel = container.querySelector(".purchase-other");
        if (v === "other") {
          other = true;
          if (otherLabel) otherLabel.hidden = false;
        } else {
          other = false;
          unit = Number(v);
          if (otherLabel) otherLabel.hidden = true;
        }
        refreshSummary();
      });
    });
    container.querySelectorAll(".purchase-type input").forEach(function (inp) {
      inp.addEventListener("change", refreshSummary);
    });
    var otherInput = document.getElementById("purchaseOtherInput");
    if (otherInput) {
      otherInput.addEventListener("input", function () {
        otherInput.value = String(otherInput.value || "").replace(/\D/g, "");
        refreshSummary();
      });
    }

    document.getElementById("purchaseSubmitBtn").addEventListener("click", function () {
      var msg = document.getElementById("purchaseMsg");
      var u = currentUnit();
      if (u < 100 || u % 100 !== 0) {
        if (msg) msg.textContent = "金額は100円単位で入力してください。";
        return;
      }
      var types = selectedTypes();
      if (!types.length) {
        if (msg) msg.textContent = "券種を1つ以上選んでください。";
        return;
      }
      var pts = estimatePoints(strategyData, types);
      var total = pts * u;
      var maxAmt = 50000;
      if (global.ExpectUserProgress && ExpectUserProgress.get && ExpectUserProgress.get()) {
        /* max from progress settings if loaded later */
      }
      if (total > maxAmt) {
        if (msg) msg.textContent = "1レースの上限（¥" + maxAmt.toLocaleString("ja-JP") + "）を超えています。";
        return;
      }

      function doRegister(confirmDivergence) {
        var msg = document.getElementById("purchaseMsg");
        if (
          global.ExpectUiTestRace &&
          ExpectUiTestRace.isUiTestRaceId &&
          ExpectUiTestRace.isUiTestRaceId(raceId)
        ) {
          if (msg) {
            msg.textContent =
              "UIテストレースのため実購入は登録されません（API未送信・DB未書込）。";
          }
          var btn = document.getElementById("purchaseSubmitBtn");
          if (btn) {
            btn.disabled = true;
            btn.textContent = "テスト確認済み（未登録）";
          }
          return;
        }
        if (msg) msg.textContent = "登録中…";
        if (!(global.ExpectApi && ExpectApi.User && ExpectApi.User.registerPurchase)) {
          if (msg) msg.textContent = "API を利用できません。";
          return;
        }
        ExpectApi.User.registerPurchase({
          race_id: raceId,
          race_date: meta.raceDate || raceDateFromId(raceId),
          race_label: meta.raceLabel || meta.place || null,
          prediction_version: meta.predictionVersion || null,
          unit_stake: u,
          bet_types: types,
          axis: strategyData.axis,
          rivals: strategyData.rivals,
          confirm_divergence: !!confirmDivergence,
        })
          .then(function (res) {
            if (res && res.needs_confirmation) {
              var ok = window.confirm(
                (res.message || "金額が理論額から乖離しています。登録しますか？") +
                  "\n\nAI買い目 " +
                  (res.ticket_points || pts) +
                  "点\n登録金額 " +
                  fmtYen(res.purchase_amount || total)
              );
              if (ok) return doRegister(true);
              if (msg) msg.textContent = "登録をキャンセルしました。";
              return;
            }
            if (msg) msg.textContent = "購入を登録しました。結果確定後にポイントが付与されます。";
            var btn = document.getElementById("purchaseSubmitBtn");
            if (btn) {
              btn.disabled = true;
              btn.textContent = "登録済み";
            }
          })
          .catch(function (err) {
            if (msg) msg.textContent = (err && err.message) || "登録に失敗しました。";
          });
      }

      doRegister(false);
    });

    refreshSummary();
  }

  /**
   * Challenge専用: 式別1択 → 必要頭数の馬選択 → 金額 → 確認
   * @param {HTMLElement} container
   * @param {string} raceId
   * @param {{horse_number:number, horse_name:string}[]} runners
   * @param {object} [meta]
   */
  function mountChallengeDynamicPurchaseForm(container, raceId, runners, meta) {
    if (!container) return;
    meta = meta || {};
    runners = Array.isArray(runners)
      ? runners
          .map(function (r) {
            return {
              horse_number: Number(r.horse_number),
              horse_name: String(r.horse_name || ""),
            };
          })
          .filter(function (r) {
            return Number.isFinite(r.horse_number) && r.horse_number >= 1;
          })
          .sort(function (a, b) {
            return a.horse_number - b.horse_number;
          })
      : [];

    var BET_SPECS = {
      単勝: { count: 1, labels: ["対象馬"], ordered: false },
      複勝: { count: 1, labels: ["対象馬"], ordered: false },
      馬連: { count: 2, labels: ["1頭目", "2頭目"], ordered: false },
      ワイド: { count: 2, labels: ["1頭目", "2頭目"], ordered: false },
      馬単: { count: 2, labels: ["1着", "2着"], ordered: true },
      三連複: { count: 3, labels: ["1頭目", "2頭目", "3頭目"], ordered: false },
      三連単: { count: 3, labels: ["1着", "2着", "3着"], ordered: true },
    };

    var isUiTest =
      global.ExpectUiTestRace &&
      ExpectUiTestRace.isUiTestRaceId &&
      ExpectUiTestRace.isUiTestRaceId(raceId);

    var state = {
      betType: "",
      picks: [],
      unit: null,
      other: false,
      stock: [],
      stockSeq: 0,
    };

    container.innerHTML =
      '<section class="chart-card purchase-card challenge-dyn-purchase" id="purchaseCard">' +
      "<h3>Challenge内容を登録</h3>" +
      '<div class="challenge-dyn-jra-notice" role="note">' +
      "<p>Challengeは予想した買い目と金額を登録して成績を競う機能です。実際の馬券購入は行われません。</p>" +
      "<p>馬券を購入する場合は、JRA公式サイト等で別途購入してください。</p>" +
      "</div>" +
      '<p class="muted">' +
      (isUiTest
        ? "UIテスト用です。買い目追加・Challenge参加を押しても Production への登録・DB書き込みは行いません。"
        : "式別・馬・金額を選んで買い目を追加し、Challengeに参加します。") +
      "</p>" +
      '<div class="challenge-dyn-step">' +
      '<p class="challenge-dyn-step-title">① 式別を選択</p>' +
      '<label class="challenge-dyn-field">' +
      '<span class="visually-hidden">式別</span>' +
      '<select id="challengeBetTypeSelect" class="challenge-dyn-select">' +
      '<option value="">式別を選択してください</option>' +
      BET_TYPES.map(function (bt) {
        return '<option value="' + escapeHtml(bt) + '">' + escapeHtml(bt) + "</option>";
      }).join("") +
      "</select></label></div>" +
      '<div class="challenge-dyn-step" id="challengeHorseStep" hidden>' +
      '<p class="challenge-dyn-step-title">② 馬を選択</p>' +
      '<div id="challengeHorseFields" class="challenge-dyn-horse-fields"></div></div>' +
      '<div class="challenge-dyn-step">' +
      '<p class="challenge-dyn-step-title">③ 金額を選択</p>' +
      '<div class="purchase-presets" role="group" aria-label="登録金額">' +
      PRESETS.map(function (n) {
        return (
          '<button type="button" class="purchase-preset" data-unit="' +
          n +
          '">' +
          n +
          "円</button>"
        );
      }).join("") +
      '<button type="button" class="purchase-preset" data-unit="other">その他</button>' +
      "</div>" +
      '<label class="purchase-other challenge-dyn-other" id="challengeOtherAmount" hidden>' +
      "<span>任意金額（円）</span>" +
      '<input type="text" inputmode="numeric" pattern="[0-9]*" id="purchaseOtherInput" maxlength="6" autocomplete="off" /></label>' +
      '<p class="challenge-dyn-amount-error" id="challengeAmountError" role="alert" hidden></p>' +
      "</div>" +
      '<button type="button" class="strategy-btn strategy-btn--ghost challenge-dyn-add" id="challengeAddBetBtn" disabled>買い目を追加</button>' +
      '<div class="challenge-dyn-step" id="challengeStockStep">' +
      '<p class="challenge-dyn-step-title">④ 登録する買い目</p>' +
      '<div class="challenge-dyn-stock" id="challengeBetStock" aria-live="polite"></div>' +
      '<p class="challenge-dyn-total" id="challengeStockTotal" hidden>合計登録金額 <strong></strong></p>' +
      "</div>" +
      '<p class="purchase-msg muted" id="purchaseMsg" role="status"></p>' +
      '<button type="button" class="strategy-btn challenge-dyn-submit" id="purchaseSubmitBtn" disabled>' +
      (isUiTest ? "Challengeに参加する（UIテスト）" : "Challengeに参加する") +
      "</button>" +
      '<div class="challenge-confirm-dialog" id="challengeConfirmDialog" hidden>' +
      '<div class="challenge-confirm-dialog__backdrop" data-challenge-confirm-cancel></div>' +
      '<div class="challenge-confirm-dialog__panel" role="dialog" aria-modal="true" aria-labelledby="challengeConfirmTitle">' +
      '<h3 id="challengeConfirmTitle">確認</h3>' +
      '<div class="challenge-confirm-dialog__body" id="challengeConfirmBody"></div>' +
      '<div class="challenge-confirm-dialog__actions">' +
      '<button type="button" class="strategy-btn strategy-btn--ghost" data-challenge-confirm-cancel>キャンセル</button>' +
      '<button type="button" class="strategy-btn" id="challengeConfirmSubmit">この内容で参加する</button>' +
      "</div></div></div>" +
      "</section>";

    var betSelect = container.querySelector("#challengeBetTypeSelect");
    var horseStep = container.querySelector("#challengeHorseStep");
    var horseFields = container.querySelector("#challengeHorseFields");
    var stockEl = container.querySelector("#challengeBetStock");
    var totalEl = container.querySelector("#challengeStockTotal");
    var addBtn = container.querySelector("#challengeAddBetBtn");
    var submitBtn = container.querySelector("#purchaseSubmitBtn");
    var msgEl = container.querySelector("#purchaseMsg");
    var otherLabel = container.querySelector("#challengeOtherAmount");
    var otherInput = container.querySelector("#purchaseOtherInput");
    var amountErrorEl = container.querySelector("#challengeAmountError");
    var confirmDialog = container.querySelector("#challengeConfirmDialog");
    var confirmBody = container.querySelector("#challengeConfirmBody");
    var confirmSubmitBtn = container.querySelector("#challengeConfirmSubmit");
    var maxUnitAmount = OFFICIAL_MAX_PURCHASE_AMOUNT_PER_RACE;
    var submitting = false;

    function runnerByNum(num) {
      var n = Number(num);
      for (var i = 0; i < runners.length; i++) {
        if (runners[i].horse_number === n) return runners[i];
      }
      return null;
    }

    function formatHorseOption(r) {
      return r.horse_number + "番 " + (r.horse_name || "");
    }

    function formatLegs(spec, picks) {
      var nums = picks.map(Number);
      if (spec.ordered) {
        return nums.join(" → ");
      }
      var sorted = nums.slice().sort(function (a, b) {
        return a - b;
      });
      if (sorted.length === 1) return String(sorted[0]);
      return sorted.join(" - ");
    }

    function selectionKey(spec, picks) {
      var nums = picks.map(Number);
      if (spec.ordered) return nums.join(">");
      return nums
        .slice()
        .sort(function (a, b) {
          return a - b;
        })
        .join("-");
    }

    function currentUnit() {
      if (state.other) {
        var raw = otherInput ? otherInput.value : "";
        var checked = validateChallengeUnitAmount(raw, maxUnitAmount);
        return checked.ok ? checked.amount : 0;
      }
      if (state.unit == null) return 0;
      return state.unit;
    }

    function amountValidation() {
      if (!state.other) {
        if (state.unit == null) {
          return { ok: false, code: "unset", message: "" };
        }
        return validateChallengeUnitAmount(state.unit, maxUnitAmount);
      }
      return validateChallengeUnitAmount(
        otherInput ? otherInput.value : "",
        maxUnitAmount
      );
    }

    function isAmountValid() {
      return amountValidation().ok;
    }

    function setAmountError(message) {
      if (!amountErrorEl) return;
      if (message) {
        amountErrorEl.hidden = false;
        amountErrorEl.textContent = message;
      } else {
        amountErrorEl.hidden = true;
        amountErrorEl.textContent = "";
      }
    }

    function isBuilderComplete() {
      var spec = BET_SPECS[state.betType];
      if (!spec) return false;
      if (state.picks.length !== spec.count) return false;
      for (var i = 0; i < state.picks.length; i++) {
        if (!state.picks[i]) return false;
      }
      var seen = {};
      for (var j = 0; j < state.picks.length; j++) {
        var key = String(state.picks[j]);
        if (seen[key]) return false;
        seen[key] = true;
      }
      return isAmountValid();
    }

    function buildDraftItem() {
      var spec = BET_SPECS[state.betType];
      if (!spec || !isBuilderComplete()) return null;
      var picks = state.picks.map(Number);
      var amtCheck = amountValidation();
      if (!amtCheck.ok) return null;
      var amount = amtCheck.amount;
      if (stockTotal() + amount > maxUnitAmount) {
        return null;
      }
      var lines = [];
      if (spec.ordered && picks.length > 1) {
        lines.push(formatLegs(spec, state.picks));
      } else {
        picks.forEach(function (n) {
          var r = runnerByNum(n);
          lines.push(r ? formatHorseOption(r) : n + "番");
        });
      }
      return {
        race_id: raceId,
        bet_type: state.betType,
        selection: picks,
        selection_key: selectionKey(spec, state.picks),
        selection_lines: lines,
        legs_display: formatLegs(spec, state.picks),
        amount: amount,
        ordered: !!spec.ordered,
      };
    }

    function isExactDuplicate(item) {
      for (var i = 0; i < state.stock.length; i++) {
        var s = state.stock[i];
        if (
          s.bet_type === item.bet_type &&
          s.selection_key === item.selection_key &&
          s.amount === item.amount
        ) {
          return true;
        }
      }
      return false;
    }

    function stockTotal() {
      var sum = 0;
      for (var i = 0; i < state.stock.length; i++) sum += state.stock[i].amount;
      return sum;
    }

    function setOtherVisible(show) {
      if (!otherLabel) return;
      otherLabel.hidden = !show;
      if (!show && otherInput) otherInput.value = "";
    }

    function resetBuilder() {
      state.betType = "";
      state.picks = [];
      state.unit = null;
      state.other = false;
      if (betSelect) betSelect.value = "";
      container.querySelectorAll(".purchase-preset").forEach(function (b) {
        b.classList.remove("is-active");
      });
      setOtherVisible(false);
      renderHorseFields();
    }

    function renderStock() {
      if (!stockEl) return;
      if (!state.stock.length) {
        stockEl.innerHTML =
          '<p class="challenge-dyn-stock-empty muted">まだ買い目がありません。式別・馬・金額を選んで追加してください。</p>';
        if (totalEl) totalEl.hidden = true;
      } else {
        stockEl.innerHTML = state.stock
          .map(function (item, idx) {
            var lines = (item.selection_lines || [])
              .map(function (line) {
                return "<div>" + escapeHtml(line) + "</div>";
              })
              .join("");
            return (
              '<article class="challenge-dyn-stock-item" data-stock-id="' +
              escapeHtml(String(item.id)) +
              '">' +
              '<div class="challenge-dyn-stock-head">' +
              "<strong>" +
              escapeHtml(String(idx + 1)) +
              "　" +
              escapeHtml(item.bet_type) +
              "</strong>" +
              '<button type="button" class="challenge-dyn-stock-remove" data-stock-id="' +
              escapeHtml(String(item.id)) +
              '">削除</button></div>' +
              '<div class="challenge-dyn-stock-body">' +
              lines +
              "</div>" +
              '<p class="challenge-dyn-stock-amount">' +
              escapeHtml(fmtYen(item.amount)) +
              "</p></article>"
            );
          })
          .join("");
        if (totalEl) {
          totalEl.hidden = false;
          var strong = totalEl.querySelector("strong");
          if (strong) strong.textContent = fmtYen(stockTotal());
        }
        stockEl.querySelectorAll(".challenge-dyn-stock-remove").forEach(function (btn) {
          btn.addEventListener("click", function () {
            var sid = String(btn.getAttribute("data-stock-id") || "");
            state.stock = state.stock.filter(function (it) {
              return String(it.id) !== sid;
            });
            if (msgEl) msgEl.textContent = "";
            renderStock();
            refreshUi();
          });
        });
      }
      refreshUi();
    }

    function renderHorseFields() {
      var spec = BET_SPECS[state.betType];
      if (!spec) {
        horseStep.hidden = true;
        horseFields.innerHTML = "";
        state.picks = [];
        refreshUi();
        return;
      }
      horseStep.hidden = false;
      if (state.picks.length !== spec.count) {
        state.picks = [];
        for (var z = 0; z < spec.count; z++) state.picks.push("");
      }
      var html = "";
      for (var i = 0; i < spec.count; i++) {
        var selected = String(state.picks[i] || "");
        var used = {};
        for (var j = 0; j < state.picks.length; j++) {
          if (j !== i && state.picks[j]) used[String(state.picks[j])] = true;
        }
        html +=
          '<label class="challenge-dyn-field">' +
          "<span>" +
          escapeHtml(spec.labels[i] || "馬") +
          "</span>" +
          '<select class="challenge-dyn-select challenge-dyn-horse" data-pick-index="' +
          i +
          '">' +
          '<option value="">馬を選択してください</option>';
        runners.forEach(function (r) {
          var val = String(r.horse_number);
          if (used[val] && val !== selected) return;
          html +=
            '<option value="' +
            escapeHtml(val) +
            '"' +
            (val === selected ? " selected" : "") +
            ">" +
            escapeHtml(formatHorseOption(r)) +
            "</option>";
        });
        html += "</select></label>";
      }
      horseFields.innerHTML = html;
      horseFields.querySelectorAll("select.challenge-dyn-horse").forEach(function (sel) {
        sel.addEventListener("change", function () {
          var idx = Number(sel.getAttribute("data-pick-index"));
          state.picks[idx] = sel.value || "";
          renderHorseFields();
        });
      });
      refreshUi();
    }

    function refreshUi() {
      var amt = amountValidation();
      var showAmtError = state.other && !amt.ok && String((otherInput && otherInput.value) || "").length > 0;
      setAmountError(showAmtError ? amt.message : "");
      if (addBtn) {
        var canAdd = isBuilderComplete();
        if (canAdd && amt.ok && stockTotal() + amt.amount > maxUnitAmount) {
          canAdd = false;
          setAmountError(
            "合計金額は" +
              maxUnitAmount.toLocaleString("ja-JP") +
              "円以下で入力してください"
          );
        }
        addBtn.disabled = !canAdd;
      }
      if (submitBtn) submitBtn.disabled = submitting || state.stock.length < 1;
    }

    if (betSelect) {
      betSelect.addEventListener("change", function () {
        state.betType = betSelect.value || "";
        state.picks = [];
        if (msgEl) msgEl.textContent = "";
        renderHorseFields();
      });
    }

    container.querySelectorAll(".purchase-preset").forEach(function (btn) {
      btn.addEventListener("click", function () {
        container.querySelectorAll(".purchase-preset").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        var v = btn.getAttribute("data-unit");
        if (v === "other") {
          state.other = true;
          state.unit = null;
          setOtherVisible(true);
          if (otherInput) otherInput.focus();
        } else {
          state.other = false;
          state.unit = Number(v);
          setOtherVisible(false);
        }
        if (msgEl) msgEl.textContent = "";
        refreshUi();
      });
    });

    if (otherInput) {
      otherInput.addEventListener("input", function () {
        // Keep raw for validation; strip only spaces. Do not convert "100.5" → "1005".
        otherInput.value = String(otherInput.value || "").replace(/\s+/g, "");
        refreshUi();
      });
      otherInput.addEventListener("blur", function () {
        refreshUi();
      });
    }

    if (addBtn) {
      addBtn.addEventListener("click", function () {
        var amt = amountValidation();
        if (!amt.ok) {
          setAmountError(amt.message || "購入金額は100円単位で入力してください");
          if (msgEl) msgEl.textContent = amt.message || "";
          return;
        }
        if (stockTotal() + amt.amount > maxUnitAmount) {
          var overMsg =
            "合計金額は" +
            maxUnitAmount.toLocaleString("ja-JP") +
            "円以下で入力してください";
          setAmountError(overMsg);
          if (msgEl) msgEl.textContent = overMsg;
          return;
        }
        var draft = buildDraftItem();
        if (!draft) {
          if (msgEl) {
            msgEl.textContent = isAmountValid()
              ? "式別・馬・金額をすべて選択してください。"
              : "金額は100円単位の正の整数で入力してください。";
          }
          return;
        }
        if (isExactDuplicate(draft)) {
          if (msgEl) msgEl.textContent = "同じ買い目がすでに追加されています";
          return;
        }
        state.stockSeq += 1;
        draft.id = "bet-" + state.stockSeq;
        state.stock.push(draft);
        if (msgEl) msgEl.textContent = "";
        setAmountError("");
        resetBuilder();
        renderStock();
      });
    }

    function closeConfirmDialog() {
      if (confirmDialog) confirmDialog.hidden = true;
      document.body.classList.remove("is-challenge-confirm-open");
    }

    function openConfirmDialog() {
      if (!confirmDialog || !confirmBody) return;
      var rows = state.stock
        .map(function (item, idx) {
          return (
            "<tr>" +
            "<td>" +
            escapeHtml(String(idx + 1)) +
            "</td>" +
            "<td>" +
            escapeHtml(item.bet_type) +
            "</td>" +
            "<td>" +
            escapeHtml(item.legs_display || "") +
            "</td>" +
            "<td>" +
            escapeHtml(fmtYen(item.amount)) +
            "</td>" +
            "</tr>"
          );
        })
        .join("");
      confirmBody.innerHTML =
        '<p class="challenge-confirm-lead">登録する買い目・金額に間違いがないか確認してください。</p>' +
        '<p class="challenge-confirm-odds-note">実際の馬券購入では、投票状況や購入タイミングによってオッズが変動する場合があります。</p>' +
        '<p class="challenge-confirm-ask">この内容でChallengeに参加しますか？</p>' +
        '<div class="challenge-confirm-summary">' +
        "<p>買い目数 <strong>" +
        state.stock.length +
        "</strong></p>" +
        '<p class="challenge-confirm-total">合計金額 <strong>' +
        escapeHtml(fmtYen(stockTotal())) +
        "</strong></p>" +
        "</div>" +
        '<div class="challenge-confirm-table-wrap"><table class="challenge-confirm-table">' +
        "<thead><tr><th>#</th><th>式別</th><th>馬番号/組み合わせ</th><th>金額</th></tr></thead>" +
        "<tbody>" +
        rows +
        "</tbody></table></div>";
      confirmDialog.hidden = false;
      document.body.classList.add("is-challenge-confirm-open");
      if (confirmSubmitBtn) confirmSubmitBtn.focus();
    }

    function performChallengeJoin() {
      if (submitting || !state.stock.length) return;
      submitting = true;
      closeConfirmDialog();
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = isUiTest
          ? "参加処理中…（UIテスト）"
          : "参加処理中…";
      }

      if (isUiTest) {
        var enriched = state.stock.map(function (item) {
          return {
            bet_type: item.bet_type,
            ordered: !!item.ordered,
            legs_display: item.legs_display,
            selection: item.selection,
            selection_lines: (item.selection || []).map(function (n) {
              var r = runnerByNum(n);
              return r ? formatHorseOption(r) : n + "番";
            }),
            amount: item.amount,
          };
        });
        var entry =
          global.ExpectUiTestChallengeEntry &&
          ExpectUiTestChallengeEntry.buildFromStock
            ? ExpectUiTestChallengeEntry.buildFromStock(raceId, enriched, meta)
            : null;
        if (entry && ExpectUiTestChallengeEntry.save) {
          ExpectUiTestChallengeEntry.save(entry);
        }
        var hrefUi =
          ExpectUiTestChallengeEntry && ExpectUiTestChallengeEntry.aiChallengeHref
            ? ExpectUiTestChallengeEntry.aiChallengeHref({
                raceId: raceId,
                from: "challenge-entry",
              })
            : "saved.html";
        location.href = hrefUi;
        return;
      }

      if (!(global.ExpectApi && ExpectApi.User && ExpectApi.User.registerPurchase)) {
        if (msgEl) msgEl.textContent = "API を利用できません。";
        submitting = false;
        if (submitBtn) {
          submitBtn.disabled = state.stock.length < 1;
          submitBtn.textContent = "Challengeに参加する";
        }
        return;
      }

      if (msgEl) msgEl.textContent = "登録中…";
      var chain = Promise.resolve();
      state.stock.forEach(function (item) {
        chain = chain.then(function () {
          var axisRunner = runnerByNum(item.selection[0]);
          var rivals = item.selection.slice(1).map(function (n) {
            var r = runnerByNum(n);
            return { num: String(n), name: r ? r.horse_name : "" };
          });
          return ExpectApi.User.registerPurchase({
            race_id: raceId,
            race_date: meta.raceDate || raceDateFromId(raceId),
            race_label: meta.raceLabel || meta.place || null,
            prediction_version: meta.predictionVersion || null,
            unit_stake: item.amount,
            bet_types: [item.bet_type],
            axis: {
              num: String(item.selection[0]),
              name: axisRunner ? axisRunner.horse_name : "",
            },
            rivals: rivals,
            confirm_divergence: false,
          });
        });
      });
      chain
        .then(function () {
          if (msgEl) msgEl.textContent = "Challenge参加を登録しました。";
          if (submitBtn) submitBtn.textContent = "登録済み";
          var href =
            "saved.html?race_id=" +
            encodeURIComponent(raceId) +
            "&from=challenge-entry";
          setTimeout(function () {
            location.href = href;
          }, 400);
        })
        .catch(function (err) {
          if (msgEl) msgEl.textContent = (err && err.message) || "登録に失敗しました。";
          submitting = false;
          if (submitBtn) {
            submitBtn.disabled = state.stock.length < 1;
            submitBtn.textContent = "Challengeに参加する";
          }
        });
    }

    if (submitBtn) {
      submitBtn.addEventListener("click", function () {
        if (submitting) return;
        if (!state.stock.length) {
          if (msgEl) msgEl.textContent = "買い目を1件以上追加してください。";
          return;
        }
        openConfirmDialog();
      });
    }

    if (confirmDialog) {
      confirmDialog.querySelectorAll("[data-challenge-confirm-cancel]").forEach(function (el) {
        el.addEventListener("click", function () {
          if (submitting) return;
          closeConfirmDialog();
          if (msgEl) msgEl.textContent = "参加をキャンセルしました。";
        });
      });
    }
    if (confirmSubmitBtn) {
      confirmSubmitBtn.addEventListener("click", function () {
        performChallengeJoin();
      });
    }

    setOtherVisible(false);
    renderStock();
    refreshUi();
  }

  /** @deprecated auto snapshot — prefer mountPurchaseForm */
  function saveSnapshot(raceId, strategyData, meta) {
    return Promise.resolve(null);
  }

  function raceTitle(r) {
    var dateShort = (r.race_date || "").slice(5).replace("-", "/");
    var label = r.race_label || r.race_id || "—";
    return (dateShort ? dateShort + " " : "") + label;
  }

  function hitHorseNumbers(r) {
    var seen = {};
    var out = [];
    var bets = r.bet_results || {};
    Object.keys(bets).forEach(function (type) {
      ((bets[type] && bets[type].hit_tickets) || []).forEach(function (t) {
        (t.legs || []).forEach(function (n) {
          var key = String(n);
          if (!seen[key]) {
            seen[key] = true;
            out.push(n);
          }
        });
      });
    });
    if (out.length) return out.map(function (n) { return n + "番"; }).join(" · ");
    var order = r.finish_order || [];
    if (r.hit && order.length) {
      return order.slice(0, 3).map(function (n) { return n + "番"; }).join(" · ");
    }
    return "—";
  }

  function ticketRowsHtml(r) {
    var bets = r.bet_results || {};
    var rows = [];
    Object.keys(bets).forEach(function (type) {
      var b = bets[type] || {};
      var all = []
        .concat(b.hit_tickets || [])
        .concat(b.miss_tickets || []);
      if (!all.length && b.amount != null) {
        rows.push({
          label: type,
          status: b.pending ? "判定待ち" : b.hit ? "的中" : "不的中",
          hit: !!b.hit,
          pending: !!b.pending,
        });
        return;
      }
      all.forEach(function (t) {
        var legs = (t.legs || []).join("-");
        rows.push({
          label: type + " " + (legs || t.key || ""),
          status: t.pending ? "判定待ち" : t.hit ? "的中" : "不的中",
          hit: !!t.hit,
          pending: !!t.pending,
        });
      });
    });
    if (!rows.length) {
      var snap = r.strategy_snapshot || {};
      var snapBets = snap.bets || {};
      Object.keys(snapBets).forEach(function (type) {
        ((snapBets[type] && snapBets[type].tickets) || []).forEach(function (t) {
          var legs = (t.legs || []).join("-");
          rows.push({
            label: type + " " + (legs || t.key || ""),
            status: r.settled ? "不的中" : "判定待ち",
            hit: false,
            pending: !r.settled,
          });
        });
      });
    }
    if (!rows.length) return '<p class="muted">買い目なし</p>';
    return (
      '<ul class="ph-tickets">' +
      rows
        .map(function (row) {
          return (
            '<li class="' +
            (row.hit ? "is-hit" : row.pending ? "is-pending" : "is-miss") +
            '"><span>' +
            escapeHtml(row.label) +
            "</span><b>" +
            escapeHtml(row.status) +
            "</b></li>"
          );
        })
        .join("") +
      "</ul>"
    );
  }

  function marksHtml(r) {
    var marks = r.marks_result || {};
    var rows = [];
    if (marks.honmei) rows.push(marks.honmei);
    (marks.others || []).forEach(function (m) {
      rows.push(m);
    });
    if (!rows.length) return '<p class="muted">AI印の結果はまだありません</p>';
    return (
      '<ul class="ph-marks">' +
      rows
        .map(function (m) {
          return (
            "<li><span>" +
            escapeHtml(m.mark || "") +
            "</span><b>" +
            escapeHtml(m.horse_number) +
            "番</b>" +
            (m.place != null ? " · " + m.place + "着" : " · —") +
            "</li>"
          );
        })
        .join("") +
      "</ul>"
    );
  }

  function raceDetailHtml(r) {
    var profit = Number(r.profit) || 0;
    var profitCls = profit > 0 ? "is-plus" : profit < 0 ? "is-minus" : "";
    var resultLabel = !r.settled ? "未確定" : r.hit ? "的中" : "不的中";
    var types = (r.selected_bet_types || []).join(" · ") || "—";
    return (
      '<div class="ph-race-detail">' +
      '<dl class="ph-dl">' +
      "<div><dt>収支</dt><dd class=\"" +
      profitCls +
      '">' +
      (r.settled ? fmtYen(profit, true) : "—") +
      "</dd></div>" +
      "<div><dt>結果</dt><dd>" +
      escapeHtml(resultLabel) +
      "</dd></div>" +
      "<div><dt>券種</dt><dd>" +
      escapeHtml(types) +
      "</dd></div>" +
      "<div><dt>購入金額</dt><dd>" +
      fmtYen(r.purchase_amount) +
      "</dd></div>" +
      "<div><dt>払戻金額</dt><dd>" +
      fmtYen(r.payout_amount) +
      "</dd></div>" +
      "<div><dt>的中馬番</dt><dd>" +
      escapeHtml(hitHorseNumbers(r)) +
      "</dd></div>" +
      "</dl>" +
      "<h4>買い目一覧</h4>" +
      ticketRowsHtml(r) +
      "<h4>AI印の結果</h4>" +
      marksHtml(r) +
      '<a class="ph-result-btn" href="race.html?race_id=' +
      encodeURIComponent(r.race_id) +
      '&tab=result">レース結果を見る</a>' +
      "</div>"
    );
  }

  function raceAccordionHtml(r) {
    var profit = Number(r.profit) || 0;
    var profitCls = profit > 0 ? "is-plus" : profit < 0 ? "is-minus" : "";
    var side = r.settled ? fmtYen(profit, true) : "未確定";
    return (
      '<details class="ph-race">' +
      "<summary>" +
      '<span class="ph-race-title">' +
      escapeHtml(raceTitle(r)) +
      "</span>" +
      '<b class="ph-race-profit ' +
      profitCls +
      '">' +
      side +
      "</b>" +
      "</summary>" +
      raceDetailHtml(r) +
      "</details>"
    );
  }

  function monthAccordionHtml(monthBlock, open) {
    var summary = monthBlock.summary || {};
    var profit = Number(summary.profit) || 0;
    var profitCls = profit > 0 ? "is-plus" : profit < 0 ? "is-minus" : "";
    var races = monthBlock.races || [];
    var raceList = races.length
      ? races.map(raceAccordionHtml).join("")
      : '<p class="ph-empty">この月の購入登録はありません</p>';
    return (
      '<details class="ph-month"' +
      (open ? " open" : "") +
      ">" +
      "<summary>" +
      '<span class="ph-month-title">' +
      escapeHtml(monthLabel(monthBlock.month)) +
      "</span>" +
      '<span class="ph-month-meta">' +
      (summary.race_count || 0) +
      "R · " +
      '<b class="' +
      profitCls +
      '">' +
      fmtYen(profit, true) +
      "</b></span>" +
      "</summary>" +
      '<div class="ph-month-body">' +
      '<dl class="ph-month-stats">' +
      "<div><dt>レース数</dt><dd>" +
      (summary.race_count != null ? summary.race_count + "R" : "—") +
      "</dd></div>" +
      "<div><dt>総購入金額</dt><dd>" +
      fmtYen(summary.purchase_amount) +
      "</dd></div>" +
      "<div><dt>総払戻金額</dt><dd>" +
      fmtYen(summary.payout_amount) +
      "</dd></div>" +
      "<div><dt>総収支</dt><dd class=\"" +
      profitCls +
      '">' +
      fmtYen(profit, true) +
      "</dd></div>" +
      "<div><dt>回収率</dt><dd>" +
      (summary.recovery_rate != null ? summary.recovery_rate + "%" : "—") +
      "</dd></div>" +
      "<div><dt>的中率</dt><dd>" +
      (summary.hit_rate != null ? summary.hit_rate + "%" : "—") +
      "</dd></div>" +
      "</dl>" +
      '<div class="ph-race-list">' +
      raceList +
      "</div>" +
      "</div>" +
      "</details>"
    );
  }

  function bindPurchaseHistory(root) {
    root = root || document;
    var mount = root.querySelector("#purchaseHistoryMount") || root.querySelector(".ph-root");
    if (!mount) return { reload: function () {} };

    function paint(data) {
      var months = (data && data.months) || [];
      var current = currentMonth();
      if (!months.length) {
        mount.innerHTML =
          '<div class="ph-empty-card">' +
          "<p>購入履歴がありません</p>" +
          "<p class=\"muted\">買い目戦略画面から購入を登録すると、ここに月単位で表示されます。</p>" +
          '<a class="balance-link" href="races.html">レース一覧へ ›</a>' +
          "</div>";
        return;
      }
      mount.innerHTML =
        '<div class="ph-stack" role="list">' +
        months
          .map(function (m, i) {
            var open = m.month === current || (i === 0 && !months.some(function (x) { return x.month === current; }));
            return monthAccordionHtml(m, open);
          })
          .join("") +
        "</div>";
    }

    function load() {
      mount.innerHTML = '<p class="muted">購入履歴を読み込み中…</p>';
      var api = global.ExpectApi && ExpectApi.User;
      var req =
        api && api.purchaseHistory
          ? api.purchaseHistory()
          : api && api.monthlyRaceResults
            ? api.monthlyRaceResults(currentMonth()).then(function (d) {
                return {
                  months: d && d.races && d.races.length
                    ? [{ month: d.month || currentMonth(), summary: d.summary, races: d.races }]
                    : [],
                };
              })
            : Promise.resolve({ months: [] });
      return req
        .then(paint)
        .catch(function () {
          mount.innerHTML =
            '<p class="muted">購入履歴を読み込めませんでした。<button type="button" class="ph-retry">再試行</button></p>';
          var btn = mount.querySelector(".ph-retry");
          if (btn) btn.addEventListener("click", load);
        });
    }

    load();
    return { reload: load };
  }

  function bindMonthlyPage(root) {
    // Backward-compatible alias → accordion purchase history
    return bindPurchaseHistory(root);
  }

  function paintResultTab(mount, payload) {
    if (!mount) return;
    var raceId = (payload && payload.race_id) || "";
    var item = (payload && payload.item) || null;
    var official = (payload && payload.official) || null;
    var aiTheory = (payload && payload.ai_theory) || null;
    var userResult =
      (payload && payload.user_result) ||
      (item && item.purchase_registered ? item : null);
    var order =
      (official && official.finish_order) ||
      (item && item.finish_order) ||
      (aiTheory && aiTheory.finish_order) ||
      [];
    var marks =
      (aiTheory && aiTheory.marks_result) ||
      (item && item.marks_result) ||
      {};

    var finishHtml = order.length
      ? '<ol class="result-finish">' +
        order
          .map(function (n, i) {
            return "<li><span>" + (i + 1) + "着</span><b>" + escapeHtml(n) + "番</b></li>";
          })
          .join("") +
        "</ol>"
      : '<p class="muted">着順はまだ反映されていません。</p>';

    var markRows = [];
    if (marks.honmei) markRows.push(marks.honmei);
    (marks.others || []).forEach(function (m) {
      markRows.push(m);
    });
    var marksHtml = markRows.length
      ? '<ul class="result-marks">' +
        markRows
          .map(function (m) {
            var name = m.name ? " " + escapeHtml(m.name) : "";
            return (
              "<li><span>" +
              escapeHtml(m.mark || "") +
              "</span><b>" +
              escapeHtml(m.horse_number) +
              "番</b>" +
              name +
              (m.place != null ? " · " + m.place + "着" : " · —") +
              "</li>"
            );
          })
          .join("") +
        "</ul>"
      : '<p class="muted">AI印の結果はまだありません（予想または着順待ち）。</p>';

    var aiBets = (aiTheory && aiTheory.bet_results) || {};
    var snapBets =
      (aiTheory &&
        aiTheory.strategy_snapshot &&
        aiTheory.strategy_snapshot.bets) ||
      {};
    var aiBetTypes = Object.keys(aiBets);
    if (!aiBetTypes.length) aiBetTypes = Object.keys(snapBets);
    var aiBetsHtml = aiBetTypes
      .map(function (type) {
        var b = aiBets[type] || {};
        var snap = snapBets[type] || {};
        var amount = Number(b.amount != null ? b.amount : snap.amount) || 0;
        var hitN = (b.hit_tickets && b.hit_tickets.length) || 0;
        var missN = (b.miss_tickets && b.miss_tickets.length) || 0;
        var points =
          (snap.tickets && snap.tickets.length) || hitN + missN || 0;
        var status = !Object.keys(b).length
          ? "—"
          : b.pending
            ? "判定待ち"
            : b.hit
              ? "的中"
              : "不的中";
        var body = "";
        if (b.hit) {
          body =
            "<p>払戻 " +
            fmtYen(b.payout) +
            " · 利益 " +
            fmtYen(b.profit, true) +
            "</p>";
        } else if (b && b.pending === false) {
          body = "<p>" + fmtYen(-amount, true) + "</p>";
        }
        var ticketHint =
          points > 0 ? '<p class="muted">' + points + "点</p>" : "";
        return (
          '<article class="result-bet' +
          (b.hit ? " is-hit" : "") +
          '"><div class="result-bet-top"><h4>' +
          escapeHtml(type) +
          "</h4><b>" +
          status +
          " · " +
          fmtYen(amount) +
          "</b></div>" +
          ticketHint +
          body +
          "</article>"
        );
      })
      .join("");

    var aiPayout = aiTheory ? Number(aiTheory.payout_amount) || 0 : null;
    var aiPurchase = aiTheory ? Number(aiTheory.purchase_amount) || 0 : null;
    var aiProfit = aiTheory ? Number(aiTheory.profit) || 0 : null;

    var registered = !!(userResult && userResult.purchase_registered);
    var betResults = (userResult && userResult.bet_results) || {};
    var betsHtml = Object.keys(betResults)
      .map(function (type) {
        var b = betResults[type] || {};
        var status = b.pending ? "判定待ち" : b.hit ? "的中" : "不的中";
        var body = b.hit
          ? "<p>払戻 " + fmtYen(b.payout) + " · 利益 " + fmtYen(b.profit, true) + "</p>"
          : !b.pending
            ? "<p>" + fmtYen(-(b.amount || 0), true) + "</p>"
            : "";
        return (
          '<article class="result-bet' +
          (b.hit ? " is-hit" : "") +
          '"><div class="result-bet-top"><h4>' +
          escapeHtml(type) +
          "</h4><b>" +
          status +
          " · " +
          fmtYen(b.amount) +
          "</b></div>" +
          body +
          "</article>"
        );
      })
      .join("");

    var purchase = registered ? Number(userResult.purchase_amount) || 0 : 0;
    var payout = registered ? Number(userResult.payout_amount) || 0 : 0;
    var profit = registered ? Number(userResult.profit) || 0 : 0;
    var pointsAwarded = registered ? Number(userResult.points_awarded) || 0 : 0;
    var strategyHref =
      "strategy.html?race_id=" +
      encodeURIComponent(
        raceId ||
          (official && official.race_id) ||
          (item && item.race_id) ||
          ""
      );

    var aiTheoryCard =
      '<section class="chart-card result-ai-block">' +
      "<h3>AI理論結果</h3>" +
      '<p class="muted result-card-lead">Prediction と公式結果から算出（購入登録不要）</p>' +
      "<h4>AI印結果（◎○▲△）</h4>" +
      marksHtml +
      "<h4>AI理論買い目</h4>" +
      (aiBetsHtml ||
        '<p class="muted">理論買い目は予想データと着順が揃うと表示されます。</p>') +
      "<h4>理論収支</h4>" +
      (aiTheory
        ? '<div class="result-pnl"><div><span>理論購入額</span><b>' +
          fmtYen(aiPurchase) +
          "</b></div><div><span>理論払戻</span><b>" +
          fmtYen(aiPayout) +
          '</b></div><div><span>理論収支</span><b class="' +
          (aiProfit > 0 ? "is-plus" : aiProfit < 0 ? "is-minus" : "") +
          '">' +
          fmtYen(aiProfit, true) +
          "</b></div></div>" +
          '<p class="muted">' +
          (aiTheory.hit ? "理論的中" : aiTheory.settled ? "理論不的中" : "判定待ち") +
          "</p>"
        : '<p class="muted">理論払戻は着順・配当反映後に表示されます。</p>') +
      "</section>";

    var userCard =
      '<section class="chart-card result-user-block">' +
      "<h3>あなたの購入結果</h3>" +
      (registered
        ? '<p class="muted result-card-lead">買い目戦略で登録した実購入</p>' +
          "<h4>購入した券種</h4>" +
          (betsHtml || '<p class="muted">券種結果待ち</p>') +
          '<div class="result-pnl" style="margin-top:12px"><div><span>購入金額</span><b>' +
          fmtYen(purchase) +
          "</b></div><div><span>払戻</span><b>" +
          fmtYen(payout) +
          '</b></div><div><span>収支</span><b class="' +
          (profit > 0 ? "is-plus" : profit < 0 ? "is-minus" : "") +
          '">' +
          fmtYen(profit, true) +
          "</b></div><div><span>ポイント</span><b>" +
          (pointsAwarded ? "+" + pointsAwarded + "P" : "—") +
          "</b></div></div>" +
          '<p class="muted">' +
          (userResult.settled
            ? userResult.hit
              ? "的中"
              : "不的中"
            : "未確定") +
          "</p>"
        : '<p class="muted">購入が登録されていません。買い目戦略から登録すると、ここに購入金額・払戻・収支・ポイントが表示されます。</p>' +
          '<p><a class="balance-link" href="' +
          strategyHref +
          '">買い目戦略へ ›</a></p>') +
      "</section>";

    mount.innerHTML =
      '<section class="chart-card"><h3>着順</h3>' +
      finishHtml +
      "</section>" +
      aiTheoryCard +
      userCard;
  }

  function loadAndPaintResult(raceId, mount) {
    if (!mount) return Promise.resolve();
    mount.innerHTML = '<p class="muted">結果を読み込み中…</p>';
    var api = global.ExpectApi && ExpectApi.User;
    if (!api || !api.getRaceResult) {
      mount.innerHTML = '<p class="muted">結果 API を利用できません。</p>';
      return Promise.resolve();
    }
    return api
      .settleRaceResult(raceId, {})
      .catch(function () {
        return null;
      })
      .then(function () {
        return api.getRaceResult(raceId);
      })
      .then(function (payload) {
        payload = payload || {};
        payload.race_id = payload.race_id || raceId;
        paintResultTab(mount, payload);
      })
      .catch(function () {
        mount.innerHTML = '<p class="muted">結果データがありません。</p>';
      });
  }

  /** Version7.1: 結果タブ表示中なら再取得して描画 */
  function refreshActiveTab(raceId) {
    var mount =
      global.document &&
      (global.document.getElementById("tab-result") ||
        global.document.querySelector('[data-tab-panel="result"]'));
    if (!mount || mount.hidden || mount.getAttribute("aria-hidden") === "true") {
      return Promise.resolve();
    }
    var style = global.getComputedStyle ? global.getComputedStyle(mount) : null;
    if (style && style.display === "none") return Promise.resolve();
    return loadAndPaintResult(raceId, mount);
  }

  global.ExpectUserRaceResults = {
    saveSnapshot: saveSnapshot,
    mountPurchaseForm: mountPurchaseForm,
    mountChallengeDynamicPurchaseForm: mountChallengeDynamicPurchaseForm,
    BET_TYPES: BET_TYPES,
    OFFICIAL_MAX_PURCHASE_AMOUNT_PER_RACE: OFFICIAL_MAX_PURCHASE_AMOUNT_PER_RACE,
    validateChallengeUnitAmount: validateChallengeUnitAmount,
    bindMonthlyPage: bindMonthlyPage,
    bindPurchaseHistory: bindPurchaseHistory,
    loadAndPaintResult: loadAndPaintResult,
    refreshActiveTab: refreshActiveTab,
    paintResultTab: paintResultTab,
    fmtYen: fmtYen,
    currentMonth: currentMonth,
  };
})(typeof window !== "undefined" ? window : globalThis);
