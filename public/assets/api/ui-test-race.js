/**
 * ExpectUiTestRace — Frontend-only UI 開発用テストレース
 *
 * HARD ISOLATION:
 *   race_id === ui-test-race-001 のとき Prediction / Board / History / Analysis /
 *   SingleDetail / Catalog DATE LIST へ通信しない。
 *
 * 削除手順: beta.json の enable_ui_test_race を false、本ファイルと script タグを除去。
 */
(function (global) {
  "use strict";

  var RACE_ID = "ui-test-race-001";
  var FLAG = "enable_ui_test_race";
  var ENGINE = "frontend_ui_test_fixture";
  var MODEL = "ui-test-fixture-1.0.0";

  /** 計測: テストレース経路で実際に backend fetch が走った回数（0 が目標） */
  var backendCallCount = 0;

  function isUiTestRaceId(raceId) {
    return String(raceId || "").trim() === RACE_ID;
  }

  function enabled() {
    if (!isUiTestRaceId(RACE_ID)) return false;
    if (global.ExpectUiFeatures && typeof ExpectUiFeatures.enabled === "function") {
      return !!ExpectUiFeatures.enabled(FLAG);
    }
    return false;
  }

  function runners() {
    var names = [
      "テスト馬イチバン",
      "テスト馬ニバン",
      "テスト馬サンバン",
      "テスト馬ヨンバン",
      "テスト馬ゴバン",
      "テスト馬ロクバン",
      "テスト馬ナナバン",
      "テスト馬ハチバン",
      "テスト馬キュウバン",
      "テスト馬ジュウバン",
      "テスト馬ジュウイチ",
      "テスト馬ジュウニ",
      "テスト馬ジュウサン",
      "テスト馬ジュウヨン",
      "テスト馬ジュウゴ",
      "テスト馬ジュウロク",
    ];
    var marks = {
      1: "honmei",
      5: "taikou",
      9: "ana",
      12: "chuuken",
    };
    var out = [];
    var i;
    for (i = 0; i < names.length; i++) {
      var num = i + 1;
      var mark = marks[num] || "none";
      var rank = mark === "honmei" ? 1 : mark === "taikou" ? 2 : mark === "ana" ? 3 : mark === "chuuken" ? 4 : num + 3;
      out.push({
        candidate_id: "ui-test-c" + String(num).padStart(2, "0"),
        horse_number: num,
        horse_name: names[i],
        model_rank: rank,
        win_prob: Math.max(0.02, 0.2 - i * 0.01),
        mark: mark,
        mark_rank: mark === "none" ? null : 1,
        ability_scores:
          mark === "honmei"
            ? {
                // Canonical ability keys (analysis-bind chartsFromAbilityScores)
                history_score: 0.78,
                distance_score: 0.72,
                style_distance_fit_weight: 0.7,
                front_rate: 0.68,
                pace_resilience: 0.65,
                // UI aliases kept for older readers
                history: 0.78,
                distance: 0.72,
                style_fit: 0.7,
                front: 0.68,
              }
            : undefined,
      });
    }
    return out;
  }

  function raceInfo() {
    return {
      race_id: RACE_ID,
      date: "TEST",
      date_label: "UIテスト",
      date_full: "UIテスト（本番データではありません）",
      venue: "東京",
      meeting_id: "ui-test-tokyo",
      race_no: 11,
      race_number: 11,
      race_name: "Expect Challenge テストレース",
      race_label: "UIテスト 東京11R",
      post_time: "15:40",
      distance: 1600,
      surface: "turf",
      course: "左",
      class_label: "UIテスト",
      grade: "TEST",
      field_size: 16,
      race_status: "UI_TEST",
    };
  }

  function getCard() {
    var info = raceInfo();
    return {
      schema_version: "expect-race-card-summary/1.0",
      race_id: RACE_ID,
      race_info: info,
      prediction: {
        status: "ready",
        engine_source: ENGINE,
      },
      summary: {
        honmei: {
          horse_number: 1,
          horse_name: "テスト馬イチバン",
          mark: "honmei",
        },
        confidence: {
          score: 0.74,
          band: "high",
          label: "high",
        },
        short_reason: "UIテスト用フィクスチャ（本番AIではありません）",
      },
      __ui_test_fixture: true,
    };
  }

  function getBundle() {
    var info = raceInfo();
    var list = runners();
    return {
      schema_version: "single-prediction-bundle/2.0",
      race_id: RACE_ID,
      generated_at: "2026-08-30T00:00:00+09:00",
      model_version: MODEL,
      core_version: "ui-test-core-0.0.0",
      product_version: "ui-test-fixture",
      status: "ok",
      warnings: ["FRONTEND_UI_TEST_FIXTURE_ONLY"],
      race_info: info,
      evaluation: {
        status: "ok",
        world: "ui_test_world",
        sub_world: "ui_test_sub",
        runners: list,
      },
      ai_confidence: {
        schema_version: "single-ai-confidence/1.0",
        status: "ok",
        score: 0.74,
        score_unit: "normalized",
        band: "high",
        notes: "UIテスト用フィクスチャ。Production AI は未呼び出し。",
        computed_at: "2026-08-30T00:00:00+09:00",
      },
      explain: {
        meta: {
          world: "ui_test_world",
          sub_world: "ui_test_sub",
          strategy_id: "ui-test-fixture",
          confidence_band: "high",
        },
        reasons: [
          {
            candidate_id: "ui-test-c01",
            horse_number: 1,
            bullets: ["UIテスト本命（フィクスチャ）", "本番AI推論は行っていません"],
          },
          {
            candidate_id: "ui-test-c05",
            horse_number: 5,
            bullets: ["UIテスト対抗"],
          },
          {
            candidate_id: "ui-test-c09",
            horse_number: 9,
            bullets: ["UIテスト穴"],
          },
          {
            candidate_id: "ui-test-c12",
            horse_number: 12,
            bullets: ["UIテスト中穴"],
          },
        ],
        narrative:
          "【UIテスト】本命1・対抗5・穴9・中穴12はフロントエンド専用フィクスチャです。Production Prediction / PI / Final には接続していません。",
      },
      betting_recommendations: {
        schema_version: "single-betting-recommendations/1.0",
        race_id: RACE_ID,
        generated_at: "2026-08-30T00:00:00+09:00",
        strategy_id: "ui-test-fixture",
        status: "ok",
        items: [
          {
            recommendation_id: "ui-tf-1",
            bet_type: "trifecta",
            combination: {
              schema_version: "single-combination/1.0",
              selection_mode: "exact_order",
              is_ordered: true,
              cardinality: 3,
              legs: [
                { position: 1, horse_number: 1, candidate_id: "ui-test-c01" },
                { position: 2, horse_number: 5, candidate_id: "ui-test-c05" },
                { position: 3, horse_number: 9, candidate_id: "ui-test-c09" },
              ],
            },
            recommendation_rank: 1,
            recommendation_score: 0.9,
            score_unit: "normalized",
            comment: "UIテスト用買い目（非本番）",
            legs_display: "1-5-9",
          },
        ],
      },
      __meta: {
        engine_source: ENGINE,
        prediction_status: "ready",
        prediction_available: true,
        model_version: MODEL,
        ui_test_fixture: true,
      },
      __ui_test_fixture: true,
    };
  }

  function getBoard() {
    var list = runners();
    var oddsBase = [3.2, 5.1, 8.4, 12.0, 6.8, 15.0, 22.0, 28.0, 18.5, 35.0, 42.0, 25.0, 55.0, 70.0, 90.0, 120.0];
    return {
      schema_version: "expect-race-board/1.0",
      race_id: RACE_ID,
      entries: list.map(function (r, i) {
        var frame = Math.min(8, Math.ceil(r.horse_number / 2));
        return {
          horse_number: r.horse_number,
          frame_number: frame,
          horse_name: r.horse_name,
          sex_age: i % 2 === 0 ? "牡4" : "牝3",
          jockey: "テスト騎手" + r.horse_number,
          weight: 54 + (i % 4) * 0.5,
          odds: oddsBase[i],
          popularity: i + 1,
        };
      }),
      __ui_test_fixture: true,
    };
  }

  function getHistory() {
    return {
      schema_version: "expect-race-history/1.0",
      race_id: RACE_ID,
      items: [],
      __ui_test_fixture: true,
    };
  }

  function getAnalysis() {
    return {
      schema_version: "expect-analysis/1.0",
      race_id: RACE_ID,
      charts: [
        { key: "history", label: "近走成績", value: 78 },
        { key: "distance", label: "距離適性", value: 72 },
        { key: "style_fit", label: "脚質適性", value: 70 },
        { key: "front", label: "前半パフォーマンス", value: 68 },
        { key: "pace_resilience", label: "展開耐性", value: 65 },
      ],
      overall: 74,
      narrative: "【UIテスト】評価内訳はフロントエンド専用フィクスチャです。",
      __ui_test_fixture: true,
    };
  }

  function getWithMetaResult() {
    var bundle = getBundle();
    return {
      bundle: bundle,
      meta: bundle.__meta,
      pending: false,
    };
  }

  /**
   * 一覧用: 実レース cards の先頭に 1 件だけ追加。重複防止。
   * 日付タブ集計は ISO のみのため date=TEST は開催日グループを壊さない。
   */
  function injectCards(cards) {
    if (!enabled()) return cards || [];
    var list = Array.isArray(cards) ? cards.slice() : [];
    var i;
    for (i = 0; i < list.length; i++) {
      if (list[i] && isUiTestRaceId(list[i].race_id)) {
        return list;
      }
    }
    list.unshift(getCard());
    return list;
  }

  /** フィルタ集計用: テストカードを除外（実レース件数を維持） */
  function withoutTestCards(cards) {
    return (cards || []).filter(function (c) {
      return !(c && isUiTestRaceId(c.race_id));
    });
  }

  function applyDetailHeader(raceId) {
    if (!enabled() || !isUiTestRaceId(raceId)) return false;
    var info = raceInfo();
    if (global.ExpectPredictionBind) {
      if (ExpectPredictionBind.setCatalogRaceInfo) {
        ExpectPredictionBind.setCatalogRaceInfo(raceId, info);
      }
      if (ExpectPredictionBind.paintRaceDetailHeader) {
        ExpectPredictionBind.paintRaceDetailHeader(info, raceId);
      }
    }
    return true;
  }

  function wrapMethod(obj, key, handler) {
    if (!obj || typeof obj[key] !== "function") return;
    if (obj[key].__uiTestRaceWrapped) return;
    var orig = obj[key];
    function wrapped() {
      var args = arguments;
      var raceId = args[0];
      if (enabled() && isUiTestRaceId(raceId)) {
        return handler.apply(null, args);
      }
      return orig.apply(obj, args);
    }
    wrapped.__uiTestRaceWrapped = true;
    wrapped.__uiTestRaceOrig = orig;
    obj[key] = wrapped;
  }

  function wrapPurchaseMethod(obj, key, handler) {
    if (!obj || typeof obj[key] !== "function") return;
    if (obj[key].__uiTestRaceWrapped) return;
    var orig = obj[key];
    function wrapped(body) {
      var rid = body && body.race_id;
      if (enabled() && isUiTestRaceId(rid)) {
        return handler(body);
      }
      return orig.apply(obj, arguments);
    }
    wrapped.__uiTestRaceWrapped = true;
    wrapped.__uiTestRaceOrig = orig;
    obj[key] = wrapped;
  }

  function noteBackendCall() {
    backendCallCount += 1;
  }

  /** Bottom Nav「分析」と同じ path（partials-nav.js） */
  var ANALYSIS_ICON_SVG =
    '<svg class="nav-ico race-detail-cta-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M4 19h16M7 16V9M12 16V5M17 16v-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
    "</svg>";

  /** Bottom Nav「チャレンジ」と同じ path（partials-nav.js） */
  var CHALLENGE_ICON_SVG =
    '<svg class="nav-ico race-detail-cta-ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
    '<path d="M4 19h16M7 16V9M12 16v-7M17 16V6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
    '<path d="M6 6.5h3.5M14.5 4h3.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>' +
    "</svg>";

  function buyStrategyHref(raceId) {
    return "strategy.html?race_id=" + encodeURIComponent(raceId || RACE_ID);
  }

  /**
   * Challenge専用購入画面（買い目攻略 strategy.html とは分離）。
   */
  function challengePurchaseHref(raceId) {
    return (
      "challenge-purchase.html?race_id=" +
      encodeURIComponent(raceId || RACE_ID)
    );
  }

  function showChallengeCtaForRace(raceId) {
    return enabled() && isUiTestRaceId(raceId);
  }

  var purchaseBackendCallCount = 0;

  function blockUiTestPurchase() {
    purchaseBackendCallCount += 1;
    return Promise.reject(
      Object.assign(new Error("UIテストレースのため実購入は登録されません。"), {
        code: "UI_TEST_PURCHASE_BLOCKED",
        status: 0,
      })
    );
  }

  function mountUiTestPurchaseBanner(container) {
    if (!container) return;
    if (container.querySelector("[data-ui-test-purchase-banner]")) return;
    var banner = document.createElement("div");
    banner.className = "ui-test-purchase-banner";
    banner.setAttribute("data-ui-test-purchase-banner", "1");
    banner.setAttribute("role", "status");
    banner.innerHTML =
      "<strong>UIテストレース</strong>" +
      "<p>実際の購入・払戻は行われません。Frontend UI 確認専用です。</p>";
    container.insertBefore(banner, container.firstChild);
  }

  function enhancePurchaseFormForUiTest(container, raceId) {
    if (!enabled() || !isUiTestRaceId(raceId) || !container) return;
    mountUiTestPurchaseBanner(container);
    var title = container.querySelector("#purchaseCard h3");
    if (title) title.textContent = "購入を確認（UIテスト・未登録）";
    var lead = container.querySelector("#purchaseCard > p.muted");
    if (lead) {
      lead.textContent =
        "UIテスト用です。ボタンを押しても Production への購入登録・DB書き込みは行いません。";
    }
    var btn = container.querySelector("#purchaseSubmitBtn");
    if (btn) btn.textContent = "テスト確認（実購入なし）";
  }

  function installHooks() {
    if (!global.ExpectApi) return;

    wrapMethod(ExpectApi.Prediction, "getWithMeta", function () {
      return Promise.resolve(getWithMetaResult());
    });
    wrapMethod(ExpectApi.Prediction, "get", function () {
      return Promise.resolve(getBundle());
    });

    if (ExpectApi.SingleDetail) {
      wrapMethod(ExpectApi.SingleDetail, "getWithMeta", function () {
        return Promise.resolve(getWithMetaResult());
      });
    }

    if (ExpectApi.RaceBoard) {
      wrapMethod(ExpectApi.RaceBoard, "getBoard", function () {
        return Promise.resolve(getBoard());
      });
    }

    if (ExpectApi.RaceHistory) {
      wrapMethod(ExpectApi.RaceHistory, "getHistory", function () {
        return Promise.resolve(getHistory());
      });
    }

    if (ExpectApi.Analysis) {
      wrapMethod(ExpectApi.Analysis, "get", function () {
        return Promise.resolve(getAnalysis());
      });
    }

    if (ExpectApi.OddsSeries && typeof ExpectApi.OddsSeries.getSeries === "function") {
      wrapMethod(ExpectApi.OddsSeries, "getSeries", function () {
        return Promise.resolve(null);
      });
    }

    if (ExpectApi.User && typeof ExpectApi.User.registerPurchase === "function") {
      wrapPurchaseMethod(ExpectApi.User, "registerPurchase", function () {
        return blockUiTestPurchase();
      });
    }
  }

  global.ExpectUiTestRace = {
    RACE_ID: RACE_ID,
    FLAG: FLAG,
    ENGINE: ENGINE,
    ANALYSIS_ICON_SVG: ANALYSIS_ICON_SVG,
    CHALLENGE_ICON_SVG: CHALLENGE_ICON_SVG,
    enabled: enabled,
    isUiTestRaceId: isUiTestRaceId,
    getCard: getCard,
    getBundle: getBundle,
    getBoard: getBoard,
    getHistory: getHistory,
    getAnalysis: getAnalysis,
    getWithMetaResult: getWithMetaResult,
    injectCards: injectCards,
    withoutTestCards: withoutTestCards,
    applyDetailHeader: applyDetailHeader,
    installHooks: installHooks,
    buyStrategyHref: buyStrategyHref,
    challengePurchaseHref: challengePurchaseHref,
    showChallengeCtaForRace: showChallengeCtaForRace,
    enhancePurchaseFormForUiTest: enhancePurchaseFormForUiTest,
    mountUiTestPurchaseBanner: mountUiTestPurchaseBanner,
    getBackendCallCount: function () {
      return backendCallCount;
    },
    getPurchaseBackendCallCount: function () {
      return purchaseBackendCallCount;
    },
    noteBackendCall: noteBackendCall,
  };

  // Prediction 等が先に定義される想定。遅延インストールも用意。
  if (global.ExpectApi) {
    installHooks();
  } else {
    setTimeout(installHooks, 0);
  }
})(typeof window !== "undefined" ? window : this);
