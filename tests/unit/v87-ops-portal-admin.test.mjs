/**
 * Version8.7 — Ops Portal ADMIN gate + role normalize (unit)
 */
import assert from "node:assert/strict";
import test from "node:test";
import { isOpsPortalAdmin } from "../../functions/_lib/opsPortalAccess.js";
import { normalizeRole } from "../../functions/_lib/roles.js";

test("normalizeRole accepts admin / ADMIN / administrator", () => {
  assert.equal(normalizeRole("admin"), "ADMIN");
  assert.equal(normalizeRole("ADMIN"), "ADMIN");
  assert.equal(normalizeRole("administrator"), "ADMIN");
  assert.equal(normalizeRole("ROOT"), "ADMIN");
});

test("ops portal allows role=ADMIN", () => {
  assert.equal(isOpsPortalAdmin({}, { id: "u1", role: "ADMIN" }, { role: "ADMIN" }), true);
});

test("ops portal denies USER", () => {
  assert.equal(isOpsPortalAdmin({}, { id: "u2", role: "USER" }, { role: "USER" }), false);
});

test("ops portal denies OPS/DEVELOPER without allowlist", () => {
  assert.equal(isOpsPortalAdmin({}, { id: "u3", role: "OPS" }, { role: "OPS" }), false);
  assert.equal(
    isOpsPortalAdmin({}, { id: "u4", role: "DEVELOPER" }, { role: "DEVELOPER" }),
    false
  );
});

test("ops portal allows admin_user_ids allowlist", () => {
  assert.equal(
    isOpsPortalAdmin({ admin_user_ids: ["legacy-admin"] }, { id: "legacy-admin", role: "USER" }, null),
    true
  );
});
