import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ROOT, readJson } from "../helpers/load.mjs";
import { createHash } from "node:crypto";

const cli = join(ROOT, "scripts/beta-admin.mjs");

function hashPassword(password, salt = "expect-beta-v1") {
  const hex = createHash("sha256").update(`${salt}:${password}`, "utf8").digest("hex");
  return `sha256$${salt}$${hex}`;
}

function runBeta(root, args) {
  return spawnSync(process.execPath, [cli, ...args], {
    encoding: "utf8",
    env: { ...process.env, BETA_ADMIN_ROOT: root },
  });
}

describe("Phase10 beta.json", () => {
  it("config/beta.json と public/config/beta.json が同期キーを持つ", () => {
    const a = readJson("config/beta.json");
    const b = readJson("public/config/beta.json");
    for (const key of [
      "schema_version",
      "beta_name",
      "maintenance_mode",
      "terms_version",
      "invitation_required",
      "max_concurrent_sessions",
    ]) {
      assert.equal(a[key], b[key], key);
    }
    assert.equal(a.schema_version, "expect-beta-config/1.0");
    assert.equal(typeof a.beta_name, "string");
    assert.equal(typeof a.maintenance_mode, "boolean");
    assert.equal(typeof a.invitation_required, "boolean");
    assert.ok(a.audit && typeof a.audit.enabled === "boolean");
  });
});

describe("Phase10 auditLog helpers", () => {
  it("AuditEvent に必須種別がある", async () => {
    const { pathToFileURL } = await import("node:url");
    const m = await import(pathToFileURL(join(ROOT, "functions/_lib/auditLog.js")).href);
    const E = m.AuditEvent;
    for (const k of [
      "LOGIN_SUCCESS",
      "LOGIN_FAILURE",
      "INVITATION_USED",
      "SETUP_COMPLETE",
      "ACCOUNT_DISABLED",
      "PREDICTION_USED",
      "ANALYSIS_USED",
      "KAOBA_USED",
    ]) {
      assert.ok(E[k], k);
    }
    const line = m.writeAudit(null, { type: E.LOGIN_SUCCESS, actor: "u1" });
    assert.equal(line.type, "login_success");
    assert.equal(line.ok, true);
    assert.ok(line.ts);
  });
});

describe("Phase10 beta-admin CLI", () => {
  let root;

  before(() => {
    root = mkdtempSync(join(tmpdir(), "beta-admin-"));
    mkdirSync(join(root, "public/data"), { recursive: true });
    mkdirSync(join(root, "logs/audit"), { recursive: true });
    writeFileSync(
      join(root, "public/data/invitations.json"),
      JSON.stringify({ schema_version: "expect-invitation/1.0", invitations: [] }, null, 2)
    );
    writeFileSync(
      join(root, "public/data/users.json"),
      JSON.stringify(
        {
          schema_version: "expect-user/1.0",
          users: [
            {
              user_id: "cli-user",
              password_hash: hashPassword("old-password"),
              display_name: "cli-user",
              invite_id: "BETA-CLI-TEST01",
              status: "active",
              created_at: "2026-07-10T12:00:00+09:00",
              terms_version: "2026-07-19",
              terms_accepted_at: "2026-07-10T12:00:00+09:00",
            },
          ],
        },
        null,
        2
      )
    );
  });

  after(() => {
    if (root && existsSync(root)) rmSync(root, { recursive: true, force: true });
  });

  it("issue / list / show / disable / enable", () => {
    let r = runBeta(root, ["issue", "BETA-CLI-TEST01", "--note", "t"]);
    assert.equal(r.status, 0, r.stderr);
    const issued = JSON.parse(r.stdout);
    assert.equal(issued.invite.invite_id, "BETA-CLI-TEST01");
    assert.equal(issued.invite.status, "issued");

    r = runBeta(root, ["list", "--status", "issued"]);
    assert.equal(r.status, 0, r.stderr);
    const listed = JSON.parse(r.stdout);
    assert.equal(listed.count, 1);

    r = runBeta(root, ["show", "BETA-CLI-TEST01"]);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(JSON.parse(r.stdout).invite.status, "issued");

    r = runBeta(root, ["disable", "BETA-CLI-TEST01"]);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(JSON.parse(r.stdout).invite.status, "disabled");

    r = runBeta(root, ["enable", "BETA-CLI-TEST01"]);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(JSON.parse(r.stdout).invite.status, "issued");
  });

  it("disable --user / enable --user / reset-password + audit JSONL", () => {
    let r = runBeta(root, ["disable", "--user", "cli-user"]);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(JSON.parse(r.stdout).user.status, "disabled");

    r = runBeta(root, ["enable", "--user", "cli-user"]);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(JSON.parse(r.stdout).user.status, "active");

    r = runBeta(root, ["reset-password", "cli-user", "new-pass-99"]);
    assert.equal(r.status, 0, r.stderr);

    const users = JSON.parse(readFileSync(join(root, "public/data/users.json"), "utf8"));
    assert.equal(users.users[0].password_hash, hashPassword("new-pass-99"));

    const audit = readFileSync(join(root, "logs/audit/beta-audit.jsonl"), "utf8")
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));
    const types = new Set(audit.map((x) => x.type));
    assert.ok(types.has("invitation_issued"));
    assert.ok(types.has("account_disabled"));
    assert.ok(types.has("password_reset"));
    for (const line of audit) {
      assert.ok(line.ts);
      assert.ok(line.type);
      assert.equal(line.source, "cli");
    }
  });
});

describe("Phase10 docs", () => {
  it("運営・チェックリスト・成果物ドキュメントがある", () => {
    assert.ok(existsSync(join(ROOT, "docs/beta-operation.md")));
    assert.ok(existsSync(join(ROOT, "docs/beta-security-checklist.md")));
    assert.ok(existsSync(join(ROOT, "docs/phase10-beta-release-preparation.md")));
  });
});
