-- ============================================================
-- AquaSense Phase 2: Materialized Views & Refresh Schedules (PostgreSQL 17)
-- Execute in Supabase SQL Editor or via Supabase CLI
-- ============================================================

-- Hourly aggregate (for 24h chart)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.readings_hourly AS
SELECT
  user_id,
  date_trunc('hour', timestamp) AS bucket,
  AVG(ph)        AS avg_ph,
  AVG(tds)       AS avg_tds,
  AVG(turbidity) AS avg_turbidity,
  AVG(wqi_score) AS avg_wqi
FROM public.readings
GROUP BY user_id, date_trunc('hour', timestamp);

-- Create unique index for concurrent refreshes
CREATE UNIQUE INDEX IF NOT EXISTS idx_readings_hourly_unique ON public.readings_hourly (user_id, bucket);

-- Daily aggregate (for 7d and 30d charts)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.readings_daily AS
SELECT
  user_id,
  date_trunc('day', timestamp) AS bucket,
  AVG(ph)        AS avg_ph,
  AVG(tds)       AS avg_tds,
  AVG(turbidity) AS avg_turbidity,
  AVG(wqi_score) AS avg_wqi
FROM public.readings
GROUP BY user_id, date_trunc('day', timestamp);

-- Create unique index for concurrent refreshes
CREATE UNIQUE INDEX IF NOT EXISTS idx_readings_daily_unique ON public.readings_daily (user_id, bucket);

-- Enable pg_cron if available (typically enabled via Supabase dashboard or superuser)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule hourly view refresh (refreshes every hour on the hour)
SELECT cron.schedule(
  'refresh-readings-hourly',
  '0 * * * *',
  'REFRESH MATERIALIZED VIEW CONCURRENTLY public.readings_hourly'
);

-- Schedule daily view refresh (refreshes daily at 00:05 UTC)
SELECT cron.schedule(
  'refresh-readings-daily',
  '5 0 * * *',
  'REFRESH MATERIALIZED VIEW CONCURRENTLY public.readings_daily'
);

-- NOTE ON MANUAL REFRESH / SUPABASE SCHEDULED FUNCTIONS:
-- If pg_cron is not available or disabled in your database environment, you can refresh these views:
-- 1. Via Supabase edge functions or net extensions to call custom RPCs.
-- 2. By creating a database RPC function (e.g. refresh_water_quality_views()) and invoking it via external cron (Vercel Cron, GitHub Actions, or Railway Cron).
-- 3. Directly using Supabase's built-in pg_cron support if enabled in the extension list.
