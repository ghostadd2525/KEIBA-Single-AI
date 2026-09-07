#!/usr/bin/env node
/** Requires DEPLOY_PAGES_OVERRIDE=1 before raw wrangler deploy. */
import process from "process";

if (process.env.DEPLOY_PAGES_OVERRIDE !== "1") {
  console.error(`
BLOCKED: deploy:pages:raw requires DEPLOY_PAGES_OVERRIDE=1.

Use the gated entry point:
  npm run deploy:pages:safe
`);
  process.exit(1);
}

process.exit(0);
