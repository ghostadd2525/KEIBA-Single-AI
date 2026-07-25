/**
 * ExpectApi.Analysis — AnalysisService クライアント
 *
 * GET /api/analysis/:raceId → Analysis（expect-analysis/1.0）
 * キーは必ず PredictionBundle.race_id
 *
 * fetch はここ以外に書かない
 *
 * 契約: contracts/expect-analysis/1.0/
 */
(function (global) {
  "use strict";

  var SCHEMA = "expect-analysis/1.0";

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function normalizeAnalysis(raw, raceId) {
    if (!raw || typeof raw !== "object") {
      return {
        schema_version: SCHEMA,
        race_id: raceId,
        charts: [],
        overall: null,
        narrative: "",
      };
    }
    return {
      schema_version: SCHEMA,
      race_id: raceId || raw.race_id || "",
      charts: Array.isArray(raw.charts) ? raw.charts : [],
      overall: raw.overall != null ? Number(raw.overall) : null,
      narrative: typeof raw.narrative === "string" ? raw.narrative : "",
    };
  }

  function mockGet(id) {
    return fetch("data/mocks/analysis.json")
      .then(function (r) {
        return r.json();
      })
      .then(function (all) {
        var row = all[id] || {
          race_id: id,
          charts: [
            { key: "pedigree", label: "血統", value: 70 },
            { key: "pace", label: "展開", value: 68 },
            { key: "jockey", label: "騎手", value: 66 },
            { key: "form", label: "近走", value: 67 },
            { key: "odds", label: "オッズ", value: 64 },
          ],
          overall: 70,
          narrative: "データ準備中のレースです。",
        };
        return normalizeAnalysis(row, id);
      });
  }

  function apiGet(path) {
    var headers = { Accept: "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;

    return fetch(path, { method: "GET", headers: headers }).then(function (res) {
      return res.text().then(function (text) {
        var payload = null;
        try {
          payload = text ? JSON.parse(text) : null;
        } catch (e) {
          payload = null;
        }
        if (!res.ok || (payload && payload.ok === false)) {
          var err = new Error(
            (payload && payload.error && payload.error.message) || "API error " + res.status
          );
          err.status = res.status;
          throw err;
        }
        return payload && payload.data != null ? payload.data : payload;
      });
    });
  }

  function attachContract(analysis) {
    if (!analysis) return null;
    if (global.ExpectContractGuard) {
      var r = ExpectContractGuard.validateAnalysis(analysis);
      analysis.__contract = r;
      if (!r.ok) {
        console.warn("[ExpectApi.Analysis] contract violation", r.errors);
      }
    }
    return analysis;
  }

  var Analysis = {
    SCHEMA: SCHEMA,

    /** @returns {Promise<Object>} Analysis */
    get: function (raceId) {
      if (!raceId) return Promise.reject(new Error("race_id required"));
      return apiGet("/api/analysis/" + encodeURIComponent(raceId))
        .then(function (data) {
          return attachContract(normalizeAnalysis(data, raceId));
        })
        .catch(function (err) {
          if (global.ExpectMockGate && ExpectMockGate.allowMockFallback()) {
            return mockGet(raceId).then(attachContract);
          }
          return Promise.reject(err || new Error("Analysis API unavailable"));
        });
    },

    validate: function (analysis) {
      if (global.ExpectContractGuard) {
        return ExpectContractGuard.validateAnalysis(analysis);
      }
      return { ok: true, errors: [], contract: "Analysis" };
    },

    /** charts[] → score map（能力値キー + 旧キー互換） */
    chartMap: function (analysis) {
      var map = {
        history: 0,
        distance: 0,
        style_fit: 0,
        front: 0,
        pace_resilience: 0,
        overall: 0,
        pedigree: 0,
        pace: 0,
        jockey: 0,
        form: 0,
        odds: 0,
        style: 0,
      };
      if (!analysis) return map;
      if (analysis.overall != null) map.overall = Number(analysis.overall) || 0;
      (analysis.charts || []).forEach(function (c) {
        if (c && c.key) map[c.key] = Number(c.value) || 0;
      });
      return map;
    },
  };

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Analysis = Analysis;
})(window);
