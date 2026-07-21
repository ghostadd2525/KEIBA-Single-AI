/**
 * Phase7 — Real PB から UI カード HTML プレビューを生成し、可能なら Playwright で撮影
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const ART = path.join(ROOT, "docs/phase7/artifacts");
const PREV = path.join(ROOT, "docs/phase7/screenshots");

function scorePercent(bundle) {
  const c = (bundle && bundle.ai_confidence) || {};
  if (typeof c.score === "number") {
    return c.score <= 1 ? Math.round(c.score * 100) : Math.round(c.score);
  }
  return 0;
}

function starsFromScore(pct) {
  const n = Math.max(1, Math.min(5, Math.round((Number(pct) || 0) / 20)));
  let s = "";
  for (let i = 0; i < 5; i++) s += i < n ? "★" : "☆";
  return s;
}

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function honmei(bundle) {
  const runners = (((bundle || {}).evaluation || {}).runners) || [];
  return runners.find((r) => r.mark === "honmei") || runners[0] || null;
}

function raceCard(bundle) {
  const info = bundle.race_info || {};
  const conf = scorePercent(bundle);
  const place = `${info.venue || ""} ${info.race_no != null ? info.race_no + "R" : ""}`.trim();
  const name = info.class_label || "レース";
  const grade = info.grade || "";
  const post = info.post_time || "—";
  return `<article class="race-item">
  <div>
    <p class="place">${escapeHtml(place)}</p>
    <p class="name">${escapeHtml(name)}${grade ? "（" + escapeHtml(grade) + "）" : ""}</p>
    <div class="meta"><span>${escapeHtml(post)}発走</span><span class="stars">${starsFromScore(conf)}</span></div>
  </div>
  <div class="side"><div class="conf">${conf}%<small>AI信頼度</small></div><span class="src">${escapeHtml(bundle.product_version || "")}</span></div>
</article>`;
}

function detailCard(bundle) {
  const info = bundle.race_info || {};
  const conf = scorePercent(bundle);
  const h = honmei(bundle) || {};
  const narrative = (bundle.explain && bundle.explain.narrative) || "";
  return `<section class="detail">
  <h2>${escapeHtml(info.venue || "")} ${info.race_no != null ? info.race_no + "R" : ""}</h2>
  <p class="sub">${escapeHtml(info.class_label || "")}${info.post_time ? " · " + escapeHtml(info.post_time) : ""}</p>
  <div class="honmei">
    <div class="num">${escapeHtml(h.horse_number)}</div>
    <div>
      <h3>${escapeHtml(h.horse_name || "本命馬")}</h3>
      <p>AI本命 · 信頼度 ${conf}%</p>
      <p class="stars">${starsFromScore(conf)}</p>
    </div>
  </div>
  <div class="pace"><strong>展開</strong><p>${escapeHtml(narrative)}</p></div>
  <div class="bets">買い目 ${((bundle.betting_recommendations || {}).items || []).length} 件</div>
</section>`;
}

function page(title, body) {
  return `<!doctype html><html lang="ja"><head><meta charset="utf-8"/><title>${escapeHtml(title)}</title>
<style>
  body{font-family:"Segoe UI","Hiragino Sans",sans-serif;background:#f3f0ea;color:#1a1a1a;margin:0;padding:24px}
  h1{font-size:18px;margin:0 0 16px}
  .grid{display:grid;gap:12px;max-width:720px}
  .race-item{display:flex;justify-content:space-between;gap:12px;background:#fff;border:1px solid #ddd;padding:14px 16px;border-radius:4px}
  .place{margin:0;font-size:12px;color:#666}.name{margin:4px 0;font-weight:700}.meta{font-size:12px;color:#555;display:flex;gap:10px}
  .side{text-align:right}.conf{font-size:22px;font-weight:700;line-height:1}.conf small{display:block;font-size:10px;font-weight:400;color:#777}
  .src{display:block;font-size:10px;color:#999;margin-top:6px;max-width:160px}
  .detail{background:#fff;border:1px solid #ddd;padding:20px;border-radius:4px;max-width:520px}
  .honmei{display:flex;gap:14px;margin:16px 0;align-items:center}
  .num{width:56px;height:56px;border-radius:50%;background:#1f3a5f;color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700}
  .pace{background:#f7f5f1;padding:12px;margin-top:12px}.pace p{margin:6px 0 0;font-size:14px;line-height:1.5}
  .badge{display:inline-block;background:#e8e4dc;padding:2px 8px;font-size:11px;margin-bottom:8px}
</style></head><body>${body}</body></html>`;
}

fs.mkdirSync(PREV, { recursive: true });
const files = fs.readdirSync(ART).filter((f) => f.startsWith("bundle-") && f.endsWith(".json")).sort();
const bundles = files.map((f) => JSON.parse(fs.readFileSync(path.join(ART, f), "utf8")));

const listHtml = page(
  "Phase7 races list preview",
  `<h1>Phase7 · レース一覧プレビュー（Real/Mock混在）</h1><div class="grid">${bundles.map(raceCard).join("")}</div>`
);
const listPath = path.join(PREV, "preview-races-list.html");
fs.writeFileSync(listPath, listHtml, "utf8");

const real = bundles.filter((b) => String(b.product_version || "").includes("single-ai"));
const mockFb = bundles.filter((b) => !String(b.product_version || "").includes("single-ai"));
const detailTargets = [...real.slice(0, 2), ...mockFb.slice(0, 1)];
const detailPaths = [];
for (const b of detailTargets) {
  const html = page(
    `Phase7 detail ${b.race_id}`,
    `<span class="badge">${String(b.product_version || "").includes("single-ai") ? "REAL AI" : "MOCK FALLBACK"}</span>
     ${detailCard(b)}`
  );
  const p = path.join(PREV, `preview-detail-${b.race_id}.html`);
  fs.writeFileSync(p, html, "utf8");
  detailPaths.push(p);
}

console.log("wrote", listPath);
detailPaths.forEach((p) => console.log("wrote", p));

// Playwright optional
const shotScript = `
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 800, height: 1200 } });
  const files = ${JSON.stringify([listPath, ...detailPaths])};
  for (const f of files) {
    await page.goto('file:///' + f.replace(/\\\\/g, '/'));
    const out = f.replace(/\\.html$/, '.png');
    await page.screenshot({ path: out, fullPage: true });
    console.log('shot', out);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
`;
const shotJs = path.join(PREV, "_shot.mjs");
// use .cjs for require
const shotCjs = path.join(PREV, "_shot.cjs");
fs.writeFileSync(shotCjs, shotScript.replace("shot.mjs", "shot.cjs"), "utf8");

const tryPw = spawnSync(
  process.platform === "win32" ? "npx.cmd" : "npx",
  ["--yes", "playwright", "install", "chromium"],
  { cwd: ROOT, encoding: "utf8", timeout: 180000, shell: true }
);
console.log("playwright install status", tryPw.status);

const run = spawnSync(
  process.platform === "win32" ? "npx.cmd" : "npx",
  ["--yes", "playwright", "test", "--version"],
  { cwd: ROOT, encoding: "utf8", shell: true }
);

const nodeRun = spawnSync("node", ["-e", `
try {
  require('playwright');
  console.log('has-playwright');
} catch (e) {
  console.log('no-playwright');
}
`], { cwd: ROOT, encoding: "utf8", shell: true });

if ((nodeRun.stdout || "").includes("has-playwright") || tryPw.status === 0) {
  const exec = spawnSync("npx", ["--yes", "-p", "playwright", "node", shotCjs], {
    cwd: ROOT,
    encoding: "utf8",
    shell: true,
    timeout: 120000,
  });
  console.log(exec.stdout);
  console.error(exec.stderr);
  console.log("shot exit", exec.status);
} else {
  console.log("Playwright unavailable; HTML previews only");
}
