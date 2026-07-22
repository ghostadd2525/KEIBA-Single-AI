/**
 * ExpectUiFeatures — Version 1.1 Feature Flags（beta.json ui_features）
 * Flag OFF = v1.0 同等パス。Prediction Core / API 契約に非依存。
 */
(function (global) {
  "use strict";

  var DEFAULTS = {
    v11_loading_errors: true,
    v11_mobile: false,
    v11_home: false,
    v11_races: false,
    v11_race_detail: false,
    v11_explain: false,
    v11_confidence: false,
    v11_collector_status: false,
    v11_system_health: false,
    v11_ops_dashboard: false,
    v11_auto_maintenance: false,
    /** Version 2 Explainability */
    v2_explain: false,
    v2_race_cards: false,
    v2_race_list_ui: false,
    /** Version 2 Operations — PI Health Dashboard 基盤 */
    v2_ops_dashboard: false,
  };

  var cache = null;
  var readyPromise = null;

  function mergeFeatures(raw) {
    var out = {};
    var key;
    for (key in DEFAULTS) {
      if (Object.prototype.hasOwnProperty.call(DEFAULTS, key)) {
        out[key] = DEFAULTS[key];
      }
    }
    if (raw && typeof raw === "object") {
      for (key in DEFAULTS) {
        if (Object.prototype.hasOwnProperty.call(raw, key)) {
          out[key] = !!raw[key];
        }
      }
    }
    return out;
  }

  function load() {
    if (readyPromise) return readyPromise;
    readyPromise = fetch("/config/beta.json", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("beta " + res.status);
        return res.json();
      })
      .then(function (doc) {
        cache = mergeFeatures(doc && doc.ui_features);
        return cache;
      })
      .catch(function () {
        cache = mergeFeatures(null);
        return cache;
      });
    return readyPromise;
  }

  function getSync() {
    return cache || mergeFeatures(null);
  }

  function enabled(name) {
    var f = getSync();
    return !!(f && f[name]);
  }

  function applyBodyClasses() {
    var f = getSync();
    var body = document.body;
    if (!body) return;
    body.classList.add("v11-fe");
    Object.keys(f).forEach(function (key) {
      if (f[key]) body.classList.add(key.replace(/_/g, "-"));
      else body.classList.remove(key.replace(/_/g, "-"));
    });
  }

  global.ExpectUiFeatures = {
    defaults: DEFAULTS,
    load: load,
    getSync: getSync,
    enabled: enabled,
    applyBodyClasses: applyBodyClasses,
    ready: function (cb) {
      return load().then(function (f) {
        applyBodyClasses();
        if (typeof cb === "function") cb(f);
        return f;
      });
    },
  };
})(window);
