#!/usr/bin/env node
/**
 * Cloudflare Pages に AI_BASE_URL（および任意で Access / API key）を設定する。
 *
 * 前提:
 *   - CLOUDFLARE_API_TOKEN が環境変数にある（Pages Edit 権限）
 *   - または事前に `npx wrangler login`
 *
 * 使い方:
 *   node scripts/set-pages-ai-url.mjs https://ai.example.com
 *   node scripts/set-pages-ai-url.mjs https://ai.example.com --with-access
 *
 * EC2 上の Python は 127.0.0.1:8000 + cloudflared。ここには Tunnel の https URL を渡す。
 */
import { spawnSync } from "node:child_process";

const project = process.env.CF_PAGES_PROJECT || "keiba-single-ai";
const args = process.argv.slice(2).filter((a) => a !== "--with-access");
const withAccess = process.argv.includes("--with-access");
const url = String(args[0] || "").replace(/\/$/, "");

if (!url || !/^https:\/\//i.test(url)) {
  console.error("Usage: node scripts/set-pages-ai-url.mjs https://<tunnel-ai-hostname>");
  process.exit(1);
}

function put(name, value) {
  const r = spawnSync(
    "npx",
    ["wrangler", "pages", "secret", "put", name, "--project-name", project],
    {
      input: value,
      encoding: "utf8",
      shell: true,
      stdio: ["pipe", "inherit", "inherit"],
    }
  );
  if (r.status !== 0) process.exit(r.status || 1);
  console.log("OK:", name);
}

put("AI_BASE_URL", url);

if (process.env.AI_API_KEY) put("AI_API_KEY", process.env.AI_API_KEY);
if (withAccess) {
  if (!process.env.CF_ACCESS_CLIENT_ID || !process.env.CF_ACCESS_CLIENT_SECRET) {
    console.error("--with-access requires CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET env");
    process.exit(1);
  }
  put("CF_ACCESS_CLIENT_ID", process.env.CF_ACCESS_CLIENT_ID);
  put("CF_ACCESS_CLIENT_SECRET", process.env.CF_ACCESS_CLIENT_SECRET);
}

console.log(`
Next:
  1) Cloudflare Dashboard → Pages → ${project} → Deployments で最新を確認
  2) curl -s https://keiba-single-ai.pages.dev/api/predictions | head
     → meta.provider should be "python"
     → meta.items[].engine_source should be real_ai or mock_fallback (not bff_mock)
  3) EC2: AI_ENGINE=real in /opt/expect-ai/shared/.env then systemctl restart expect-ai
`);
