-- ============================================================
-- AquaSense Phase 2: Readings Hypertable (TimescaleDB)
-- Execute in Supabase SQL Editor or via Supabase CLI
-- ============================================================

-- Enable the TimescaleDB extension if not already enabled
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create the readings table
CREATE TABLE IF NOT EXISTS readings (
  timestamp   TIMESTAMPTZ NOT NULL,
  id          UUID DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id),
  ph          NUMERIC(5,2),
  tds         NUMERIC(7,2),
  turbidity   NUMERIC(7,2),
  wqi_score   NUMERIC(5,2),
  label       TEXT
);

-- Convert to hypertable with a 1-day chunk interval
SELECT create_hypertable('readings', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);

-- Add the composite index
CREATE INDEX IF NOT EXISTS idx_readings_user_time ON readings (user_id, timestamp DESC);

-- Enable compression and add the 7-day compression policy
ALTER TABLE readings SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'user_id'
);

SELECT add_compression_policy('readings', INTERVAL '7 days', if_not_exists => TRUE);
