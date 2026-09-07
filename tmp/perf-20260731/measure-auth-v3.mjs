/**
 * Measure authenticated pages by blocking auto-maintenance (which force-clears invalid tokens).
 * Methodology: iPhone 14 viewport, CPU 4x throttle, cold-ish loads, no product code changes.
 */
import { chromium, devices } from "playwright";
import fs from "fs";

const outDir = "C:/win5-ai/KEIBA-Single-AI/tmp/perf-20260731";
const chromePath =
  "C:/Program Files/Google/Chrome/Application/chrome.exe";

const pages = [
  { name: "home", url: "https://expect-keiba.com/" },
  { name: "races", url: "https://expect-keiba.com/races" },
  {
    name: "detail",
    url: "https://expect-keiba.com/race.html?race_id=2026-08-01-01-02",
  },
  { name: "analysis", url: "https://expect-keiba.com/analysis.html" },
  { name: "fortune", url: "https://expect-keiba.com/fortune.html" },
  { name: "consult", url: "https://expect-keiba.com/chat.html?mode=review" },
];

function mb(n) {
  return Number((n / 1024 / 1024).toFixed(2));
}
function kb(n) {
  return Math.round(n / 1024);
}

function categorize(url, mime, resourceType) {
  try {
    const u = new URL(url);
    const path = u.pathname || "";
    if (path.startsWith("/api/") || path === "/config/beta.json") return "api";
    if (resourceType === "Script" || /\.m?js(\?|$)/i.test(path)) return "js";
    if (resourceType === "Stylesheet" || /\.css(\?|$)/i.test(path)) return "css";
    if (
      resourceType === "Image" ||
      resourceType === "Media" ||
      /\.(png|jpe?g|webp|gif|svg|avif)(\?|$)/i.test(path)
    )
      return "img";
    if (/\.(woff2?|ttf|otf)(\?|$)/i.test(path) || /font/i.test(mime || ""))
      return "font";
    if (resourceType === "Document" || path.endsWith(".html") || path === "/" || path === "/races")
      return "doc";
  } catch (_) {}
  return "other";
}

