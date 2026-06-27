-- ============================================================
-- AquaSense Phase 5: Real-time Alerting System Schema Updates
-- Execute in Supabase SQL Editor or via Supabase CLI
-- ============================================================

-- Alter the alerts table to support new Phase 5 alerting fields
ALTER TABLE public.alerts 
  ADD COLUMN IF NOT EXISTS severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
  ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS is_acknowledged BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS is_resolved BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS recommendation TEXT,
  ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;

-- Create an index to quickly filter alerts by user, read status, and acknowledgement status
CREATE INDEX IF NOT EXISTS idx_alerts_user_status ON public.alerts (user_id, is_read, is_acknowledged);

-- Create an index to quickly check the latest alert of a category for cooldown checks
CREATE INDEX IF NOT EXISTS idx_alerts_user_category_time ON public.alerts (user_id, category, timestamp DESC);
