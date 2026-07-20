#!/usr/bin/env node
/**
 * Phase OPS-Monitor — ローカル開発用（wrangler dev 非依存）
 *
 * Python AI のみをプローブ。Tunnel / systemd はスキップ。
 *
 * Usage:
 *   npm run monitor:dev
 *   PYTHON_HEALTH_URL=http://127.0.0.1:8000/health npm run monitor:dev
 */
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const prodScript = join(__dirname, "monitor-prod.mjs");

const env = {
  ...process.env,
  EXPECT_OPS_ROOT: process.env.EXPECT_OPS_ROOT || join(__dirname, "..", "..", "var", "ops-dev"),
  BFF_MONITOR_URL: process.env.BFF_MONITOR_URL || "",
  AI_TUNNEL_HEALTH_URL: "",
};

const r = spawnSync(process.execPath, [prodScript], {
  env,
  stdio: "inherit",
});

process.exit(r.status ?? 1);
