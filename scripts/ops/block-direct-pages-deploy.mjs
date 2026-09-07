#!/usr/bin/env node
/** Blocks ungated Cloudflare Pages deploy. Always fails — use deploy:pages:safe. */
console.error(`
BLOCKED: direct Pages deploy is forbidden.

Production deploy entry point:
  npm run deploy:pages:safe

This runs deploy:pages:gate first, then deploys only if the gate passes.

Emergency raw deploy (requires explicit acknowledgment):
  DEPLOY_PAGES_OVERRIDE=1 npm run deploy:pages:raw
`);
process.exit(1);
