/**
 * Unit-ish checks for race data status mapping (no Ops vocabulary leakage).
 */
import { buildRaceDataStatus } from "../../functions/_lib/raceDataStatus.js";

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assert failed");
}

const raceId = "2026-07-26-01-01";

const readyPayload = {
  live_runners: {
    ok: true,
    races: [
      {
        race_id: raceId,
        ok: true,
        horse_number_ready: true,
        frame_number_ready: true,
      },
    ],
  },
};

const pendingPayload = {
  live_runners: {
    ok: false,
    races: [
      {
        race_id: raceId,
        ok: false,
        horse_number_ready: false,
        frame_number_ready: false,
        reasons: ["Race Refresh Incomplete", "Horse Number Not Ready"],
      },
    ],
  },
};

const ready = buildRaceDataStatus(raceId, readyPayload);
assert(ready.state === "ready", "ready state");
assert(ready.visible === false, "ready hidden");
assert(!/Integrity|Refresh|Horse Number/i.test(JSON.stringify(ready)), "no ops terms in ready");

const pending = buildRaceDataStatus(raceId, pendingPayload);
assert(pending.state === "pending", "pending state");
assert(pending.visible === true, "pending visible");
assert(pending.surfaces.board.visible === true, "board banner");
assert(!/Integrity|Refresh|Horse Number Not Ready/i.test(JSON.stringify(pending)), "no ops terms in pending");
assert(/確定/.test(pending.message), "user-facing pending message");

const loading = buildRaceDataStatus(raceId, null);
assert(loading.state === "loading", "loading state");

const errored = buildRaceDataStatus(raceId, null, { fetchFailed: true });
assert(errored.state === "error", "error state");
assert(/失敗/.test(errored.message), "error message");

console.log("raceDataStatus mapping OK");
