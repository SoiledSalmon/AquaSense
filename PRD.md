# AQUASENSE

IoT Water Quality Monitoring — Web Application

**PRODUCT REQUIREMENTS DOCUMENT v3.1**

*Revised — MQTT Connectivity Live + Railway Hosting*

| **Field** | **Detail** |
| --- | --- |
| Project | AquaSense Web App |
| Version | 3.1 — Railway Hosting Revision |
| Date | June 2026 |
| Authors | Ananth G Karanth · Anurag G Kharvi · Manoj Gupta D B |
| Institution | RV College of Engineering, Bengaluru — 560059 |
| Status | Revised — Ready for Development |
| Changes from v2.0 | MQTT subscribe (backend → ThingSpeak's own broker) replaces HTTP polling, eliminating the 60s ingestion delay — **no ESP32 firmware change required**; **Clerk migration evaluated and not pursued — Supabase Auth retained, `users.id` stays UUID, no schema change** |
| Changes from v3.0 | Backend hosting moved from Render to **Railway** — Railway runs containers as always-on by default, which holds the persistent MQTT connection without Render's free-tier spin-down or a Render Starter upgrade. Railway's free option is a 30-day, $5-credit trial rather than a permanent free tier; accepted as fine for the current project timeline, with a move to Railway's Hobby tier (~$5/month) once the credit runs out |

# **1. IoT Architecture Comparison & Stack Alignment**

Standard IoT application architecture follows a five-layer model: Perception (devices/sensors), Connectivity (protocols), Ingestion (message broker), Storage (time-series database), and Application (dashboard/API). This section maps the original AquaSense stack against each layer and documents the changes made in v2.0 and v3.0 to align with industry best practice.

## **1.1 Standard IoT 5-Layer Architecture vs AquaSense v1 vs v2 vs v3**

| **IoT Layer** | **Standard Approach** | **v1 (Original)** | **v2.0 (Prior Revision)** | **v3.0 (Current)** | **Status** |
| --- | --- | --- | --- | --- | --- |
| Perception | ESP32/microcontroller + sensors | ESP32 + pH, TDS, turbidity | Unchanged | Unchanged | **ALIGNED** |
| Connectivity | MQTT (pub/sub) as primary protocol | HTTP POST to ThingSpeak | HTTP polling (60s); MQTT identified as a future upgrade | Backend subscribes directly to ThingSpeak's MQTT broker (~1–3s latency); ESP32 side is **unchanged** | **CHANGED** |
| Ingestion | MQTT broker + message queue (e.g. EMQX + Kafka) | Backend HTTP polls ThingSpeak every 60s | SSE push on each 60s ingest cycle | SSE push triggered by each incoming MQTT message — no poll cycle to wait for | **CHANGED** |
| Storage | Time-series DB (TimescaleDB / InfluxDB) | Supabase PostgreSQL (plain relational) | Supabase PostgreSQL + TimescaleDB hypertable on readings | Unchanged from v2.0 | **KEPT** |
| Application | REST API + real-time dashboard | FastAPI REST + 15s frontend polling | FastAPI REST + SSE stream to frontend | Unchanged from v2.0 | **KEPT** |

## **1.2 Why the Changes Were Made**

### **Change 1: TimescaleDB hypertable for the readings table** *(from v2.0 — unchanged)*

The readings table is pure time-series data — every row is a sensor measurement at a timestamp. Standard IoT storage uses a time-series database for three reasons the standard PostgreSQL schema in v1 does not address:

- Time-range queries (24h / 7d / 30d charts) are up to 1000x faster on hypertables due to automatic time-partitioning into chunks

- Continuous aggregates pre-compute hourly and daily roll-ups, so chart queries read from a materialized view rather than scanning millions of raw rows

- Compression policies (on chunks older than 7 days) reduce storage by up to 90% — critical since sensor data accumulates indefinitely

Supabase supports the TimescaleDB extension on Postgres 15 projects. The readings table is converted to a hypertable with a 1-day chunk interval. This is a schema-level change and requires no changes to the application code beyond enabling the extension.

*Note: TimescaleDB is deprecated in Supabase Postgres 17. The project must be created on Postgres 15, or alternatively use native pg_partman partitioning on PG17.*

### **Change 2: SSE replaces frontend polling for live data** *(from v2.0 — unchanged)*

The v1 dashboard polled GET /api/readings/latest every 15 seconds and GET /api/alerts/unread every 30 seconds. This is the long-polling anti-pattern: it wastes bandwidth, introduces up to 15s lag, and puts constant load on the backend regardless of whether new data exists.

Server-Sent Events (SSE) is the IoT-standard approach for server-to-client real-time push. FastAPI has native SSE support (EventSourceResponse, added in v0.135.0). After a reading is ingested, the ingestion service publishes to a per-user async queue; the SSE endpoint streams the event to connected browser clients immediately. This replaces both polling loops with a single persistent HTTP stream.

- Latency: from up to 15s (polling) to near-instant (SSE push immediately after each reading is ingested)

- Bandwidth: SSE connection is idle when no new data exists; polling wastes a round-trip every 15s

- Alerts delivered on the same SSE stream — no separate 30s poll needed

- SSE is unidirectional (server→client), which is exactly what a sensor dashboard requires

### **Change 3: MQTT subscribe replaces HTTP polling — and the hosting tier that makes it possible** *(v3.0 — NEW)*

v2.0 documented MQTT subscribe as a *future* upgrade path, deferred because Render's free tier spins down services after 15 minutes of inactivity and cannot hold the persistent TCP connection MQTT requires. That trade-off has now been revisited and reversed: **MQTT subscribe is moving into the current build.**

Two decisions made this possible:

1. **No ESP32 firmware change.** The ESP32 continues posting to ThingSpeak over HTTP exactly as it always has. The backend, not the device, is what switches protocols — it now subscribes directly to ThingSpeak's own MQTT broker (`mqtt3.thingspeak.com`) instead of polling ThingSpeak's REST API every 60 seconds. ThingSpeak forwards the same data it already receives from the device onward over MQTT, so the device-side contract is untouched.

2. **Hosting platform change.** Holding a persistent MQTT connection isn't possible on a service that spins down when idle, which ruled out Render's free tier. Rather than upgrading to Render's paid Starter tier, the backend moves to **Railway**, which runs containers as always-on processes by default — no idle spin-down, no upgrade needed just to keep a TCP connection alive. Railway's free option is a 30-day, $5-credit trial rather than a permanent free tier, but that's an acceptable trade-off for the current build; the team moves to Railway's Hobby tier (~$5/month) once the trial credit is used up. See Section 6 for full implementation detail.

Effect on the rest of the pipeline: ingestion latency drops from ~60s (poll interval) to ~1–3s (MQTT publish-to-receive), and the SSE layer built in v2.0 needs no redesign — it simply gets fed by MQTT message arrivals instead of a 60s poll cycle.

## **1.3 What Did NOT Change and Why**

| **Component** | **Decision** | **Rationale** |
| --- | --- | --- |
| ESP32 firmware | Kept — no changes | Continues posting to ThingSpeak via HTTP exactly as before. MQTT subscribe happens entirely on the backend side; the device has no awareness of the protocol change. |
| ThingSpeak as data source | Kept | The backend now subscribes to ThingSpeak's own MQTT broker rather than its REST API — still the same ThingSpeak channel, same data, just a faster delivery path. |
| FastAPI backend | Kept | ML-native Python; async; asyncio-mqtt subscriber replaces APScheduler for ingestion — no better IoT-compatible alternative |
| Next.js frontend | Kept | App Router + Vercel = zero-config deployment; EventSource API natively supports SSE |
| Supabase Auth | Kept | Clerk migration was evaluated (Clerk's string-based user IDs vs Supabase Auth's UUIDs) and **not pursued**. `users.id` remains `UUID`; no schema or foreign-key changes needed anywhere in the database. |
| Supabase (non-time-series tables) | Kept | users, alerts, ml_results, retrain_logs are relational data — Supabase PostgreSQL is the correct choice for these |
| XGBoost + SHAP + Isolation Forest | Kept | Validated by 2025 academic literature for water quality; no IoT-specific constraint changes this choice |

# **2. Executive Summary**

AquaSense is an IoT-driven water quality monitoring system. The hardware layer — an ESP32 microcontroller with pH, TDS, and turbidity sensors — streams readings to ThingSpeak every 60 seconds. The web application ingests this data, runs a three-layer ML pipeline, and delivers live sensor readings, WQI scores, and plain-language recommendations to end users.

v2.0 of this PRD aligned the stack with the standard five-layer IoT architecture: a TimescaleDB hypertable for time-series-optimised storage, and Server-Sent Events (SSE) replacing frontend polling.

**v3.0 moved MQTT from a documented future path into the current build, and v3.1 settles the hosting question that move raised.** The backend now subscribes directly to ThingSpeak's MQTT broker, eliminating 60-second polling latency in favor of near-real-time ingestion (~1–3s). That connection needs to stay open continuously, which Render's free tier can't do — so the backend now deploys to **Railway**, whose containers run always-on by default. Railway's free option is a 30-day trial rather than a permanent free tier, which is an accepted trade-off for now. No ESP32 firmware changes are required — the device continues posting to ThingSpeak exactly as before. Supabase Auth is retained (a Clerk migration was considered and not pursued), so the database's UUID-based user IDs are unaffected.

# **3. Updated Tech Stack**

| **Layer** | **Technology** | **Hosting** | **IoT Layer it covers** |
| --- | --- | --- | --- |
| Sensors + device | ESP32 + pH/TDS/turbidity + ThingSpeak | MathWorks cloud | Perception + Connectivity |
| Backend API + MQTT subscriber | FastAPI (Python 3.11+) + asyncio-mqtt | **Railway** (Hobby tier ~$5/mo — $5 trial credit covers initial development) | Ingestion |
| Database — relational | Supabase PostgreSQL (users, alerts, ml_results) | Supabase (free) | Storage — relational data |
| Database — time-series | TimescaleDB hypertable on readings table (PG15) | Supabase (free, PG15 project) | Storage — sensor time-series |
| Continuous aggregates | TimescaleDB hourly + daily views on readings | Same Supabase project | Storage — pre-computed chart data |
| Real-time push | FastAPI SSE (EventSourceResponse) | Railway (same service) | Application — live dashboard |
| ML pipeline | XGBoost + SHAP + Isolation Forest + EWMA | Railway (same service) | Application — analytics |
| Frontend | Next.js 15 (App Router) + TypeScript | Vercel (free) | Application — UI |
| UI components | shadcn/ui + Tailwind + Recharts | — | Application — charts + gauges |
| Auth | Supabase Auth + JWT (httpOnly cookies) | Supabase | Application — security |
| MQTT connectivity | asyncio-mqtt subscribing to ThingSpeak's broker (`mqtt3.thingspeak.com`) | Railway | Connectivity (replaces HTTP polling) |

# **4. Database Schema (Updated)**

No schema changes in v3.0. `users.id` remains `UUID DEFAULT gen_random_uuid()` — Supabase Auth is retained, so there is no Clerk string ID to accommodate and no foreign-key types to migrate.

## **4.1 readings — TimescaleDB Hypertable**

This table is unchanged from v2.0. It is created as a standard PostgreSQL table and then converted to a TimescaleDB hypertable. All existing queries remain valid SQL — no application code changes required.

| **Column** | **Type** | **Notes** |
| --- | --- | --- |
| timestamp | TIMESTAMPTZ NOT NULL | Partition key — ThingSpeak entry timestamp |
| id | UUID DEFAULT gen_random_uuid() | Row identifier |
| user_id | UUID FK → users.id | Row-level security anchor |
| ph | NUMERIC(5,2) | pH sensor value |
| tds | NUMERIC(7,2) | TDS in ppm |
| turbidity | NUMERIC(7,2) | Turbidity in NTU |
| wqi_score | NUMERIC(5,2) | Computed WQI (0–100) |
| label | TEXT | 'safe' │ 'borderline' │ 'unsafe' |

TimescaleDB configuration applied after table creation:

- SELECT create_hypertable('readings', 'timestamp', chunk_time_interval => INTERVAL '1 day');

- CREATE INDEX idx_readings_user_time ON readings (user_id, timestamp DESC);

- ALTER TABLE readings SET (timescaledb.compress, timescaledb.compress_segmentby = 'user_id');

- SELECT add_compression_policy('readings', INTERVAL '7 days');

## **4.2 Continuous Aggregates (pre-computed chart data)**

Two continuous aggregates are created for fast chart rendering. The dashboard reads from these views instead of scanning raw rows.

- readings_hourly — time_bucket(1 hour): avg pH, avg TDS, avg turbidity, avg WQI per user per hour

- readings_daily — time_bucket(1 day): same aggregates at daily resolution

The 24h chart reads from readings_hourly (last 24 buckets). The 7d and 30d charts read from readings_daily. This reduces query cost from a full table scan to a pre-materialized view lookup.

## **4.3 Other Tables (unchanged from v1)**

users, ml_results, alerts, and retrain_logs remain standard PostgreSQL tables — they are relational metadata, not time-series sensor data, and require no time-series optimisation. `users.id` stays `UUID`.

# **5. Real-Time Data Architecture (SSE)**

## **5.1 How SSE Replaces Polling**

The v1 design polled two endpoints: GET /api/readings/latest every 15s and GET /api/alerts/unread every 30s. Both are replaced by a single SSE stream per authenticated user, now fed by MQTT message arrivals rather than a polling cycle.

| **Aspect** | **v1 (Polling)** | **v3.0 (MQTT + SSE)** |
| --- | --- | --- |
| Mechanism | Client initiates GET every 15s | ThingSpeak MQTT message → backend ingests → server pushes event over persistent SSE connection |
| Latency | Up to 15s from ingest to display | Near-instant — ~1–3s from sensor publish to dashboard update |
| Bandwidth | Round-trip every 15s regardless of new data | SSE connection is idle; only transmits when data changes |
| Alerts | Separate 30s poll | Delivered on same SSE stream as readings |
| Protocol | Standard HTTP REST | MQTT (backend ingestion) + SSE (text/event-stream, frontend delivery) |
| Browser support | Universal | Universal (EventSource API, all modern browsers) |
| Hosting requirement | Render free tier — fully compatible (no persistent connection needed) | **Railway** — runs as an always-on container by default, holding the persistent MQTT connection without spin-down; SSE itself is plain HTTP and would have been free-tier-safe on its own |

## **5.2 SSE Stream Endpoint**

- Endpoint: GET /api/stream — authenticated, per-user SSE stream

- FastAPI uses EventSourceResponse (native, v0.135.0+)

- On connection: immediately emit latest reading + any unread alerts as initial state

- On each MQTT message received: parse payload → insert into readings hypertable → run ML pipeline → publish to per-user asyncio.Queue → SSE generator yields event

- Event types: reading_update (new sensor data + ML result), alert_new (new unacknowledged alert), heartbeat (every 30s to keep connection alive)

- Client uses EventSource API: const es = new EventSource('/api/stream'); es.onmessage = ...

## **5.3 SSE Architecture Flow**

- ESP32 pushes reading to ThingSpeak (every 60s) — **unchanged**

- asyncio-mqtt subscriber receives the message on the user's ThingSpeak channel topic the instant ThingSpeak publishes it — **replaces the old 60s polling job**

- New reading inserted into readings hypertable; ML pipeline runs

- Ingest service publishes {reading, ml_result, alerts} to per-user asyncio.Queue

- SSE generator (awaiting queue) receives event and yields ServerSentEvent to browser

- Browser EventSource receives event; React state updates; gauges and charts re-render

- No client-initiated HTTP request is involved after the initial SSE connection; no polling of any kind remains in the pipeline

# **6. MQTT Connectivity (v3.0 — Current Implementation)**

MQTT is the standard IoT connectivity protocol. ThingSpeak's MQTT broker supports topic-based subscriptions, so the backend receives readings the instant the ESP32's data lands in ThingSpeak — eliminating the 60s polling latency entirely. This is no longer a future upgrade path; it is part of the current build.

## **6.1 ThingSpeak MQTT Topics**

- Subscribe topic: channels/{channel_id}/subscribe/fields/field1 (per field), or channels/{channel_id}/subscribe/feeds (all fields)

- Broker: mqtt3.thingspeak.com, port 1883 (or 8883 for TLS)

- Authentication: MQTT username = ThingSpeak username, password = MQTT API key

## **6.2 Implementation**

- APScheduler's HTTP polling job is replaced by an asyncio-mqtt subscriber coroutine running continuously inside the FastAPI backend process

- On each MQTT message: parse payload → insert into readings hypertable → run ML pipeline → publish to the per-user SSE queue

- Effective latency drops from ~60s (previous polling) to ~1–3s (MQTT publish-to-receive)

- **Requires an always-on process** — the backend now runs on **Railway**, which keeps containers running continuously by default (no idle spin-down), making it a natural fit for a persistent MQTT subscriber. Railway's free tier is a 30-day, $5-credit trial rather than a permanent free tier — budget for the Hobby tier (~$5/month) once that credit is used up.

- Reconnect resilience: the subscriber should implement automatic reconnect with exponential backoff to recover from network blips or broker-side disconnects without losing data. As a safety net, on reconnect the backend can do a one-off GET to ThingSpeak's REST API to catch up on any readings published while disconnected.

## **6.3 v1 (Original) vs v3.0 (Current) Protocol Comparison**

| **Attribute** | **v1 (HTTP Polling)** | **v3.0 (MQTT Subscribe — Current)** |
| --- | --- | --- |
| Latency | ~60s (poll interval) | ~1–3s (publish → receive) |
| Protocol | HTTP REST GET | MQTT pub/sub over TCP |
| Connection type | Stateless (new req per poll) | Persistent TCP connection |
| Hosting platform | Render (free tier) | **Railway** (always-on container; $5/30-day trial credit, then ~$5/mo Hobby tier) |
| Standard IoT practice | Acceptable for low-frequency sensors | Preferred — industry standard |
| Implementation complexity | Low | Medium (asyncio-mqtt + reconnect logic) |
| ESP32 firmware impact | None | **None** — device-side behavior is identical |

# **7. Updated API Specification**

All routes from v1 are retained. Two changes carried over from v2.0: /api/stream is added (SSE); /api/readings/latest and /api/alerts/unread are kept for initial page load but are no longer polled continuously by the frontend. No further API changes in v3.0 — the MQTT switch is an internal ingestion-layer change and is transparent to the API surface.

## **7.1 New — SSE Endpoint**

| **Method** | **Endpoint** | **Auth** | **Description** |
| --- | --- | --- | --- |
| GET | GET /api/stream | User | Per-user SSE stream. Emits reading_update, alert_new, heartbeat events. Connect once; receive all live updates. |

## **7.2 Auth Routes (unchanged — Supabase Auth)**

| **Method** | **Endpoint** | **Auth** | **Description** |
| --- | --- | --- | --- |
| POST | /api/auth/signup | None | Create account; default role = user |
| POST | /api/auth/login | None | Exchange credentials for JWT |
| POST | /api/auth/logout | User | Invalidate session |
| GET | /api/auth/me | User | Return current user profile |
| PATCH | /api/auth/profile | User | Update channel_id, ts_api_key, phone |

## **7.3 Readings Routes (unchanged from v2.0 — continuous aggregate queries)**

| **Method** | **Endpoint** | **Auth** | **Description** |
| --- | --- | --- | --- |
| GET | /api/readings/latest | User | Latest reading + ML result — used for initial page load only (SSE takes over after) |
| GET | /api/readings?range=24h | User | Returns from readings_hourly continuous aggregate |
| GET | /api/readings?range=7d│30d | User | Returns from readings_daily continuous aggregate |
| GET | /api/readings/all (admin) | Admin | Readings across all users for admin dashboard |

## **7.4 Alerts, ML, Admin Routes (unchanged from v1)**

See v1 PRD Section 9.3–9.5. No changes to these endpoints.

# **8. Updated Build Phases**

| **Phase** | **Deliverable** | **Key Changes (v3.0 vs v2.0)** |
| --- | --- | --- |
| 1 | Auth + User Profile | No change — Supabase Auth retained, UUID user IDs |
| 2 | ThingSpeak MQTT Subscribe + DB (with TimescaleDB) | Create Supabase project on PG15. Enable TimescaleDB extension. Convert readings to hypertable. Create continuous aggregates. Implement the asyncio-mqtt subscriber connecting to ThingSpeak's broker (replaces HTTP polling entirely — no ESP32 firmware change). **Backend must be deployed on Railway from this phase onward** (always-on container) to hold the persistent MQTT connection. The $5 trial credit covers initial development. |
| 3 | Live Dashboard + SSE | Replace frontend polling with EventSource. Implement FastAPI SSE endpoint with per-user asyncio.Queue, now fed by MQTT message arrivals instead of a 60s poll cycle. Chart queries read from continuous aggregates. |
| 4 | ML Pipeline | No change |
| 5 | Alerts System | Alerts delivered on SSE stream (event type: alert_new) — no separate polling endpoint needed on frontend |
| 6 | Admin Panel | No change |
| 7 | Deployment | Vercel + **Railway (backend + MQTT subscriber)** + Supabase. Verify Supabase project is PG15 at creation. Confirm the MQTT connection survives Railway redeploys/restarts (reconnect logic in asyncio-mqtt). Track the $5 trial credit and budget for Railway's Hobby tier (~$5/mo) once it's exhausted. |

# **9. Key Resources & Repositories**

## **9.1 Frontend Starter (unchanged)**

- Vercel Next.js + Supabase SSR starter: https://github.com/vercel/next.js/tree/canary/examples/with-supabase

- Full-stack Next.js + FastAPI + Supabase template: https://github.com/gvago/nextjs-supabase-ai-template

- Free MIT boilerplate (auth + RLS + React Query): https://github.com/imbhargav5/nextbase-nextjs-supabase-starter

## **9.2 UI Components (unchanged)**

- shadcn/ui official charts (Recharts): https://ui.shadcn.com/charts — install: npx shadcn add chart-area-interactive

- 53 copy-paste Recharts components: https://www.shadcn.io/charts

## **9.3 TimescaleDB (from v2.0)**

- Supabase TimescaleDB extension docs: https://supabase.com/docs/guides/database/extensions/timescaledb

- IoT hypertable guide: https://oneuptime.com/blog/post/2026-01-27-timescaledb-iot/view

- Manufacturing IoT pipeline tutorial: https://www.tigerdata.com/blog/timescaledb-manufacturing-iot-building-data-pipeline

- IMPORTANT: Create Supabase project on Postgres 15 — TimescaleDB is deprecated on PG17

## **9.4 FastAPI SSE (from v2.0)**

- FastAPI SSE official docs: https://fastapi.tiangolo.com/tutorial/server-sent-events/

- Per-client queue pattern (multiple users): https://tobydevlin.com/blog/sse-server-sent-events-in-fastapi/

- SSE scales to 100K connections vs WebSocket 12K limit (2026 benchmark)

## **9.5 ML Resources (unchanged)**

- Water Quality & Potability dataset (Kaggle): https://www.kaggle.com/datasets/adityakadiwal/water-potability

- XGBoost + SHAP validated: R² = 0.9952 on Indian river water quality dataset (Nature, 2025)

- XGBoost achieves 99.83% peak accuracy on WQI prediction (IWA Publishing, 2025)

## **9.6 ThingSpeak MQTT (v3.0 — implemented)**

- ThingSpeak MQTT API docs: https://www.mathworks.com/help/thingspeak/mqtt-api.html

- asyncio-mqtt library: https://github.com/sbtinstruments/asyncio-mqtt

- Broker: mqtt3.thingspeak.com:1883

# **10. Out of Scope — v1**

- SMS / Twilio alerts — deferred to v2; phone column pre-provisioned in users table

- Email alerts — deferred to v2

- Mobile app — web app is mobile-responsive

- ORP, temperature, flow sensors — not in current ESP32 hardware setup

- Multi-device per user — one channel_id per account in v1

- InfluxDB / standalone TimescaleDB — TimescaleDB extension on Supabase PG15 is sufficient for v1 data volumes

- Clerk / third-party auth migration — evaluated, not pursued; Supabase Auth retained

*AquaSense PRD v3.1 — MQTT Connectivity Live + Railway Hosting — RV College of Engineering, Bengaluru — June 2026*
