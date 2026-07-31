import test from "node:test";
import assert from "node:assert/strict";
import {
  evaluateProductionAuthConfig,
  PRODUCTION_AUTH_FATAL_MESSAGE,
  PRODUCTION_AUTH_FATAL_CODE,
} from "../../functions/_lib/productionAuthGuard.js";

test("FATAL when production + stub + ALLOW_STUB_AUTH unset", () => {
  const r = evaluateProductionAuthConfig({
    EXPECT_ENV: "production",
    AUTH_MODE: "stub",
    ALLOW_STUB_AUTH: "",
  });
  assert.equal(r.fatal, true);
  assert.equal(r.code, PRODUCTION_AUTH_FATAL_CODE);
  assert.equal(r.message, PRODUCTION_AUTH_FATAL_MESSAGE);
});

test("FATAL when production + default AUTH_MODE + ALLOW_STUB_AUTH!=1", () => {
  const r = evaluateProductionAuthConfig({
    EXPECT_ENV: "prod",
    AUTH_MODE: "",
    ALLOW_STUB_AUTH: "0",
  });
  assert.equal(r.fatal, true);
});

test("OK when production + stub + ALLOW_STUB_AUTH=1", () => {
  const r = evaluateProductionAuthConfig({
    EXPECT_ENV: "production",
    AUTH_MODE: "stub",
    ALLOW_STUB_AUTH: "1",
  });
  assert.equal(r.fatal, false);
  assert.equal(r.message, null);
});

test("OK when non-production stub without allow", () => {
  const r = evaluateProductionAuthConfig({
    EXPECT_ENV: "development",
    AUTH_MODE: "stub",
    ALLOW_STUB_AUTH: "",
  });
  assert.equal(r.fatal, false);
});
