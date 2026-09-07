/**
 * GET /api/races/:id/history
 *
 * Version7.2: 近走専用（Board / Odds から分離）
 * PI GET /v1/races/{id}/history
 */
import { piFetch } from "../../../_lib/piProxy.js";
import { isPiRaceId } from "../../../_lib/raceIdResolve.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import { groupHistoryByHorse } from "../../../_lib/raceBoard.js";

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);
  if (!isPiRaceId(id)) {
    return jsonError("INVALID_RACE_ID", "race_id must be YYYY-MM-DD-LL-RR", 400);
  }

  const proxied = await piFetch(
    context,
    "/v1/races/" + encodeURIComponent(id) + "/history",
    { timeoutMs: 60000 }
  );
  if (proxied instanceof Response) return proxied;
  if (!proxied || !proxied.ok || !proxied.payload) {
    return jsonError(
      "PI_HISTORY_FAILED",
      "Failed to load race history from PI API",
      502
    );
  }

  const p = proxied.payload;
  let history = [];
  if (Array.isArray(p.history) && p.history.length) {
    history = p.history.map(function (h) {
      return {
        horse_id: h.horse_id || null,
        horse_number: h.horse_number != null ? Number(h.horse_number) : null,
        horse_name: h.horse_name || "—",
        recent: Array.isArray(h.recent) ? h.recent.slice(0, 3) : [],
      };
    });
  } else if (Array.isArray(p.history_rows)) {
    history = groupHistoryByHorse(p.history_rows, 3);
  } else if (Array.isArray(p.items)) {
    history = p.items;
  }

  return jsonOk(
    {
      schema_version: p.schema_version || "expect-race-history/1.0",
      race_id: String(p.race_id || id),
      race_label: p.race_label || "",
      race_name: p.race_name || "",
      date: p.date || "",
      venue: p.venue || "",
      race_no: p.race_no != null ? Number(p.race_no) : null,
      history: history,
      count: history.length,
    },
    {
      source: proxied.source || "pi-keibanet-api",
      service: "RaceHistory",
    },
    {
      cacheControl: "public, max-age=120",
    }
  );
}
