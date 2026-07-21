/**
 * Phase10 — β運営 CLI（管理UIなし）
 *
 *   node scripts/beta-admin.mjs <command> ...
 *
 * Commands:
 *   issue <INVITE_ID> [--note ...] [--expires ISO]
 *   list [--status issued|activated|disabled|expired]
 *   disable <INVITE_ID> | --user <USER_ID>
 *   enable  <INVITE_ID> | --user <USER_ID>
 *   show <INVITE_ID>
 *   reset-password <USER_ID> <NEW_PASSWORD>
 *
 * 永続化: public/data/invitations.json / users.json
 * 監査: logs/audit/beta-audit.jsonl
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const root = process.env.BETA_ADMIN_ROOT
  ? String(process.env.BETA_ADMIN_ROOT)
  : join(dirname(fileURLToPath(import.meta.url)), "..");
const invitesPath = join(root, "public/data/invitations.json");
const usersPath = join(root, "public/data/users.json");
const auditPath = join(root, "logs/audit/beta-audit.jsonl");
const DEFAULT_SALT = "expect-beta-v1";

function usage(code = 1) {
  console.error(`Usage:
  node scripts/beta-admin.mjs issue <INVITE_ID> [--note ...] [--expires ISO]
  node scripts/beta-admin.mjs list [--status STATUS]
  node scripts/beta-admin.mjs disable <INVITE_ID>
  node scripts/beta-admin.mjs disable --user <USER_ID>
  node scripts/beta-admin.mjs enable <INVITE_ID>
  node scripts/beta-admin.mjs enable --user <USER_ID>
  node scripts/beta-admin.mjs show <INVITE_ID>
  node scripts/beta-admin.mjs reset-password <USER_ID> <NEW_PASSWORD>`);
  process.exit(code);
}

function normalizeInviteId(id) {
  return String(id || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");
}

function readJson(path, fallback) {
  if (!existsSync(path)) return fallback;
  return JSON.parse(readFileSync(path, "utf8"));
}

function writeJson(path, doc) {
  writeFileSync(path, JSON.stringify(doc, null, 2) + "\n", "utf8");
}

function hashPassword(password, salt = DEFAULT_SALT) {
  const raw = String(salt) + ":" + String(password);
  const hex = createHash("sha256").update(raw, "utf8").digest("hex");
  return `sha256$${salt}$${hex}`;
}

function audit(type, { ok = true, target = null, detail = {} } = {}) {
  mkdirSync(dirname(auditPath), { recursive: true });
  const line = {
    ts: new Date().toISOString(),
    type,
    ok,
    actor: "cli",
    target,
    detail,
    source: "cli",
  };
  writeFileSync(auditPath, JSON.stringify(line) + "\n", {
    flag: "a",
    encoding: "utf8",
  });
  return line;
}

function loadInvites() {
  const doc = readJson(invitesPath, {
    schema_version: "expect-invitation/1.0",
    invitations: [],
  });
  doc.invitations = Array.isArray(doc.invitations) ? doc.invitations : [];
  return doc;
}

function loadUsers() {
  const doc = readJson(usersPath, {
    schema_version: "expect-user/1.0",
    users: [],
  });
  doc.users = Array.isArray(doc.users) ? doc.users : [];
  return doc;
}

function findInvite(doc, inviteId) {
  const id = normalizeInviteId(inviteId);
  return doc.invitations.find((x) => normalizeInviteId(x.invite_id) === id) || null;
}

function findUser(doc, userId) {
  const id = String(userId || "").trim();
  return doc.users.find((x) => String(x.user_id || "") === id) || null;
}

function cmdIssue(args) {
  const inviteId = normalizeInviteId(args[0]);
  if (!inviteId || inviteId.startsWith("--")) usage();
  if (inviteId.length < 4) {
    console.error("invite_id too short");
    process.exit(1);
  }
  let note = null;
  let expires_at = null;
  for (let i = 1; i < args.length; i++) {
    if (args[i] === "--note") note = args[++i] || null;
    if (args[i] === "--expires") expires_at = args[++i] || null;
  }
  const doc = loadInvites();
  if (findInvite(doc, inviteId)) {
    console.error("already exists:", inviteId);
    process.exit(2);
  }
  const row = {
    invite_id: inviteId,
    status: "issued",
    issued_at: new Date().toISOString(),
    expires_at,
    activated_at: null,
    activated_user_id: null,
    note,
  };
  doc.invitations.push(row);
  writeJson(invitesPath, doc);
  audit("invitation_issued", { target: inviteId, detail: { note, expires_at } });
  console.log(JSON.stringify({ ok: true, invite: row }, null, 2));
}

function cmdList(args) {
  let status = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--status") status = String(args[++i] || "").toLowerCase();
  }
  const doc = loadInvites();
  let rows = doc.invitations;
  if (status) rows = rows.filter((x) => String(x.status || "").toLowerCase() === status);
  const out = rows.map((x) => ({
    invite_id: x.invite_id,
    status: x.status,
    issued_at: x.issued_at,
    expires_at: x.expires_at,
    activated_user_id: x.activated_user_id,
    note: x.note,
  }));
  console.log(JSON.stringify({ ok: true, count: out.length, invitations: out }, null, 2));
}

function cmdDisable(args) {
  if (args[0] === "--user") {
    const userId = String(args[1] || "").trim();
    if (!userId) usage();
    const doc = loadUsers();
    const user = findUser(doc, userId);
    if (!user) {
      console.error("user not found:", userId);
      process.exit(2);
    }
    user.status = "disabled";
    writeJson(usersPath, doc);
    audit("account_disabled", { target: userId });
    console.log(JSON.stringify({ ok: true, user: { user_id: user.user_id, status: user.status } }, null, 2));
    return;
  }
  const inviteId = normalizeInviteId(args[0]);
  if (!inviteId) usage();
  const doc = loadInvites();
  const inv = findInvite(doc, inviteId);
  if (!inv) {
    console.error("invite not found:", inviteId);
    process.exit(2);
  }
  if (inv.status === "expired") {
    console.error("cannot disable expired invite");
    process.exit(3);
  }
  inv.status = "disabled";
  writeJson(invitesPath, doc);
  audit("invitation_disabled", { target: inviteId });
  console.log(JSON.stringify({ ok: true, invite: inv }, null, 2));
}

function cmdEnable(args) {
  if (args[0] === "--user") {
    const userId = String(args[1] || "").trim();
    if (!userId) usage();
    const doc = loadUsers();
    const user = findUser(doc, userId);
    if (!user) {
      console.error("user not found:", userId);
      process.exit(2);
    }
    user.status = "active";
    writeJson(usersPath, doc);
    audit("account_enabled", { target: userId });
    console.log(JSON.stringify({ ok: true, user: { user_id: user.user_id, status: user.status } }, null, 2));
    return;
  }
  const inviteId = normalizeInviteId(args[0]);
  if (!inviteId) usage();
  const doc = loadInvites();
  const inv = findInvite(doc, inviteId);
  if (!inv) {
    console.error("invite not found:", inviteId);
    process.exit(2);
  }
  if (inv.status === "expired") {
    console.error("cannot enable expired invite");
    process.exit(3);
  }
  if (inv.status === "disabled") {
    inv.status = inv.activated_user_id ? "activated" : "issued";
  }
  writeJson(invitesPath, doc);
  audit("invitation_enabled", { target: inviteId, detail: { status: inv.status } });
  console.log(JSON.stringify({ ok: true, invite: inv }, null, 2));
}

function cmdShow(args) {
  const inviteId = normalizeInviteId(args[0]);
  if (!inviteId) usage();
  const invDoc = loadInvites();
  const inv = findInvite(invDoc, inviteId);
  if (!inv) {
    console.error("invite not found:", inviteId);
    process.exit(2);
  }
  let user = null;
  if (inv.activated_user_id) {
    user = findUser(loadUsers(), inv.activated_user_id);
    if (user) {
      user = {
        user_id: user.user_id,
        status: user.status,
        display_name: user.display_name,
        created_at: user.created_at,
        terms_version: user.terms_version,
      };
    }
  }
  console.log(JSON.stringify({ ok: true, invite: inv, user }, null, 2));
}

function cmdResetPassword(args) {
  const userId = String(args[0] || "").trim();
  const password = String(args[1] || "");
  if (!userId || !password) usage();
  if (password.length < 8) {
    console.error("password must be at least 8 characters");
    process.exit(1);
  }
  const doc = loadUsers();
  const user = findUser(doc, userId);
  if (!user) {
    console.error("user not found:", userId);
    process.exit(2);
  }
  user.password_hash = hashPassword(password);
  writeJson(usersPath, doc);
  audit("password_reset", { target: userId });
  console.log(
    JSON.stringify(
      { ok: true, user_id: user.user_id, password_reset: true, note: "redeploy / sync ASSETS after change" },
      null,
      2
    )
  );
}

const [cmd, ...rest] = process.argv.slice(2);
if (!cmd || cmd === "-h" || cmd === "--help") usage(cmd ? 0 : 1);

const map = {
  issue: cmdIssue,
  list: cmdList,
  disable: cmdDisable,
  enable: cmdEnable,
  show: cmdShow,
  "reset-password": cmdResetPassword,
};

if (!map[cmd]) {
  console.error("unknown command:", cmd);
  usage();
}
map[cmd](rest);
