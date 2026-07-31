/**
 * GET /api/races/:id/data-status
 *
 * User-facing race data readiness (maps Ops integrity internally).
 * Response never includes Ops / Integrity vocabulary.
 */
import { piFetch, piFetchStatus } from "../../../_lib/piProxy.js";
import { isPiRaceId } from "../../../_lib/raceIdResolve.js";
import { buildRaceDataStatus } from "../../../_lib/raceDataStatus.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import { normalizeBoardEntries } from "../../../_lib/raceBoard.js";

function dateFromRaceId(raceId) {
  const m = /^(\d{4}-\d{2}-\d{2})-/.exec(String(raceId || ""));
  return m ? m[1] : "";
}

function statusFromBoardEntries(raceId, entries) {
  const list = Array.isArray(entries) ? entries : [];
  if (!list.length) {
    return buildRaceDataStatus(raceId, null);
  }
  const allNumbered = list.every(function (e) {
    const n = Number(e && e.horse_number);
    return Number.isFinite(n) && n >= 1 && e && e.horse_id;
  });
  if (allNumbered) {
    return buildRaceDataStatus(raceId, {
      live_runners: {
        ok: true,
        ready_race_ids: [raceId],
        blocked_race_ids: [],
        races: [{ race_id: raceId, ok: true, horse_number_ready: true }],
      },
    });
  }
  return buildRaceDataStatus(raceId, {
    live_runners: {
      ok: false,
      ready_race_ids: [],
      blocked_race_ids: [raceId],
      races: [{ race_id: raceId, ok: false, horse_number_ready: false }],
    },
  });
}

function hasUsableIntegrity(payload) {
  if (!payload || typeof payload !== "object") return false;
  const live = payload.live_runners || payload.latest_report;
  if (!live || typeof live !== "object") return false;
  return (
    Array.isArray(live.races) ||
    Array.isArray(live.ready_race_ids) ||
    Array.isArray(live.blocked_race_ids)
  );
}

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);
  if (!isPiRaceId(id)) {
    return jsonError("INVALID_RACE_ID", "race_id must be YYYY-MM-DD-LL-RR", 400);
  }

  const date = dateFromRaceId(id);
  const qs = date ? "?date=" + encodeURIComponent(date) : "";
  const proxied = await piFetchStatus(
    context,
    "/v1/ops/horse-number-integrity" + qs
  );

  let payload =
    proxied && proxied.payload && proxied.payload.data != null
      ? proxied.payload.data
      : proxied && proxied.payload;
  if (payload && payload.data && hasUsableIntegrity(payload.data)) {
    payload = payload.data;
  }

  let data;
  if (hasUsableIntegrity(payload)) {
    data = buildRaceDataStatus(id, payload);
  } else {
    // Integrity unreachable / empty → fall back to board entries (still no Ops labels).
    const boardProxied = await piFetch(
      context,
      "/v1/races/" + encodeURIComponent(id) + "/board"
    );
    if (boardProxied instanceof Response) {
      data = buildRaceDataStatus(id, null, { fetchFailed: true });
    } else if (!boardProxied || !boardProxied.ok || !boardProxied.payload) {
      data = buildRaceDataStatus(id, null, { fetchFailed: true });
    } else {
      const entries = normalizeBoardEntries(boardProxied.payload.entries || []);
      data = statusFromBoardEntries(id, entries);
    }
  }

  return jsonOk(
    data,
    {
      service: "RaceDataStatus",
      cache: "no-store",
      source: "pi-mapped",
    },
    { status: 200, cacheControl: "no-store" }
  );
}
