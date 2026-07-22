/**
 * ExpectApi.Prediction — Single-AI PredictionService クライアント
 *
 * GET /api/predictions      → PredictionBundle[]
 * GET /api/predictions/:id  → PredictionBundle
 *
 * fetch はここ以外に書かない（画面は ExpectApi.Prediction のみ使う）
 *
 * 契約正本:
 *   contracts/single-prediction-bundle/2.0/schema.json
 *   contracts/single-prediction-bundle/2.0/PredictionBundle.d.ts
 *   contracts/single-prediction-bundle/2.0/typedef.js（JSDoc）
 */
(function (global) {
  "use strict";

  /** @type {"single-prediction-bundle/2.0"} */
  var SCHEMA = "single-prediction-bundle/2.0";

  function getToken() {
    try {
      return global.localStorage.getItem("expect_access_token_v1") || "";
    } catch (e) {
      return "";
    }
  }

  function buildUrl(path, query) {
    var url = path;
    if (query && typeof query === "object") {
      var qs = new URLSearchParams();
      Object.keys(query).forEach(function (k) {
        if (query[k] != null && query[k] !== "") qs.set(k, query[k]);
      });
      var q = qs.toString();
      if (q) url += "?" + q;
    }
    return url;
  }

  function normalizeBundle(raw, raceId) {
    if (!raw || typeof raw !== "object") return null;
    var id = raceId || raw.race_id || (raw.race_info && raw.race_info.race_id);
    var info = Object.assign({}, raw.race_info || {});
    if (id) info.race_id = id;
    var ev = raw.evaluation || {};
    var conf = raw.ai_confidence || {};
    var ex = raw.explain || {};
    var bets = raw.betting_recommendations || {};
    return Object.assign({}, raw, {
      schema_version: SCHEMA,
      race_id: id,
      race_info: info,
      evaluation: {
        status: ev.status || "unknown",
        world: ev.world != null ? ev.world : null,
        sub_world: ev.sub_world != null ? ev.sub_world : null,
        runners: Array.isArray(ev.runners) ? ev.runners : [],
      },
      ai_confidence: Object.assign({}, conf, {
        status: conf.status || "unknown",
        score: Object.prototype.hasOwnProperty.call(conf, "score") ? conf.score : null,
        band: conf.band || "unknown",
      }),
      explain: (function () {
        var out = {
          meta: ex.meta || {},
          reasons: Array.isArray(ex.reasons) ? ex.reasons : [],
          narrative: typeof ex.narrative === "string" ? ex.narrative : "",
        };
        if (ex.schema_version) out.schema_version = ex.schema_version;
        if (ex.reason) out.reason = ex.reason;
        if (ex.confidence_reason) out.confidence_reason = ex.confidence_reason;
        if (ex.decision_trace) out.decision_trace = ex.decision_trace;
        return out;
      })(),
      betting_recommendations: Object.assign({ race_id: id, items: [] }, bets, {
        items: Array.isArray(bets.items) ? bets.items : [],
      }),
    });
  }

  function scorePercent(bundle) {
    var c = (bundle && bundle.ai_confidence) || {};
    if (typeof c.score === "number") {
      return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
    }
    return null;
  }

  function mockList(query) {
    return Promise.all([
      fetch("data/mocks/races.json").then(function (r) {
        return r.json();
      }),
      fetch("data/mocks/bundle-20260719_hanshin_11.json").then(function (r) {
        return r.json();
      }),
    ]).then(function (pair) {
      var catalog = pair[0];
      var template = pair[1];
      var races = catalog.races || [];
      if (query && query.date) {
        races = races.filter(function (r) {
          return r.date === query.date;
        });
      }
      if (query && query.venue) {
        races = races.filter(function (r) {
          return r.venue === query.venue;
        });
      }
      return Promise.all(
        races.map(function (race) {
          return fetch("data/mocks/bundle-" + race.race_id + ".json")
            .then(function (r) {
              if (!r.ok) throw new Error("missing");
              return r.json();
            })
            .then(function (b) {
              return normalizeBundle(b, race.race_id);
            })
            .catch(function () {
              var b = normalizeBundle(template, race.race_id);
              b.race_info = Object.assign({}, b.race_info, {
                venue: race.venue,
                race_no: race.race_no,
                post_time: race.post_time,
                class_label: race.class_label,
                date: race.date,
                date_label: race.date_label,
                date_full: race.date_full,
                grade: race.badge,
                bg: race.bg,
              });
              if (race.ai_confidence != null) {
                b.ai_confidence = Object.assign({}, b.ai_confidence, {
                  score: Number(race.ai_confidence) / 100,
                  status: "ok",
                });
              }
              return b;
            });
        })
      );
    });
  }

  function mockGet(id) {
    return fetch("data/mocks/bundle-" + id + ".json")
      .catch(function () {
        return fetch("data/mocks/bundle-20260719_hanshin_11.json");
      })
      .then(function (r) {
        return r.json();
      })
      .then(function (b) {
        return normalizeBundle(b, id);
      });
  }

  function parsePayload(payload) {
    if (!payload || typeof payload !== "object") {
      return { data: payload, meta: {} };
    }
    if (payload.ok === false) {
      var err = new Error(
        (payload.error && payload.error.message) || "API error"
      );
      err.status = payload.status;
      throw err;
    }
    return {
      data: payload.data != null ? payload.data : payload,
      meta: payload.meta || {},
    };
  }

  function attachMeta(bundle, meta) {
    if (!bundle) return null;
    if (meta && typeof meta === "object") {
      bundle.__meta = Object.assign({}, meta);
    }
    return bundle;
  }

  function apiGet(path, query) {
    var headers = { Accept: "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;

    return fetch(buildUrl(path, query), { method: "GET", headers: headers }).then(function (res) {
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
        return parsePayload(payload);
      });
    });
  }

  function attachContract(bundle) {
    if (!bundle) return null;
    if (global.ExpectContractGuard) {
      var r = ExpectContractGuard.validatePredictionBundle(bundle);
      bundle.__contract = r;
      if (!r.ok) {
        console.warn("[ExpectApi.Prediction] contract violation", r.errors);
      }
    }
    return bundle;
  }

  var Prediction = {
    SCHEMA: SCHEMA,

    /** @returns {Promise<PredictionBundle[]>} */
    list: function (opts) {
      opts = opts || {};
      var query = { date: opts.date || "", venue: opts.venue || "" };
      return apiGet("/api/predictions", query)
        .then(function (parsed) {
          var data = parsed.data;
          var meta = parsed.meta || {};
          var items = Array.isArray(data) ? data : (data && data.items) || [];
          var metaItems = Array.isArray(meta.items) ? meta.items : [];
          return items.map(function (b) {
            var itemMeta = Object.assign({}, meta);
            for (var i = 0; i < metaItems.length; i++) {
              if (metaItems[i] && b && metaItems[i].race_id === b.race_id) {
                itemMeta = Object.assign({}, meta, metaItems[i]);
                break;
              }
            }
            return attachContract(attachMeta(normalizeBundle(b, b.race_id), itemMeta));
          });
        })
        .catch(function (err) {
          if (global.ExpectMockGate && ExpectMockGate.allowMockFallback()) {
            return mockList(query).then(function (items) {
              return items.map(function (b) {
                return attachContract(b);
              });
            });
          }
          return Promise.reject(err || new Error("Prediction API unavailable"));
        });
    },

    /** @returns {Promise<PredictionBundle>} */
    get: function (raceId) {
      return Prediction.getWithMeta(raceId).then(function (result) {
        return result.bundle;
      });
    },

    /** @returns {Promise<{bundle: PredictionBundle, meta: object}>} */
    getWithMeta: function (raceId) {
      if (!raceId) return Promise.reject(new Error("race_id required"));
      return apiGet("/api/predictions/" + encodeURIComponent(raceId))
        .then(function (parsed) {
          var bundle = attachContract(
            attachMeta(normalizeBundle(parsed.data, raceId), parsed.meta || {})
          );
          return { bundle: bundle, meta: (bundle && bundle.__meta) || parsed.meta || {} };
        })
        .catch(function (err) {
          if (global.ExpectMockGate && ExpectMockGate.allowMockFallback()) {
            return mockGet(raceId).then(function (b) {
              var bundle = attachContract(b);
              return { bundle: bundle, meta: (bundle && bundle.__meta) || {} };
            });
          }
          return Promise.reject(err || new Error("Prediction API unavailable"));
        });
    },

    scorePercent: scorePercent,

    /** 契約チェック（ExpectContractGuard 委譲） */
    validate: function (bundle) {
      if (global.ExpectContractGuard) {
        return ExpectContractGuard.validatePredictionBundle(bundle);
      }
      return { ok: true, errors: [], contract: "PredictionBundle" };
    },
  };

  global.ExpectApi = global.ExpectApi || {};
  global.ExpectApi.Prediction = Prediction;
})(window);
