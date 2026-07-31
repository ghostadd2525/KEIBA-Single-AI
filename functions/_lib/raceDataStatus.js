/**
 * Map internal horse-number integrity → user-facing race data status.
 * Never expose Ops / Integrity vocabulary to clients.
 */
export const DATA_STATUS_SCHEMA = "expect-race-data-status/1.0";

const MSG = {
  loading: "レースデータを確認しています…",
  pending: "出走情報がまだ確定していません。確定後に自動で表示されます。",
  pending_board: "出馬表の馬番が確定するまで、一部の情報は表示できません。",
  pending_odds: "オッズ表示に必要な出走情報がまだ確定していません。",
  pending_detail: "レース詳細の一部情報は、出走確定後に表示されます。",
  error: "データの取得に失敗しました。しばらくしてから再度お試しください。",
};

/**
 * @param {string} raceId
 * @param {object|null} integrityPayload PI /v1/ops/horse-number-integrity body
 * @param {{ fetchFailed?: boolean }} [opts]
 */
export function buildRaceDataStatus(raceId, integrityPayload, opts) {
  opts = opts || {};
  const id = String(raceId || "").trim();
  const emptySurfaces = function (state, message) {
    const visible = state !== "ready";
    const surf = { visible: visible, state: state, message: message };
    return { detail: { ...surf }, board: { ...surf }, odds: { ...surf } };
  };

  if (opts.fetchFailed) {
    return {
      schema_version: DATA_STATUS_SCHEMA,
      race_id: id,
      state: "error",
      message: MSG.error,
      visible: true,
      surfaces: emptySurfaces("error", MSG.error),
    };
  }

  if (!integrityPayload) {
    return {
      schema_version: DATA_STATUS_SCHEMA,
      race_id: id,
      state: "loading",
      message: MSG.loading,
      visible: true,
      surfaces: emptySurfaces("loading", MSG.loading),
    };
  }

  const live = integrityPayload.live_runners || integrityPayload.latest_report || null;
  const readyIds = (live && live.ready_race_ids) || [];
  const blockedIds = (live && live.blocked_race_ids) || [];
  const races = (live && live.races) || [];
  const hit = races.find(function (r) {
    return r && String(r.race_id || "") === id;
  });

  if (readyIds.map(String).includes(id) || (hit && hit.ok && hit.horse_number_ready)) {
    return {
      schema_version: DATA_STATUS_SCHEMA,
      race_id: id,
      state: "ready",
      message: "",
      visible: false,
      surfaces: {
        detail: { visible: false, state: "ready", message: "" },
        board: { visible: false, state: "ready", message: "" },
        odds: { visible: false, state: "ready", message: "" },
      },
    };
  }

  if (blockedIds.map(String).includes(id) || (hit && !hit.ok)) {
    return {
      schema_version: DATA_STATUS_SCHEMA,
      race_id: id,
      state: "pending",
      message: MSG.pending,
      visible: true,
      surfaces: {
        detail: { visible: true, state: "pending", message: MSG.pending_detail },
        board: { visible: true, state: "pending", message: MSG.pending_board },
        odds: { visible: true, state: "pending", message: MSG.pending_odds },
      },
    };
  }

  // Day report missing this race, or integrity payload incomplete → still preparing
  if (!live || (!races.length && !readyIds.length && !blockedIds.length)) {
    return {
      schema_version: DATA_STATUS_SCHEMA,
      race_id: id,
      state: "loading",
      message: MSG.loading,
      visible: true,
      surfaces: emptySurfaces("loading", MSG.loading),
    };
  }

  return {
    schema_version: DATA_STATUS_SCHEMA,
    race_id: id,
    state: "loading",
    message: MSG.loading,
    visible: true,
    surfaces: emptySurfaces("loading", MSG.loading),
  };
}
