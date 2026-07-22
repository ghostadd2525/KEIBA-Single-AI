/**
 * BFF Feature Flags（Version 2）
 *
 * 設計: docs/releases/v2-ui-enhancement-mock.md §2.3
 * 既定はすべて false（Flag OFF = v1.1 完全互換）。
 */
import { getBetaConfig } from "./betaConfig.js";
import { getEnv } from "./env.js";

function envBool(raw) {
  if (raw == null || String(raw).trim() === "") return null;
  return ["1", "true", "yes", "on"].includes(String(raw).trim().toLowerCase());
}

/**
 * @param {object} context Cloudflare Pages context
 * @param {string} flagName 例: "v2_race_cards"
 * @param {{ envKey?: string, betaKey?: string }} [opts]
 */
export async function isBffFeatureEnabled(context, flagName, opts = {}) {
  const envKey = opts.envKey || String(flagName).toUpperCase();
  const betaKey = opts.betaKey || flagName;
  const env = getEnv(context);
  const fromEnv = envBool(context?.env?.[envKey] ?? env?.[envKey]);
  if (fromEnv != null) return fromEnv;

  try {
    const beta = await getBetaConfig(context);
    const features = (beta && beta.ui_features) || {};
    if (Object.prototype.hasOwnProperty.call(features, betaKey)) {
      return Boolean(features[betaKey]);
    }
  } catch {
    /* ignore — default false */
  }
  return false;
}

/** Flag: v2_race_cards — GET /api/race-cards 有効化（既定 false） */
export async function isV2RaceCardsEnabled(context) {
  return isBffFeatureEnabled(context, "v2_race_cards", {
    envKey: "V2_RACE_CARDS",
    betaKey: "v2_race_cards",
  });
}