async function measurePage(browser, p) {
  const context = await browser.newContext({
    ...devices["iPhone 14"],
    locale: "ja-JP",
  });

  // Prevent maintenance gate from wiping fake probe session
  await context.route("**/assets/auto-maintenance.js**", (route) => route.abort());
  await context.route("**/api/system/status**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        maintenance: false,
        maintenance_mode: false,
      }),
    });
  });

  await context.addInitScript(() => {
    localStorage.setItem(
      "expect_auth_v1",
      JSON.stringify({
        id: "perf-probe",
        display_name: "perf-probe",
        at: Date.now(),
      })
    );
    localStorage.setItem("expect_access_token_v1", "perf-probe-token");
    localStorage.setItem(
      "expect_terms_v1",
      JSON.stringify({ version: "2026-07-19", accepted: true, at: Date.now() })
    );
    localStorage.setItem(
      "expect_onboard_v1",
      JSON.stringify({ version: "2026-07-19", done: true, at: Date.now() })
    );
    localStorage.setItem("expect_account_ready_v1", "1");
    window.__EXPECT_MAINT_BYPASS = true;
  });

  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  try {
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  } catch (_) {}

  const responses = new Map();
  const finished = new Map();
  const reqMeta = new Map();
  const startWall = new Map();

  cdp.on("Network.requestWillBeSent", (e) => {
    reqMeta.set(e.requestId, {
      url: e.request.url,
      method: e.request.method,
      type: e.type,
    });
    startWall.set(e.requestId, Date.now());
  });
  cdp.on("Network.responseReceived", (e) => {
    responses.set(e.requestId, {
      url: e.response.url,
      status: e.response.status,
      mime: e.response.mimeType,
      fromDiskCache: !!e.response.fromDiskCache,
      fromServiceWorker: !!e.response.fromServiceWorker,
    });
  });
  cdp.on("Network.loadingFinished", (e) => {
    finished.set(e.requestId, {
      bytes: e.encodedDataLength || 0,
      ms: startWall.has(e.requestId) ? Date.now() - startWall.get(e.requestId) : null,
    });
  });

  await page.goto(p.url, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(12000);
  await page.evaluate(() => window.scrollBy(0, 1200)).catch(() => {});
  await page.waitForTimeout(3000);
  await page.evaluate(() => window.scrollBy(0, 1200)).catch(() => {});
  await page.waitForTimeout(4000);

  const vitals = await page.evaluate(() => {
    const out = {
      title: document.title,
      href: location.href,
      path: location.pathname,
      nodes: document.getElementsByTagName("*").length,
      heap: performance.memory ? performance.memory.usedJSHeapSize : null,
      fcp: null,
      lcp: null,
      cls: 0,
      longTasks: [],
      dcl: null,
      load: null,
      raceCards: document.querySelectorAll("a.race-item, .fav-card, .ai-card").length,
    };
    const nav = performance.getEntriesByType("navigation")[0];
    if (nav) {
      out.dcl = Math.round(nav.domContentLoadedEventEnd);
      out.load = Math.round(nav.loadEventEnd);
    }
    for (const pe of performance.getEntriesByType("paint")) {
      if (pe.name === "first-contentful-paint") out.fcp = Math.round(pe.startTime);
    }
    for (const e of performance.getEntriesByType("largest-contentful-paint")) {
      out.lcp = Math.round(e.startTime);
    }
    for (const e of performance.getEntriesByType("layout-shift")) {
      if (!e.hadRecentInput) out.cls += e.value;
    }
    for (const e of performance.getEntriesByType("longtask")) {
      out.longTasks.push({
        dur: Math.round(e.duration),
        start: Math.round(e.startTime),
      });
    }
    out.cls = Number(out.cls.toFixed(3));
    out.longTasks = out.longTasks.sort((a, b) => b.dur - a.dur).slice(0, 15);
    return out;
  });

  await page.waitForTimeout(6000);
  await page.evaluate(() => window.scrollBy(0, 400)).catch(() => {});
  await page.waitForTimeout(2000);
  const later = await page.evaluate(() => ({
    nodes: document.getElementsByTagName("*").length,
    heap: performance.memory ? performance.memory.usedJSHeapSize : null,
  }));

  const buckets = { js: 0, css: 0, img: 0, api: 0, font: 0, doc: 0, other: 0, total: 0 };
  const apiCalls = [];
  const assets = [];
  const urlCount = {};

  for (const [id, fin] of finished.entries()) {
    const res = responses.get(id) || {};
    const meta = reqMeta.get(id) || {};
    const url = res.url || meta.url || "";
    const cat = categorize(url, res.mime || "", meta.type || "");
    const transfer = fin.bytes || 0;
    buckets[cat] = (buckets[cat] || 0) + transfer;
    buckets.total += transfer;
    urlCount[url] = (urlCount[url] || 0) + 1;
    const row = {
      url: url.replace("https://expect-keiba.com", "").slice(0, 170),
      cat,
      kb: kb(transfer),
      status: res.status,
      cached: !!(res.fromDiskCache || res.fromServiceWorker),
      type: meta.type,
      ms: fin.ms,
    };
    assets.push(row);
    if (cat === "api") apiCalls.push(row);
  }

  const dups = Object.entries(urlCount)
    .filter(([, c]) => c > 1)
    .map(([u, c]) => ({
      u: u.replace("https://expect-keiba.com", "").slice(0, 150),
      c,
    }))
    .sort((a, b) => b.c - a.c);

  await context.close();
  return {
    name: p.name,
    finalHref: vitals.href,
    path: vitals.path,
    redirectedToLogin: /login/i.test(vitals.path || ""),
    title: vitals.title,
    raceCards: vitals.raceCards,
    transferMB: {
      js: mb(buckets.js),
      css: mb(buckets.css),
      img: mb(buckets.img),
      api: mb(buckets.api),
      font: mb(buckets.font),
      other: mb(buckets.doc + buckets.other),
      total: mb(buckets.total),
    },
    transferBytes: buckets,
    reqCount: assets.length,
    vitals: {
      fcp: vitals.fcp,
      lcp: vitals.lcp,
      cls: vitals.cls,
      dcl: vitals.dcl,
      load: vitals.load,
    },
    longTasks: vitals.longTasks,
    memory: {
      heapAfterLoadMB: vitals.heap != null ? mb(vitals.heap) : null,
      heapLaterMB: later.heap != null ? mb(later.heap) : null,
      nodesAfterLoad: vitals.nodes,
      nodesLater: later.nodes,
      heapDeltaMB:
        vitals.heap != null && later.heap != null
          ? mb(later.heap - vitals.heap)
          : null,
      nodeDelta: later.nodes - vitals.nodes,
    },
    apiCalls: apiCalls.sort((a, b) => (b.ms || 0) - (a.ms || 0)),
    dups,
    topImg: assets
      .filter((a) => a.cat === "img")
      .sort((a, b) => b.kb - a.kb)
      .slice(0, 12),
    topJs: assets
      .filter((a) => a.cat === "js")
      .sort((a, b) => b.kb - a.kb)
      .slice(0, 15),
    note: "auto-maintenance.js aborted + system/status stubbed to keep session for measurement",
  };
}

const browser = await chromium.launch({
  executablePath: chromePath,
  headless: true,
  args: ["--disable-dev-shm-usage"],
});

const results = [];
for (const p of pages) {
  console.error("measuring", p.name);
  const r = await measurePage(browser, p);
  results.push(r);
  console.error(
    JSON.stringify({
      name: r.name,
      path: r.path,
      total: r.transferMB.total,
      js: r.transferMB.js,
      css: r.transferMB.css,
      img: r.transferMB.img,
      api: r.transferMB.api,
      font: r.transferMB.font,
      fcp: r.vitals.fcp,
      lcp: r.vitals.lcp,
      cls: r.vitals.cls,
      cards: r.raceCards,
      long: r.longTasks[0] || null,
      heap: r.memory.heapLaterMB,
      nodes: r.memory.nodesLater,
    })
  );
}
await browser.close();
fs.writeFileSync(
  outDir + "/auth-mobile-probe-v3.json",
  JSON.stringify({ measuredAt: new Date().toISOString(), results }, null, 2)
);
console.log("WROTE auth-mobile-probe-v3.json");
