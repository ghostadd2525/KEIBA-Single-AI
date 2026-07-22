/**
 * ExpectRaceListUrl — races.html の開催日 URL 同期（Phase 2）
 *
 * 唯一の状態源: ?date=YYYY-MM-DD
 * - 初期表示は URL の date を優先
 * - 日付タブ操作で history を更新
 * - popstate で状態復元
 * - 不正な date はカレンダーフォールバック（replaceState）
 *
 * 見た目・fetch 切替（race-cards）・検索/お気に入りは対象外。
 */
(function (global) {
  "use strict";

  var ISO_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

  function isValidIsoDate(value) {
    var s = String(value == null ? "" : value).trim();
    var m = ISO_RE.exec(s);
    if (!m) return false;
    var y = Number(m[1]);
    var mo = Number(m[2]);
    var d = Number(m[3]);
    if (mo < 1 || mo > 12 || d < 1 || d > 31) return false;
    var dt = new Date(Date.UTC(y, mo - 1, d));
    return (
      dt.getUTCFullYear() === y &&
      dt.getUTCMonth() === mo - 1 &&
      dt.getUTCDate() === d
    );
  }

  function dateLabelFromIso(date) {
    var p = String(date || "").split("-");
    if (p.length !== 3) return "";
    return Number(p[1]) + "/" + Number(p[2]);
  }

  function calendarFallbackDate(instant) {
    if (global.ExpectWeekendCalendar && ExpectWeekendCalendar.decide) {
      var cal = ExpectWeekendCalendar.decide(instant || new Date());
      if (cal && cal.is_race_day && isValidIsoDate(cal.date_jst)) return cal.date_jst;
      if (cal && isValidIsoDate(cal.next_open_date_jst)) return cal.next_open_date_jst;
    }
    return "";
  }

  function readRawDateParam(search) {
    try {
      var params = new URLSearchParams(
        search != null ? search : (global.location && global.location.search) || ""
      );
      var raw = params.get("date");
      if (raw == null || raw === "") return null;
      return String(raw).trim();
    } catch (e) {
      return null;
    }
  }

  /**
   * URL → 正規化済み date 状態
   * @returns {{ date: string|null, source: "url"|"fallback"|"none", replaced: boolean, raw: string|null }}
   *   date=null は「すべて」（クエリなし）
   */
  function resolveFromLocation(opts) {
    opts = opts || {};
    var raw = readRawDateParam(opts.search);
    if (raw == null) {
      return { date: null, source: "none", replaced: false, raw: null };
    }
    if (isValidIsoDate(raw)) {
      return { date: raw, source: "url", replaced: false, raw: raw };
    }
    var fb = calendarFallbackDate(opts.now);
    if (fb) {
      return { date: fb, source: "fallback", replaced: true, raw: raw };
    }
    return { date: null, source: "fallback", replaced: true, raw: raw };
  }

  function buildSearchWithDate(date, currentSearch) {
    var params = new URLSearchParams(
      currentSearch != null
        ? currentSearch
        : (global.location && global.location.search) || ""
    );
    if (date && isValidIsoDate(date)) {
      params.set("date", date);
    } else {
      params.delete("date");
    }
    var q = params.toString();
    return q ? "?" + q : "";
  }

  function currentPathname() {
    return (global.location && global.location.pathname) || "/races.html";
  }

  /**
   * URL を更新する。date=null/"all"/"" → date クエリ削除（すべて）
   * @param {string|null} date
   * @param {{ mode?: "push"|"replace", search?: string }} opts
   */
  function writeDate(date, opts) {
    opts = opts || {};
    var mode = opts.mode === "replace" ? "replace" : "push";
    var iso = date && date !== "all" && isValidIsoDate(date) ? date : null;
    var search = buildSearchWithDate(iso, opts.search);
    var url = currentPathname() + search + ((global.location && global.location.hash) || "");
    var state = { expectRaceListDate: iso };
    try {
      if (mode === "replace" && global.history && history.replaceState) {
        history.replaceState(state, "", url);
      } else if (global.history && history.pushState) {
        history.pushState(state, "", url);
      }
    } catch (e) {
      /* ignore */
    }
    return iso;
  }

  /**
   * 不正 date を検知したら replaceState で正規化する。
   * @returns {string|null} 適用すべき filter date（null=すべて）
   */
  function normalizeLocation(opts) {
    var resolved = resolveFromLocation(opts);
    if (resolved.replaced) {
      writeDate(resolved.date, { mode: "replace", search: opts && opts.search });
    }
    return resolved.date;
  }

  function bindPopState(handler) {
    if (typeof handler !== "function" || !global.addEventListener) return function () {};
    function onPop() {
      handler(resolveFromLocation());
    }
    global.addEventListener("popstate", onPop);
    return function unbind() {
      global.removeEventListener("popstate", onPop);
    };
  }

  global.ExpectRaceListUrl = {
    isValidIsoDate: isValidIsoDate,
    dateLabelFromIso: dateLabelFromIso,
    calendarFallbackDate: calendarFallbackDate,
    readRawDateParam: readRawDateParam,
    resolveFromLocation: resolveFromLocation,
    buildSearchWithDate: buildSearchWithDate,
    writeDate: writeDate,
    normalizeLocation: normalizeLocation,
    bindPopState: bindPopState,
  };
})(typeof window !== "undefined" ? window : globalThis);
