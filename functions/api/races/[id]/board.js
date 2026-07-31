/**
 * GET /api/races/:id/board
 *
 * Version7.2: history は含めない（近走は /history）。
 * PI GET /v1/races/{id}/board をプロキシ。
 */
import { piFetch } from "../../../_lib/piProxy.js";
import { isPiRaceId } from "../../../_lib/raceIdResolve.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import { normalizeBoardEntries } from "../../../_lib/raceBoard.js";

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);
  if (!isPiRaceId(id)) {
    return jsonError("INVALID_RACE_ID", "race_id must be YYYY-MM-DD-LL-RR", 400);
  }

  // Version7.2: include=history は無視（近走は /api/races/:id/history）
  const proxied = await piFetch(
    context,
    "/v1/races/" + encodeURIComponent(id) + "/board",
    { timeoutMs: 45000 }
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
    odds_status: p.odds_status || null,
    odds_cache_ttl_sec:
      p.odds_cache_ttl_sec != null ? Number(p.odds_cache_ttl_sec) : 300,
  };

  return jsonOk(
    data,
    {
      source: proxied.source || "pi-keibanet-api",
      service: "RaceBoard",
      odds_status: p.odds_status || null,
      odds_cache_ttl_sec: p.odds_cache_ttl_sec || 300,
    },
    {
      cacheControl: "public, max-age=60",
    }
  );
}
