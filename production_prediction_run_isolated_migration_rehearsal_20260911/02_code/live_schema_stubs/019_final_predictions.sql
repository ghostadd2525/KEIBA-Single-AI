-- RECONSTRUCTED STUB. NOT live Production SQL.
-- Live file 019_final_predictions is not in origin/main.
-- Columns inferred from services/win5-ai/app/ops/result_day_contract.py
-- (PRAGMA table_info probes race_id / source_race_id).
-- Do not apply this file to Production.

CREATE TABLE IF NOT EXISTS final_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_id TEXT,
  source_race_id TEXT,
  payload_json TEXT,
  created_at TEXT
);
