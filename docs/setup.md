# AquaSense Installation & Setup Guide

This document contains step-by-step instructions for setting up, validating, and deploying the AquaSense IoT Water Quality Monitoring system in local and production environments.

---

## 1. Local Development Setup

### 1.1 Database & Authentication (Supabase)
AquaSense relies on Supabase (Postgres) for auth and data storage.

1. Create a new project on the [Supabase Dashboard](https://supabase.com).
2. Open the Supabase SQL Editor and execute the SQL migrations in order:
   - **Relational Schema:** Execute the scripts in `backend/migrations/relational/` sequentially.
   - **Time-Series Schema:** Execute the scripts in `backend/migrations/timescaledb/` sequentially.
3. Record the project **URL**, **Anon Key**, **Service Role (Admin) Key**, and **JWT Secret**.

### 1.2 Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Fill in Supabase credentials and ThingSpeak MQTT parameters.
5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload
   ```
6. Run the test suite:
   ```bash
   # Run from root of repository
   backend\.venv\Scripts\python -m pytest
   ```

### 1.3 Frontend Setup
1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Configure environment variables:
   - Copy `.env.example` to `.env.local`
   - Ensure `NEXT_PUBLIC_API_URL` points to the local backend (usually `http://localhost:8000`).
4. Launch the Next.js development server:
   ```bash
   npm run dev
   ```
5. Access the client dashboard at `http://localhost:3000`.

---

## 2. Production Deployment

### 2.1 Backend Deployment (Always-On Container Context)
The backend requires an always-on environment to hold the persistent MQTT connection to ThingSpeak.

1. Deploy the backend from your git repository.
2. In your cloud container host (e.g. Railway, Render instance, or VPS), configure the following environment variables:

| Variable Name | Description |
| --- | --- |
| `ENVIRONMENT` | Deployment stage (e.g., `production`) |
| `FRONTEND_URL` | Deployed frontend URL |
| `SUPABASE_URL` | Supabase API Endpoint |
| `SUPABASE_KEY` | Public Anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only Admin key |
| `SUPABASE_JWT_SECRET` | Secret key for JWT verification |
| `THINGSPEAK_MQTT_USER` | Username for ThingSpeak broker |
| `THINGSPEAK_MQTT_API_KEY` | Password/API key for ThingSpeak broker |
| `THINGSPEAK_REST_API_KEY` | Fallback REST Read API key |

3. The background MQTT subscriber automatically connects and handles reconnection loops with exponential backoff.

### 2.2 Frontend Deployment (Vercel)
Vercel automatically provisions and builds Next.js projects.

1. Import the `frontend` folder from your repository in Vercel.
2. Provide the following configuration variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` (Points to the deployed backend URL)

---

## 3. Maintenance & Procedures

### 3.1 Database Backups
To perform a manual logical backup, run:
```bash
pg_dump -h db.xyz.supabase.co -U postgres -d postgres -F c -b -v -f aquasense_backup.dump
```

### 3.2 Materialized Views Maintenance & Refresh Schedule
- **Refresh Schedule (pg_cron):** By default, view aggregation updates are scheduled to execute automatically:
  - `readings_hourly` refreshes concurrently every hour: `0 * * * *`
  - `readings_daily` refreshes concurrently once a day: `5 0 * * *`
- **Manual Refresh Command:** Execute the following SQL commands to refresh views manually:
  ```sql
  REFRESH MATERIALIZED VIEW CONCURRENTLY public.readings_hourly;
  REFRESH MATERIALIZED VIEW CONCURRENTLY public.readings_daily;
  ```
