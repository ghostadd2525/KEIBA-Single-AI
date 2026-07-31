/**
 * UI7 mapping unit check (no browser).
 * Run: node docs/research/artifacts/ui7/verify-mapping.mjs
 */
import assert from "node:assert/strict";
import {
  confidenceBandFromScore,
  CONFIDENCE_BAND_HIGH,
  CONFIDENCE_BAND_RATHER_HIGH,
  CONFIDENCE_BAND_MEDIUM,
} from "../../../../functions/_lib/confidenceBands.js";

const BAND_LABEL = {
  high: "高い",
  rather_high: "やや高い",
  medium: "ふつう",
  low: "低い",
};

function starsFromBand(band) {
  if (band === "high") return "★★★★★";
  if (band === "rather_high") return "★★★★☆";
  if (band === "medium") return "★★★☆☆";
  if (band === "low") return "★★☆☆☆";
  return "☆☆☆☆☆";
}

const cases = [
  [0.8, "high", "★★★★★", "高い"],
  [0.75, "high", "★★★★★", "高い"],
  [0.74, "rather_high", "★★★★☆", "やや高い"],
  [0.6, "rather_high", "★★★★☆", "やや高い"],
  [0.59, "medium", "★★★☆☆", "ふつう"],
  [0.35, "medium", "★★★☆☆", "ふつう"],
  [0.34, "low", "★★☆☆☆", "低い"],
  [0.0, "low", "★★☆☆☆", "低い"],
];

assert.equal(CONFIDENCE_BAND_HIGH, 0.75);
assert.equal(CONFIDENCE_BAND_RATHER_HIGH, 0.6);
assert.equal(CONFIDENCE_BAND_MEDIUM, 0.35);

for (const [score, band, stars, label] of cases) {
  const b = confidenceBandFromScore(score);
  assert.equal(b, band, `score=${score}`);
  assert.equal(starsFromBand(b), stars);
  assert.equal(BAND_LABEL[b], label);
}

console.log("UI7 mapping verify PASS", cases.length, "cases");
