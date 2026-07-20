import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { clone, loadSchemas, readJson, validateDef } from "../helpers/load.mjs";

const { auth: schema } = loadSchemas();
const login = readJson("fixtures/auth/login-response.json");
const me = readJson("fixtures/auth/me-response.json");
const logout = readJson("fixtures/auth/logout-response.json");
const favorites = readJson("fixtures/auth/favorites-state.json");

describe("AuthService contract", () => {
  it("正常系: AuthLoginResponse", () => {
    const r = validateDef(schema, "AuthLoginResponse", login);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("正常系: AuthMeResponse", () => {
    const r = validateDef(schema, "AuthMeResponse", me);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("正常系: AuthLogoutResponse", () => {
    const r = validateDef(schema, "AuthLogoutResponse", logout);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("正常系: FavoritesState", () => {
    const r = validateDef(schema, "FavoritesState", favorites);
    assert.equal(r.ok, true, r.errors.join(" | "));
  });

  it("必須フィールド欠落: login.access_token", () => {
    const bad = clone(login);
    delete bad.access_token;
    const r = validateDef(schema, "AuthLoginResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("access_token") && e.includes("required")));
  });

  it("必須フィールド欠落: me.user", () => {
    const bad = clone(me);
    delete bad.user;
    const r = validateDef(schema, "AuthMeResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("user") && e.includes("required")));
  });

  it("型不一致: expires_in が文字列", () => {
    const bad = clone(login);
    bad.expires_in = "86400";
    const r = validateDef(schema, "AuthLoginResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("expires_in") && e.includes("type")));
  });

  it("schema_version 不一致: login", () => {
    const bad = clone(login);
    bad.schema_version = "expect-auth/0.1";
    const r = validateDef(schema, "AuthLoginResponse", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("const")));
  });

  it("FavoritesState: race_ids 欠落", () => {
    const bad = clone(favorites);
    delete bad.race_ids;
    const r = validateDef(schema, "FavoritesState", bad);
    assert.equal(r.ok, false);
    assert.ok(r.errors.some((e) => e.includes("race_ids")));
  });
});
