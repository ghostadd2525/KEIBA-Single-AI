/** Single-AI バックエンド接続（WIN5 ではない） */
export function getEnv(context) {
  const env = context.env || {};
  return {
    AI_BASE_URL: String(env.AI_BASE_URL || "").replace(/\/$/, ""),
    AI_API_KEY: String(env.AI_API_KEY || ""),
    AUTH_MODE: String(env.AUTH_MODE || "stub"),
    /** Kaoba 応答: auto | python | rule（契約は不変） */
    KAOBA_PROVIDER: String(env.KAOBA_PROVIDER || "auto"),
    /** Prediction/Analysis エンジンヒント（観測用。実切替は AI_BASE_URL） */
    AI_ENGINE: String(env.AI_ENGINE || "auto"),
    /** Phase9-A: Tunnel 上 AI を Access Service Token で呼ぶときのみ設定 */
    CF_ACCESS_CLIENT_ID: String(env.CF_ACCESS_CLIENT_ID || ""),
    CF_ACCESS_CLIENT_SECRET: String(env.CF_ACCESS_CLIENT_SECRET || ""),
    EXPECT_ENV: String(env.EXPECT_ENV || ""),
    OPS_MONITOR_KEY: String(env.OPS_MONITOR_KEY || ""),
  };
}

export function useAiProxy(env) {
  return Boolean(env.AI_BASE_URL);
}
