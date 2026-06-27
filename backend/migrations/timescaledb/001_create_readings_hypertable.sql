-- ============================================================
-- AquaSense Phase 2: Readings Table & Indexes (PostgreSQL 17)
-- Execute in Supabase SQL Editor or via Supabase CLI
-- ============================================================

-- Create the readings table
CREATE TABLE IF NOT EXISTS public.readings (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp   TIMESTAMPTZ NOT NULL,
  user_id     UUID REFERENCES public.users(id) ON DELETE CASCADE,
  ph          NUMERIC(5,2),
  tds         NUMERIC(7,2),
  turbidity   NUMERIC(7,2),
  wqi_score   NUMERIC(5,2),
  label       TEXT
);

-- Add a standard B-tree index on the timestamp column
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON public.readings (timestamp DESC);

-- Add a composite index on (user_id, timestamp DESC) for common query patterns
CREATE INDEX IF NOT EXISTS idx_readings_user_time ON public.readings (user_id, timestamp DESC);

-- Enable Row Level Security
ALTER TABLE public.readings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own readings
CREATE POLICY "users_select_own_readings" ON public.readings
  FOR SELECT USING (auth.uid() = user_id);

-- Policy: Allow inserts
CREATE POLICY "users_insert_service_readings" ON public.readings
  FOR INSERT WITH CHECK (true);

-- Policy: Allow updates for WQI score and label calculation
CREATE POLICY "users_update_service_readings" ON public.readings
  FOR UPDATE USING (true) WITH CHECK (true);

