/**
 * ExpectChallengeDashboard — AI benchmark vs user (V7 / V9 Benchmark Layer)
 * AI = monthly-reset target. User points/levels stay cumulative elsewhere.
 * V9 (feature_flags.v9_benchmark_layer): main card = ◎単勝 Benchmark;
 * Purchase Lab is collapsed / detail-only.
 */
(function (global) {
  "use strict";

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
    return "±" + abs;
  }

  function monthLabel(ym) {
    var p = String(ym || "").split("-");
    if (p.length !== 2) return ym || "";
    return p[0] + "年" + Number(p[1]) + "月";
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

  function barWidth(value, maxAbs) {
    var v = Math.abs(Number(value) || 0);
    if (!maxAbs || maxAbs <= 0) return 8;
    return Math.max(8, Math.round((v / maxAbs) * 100));
  }

  function isV9(data) {
    return !!(data && data.feature_flags && data.feature_flags.v9_benchmark_layer);
  }

  function paintBars(mount, aiProfit, userProfit, aiLabel) {
    if (!mount) return;
    var maxAbs = Math.max(Math.abs(aiProfit), Math.abs(userProfit), 1);
    var label = aiLabel || "AI";
    mount.innerHTML =
      '<div class="cmp-bar-row">' +
      '<span class="cmp-bar-label">' +
      escapeHtml(label) +
      "</span>" +
      '<div class="cmp-bar-track"><i class="cmp-bar cmp-bar--ai' +
      (aiProfit < 0 ? " is-neg" : "") +
      '" style="width:' +
      barWidth(aiProfit, maxAbs) +
      '%"></i></div>' +
      "<b>" +
      fmtYen(aiProfit, true) +
      "</b></div>" +
      '<div class="cmp-bar-row">' +
      '<span class="cmp-bar-label">あなた</span>' +
      '<div class="cmp-bar-track"><i class="cmp-bar cmp-bar--you' +
      (userProfit < 0 ? " is-neg" : "") +
      '" style="width:' +
      barWidth(userProfit, maxAbs) +
      '%"></i></div>' +
      "<b>" +
      fmtYen(userProfit, true) +
      "</b></div>";
  }

  function paintWeekBars(mount, weeks, aiLabel) {
    if (!mount) return;
    weeks = weeks || [];
    var label = aiLabel || "AI";
    var maxAbs = 1;
    weeks.forEach(function (w) {
      maxAbs = Math.max(maxAbs, Math.abs(w.ai_profit || 0), Math.abs(w.user_profit || 0));
    });
    mount.innerHTML = weeks
      .map(function (w) {
        return (
          '<div class="cmp-week">' +
          "<h4>第" +
          w.week +
          "週</h4>" +
          '<div class="cmp-bar-row"><span class="cmp-bar-label">' +
          escapeHtml(label) +
          "</span>" +
          '<div class="cmp-bar-track"><i class="cmp-bar cmp-bar--ai' +
          ((w.ai_profit || 0) < 0 ? " is-neg" : "") +
          '" style="width:' +
          barWidth(w.ai_profit, maxAbs) +
          '%"></i></div><b>' +
          (w.ai_races ? fmtYen(w.ai_profit, true) : "—") +
          "</b></div>" +
          '<div class="cmp-bar-row"><span class="cmp-bar-label">あなた</span>' +
          '<div class="cmp-bar-track"><i class="cmp-bar cmp-bar--you' +
          ((w.user_profit || 0) < 0 ? " is-neg" : "") +
          '" style="width:' +
          barWidth(w.user_profit, maxAbs) +
          '%"></i></div><b>' +
          (w.user_races ? fmtYen(w.user_profit, true) : "—") +
          "</b></div></div>"
        );
      })
      .join("");
  }

  function paintChallengeBanner(el, cmp, month, v9) {
    if (!el || !cmp) return;
    var status = cmp.status || "tied";
    var title =
      status === "achieved" ? "🎉 今月のAIチャレンジ達成！" : "今月のAIチャレンジ";
    var aiCaption = v9 ? "AI Benchmark（◎単勝）" : "AI利益（今月の目標）";
    el.className =
      "challenge-banner" +
      (status === "achieved" ? " is-achieved" : status === "behind" ? " is-behind" : " is-tied");
    el.innerHTML =
      '<p class="challenge-kicker">' +
      escapeHtml(monthLabel(month)) +
      "</p>" +
      "<h2>" +
      title +
      "</h2>" +
      '<div class="challenge-scores">' +
      "<div><span>" +
      escapeHtml(aiCaption) +
      "</span><b>" +
      fmtYen(cmp.ai_profit != null ? cmp.ai_profit : cmp.benchmark_profit, true) +
      "</b></div>" +
      "<div><span>あなた</span><b>" +
      fmtYen(cmp.user_profit, true) +
      "</b></div></div>" +
      '<p class="challenge-msg">' +
      escapeHtml(cmp.challenge_message || "") +
      "</p>";
  }

  function paintProgress(el, progress) {
    if (!el) return;
    if (!progress || typeof progress !== "object") {
      el.innerHTML = '<p class="muted">No Data</p>';
      return;
    }
    var level = progress.level != null ? progress.level : progress.lv;
    var points =
      progress.cumulative_points != null
        ? progress.cumulative_points
        : progress.points != null
          ? progress.points
          : progress.total_points;
    var rank = progress.rank != null ? progress.rank : progress.ranking;
    var title = progress.title || progress.rank_title || "";
    var next =
      progress.points_to_next_level != null
        ? progress.points_to_next_level
        : progress.points_to_next != null
          ? progress.points_to_next
          : progress.next_level_points;
    var parts = [];
    if (level != null) {
      parts.push("<div><span>レベル</span><b>Lv." + escapeHtml(level) + "</b></div>");
    }
    if (points != null) {
      parts.push(
        "<div><span>累計ポイント</span><b>" +
          escapeHtml(Number(points).toLocaleString("ja-JP")) +
          "</b></div>"
      );
    }
    if (rank != null) {
      parts.push("<div><span>ランキング</span><b>" + escapeHtml(rank) + "</b></div>");
    } else {
      parts.push("<div><span>ランキング</span><b>No Data</b></div>");
    }
    if (title) {
      parts.push("<div><span>称号</span><b>" + escapeHtml(title) + "</b></div>");
    }
    if (next != null) {
      parts.push(
        "<div><span>次レベルまで</span><b>" +
          escapeHtml(Number(next).toLocaleString("ja-JP")) +
          " pt</b></div>"
      );
    }
    if (!parts.length) {
      el.innerHTML = '<p class="muted">No Data</p>';
      return;
    }
    el.innerHTML = '<div class="dash-card-grid">' + parts.join("") + "</div>";
  }

  function sideSummary(side) {
    if (!side || typeof side !== "object") return {};
    if (side.summary && typeof side.summary === "object") return side.summary;
    return side;
  }

  function paintSideCard(el, title, summary, kind) {
    if (!el) return;
    summary = summary || {};
    var profit = Number(summary.profit) || 0;
    var grid =
      "<div><span>回収率</span><b>" +
      (summary.recovery_rate != null ? summary.recovery_rate + "%" : "—") +
      "</b></div>" +
      "<div><span>的中率</span><b>" +
      (summary.hit_rate != null ? summary.hit_rate + "%" : "—") +
      "</b></div>";

    if (kind === "benchmark") {
      grid +=
        "<div><span>購入額</span><b>" +
        fmtYen(summary.purchase_amount) +
        "</b></div>" +
        "<div><span>払戻額</span><b>" +
        fmtYen(summary.payout_amount) +
        "</b></div>" +
        "<div><span>対象レース数</span><b>" +
        (summary.race_count != null ? summary.race_count : "—") +
        "</b></div>" +
        "<div><span>的中数</span><b>" +
        (summary.hit_count != null ? summary.hit_count : "—") +
        "</b></div>";
    } else {
      grid +=
        "<div><span>的中数</span><b>" +
        (summary.hit_count != null
          ? summary.hit_count + " / " + (summary.race_count || 0)
          : "—") +
        "</b></div>" +
        (kind === "user"
          ? "<div><span>購入</span><b>" + fmtYen(summary.purchase_amount) + "</b></div>"
          : "<div><span>理論購入</span><b>" + fmtYen(summary.purchase_amount) + "</b></div>");
    }

    el.innerHTML =
      "<h3>" +
      escapeHtml(title) +
      "</h3>" +
      '<p class="dash-card-profit' +
      (profit > 0 ? " is-plus" : profit < 0 ? " is-minus" : "") +
      '">' +
      fmtYen(profit, true) +
      "</p>" +
      '<div class="dash-card-grid">' +
      grid +
      "</div>";
  }

  /** UI title only — admin keeps research label; general users see short title. */
  function purchaseLabSummaryTitle() {
    var isAdmin = false;
    try {
      if (global.ExpectRoles && ExpectRoles.isOpsPortalAdminSync) {
        var authRaw = null;
        try {
          authRaw = JSON.parse(localStorage.getItem("expect_auth_v1") || "null");
        } catch (eAuth) {
          authRaw = null;
        }
        isAdmin = !!ExpectRoles.isOpsPortalAdminSync(authRaw);
      } else if (global.ExpectRoles && ExpectRoles.roleFromAccessToken) {
        isAdmin = ExpectRoles.roleFromAccessToken() === ExpectRoles.Role.ADMIN;
      }
    } catch (e) {
      isAdmin = false;
    }
    return isAdmin ? "Purchase Lab（研究用・公式実績外）" : "Purchase Lab";
  }

  function paintPurchaseLab(el, lab) {
    if (!el) return;
    if (!lab || !Array.isArray(lab.strategies) || !lab.strategies.length) {
      el.hidden = true;
      el.innerHTML = "";
      return;
    }
    el.hidden = false;
    var rows = lab.strategies
      .map(function (s) {
        var sum = s.summary || {};
        var profit = Number(sum.profit) || 0;
        var cls = profit > 0 ? "is-plus" : profit < 0 ? "is-minus" : "";
        return (
          "<tr>" +
          "<th scope='row'>" +
          escapeHtml(s.label || s.id) +
          "</th>" +
          '<td class="' +
          cls +
          '">' +
          fmtYen(profit, true) +
          "</td>" +
          "<td>" +
          (sum.recovery_rate != null ? sum.recovery_rate + "%" : "—") +
          "</td>" +
          "<td>" +
          (sum.hit_rate != null ? sum.hit_rate + "%" : "—") +
          "</td>" +
          "<td>" +
          fmtYen(sum.purchase_amount) +
          "</td>" +
          "<td>" +
          (sum.race_count != null ? sum.race_count : "—") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    el.innerHTML =
      "<details class='purchase-lab'>" +
      "<summary>" +
      escapeHtml(purchaseLabSummaryTitle()) +
      "</summary>" +
      "<p class='purchase-lab-note'>公式AI実績は Benchmark（◎単勝1点）のみです。ここは購入フォーメーション比較用です。</p>" +
      "<div class='purchase-lab-table-wrap'><table class='purchase-lab-table'>" +
      "<thead><tr><th>戦略</th><th>利益</th><th>回収率</th><th>的中率</th><th>購入額</th><th>レース</th></tr></thead>" +
      "<tbody>" +
      rows +
      "</tbody></table></div></details>";
  }

  function bindDashboard(root) {
    root = root || document;
    var state = { month: currentMonth() };

    function paint(data) {
      if (!data) return;
      var v9 = isV9(data);
      var cmp = data.comparison || {};
      var aiSummary = v9
        ? sideSummary(data.benchmark) || data.ai_summary || sideSummary(data.ai)
        : data.ai_summary || sideSummary(data.ai);
      var userSummary = data.user_summary || sideSummary(data.user);
      var aiLabel = v9 ? "BM" : "AI";

      paintChallengeBanner(root.querySelector("#challengeBanner"), cmp, state.month, v9);
      if (v9) {
        paintSideCard(
          root.querySelector("#aiScoreCard"),
          "AI Benchmark（◎単勝1点）",
          aiSummary,
          "benchmark"
        );
      } else {
        paintSideCard(
          root.querySelector("#aiScoreCard"),
          "AI成績（今月の目標）",
          aiSummary,
          "ai"
        );
      }
      paintSideCard(root.querySelector("#userScoreCard"), "あなた（User Challenge）", userSummary, "user");
      paintBars(
        root.querySelector("#profitCompareBars"),
        cmp.ai_profit != null ? cmp.ai_profit : cmp.benchmark_profit || 0,
        cmp.user_profit || 0,
        aiLabel
      );
      paintWeekBars(root.querySelector("#weekCompareBars"), data.weeks_compare || [], aiLabel);
      paintProgress(root.querySelector("#challengeProgress"), data.progress);
      paintPurchaseLab(root.querySelector("#purchaseLabSection"), v9 ? data.purchase_lab : null);

      var monthNav = root.querySelector(".ledger-month-nav-label");
      if (monthNav) monthNav.textContent = monthLabel(state.month);

      var raceList = root.querySelector(".ledger-race-list");
      if (raceList) {
        var races =
          data.user_races ||
          (data.user && Array.isArray(data.user.races) ? data.user.races : []) ||
          [];
        if (!races.length) {
          raceList.innerHTML =
            '<li class="ledger-race-empty"><span>購入登録がありません</span>' +
            "<p>買い目戦略から購入すると、あなた側の成績に反映されます。</p></li>";
        } else {
          raceList.innerHTML = races
            .slice(0, 20)
            .map(function (r) {
              var p = Number(r.profit) || 0;
              var cls = p > 0 ? "is-plus" : p < 0 ? "is-minus" : "";
              var label = r.race_label || r.race_id || "—";
              var dateShort = (r.race_date || "").slice(5).replace("-", "/");
              return (
                '<li><a href="race.html?race_id=' +
                encodeURIComponent(r.race_id) +
                '&tab=result"><span>' +
                escapeHtml(dateShort ? dateShort + " " + label : label) +
                '</span><b class="' +
                cls +
                '">' +
                (r.settled ? fmtYen(p, true) : "未確定") +
                "</b><em>詳細 ›</em></a></li>"
              );
            })
            .join("");
        }
      }

      var lines = [];
      var kaoba = (cmp.kaoba_message || "").replace(/\n/g, "<br>");
      if (kaoba) lines.push(kaoba);
      if (v9) {
        lines.push("公式は<strong>◎単勝</strong>だよ！<br>購入作戦は Lab で研究してね");
      } else {
        lines.push("AIはライバルじゃなく<br><strong>今月の目標</strong>だよ！");
      }
      if (window.ExpectShell && ExpectShell.initMascotTalk) {
        ExpectShell.initMascotTalk(lines);
      }
    }

    function load() {
      if (!(global.ExpectApi && ExpectApi.User && ExpectApi.User.challengeMonthly)) {
        return;
      }
      ExpectApi.User.challengeMonthly(state.month)
        .then(paint)
        .catch(function () {
          paint({
            feature_flags: { v9_benchmark_layer: false },
            ai: {},
            user: {},
            comparison: {
              ai_profit: 0,
              user_profit: 0,
              profit_diff: 0,
              status: "tied",
              challenge_message: "No Data",
              kaoba_message: "データを取得できませんでした",
            },
            weeks_compare: [1, 2, 3, 4, 5].map(function (w) {
              return { week: w, ai_profit: 0, user_profit: 0, ai_races: 0, user_races: 0 };
            }),
          });
        });
    }

    var prev = root.querySelector("[data-ledger-prev]");
    var next = root.querySelector("[data-ledger-next]");
    if (prev) {
      prev.addEventListener("click", function () {
        state.month = shiftMonth(state.month, -1);
        load();
      });
    }
    if (next) {
      next.addEventListener("click", function () {
        state.month = shiftMonth(state.month, 1);
        load();
      });
    }
    load();
  }

  function paintHomeChallenge(el, data) {
    if (!el) return;
    var cmp = (data && data.comparison) || {};
    var status = cmp.status || "tied";
    var v9 = isV9(data);
    var kicker = v9 ? "AI Benchmark（◎単勝）" : "今月のAIチャレンジ";
    var aiProfit = cmp.ai_profit != null ? cmp.ai_profit : cmp.benchmark_profit;
    el.hidden = false;
    if (status === "achieved") {
      el.innerHTML =
        '<div class="home-challenge is-achieved">' +
        '<p class="home-challenge-kicker">' +
        escapeHtml(kicker) +
        "</p>" +
        "<h3>🎉 達成！</h3>" +
        "<p>AI " +
        fmtYen(aiProfit, true) +
        " · あなた " +
        fmtYen(cmp.user_profit, true) +
        "</p>" +
        '<p class="home-challenge-kaoba">KAOBA「' +
        escapeHtml((cmp.home_kaoba_message || "").replace(/\n/g, " ")) +
        "」</p>" +
        '<a class="home-challenge-link" href="saved.html">ダッシュボードへ ›</a></div>';
      return;
    }
    el.innerHTML =
      '<div class="home-challenge">' +
      '<p class="home-challenge-kicker">' +
      escapeHtml(kicker) +
      "</p>" +
      '<div class="home-challenge-row"><span>' +
      (v9 ? "Benchmark" : "AI利益") +
      "</span><b>" +
      fmtYen(aiProfit, true) +
      "</b></div>" +
      '<div class="home-challenge-row"><span>あなた</span><b>' +
      fmtYen(cmp.user_profit, true) +
      "</b></div>" +
      '<p class="home-challenge-msg">' +
      escapeHtml(cmp.challenge_message || "") +
      "</p>" +
      '<a class="home-challenge-link" href="saved.html">詳しく見る ›</a></div>';
  }

  function bindHomeChallenge(root) {
    root = root || document;
    var el = root.querySelector("#homeChallengeSlot");
    if (!el || !(global.ExpectApi && ExpectApi.User && ExpectApi.User.challengeMonthly)) {
      return;
    }
    ExpectApi.User.challengeMonthly(currentMonth())
      .then(function (data) {
        paintHomeChallenge(el, data);
      })
      .catch(function () {
        el.hidden = true;
      });
  }

  global.ExpectChallengeDashboard = {
    bindDashboard: bindDashboard,
    bindHomeChallenge: bindHomeChallenge,
    paintHomeChallenge: paintHomeChallenge,
    fmtYen: fmtYen,
    currentMonth: currentMonth,
  };
})(typeof window !== "undefined" ? window : globalThis);
