/**
 * Mock gate — Phase UI-RealData
 * 本番 UI は API 必須。mock fallback は ?mock=1 または EXPECT_USE_MOCK のみ。
 */
(function (global) {
  "use strict";

  var qs =
    typeof location !== "undefined" && location.search
      ? new URLSearchParams(location.search)
      : null;

  global.EXPECT_USE_MOCK =
    global.EXPECT_USE_MOCK === true ||
    !!(qs && (qs.get("mock") === "1" || qs.get("use_mock") === "1"));

  global.EXPECT_MOCK_FALLBACK = global.EXPECT_USE_MOCK;

  global.ExpectMockGate = {
    allowMockFallback: function () {
      return global.EXPECT_USE_MOCK === true || global.EXPECT_MOCK_FALLBACK === true;
    },
    allowDevMock: function () {
      return global.EXPECT_USE_MOCK === true;
    },
  };
})(window);
