/**
 * ExpectApi — AI ドメインサービス向けクライアント
 *
 * PredictionService は PredictionBundle（共通契約）を返す。
 * Analysis / Confidence / Ticket / Kaoba は bundle.race_id で参照する。
 * 画面の入口は PredictionBundle（ExpectCompose + ExpectBundle）。
 */
(function (global) {
  "use strict";

  var TOKEN_KEY = "expect_access_token_v1";

  function storage() {
    try {
      return global.localStorage;
    } catch (e) {
      return null;
    }
  }

  function getToken() {
    var s = storage();
    return s ? s.getItem(TOKEN_KEY) || "" : "";
  }

  function setToken(token) {
    var s = storage();
    if (!s) return false;
    if (!token) {
      s.removeItem(TOKEN_KEY);
      return true;
    }
    s.setItem(TOKEN_KEY, token);
    return true;
  }

  function useMock() {
    if (global.ExpectMockGate && typeof ExpectMockGate.allowMockFallback === "function") {
      return ExpectMockGate.allowMockFallback();
    }
    return global.EXPECT_USE_MOCK === true;
  }

  function buildUrl(path, query) {
    var url = path.charAt(0) === "/" ? path : "/" + path;
    if (query && typeof query === "object") {
      var qs = new URLSearchParams();
      Object.keys(query).forEach(function (k) {
        if (query[k] != null && query[k] !== "") qs.set(k, query[k]);
      });
      var q = qs.toString();
      if (q) url += (url.indexOf("?") >= 0 ? "&" : "?") + q;
    }
    return url;
  }

  function unwrap(res) {
    return res && res.data != null ? res.data : res;
  }

  function asPredictionBundle(raw, raceId, raceMeta) {
    var id = raceId || (raw && raw.race_id);
    var info = Object.assign({}, (raw && raw.race_info) || {});
    if (raceMeta) {
      info.race_id = id;
      info.date = raceMeta.date || info.date;
      info.venue = raceMeta.venue || info.venue;
      info.race_no = raceMeta.race_no != null ? raceMeta.race_no : info.race_no;
      info.post_time = raceMeta.post_time || info.post_time;
      info.class_label = raceMeta.class_label || info.class_label;
      info.grade = raceMeta.badge || info.grade;
      info.distance = raceMeta.distance != null ? raceMeta.distance : info.distance;
      info.surface = raceMeta.surface || info.surface;
      info.field_size = raceMeta.field_size != null ? raceMeta.field_size : info.field_size;
      info.date_label = raceMeta.date_label || info.date_label;
      info.date_full = raceMeta.date_full || info.date_full;
      info.bg = raceMeta.bg != null ? raceMeta.bg : info.bg;
    }
    info.race_id = id;
    var hint = raceMeta && raceMeta.ai_confidence != null ? Number(raceMeta.ai_confidence) : null;
    var conf = (raw && raw.ai_confidence) || {};
    if (hint != null) {
      conf = Object.assign({}, conf, {
        schema_version: "single-ai-confidence/1.0",
        status: "ok",
        score: hint / 100,
        score_unit: "normalized",
      });
    }
    return Object.assign({}, raw || {}, {
      schema_version: "single-prediction-bundle/2.0",
      race_id: id,
      race_info: info,
      evaluation: (raw && raw.evaluation) || { status: "list", runners: [] },
      ai_confidence: conf,
      explain: (raw && raw.explain) || { narrative: "", reasons: [], meta: {} },
      betting_recommendations: (raw && raw.betting_recommendations) || {
        schema_version: "single-betting-recommendations/1.0",
        race_id: id,
        status: "list",
        items: [],
      },
    });
  }

  function mockGet(path, query) {
    if (path === "/api/predictions") {
      return Promise.all([
        fetch("data/mocks/races.json").then(function (r) {
          return r.json();
        }),
        fetch("data/mocks/bundle-20260719_hanshin_11.json").then(function (r) {
          return r.json();
        }),
      ]).then(function (pair) {
        var raw = pair[0];
        var template = pair[1];
        var races = raw.races || [];
        if (query && query.date) {
          races = races.filter(function (i) {
            return i.date === query.date;
          });
        }
        if (query && query.venue && query.venue !== "すべて") {
          races = races.filter(function (i) {
            return i.venue === query.venue;
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
                return asPredictionBundle(b, race.race_id, race);
              })
              .catch(function () {
                return asPredictionBundle(template, race.race_id, race);
              });
          })
        ).then(function (items) {
          return {
            ok: true,
            meta: {
              source: "mock-fallback",
              service: "PredictionService",
              contract: "PredictionBundle",
            },
            data: { date: (query && query.date) || raw.date, venues: raw.venues, items: items },
          };
        });
      });
    }

    var pred = path.match(/^\/api\/predictions\/([^/?]+)/);
    if (pred) {
      var id = decodeURIComponent(pred[1]);
      return fetch("data/mocks/bundle-" + id + ".json")
        .catch(function () {
          return fetch("data/mocks/bundle-20260719_hanshin_11.json");
        })
        .then(function (r) {
          return r.json();
        })
        .then(function (bundle) {
          return {
            ok: true,
            meta: {
              source: "mock-fallback",
              service: "PredictionService",
              contract: "PredictionBundle",
            },
            data: asPredictionBundle(bundle, id),
          };
        });
    }

    var analysis = path.match(/^\/api\/analysis\/([^/?]+)/);
    if (analysis) {
      var aid = decodeURIComponent(analysis[1]);
      return fetch("data/mocks/analysis.json")
        .then(function (r) {
          return r.json();
        })
        .then(function (all) {
          var row = all[aid] || { race_id: aid, charts: [], overall: 70, narrative: "" };
          return {
            ok: true,
            meta: { source: "mock-fallback", service: "AnalysisService" },
            data: {
              schema_version: "expect-analysis/1.0",
              race_id: aid,
              charts: row.charts || [],
              overall: row.overall,
              narrative: row.narrative || "",
            },
          };
        });
    }

    var conf = path.match(/^\/api\/confidence\/([^/?]+)/);
    if (conf) {
      var cid = decodeURIComponent(conf[1]);
      return Promise.all([
        fetch("data/mocks/bundle-" + cid + ".json")
          .catch(function () {
            return fetch("data/mocks/bundle-20260719_hanshin_11.json");
          })
          .then(function (r) {
            return r.json();
          }),
        fetch("data/mocks/races.json").then(function (r) {
          return r.json();
        }),
      ]).then(function (pair) {
        var bundle = pair[0];
        var races = pair[1];
        var c = bundle.ai_confidence || {};
        var meta = ((races && races.races) || []).find(function (x) {
          return x.race_id === cid;
        });
        var scorePct =
          meta && meta.ai_confidence != null
            ? Number(meta.ai_confidence)
            : typeof c.score === "number"
              ? c.score <= 1
                ? Math.round(c.score * 100)
                : Math.round(c.score)
              : null;
        return {
          ok: true,
          meta: { source: "mock-fallback", service: "ConfidenceService" },
          data: {
            schema_version: "expect-confidence/1.0",
            race_id: cid,
            status: c.status || "ok",
            score: scorePct != null ? scorePct / 100 : c.score,
            score_percent: scorePct,
            score_unit: c.score_unit || "normalized",
            band: c.band || "unknown",
            factors: c.factors || [],
            component_scores: c.component_scores || {},
            notes: c.notes || "",
            computed_at: c.computed_at || null,
          },
        };
      });
    }

    var tickets = path.match(/^\/api\/tickets\/([^/?]+)/);
    if (tickets) {
      var tid = decodeURIComponent(tickets[1]);
      return fetch("data/mocks/bundle-" + tid + ".json")
        .catch(function () {
          return fetch("data/mocks/bundle-20260719_hanshin_11.json");
        })
        .then(function (r) {
          return r.json();
        })
        .then(function (bundle) {
          var br = bundle.betting_recommendations || {};
          return {
            ok: true,
            meta: { source: "mock-fallback", service: "TicketService" },
            data: {
              schema_version: "expect-tickets/1.0",
              race_id: tid,
              status: br.status || "ok",
              strategy_id: br.strategy_id || null,
              generated_at: br.generated_at || null,
              items: br.items || [],
              by_bet_type: br.by_bet_type || {},
            },
          };
        });
    }

    return Promise.reject(new Error("no mock for " + path));
  }

  function request(path, options) {
    options = options || {};
    var method = (options.method || "GET").toUpperCase();
    var url = buildUrl(path, options.query);

    if (useMock() && method === "GET") {
      return mockGet(url.split("?")[0], options.query);
    }
    if (useMock() && path === "/api/auth/login" && method === "POST") {
      var id = (options.body && options.body.id) || "mock-user";
      return Promise.resolve({
        ok: true,
        data: {
          access_token: "stub.mock." + encodeURIComponent(id),
          token_type: "bearer",
          expires_in: 86400,
          user: { id: id, display_name: id },
        },
      });
    }
    if (useMock() && path === "/api/kaoba/chat" && method === "POST") {
      return Promise.resolve({
        ok: true,
        data: {
          schema_version: "expect-kaoba/1.0",
          reply: "（モック）了解！データは参考程度に楽しんでね。",
          emotion: "fun",
          suggestions: ["買い目を整理", "リスクを教えて"],
          live2d: { motion: "talk_idle", expression: "neutral" },
        },
      });
    }

    var headers = { Accept: "application/json" };
    var token = getToken();
    if (token) headers.Authorization = "Bearer " + token;
    if (options.body != null) headers["Content-Type"] = "application/json; charset=utf-8";

    return fetch(url, {
      method: method,
      headers: headers,
      body: options.body != null ? JSON.stringify(options.body) : undefined,
    })
      .then(function (res) {
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
            err.code = (payload && payload.error && payload.error.code) || "HTTP_" + res.status;
            err.status = res.status;
            err.payload = payload;
            throw err;
          }
          return payload;
        });
      })
      .catch(function (err) {
        if (method === "GET" && useMock()) {
          return mockGet(url.split("?")[0], options.query).catch(function () {
            throw err;
          });
        }
        throw err;
      });
  }

  var Prediction = {
    list: function (opts) {
      opts = opts || {};
      return request("/api/predictions", {
        query: { date: opts.date || "", venue: opts.venue || "" },
      }).then(unwrap);
    },
    get: function (raceId) {
      return request("/api/predictions/" + encodeURIComponent(raceId)).then(unwrap);
    },
  };

  var Analysis = {
    get: function (raceId) {
      return request("/api/analysis/" + encodeURIComponent(raceId)).then(unwrap);
    },
  };

  var Confidence = {
    get: function (raceId) {
      return request("/api/confidence/" + encodeURIComponent(raceId)).then(unwrap);
    },
  };

  var Ticket = {
    get: function (raceId) {
      return request("/api/tickets/" + encodeURIComponent(raceId)).then(unwrap);
    },
  };

  var Kaoba = {
    chat: function (payload) {
      return request("/api/kaoba/chat", { method: "POST", body: payload || {} }).then(unwrap);
    },
  };

  var Auth = {
    login: function (creds) {
      return request("/api/auth/login", { method: "POST", body: creds || {} }).then(function (res) {
        var data = unwrap(res);
        if (data && data.access_token) setToken(data.access_token);
        return data;
      });
    },
  };

  global.ExpectApi = {
    request: request,
    unwrap: unwrap,
    getToken: getToken,
    setToken: setToken,
    logout: function () {
      setToken("");
    },
    Prediction: Prediction,
    Analysis: Analysis,
    Confidence: Confidence,
    Ticket: Ticket,
    Kaoba: Kaoba,
    Auth: Auth,
    // 互換エイリアス（段階移行）
    login: function (creds) {
      return Auth.login(creds).then(function (data) {
        return { ok: true, data: data };
      });
    },
    kaoba: function (payload) {
      return Kaoba.chat(payload).then(function (data) {
        return { ok: true, data: data };
      });
    },
  };
})(window);
