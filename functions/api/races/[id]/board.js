/**
 * GET /api/races/:id/board
 *
 * PI GET /v1/races/{id}/board をプロキシ（Tunnel /v1/races* → PI）
 * ?include=history で近走（各馬最大3件）も返す
 */
import { piFetch } from "../../../_lib/piProxy.js";
import { isPiRaceId } from "../../../_lib/raceIdResolve.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import {
  groupHistoryByHorse,
  normalizeBoardEntries,
} from "../../../_lib/raceBoard.js";

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);
  if (!isPiRaceId(id)) {
    return jsonError("INVALID_RACE_ID", "race_id must be YYYY-MM-DD-LL-RR", 400);
  }

  const url = new URL(context.request.url);
  const includeHistory =
    url.searchParams.get("include") === "history" ||
    url.searchParams.get("history") === "1";

  const qs = includeHistory ? "?include=history" : "";
  const proxied = await piFetch(
    context,
    "/v1/races/" + encodeURIComponent(id) + "/board" + qs
  );
  if (proxied instanceof Response) return proxied;
  if (!proxied || !proxied.ok || !proxied.payload) {
    return jsonError("PI_BOARD_FAILED", "Failed to load race board from PI API", 502);
  }

  const p = proxied.payload;
  const entries = normalizeBoardEntries(p.entries || []);
  const data = {
    schema_version: "expect-race-board/1.0",
    race_id: String(p.race_id || id),
    race_label: p.race_label || "",
    race_name: p.race_name || "",
    date: p.date || "",
    venue: p.venue || p.course || "",
    race_no: p.race_no != null ? Number(p.race_no) : null,
    post_time: p.post_time || null,
    numeric_race_id: p.numeric_race_id != null ? String(p.numeric_race_id) : null,
    entries,
    count: entries.length,
  };

  if (includeHistory) {
    if (Array.isArray(p.history) && p.history.length) {
      // PI already grouped
      data.history = p.history.map((h) => ({
        horse_id: h.horse_id || null,
        horse_number: h.horse_number != null ? Number(h.horse_number) : null,
        horse_name: h.horse_name || "—",
        recent: Array.isArray(h.recent) ? h.recent.slice(0, 3) : [],
      }));
    } else if (Array.isArray(p.history_rows)) {
      data.history = groupHistoryByHorse(p.history_rows, 3);
    } else {
      data.history = [];
    }
  }

  data.odds_status = p.odds_status || null;
  data.odds_cache_ttl_sec = p.odds_cache_ttl_sec != null ? Number(p.odds_cache_ttl_sec) : 300;

  return jsonOk(
    data,
    {
      source: proxied.source || "pi-keibanet-api",
      service: "RaceBoard",
      odds_status: p.odds_status || null,
      odds_cache_ttl_sec: p.odds_cache_ttl_sec || 300,
    },
    {
      cacheControl: includeHistory
        ? "public, max-age=60"
        : "public, max-age=60, stale-while-revalidate=240",
    }
  );
}
