-- ============================================================
-- AquaSense Phase 1: Users Table + Row Level Security
-- Execute in Supabase SQL Editor or via Supabase CLI
-- ============================================================

-- Create the users table
CREATE TABLE IF NOT EXISTS public.users (
  id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email      TEXT NOT NULL,
  full_name  TEXT,
  role       TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
  channel_id TEXT,
  ts_api_key TEXT,
  phone      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own profile
CREATE POLICY "users_select_own" ON public.users
  FOR SELECT USING (auth.uid() = id);

-- Policy: Users can update their own profile
-- WITH CHECK prevents reassigning the row to a different user
CREATE POLICY "users_update_own" ON public.users
  FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Policy: Allow inserts (service role bypasses RLS anyway,
-- but this documents the intent for non-service-role contexts)
CREATE POLICY "users_insert_service" ON public.users
  FOR INSERT WITH CHECK (true);

-- Trigger: Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- Index for email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users (email);
