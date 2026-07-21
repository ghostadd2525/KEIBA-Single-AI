#!/usr/bin/env node
/**
 * Cloudflare Pages に PI_BASE_URL を設定する。
 * 本番: ai.expect-keiba.com トンネル経由で /v1/races → PI :8081
 */
import { spawnSync } from "node:child_process";

const project = process.env.CF_PAGES_PROJECT || "keiba-single-ai";
const url = String(process.argv[2] || "https://ai.expect-keiba.com").replace(/\/$/, "");

function put(name, value) {
  const r = spawnSync(
    "npx",
    ["wrangler", "pages", "secret", "put", name, "--project-name", project],
    { input: value, encoding: "utf8", shell: true, stdio: ["pipe", "inherit", "inherit"] }
  );
  if (r.status !== 0) process.exit(r.status || 1);
  console.log("OK:", name, "=", url);
}

put("PI_BASE_URL", url);
console.log("PI /v1/races は Tunnel path ルールで :8081 に転送されている必要があります。");
