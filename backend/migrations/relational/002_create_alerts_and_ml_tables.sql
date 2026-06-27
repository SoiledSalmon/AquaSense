-- ============================================================
-- AquaSense Phase 4: Machine Learning Pipeline Metadata
-- Execute in Supabase SQL Editor or via Supabase CLI
-- ============================================================

-- Create the alerts table
CREATE TABLE IF NOT EXISTS public.alerts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES public.users(id) ON DELETE CASCADE,
  timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
  message     TEXT NOT NULL,
  is_read     BOOLEAN NOT NULL DEFAULT false
);

-- Enable Row Level Security on alerts
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

-- Policies for alerts
CREATE POLICY "users_select_own_alerts" ON public.alerts
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "users_update_own_alerts" ON public.alerts
  FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "users_insert_service_alerts" ON public.alerts
  FOR INSERT WITH CHECK (true);

-- Create index on user_id and timestamp for fast lookups
CREATE INDEX IF NOT EXISTS idx_alerts_user_time ON public.alerts (user_id, timestamp DESC);


-- Create the ml_results table
CREATE TABLE IF NOT EXISTS public.ml_results (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reading_id     UUID,  -- Stored as plain UUID to avoid TimescaleDB hypertable foreign key limitations
  user_id        UUID REFERENCES public.users(id) ON DELETE CASCADE,
  timestamp      TIMESTAMPTZ NOT NULL,
  ph_smoothed    NUMERIC(5,2),
  tds_smoothed   NUMERIC(7,2),
  turb_smoothed  NUMERIC(7,2),
  anomaly_score  NUMERIC(7,4),
  is_anomaly     BOOLEAN DEFAULT false,
  shap_ph        NUMERIC(7,4),
  shap_tds       NUMERIC(7,4),
  shap_turbidity NUMERIC(7,4),
  risk_level     TEXT CHECK (risk_level IN ('low', 'medium', 'high')),
  recommendation TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row Level Security on ml_results
ALTER TABLE public.ml_results ENABLE ROW LEVEL SECURITY;

-- Policies for ml_results
CREATE POLICY "users_select_own_ml_results" ON public.ml_results
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "users_insert_service_ml_results" ON public.ml_results
  FOR INSERT WITH CHECK (true);

-- Index for fast user/time queries
CREATE INDEX IF NOT EXISTS idx_ml_results_user_time ON public.ml_results (user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ml_results_reading_id ON public.ml_results (reading_id);


-- Create the retrain_logs table (for auditing offline model retraining)
CREATE TABLE IF NOT EXISTS public.retrain_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES public.users(id) ON DELETE CASCADE,
  timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
  model_type  TEXT NOT NULL,
  status      TEXT NOT NULL,
  metrics     JSONB,
  error       TEXT
);

-- Enable Row Level Security on retrain_logs
ALTER TABLE public.retrain_logs ENABLE ROW LEVEL SECURITY;

-- Policies for retrain_logs
CREATE POLICY "users_select_own_retrain_logs" ON public.retrain_logs
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "users_insert_service_retrain_logs" ON public.retrain_logs
  FOR INSERT WITH CHECK (true);
