/**
 * Mobile-like authenticated performance probe (no code changes to product).
 * Injects local auth/terms so requireAuth passes; measures network + vitals + memory.
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

function categorize(url, mime) {
  const u = url || "";
  const m = mime || "";
  if (/\/api\//i.test(u) || /\/config\/beta\.json/i.test(u)) return "api";
  if (/javascript|\.mjs(\?|$)|\.js(\?|$)/i.test(m + " " + u)) return "js";
  if (/css|\.css(\?|$)/i.test(m + " " + u)) return "css";
  if (/image|png|jpe?g|webp|gif|svg|avif/i.test(m + " " + u)) return "img";
  if (/font|woff2?/i.test(m + " " + u)) return "font";
  if (/html|document/i.test(m)) return "doc";
  return "other";
}

async function measurePage(browser, p) {
  const iphone = devices["iPhone 14"];
  const context = await browser.newContext({
    ...iphone,
    locale: "ja-JP",
  });

  await context.addInitScript(() => {
    const auth = {
      id: "perf-probe",
      display_name: "perf-probe",
      at: Date.now(),
    };
    localStorage.setItem("expect_auth_v1", JSON.stringify(auth));
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
  });

  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Performance.enable");

  // Mild CPU throttle (4x) to approximate mid-range mobile
  try {
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  } catch (_) {}

  const responses = new Map();
  const finished = new Map();
  const reqMeta = new Map();

  cdp.on("Network.requestWillBeSent", (e) => {
    reqMeta.set(e.requestId, {
      url: e.request.url,
      method: e.request.method,
      type: e.type,
      ts: e.timestamp,
    });
  });
  cdp.on("Network.responseReceived", (e) => {
    responses.set(e.requestId, {
      url: e.response.url,
      status: e.response.status,
      mime: e.response.mimeType,
      fromDiskCache: !!e.response.fromDiskCache,
      fromServiceWorker: !!e.response.fromServiceWorker,
      fromPrefetchCache: !!e.response.fromPrefetchCache,
    });
  });
  cdp.on("Network.loadingFinished", (e) => {
    finished.set(e.requestId, e.encodedDataLength || 0);
  });

  await page.goto(p.url, { waitUntil: "domcontentloaded", timeout: 90000 });
  // Wait for late XHR / images
  await page.waitForTimeout(8000);
  await page.evaluate(() => window.scrollBy(0, 900)).catch(() => {});
  await page.waitForTimeout(2500);
  await page.evaluate(() => window.scrollBy(0, 900)).catch(() => {});
  await page.waitForTimeout(2500);

  const vitals = await page.evaluate(() => {
    return new Promise((resolve) => {
      const out = {
        title: document.title,
        href: location.href,
        nodes: document.getElementsByTagName("*").length,
        heap: performance.memory ? performance.memory.usedJSHeapSize : null,
        nav: null,
        paints: {},
        lcp: null,
        cls: 0,
        longTasks: [],
      };
      const nav = performance.getEntriesByType("navigation")[0];
      if (nav) {
        out.nav = {
          domContentLoaded: Math.round(nav.domContentLoadedEventEnd),
          loadEvent: Math.round(nav.loadEventEnd),
          responseStart: Math.round(nav.responseStart),
          transferSize: nav.transferSize || 0,
        };
      }
      for (const pe of performance.getEntriesByType("paint")) {
        out.paints[pe.name] = Math.round(pe.startTime);
      }
      try {
        const po = new PerformanceObserver((list) => {
          for (const e of list.getEntries()) {
            if (e.entryType === "largest-contentful-paint") {
              out.lcp = Math.round(e.startTime);
            }
            if (e.entryType === "layout-shift" && !e.hadRecentInput) {
              out.cls += e.value;
            }
            if (e.entryType === "longtask") {
              out.longTasks.push({
                dur: Math.round(e.duration),
                start: Math.round(e.startTime),
              });
            }
          }
        });
        po.observe({
          type: "largest-contentful-paint",
          buffered: true,
        });
        po.observe({ type: "layout-shift", buffered: true });
        po.observe({ type: "longtask", buffered: true });
      } catch (_) {}
      setTimeout(() => {
        out.cls = Number(out.cls.toFixed(3));
        out.longTasks = out.longTasks
          .sort((a, b) => b.dur - a.dur)
          .slice(0, 12);
        resolve(out);
      }, 500);
    });
  });

  // Memory / DOM after idle
  await page.waitForTimeout(4000);
  const later = await page.evaluate(() => ({
    nodes: document.getElementsByTagName("*").length,
    heap: performance.memory ? performance.memory.usedJSHeapSize : null,
  }));

  const buckets = { js: 0, css: 0, img: 0, api: 0, font: 0, doc: 0, other: 0, total: 0 };
  const apiCalls = [];
  const assets = [];
  const urlCount = {};
  const cacheable = [];

  for (const [id, transfer] of finished.entries()) {
    const res = responses.get(id) || {};
    const meta = reqMeta.get(id) || {};
    const url = res.url || meta.url || "";
    const mime = res.mime || "";
    const cat = categorize(url, mime);
    buckets[cat] = (buckets[cat] || 0) + transfer;
    buckets.total += transfer;
    urlCount[url] = (urlCount[url] || 0) + 1;
    const row = {
      url: url.replace("https://expect-keiba.com", "").slice(0, 140),
      cat,
      kb: kb(transfer),
      status: res.status,
      cached: !!(res.fromDiskCache || res.fromServiceWorker || res.fromPrefetchCache),
      type: meta.type,
    };
    assets.push(row);
    if (cat === "api") apiCalls.push(row);
    if (/\/assets\//.test(url) && transfer > 0) {
      cacheable.push(row);
    }
  }

  const dups = Object.entries(urlCount)
    .filter(([, c]) => c > 1)
    .map(([u, c]) => ({
      u: u.replace("https://expect-keiba.com", "").slice(0, 120),
      c,
    }))
    .sort((a, b) => b.c - a.c)
    .slice(0, 20);

  const topImg = assets
    .filter((a) => a.cat === "img")
    .sort((a, b) => b.kb - a.kb)
    .slice(0, 10);
  const topJs = assets
    .filter((a) => a.cat === "js")
    .sort((a, b) => b.kb - a.kb)
    .slice(0, 12);
  const slowHint = assets
    .filter((a) => a.cat === "api")
    .slice()
    .sort((a, b) => b.kb - a.kb);

  const redirectedToLogin = /\/login/i.test(vitals.href || "");

  await context.close();
  return {
    name: p.name,
    url: p.url,
    finalHref: vitals.href,
    redirectedToLogin,
    title: vitals.title,
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
    reqCount: finished.size,
    vitals: {
      fcp: vitals.paints["first-contentful-paint"] || null,
      lcp: vitals.lcp,
      cls: vitals.cls,
      dcl: vitals.nav?.domContentLoaded || null,
      load: vitals.nav?.loadEvent || null,
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
    apiCalls,
    dups,
    topImg,
    topJs,
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
  try {
    const r = await measurePage(browser, p);
    results.push(r);
    console.error(
      "done",
      p.name,
      "totalMB",
      r.transferMB.total,
      "login?",
      r.redirectedToLogin,
      "lcp",
      r.vitals.lcp
    );
  } catch (e) {
    results.push({ name: p.name, error: String(e && e.stack ? e.stack : e) });
    console.error("fail", p.name, e);
  }
}

await browser.close();
fs.writeFileSync(
  outDir + "/auth-mobile-probe.json",
  JSON.stringify({ measuredAt: new Date().toISOString(), results }, null, 2)
);
console.log("WROTE auth-mobile-probe.json");
