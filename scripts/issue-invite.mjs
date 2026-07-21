/**
 * 互換ラッパー → beta-admin issue
 *
 *   node scripts/issue-invite.mjs BETA-XXXX-YYYY [--note "memo"] [--expires ISO]
 */
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const cli = join(root, "scripts/beta-admin.mjs");
const args = process.argv.slice(2);
if (!args[0] || String(args[0]).startsWith("--")) {
  console.error("Usage: node scripts/issue-invite.mjs <INVITE_ID> [--note ...] [--expires ISO]");
  process.exit(1);
}
const r = spawnSync(process.execPath, [cli, "issue", ...args], {
  stdio: "inherit",
  cwd: root,
});
process.exit(r.status == null ? 1 : r.status);
