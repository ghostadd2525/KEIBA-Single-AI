#!/usr/bin/env node
/**
 * Sync Improvement Evidence (+ legacy miss) into Git paths.
 *
 * Usage:
 *   node scripts/ops/sync-miss-evidence.mjs --date 2026-07-19
 *   node scripts/ops/sync-miss-evidence.mjs --date 2026-07-19 --commit
 */
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function copyTree(src, dest) {
  if (!existsSync(src)) return false;
  mkdirSync(dest, { recursive: true });
  for (const name of readdirSync(src)) {
    const s = join(src, name);
    const d = join(dest, name);
    if (statSync(s).isDirectory()) copyTree(s, d);
    else cpSync(s, d);
  }
  return true;
}

const date = arg("--date", "");
const doCommit = process.argv.includes("--commit");
const fromImp =
  process.env.EXPECT_IMPROVEMENT_EVIDENCE_DIR ||
  join(REPO, "services", "win5-ai", "var", "improvement-evidence");
const fromMiss =
  process.env.EXPECT_MISS_EVIDENCE_DIR ||
  join(REPO, "services", "win5-ai", "var", "miss-evidence");
const toImp = join(REPO, "evidence", "improvement");
const toMiss = join(REPO, "evidence", "miss");

if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
  console.error("Usage: node scripts/ops/sync-miss-evidence.mjs --date YYYY-MM-DD [--commit]");
  process.exit(2);
}

const synced = {
  improvement_event_types: [],
  miss: false,
};

for (const et of ["miss", "feature_missing", "prediction_failed", "result_sync_failed"]) {
  const src = join(fromImp, et, date);
  if (copyTree(src, join(toImp, et, date))) synced.improvement_event_types.push(et);
}
copyTree(join(fromImp, "manifest", date), join(toImp, "manifest", date));

if (copyTree(join(fromMiss, date), join(toMiss, date))) synced.miss = true;

const summaryPath = join(toImp, "manifest", date, "summary.json");
let eventTotal = 0;
if (existsSync(summaryPath)) {
  const s = JSON.parse(readFileSync(summaryPath, "utf8"));
  eventTotal = s.event_total || 0;
  s.synced_at = new Date().toISOString();
  writeFileSync(summaryPath, JSON.stringify(s, null, 2) + "\n", "utf8");
}

console.log(JSON.stringify({ ok: true, date, synced, eventTotal }, null, 2));

if (doCommit) {
  spawnSync("git", ["add", `evidence/improvement`, `evidence/miss/${date}`], {
    cwd: REPO,
    stdio: "inherit",
  });
  const msg = `evidence: improvement export ${date} (${eventTotal} events)`;
  const r = spawnSync("git", ["commit", "-m", msg], { cwd: REPO, encoding: "utf8" });
  if (r.status !== 0) {
    console.error(r.stdout || r.stderr || "commit failed or nothing to commit");
    process.exit(r.status ?? 1);
  }
}
