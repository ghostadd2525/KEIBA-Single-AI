import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { ROOT } from "../helpers/load.mjs";

async function load(rel) {
  return import(pathToFileURL(join(ROOT, rel)).href);
}

describe("Phase OPS-1A roles", () => {
  it("ADMIN / OPS / DEVELOPER は bypass、USER は不可", async () => {
    const { Role, canBypassOpsMode, normalizeRole } = await load("functions/_lib/roles.js");
    assert.equal(canBypassOpsMode(Role.USER), false);
    assert.equal(canBypassOpsMode(Role.ADMIN), true);
    assert.equal(canBypassOpsMode(Role.OPS), true);
    assert.equal(canBypassOpsMode(Role.DEVELOPER), true);
    assert.equal(normalizeRole("administrator"), Role.ADMIN);
    assert.equal(normalizeRole("guest"), Role.USER);
  });
});

describe("Phase OPS-1A opsMode evaluateOpsAccess", () => {
  it("CLOSED で USER は拒否、ADMIN は許可", async () => {
    const { OpsMode, evaluateOpsAccess } = await load("functions/_lib/opsMode.js");
    const userDenied = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode: OpsMode.CLOSED,
      role: "USER",
    });
    assert.equal(userDenied.allow, false);
    assert.equal(userDenied.reason, "ops_closed");

    const adminOk = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode: OpsMode.CLOSED,
      role: "ADMIN",
    });
    assert.equal(adminOk.allow, true);
    assert.equal(adminOk.reason, "role_bypass");
  });

  it("権限判定が公開制御より先（CLOSED でも bypass ロールは通る）", async () => {
    const { OpsMode, evaluateOpsAccess } = await load("functions/_lib/opsMode.js");
    const r = evaluateOpsAccess({
      pathname: "/api/conversation/chat",
      opsMode: OpsMode.CLOSED,
      role: "DEVELOPER",
      bypassOpsMode: true,
    });
    assert.equal(r.allow, true);
    assert.equal(r.reason, "role_bypass");
  });

  it("OPS-Monitor / health は CLOSED でも exempt", async () => {
    const { OpsMode, evaluateOpsAccess } = await load("functions/_lib/opsMode.js");
    for (const path of ["/api/ops/monitor", "/api/health", "/api/auth/login"]) {
      const r = evaluateOpsAccess({
        pathname: path,
        opsMode: OpsMode.CLOSED,
        role: "USER",
      });
      assert.equal(r.allow, true, path);
      assert.equal(r.reason, "exempt_path", path);
    }
  });

  it("PUBLIC では USER も許可", async () => {
    const { OpsMode, evaluateOpsAccess } = await load("functions/_lib/opsMode.js");
    const r = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode: OpsMode.PUBLIC,
      role: "USER",
    });
    assert.equal(r.allow, true);
    assert.equal(r.reason, "ops_public");
  });

  it("maintenance_mode から CLOSED を導出", async () => {
    const { resolveOpsMode, OpsMode } = await load("functions/_lib/opsMode.js");
    assert.equal(resolveOpsMode({ maintenance_mode: true }), OpsMode.CLOSED);
    assert.equal(resolveOpsMode({ maintenance_mode: false }), OpsMode.PUBLIC);
    assert.equal(resolveOpsMode({ ops_mode: "CLOSED", maintenance_mode: false }), OpsMode.CLOSED);
  });
});

describe("Phase OPS-1A authorization resolve", () => {
  it("profile.role=ADMIN を優先", async () => {
    const { resolveAuthorization } = await load("functions/_lib/authorization.js");
    const { _upsertUserForPersist, _resetUserRuntimeForTests } = await load(
      "functions/_lib/userRepository.js"
    );
    _resetUserRuntimeForTests();
    _upsertUserForPersist({
      user_id: "admin1",
      password_hash: "x",
      role: "ADMIN",
      status: "active",
    });
    const context = {
      data: { user: { id: "admin1", purpose: "access" } },
      env: {},
    };
    const authz = await resolveAuthorization(context, {});
    assert.equal(authz.role, "ADMIN");
    assert.equal(authz.bypass_ops_mode, true);
    assert.equal(authz.source, "user_profile");
    _resetUserRuntimeForTests();
  });

  it("一般ユーザーは bypass なし", async () => {
    const { resolveAuthorization } = await load("functions/_lib/authorization.js");
    const { _upsertUserForPersist, _resetUserRuntimeForTests } = await load(
      "functions/_lib/userRepository.js"
    );
    _resetUserRuntimeForTests();
    _upsertUserForPersist({
      user_id: "user1",
      password_hash: "x",
      role: "USER",
      status: "active",
    });
    const context = {
      data: { user: { id: "user1", purpose: "access" } },
      env: {},
    };
    const authz = await resolveAuthorization(context, {});
    assert.equal(authz.role, "USER");
    assert.equal(authz.bypass_ops_mode, false);
    _resetUserRuntimeForTests();
  });

  it("admin_user_ids allowlist で ADMIN 昇格", async () => {
    const { resolveAuthorization } = await load("functions/_lib/authorization.js");
    const { _resetUserRuntimeForTests } = await load("functions/_lib/userRepository.js");
    _resetUserRuntimeForTests();
    const context = {
      data: { user: { id: "ops-boss", purpose: "access" } },
      env: {},
    };
    const authz = await resolveAuthorization(context, {
      admin_user_ids: ["ops-boss"],
    });
    assert.equal(authz.role, "ADMIN");
    assert.equal(authz.bypass_ops_mode, true);
    assert.equal(authz.source, "admin_allowlist");
    _resetUserRuntimeForTests();
  });
});

describe("Phase OPS-1A middleware integration (admin vs user)", () => {
  it("CLOSED 時: USER ブロック / ADMIN bypass の判定が一致", async () => {
    const { OpsMode, evaluateOpsAccess } = await load("functions/_lib/opsMode.js");
    const { resolveAuthorization } = await load("functions/_lib/authorization.js");
    const { _upsertUserForPersist, _resetUserRuntimeForTests } = await load(
      "functions/_lib/userRepository.js"
    );
    _resetUserRuntimeForTests();
    _upsertUserForPersist({ user_id: "u", role: "USER", password_hash: "x", status: "active" });
    _upsertUserForPersist({ user_id: "a", role: "ADMIN", password_hash: "x", status: "active" });

    const beta = { maintenance_mode: true };
    const opsMode = OpsMode.CLOSED;

    const userCtx = { data: { user: { id: "u" } }, env: {} };
    const adminCtx = { data: { user: { id: "a" } }, env: {} };
    const userAuthz = await resolveAuthorization(userCtx, beta);
    const adminAuthz = await resolveAuthorization(adminCtx, beta);

    const userAccess = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode,
      role: userAuthz.role,
      bypassOpsMode: userAuthz.bypass_ops_mode,
    });
    const adminAccess = evaluateOpsAccess({
      pathname: "/api/predictions",
      opsMode,
      role: adminAuthz.role,
      bypassOpsMode: adminAuthz.bypass_ops_mode,
    });

    assert.equal(userAccess.allow, false);
    assert.equal(adminAccess.allow, true);
    _resetUserRuntimeForTests();
  });
});
