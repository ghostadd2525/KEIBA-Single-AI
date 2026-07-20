import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { clone, loadSchemas, readJson, validateDef } from "../helpers/load.mjs";

const { auth: schema } = loadSchemas();
const inviteStart = readJson("fixtures/auth/invite-start-response.json");
const invitation = readJson("fixtures/auth/invitation-record.json");
const user = readJson("fixtures/auth/user-record.json");
const invitationsDoc = readJson("public/data/invitations.json");
const usersDoc = readJson("public/data/users.json");

describe("Phase9 Invitation Auth contract", () => {
  it("AuthInviteStartResponse", () => {
    const r = validateDef(schema, "AuthInviteStartResponse", inviteStart);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("InvitationRecord", () => {
    const r = validateDef(schema, "InvitationRecord", invitation);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("UserRecord", () => {
    const r = validateDef(schema, "UserRecord", user);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("invitations.json の各要素が InvitationRecord", () => {
    assert.ok(Array.isArray(invitationsDoc.invitations));
    for (const row of invitationsDoc.invitations) {
      const r = validateDef(schema, "InvitationRecord", row);
      assert.equal(r.ok, true, r.errors.join(" | "));
    }
  });

  it("users.json の各要素が UserRecord", () => {
    assert.ok(Array.isArray(usersDoc.users));
    for (const row of usersDoc.users) {
      const r = validateDef(schema, "UserRecord", row);
      assert.equal(r.ok, true, r.errors.join(" | "));
    }
  });

  it("InvitationRecord: invite_id 欠落は失敗", () => {
    const bad = clone(invitation);
    delete bad.invite_id;
    const r = validateDef(schema, "InvitationRecord", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("invite_id")));
  });

  it("setup_token 欠落は失敗", () => {
    const bad = clone(inviteStart);
    delete bad.setup_token;
    const r = validateDef(schema, "AuthInviteStartResponse", bad);
    assert.equal(r.ok, false);
  });
});
