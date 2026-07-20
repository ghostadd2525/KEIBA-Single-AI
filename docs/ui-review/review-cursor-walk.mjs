/**
 * UI review walk — cursor-review account (local BFF).
 * Does not mutate Prediction Core / ops config.
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.EXPECT_BASE || "http://127.0.0.1:8788";
const LOGIN_ID = "cursor-review";
const PASSWORD = "Reviewer2026!";
const OUT = path.resolve("docs/ui-review");
const SHOT = path.join(OUT, "shots");

fs.mkdirSync(SHOT, { recursive: true });

const findings = [];
const log = (m) => {
  findings.push(m);
  console.log(m);
};

async function shot(page, name) {
  await page.screenshot({ path: path.join(SHOT, `${name}.png`), fullPage: true });
}

async function bodySnippet(page, n = 280) {
  return (await page.locator("body").innerText()).replace(/\s+/g, " ").slice(0, n);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
});

const consoles = [];
const apis = [];
page.on("console", (m) => {
  if (m.type() === "error" || m.type() === "warning") {
    consoles.push({ type: m.type(), text: m.text() });
  }
});
page.on("pageerror", (e) => consoles.push({ type: "pageerror", text: String(e) }));
page.on("response", (r) => {
  if (r.url().includes("/api/")) {
    apis.push({ status: r.status(), path: r.url().replace(BASE, "").split("?")[0] });
  }
});

// --- Login ---
await page.goto(`${BASE}/login.html`, { waitUntil: "networkidle" });
await page.locator("#tabAccount").click();
await page.locator("#loginId, #accountId, input[name='loginId']").first().fill(LOGIN_ID);
await page.locator("#password, input[type='password']").first().fill(PASSWORD);
await page.locator("#accountForm button[type='submit'], #loginForm button[type='submit']").first().click();
await page.waitForTimeout(2000);
log(`LOGIN url=${page.url()}`);
await shot(page, "01-after-login");

// Skip terms/onboarding if present
await page.evaluate(() => {
  try {
    localStorage.setItem("expect_terms_accepted_v1", "1");
    localStorage.setItem("expect_onboard_done_v1", "1");
    const raw = localStorage.getItem("expect_auth_v1");
    const cur = raw ? JSON.parse(raw) : {};
    cur.termsVersion = cur.termsVersion || "2026-07-19";
    cur.onboardVersion = cur.onboardVersion || "1";
    localStorage.setItem("expect_auth_v1", JSON.stringify(cur));
  } catch (_) {}
});

if (/terms|onboard|setup/i.test(page.url())) {
  await page.goto(`${BASE}/index.html`, { waitUntil: "networkidle" });
}

// --- Home ---
await page.goto(`${BASE}/index.html`, { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
log(`HOME url=${page.url()} | ${await bodySnippet(page)}`);
const homeNav = await page.locator(".bottom-nav a, [data-expect-nav] a").count();
const mascot = await page.locator("#mascotKa0ba").count();
const aiCards = await page.locator(".ai-card").count();
log(`HOME nav_links=${homeNav} mascot=${mascot} ai_cards=${aiCards}`);
await shot(page, "02-home");

// Tap mascot if present
if (mascot) {
  await page.locator("#mascotTalkBtn").click().catch(() => {});
  await page.waitForTimeout(800);
  const bubble = await page.locator("#mascotBubble").innerText().catch(() => "");
  log(`HOME mascot_bubble=${bubble.slice(0, 120)}`);
  await shot(page, "03-home-mascot");
}

// --- Races → Race detail ---
await page.goto(`${BASE}/races.html`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
log(`RACES | ${await bodySnippet(page, 200)}`);
await shot(page, "04-races");

let raceId = "";
const firstRace = page.locator("a[href*='race.html'], a[href*='race?'], .race-card a, .race-row a").first();
if (await firstRace.count()) {
  const href = await firstRace.getAttribute("href");
  const m = String(href || "").match(/race_id=([^&]+)/);
  raceId = m ? decodeURIComponent(m[1]) : "";
  await firstRace.click();
  await page.waitForTimeout(2000);
} else {
  // fallback known id
  raceId = "20260719_hanshin_11";
  await page.goto(`${BASE}/race.html?race_id=${raceId}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
}
log(`RACE url=${page.url()} race_id=${raceId || "(from url)"} | ${await bodySnippet(page)}`);
const tabs = await page.locator("#detailTabs .chip").allInnerTexts();
log(`RACE tabs=${JSON.stringify(tabs)}`);
const strategyCta = await page.locator("#strategyLink").innerText().catch(() => "");
log(`RACE strategy_cta=${strategyCta}`);
const fabVisible = await page.locator(".fab-bet").isVisible().catch(() => false);
log(`RACE fab_visible=${fabVisible}`);
await shot(page, "05-race-detail");

// Click non-active tabs to see if they switch content
const tabBtns = page.locator("#detailTabs .chip");
const tabCount = await tabBtns.count();
for (let i = 1; i < Math.min(tabCount, 3); i++) {
  await tabBtns.nth(i).click();
  await page.waitForTimeout(400);
}
const activeTab = await page.locator("#detailTabs .chip.is-active").innerText().catch(() => "");
log(`RACE after_tab_clicks active=${activeTab}`);
await shot(page, "06-race-tabs");

// --- Strategy (買い方相談) ---
const rid = raceId || new URL(page.url()).searchParams.get("race_id") || "20260719_hanshin_11";
await page.goto(`${BASE}/strategy.html?race_id=${encodeURIComponent(rid)}`, {
  waitUntil: "networkidle",
});
await page.waitForTimeout(1800);
log(`STRATEGY | ${await bodySnippet(page)}`);
const consultBtn = page.locator("#consultKaobaBtn");
const hasConsult = (await consultBtn.count()) > 0;
log(`STRATEGY consult_btn=${hasConsult}`);
await shot(page, "07-strategy");

// --- Chat from strategy ---
if (hasConsult) {
  await consultBtn.click();
  await page.waitForTimeout(2500);
} else {
  await page.goto(`${BASE}/chat.html?from=strategy&race_id=${encodeURIComponent(rid)}`, {
    waitUntil: "networkidle",
  });
  await page.waitForTimeout(2000);
}
log(`CHAT_FROM_STRATEGY url=${page.url()} | ${await bodySnippet(page, 320)}`);
const openMsgs = await page.locator(".msg").count();
log(`CHAT open_messages=${openMsgs}`);
await shot(page, "08-chat-strategy-entry");

// Send chip / free text
const chip = page.locator("#quickChips .chip").first();
if (await chip.count()) {
  await chip.click();
  await page.waitForTimeout(3500);
  const lastAi = await page.locator(".msg-ai .msg-bubble, .msg-ai").last().innerText().catch(() => "");
  log(`CHAT chip_reply=${lastAi.slice(0, 200)}`);
  await shot(page, "09-chat-after-chip");
}

await page.locator("#chatInput").fill("このレースの本命と買い方を短く教えて");
await page.locator("#chatSend").click();
await page.waitForTimeout(4000);
const freeReply = await page.locator(".msg-ai .msg-bubble, .msg-ai").last().innerText().catch(() => "");
log(`CHAT free_reply=${freeReply.slice(0, 240)}`);
await shot(page, "10-chat-after-free");

// Direct KAOBA entry (mypage path)
await page.goto(`${BASE}/chat.html`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200);
log(`CHAT_DIRECT url=${page.url()} msgs=${await page.locator(".msg").count()} | ${await bodySnippet(page, 200)}`);
await shot(page, "11-chat-direct");

// Mobile a11y spot checks on home
await page.goto(`${BASE}/index.html`, { waitUntil: "networkidle" });
const issues = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll("button, a").forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0 && (r.width < 36 || r.height < 36)) {
      const label = (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 40);
      out.push({ tag: el.tagName, w: Math.round(r.width), h: Math.round(r.height), label });
    }
  });
  return out.slice(0, 12);
});
log(`A11Y small_targets=${JSON.stringify(issues)}`);

const report = {
  base: BASE,
  account: LOGIN_ID,
  race_id: rid,
  findings,
  apis: apis.slice(-40),
  consoles,
  generated_at: new Date().toISOString(),
};
fs.writeFileSync(path.join(OUT, "walk-report.json"), JSON.stringify(report, null, 2));
log("DONE wrote docs/ui-review/walk-report.json");
await browser.close();
