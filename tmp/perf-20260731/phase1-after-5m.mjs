/**
 * Phase1 after-deploy comparison probe (5 min flow, same methodology as 30m baseline).
 */
import { chromium, devices } from "playwright";
import fs from "fs";

const OUT =
  "C:/win5-ai/KEIBA-Single-AI/tmp/perf-20260731/phase1-after-5m.json";
const chromePath =
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const RACE_ID = "2026-08-01-01-02";
const FLOW = [
  { name: "home", url: "https://expect-keiba.com/" },
  { name: "races", url: "https://expect-keiba.com/races" },
  {
    name: "detail",
    url: `https://expect-keiba.com/race.html?race_id=${RACE_ID}`,
  },
  {
    name: "consult",
    url: `https://expect-keiba.com/chat.html?mode=review&race_id=${RACE_ID}`,
  },
  { name: "analysis", url: "https://expect-keiba.com/analysis.html" },
  { name: "fortune", url: "https://expect-keiba.com/fortune.html" },
];

function mb(n) {
  return Number((n / 1024 / 1024).toFixed(3));
}

const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ["--disable-dev-shm-usage"],
});
const context = await browser.newContext({
  ...devices["iPhone 14"],
  locale: "ja-JP",
});
await context.route("**/assets/auto-maintenance.js**", (r) => r.abort());
await context.route("**/api/system/status**", async (r) => {
  await r.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ ok: true, maintenance: false }),
  });
});
await context.addInitScript(() => {
  localStorage.setItem(
    "expect_auth_v1",
    JSON.stringify({ id: "flow-probe", display_name: "flow-probe", at: Date.now() })
  );
  localStorage.setItem("expect_access_token_v1", "flow-probe-token");
  localStorage.setItem(
    "expect_terms_v1",
    JSON.stringify({ version: "2026-07-19", accepted: true, at: Date.now() })
  );
  localStorage.setItem(
    "expect_onboard_v1",
    JSON.stringify({ version: "2026-07-19", done: true, at: Date.now() })
  );
  window.__EXPECT_MAINT_BYPASS = true;
});

const page = await context.newPage();
const cdp = await context.newCDPSession(page);
await cdp.send("Network.enable");
try {
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
} catch (_) {}

let transferBytes = 0;
let apiNetworkCount = 0;
const apiPaths = {};
const assetTypes = { js: 0, css: 0, img: 0, other: 0 };

cdp.on("Network.loadingFinished", (e) => {
  transferBytes += e.encodedDataLength || 0;
});
cdp.on("Network.responseReceived", (e) => {
  const u = e.response.url || "";
  const mime = e.response.mimeType || "";
  const n = 0; // size filled on finish only
  if (/\/api\//.test(u) || /config\/beta\.json/.test(u)) {
    try {
      const p = new URL(u).pathname;
      apiPaths[p] = (apiPaths[p] || 0) + 1;
    } catch (_) {}
  }
  if (/image|webp|png|jpeg/i.test(mime + u)) assetTypes.img += 1;
  else if (/javascript|\.js/i.test(mime + u)) assetTypes.js += 1;
  else if (/css/i.test(mime + u)) assetTypes.css += 1;
  else assetTypes.other += 1;
});
cdp.on("Network.requestWillBeSent", (e) => {
  const u = e.request.url || "";
  try {
    const path = new URL(u).pathname;
    if (path.startsWith("/api/") || path === "/config/beta.json") {
      apiNetworkCount += 1;
    }
  } catch (_) {}
});

const started = Date.now();
const snaps = [];
let i = 0;
while (Date.now() - started < 5 * 60 * 1000) {
  const step = FLOW[i % FLOW.length];
  i += 1;
  try {
    await page.goto(step.url, { waitUntil: "domcontentloaded", timeout: 60000 });
  } catch (_) {}
  await page.waitForTimeout(700);
  await page.evaluate(() => window.scrollBy(0, 500)).catch(() => {});
  await page.waitForTimeout(500);
  if (i % 12 === 0 || Date.now() - started > 5 * 60 * 1000 - 2000) {
    const m = await page.evaluate(() => ({
      path: location.pathname,
      nodes: document.getElementsByTagName("*").length,
      heap: performance.memory ? performance.memory.usedJSHeapSize : null,
      cacheKeys: (() => {
        try {
          let n = 0;
          for (let i = 0; i < sessionStorage.length; i++) {
            const k = sessionStorage.key(i);
            if (k && k.indexOf("expect_http_cache_v1:") === 0) n++;
          }
          return n;
        } catch (e) {
          return -1;
        }
      })(),
      hasHttpCache: !!(window.ExpectHttpCache && ExpectHttpCache.cachedGet),
    }));
    snaps.push({
      atMin: Number(((Date.now() - started) / 60000).toFixed(2)),
      transferMB: mb(transferBytes),
      apiNetworkCount,
      ...m,
      heapMB: m.heap != null ? mb(m.heap) : null,
    });
    console.log(JSON.stringify(snaps[snaps.length - 1]));
  }
}

const report = {
  measuredAt: new Date().toISOString(),
  durationMin: 5,
  final: {
    transferMB: mb(transferBytes),
    apiNetworkCount,
    navigations: i,
    apiPaths,
    assetResponseCounts: assetTypes,
  },
  snaps,
  baseline5mFrom30mStudy: {
    note: "30m study had ~127.6MB and 368 APIs at 5min",
    transferMB: 127.6,
    api: 368,
  },
};
fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
console.log("DONE", JSON.stringify(report.final));
await browser.close();
