import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const catalog = require("../../public/assets/api/catalog-identity.js");

describe("Challenge Race Detail CTA (catalog-valid, not ui-test flag)", () => {
  const prevUi = globalThis.ExpectUiTestRace;

  beforeEach(() => {
    delete globalThis.ExpectUiTestRace;
  });

  afterEach(() => {
    if (prevUi === undefined) delete globalThis.ExpectUiTestRace;
    else globalThis.ExpectUiTestRace = prevUi;
  });

  it("A. real catalog race_id is visible without enable_ui_test_race", () => {
    assert.equal(catalog.showChallengeCtaForRace("2026-09-06-02-10"), true);
    assert.equal(catalog.showChallengeCtaForRace("2026-09-05-01-01"), true);
    assert.equal(
      catalog.challengePurchaseHref("2026-09-06-02-10"),
      "challenge-purchase.html?race_id=2026-09-06-02-10"
    );
  });

  it("B. ui-test race keeps existing fixture gate", () => {
    assert.equal(catalog.showChallengeCtaForRace("ui-test-race-001"), false);
    assert.equal(catalog.challengePurchaseHref("ui-test-race-001"), "");

    globalThis.ExpectUiTestRace = {
      isUiTestRaceId: function (id) {
        return String(id || "").trim() === "ui-test-race-001";
      },
      enabled: function () {
        return true;
      },
    };
    assert.equal(catalog.showChallengeCtaForRace("ui-test-race-001"), true);
    assert.equal(
      catalog.challengePurchaseHref("ui-test-race-001"),
      "challenge-purchase.html?race_id=ui-test-race-001"
    );

    globalThis.ExpectUiTestRace.enabled = function () {
      return false;
    };
    assert.equal(catalog.showChallengeCtaForRace("ui-test-race-001"), false);
    assert.equal(catalog.showChallengeCtaForRace("2026-09-06-02-10"), true);
  });

  it("C. invalid race_id does not produce href", () => {
    ["", "   ", "not-a-race", "20260719_hanshin_11", "ui-test-race-999"].forEach(
      function (id) {
        assert.equal(catalog.showChallengeCtaForRace(id), false);
        assert.equal(catalog.challengePurchaseHref(id), "");
      }
    );
  });

  it("D. purchase href keeps the given race_id", () => {
    assert.equal(
      catalog.challengePurchaseHref("2026-09-06-02-10"),
      "challenge-purchase.html?race_id=2026-09-06-02-10"
    );
    assert.equal(
      catalog.challengePurchaseHref("2026-09-05-03-12"),
      "challenge-purchase.html?race_id=2026-09-05-03-12"
    );
  });
});
