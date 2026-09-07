#!/usr/bin/env node
/** Runs raw Pages deploy after gate (sets DEPLOY_PAGES_OVERRIDE=1). */
import { spawnSync } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");
const env = { ...process.env, DEPLOY_PAGES_OVERRIDE: "1" };
const r = spawnSync("npm run deploy:pages:raw", {
  cwd: ROOT,
  env,
  shell: true,
  stdio: "inherit",
});
process.exit(r.status ?? 1);
