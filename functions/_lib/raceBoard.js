/**
 * Race board — 出馬表 / オッズ / 近走データ（PI Collector 経由）
 */
import { piFetch } from "./piProxy.js";
import { extractDateFromPiRaceId, isPiRaceId } from "./raceIdResolve.js";

/**
 * @param {unknown} v
 * @returns {number|null}
 */
function asNum(v) {
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * @param {unknown} v
 * @returns {string}
 */
function asStr(v) {
  return v == null ? "" : String(v).trim();
}

/**
 * race_id → date / venue / race_no（PI get_race）
 * @param {import("@cloudflare/workers-types").EventContext} context
 * @param {string} raceId
 */
export async function resolveRaceRefFromPi(context, raceId) {
  const id = String(raceId || "").trim();
  if (!id || !isPiRaceId(id)) {
    return { ok: false, status: 400, error: "INVALID_RACE_ID", message: "race_id must be YYYY-MM-DD-LL-RR" };
  }
  const proxied = await piFetch(
    context,
    "/v1/races/" + encodeURIComponent(id) + "?enrich=0"
  );
  if (proxied instanceof Response) {
    return { ok: false, errorResponse: proxied };
  }
  if (!proxied || !proxied.ok || !proxied.payload) {
    return { ok: false, status: 502, error: "PI_RACE_RESOLVE_FAILED", message: "Failed to resolve race_id" };
  }
  const p = proxied.payload;
  const date = asStr(p.date || p.race_date) || extractDateFromPiRaceId(id);
  const venue = asStr(p.course || p.venue);
  const raceNo = asNum(p.race_number ?? p.race_no);
  if (!date || !venue || raceNo == null) {
    return { ok: false, status: 404, error: "RACE_REF_INCOMPLETE", message: "Could not resolve venue/race_no" };
  }
  return {
    ok: true,
    ref: {
      race_id: asStr(p.race_id) || id,
      date,
      venue,
      race_no: raceNo,
      race_label: asStr(p.race_label) || venue + raceNo + "R",
      race_name: asStr(p.race_name),
      post_time: asStr(p.post_time) || null,
      numeric_race_id: asStr(p.numeric_race_id) || null,
    },
    source: proxied.source || "pi-keibanet-api",
  };
}

/**
 * @param {import("@cloudflare/workers-types").EventContext} context
 * @param {{ date: string, venue: string, race_no: number }} ref
 */
export async function fetchEntriesFull(context, ref) {
  const qs = new URLSearchParams({
    date: ref.date,
    venue: ref.venue,
    race_no: String(ref.race_no),
  });
  const proxied = await piFetch(context, "/v1/pipeline/entries_full?" + qs.toString());
  if (proxied instanceof Response) return { ok: false, errorResponse: proxied };
  if (!proxied || !proxied.ok) {
    return { ok: false, status: 502, error: "PI_ENTRIES_FAILED", message: "Failed to load entries" };
  }
  const entries = Array.isArray(proxied.payload?.entries) ? proxied.payload.entries : [];
  return { ok: true, entries, payload: proxied.payload, source: proxied.source };
}

/**
 * entries_full 行 → 出馬表 / オッズ表示用
 * @param {Record<string, unknown>[]} entries
 */
export function normalizeBoardEntries(entries) {
  return (entries || [])
    .map((e) => {
      const horseNumber = asNum(e.horse_number);
      const frame = asNum(e.frame_number ?? e.frame);
      const odds = asNum(e.odds);
      const popularity = asNum(e.popularity);
      return {
        horse_number: horseNumber,
        frame_number: frame,
        horse_name: asStr(e.horse_name) || "—",
        jockey: asStr(e.jockey) || null,
        horse_id: asStr(e.horse_id) || null,
        odds: odds,
        popularity: popularity,
        weight: asNum(e.weight_carried ?? e.weight),
        sex: asStr(e.sex) || null,
        age: asNum(e.age),
      };
    })
    .filter((e) => e.horse_number != null)
    .sort((a, b) => a.horse_number - b.horse_number);
}

/**
 * @param {string} dateStr
 */
function historyDateKey(dateStr) {
  const s = asStr(dateStr);
  // YYYY-MM-DD or YYYY/MM/DD or YYYYMMDD
  const m = s.match(/(\d{4})[\/\-]?(\d{1,2})[\/\-]?(\d{1,2})/);
  if (!m) return 0;
  return Number(m[1]) * 10000 + Number(m[2]) * 100 + Number(m[3]);
}

/**
 * history_rows → 馬ごと直近 limit 件
 * @param {Record<string, unknown>[]} rows
 * @param {number} [limit=3]
 */
export function groupHistoryByHorse(rows, limit = 3) {
  const byHorse = new Map();
  for (const row of rows || []) {
    const horseId = asStr(row.horse_id);
    const horseNumber = asNum(row.horse_number ?? row.umaban);
    const key = horseId || (horseNumber != null ? "n:" + horseNumber : "");
    if (!key) continue;
    if (!byHorse.has(key)) {
      byHorse.set(key, {
        horse_id: horseId || null,
        horse_number: horseNumber,
        horse_name: asStr(row.horse_name) || "—",
        recent: [],
      });
    }
    const bucket = byHorse.get(key);
    if (!bucket.horse_name || bucket.horse_name === "—") {
      const n = asStr(row.horse_name);
      if (n) bucket.horse_name = n;
    }
    if (bucket.horse_number == null && horseNumber != null) {
      bucket.horse_number = horseNumber;
    }
    bucket.recent.push({
      date: asStr(row.history_date) || null,
      place: asStr(row.history_place) || null,
      race_name: asStr(row.history_race_name) || null,
      finish: asStr(row.history_finish) || null,
      odds: asNum(row.history_odds),
      distance: asNum(row.history_distance),
      surface: asStr(row.history_surface) || null,
      last3f: asStr(row.history_last3f) || null,
      _sort: historyDateKey(row.history_date),
    });
  }

  const out = [];
  for (const bucket of byHorse.values()) {
    bucket.recent.sort((a, b) => b._sort - a._sort);
    bucket.recent = bucket.recent.slice(0, limit).map((r) => {
      const { _sort, ...rest } = r;
      return rest;
    });
    out.push(bucket);
  }
  out.sort((a, b) => (a.horse_number || 99) - (b.horse_number || 99));
  return out;
}

/**
 * @param {import("@cloudflare/workers-types").EventContext} context
 * @param {Record<string, unknown>[]} entries
 * @param {object} [raceContext]
 */
export async function fetchHorseHistory(context, entries, raceContext = null) {
  const body = {
    entries: (entries || []).map((e) => ({
      horse_id: asStr(e.horse_id),
      horse_number: asNum(e.horse_number),
      horse_name: asStr(e.horse_name),
      frame_number: asNum(e.frame_number ?? e.frame),
      odds: asNum(e.odds),
    })),
    race_context: raceContext || undefined,
  };
  const proxied = await piFetch(context, "/v1/pipeline/horse_history", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (proxied instanceof Response) return { ok: false, errorResponse: proxied };
  if (!proxied || !proxied.ok) {
    return { ok: false, status: 502, error: "PI_HISTORY_FAILED", message: "Failed to load horse history" };
  }
  const rows = Array.isArray(proxied.payload?.history_rows)
    ? proxied.payload.history_rows
    : [];
  return { ok: true, rows, source: proxied.source };
}
