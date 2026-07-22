/**
 * GET /api/race-cards?date=YYYY-MM-DD
 *
 * Version 2 UI Enhancement Phase 1 — BFF のみ。
 * PI /v1/races + /v1/predictions を内部取得し RaceCardSummary[] を合成。
 * PredictionBundle は返さない。
 *
 * Feature Flag: v2_race_cards（既定 false）
 * 設計: docs/releases/v2-ui-enhancement-mock.md
 */
import { isV2RaceCardsEnabled } from "../../_lib/featureFlags.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { piFetch, piFetchStatus, usePiProxy } from "../../_lib/piProxy.js";
import { getEnv } from "../../_lib/env.js";
import {
  RACE_CARDS_FETCH_CONCURRENCY,
  RACE_CARDS_LIST_SCHEMA,
  buildRaceCardSummary,
  classifyPiPredictionPayload,
  mapWithConcurrency,
  predictionStatusFromHttp,
} from "../../_lib/raceCardSummary.js";

async function buildCardForRace(context, race) {
  const raceId = String(race.race_id || "");
  if (!raceId) {
    return buildRaceCardSummary({
      raceId: "",
      catalogRace: race,
      predictionStatus: "failed",
    });
  }

  const fetched = await piFetchStatus(
    context,
    `/v1/predictions/${encodeURIComponent(raceId)}`
  );

  if (!fetched.ok) {
    return buildRaceCardSummary({
      raceId,
      catalogRace: race,
      predictionStatus: predictionStatusFromHttp(fetched.status),
    });
  }

  const classified = classifyPiPredictionPayload(fetched.payload, race);
  return buildRaceCardSummary({
    raceId,
    catalogRace: race,
    predictionStatus: classified.status,
    bundle: classified.bundle,
    engineSource: classified.status === "ready" ? "pi" : undefined,
  });
}

export async function onRequestGet(context) {
  const enabled = await isV2RaceCardsEnabled(context);
  if (!enabled) {
    return jsonError(
      "FEATURE_DISABLED",
      "v2_race_cards is disabled (default OFF — v1.1 compatible)",
      404,
      { flag: "v2_race_cards", default: false }
    );
  }

  const env = getEnv(context);
  if (!usePiProxy(env)) {
    return jsonError("PI_BASE_URL_REQUIRED", "PI KeibaNet API is not configured", 503);
  }

  const url = new URL(context.request.url);
  const date = (url.searchParams.get("date") || "").trim();
  if (!date) {
    return jsonError("DATE_REQUIRED", "date query parameter is required (YYYY-MM-DD)", 400);
  }

  const qs = new URLSearchParams({ date });
  const catalogProxied = await piFetch(context, "/v1/races?" + qs.toString());
  if (catalogProxied instanceof Response) return catalogProxied;
  if (!catalogProxied || !catalogProxied.ok) {
    return jsonError("PI_RACES_FAILED", "Failed to load race catalog from PI API", 502);
  }

  const races = Array.isArray(catalogProxied.payload?.races)
    ? catalogProxied.payload.races
    : [];

  const race_cards = await mapWithConcurrency(
    races,
    RACE_CARDS_FETCH_CONCURRENCY,
    (race) => buildCardForRace(context, race)
  );

  return jsonOk(
    {
      schema_version: RACE_CARDS_LIST_SCHEMA,
      date,
      count: race_cards.length,
      race_cards,
    },
    {
      source: catalogProxied.source || "pi-keibanet-api",
      service: "RaceCardSummary",
      feature: "v2_race_cards",
      cache: "public, max-age=60",
    },
    { cacheControl: "public, max-age=60" }
  );
}
