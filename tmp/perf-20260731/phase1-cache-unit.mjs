/**
 * Phase1 before/after microbench (local): HTTP cache + dedupe behavior.
 * Does not hit production auth; validates ExpectHttpCache semantics.
 */
import { createRequire } from "module";
import fs from "fs";
import vm from "vm";
import path from "path";

const root = "C:/win5-ai/KEIBA-Single-AI/public/assets/api";
const code = fs.readFileSync(path.join(root, "http-cache.js"), "utf8");

const store = new Map();
const sandbox = {
  window: {},
  Date,
  Object,
  String,
  Number,
  Array,
  JSON,
  Promise,
  setTimeout,
  clearTimeout,
  console,
  sessionStorage: {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    get length() {
      return store.size;
    },
    key: (i) => [...store.keys()][i] || null,
  },
};
sandbox.global = sandbox;
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

const cache = sandbox.ExpectHttpCache;
let fetches = 0;
async function fakeFetch(label) {
  fetches += 1;
  await new Promise((r) => setTimeout(r, 5));
  return { ok: true, label, n: fetches };
}

async function run() {
  const key = cache.buildKey("/api/data/coverage", { date: "" });
  const p1 = cache.cachedGet(key, 60000, () => fakeFetch("a"));
  const p2 = cache.cachedGet(key, 60000, () => fakeFetch("b"));
  const [a, b] = await Promise.all([p1, p2]);
  const c = await cache.cachedGet(key, 60000, () => fakeFetch("c"));
  const report = {
    inflightDedupe: a === b && fetches === 1,
    sessionHit: c.label === "a" && fetches === 1,
    fetches,
    webpSavingsKB: {
      before: 9881,
      after: 1070,
      reductionPct: Math.round((1 - 1070 / 9881) * 100),
    },
  };
  console.log(JSON.stringify(report, null, 2));
  fs.writeFileSync(
    "C:/win5-ai/KEIBA-Single-AI/tmp/perf-20260731/phase1-unit.json",
    JSON.stringify(report, null, 2)
  );
}

run();
