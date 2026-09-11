-- Migration: 002_race_identity
-- Canonical race identity columns for Race Resolver / ETL

ALTER TABLE races ADD COLUMN core_race_id TEXT;
ALTER TABLE races ADD COLUMN public_race_id TEXT;
ALTER TABLE races ADD COLUMN venue_code TEXT;

CREATE INDEX IF NOT EXISTS idx_races_core_race_id ON races(core_race_id);
CREATE INDEX IF NOT EXISTS idx_races_public_race_id ON races(public_race_id);
CREATE INDEX IF NOT EXISTS idx_races_venue_code ON races(venue_code);
