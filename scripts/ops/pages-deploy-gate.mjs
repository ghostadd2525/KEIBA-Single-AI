#!/usr/bin/env node
/**
 * Cloudflare Pages deploy gate — compare live Production baseline vs candidate public/.
 *
 * Usage:
 *   node scripts/ops/pages-deploy-gate.mjs \
 *     --baseline https://2221d90e.keiba-single-ai.pages.dev \
 *     --candidate public \
 *     --allow assets/api/odds-chart.js odds.html
 *
 * Exit 0 only when:
 *   DEPLOY_CANDIDATE_INCLUDES_PREVIOUS_PROD_FIXES = YES (no regressions vs baseline except allowlist)
 *   UNEXPECTED_FILE_REGRESSIONS = 0
 */
import crypto from "crypto";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "../..");

function parseArgs(argv) {
  const out = {
    baseline: "",
    candidate: "public",
    allow: [],
    project: "keiba-single-ai",
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--baseline") out.baseline = argv[++i] || "";
    else if (a === "--candidate") out.candidate = argv[++i] || "public";
    else if (a === "--allow") out.allow = (argv[++i] || "").split(",").map((s) => s.trim()).filter(Boolean);
    else if (a === "--project") out.project = argv[++i] || out.project;
  }
  return out;
}

function hashText(t) {
  return crypto.createHash("sha256").update(Buffer.from(t, "utf8")).digest("hex");
}

function walk(dir, base = "") {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const rel = base ? base + "/" + f.name : f.name;
    const p = path.join(dir, f.name);
    if (f.isDirectory()) out.push(...walk(p, rel));
    else out.push(rel.replace(/\\/g, "/"));
  }
  return out;
}

async function fetchLiveDeploymentUrl(project) {
  try {
    const { execSync } = await import("child_process");
    const out = execSync(
      `npx wrangler pages deployment list --project-name=${project} 2>nul`,
      { encoding: "utf8", cwd: ROOT }
    );
    const m = out.match(/https:\/\/[a-f0-9]+\.keiba-single-ai\.pages\.dev/);
    return m ? m[0] : "";
  } catch {
    return "";
  }
}

async function fetchHash(baseUrl, rel) {
  const url = baseUrl.replace(/\/$/, "") + "/" + rel.split("/").map(encodeURIComponent).join("/");
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) return null;
  const t = await r.text();
  return { hash: hashText(t), len: t.length };
}

async function main() {
  const args = parseArgs(process.argv);
  let baseline = args.baseline;
  if (!baseline) {
    baseline = await fetchLiveDeploymentUrl(args.project);
    if (!baseline) {
      console.error("FAIL: --baseline required (could not detect live deployment)");
      process.exit(2);
    }
    console.log("Using live baseline:", baseline);
  }

  const candRoot = path.isAbsolute(args.candidate)
    ? args.candidate
    : path.join(ROOT, args.candidate);
  const allow = new Set(args.allow.map((p) => p.replace(/\\/g, "/")));

  const candFiles = new Set(walk(candRoot).filter((rel) => !rel.startsWith("_")));
  const baselineRoot = path.join(ROOT, "tmp", ".gate-baseline-cache");
  fs.mkdirSync(baselineRoot, { recursive: true });

  // Build baseline manifest from live deployment (fail-closed if baseline unreachable).
  const baselineManifestPath = path.join(baselineRoot, "manifest.txt");
  let baselineFiles = [];
  if (fs.existsSync(baselineManifestPath)) {
    baselineFiles = fs.readFileSync(baselineManifestPath, "utf8").trim().split("\n").filter(Boolean);
  } else {
    const seed = walk(candRoot).filter((rel) => !rel.startsWith("_"));
    for (const rel of seed) {
      const b = await fetchHash(baseline, rel);
      if (b) baselineFiles.push(rel);
    }
    fs.writeFileSync(baselineManifestPath, baselineFiles.join("\n"), "utf8");
  }

  const changed = [];
  const same = [];
  const missingOnBaseline = [];
  const deletedFromCandidate = [];

  for (const rel of candFiles) {
    const local = fs.readFileSync(path.join(candRoot, rel), "utf8");
    const lh = hashText(local);
    const b = await fetchHash(baseline, rel);
    if (!b) {
      missingOnBaseline.push(rel);
      continue;
    }
    if (lh === b.hash) same.push(rel);
    else changed.push({ rel, baseLen: b.len, candLen: local.length });
  }

  for (const rel of baselineFiles) {
    if (!candFiles.has(rel)) deletedFromCandidate.push(rel);
  }

  const unexpected = changed.filter((x) => !allow.has(x.rel)).map((x) => x.rel);
  const ok =
    unexpected.length === 0 &&
    missingOnBaseline.length === 0 &&
    deletedFromCandidate.length === 0;

  const report = {
    baseline,
    candidate: candRoot,
    allowlist: [...allow],
    same_count: same.length,
    changed_count: changed.length,
    ACTUAL_CHANGED_FILES: changed.map((x) => x.rel),
    UNEXPECTED_FILE_REGRESSIONS: unexpected.length,
    UNEXPECTED_LIST: unexpected,
    missing_on_baseline: missingOnBaseline.length,
    MISSING_ON_BASELINE_LIST: missingOnBaseline,
    deleted_from_candidate: deletedFromCandidate.length,
    DELETED_FROM_CANDIDATE_LIST: deletedFromCandidate,
    DEPLOY_CANDIDATE_INCLUDES_PREVIOUS_PROD_FIXES: ok ? "YES" : "NO",
    READY_FOR_DEPLOY: ok ? "YES" : "NO",
    FAIL_CLOSED: "YES",
    DIRTY_PRODUCTION_DEPLOY: "FORBIDDEN unless this gate passes",
  };

  console.log(JSON.stringify(report, null, 2));
  process.exit(ok ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
