/**
 * 30-minute real-user flow simulation on production.
 * Cycles: home → races → detail → consult → analysis → fortune
 * Snapshots every 5 minutes. No product code changes.
 */
import { chromium, devices } from "playwright";
import fs from "fs";

const OUT =
  "C:/win5-ai/KEIBA-Single-AI/tmp/perf-20260731/user-flow-30m.json";
const chromePath =
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const TOTAL_MS = 30 * 60 * 1000;
const SNAP_MS = 5 * 60 * 1000;
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
  return n == null ? null : Number((n / 1024 / 1024).toFixed(3));
}

async function main() {
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
    args: ["--disable-dev-shm-usage"],
  });

  const context = await browser.newContext({
    ...devices["iPhone 14"],
    locale: "ja-JP",
  });

  // Keep client session alive for SPA-like multi-page browsing
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
      JSON.stringify({
        id: "flow-probe",
        display_name: "flow-probe",
        at: Date.now(),
      })
    );
    localStorage.setItem("expect_access_token_v1", "flow-probe-token");
    localStorage.setItem(
      "expect_terms_v1",
      JSON.stringify({
        version: "2026-07-19",
        accepted: true,
        at: Date.now(),
      })
    );
    localStorage.setItem(
      "expect_onboard_v1",
      JSON.stringify({ version: "2026-07-19", done: true, at: Date.now() })
    );
    localStorage.setItem("expect_account_ready_v1", "1");
    window.__EXPECT_MAINT_BYPASS = true;

    // FPS / longtask / CLS collectors
    window.__PERF_PROBE = {
      frames: 0,
      lastTs: performance.now(),
      fpsSamples: [],
      longTasks: [],
      apiCalls: 0,
      transferBytes: 0,
    };

    const probe = window.__PERF_PROBE;
    const loop = (ts) => {
      probe.frames += 1;
      if (ts - probe.lastTs >= 1000) {
        probe.fpsSamples.push(probe.frames);
        if (probe.fpsSamples.length > 120) probe.fpsSamples.shift();
        probe.frames = 0;
        probe.lastTs = ts;
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);

    try {
      const po = new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          if (e.entryType === "longtask") {
            probe.longTasks.push({
              dur: Math.round(e.duration),
              start: Math.round(e.startTime),
              at: Date.now(),
            });
            if (probe.longTasks.length > 200) probe.longTasks.shift();
          }
        }
      });
      po.observe({ type: "longtask", buffered: true });
    } catch (_) {}

    // Hook fetch for API counting
    const origFetch = window.fetch.bind(window);
    window.fetch = async (...args) => {
      try {
        const u = String(args[0] && args[0].url ? args[0].url : args[0]);
        if (/\/api\//.test(u) || /config\/beta\.json/.test(u)) {
          probe.apiCalls += 1;
        }
      } catch (_) {}
      return origFetch(...args);
    };
  });

  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  try {
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  } catch (_) {}

  let transferBytes = 0;
  let apiNetworkCount = 0;
  const apiUrls = [];

  cdp.on("Network.loadingFinished", (e) => {
    transferBytes += e.encodedDataLength || 0;
  });
  cdp.on("Network.requestWillBeSent", (e) => {
    const u = e.request.url || "";
    try {
      const path = new URL(u).pathname;
      if (path.startsWith("/api/") || path === "/config/beta.json") {
        apiNetworkCount += 1;
        apiUrls.push({ u: path + (new URL(u).search || ""), t: Date.now() });
        if (apiUrls.length > 500) apiUrls.shift();
      }
    } catch (_) {}
  });

  const startedAt = Date.now();
  const snapshots = [];
  let flowIndex = 0;
  let actions = 0;
  let snapIndex = 0;

  async function interact(label) {
    actions += 1;
    try {
      await page.waitForTimeout(800 + Math.floor(Math.random() * 700));
      await page.evaluate(() => window.scrollBy(0, 400 + Math.random() * 500));
      await page.waitForTimeout(500 + Math.floor(Math.random() * 500));
      // light taps
      const clicked = await page.evaluate(() => {
        const candidates = [
          ...document.querySelectorAll(
            "a.race-item, .fav-card, .chip, .tab-pill, button.chip, .ai-card, .nav a, [data-nav]"
          ),
        ].filter((el) => {
          const r = el.getBoundingClientRect();
          return r.width > 10 && r.height > 10 && r.bottom > 0 && r.top < innerHeight;
        });
        if (!candidates.length) return null;
        const el = candidates[Math.floor(Math.random() * Math.min(5, candidates.length))];
        el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
        return (el.className || el.tagName || "").toString().slice(0, 60);
      });
      await page.waitForTimeout(600 + Math.floor(Math.random() * 900));
      return clicked;
    } catch (e) {
      return String(e.message || e).slice(0, 80);
    }
  }

  async function takeSnapshot(reason) {
    const elapsedMin = Number(((Date.now() - startedAt) / 60000).toFixed(2));
    const metrics = await page.evaluate(() => {
      const p = window.__PERF_PROBE || {
        fpsSamples: [],
        longTasks: [],
        apiCalls: 0,
      };
      const samples = p.fpsSamples || [];
      const recent = samples.slice(-5);
      const fps =
        recent.length > 0
          ? Math.round(recent.reduce((a, b) => a + b, 0) / recent.length)
          : null;
      const longRecent = (p.longTasks || []).filter(
        (t) => Date.now() - (t.at || 0) < 5 * 60 * 1000
      );
      return {
        href: location.href,
        path: location.pathname,
        title: document.title,
        nodes: document.getElementsByTagName("*").length,
        heap: performance.memory ? performance.memory.usedJSHeapSize : null,
        heapTotal: performance.memory
          ? performance.memory.totalJSHeapSize
          : null,
        fps,
        fpsSamples: samples.slice(-10),
        longTaskCount5m: longRecent.length,
        longTaskMax5m: longRecent.reduce((m, t) => Math.max(m, t.dur || 0), 0),
        longTaskSum5m: longRecent.reduce((s, t) => s + (t.dur || 0), 0),
        fetchApiCalls: p.apiCalls || 0,
        bodyChildren: document.body ? document.body.children.length : 0,
      };
    });

    const snap = {
      index: snapIndex,
      reason,
      at: new Date().toISOString(),
      elapsedMin,
      transferMB: mb(transferBytes),
      transferBytes,
      apiNetworkCount,
      apiRecent: apiUrls.slice(-15),
      actions,
      flowIndex,
      ...metrics,
      heapMB: mb(metrics.heap),
      heapTotalMB: mb(metrics.heapTotal),
    };
    snapshots.push(snap);
    snapIndex += 1;
    fs.writeFileSync(
      OUT,
      JSON.stringify(
        {
          startedAt: new Date(startedAt).toISOString(),
          updatedAt: new Date().toISOString(),
          note: "auto-maintenance aborted; API may 401; CPU 4x mobile",
          snapshots,
        },
        null,
        2
      )
    );
    console.log(
      JSON.stringify({
        snap: snap.index,
        min: snap.elapsedMin,
        path: snap.path,
        transferMB: snap.transferMB,
        heapMB: snap.heapMB,
        nodes: snap.nodes,
        fps: snap.fps,
        longTasks5m: snap.longTaskCount5m,
        longMax: snap.longTaskMax5m,
        api: snap.apiNetworkCount,
      })
    );
  }

  // Initial navigation
  await page.goto(FLOW[0].url, {
    waitUntil: "domcontentloaded",
    timeout: 90000,
  });
  await page.waitForTimeout(2000);
  await takeSnapshot("t0");

  let nextSnapAt = startedAt + SNAP_MS;
  const endAt = startedAt + TOTAL_MS;

  while (Date.now() < endAt) {
    const step = FLOW[flowIndex % FLOW.length];
    flowIndex += 1;
    try {
      await page.goto(step.url, {
        waitUntil: "domcontentloaded",
        timeout: 60000,
      });
    } catch (e) {
      console.error("nav-fail", step.name, String(e).slice(0, 100));
    }
    await interact(step.name);
    // Sometimes stay and scroll more (dwell)
    if (Math.random() < 0.4) {
      await interact(step.name + ":dwell");
    }

    if (Date.now() >= nextSnapAt) {
      await takeSnapshot(`t${snapIndex * 5}m`);
      nextSnapAt += SNAP_MS;
    }
  }

  await takeSnapshot("t30m-final");

  // Trend analysis
  const heaps = snapshots.map((s) => s.heapMB).filter((x) => x != null);
  const nodes = snapshots.map((s) => s.nodes);
  const trend = {
    heapStart: heaps[0],
    heapEnd: heaps[heaps.length - 1],
    heapDelta: heaps.length
      ? Number((heaps[heaps.length - 1] - heaps[0]).toFixed(3))
      : null,
    heapMonotonicUp: heaps.every((v, i) => i === 0 || v >= heaps[i - 1] - 0.02),
    nodesStart: nodes[0],
    nodesEnd: nodes[nodes.length - 1],
    nodesDelta: nodes[nodes.length - 1] - nodes[0],
    nodesMonotonicUp: nodes.every((v, i) => i === 0 || v >= nodes[i - 1]),
  };

  const report = {
    startedAt: new Date(startedAt).toISOString(),
    endedAt: new Date().toISOString(),
    durationMin: 30,
    methodology: {
      device: "iPhone 14 emulation",
      cpuThrottle: "4x",
      auth: "localStorage seed",
      maintenance: "auto-maintenance.js aborted + status stubbed",
      apiNote: "Most /api/* likely 401 without real token",
    },
    trend,
    snapshots,
    topApiPaths: Object.entries(
      apiUrls.reduce((acc, x) => {
        const k = x.u.split("?")[0];
        acc[k] = (acc[k] || 0) + 1;
        return acc;
      }, {})
    )
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20),
  };

  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log("DONE", JSON.stringify(trend));
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
