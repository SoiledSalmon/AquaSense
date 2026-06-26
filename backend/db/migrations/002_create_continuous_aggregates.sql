-- ============================================================
-- AquaSense Phase 2: Continuous Aggregates (TimescaleDB)
-- Execute in Supabase SQL Editor or via Supabase CLI
-- ============================================================

-- Hourly aggregate (for 24h chart)
CREATE MATERIALIZED VIEW IF NOT EXISTS readings_hourly
WITH (timescaledb.continuous) AS
SELECT
  user_id,
  time_bucket('1 hour', timestamp) AS bucket,
  AVG(ph)        AS avg_ph,
  AVG(tds)       AS avg_tds,
  AVG(turbidity) AS avg_turbidity,
  AVG(wqi_score) AS avg_wqi
FROM readings
GROUP BY user_id, bucket;

-- Daily aggregate (for 7d and 30d charts)
CREATE MATERIALIZED VIEW IF NOT EXISTS readings_daily
WITH (timescaledb.continuous) AS
SELECT
  user_id,
  time_bucket('1 day', timestamp) AS bucket,
  AVG(ph)        AS avg_ph,
  AVG(tds)       AS avg_tds,
  AVG(turbidity) AS avg_turbidity,
  AVG(wqi_score) AS avg_wqi
FROM readings
GROUP BY user_id, bucket;

-- Add refresh policies for the continuous aggregates to ensure they update automatically
SELECT add_continuous_aggregate_policy('readings_hourly',
  start_offset => INTERVAL '1 day',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour',
  if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('readings_daily',
  start_offset => INTERVAL '1 month',
  end_offset => INTERVAL '1 day',
  schedule_interval => INTERVAL '1 day',
  if_not_exists => TRUE);
