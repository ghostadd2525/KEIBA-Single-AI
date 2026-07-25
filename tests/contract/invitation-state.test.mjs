import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";
import {
  InvitationRepository,
  _resetInvitationRuntimeForTests,
  _seedInvitationsForTests,
} from "../../functions/_lib/invitationRepository.js";
import { _resetAuthStoreMemoryForTests } from "../../functions/_lib/authStore.js";

const ctx = {};

describe("Phase9-B Invitation state machine", () => {
  beforeEach(() => {
    _resetInvitationRuntimeForTests();
    _resetAuthStoreMemoryForTests();
    _seedInvitationsForTests([
      {
        invite_id: "BETA-STATE-01",
        status: "issued",
        issued_at: "2026-07-01T00:00:00Z",
        expires_at: null,
      },
      {
        invite_id: "BETA-EXPIRED-01",
        status: "issued",
        issued_at: "2026-01-01T00:00:00Z",
        expires_at: "2026-01-02T00:00:00Z",
      },
      {
        invite_id: "BETA-OFF-01",
        status: "disabled",
        issued_at: "2026-07-01T00:00:00Z",
      },
    ]);
  });

  it("issued のみ assertIssuable ok", async () => {
    const ok = await InvitationRepository.assertIssuable(ctx, "BETA-STATE-01");
    assert.equal(ok.ok, true);
    const bad = await InvitationRepository.assertIssuable(ctx, "BETA-OFF-01");
    assert.equal(bad.ok, false);
    assert.equal(bad.code, "INVITE_DISABLED");
  });

  it("expires_at 経過は expired", async () => {
    const r = await InvitationRepository.assertIssuable(ctx, "BETA-EXPIRED-01");
    assert.equal(r.ok, false);
    assert.equal(r.code, "INVITE_EXPIRED");
  });

  it("issued → activated", async () => {
    const act = await InvitationRepository.activate(ctx, "BETA-STATE-01", "user-a");
    assert.equal(act.ok, true);
    assert.equal(act.invite.status, "activated");
    assert.equal(act.invite.activated_user_id, "user-a");
    const again = await InvitationRepository.assertIssuable(ctx, "BETA-STATE-01");
    assert.equal(again.ok, false);
    assert.equal(again.code, "INVITE_ALREADY_USED");
  });

  it("issued → disabled", async () => {
    const d = await InvitationRepository.disable(ctx, "BETA-STATE-01");
    assert.equal(d.ok, true);
    assert.equal(d.invite.status, "disabled");
  });

  it("issue で新規 issued", async () => {
    const r = await InvitationRepository.issue(ctx, "BETA-NEW-99", { note: "test" });
    assert.equal(r.ok, true);
    assert.equal(r.invite.status, "issued");
    const list = await InvitationRepository.list(ctx);
    assert.ok(list.some((x) => x.invite_id === "BETA-NEW-99"));
  });

  it("署名付き一時IDはメモリ未登録でも assertIssuable ok", async () => {
    const minted = await InvitationRepository.issue(ctx, "", { expires_days: 14, note: "signed" });
    assert.equal(minted.ok, true);
    assert.match(minted.invite.invite_id, /^TMP-[0-9A-F]+-[0-9A-F]{8}-[0-9A-F]{12}$/);
    // 別 isolate 相当: メモリを全消ししても署名で検証できる
    _resetInvitationRuntimeForTests();
    _resetAuthStoreMemoryForTests();
    _seedInvitationsForTests([]);
    const check = await InvitationRepository.assertIssuable(ctx, minted.invite.invite_id);
    assert.equal(check.ok, true);
    assert.equal(check.invite.status, "issued");
  });
});
