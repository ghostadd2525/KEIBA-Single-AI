/**
 * Version8 calendar helpers (JST).
 * Research (Analyzer→Decide) is forbidden on Sat/Sun.
 * Production Evidence collection remains ResultAutomation-only on race days.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, "..", "..", "..");

/** @param {Date} [now] */
export function jstParts(now = new Date()) {
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  });
  const map = Object.fromEntries(
    fmt.formatToParts(now).filter((p) => p.type !== "literal").map((p) => [p.type, p.value])
  );
  const wd = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return {
    date_jst: `${map.year}-${map.month}-${map.day}`,
    weekday: wd[map.weekday] ?? 0,
    weekday_name: map.weekday,
  };
}

/** @param {Date} [now] */
export function isRaceWeekendJst(now = new Date()) {
  const w = jstParts(now).weekday;
  return w === 0 || w === 6;
}

/**
 * ISO week id in JST: YYYY-Www
 * @param {Date} [now]
 */
export function weekIdJst(now = new Date()) {
  const parts = jstParts(now);
  const [y, m, d] = parts.date_jst.split("-").map(Number);
  const utc = new Date(Date.UTC(y, m - 1, d));
  const dayNum = utc.getUTCDay() || 7;
  utc.setUTCDate(utc.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((utc - yearStart) / 86400000 + 1) / 7);
  const isoYear = utc.getUTCFullYear();
  return `${isoYear}-W${String(weekNo).padStart(2, "0")}`;
}

/**
 * @param {{ allowWeekend?: boolean, now?: Date, purpose?: string }} [opts]
 */
export function assertResearchDay(opts = {}) {
  if (opts.allowWeekend) return { ok: true, ...jstParts(opts.now) };
  if (!isRaceWeekendJst(opts.now)) return { ok: true, ...jstParts(opts.now) };
  const p = jstParts(opts.now);
  const err = new Error(
    `Version8 Research forbidden on race weekend (JST ${p.date_jst} ${p.weekday_name}). ` +
      `Production collects Evidence only. purpose=${opts.purpose || "research"}`
  );
  err.code = "V8_RESEARCH_WEEKEND_BLOCKED";
  throw err;
}

/** Soft gate for callers that prefer boolean over throw. */
export function researchGate(purpose = "research", now = new Date()) {
  if (!isRaceWeekendJst(now)) {
    return { allowed: true, blocked: false, purpose, ...jstParts(now) };
  }
  const p = jstParts(now);
  return {
    allowed: false,
    blocked: true,
    purpose,
    code: "V8_RESEARCH_WEEKEND_BLOCKED",
    message:
      `Version8 Research forbidden on race weekend (JST ${p.date_jst} ${p.weekday_name}). ` +
      `Production collects Evidence only. purpose=${purpose}`,
    ...p,
  };
}

/** Alias used by tests / docs */
export const isWeekendJst = isRaceWeekendJst;

export function loadTaxonomy() {
  const path = join(
    REPO,
    "contracts",
    "expect-root-cause-taxonomy",
    "1.0",
    "taxonomy.json"
  );
  return JSON.parse(readFileSync(path, "utf8"));
}

export function repoRoot() {
  return REPO;
}
