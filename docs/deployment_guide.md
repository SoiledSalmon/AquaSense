# AquaSense Production Deployment & Operations Guide

This document contains step-by-step instructions for deploying, validating, and maintaining the AquaSense IoT Water Quality Monitoring system in its production architecture.

---

## 1. Production Architecture Overview

The system consists of three main hosting components:
1. **Supabase (Database & Auth)**:
   - PostgreSQL 15 engine (required for TimescaleDB extension).
   - Supabase Auth manages secure user registration and JWT-based session token exchange.
   - TimescaleDB extension manages the `readings` hypertable (1-day chunk interval, 7-day compression policy) and continuous aggregate hourly/daily materialized views.
2. **Railway (FastAPI Backend + MQTT Subscriber)**:
   - Always-on container process.
   - Houses the REST API endpoints and Server-Sent Events (SSE) broadcaster.
   - Houses the persistent `asyncio-mqtt` listener connected to ThingSpeak's broker (`mqtt3.thingspeak.com`).
3. **Vercel (Next.js 15 Frontend)**:
   - Deploys the React client application.
   - Natively interfaces with Supabase Auth client-side and proxies API calls/SSE streams to the Railway backend.

---

## 2. Supabase & Database Production Configuration

### 2.1 Project Creation
1. Go to the [Supabase Dashboard](https://supabase.com) and create a new project.
2. **Critical**: Ensure the project is provisioned with **PostgreSQL 15**. (Supabase does not support the TimescaleDB extension on Postgres 16 or 17).
3. Record the project **URL**, **Anon (Public) API key**, **Service Role (Admin) API key**, and **JWT Secret**.

### 2.2 Running Migrations
Run the following migration scripts in order. You can execute them via the Supabase SQL Editor or through the Supabase CLI.

1. **Relational Core Schema**:
   - Run [001_create_users_table.sql](file:///D:/Coding%20Projects/College%20Era/AquaSense/backend/migrations/relational/001_create_users_table.sql) to create the profiles table with Row Level Security.
   - Run [002_create_alerts_and_ml_tables.sql](file:///D:/Coding%20Projects/College%20Era/AquaSense/backend/migrations/relational/002_create_alerts_and_ml_tables.sql) to create relational alerts, ML predictions, and training audit log schemas.
   - Run [003_update_alerts_table.sql](file:///D:/Coding%20Projects/College%20Era/AquaSense/backend/migrations/relational/003_update_alerts_table.sql) to support severity, category, and acknowledgement statuses.

2. **TimescaleDB Time-Series Schema**:
   - Run [001_create_readings_hypertable.sql](file:///D:/Coding%20Projects/College%20Era/AquaSense/backend/migrations/timescaledb/001_create_readings_hypertable.sql) to enable the `timescaledb` extension, create the telemetry table, partition it into chunks, and add the 7-day compression policy.
   - Run [002_create_continuous_aggregates.sql](file:///D:/Coding%20Projects/College%20Era/AquaSense/backend/migrations/timescaledb/002_create_continuous_aggregates.sql) to establish hourly/daily pre-computed aggregates and configure automatic refresh policies.

---

## 3. Railway Backend Deployment

Railway uses `railway.json` to compile and launch the FastAPI server via Nixpacks.

### 3.1 Initial Setup
1. Log in to [Railway](https://railway.app).
2. Create a new project and select **Deploy from GitHub repo**.
3. Select the repository and specify the **Root Directory** as `/` or keep it default, and ensure that build settings point to the root `railway.json`.
4. Railway will build the backend code using the `requirements.txt` file and start the server using the configured start command.

### 3.2 Environment Variables (Railway)
In the **Variables** tab of your Railway service, configure the following:

| Variable Name | Description | Example |
| --- | --- | --- |
| `ENVIRONMENT` | Deployment stage | `production` |
| `FRONTEND_URL` | Deployed Vercel frontend URL | `https://aquasense.vercel.app` |
| `SUPABASE_URL` | Supabase API Endpoint | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | Public Anon key | `eyJhbGci...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only Admin key | `eyJhbGci...` |
| `SUPABASE_JWT_SECRET` | Secret key for JWT verification | `your-jwt-signing-secret` |
| `THINGSPEAK_MQTT_USER` | Username for ThingSpeak broker | `aquasense-mqtt-user` |
| `THINGSPEAK_MQTT_API_KEY` | Password/API key for ThingSpeak broker | `THINGSPEAK_MQTT_PASS` |
| `THINGSPEAK_REST_API_KEY` | Fallback REST Read API key | `THINGSPEAK_REST_READ_KEY` |

### 3.3 Reconnect Strategy & Reliability
- The backend contains a robust reconnection handler with exponential backoff capping at `60.0` seconds. If the network drops or the container restarts, the subscriber will retry connection automatically.
- Upon successful reconnection, the backend executes a **REST catch-up query** against ThingSpeak to backfill any readings that were published during the downtime.

---

## 4. Vercel Frontend Deployment

Vercel automatically provisions, builds, and deploys Next.js projects.

### 4.1 Setup
1. Log in to [Vercel](https://vercel.com).
2. Import the `frontend` folder from your repository.
3. Keep the **Framework Preset** as `Next.js`.
4. Configure the **Build & Development Settings** with default Next.js build commands.

### 4.2 Environment Variables (Vercel)
Provide the following configuration:

| Variable Name | Description | Example |
| --- | --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | `https://xyz.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase public anon key | `eyJhbGci...` |
| `NEXT_PUBLIC_API_URL` | Deployed Railway backend API URL | `https://aquasense-api.railway.app` |

---

## 5. Operations, Monitoring & Health Checks

### 5.1 Health Monitoring
Railway monitors the `/api/health` HTTP endpoint for container liveness. It queries:
- **`status`**: Current API viability (returns `"healthy"`).
- **`mqtt_status`**: Current connection status of the background MQTT subscriber (`"connected"`, `"reconnecting"`, or `"error"`). If this shifts to `"error"`, the logs should be inspected.

### 5.2 Structured Logging
The FastAPI backend logs standard events to `stdout` in **JSON format** when `ENVIRONMENT=production`.
Log parsers can index fields such as `timestamp`, `level`, `event`, `user_id`, and `error` without needing complex regex mappings.

---

## 6. Recovery & Backup Procedures

### 6.1 Database Backups
- Relational tables and auth schemas are automatically backed up daily by Supabase's integrated backup systems.
- To perform a manual logical backup, run:
  ```bash
  pg_dump -h db.xyz.supabase.co -U postgres -d postgres -F c -b -v -f aquasense_backup.dump
  ```

### 6.2 TimescaleDB Maintenance
- **Compression policy**: Active data is automatically compressed after 7 days, reducing storage footprint by up to 90%.
- **Decompression**: If historical records require manual correction, temporarily pause the compression policy:
  ```sql
  SELECT alter_job_relation('readings', scheduled => false);
  ```
