#!/usr/bin/env node
/**
 * Pre-deploy / CI check: Production + stub auth contradiction.
 *
 * Fails when:
 *   EXPECT_ENV=production|prod
 *   AND AUTH_MODE=stub (default)
 *   AND ALLOW_STUB_AUTH != 1
 *
 * Usage:
 *   node scripts/ops/check-production-auth.mjs
 *   node scripts/ops/check-production-auth.mjs --env-file infra/cloudflare/env/production.env.example
 *   npm run check:auth:prod
 */
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { evaluateProductionAuthConfig } from "../../functions/_lib/productionAuthGuard.js";

function parseArgs(argv) {
  const out = { envFile: "", wrangler: "wrangler.toml", json: false };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--env-file" && argv[i + 1]) {
      out.envFile = argv[++i];
    } else if (argv[i] === "--wrangler" && argv[i + 1]) {
      out.wrangler = argv[++i];
    } else if (argv[i] === "--json") {
      out.json = true;
    }
  }
  return out;
}

function parseEnvFile(text) {
  const env = {};
  for (const line of String(text || "").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i < 0) continue;
    const k = t.slice(0, i).trim();
    let v = t.slice(i + 1).trim();
    if (
      (v.startsWith('"') && v.endsWith('"')) ||
      (v.startsWith("'") && v.endsWith("'"))
    ) {
      v = v.slice(1, -1);
    }
    env[k] = v;
  }
  return env;
}

function parseWranglerVars(text) {
  const env = {};
  const lines = String(text || "").split(/\r?\n/);
  let inVars = false;
  for (const line of lines) {
    const t = line.trim();
    if (t === "[vars]") {
      inVars = true;
      continue;
    }
    if (t.startsWith("[")) {
      inVars = false;
      continue;
    }
    if (!inVars || !t || t.startsWith("#")) continue;
    const m = /^([A-Za-z0-9_]+)\s*=\s*"([^"]*)"/.exec(t);
    if (m) env[m[1]] = m[2];
  }
  return env;
}

function main() {
  const args = parseArgs(process.argv);
  const merged = {
    EXPECT_ENV: process.env.EXPECT_ENV || "",
    AUTH_MODE: process.env.AUTH_MODE || "",
    ALLOW_STUB_AUTH: process.env.ALLOW_STUB_AUTH || "",
  };

  const wranglerPath = resolve(process.cwd(), args.wrangler);
  if (existsSync(wranglerPath)) {
    Object.assign(merged, parseWranglerVars(readFileSync(wranglerPath, "utf8")));
  }

  if (args.envFile) {
    const p = resolve(process.cwd(), args.envFile);
    if (!existsSync(p)) {
      console.error("ENV_FILE_MISSING", p);
      process.exit(2);
    }
    Object.assign(merged, parseEnvFile(readFileSync(p, "utf8")));
  }

  // Process env wins for CI overrides
  if (process.env.EXPECT_ENV) merged.EXPECT_ENV = process.env.EXPECT_ENV;
  if (process.env.AUTH_MODE) merged.AUTH_MODE = process.env.AUTH_MODE;
  if (process.env.ALLOW_STUB_AUTH != null && process.env.ALLOW_STUB_AUTH !== "") {
    merged.ALLOW_STUB_AUTH = process.env.ALLOW_STUB_AUTH;
  }

  const result = evaluateProductionAuthConfig(merged);
  const report = {
    ok: !result.fatal,
    check: "production_stub_auth",
    ...result,
    sources: {
      wrangler: existsSync(wranglerPath) ? args.wrangler : null,
      env_file: args.envFile || null,
    },
  };

  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else if (result.fatal) {
    console.error("FATAL", result.code);
    console.error(result.message);
    console.error(
      `EXPECT_ENV=${result.expect_env} AUTH_MODE=${result.auth_mode} ALLOW_STUB_AUTH=${result.allow_stub_auth}`
    );
    console.error(
      "Remediation: set ALLOW_STUB_AUTH=1 in wrangler [vars] / Pages, or stop using AUTH_MODE=stub in production."
    );
  } else {
    console.log(
      "OK production auth config",
      `EXPECT_ENV=${result.expect_env}`,
      `AUTH_MODE=${result.auth_mode}`,
      `ALLOW_STUB_AUTH=${result.allow_stub_auth}`
    );
  }

  process.exit(result.fatal ? 1 : 0);
}

main();
