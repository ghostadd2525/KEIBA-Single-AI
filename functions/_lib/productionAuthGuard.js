/**
 * Production Auth configuration guard (Version8.5.1 / ops hardening).
 *
 * FATAL when:
 *   EXPECT_ENV=production|prod
 *   AND AUTH_MODE=stub (or unset → stub)
 *   AND ALLOW_STUB_AUTH != "1"
 *
 * Message: "Production cannot start with stub auth disabled."
 * Prevents login-issues-stub + middleware-rejects-stub deadlock.
 */
export const PRODUCTION_AUTH_FATAL_MESSAGE =
  "Production cannot start with stub auth disabled.";

export const PRODUCTION_AUTH_FATAL_CODE = "PRODUCTION_AUTH_MISCONFIG";

/**
 * @param {{ EXPECT_ENV?: string, AUTH_MODE?: string, ALLOW_STUB_AUTH?: string } | null | undefined} env
 * @returns {{
 *   fatal: boolean,
 *   code: string | null,
 *   message: string | null,
 *   expect_env: string,
 *   auth_mode: string,
 *   allow_stub_auth: string,
 *   stub_mode: boolean,
 * }}
 */
export function evaluateProductionAuthConfig(env) {
  const expectEnv = String((env && env.EXPECT_ENV) || "")
    .trim()
    .toLowerCase();
  const authMode = String((env && env.AUTH_MODE) || "stub")
    .trim()
    .toLowerCase();
  const allowStub = String((env && env.ALLOW_STUB_AUTH) || "").trim();
  const isProd = expectEnv === "production" || expectEnv === "prod";
  const stubMode = !authMode || authMode === "stub";

  if (isProd && stubMode && allowStub !== "1") {
    return {
      fatal: true,
      code: PRODUCTION_AUTH_FATAL_CODE,
      message: PRODUCTION_AUTH_FATAL_MESSAGE,
      expect_env: expectEnv || "(empty)",
      auth_mode: authMode || "stub",
      allow_stub_auth: allowStub || "(unset)",
      stub_mode: true,
    };
  }

  return {
    fatal: false,
    code: null,
    message: null,
    expect_env: expectEnv || "(empty)",
    auth_mode: authMode || "stub",
    allow_stub_auth: allowStub || "(unset)",
    stub_mode: stubMode,
  };
}

/**
 * Paths that remain reachable during FATAL so ops can diagnose schedule / liveness shape.
 * /api/health intentionally NOT exempt — it must surface FATAL.
 */
export const PRODUCTION_AUTH_FATAL_EXEMPT = new Set([
  "/api/ops/public-status",
  "/api/system/status",
]);
