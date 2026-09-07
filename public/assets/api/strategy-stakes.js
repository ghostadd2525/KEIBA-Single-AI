/**
 * ExpectStrategyStakes — ROI・オッズ変動を反映した資金・買い目金額
 */
(function (global) {
  "use strict";

  function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, n));
  }

  function round100(n) {
    return Math.max(100, Math.round(Number(n) / 100) * 100);
  }

  function fmtYen(n) {
    return "¥" + Number(n).toLocaleString("ja-JP");
  }

  function pct(n) {
    return Math.round(n) + "%";
  }

  function num(v) {
    var n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function oddsFromBoard(board, horseNumber) {
    if (!board || !board.entries || horseNumber == null) return null;
    for (var i = 0; i < board.entries.length; i++) {
      var e = board.entries[i];
      if (Number(e.horse_number) === Number(horseNumber)) {
        return num(e.odds);
      }
    }
    return null;
  }

  function seriesDrift(seriesPayload, horseNumber) {
    if (!seriesPayload || !seriesPayload.series || horseNumber == null) {
      return { driftPct: 0, latest: null, first: null, points: 0 };
    }
    var row = null;
    for (var i = 0; i < seriesPayload.series.length; i++) {
      if (Number(seriesPayload.series[i].horse_number) === Number(horseNumber)) {
        row = seriesPayload.series[i];
        break;
      }
    }
    if (!row || !row.points || !row.points.length) {
      return { driftPct: 0, latest: num(row && row.latest_odds), first: null, points: 0 };
    }
    var vals = row.points
      .map(function (p) {
        return num(p.odds);
      })
      .filter(function (v) {
        return v != null;
      });
    if (!vals.length) {
      return { driftPct: 0, latest: null, first: null, points: 0 };
    }
    var first = vals[0];
    var latest = vals[vals.length - 1];
    var driftPct = first > 0 ? ((latest - first) / first) * 100 : 0;
    return { driftPct: driftPct, latest: latest, first: first, points: vals.length };
  }

  /**
   * AI信頼度・単勝オッズ・オッズ変動から資金配分を算出
   * @returns {{
   *   total:number, main:number, cover:number, lottery:number,
   *   mainPct:number, coverPct:number, lotteryPct:number,
   *   axisOdds:number|null, driftPct:number, expectedRoi:number,
   *   risk:string, note:string
   * }}
   */
  function computeBankroll(opts) {
    opts = opts || {};
    var conf = clamp(num(opts.confidence) != null ? num(opts.confidence) : 70, 35, 95);
    var odds = num(opts.axisOdds);
    var drift = num(opts.driftPct) || 0;

    // ベース予算: 信頼度が高いほど厚く（¥3,000〜¥8,000）
    var total = round100(3000 + (conf - 50) * 80);

    // オッズ帯で主軸/保険/一発の比率
    var mainPct = 55;
    var coverPct = 30;
    var lotteryPct = 15;
    if (odds != null) {
      if (odds < 2.5) {
        mainPct = 68;
        coverPct = 22;
        lotteryPct = 10;
      } else if (odds < 5) {
        mainPct = 58;
        coverPct = 28;
        lotteryPct = 14;
      } else if (odds < 10) {
        mainPct = 48;
        coverPct = 32;
        lotteryPct = 20;
      } else {
        mainPct = 38;
        coverPct = 35;
        lotteryPct = 27;
        total = round100(total * 0.85);
      }
    }

    // オッズ変動: 短縮＝市場支持で主軸厚め / 拡大＝妙味だが主軸抑制
    if (drift <= -8) {
      mainPct += 7;
      lotteryPct -= 4;
      coverPct -= 3;
      total = round100(total * 1.08);
    } else if (drift <= -3) {
      mainPct += 3;
      lotteryPct -= 2;
      coverPct -= 1;
    } else if (drift >= 12) {
      mainPct -= 8;
      coverPct += 4;
      lotteryPct += 4;
      total = round100(total * 0.9);
    } else if (drift >= 5) {
      mainPct -= 4;
      coverPct += 2;
      lotteryPct += 2;
    }

    // 信頼度が低いときは一発を削る
    if (conf < 55) {
      lotteryPct = Math.max(8, lotteryPct - 6);
      coverPct += 3;
      mainPct += 3;
      total = round100(total * 0.85);
    } else if (conf >= 80) {
      mainPct += 4;
      lotteryPct = Math.max(8, lotteryPct - 2);
      coverPct = Math.max(18, coverPct - 2);
    }

    var sum = mainPct + coverPct + lotteryPct;
    mainPct = (mainPct / sum) * 100;
    coverPct = (coverPct / sum) * 100;
    lotteryPct = 100 - mainPct - coverPct;

    var main = round100((total * mainPct) / 100);
    var cover = round100((total * coverPct) / 100);
    var lottery = round100(total - main - cover);
    if (lottery < 100) {
      lottery = 100;
      total = main + cover + lottery;
    }

    // 期待ROIの粗い目安: 信頼度を勝率近似、単勝オッズで EV
    var winProb = conf / 100 * 0.55;
    var ev = odds != null ? winProb * odds - 1 : 0;
    var expectedRoi = Math.round(ev * 100);

    var riskParts = [];
    if (conf < 60) riskParts.push("AIの自信が控えめなので、総額は抑えめがおすすめです");
    if (odds != null && odds >= 10) riskParts.push("軸のオッズが高めなので、保険の馬も少し多めに残しましょう");
    if (drift >= 8) riskParts.push("人気が薄れ気味なので、主軸だけで深追いしない方が安心です");
    if (drift <= -5) riskParts.push("人気が集まってきているので、中心の馬をしっかり軸にしましょう");
    if (!riskParts.length) riskParts.push("普段どおりの金額で組み立てやすい配分です");

    var noteParts = [];
    if (odds != null) {
      noteParts.push("現在の想定オッズは" + odds.toFixed(1) + "倍です");
    }
    if (drift <= -5) {
      noteParts.push("人気が高くオッズは下がる可能性があります");
    } else if (drift >= 8) {
      noteParts.push("人気が薄れ気味で、オッズが上がっている可能性があります");
    } else if (drift < -1) {
      noteParts.push("少し人気が集まってきている様子です");
    } else if (drift > 1) {
      noteParts.push("少し人気が分散している様子です");
    }
    var note = noteParts.length
      ? noteParts.join("。") + "。"
      : "オッズの動きを見ながら、無理のない金額で組み立てましょう。";

    return {
      total: total,
      main: main,
      cover: cover,
      lottery: lottery,
      mainPct: Math.round(mainPct),
      coverPct: Math.round(coverPct),
      lotteryPct: Math.round(lotteryPct),
      axisOdds: odds,
      driftPct: drift,
      expectedRoi: expectedRoi,
      risk: riskParts.join("。") + "。",
      note: note,
    };
  }

  function buildTickets(bank, opts) {
    var oddsLabel =
      bank.axisOdds != null
        ? "現在の想定オッズは" + bank.axisOdds.toFixed(1) + "倍"
        : "オッズはまだ取得待ちです";
    var driftHint = "";
    if (bank.driftPct <= -5) {
      driftHint = "人気が高くオッズは下がる可能性があります";
    } else if (bank.driftPct >= 8) {
      driftHint = "人気が薄れ気味でオッズが上がる可能性があります";
    } else if (Math.abs(bank.driftPct) >= 1) {
      driftHint =
        bank.driftPct < 0
          ? "少し人気が集まってきている様子です"
          : "少し人気が分散している様子です";
    } else {
      driftHint = "オッズの動きは落ち着いています";
    }

    var umaren = round100(bank.main * 0.62);
    var wide = round100(bank.main - umaren);
    if (wide < 100) {
      wide = 100;
      umaren = Math.max(100, bank.main - wide);
    }
    var trio = bank.cover;
    var trifecta = bank.lottery;

    return [
      {
        type: "馬連",
        legs: "軸→相手3頭",
        points: "3点",
        stake: fmtYen(umaren),
        stakeYen: umaren,
        note: "中心の買い目です。" + oddsLabel,
      },
      {
        type: "ワイド",
        legs: "軸→相手2頭",
        points: "2点",
        stake: fmtYen(wide),
        stakeYen: wide,
        note: "的中を意識した補助の買い目です。" + driftHint,
      },
      {
        type: "三連複",
        legs: "軸＋相手2〜3",
        points: "2-3点",
        stake: fmtYen(trio),
        stakeYen: trio,
        note: "保険として点数を抑えて入れる部分です",
      },
      {
        type: "三連単",
        legs: "1着固定マルチ抑制",
        points: "6点前後",
        stake: fmtYen(trifecta),
        stakeYen: trifecta,
        note: "一発狙いは総額の範囲内で楽しむ程度に",
      },
    ];
  }

  function comboKey(nums, ordered) {
    var xs = (nums || []).map(Number).filter(function (n) {
      return Number.isFinite(n) && n >= 1;
    });
    if (!ordered) xs = xs.slice().sort(function (a, b) {
      return a - b;
    });
    return xs.join("-");
  }

  function expandBetTickets(betType, amount, axis, rivals) {
    amount = Math.max(0, Math.round(Number(amount) || 0));
    rivals = (rivals || [])
      .map(Number)
      .filter(function (n) {
        return Number.isFinite(n) && n >= 1 && n !== axis;
      });
    var tickets = [];
    if (amount <= 0 || axis == null || !Number.isFinite(axis)) return tickets;

    if (betType === "単勝" || betType === "複勝") {
      tickets.push({ legs: [axis], stake: amount || 100, key: String(axis) });
    } else if (betType === "馬連") {
      var partners = rivals.slice(0, 3);
      if (!partners.length) return tickets;
      var unit = Math.max(100, Math.floor(amount / partners.length / 100) * 100);
      partners.forEach(function (p) {
        tickets.push({
          legs: [axis, p].slice().sort(function (a, b) {
            return a - b;
          }),
          stake: unit,
          key: comboKey([axis, p]),
        });
      });
    } else if (betType === "馬単") {
      var sPartners = rivals.slice(0, 3);
      if (!sPartners.length) return tickets;
      var sUnit = Math.max(100, Math.floor(amount / sPartners.length / 100) * 100);
      sPartners.forEach(function (p) {
        tickets.push({
          legs: [axis, p],
          stake: sUnit,
          key: comboKey([axis, p], true),
          ordered: true,
        });
      });
    } else if (betType === "ワイド") {
      var wPartners = rivals.slice(0, 2);
      if (!wPartners.length) return tickets;
      var wUnit = Math.max(100, Math.floor(amount / wPartners.length / 100) * 100);
      wPartners.forEach(function (p) {
        tickets.push({
          legs: [axis, p].slice().sort(function (a, b) {
            return a - b;
          }),
          stake: wUnit,
          key: comboKey([axis, p]),
        });
      });
    } else if (betType === "三連複") {
      var pool = [axis].concat(rivals.slice(0, 3));
      var uniq = [];
      pool.forEach(function (n) {
        if (uniq.indexOf(n) < 0) uniq.push(n);
      });
      if (uniq.length < 3) return tickets;
      var combos = [];
      for (var i = 0; i < uniq.length; i++) {
        for (var j = i + 1; j < uniq.length; j++) {
          for (var k = j + 1; k < uniq.length; k++) {
            combos.push([uniq[i], uniq[j], uniq[k]]);
          }
        }
      }
      var tUnit = Math.max(100, Math.floor(amount / Math.max(combos.length, 1) / 100) * 100);
      combos.forEach(function (c) {
        tickets.push({
          legs: c.slice().sort(function (a, b) {
            return a - b;
          }),
          stake: tUnit,
          key: comboKey(c),
        });
      });
    } else if (betType === "三連単") {
      var r = rivals.slice(0, 3);
      if (r.length < 2) return tickets;
      var perms = [];
      for (var a = 0; a < r.length; a++) {
        for (var b = 0; b < r.length; b++) {
          if (a === b) continue;
          perms.push([axis, r[a], r[b]]);
        }
      }
      var fUnit = Math.max(100, Math.floor(amount / Math.max(perms.length, 1) / 100) * 100);
      perms.forEach(function (p) {
        tickets.push({
          legs: p,
          stake: fUnit,
          key: comboKey(p, true),
          ordered: true,
        });
      });
    }
    return tickets;
  }

  /**
   * Freeze strategy at race-view time so later AI changes do not rewrite history.
   */
  function buildStrategySnapshot(strategyData, opts) {
    opts = opts || {};
    var axisNum = num(strategyData && strategyData.axis && strategyData.axis.num);
    var rivals = ((strategyData && strategyData.rivals) || [])
      .map(function (r) {
        return {
          num: num(r.num),
          name: r.name,
          role: r.role,
        };
      })
      .filter(function (r) {
        return r.num != null;
      });
    var rivalNums = rivals.map(function (r) {
      return r.num;
    });
    var bets = {};
    var purchase = 0;
    ((strategyData && strategyData.tickets) || []).forEach(function (t) {
      var type = t.type;
      var amount = Math.round(Number(t.stakeYen) || 0);
      var tickets = expandBetTickets(type, amount, axisNum, rivalNums);
      var spent =
        tickets.reduce(function (s, x) {
          return s + (x.stake || 0);
        }, 0) || amount;
      bets[type] = { amount: spent, tickets: tickets };
      purchase += spent;
    });
    return {
      axis: strategyData && strategyData.axis,
      rivals: rivals,
      prediction_version: opts.predictionVersion || null,
      bets: bets,
      purchase_amount: purchase,
      captured_at: new Date().toISOString(),
    };
  }

  function toDisplayBankroll(bank) {
    return {
      total: fmtYen(bank.total),
      main: pct(bank.mainPct) + "（" + fmtYen(bank.main) + "）",
      cover: pct(bank.coverPct) + "（" + fmtYen(bank.cover) + "）",
      lottery: pct(bank.lotteryPct) + "（" + fmtYen(bank.lottery) + "）",
      note: bank.note,
      raw: bank,
    };
  }

  global.ExpectStrategyStakes = {
    computeBankroll: computeBankroll,
    buildTickets: buildTickets,
    buildStrategySnapshot: buildStrategySnapshot,
    expandBetTickets: expandBetTickets,
    toDisplayBankroll: toDisplayBankroll,
    oddsFromBoard: oddsFromBoard,
    seriesDrift: seriesDrift,
    fmtYen: fmtYen,
  };
})(typeof window !== "undefined" ? window : globalThis);
