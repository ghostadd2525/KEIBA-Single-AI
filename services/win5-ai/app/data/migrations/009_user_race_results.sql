-- Phase U-2: user race results (household ledger / personal P&L)
-- Independent from Prediction Engine

CREATE TABLE IF NOT EXISTS user_race_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  race_id TEXT NOT NULL,
  race_date TEXT,
  race_label TEXT,
  prediction_version TEXT,
  strategy_snapshot_json TEXT NOT NULL,
  purchase_amount INTEGER NOT NULL DEFAULT 0,
  payout_amount INTEGER NOT NULL DEFAULT 0,
  profit INTEGER NOT NULL DEFAULT 0,
  hit INTEGER NOT NULL DEFAULT 0,
  settled INTEGER NOT NULL DEFAULT 0,
  finish_order_json TEXT,
  payouts_json TEXT,
  bet_results_json TEXT,
  marks_result_json TEXT,
  official_result_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  settled_at TEXT,
  UNIQUE(user_id, race_id),
  FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_urr_user_date
  ON user_race_results(user_id, race_date);
CREATE INDEX IF NOT EXISTS idx_urr_user_month
  ON user_race_results(user_id, substr(race_date, 1, 7));
CREATE INDEX IF NOT EXISTS idx_urr_settled
  ON user_race_results(user_id, settled);
