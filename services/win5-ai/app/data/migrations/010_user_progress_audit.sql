-- Phase U-3: user progress (points/level), purchase audit, settings
-- Independent from Prediction Engine

CREATE TABLE IF NOT EXISTS user_progress (
  user_id TEXT PRIMARY KEY,
  cumulative_points INTEGER NOT NULL DEFAULT 0,
  cumulative_profit INTEGER NOT NULL DEFAULT 0,
  level INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_purchase_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  race_id TEXT,
  event_type TEXT NOT NULL,
  purchase_amount INTEGER,
  payout_amount INTEGER,
  profit INTEGER,
  points_awarded INTEGER DEFAULT 0,
  ai_strategy_json TEXT,
  user_bets_json TEXT,
  ip_address TEXT,
  user_agent TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_upa_user_created
  ON user_purchase_audit(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_upa_event
  ON user_purchase_audit(event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO app_settings(key, value_json, updated_at)
VALUES ('max_purchase_amount_per_race', '50000', datetime('now'));
INSERT OR IGNORE INTO app_settings(key, value_json, updated_at)
VALUES ('purchase_anomaly_payout_multiple', '200', datetime('now'));
INSERT OR IGNORE INTO app_settings(key, value_json, updated_at)
VALUES ('purchase_amount_divergence_ratio', '3', datetime('now'));

-- Extend user_race_results for explicit purchase registration + points
ALTER TABLE user_race_results ADD COLUMN purchase_registered INTEGER NOT NULL DEFAULT 0;
ALTER TABLE user_race_results ADD COLUMN unit_stake INTEGER;
ALTER TABLE user_race_results ADD COLUMN selected_bet_types_json TEXT;
ALTER TABLE user_race_results ADD COLUMN points_awarded INTEGER NOT NULL DEFAULT 0;
ALTER TABLE user_race_results ADD COLUMN registered_at TEXT;
ALTER TABLE user_race_results ADD COLUMN client_meta_json TEXT;
