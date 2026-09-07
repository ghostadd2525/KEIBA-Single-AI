/**
 * ExpectUserProgress — level / unlocks (client helpers)
 */
(function (global) {
  "use strict";

  var cache = null;

  function fromMe(me) {
    if (me && me.progress) {
      cache = me.progress;
      return cache;
    }
    return cache;
  }

  function load() {
    if (!(global.ExpectApi && ExpectApi.User && ExpectApi.User.progress)) {
      return Promise.resolve(null);
    }
    return ExpectApi.User.progress()
      .then(function (data) {
        cache = (data && data.progress) || data;
        return cache;
      })
      .catch(function () {
        return cache;
      });
  }

  function unlocked(key) {
    if (!cache || !cache.unlocks) return key === "race_predict" || key === "strategy" || key === "user_results";
    return !!cache.unlocks[key];
  }

  function level() {
    return (cache && cache.level) || 1;
  }

  function applyHomeWin5(root) {
    root = root || document;
    var slot = root.querySelector("#homeWin5Slot");
    if (!slot) return;
    if (!unlocked("win5_predict")) {
      slot.hidden = true;
      slot.innerHTML = "";
      return;
    }
    slot.hidden = false;
    slot.innerHTML =
      '<a class="ai-card ai-card--win5" href="win5.html">' +
      '<div class="ai-card-row"><div class="ai-copy">' +
      '<p class="ai-kicker">WIN5</p>' +
      '<h3 class="ai-title">WIN5予想</h3>' +
      '<p class="ai-desc">Lv100解放 · 5レース連勝予想</p>' +
      '</div><div class="ai-side ai-side--solo"><span class="ai-pill">WIN5を開く ›</span></div>' +
      "</div></a>";
  }

  function guardPage(requiredKey, fallbackHref) {
    return load().then(function (p) {
      if (unlocked(requiredKey)) return true;
      var need = (p && p.unlock_thresholds && p.unlock_thresholds[requiredKey]) || "?";
      alert("この機能は Lv" + need + " から利用できます。");
      location.href = fallbackHref || "index.html";
      return false;
    });
  }

  global.ExpectUserProgress = {
    load: load,
    fromMe: fromMe,
    unlocked: unlocked,
    level: level,
    applyHomeWin5: applyHomeWin5,
    guardPage: guardPage,
    get: function () {
      return cache;
    },
  };
})(typeof window !== "undefined" ? window : globalThis);
