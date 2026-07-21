/**
 * E2E: PI Prediction via BFF contract (no mock_fallback)
 *
 * Usage:
 *   PI_BASE_URL=http://127.0.0.1:8081 node scripts/e2e-pi-prediction.mjs
 *   # production tunnel (after /v1/predictions route):
 *   PI_BASE_URL=https://ai.expect-keiba.com node scripts/e2e-pi-prediction.mjs
 */
import { mapPiPredictionToBundle } from "../functions/_lib/piPredictionMapper.js";

const piBase = (process.argv[2] || process.env.PI_BASE_URL || "http://127.0.0.1:8081").replace(
  /\/$/,
  ""
);
const raceId = process.env.RACE_ID || "2026-07-25-01-06";
const date = process.env.RACE_DATE || "2026-07-25";

async function main() {
  const predRes = await fetch(`${piBase}/v1/predictions/${encodeURIComponent(raceId)}`, {
    headers: { accept: "application/json" },
  });
  const predBody = await predRes.json();
  if (!predRes.ok || !predBody.prediction_available) {
    throw new Error(
      `PI prediction unavailable: HTTP ${predRes.status} ${JSON.stringify(predBody).slice(0, 200)}`
    );
  }

  const bundle = mapPiPredictionToBundle(predBody);
  if (!bundle || bundle.race_id !== raceId) {
    throw new Error(`mapper failed for ${raceId}`);
  }
  if (!bundle.evaluation.runners.length) {
    throw new Error("no runners in bundle");
  }
  console.log("[PI-PRED]", raceId, "runners=", bundle.evaluation.runners.length);
  console.log("[PI-PRED] honmei=", bundle.evaluation.runners[0].horse_name);

  const racesRes = await fetch(`${piBase}/v1/races?date=${encodeURIComponent(date)}`, {
    headers: { accept: "application/json" },
  });
  const catalog = await racesRes.json();
  if (!racesRes.ok || !Array.isArray(catalog.races) || catalog.races.length < 1) {
    throw new Error(`PI races failed: ${racesRes.status}`);
  }
  console.log("[PI-RACES] count=", catalog.count);

  console.log("E2E PASS (PI prediction, no mock)");
}

main().catch((err) => {
  console.error("E2E FAIL:", err.message || err);
  process.exit(1);
});
