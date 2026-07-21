/**
 * E2E smoke: Race Catalog (PI → BFF mapper → expected labels)
 * Usage: node scripts/e2e-race-catalog.mjs [PI_BASE_URL]
 */
import { mapPiCatalogToWebItems } from "../functions/_lib/raceCatalog.js";

const piBase = (process.argv[2] || process.env.PI_BASE_URL || "http://127.0.0.1:8081").replace(
  /\/$/,
  ""
);
const date = process.env.RACE_DATE || "2026-07-25";

const expected = [
  ["新潟6R", "豊栄特別"],
  ["新潟7R", "新潟日報賞"],
  ["新潟8R", "清津峡特別"],
  ["中京6R", "四日市特別"],
  ["中京7R", "関ケ原S"],
  ["中京8R", "香嵐渓特別"],
  ["札幌10R", "ライラック賞"],
  ["札幌11R", "TVh賞"],
  ["札幌12R", "桑園特別"],
];

async function main() {
  const url = `${piBase}/v1/races?date=${encodeURIComponent(date)}`;
  const res = await fetch(url, { headers: { accept: "application/json" } });
  const catalog = await res.json();
  if (!res.ok) {
    throw new Error(`PI /v1/races failed: ${res.status} ${JSON.stringify(catalog)}`);
  }
  console.log("[PI] count=", catalog.count);

  const items = mapPiCatalogToWebItems(catalog);
  if (items.length !== 9) {
    throw new Error(`expected 9 races, got ${items.length}`);
  }

  for (let i = 0; i < expected.length; i++) {
    const [label, name] = expected[i];
    const item = items[i];
    if (item.race_label !== label || item.race_name !== name) {
      throw new Error(
        `race[${i}] mismatch: got ${item.race_label} / ${item.race_name}, want ${label} / ${name}`
      );
    }
    if (item.race_info.venue !== item.course) {
      throw new Error(`race_info.venue compat failed for ${item.race_id}`);
    }
    if (item.race_info.class_label !== name) {
      throw new Error(`race_info.class_label compat failed for ${item.race_id}`);
    }
  }
  console.log("[MAP] 9/9 race labels OK");

  const sampleId = "2026-07-25-01-06";
  const piPredRes = await fetch(`${piBase}/v1/predictions/${encodeURIComponent(sampleId)}`, {
    headers: { accept: "application/json" },
  });
  const piPredBody = await piPredRes.json();
  if (!piPredRes.ok || !piPredBody.prediction_available) {
    throw new Error(`PI prediction unavailable: ${piPredRes.status}`);
  }
  console.log("[PI-PRED] GET /v1/predictions/" + sampleId + " OK");

  const aiBase = (process.env.AI_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  try {
    const predRes = await fetch(`${aiBase}/v1/predictions/${encodeURIComponent(sampleId)}`, {
      headers: { accept: "application/json" },
    });
    const predBody = await predRes.json();
    if (predRes.ok && predBody.ok) {
      const bundle = predBody.data || predBody;
      console.log("[WIN5-PRED] race_id", bundle.race_id);
    } else {
      console.log("[WIN5-PRED] skipped (unavailable locally)");
    }
  } catch {
    console.log("[WIN5-PRED] skipped (unreachable)");
  }

  console.log("E2E PASS");
}

main().catch((err) => {
  console.error("E2E FAIL:", err.message || err);
  process.exit(1);
});
