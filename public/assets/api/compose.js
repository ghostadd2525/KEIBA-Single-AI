/**
 * 画面構築: PredictionBundle を入口にし、race_id で他サービスを参照する
 */
(function (global) {
  "use strict";

  function settled(promise) {
    return promise.then(
      function (v) {
        return { ok: true, value: v };
      },
      function (e) {
        return { ok: false, error: e };
      }
    );
  }

  /**
   * レース詳細の入口
   * 1) PredictionBundle を取得
   * 2) bundle.race_id で Analysis を参照（Confidence/Ticket は Bundle 内から投影）
   */
  function raceDetail(raceId) {
    return global.ExpectApi.Prediction.get(raceId).then(function (bundle) {
      var id = global.ExpectBundle.raceId(bundle) || raceId;
      return settled(global.ExpectApi.Analysis.get(id)).then(function (analysisPart) {
        return {
          raceId: id,
          bundle: bundle,
          analysis: analysisPart.ok ? analysisPart.value : null,
          confidence: global.ExpectBundle.confidence(bundle),
          tickets: global.ExpectBundle.tickets(bundle),
        };
      });
    });
  }

  /** 一覧: PredictionBundle[] */
  function raceList(opts) {
    return global.ExpectApi.Prediction.list(opts || {});
  }

  /** ホーム: Bundle 一覧から注目を選び、その Bundle だけでカードを構築 */
  function homeSpotlight(opts) {
    return global.ExpectApi.Prediction.list(opts || {}).then(function (list) {
      var items = (list && list.items) || [];
      var top = items.slice().sort(function (a, b) {
        return (
          (global.ExpectBundle.scorePercent(b) || 0) - (global.ExpectBundle.scorePercent(a) || 0)
        );
      })[0] || null;
      return {
        list: list,
        bundle: top,
        confidence: top ? global.ExpectBundle.confidence(top) : null,
      };
    });
  }

  /**
   * 分析画面: 各 race_id について
   * PredictionBundle（入口）→ Analysis / Confidence（race_id 参照、Confidence は Bundle 投影でも可）
   */
  function analysisForRaces(raceIds) {
    return Promise.all(
      (raceIds || []).map(function (id) {
        return global.ExpectApi.Prediction.get(id)
          .then(function (bundle) {
            var rid = global.ExpectBundle.raceId(bundle) || id;
            return settled(global.ExpectApi.Analysis.get(rid)).then(function (a) {
              return {
                race_id: rid,
                bundle: bundle,
                analysis: a.ok ? a.value : null,
                confidence: global.ExpectBundle.confidence(bundle),
              };
            });
          })
          .catch(function () {
            return { race_id: id, bundle: null, analysis: null, confidence: null };
          });
      })
    );
  }

  global.ExpectCompose = {
    raceDetail: raceDetail,
    raceList: raceList,
    homeSpotlight: homeSpotlight,
    analysisForRaces: analysisForRaces,
  };
})(window);
